# openjev

One-pass option scoring with a local Gemma 3 4B, on Apple silicon via MLX or on
NVIDIA/CPU via PyTorch (`--backend torch`).
Design notes: [docs/design/one-pass-option-scoring.md](docs/design/one-pass-option-scoring.md);
per-task training: [docs/design/per-task-finetuning-with-gemma.md](docs/design/per-task-finetuning-with-gemma.md).

Given a context and a list of pre-written options, the model prefills the
context once, expands that KV cache across the option batch, and scores every
option in a single padded forward pass. No decoding. The score is the
log-probability of the option tokens given the context; a softmax over the
option scores gives a probability per option, like `jevlike-predict`.

## Setup

```sh
make setup       # uv sync (arm64 Python 3.12 venv) + download google/gemma-3-4b-it into models/ (gated; needs HF login)
make serve       # start the HTTP server on :8000
make health      # curl /health
make request     # example curl against /score
make systemone   # TypeSafe-style request against /v1/systemone
make check       # verify cached batched scoring against naive re-encoding
make bench       # latency benchmark
make eval DATA=data/synthetic/test.jsonl
```

`make setup` picks the backend extra for the platform: `mlx` (plus `torch`, for the jevlike comparison
and HF cross-checks) on macOS, `torch` alone elsewhere. Installing by hand:

```sh
uv sync --extra mlx --extra torch   # Apple silicon
uv sync --extra torch               # NVIDIA or CPU
```

Both backends are optional extras, so a bare `uv sync` installs neither. `mlx` in particular must not
be installed off Apple silicon: it resolves on Linux without its `libmlx.so`, and `transformers`
finds the metadata, tries to import it, and dies -- taking the torch backend down with it.

`make` on macOS needs the Xcode licence accepted (`sudo xcodebuild -license accept`) or Homebrew's `gmake`.

## Usage

```sh
# Rank options for one context (prints probability, score, raw sum, token count)
.venv/bin/openjev score --context "The capital of France is" \
    --option " Paris" --option " Berlin" --option " Lyon"

# Chat template (context as user turn, options scored as the reply) + PMI normalisation
.venv/bin/openjev score --chat --norm pmi --context "..." --option "..." --option "..."

# Predefined options: one per line in a text file, reused for every context
.venv/bin/openjev score --options-file options.txt --context "..."
.venv/bin/openjev eval contexts.jsonl --fixed-options options.txt   # rows need only {"context": ...}; add "label" for accuracy

# Top-1 / top-3 accuracy on jevlike-style JSONL: {"context": ..., "options": [...], "label": 0}
.venv/bin/openjev eval data.jsonl --norm mean

# Verify the cached batched path against naive re-encoding, and benchmark it
.venv/bin/openjev check
.venv/bin/openjev bench --context-tokens 200 --options 8 --option-tokens 30
```

## Server

Loads the model once and answers scoring requests in about 90 ms each. Runs natively on macOS with
Metal, or on Linux/NVIDIA with `--backend torch` (see below); the MLX path has no container story,
because Linux containers cannot reach the Apple GPU.

```sh
make serve                                     # = .venv/bin/openjev serve --port 8000
curl -s localhost:8000/score -H 'content-type: application/json' -d '{
  "context": "Customer: my order arrived broken. Agent:",
  "options": [" I am sorry, I will send a replacement.", " Please read our returns policy."],
  "norm": "mean", "chat": false, "sep": ""
}'
```

The response has `best`, `best_index`, per-option `probability` / `logprob_sum` / `n_tokens`, and `timing`.

## TypeSafe System One contract

