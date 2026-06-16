"""
publisher.py — Platform dispatch for publishing/outputting a generated article.

Single seam that routes by `site['platform']`:
  - 'wordpress' (default) → wp_publisher.publish_post (live WP REST + Yoast)
  - 'markdown_export'     → markdown_publisher.export_markdown (content-only .md file)

Callers (scheduler.py, _write_one.py) use publish_for_site() and store the
returned identifier appropriately (WP post id vs. file url).
"""
from typing import Dict, Optional


def is_wordpress(site: Dict) -> bool:
    """True for legacy/default WordPress sites; False for markdown_export etc."""
    return (site.get("platform") or "wordpress") == "wordpress"


def publish_for_site(
    site: Dict,
    *,
    title: str,
    content_html: str,
    slug: str = None,
    status: str = "draft",
    category: int = None,
    meta_description: str = None,
    focus_keyword: str = None,
    seo_title: str = None,
    schema_type: str = "Article",
    faq_html: str = "",
    featured_media_id: int = None,
    update_post_id: int = None,
) -> Optional[Dict]:
    """
    Route an article to the right output target.

    Returns:
      WordPress      → {"kind": "wp", "id": <int post id>, "url": None}
      markdown_export→ {"kind": "md", "path": <file>, "url": <public url>}
      None on failure.
    """
    if is_wordpress(site):
        from wp_publisher import publish_post
        post_id = publish_post(
            site=site, title=title, content_html=content_html, status=status,
            category=category, slug=slug, meta_description=meta_description,
            focus_keyword=focus_keyword, seo_title=seo_title, schema_type=schema_type,
            faq_html=faq_html, featured_media_id=featured_media_id,
            update_post_id=update_post_id,
        )
        return {"kind": "wp", "id": post_id, "url": None} if post_id else None

    if (site.get("platform") or "") == "markdown_export":
        from markdown_publisher import export_markdown
        return export_markdown(
            site, slug=slug, content_html=content_html, faq_html=faq_html,
            title=title, meta_description=meta_description, meta_title=seo_title,
        )

    raise ValueError(f"Unknown site platform: {site.get('platform')!r}")
