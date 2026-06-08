"""
Unit tests for wp_sync.sync_wp_to_db 3-way matching logic.

The WP REST fetch and all database calls are stubbed via monkeypatch so the
test exercises only the create / link / already-synced / error branching.
"""
import pytest

import wp_sync


def _patch_db(monkeypatch, *, wp_ids, slugs, stub_returns=1):
    """Stub out the database + fetch dependencies used by sync_wp_to_db."""
    created, linked = [], []

    monkeypatch.setattr(wp_sync, "get_site", lambda sid: {"id": sid, "wp_url": "https://x"})
    monkeypatch.setattr(wp_sync, "get_or_create_import_plan", lambda sid: 999)
    monkeypatch.setattr(wp_sync, "get_all_topic_wp_ids", lambda sid: set(wp_ids))
    monkeypatch.setattr(wp_sync, "get_all_topic_slugs", lambda sid: set(slugs))

    def fake_stub(site_id, plan_id, title, slug, wp_id):
        created.append(wp_id)
        return stub_returns

    def fake_link(site_id, slug, wp_id):
        linked.append((slug, wp_id))

    monkeypatch.setattr(wp_sync, "import_wp_post_stub", fake_stub)
    monkeypatch.setattr(wp_sync, "link_wp_post_by_slug", fake_link)
    return created, linked


def test_three_way_match(monkeypatch):
    """One already-synced (by wp_id), one linked (by slug), one newly created."""
    posts = [
        {"id": 101, "slug": "already", "title": "Already Synced"},
        {"id": 102, "slug": "by-slug", "title": "Link Me By Slug"},
        {"id": 103, "slug": "brand-new", "title": "Brand New"},
    ]
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site: posts)
    created, linked = _patch_db(monkeypatch, wp_ids={101}, slugs={"already", "by-slug"})

    stats = wp_sync.sync_wp_to_db(site_id=4)

    assert stats == {
        "total_wp": 3, "created": 1, "updated": 1,
        "already_synced": 1, "errors": 0,
    }
    assert created == [103]
    assert linked == [("by-slug", 102)]


def test_missing_id_or_slug_counts_as_error(monkeypatch):
    posts = [
        {"id": None, "slug": "no-id", "title": "No ID"},
        {"id": 200, "slug": "", "title": "No Slug"},
        {"id": 201, "slug": "good", "title": "Good"},
    ]
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site: posts)
    created, linked = _patch_db(monkeypatch, wp_ids=set(), slugs=set())

    stats = wp_sync.sync_wp_to_db(site_id=4)

    assert stats["errors"] == 2
    assert stats["created"] == 1
    assert created == [201]


def test_no_wp_posts_returns_zeroed_stats(monkeypatch):
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site: [])
    monkeypatch.setattr(wp_sync, "get_site", lambda sid: {"id": sid, "wp_url": "https://x"})

    stats = wp_sync.sync_wp_to_db(site_id=4)

    assert stats["total_wp"] == 0
    assert stats["created"] == 0
    assert stats["updated"] == 0


def test_missing_site_returns_error(monkeypatch):
    monkeypatch.setattr(wp_sync, "get_site", lambda sid: None)
    stats = wp_sync.sync_wp_to_db(site_id=12345)
    assert stats["errors"] == 1


def test_stub_dedup_returns_zero_not_counted(monkeypatch):
    """If import_wp_post_stub returns 0 (duplicate), it should not count as created."""
    posts = [{"id": 300, "slug": "dup", "title": "Dup"}]
    monkeypatch.setattr(wp_sync, "fetch_all_wp_posts", lambda site: posts)
    _patch_db(monkeypatch, wp_ids=set(), slugs=set(), stub_returns=0)

    stats = wp_sync.sync_wp_to_db(site_id=4)

    assert stats["created"] == 0
