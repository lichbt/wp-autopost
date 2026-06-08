"""
Rewrite 4 existing ShaunSocial articles with AEO-optimised content.

Articles:
  #1  Best Social Network Software 2026       → PATCH WP#2765  (keep slug)
  #2  Best Frameworks to Build Social Net 2026 → PATCH WP#1802  (keep slug)
  #3  Best WoWonder Alternative 2026           → NEW POST       (new slug)
  #4  Best White Label Social Media Platform   → NEW POST       (new slug)

Run:
  python3 rewrite_articles.py            # all 4
  python3 rewrite_articles.py 1          # article #1 only
  python3 rewrite_articles.py 1 2        # articles 1 and 2
"""
import json
import sqlite3
import sys
import os
import requests

sys.path.insert(0, ".")

# Load .env manually
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from database import get_site
from content_generator import generate_post_content
from template_assembler import assemble_final_html
from wp_publisher import publish_post, _build_json_ld, _xmlrpc_set_yoast_meta
from logger import logger

SITE_ID = 4
DB_PATH = "data/blog_automation.db"

# ─── Article definitions ───────────────────────────────────────────────────────
# mode: "patch" = update existing WP post (same URL)
#        "new"   = create new WP post (new slug)
LENGTH_PREAMBLE = (
    "MANDATORY LENGTH REQUIREMENT: The 'content' field must be AT LEAST 2,500 words of body HTML. "
    "Do NOT stop early. Write every section in FULL — multiple paragraphs per section, not just bullet points. "
    "Each individual product/platform/framework review section must be 150–250 words minimum. "
    "Every H2 section must contain at least 2 full paragraphs PLUS a list or table. "
    "Do NOT abbreviate, summarize, or use placeholder text. This is a long-form SEO article. "
    "If you finish a section and the total content so far is under 2,000 words, add more depth before moving on. "
)

