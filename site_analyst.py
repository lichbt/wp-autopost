"""
Interactive content plan generator.

Flow:
  1. Loads site intake YAML (sites/<slug>.yaml)
  2. Pulls GSC + GA4 summaries from DB (fetches fresh data if credentials set)
  3. Feeds context to Claude → receives a structured JSON plan
  4. Displays plan in the terminal
  5. Enters a chat loop: user types feedback, Claude revises
  6. User types 'approve' → imports to DB | 'save' → exports to file | 'quit' → exits
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from claude_cli import claude_complete
import yaml

from config import CLAUDE_ANALYSIS_MODEL, DRY_RUN, PROJECT_ROOT, SITES_DIR
from database import (
    get_site, get_gsc_summary, get_ga4_summary, get_topics_summary,
    add_plan, add_topics_bulk,
)
from logger import logger

# ── ANSI colour helpers ───────────────────────────────────────────────────────

def _c(text: str, code: str) -> str:
    """Wrap text in an ANSI colour code."""
    return f"\033[{code}m{text}\033[0m"

BOLD  = lambda t: _c(t, "1")
GREEN = lambda t: _c(t, "32")
CYAN  = lambda t: _c(t, "36")
YELLOW= lambda t: _c(t, "33")
DIM   = lambda t: _c(t, "2")
RED   = lambda t: _c(t, "31")

GEO_PILLARS = {"vs_comparison", "best_of", "buyer_guide"}  # highest citation value

# ── Site intake YAML ──────────────────────────────────────────────────────────

def find_intake_yaml(site_id: int) -> Optional[Path]:
    """Look for any YAML in sites/ that contains this site_id."""
    if not SITES_DIR.exists():
        return None
    for f in SITES_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text())
            if data and data.get("site_id") == site_id:
                return f
        except Exception:
            continue
    return None


def load_intake(site_id: int) -> Dict:
    """Load site intake YAML. Returns empty dict if not found."""
    path = find_intake_yaml(site_id)
    if not path:
        logger.warning(f"No intake YAML found for site {site_id} in sites/. Using DB info only.")
        return {}
    data = yaml.safe_load(path.read_text())
    logger.info(f"Loaded intake from {path.name}")
    return data or {}


# ── Context builder ───────────────────────────────────────────────────────────

def _fmt_gsc_rows(rows: List[Dict], limit: int = 15) -> str:
    if not rows:
        return "  (no data)"
    lines = []
    for r in rows[:limit]:
        lines.append(
            f"  {r.get('query','')[:60]:<62} "
            f"imp={r.get('impressions',0):>6}  "
            f"clicks={r.get('clicks',0):>5}  "
            f"pos={r.get('avg_position', r.get('position', 0)):>5.1f}"
        )
    return "\n".join(lines)


def _fmt_ga4_rows(rows: List[Dict], limit: int = 10) -> str:
    if not rows:
        return "  (no data)"
    lines = []
    for r in rows[:limit]:
        lines.append(
            f"  {r.get('page_path','')[:50]:<52} "
            f"sessions={r.get('sessions',0):>6}  "
            f"pageviews={r.get('pageviews',0):>6}"
        )
    return "\n".join(lines)


def _fmt_existing_topics(topics: List[Dict], limit: int = 50) -> str:
    if not topics:
        return "  (no existing topics)"
    by_status: Dict[str, List] = {}
    for t in topics[:limit]:
        s = t.get("status", "unknown")
        by_status.setdefault(s, []).append(t.get("title", ""))
    lines = []
    for status, titles in by_status.items():
        lines.append(f"  [{status.upper()}] ({len(titles)} posts)")
        for title in titles[:5]:
            lines.append(f"    - {title}")
        if len(titles) > 5:
            lines.append(f"    ... and {len(titles)-5} more")
    return "\n".join(lines)


def _fmt_wp_posts(posts: List[Dict], limit: int = 300) -> str:
    """Format live WP posts for the Claude planning prompt."""
    if not posts:
        return "  (none — site may be new or credentials not set)"
    lines = []
    for p in posts[:limit]:
        slug  = p.get("slug", "")
        title = p.get("title", "")
        lines.append(f"  /{slug}/ — {title}")
    if len(posts) > limit:
        lines.append(f"  ... and {len(posts) - limit} more (not shown)")
    return "\n".join(lines)


def build_analysis_prompt(intake: Dict, gsc: Dict, ga4: Dict, existing: List[Dict], num_topics: int, wp_posts: List[Dict] = None, planner_signals: str = "") -> str:
    site_name = intake.get("name", "Unknown Site")
    site_url = intake.get("url", "")
    niche = intake.get("niche", "")
    product = intake.get("product_name", site_name)
    audience = intake.get("target_audience", [])
    competitors = intake.get("competitors", [])
    pillars = intake.get("content_pillars", [])
    cta_url = intake.get("main_cta", site_url)
    tone = intake.get("tone", "professional")
    posts_per_day = intake.get("posts_per_day", 2)
    today = date.today().isoformat()

    competitor_names = ", ".join(
        (c["name"] if isinstance(c, dict) else c) for c in competitors
    )

    audience_str = (
        "\n  - ".join(audience) if isinstance(audience, list) else str(audience)
    )

    gsc_top = _fmt_gsc_rows(gsc.get("top_queries", []))
    gsc_low_ctr = _fmt_gsc_rows(gsc.get("low_ctr_opportunities", []))
    ga4_top = _fmt_ga4_rows(ga4.get("top_pages", []))
    existing_str = _fmt_existing_topics(existing)
    wp_posts_list = wp_posts or []
    wp_posts_str = _fmt_wp_posts(wp_posts_list)
    signals_block = (f"\n## 📊 PERFORMANCE SIGNALS — let these DRIVE the plan\n{planner_signals}\n"
                     if planner_signals else "")

    # Available content-structure templates (discovered from the templates dir),
    # offered to the planner so it can pick the best-fit structure per topic.
    try:
        from content_generator import available_template_stems
        available_templates = ", ".join(available_template_stems()) or "how_to"
    except Exception:
        available_templates = "vs_comparison, best_of, buyer_guide, setup_tutorial, feature_explainer, use_case, how_to, definition, cost_roi"

    # Compute a date schedule: posts_per_day posts/day over the horizon
    horizon_days = max(14, num_topics // posts_per_day + 1)

    return f"""You are a senior content strategist generating a data-driven {horizon_days}-day content plan.

