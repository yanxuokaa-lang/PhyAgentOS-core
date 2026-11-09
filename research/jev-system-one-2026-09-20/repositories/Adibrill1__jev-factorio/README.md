# jev-factorio

A Jev-powered Factorio agent. Jev (TypeSafe AI's System One model) makes the
fast macro decisions - goal, next action, stuck detection - as typed
Choice/Score/Noul questions; deterministic code owns game rules, option
filtering, and actuation. To our knowledge this is the first Jev-driven
game agent.

Docs: [ARCHITECTURE](docs/ARCHITECTURE.md) | [BUILD PLAN](docs/BUILD_PLAN.md)

## Quick start (offline, no key, no game)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
PYTHONPATH=src python -m jev_factorio --backend mock --steps 8 --tick-seconds 0
```

With a real key (`TYPESAFE_API_KEY` in the environment) the same loop calls
`jev-latest` at `https://api.typesafe.ai/v1/systemone`.

## Layout

- `src/jev_factorio/state.py` - GameSnapshot + compact Jev-facing state
- `src/jev_factorio/questions.py` - typed question builders + candidate-action filter
- `src/jev_factorio/jev_client.py` - SDK/HTTP client + offline MockJevClient
- `src/jev_factorio/loop.py` - observe -> ask -> gate on confidence -> act
- `src/jev_factorio/backends/` - mock (working), play_api (skeleton), fle (skeleton)
