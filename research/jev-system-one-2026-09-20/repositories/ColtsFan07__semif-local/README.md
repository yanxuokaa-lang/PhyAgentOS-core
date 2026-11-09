# semif-local

One-command local setup for [SemIf](https://github.com/TheoLeeCJ/SemIf) (formerly **OpenJev**, [openjev.com](https://openjev.com/)) — typed decisions from open models, on your own hardware.

SemIf reproduces the *interface pattern* of TypeSafe's closed **Jev** service with open models: give it unstructured state + a question + allowed options, and it reads typed option probabilities **directly from the model's logits** (one forward pass, zero generated tokens) — or, as a baseline, has the model write the same distribution as JSON token by token. It is an independent research project, not affiliated with TypeSafe.

This repo is a thin setup wrapper. It pins upstream at a known commit, bootstraps a venv, and gives you two ways to run it locally.

## Two ways to use it

### A. Browser demo — any machine, no backend

```bash
make demo          # serves http://127.0.0.1:8175/webgpu-demo/
```

Open the URL in a WebGPU browser (Chrome/Edge 113+). Pick a model, click load — weights download from Hugging Face **into your browser cache** (639 MB / 1.56 GB / 3.01 GB), then everything runs on your GPU. Inputs never leave the page.

| Model | Download | Authored balanced accuracy |
|---|---:|---:|
| Qwen3 0.6B | 639 MB | 0.440 |
| MiniCPM5 2B | 1.56 GB | 0.686 |
| Qwen3.5 4B | 3.01 GB | **0.813** |
| Published Jev (closed, hosted) | — | 0.883 |

### B. CLI scoring — machine with an NVIDIA GPU

```bash
make setup         # clone (pinned) + .venv + pip install -e './SemIf[test]'
make models        # pre-pull pinned Qwen3.5-4B BF16 (~8 GB) into ./hf-cache
make score         # runs the upstream owned example -> results/example-direct.jsonl
```

Requirements: Python 3.10+, CUDA, a GPU that can hold a 4B BF16 model (~8 GB VRAM — a 3090/4090 is plenty). If your default `python3` is too new for a dependency, use `PYTHON=python3.11 make setup`.

Each result row carries typed option scores, timing, the exact model revision, and a prompt hash. All rows sharing one identical state can use `--mode shared` to prefill the state once and evaluate criteria in parallel.

Bring your own decisions (JSONL, one per line):

```json
{
  "id": "route-1",
  "state": "Customer cannot access an account after a password reset.",
  "question": "Which queue should handle this request?",
  "options": [
    {"id": "access", "description": "Account access support."},
    {"id": "billing", "description": "Billing support."}
  ]
}
```

```bash
./score.sh --mode direct --model Qwen/Qwen3.5-4B \
  --revision 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a \
  --input my-decisions.jsonl --output results/mine.jsonl
```

## What lands where

| Path | What | Created by |
|---|---|---|
| `SemIf/` | upstream clone, detached at the pinned commit | `make setup` |
| `.venv/` | Python env with `semif-score` installed editable | `make setup` |
| `hf-cache/` | HuggingFace weights (CLI path) | `make models` / first run |

None of these are committed — they're rebuilt by the scripts.

## Pins

- Upstream: `TheoLeeCJ/SemIf` @ `b9cb32537e78be65f19abfcb1de8fc504b627d84` (master, 2026-09-18)
- Model revision (4B): `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` — same revision upstream's README uses

To move the pin: `SEMIF_SHA=<sha> ./setup.sh`, or `make clean` and re-run to take the new default.

## Housekeeping

- `make clean` removes the venv, cache, clone, and results.
- Upstream docs worth reading: [Results](https://github.com/TheoLeeCJ/SemIf/blob/master/docs/RESULTS.md), [Method](https://github.com/TheoLeeCJ/SemIf/blob/master/docs/METHOD.md), [Reproduce](https://github.com/TheoLeeCJ/SemIf/blob/master/docs/REPRODUCE.md).

## License & attribution

This wrapper: MIT. Upstream SemIf: MIT. Baseline models keep their own licenses and are fetched from Hugging Face at run time. Jev/TypeSafe are marks of their respective owners; this project and SemIf are independent and unaffiliated.
