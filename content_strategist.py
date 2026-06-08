"""
content_strategist.py — Performance-Based Strategy Context + Article Scoring
=============================================================================
Feature 2: get_strategy_context() — injects GSC/GA4 insights into the content
           generation prompt so the LLM knows what's working.

Feature 3: score_all_topics()         — composite score per published article
           get_top_and_bottom_performers() — ranked report
           generate_strategy_memo()   — weekly LLM-written strategy memo

Usage (CLI via strategy.py):
    python strategy.py --site 2 --score --report
    python strategy.py --site 2 --memo --out memos/weekly.md
"""

import os
import re
import json
import requests
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from database import get_db_connection, update_topic_status
from logger import logger


# ── Pillar normalisation ───────────────────────────────────────────────────────

_PILLAR_ALIASES: Dict[str, str] = {
    "vs_comparison":    "vs_comparison",
    "comparisons":      "vs_comparison",
    "comparison":       "vs_comparison",
    "vs":               "vs_comparison",
    "best_of":          "best_of",
    "buyer_guide":      "buyer_guide",
    "setup_tutorial":   "setup_tutorial",
    "feature_explainer":"feature_explainer",
    "explainer":        "feature_explainer",
    "use_case":         "use_case",
    "niche":            "use_case",
    "how_to":           "how_to",
    "how-to":           "how_to",
    "how to":           "how_to",
    "definition":       "definition",
    "definitions":      "definition",
    "cost_roi":         "cost_roi",
    "cost & roi":       "cost_roi",
    "pricing":          "cost_roi",
}


def _normalize_pillar(raw: str) -> str:
    return _PILLAR_ALIASES.get((raw or "").lower().strip(), raw or "other")


# ── Feature 2: Strategy Context ───────────────────────────────────────────────

def get_pillar_performance(site_id: int, days: int = 60) -> List[Dict]:
    """
    Aggregate GSC data grouped by topic pillar for the last N days.
    Join strategy: gsc_data.page LIKE '%<topic.slug>%' (same as get_stale_topics_for_refresh).

    Returns list of dicts sorted by total_clicks DESC:
      [{"pillar", "topic_count", "total_clicks", "total_impressions", "avg_ctr", "avg_position"}, ...]
    """
    conn = get_db_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    rows = conn.execute("""
        SELECT
            t.pillar,
            COUNT(DISTINCT t.id)      AS topic_count,
            SUM(g.clicks)             AS total_clicks,
            SUM(g.impressions)        AS total_impressions,
            AVG(g.ctr)                AS avg_ctr,
            AVG(g.position)           AS avg_position
        FROM topics t
        LEFT JOIN gsc_data g
            ON  g.site_id = t.site_id
            AND g.page LIKE '%' || COALESCE(t.slug, '') || '%'
            AND g.fetched_date >= ?
        WHERE t.site_id = ?
          AND t.status IN ('draft', 'published')
          AND t.slug IS NOT NULL AND t.slug != ''
        GROUP BY t.pillar
        ORDER BY total_clicks DESC
    """, (cutoff, site_id)).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["pillar"]             = _normalize_pillar(d.get("pillar", ""))
        d["total_clicks"]       = d["total_clicks"] or 0
        d["total_impressions"]  = d["total_impressions"] or 0
        d["avg_ctr"]            = round(d["avg_ctr"] or 0.0, 4)
        d["avg_position"]       = round(d["avg_position"] or 0.0, 1)
        result.append(d)
    return result


