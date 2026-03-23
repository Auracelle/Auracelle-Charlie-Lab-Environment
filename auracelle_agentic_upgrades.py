

import random
from typing import Dict, List, Tuple

DEFAULT_POLICY_PACKAGES: List[Dict] = [
    {"name": "Safeguards + Compute Reporting + Audit Corridor",
     "moves": ["Privacy Safeguards", "Compute Reporting", "Cross-Border Audit Pathway"],
     "base_cost": 1.2},
    {"name": "Transparency Exchange + Incident Protocol",
     "moves": ["Transparency Exchange", "Incident Response Protocol"],
     "base_cost": 1.0},
    {"name": "Joint Oversight Board + Redress Mechanism",
     "moves": ["Joint Oversight Board", "User Redress Mechanism"],
     "base_cost": 1.1},
    {"name": "Minimal Deal: Shared Definitions",
     "moves": ["Shared Definitions / Terminology"],
     "base_cost": 0.6},
]

def is_institution_actor(actor: str) -> bool:
    a = (actor or "").strip().lower()
    return any(x in a for x in ["nato", "eu", "oecd", "un", "g7", "g20", "gcc", "mena"])

def infer_opponent_stance(last_moves: List[str]) -> str:
    """Classify stance from the last 2–3 moves (conciliatory/neutral/hardline)."""
    if not last_moves:
        return "neutral"
    recent = [m.lower() for m in last_moves[-3:]]
    hard = sum(any(k in m for k in ["escalat", "sanction", "demand", "ultimatum"]) for m in recent)
    conc = sum(any(k in m for k in ["concess", "offer", "share", "cooperat", "joint"]) for m in recent)
    if hard >= 2 and conc == 0:
        return "hardline"
    if conc >= 2 and hard == 0:
        return "conciliatory"
    return "neutral"

class AutonomousNegotiationAgent:
    """Lightweight learning agent (linear Q approximator) with opponent stance in state."""

    def __init__(self, name: str, institution: bool = False, alpha: float = 0.15, gamma: float = 0.95, eps: float = 0.15):
        self.name = name
        self.institution = institution
        self.alpha = alpha
        self.gamma = gamma
        self.eps = eps
        # weights[action_name] = dict(feature->weight)
        self.weights: Dict[str, Dict[str, float]] = {}
        self.last_opponent_moves: List[str] = []

    def _features(self, tension: float, stance: str, round_idx: int) -> Dict[str, float]:
        # Tiny, interpretable feature set
        return {
            "bias": 1.0,
            "tension": float(tension),
            "round": float(round_idx),
            "stance_conc": 1.0 if stance == "conciliatory" else 0.0,
            "stance_hard": 1.0 if stance == "hardline" else 0.0,
        }

    def _score(self, action_name: str, feats: Dict[str, float]) -> float:
        w = self.weights.get(action_name)
        if w is None:
            # lazy init
            w = {k: 0.0 for k in feats.keys()}
            self.weights[action_name] = w
        return sum(w.get(k, 0.0) * v for k, v in feats.items())

    def choose_package(self, tension: float, policy_packages: List[Dict], round_idx: int = 0) -> Tuple[Dict, str, float]:
        stance = infer_opponent_stance(self.last_opponent_moves)
        feats = self._features(tension=tension, stance=stance, round_idx=round_idx)

        # epsilon-greedy over packages
        if random.random() < self.eps:
            pkg = random.choice(policy_packages)
        else:
            scored = [(pkg, self._score(pkg["name"], feats)) for pkg in policy_packages]
            scored.sort(key=lambda x: x[1], reverse=True)
            pkg = scored[0][0]

        cost_mult = 1.5 if self.institution else 1.0
        return pkg, stance, cost_mult

    def learn(self, prev_tension: float, new_tension: float, round_idx: int, action_name: str, reward: float):
        stance = infer_opponent_stance(self.last_opponent_moves)
        feats = self._features(tension=prev_tension, stance=stance, round_idx=round_idx)
        q = self._score(action_name, feats)

        # bootstrap target using new tension (proxy for next state)
        next_feats = self._features(tension=new_tension, stance=stance, round_idx=round_idx + 1)
        # optimistic estimate: max over known actions
        if self.weights:
            next_q = max(self._score(a, next_feats) for a in self.weights.keys())
        else:
            next_q = 0.0

        target = reward + self.gamma * next_q
        td = target - q

        w = self.weights[action_name]
        for k, v in feats.items():
            w[k] = w.get(k, 0.0) + self.alpha * td * v

class MediatorAgent:
    """Rule/heuristic mediator that proposes 2–3 compromise bundles plus a rationale trace."""

    def propose(self, positions: Dict, tension: float, policy_packages: List[Dict]) -> Tuple[List[Dict], Dict]:
        # Simple heuristic: when tension is high, propose lower-cost or legitimacy-building bundles
        sorted_pkgs = sorted(policy_packages, key=lambda p: p.get("base_cost", 1.0))
        if tension >= 0.7:
            picks = [sorted_pkgs[0], sorted_pkgs[1]]
        elif tension >= 0.4:
            picks = [sorted_pkgs[1], sorted_pkgs[2]]
        else:
            picks = [sorted_pkgs[2], sorted_pkgs[3] if len(sorted_pkgs) > 3 else sorted_pkgs[0]]

        rationale = {
            "what_each_side_gains": "Lower immediate escalation risk; clearer pathway to mutual verification and trust-building.",
            "what_each_side_concedes": "Partial flexibility on sovereignty/oversight to gain reciprocal assurances.",
            "predicted_diffusion_impact": "Higher if an institutional actor (EU/NATO/UN/OECD) adopts early; moderate otherwise.",
            "predicted_tension_change": "Decrease expected if accepted; neutral-to-increase if rejected under high tension."
        }
        return picks, rationale

class RedTeamAgent:
    """Adversarial stress-tester that selects plausible/worst-timed shocks and scores robustness."""

    SHOCKS = [
        "Cross-Border Data Breach",
        "Disinformation Wave",
        "Critical Infrastructure AI Failure",
        "Data Localization Emergency",
        "Supply Chain/Compute Restriction Shock",
    ]

    def select_shock(self, tension: float) -> str:
        # Worst-timed: pick higher-severity shocks when tension is already high
        if tension >= 0.75:
            return "Critical Infrastructure AI Failure"
        if tension >= 0.55:
            return "Cross-Border Data Breach"
        return "Disinformation Wave"

    def score_robustness(self, pre_tension: float, post_tension: float) -> str:
        if post_tension - pre_tension > 0.15:
            return "Fracture risk ↑"
        if pre_tension - post_tension > 0.10:
            return "Adapted"
        return "Held"

