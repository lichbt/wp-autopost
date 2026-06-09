"""Tests for Tier-3 Serper keyword research (network mocked)."""
import pytest
import keyword_research as kr

FAKE = {
    "relatedSearches": [{"query": "wowonder alternative free"},
                        {"query": "best wowonder alternative"}],
    "peopleAlsoAsk": [{"question": "Is WoWonder still supported?"}],
    "aiOverview": {"present": True},
}


class _Resp:
    def __init__(self, data, code=200):
        self._d = data; self.status_code = code
    def json(self):
        return self._d


def test_unavailable_returns_empty(monkeypatch):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "")
    assert kr.serper_available() is False
    assert kr.get_keyword_research_block(["x"]) == ""
    assert kr.serper_search("x") is None


def test_extract_parses_serp():
    ex = kr._extract(FAKE)
    assert "best wowonder alternative" in ex["related"]
    assert ex["paa"] == ["Is WoWonder still supported?"]
    assert ex["ai_overview"] is True


def test_serper_search_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "testkey")
    monkeypatch.setattr(kr, "_CACHE_DIR", tmp_path)
    calls = {"n": 0}
    def _post(*a, **k):
        calls["n"] += 1
        return _Resp(FAKE)
    monkeypatch.setattr(kr.requests, "post", _post)

    d1 = kr.serper_search("wowonder alternative")
    d2 = kr.serper_search("wowonder alternative")   # served from cache
    assert d1 == FAKE and d2 == FAKE
    assert calls["n"] == 1                            # only one network call


def test_discover_and_block(monkeypatch):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "testkey")
    monkeypatch.setattr(kr, "serper_search", lambda q, **k: FAKE)

    res = kr.discover_related_queries(["wowonder alternative"])
    assert "best wowonder alternative" in res["related"]
    assert "wowonder alternative" in res["ai_overview"]

    block = kr.get_keyword_research_block(["wowonder alternative"])
    assert "Related searches" in block
    assert "People Also Ask" in block
    assert "AI Overviews" in block


def test_block_empty_when_no_results(monkeypatch):
    monkeypatch.setattr(kr, "SERPER_API_KEY", "testkey")
    monkeypatch.setattr(kr, "serper_search", lambda q, **k: {"organic": []})
    assert kr.get_keyword_research_block(["x"]) == ""
