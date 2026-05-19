import html
from logger import logger


def _get_site_cta(site: dict) -> tuple:
    """
    Resolve CTA link and text for a site.
    Tries the site intake YAML first, falls back to site URL.
    """
    site_id = site.get("id")
    if site_id:
        try:
            import yaml
            from config import SITES_DIR
            for f in SITES_DIR.glob("*.yaml"):
                data = yaml.safe_load(f.read_text())
                if data and data.get("site_id") == site_id:
                    cta_url = data.get("main_cta", site.get("wp_url", "/"))
                    return cta_url, "Get Started"
        except Exception:
            pass
    return site.get("wp_url", "/"), "Learn More"


def assemble_final_html(
    site: dict,
    title: str,
    tldr: str,
    content: str,
    faq: str,
    meta_description: str,
    cta_link: str = "",
    cta_text: str = "",
) -> str:
    """
    Insert generated content into the site's blog template.

    Falls back to a minimal default if the site has no template.
    CTA resolves from: explicit args → site intake YAML → site URL.
    """
    template = site.get("blog_template", "")

    if not template:
        logger.warning("Site has no blog template — using minimal default")
        template = """<article>
<h1>{{title}}</h1>
<p><strong>TL;DR:</strong> {{tldr}}</p>
<div class="post-content">{{content}}</div>
<div class="faq"><h2>Frequently Asked Questions</h2>{{faq}}</div>
<div class="cta"><p><a href="{{cta_link}}">{{cta_text}}</a></p></div>
</article>"""

    # Resolve CTA
    if not cta_link:
        cta_link, default_text = _get_site_cta(site)
        if not cta_text:
            cta_text = default_text
    if not cta_text:
        cta_text = "Get Started"

    safe_title = html.escape(title)
    safe_meta = html.escape(meta_description) if meta_description else ""

    replacements = {
        "{{title}}": safe_title,
        "{{tldr}}": tldr or "",
        "{{content}}": content or "",
        "{{faq}}": faq or "",
        "{{meta_description}}": safe_meta,
        "{{cta_link}}": cta_link,
        "{{cta_text}}": cta_text,
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    remaining = result.count("{{")
    if remaining > 0:
        logger.warning(f"Template has {remaining} unreplaced placeholder(s)")

    logger.info(f"Assembled HTML ({len(result)} chars)")
    return result
