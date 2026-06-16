"""Tests for predefined-cluster injection into the planner prompt (seo-plan bridge)."""
from site_analyst import build_analysis_prompt

_BASE = dict(gsc={}, ga4={}, existing=[], num_topics=10)


def _intake(clusters=None):
    d = {"name": "ShaunSocial", "url": "https://shaunsocial.com",
         "niche": "social network software", "content_pillars": ["vs_comparison", "best_of"]}
    if clusters is not None:
        d["clusters"] = clusters
    return d


def test_predefined_clusters_injected():
    clusters = [
        {"pillar": "Social Network Software", "keyword": "social networking software",
         "spokes": ["white label social network", "php social network script"]},
        {"pillar": "WoWonder Alternatives", "spokes": ["best wowonder alternative"]},
    ]
    p = build_analysis_prompt(_intake(clusters), {}, {}, [], 10)
    assert "build the plan to FILL these" in p   # the injected block header
    assert 'CLUSTER "Social Network Software"' in p
    assert "head keyword: social networking software" in p
    assert "white label social network" in p
    assert 'CLUSTER "WoWonder Alternatives"' in p


def test_no_clusters_no_block():
    p = build_analysis_prompt(_intake(), {}, {}, [], 10)
    assert "build the plan to FILL these" not in p   # no injected block
    # falls back to the generic 3–5 cluster instruction
    assert "3–5 clusters" in p