## SITE CONTEXT
Site: {site_name}
URL: {site_url}
Niche: {niche}
Product: {product}
CTA: {cta_url}
Tone: {tone}
Target audience:
  - {audience_str}
Competitors: {competitor_names}
Content pillars: {", ".join(pillars) if isinstance(pillars, list) else pillars}

## EXISTING CONTENT IN DB (automation-tracked)
{existing_str}

## LIVE WORDPRESS POSTS — DO NOT SUGGEST THESE
These articles already exist on the live site. Do NOT propose any topic that
covers the same subject matter, even with a different year or angle:
{wp_posts_str}
(Total live: {len(wp_posts_list)} posts)

## GOOGLE SEARCH CONSOLE — Top Queries (last 30 days)
{gsc_top}

## GSC — Low CTR Opportunities (high impressions, poor click-through)
{gsc_low_ctr}

## GA4 — Top Pages by Sessions (last 30 days)
{ga4_top}
{signals_block}
## TASK
Today: {today}
Generate exactly {num_topics} blog topics for a {horizon_days}-day publishing plan
at {posts_per_day} post(s) per day.

PRIORITISE BY PERFORMANCE (most important):
0. STRIKING DISTANCE FIRST — for queries already ranking pos 8–20 (see PERFORMANCE SIGNALS),
   create or refresh a focused article to push them onto page 1. These are the highest-ROI topics.
   If a page already exists for that query, propose action="refresh" with its target_url instead of a new post.
1. DOUBLE DOWN on pillars/article patterns that already perform well; AVOID the underperformer patterns.
2. REFRESH decaying pages (listed under DECAYING PAGES) rather than writing new ones on the same subject.

Then optimise for TWO goals simultaneously:
A. Google SEO — target the GSC queries above; fix low-CTR pages with better title/angle; cover gaps competitors own.
B. GEO (Generative Engine Optimisation) — structure topics so AI systems (ChatGPT, Perplexity, Gemini, Claude) will cite them.
   GEO priority order: vs_comparison > best_of > buyer_guide > setup_tutorial > feature_explainer > use_case

CRITICAL: Do NOT suggest any topic whose title or subject closely matches any entry
in EXISTING CONTENT IN DB or LIVE WORDPRESS POSTS above. Check both lists carefully.

