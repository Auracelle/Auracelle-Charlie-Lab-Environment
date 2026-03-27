"""
adjudication/policy_owner.py — Policy Owner agentic adjudicator.

The Policy Owner enforces the selected governance framework and
provides structured feedback on actor choices each round.
Extracted and refactored from notebook's adjudicator.py.
"""
from __future__ import annotations

import random
import numpy as np
from datetime import datetime
from typing import Any

from engine.negotiation import SHOCK_TYPES


class PolicyOwner:
    """
    Neutral referee / policy enforcer.

    Responsibilities:
    - Maintain and update tension index
    - Detect potential actor deception
    - Generate shock events
    - Provide round narrative to facilitator

    This class is framework-agnostic: it receives real-world data via
    integrate_real_world_data() and applies it to its calculations.
    It does NOT call external APIs directly — callers supply data.
    """

    def __init__(self, mode: str = "neutral"):
        self.mode = mode
        self.event_history: list[dict] = []
        self.tension_index: float = 0.5
        self.real_world_data: dict[str, dict] = {}

    # ── Real-world data ingestion ─────────────────────────────────────────────

    def integrate_real_world_data(
        self,
        country_code: str,
        gdp: float | None = None,
        mil_exp: float | None = None,
        internet: float | None = None,
        sanctions: int | None = None,
    ) -> None:
        self.real_world_data[country_code] = {
            "gdp": gdp,
            "military_expenditure_pct": mil_exp,
            "internet_penetration": internet,
            "sanctioned_entities": sanctions,
        }

    # ── Tension index ─────────────────────────────────────────────────────────

    def calculate_tension_index(
        self,
        actor_positions: dict[str, str],
        power_levels: dict[str, float],
        alignment_graph: dict[str, float],
    ) -> float:
        position_divergence = (
            np.std([hash(p) % 100 for p in actor_positions.values()]) / 100
        )
        power_imbalance = np.std(list(power_levels.values())) if power_levels else 0.0
        alignment_factor = 1.0 - (
            sum(alignment_graph.values()) / (len(alignment_graph) + 1e-6)
        )
        mil_exp_factor = 0.0
        if self.real_world_data:
            mil_exps = [
                d.get("military_expenditure_pct", 2.0)
                for d in self.real_world_data.values()
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
        self.tension_index = float(np.clip(tension, 0.0, 1.0))
        return self.tension_index

    # ── Deception detection ───────────────────────────────────────────────────

    def detect_deception(
        self,
        stated_position: str,
        historical_actions: list[str],
        power_level: float,
    ) -> float:
        deception_score = 0.0
        if historical_actions:
            consistency = sum(
                1 for a in historical_actions if a == stated_position
            ) / len(historical_actions)
            deception_score += (1.0 - consistency) * 0.5
        if power_level < 0.5 and "aggressive" in stated_position.lower():
            deception_score += 0.3
        return float(min(1.0, deception_score))

    # ── Shock injection ───────────────────────────────────────────────────────

    def inject_shock(self, current_round: int, tension_level: float) -> dict | None:
        sanctions_multiplier = 1.0
        if self.real_world_data:
            total_sanctions = sum(
                d.get("sanctioned_entities", 0) or 0
                for d in self.real_world_data.values()
            )
            if total_sanctions > 0:
                sanctions_multiplier = 1.3

        shock_prob = tension_level * 0.3 * sanctions_multiplier
        if random.random() < shock_prob:
            shock_type = random.choice(SHOCK_TYPES)
            magnitude = random.uniform(0.1, 0.5) * tension_level
            event = {
                "round": current_round,
                "type": shock_type,
                "magnitude": round(magnitude, 3),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "description": (
                    f"Shock: {shock_type.replace('_', ' ').title()} "
                    f"(magnitude {magnitude:.2f})"
                ),
            }
            self.event_history.append(event)
            return event
        return None

    # ── Round narrative ───────────────────────────────────────────────────────

    def generate_round_narrative(
        self,
        round_num: int,
        actions: dict[str, str],
        metrics: dict[str, float],
        policy: str,
    ) -> str:
        tension = metrics.get("tension", self.tension_index)
        stability = metrics.get("stability", 0.5)
        compliance = metrics.get("compliance", 0.5)

        defectors = [a for a, act in actions.items() if act == "Defect"]
        cooperators = [a for a, act in actions.items() if act == "Cooperate"]

        parts = [f"**Round {round_num} — Policy Owner Assessment ({policy})**"]
        if defectors:
            parts.append(
                f"⚠️ Defection detected: {', '.join(defectors)}. "
                f"Tension raised to {tension:.2f}."
            )
        if cooperators:
            parts.append(
                f"✅ Cooperative actors: {', '.join(cooperators)}. "
                f"Stability at {stability:.2f}."
            )
        if tension > 0.7:
            parts.append("🔴 **HIGH TENSION** — risk of cascading breakdown.")
        elif tension > 0.45:
            parts.append("🟡 Elevated tension — monitor closely.")
        else:
            parts.append("🟢 Stable governance environment.")

        parts.append(f"Compliance index: {compliance:.0%}")
        return "\n\n".join(parts)