def get_rising_vs_stalling(
    site_id: int,
    days_recent: int = 14,
    days_baseline: int = 60,
) -> Dict[str, List[Dict]]:
    """
    Compare recent clicks (last days_recent) vs baseline period clicks per topic.
    A topic is "rising" if recent rate >20% above baseline; "stalling" if >30% below.

    Returns {"rising": [...], "stalling": [...]}, each list capped at 5.
    """
    conn = get_db_connection()
    recent_cutoff   = (date.today() - timedelta(days=days_recent)).isoformat()
    baseline_cutoff = (date.today() - timedelta(days=days_baseline)).isoformat()

    rows = conn.execute("""
        SELECT
            t.id, t.title, t.slug, t.pillar,
            SUM(CASE WHEN g.fetched_date >= ?
                     THEN g.clicks ELSE 0 END)                             AS recent_clicks,
            SUM(CASE WHEN g.fetched_date >= ? AND g.fetched_date < ?
                     THEN g.clicks ELSE 0 END)                             AS baseline_clicks
        FROM topics t
        LEFT JOIN gsc_data g
            ON  g.site_id = t.site_id
            AND g.page LIKE '%' || COALESCE(t.slug, '') || '%'
        WHERE t.site_id = ?
          AND t.status IN ('draft', 'published')
          AND t.slug IS NOT NULL AND t.slug != ''
        GROUP BY t.id
        HAVING (recent_clicks > 0 OR baseline_clicks > 0)
    """, (recent_cutoff, baseline_cutoff, recent_cutoff, site_id)).fetchall()
    conn.close()

    rising, stalling = [], []
    for r in [dict(r) for r in rows]:
        rc = r["recent_clicks"] or 0
        bc = r["baseline_clicks"] or 0
        # Normalise baseline to the same window length as recent
        bc_norm = bc * (days_recent / max(days_baseline - days_recent, 1))
        if rc > bc_norm * 1.2:
            rising.append(r)
        elif rc < bc_norm * 0.7:
            stalling.append(r)

    rising.sort(key=lambda x: x["recent_clicks"], reverse=True)
    stalling.sort(key=lambda x: x["baseline_clicks"], reverse=True)
    return {"rising": rising[:5], "stalling": stalling[:5]}


def get_strategy_context(site_id: int, days: int = 60) -> str:
    """
    Build a compact plain-text block summarising GSC/GA4 performance.
    Injected as {strategy_section} into the content generation prompt.

    Returns "" (empty string) when no data exists — safe for new sites.
    The prompt template handles the empty case without adding blank sections.
    """
    try:
        pillar_perf = get_pillar_performance(site_id, days)
        trend_data  = get_rising_vs_stalling(site_id)
    except Exception as exc:
        logger.warning(f"[strategy_context] Could not load data for site {site_id}: {exc}")
        return ""

    # No clicks recorded yet — don't inject misleading empty tables
    if not pillar_perf or all(p["total_clicks"] == 0 for p in pillar_perf):
        return ""

    lines = [
        "=== CONTENT PERFORMANCE CONTEXT (last 60 days) ===",
        "\nPillar performance across your published articles:",
        f"  {'Pillar':<22} {'Topics':>6} {'Clicks':>7} {'Impr':>8} {'CTR':>6} {'Pos':>5}",
    ]
    for p in pillar_perf[:8]:
        lines.append(
            f"  {p['pillar']:<22} {p['topic_count']:>6} {p['total_clicks']:>7} "
            f"{p['total_impressions']:>8} {p['avg_ctr']*100:>5.1f}% {p['avg_position']:>5.1f}"
        )

    if trend_data.get("rising"):
        lines.append("\nRising content (study these patterns):")
        for r in trend_data["rising"][:3]:
            lines.append(f"  [{_normalize_pillar(r['pillar'])}] {r['title']}")

    if trend_data.get("stalling"):
        lines.append("\nStalling content (avoid these patterns):")
        for r in trend_data["stalling"][:3]:
            lines.append(f"  [{_normalize_pillar(r['pillar'])}] {r['title']}")

    if pillar_perf:
        best_ctr = max(pillar_perf, key=lambda x: x["avg_ctr"])
        best_vol = max(pillar_perf, key=lambda x: x["total_clicks"])
        lines.append(
            f"\nHighest CTR pillar: {best_ctr['pillar']} ({best_ctr['avg_ctr']*100:.1f}%)"
        )
        if best_vol["pillar"] != best_ctr["pillar"]:
            lines.append(
                f"Highest volume pillar: {best_vol['pillar']} ({best_vol['total_clicks']} clicks)"
            )
        lines.append(
            "Apply these insights within the required template structure — do not deviate from it."
        )

    return "\n".join(lines)


