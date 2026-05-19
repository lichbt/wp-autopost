"""
image_handler.py — Fetch a relevant image from Pixabay and upload it to
the WordPress media library as the post's featured image.

Returns the WP media ID (int) on success, or None on failure.
Non-blocking: callers should treat None as "no image, continue anyway".
"""
import io
import re
import requests
from typing import Optional

from config import PIXABAY_API_KEY
from logger import logger

# Pillar-based fallback queries when focus keyword is brand-specific or too short
PILLAR_FALLBACK = {
    "vs_comparison":     "software comparison technology",
    "best_of":           "top rated software apps",
    "buyer_guide":       "business decision checklist",
    "setup_tutorial":    "laptop computer setup tutorial",
    "feature_explainer": "mobile app features interface",
    "use_case":          "people using smartphone app",
    "how_to":            "step by step guide tutorial",
    "how-to":            "step by step guide tutorial",
    "cost_roi":          "business investment money",
    "cost":              "business investment money",
    "definition":        "concept explanation whiteboard",
    "definitions":       "concept explanation whiteboard",
}

# Brand/product names to strip from search queries
_BRAND_PATTERN = re.compile(
    r'\b(20\d{2}|moodatescript|moodating|skadate|wpdating|chameleon|'
    r'dating pro|shaunsocial|shaun social|wpcode|yoast)\b',
    re.IGNORECASE,
)


def _build_query(topic: dict) -> str:
    """
    Derive a clean Pixabay search query from the topic.
    Priority: generated_focus_keyword > target_keywords[0] > title
    """
    raw = (
        topic.get("generated_focus_keyword")
        or (topic.get("target_keywords") or [""])[0]
        or topic.get("title", "")
    )
    # Strip year numbers and known brand names
    query = _BRAND_PATTERN.sub("", raw)
    query = re.sub(r"\s+", " ", query).strip()

    # If too short after stripping, use pillar fallback
    if len(query) < 5:
        pillar = topic.get("pillar", "")
        query = PILLAR_FALLBACK.get(pillar, "dating website app")

    return query[:100]


def _search_pixabay(query: str) -> Optional[dict]:
    """
    Search Pixabay for a horizontal photo matching the query.
    Returns the first hit dict or None.
    """
    if not PIXABAY_API_KEY:
        logger.warning("PIXABAY_API_KEY not configured — skipping image fetch")
        return None

    try:
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "min_width": 1200,
                "safesearch": "true",
                "per_page": 5,
                "order": "popular",
            },
            timeout=15,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if hits:
            logger.info(f"Pixabay: found {len(hits)} results for '{query}'")
            return hits[0]
        logger.warning(f"Pixabay: no results for '{query}'")
        return None
    except Exception as e:
        logger.warning(f"Pixabay search error: {e}")
        return None


def _download_image(url: str) -> Optional[bytes]:
    """Download image bytes from a URL."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning(f"Image download failed ({url}): {e}")
        return None


def _upload_to_wp(
    site: dict,
    image_bytes: bytes,
    filename: str,
    alt_text: str,
) -> Optional[int]:
    """
    Upload image bytes to WordPress media library via REST API.
    Returns the WP media ID or None on failure.
    """
    wp_url = site.get("wp_url", "").rstrip("/")
    auth = (site["wp_username"], site["wp_app_password"])

    try:
        resp = requests.post(
            f"{wp_url}/wp-json/wp/v2/media",
            files={"file": (filename, io.BytesIO(image_bytes), "image/jpeg")},
            data={"alt_text": alt_text[:125], "caption": ""},
            auth=auth,
            timeout=60,
        )
        if resp.status_code in (200, 201):
            media_id = resp.json().get("id")
            media_url = resp.json().get("source_url", "")
            logger.info(f"Uploaded image → WP media #{media_id} ({media_url})")
            return media_id
        logger.warning(
            f"WP media upload failed: HTTP {resp.status_code} — {resp.text[:300]}"
        )
    except Exception as e:
        logger.warning(f"WP media upload error: {e}")

    return None


def fetch_and_upload_image(topic: dict, site: dict) -> Optional[int]:
    """
    Main entry point: search Pixabay, download the image, upload to WordPress.

    Returns the WP media ID to set as `featured_media`, or None if any step
    fails. Callers must treat None gracefully (post without featured image).

    Args:
        topic: topic dict — should include generated_focus_keyword, pillar,
               target_keywords, title, and slug.
        site:  site dict with wp_url, wp_username, wp_app_password.
    """
    query = _build_query(topic)
    logger.info(f"Image search query: '{query}'")

    hit = _search_pixabay(query)
    if not hit:
        # Try broader pillar fallback if specific query returned nothing
        pillar = topic.get("pillar", "")
        fallback_query = PILLAR_FALLBACK.get(pillar, "dating website app")
        if fallback_query != query:
            logger.info(f"Retrying with pillar fallback: '{fallback_query}'")
            hit = _search_pixabay(fallback_query)
    if not hit:
        return None

    image_url = hit.get("largeImageURL") or hit.get("webformatURL")
    image_bytes = _download_image(image_url)
    if not image_bytes:
        return None

    # Build a clean filename from the post slug
    slug = topic.get("slug") or re.sub(
        r"[^a-z0-9]+", "-", topic.get("title", "image").lower()
    ).strip("-")[:60]
    filename = f"{slug}.jpg"

    alt_text = (
        topic.get("generated_focus_keyword")
        or topic.get("title", "")
    )

    return _upload_to_wp(site, image_bytes, filename, alt_text)
