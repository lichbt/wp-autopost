import pytest
from content_generator import generate_post_content, _get_mock_content


class TestContentGenerator:
    """Test content generation functionality."""
    
    def test_mock_content_structure(self):
        """Test that mock content has correct structure."""
        topic = {
            "title": "Best Dating Apps",
            "pillar": "Comparisons",
            "target_keywords": ["dating apps", "best apps"]
        }
        
        content = _get_mock_content(topic)
        
        assert "tldr" in content
        assert "content" in content
        assert "faq" in content
        assert "meta_description" in content
        
        # Verify content is non-empty
        assert len(content["tldr"]) > 0
        assert len(content["content"]) > 0
        assert len(content["faq"]) > 0
        assert len(content["meta_description"]) > 0
    
    def test_mock_content_by_pillar(self):
        """Test that different pillars produce different content."""
        comparison_topic = {"title": "Compare Apps", "pillar": "Comparisons"}
        howto_topic = {"title": "Build App", "pillar": "How-To"}
        
        comparison = _get_mock_content(comparison_topic)
        howto = _get_mock_content(howto_topic)
        
        # Content should be different for different pillars
        assert comparison["content"] != howto["content"]
        
        # Comparisons should have a table
        assert "<table>" in comparison["content"]
        
        # How-To should have numbered steps
        assert "Step 1" in howto["content"] or "step 1" in howto["content"].lower()
    
    def test_generate_post_content_dry_run(self, monkeypatch):
        """Test content generation in dry-run mode."""
        monkeypatch.setattr("content_generator.DRY_RUN", True)
        
        topic = {
            "title": "Test Topic",
            "pillar": "How-To",
            "target_keywords": ["test"],
            "special_instructions": None
        }
        site = {"blog_template": "<div>{{content}}</div>"}
        plan_context = {
            "default_pillar_template_hints": {"How-To": "Numbered steps"}
        }
        
        result = generate_post_content(topic, site, plan_context)
        
        assert "tldr" in result
        assert "content" in result
        assert "faq" in result
        assert "meta_description" in result
    
    def test_generate_with_special_instructions(self, monkeypatch):
        """Test generation with special instructions."""
        monkeypatch.setattr("content_generator.DRY_RUN", True)
        
        topic = {
            "title": "Custom Topic",
            "pillar": "General",
            "target_keywords": ["custom"],
            "special_instructions": "Include a pricing table"
        }
        site = {}
        plan_context = {}
        
        result = generate_post_content(topic, site, plan_context)
        
        # Should still return valid content
        assert len(result["tldr"]) > 0
