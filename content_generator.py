import json
import re
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from openai import OpenAI
from config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL, DRY_RUN, MAX_RETRIES, RETRY_DELAYS, PROJECT_ROOT
from logger import logger

# Templates directory
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Facts files directory
FACTS_DIR = PROJECT_ROOT / "data"

# Map site domain keywords → facts filename
_SITE_FACTS_MAP = {
    "moodatingscript": "moodatingscript-facts.md",
    "moodating":       "moodatingscript-facts.md",
    "shaunsocial":     "shaunsocial-facts.md",
}


def _load_site_facts(site: Dict) -> str:
    """
    Load the product facts markdown for the given site.
    Returns the facts content as a string, or empty string if not found.
    """
    site_url = site.get("wp_url", "").lower()
    site_name = site.get("name", "").lower()

    facts_file = None
    for keyword, filename in _SITE_FACTS_MAP.items():
        if keyword in site_url or keyword in site_name:
            facts_file = FACTS_DIR / filename
            break

    if facts_file and facts_file.exists():
        content = facts_file.read_text(encoding="utf-8")
        logger.info(f"Loaded site facts: {facts_file.name}")
        return content

    logger.info("No site facts file found — proceeding without facts context")
    return ""


def _fetch_published_posts(site: Dict) -> List[Dict]:
    """
    Fetch published posts from the WordPress site for use as internal link targets.
    Returns a list of {title, url} dicts, capped at 40 most recent.
    Non-blocking: returns [] on any error.
    """
    try:
        wp_url = site.get("wp_url", "").rstrip("/")
        auth = (site["wp_username"], site["wp_app_password"])
        resp = requests.get(
            f"{wp_url}/wp-json/wp/v2/posts",
            params={"status": "publish", "per_page": 40, "orderby": "date", "order": "desc",
                    "_fields": "title,link"},
            auth=auth,
            timeout=10,
        )
        if resp.status_code == 200:
            posts = [
                {"title": p["title"]["rendered"], "url": p["link"]}
                for p in resp.json()
                if p.get("link") and "?" not in p.get("link", "")  # skip draft /?p= URLs
            ]
            return posts
    except Exception as e:
        logger.warning(f"Could not fetch published posts for internal links: {e}")
    return []


def _format_link_context(posts: List[Dict]) -> str:
    """Format the published post list into a prompt-ready string."""
    if not posts:
        return ""
    lines = ["PUBLISHED POSTS AVAILABLE FOR INTERNAL LINKS:"]
    for p in posts:
        lines.append(f'- "{p["title"]}" → {p["url"]}')
    return "\n".join(lines)


def load_template(pillar: str) -> Optional[str]:
    """
    Load a blog template for the given pillar.
    
    Args:
        pillar: Content pillar name (e.g., "How-To", "Comparisons", "Definition")
    
    Returns:
        Template content or None if not found
    """
    # Map pillar names to template files
    pillar_to_file = {
        "how-to": "how_to.md",
        "how to": "how_to.md",
        "comparisons": "comparison.md",
        "comparison": "comparison.md",
        "vs": "comparison.md",
        "definition": "definition.md",
        "definitions": "definition.md",
        "explainer": "definition.md",
        "cost & roi": "cost_roi.md",
        "cost": "cost_roi.md",
        "roi": "cost_roi.md",
        "pricing": "cost_roi.md",
        "niche": "niche.md",
        "market": "niche.md",
    }
    
    # Normalize pillar name
    pillar_lower = pillar.lower().strip()
    
    # Get template filename
    filename = pillar_to_file.get(pillar_lower)
    if not filename:
        # Try partial match
        for key, value in pillar_to_file.items():
            if key in pillar_lower or pillar_lower in key:
                filename = value
                break
    
    if not filename:
        filename = "how_to.md"  # Default template
    
    # Load template
    template_path = TEMPLATES_DIR / filename
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    
    return None


