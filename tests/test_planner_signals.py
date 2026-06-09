"""Tests for Tier-1 data-driven planner signals (content_strategist) + action fields."""
import pytest
from datetime import date

from database import upsert_gsc_data, add_plan, add_topics_bulk, get_pending_topics
from content_strategist import (
    get_striking_distance,
    get_planner_signals,
    format_planner_signals,
)


def _seed_gsc(site_id):
    today = date.today().isoformat()
    upsert_gsc_data(site_id, today, [
        {"query": "almost there",    "page": "https://x/almost", "clicks": 2,  "impressions": 100, "ctr": 0.02, "position": 12.0},
        {"query": "page two deep",   "page": "https://x/deep",   "clicks": 0,  "impressions": 100, "ctr": 0.0,  "position": 25.0},
        {"query": "already winning", "page": "https://x/win",    "clicks": 30, "impressions": 100, "ctr": 0.3,  "position": 3.0},
        {"query": "too few impr",    "page": "https://x/low",    "clicks": 0,  "impressions": 5,   "ctr": 0.0,  "position": 12.0},
    ])


class TestStrikingDistance:
    def test_only_returns_edge_of_page1(self, db_conn, sample_site):
        _seed_gsc(sample_site)
        sd = get_striking_distance(sample_site)
        queries = {r["query"] for r in sd}
        assert queries == {"almost there"}            # pos 8-20 AND impressions>=30
        row = sd[0]
        assert row["position"] == 12.0
        assert row["impressions"] == 100
        assert row["top_page"] == "https://x/almost"   # best-ranking page surfaced

    def test_empty_when_no_gsc(self, db_conn, sample_site):
        assert get_striking_distance(sample_site) == []


class TestFormatSignals:
    def test_empty_signals_blank(self):
        assert format_planner_signals(
            {"striking_distance": [], "pillar_performance": [], "performers": {}, "trends": {}}
        ) == ""

    def test_renders_striking_and_refresh_hint(self):
        sig = {
            "striking_distance": [
                {"query": "almost there", "position": 12.0, "impressions": 100, "top_page": "https://x/almost"},
                {"query": "fresh angle",  "position": 15.0, "impressions": 60,  "top_page": ""},
            ],
            "pillar_performance": [{"pillar": "best_of", "total_clicks": 50, "avg_ctr": 0.04, "avg_position": 9.0}],
            "performers": {"top": [{"pillar": "best_of", "title": "Top one", "performance_score": 88}], "bottom": []},
            "trends": {"rising": [], "stalling": [{"title": "Old decaying post", "slug": "old-post"}]},
        }
        out = format_planner_signals(sig)
        assert "STRIKING-DISTANCE" in out
        assert "REFRESH: https://x/almost" in out   # existing page → refresh hint
        assert "no strong page → NEW" in out         # missing page → new hint
        assert "DECAYING PAGES" in out and "old-post" in out
        assert "PILLAR PERFORMANCE" in out


class TestActionFields:
    def test_action_and_target_url_round_trip(self, db_conn, sample_site):
        plan_id = add_plan(sample_site, "raw", None)
        add_topics_bulk(sample_site, plan_id, [{
            "title": "Refresh the WoWonder post", "slug": "wowonder-x", "pillar": "best_of",
            "action": "refresh", "target_url": "https://x/best-wowonder-alternative-2026",
        }])
        pend = get_pending_topics(sample_site)
        assert pend[0]["action"] == "refresh"
        assert pend[0]["target_url"] == "https://x/best-wowonder-alternative-2026"

    def test_action_defaults_to_new(self, db_conn, sample_site):
        plan_id = add_plan(sample_site, "raw", None)
        add_topics_bulk(sample_site, plan_id, [{"title": "Plain new topic", "slug": "plain", "pillar": "how_to"}])
        pend = get_pending_topics(sample_site)
        assert pend[0]["action"] == "new"
