import pytest
import json
from datetime import date, timedelta
from database import (
    init_db, get_db_connection, add_site, get_site, list_sites,
    add_plan, get_plan, add_topics_bulk, get_pending_topics,
    update_topic_status, log_action, count_published_today,
    encrypt_password, decrypt_password
)


class TestEncryption:
    """Test password encryption/decryption."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt then decrypt returns original."""
        password = "my-secret-password-123"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)
        assert decrypted == password
    
    def test_encrypted_is_different(self):
        """Test that encrypted value differs from original."""
        password = "test-password"
        encrypted = encrypt_password(password)
        assert encrypted != password


class TestSites:
    """Test site CRUD operations."""
    
    def test_add_site(self, db_conn):
        """Test adding a new site."""
        site_id = add_site(
            name="Test Blog",
            wp_url="https://blog.example.com",
            wp_username="admin",
            wp_app_password="app-pass-123",
            blog_template="<article>{{content}}</article>",
            default_category=5,
            posts_per_day=3
        )
        
        assert site_id is not None
        assert site_id > 0
    
    def test_get_site(self, db_conn):
        """Test retrieving a site with decrypted password."""
        # Add site
        site_id = add_site(
            name="My Blog",
            wp_url="https://example.com",
            wp_username="user",
            wp_app_password="secret-pass",
            blog_template="<div>{{title}}</div>"
        )
        
        # Retrieve site
        site = get_site(site_id)
        
        assert site is not None
        assert site["name"] == "My Blog"
        assert site["wp_url"] == "https://example.com"
        assert site["wp_app_password"] == "secret-pass"  # Should be decrypted
    
    def test_list_sites(self, db_conn):
        """Test listing all sites."""
        # Get initial count
        initial_sites = list_sites()
        initial_count = len(initial_sites)
        
        add_site("Site A", "https://sa.com", "u1", "p1", "<div></div>")
        add_site("Site B", "https://sb.com", "u2", "p2", "<div></div>")
        
        sites = list_sites()
        
        assert len(sites) == initial_count + 2
        # Verify the newly added sites exist
        site_names = [s["name"] for s in sites]
        assert "Site A" in site_names
        assert "Site B" in site_names


class TestPlans:
    """Test plan CRUD operations."""
    
    def test_add_plan(self, db_conn, sample_site):
        """Test adding a new plan."""
        plan_id = add_plan(
            site_id=sample_site,
            raw_markdown="# My Plan",
            extracted_json='{"topics": []}'
        )
        
        assert plan_id is not None
        assert plan_id > 0
    
    def test_get_plan(self, db_conn, sample_site):
        """Test retrieving a plan."""
        plan_id = add_plan(sample_site, "# Test Plan", '{"test": true}')
        plan = get_plan(plan_id)
        
        assert plan is not None
        assert plan["raw_markdown"] == "# Test Plan"


class TestTopics:
    """Test topic CRUD operations."""
    
    def test_add_topics_bulk(self, db_conn, sample_site, sample_plan):
        """Test bulk adding topics."""
        topics = get_pending_topics(sample_site)
        
        # We have 2 topics from fixture, one is scheduled for today
        assert len(topics) >= 1
    
    def test_pending_topics_ordering(self, db_conn, sample_site):
        """Test that pending topics are ordered by priority."""
        # Create plan with mixed priorities
        plan_id = add_plan(sample_site, "test", "{}")
        
        # Add topics with different priorities
        low_topic = {
            "title": "Low Priority",
            "priority": "low",
            "scheduled_date": date.today().isoformat()
        }
        high_topic = {
            "title": "High Priority",
            "priority": "high",
            "scheduled_date": date.today().isoformat()
        }
        
        add_topics_bulk(sample_site, plan_id, [low_topic, high_topic])
        
        topics = get_pending_topics(sample_site)
        
        # High priority should come first
        assert topics[0]["title"] == "High Priority"
    
    def test_update_topic_status(self, db_conn, sample_site, sample_plan):
        """Test updating topic status."""
        topics = get_pending_topics(sample_site)
        topic_id = topics[0]["id"]
        
        update_topic_status(
            topic_id,
            "content_generated",
            generated_tldr="Test TLDR",
            final_html="<p>Test</p>"
        )
        
        # Verify update
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
        updated = dict(cursor.fetchone())
        conn.close()
        
        assert updated["status"] == "content_generated"
        assert updated["generated_tldr"] == "Test TLDR"
    
    def test_count_published_today(self, db_conn, sample_site, sample_plan):
        """Test counting published topics for today."""
        topics = get_pending_topics(sample_site)
        
        # Mark one as published
        update_topic_status(topics[0]["id"], "published")
        
        count = count_published_today(sample_site)
        assert count == 1


class TestPostLog:
    """Test post logging."""
    
    def test_log_action(self, db_conn, sample_site, sample_plan):
        """Test logging an action."""
        topics = get_pending_topics(sample_site)
        topic_id = topics[0]["id"]
        
        log_action(topic_id, "test_action", "Test details")
        
        # Verify log entry
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM post_log WHERE topic_id = ?", (topic_id,))
        logs = cursor.fetchall()
        conn.close()
        
        assert len(logs) == 1
        assert logs[0]["action"] == "test_action"
