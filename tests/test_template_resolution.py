"""
Unit tests for template resolution (content_generator.resolve_template_name).

Guards the bug fix where planner pillars best_of / buyer_guide / setup_tutorial /
use_case / feature_explainer silently fell back to (or mis-mapped away from)
their own templates.
"""
import pytest

from content_generator import (
    resolve_template_name,
    _slugify_pillar,
    available_template_stems,
    DEFAULT_TEMPLATE,
)

# The 9 pillars the planner (site_analyst) can emit.
PLANNER_PILLARS = [
    "vs_comparison", "best_of", "buyer_guide", "setup_tutorial",
    "feature_explainer", "use_case", "how_to", "definition", "cost_roi",
]


class TestSlugify:
    @pytest.mark.parametrize("raw,expected", [
        ("How-To", "how_to"),
        ("How To", "how_to"),
        ("vs_comparison", "vs_comparison"),
        ("Cost & ROI", "cost_roi"),
        ("  Best  Of ", "best_of"),
        ("feature/explainer", "feature_explainer"),
    ])
    def test_slugify(self, raw, expected):
        assert _slugify_pillar(raw) == expected

    def test_empty(self):
        assert _slugify_pillar("") == ""
        assert _slugify_pillar(None) == ""


class TestResolveTemplateName:
    def test_every_planner_pillar_has_its_own_template(self):
        """Each pillar must resolve to a real, matching template file — not a fallback."""
        stems = set(available_template_stems())
        for pillar in PLANNER_PILLARS:
            resolved = resolve_template_name(pillar)
            assert resolved.endswith(".md")
            # the file must exist on disk
            assert resolved[:-3] in stems, f"{pillar} resolved to missing {resolved}"

    @pytest.mark.parametrize("pillar,expected", [
        ("best_of", "best_of.md"),            # previously fell back to how_to
        ("buyer_guide", "buyer_guide.md"),    # previously fell back to how_to
        ("setup_tutorial", "setup_tutorial.md"),  # previously fell back to how_to
        ("use_case", "use_case.md"),          # previously fell back to how_to
        ("feature_explainer", "feature_explainer.md"),  # previously mis-mapped to definition
        ("how_to", "how_to.md"),
        ("definition", "definition.md"),
        ("cost_roi", "cost_roi.md"),
    ])
    def test_regression_previously_broken_pillars(self, pillar, expected):
        assert resolve_template_name(pillar) == expected

    @pytest.mark.parametrize("loose,expected", [
        ("How-To", "how_to.md"),
        ("Comparison", "comparison.md"),       # direct file match wins (comparison.md exists)
        ("comparisons", "vs_comparison.md"),   # plural has no file → alias to vs_comparison
        ("explainer", "feature_explainer.md"),
        ("pricing", "cost_roi.md"),
        ("Cost & ROI", "cost_roi.md"),
        ("listicle", "best_of.md"),
        ("buying guide", "buyer_guide.md"),
    ])
    def test_aliases(self, loose, expected):
        assert resolve_template_name(loose) == expected

    def test_unknown_pillar_falls_back_to_default(self):
        assert resolve_template_name("totally_made_up_pillar_xyz") == DEFAULT_TEMPLATE

    def test_empty_pillar_falls_back_to_default(self):
        assert resolve_template_name("") == DEFAULT_TEMPLATE
        assert resolve_template_name(None) == DEFAULT_TEMPLATE

    def test_override_wins_over_pillar(self):
        # pillar would be how_to, but override picks best_of
        assert resolve_template_name("how_to", override="best_of") == "best_of.md"

    def test_override_falls_through_to_pillar_when_invalid(self):
        # bogus override → fall back to the pillar's own template
        assert resolve_template_name("definition", override="nonexistent_xyz") == "definition.md"
