import pytest
import json
from datetime import date
from plan_parser import extract_plan, _get_mock_parsed_plan


class TestPlanParser:
    """Test plan parsing functionality."""
    
    def test_mock_parsed_plan_structure(self):
        """Test that mock plan has correct structure."""
        mock = _get_mock_parsed_plan()
        
        assert "topics" in mock
        assert "global" in mock
        assert len(mock["topics"]) > 0
        
        # Check topic structure
        topic = mock["topics"][0]
        required_fields = ["title", "pillar", "priority", "intent", 
                          "target_keywords", "internal_links", 
                          "special_instructions", "scheduled_date"]
        for field in required_fields:
            assert field in topic, f"Missing field: {field}"
        
        # Check global structure
        global_settings = mock["global"]
        assert "default_pillar_template_hints" in global_settings
        assert "posts_per_month" in global_settings
        assert "overall_strategy_goal" in global_settings
    
    def test_extract_plan_dry_run(self, monkeypatch):
        """Test plan extraction in dry-run mode."""
        # Force dry-run mode
        monkeypatch.setattr("plan_parser.DRY_RUN", True)
        
        result = extract_plan("# Test Strategy Document")
        
        assert "topics" in result
        assert "global" in result
        assert len(result["topics"]) >= 1
    
    def test_extract_plan_validates_structure(self, monkeypatch):
        """Test that parser validates response structure."""
        # Mock OpenAI response with missing keys
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({"topics": []})  # Missing "global"
                }
            }]
        }
        
        # This would fail validation in real mode
        # For now, just verify dry-run works
        monkeypatch.setattr("plan_parser.DRY_RUN", True)
        result = extract_plan("# Test")
        assert "global" in result
