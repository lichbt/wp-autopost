import pytest
from template_assembler import assemble_final_html


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
        """Test default CTA values."""
        site = {"blog_template": "<a href='{{cta_link}}'>{{cta_text}}</a>"}
        
        result = assemble_final_html(
            site=site,
            title="Test",
            tldr="",
            content="",
            faq="",
            meta_description=""
        )
        
        assert "/demo" in result
        assert "Try Demo" in result
    
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
