import json
from typing import Optional
from database import (
    get_site, get_pending_topics, update_topic_status,
    count_published_today, log_action, get_plan
)
from content_generator import generate_post_content
from template_assembler import assemble_final_html
from wp_publisher import publish_post
from logger import logger


def run_automation_cycle(site_id: int) -> int:
    """
    Run one automation cycle: generate and publish due topics.
    
    Args:
        site_id: Site ID to process
    
    Returns:
        Number of topics processed in this cycle
    """
    # Load site settings
    site = get_site(site_id)
    if not site:
        logger.error(f"Site {site_id} not found")
        return 0
    
    posts_per_day = site.get("posts_per_day", 2)
    
    # Check daily limit
    published_today = count_published_today(site_id)
    remaining_slots = posts_per_day - published_today
    
    if remaining_slots <= 0:
        logger.info(f"Daily limit reached for site {site_id} ({published_today}/{posts_per_day} published today)")
        return 0
    
    logger.info(f"Site {site_id}: {remaining_slots} slots remaining for today")
    
    # Get pending topics
    topics = get_pending_topics(site_id, limit=remaining_slots)
    
    if not topics:
        logger.info(f"No pending topics due for site {site_id}")
        return 0
    
    logger.info(f"Found {len(topics)} topics to process")
    
    processed = 0
    for topic in topics:
        topic_id = topic["id"]
        title = topic["title"]
        
        try:
            logger.info(f"Processing topic {topic_id}: {title}")
            log_action(topic_id, "started", f"Beginning content generation for: {title}")
            
            # Get plan context
            plan_context = topic.get("plan_context", {})
            if not plan_context:
                # Try to load from plan
                plan = get_plan(topic.get("plan_id"))
                if plan and plan.get("extracted_json"):
                    parsed = json.loads(plan["extracted_json"])
                    plan_context = parsed.get("global", {})
            
            # Update attempts count
            attempts = topic.get("attempts", 0) + 1
            update_topic_status(topic_id, "pending", attempts=attempts)
            
            # Generate content
            logger.info(f"Generating content for: {title}")
            content = generate_post_content(topic, site, plan_context)
            
            # Store generated content
            update_topic_status(
                topic_id,
                "content_generated",
                generated_tldr=content.get("tldr", ""),
                generated_body=content.get("content", ""),
                generated_faq=content.get("faq", ""),
                generated_meta_description=content.get("meta_description", "")
            )
            log_action(topic_id, "content_generated", "Content generated successfully")
            
            # Assemble final HTML
            logger.info(f"Assembling HTML for: {title}")
            final_html = assemble_final_html(
                site=site,
                title=title,
                tldr=content.get("tldr", ""),
                content=content.get("content", ""),
                faq=content.get("faq", ""),
                meta_description=content.get("meta_description", "")
            )
            
            update_topic_status(topic_id, "content_generated", final_html=final_html)
            
            # Publish to WordPress
            logger.info(f"Publishing '{title}' to WordPress...")
            wp_post_id = publish_post(
                site=site,
                title=title,
                content_html=final_html,
                status="draft",
                category=site.get("default_category"),
                slug=topic.get("slug"),
                meta_description=content.get("meta_description")
            )
            
            # Update topic with WP post ID
            update_topic_status(
                topic_id,
                "draft",
                wp_post_id=wp_post_id
            )
            log_action(topic_id, "published", f"Published as draft. WP Post ID: {wp_post_id}")
            
            processed += 1
            logger.info(f"✓ Successfully processed: {title}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to process topic {topic_id}: {error_msg}")
            
            # Update topic status
            attempts = topic.get("attempts", 0) + 1
            new_status = "failed" if attempts >= 3 else "pending"
            
            update_topic_status(
                topic_id,
                new_status,
                last_error=error_msg,
                attempts=attempts
            )
            log_action(topic_id, "error", f"Attempt {attempts}: {error_msg}")
            
            if new_status == "failed":
                logger.error(f"Topic {topic_id} marked as failed after {attempts} attempts")
    
    logger.info(f"Cycle complete: {processed}/{len(topics)} topics processed")
    return processed
