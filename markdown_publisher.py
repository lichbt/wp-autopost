"""
markdown_publisher.py — Output adapter for non-WordPress (markdown_export) sites.

Instead of publishing to WordPress, this writes the generated article as a
content-only Markdown file (YAML frontmatter + Markdown body + FAQ) into the
site's `content_repo_path`. Deployment (git commit / Cloudflare Pages build) is
the user's responsibility — this only produces the file.
"""
import os
import re
from datetime import date
from typing import Dict, Optional

from markdownify import markdownify as _md
from logger import logger


def _to_md(html: str) -> str:
    """Convert generated HTML to clean Markdown (ATX headings, no stray blanks)."""
    if not html:
        return ""
    md = _md(html, heading_style="ATX", bullets="-")
    # collapse 3+ blank lines to a single blank line
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md


def _frontmatter(title: str, description: str, slug: str) -> str:
    def esc(s: str) -> str:
        return (s or "").replace('"', '\\"').strip()
    return (
        "---\n"
        f'title: "{esc(title)}"\n'
        f'description: "{esc(description)}"\n'
        f'slug: "{esc(slug)}"\n'
        f"date: {date.today().isoformat()}\n"
        "---\n"
    )


def export_markdown(
    site: Dict,
    *,
    slug: str,
    content_html: str,
    faq_html: str = "",
    title: str = "",
    meta_description: str = "",
    meta_title: Optional[str] = None,
) -> Optional[Dict]:
    """
    Write the article as a content-only Markdown file.

    Returns {"kind": "md", "path": <abs path>, "url": <public url>} on success,
    or None on failure (non-blocking, mirrors wp_publisher's tolerant style).
    """
    out_dir = site.get("content_repo_path")
    if not out_dir:
        logger.error("[md_export] site has no content_repo_path — cannot write file")
        return None
    if not slug:
        logger.error("[md_export] missing slug — cannot name file")
        return None

    body = _to_md(content_html)
    faq_md = _to_md(faq_html)
    parts = [_frontmatter(title or meta_title or slug, meta_description, slug), "", body]
    if faq_md:
        parts += ["", "## Frequently Asked Questions", "", faq_md]
    document = "\n".join(parts).rstrip() + "\n"

    try:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{slug}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(document)
    except Exception as exc:
        logger.error(f"[md_export] failed to write {slug}.md: {exc}")
        return None

    base = (site.get("wp_url") or "").rstrip("/")
    url = f"{base}/{slug}" if base else f"/{slug}"
    logger.info(f"[md_export] wrote {path} ({len(document)} chars)")
    return {"kind": "md", "path": path, "url": url}
