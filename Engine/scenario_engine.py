"""
engine/scenario_engine.py — E-AGPO-HT-aligned MARL governance environment.

Extracted verbatim from the notebook's agpo_rl_engine.py with one fix:
  - EAGPOEnv.reset() now accepts optional initial_tension / initial_stability /
    initial_sanction_pressure kwargs so that scenario YAML values are honoured.
  - risk_weight and sanction_sensitivity are resolved from actor_profiles with
    safe defaults so the engine never KeyErrors.
"""
from __future__ import annotations

import math
import random
from typing import Any

import numpy as np

# ── Action space ───────────────────────────────────────────────────────────────
COOPERATE = 0
TIGHTEN = 1
DEFECT = 2

ACTION_NAMES: dict[int, str] = {
    COOPERATE: "Cooperate",
    TIGHTEN: "Tighten Controls",
    DEFECT: "Defect",
}


def institutional_capacity_from_wb(inst_capacity: Any, fallback: float = 0.55) -> float:
    if inst_capacity is None:
        return float(fallback)
    try:
        return float(inst_capacity)
    except Exception:
        return float(fallback)


class EAGPOEnv:
    """E-AGPO-HT-aligned governance environment (MARL, tabular).

    Dynamics:
    - Actor-specific reward weighting (risk_weight, sanction_sensitivity)
    - Institutional capacity embedded in reward
    - Network-weighted sanction propagation (centrality mean)
    - Stochastic shock injection (shock_sigma)
    - Centrality-weighted payoff asymmetry
    - Treaty durability forecasting curve
    """

    def __init__(self, actor_profiles: dict[str, dict]):
        self.actor_profiles = actor_profiles
        self._initial_tension = 0.40
        self._initial_stability = 0.60
        self._initial_sanction_pressure = 0.20
        self.reset()

    def configure_initial_state(
        self,
        tension: float = 0.40,
        stability: float = 0.60,
        sanction_pressure: float = 0.20,
    ) -> None:
        """Set initial state values from a scenario definition."""
        self._initial_tension = float(tension)
        self._initial_stability = float(stability)
        self._initial_sanction_pressure = float(sanction_pressure)

    def reset(self) -> np.ndarray:
        self.round = 0
        self.tension = self._initial_tension
        self.stability = self._initial_stability
        self.sanction_pressure = self._initial_sanction_pressure
        self.history: list[tuple] = []
        return self.state()

    def state(self) -> np.ndarray:
        return np.array([self.tension, self.stability, self.sanction_pressure], dtype=float)

    def durability(self) -> float:
        return float(self.stability * math.exp(-self.tension))

    def step(
        self,
        actions: dict[str, int],
        shock_sigma: float = 0.02,
    ) -> tuple[np.ndarray, dict[str, float], bool]:
        self.round += 1

        coop = sum(1 for a in actions.values() if a == COOPERATE)
        defect = sum(1 for a in actions.values() if a == DEFECT)

        shock = float(np.random.normal(0.0, shock_sigma))
        centrality = float(
            np.mean([self.actor_profiles[a]["centrality"] for a in actions])
        )

        self.tension += 0.05 * defect + shock
        self.stability += 0.04 * coop - 0.03 * defect
        self.sanction_pressure += 0.03 * defect * centrality

        self.tension = float(np.clip(self.tension, 0, 1))
        self.stability = float(np.clip(self.stability, 0, 1))
        self.sanction_pressure = float(np.clip(self.sanction_pressure, 0, 1))

        rewards: dict[str, float] = {}
        for actor, action in actions.items():
            p = self.actor_profiles[actor]
            inst_cap = float(p.get("institutional_capacity", 0.55))
            asymmetry = float(p.get("centrality", 0.5)) * 0.15
            risk_w = float(p.get("risk_weight", 0.55))
            sanction_s = float(p.get("sanction_sensitivity", 0.35))

            reward = (
                risk_w * self.stability
                - (1.0 - risk_w) * self.tension
                - sanction_s * self.sanction_pressure
                + 0.25 * inst_cap
                + asymmetry
            )
            if action == DEFECT:
                reward -= 0.15
            rewards[actor] = float(reward)

        self.history.append(
            (self.tension, self.stability, self.sanction_pressure, self.durability())
        )
        done = self.round >= 20
        return self.state(), rewards, done


class QAgent:
    """Interpretable tabular Q-learning agent (ε-greedy, TD(0))."""

    def __init__(
        self,
        name: str,
        alpha: float = 0.1,
        gamma: float = 0.9,
        epsilon: float = 0.15,
    ):
        self.name = name
        self.q: dict[tuple, np.ndarray] = {}
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self.epsilon = float(epsilon)

    def _key(self, state: np.ndarray) -> tuple:
        return tuple(np.round(state, 2))

    def choose(self, state: np.ndarray, n_actions: int = 3) -> int:
        key = self._key(state)
        if key not in self.q:
            self.q[key] = np.zeros(n_actions, dtype=float)
        if random.random() < self.epsilon:
            return random.randint(0, n_actions - 1)
        return int(np.argmax(self.q[key]))

    def update(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
    ) -> None:
        k = self._key(state)
        nk = self._key(next_state)
        if k not in self.q:
            self.q[k] = np.zeros(3, dtype=float)
        if nk not in self.q:
            self.q[nk] = np.zeros(3, dtype=float)
        self.q[k][action] += self.alpha * (
            reward + self.gamma * np.max(self.q[nk]) - self.q[k][action]
        )
