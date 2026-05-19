import json
import re
import time
from pathlib import Path
from typing import Dict, Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_CONTENT_MODEL, DRY_RUN, MAX_RETRIES, RETRY_DELAYS, PROJECT_ROOT
from logger import logger

TEMPLATES_DIR = PROJECT_ROOT / "templates"

PILLAR_TO_FILE = {
    "vs_comparison": "vs_comparison.md",
    "best_of": "best_of.md",
    "buyer_guide": "buyer_guide.md",
    "setup_tutorial": "setup_tutorial.md",
    "feature_explainer": "feature_explainer.md",
    "use_case": "use_case.md",
    "how-to": "how_to.md",
    "how_to": "how_to.md",
    "how to": "how_to.md",
    "comparisons": "vs_comparison.md",
    "comparison": "vs_comparison.md",
    "vs": "vs_comparison.md",
    "definition": "definition.md",
    "definitions": "definition.md",
    "explainer": "feature_explainer.md",
    "cost & roi": "cost_roi.md",
    "cost_roi": "cost_roi.md",
    "cost": "cost_roi.md",
    "roi": "cost_roi.md",
    "pricing": "cost_roi.md",
    "niche": "use_case.md",
    "market": "use_case.md",
}

CONTENT_SYSTEM_PROMPT = """You are an expert SEO and GEO (Generative Engine Optimization) content writer.
Your posts are designed to rank on Google AND be cited by AI systems (ChatGPT, Perplexity, Gemini, Claude).

GEO writing rules:
1. State the direct answer in the FIRST sentence — AI lifts this as the snippet
2. Use specific, citable facts and numbers (not vague claims)
3. Structured comparison tables are gold — AI extracts these for recommendations
4. Every H2 should be a complete, quotable statement
5. FAQ questions must mirror real natural-language queries (how people ask AI)
6. Never use marketing fluff — be authoritative and direct

You MUST follow the provided blog template structure exactly."""


def load_template(pillar: str) -> Optional[str]:
    pillar_lower = pillar.lower().strip()
    filename = PILLAR_TO_FILE.get(pillar_lower)
    if not filename:
        for key, val in PILLAR_TO_FILE.items():
            if key in pillar_lower or pillar_lower in key:
                filename = val
                break
    if not filename:
        filename = "how_to.md"
    template_path = TEMPLATES_DIR / filename
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return None


def _call_claude(system: str, user: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_CONTENT_MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def _parse_json_response(raw: str) -> Dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        if match:
            return json.loads(match.group(1))
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > 0:
            return json.loads(raw[start:end])
        raise ValueError("Could not extract JSON from Claude response")


def _get_mock_content(topic: Dict) -> Dict:
    title = topic.get("title", "Sample Post")
    pillar = topic.get("pillar", "general")
    logger.info(f"[DRY RUN] Mock content for: {title}")
    return {
        "tldr": f"{title} — this is mock content in dry-run mode.",
        "content": f"<h2>About {title}</h2><p>Dry-run mode. No API key configured.</p>",
        "faq": "<div class='faq-item'><h3>What is this?</h3><p>Dry-run mock content.</p></div>",
        "meta_description": f"Learn about {title.lower()}. Comprehensive guide.",
        "focus_keyword": topic.get("target_keywords", [""])[0] if topic.get("target_keywords") else title.lower(),
        "seo_title": f"{title} | Complete Guide",
        "schema_type": "Article",
    }


def generate_post_content(topic: Dict, site: Dict, plan_context: Dict) -> Dict:
    """
    Generate full blog post content using Claude.

    Returns dict with keys:
        tldr, content, faq, meta_description, focus_keyword, seo_title, schema_type
    """
    if DRY_RUN:
        return _get_mock_content(topic)

    title = topic.get("title", "Untitled")
    pillar = topic.get("pillar", "general")
    site_name = site.get("name", "")
    site_url = site.get("wp_url", "")
    cta_url = site.get("cta_url", site_url)

    template = load_template(pillar)
    if template:
        logger.info(f"Loaded template '{pillar}' for: {title}")
    else:
        template = "Write a structured SEO article with H2 sections and FAQ."
        logger.warning(f"No template for pillar '{pillar}', using generic")

    pillar_hints = (
        plan_context.get("default_pillar_template_hints", {}).get(pillar, "")
        or "Follow the template structure above."
    )

    user_prompt = f"""Create a blog post for {site_name} ({site_url}).

Title: {title}
Content Pillar: {pillar}
Intent: {topic.get("intent", "informational")}
Target Keywords: {", ".join(topic.get("target_keywords", []))}
Special Instructions: {topic.get("special_instructions") or "None"}
CTA URL: {cta_url}

=== BLOG TEMPLATE (follow this structure exactly) ===
{template}

=== PILLAR GUIDELINES ===
{pillar_hints}

=== OUTPUT FORMAT ===
Return a single JSON object with these exact keys:
- "tldr": 2–3 direct, confident sentences that answer the main question. First sentence states the answer outright. AI systems lift this as the snippet.
- "content": full HTML body following the template. Use <h2>, <h3>, <p>, <ul>, <li>, <table>, <strong>. Comparison tables must have <thead> and <tbody>.
- "faq": HTML for 5–8 FAQ items. Use <div class="faq-item"><h3>Question?</h3><p>Answer.</p></div>. Questions must be natural-language queries (how people ask AI assistants).
- "meta_description": compelling meta description, max 155 characters, includes primary keyword.
- "focus_keyword": the single primary keyword phrase to target (for Yoast).
- "seo_title": Yoast SEO title, max 60 characters, includes primary keyword. Format: "[Topic] | [Brand]" or "[Year] [Topic] Guide".
- "schema_type": one of Article, HowTo, FAQPage, TechArticle — choose the best fit for this pillar.

Do not invent product features. Use specific facts. No marketing fluff."""

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Generating content (attempt {attempt + 1}/{MAX_RETRIES}): {title}")
            raw = _call_claude(CONTENT_SYSTEM_PROMPT, user_prompt)
            result = _parse_json_response(raw)

            required = ["tldr", "content", "faq", "meta_description", "focus_keyword", "seo_title", "schema_type"]
            for key in required:
                if key not in result:
                    raise ValueError(f"Missing key in Claude response: {key}")

            logger.info(f"Content generated: {title}")
            return result

        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)

    logger.error(f"Content generation failed after {MAX_RETRIES} attempts: {last_error}")
    raise last_error
