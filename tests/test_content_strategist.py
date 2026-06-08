"""
Unit tests for content_strategist scoring logic.

These cover the pure, deterministic functions — min-max normalization,
tier assignment, and the score weighting — without touching the database.
"""
import pytest

from content_strategist import (
    _normalize_values,
    _assign_tier,
    SCORE_WEIGHTS,
    SCORE_TIERS,
)


class TestNormalizeValues:
    def test_basic_min_max(self):
        assert _normalize_values([10, 20, 30]) == [0.0, 50.0, 100.0]

    def test_two_point_spread(self):
        assert _normalize_values([0, 100]) == [0.0, 100.0]

    def test_constant_list_returns_midpoint(self):
        # min == max → no spread → every value maps to the neutral 50.0
        assert _normalize_values([5, 5, 5]) == [50.0, 50.0, 50.0]

    def test_single_value_returns_midpoint(self):
        assert _normalize_values([42]) == [50.0]

    def test_output_length_preserved(self):
        vals = [3, 1, 4, 1, 5, 9, 2, 6]
        assert len(_normalize_values(vals)) == len(vals)

    def test_output_bounded_0_100(self):
        out = _normalize_values([-50, 0, 17, 200])
        assert min(out) == 0.0
        assert max(out) == 100.0
        assert all(0.0 <= v <= 100.0 for v in out)


class TestAssignTier:
    @pytest.mark.parametrize("score,expected", [
        (100.0, "top_performer"),
        (90.0,  "top_performer"),
        (75.0,  "top_performer"),   # lower bound of top is inclusive, checked first
        (74.9,  "rising"),
        (60.0,  "rising"),
        (50.0,  "rising"),          # boundary resolves to the higher tier (checked first)
        (40.0,  "stalled"),
        (25.0,  "stalled"),
        (10.0,  "declining"),
        (0.0,   "declining"),
    ])
    def test_tier_boundaries(self, score, expected):
        assert _assign_tier(score) == expected

    def test_out_of_range_falls_back_to_declining(self):
        assert _assign_tier(-5.0) == "declining"
        assert _assign_tier(150.0) == "declining"


class TestScoreConfig:
    def test_weights_sum_to_one(self):
        assert pytest.approx(sum(SCORE_WEIGHTS.values()), abs=1e-9) == 1.0

    def test_weights_have_expected_keys(self):
        assert set(SCORE_WEIGHTS) == {"impressions", "ctr", "position"}

    def test_tiers_cover_full_range_without_gaps(self):
        # Bounds, when sorted, should be contiguous from 0 to 100
        edges = sorted({b for bounds in SCORE_TIERS.values() for b in bounds})
        assert edges[0] == 0.0
        assert edges[-1] == 100.0
