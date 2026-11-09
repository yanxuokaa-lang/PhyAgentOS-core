"""Optional Gymnasium environments; importing LitJev itself does not require games."""

import gymnasium as gym
from gymnasium.envs.registration import register, registry

for name, entry in {
    "LitJev/ChessKeys-v0": "litjev.games.chess:ChessKeysEnv",
    "LitJev/DoomButtons-v0": "litjev.games.doom:DoomButtonsEnv",
}.items():
    if name not in registry:
        register(id=name, entry_point=entry)


def make_env(name, **kwargs):
    names = {"chess": "LitJev/ChessKeys-v0", "doom": "LitJev/DoomButtons-v0"}
    if name not in names:
        raise ValueError(f"Unknown environment {name!r}; choose chess or doom")
    return gym.make(names[name], **kwargs)
