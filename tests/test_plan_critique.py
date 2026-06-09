"""Tests for Tier-2: self-critique pass + topic-cluster fields."""
import json
import pytest

import site_analyst as sa
from database import add_plan, add_topics_bulk, get_pending_topics

DRAFT = {"topics": [
    {"title": "A", "pillar": "best_of", "cluster": "x", "is_pillar_page": True},
    {"title": "B", "pillar": "how_to", "cluster": "x", "is_pillar_page": False},
    {"title": "C", "pillar": "how_to", "cluster": "x", "is_pillar_page": False},
], "global": {}}


class TestCritiquePrompt:
    def test_prompt_has_checks_and_context(self):
        p = sa.build_critique_prompt(DRAFT, existing=[], wp_posts=[], planner_signals="SIGS")
        assert "DEDUPE" in p and "CANNIBALISATION" in p
        assert "CLUSTER COHERENCE" in p
        assert "DRAFT PLAN" in p and '"title": "A"' in p
        assert "SIGS" in p


class TestCritiqueRefine:
    def test_returns_refined_plan(self, monkeypatch):
        refined = {"topics": [{"title": "A2"}, {"title": "B2"}, {"title": "C2"}], "global": {}}
        monkeypatch.setattr(sa, "_call_claude", lambda msgs: json.dumps(refined))
        out = sa.critique_and_refine_plan(DRAFT, [], [], "")
        assert [t["title"] for t in out["topics"]] == ["A2", "B2", "C2"]

    def test_falls_back_on_error(self, monkeypatch):
        def _boom(msgs): raise RuntimeError("cli down")
        monkeypatch.setattr(sa, "_call_claude", _boom)
        out = sa.critique_and_refine_plan(DRAFT, [], [], "")
        assert out is DRAFT  # original returned unchanged

    def test_falls_back_when_refined_too_small(self, monkeypatch):
        big = {"topics": [{"title": f"T{i}"} for i in range(8)], "global": {}}
        # critique returns 2 topics vs draft 8 (< half=4) → keep original
        monkeypatch.setattr(sa, "_call_claude",
                            lambda msgs: json.dumps({"topics": [{"title": "x"}, {"title": "y"}], "global": {}}))
        out = sa.critique_and_refine_plan(big, [], [], "")
        assert len(out["topics"]) == 8


class TestClusterFields:
    def test_cluster_round_trip(self, db_conn, sample_site):
        plan_id = add_plan(sample_site, "raw", None)
        add_topics_bulk(sample_site, plan_id, [
            {"title": "Hub", "slug": "hub", "pillar": "best_of",
             "cluster": "wowonder", "is_pillar_page": True},
            {"title": "Support", "slug": "sup", "pillar": "how_to",
             "cluster": "wowonder", "is_pillar_page": False},
        ])
        pend = {t["title"]: t for t in get_pending_topics(sample_site)}
        assert pend["Hub"]["cluster"] == "wowonder"
        assert pend["Hub"]["is_pillar_page"] == 1
        assert pend["Support"]["is_pillar_page"] == 0
