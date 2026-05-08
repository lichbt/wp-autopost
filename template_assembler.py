import html
from typing import Optional
from logger import logger


def assemble_final_html(
    site: dict,
    title: str,
    tldr: str,
    content: str,
    faq: str,
    meta_description: str,
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
        cta_link: Call-to-action URL (default: /demo)
        cta_text: Call-to-action text (default: "Try Demo")
    
    Returns:
        Final assembled HTML string
    """
    template = site.get("blog_template", "")
    
    if not template:
        logger.warning("Site has no blog template, using minimal default")
        template = """<article>
<h1>{{title}}</h1>
<p><strong>TL;DR:</strong> {{tldr}}</p>
<div class="post-content">{{content}}</div>
<div class="faq">{{faq}}</div>
</article>"""
    
    # HTML escape values for safety (except content which is already HTML)
    safe_title = html.escape(title)
    safe_meta = html.escape(meta_description) if meta_description else ""
    
    # Replace placeholders
    replacements = {
        "{{title}}": safe_title,
        "{{tldr}}": tldr or "",
        "{{content}}": content or "",
        "{{faq}}": faq or "",
        "{{meta_description}}": safe_meta,
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