# ── Feature 3: Article Scoring ────────────────────────────────────────────────

SCORE_WEIGHTS: Dict[str, float] = {
    "impressions": 0.30,
    "ctr":         0.40,
    "position":    0.30,   # applied to 1/position so lower position = higher score
}

SCORE_TIERS: Dict[str, Tuple[float, float]] = {
    "top_performer": (75.0, 100.0),
    "rising":        (50.0,  75.0),
    "stalled":       (25.0,  50.0),
    "declining":     ( 0.0,  25.0),
}

_TIER_NO_DATA = "no_data"


def _normalize_values(values: List[float]) -> List[float]:
    """Min-max normalize a list of floats to 0–100. Returns 50.0 for constant lists."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [(v - lo) / (hi - lo) * 100.0 for v in values]


def _assign_tier(score: float) -> str:
    for tier, (lo, hi) in SCORE_TIERS.items():
        if lo <= score <= hi:
            return tier
    return "declining"


def score_all_topics(site_id: int, days: int = 60) -> Dict[str, int]:
    """
    Compute and persist composite performance scores for all published/draft topics.

    Algorithm:
      1. Fetch GSC rows for site in window; map to topics via slug LIKE match.
      2. Per topic: raw = (total_impressions, avg_ctr, 1/avg_position).
      3. Min-max normalise each dimension across all topics → 0–100.
      4. score = norm_impr*0.30 + norm_ctr*0.40 + norm_pos_inv*0.30
      5. Tier: top_performer>=75, rising>=50, stalled>=25, declining<25.
      6. Persist: performance_score, last_scored_at, score_tier via update_topic_status.

    Returns stats dict: {scored, no_data, top_performer, rising, stalled, declining}
    """
    conn   = get_db_connection()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    today  = date.today().isoformat()

    # All published/draft topics with a slug
    topic_rows = conn.execute("""
        SELECT id, slug, title, pillar, status
        FROM topics
        WHERE site_id = ?
          AND status IN ('draft', 'published')
          AND slug IS NOT NULL AND slug != ''
    """, (site_id,)).fetchall()
    topics = [dict(r) for r in topic_rows]

    if not topics:
        conn.close()
        logger.info(f"[scorer] No published/draft topics found for site {site_id}")
        return {"scored": 0, "no_data": 0}

    # Batch-fetch all GSC rows for the site in this window
    gsc_rows = conn.execute("""
        SELECT page, clicks, impressions, ctr, position
        FROM gsc_data
        WHERE site_id = ? AND fetched_date >= ?
    """, (site_id, cutoff)).fetchall()
    gsc_rows = [dict(r) for r in gsc_rows]
    conn.close()

    # Index GSC rows by topic_id using slug substring match
    gsc_by_topic: Dict[int, List[Dict]] = defaultdict(list)
    for row in gsc_rows:
        page = row.get("page", "")
        for t in topics:
            if t["slug"] and t["slug"] in page:
                gsc_by_topic[t["id"]].append(row)

    # Compute raw (un-normalised) values per topic
    raw: Dict[int, Tuple[float, float, float]] = {}  # topic_id → (impr, ctr, pos_inv)
    for t in topics:
        rows_for_topic = gsc_by_topic.get(t["id"], [])
        if not rows_for_topic:
            continue
        total_impr = sum(r.get("impressions", 0) for r in rows_for_topic)
        avg_ctr    = sum(r.get("ctr", 0.0) for r in rows_for_topic) / len(rows_for_topic)
        avg_pos    = sum(r.get("position", 50.0) for r in rows_for_topic) / len(rows_for_topic)
        pos_inv    = 1.0 / max(avg_pos, 1.0)
        raw[t["id"]] = (float(total_impr), avg_ctr, pos_inv)

    stats: Dict[str, int] = {
        "scored": 0, "no_data": 0,
        "top_performer": 0, "rising": 0, "stalled": 0, "declining": 0,
    }

    if not raw:
        # No GSC data at all — mark everything no_data
        for t in topics:
            update_topic_status(
                t["id"], t["status"],
                score_tier=_TIER_NO_DATA,
                last_scored_at=today,
            )
        stats["no_data"] = len(topics)
        logger.info(f"[scorer] No GSC data found — {len(topics)} topics marked no_data")
        return stats

    # Min-max normalise each dimension independently
    topic_ids_with_data = list(raw.keys())
    impr_vals  = [raw[tid][0] for tid in topic_ids_with_data]
    ctr_vals   = [raw[tid][1] for tid in topic_ids_with_data]
    pos_vals   = [raw[tid][2] for tid in topic_ids_with_data]

    norm_impr = _normalize_values(impr_vals)
    norm_ctr  = _normalize_values(ctr_vals)
    norm_pos  = _normalize_values(pos_vals)

    scored_map: Dict[int, Tuple[float, str]] = {}  # topic_id → (score, tier)
    for i, tid in enumerate(topic_ids_with_data):
        score = (
            norm_impr[i] * SCORE_WEIGHTS["impressions"] +
            norm_ctr[i]  * SCORE_WEIGHTS["ctr"]         +
            norm_pos[i]  * SCORE_WEIGHTS["position"]
        )
        score = round(min(max(score, 0.0), 100.0), 2)
        tier  = _assign_tier(score)
        scored_map[tid] = (score, tier)

    # Persist scores
    for t in topics:
        tid = t["id"]
        if tid in scored_map:
            score, tier = scored_map[tid]
            update_topic_status(
                tid, t["status"],
                performance_score=score,
                last_scored_at=today,
                score_tier=tier,
            )
            stats["scored"] += 1
            stats[tier] = stats.get(tier, 0) + 1
        else:
            update_topic_status(
                tid, t["status"],
                score_tier=_TIER_NO_DATA,
                last_scored_at=today,
            )
            stats["no_data"] += 1

    logger.info(
        f"[scorer] site {site_id}: {stats['scored']} scored, {stats['no_data']} no_data | "
        f"top={stats['top_performer']} rising={stats['rising']} "
        f"stalled={stats['stalled']} declining={stats['declining']}"
    )
    return stats


def get_top_and_bottom_performers(site_id: int, n: int = 5) -> Dict[str, List[Dict]]:
    """
    Return top N (highest score) and bottom N (lowest score) scored topics.
    Excludes no_data tier from the bottom list.
    """
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, title, pillar, performance_score, score_tier, writing_persona, slug, status
        FROM topics
        WHERE site_id = ?
          AND score_tier IS NOT NULL
          AND score_tier != 'no_data'
          AND performance_score IS NOT NULL
        ORDER BY performance_score DESC
    """, (site_id,)).fetchall()
    conn.close()

    all_scored = [dict(r) for r in rows]
    return {
        "top":    all_scored[:n],
        "bottom": all_scored[-n:] if len(all_scored) >= n else list(reversed(all_scored)),
    }


