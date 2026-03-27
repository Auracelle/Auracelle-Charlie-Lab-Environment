"""
engine/rounds.py — Round execution logic.

Orchestrates one simulation round: collect actions → step environment →
compute metrics → log to DB.  Keeps page code thin.
"""
from __future__ import annotations

from typing import Any

from engine.scenario_engine import EAGPOEnv, QAgent, ACTION_NAMES, COOPERATE, TIGHTEN, DEFECT
from engine.scoring import round_metrics_snapshot
from storage.research_store import log_move, set_outcomes


def run_round(
    env: EAGPOEnv,
    agents: dict[str, QAgent],
    human_actions: dict[str, int],
    session_id: str,
    participant_id: str,
    policy: str,
    shock_sigma: float = 0.02,
    stochastic: bool = False,
    actor_positions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Execute one round of the simulation.

    Parameters
    ----------
    env             : live EAGPOEnv instance
    agents          : dict of QAgents (may be partially human-controlled)
    human_actions   : dict actor_name → action int for human-controlled actors
    session_id      : current session UUID
    participant_id  : current participant UUID
    policy          : selected policy scenario label
    shock_sigma     : stochastic shock standard deviation
    stochastic      : if True, QAgents also use their ε-greedy policy
    actor_positions : dict actor_name → current position string (for alignment)

    Returns
    -------
    dict with keys: actions, action_names, state, rewards, metrics, event_log_entry
    """
    state_before = env.state()

    # Build final action dict: human overrides take precedence
    actions: dict[str, int] = {}
    for actor, agent in agents.items():
        if actor in human_actions:
            actions[actor] = human_actions[actor]
        else:
            actions[actor] = agent.choose(state_before)

    # Step environment
    next_state, rewards, done = env.step(actions, shock_sigma=shock_sigma)

    # Q-table update for all agents
    for actor, agent in agents.items():
        agent.update(state_before, actions[actor], rewards.get(actor, 0.0), next_state)

    # Metrics
    metrics = round_metrics_snapshot(
        next_state,
        actions,
        actor_positions or {},
        env.durability(),
    )

    # Persist to DB (best-effort; non-blocking on failure)
    _safe_log(session_id, participant_id, env.round, policy, actions, metrics, next_state)

    action_names = {actor: ACTION_NAMES[a] for actor, a in actions.items()}

    return {
        "round": env.round,
        "actions": actions,
        "action_names": action_names,
        "state": next_state,
        "rewards": rewards,
        "metrics": metrics,
        "done": done,
    }


def _safe_log(session_id, participant_id, round_num, policy, actions, metrics, state):
    try:
        import json
        log_move(
            session_id=session_id,
            participant_id=participant_id,
            round_num=round_num,
            policy=policy,
            action=json.dumps({k: ACTION_NAMES[v] for k, v in actions.items()}),
            state_json=json.dumps({
                "tension": float(state[0]),
                "stability": float(state[1]),
                "sanction_pressure": float(state[2]),
            }),
        )
        set_outcomes(
            session_id=session_id,
            trust=metrics["trust"],
            compliance=metrics["compliance"],
            alignment=metrics["alignment"],
            resilience=metrics["resilience"],
        )
    except Exception:
        pass  # Never crash the simulation on a DB write failure
