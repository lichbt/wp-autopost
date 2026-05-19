import json
import os
import tempfile
from datetime import date
from typing import Optional

from database import (
    get_site, get_pending_topics, get_stale_topics_for_refresh,
    update_topic_status, count_published_today, log_action, get_plan,
    add_plan, add_topics_bulk,
)
from content_generator import generate_post_content
from template_assembler import assemble_final_html
from wp_publisher import publish_post
from image_handler import fetch_and_upload_image
from logger import logger


def _queue_refresh_topics(site_id: int) -> int:
    """
    Find stale published/draft posts with poor GSC position and re-queue them
    as new 'pending' refresh topics in the same plan.
    Returns number of topics queued.
    """
    stale = get_stale_topics_for_refresh(site_id)
    if not stale:
        return 0

    # Use or create a refresh plan for this site
    from database import get_plan_by_site
    existing_plan = get_plan_by_site(site_id)
    plan_id = existing_plan["id"] if existing_plan else None

    if not plan_id:
        plan_id = add_plan(
            site_id=site_id,
            raw_markdown="Auto-generated refresh plan",
            extracted_json=json.dumps({"topics": [], "global": {}}),
        )

    refresh_topics = []
    for t in stale:
        refresh_topics.append({
            "title": t["title"],
            "pillar": t.get("pillar", "how_to"),
            "priority": "medium",
            "intent": "refresh",
            "target_keywords": t.get("target_keywords", []),
            "internal_links": t.get("internal_links", []),
            "special_instructions": (
                "CONTENT REFRESH: Update all statistics, dates, and examples. "
                "Improve structure for GEO (answer-first, add comparison table if missing). "
                "Keep existing H2 topics but deepen each section."
            ),
            "scheduled_date": None,  # process ASAP
        })

    add_topics_bulk(site_id, plan_id, refresh_topics)
    logger.info(f"Queued {len(refresh_topics)} stale topics for refresh on site {site_id}")
    return len(refresh_topics)


def run_automation_cycle(site_id: int, check_refresh: bool = True) -> int:
    """
    Run one automation cycle: generate and publish due topics.

    Args:
        site_id: Site ID to process
        check_refresh: If True, also check for stale content to refresh

    Returns:
        Number of topics processed
    """
    # Per-site lock file — prevents two concurrent runs from duplicating posts
    lock_path = os.path.join(tempfile.gettempdir(), f"content_automation_site{site_id}.lock")
    if os.path.exists(lock_path):
        pid = open(lock_path).read().strip()
        try:
            os.kill(int(pid), 0)  # check if PID still alive
            logger.warning(f"Site {site_id} already running (PID {pid}) — skipping")
            return 0
        except (ProcessLookupError, ValueError):
            pass  # stale lock, proceed
    open(lock_path, "w").write(str(os.getpid()))
    try:
        return _run_automation_cycle_locked(site_id, check_refresh)
    finally:
        os.unlink(lock_path)


def _run_automation_cycle_locked(site_id: int, check_refresh: bool = True) -> int:
    site = get_site(site_id)
    if not site:
        logger.error(f"Site {site_id} not found")
        return 0

    posts_per_day = site.get("posts_per_day", 2)

    # Check daily limit
    published_today = count_published_today(site_id)
    remaining_slots = posts_per_day - published_today

    if remaining_slots <= 0:
        logger.info(f"Daily limit reached for site {site_id} ({published_today}/{posts_per_day})")
        return 0

    logger.info(f"Site {site_id}: {remaining_slots} slot(s) remaining today")

    # Queue stale content refreshes (runs once per cycle, doesn't consume slots)
    if check_refresh:
        refreshed = _queue_refresh_topics(site_id)
        if refreshed:
            logger.info(f"Queued {refreshed} refresh topic(s)")

    # Get pending topics (ordered by GEO pillar priority then DB priority)
    topics = get_pending_topics(site_id, limit=remaining_slots)
    if not topics:
        logger.info(f"No pending topics due for site {site_id}")
        return 0

    logger.info(f"Processing {len(topics)} topic(s)")

    processed = 0
    for topic in topics:
        topic_id = topic["id"]
        title = topic["title"]

        try:
            logger.info(f"Processing topic {topic_id}: {title}")
            log_action(topic_id, "started", f"Beginning pipeline for: {title}")

            # Resolve plan context
            plan_context = topic.get("plan_context", {})
            if not plan_context:
                plan = get_plan(topic.get("plan_id"))
                if plan and plan.get("extracted_json"):
                    parsed = json.loads(plan["extracted_json"])
                    plan_context = parsed.get("global", {})

            # Increment attempts
            attempts = topic.get("attempts", 0) + 1
            update_topic_status(topic_id, "pending", attempts=attempts)

            # Generate content
            logger.info(f"Generating content: {title}")
            content = generate_post_content(topic, site, plan_context)

            update_topic_status(
                topic_id,
                "content_generated",
                generated_tldr=content.get("tldr", ""),
                generated_body=content.get("content", ""),
                generated_faq=content.get("faq", ""),
                generated_meta_description=content.get("meta_description", ""),
                generated_focus_keyword=content.get("focus_keyword", ""),
                generated_seo_title=content.get("seo_title", ""),
                generated_schema_type=content.get("schema_type", "Article"),
            )
            log_action(topic_id, "content_generated", "Content generated")

            # Fetch & upload featured image (non-blocking)
            logger.info(f"Fetching featured image: {title}")
            topic_with_keywords = {**topic, "generated_focus_keyword": content.get("focus_keyword", "")}
            featured_image_id = fetch_and_upload_image(topic_with_keywords, site)
            if featured_image_id:
                logger.info(f"Featured image ready: WP media #{featured_image_id}")
            else:
                logger.info(f"No featured image — post will publish without one")

            # Assemble HTML
            logger.info(f"Assembling HTML: {title}")
            final_html = assemble_final_html(
                site=site,
                title=title,
                tldr=content.get("tldr", ""),
                content=content.get("content", ""),
                faq=content.get("faq", ""),
                meta_description=content.get("meta_description", ""),
            )
            update_topic_status(topic_id, "content_generated", final_html=final_html)

            # Publish to WordPress
            logger.info(f"Publishing: {title}")
            wp_post_id = publish_post(
                site=site,
                title=title,
                content_html=final_html,
                status="draft",
                category=site.get("default_category"),
                slug=topic.get("slug"),
                meta_description=content.get("meta_description"),
                focus_keyword=content.get("focus_keyword"),
                seo_title=content.get("seo_title"),
                schema_type=content.get("schema_type", "Article"),
                faq_html=content.get("faq", ""),
                featured_media_id=featured_image_id,
            )

            update_topic_status(topic_id, "draft", wp_post_id=wp_post_id)
            log_action(topic_id, "published", f"Draft created — WP post ID: {wp_post_id}")

            processed += 1
            logger.info(f"✓ Done: {title}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Topic {topic_id} failed: {error_msg}")

            attempts = topic.get("attempts", 0) + 1
            new_status = "failed" if attempts >= 3 else "pending"
            update_topic_status(topic_id, new_status, last_error=error_msg, attempts=attempts)
            log_action(topic_id, "error", f"Attempt {attempts}: {error_msg}")

            if new_status == "failed":
                logger.error(f"Topic {topic_id} marked failed after {attempts} attempts")

    logger.info(f"Cycle complete: {processed}/{len(topics)} topics processed")
    return processed
