"""
engine/scoring.py — Governance metric calculations.

Computes trust, compliance, alignment, and resilience from simulation state.
These are the four outcome metrics logged to the research database.
"""
from __future__ import annotations

import numpy as np


def compute_trust(stability: float, sanction_pressure: float) -> float:
    """
    Trust increases with stability and decreases with sanction pressure.
    Returns a value in [0, 1].
    """
    return float(np.clip(stability * (1.0 - 0.5 * sanction_pressure), 0.0, 1.0))


def compute_compliance(actions: dict[str, int], n_actions: int = 3) -> float:
    """
    Compliance proxy: fraction of actors choosing COOPERATE (action 0)
    or TIGHTEN (action 1) rather than DEFECT (action 2).
    """
    if not actions:
        return 0.5
    compliant = sum(1 for a in actions.values() if a != 2)
    return float(compliant / len(actions))


def compute_alignment(actor_positions: dict[str, str]) -> float:
    """
    Alignment proxy from position diversity.
    Uses set cardinality as a rough divergence measure.
    """
    if not actor_positions:
        return 0.5
    unique = len(set(actor_positions.values()))
    total = len(actor_positions)
    return float(np.clip(1.0 - (unique - 1) / max(total, 1), 0.0, 1.0))


def compute_resilience(durability: float, tension: float) -> float:
    """
    Resilience: durability adjusted for tension overhang.
    """
    return float(np.clip(durability * (1.0 - 0.3 * tension), 0.0, 1.0))


def compute_systemic_risk(tension: float, sanction_pressure: float, stability: float) -> float:
    """
    Aggregate systemic risk score in [0, 1].
    Higher tension and sanction pressure raise risk; stability lowers it.
    """
    return float(np.clip(
        0.4 * tension + 0.35 * sanction_pressure + 0.25 * (1.0 - stability),
        0.0, 1.0,
    ))


def round_metrics_snapshot(
    env_state: np.ndarray,
    actions: dict[str, int],
    actor_positions: dict[str, str],
    durability: float,
) -> dict:
    """
    Produce a single-round metrics dict suitable for logging and chart traces.
    """
    tension, stability, sanction_pressure = float(env_state[0]), float(env_state[1]), float(env_state[2])
    return {
        "trust": compute_trust(stability, sanction_pressure),
        "compliance": compute_compliance(actions),
        "alignment": compute_alignment(actor_positions),
        "resilience": compute_resilience(durability, tension),
        "systemic_risk": compute_systemic_risk(tension, sanction_pressure, stability),
        "tension": tension,
        "stability": stability,
        "sanction_pressure": sanction_pressure,
        "durability": durability,
    }