For each topic return:
  - title: exact post title (SEO-optimized, includes year if relevant)
  - pillar: one of [vs_comparison, best_of, buyer_guide, setup_tutorial, feature_explainer, use_case, how_to, definition, cost_roi]
  - recommended_template: the content STRUCTURE that best fits THIS topic's search intent.
    Choose one of: [{available_templates}]. It usually matches the pillar, but pick a
    different one when the SERP/intent calls for it (e.g. a topic filed under "best_of"
    that is really a walkthrough → "setup_tutorial"). Use null to fall back to the pillar default.
  - action: "new" (write a new post) or "refresh" (improve an existing live post). Use "refresh"
    for decaying pages and for striking-distance queries that already have a page.
  - target_url: for action="refresh", the existing URL to update; otherwise null.
  - priority: high / medium / low (striking-distance & refresh items should usually be high)
  - intent: commercial / informational / navigational
  - target_keywords: array of 3–5 keyword strings
  - internal_links: array of URLs to link to within this post (or [])
  - special_instructions: specific writing guidance (what tables, what comparisons, what data to include)
  - scheduled_date: YYYY-MM-DD (distribute evenly, {posts_per_day}/day, starting tomorrow)
  - cluster: the topic-cluster/hub this article belongs to (a short theme name, e.g. "WoWonder alternatives").
    Organise ALL topics into 3–5 clusters. Each cluster has ONE pillar/hub page plus supporting articles.
  - is_pillar_page: true for the single hub page of its cluster, false for supporting articles.
  - geo_rationale: 1-sentence reason this will be cited by AI systems
  - gsc_opportunity: the specific GSC query this targets (or null)

Topic-cluster rules: group topics into 3–5 clusters around your highest-value themes. In each cluster,
the pillar page targets the broad head term and each supporting article targets a specific long-tail/intent.
Set internal_links so supporting articles link to their pillar page and the pillar links back to supporters.

Also return a "global" object:
  - strategy_summary: 3-sentence executive summary
  - priority_reasoning: why topics are ordered this way
  - default_pillar_template_hints: writing guidance per pillar
  - posts_per_month: number
  - overall_strategy_goal: one sentence

Return valid JSON only — no commentary.
JSON structure: {{"topics": [...], "global": {{...}}}}"""


# ── Tier 2: self-critique / refine pass ───────────────────────────────────────

def build_critique_prompt(plan: Dict, existing: List[Dict], wp_posts: List[Dict],
                          planner_signals: str = "") -> str:
    """Prompt a skeptical editor pass to prune duplicates/cannibalisation, tighten
    clusters, and swap weak topics for higher-opportunity ones."""
    return f"""You are a skeptical senior content editor reviewing a DRAFT content plan before it ships.
Return an IMPROVED version of the plan. Apply these checks rigorously:

1. DEDUPE & CANNIBALISATION — remove or merge topics that duplicate each other, or that closely match
   any entry in EXISTING CONTENT or LIVE WORDPRESS POSTS below (two pages targeting the same query hurt
   each other). When two drafts overlap, keep the stronger one.
2. CLUSTER COHERENCE — every topic must belong to a cluster; each cluster has exactly ONE pillar/hub page
   (is_pillar_page=true) and ≥2 supporting articles, with internal_links wiring supporters↔pillar.
3. INTENT MIX — ensure a healthy mix of commercial and informational intent; fix obvious gaps.
4. OPPORTUNITY — drop vague/low-value topics. If you drop any, REPLACE them (keep the same total count)
   with stronger topics that exploit the PERFORMANCE SIGNALS (striking-distance queries, winning pillars).
5. Preserve every required field, including action/target_url for refreshes and recommended_template.

=== DRAFT PLAN ===
{json.dumps(plan, ensure_ascii=False)[:14000]}

=== EXISTING CONTENT IN DB ===
{_fmt_existing_topics(existing)}

=== LIVE WORDPRESS POSTS ===
{_fmt_wp_posts(wp_posts or [])}

=== PERFORMANCE SIGNALS ===
{planner_signals or '(none)'}

