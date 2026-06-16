import sqlite3
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from cryptography.fernet import Fernet
from config import DB_FULL_PATH, ENCRYPTION_KEY, ensure_directories
from logger import logger

_memory_conn = None


# ── Encryption ────────────────────────────────────────────────────────────────

def _get_cipher() -> Fernet:
    if not ENCRYPTION_KEY:
        raise ValueError(
            "ENCRYPTION_KEY not set. Run: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_password(password: str) -> str:
    return _get_cipher().encrypt(password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    return _get_cipher().decrypt(encrypted_password.encode()).decode()


# ── Connection ────────────────────────────────────────────────────────────────

def get_db_connection() -> sqlite3.Connection:
    global _memory_conn
    db_path = str(DB_FULL_PATH)
    if db_path == ":memory:":
        if _memory_conn is None:
            _memory_conn = sqlite3.connect(":memory:")
            _memory_conn.row_factory = sqlite3.Row
            _memory_conn.execute("PRAGMA foreign_keys = ON")
        return _memory_conn
    ensure_directories()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def reset_memory_db():
    global _memory_conn
    if _memory_conn:
        _memory_conn.close()
        _memory_conn = None


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """Initialize all database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            wp_url TEXT NOT NULL,
            wp_username TEXT NOT NULL,
            wp_app_password TEXT NOT NULL,
            blog_template TEXT NOT NULL,
            default_category INTEGER DEFAULT 1,
            default_author INTEGER DEFAULT 1,
            posts_per_day INTEGER DEFAULT 2,
            gsc_url TEXT,
            ga4_property_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            raw_markdown TEXT NOT NULL,
            extracted_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            slug TEXT,
            pillar TEXT,
            priority TEXT CHECK(priority IN ('high','medium','low')),
            intent TEXT,
            target_keywords TEXT,
            internal_links TEXT,
            special_instructions TEXT,
            scheduled_date DATE,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','content_generated','draft','published','failed')),
            wp_post_id INTEGER,
            generated_tldr TEXT,
            generated_body TEXT,
            generated_faq TEXT,
            generated_meta_description TEXT,
            generated_focus_keyword TEXT,
            generated_seo_title TEXT,
            generated_schema_type TEXT,
            final_html TEXT,
            attempts INTEGER DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            action TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    """)

    # Google Search Console data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gsc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            fetched_date DATE NOT NULL,
            query TEXT NOT NULL,
            page TEXT,
            clicks INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            ctr REAL DEFAULT 0,
            position REAL DEFAULT 0,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_gsc_site_date ON gsc_data(site_id, fetched_date)
    """)

    # Google Analytics 4 data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ga4_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            fetched_date DATE NOT NULL,
            page_path TEXT NOT NULL,
            sessions INTEGER DEFAULT 0,
            pageviews INTEGER DEFAULT 0,
            bounce_rate REAL DEFAULT 0,
            avg_session_duration REAL DEFAULT 0,
            new_users INTEGER DEFAULT 0,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ga4_site_date ON ga4_data(site_id, fetched_date)
    """)

    # GEO sightings — when your content appears in an AI answer
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geo_sightings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            url TEXT NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('chatgpt','perplexity','gemini','claude','copilot','other')),
            spotted_at DATE NOT NULL,
            notes TEXT,
            pillar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        )
    """)

    conn.commit()
    conn.close()

    # Run migrations to add new columns to existing tables
    _run_migrations()

    logger.info("Database initialized successfully")


def _run_migrations():
    """Add new columns to existing tables if they don't exist (safe for existing DBs)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    new_site_cols = [
        ("gsc_url", "TEXT"),
        ("ga4_property_id", "TEXT"),
        # Publishing target: 'wordpress' (default) or 'markdown_export'
        ("platform", "TEXT DEFAULT 'wordpress'"),
        # For non-WP sites: local directory where generated content files are written
        ("content_repo_path", "TEXT"),
    ]
    new_topic_cols = [
        ("generated_focus_keyword", "TEXT"),
        ("generated_seo_title", "TEXT"),
        ("generated_schema_type", "TEXT"),
        # Feature 1: writing persona used for this article
        ("writing_persona", "TEXT"),
        # Feature 3: article performance scoring
        ("performance_score", "REAL"),
        ("last_scored_at", "DATE"),
        ("score_tier", "TEXT"),
        # LLM-suggested content template (overrides the pillar default structure)
        ("recommended_template", "TEXT"),
        # Planner action: 'new' (default) or 'refresh' an existing live URL
        ("action", "TEXT"),
        ("target_url", "TEXT"),
        # Topic cluster / hub this article belongs to (Tier 2)
        ("cluster", "TEXT"),
        ("is_pillar_page", "INTEGER DEFAULT 0"),
    ]

    for col, col_type in new_site_cols:
        try:
            cursor.execute(f"ALTER TABLE sites ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # column already exists

    for col, col_type in new_topic_cols:
        try:
            cursor.execute(f"ALTER TABLE topics ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    conn.commit()
    conn.close()


# ── Sites CRUD ────────────────────────────────────────────────────────────────

def add_site(
    name: str,
    wp_url: str,
    wp_username: str,
    wp_app_password: str,
    blog_template: str,
    default_category: int = 1,
    default_author: int = 1,
    posts_per_day: int = 2,
    gsc_url: str = "",
    ga4_property_id: str = "",
    platform: str = "wordpress",
    content_repo_path: str = None,
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    encrypted_pw = encrypt_password(wp_app_password)
    cursor.execute("""
        INSERT INTO sites (name, wp_url, wp_username, wp_app_password, blog_template,
                          default_category, default_author, posts_per_day, gsc_url, ga4_property_id,
                          platform, content_repo_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, wp_url, wp_username, encrypted_pw, blog_template,
          default_category, default_author, posts_per_day, gsc_url, ga4_property_id,
          platform, content_repo_path))
    site_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Site added: {name} (ID: {site_id})")
    return site_id


def get_site(site_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    site = dict(row)
    site["wp_app_password"] = decrypt_password(site["wp_app_password"])
    return site


def list_sites() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, wp_url, wp_username, default_category, posts_per_day, gsc_url, ga4_property_id FROM sites"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_site_google_config(site_id: int, gsc_url: str, ga4_property_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sites SET gsc_url = ?, ga4_property_id = ? WHERE id = ?",
        (gsc_url, ga4_property_id, site_id),
    )
    conn.commit()
    conn.close()


# ── Plans CRUD ────────────────────────────────────────────────────────────────

def add_plan(site_id: int, raw_markdown: str, extracted_json: str = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO plans (site_id, raw_markdown, extracted_json) VALUES (?, ?, ?)",
        (site_id, raw_markdown, extracted_json),
    )
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Plan added for site {site_id} (ID: {plan_id})")
    return plan_id


def get_plan(plan_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_plan_by_site(site_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM plans WHERE site_id = ? ORDER BY created_at DESC LIMIT 1",
        (site_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ── Topics CRUD ───────────────────────────────────────────────────────────────

def add_topics_bulk(site_id: int, plan_id: int, topics_list: List[Dict]) -> List[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    topic_ids = []
    for topic in topics_list:
        target_keywords = json.dumps(topic.get("target_keywords", []))
        internal_links = json.dumps(topic.get("internal_links", []))
        cursor.execute("""
            INSERT INTO topics (site_id, plan_id, title, slug, pillar, priority, intent,
                              target_keywords, internal_links, special_instructions, scheduled_date,
                              recommended_template, action, target_url, cluster, is_pillar_page)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            site_id, plan_id,
            topic.get("title"), topic.get("slug"), topic.get("pillar"),
            topic.get("priority", "medium"), topic.get("intent", "informational"),
            target_keywords, internal_links,
            topic.get("special_instructions"), topic.get("scheduled_date"),
            topic.get("recommended_template"),
            topic.get("action", "new"), topic.get("target_url"),
            topic.get("cluster"), 1 if topic.get("is_pillar_page") else 0,
        ))
        topic_ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    logger.info(f"Added {len(topic_ids)} topics for plan {plan_id}")
    return topic_ids


def get_pending_topics(site_id: int, limit: int = 10) -> List[Dict]:
    """Return pending topics due today, ordered by GEO-priority pillar then DB priority."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    # GEO-high-value pillars (vs_comparison, best_of, buyer_guide) published first
    cursor.execute("""
        SELECT t.*, p.extracted_json as plan_json
        FROM topics t
        JOIN plans p ON t.plan_id = p.id
        WHERE t.site_id = ?
          AND t.status = 'pending'
          AND (t.scheduled_date IS NULL OR t.scheduled_date <= ?)
          AND LOWER(TRIM(t.title)) NOT IN (
              SELECT LOWER(TRIM(title)) FROM topics
              WHERE site_id = t.site_id
                AND status IN ('published', 'draft', 'content_generated')
                AND id != t.id
          )
        ORDER BY
            CASE t.pillar
                WHEN 'vs_comparison'  THEN 1
                WHEN 'best_of'        THEN 2
                WHEN 'buyer_guide'    THEN 3
                WHEN 'setup_tutorial' THEN 4
                WHEN 'how_to'         THEN 4
                WHEN 'feature_explainer' THEN 5
                WHEN 'use_case'       THEN 6
                ELSE 7
            END,
            CASE t.priority
                WHEN 'high'   THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low'    THEN 3
            END,
            t.scheduled_date IS NOT NULL,
            t.scheduled_date
        LIMIT ?
    """, (site_id, today, limit))
    rows = cursor.fetchall()
    conn.close()
    topics = []
    for row in rows:
        topic = dict(row)
        topic["target_keywords"] = json.loads(topic.get("target_keywords") or "[]")
        topic["internal_links"] = json.loads(topic.get("internal_links") or "[]")
        topic["plan_context"] = json.loads(topic["plan_json"]) if topic.get("plan_json") else {}
        topics.append(topic)
    return topics


def get_stale_topics_for_refresh(site_id: int, days_old: int = 90) -> List[Dict]:
    """Return published/draft topics older than days_old with avg GSC position > 20."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (date.today() - timedelta(days=days_old)).isoformat()
    cursor.execute("""
        SELECT t.*,
               AVG(g.position) as avg_position,
               SUM(g.impressions) as total_impressions
        FROM topics t
        LEFT JOIN gsc_data g ON g.site_id = t.site_id
            AND g.page LIKE '%' || COALESCE(t.slug, '') || '%'
        WHERE t.site_id = ?
          AND t.status IN ('draft', 'published')
          AND DATE(t.updated_at) <= ?
        GROUP BY t.id
        HAVING (avg_position IS NULL OR avg_position > 20)
           AND (total_impressions IS NULL OR total_impressions > 0)
        ORDER BY
            CASE WHEN t.performance_score IS NOT NULL THEN t.performance_score ELSE 50 END ASC,
            total_impressions DESC
        LIMIT 5
    """, (site_id, cutoff))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        t = dict(row)
        t["target_keywords"] = json.loads(t.get("target_keywords") or "[]")
        t["internal_links"] = json.loads(t.get("internal_links") or "[]")
        result.append(t)
    return result


def update_topic_status(topic_id: int, status: str, **kwargs):
    conn = get_db_connection()
    cursor = conn.cursor()
    allowed_fields = {
        "wp_post_id", "generated_tldr", "generated_body", "generated_faq",
        "generated_meta_description", "generated_focus_keyword", "generated_seo_title",
        "generated_schema_type", "final_html", "last_error", "attempts", "slug",
        # Non-WP (markdown_export) output: public URL of the produced file
        "target_url",
        # Feature 1
        "writing_persona",
        # Feature 3
        "performance_score", "last_scored_at", "score_tier",
    }
    updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params = [status]
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            params.append(value)
    params.append(topic_id)
    cursor.execute(f"UPDATE topics SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    logger.info(f"Topic {topic_id} updated: status={status}")


def get_topic(topic_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    topic = dict(row)
    topic["target_keywords"] = json.loads(topic.get("target_keywords") or "[]")
    topic["internal_links"] = json.loads(topic.get("internal_links") or "[]")
    return topic


def get_topics_by_plan(plan_id: int) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM topics WHERE plan_id = ? ORDER BY id", (plan_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_topics_summary(site_id: int) -> List[Dict]:
    """Lightweight summary of all topics for context building."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, pillar, status, intent, target_keywords, scheduled_date, created_at
        FROM topics
        WHERE site_id = ?
        ORDER BY created_at DESC
        LIMIT 200
    """, (site_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        t = dict(row)
        t["target_keywords"] = json.loads(t.get("target_keywords") or "[]")
        result.append(t)
    return result


def count_published_today(site_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("""
        SELECT COUNT(*) as count FROM topics
        WHERE site_id = ? AND status IN ('draft','published') AND DATE(updated_at) = ?
    """, (site_id, today))
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0


# ── Post Log ──────────────────────────────────────────────────────────────────

def log_action(topic_id: int, action: str, details: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO post_log (topic_id, action, details) VALUES (?, ?, ?)",
        (topic_id, action, details),
    )
    conn.commit()
    conn.close()


def get_topic_logs(topic_id: int) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM post_log WHERE topic_id = ? ORDER BY created_at", (topic_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ── WP Sync helpers ──────────────────────────────────────────────────────────

def get_or_create_import_plan(site_id: int) -> int:
    """
    Return the plan_id of the 'WP Historical Import' pseudo-plan for this site.
    Creates it if it doesn't exist yet (idempotent).
    Required because topics.plan_id is NOT NULL with a FK constraint.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM plans WHERE site_id = ? AND raw_markdown = 'WP Historical Import' LIMIT 1",
        (site_id,),
    )
    row = cursor.fetchone()
    if row:
        conn.close()
        return row["id"]
    cursor.execute(
        "INSERT INTO plans (site_id, raw_markdown, extracted_json) VALUES (?, ?, ?)",
        (site_id, "WP Historical Import", '{"global": {"strategy_summary": "Imported from WordPress"}, "topics": []}'),
    )
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Created WP import plan for site {site_id} (plan_id={plan_id})")
    return plan_id


def import_wp_post_stub(
    site_id: int, plan_id: int,
    title: str, slug: str, wp_post_id: int,
) -> int:
    """
    Insert a minimal stub topic row for a WordPress post not already in the DB.
    Sets status='published' so get_pending_topics() dedup skips it.
    Returns new topic_id, or 0 if a duplicate slug/wp_post_id already exists.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Guard against race conditions / duplicate calls
    cursor.execute(
        "SELECT id FROM topics WHERE site_id = ? AND (slug = ? OR wp_post_id = ?) LIMIT 1",
        (site_id, slug, wp_post_id),
    )
    if cursor.fetchone():
        conn.close()
        return 0
    cursor.execute("""
        INSERT INTO topics
            (site_id, plan_id, title, slug, wp_post_id, status, priority, attempts)
        VALUES (?, ?, ?, ?, ?, 'published', 'medium', 0)
    """, (site_id, plan_id, title, slug, wp_post_id))
    topic_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return topic_id


def get_all_topic_wp_ids(site_id: int) -> set:
    """Return set of all wp_post_id integers tracked in the DB for this site."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT wp_post_id FROM topics WHERE site_id = ? AND wp_post_id IS NOT NULL",
        (site_id,),
    ).fetchall()
    conn.close()
    return {r["wp_post_id"] for r in rows}


def get_all_topic_slugs(site_id: int) -> set:
    """Return set of all non-empty slugs tracked in the DB for this site."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT slug FROM topics WHERE site_id = ? AND slug IS NOT NULL AND slug != ''",
        (site_id,),
    ).fetchall()
    conn.close()
    return {r["slug"] for r in rows}


def link_wp_post_by_slug(site_id: int, slug: str, wp_post_id: int):
    """
    Update a topic found by slug to record the WordPress post ID and mark as published.
    Used when sync finds a slug match but the wp_post_id column was NULL.
    """
    conn = get_db_connection()
    conn.execute(
        "UPDATE topics SET wp_post_id = ?, status = 'published', updated_at = CURRENT_TIMESTAMP "
        "WHERE site_id = ? AND slug = ?",
        (wp_post_id, site_id, slug),
    )
    conn.commit()
    conn.close()


# ── GSC / GA4 data ────────────────────────────────────────────────────────────

def upsert_gsc_data(site_id: int, fetched_date: str, rows: List[Dict]):
    """Replace GSC data for a given fetch date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM gsc_data WHERE site_id = ? AND fetched_date = ?",
        (site_id, fetched_date),
    )
    for row in rows:
        cursor.execute("""
            INSERT INTO gsc_data (site_id, fetched_date, query, page, clicks, impressions, ctr, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            site_id, fetched_date,
            row.get("query", ""), row.get("page", ""),
            row.get("clicks", 0), row.get("impressions", 0),
            row.get("ctr", 0.0), row.get("position", 0.0),
        ))
    conn.commit()
    conn.close()
    logger.info(f"Stored {len(rows)} GSC rows for site {site_id} ({fetched_date})")


def upsert_ga4_data(site_id: int, fetched_date: str, rows: List[Dict]):
    """Replace GA4 data for a given fetch date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM ga4_data WHERE site_id = ? AND fetched_date = ?",
        (site_id, fetched_date),
    )
    for row in rows:
        cursor.execute("""
            INSERT INTO ga4_data (site_id, fetched_date, page_path, sessions, pageviews,
                                  bounce_rate, avg_session_duration, new_users)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            site_id, fetched_date,
            row.get("page_path", ""),
            row.get("sessions", 0), row.get("pageviews", 0),
            row.get("bounce_rate", 0.0), row.get("avg_session_duration", 0.0),
            row.get("new_users", 0),
        ))
    conn.commit()
    conn.close()
    logger.info(f"Stored {len(rows)} GA4 rows for site {site_id} ({fetched_date})")


def get_gsc_summary(site_id: int, days: int = 30) -> Dict:
    """Return aggregated GSC data for the last N days."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    cursor.execute("""
        SELECT query, page,
               SUM(clicks) as clicks, SUM(impressions) as impressions,
               AVG(ctr) as avg_ctr, AVG(position) as avg_position
        FROM gsc_data
        WHERE site_id = ? AND fetched_date >= ?
        GROUP BY query, page
        ORDER BY impressions DESC
        LIMIT 200
    """, (site_id, cutoff))
    rows = [dict(r) for r in cursor.fetchall()]

    # Top queries, low-CTR opportunities, top pages
    top_queries = rows[:20]
    low_ctr = [r for r in rows if r["avg_ctr"] < 0.03 and r["impressions"] > 50][:10]

    cursor.execute("""
        SELECT page, SUM(clicks) as clicks, SUM(impressions) as impressions, AVG(position) as avg_position
        FROM gsc_data
        WHERE site_id = ? AND fetched_date >= ?
        GROUP BY page
        ORDER BY clicks DESC
        LIMIT 20
    """, (site_id, cutoff))
    top_pages = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "top_queries": top_queries,
        "low_ctr_opportunities": low_ctr,
        "top_pages": top_pages,
        "total_rows": len(rows),
    }


def get_ga4_summary(site_id: int, days: int = 30) -> Dict:
    """Return aggregated GA4 data for the last N days."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    cursor.execute("""
        SELECT page_path,
               SUM(sessions) as sessions, SUM(pageviews) as pageviews,
               AVG(bounce_rate) as avg_bounce_rate,
               AVG(avg_session_duration) as avg_duration,
               SUM(new_users) as new_users
        FROM ga4_data
        WHERE site_id = ? AND fetched_date >= ?
        GROUP BY page_path
        ORDER BY sessions DESC
        LIMIT 30
    """, (site_id, cutoff))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"top_pages": rows}


# ── GEO Sightings ─────────────────────────────────────────────────────────────

def add_geo_sighting(
    site_id: int, query: str, url: str, source: str,
    spotted_at: str, notes: str = "", pillar: str = ""
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO geo_sightings (site_id, query, url, source, spotted_at, notes, pillar)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (site_id, query, url, source, spotted_at, notes, pillar))
    sighting_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"GEO sighting logged: {source} cited {url}")
    return sighting_id


def get_geo_sightings(site_id: int) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM geo_sightings WHERE site_id = ? ORDER BY spotted_at DESC
    """, (site_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_geo_stats(site_id: int) -> Dict:
    """Aggregate GEO sightings by source and pillar."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT source, COUNT(*) as count FROM geo_sightings
        WHERE site_id = ? GROUP BY source ORDER BY count DESC
    """, (site_id,))
    by_source = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT pillar, COUNT(*) as count FROM geo_sightings
        WHERE site_id = ? AND pillar != '' GROUP BY pillar ORDER BY count DESC
    """, (site_id,))
    by_pillar = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {"by_source": by_source, "by_pillar": by_pillar}