# ── Feature 3: Strategy Memo ──────────────────────────────────────────────────

def generate_strategy_memo(site_id: int) -> str:
    """
    Call the LLM via OpenRouter to produce a ~400-word Markdown strategy memo.

    Sections:
      1. What's Working
      2. Warning Signs
      3. Specific Recommendations (3–5 actionable items)
      4. Content Mix Guidance (pillar priorities for next 4 weeks)

    Returns the Markdown string. Raises RuntimeError on failure.
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if not openrouter_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set — cannot generate strategy memo. "
            "Add it to .env and try again."
        )

    # Gather data
    pillar_perf  = get_pillar_performance(site_id, days=60)
    trend_data   = get_rising_vs_stalling(site_id)
    performers   = get_top_and_bottom_performers(site_id, n=5)

    conn = get_db_connection()
    tier_counts = {
        r["score_tier"]: r["cnt"]
        for r in conn.execute("""
            SELECT score_tier, COUNT(*) AS cnt
            FROM topics
            WHERE site_id = ? AND score_tier IS NOT NULL
            GROUP BY score_tier
        """, (site_id,)).fetchall()
    }
    conn.close()

    # Build prompt
    prompt = f"""You are a content performance analyst. Based on this data, write a concise weekly strategy memo (Markdown, ~400 words).

