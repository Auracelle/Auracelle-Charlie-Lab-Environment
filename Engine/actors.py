"""
engine/actors.py — Actor profile loading and management.

Reads config/actors.yaml and provides helpers used by the simulation
engine and Streamlit pages.
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

_ACTORS_YAML = Path(__file__).parent.parent / "config" / "actors.yaml"

# ── Canonical baseline actor profiles ─────────────────────────────────────────

def load_actor_profiles() -> dict[str, dict[str, Any]]:
    """Return the full actor dict keyed by actor name."""
    with open(_ACTORS_YAML, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return raw.get("actors", {})


def get_actor_names() -> list[str]:
    """Sorted list of actor names defined in config/actors.yaml."""
    return sorted(load_actor_profiles().keys())


def get_iso3_map() -> dict[str, str]:
    """Map actor name → ISO3 code (omits actors with null iso3)."""
    profiles = load_actor_profiles()
    return {
        name: data["iso3"]
        for name, data in profiles.items()
        if data.get("iso3")
    }


def build_rl_actor_profiles(actor_names: list[str]) -> dict[str, dict]:
    """
    Build the actor_profiles dict expected by EAGPOEnv.

    Each entry contains:
      - centrality      : normalised influence score used for network weighting
      - institutional_capacity : proxy from influence score (fallback 0.55)
      - reward_weights  : (coop_w, defect_w, tighten_w)
    """
    raw = load_actor_profiles()
    result: dict[str, dict] = {}
    for name in actor_names:
        if name not in raw:
            # safe default for actors not in YAML
            result[name] = {
                "centrality": 0.5,
                "institutional_capacity": 0.55,
                "reward_weights": (1.0, -1.0, 0.5),
            }
            continue
        d = raw[name]
        inf = float(d.get("influence", 0.5))
        result[name] = {
            "centrality": inf,
            "institutional_capacity": min(inf + 0.05, 1.0),
            "reward_weights": (1.0, -1.0, 0.5),
        }
    return result