REWRITE_ARTICLES = {
    1: {
        "topic_id": 133,
        "wp_post_id": 2765,
        "mode": "patch",
        "title": "Best Social Network Software in 2026: Full Comparison (Updated)",
        "pillar": "best_of",
        "slug": "best-social-network-softwares-in-2025-comparison",  # keep existing slug
        "target_keywords": [
            "best social network software 2026",
            "best social networking software",
            "social network software comparison",
            "social networking platform",
        ],
        "intent": "commercial",
        "special_instructions": (
            LENGTH_PREAMBLE +
            "AEO REWRITE of existing post. Keep slug best-social-network-softwares-in-2025-comparison unchanged. "
            "Update ALL '2025' date references to '2026'. "
            "OPEN with a 3-sentence direct answer box answering 'What is the best social networking software in 2026?'. "
            "First sentence must contain 'best social network software 2026'. "
            "Structure:\n"
            "1. Direct Answer box (3 sentences, wrap in <div class='quick-answer'>)\n"
            "2. Introduction: Why choosing the right social network software matters in 2026 — "
            "discuss market trends, open-source vs hosted, cost of mistakes. WRITE 2 full paragraphs.\n"
            "3. Comparison Table: ShaunSocial, phpFox, WoWonder, Sngine, HumHub, SocialEngine — "
            "columns: Software / Best For / Starting Price / Hosting / Mobile App / Open Source / Active Development\n"
            "4. Individual reviews — for EACH of the 6 platforms write a separate H2 section (150-250 words each) with: "
            "overview paragraph, pros list (4+ items), cons list (2+ items), pricing details, best for sentence. "
            "ShaunSocial is #1 with emphasis on: native iOS+Android app, full PHP source code, one-time purchase price, "
            "active updates, community features, demo at https://shaunsocial.com/demo/.\n"
            "5. How to Choose section (200+ words): budget considerations, hosting requirements, mobile app need, "
            "technical skill, support expectations — build a decision framework.\n"
            "6. FAQ: 8 questions answering: 'what is the best social networking software?', "
            "'what software is used to build social networks?', 'is there a free social network software?', "
            "'which social network platform is best for business?', 'can I build my own social network?', "
            "'how much does social network software cost?', 'what is the difference between HumHub and ShaunSocial?', "
            "'does ShaunSocial have a mobile app?'. Write full paragraph answers (50+ words each).\n"
            "Every H2 phrased as a question. No <h1> tags. Total target: 2,500+ words."
        ),
    },
    2: {
        "topic_id": 163,
        "wp_post_id": 1802,
        "mode": "patch",
        "title": "Best Frameworks to Build a Social Network in 2026 (Developer Guide)",
        "pillar": "best_of",
        "slug": "best-frameworks-to-create-a-social-network-in-2025",  # keep existing slug
        "target_keywords": [
            "best framework to build social network",
            "social network framework",
            "social networking website development",
            "build social network website",
            "social network development framework",
        ],
        "intent": "informational",
        "special_instructions": (
            LENGTH_PREAMBLE +
            "AEO REWRITE. Keep slug best-frameworks-to-create-a-social-network-in-2025 unchanged. "
            "Update ALL '2025' to '2026'. "
            "OPEN with a 3-sentence direct answer box: 'What is the best framework to build a social network in 2026?' "
            "First sentence: 'The best framework to build a social network in 2026 is...' "
            "Structure:\n"
            "1. Direct Answer box (3 sentences)\n"
            "2. Why Framework Choice Matters (200+ words): cover cost of getting it wrong, "
            "custom build vs ready-made tradeoffs, timeline comparisons. Include cost comparison table: "
            "Ready-Made (ShaunSocial) vs Custom (Laravel/React) — columns: Cost / Time to Launch / Maintenance / Scalability.\n"
            "3. Comparison Table of all options: ShaunSocial (Ready-Made), Laravel, React+Node.js, Django, "
            "Ruby on Rails, Vue.js+Express — columns: Language / Best For / Learning Curve / Time to Launch / Hosting / Cost Range.\n"
            "4. Individual framework sections — 6 sections, 150-200 words EACH:\n"
            "   - ShaunSocial (#1 recommended): what it includes out-of-box, mobile app, source code, pricing, "
            "who it's best for, demo link https://shaunsocial.com/demo/\n"
            "   - Laravel: strengths for social apps, ecosystem, real-world examples, limitations\n"
            "   - React + Node.js: real-time features, modern stack, when to choose it, skill requirements\n"
            "   - Django: Python-based, rapid prototyping, admin panel strengths, weaknesses for social features\n"
            "   - Ruby on Rails: fast MVPs, convention-over-config, community size, declining usage\n"
            "   - Vue.js + Express: lightweight, good for smaller communities, JavaScript full-stack\n"
            "5. Step-by-Step: 'How to Start Social Network Website Development in 2026' — "
            "5 full steps, each with 2-3 sentences of explanation:\n"
            "   Step 1: Define your niche and audience\n"
            "   Step 2: Choose approach (ready-made vs custom build)\n"
            "   Step 3: Set up hosting and domain\n"
            "   Step 4: Configure core features (profiles, feeds, messaging)\n"
            "   Step 5: Launch, market, and iterate\n"
            "6. FAQ: 8 questions — 'what framework is used to build social networks?', "
            "'how much does it cost to build a social network website?', "
            "'how long does it take to build a social network?', "
            "'is Laravel good for social networking?', "
            "'can I build a social network without coding?', "
            "'what is ShaunSocial built with?', "
            "'is React or Vue better for social networks?', "
            "'how to build a social network website from scratch?'. "
            "Write full paragraph answers (50+ words each).\n"
            "Every H2 phrased as a question. No <h1> tags. Total target: 2,500+ words."
        ),
    },
    3: {
        "topic_id": 130,
        "wp_post_id": 3534,   # already created — patch it
        "mode": "patch",
        "title": "Best WoWonder Alternative in 2026: Full Comparison (7 Options)",
        "pillar": "vs_comparison",
        "slug": "best-wowonder-alternative-2026",
        "target_keywords": [
            "best wowonder alternative",
            "wowonder alternative",
            "wowonder alternatives",
            "shaunsocial vs wowonder",
        ],
        "intent": "commercial",
        "special_instructions": (
            LENGTH_PREAMBLE +
            "AEO article: the best WoWonder alternatives in 2026. "
            "OPEN with a bold direct-answer box (wrap in <div class='quick-answer'>): "
            "'The best WoWonder alternative in 2026 is ShaunSocial — it offers a native iOS+Android mobile app, "
            "active monthly updates, full PHP source code, and competitive one-time pricing.' "
            "Structure:\n"
            "1. Direct Answer box\n"
            "2. Why People Switch from WoWonder (200+ words, 2+ paragraphs): "
            "Cover these specific pain points honestly — "
            "WoWonder's update schedule has slowed significantly (mention it's been years since major features), "
            "no official native mobile app (only a PWA), limited official support channels, "
            "small developer community, dated UI compared to competitors. Be factual, not defamatory.\n"
            "3. Quick Comparison Table (ALL 7 alternatives): "
            "ShaunSocial, Sngine, SocialEngine, phpFox, ColibriSM, HumHub, BuddyBoss — "
            "columns: Platform / Starting Price / Native Mobile App / Open Source / Self-Hosted / Last Major Update / Best For\n"
            "4. Detailed reviews — write a SEPARATE H3 section for EACH of the 7 platforms (150-200 words each):\n"
            "   - ShaunSocial: pricing (one-time license), iOS+Android native app, full PHP source, active updates, "
            "demo at https://shaunsocial.com/demo/, pros: [4+ items], cons: [2 items]\n"
            "   - Sngine: PHP script, CodeCanyon marketplace, features overview, pros/cons, pricing\n"
            "   - SocialEngine: long-established platform, plugin marketplace, pros/cons, pricing\n"
            "   - phpFox: enterprise-focused, subscription pricing, pros/cons\n"
            "   - ColibriSM: newer entrant, lightweight, CodeCanyon, pros/cons, pricing\n"
            "   - HumHub: open source, free core, enterprise edition, pros/cons\n"
            "   - BuddyBoss: WordPress-based, LMS integration, pros/cons, pricing\n"
            "5. ShaunSocial Spotlight section (200+ words): deep dive — full feature list, "
            "mobile app capabilities, admin panel, customization options, pricing tiers, "
            "migration path from WoWonder (import users, posts, data), support options\n"
            "6. Head-to-Head: ShaunSocial vs WoWonder table — "
            "rows: Native Mobile App / Last Major Update / PHP Source Code / Starting Price / "
            "Support Channel / Community Size / Hosting Options / Demo Available\n"
            "7. How to Choose section (150+ words): decision tree based on budget, technical skill, mobile needs\n"
            "8. FAQ: 6 questions with full paragraph answers (60+ words each): "
            "'Is WoWonder still actively developed?', "
            "'What is the cheapest WoWonder alternative?', "
            "'Does ShaunSocial have a mobile app?', "
            "'Can I migrate from WoWonder to ShaunSocial?', "
            "'Is WoWonder free to use?', "
            "'What is the best free WoWonder alternative?'\n"
            "Every H2/H3 phrased as a question or clear label. No <h1> tags. Total target: 2,000+ words."
        ),
    },
    4: {
        "topic_id": 110,
        "wp_post_id": 3536,   # already created — patch it
        "mode": "patch",
        "title": "Best White Label Social Media Platform in 2026 (Ranked & Compared)",
        "pillar": "best_of",
        "slug": "best-white-label-social-media-platform-2026",
        "target_keywords": [
            "white label social media platform",
            "white label community platform",
            "white label social media app",
            "white label social network software",
        ],
        "intent": "commercial",
        "special_instructions": (
            LENGTH_PREAMBLE +
            "AEO article targeting three keyword clusters: 'white label social media platform', "
            "'white label community platform', 'white label social media app'. "
            "OPEN with a direct-answer box (wrap in <div class='quick-answer'>): "
            "'A white-label social media platform is software you fully brand as your own — "
            "no vendor branding visible to users. Best options in 2026: ShaunSocial (self-hosted, one-time price), "
            "Bettermode (cloud SaaS), HumHub (open source). Choose based on budget and mobile app needs.' "
            "Structure:\n"
            "1. Direct Answer box\n"
            "2. What Is a White Label Social Media Platform? (200+ words): "
            "Define white-labeling in the context of social software. Explain the 4 key characteristics: "
            "custom domain, full brand control (logo, colors, name), no vendor watermarks, modular features. "
            "Contrast with open-source (different concept) and SaaS-with-branding (partial white-label). "
            "Explain who uses white-label social platforms: businesses, agencies, communities, NGOs.\n"
            "3. Comparison Table (8 platforms): "
            "ShaunSocial, Bettermode, Hivebrite, HumHub, phpFox, SocialEngine, Mighty Networks, Disciple.media — "
            "columns: Platform / Starting Price / Hosting / Native Mobile App / Custom Domain / "
            "White-Label Depth (full/partial) / Best For\n"
            "4. Detailed reviews — 8 platform sections, 150-200 words EACH:\n"
            "   - ShaunSocial (#1): one-time pricing, self-hosted on your server, native iOS+Android app, "
            "full PHP source code access, complete white-labeling, demo at https://shaunsocial.com/demo/\n"
            "   - Bettermode: cloud SaaS, $499+/month, PWA mobile, strong integrations, no source code\n"
            "   - Hivebrite: enterprise-focused, alumni/association use case, higher pricing\n"
            "   - HumHub: open source, free core + enterprise edition, self-hosted, developer-friendly\n"
            "   - phpFox: subscription licensing, large plugin library, established since 2005\n"
            "   - SocialEngine: PHP script, one-time + annual, plugin marketplace\n"
            "   - Mighty Networks: course+community hybrid, not truly white-label, mobile app\n"
            "   - Disciple.media: mobile-first, subscription, good for creator communities\n"
            "5. Dedicated section: 'What Is the Best White Label Community Platform in 2026?' (200+ words): "
            "Target the 'white label community platform' keyword. Focus on community-specific features: "
            "member directory, forums, groups, events, notifications, gamification. "
            "Rank top 3: ShaunSocial, HumHub, Bettermode for community use.\n"
            "6. Dedicated section: 'Best White Label Social Media App in 2026' (200+ words): "
            "Target 'white label social media app' keyword. Compare native app vs PWA vs React Native approaches. "
            "ShaunSocial has native iOS+Android. Others use PWA. Explain why native matters for engagement.\n"
            "7. Buyer Decision Guide (200+ words): "
            "Self-Hosted vs SaaS breakdown, Budget tiers (<$5k one-time vs monthly subscription), "
            "Technical skill required for each, Recommendation chart.\n"
            "8. FAQ: 6 questions with full paragraph answers (60+ words each): "
            "'What is a white label social media platform?', "
            "'Which white label social media platform has the best mobile app?', "
            "'Is ShaunSocial a white label platform?', "
            "'What is the cheapest white label community platform?', "
            "'Can I use my own domain with a white label social platform?', "
            "'What is the difference between white label and open source social software?'\n"
            "Every H2 phrased as a question. No <h1> tags. Total target: 2,500+ words."
        ),
    },
}

