"""Tests for the markdown_export output adapter + platform dispatch."""
import os
import pytest

from markdown_publisher import export_markdown
import publisher


def _site(tmp_path, platform="markdown_export"):
    return {
        "id": 99, "name": "Test MD Site", "platform": platform,
        "content_repo_path": str(tmp_path), "wp_url": "https://example.com",
    }


def test_export_markdown_writes_clean_md(tmp_path):
    site = _site(tmp_path)
    res = export_markdown(
        site,
        slug="my-article",
        content_html="<h2>Intro</h2><p>Hello <strong>world</strong>.</p>",
        faq_html='<div class="faq-item"><h3>Q one?</h3><p>A one.</p></div>',
        title="My Article",
        meta_description="A short description.",
    )
    assert res and res["kind"] == "md"
    assert res["url"] == "https://example.com/my-article"
    path = os.path.join(str(tmp_path), "my-article.md")
    assert os.path.exists(path)
    text = open(path, encoding="utf-8").read()

    # frontmatter
    assert text.startswith("---\n")
    assert 'title: "My Article"' in text
    assert 'slug: "my-article"' in text
    # markdown body, not raw HTML
    assert "## Intro" in text
    assert "**world**" in text
    assert "<p>" not in text and "<h2" not in text
    # FAQ section converted too
    assert "## Frequently Asked Questions" in text
    assert "Q one?" in text and "A one." in text


def test_export_markdown_requires_path_and_slug(tmp_path):
    assert export_markdown({"content_repo_path": None}, slug="x", content_html="<p>y</p>") is None
    assert export_markdown(_site(tmp_path), slug="", content_html="<p>y</p>") is None


def test_is_wordpress_default_and_override():
    assert publisher.is_wordpress({}) is True
    assert publisher.is_wordpress({"platform": "wordpress"}) is True
    assert publisher.is_wordpress({"platform": "markdown_export"}) is False


def test_publish_for_site_routes_markdown(tmp_path):
    site = _site(tmp_path)
    res = publisher.publish_for_site(
        site, title="T", content_html="<p>body</p>", slug="routed", faq_html="")
    assert res["kind"] == "md"
    assert os.path.exists(os.path.join(str(tmp_path), "routed.md"))


def test_publish_for_site_routes_wordpress(monkeypatch):
    import wp_publisher
    captured = {}
    def fake_publish(**kwargs):
        captured.update(kwargs); return 4242
    monkeypatch.setattr(wp_publisher, "publish_post", fake_publish)
    res = publisher.publish_for_site(
        {"platform": "wordpress"}, title="T", content_html="<p>x</p>", slug="s")
    assert res == {"kind": "wp", "id": 4242, "url": None}
    assert captured["title"] == "T" and captured["slug"] == "s"
