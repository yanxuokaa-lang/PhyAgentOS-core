# Chess

Five-key visual chess-controller port using unmodified Qwen weights through LitJev.
The policy sees pixels, not FEN or legal-move text. The opponent is seeded random.

```bash
uv run --locked --extra games python examples/chess/play.py --max-steps 100 --output runs/chess.json
```

Start the LitJev server first, or pass `--model /path/to/checkpoint` for local inference.
See [visual games](../../docs/visual-games.md) for Gym/API/film usage and limitations,
and [upstream attribution](../../THIRD_PARTY_NOTICES.md) for the MIT source license.
