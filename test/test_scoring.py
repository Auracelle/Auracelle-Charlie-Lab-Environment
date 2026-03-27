"""
tests/test_scoring.py — Unit tests for engine/scoring.py

Run: pytest tests/test_scoring.py -v
"""
import numpy as np
import pytest

from engine.scoring import (
    compute_trust,
    compute_compliance,
    compute_alignment,
    compute_resilience,
    compute_systemic_risk,
    round_metrics_snapshot,
)
from engine.scenario_engine import COOPERATE, TIGHTEN, DEFECT


class TestComputeTrust:
    def test_high_stability_low_sanction_gives_high_trust(self):
        assert compute_trust(stability=1.0, sanction_pressure=0.0) == pytest.approx(1.0)

    def test_low_stability_gives_low_trust(self):
        assert compute_trust(stability=0.0, sanction_pressure=0.0) == pytest.approx(0.0)

    def test_trust_in_unit_interval(self):
        for s in np.linspace(0, 1, 10):
            for p in np.linspace(0, 1, 10):
                t = compute_trust(s, p)
                assert 0.0 <= t <= 1.0


class TestComputeCompliance:
    def test_all_cooperate_is_full_compliance(self):
        actions = {"A": COOPERATE, "B": COOPERATE, "C": COOPERATE}
        assert compute_compliance(actions) == pytest.approx(1.0)

    def test_all_defect_is_zero_compliance(self):
        actions = {"A": DEFECT, "B": DEFECT}
        assert compute_compliance(actions) == pytest.approx(0.0)

    def test_mixed_actions(self):
        actions = {"A": COOPERATE, "B": DEFECT}
        c = compute_compliance(actions)
        assert c == pytest.approx(0.5)

    def test_empty_actions_returns_default(self):
        assert compute_compliance({}) == pytest.approx(0.5)

    def test_tighten_counts_as_compliant(self):
        actions = {"A": TIGHTEN, "B": DEFECT}
        assert compute_compliance(actions) == pytest.approx(0.5)


class TestComputeAlignment:
    def test_identical_positions_full_alignment(self):
        positions = {"A": "same", "B": "same", "C": "same"}
        assert compute_alignment(positions) == pytest.approx(1.0)

    def test_all_different_positions_low_alignment(self):
        positions = {"A": "pos1", "B": "pos2", "C": "pos3"}
        a = compute_alignment(positions)
        assert a < 0.5

    def test_empty_positions_returns_default(self):
        assert compute_alignment({}) == pytest.approx(0.5)

    def test_alignment_in_unit_interval(self):
        positions = {"A": "x", "B": "y"}
        a = compute_alignment(positions)
        assert 0.0 <= a <= 1.0


class TestComputeResilience:
    def test_high_durability_low_tension_gives_high_resilience(self):
        r = compute_resilience(durability=1.0, tension=0.0)
        assert r == pytest.approx(1.0)

    def test_zero_durability_gives_zero_resilience(self):
        r = compute_resilience(durability=0.0, tension=0.5)
        assert r == pytest.approx(0.0)

    def test_resilience_in_unit_interval(self):
        for d in np.linspace(0, 1, 5):
            for t in np.linspace(0, 1, 5):
                r = compute_resilience(d, t)
                assert 0.0 <= r <= 1.0


class TestComputeSystemicRisk:
    def test_max_inputs_give_high_risk(self):
        r = compute_systemic_risk(tension=1.0, sanction_pressure=1.0, stability=0.0)
        assert r == pytest.approx(1.0)

    def test_min_inputs_give_low_risk(self):
        r = compute_systemic_risk(tension=0.0, sanction_pressure=0.0, stability=1.0)
        assert r == pytest.approx(0.0)

    def test_risk_in_unit_interval(self):
        for t in np.linspace(0, 1, 5):
            for p in np.linspace(0, 1, 5):
                for s in np.linspace(0, 1, 5):
                    r = compute_systemic_risk(t, p, s)
                    assert 0.0 <= r <= 1.0


class TestRoundMetricsSnapshot:
    def test_returns_all_expected_keys(self):
        state = np.array([0.4, 0.6, 0.2])
        actions = {"A": COOPERATE, "B": DEFECT}
        positions = {"A": "moderate", "B": "strict"}
        snapshot = round_metrics_snapshot(state, actions, positions, durability=0.45)
        expected = {"trust", "compliance", "alignment", "resilience",
                    "systemic_risk", "tension", "stability", "sanction_pressure", "durability"}
        assert set(snapshot.keys()) >= expected

    def test_all_values_in_unit_interval(self):
        state = np.array([0.55, 0.45, 0.30])
        actions = {"A": TIGHTEN, "B": COOPERATE}
        positions = {"A": "pos1", "B": "pos1"}
        snapshot = round_metrics_snapshot(state, actions, positions, durability=0.3)
        for k, v in snapshot.items():
            assert 0.0 <= v <= 1.0, f"{k} = {v} is out of [0, 1]"
