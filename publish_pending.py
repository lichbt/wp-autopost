"""
One-shot script: generate & publish pending topics #205, #206, #213 for ShaunSocial (site_id=4).
Run: python3 publish_pending.py [topic_id]
If topic_id is given, only that topic is processed.
"""
import json
import sqlite3
import sys
import os

sys.path.insert(0, ".")

# Load .env manually
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from database import get_site
from content_generator import generate_post_content
from template_assembler import assemble_final_html
from wp_publisher import publish_post
from logger import logger

SITE_ID = 4
DB_PATH = "data/blog_automation.db"

# Optional: override to a single topic id from CLI
only_id = int(sys.argv[1]) if len(sys.argv) > 1 else None


def get_pending_topics(conn, topic_ids):
    placeholders = ",".join("?" * len(topic_ids))
    rows = conn.execute(
        f"SELECT id, title, pillar, target_keywords, special_instructions, intent "
        f"FROM topics WHERE id IN ({placeholders}) AND status='pending'",
        topic_ids,
    ).fetchall()
    topics = []
    for r in rows:
        d = dict(r)
        try:
            d["target_keywords"] = json.loads(d["target_keywords"]) if d["target_keywords"] else []
        except Exception:
            d["target_keywords"] = []
        topics.append(d)
    return topics


def update_status(conn, topic_id, status, wp_post_id=None):
    if wp_post_id:
        conn.execute(
            "UPDATE topics SET status=?, wp_post_id=? WHERE id=?",
            (status, wp_post_id, topic_id),
        )
    else:
        conn.execute("UPDATE topics SET status=? WHERE id=?", (status, topic_id))
    conn.commit()


# Pillar → schema type mapping
SCHEMA_MAP = {
    "definition": "Article",
    "best_of": "Article",
    "vs_comparison": "Article",
    "how_to": "HowTo",
    "setup_tutorial": "HowTo",
    "feature_explainer": "TechArticle",
    "use_case": "Article",
    "cost_roi": "Article",
    "buyer_guide": "Article",
}

# Pillar → CTA defaults
CTA_MAP = {
    "definition": ("https://shaunsocial.com/demo/", "View ShaunSocial Demo"),
    "best_of": ("https://shaunsocial.com/demo/", "Try ShaunSocial Free Demo"),
    "vs_comparison": ("https://shaunsocial.com/demo/", "Try ShaunSocial Demo"),
}


def main():
    site = get_site(SITE_ID)
    if not site:
        print(f"ERROR: site_id={SITE_ID} not found")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    target_ids = [only_id] if only_id else [205, 206, 213]
    topics = get_pending_topics(conn, target_ids)

    if not topics:
        print("No pending topics found.")
        return

    # Minimal plan_context (pillar hints pulled from plan if available)
    plan_context = {
        "default_pillar_template_hints": {
            "definition": (
                "Open with a direct one-sentence definition. "
                "Explain how it differs from a standard CMS. "
                "Include a feature comparison table. "
                "Mention top tools with ShaunSocial highlighted."
            ),
            "best_of": (
                "Open with the top pick immediately. "
                "Include a ranked list with pros/cons for each tool. "
                "Add a feature comparison table. "
                "Link to demo or pricing for top pick."
            ),
            "vs_comparison": (
                "Open with a direct verdict. "
                "Compare head-to-head across key dimensions. "
                "Include a side-by-side comparison table. "
                "Recommend ShaunSocial with demo CTA."
            ),
        }
    }

    for topic in topics:
        tid = topic["id"]
        title = topic["title"]
        pillar = topic.get("pillar", "definition")

        print(f"\n{'='*60}")
        print(f"Processing topic #{tid}: {title}")
        print(f"{'='*60}")

        try:
            # 1. Generate content
            print("Generating content...")
            content = generate_post_content(topic, site, plan_context)
            print(f"Content generated: {len(content.get('content',''))} chars")

            tldr = content.get("tldr", "")
            body_html = content.get("content", "")
            faq_html = content.get("faq", "")
            meta_desc = content.get("meta_description", "")
            meta_title = content.get("meta_title", title)
            focus_kw = content.get("focus_keyword", topic["target_keywords"][0] if topic["target_keywords"] else "")
            slug = content.get("slug", "")

            cta_link, cta_text = CTA_MAP.get(pillar, ("https://shaunsocial.com/demo/", "Learn More"))

            # 2. Assemble full HTML
            print("Assembling HTML...")
            final_html = assemble_final_html(
                site=site,
                title=title,
                tldr=tldr,
                content=body_html,
                faq=faq_html,
                meta_description=meta_desc,
                meta_title=meta_title,
                cta_link=cta_link,
                cta_text=cta_text,
            )
            print(f"Final HTML: {len(final_html)} chars")

            schema_type = SCHEMA_MAP.get(pillar, "Article")

            # 3. Publish to WP
            print(f"Publishing to WordPress (status=publish)...")
            wp_id = publish_post(
                site=site,
                title=title,
                content_html=final_html,
                status="publish",
                slug=slug or None,
                meta_description=meta_desc,
                focus_keyword=focus_kw,
                seo_title=meta_title,
                schema_type=schema_type,
                faq_html=faq_html,
            )

            if wp_id:
                print(f"✓ Published! WP post ID: {wp_id}")
                update_status(conn, tid, "published", wp_id)
                print(f"✓ DB updated: topic #{tid} → published, wp_post_id={wp_id}")
            else:
                print(f"✗ Publish failed for topic #{tid}")
                update_status(conn, tid, "error")

        except Exception as e:
            import traceback
            print(f"✗ Error on topic #{tid}: {e}")
            traceback.print_exc()
            update_status(conn, tid, "error")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