`POST /v1/systemone` implements the request/response shape documented at
[docs.typesafe.ai](https://docs.typesafe.ai): a `state` (string, object or array) plus a map of typed
`questions`, answered against that state.

```sh
make systemone     # sends examples/systemone-quickstart.json; or:
curl -s localhost:8000/v1/systemone -H 'content-type: application/json' -d '{
  "state": "I ordered size 10 shoes but received size 8. Please send the right size.",
  "model": "jev-latest",
  "questions": {
    "department":  {"type": "choice", "instructions": "Which department handles this?",
                    "criteria": {"returns": "Returns and exchanges", "shipping": "Delivery issues", "billing": "Charges and refunds"}},
    "severity":    {"type": "score",  "instructions": "How severe is the problem?",
                    "criteria": ["minor", "moderate: wrong item", "major: safety or financial loss"]},
    "wants_refund":{"type": "noul",   "instructions": "Is the customer asking for a refund to their card?"}
  }
}'
```

| question `type` | request `criteria` | answer fields |
|---|---|---|
| `choice` | map of option name to description (string, object, array or null); up to 255 options | `choice`, `probabilities` (sum to 1), `confidence` |
| `score` | ordered array of level descriptions | `score` (probability-weighted mean of level index), `probabilities` keyed `"0".."n-1"`, `legend`, `confidence` |
| `noul` | optional `{"true": ..., "false": ...}` | `noul` = probability of yes |

Response: `{"model", "answers": {id: answer}, "usage": {"input_tokens", "output_tokens"}}`.
Set `OPENJEV_API_KEY` before `make serve` to require `Authorization: Bearer <key>` on this route.

How it maps onto the scorer: each question is rendered to a plain-text prompt (state, instructions,
options or levels, then `Answer:` and a newline) and the option names, level numbers, or `yes`/`no`
are scored as continuations in one prefix-shared batched pass per question. `confidence` is 1 minus
the normalised entropy of the distribution; TypeSafe does not publish its formula, so treat it as an
approximation. `usage.output_tokens` counts the candidate-label tokens that were scored.

Comparison on the docs' quick-start request (`examples/systemone-quickstart.json`), Gemma 3 4B
zero-shot vs the numbers TypeSafe publishes for Jev:

| answer | Jev (docs) | openjev / Gemma 3 4B |
|---|---|---|
| `department.choice` | technical, p=0.84, confidence 0.60 | technical, p=1.00, confidence 1.00 |
| `frustration.score` | 1.04 (annoyed but polite) | 2.00 (furious) |
| `is_urgent.noul` | 0.999 | 0.005 |

Same routing decision, but Gemma is over-confident and disagrees on the two judgement calls. Zero-shot
probabilities are softmaxed next-token likelihoods, not calibrated judgements. Closing the gap means
labelled data and a trained head (below).

## Training a head (per-task, on frozen Gemma features)

```sh
make features    # one prefix-shared pass per example, cached to runs/feats/{train,validation,test}.npz
make train       # jevlike's cross-attention head in MLX, listwise cross-entropy -> runs/head.safetensors
make eval-head   # top-1/top-3, ECE, and the shuffled-context control on the test split
```

- `openjev features DATA --out F.npz` stops Gemma before the LM head, keeps every context token's
  final hidden state and the masked-mean of each option's tokens (float16). Options are encoded on
  their own, as in jevlike, so the head has to do the matching. `--contextual` encodes them as
  continuations of the context instead: stronger features, but the match leaks into the option
  vectors and the shuffled-context control below stops meaning anything.
- `openjev train` = AdamW 5e-4 (2e-3 diverges on Gemma features, whose norms are ~115), weight decay 1e-4, grad clip 1.0, 8 epochs, batch 64, best validation
  epoch kept. The checkpoint is `head.safetensors` plus `head.json` (rank, hidden size, training config).
- `openjev eval-head` reports what `jevlike-eval` reports: top-1, top-3, 10-bin expected calibration
  error, and the same metrics with every example paired with another example's context. If the
  shuffled number does not collapse, the head is reading option priors rather than the state.

Result on the synthetic split (2000 train / 400 validation / 400 test, 2026-09-17): features at
77 ms per example, head training 8 epochs in about 15 s.

| | top-1 | top-3 | ECE |
|---|---|---|---|
| head on frozen Gemma features, test | 0.970 | 1.000 | 0.027 |
| same head, shuffled-context control | 0.258 | 0.698 | 0.724 |
| jevlike tiny byte encoder, test | 0.998 | 1.000 | 0.008 |
| Gemma zero-shot, `--norm sum`, test | 1.000 | 1.000 | n/a |

The control sits at chance (about 4.5 options per row), so the head really matches options to the
state, and its ECE of 0.03 is what a calibrated `confidence` looks like.

Python:

```python
from openjev import OptionScorer
s = OptionScorer("models/gemma-3-4b-it", batch_size=8)
for r in s.score("The capital of France is", [" Paris", " Berlin"], norm="mean"):
    print(r.option, r.probability, r.logprob_sum, r.n_tokens)
print(s.last_timing)
```

### Normalisation (`--norm`)

| norm | score | use when |
|---|---|---|
| `mean` (default) | sum of option-token log-probs divided by token count | options are the same length in tokens |
| `sum` | total log-prob | options differ in length, or you want raw likelihood |
| `pmi` | sum minus the option's unconditional log-prob (BOS-only context) | options differ in base-rate plausibility; costs one extra batched pass |

Check the `n_tokens` column before trusting the ranking: when it differs between options, the choice
of norm, not the model, is deciding. Asking Qwen 2.5 1.5B for the capital of Italy, `" Torino"` is
two tokens and `" Roma"` is one, so `mean` divides Torino's much worse total (-7.85, against Roma's
-4.04) by two and puts it first at 49.9%. `sum` gives Roma 87.3%. `pmi` is worse again here at 85.1%
for Torino, because it divides out the unconditional probability and "Torino" is the rarer word --
the base rate was the signal, not the nuisance. Tokenisation makes this model-specific: Gemma 3 has
all four city names as single tokens, so `mean` and `sum` agree and the trap never appears.

