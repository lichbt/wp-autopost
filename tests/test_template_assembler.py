import pytest
from template_assembler import assemble_final_html, _build_faq_schema


class TestFaqSchema:
    """FAQ JSON-LD must be valid AND survive wp-admin re-saves."""

    def test_faq_schema_is_wp_html_wrapped(self):
        """Bare <script> gets stripped on editor re-save → invalid FAQPage.
        The schema must be wrapped in a Gutenberg wp:html block."""
        faq = ('<div class="faq-item"><h3>What is it?</h3><p>An answer.</p></div>'
               '<div class="faq-item"><h3>How much?</h3><p>$149 one-time.</p></div>')
        out = _build_faq_schema(faq)
        assert out.startswith("<!-- wp:html -->")
        assert out.rstrip().endswith("<!-- /wp:html -->")
        assert '"@type": "FAQPage"' in out
        assert out.count('"@type": "Question"') == 2
        assert '"acceptedAnswer"' in out

    def test_faq_schema_empty_when_no_items(self):
        assert _build_faq_schema("") == ""
        assert _build_faq_schema("<p>no questions here</p>") == ""


class TestTemplateAssembler:
    """Test HTML template assembly."""
    
    def test_basic_assembly(self):
        """Test basic template assembly with all placeholders."""
        site = {
            "blog_template": """<article>
<h1>{{title}}</h1>
<p>{{tldr}}</p>
<div>{{content}}</div>
<div>{{faq}}</div>
<meta name="description" content="{{meta_description}}">
<a href="{{cta_link}}">{{cta_text}}</a>
</article>"""
        }
        
        result = assemble_final_html(
            site=site,
            title="Test Title",
            tldr="Test TLDR",
            content="<p>Body content</p>",
            faq="<div>FAQ</div>",
            meta_description="Test meta",
            cta_link="/pricing",
            cta_text="View Pricing"
        )
        
        assert "Test Title" in result
        assert "Test TLDR" in result
        assert "<p>Body content</p>" in result
        assert "<div>FAQ</div>" in result
        assert "Test meta" in result
        assert "/pricing" in result
        assert "View Pricing" in result
    
    def test_html_escaping(self):
        """Test that title is HTML escaped."""
        site = {"blog_template": "<h1>{{title}}</h1>"}
        
        result = assemble_final_html(
            site=site,
            title="Test <script>alert('xss')</script>",
            tldr="",
            content="",
            faq="",
            meta_description=""
        )
        
        # Title should be escaped
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    def test_missing_template_uses_default(self):
        """Test fallback to default template when site has none."""
        site = {}
        
        result = assemble_final_html(
            site=site,
            title="Test",
            tldr="TLDR",
            content="Content",
            faq="FAQ",
            meta_description="Meta"
        )
        
        assert "Test" in result
        assert "TLDR" in result
        assert "Content" in result
    
    def test_default_cta_values(self):
        """Test that CTA placeholders are always replaced (no unreplaced {{...}} left)."""
        site = {"blog_template": "<a href='{{cta_link}}'>{{cta_text}}</a>"}

        result = assemble_final_html(
            site=site,
            title="Test",
            tldr="",
            content="",
            faq="",
            meta_description=""
        )

        assert "{{cta_link}}" not in result
        assert "{{cta_text}}" not in result
        assert "<a href=" in result
    
    def test_empty_content_fields(self):
        """Test assembly with empty content fields."""
        site = {"blog_template": "{{title}}|{{tldr}}|{{content}}|{{faq}}"}
        
        result = assemble_final_html(
            site=site,
            title="Title",
            tldr=None,
            content=None,
            faq=None,
            meta_description=""
        )
        
        # Should not raise error
        assert "Title" in result
