import pytest
from content_generator import (
    generate_post_content,
    _get_mock_content,
    get_persona_for_topic,
    build_system_prompt,
    WRITING_PERSONAS,
    CONTENT_SYSTEM_PROMPT,
)


class TestWritingPersonas:
    """Persona rotation must be deterministic and cover every topic id."""

    def test_six_personas_defined(self):
        assert len(WRITING_PERSONAS) == 6
        # each persona has the fields the rest of the code relies on
        for p in WRITING_PERSONAS:
            assert p["name"]
            assert p["system_addon"]

    def test_rotation_is_deterministic(self):
        # same id → same persona, always
        assert get_persona_for_topic(7) == get_persona_for_topic(7)

    def test_rotation_cycles_by_modulo(self):
        # ids 0..5 map to the six distinct personas in order
        names = [get_persona_for_topic(i)["name"] for i in range(6)]
        assert names == [p["name"] for p in WRITING_PERSONAS]
        assert len(set(names)) == 6

    def test_rotation_wraps_around(self):
        # id 6 wraps back to the first persona
        assert get_persona_for_topic(6) == get_persona_for_topic(0)
        assert get_persona_for_topic(13) == get_persona_for_topic(1)

    def test_build_system_prompt_includes_base_and_addon(self):
        persona = get_persona_for_topic(0)
        prompt = build_system_prompt(persona)
        assert CONTENT_SYSTEM_PROMPT in prompt
        assert persona["system_addon"] in prompt

    def test_mock_content_persona_matches_topic_id(self):
        result = _get_mock_content({"title": "X", "pillar": "General", "id": 3})
        assert result["writing_persona"] == get_persona_for_topic(3)["name"]


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
            for key in ("tldr", "content", "faq", "meta_description", "meta_title", "focus_keyword"):
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
        
        for key in ("tldr", "content", "faq", "meta_description", "meta_title", "focus_keyword"):
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
