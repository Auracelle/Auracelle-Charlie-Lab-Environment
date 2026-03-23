import numpy as np
import random
import math

# Interpretable action space
COOPERATE = 0
TIGHTEN = 1
DEFECT = 2

ACTION_NAMES = {
    COOPERATE: "Cooperate",
    TIGHTEN: "Tighten Controls",
    DEFECT: "Defect"
}

def institutional_capacity_from_wb(inst_capacity, fallback=0.55):
    if inst_capacity is None:
        return float(fallback)
    try:
        return float(inst_capacity)
    except Exception:
        return float(fallback)

class EAGPOEnv:
    """E-AGPO-HT-aligned governance environment.

    Includes:
    - actor-specific reward weighting
    - institutional capacity embedded in reward
    - network-weighted sanction propagation (centrality mean)
    - stochastic shock injection (sigma)
    - centrality-weighted payoff asymmetry
    - treaty durability forecasting curve
    """

    def __init__(self, actor_profiles: dict):
        self.actor_profiles = actor_profiles
        self.reset()

    def reset(self):
        self.round = 0
        self.tension = 0.40
        self.stability = 0.60
        self.sanction_pressure = 0.20
        self.history = []  # (tension, stability, sanction_pressure, durability)
        return self.state()

    def state(self):
        return np.array([self.tension, self.stability, self.sanction_pressure], dtype=float)

    def durability(self):
        return float(self.stability * math.exp(-self.tension))

    def step(self, actions: dict, shock_sigma: float = 0.02):
        self.round += 1

        coop = sum(1 for a in actions.values() if a == COOPERATE)
        defect = sum(1 for a in actions.values() if a == DEFECT)

        # Stochastic shock injection
        shock = float(np.random.normal(0.0, shock_sigma))

        # Network-weighted sanction propagation (centrality mean proxy)
        centrality = float(np.mean([self.actor_profiles[a]["centrality"] for a in actions]))

        # Governance dynamics
        self.tension += 0.05 * defect + shock
        self.stability += 0.04 * coop - 0.03 * defect
        self.sanction_pressure += 0.03 * defect * centrality

        # Clamp 0..1
        self.tension = float(np.clip(self.tension, 0, 1))
        self.stability = float(np.clip(self.stability, 0, 1))
        self.sanction_pressure = float(np.clip(self.sanction_pressure, 0, 1))

        # Rewards
        rewards = {}
        for actor, action in actions.items():
            p = self.actor_profiles[actor]
            inst_cap = float(p["institutional_capacity"])
            asymmetry = float(p["centrality"]) * 0.15

            reward = (
                float(p["risk_weight"]) * self.stability
                - (1.0 - float(p["risk_weight"])) * self.tension
                - float(p["sanction_sensitivity"]) * self.sanction_pressure
                + 0.25 * inst_cap
                + asymmetry
            )
            if action == DEFECT:
                reward -= 0.15
            rewards[actor] = float(reward)

        self.history.append((self.tension, self.stability, self.sanction_pressure, self.durability()))
        done = self.round >= 20
        return self.state(), rewards, done

class QAgent:
    """Interpretable tabular Q-learning agent."""
    def __init__(self, name: str, alpha=0.1, gamma=0.9, epsilon=0.15):
        self.name = name
        self.q = {}
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self.epsilon = float(epsilon)

    def _key(self, state):
        return tuple(np.round(state, 2))

    def choose(self, state, n_actions=3):
        key = self._key(state)
        if key not in self.q:
            self.q[key] = np.zeros(n_actions, dtype=float)
        if random.random() < self.epsilon:
            return random.randint(0, n_actions-1)
        return int(np.argmax(self.q[key]))

    def update(self, state, action, reward, next_state):
        k = self._key(state)
        nk = self._key(next_state)
        if k not in self.q:
            self.q[k] = np.zeros(3, dtype=float)
        if nk not in self.q:
            self.q[nk] = np.zeros(3, dtype=float)
        self.q[k][action] += self.alpha * (reward + self.gamma*np.max(self.q[nk]) - self.q[k][action])