Required sections:
1. **What's Working** — highlight high-CTR pillars and top-performing articles
2. **Warning Signs** — stalling/declining articles and low-CTR pillars to fix
3. **Specific Recommendations** — 3–5 concrete, actionable next steps with rationale
4. **Content Mix Guidance** — which pillar types to prioritise in the next 4 weeks and why

=== PILLAR PERFORMANCE (last 60 days) ===
{json.dumps(pillar_perf, indent=2)}

=== TOP PERFORMERS ===
{json.dumps(performers['top'], indent=2)}

=== BOTTOM PERFORMERS ===
{json.dumps(performers['bottom'], indent=2)}

=== RISING / STALLING TOPICS ===
Rising:   {json.dumps(trend_data['rising'], indent=2)}
Stalling: {json.dumps(trend_data['stalling'], indent=2)}

=== SCORE TIER DISTRIBUTION ===
{json.dumps(tier_counts, indent=2)}

Be direct. Use the actual data — reference specific pillars, titles, and numbers. Return Markdown only."""

    logger.info(f"[memo] Requesting strategy memo for site {site_id} via OpenRouter...")
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://shaunsocial.com",
                "X-Title": "Content Strategy Memo",
            },
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a content strategy analyst. Be concise, direct, and data-driven. Return Markdown only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1200,
                "temperature": 0.4,
            },
            timeout=60,
        )
        resp.raise_for_status()
        memo = resp.json()["choices"][0]["message"]["content"].strip()
        logger.info(f"[memo] Strategy memo generated ({len(memo)} chars)")
        return memo
    except Exception as exc:
        raise RuntimeError(f"Strategy memo generation failed: {exc}") from exc


# ── Feature 4: Data-Driven Template Proposals ─────────────────────────────────

def _read_template_library() -> List[Dict]:
    """Summarise each existing template (name + heading outline) so the LLM can
    avoid proposing duplicates. Lazy-imports content_generator to dodge a cycle."""
    from content_generator import TEMPLATES_DIR, available_template_stems
    library: List[Dict] = []
    for stem in available_template_stems():
        try:
            text = (TEMPLATES_DIR / f"{stem}.md").read_text(encoding="utf-8")
        except Exception:
            continue
        headings = [ln.strip() for ln in text.splitlines() if ln.lstrip().startswith("#")]
        library.append({"name": stem, "headings": headings[:25]})
    return library


def _parse_proposals_json(raw: str) -> List[Dict]:
    """Best-effort parse of the LLM's JSON proposals payload."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        candidate = match.group(1) if match else raw
        start, end = candidate.find("{"), candidate.rfind("}") + 1
        candidate = candidate[start:end] if start != -1 and end > 0 else candidate
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            from json_repair import repair_json
            data = json.loads(repair_json(candidate))
    proposals = data.get("proposals", data) if isinstance(data, dict) else data
    return proposals if isinstance(proposals, list) else []


def suggest_templates(site_id: int, n_top: int = 10, max_proposals: int = 3) -> Dict:
    """
    Propose NEW reusable content templates from performance data.

    Looks at the top-scoring articles + pillar performance + the existing template
    library, and asks the LLM to propose content structures that would capture more
    traffic/citations — only when meaningfully different from what already exists.

    Proposals are written to templates/proposed/ for human review. They are NOT
    activated: available_template_stems() globs only the top-level templates dir,
    so a proposal has no effect until a human moves it into templates/.

    Returns {"proposals": [...], "saved_to": str|None, "skipped": str|None}.
    Raises RuntimeError if OPENROUTER_API_KEY is missing.
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if not openrouter_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set — cannot suggest templates. Add it to .env."
        )

    performers  = get_top_and_bottom_performers(site_id, n=n_top)
    pillar_perf = get_pillar_performance(site_id, days=60)
    library     = _read_template_library()
    existing_names = [t["name"] for t in library]

    if not performers["top"]:
        return {
            "proposals": [], "saved_to": None,
            "skipped": "No scored articles yet — run scoring first (strategy.py --score).",
        }

    prompt = f"""You are a content template strategist. Using the performance data below,
