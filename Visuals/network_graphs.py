"""
visuals/network_graphs.py — NetworkX influence graph helpers.

These functions produce Plotly figures; they do not contain Streamlit calls.
Pages call these and pass the returned figure to st.plotly_chart().
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import plotly.graph_objects as go


def build_influence_graph(actor_data: dict[str, dict]) -> nx.DiGraph:
    """
    Build a directed influence graph from actor profile data.

    Edges are added where cultural alignment partially overlaps;
    edge weight = geometric mean of the two actors' influence scores.
    """
    G = nx.DiGraph()
    actors = list(actor_data.keys())
    for name, data in actor_data.items():
        G.add_node(name, **data)

    # Add weighted edges based on influence proximity
    for i, a in enumerate(actors):
        for b in actors[i + 1:]:
            inf_a = float(actor_data[a].get("influence", 0.5))
            inf_b = float(actor_data[b].get("influence", 0.5))
            weight = float(np.sqrt(inf_a * inf_b))
            G.add_edge(a, b, weight=weight)
            G.add_edge(b, a, weight=weight)
    return G


def influence_graph_figure(
    actor_data: dict[str, dict],
    highlight: list[str] | None = None,
    title: str = "Actor Influence Network",
) -> go.Figure:
    """
    Return a Plotly figure of the influence network.

    Parameters
    ----------
    actor_data  : dict keyed by actor name; values have 'influence', 'gdp', 'position'
    highlight   : list of actor names to highlight (larger marker)
    title       : chart title
    """
    G = build_influence_graph(actor_data)
    pos = nx.spring_layout(G, seed=42, k=1.5)

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=0.6, color="#475569"),
        hoverinfo="none",
    )

    highlight = set(highlight or [])
    node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        d = actor_data.get(node, {})
        inf = float(d.get("influence", 0.5))
        node_x.append(x)
        node_y.append(y)
        node_text.append(
            f"<b>{node}</b><br>Influence: {inf:.2f}<br>GDP: ${d.get('gdp', 0):.1f}T<br>{d.get('position', '')}"
        )
        node_size.append(20 + 25 * inf if node in highlight else 12 + 20 * inf)
        node_color.append("#38bdf8" if node in highlight else "#64748b")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        hoverinfo="text",
        hovertext=node_text,
        text=list(G.nodes()),
        textposition="top center",
        textfont=dict(size=10, color="#e2e8f0"),
        marker=dict(size=node_size, color=node_color, line=dict(width=1.5, color="#0f172a")),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=dict(text=title, font=dict(size=14)),
            showlegend=False,
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=420,
        ),
    )
    return fig


def centrality_bar_figure(actor_data: dict[str, dict]) -> go.Figure:
    """Bar chart of actor influence scores, sorted descending."""
    G = build_influence_graph(actor_data)
    centrality = nx.degree_centrality(G)
    actors  = sorted(centrality, key=centrality.get, reverse=True)
    values  = [centrality[a] for a in actors]

    fig = go.Figure(go.Bar(
        x=actors, y=values,
        marker_color=["#38bdf8" if v == max(values) else "#475569" for v in values],
    ))
    fig.update_layout(
        title="Network Centrality by Actor",
        yaxis_title="Degree Centrality",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig
