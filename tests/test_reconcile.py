"""Tests for wp_sync.reconcile_pending_against_live (plan↔live self-heal)."""
import pytest

import wp_sync
from database import add_plan, add_topics_bulk, get_db_connection

LIVE = [
    {"id": 900, "title": "Launch Guide for X",                "slug": "launch-guide-x",  "link": ""},
    {"id": 901, "title": "Best WoWonder Alternative in 2026", "slug": "best-wowonder-alternative-2026", "link": ""},
    {"id": 902, "title": "Cloud Hosting Plans",               "slug": "cloud-hosting-plans", "link": ""},
    {"id": 903, "title": "ShaunSocial vs Sngine Comparison",  "slug": "shaunsocial-vs-sngine", "link": ""},
]


def _seed_pending(site_id):
    plan_id = add_plan(site_id, "raw", None)
    add_topics_bulk(site_id, plan_id, [
        {"title": "Totally Different Heading", "slug": "launch-guide-x"},          # slug match → 900
        {"title": "Best WoWonder Alternative", "slug": "my-wowonder-post"},        # title match → 901
        {"title": "Cloud Hosting Pricing",     "slug": "cloud-pricing"},           # medium → review (902)
        {"title": "ShaunSocial vs phpSocial",  "slug": "vs-phpsocial"},            # different entity → new
    ])


def _status(site_id):
    c = get_db_connection()
    return {r["slug"]: dict(r) for r in c.execute(
        "SELECT slug,status,wp_post_id,title FROM topics WHERE site_id=?", (site_id,))}


def test_auto_publishes_confident_leaves_rest(db_conn, sample_site, monkeypatch):
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site: LIVE)
    _seed_pending(sample_site)

    res = wp_sync.reconcile_pending_against_live(sample_site, apply=True)

    assert res["checked"] == 4
    assert len(res["published"]) == 2          # slug-match + title-match
    assert len(res["review"]) == 1             # cloud pricing ~ cloud plans

    st = _status(sample_site)
    # slug match → published + linked to 900
    by_title = {v["title"]: v for v in st.values()}
    assert by_title["Totally Different Heading"]["status"] == "published"
    assert by_title["Totally Different Heading"]["wp_post_id"] == 900
    # title match → published + linked to 901
    assert by_title["Best WoWonder Alternative"]["status"] == "published"
    assert by_title["Best WoWonder Alternative"]["wp_post_id"] == 901
    # medium → still pending (review only)
    assert by_title["Cloud Hosting Pricing"]["status"] == "pending"
    # different entity → still pending (new)
    assert by_title["ShaunSocial vs phpSocial"]["status"] == "pending"


def test_dry_run_changes_nothing(db_conn, sample_site, monkeypatch):
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site: LIVE)
    _seed_pending(sample_site)

    res = wp_sync.reconcile_pending_against_live(sample_site, apply=False)
    assert len(res["published"]) == 2          # reported...
    st = _status(sample_site)
    assert all(v["status"] == "pending" for v in st.values())  # ...but nothing applied


def test_no_live_posts_safe(db_conn, sample_site, monkeypatch):
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site: [])
    _seed_pending(sample_site)
    res = wp_sync.reconcile_pending_against_live(sample_site, apply=True)
    assert res["published"] == [] and res["review"] == []
    assert all(v["status"] == "pending" for v in _status(sample_site).values())
