"""Tests for find_plan_duplicates — block proposed topics that duplicate existing DB/live content."""
import pytest
import wp_sync
from database import add_plan, add_topics_bulk

EXISTING = [
    {"title": "What is White-Label Dating Software?", "slug": "what-is-white-label-dating-software", "pillar": "definition"},
    {"title": "What are the best niche dating app ideas in 2026", "slug": "best-niche-dating-app-ideas-2026", "pillar": "best_of"},
    {"title": "ShaunSocial vs Sngine: Which Social Network Script Is Better", "slug": "shaunsocial-vs-sngine", "pillar": "vs_comparison"},
]

def _seed(site_id):
    plan_id = add_plan(site_id, "raw", None)
    add_topics_bulk(site_id, plan_id, EXISTING)


def test_flags_near_identical_and_subset(db_conn, sample_site):
    _seed(sample_site)
    proposed = [
        {"title": "What is White-Label Dating Software? The Complete Guide for 2026", "slug": "x1"},  # dup #1 (jaccard)
        {"title": "10 Profitable Niche Dating App Ideas for 2026", "slug": "x2"},                      # dup #2 (overlap)
        {"title": "ShaunSocial vs phpSocial: Which PHP Social Network Script Is Better", "slug": "x3"},# distinct competitor → unique
        {"title": "How to Build a Senior Dating Site", "slug": "x4"},                                  # unique
    ]
    res = wp_sync.find_plan_duplicates(sample_site, proposed, include_live=False)
    dup_titles = {d["title"] for d in res["duplicates"]}
    uniq_titles = {(p["title"]) for p in res["unique"]}

    assert "What is White-Label Dating Software? The Complete Guide for 2026" in dup_titles
    assert "10 Profitable Niche Dating App Ideas for 2026" in dup_titles
    # "vs phpSocial" must NOT be flagged as a dup of "vs Sngine"
    assert "ShaunSocial vs phpSocial: Which PHP Social Network Script Is Better" in uniq_titles
    assert "How to Build a Senior Dating Site" in uniq_titles
    assert len(res["duplicates"]) == 2 and len(res["unique"]) == 2


def test_exact_slug_match_is_duplicate(db_conn, sample_site):
    _seed(sample_site)
    proposed = [{"title": "Totally different headline here", "slug": "shaunsocial-vs-sngine"}]  # slug collision
    res = wp_sync.find_plan_duplicates(sample_site, proposed, include_live=False)
    assert len(res["duplicates"]) == 1
    assert res["duplicates"][0]["via"] == "slug"


def test_string_items_supported(db_conn, sample_site):
    _seed(sample_site)
    res = wp_sync.find_plan_duplicates(
        sample_site, ["What is White-Label Dating Software?", "Brand new unrelated topic about pricing models"],
        include_live=False)
    assert len(res["duplicates"]) == 1   # the white-label one
    assert res["unique"] == ["Brand new unrelated topic about pricing models"]


def test_no_existing_all_unique(db_conn, sample_site):
    res = wp_sync.find_plan_duplicates(sample_site, [{"title": "Anything", "slug": "a"}], include_live=False)
    assert res["duplicates"] == [] and len(res["unique"]) == 1


def test_unpublished_draft_counts_as_candidate(db_conn, sample_site, monkeypatch):
    """A live WP *draft* (not yet published) must still block a duplicate proposal."""
    monkeypatch.setattr(wp_sync, "get_site", lambda sid: {"wp_url": "https://x", "wp_username": "u", "wp_app_password": "p"})
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site, statuses="publish": [
        {"id": 1, "title": "Social Network PHP Script: Best Options in 2026", "slug": "social-network-php-script", "status": "draft"},
    ])
    proposed = [
        {"title": "Best Social Network PHP Scripts to Use in 2026", "slug": "p1"},  # dup of the DRAFT
        {"title": "How to Moderate User-Generated Content", "slug": "p2"},          # unique
    ]
    res = wp_sync.find_plan_duplicates(sample_site, proposed, include_live=True)
    dups = {d["title"]: d for d in res["duplicates"]}
    assert "Best Social Network PHP Scripts to Use in 2026" in dups
    assert dups["Best Social Network PHP Scripts to Use in 2026"]["source"] == "live:draft"
    assert res["unique"] == [proposed[1]]
