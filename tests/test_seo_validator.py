"""Tests for the pre-publish SEO validator (score_html + gate behavior)."""
import seo_validator


def _good_article():
    body = "<h2>Intro to Headless CMS</h2>" + ("<p>" + ("A headless cms decouples content from the front end. " * 40) + "</p>")
    body += "<h2>Benefits</h2><p>" + ("Speed and flexibility and scale all matter a great deal here. " * 40) + "</p>"
    body += "<h2>How to Choose</h2><ul><li>API quality</li><li>Pricing</li><li>Docs</li></ul>"
    body += "<h2>Comparison</h2><table><tr><td>A</td><td>B</td></tr></table><p>" + ("Detail about each option follows below. " * 40) + "</p>"
    faq = ('<div class="faq-item"><h3>What is a headless CMS?</h3><p>A backend-only CMS.</p></div>'
           '<div class="faq-item"><h3>Is it worth it?</h3><p>Often yes.</p></div>')
    return body, faq


def test_good_article_passes():
    body, faq = _good_article()
    v = seo_validator.score_html(
        title="What Is a Headless CMS? A Practical 2026 Guide",
        content_html=body, faq_html=faq,
        meta_description="A headless CMS decouples content from presentation. Learn what it is, "
                         "the benefits, and how to choose one in 2026 with this practical guide.",
        focus_keyword="headless cms",
    )
    assert v["passed"] is True
    assert v["score"] >= 70
    assert v["word_count"] >= 800


def test_thin_article_fails_with_findings():
    v = seo_validator.score_html(
        title="x",                     # too short, no keyword
        content_html="<p>Short.</p>",  # ~1 word, no H2
        faq_html="",
        meta_description="too short",
        focus_keyword="headless cms",
    )
    assert v["passed"] is False
    assert v["score"] < 70
    checks = {f["check"] for f in v["findings"]}
    # the obvious failures should be flagged
    assert {"word_count", "h2_sections", "keyword_in_title", "faq_section"} <= checks


def test_findings_have_shape():
    v = seo_validator.score_html(title="t", content_html="<p>hi</p>", focus_keyword="x")
    for f in v["findings"]:
        assert set(f) >= {"check", "severity", "points", "detail"}
        assert f["severity"] in ("high", "med", "low")