# System prompt for content generation
CONTENT_SYSTEM_PROMPT = """You are an expert SEO/GEO content writer creating blog posts that are highly likely to be cited by AI systems (ChatGPT, Perplexity, Gemini).
Your writing must be factual, structured with clear H2/H3 headings, include tables and lists when helpful, and always start with a direct answer.

PRODUCT FACTS RULES (critical):
- The prompt includes a PRODUCT FACTS section — treat every fact in it as absolute ground truth.
- Never invent, contradict, or deviate from the pricing, features, mobile app type, or open-source status stated in the facts.
- If the facts say the price is $149, always write $149 — never a different number.
- If the facts say the mobile app is a PWA, never call it a native app, and vice versa.

You MUST follow the provided blog template structure exactly. The template defines the required sections, headings, and formatting.

INTERNAL LINKING RULES (mandatory):
- Insert 3–5 contextual internal links within the body text using real <a href="URL">anchor text</a> HTML tags.
- Use the PUBLISHED POSTS list provided in the prompt — only link to URLs from that list.
- Place links naturally inside sentences where the linked topic is genuinely relevant — not in a forced list at the bottom.
- Use descriptive anchor text that matches the target page topic (e.g. "how to monetise a dating app", NOT "click here").
- Never repeat the same URL more than once.
- Do NOT add links inside the tldr, meta_description, or faq fields — only in the "content" field."""


# ── Writing Personas ──────────────────────────────────────────────────────────
# Each persona adds a style addon to CONTENT_SYSTEM_PROMPT. Selection is
# deterministic: topic_id % len(WRITING_PERSONAS) — reproducible and loggable.

WRITING_PERSONAS = [
    {
        "name": "expert_practitioner",
        "system_addon": (
            "WRITING PERSONA — Expert Practitioner:\n"
            "Write from hard-won, hands-on experience. Open with a direct, opinionated statement you'd only "
            "make if you'd actually used these tools. No hedge words ('may', 'might', 'could'). "
            "Sentence length varies — short punchy sentences after long technical ones. "
            "Get to the recommendation fast; justify it after."
        ),
    },
    {
        "name": "journalist",
        "system_addon": (
            "WRITING PERSONA — Journalist:\n"
            "Open with a lede: one punchy sentence that tells the whole story. Use the inverted pyramid — "
            "most important facts first. Headlines are verb-forward and crisp. "
            "Named examples over abstractions. Context and stakes before the deep-dive."
        ),
    },
    {
        "name": "educator",
        "system_addon": (
            "WRITING PERSONA — Educator:\n"
            "Assume the reader is intelligent but new to the topic. Define terms on first use. "
            "Use one concrete analogy per major concept. Build knowledge progressively — "
            "each section assumes the previous was read. Use numbered steps for any process. "
            "Why-before-how structure throughout."
        ),
    },
    {
        "name": "business_strategist",
        "system_addon": (
            "WRITING PERSONA — Business Strategist:\n"
            "Frame everything through business outcomes: cost saved, time reduced, risk managed, revenue gained. "
            "Open with the business case, not the technical problem. "
            "Decision-framing language: 'If X is your priority, choose Y.' "
            "Include at least one cost or ROI data point per H2."
        ),
    },
    {
        "name": "data_analyst",
        "system_addon": (
            "WRITING PERSONA — Data Analyst:\n"
            "Lead with the numbers. Every claim needs a figure, a source, or a stated basis. "
            "Tables preferred over prose for any comparison with 3+ variables. "
            "Precise language: '40% faster' not 'much faster'. "
            "Data summary first, methodology second, interpretation third."
        ),
    },
    {
        "name": "critical_reviewer",
        "system_addon": (
            "WRITING PERSONA — Critical Reviewer:\n"
            "Acknowledge real weaknesses of every tool or approach before recommending it. "
            "Structure: strengths → real limitations → who it's actually right for. "
            "Open with what the tool does NOT do well — earn reader trust before the recommendation. "
            "No overselling. Honest limitations build credibility."
        ),
    },
]


def get_persona_for_topic(topic_id: int) -> dict:
    """Deterministic persona selection: topic_id % number of personas."""
    return WRITING_PERSONAS[topic_id % len(WRITING_PERSONAS)]


def build_system_prompt(persona: dict) -> str:
    """Combine base system prompt with persona-specific writing style addon."""
    return f"{CONTENT_SYSTEM_PROMPT}\n\n{persona['system_addon']}"


