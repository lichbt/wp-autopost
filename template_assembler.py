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

    result = _add_code_styles(result)

    logger.info(f"Assembled final HTML ({len(result)} chars)")
    return result


def _add_code_styles(html_content: str) -> str:
    """Add inline CSS to <code> and <pre> elements so they stand out from body text."""
    PRE_STYLE = (
        'style="display:block;background:#f6f8fa;color:#24292f;'
        'font-family:\'Consolas\',\'Courier New\',monospace;font-size:13px;'
        'line-height:1.7;padding:16px 20px;margin:20px 0;border-radius:8px;'
        'overflow-x:auto;border:1px solid #d0d7de;border-left:4px solid #6c63ff;'
        'white-space:pre-wrap;word-break:break-word;"'
    )
    INLINE_CODE_STYLE = (
        'style="background:#f0f0f5;color:#7c3aed;'
        'font-family:\'Consolas\',\'Courier New\',monospace;font-size:0.88em;'
        'padding:2px 6px;border-radius:4px;border:1px solid #e0d9f5;"'
    )
    # Style <pre> blocks
    result = re.sub(r'<pre(\s[^>]*)?>', f'<pre {PRE_STYLE}>', html_content)
    # Style inline <code> only outside <pre> blocks
    # Split on <pre>...</pre>, apply inline style only to code outside those segments
    parts = re.split(r'(<pre[\s\S]*?</pre>)', result)
    styled_parts = []
    for part in parts:
        if part.startswith('<pre'):
            styled_parts.append(part)  # inside pre — leave <code> unstyled
        else:
            styled_parts.append(re.sub(r'<code(\s[^>]*)?>', f'<code {INLINE_CODE_STYLE}>', part))
    return ''.join(styled_parts)
