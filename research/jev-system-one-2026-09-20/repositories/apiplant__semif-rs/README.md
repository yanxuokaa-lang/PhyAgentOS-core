# semif-rs

A Rust + [candle](https://github.com/huggingface/candle) port of [SemIf](https://openjev.com)'s
worker.js demo: a side-by-side comparison of two ways to get a typed decision out of a small
open-weight chat model (Qwen3), run locally with no server round-trip.

Given a **state**, a **question**, and 2–20 **options**, it runs the same prompt through both
lanes and prints wall-clock, token counts, and the resulting distribution for each:

- **02A / direct readout** — one forward pass. The prompt asks for a single option letter; the
  model's next-token logits are read directly at the label-token positions and softmaxed, so the
  reported probabilities are exactly the model's own logprobs over the allowed options — no
  sampling, no decode loop.
- **02B / generation** — autoregressive: the model greedy-decodes a full JSON object mapping
  every option to a probability (grammar-constrained the way the original site does it via
  logit bias, reproduced here as a JSON-prefill + validation pass matching `worker.js`'s
  `validateGeneration()`), then the parsed distribution is reported.

Supports `qwen3-0.6b` (Q8_0 GGUF) and `qwen3.5-4b` (Q4_K_M GGUF, using a from-scratch Gated
DeltaNet CUDA kernel in `src/gdn.rs` since candle-transformers doesn't ship Qwen3.5's linear
attention layer), both pinned to the same GGUF builds and tokenizer revisions the live site uses,
downloaded from Hugging Face Hub on first run.

## Usage

```bash
# built-in presets ("account": support routing, "email": phishing triage)
cargo run --release -- --preset account
cargo run --release -- --preset email --model qwen3.5-4b

# your own decision
cargo run --release -- \
  --state "..." \
  --question "..." \
  --option "option a" --option "option b" --option "option c"

# CPU instead of CUDA
cargo run --release -- --preset account --cpu
```

Not affiliated with openjev.com / SemIf; this is an independent reimplementation for local,
offline comparison of the two decision lanes.
