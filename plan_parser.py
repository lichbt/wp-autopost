import json
import re
from datetime import date, timedelta
from typing import Dict, List

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_ANALYSIS_MODEL, DRY_RUN
from logger import logger

PARSE_SYSTEM_PROMPT = """You are a content strategy parser. Convert strategy documents into machine-readable JSON action plans.
Output ONLY valid JSON — no commentary, no markdown fences."""


def _call_claude(system: str, user: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_ANALYSIS_MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def _parse_json(raw: str) -> Dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        if match:
            return json.loads(match.group(1))
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > 0:
            return json.loads(raw[start:end])
        raise ValueError("Could not extract JSON from response")


def _get_mock_parsed_plan() -> Dict:
    today = date.today()
    p1 = today + timedelta(days=7)
    p2 = today + timedelta(days=60)
    return {
        "topics": [
            {
                "title": "Best Dating App Scripts in 2026: Complete Comparison",
                "pillar": "best_of",
                "priority": "high",
                "intent": "commercial",
                "target_keywords": ["best dating script", "dating app software", "dating script comparison"],
                "internal_links": [],
                "special_instructions": "Ranked list with comparison table. Include price, features, time-to-launch.",
                "scheduled_date": p1.isoformat(),
                "geo_rationale": "LLMs frequently cite 'best X' ranked lists for software recommendations.",
            },
            {
                "title": "MooDateScript vs SkaDate: Which Is Better in 2026?",
                "pillar": "vs_comparison",
                "priority": "high",
                "intent": "commercial",
                "target_keywords": ["moodatescript vs skadate", "skadate alternative", "best dating script"],
                "internal_links": [],
                "special_instructions": "Head-to-head table: pricing, features, support, customization.",
                "scheduled_date": (p1 + timedelta(days=1)).isoformat(),
                "geo_rationale": "Head-to-head comparisons are top LLM citation targets for product decisions.",
            },
        ],
        "global": {
            "default_pillar_template_hints": {
                "vs_comparison": "Open with a direct verdict. Use H2s per comparison dimension. Include a feature table.",
                "best_of": "Ranked list with H2 per option. Overall winner upfront. Comparison table required.",
                "buyer_guide": "Decision framework first. Address each buyer type separately. FAQ at end.",
                "setup_tutorial": "Numbered H2 steps. Include prerequisites. Screenshot placeholders where helpful.",
                "feature_explainer": "Define the feature in sentence 1. Explain why it matters, then how to use it.",
                "use_case": "Lead with the specific scenario. Explain how the product solves it. ROI/outcome at end.",
            },
            "posts_per_month": 60,
            "overall_strategy_goal": "Dominate comparison and 'best of' queries in the dating script niche to drive commercial traffic to pricing and demo pages.",
        },
    }


def extract_plan(raw_markdown: str) -> Dict:
    """
    Parse a content strategy document using Claude.

    Returns dict with 'topics' list and 'global' settings.
    """
    if DRY_RUN:
        logger.info("[DRY RUN] Returning mock parsed plan")
        return _get_mock_parsed_plan()

    today = date.today().isoformat()
    user_prompt = f"""Parse this content strategy document into a JSON action plan.

Today's date: {today}

Strategy document:
{raw_markdown}

Extract a list of "topics", each with:
  - title (exact post title, SEO-optimized)
  - pillar (one of: vs_comparison, best_of, buyer_guide, setup_tutorial, feature_explainer, use_case, how_to, definition, cost_roi, niche)
  - priority (high / medium / low)
  - intent (commercial / informational / navigational)
  - target_keywords (array of 3–5 strings)
  - internal_links (array of URLs from the strategy's linking suggestions, or [])
  - special_instructions (string or null)
  - scheduled_date (YYYY-MM-DD or null; if phases mentioned, Phase 1 = months 1–2, Phase 2 = months 3–4, Phase 3 = months 5–6)
  - geo_rationale (one sentence: why this topic will be cited by AI systems)

Also extract a "global" object with:
  - default_pillar_template_hints (object mapping each pillar to writing guidance)
  - posts_per_month (number)
  - overall_strategy_goal (one sentence)

Return valid JSON only."""

    try:
        raw = _call_claude(PARSE_SYSTEM_PROMPT, user_prompt)
        result = _parse_json(raw)

        if "topics" not in result:
            raise ValueError("Response missing 'topics' key")
        if "global" not in result:
            raise ValueError("Response missing 'global' key")

        logger.info(f"Parsed {len(result['topics'])} topics from plan")
        return result

    except Exception as e:
        logger.error(f"Plan parsing failed: {e}")
        raise


def import_plan(site_id: int, raw_markdown: str) -> int:
    """Parse a strategy doc and import topics into the database. Returns plan ID."""
    from database import add_plan, add_topics_bulk

    parsed = extract_plan(raw_markdown)
    plan_id = add_plan(
        site_id=site_id,
        raw_markdown=raw_markdown,
        extracted_json=json.dumps(parsed),
    )
    topics = parsed.get("topics", [])
    if topics:
        add_topics_bulk(site_id, plan_id, topics)
        logger.info(f"Imported {len(topics)} topics for site {site_id} (plan {plan_id})")
    return plan_id
