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
        """Test that mock content returns required keys for any pillar."""
        comparison_topic = {"title": "Compare Apps", "pillar": "vs_comparison"}
        howto_topic = {"title": "Build App", "pillar": "how_to", "target_keywords": ["build app"]}

        for topic in (comparison_topic, howto_topic):
            result = _get_mock_content(topic)
            for key in ("tldr", "content", "faq", "meta_description", "focus_keyword", "seo_title", "schema_type"):
                assert key in result, f"Missing key '{key}' for pillar {topic['pillar']}"
            assert len(result["content"]) > 0
    
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
        
        for key in ("tldr", "content", "faq", "meta_description", "focus_keyword", "seo_title", "schema_type"):
            assert key in result

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
