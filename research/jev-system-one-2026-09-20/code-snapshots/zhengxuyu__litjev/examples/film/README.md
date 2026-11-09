# Film

Port of the jevlike trace-to-film workflow, adapted for measured Qwen logits instead
of the upstream trained option-attention head. No synthetic activations or soundtrack.

Build an HTML replay with `uv run --extra games litjev-film TRACE.json --output runs/replay.html`
from the repository root. To produce a silent MP4, from this directory:

```bash
npm ci
npx playwright install chromium
npm test
node render-film.mjs ../../runs/replay.html ../../runs/replay.mp4 10
```

Requires an installed FFmpeg executable. Uses recorded wall time, refuses to overwrite
existing video files, and never loads a model. See [visual games](../../docs/visual-games.md)
for the trace contract and [third-party notices](../../THIRD_PARTY_NOTICES.md) for attribution.
