"""
tests/test_scenario_engine.py — Unit tests for engine/scenario_engine.py

Run: pytest tests/test_scenario_engine.py -v
"""
import numpy as np
import pytest

from engine.scenario_engine import (
    EAGPOEnv,
    QAgent,
    COOPERATE,
    TIGHTEN,
    DEFECT,
    ACTION_NAMES,
)

# ── Fixture: minimal actor profiles ──────────────────────────────────────────

@pytest.fixture
def minimal_profiles():
    return {
        "Alpha": {
            "centrality": 0.8,
            "institutional_capacity": 0.7,
            "risk_weight": 0.6,
            "sanction_sensitivity": 0.3,
            "reward_weights": (1.0, -1.0, 0.5),
        },
        "Beta": {
            "centrality": 0.5,
            "institutional_capacity": 0.55,
            "risk_weight": 0.5,
            "sanction_sensitivity": 0.4,
            "reward_weights": (1.0, -1.0, 0.5),
        },
    }


@pytest.fixture
def env(minimal_profiles):
    return EAGPOEnv(minimal_profiles)


# ── EAGPOEnv tests ────────────────────────────────────────────────────────────

class TestEAGPOEnv:
    def test_initial_state_shape(self, env):
        state = env.reset()
        assert state.shape == (3,), "State should be a 3-element array"

    def test_initial_state_values(self, env):
        state = env.reset()
        assert 0.0 <= state[0] <= 1.0, "tension out of range"
        assert 0.0 <= state[1] <= 1.0, "stability out of range"
        assert 0.0 <= state[2] <= 1.0, "sanction_pressure out of range"

    def test_step_returns_correct_types(self, env):
        actions = {"Alpha": COOPERATE, "Beta": COOPERATE}
        next_state, rewards, done = env.step(actions)
        assert isinstance(next_state, np.ndarray)
        assert isinstance(rewards, dict)
        assert isinstance(done, bool)

    def test_step_all_cooperate_lowers_tension(self, env):
        env.reset()
        env.tension = 0.5  # force known starting tension
        actions = {"Alpha": COOPERATE, "Beta": COOPERATE}
        for _ in range(5):
            state, _, _ = env.step(actions, shock_sigma=0.0)
        assert state[0] <= 0.5, "All-cooperate should not raise tension"

    def test_step_all_defect_raises_tension(self, env):
        env.reset()
        env.tension = 0.4
        actions = {"Alpha": DEFECT, "Beta": DEFECT}
        for _ in range(5):
            state, _, _ = env.step(actions, shock_sigma=0.0)
        assert state[0] > 0.4, "All-defect should raise tension"

    def test_state_clamped_to_unit_interval(self, env):
        actions = {"Alpha": DEFECT, "Beta": DEFECT}
        for _ in range(30):
            state, _, _ = env.step(actions, shock_sigma=0.05)
        assert all(0.0 <= v <= 1.0 for v in state), "State values must stay in [0, 1]"

    def test_durability_positive(self, env):
        env.reset()
        d = env.durability()
        assert d >= 0.0, "Durability should be non-negative"

    def test_done_after_20_steps(self, env):
        actions = {"Alpha": COOPERATE, "Beta": COOPERATE}
        done = False
        for _ in range(21):
            _, _, done = env.step(actions, shock_sigma=0.0)
        assert done, "Episode should be done after 20 steps"

    def test_configure_initial_state(self, minimal_profiles):
        env = EAGPOEnv(minimal_profiles)
        env.configure_initial_state(tension=0.8, stability=0.2, sanction_pressure=0.6)
        state = env.reset()
        assert abs(state[0] - 0.8) < 1e-6
        assert abs(state[1] - 0.2) < 1e-6
        assert abs(state[2] - 0.6) < 1e-6

    def test_history_appended_each_step(self, env):
        env.reset()
        actions = {"Alpha": COOPERATE, "Beta": COOPERATE}
        for i in range(3):
            env.step(actions)
        assert len(env.history) == 3

    def test_rewards_have_actor_keys(self, env):
        actions = {"Alpha": COOPERATE, "Beta": DEFECT}
        _, rewards, _ = env.step(actions)
        assert set(rewards.keys()) == {"Alpha", "Beta"}

    def test_missing_risk_weight_defaults_gracefully(self):
        """Engine should not KeyError if risk_weight absent from profiles."""
        profiles = {
            "X": {"centrality": 0.5, "institutional_capacity": 0.5}
        }
        env = EAGPOEnv(profiles)
        actions = {"X": COOPERATE}
        state, rewards, done = env.step(actions)
        assert "X" in rewards


# ── QAgent tests ──────────────────────────────────────────────────────────────

class TestQAgent:
    def test_choose_returns_valid_action(self):
        agent = QAgent("test")
        state = np.array([0.4, 0.6, 0.2])
        action = agent.choose(state)
        assert action in (COOPERATE, TIGHTEN, DEFECT)

    def test_update_modifies_q_table(self):
        agent = QAgent("test", alpha=1.0, gamma=0.0, epsilon=0.0)
        s  = np.array([0.4, 0.6, 0.2])
        s2 = np.array([0.5, 0.5, 0.3])
        agent.update(s, COOPERATE, 1.0, s2)
        key = tuple(np.round(s, 2))
        assert key in agent.q
        assert agent.q[key][COOPERATE] == pytest.approx(1.0, abs=1e-6)

    def test_epsilon_zero_is_greedy(self):
        agent = QAgent("test", epsilon=0.0)
        state = np.array([0.4, 0.6, 0.2])
        # Prime the Q table with a known best action
        key = tuple(np.round(state, 2))
        agent.q[key] = np.array([0.0, 5.0, 0.0])  # TIGHTEN is best
        action = agent.choose(state)
        assert action == TIGHTEN

    def test_epsilon_one_is_random(self):
        """With epsilon=1.0 all choices are random — just verify no crash."""
        agent = QAgent("test", epsilon=1.0)
        state = np.array([0.4, 0.6, 0.2])
        actions = {agent.choose(state) for _ in range(20)}
        assert len(actions) >= 1  # at least some action chosen


# ── Action space ──────────────────────────────────────────────────────────────

def test_action_names_coverage():
    assert set(ACTION_NAMES.keys()) == {COOPERATE, TIGHTEN, DEFECT}
    assert all(isinstance(v, str) for v in ACTION_NAMES.values())
