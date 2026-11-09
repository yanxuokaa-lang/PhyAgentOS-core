import json

import numpy as np
import pytest

gym = pytest.importorskip("gymnasium")
pytest.importorskip("chess")

from gymnasium.utils.env_checker import check_env

from litjev.games import make_env
from litjev.games.policy import LitJevPolicy
from litjev.games.rollout import record_episode


def test_chess_gym_contract_seed_and_controller_move():
    env = make_env("chess", max_steps=100)
    try:
        check_env(env.unwrapped, skip_render_check=False)
        observation, info = env.reset(seed=8)
        assert env.observation_space.contains(observation)
        assert env.action_space == gym.spaces.Discrete(5)
        assert "fen" not in info and "legal_moves" not in info
        # Starting cursor e1 -> e2, lift, e4, put. No direct move action.
        for key in [0, 4, 0, 0, 4]:
            observation, _reward, terminated, truncated, info = env.step(key)
        assert info["event"] == "put" and info["move"] == "e2e4"
        assert not terminated and not truncated
        assert env.unwrapped.board.fullmove_number == 2  # random opponent also moved
        assert observation.shape == (480, 640, 3)
        first = observation.copy()
        env.reset(seed=8)
        for key in [0, 4, 0, 0, 4]:
            observation, *_ = env.step(key)
        np.testing.assert_array_equal(first, observation)
        with pytest.raises(ValueError):
            env.step(5)
    finally:
        env.close()
        env.close()


def test_chess_truncation_and_no_oracle_rescue():
    with make_env("chess", max_steps=2) as env:
        env.reset(seed=1)
        env.step(1)  # hit lower edge
        _, _, terminated, truncated, info = env.step(1)
        assert info["event"] == "edge"
        assert truncated and not terminated
        with pytest.raises(RuntimeError):
            env.step(0)


def test_doom_real_headless_gym_contract():
    pytest.importorskip("vizdoom")
    with make_env("doom", max_steps=3, resolution="160x120") as env:
        observation, _ = env.reset(seed=2)
        assert env.observation_space.contains(observation)
        assert env.action_space.n == 7
        first = observation.copy()
        observation2, _ = env.reset(seed=2)
        np.testing.assert_array_equal(first, observation2)
        for _ in range(3):
            observation, reward, terminated, truncated, _ = env.step(6)
            assert env.observation_space.contains(observation)
            if terminated or truncated:
                break
        assert terminated or truncated
        assert isinstance(reward, float)


class RecordingClient:
    model_id = "fake"

    def __init__(self):
        self.calls = []

    def decide(self, state, schema, image):
        self.calls.append((state, schema, image.copy()))
        labels = list(schema["action"]["criteria"])
        return {
            "result": {
                "model": "fake",
                "answers": {
                    "action": {
                        "type": "choice",
                        "choice": labels[0],
                        "confidence": 1.0,
                        "probabilities": {label: float(i == 0) for i, label in enumerate(labels)},
                    }
                },
                "usage": {"output_tokens": 0, "input_tokens": 42},
            },
            "diagnostics": {
                "calibration_fitted": False,
                "forward_calls": 2,
                "fields": {
                    "action": {
                        "logits": list(range(len(labels))),
                        "provenance": {"module": "lm_head"},
                    }
                },
            },
        }


def test_same_policy_and_trace_for_both_environments(tmp_path):
    for name in ["chess", "doom"]:
        client = RecordingClient()
        with make_env(name, max_steps=2) as env:
            policy = LitJevPolicy(client, env.unwrapped.action_names, env.unwrapped.instructions)
            trace = record_episode(env, policy, seed=3, episode=1)
        assert len(client.calls) == 2
        assert trace["schema_version"] == "litjev.trace.v1"
        assert trace["training"] is False
        assert trace["decisions"][-1]["truncated"]
        assert trace["decisions"][0]["frame"].startswith("data:image/png;base64,")
        assert trace["decisions"][0]["forward_calls"] == 2
        assert trace["decisions"][0]["action"] == env.unwrapped.action_names[0]
        assert not any(
            term in client.calls[0][0] for term in ["fen", "enemy_position", "legal_moves"]
        )
        json.dumps(trace, allow_nan=False)


def test_policy_rejects_unknown_answer_and_wrong_probability_shape():
    client = RecordingClient()
    policy = LitJevPolicy(client, ("left", "right"), "Choose a key.")
    client.decide = lambda *a: {
        "result": {"answers": {"action": {"choice": "invented"}}},
        "diagnostics": {},
    }
    with pytest.raises(ValueError):
        policy.decide(np.zeros((8, 8, 3), np.uint8))
