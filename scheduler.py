import json
from typing import Optional
from database import (
    get_site, get_pending_topics, update_topic_status,
    count_published_today, log_action, get_plan
)
from content_generator import generate_post_content
from template_assembler import assemble_final_html
from publisher import publish_for_site, is_wordpress
import seo_validator
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

    # Self-heal: mark pending topics that already exist live as published, so we
    # never re-write a duplicate when a plan slug differs from the live slug.
    # WordPress-only — non-WP (markdown_export) sites have no live API to reconcile against.
    if is_wordpress(site):
        try:
            from wp_sync import reconcile_pending_against_live
            rec = reconcile_pending_against_live(site_id, apply=True)
            if rec.get("published"):
                logger.info(f"[cycle] reconcile auto-marked {len(rec['published'])} already-live topic(s) published")
            if rec.get("review"):
                logger.warning(f"[cycle] reconcile flagged {len(rec['review'])} topic(s) as possible live duplicates — review")
        except Exception as exc:
            logger.warning(f"[cycle] reconcile skipped: {exc}")

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
            
            # Generate content + SEO validation (auto-revises once if it fails)
            logger.info(f"Generating content for: {title}")
            try:
                content, seo_val = seo_validator.generate_and_validate(topic, site, plan_context)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to generate content for topic {topic_id}: {error_msg}")
                
                # Update topic status
                attempts = topic.get("attempts", 0) + 1
                new_status = "failed" if attempts >= 3 else "pending"
                
                update_topic_status(
                    topic_id,
                    new_status,
                    last_error=error_msg,
                    attempts=attempts
                )
                log_action(topic_id, "error", f"Content generation attempt {attempts}: {error_msg}")
                
                if new_status == "failed":
                    logger.error(f"Topic {topic_id} marked as failed after {attempts} attempts")
                continue  # Skip to next topic
            
            # Store generated content
            update_topic_status(
                topic_id,
                "content_generated",
                generated_tldr=content.get("tldr", ""),
                generated_body=content.get("content", ""),
                generated_faq=content.get("faq", ""),
                generated_meta_description=content.get("meta_description", ""),
                generated_meta_title=content.get("meta_title", ""),
                generated_slug=content.get("slug", ""),
                writing_persona=content.get("writing_persona", ""),
                final_html=""  # Will be set below
            )
            log_action(topic_id, "content_generated", "Content generated successfully")
            
            # Assemble final HTML (WordPress only — markdown_export skips the HTML wrapper
            # and converts the raw content body to Markdown at output time).
            if is_wordpress(site):
                logger.info(f"Assembling HTML for: {title}")
                publish_body = assemble_final_html(
                    site=site,
                    title=title,
                    tldr=content.get("tldr", ""),
                    content=content.get("content", ""),
                    faq=content.get("faq", ""),
                    meta_description=content.get("meta_description", ""),
                    meta_title=content.get("meta_title") or title  # Use generated or fallback to title
                )
                update_topic_status(topic_id, "content_generated", final_html=publish_body)
            else:
                publish_body = content.get("content", "")

            # SEO gate — if the article still failed after the auto-revision pass,
            # hold it for review (leave status content_generated, do NOT publish).
            if not seo_val.get("passed"):
                issues = "; ".join(f["detail"] for f in seo_val["findings"][:6])
                msg = f"SEO gate: {seo_val['score']}/100 — held for review. {issues}"
                update_topic_status(topic_id, "content_generated", last_error=msg,
                                    final_html=publish_body if is_wordpress(site) else "")
                log_action(topic_id, "seo_hold", msg)
                logger.warning(f"[seo] HOLD topic {topic_id}: {msg}")
                continue  # skip publish

            # Map pillar → schema type
            _PILLAR_SCHEMA = {
                "how_to": "HowTo",
                "how-to": "HowTo",
                "setup_tutorial": "HowTo",
                "definition": "Article",
                "definitions": "Article",
                "vs_comparison": "Article",
                "best_of": "Article",
                "buyer_guide": "Article",
                "feature_explainer": "TechArticle",
                "cost_roi": "Article",
                "use_case": "Article",
            }
            pillar = topic.get("pillar", "")
            schema_type = _PILLAR_SCHEMA.get(pillar, "Article")

            # Output: WordPress draft OR markdown file (routed by platform)
            logger.info(f"Publishing '{title}' ({site.get('platform') or 'wordpress'})...")
            res = publish_for_site(
                site=site,
                title=title,
                content_html=publish_body,
                status="draft",
                category=site.get("default_category"),
                slug=topic.get("slug") or content.get("slug"),
                meta_description=content.get("meta_description"),
                focus_keyword=content.get("focus_keyword") or topic.get("generated_focus_keyword", ""),
                seo_title=content.get("meta_title") or title,
                schema_type=schema_type,
                faq_html=content.get("faq", ""),
            )
            if not res:
                raise Exception("Publishing/output returned no result")

            if res["kind"] == "wp":
                update_topic_status(topic_id, "draft", wp_post_id=res["id"])
                log_action(topic_id, "published", f"Published as draft. WP Post ID: {res['id']}")
            else:
                update_topic_status(topic_id, "draft",
                                    target_url=res["url"], generated_slug=res.get("slug"))
                log_action(topic_id, "published", f"Wrote markdown file: {res['path']}")

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
