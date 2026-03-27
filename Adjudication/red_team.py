"""
adjudication/red_team.py — Red Team cognitive attack engine.

Extracted verbatim from pages/3_Red_Team_Module.py with all Streamlit UI
removed.  Pages import these functions; they do not carry display logic.
"""
from __future__ import annotations

from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────

def clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def init_agents(names: list[str]) -> dict[str, dict]:
    """Initialise cognitive agent profiles for red-team stress testing."""
    agents: dict[str, dict] = {}
    for n in names:
        agents[n] = {
            "cognition": {
                "H":      3,     # Horizon depth (1..K)
                "Omega":  0.55,  # Openness / update rate (0..1)
                "Lambda": 0.55,  # Uncertainty tolerance (0..1)
                "Pi":     0.45,  # Narrative lock-in (0..1)
            },
            "belief": {
                "mu":    0.50,   # Expected outcome proxy (0..1)
                "sigma": 0.25,   # Uncertainty proxy (0..1)
            },
            "metrics": {
                "USI": None,     # Update Suppression Index
                "HD":  0,        # Horizon Degradation
            },
        }
    return agents


def compute_alpha(cog: dict) -> float:
    """Effective belief-update rate: α = Ω × (1 − Π)."""
    return clip01(cog["Omega"] * (1.0 - cog["Pi"]))


def update_belief(agent: dict, evidence: float) -> None:
    """
    Cognition-weighted Bayesian-style belief update.

    evidence: float in [-1, 1]
      +1 pushes mu toward 1.0 (strong positive signal)
      -1 pushes mu toward 0.0 (strong disconfirmation)
    """
    cog = agent["cognition"]
    bel = agent["belief"]

    alpha = compute_alpha(cog)
    target = clip01(0.5 + 0.5 * float(evidence))

    bel["mu"] = clip01((1 - alpha) * bel["mu"] + alpha * target)

    # Uncertainty: low Lambda collapses sigma faster (more certain, less open)
    collapse = (1.0 - cog["Lambda"]) * 0.20
    bel["sigma"] = clip01(bel["sigma"] * (1.0 - collapse))

    agent["metrics"]["USI"] = clip01(1.0 - alpha)


# ── Red team moves ────────────────────────────────────────────────────────────

RED_TEAM_MOVES = [
    "Horizon Collapse",
    "Narrative Entrenchment",
    "Epistemic Distrust",
    "Panic Amplification",
    "Metric Spoofing",
    "Frame Flip",
]


def apply_red_team_move(
    agent: dict,
    move: str,
    intensity: float,
    K: int = 5,
) -> None:
    """
    Apply a red-team cognitive attack to a single agent.

    Parameters
    ----------
    agent     : agent dict produced by init_agents()
    move      : one of RED_TEAM_MOVES
    intensity : attack intensity in [0, 1]
    K         : max horizon depth (default 5)
    """
    cog = agent["cognition"]
    bel = agent["belief"]

    if move == "Horizon Collapse":
        old = cog["H"]
        cog["H"] = int(max(1, cog["H"] - int(round(intensity * 2))))
        agent["metrics"]["HD"] += old - cog["H"]

    elif move == "Narrative Entrenchment":
        cog["Pi"] = clip01(cog["Pi"] + 0.35 * intensity)

    elif move == "Epistemic Distrust":
        cog["Omega"] = clip01(cog["Omega"] - 0.35 * intensity)

    elif move == "Panic Amplification":
        cog["Lambda"] = clip01(cog["Lambda"] - 0.35 * intensity)

    elif move == "Metric Spoofing":
        bel["mu"] = clip01(bel["mu"] + 0.25 * intensity)

    elif move == "Frame Flip":
        cog["Omega"] = clip01(1.0 - cog["Omega"])


def agent_summary(name: str, agent: dict) -> dict[str, Any]:
    """Flatten an agent dict to a summary suitable for display."""
    cog = agent["cognition"]
    bel = agent["belief"]
    met = agent["metrics"]
    alpha = compute_alpha(cog)
    return {
        "Actor":      name,
        "H (Horizon)":   cog["H"],
        "Ω (Openness)":  round(cog["Omega"], 3),
        "Λ (Uncertainty tol.)": round(cog["Lambda"], 3),
        "Π (Lock-in)":   round(cog["Pi"], 3),
        "α (Update rate)": round(alpha, 3),
        "μ (Belief)":    round(bel["mu"], 3),
        "σ (Uncertainty)": round(bel["sigma"], 3),
        "USI":           round(met["USI"], 3) if met["USI"] is not None else "–",
        "HD":            met["HD"],
    }
