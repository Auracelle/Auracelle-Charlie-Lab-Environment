# Auracelle Charlie – Leader Tools (IP-safe utilities)
# Provides: Leader Decision Brief, Quantitative Scoreboard, AAR Export (MD/PDF)
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Tuple, Optional

import math

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _to_pct01(x: float) -> float:
    return _clamp(float(x), 0.0, 1.0)

def compute_scoreboard(actor: str,
                       history: List[List[float]],
                       institutional_capacity: Optional[float] = None) -> Dict[str, Any]:
    """
    Compute leader-friendly, interpretable metrics from env history.
    NOTE: These are comparative decision-test outputs, not predictions.
    """
    if not history:
        return {
            "actor": actor,
            "robustness_0_100": None,
            "friction_0_100": None,
            "evidence_threshold_pct": None,
            "coord_latency_turns": None,
        }

    # history rows: [tension, stability, sanction_pressure, durability]
    last = history[-1]
    tension = _to_pct01(last[0])
    stability = _to_pct01(last[1])
    sanction = _to_pct01(last[2])
    durability = _to_pct01(last[3])

    # Composite robustness (interpretable): reward stability+durability, penalize tension+sanction
    comp = (stability + durability)/2.0 - (tension + sanction)/2.0
    robustness = int(round(_clamp((comp + 1.0) * 50.0, 0.0, 100.0)))

    # Friction: average pressure terms
    friction = int(round(_clamp(((tension + sanction)/2.0) * 100.0, 0.0, 100.0)))

    cap = institutional_capacity
    if cap is None:
        cap = 0.55
    cap = _to_pct01(cap)

    # Evidence threshold: higher when tension/sanction high; lower when capacity high
    threshold = 65.0 + 25.0*((tension + sanction)/2.0) - 20.0*cap
    threshold = int(round(_clamp(threshold, 15.0, 95.0)))

    # Coordination latency: first turn meeting "stable enough" condition, else total turns
    latency = len(history)
    for i, row in enumerate(history, start=1):
        t, s, sp, d = map(_to_pct01, row)
        if (s >= 0.70) and (d >= 0.60) and (t <= 0.45):
            latency = i
            break

    return {
        "actor": actor,
        "robustness_0_100": robustness,
        "friction_0_100": friction,
        "evidence_threshold_pct": threshold,
        "coord_latency_turns": latency,
        "last_state": {
            "tension": tension,
            "stability": stability,
            "sanction_pressure": sanction,
            "durability": durability,
        },
    }

def sensitivity_rank(shock_impacts: Dict[str, float]) -> List[Tuple[str, float]]:
    """Return ranked stressors by absolute impact (descending)."""
    items = [(k, float(v)) for k, v in (shock_impacts or {}).items()]
    items.sort(key=lambda kv: abs(kv[1]), reverse=True)
    return items

def build_leader_brief(run: Dict[str, Any],
                       scoreboard: Dict[str, Any],
                       sensitivity: List[Tuple[str, float]]) -> Dict[str, Any]:
    """Structured leader brief content (rendered in Streamlit)."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    actor = run.get("actor", "—")
    scenario = run.get("scenario", "—")
    shock = run.get("shock", "None")
    intensity = run.get("intensity", "—")
    window = run.get("metrics_window", "—")
    trade_year = run.get("trade_year", "—")

    # Most recent pressures (derived)
    last = scoreboard.get("last_state") or {}
    pressures = []
    if last:
        pressures = [
            ("Tension", int(round(last.get("tension", 0)*100))),
            ("Sanction pressure", int(round(last.get("sanction_pressure", 0)*100))),
        ]

    top_sens = [f"{k} (Δ {v:+.1f})" for k, v in (sensitivity or [])[:3]] or ["—"]

    return {
        "header": f"Leader Decision Brief — {actor}",
        "timestamp": now,
        "decision_question": "Given current constraints and pressures, how should the actor posture on this policy move this round?",
        "run_context": {
            "Scenario": scenario,
            "Shock": shock,
            "Intensity": intensity,
            "Metrics window": window,
            "Trade year": trade_year,
        },
        "now_state": pressures,
        "scoreboard": scoreboard,
        "top_sensitivity": top_sens,
        "focus": [
            "This is a decision-test snapshot, not a forecast.",
            "Use robustness + friction + evidence threshold + latency to compare options under stress.",
        ],
        "triggers": [
            "Evidence confidence changes materially (new verification, audit signals, incident disclosure).",
            "Shock conditions escalate or reverse (sanctions, supply chain, cyber incident severity).",
            "Alliance posture shifts (coordination commitments or defections).",
        ],
    }

def build_aar_markdown(run: Dict[str, Any],
                       scoreboard: Dict[str, Any],
                       sensitivity: List[Tuple[str, float]],
                       event_log: List[str]) -> str:
    """AAR in Markdown."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    actor = run.get("actor", "—")
    scenario = run.get("scenario", "—")
    shock = run.get("shock", "None")
    intensity = run.get("intensity", "—")
    mw = run.get("metrics_window", "—")
    trade_year = run.get("trade_year", "—")

    lines = []
    lines.append(f"# Auracelle Charlie — After Action Report (AAR)")
    lines.append(f"- **Generated:** {ts}")
    lines.append("")
    lines.append("## Run Context")
    lines.append(f"- **Actor:** {actor}")
    lines.append(f"- **Scenario:** {scenario}")
    lines.append(f"- **Shock:** {shock}")
    lines.append(f"- **Intensity:** {intensity}")
    lines.append(f"- **Metrics window:** {mw}")
    lines.append(f"- **Trade year:** {trade_year}")
    lines.append("")
    lines.append("## Quantitative Scoreboard (Decision-Test Outputs)")
    lines.append(f"- **Robustness (0–100):** {scoreboard.get('robustness_0_100')}")
    lines.append(f"- **Friction (0–100):** {scoreboard.get('friction_0_100')}")
    lines.append(f"- **Evidence threshold (%):** {scoreboard.get('evidence_threshold_pct')}")
    lines.append(f"- **Coordination latency (turns):** {scoreboard.get('coord_latency_turns')}")
    lines.append("")
    lines.append("## Sensitivity (Top Stressors by Impact)")
    if sensitivity:
        for k, v in sensitivity[:10]:
            lines.append(f"- {k}: Δ {v:+.1f}")
    else:
        lines.append("- —")
    lines.append("")
    lines.append("## Event Log (Operational Trace)")
    if event_log:
        for e in event_log[-80:]:
            lines.append(f"- {e}")
    else:
        lines.append("- —")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Outputs are comparative decision-test artifacts; they do not predict real-world actions.")
    return "\n".join(lines)

def build_aar_pdf_bytes(markdown_text: str) -> bytes:
    """
    Minimal PDF builder from markdown text.
    Uses reportlab if available; otherwise returns UTF-8 bytes of markdown.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        return markdown_text.encode("utf-8")

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    x = 50
    y = height - 60
    line_h = 12

    for raw_line in markdown_text.splitlines():
        line = raw_line.replace("\t", "    ")
        if y < 60:
            c.showPage()
            y = height - 60
        c.drawString(x, y, line[:110])
        y -= line_h

    c.save()
    return buf.getvalue()
