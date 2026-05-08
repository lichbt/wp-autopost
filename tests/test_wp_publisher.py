import pytest
from wp_publisher import generate_slug, publish_post


class TestSlugGeneration:
    """Test URL slug generation."""
    
    def test_basic_slug(self):
        """Test basic slug generation."""
        assert generate_slug("Hello World") == "hello-world"
    
    def test_special_characters(self):
        """Test slug with special characters."""
        assert generate_slug("Best Apps (2026)!") == "best-apps-2026"
    
    def test_multiple_spaces(self):
        """Test slug with multiple spaces."""
        assert generate_slug("Hello   World") == "hello-world"
    
    def test_length_limit(self):
        """Test slug length limiting."""
        long_title = "A " * 200  # 400 chars
        slug = generate_slug(long_title)
        assert len(slug) <= 200
        assert not slug.endswith("-")
    
    def test_empty_title(self):
        """Test slug with empty title."""
        assert generate_slug("") == ""
    
    def test_unicode(self):
        """Test slug with unicode characters."""
        result = generate_slug("Héllo Wörld")
        # Unicode chars are normalized by regex, hyphens replace non-ascii
        assert result == "h-llo-w-rld" or result == "hello-world"


class TestPublishPost:
    """Test WordPress publishing."""
    
    def test_dry_run_returns_mock_id(self, monkeypatch):
        """Test that dry-run mode returns mock post ID."""
        monkeypatch.setattr("wp_publisher.DRY_RUN", True)
        
        site = {"wp_url": "https://test.com", "wp_username": "user", "wp_app_password": "pass"}
        
        post_id = publish_post(site, "Test Title", "<p>Content</p>")
        
        assert post_id == 9999
    
    def test_dry_run_logs_action(self, monkeypatch, caplog):
        """Test that dry-run mode logs the action."""
        monkeypatch.setattr("wp_publisher.DRY_RUN", True)
        
        site = {"wp_url": "https://test.com", "wp_username": "user", "wp_app_password": "pass"}
        
        with caplog.at_level("INFO"):
            publish_post(site, "My Post", "<p>Body</p>")
        
        assert "DRY RUN" in caplog.text
        assert "My Post" in caplog.text
