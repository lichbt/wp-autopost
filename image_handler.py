"""
image_handler.py — Generate a relevant featured image and upload it to the
WordPress media library.

Primary:  Pollinations.AI  — free AI image generation, no API key needed.
          Generates an image from a prompt tailored to the article topic.
Fallback: Pixabay          — stock photo search if Pollinations fails.

Returns the WP media ID (int) on success, or None on failure.
Non-blocking: callers should treat None as "no image, continue anyway".
"""
import io
import re
import time
import requests
from typing import Optional
from urllib.parse import quote

from config import PIXABAY_API_KEY, CLAUDE_ANALYSIS_MODEL, CLAUDE_CLI_AVAILABLE
from claude_cli import claude_complete
from logger import logger

# ── Niche-aware prompt templates for Pollinations ────────────────────────────
# Used when the LLM prompt builder is unavailable or returns something empty.
# These are AI image prompts, not Pixabay search terms.
_NICHE_PILLAR_PROMPT = {
    ("dating", "vs_comparison"):     "two smartphones side by side showing dating apps, clean comparison, professional product photography, soft studio lighting",
    ("dating", "best_of"):           "attractive couple smiling while using a dating app on a smartphone, warm natural lighting, lifestyle photography",
    ("dating", "buyer_guide"):       "person thoughtfully browsing a dating website on a laptop at a bright modern desk, soft focus background",
    ("dating", "setup_tutorial"):    "developer setting up a dating website on a laptop, clean workspace, coffee cup, code on screen",
    ("dating", "feature_explainer"): "close-up of a modern dating app UI on a smartphone screen, heart icons, profile cards, vibrant design",
    ("dating", "use_case"):          "diverse couple happily meeting for the first time at a cafe, warm sunlight, candid lifestyle photo",
    ("dating", "how_to"):            "person creating a dating profile on a smartphone, smiling, cozy home environment",
    ("dating", "how-to"):            "person creating a dating profile on a smartphone, smiling, cozy home environment",
    ("dating", "cost_roi"):          "entrepreneur reviewing a business plan on a laptop, charts showing growth, modern office setting",
    ("dating", "cost"):              "entrepreneur reviewing a business plan on a laptop, charts showing growth, modern office setting",
    ("dating", "definition"):        "conceptual image of digital hearts and connections on a glowing smartphone screen, abstract technology",
    ("dating", "definitions"):       "conceptual image of digital hearts and connections on a glowing smartphone screen, abstract technology",
    ("social", "vs_comparison"):     "two phones side by side showing different social media feeds, minimalist flat lay",
    ("social", "best_of"):           "group of young people smiling and using social media on their smartphones, vibrant lifestyle photo",
    ("social", "buyer_guide"):       "person researching social media tools on a laptop, sticky notes, bright modern workspace",
    ("social", "setup_tutorial"):    "person setting up a social media profile on a laptop, clean desk, natural light",
    ("social", "feature_explainer"): "smartphone showing a social media feed with likes and notifications, close-up product shot",
    ("social", "use_case"):          "friends laughing and sharing content on social media at a cafe, candid photo",
    ("social", "how_to"):            "person learning social media marketing, laptop open, taking notes, home office",
    ("social", "how-to"):            "person learning social media marketing, laptop open, taking notes, home office",
    ("social", "cost_roi"):          "marketing professional reviewing social media analytics on a screen, data charts, office setting",
    ("social", "cost"):              "marketing professional reviewing social media analytics on a screen, data charts",
    ("social", "definition"):        "abstract network of people connected digitally, glowing nodes, blue tones, technology concept",
    ("social", "definitions"):       "abstract network of people connected digitally, glowing nodes, blue tones, technology concept",
}

_GENERIC_PILLAR_PROMPT = {
    "vs_comparison":     "two products being compared side by side, clean product photography, studio lighting",
    "best_of":           "award-winning products arranged on a clean surface, top choices, modern flat lay",
    "buyer_guide":       "person thoughtfully researching on a laptop, bright modern workspace, decision making",
    "setup_tutorial":    "hands setting up software on a laptop, clean desk, modern workspace",
    "feature_explainer": "modern app interface on a smartphone, clean UI, feature highlights",
    "use_case":          "people using a mobile app in everyday life, candid lifestyle photo",
    "how_to":            "person following a step-by-step guide on a laptop or phone, home office",
    "how-to":            "person following a step-by-step guide on a laptop or phone, home office",
    "cost_roi":          "business professional reviewing financials and growth charts on a laptop",
    "cost":              "business professional reviewing budget on a laptop, modern office",
    "definition":        "clean conceptual illustration of a digital concept, glowing screen, abstract",
    "definitions":       "clean conceptual illustration of a digital concept, glowing screen, abstract",
}

# Suffix appended to every Pollinations prompt for consistent quality
_QUALITY_SUFFIX = (
    ", ultra-realistic, 4K, professional editorial photography, "
    "natural lighting, shallow depth of field, no text, no watermark"
)


def _niche_key(site: dict) -> str:
    """Derive a short niche key from the site dict."""
    niche = (site.get("niche") or site.get("name") or "").lower()
    if "dating" in niche:
        return "dating"
    if "social" in niche:
        return "social"
    return "generic"


