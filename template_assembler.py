import html
from typing import Optional
from logger import logger


import html
import json
import re
from typing import Optional
from logger import logger


def _extract_faq_items(faq_html: str) -> list:
    """Extract Q&A pairs from FAQ HTML to build JSON-LD schema."""
    items = []
    
    question_pattern = re.compile(r'<h3[^>]*>(.*?)</h3>', re.IGNORECASE | re.DOTALL)
    answer_pattern = re.compile(r'<p[^>]*>(.*?)</p>', re.IGNORECASE | re.DOTALL)
    
    questions = question_pattern.findall(faq_html)
    answers = answer_pattern.findall(faq_html)
    
    for i, q in enumerate(questions):
        a = answers[i] if i < len(answers) else ""
        items.append({
            "@type": "Question",
            "name": html.unescape(re.sub(r'<[^>]+>', '', q)).strip(),
            "acceptedAnswer": {
                "@type": "Answer",
                "text": html.unescape(re.sub(r'<[^>]+>', '', a)).strip()
            }
        })
    
    return items


def _build_faq_schema(faq_html: str) -> str:
    """Build FAQPage JSON-LD schema from FAQ HTML."""
    items = _extract_faq_items(faq_html)
    if not items:
        return ""
    
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": items
    }
    
    return f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'


def assemble_final_html(
    site: dict,
    title: str,
    tldr: str,
    content: str,
    faq: str,
    meta_description: str,
    meta_title: str = None,
    cta_link: str = "/demo",
    cta_text: str = "Try Demo"
) -> str:
    """
    Insert generated content into the site's blog template.
    
    Args:
        site: Site settings dict (must have 'blog_template')
        title: Post title
        tldr: TL;DR section HTML
        content: Main body HTML
        faq: FAQ section HTML
        meta_description: Meta description text
        meta_title: SEO meta title (falls back to title)
        cta_link: Call-to-action URL (default: /demo)
        cta_text: Call-to-action text (default: "Try Demo")
    
    Returns:
        Final assembled HTML string
    """
    template = site.get("blog_template", "")
    
    if not template:
        logger.warning("Site has no blog template, using minimal default")
        template = """<!DOCTYPE html>
<html>
<head>
<meta name="description" content="{{meta_description}}">
<meta name="title" content="{{meta_title}}">
<title>{{meta_title}}</title>
</head>
<body>
<article>
<h1>{{title}}</h1>
<p><strong>TL;DR:</strong> {{tldr}}</p>
<div class="post-content">{{content}}</div>
<div class="faq">{{faq}}</div>
{{faq_schema}}
</article>
</body>
</html>"""
    
    # HTML escape values for safety (except content which is already HTML)
    safe_title = html.escape(title)
    safe_meta_desc = html.escape(meta_description) if meta_description else ""
    safe_meta_title = html.escape(meta_title or title)
    
    # Build FAQ schema
    faq_schema = _build_faq_schema(faq or "")
    
    # Replace placeholders
    replacements = {
        "{{title}}": safe_title,
        "{{meta_title}}": safe_meta_title,
        "{{tldr}}": tldr or "",
        "{{content}}": content or "",
        "{{faq}}": faq or "",
        "{{meta_description}}": safe_meta_desc,
        "{{faq_schema}}": faq_schema,
        "{{cta_link}}": cta_link or "/demo",
        "{{cta_text}}": cta_text or "Try Demo"
    }
    
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    # Check for any remaining unreplaced placeholders
    remaining = result.count("{{")
    if remaining > 0:
        logger.warning(f"Template has {remaining} unreplaced placeholders")
    
    logger.info(f"Assembled final HTML ({len(result)} chars)")
    return result