Return the improved plan as valid JSON ONLY, same schema: {{"topics": [...], "global": {{...}}}}."""


def critique_and_refine_plan(plan: Dict, existing: List[Dict], wp_posts: List[Dict],
                             planner_signals: str = "") -> Dict:
    """Run one editor pass; return the refined plan, or the original on any failure
    or if the critique returns fewer than half the topics (likely a parse problem)."""
    try:
        raw = _call_claude([{"role": "user", "content":
                             build_critique_prompt(plan, existing, wp_posts, planner_signals)}])
        refined = _parse_plan_json(raw)
        if len(refined.get("topics", [])) >= max(1, len(plan.get("topics", [])) // 2):
            return refined
        logger.warning("[critique] refined plan too small — keeping original")
    except Exception as exc:
        logger.warning(f"[critique] refine pass failed, keeping original: {exc}")
    return plan


# ── Display plan ──────────────────────────────────────────────────────────────

def display_plan(plan: Dict, site_name: str = ""):
    topics = plan.get("topics", [])
    g = plan.get("global", {})
    today = date.today().isoformat()

    print("\n" + "="*70)
    print(BOLD(f"  CONTENT PLAN — {site_name}"))
    print(f"  Generated: {today}  |  {len(topics)} topics")
    print("="*70)

    if g.get("strategy_summary"):
        print(f"\n{CYAN('Strategy:')} {g['strategy_summary']}")
    if g.get("priority_reasoning"):
        print(f"{DIM('Ordering:')} {g['priority_reasoning']}")

    print(f"\n{BOLD('─── TOPICS ───────────────────────────────────────────────────────────')}")

    for i, t in enumerate(topics, 1):
        pillar = t.get("pillar", "")
        priority = t.get("priority", "medium")
        geo_flag = GREEN(" ★GEO") if pillar in GEO_PILLARS else ""
        priority_colour = GREEN if priority == "high" else (YELLOW if priority == "medium" else DIM)

        print(f"\n  {BOLD(f'#{i:02d}')} [{CYAN(pillar)}]{geo_flag}  {priority_colour(f'[{priority.upper()}]')}")
        print(f"      {BOLD(t.get('title', ''))}")
        kws = ", ".join(t.get("target_keywords", [])[:3])
        print(f"      {DIM('Keywords:')} {kws}")
        sched = t.get("scheduled_date", "TBD")
        intent = t.get("intent", "")
        print(f"      {DIM('Date:')} {sched}  {DIM('Intent:')} {intent}")
        if t.get("geo_rationale"):
            print(f"      {DIM('GEO:')} {t['geo_rationale']}")
        if t.get("gsc_opportunity"):
            print(f"      {DIM('GSC:')} {t['gsc_opportunity']}")
        if t.get("special_instructions"):
            print(f"      {DIM('Notes:')} {t['special_instructions'][:100]}")

    # Pillar breakdown
    from collections import Counter
    pillar_counts = Counter(t.get("pillar", "?") for t in topics)
    print(f"\n{BOLD('─── PILLAR BREAKDOWN ─────────────────────────────────────────────────')}")
    for pillar, count in pillar_counts.most_common():
        geo_flag = " ★" if pillar in GEO_PILLARS else ""
        print(f"  {pillar:<20}{geo_flag}  {count} posts")

    print("\n" + "="*70 + "\n")


# ── Claude chat ───────────────────────────────────────────────────────────────

def _call_claude(messages: List[Dict]) -> str:
    system = ("You are a senior content strategist. When revising a plan, return the FULL "
              "updated plan as valid JSON only — no commentary. Preserve all topics not "
              "explicitly changed.")
    # Flatten the (possibly multi-turn) conversation into one prompt for the CLI.
    if len(messages) == 1:
        prompt = messages[0].get("content", "")
    else:
        prompt = "\n\n".join(f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
                             for m in messages)
    return claude_complete(prompt, system=system, model=CLAUDE_ANALYSIS_MODEL, timeout=600).strip()


def _parse_plan_json(raw: str) -> Dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        if match:
            return json.loads(match.group(1))
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > 0:
            return json.loads(raw[start:end])
        raise ValueError("Could not parse JSON from Claude response")


def _get_mock_plan(site_name: str, num_topics: int) -> Dict:
    """Dry-run mock plan."""
    today = date.today()
    topics = []
    pillars = ["vs_comparison", "best_of", "buyer_guide", "setup_tutorial", "feature_explainer", "use_case"]
    for i in range(min(num_topics, 6)):
        topics.append({
            "title": f"[DRY RUN] Sample Topic #{i+1} for {site_name}",
            "pillar": pillars[i % len(pillars)],
            "priority": "high" if i < 2 else "medium",
            "intent": "commercial" if i < 3 else "informational",
            "target_keywords": ["sample keyword", f"keyword {i+1}"],
            "internal_links": [],
            "special_instructions": "Dry-run mode — no real content.",
            "scheduled_date": (today + timedelta(days=i+1)).isoformat(),
            "geo_rationale": "Dry-run placeholder.",
            "gsc_opportunity": None,
        })
    return {
        "topics": topics,
        "global": {
            "strategy_summary": "This is a dry-run mock plan.",
            "priority_reasoning": "Ordered for demonstration only.",
            "default_pillar_template_hints": {},
            "posts_per_month": 60,
            "overall_strategy_goal": "Dry-run demonstration.",
        },
    }


# ── Main interactive session ──────────────────────────────────────────────────

def generate_plan_interactive(site_id: int, num_topics: int = 30, fresh_data: bool = True):
    """
    Full interactive plan generation session.

    Args:
        site_id: DB site ID
        num_topics: How many topics to generate
        fresh_data: If True, refresh GSC/GA4 from APIs before generating
    """
    site = get_site(site_id)
    if not site:
        print(RED(f"Site {site_id} not found in database."))
        sys.exit(1)

    site_name = site.get("name", f"Site {site_id}")
    print(f"\n{BOLD('Content Plan Generator')} — {CYAN(site_name)}")
    print("─"*50)

    # Optional: refresh API data
    if fresh_data and not DRY_RUN:
        from data_collector import collect_site_data
        print("Fetching fresh GSC + GA4 data...")
        result = collect_site_data(site_id)
        if result["gsc_rows"]:
            print(GREEN(f"  ✓ GSC: {result['gsc_rows']} rows"))
        if result["ga4_rows"]:
            print(GREEN(f"  ✓ GA4: {result['ga4_rows']} rows"))

    # Load context
    intake = load_intake(site_id)
    # Merge site DB info into intake if YAML is sparse
    if not intake.get("name"):
        intake["name"] = site_name
    if not intake.get("url"):
        intake["url"] = site.get("wp_url", "")
    if not intake.get("posts_per_day"):
        intake["posts_per_day"] = site.get("posts_per_day", 2)

    gsc = get_gsc_summary(site_id)
    ga4 = get_ga4_summary(site_id)
    existing = get_topics_summary(site_id)

    # Fetch live WP posts so Claude avoids proposing duplicates
    wp_posts: List[Dict] = []
    if not DRY_RUN:
        try:
            from wp_sync import get_wp_post_list
            wp_posts = get_wp_post_list(site)
            print(GREEN(f"  ✓ Live WP posts fetched: {len(wp_posts)}"))
        except Exception as exc:
            print(YELLOW(f"  ⚠ Could not fetch live WP posts: {exc}"))

    # Tier 1: performance feedback signals (striking-distance, pillar perf, decay)
    planner_signals = ""
    sig = {}
    try:
        from content_strategist import get_planner_signals, format_planner_signals
        sig = get_planner_signals(site_id)
        planner_signals = format_planner_signals(sig)
        if planner_signals:
            sd = len([l for l in planner_signals.splitlines() if l.strip().startswith("•")])
            print(GREEN(f"  ✓ Performance signals loaded ({sd} data points)"))
    except Exception as exc:
        print(YELLOW(f"  ⚠ Could not load performance signals: {exc}"))

    # Tier 3: live keyword research (Serper if keyed, else free Google autocomplete)
    if not DRY_RUN:
        try:
            from keyword_research import get_keyword_research_block
            seeds = [q.get("query") for q in sig.get("striking_distance", [])]
            seeds += [q.get("query") for q in gsc.get("top_queries", [])[:6]]
            seeds = [s for s in seeds if s]
            if not seeds:
                # No GSC data yet → seed from intake (niche + competitor names)
                comp = [(c["name"] if isinstance(c, dict) else c)
                        for c in (intake.get("competitors") or [])]
                seeds = [intake.get("niche") or intake.get("name", "")] + comp[:3]
                seeds = [s for s in seeds if s]
            kw_block = get_keyword_research_block(seeds)
            if kw_block:
                planner_signals = (planner_signals + "\n\n" + kw_block).strip()
                src = "Serper" if "via Serper" in kw_block else "Google Autocomplete (free)"
                print(GREEN(f"  ✓ Keyword research added via {src} ({len(kw_block.splitlines())} lines)"))
        except Exception as exc:
            print(YELLOW(f"  ⚠ Keyword research skipped: {exc}"))

    print(f"  Existing topics in DB: {len(existing)}")
    print(f"  GSC query rows: {len(gsc.get('top_queries', []))}")
    print(f"  GA4 page rows:  {len(ga4.get('top_pages', []))}")
    print(f"\nAsking Claude to generate {num_topics} topics...")

    # Initial plan generation
    if DRY_RUN:
        plan = _get_mock_plan(site_name, num_topics)
        print(YELLOW("  [DRY RUN] Mock plan generated — install/log in the claude CLI for real output."))
    else:
        analysis_prompt = build_analysis_prompt(intake, gsc, ga4, existing, num_topics,
                                                wp_posts=wp_posts, planner_signals=planner_signals)
        messages: List[Dict] = [{"role": "user", "content": analysis_prompt}]
        try:
            raw = _call_claude(messages)
            plan = _parse_plan_json(raw)
            # Store assistant reply for conversation continuity
            messages.append({"role": "assistant", "content": raw})
        except Exception as e:
            print(RED(f"Claude failed: {e}"))
            sys.exit(1)

        # Tier 2: self-critique / refine pass (dedupe, cannibalisation, clusters)
        print("Refining plan (self-critique pass)...")
        before = len(plan.get("topics", []))
        plan = critique_and_refine_plan(plan, existing, wp_posts, planner_signals)
        after = len(plan.get("topics", []))
        print(GREEN(f"  ✓ Plan refined ({before} → {after} topics after dedupe/cannibalisation check)"))

    display_plan(plan, site_name)

    # Interactive refinement loop
    print(f"{BOLD('Commands:')} type feedback to refine | {GREEN('approve')} to import | {YELLOW('save')} to export | {RED('quit')} to exit")
    print()

    while True:
        try:
            user_input = input(f"{BOLD('>')} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM('Exiting without importing.')}")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd == "quit" or cmd == "exit":
            print(DIM("Exiting without importing."))
            break

        elif cmd == "approve":
            _import_plan(site_id, plan, intake)
            break

        elif cmd == "save":
            _save_plan(plan, site_id, site_name)

        elif cmd.startswith("save "):
            path = cmd[5:].strip()
            _save_plan(plan, site_id, site_name, path)

        elif cmd == "show":
            display_plan(plan, site_name)

        else:
            # Send feedback to Claude
            if DRY_RUN:
                print(YELLOW("[DRY RUN] Cannot refine plan without the claude CLI."))
                continue
            print(DIM("Updating plan with Claude..."))
            messages.append({"role": "user", "content": (
                f"Please update the content plan based on this feedback:\n\n{user_input}\n\n"
                "Return the FULL updated plan as JSON (topics + global). "
                "Preserve all topics not explicitly changed."
            )})
            try:
                raw = _call_claude(messages)
                updated_plan = _parse_plan_json(raw)
                messages.append({"role": "assistant", "content": raw})
                plan = updated_plan
                display_plan(plan, site_name)
            except Exception as e:
                print(RED(f"Failed to update plan: {e}"))


def _import_plan(site_id: int, plan: Dict, intake: Dict):
    """Import the approved plan into the database."""
    topics = plan.get("topics", [])
    if not topics:
        print(RED("No topics in plan — nothing to import."))
        return

    import json
    plan_id = add_plan(
        site_id=site_id,
        raw_markdown=f"Generated by site_analyst on {date.today().isoformat()}",
        extracted_json=json.dumps(plan),
    )
    add_topics_bulk(site_id, plan_id, topics)
    print(GREEN(f"\n✓ Imported {len(topics)} topics (plan ID: {plan_id})"))
    print(DIM("  Run `python main.py --site {sid} --run-once` to start publishing.".replace("{sid}", str(site_id))))


def _save_plan(plan: Dict, site_id: int, site_name: str, path: str = ""):
    if not path:
        slug = site_name.lower().replace(" ", "_")
        path = f"plan_{slug}_{date.today().isoformat()}.json"
    out = Path(path)
    out.write_text(json.dumps(plan, indent=2))
    print(GREEN(f"✓ Plan saved to {out}"))
