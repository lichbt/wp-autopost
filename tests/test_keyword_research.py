"""Tests for Tier-3 keyword research: Serper primary + free autocomplete fallback (network mocked)."""
import json
import pytest
import keyword_research as kr

FAKE_SERP = {
    "relatedSearches": [{"query": "wowonder alternative free"},
                        {"query": "best wowonder alternative"}],
    "peopleAlsoAsk": [{"question": "Is WoWonder still supported?"}],
    "aiOverview": {"present": True},
}


class _Resp:
    def __init__(self, data=None, text=None, code=200):
        self._d = data
        self.text = text if text is not None else json.dumps(data)
        self.status_code = code
    def json(self):
        return self._d


# ── Serper layer ──────────────────────────────────────────────────────────────

def test_serper_search_none_without_key(monkeypatch):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "")
    assert kr.serper_available() is False
    assert kr.serper_search("x") is None


def test_extract_parses_serp():
    ex = kr._extract(FAKE_SERP)
    assert "best wowonder alternative" in ex["related"]
    assert ex["paa"] == ["Is WoWonder still supported?"]
    assert ex["ai_overview"] is True


def test_serper_search_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "testkey")
    monkeypatch.setattr(kr, "_CACHE_DIR", tmp_path)
    calls = {"n": 0}
    monkeypatch.setattr(kr.requests, "post",
                        lambda *a, **k: calls.__setitem__("n", calls["n"] + 1) or _Resp(FAKE_SERP))
    assert kr.serper_search("wowonder alternative") == FAKE_SERP
    assert kr.serper_search("wowonder alternative") == FAKE_SERP   # cached
    assert calls["n"] == 1


def test_serper_path_block(monkeypatch):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "testkey")
    monkeypatch.setattr(kr, "serper_search", lambda q, **k: FAKE_SERP)
    res = kr.discover_related_queries(["wowonder alternative"])
    assert res["provider"] == "serper"
    assert "best wowonder alternative" in res["related"]
    assert "wowonder alternative" in res["ai_overview"]
    block = kr.get_keyword_research_block(["wowonder alternative"])
    assert "via Serper SERP" in block
    assert "People Also Ask" in block and "AI Overviews" in block


# ── Free autocomplete fallback ──────────────────────────────────────────────────

def test_google_autocomplete_parses_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(kr, "_CACHE_DIR", tmp_path)
    payload = json.dumps(["wowonder", ["wowonder alternative", "wowonder vs sngine"]])
    calls = {"n": 0}
    monkeypatch.setattr(kr.requests, "get",
                        lambda *a, **k: calls.__setitem__("n", calls["n"] + 1) or _Resp(text=payload))
    out = kr.google_autocomplete("wowonder")
    assert out == ["wowonder alternative", "wowonder vs sngine"]
    kr.google_autocomplete("wowonder")          # cached
    assert calls["n"] == 1


def test_falls_back_to_autocomplete_without_serper(monkeypatch):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "")            # no key → serper unavailable
    monkeypatch.setattr(kr, "google_autocomplete", lambda q, **k: [f"{q} idea"])
    res = kr.discover_related_queries(["best dating script"])
    assert res["provider"] == "autocomplete"
    assert any("best dating script" in r for r in res["related"])

    block = kr.get_keyword_research_block(["best dating script"])
    assert "via Google Autocomplete (free)" in block
    assert "Related / suggested searches" in block
    # autocomplete has no PAA / AI-Overview
    assert "People Also Ask" not in block and "AI Overviews" not in block


def test_block_empty_when_nothing_found(monkeypatch):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "")
    monkeypatch.setattr(kr, "google_autocomplete", lambda q, **k: [])
    assert kr.get_keyword_research_block(["x"]) == ""
