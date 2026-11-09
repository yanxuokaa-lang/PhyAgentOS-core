# Benchmarking

Two kinds of benchmarks ship with LitJev: text decisions on MMLU-Pro, and visual
decisions in Doom and chess. Both use the same off-the-shelf Qwen weights, without
training, and both talk to the running LitJev server.

## MMLU-Pro

With the server running:

```bash
uv run litjev-mmlu --split test --limit 10 --output mmlu-results.json
```

Downloads `TIGER-Lab/MMLU-Pro`, sends ten questions per request, and scores labels
locally. Gold answers and CoT explanations never enter inference prompts. This is
**direct-answer scoring, not the standard CoT benchmark protocol**. `--prepare-only`
exports requests without inference; `--revision COMMIT` pins the dataset snapshot.
Incomplete final batches use duplicate padding excluded from metrics. Invalid or
non-MCQ records are skipped with reasons.

A **historical, pre-migration** ten-question smoke experiment on one H100 80 GB
achieved 9/10 and approximately 0.472 s per warm ten-question request (mean of three
repeats). This is not a full MMLU-Pro score or a latency guarantee. Repeated questions
are not extra test examples; loading, queueing, and HTTP overhead are excluded from
this measurement. It used the old shared question catalog, not the current isolated
question branches. No current 27B accuracy/latency result is claimed by this migration.

See [Slurm usage](slurm.md) for configurable cluster launchers. Raw local experiment
outputs are excluded from the public distribution because they contain machine
paths, hostnames, and dataset text.

## Visual games: Doom and chess

Play from screenshots. The ported Doom (seven buttons) and chess (five controller
keys) examples share a Gymnasium interface and a LitJev policy supporting either
local inference or HTTP.

```bash
# Start the model server, then run a game in another terminal.
uv run --locked --extra games litjev --model Qwen/Qwen3.8-27B
uv run --locked --extra games litjev-play chess --max-steps 100 --output runs/chess.json
uv run --locked --extra games litjev-play doom --max-steps 100 --output runs/doom.json
uv run --locked --extra games litjev-film runs/chess.json --output runs/chess.html
```

Open `/film` to inspect traces, or open the standalone HTML. The screenshot playground
also accepts PNG/JPEG uploads. Only the debug API adds an optional base64 `image`
field; it never substitutes hidden game state or text descriptions for pixels.
See [visual games](visual-games.md) for the complete interface, timing boundaries,
MP4 export, and limitations. No gameplay quality or real-time performance is promised.
The examples are adapted from [jevlike](https://github.com/vinnylarouge/jevlike), with
[MIT attribution retained](../THIRD_PARTY_NOTICES.md).

## Reporting results

Separate cold and warm timings, and report hardware, precision, model revision,
batch size, synchronization, and timing boundaries. Do not claim GPU or full-dataset
verification unless performed.
