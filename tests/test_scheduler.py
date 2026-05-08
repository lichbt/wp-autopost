import pytest
import json
from datetime import date
from scheduler import run_automation_cycle
from database import get_pending_topics, update_topic_status, get_topic


class TestScheduler:
    """Test scheduler integration."""
    
    def test_run_cycle_with_dry_run(self, monkeypatch, db_conn, sample_site, sample_plan):
        """Test running a full cycle in dry-run mode."""
        # Force dry-run in all modules
        monkeypatch.setattr("config.DRY_RUN", True)
        monkeypatch.setattr("content_generator.DRY_RUN", True)
        monkeypatch.setattr("wp_publisher.DRY_RUN", True)
        
        # Run the cycle
        processed = run_automation_cycle(sample_site)
        
        # Should process at least 1 topic (today's scheduled)
        assert processed >= 1
    
    def test_daily_limit_respected(self, monkeypatch, db_conn, sample_site, sample_plan):
        """Test that daily limits are respected."""
        monkeypatch.setattr("config.DRY_RUN", True)
        monkeypatch.setattr("content_generator.DRY_RUN", True)
        monkeypatch.setattr("wp_publisher.DRY_RUN", True)
        
        # First run should process topics
        processed1 = run_automation_cycle(sample_site)
        assert processed1 >= 1
        
        # Get remaining pending topics
        remaining = get_pending_topics(sample_site)
        
        # Second run should process more if under limit
        processed2 = run_automation_cycle(sample_site)
        
        # Total should not exceed posts_per_day (2)
        total = processed1 + processed2
        assert total <= 2
    
    def test_topic_status_updates(self, monkeypatch, db_conn, sample_site, sample_plan):
        """Test that topic status is updated correctly."""
        monkeypatch.setattr("config.DRY_RUN", True)
        monkeypatch.setattr("content_generator.DRY_RUN", True)
        monkeypatch.setattr("wp_publisher.DRY_RUN", True)
        
        # Get a topic to process
        topics = get_pending_topics(sample_site, limit=1)
        topic_id = topics[0]["id"]
        
        # Run cycle
        run_automation_cycle(sample_site)
        
        # Check topic status
        topic = get_topic(topic_id)
        
        # Should be updated from 'pending'
        assert topic["status"] in ("draft", "content_generated")
        assert topic["wp_post_id"] is not None
    
    def test_failed_topic_handling(self, monkeypatch, db_conn, sample_site, sample_plan):
        """Test handling of failed content generation."""
        monkeypatch.setattr("config.DRY_RUN", True)
        monkeypatch.setattr("content_generator.DRY_RUN", True)
        monkeypatch.setattr("wp_publisher.DRY_RUN", True)
        
        # Make content generation fail by patching in scheduler's namespace
        def mock_generate_fail(*args, **kwargs):
            raise Exception("LLM API Error")
        
        monkeypatch.setattr("scheduler.generate_post_content", mock_generate_fail)
        
        # Run cycle
        processed = run_automation_cycle(sample_site)
        
        # Topics should be marked as failed or pending with attempts
        topics = get_pending_topics(sample_site)
        # After 3 attempts, they'd be 'failed'
        # This test just ensures error handling doesn't crash
        assert processed == 0  # No topics successfully processed
