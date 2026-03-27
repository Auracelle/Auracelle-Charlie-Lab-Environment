"""
visuals/dashboards.py — Reusable Plotly chart helpers for KPI dashboards.

All functions return go.Figure objects; callers pass them to st.plotly_chart().
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def kpi_gauge(value: float, title: str, low_threshold: float = 0.35, high_threshold: float = 0.65) -> go.Figure:
    """Single KPI gauge chart. Value should be in [0, 1]."""
    if value <= low_threshold:
        color = "#22c55e"  # green
    elif value <= high_threshold:
        color = "#f59e0b"  # amber
    else:
        color = "#ef4444"  # red

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        number={"suffix": "%", "font": {"size": 24}},
        title={"text": title, "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "steps": [
                {"range": [0, low_threshold * 100],   "color": "rgba(34,197,94,0.12)"},
                {"range": [low_threshold * 100, high_threshold * 100], "color": "rgba(245,158,11,0.12)"},
                {"range": [high_threshold * 100, 100], "color": "rgba(239,68,68,0.12)"},
            ],
        },
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def metrics_line_chart(
    trace: list[dict],
    metrics: list[str] | None = None,
    title: str = "Session Metrics Trace",
) -> go.Figure:
    """Multi-line chart from a list of round metric dicts."""
    if not trace:
        return go.Figure().update_layout(title=title, height=300)
    df = pd.DataFrame(trace)
    metrics = metrics or [c for c in ["trust", "compliance", "alignment", "resilience", "tension", "systemic_risk"] if c in df.columns]
    fig = go.Figure()
    x_col = "round" if "round" in df.columns else df.index
    for m in metrics:
        if m in df.columns:
            fig.add_trace(go.Scatter(x=df[x_col], y=df[m], name=m.replace("_", " ").title(), mode="lines+markers"))
    fig.update_layout(
        title=title,
        xaxis_title="Round",
        yaxis_title="Score (0–1)",
        legend=dict(orientation="h"),
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def durability_area_chart(durability_by_ep: list[float], title: str = "Treaty Durability by Episode") -> go.Figure:
    """Area chart of durability across training episodes."""
    episodes = list(range(1, len(durability_by_ep) + 1))
    fig = go.Figure(go.Scatter(
        x=episodes, y=durability_by_ep,
        mode="lines",
        fill="tozeroy",
        line=dict(color="#38bdf8", width=1.5),
        fillcolor="rgba(56,189,248,0.15)",
        name="Durability",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Episode",
        yaxis_title="Durability",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def actor_radar_chart(actor_data: dict[str, dict], actors: list[str]) -> go.Figure:
    """Radar / spider chart comparing selected actors across key dimensions."""
    categories = ["GDP", "Influence", "Mil Exp", "Internet"]
    fig = go.Figure()
    for actor in actors:
        d = actor_data.get(actor, {})
        # Normalise to 0-1 for radar display
        values = [
            min(float(d.get("gdp", 0)) / 25.0, 1.0),           # GDP norm vs NATO ceiling
            float(d.get("influence", 0)),
            min(float(d.get("mil_exp", 0)) / 10.0, 1.0),        # mil_exp norm vs 10% ceiling
            float(d.get("internet", 0)) / 100.0,
        ]
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=actor,
            opacity=0.7,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        height=380,
        margin=dict(l=0, r=0, t=20, b=0),
        title="Actor Capability Radar",
    )
    return fig


def sankey_trade_figure(
    actor: str,
    partners: list[str],
    values: list[float],
    title: str = "Trade Flow",
) -> go.Figure:
    """Simple Sankey diagram for trade flows from one actor to partners."""
    n = len(partners)
    sources = [0] * n
    targets = list(range(1, n + 1))
    labels = [actor] + partners

    fig = go.Figure(go.Sankey(
        node=dict(pad=15, thickness=20, label=labels,
                  color=["#38bdf8"] + ["#64748b"] * n),
        link=dict(source=sources, target=targets, value=values,
                  color=["rgba(56,189,248,0.3)"] * n),
    ))
    fig.update_layout(title=title, height=350, margin=dict(l=0, r=0, t=40, b=0))
    return fig