CONTENT_USER_PROMPT_TEMPLATE = """Create a blog post for the following topic:

Title: {title}
Content Pillar: {pillar}
Intent: {intent}
Target Keywords: {keywords}
Special Instructions: {special_instructions}

=== PRODUCT FACTS (use these as ground truth — do NOT invent or contradict) ===
{site_facts}
{strategy_section}
=== BLOG TEMPLATE (You MUST follow this structure) ===
{template}

=== ADDITIONAL CONTENT GUIDELINES ===
{pillar_hints}

=== INTERNAL LINK OPPORTUNITIES ===
{link_context}

=== OUTPUT FORMAT ===
Return a JSON object with these keys IN THIS ORDER:
- "tldr": 2-3 direct, confident sentences that answer the main question. This will be the snippet AI lifts.
- "meta_title": SEO-optimized page title under 60 characters. Include target keyword and year.
- "meta_description": compelling meta description under 160 characters. Include primary keyword and call to action.
- "focus_keyword": the single most important target keyword for this post (2-4 words).
- "slug": URL-friendly slug for the post (lowercase, hyphens, max 60 chars).
- "faq": HTML for an FAQ section with 5-8 questions. Each question uses <h3> tag, answer in <p> tag, wrapped in <div class="faq-item">. Use natural language questions.
- "content": full HTML body following the template structure above. Use proper H2/H3 headings as defined in the template. Use <table> where the template calls for tables, numbered H2 steps for how-to guides. Insert 3–5 internal links from the list above using <a href="URL">anchor text</a> tags placed naturally within sentences.

Important:
- Follow the BLOG TEMPLATE structure exactly for the content organization
- Do not invent product features. Only mention product names when appropriate
- Use HTML tags for formatting (<h2>, <h3>, <p>, <ul>, <li>, <table>, <strong>, <em>)
- Include the target keywords naturally throughout the content
- Internal links MUST use real URLs from the INTERNAL LINK OPPORTUNITIES list above"""


