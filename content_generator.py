import json
import time
from pathlib import Path
from typing import Dict, Optional
from openai import OpenAI
from config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL, DRY_RUN, MAX_RETRIES, RETRY_DELAYS, PROJECT_ROOT
from logger import logger

# Templates directory
TEMPLATES_DIR = PROJECT_ROOT / "templates"


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

You MUST follow the provided blog template structure exactly. The template defines the required sections, headings, and formatting."""

CONTENT_USER_PROMPT_TEMPLATE = """Create a blog post for the following topic:

Title: {title}
Content Pillar: {pillar}
Intent: {intent}
Target Keywords: {keywords}
Special Instructions: {special_instructions}

=== BLOG TEMPLATE (You MUST follow this structure) ===
{template}

=== ADDITIONAL CONTENT GUIDELINES ===
{pillar_hints}

=== OUTPUT FORMAT ===
Return a JSON object with:
- "tldr": 2-3 direct, confident sentences that answer the main question. This will be the snippet AI lifts.
- "content": full HTML body following the template structure above. Use proper H2/H3 headings as defined in the template. Use <table> where the template calls for tables, numbered H2 steps for how-to guides.
- "faq": HTML for an FAQ section with 5-8 questions using natural language queries as defined in the template.
- "meta_description": compelling meta description under 160 characters as defined in the template.

Important: 
- Follow the BLOG TEMPLATE structure exactly for the content organization
- Do not invent product features. Only mention product names when appropriate, linking to moodatingscript.com naturally
- Use HTML tags for formatting (<h2>, <h3>, <p>, <ul>, <li>, <table>, <strong>, <em>)
- Include the target keywords naturally throughout the content"""


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
    
    return {
        "tldr": tldr,
        "content": content,
        "faq": faq,
        "meta_description": meta_description
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
    
    # Build user prompt
    user_prompt = CONTENT_USER_PROMPT_TEMPLATE.format(
        title=title,
        pillar=pillar,
        intent=topic.get("intent", "informational"),
        keywords=", ".join(topic.get("target_keywords", [])),
        special_instructions=topic.get("special_instructions") or "None",
        template=template,
        pillar_hints=pillar_hints
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
                        {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000
                )
                raw_content = response.choices[0].message.content.strip()
            except Exception:
                # Fallback to regular completion if JSON mode not supported
                response = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": CONTENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000
                )
                raw_content = response.choices[0].message.content.strip()
            
            # Try to parse JSON from response
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
                        raise ValueError("Could not extract JSON from LLM response")
            
            # Validate required keys
            required_keys = ["tldr", "content", "faq", "meta_description"]
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"LLM response missing required key: {key}")
            
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