# CTA mapping
CTA_MAP = {
    "best_of": ("https://shaunsocial.com/demo/", "Try ShaunSocial Free Demo"),
    "vs_comparison": ("https://shaunsocial.com/demo/", "Try ShaunSocial Demo"),
}

SCHEMA_MAP = {
    "best_of": "Article",
    "vs_comparison": "Article",
}


def _run_claude_cli(prompt: str, timeout: int = 300) -> str:
    """Call `claude -p <prompt>` and return stdout. Raises on failure."""
    import subprocess
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error (exit {result.returncode}): {result.stderr[:300]}")
    return result.stdout.strip()


def generate_long_content(topic: dict, site: dict) -> dict:
    """
    Two-pass content generation via `claude -p` CLI.

    Pass 1 — Full HTML body via claude CLI (no JSON wrapper, full length).
    Pass 2 — Metadata JSON via claude CLI.
    """
    import re, json as _json

    title = topic["title"]
    pillar = topic.get("pillar", "best_of")
    keywords = ", ".join(topic.get("target_keywords", []))
    instructions = topic.get("special_instructions", "")

    # Fetch published posts for internal links
    try:
        wp_url = site.get("wp_url", "").rstrip("/")
        auth = (site["wp_username"], site["wp_app_password"])
        resp = requests.get(
            f"{wp_url}/wp-json/wp/v2/posts",
            params={"status": "publish", "per_page": 40, "_fields": "title,link"},
            auth=auth, timeout=10,
        )
        posts = [{"title": p["title"]["rendered"], "url": p["link"]}
                 for p in resp.json() if p.get("link") and "?" not in p.get("link", "")]
    except Exception:
        posts = []

    link_context = "\n".join(f'- "{p["title"]}" → {p["url"]}' for p in posts) if posts else ""

    # Strip FAQ section from instructions for body prompt — it will be added separately
    body_instructions = re.sub(
        r'\n?\s*\d+\.\s+FAQ:.*?(?=\nEvery\s|\n\s*\d+\.|\Z)',
        '',
        instructions,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # ── PASS 1: Full HTML body ─────────────────────────────────────────────────
    body_prompt = f"""You are an expert long-form SEO content writer. Write the COMPLETE HTML body for the article below.

RETURN ONLY HTML — no markdown fences, no JSON, no explanation. Start directly with the first <div> or <h2> tag.

Title: {title}
Target Keywords: {keywords}

=== ARTICLE INSTRUCTIONS ===
{body_instructions}

=== INTERNAL LINKS — insert 4-6 naturally in body paragraphs ===
{link_context or "No internal links available."}

=== OUTPUT RULES ===
- Return ONLY clean HTML body (no <html>, no <body>, no <h1>)
- Use <h2> and <h3> headings
- Every individual product/platform/framework gets its OWN <h2> or <h3> section with: a 3-4 sentence overview paragraph, a <ul> features list, a pros <ul>, a cons <ul>, pricing detail, and a verdict sentence
- Include at least one <table> for comparison
- ⚠️ Do NOT include a FAQ section — FAQ will be added as a separate section after your output. SKIP any FAQ numbered section from the instructions above.
- Minimum 2,500 words — write every section in full, do not abbreviate"""

    logger.info(f"[Claude CLI] Generating HTML body for: {title}")
    body_html = ""
    try:
        body_html = _run_claude_cli(body_prompt, timeout=300)
        # Strip any accidental markdown fences
        body_html = re.sub(r'^```(?:html)?\s*', '', body_html, flags=re.MULTILINE)
        body_html = re.sub(r'\s*```\s*$', '', body_html, flags=re.MULTILINE)
        logger.info(f"[Claude CLI] Body: {len(body_html)} chars")
    except Exception as e:
        logger.warning(f"[Claude CLI] Body generation failed: {e}")

    if not body_html or len(body_html) < 2000:
        logger.warning("[Claude CLI] Body too short — falling back to generate_post_content()")
        from content_generator import generate_post_content
        return generate_post_content(topic, site, {})

    # Extract FAQ questions from original instructions to guide pass 2
    faq_match = re.search(
        r'\d+\.\s+FAQ:.*?(?=\nEvery\s|\n\s*\d+\.|\Z)',
        instructions,
        flags=re.DOTALL | re.IGNORECASE,
    )
    faq_instructions = faq_match.group(0).strip() if faq_match else ""

    # ── PASS 2: Metadata ───────────────────────────────────────────────────────
    meta_prompt = f"""Return a JSON object for this article. Return ONLY valid JSON, nothing else.

Title: {title}
Keywords: {keywords}

{f"=== FAQ REQUIREMENTS ==={chr(10)}{faq_instructions}{chr(10)}" if faq_instructions else ""}
Required keys:
- "tldr": 2-3 confident sentences directly answering the main question
- "meta_title": SEO title under 60 chars containing the primary keyword
- "meta_description": under 155 chars, includes keyword and a call-to-action
- "focus_keyword": the single most important 2-4 word keyword
- "slug": URL-friendly slug under 60 chars
- "faq": HTML string containing ALL the FAQ items from the FAQ requirements above (or 6 items if none specified). Format EACH item as: <div class="faq-item"><h3>Question?</h3><p>Answer in 60+ words — full paragraph, not a list.</p></div>. Do NOT include an outer <h2> or <section> wrapper — just the individual <div class="faq-item"> blocks."""

    logger.info(f"[Claude CLI] Generating metadata for: {title}")
    meta = {}
    try:
        raw = _run_claude_cli(meta_prompt, timeout=120)
        # Extract JSON object
        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start != -1 and end > 0:
            raw = raw[start:end]
        meta = _json.loads(raw)
    except Exception as e:
        logger.warning(f"[Claude CLI] Metadata generation failed: {e}")
        meta = {
            "tldr": "",
            "meta_title": title[:60],
            "meta_description": f"Compare the best {title.lower()} options for 2026.",
            "focus_keyword": topic.get("target_keywords", [""])[0],
            "slug": re.sub(r"[^a-z0-9]+", "-", title.lower())[:60],
            "faq": "",
        }

    return {**meta, "content": body_html}


def patch_wp_post(site: dict, wp_post_id: int, title: str, content_html: str,
                  meta_description: str, focus_keyword: str, seo_title: str,
                  schema_type: str, faq_html: str) -> bool:
    """Update an existing WP post content via REST API PATCH."""
    wp_url = site.get("wp_url", "").rstrip("/")
    auth = (site["wp_username"], site["wp_app_password"])

    json_ld = _build_json_ld(title, schema_type, meta_description or "", faq_html)
    full_content = json_ld + "\n" + content_html

    payload = {
        "title": title,
        "content": full_content,
        "status": "publish",
    }

    try:
        resp = requests.post(
            f"{wp_url}/wp-json/wp/v2/posts/{wp_post_id}",
            json=payload,
            auth=auth,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            logger.info(f"PATCH WP#{wp_post_id} OK")
            # Update Yoast SEO meta
            yoast_fields = {
                "_yoast_wpseo_schema_article_type": schema_type,
            }
            if meta_description:
                yoast_fields["_yoast_wpseo_metadesc"] = meta_description[:155]
            if focus_keyword:
                yoast_fields["_yoast_wpseo_focuskw"] = focus_keyword
            if seo_title:
                yoast_fields["_yoast_wpseo_title"] = seo_title[:60] + " %%sep%% %%sitename%%"
            _xmlrpc_set_yoast_meta(wp_url, site["wp_username"], site["wp_app_password"],
                                   wp_post_id, yoast_fields)
            return True
        else:
            print(f"  ✗ PATCH failed: HTTP {resp.status_code} — {resp.text[:300]}")
            return False
    except Exception as e:
        print(f"  ✗ PATCH error: {e}")
        return False


def update_db_wp_post_id(conn, topic_id: int, wp_post_id: int):
    conn.execute(
        "UPDATE topics SET wp_post_id=?, status='published' WHERE id=?",
        (wp_post_id, topic_id),
    )
    conn.commit()


def main():
    # Parse CLI args: which article numbers to process
    if len(sys.argv) > 1:
        nums = [int(x) for x in sys.argv[1:] if x.isdigit()]
    else:
        nums = [1, 2, 3, 4]

    site = get_site(SITE_ID)
    if not site:
        print(f"ERROR: site_id={SITE_ID} not found")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    plan_context = {
        "default_pillar_template_hints": {
            "best_of": (
                "Open with the top pick immediately in a direct answer box. "
                "Include a ranked comparison table early. "
                "Add pros/cons for each tool. "
                "Link to demo or pricing for top pick."
            ),
            "vs_comparison": (
                "Open with a direct verdict. "
                "Compare head-to-head across key dimensions. "
                "Include a side-by-side comparison table. "
                "Recommend ShaunSocial with demo CTA."
            ),
        }
    }

    for num in nums:
        art = REWRITE_ARTICLES.get(num)
        if not art:
            print(f"Unknown article number: {num}")
            continue

        print(f"\n{'='*60}")
        print(f"Article #{num}: {art['title']}")
        print(f"Mode: {art['mode'].upper()} | Pillar: {art['pillar']}")
        print(f"{'='*60}")

        topic = {
            "id": art["topic_id"],
            "title": art["title"],
            "pillar": art["pillar"],
            "target_keywords": art["target_keywords"],
            "special_instructions": art["special_instructions"],
            "intent": art.get("intent", "informational"),
        }

        try:
            # 1. Generate content — two-pass for long-form depth
            print("Generating content (two-pass)...")
            content = generate_long_content(topic, site)
            print(f"  Content: {len(content.get('content', ''))} chars")

            tldr        = content.get("tldr", "")
            body_html   = content.get("content", "")
            faq_html    = content.get("faq", "")
            meta_desc   = content.get("meta_description", "")
            meta_title  = content.get("meta_title", art["title"])
            focus_kw    = content.get("focus_keyword", art["target_keywords"][0])

            cta_link, cta_text = CTA_MAP.get(art["pillar"], ("https://shaunsocial.com/demo/", "Learn More"))
            schema_type = SCHEMA_MAP.get(art["pillar"], "Article")

            # 2. Assemble HTML
            print("Assembling HTML...")
            final_html = assemble_final_html(
                site=site,
                title=art["title"],
                tldr=tldr,
                content=body_html,
                faq=faq_html,
                meta_description=meta_desc,
                meta_title=meta_title,
                cta_link=cta_link,
                cta_text=cta_text,
            )
            print(f"  Final HTML: {len(final_html)} chars")

            # 3. Publish or patch
            if art["mode"] == "patch":
                print(f"Patching WP#{art['wp_post_id']}...")
                ok = patch_wp_post(
                    site=site,
                    wp_post_id=art["wp_post_id"],
                    title=art["title"],
                    content_html=final_html,
                    meta_description=meta_desc,
                    focus_keyword=focus_kw,
                    seo_title=meta_title,
                    schema_type=schema_type,
                    faq_html=faq_html,
                )
                if ok:
                    print(f"  ✓ WP#{art['wp_post_id']} updated successfully")
                    # Keep topic status as published, just note the refresh
                    conn.execute(
                        "UPDATE topics SET status='published' WHERE id=?",
                        (art["topic_id"],)
                    )
                    conn.commit()
                else:
                    print(f"  ✗ Patch failed for article #{num}")

            else:  # mode == "new"
                print(f"Publishing new post (slug: {art['slug']})...")
                wp_id = publish_post(
                    site=site,
                    title=art["title"],
                    content_html=final_html,
                    status="publish",
                    slug=art["slug"],
                    meta_description=meta_desc,
                    focus_keyword=focus_kw,
                    seo_title=meta_title,
                    schema_type=schema_type,
                    faq_html=faq_html,
                )
                if wp_id:
                    print(f"  ✓ Published! WP post ID: {wp_id}")
                    # Ensure publish status
                    resp = requests.post(
                        f"{site['wp_url'].rstrip('/')}/wp-json/wp/v2/posts/{wp_id}",
                        json={"status": "publish"},
                        auth=(site["wp_username"], site["wp_app_password"]),
                        headers={"Content-Type": "application/json"},
                        timeout=20,
                    )
                    if resp.status_code in (200, 201):
                        print(f"  ✓ Status confirmed: publish")
                    update_db_wp_post_id(conn, art["topic_id"], wp_id)
                    print(f"  ✓ DB updated: topic #{art['topic_id']} → wp_post_id={wp_id}")
                    if art.get("wp_post_id"):
                        print(f"  ℹ  Old post WP#{art['wp_post_id']} still exists — consider 301 redirect or trash it")
                else:
                    print(f"  ✗ Publish failed for article #{num}")

        except Exception as e:
            import traceback
            print(f"✗ Error on article #{num}: {e}")
            traceback.print_exc()

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
