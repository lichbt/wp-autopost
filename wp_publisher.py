import json
import re
import time
import requests
from typing import Optional

from config import DRY_RUN, MAX_RETRIES, RETRY_DELAYS
from logger import logger


def generate_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:200].rstrip("-")
    return slug


def _build_json_ld(title: str, schema_type: str, meta_description: str, faq_html: str) -> str:
    """
    Build JSON-LD structured data block for GEO + rich results.

    Supports: Article, TechArticle, HowTo, FAQPage.
    """
    today = __import__("datetime").date.today().isoformat()

    if schema_type in ("FAQPage", "faq"):
        # Parse FAQ items from HTML
        faq_items = re.findall(
            r"<h3>(.*?)</h3>\s*<p>(.*?)</p>",
            faq_html or "",
            re.DOTALL | re.IGNORECASE,
        )
        entities = [
            {
                "@type": "Question",
                "name": q.strip(),
                "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a).strip()},
            }
            for q, a in faq_items
        ]
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": entities,
        }

    elif schema_type == "HowTo":
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": meta_description,
            "datePublished": today,
        }

    else:
        # Article or TechArticle
        article_type = "TechArticle" if schema_type == "TechArticle" else "Article"
        schema = {
            "@context": "https://schema.org",
            "@type": article_type,
            "headline": title,
            "description": meta_description,
            "datePublished": today,
            "dateModified": today,
        }

    return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'


def publish_post(
    site: dict,
    title: str,
    content_html: str,
    status: str = "draft",
    category: int = None,
    slug: str = None,
    meta_description: str = None,
    focus_keyword: str = None,
    seo_title: str = None,
    schema_type: str = "Article",
    faq_html: str = "",
) -> Optional[int]:
    """
    Publish a post to WordPress via REST API with full Yoast SEO + JSON-LD.

    Returns WordPress post ID on success.
    """
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would publish '{title}' to {site.get('wp_url', '?')}")
        return 9999

    if not slug:
        slug = generate_slug(title)
    if category is None:
        category = site.get("default_category", 1)

    wp_url = site.get("wp_url", "").rstrip("/")
    api_endpoint = f"{wp_url}/wp-json/wp/v2/posts"
    auth = (site["wp_username"], site["wp_app_password"])

    # Inject JSON-LD at the top of the content
    json_ld = _build_json_ld(title, schema_type or "Article", meta_description or "", faq_html)
    full_content = json_ld + "\n" + content_html

    # Yoast meta fields
    # These use Yoast's REST API integration (requires Yoast SEO plugin)
    meta = {}
    if meta_description:
        meta["_yoast_wpseo_metadesc"] = meta_description[:155]
    if focus_keyword:
        meta["_yoast_wpseo_focuskw"] = focus_keyword
    if seo_title:
        meta["_yoast_wpseo_title"] = seo_title[:60]
    # Map schema_type to Yoast article type
    schema_map = {
        "Article": "Article",
        "TechArticle": "TechArticle",
        "HowTo": "HowTo",
        "FAQPage": "Article",  # Yoast doesn't have FAQPage article type
    }
    meta["_yoast_wpseo_schema_article_type"] = schema_map.get(schema_type, "Article")

    payload = {
        "title": title,
        "content": full_content,
        "status": status,
        "categories": [category],
        "slug": slug,
        "meta": meta,
    }

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Publishing '{title}' (attempt {attempt + 1}/{MAX_RETRIES})")
            response = requests.post(
                api_endpoint,
                json=payload,
                auth=auth,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            if response.status_code in (200, 201):
                post_id = response.json().get("id")
                logger.info(f"Published '{title}' — WP post ID: {post_id}")
                return post_id

            if response.status_code in (401, 403):
                raise Exception(f"Auth failed (HTTP {response.status_code}). Check WP credentials.")

            if response.status_code == 404:
                raise Exception(
                    f"WP REST API not found at {api_endpoint}. Check URL and ensure REST API is enabled."
                )

            error_msg = f"WP API error (HTTP {response.status_code}): {response.text[:300]}"
            logger.warning(error_msg)
            last_error = Exception(error_msg)

        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Connection error: {e}")
        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"Timeout: {e}")
        except Exception as e:
            if "Auth failed" in str(e) or "REST API not found" in str(e):
                raise
            last_error = e
            logger.warning(f"Publish attempt failed: {e}")

        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.info(f"Retrying in {delay}s...")
            time.sleep(delay)

    logger.error(f"Failed to publish '{title}' after {MAX_RETRIES} attempts: {last_error}")
    raise last_error
