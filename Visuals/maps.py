"""
visuals/maps.py — 3D influence map and geographic map helpers.

The full 3D AlphaFold-style influence map is in pages/07_3D_Influence_Map.py
(preserved verbatim from the notebook).  This module provides the
underlying data-preparation functions so they can be unit-tested separately
from the Streamlit page code.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


def build_3d_positions(actor_data: dict[str, dict]) -> dict[str, tuple[float, float, float]]:
    """
    Map actors to 3D positions.

    X = economic strength (GDP, log-normalised)
    Y = influence score (0–1)
    Z = policy position alignment proxy (hash-based, 0–1)
    """
    positions: dict[str, tuple[float, float, float]] = {}
    for name, d in actor_data.items():
        gdp = float(d.get("gdp", 0.1))
        x = float(np.clip(np.log1p(gdp) / np.log1p(25), 0, 1))
        y = float(d.get("influence", 0.5))
        z = float((hash(d.get("position", "")) % 1000) / 1000)
        positions[name] = (x, y, z)
    return positions


def influence_map_3d_figure(
    actor_data: dict[str, dict],
    title: str = "3D Actor Influence Map",
) -> go.Figure:
    """
    Return a Plotly 3D scatter figure of actors by GDP / Influence / Position.
    """
    positions = build_3d_positions(actor_data)
    actors = list(positions.keys())

    x_vals = [positions[a][0] for a in actors]
    y_vals = [positions[a][1] for a in actors]
    z_vals = [positions[a][2] for a in actors]
    sizes  = [12 + 20 * positions[a][1] for a in actors]

    alignment_groups = list(set(d.get("cultural_alignment", "Other") for d in actor_data.values()))
    color_map = {g: i for i, g in enumerate(alignment_groups)}
    colors = [color_map.get(actor_data[a].get("cultural_alignment", "Other"), 0) for a in actors]

    hover = [
        f"<b>{a}</b><br>GDP: ${actor_data[a].get('gdp', 0):.2f}T"
        f"<br>Influence: {actor_data[a].get('influence', 0):.2f}"
        f"<br>{actor_data[a].get('position', '')}"
        for a in actors
    ]

    trace = go.Scatter3d(
        x=x_vals, y=y_vals, z=z_vals,
        mode="markers+text",
        text=actors,
        hovertext=hover,
        hoverinfo="text",
        marker=dict(
            size=sizes,
            color=colors,
            colorscale="Viridis",
            opacity=0.85,
            line=dict(width=0.5, color="#0f172a"),
        ),
        textposition="top center",
        textfont=dict(size=9, color="#e2e8f0"),
    )

    fig = go.Figure(data=[trace])
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="Economic Strength (GDP)",
            yaxis_title="Influence Score",
            zaxis_title="Policy Position",
            xaxis=dict(range=[0, 1]),
            yaxis=dict(range=[0, 1]),
            zaxis=dict(range=[0, 1]),
            bgcolor="rgba(10,16,34,0.9)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        height=500,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig
