"""Common pixel observation and episode lifecycle contract."""

from typing import ClassVar

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class PixelEnv(gym.Env):
    metadata: ClassVar[dict] = {"render_modes": ["rgb_array"], "render_fps": 9}

    def __init__(self, action_names, shape, max_steps, render_mode="rgb_array"):
        if render_mode not in (None, "rgb_array"):
            raise ValueError("Only rgb_array rendering is supported")
        if not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError("max_steps must be a positive integer")
        self.render_mode = render_mode
        self.action_names = tuple(action_names)
        self.action_space = spaces.Discrete(len(action_names))
        self.observation_space = spaces.Box(0, 255, shape, dtype=np.uint8)
        self.max_steps = max_steps
        self.steps = 0
        self.ended = True
        self.frame = np.zeros(shape, np.uint8)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        self.ended = False
        return self.frame.copy(), {}

    def _check_action(self, action):
        if self.ended:
            raise RuntimeError("Call reset before stepping a new or completed episode")
        if not self.action_space.contains(action):
            raise ValueError(f"Action must be an integer in [0, {self.action_space.n})")

    def _transition(self, reward, terminated, info, *, timed_out=False):
        self.steps += 1
        truncated = not terminated and (timed_out or self.steps >= self.max_steps)
        self.ended = bool(terminated or truncated)
        return self.frame.copy(), float(reward), bool(terminated), bool(truncated), info

    def render(self):
        return self.frame.copy() if self.render_mode == "rgb_array" else None

    def close(self):
        self.ended = True
