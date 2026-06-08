"""
Tests for performance-weighted persona selection (content_strategist).

Deterministic epsilon-greedy: exploit the best-scoring persona, explore the
under-sampled ones every Nth topic, and fall back to round-robin rotation until
there is enough scored data.
"""
import pytest

from database import add_plan
from content_strategist import get_persona_performance, select_persona
from content_generator import WRITING_PERSONAS, get_persona_for_topic

NAMES = [p["name"] for p in WRITING_PERSONAS]
# expert_practitioner, journalist, educator, business_strategist, data_analyst, critical_reviewer


def _seed(conn, site_id, plan_id, persona, score, i):
    conn.execute(
        "INSERT INTO topics (site_id, plan_id, title, slug, pillar, status, "
        "writing_persona, performance_score) VALUES (?,?,?,?,?,?,?,?)",
        (site_id, plan_id, f"T-{persona}-{i}", f"t-{persona}-{i}", "how_to",
         "published", persona, score),
    )
    conn.commit()


def _seed_distribution(conn, site_id):
    """data_analyst best (avg 90, n3), educator mid (50, n3), journalist low (30, n2).
    Three personas left with zero samples. Total scored = 8."""
    plan_id = add_plan(site_id, "raw", None)
    for i, s in enumerate((85, 90, 95)):
        _seed(conn, site_id, plan_id, "data_analyst", s, i)
    for i, s in enumerate((45, 50, 55)):
        _seed(conn, site_id, plan_id, "educator", s, i)
    for i, s in enumerate((25, 35)):
        _seed(conn, site_id, plan_id, "journalist", s, i)


class TestPersonaPerformance:
    def test_groups_avg_and_count(self, db_conn, sample_site):
        _seed_distribution(db_conn, sample_site)
        perf = get_persona_performance(sample_site)
        assert perf["data_analyst"] == {"avg_score": 90.0, "count": 3}
        assert perf["educator"]["count"] == 3
        assert perf["journalist"]["count"] == 2
        # personas with no scored articles are absent
        assert "critical_reviewer" not in perf

    def test_min_samples_filter(self, db_conn, sample_site):
        _seed_distribution(db_conn, sample_site)
        perf = get_persona_performance(sample_site, min_samples=3)
        assert set(perf) == {"data_analyst", "educator"}  # journalist has only 2


class TestSelectPersona:
    def test_cold_start_falls_back_to_rotation(self, db_conn, sample_site):
        # Only 3 scored articles (< min_total=8) → rotation.
        plan_id = add_plan(sample_site, "raw", None)
        for i, s in enumerate((80, 60, 40)):
            _seed(db_conn, sample_site, plan_id, "educator", s, i)
        for tid in (0, 1, 7, 13):
            assert select_persona(sample_site, tid) == get_persona_for_topic(tid)

    def test_exploit_picks_best_average(self, db_conn, sample_site):
        _seed_distribution(db_conn, sample_site)
        # Non-explore topics (id % 5 != 0) exploit the best persona: data_analyst.
        for tid in (1, 2, 3, 4, 6):
            assert select_persona(sample_site, tid)["name"] == "data_analyst"

    def test_explore_picks_undersampled(self, db_conn, sample_site):
        _seed_distribution(db_conn, sample_site)
        # Explore topics (id % 5 == 0) rotate through the zero-sample personas
        # in WRITING_PERSONAS order: expert_practitioner, business_strategist, critical_reviewer.
        zero_sample = ["expert_practitioner", "business_strategist", "critical_reviewer"]
        assert select_persona(sample_site, 0)["name"] == zero_sample[0]
        assert select_persona(sample_site, 5)["name"] == zero_sample[1]
        assert select_persona(sample_site, 10)["name"] == zero_sample[2]
        assert select_persona(sample_site, 15)["name"] == zero_sample[0]

    def test_deterministic(self, db_conn, sample_site):
        _seed_distribution(db_conn, sample_site)
        assert select_persona(sample_site, 3) == select_persona(sample_site, 3)

    def test_epsilon_zero_never_explores(self, db_conn, sample_site):
        _seed_distribution(db_conn, sample_site)
        # With epsilon=0, even topic_id 0 should exploit, not explore.
        assert select_persona(sample_site, 0, epsilon=0.0)["name"] == "data_analyst"
