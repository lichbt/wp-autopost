import sqlite3
import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from cryptography.fernet import Fernet
from config import DB_FULL_PATH, ENCRYPTION_KEY, ensure_directories
from logger import logger

# Singleton connection for in-memory databases (for testing)
_memory_conn = None


# Encryption setup
def _get_cipher() -> Fernet:
    """Get Fernet cipher instance from environment key."""
    if not ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not set in environment. Run: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_password(password: str) -> str:
    """Encrypt a password for storage."""
    cipher = _get_cipher()
    return cipher.encrypt(password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a stored password."""
    cipher = _get_cipher()
    return cipher.decrypt(encrypted_password.encode()).decode()


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection with Row factory for dict-like access."""
    global _memory_conn
    
    db_path = str(DB_FULL_PATH)
    
    # For in-memory databases, reuse the same connection
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
    """Reset the in-memory database connection (for testing)."""
    global _memory_conn
    if _memory_conn:
        _memory_conn.close()
        _memory_conn = None


def init_db():
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sites table
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Plans table
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
    
    # Topics table
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
            final_html TEXT,
            attempts INTEGER DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
    """)
    
    # Post log table
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
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# ==================== Sites CRUD ====================

def add_site(
    name: str,
    wp_url: str,
    wp_username: str,
    wp_app_password: str,
    blog_template: str,
    default_category: int = 1,
    default_author: int = 1,
    posts_per_day: int = 2
) -> int:
    """Add a new site and return its ID. Encrypts the WP password."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    encrypted_pw = encrypt_password(wp_app_password)
    
    cursor.execute("""
        INSERT INTO sites (name, wp_url, wp_username, wp_app_password, blog_template,
                          default_category, default_author, posts_per_day)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, wp_url, wp_username, encrypted_pw, blog_template,
          default_category, default_author, posts_per_day))
    
    site_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Site added: {name} (ID: {site_id})")
    return site_id


def get_site(site_id: int) -> Optional[Dict]:
    """Get site by ID with decrypted password."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    site = dict(row)
    # Decrypt password for use
    site["wp_app_password"] = decrypt_password(site["wp_app_password"])
    return site


def list_sites() -> List[Dict]:
    """List all sites (without decrypted passwords)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, wp_url, wp_username, default_category, posts_per_day FROM sites")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ==================== Plans CRUD ====================

def add_plan(site_id: int, raw_markdown: str, extracted_json: str = None) -> int:
    """Add a new plan and return its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO plans (site_id, raw_markdown, extracted_json)
        VALUES (?, ?, ?)
    """, (site_id, raw_markdown, extracted_json))
    
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Plan added for site {site_id} (ID: {plan_id})")
    return plan_id


def get_plan(plan_id: int) -> Optional[Dict]:
    """Get plan by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_plan_by_site(site_id: int) -> Optional[Dict]:
    """Get the latest plan for a site."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM plans WHERE site_id = ? ORDER BY created_at DESC LIMIT 1", (site_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


# ==================== Topics CRUD ====================

def add_topics_bulk(site_id: int, plan_id: int, topics_list: List[Dict]) -> List[int]:
    """
    Bulk insert topics from parsed plan data.
    
    Args:
        site_id: Site ID
        plan_id: Plan ID
        topics_list: List of topic dicts from plan parser
    
    Returns:
        List of inserted topic IDs
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    topic_ids = []
    for topic in topics_list:
        # Convert lists to JSON strings for storage
        target_keywords = json.dumps(topic.get("target_keywords", []))
        internal_links = json.dumps(topic.get("internal_links", []))
        
        cursor.execute("""
            INSERT INTO topics (site_id, plan_id, title, slug, pillar, priority, intent,
                              target_keywords, internal_links, special_instructions, scheduled_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            site_id,
            plan_id,
            topic.get("title"),
            topic.get("slug"),
            topic.get("pillar"),
            topic.get("priority", "medium"),
            topic.get("intent", "informational"),
            target_keywords,
            internal_links,
            topic.get("special_instructions"),
            topic.get("scheduled_date")
        ))
        topic_ids.append(cursor.lastrowid)
    
    conn.commit()
    conn.close()
    logger.info(f"Added {len(topic_ids)} topics for plan {plan_id}")
    return topic_ids


def get_pending_topics(site_id: int, limit: int = 10) -> List[Dict]:
    """
    Get pending topics that are due for processing.
    
    Ordered by priority (high first), then scheduled_date (NULL first).
    Only returns topics where scheduled_date <= today or is NULL.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    cursor.execute("""
        SELECT t.*, p.extracted_json as plan_json
        FROM topics t
        JOIN plans p ON t.plan_id = p.id
        WHERE t.site_id = ?
          AND t.status = 'pending'
          AND (t.scheduled_date IS NULL OR t.scheduled_date <= ?)
        ORDER BY 
            CASE t.priority 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 3 
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
        # Parse JSON fields
        topic["target_keywords"] = json.loads(topic.get("target_keywords") or "[]")
        topic["internal_links"] = json.loads(topic.get("internal_links") or "[]")
        # Parse plan context if available
        if topic.get("plan_json"):
            topic["plan_context"] = json.loads(topic["plan_json"])
        else:
            topic["plan_context"] = {}
        topics.append(topic)
    
    return topics


def update_topic_status(topic_id: int, status: str, **kwargs):
    """
    Update topic status and optional fields.
    
    Args:
        topic_id: Topic ID
        status: New status value
        **kwargs: Additional fields to update (wp_post_id, final_html, generated_tldr, etc.)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build dynamic update query
    allowed_fields = {
        "wp_post_id", "generated_tldr", "generated_body", "generated_faq",
        "generated_meta_description", "final_html", "last_error", "attempts",
        "slug"
    }
    
    updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params = [status]
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            params.append(value)
    
    query = f"UPDATE topics SET {', '.join(updates)} WHERE id = ?"
    params.append(topic_id)
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    logger.info(f"Topic {topic_id} updated: status={status}")


def get_topic(topic_id: int) -> Optional[Dict]:
    """Get a single topic by ID."""
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
    """Get all topics for a plan."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM topics WHERE plan_id = ? ORDER BY id", (plan_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def count_published_today(site_id: int) -> int:
    """Count how many topics were published today for a site."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = date.today().isoformat()
    
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM topics 
        WHERE site_id = ? 
          AND status = 'published'
          AND DATE(updated_at) = ?
    """, (site_id, today))
    
    row = cursor.fetchone()
    conn.close()
    
    return row["count"] if row else 0


# ==================== Post Log CRUD ====================

def log_action(topic_id: int, action: str, details: str = None):
    """Log an action for a topic."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO post_log (topic_id, action, details)
        VALUES (?, ?, ?)
    """, (topic_id, action, details))
    
    conn.commit()
    conn.close()


def get_topic_logs(topic_id: int) -> List[Dict]:
    """Get all log entries for a topic."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM post_log WHERE topic_id = ? ORDER BY created_at", (topic_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
