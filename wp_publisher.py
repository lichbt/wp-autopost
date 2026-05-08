import re
import json
import time
import requests
from typing import Optional
from config import DRY_RUN, MAX_RETRIES, RETRY_DELAYS, DEFAULT_WP_STATUS
from logger import logger


def generate_slug(title: str) -> str:
    """
    Generate a URL-friendly slug from a title.
    
    Args:
        title: Post title
    
    Returns:
        Slug string (lowercase, hyphens, max 200 chars)
    """
    # Convert to lowercase
    slug = title.lower()
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Limit length
    slug = slug[:200]
    # Remove trailing hyphen after truncation
    slug = slug.rstrip('-')
    
    return slug


def publish_post(
    site: dict,
    title: str,
    content_html: str,
    status: str = "draft",
    category: int = None,
    slug: str = None,
    meta_description: str = None
) -> Optional[int]:
    """
    Publish a post to WordPress via REST API.
    
    Args:
        site: Site settings dict with wp_url, wp_username, wp_app_password
        title: Post title
        content_html: Full HTML content
        status: 'draft' or 'publish'
        category: Category ID (uses site default if None)
        slug: URL slug (auto-generated if None)
        meta_description: SEO meta description
    
    Returns:
        WordPress post ID on success, None on failure
    
    Raises:
        Exception: If publishing fails after retries
    """
    # Dry-run mode
    if DRY_RUN:
        mock_id = 9999
        logger.info(f"[DRY RUN] Would publish '{title}' to {site.get('wp_url', 'unknown')}")
        logger.info(f"[DRY RUN] Returning mock post ID: {mock_id}")
        return mock_id
    
    # Prepare slug
    if not slug:
        slug = generate_slug(title)
    
    # Prepare category
    if category is None:
        category = site.get("default_category", 1)
    
    # Build API endpoint
    wp_url = site.get("wp_url", "").rstrip("/")
    api_endpoint = f"{wp_url}/wp-json/wp/v2/posts"
    
    # Build auth tuple
    auth = (site["wp_username"], site["wp_app_password"])
    
    # Build payload
    payload = {
        "title": title,
        "content": content_html,
        "status": status,
        "categories": [category],
        "slug": slug
    }
    
    # Add meta description if Yoast or similar plugin is present
    if meta_description:
        payload["meta"] = {
            "_yoast_wpseo_metadesc": meta_description
        }
    
    # Retry logic
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Publishing '{title}' to {wp_url} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = requests.post(
                api_endpoint,
                json=payload,
                auth=auth,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            # Check for success
            if response.status_code in (200, 201):
                result = response.json()
                post_id = result.get("id")
                logger.info(f"Successfully published '{title}' - WP Post ID: {post_id}")
                return post_id
            
            # Handle specific error codes
            if response.status_code in (401, 403):
                error_msg = f"Authentication failed (HTTP {response.status_code}). Check credentials."
                logger.error(error_msg)
                raise Exception(error_msg)
            
            if response.status_code == 404:
                error_msg = f"WordPress REST API not found at {api_endpoint}. Check WP URL and ensure REST API is enabled."
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Other errors - may be retryable
            error_msg = f"WordPress API error (HTTP {response.status_code}): {response.text[:500]}"
            logger.warning(error_msg)
            last_error = Exception(error_msg)
            
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Connection error: {e}")
            
        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"Request timeout: {e}")
            
        except Exception as e:
            if "Authentication failed" in str(e) or "REST API not found" in str(e):
                raise  # Don't retry auth errors
            last_error = e
            logger.warning(f"Publish attempt failed: {e}")
        
        # Wait before retry
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    # All retries failed
    logger.error(f"Failed to publish '{title}' after {MAX_RETRIES} attempts: {last_error}")
    raise last_error
