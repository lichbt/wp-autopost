"""
Tests for Feature 4 — data-driven template proposals (content_strategist).

The claude CLI call and the templates dir are mocked, so these run offline and
never touch the real templates/ directory.
"""
import json
import pytest

import content_strategist as cs


class TestParseProposalsJson:
    def test_plain_object(self):
        raw = json.dumps({"proposals": [{"name": "x", "markdown": "# x"}]})
        out = cs._parse_proposals_json(raw)
        assert out == [{"name": "x", "markdown": "# x"}]

    def test_bare_list(self):
        raw = json.dumps([{"name": "x"}])
        assert cs._parse_proposals_json(raw) == [{"name": "x"}]

    def test_code_fenced(self):
        raw = "Here you go:\n```json\n{\"proposals\": [{\"name\": \"y\"}]}\n```\n"
        assert cs._parse_proposals_json(raw) == [{"name": "y"}]

    def test_garbage_returns_empty(self):
        assert cs._parse_proposals_json("not json at all") == []


class TestSuggestTemplates:
    def test_skips_when_no_scored_articles(self, monkeypatch):
        monkeypatch.setattr(cs, "get_top_and_bottom_performers",
                            lambda site_id, n=10: {"top": [], "bottom": []})
        result = cs.suggest_templates(site_id=1)
        assert result["proposals"] == []
        assert "No scored articles" in result["skipped"]

    def test_cli_failure_raises_runtimeerror(self, monkeypatch):
        monkeypatch.setattr(cs, "get_top_and_bottom_performers",
                            lambda site_id, n=10: {"top": [{"title": "T", "pillar": "how_to",
                                                            "performance_score": 90}], "bottom": []})
        monkeypatch.setattr(cs, "get_pillar_performance", lambda site_id, days=60: [])
        def _boom(*a, **k):
            raise cs.__dict__.get("ClaudeCLIError", RuntimeError)("cli down")
        monkeypatch.setattr(cs, "claude_complete", _boom)
        with pytest.raises(RuntimeError):
            cs.suggest_templates(site_id=1)

    def test_writes_proposals_and_dedups(self, monkeypatch, tmp_path):
        # Point the templates dir at a temp location with one existing template.
        import content_generator as cg
        (tmp_path / "how_to.md").write_text("# How-To\n## Steps\n", encoding="utf-8")
        monkeypatch.setattr(cg, "TEMPLATES_DIR", tmp_path)

        monkeypatch.setattr(cs, "get_top_and_bottom_performers",
                            lambda site_id, n=10: {"top": [{"title": "T", "pillar": "how_to",
                                                            "performance_score": 90}], "bottom": []})
        monkeypatch.setattr(cs, "get_pillar_performance", lambda site_id, days=60: [])

        # LLM returns: one valid new template, one duplicate of existing, one invalid (no markdown)
        payload = json.dumps({"proposals": [
            {"name": "Migration Guide", "when_to_use": "moving platforms",
             "rationale": "high-scoring how-tos about migration", "markdown": "# Migration\n## TL;DR\n## FAQ\n"},
            {"name": "how_to", "when_to_use": "dup", "rationale": "dup", "markdown": "# dup"},
            {"name": "broken", "when_to_use": "x", "rationale": "x", "markdown": ""},
        ]})
        monkeypatch.setattr(cs, "claude_complete", lambda *a, **k: payload)

        result = cs.suggest_templates(site_id=1, max_proposals=3)

        names = [p["name"] for p in result["proposals"]]
        assert names == ["migration_guide"]          # slugified; dup + empty dropped
        proposed_dir = tmp_path / "proposed"
        assert (proposed_dir / "migration_guide.md").exists()
        assert not (proposed_dir / "how_to.md").exists()   # duplicate not written
        # proposal carries the review header and the markdown body
        body = (proposed_dir / "migration_guide.md").read_text(encoding="utf-8")
        assert "PROPOSED TEMPLATE" in body
        assert "# Migration" in body

    def test_inactive_until_moved(self, monkeypatch, tmp_path):
        """A proposal in templates/proposed/ must NOT be picked up as an active template."""
        import content_generator as cg
        monkeypatch.setattr(cg, "TEMPLATES_DIR", tmp_path)
        (tmp_path / "proposed").mkdir()
        (tmp_path / "proposed" / "migration_guide.md").write_text("# x", encoding="utf-8")
        # available_template_stems globs only the top level → proposal not visible
        assert "migration_guide" not in cg.available_template_stems()