def _get_mock_content(topic: Dict) -> Dict:
    """Return mock generated content for dry-run mode."""
    title = topic.get("title", "Sample Blog Post")
    pillar = topic.get("pillar", "General")
    
    logger.info(f"[DRY RUN] Generating mock content for: {title}")
    
    # Generate pillar-appropriate mock content
    if pillar == "Comparisons":
        tldr = f"When comparing dating app solutions, {title.lower().replace('best ', '').replace(' in 2026', '')}, Moo Dating Script stands out for its white-label flexibility, built-in monetization features, and rapid deployment timeline. Most alternatives require 6-12 months of development, while Moo Dating Script can launch in under 2 weeks."
        
        content = """<h2>Quick Comparison: Top Dating App Solutions</h2>
<p>Choosing the right dating app solution depends on your budget, timeline, and feature requirements. Here's how the top options compare:</p>

<table>
<thead>
<tr><th>Solution</th><th>Time to Market</th><th>Starting Cost</th><th>Customization</th><th>Best For</th></tr>
</thead>
<tbody>
<tr><td>Moo Dating Script</td><td>1-2 weeks</td><td>$999</td><td>High</td><td>Entrepreneurs wanting quick launch</td></tr>
<tr><td>Custom Development</td><td>6-12 months</td><td>$50,000+</td><td>Full</td><td>Enterprise with unique requirements</td></tr>
<tr><td>White Label Apps</td><td>2-4 weeks</td><td>$2,000-5,000</td><td>Medium</td><td>Agencies managing multiple brands</td></tr>
<tr><td>Open Source Scripts</td><td>1-3 months</td><td>Free + Dev Time</td><td>High</td><td>Technical founders on budget</td></tr>
</tbody>
</table>

<h2>Key Features to Compare</h2>
<h3>Matching Algorithm</h3>
<p>Modern dating apps need sophisticated matching. Moo Dating Script includes location-based matching, preference filtering, and AI-powered suggestions out of the box.</p>

<h3>Monetization Options</h3>
<p>Revenue features should include subscriptions, in-app purchases, and premium features. Most turnkey solutions include basic monetization, but advanced options vary significantly.</p>

<h3>Security and Moderation</h3>
<p>Content moderation, user verification, and reporting systems are essential. Enterprise-grade solutions typically offer better moderation tools.</p>

<h2>Which Solution Is Right for You?</h2>
<p>For most entrepreneurs looking to enter the dating app market, a turnkey solution like Moo Dating Script offers the best balance of cost, speed, and customization. If you have unique requirements or a $100K+ budget, custom development might be worth considering.</p>"""
        
        faq = """<div class="faq-item">
<h3>What is the cheapest way to start a dating app?</h3>
<p>The most affordable approach is using a white-label dating script like Moo Dating Script, which starts at $999 and includes all core features. Custom development typically costs $50,000 or more.</p>
</div>
<div class="faq-item">
<h3>How long does it take to launch a dating app?</h3>
<p>With a turnkey solution, you can launch in 1-2 weeks. Custom development takes 6-12 months depending on complexity and team size.</p>
</div>
<div class="faq-item">
<h3>Can I customize a white-label dating app?</h3>
<p>Yes, most white-label solutions offer customization options for branding, features, and user experience. Moo Dating Script provides full source code access for unlimited customization.</p>
</div>
<div class="faq-item">
<h3>What features should a dating app have?</h3>
<p>Essential features include user profiles, matching algorithm, messaging, push notifications, location services, and payment processing for premium features.</p>
</div>
<div class="faq-item">
<h3>Is it profitable to start a dating app business?</h3>
<p>Yes, the dating app market continues to grow. With proper monetization and marketing, dating apps can achieve 40-60% profit margins through subscriptions and premium features.</p>
</div>"""
        
        meta_description = "Compare top dating app solutions for 2026. See costs, features, and time-to-market for turnkey scripts vs custom development."
        
    elif pillar == "How-To":
        tldr = f"Starting a dating app business requires market research, choosing the right technology stack, and implementing effective monetization. With solutions like Moo Dating Script, you can launch a fully-featured dating app in under 2 weeks for under $1,000."
        
        content = """<h2>Step 1: Research Your Target Market</h2>
<p>Before building anything, identify your niche. Successful dating apps often target specific demographics, interests, or relationship goals. Research competitors and identify gaps in the market.</p>

<h2>Step 2: Choose Your Technology Approach</h2>
<p>You have three main options:</p>
<ul>
<li><strong>Custom Development:</strong> $50,000-150,000, 6-12 months</li>
<li><strong>White-Label Solution:</strong> $1,000-10,000, 1-4 weeks</li>
<li><strong>Open Source:</strong> Free + development time</li>
</ul>

<h2>Step 3: Select Core Features</h2>
<p>Essential dating app features include:</p>
<ul>
<li>User registration and profiles</li>
<li>Matching algorithm</li>
<li>Messaging system</li>
<li>Push notifications</li>
<li>Location-based search</li>
<li>Payment processing</li>
</ul>

<h2>Step 4: Design Your Monetization Strategy</h2>
<p>Common revenue models include freemium subscriptions, premium features, in-app purchases, and advertising. Most successful apps combine multiple revenue streams.</p>

<h2>Step 5: Launch and Market Your App</h2>
<p>Start with a soft launch in a specific geographic area. Use social media marketing, influencer partnerships, and content marketing to build your user base.</p>"""
        
        faq = """<div class="faq-item">
<h3>How much money do I need to start a dating app?</h3>
<p>You can start with as little as $999 using a turnkey solution like Moo Dating Script. Budget an additional $500-2,000 for marketing and initial operations.</p>
</div>
<div class="faq-item">
<h3>Do I need coding skills to start a dating app?</h3>
<p>No, white-label solutions like Moo Dating Script don't require coding skills. However, basic technical knowledge helps with customization and troubleshooting.</p>
</div>
<div class="faq-item">
<h3>How do dating apps make money?</h3>
<p>Dating apps generate revenue through subscriptions, premium features, in-app purchases, and advertising. The most successful apps use a freemium model with paid upgrades.</p>
</div>
<div class="faq-item">
<h3>How long until a dating app becomes profitable?</h3>
<p>With proper marketing and monetization, dating apps can become profitable within 6-12 months. Key factors include user acquisition cost, retention rates, and average revenue per user.</p>
</div>"""
        
        meta_description = "Learn how to start a dating app business in 5 simple steps. Covers technology options, costs, features, and marketing strategies."
    
    else:
        # Generic mock content for other pillars
        tldr = f"{title} is an important consideration for anyone in the dating app market. This guide covers everything you need to know, from basic concepts to advanced implementation strategies."
        
        content = f"""<h2>Understanding {title}</h2>
<p>The dating app industry continues to evolve rapidly. Whether you're a first-time entrepreneur or an established business, understanding these fundamentals is crucial for success.</p>

<h2>Key Considerations</h2>
<h3>Market Analysis</h3>
<p>The global dating app market is projected to reach $10.5 billion by 2026. Understanding market trends and user preferences is essential for positioning your app effectively.</p>

<h3>Technology Stack</h3>
<p>Modern dating apps require robust technology infrastructure including real-time messaging, location services, and secure data storage. Choosing the right technology partner can significantly impact your time-to-market and operational costs.</p>

<h3>User Experience</h3>
<p>User experience design plays a critical role in dating app success. Intuitive interfaces, smooth onboarding, and engaging features drive user retention and satisfaction.</p>

<h2>Best Practices</h2>
<ul>
<li>Focus on a specific niche before expanding</li>
<li>Implement robust security and verification</li>
<li>Design for mobile-first experiences</li>
<li>Plan monetization from the start</li>
<li>Build community features to increase engagement</li>
</ul>

<h2>Getting Started</h2>
<p>The fastest way to enter the market is with a proven solution like Moo Dating Script, which provides all essential features with full customization options.</p>"""
        
        faq = f"""<div class="faq-item">
<h3>What is {title.lower()}?</h3>
<p>It refers to the strategies and considerations involved in building and growing a successful dating application in today's competitive market.</p>
</div>
<div class="faq-item">
<h3>Why is this important for dating app businesses?</h3>
<p>Understanding these concepts helps you make informed decisions about technology, marketing, and business strategy, ultimately leading to better outcomes.</p>
</div>
<div class="faq-item">
<h3>How can I learn more?</h3>
<p>Explore our other resources on dating app development, or contact our team for personalized guidance on your specific situation.</p>
</div>"""
        
        meta_description = f"Learn about {title.lower()} and how it impacts dating app success. Expert insights and practical guidance."
    
    # Derive SEO fields so dry-run output matches the real LLM contract
    keywords = topic.get("target_keywords") or []
    focus_keyword = keywords[0] if keywords else title.lower()
    meta_title = (title[:57] + "...") if len(title) > 60 else title
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    return {
        "tldr": tldr,
        "content": content,
        "faq": faq,
        "meta_description": meta_description,
        "meta_title": meta_title,
        "focus_keyword": focus_keyword,
        "slug": slug,
        "writing_persona": get_persona_for_topic(topic.get("id", 0))["name"],
    }


