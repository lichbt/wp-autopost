import json
from datetime import date, timedelta
from typing import Dict, List
from openai import OpenAI
from config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL, DRY_RUN
from logger import logger


# System prompt for plan parsing
PARSE_SYSTEM_PROMPT = """You are a content automation parser. You convert a content strategy document into a machine-readable action plan. 
Extract all blog topics and global settings. Always output valid JSON only, no additional commentary."""

PARSE_USER_PROMPT_TEMPLATE = """Here is the content strategy document:

{raw_markdown}

Extract:
- A list of "topics": each with title, pillar, priority (high/medium/low), intent (commercial/informational/navigational), target_keywords (array), internal_links (array of URLs from the strategy's linking suggestions), special_instructions (string or null), scheduled_date (YYYY-MM-DD or null, inferred from phase timelines if mentioned).
- "global": {{ default_pillar_template_hints (object mapping pillar to content structure requirements), posts_per_month (number), overall_strategy_goal (short sentence) }}

If a topic belongs to a phase, map the phase to dates assuming Phase 1 = month 1-2 from current date, Phase 2 = month 3-4, Phase 3 = month 5-6. For example, if today is {today}, Phase 1 topics can have dates in the first two months.

Return JSON."""


def _get_mock_parsed_plan() -> Dict:
    """Return mock parsed plan for dry-run mode."""
    today = date.today()
    phase1_start = today + timedelta(days=7)
    phase2_start = today + timedelta(days=60)
    
    return {
        "topics": [
            {
                "title": "Best Dating App Alternatives in 2026",
                "pillar": "Comparisons",
                "priority": "high",
                "intent": "commercial",
                "target_keywords": ["dating app alternatives", "best dating apps", "apps like tinder"],
                "internal_links": ["https://moodatingscript.com/features"],
                "special_instructions": "Include a comparison table with 5+ apps, highlight unique features",
                "scheduled_date": phase1_start.isoformat()
            },
            {
                "title": "How to Start a Dating App Business",
                "pillar": "How-To",
                "priority": "high",
                "intent": "informational",
                "target_keywords": ["start dating app", "dating app business", "create dating app"],
                "internal_links": ["https://moodatingscript.com/demo"],
                "special_instructions": "Step-by-step guide with numbered H2s, include cost estimates",
                "scheduled_date": (phase1_start + timedelta(days=3)).isoformat()
            },
            {
                "title": "What is a Dating App Script?",
                "pillar": "Definition",
                "priority": "medium",
                "intent": "informational",
                "target_keywords": ["dating app script", "dating software", "white label dating"],
                "internal_links": ["https://moodatingscript.com/pricing"],
                "special_instructions": None,
                "scheduled_date": (phase1_start + timedelta(days=7)).isoformat()
            },
            {
                "title": "Dating App Development Cost Breakdown",
                "pillar": "Cost & ROI",
                "priority": "medium",
                "intent": "commercial",
                "target_keywords": ["dating app cost", "development cost", "app pricing"],
                "internal_links": ["https://moodatingscript.com/pricing"],
                "special_instructions": "Include cost comparison table: custom vs script, with ROI timeline",
                "scheduled_date": phase2_start.isoformat()
            },
            {
                "title": "Niche Dating Apps: Finding Your Market",
                "pillar": "Niche",
                "priority": "low",
                "intent": "informational",
                "target_keywords": ["niche dating app", "dating app ideas", "target market"],
                "internal_links": ["https://moodatingscript.com/features"],
                "special_instructions": None,
                "scheduled_date": (phase2_start + timedelta(days=14)).isoformat()
            }
        ],
        "global": {
            "default_pillar_template_hints": {
                "Comparisons": "Open with direct answer, use H2s for each comparison point, include a comparison table, FAQ section; CTA to pricing page",
                "How-To": "Numbered steps as H2s, practical examples, screenshots or diagrams description, FAQ; CTA to free trial or demo",
                "Definition": "Clear definition in first paragraph, then expand with examples, use cases, and related concepts; CTA to features",
                "Cost & ROI": "Lead with key cost figures, breakdown table, ROI calculation, comparison with alternatives; CTA to pricing",
                "Niche": "Market opportunity first, then specific niche examples, success stories, implementation tips; CTA to demo"
            },
            "posts_per_month": 8,
            "overall_strategy_goal": "Establish authority in the dating app development space by targeting commercial and informational queries, driving traffic to moodatingscript.com demo and pricing pages"
        }
    }


def extract_plan(raw_markdown: str) -> Dict:
    """
    Parse a content strategy document using LLM.
    
    Args:
        raw_markdown: Raw markdown content of the strategy document
    
    Returns:
        Dict with 'topics' (list) and 'global' (settings) keys
    
    Raises:
        Exception: If LLM parsing fails
    """
    # Dry-run mode: return mock data
    if DRY_RUN:
        logger.info("[DRY RUN] Returning mock parsed plan")
        return _get_mock_parsed_plan()
    
    # Initialize LLM client
    if LLM_BASE_URL:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        logger.info(f"Using LLM at: {LLM_BASE_URL} with model: {LLM_MODEL}")
    else:
        client = OpenAI(api_key=LLM_API_KEY)
        logger.info(f"Using OpenAI with model: {LLM_MODEL}")
    
    today = date.today().isoformat()
    user_prompt = PARSE_USER_PROMPT_TEMPLATE.format(
        raw_markdown=raw_markdown,
        today=today
    )
    
    logger.info("Calling LLM to parse strategy document...")
    
    try:
        # Try with JSON mode first (OpenAI compatible)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=15000
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        try:
            result = json.loads(raw_content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', raw_content)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Try to find JSON object in the response
                start = raw_content.find('{')
                end = raw_content.rfind('}') + 1
                if start != -1 and end != 0:
                    result = json.loads(raw_content[start:end])
                else:
                    raise ValueError("Could not extract JSON from response")
        
        # Validate structure
        if "topics" not in result:
            raise ValueError("LLM response missing 'topics' key")
        if "global" not in result:
            raise ValueError("LLM response missing 'global' key")
        
        logger.info(f"Successfully parsed {len(result['topics'])} topics from plan")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Plan extraction failed: {e}")
        raise


def import_plan(site_id: int, raw_markdown: str) -> int:
    """
    Import a plan: parse it and store topics in database.
    
    Args:
        site_id: Site ID to associate with
        raw_markdown: Raw strategy document
    
    Returns:
        Plan ID
    """
    from database import add_plan, add_topics_bulk
    
    # Parse the plan
    parsed = extract_plan(raw_markdown)
    
    # Store plan
    plan_id = add_plan(
        site_id=site_id,
        raw_markdown=raw_markdown,
        extracted_json=json.dumps(parsed)
    )
    
    # Store topics
    topics = parsed.get("topics", [])
    if topics:
        add_topics_bulk(site_id, plan_id, topics)
        logger.info(f"Imported {len(topics)} topics for site {site_id}")
    
    return plan_id
