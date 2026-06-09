"""Tests for the Nano-Banana-2 image prompt builder (image_handler)."""
import pytest
import image_handler as ih


@pytest.fixture(autouse=True)
def _cli_available(monkeypatch):
    monkeypatch.setattr(ih, "CLAUDE_CLI_AVAILABLE", True)


def test_guide_loads():
    g = ih._load_image_guide()
    assert "Nano Banana" in g
    assert "16:9" in g


def test_build_prompt_uses_guide_and_drops_keyword_soup(monkeypatch):
    rich = ("A professional editorial photograph of two smartphones side by side under soft "
            "studio light, shot on a 50mm lens at f/2.8, warm coral-and-teal palette. "
            "16:9 widescreen, with clean negative space for a headline overlay.")
    monkeypatch.setattr(ih, "claude_complete", lambda *a, **k: rich)
    out = ih._build_image_prompt(
        {"title": "Best PHP Dating Scripts 2026", "pillar": "best_of"},
        {"niche": "dating software", "name": "MooDatingScript"},
    )
    assert out == rich
    # legacy Midjourney-style suffix must NOT be appended on the LLM path
    assert "ultra-realistic" not in out
    assert "4K" not in out


def test_guide_passed_as_system_prompt(monkeypatch):
    captured = {}
    def _cap(user, system=None, **k):
        captured["system"] = system
        captured["user"] = user
        return ("A professional editorial photograph of a tidy developer desk with soft window "
                "light. 16:9 widescreen, with clean negative space for a headline overlay.")
    monkeypatch.setattr(ih, "claude_complete", _cap)
    ih._build_image_prompt({"title": "How to Build X", "pillar": "how_to"}, {"niche": "dating"})
    assert "Nano Banana" in captured["system"]      # the guide is the system prompt
    assert 'Article title: "How to Build X"' in captured["user"]
    assert "Content type: how_to" in captured["user"]


def test_short_output_falls_back_to_template(monkeypatch):
    monkeypatch.setattr(ih, "claude_complete", lambda *a, **k: "tiny")
    out = ih._build_image_prompt({"title": "X", "pillar": "best_of"}, {"niche": "dating"})
    assert "no text" in out          # fallback template
    assert "ultra-realistic" in out  # fallback still uses the quality suffix


def test_llm_error_falls_back(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("cli down")
    monkeypatch.setattr(ih, "claude_complete", _boom)
    out = ih._build_image_prompt({"title": "X", "pillar": "how_to"}, {"niche": "social"})
    assert len(out) > 20


def test_fallback_prompt_templates_exist():
    out = ih._fallback_prompt("vs_comparison", {"niche": "dating"})
    assert "no text" in out and len(out) > 30