## PyTorch backend (NVIDIA / CPU)

Every command takes `--backend torch`, which swaps `mlx`/`mlx-lm` for `transformers`+`torch` and
keeps the same design: prefill the context once, replicate its KV cache across the option batch,
score in one padded forward pass. `openjev check` verifies that path against naive per-option
re-encoding on either backend. The server also reads `OPENJEV_BACKEND`.

```sh
openjev score --backend torch --norm sum --model Qwen/Qwen2.5-1.5B-Instruct \
    --context "The capital of France is" --option " Paris" --option " Berlin"

openjev check  --backend torch --model Qwen/Qwen2.5-1.5B-Instruct   # cached vs naive
openjev serve  --backend torch --model google/gemma-3-4b-it --quantize 4bit
```

### Quantisation (`--quantize`)

`none` (default) is bf16; `8bit` and `4bit` go through bitsandbytes, `4bit` as NF4 with double
quantisation and a bf16 compute dtype. The server also reads `OPENJEV_QUANTIZE`. Quantised weights
are pinned to GPU 0, because bitsandbytes cannot run a module that accelerate parked on the CPU and
`device_map="auto"` offloads on a small card even when the model would fit.

Gemma 3 4B it on an RTX A2000 Laptop (4 GB), 160 examples, bf16 as the reference:

| `--quantize` | VRAM | median latency | agreement with bf16 | same, where bf16 is confident |
|---|---|---|---|---|
| `none` (bf16) | 2.6 GB + **2.9B params offloaded to CPU** | 2114 ms | -- | -- |
| `8bit` | 4.8 GB (**over the 4 GB card**) | 963 ms | 0.825 | 0.858 |
| `4bit` | 3.1 GB | **211 ms** | 0.825 | 0.875 |

bf16 does not fit: two thirds of the weights end up on the CPU and every forward pass streams them
back, which is where the 2.1 s comes from. `8bit` is the worst of the three here -- it overflows the
card *and* is no more faithful than `4bit`. Note what the last column means: even at its best, 4-bit
flips about one confident decision in eight. Fine for ranking, not free if you depend on the
probabilities being calibrated. Smaller models degrade more, not less (Qwen 0.5B agrees with its own
bf16 only 0.675 of the time), so quantise the big model rather than shrinking to a small one.

