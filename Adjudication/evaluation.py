"""
adjudication/evaluation.py — After Action Review (AAR) evaluation helpers.

Produces structured evaluation output from a completed simulation session,
drawing on round_metrics_trace and event_log.
"""
from __future__ import annotations

from typing import Any
import numpy as np


def aar_summary(
    round_metrics_trace: list[dict],
    event_log: list[dict],
    policy: str,
    session_id: str,
) -> dict[str, Any]:
    """
    Generate an After Action Review summary dict.

    Parameters
    ----------
    round_metrics_trace : list of per-round metric snapshots
    event_log           : list of shock/event dicts
    policy              : selected policy label
    session_id          : session UUID

    Returns
    -------
    dict with keys: summary_text, kpis, shocks, recommendations
    """
    if not round_metrics_trace:
        return {
            "summary_text": "No rounds completed — no AAR available.",
            "kpis": {},
            "shocks": [],
            "recommendations": [],
        }

    keys = ["trust", "compliance", "alignment", "resilience", "systemic_risk"]
    kpis: dict[str, float] = {}
    for k in keys:
        vals = [r.get(k, 0.0) for r in round_metrics_trace if k in r]
        kpis[f"{k}_mean"] = round(float(np.mean(vals)), 3) if vals else 0.0
        kpis[f"{k}_final"] = round(float(vals[-1]), 3) if vals else 0.0

    shocks = [e for e in event_log if "type" in e]

    recommendations: list[str] = []
    if kpis.get("trust_final", 1.0) < 0.4:
        recommendations.append(
            "Low final trust detected — consider introducing confidence-building measures "
            "or reducing defection incentives in the next scenario iteration."
        )
    if kpis.get("systemic_risk_final", 0.0) > 0.65:
        recommendations.append(
            "Systemic risk remained elevated at session end — "
            "scenario stress-testing objective achieved; review escalation pathways."
        )
    if len(shocks) >= 3:
        recommendations.append(
            f"{len(shocks)} shocks injected — consider whether shock frequency matched "
            "intended scenario tempo."
        )
    if not recommendations:
        recommendations.append(
            "Session completed within normal governance parameters."
        )

    n_rounds = len(round_metrics_trace)
    summary_text = (
        f"**After Action Review — {policy}**\n\n"
        f"Session ID: `{session_id}`  |  Rounds completed: {n_rounds}  |  "
        f"Shocks injected: {len(shocks)}\n\n"
        f"Final trust: **{kpis.get('trust_final', 0):.0%}**  |  "
        f"Final compliance: **{kpis.get('compliance_final', 0):.0%}**  |  "
        f"Final systemic risk: **{kpis.get('systemic_risk_final', 0):.0%}**"
    )

    return {
        "summary_text": summary_text,
        "kpis": kpis,
        "shocks": shocks,
        "recommendations": recommendations,
    }