def _fallback_prompt(pillar: str, site: dict) -> str:
    """Return a Pollinations image prompt for this pillar + site niche."""
    niche = _niche_key(site)
    key = (niche, pillar)
    base = _NICHE_PILLAR_PROMPT.get(key) or _GENERIC_PILLAR_PROMPT.get(pillar, "professional business technology photo, modern office")
    return base + _QUALITY_SUFFIX


def _build_image_prompt(topic: dict, site: dict) -> str:
    """
    Use the LLM to generate a descriptive AI image prompt tailored to the
    article title and niche. Falls back to a pillar-based template if the
    LLM call fails.
    """
    title = topic.get("title", "")
    niche = site.get("niche") or site.get("name") or "technology"
    pillar = topic.get("pillar", "")

    if not CLAUDE_CLI_AVAILABLE:
        logger.info("claude CLI unavailable — using pillar prompt template")
        return _fallback_prompt(pillar, site)

    system = (
        "You are an AI image prompt writer. Given an article title and niche, "
        "write a single concise image prompt (max 25 words) suitable for AI image generation. "
        "Focus on a realistic photographic scene that visually represents the article topic. "
        "No text in image, no logos. Return only the prompt, nothing else."
    )
    user = f'Article title: "{title}"\nNiche: {niche}\n\nWrite an image prompt:'

    try:
        prompt = claude_complete(user, system=system, model=CLAUDE_ANALYSIS_MODEL, timeout=60).strip().strip('"')
        if len(prompt) > 10:
            full_prompt = prompt + _QUALITY_SUFFIX
            logger.info(f"LLM image prompt: '{prompt}'")
            return full_prompt
    except Exception as e:
        logger.warning(f"LLM prompt generation failed: {e}")

    logger.info("Falling back to pillar prompt template")
    return _fallback_prompt(pillar, site)


def _generate_with_pollinations(prompt: str, width: int = 1200, height: int = 675) -> Optional[bytes]:
    """
    Call Pollinations.AI to generate an image from a text prompt.
    Returns image bytes or None on failure.

    Endpoint: https://image.pollinations.ai/prompt/{encoded_prompt}
    Free, no API key, no rate limit (soft).
    """
    encoded = quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&model=flux&nologo=true&enhance=true"
    )
    logger.info(f"Generating image via Pollinations.AI...")
    try:
        # Pollinations can take 10-30s to generate
        resp = requests.get(url, timeout=90)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            logger.info(f"Pollinations generated image ({len(resp.content) // 1024}KB)")
            return resp.content
        logger.warning(f"Pollinations returned HTTP {resp.status_code}")
    except requests.exceptions.Timeout:
        logger.warning("Pollinations timed out after 90s")
    except Exception as e:
        logger.warning(f"Pollinations error: {e}")
    return None


def _search_pixabay(query: str) -> Optional[dict]:
    """Search Pixabay for a photo. Returns the first hit dict or None."""
    if not PIXABAY_API_KEY:
        logger.warning("PIXABAY_API_KEY not configured — skipping Pixabay fallback")
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
            logger.info(f"Pixabay fallback: found {len(hits)} results for '{query}'")
            return hits[0]
        logger.warning(f"Pixabay: no results for '{query}'")
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


def _upload_to_wp(site: dict, image_bytes: bytes, filename: str, alt_text: str) -> Optional[int]:
    """Upload image bytes to WordPress media library. Returns media ID or None."""
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
        logger.warning(f"WP media upload failed: HTTP {resp.status_code} — {resp.text[:300]}")
    except Exception as e:
        logger.warning(f"WP media upload error: {e}")
    return None


def fetch_and_upload_image(topic: dict, site: dict) -> Optional[int]:
    """
    Main entry point: generate an AI image and upload to WordPress.

    Flow:
    1. Build an image prompt (LLM-generated or pillar template)
    2. Generate image via Pollinations.AI (free, no key)
    3. If Pollinations fails → fall back to Pixabay stock photo
    4. Upload to WordPress media library
    5. Return WP media ID, or None if everything fails

    Args:
        topic: topic dict with title, pillar, slug, generated_focus_keyword, etc.
        site:  site dict with wp_url, wp_username, wp_app_password, niche.
    """
    slug = topic.get("slug") or re.sub(
        r"[^a-z0-9]+", "-", topic.get("title", "image").lower()
    ).strip("-")[:60]
    filename = f"{slug}.jpg"
    alt_text = topic.get("generated_focus_keyword") or topic.get("title", "")

    # ── Primary: Pollinations AI generation ──────────────────────────────────
    prompt = _build_image_prompt(topic, site)
    image_bytes = _generate_with_pollinations(prompt)

    # ── Fallback: Pixabay stock photo ─────────────────────────────────────────
    if not image_bytes:
        logger.info("Pollinations failed — trying Pixabay fallback")
        pillar = topic.get("pillar", "")
        niche = _niche_key(site)
        fallback_key = (niche, pillar)
        # Build a simple search query from the fallback prompt (first ~5 words)
        fallback_base = (
            _NICHE_PILLAR_PROMPT.get(fallback_key)
            or _GENERIC_PILLAR_PROMPT.get(pillar, "business technology people")
        )
        fallback_query = " ".join(fallback_base.split(",")[0].split()[:6])
        hit = _search_pixabay(fallback_query)
        if hit:
            image_url = hit.get("largeImageURL") or hit.get("webformatURL")
            image_bytes = _download_image(image_url)

    if not image_bytes:
        logger.warning("All image sources failed — post will have no featured image")
        return None

    return _upload_to_wp(site, image_bytes, filename, alt_text)
