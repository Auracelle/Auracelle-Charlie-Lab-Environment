"""
engine/negotiation.py — Negotiation dynamics helpers.

Provides deception detection, tension index calculation, and coalition
formation utilities drawn from the notebook's AgenticAdjudicator logic.
"""
from __future__ import annotations

import numpy as np
import random
from datetime import datetime


SHOCK_TYPES = [
    "economic_sanctions",
    "cyber_attack",
    "public_protest",
    "un_resolution",
    "trade_disruption",
    "diplomatic_incident",
    "tech_breakthrough",
    "alliance_shift",
    "intel_leak",
]


def calculate_tension_index(
    actor_positions: dict[str, str],
    power_levels: dict[str, float],
    alignment_graph: dict[str, float],
    real_world_data: dict[str, dict] | None = None,
) -> float:
    """
    Geopolitical tension index in [0, 1].

    Components:
      - Position divergence (std dev of hashed positions)
      - Power imbalance (std dev of power levels)
      - Alignment factor (1 - mean alignment)
      - Military expenditure factor (real-world data, if available)
    """
    position_divergence = np.std([hash(p) % 100 for p in actor_positions.values()]) / 100
    power_imbalance = np.std(list(power_levels.values())) if power_levels else 0.0
    alignment_factor = 1.0 - (
        sum(alignment_graph.values()) / (len(alignment_graph) + 1e-6)
    )

    mil_exp_factor = 0.0
    if real_world_data:
        mil_exps = [
            d.get("military_expenditure_pct", 2.0)
            for d in real_world_data.values()
            if d.get("military_expenditure_pct") is not None
        ]
        if mil_exps:
            mil_exp_factor = (np.mean(mil_exps) - 2.0) / 10.0

    tension = (
        position_divergence * 0.3
        + power_imbalance * 0.2
        + alignment_factor * 0.3
        + abs(mil_exp_factor) * 0.2
    )
    return float(np.clip(tension, 0.0, 1.0))


def detect_deception(
    stated_position: str,
    historical_actions: list[str],
    power_level: float,
) -> float:
    """
    Deception score in [0, 1].
    Higher means more likely the actor's stated position diverges from behaviour.
    """
    deception_score = 0.0
    if historical_actions:
        consistency = sum(1 for a in historical_actions if a == stated_position) / len(historical_actions)
        deception_score += (1.0 - consistency) * 0.5
    if power_level < 0.5 and "aggressive" in stated_position.lower():
        deception_score += 0.3
    return float(min(1.0, deception_score))


def inject_shock(
    current_round: int,
    tension_level: float,
    real_world_data: dict[str, dict] | None = None,
) -> dict | None:
    """
    Probabilistically inject an external shock event.
    Returns an event dict or None if no shock occurs.
    """
    sanctions_multiplier = 1.0
    if real_world_data:
        total_sanctions = sum(
            d.get("sanctioned_entities", 0) or 0
            for d in real_world_data.values()
        )
        if total_sanctions > 0:
            sanctions_multiplier = 1.3

    shock_prob = tension_level * 0.3 * sanctions_multiplier
    if random.random() < shock_prob:
        shock_type = random.choice(SHOCK_TYPES)
        magnitude = random.uniform(0.1, 0.5) * tension_level
        return {
            "round": current_round,
            "type": shock_type,
            "magnitude": round(magnitude, 3),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"Shock: {shock_type.replace('_', ' ').title()} (magnitude {magnitude:.2f})",
        }
    return None
