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


def _strip_html_entities(text: str) -> str:
    """Decode HTML entities so JSON-LD values are plain text, not HTML-encoded."""
    import html
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _parse_faq_items(faq_html: str) -> list:
    """Extract FAQ question/answer pairs from HTML as schema.org Question entities."""
    faq_items = re.findall(
        r"<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>",
        faq_html or "",
        re.DOTALL | re.IGNORECASE,
    )
    return [
        {
            "@type": "Question",
            "name": _strip_html_entities(q),
            "acceptedAnswer": {
                "@type": "Answer",
                "text": _strip_html_entities(a),
            },
        }
        for q, a in faq_items
        if q.strip() and a.strip()  # skip empty items
    ]


def _build_json_ld(title: str, schema_type: str, meta_description: str, faq_html: str) -> str:
    """
    Build JSON-LD structured data block for GEO + rich results.

    Wrapped in Gutenberg <!-- wp:html --> block so WordPress does NOT apply
    wptexturize / wpautop filters that would mangle the JSON (converting " to
    curly quotes or wrapping in <p> tags, both of which break JSON parsing).

    Emits ONE schema block only (Article, TechArticle, or HowTo).
    FAQPage schema is handled exclusively by template_assembler.py via the
    {{faq_schema}} placeholder — do NOT emit it here to avoid duplicates.
    """
    today = __import__("datetime").date.today().isoformat()
    clean_title = _strip_html_entities(title)
    clean_desc = _strip_html_entities(meta_description)

    blocks = []

    if schema_type == "HowTo":
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": clean_title,
            "description": clean_desc,
            "step": [],
        }
        blocks.append(schema)

    else:
        # Article or TechArticle — the primary schema
        # FAQPage is emitted separately by template_assembler; skip it here.
        article_type = "TechArticle" if schema_type == "TechArticle" else "Article"
        schema = {
            "@context": "https://schema.org",
            "@type": article_type,
            "headline": clean_title[:110],  # Google enforces ≤110 chars
            "description": clean_desc,
            "datePublished": today,
            "dateModified": today,
        }
        blocks.append(schema)

    def _wrap(schema: dict) -> str:
        json_str = json.dumps(schema, indent=2, ensure_ascii=False)
        script_tag = f'<script type="application/ld+json">\n{json_str}\n</script>'
        # Gutenberg raw HTML block prevents WordPress from running wptexturize /
        # wpautop filters on the script content (which would corrupt the JSON).
        return f'<!-- wp:html -->\n{script_tag}\n<!-- /wp:html -->'

    return "\n".join(_wrap(b) for b in blocks)


def _xmlrpc_set_yoast_meta(
    wp_url: str,
    username: str,
    app_password: str,
    post_id: int,
    fields: dict,
) -> bool:
    """
    Set Yoast SEO meta fields via XML-RPC.

    Fetches existing custom field IDs first so updates overwrite in-place
    rather than creating duplicate meta rows (which Yoast ignores).
    """
    import xmlrpc.client

    xmlrpc_url = f"{wp_url.rstrip('/')}/xmlrpc.php"
    pwd = app_password  # WP accepts app passwords with or without spaces

    try:
        client = xmlrpc.client.ServerProxy(xmlrpc_url)

        # Fetch existing custom fields to get their IDs
        post = client.wp.getPost(1, username, pwd, post_id, ["custom_fields"])
        existing = post.get("custom_fields", [])

        # Build key -> [list of field IDs] map to handle any pre-existing duplicates
        key_ids: dict = {}
        for cf in existing:
            k = cf.get("key", "")
            if k in fields:
                key_ids.setdefault(k, []).append(cf["id"])

        custom_fields = []
        for key, value in fields.items():
            ids = key_ids.get(key, [])
            if ids:
                # Update the first occurrence; blank out any extras (duplicates)
                custom_fields.append({"id": ids[0], "key": key, "value": str(value)})
                for dup_id in ids[1:]:
                    custom_fields.append({"id": dup_id, "key": key, "value": ""})
            else:
                # No existing field — let WP create it
                custom_fields.append({"key": key, "value": str(value)})

        result = client.wp.editPost(1, username, pwd, post_id, {"custom_fields": custom_fields})
        if not result:
            logger.warning(f"XML-RPC Yoast meta update returned false for post {post_id}")
        return bool(result)

    except Exception as e:
        logger.warning(f"XML-RPC Yoast meta update error: {e}")
        return False


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
    featured_media_id: int = None,
) -> Optional[int]:
    """
    Publish a post to WordPress via REST API with full Yoast SEO + JSON-LD.

    Yoast meta (title, description, focus keyword) are written via XML-RPC
    after the REST publish, because Yoast does not register _yoast_wpseo_metadesc
    / _yoast_wpseo_focuskw for the WP REST API meta endpoint.

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

    payload = {
        "title": title,
        "content": full_content,
        "status": status,
        "categories": [category],
        "slug": slug,
    }
    if featured_media_id:
        payload["featured_media"] = featured_media_id

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

                # ── Set Yoast SEO meta via XML-RPC ────────────────────────────
                # REST API silently ignores _yoast_wpseo_metadesc and focuskw;
                # XML-RPC writes them correctly via custom_fields.
                schema_map = {
                    "Article": "Article",
                    "TechArticle": "TechArticle",
                    "HowTo": "HowTo",
                    "FAQPage": "Article",
                }
                yoast_fields = {
                    "_yoast_wpseo_schema_article_type": schema_map.get(schema_type, "Article"),
                }
                if meta_description:
                    yoast_fields["_yoast_wpseo_metadesc"] = meta_description[:155]
                if focus_keyword:
                    yoast_fields["_yoast_wpseo_focuskw"] = focus_keyword
                if seo_title:
                    # Append Yoast separator + site name template
                    yoast_fields["_yoast_wpseo_title"] = seo_title[:60] + " %%sep%% %%sitename%%"

                if yoast_fields:
                    ok = _xmlrpc_set_yoast_meta(
                        wp_url,
                        site["wp_username"],
                        site["wp_app_password"],
                        post_id,
                        yoast_fields,
                    )
                    if ok:
                        logger.info(f"Yoast meta set for post {post_id}")
                    else:
                        logger.warning(f"Yoast meta partially failed for post {post_id} — continuing")

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
