# Doom

Seven-key ViZDoom port using screenshots and unmodified Qwen weights through LitJev.
No training or upstream policy checkpoint is required.

```bash
uv run --locked --extra games python examples/doom/play.py --max-steps 100 --output runs/doom.json
```

Start the LitJev server first, or pass `--model /path/to/checkpoint` for local inference.
See [visual games](../../docs/visual-games.md) for Gym/API/film usage and limitations,
and [upstream attribution](../../THIRD_PARTY_NOTICES.md) for the MIT source license.