Same workload as the MLX table below (202-token context, 8 options, 242 option tokens), Gemma 3 4B
in 4-bit on the same 4 GB card:

| path | median latency |
|---|---|
| context cached once, options batched | 0.63 s |
| context re-encoded per option, no cache | 4.25 s |

`openjev check` compares log-probs with an absolute tolerance (`--tol`, default 0.5) that does not
scale with context length, so quantised runs over long contexts need `--tol 1.0` to pass on what is
ordinary NF4 noise (0.4% relative).

## Measured on M5 Pro, 64 GB (MLX, bf16)

Workload: 202-token context, 8 options, 242 option tokens total.

| path | median latency |
|---|---|
| context cached once, options batched | 0.17 s |
| context re-encoded per option, no cache | 0.68 s |

Model load is about 1 s from a warm disk. First forward pass adds under a second of warm-up.

## Validating against jevlike

`jevlike` is installed into the same venv (`uv pip install -e ../../vinnylarouge/jevlike`), so both
CLIs read the same JSONL. Generate its synthetic menu set, then score it both ways:

```sh
.venv/bin/jevlike-data synthetic --output data/synthetic
.venv/bin/openjev eval data/synthetic/test.jsonl --norm sum --sep $'\nChoice: '
.venv/bin/jevlike-train data/synthetic/train.jsonl --validation data/synthetic/validation.jsonl \
    --output runs/synthetic-tiny.pt --device mps
.venv/bin/jevlike-eval runs/synthetic-tiny.pt data/synthetic/test.jsonl --device mps
```

Results on the 400-row synthetic test set (2026-09-16):

| scorer | training | top-1 | top-3 | median latency / example |
|---|---|---|---|---|
| openjev, Gemma 3 4B zero-shot, `--norm sum` | none | 1.000 | 1.000 | 0.086 s |
| openjev, `--norm mean` | none | 0.988 | 1.000 | 0.086 s |
| openjev, `--norm pmi` | none | 0.988 | 1.000 | 0.153 s |
| jevlike tiny byte encoder + head | 2000 rows, 8 epochs | 0.998 | 1.000 | well under 10 ms |

The synthetic task is easy for both. The real validation is your own labelled rows: run
`openjev eval` on them zero-shot and compare against a `jevlike-train`/`jevlike-eval` run on the
same split. If Gemma zero-shot is close to the trained head, Route B is enough; if not, train a head
(Route A) with `make features && make train && make eval-head`.

## Demo: Doom in the terminal

`demo/doom/` runs ViZDoom headless, describes each frame in a line of text, and
lets the server rank the action menu with one `/score` call (or one System One
`choice` question). Start `make serve`, then `make doom`. Details and keys in
[`demo/doom/README.md`](demo/doom/README.md).

![openjev playing Doom in the terminal: the model ranks the action menu each step](docs/media/doom-recording.gif)

Full-resolution recording: [docs/media/doom-recording.mov](docs/media/doom-recording.mov).

## Layout

- `openjev/scorer.py`: `OptionScorer` (prefill, cache expansion, batched scoring, naive reference).
- `openjev/systemone.py`: System One request/answer models, prompt renderers, zero-shot answers.
- `openjev/server.py`: FastAPI app, `/health`, `/score`, `/v1/systemone`.
- `openjev/features.py`: frozen-Gemma feature extraction and the `.npz` feature cache.
- `openjev/head.py`: jevlike's cross-attention head in `mlx.nn`, save/load.
- `openjev/train.py`: head training loop and evaluation (top-k, ECE, shuffled-context control).
- `openjev/cli.py`: `openjev score | eval | bench | check | serve | features | train | eval-head`.
- `openjev/{scorer,features,head,train}_torch.py`: the `--backend torch` counterparts of the four
  modules above (`transformers` + `torch`, bitsandbytes quantisation). `systemone.py`, `server.py`
  and `cli.py` are backend-agnostic and import a backend only when one is selected.
- `demo/doom/`: Doom in the terminal, the server picks every action (`make doom`).
- `models/`: downloaded weights (git-ignored).