propose NEW reusable article templates (content structures) that would help this site
capture more search traffic and AI citations.

=== TOP-PERFORMING ARTICLES (highest composite score) ===
{json.dumps(performers['top'], indent=2)}

=== PILLAR PERFORMANCE (last 60 days, GSC) ===
{json.dumps(pillar_perf, indent=2)}

=== EXISTING TEMPLATE LIBRARY (name + heading outline) — DO NOT DUPLICATE THESE ===
{json.dumps(library, indent=2)}

Return JSON ONLY in this exact shape:
{{"proposals": [
  {{"name": "lowercase_slug", "when_to_use": "1 sentence on the search intent/topic type this fits",
    "rationale": "why the data justifies a new template (cite specific pillars/scores)",
    "markdown": "# Title Template\\n\\n...full template in the same style as the existing ones..."}}
]}}

Rules:
- Propose AT MOST {max_proposals} templates. Propose FEWER, even zero (empty list), if the
  existing library already covers the high-performing patterns — quality over quantity.
- Each proposal MUST be meaningfully different from every existing template: {existing_names}.
- "name" is a lowercase underscore slug and must NOT match any existing template name.
- "markdown" must follow the same structure style as the existing templates AND must include
  a TL;DR block and an FAQ section (these are mandatory AEO/GEO blocks).
- Ground every proposal in the data — reference the pillars/titles/scores that justify it.
Return valid JSON only, no commentary."""

    logger.info(f"[templates] Requesting template proposals for site {site_id} via OpenRouter...")
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://shaunsocial.com",
                "X-Title": "Content Template Proposals",
            },
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [
                    {"role": "system", "content": "You are a content template strategist. Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 4000,
                "temperature": 0.5,
            },
            timeout=90,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"Template proposal request failed: {exc}") from exc

    proposals = _parse_proposals_json(raw)

    # Persist proposals for human review (NOT into the active templates dir).
    from content_generator import TEMPLATES_DIR
    proposed_dir = TEMPLATES_DIR / "proposed"
    existing_lower = {n.lower() for n in existing_names}

    saved: List[Dict] = []
    for p in proposals[:max_proposals]:
        if not isinstance(p, dict):
            continue
        markdown = (p.get("markdown") or "").strip()
        raw_name = p.get("name") or ""
        slug = re.sub(r"[\s\-&/]+", "_", raw_name.strip().lower())
        slug = re.sub(r"_+", "_", slug).strip("_")
        if not slug or not markdown:
            continue
        if slug in existing_lower:
            logger.info(f"[templates] Skipping proposal '{slug}' — duplicates an existing template.")
            continue

        proposed_dir.mkdir(parents=True, exist_ok=True)
        header = (
            "<!-- PROPOSED TEMPLATE — review before activating.\n"
            f"When to use: {p.get('when_to_use', '').strip()}\n"
            f"Rationale:   {p.get('rationale', '').strip()}\n"
            f"To activate: move this file up into {TEMPLATES_DIR} (out of 'proposed/').\n"
            "-->\n\n"
        )
        out_path = proposed_dir / f"{slug}.md"
        out_path.write_text(header + markdown + "\n", encoding="utf-8")
        saved.append({
            "name": slug,
            "when_to_use": p.get("when_to_use", "").strip(),
            "rationale": p.get("rationale", "").strip(),
            "path": str(out_path),
        })
        logger.info(f"[templates] Proposed new template '{slug}' → {out_path}")

    return {
        "proposals": saved,
        "saved_to": str(proposed_dir) if saved else None,
        "skipped": None if saved else "No new templates proposed — existing library already covers the patterns.",
    }