def generate_post_content(topic: Dict, site: Dict, plan_context: Dict) -> Dict:
    """
    Generate blog post content for a topic using LLM.
    
    Args:
        topic: Topic dict from database (with title, pillar, keywords, etc.)
        site: Site settings dict
        plan_context: Global plan settings (pillar_template_hints, etc.)
    
    Returns:
        Dict with keys: tldr, content, faq, meta_description
    
    Raises:
        Exception: If generation fails after retries
    """
    title = topic.get("title", "Untitled")
    pillar = topic.get("pillar", "General")

    # Dry-run mode: return mock content
    if DRY_RUN:
        return _get_mock_content(topic)

    # ── Writing persona (performance-weighted, with rotation fallback) ─────────
    topic_id = topic.get("id", 0)
    site_id = topic.get("site_id") or (site or {}).get("id")
    try:
        from content_strategist import select_persona
        persona = select_persona(site_id, topic_id) if site_id else get_persona_for_topic(topic_id)
    except Exception as exc:
        logger.warning(f"Persona selection fell back to rotation: {exc}")
        persona = get_persona_for_topic(topic_id)
    system_prompt = build_system_prompt(persona)
    logger.info(f"Writing persona: '{persona['name']}' (topic {topic_id})")

    # ── Strategy context from GSC/GA4 data (Feature 2) ───────────────────────
    try:
        from content_strategist import get_strategy_context
        strategy_context = get_strategy_context(site.get("id", 0))
    except Exception:
        strategy_context = ""
    strategy_section = f"\n{strategy_context}\n" if strategy_context else ""

    # Load template for this pillar
    template = load_template(pillar)
    if template:
        logger.info(f"Loaded template for pillar: {pillar}")
    else:
        logger.warning(f"No template found for pillar: {pillar}, using default guidelines")
        template = "Standard SEO-optimized article with introduction, H2 sections, and FAQ"

    # Get pillar hints from plan context (additional to template)
    pillar_hints = plan_context.get("default_pillar_template_hints", {}).get(
        pillar,
        "Follow the template structure above"
    )

    # Load site facts (product pricing, features, correct names)
    site_facts = _load_site_facts(site)

    # Fetch published posts for internal link context
    published_posts = _fetch_published_posts(site)
    link_context = _format_link_context(published_posts)
    if published_posts:
        logger.info(f"Loaded {len(published_posts)} published posts as internal link candidates")
    else:
        logger.info("No published posts available for internal links (site may be new)")

    # Build user prompt
    user_prompt = CONTENT_USER_PROMPT_TEMPLATE.format(
        title=title,
        pillar=pillar,
        intent=topic.get("intent", "informational"),
        keywords=", ".join(topic.get("target_keywords", [])),
        special_instructions=topic.get("special_instructions") or "None",
        site_facts=site_facts or "No product facts file found — use general knowledge.",
        strategy_section=strategy_section,
        template=template,
        pillar_hints=pillar_hints,
        link_context=link_context or "No existing posts yet — skip internal links for now.",
    )
    
    # Initialize LLM client
    if LLM_BASE_URL:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        logger.info(f"Using LLM at: {LLM_BASE_URL} with model: {LLM_MODEL}")
    else:
        client = OpenAI(api_key=LLM_API_KEY)
        logger.info(f"Using OpenAI with model: {LLM_MODEL}")
    
    # Retry logic
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Generating content for: {title} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            # Try with JSON mode first (some local LLMs may not support it)
            try:
                response = client.chat.completions.create(
                    model=LLM_MODEL,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=16000
                )
                raw_content = response.choices[0].message.content.strip()
            except Exception:
                # Fallback to regular completion if JSON mode not supported
                response = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=16000
                )
                raw_content = response.choices[0].message.content.strip()
            
            # Try to parse JSON from response
            try:
                result = json.loads(raw_content)
            except json.JSONDecodeError:
                import re
                from json_repair import repair_json
                # Try markdown code block first
                json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', raw_content)
                candidate = json_match.group(1) if json_match else raw_content
                # Find outermost JSON object
                start = candidate.find('{')
                if start == -1:
                    raise ValueError("Could not extract JSON from LLM response")
                end = candidate.rfind('}') + 1
                # If closing brace not found, JSON was truncated — try repair anyway
                candidate = candidate[start:end] if end > 0 else candidate[start:]
                # Repair and parse
                repaired = repair_json(candidate)
                result = json.loads(repaired)
            
            # Validate required keys — tldr is optional, fallback to meta_description
            if "tldr" not in result:
                result["tldr"] = result.get("meta_description", "")
            required_keys = ["meta_title", "meta_description", "content", "faq"]
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"LLM response missing required key: {key}")

            # Tag with persona so scheduler can persist it
            result["writing_persona"] = persona["name"]

            logger.info(f"Successfully generated content for: {title}")
            return result
            
        except Exception as e:
            last_error = e
            logger.warning(f"Content generation attempt {attempt + 1} failed: {e}")
            
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    # All retries failed
    logger.error(f"Content generation failed after {MAX_RETRIES} attempts: {last_error}")
    raise last_error
