# openjev classifier

Natural language inference with [AlexWortega/openjev](https://huggingface.co/AlexWortega/openjev), a Qwen3.5-4B cross-encoder that reads a premise and a hypothesis and answers with `contradiction`, `entailment`, or `neutral`.

`classify.py` is a single self-contained script exposing pair classification, multiple-choice rerank, a library API, and a CLI.

## Requirements

- Python 3.10 or newer (3.13 tested) — `transformers` 5.x and `torch` 2.14 both require it
- `torch` and `transformers`
- About 9.1 GB of disk for the checkpoint, plus roughly 2 GB resident while running

## Setup

```bash
brew install python@3.13
python3.13 -m venv .venv
.venv/bin/pip install torch transformers
```

The checkpoint is 9.1 GB, so point the Hugging Face cache somewhere with room before the first run. This matters on machines whose home volume is nearly full:

```bash
export HF_HOME=/path/to/roomy/volume/hf-cache
.venv/bin/hf download AlexWortega/openjev --include "qwen3.5-4b-nli/*"
```

Downloading is optional — the first run fetches the checkpoint automatically into `HF_HOME`.

## Usage

Classify a single pair:

```bash
.venv/bin/python classify.py classify \
  --premise "A man is playing a guitar." \
  --hypothesis "Someone is making music."
```

```
entailment     0.8727  contradiction=0.0016  entailment=0.8727  neutral=0.1257
```

Classify many pairs from a JSONL or CSV file:

```bash
.venv/bin/python classify.py classify --input pairs.jsonl
.venv/bin/python classify.py classify --input pairs.csv --json
```

JSONL entries and CSV rows both need `premise` and `hypothesis` fields:

```json
{"premise": "A man is playing a guitar.", "hypothesis": "A man is sleeping."}
```

Pick the option best entailed by a question:

```bash
.venv/bin/python classify.py rerank \
  --question "Which gas do plants absorb during photosynthesis?" \
  --option oxygen --option "carbon dioxide" --option nitrogen
```

```
1	carbon dioxide
```

`rerank` prints the zero-based index and the winning option. Add `--json` for `{"index": 1, "option": "carbon dioxide"}`.

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--model` | `AlexWortega/openjev` | Hugging Face repository id |
| `--subfolder` | `qwen3.5-4b-nli` | Checkpoint subfolder |
| `--device` | `auto` | `auto`, `cpu`, `mps`, or `cuda` |
| `--precision` | `bfloat16` | `bfloat16`, `float16`, or `float32` |
| `--batch-size` | `8` | Pairs per forward pass |
| `--max-length` | `256` | Tokenizer truncation length |
| `--threads` | auto | Torch CPU thread count. Auto picks 2 when the checkpoint exceeds physical RAM, otherwise half the cores |
| `--keep-vision-tower` | off | Retain unused vision weights |

## Library API

```python
from classify import ClassifierFactory, OpenJevSettings, TextPair

classifier = ClassifierFactory.create(OpenJevSettings())

predictions = classifier.classify([
    TextPair("A man is playing a guitar.", "Someone is making music."),
    TextPair("A man is playing a guitar.", "A man is sleeping."),
])

predictions[0].label          # <NliLabel.ENTAILMENT: 1>
predictions[0].confidence     # 0.8727...
predictions[0].probabilities  # {CONTRADICTION: 0.0016, ENTAILMENT: 0.8727, NEUTRAL: 0.1257}

classifier.rerank("Which gas do plants absorb during photosynthesis?",
                  ["oxygen", "carbon dioxide", "nitrogen"])  # 1
```

`ClassifierFactory.create` caches its result, so repeated calls with equal settings reuse one loaded model rather than reloading 9 GB.

## Design notes

The checkpoint dictates its own preprocessing, and deviating from it silently degrades accuracy:

- Label order is `contradiction=0`, `entailment=1`, `neutral=2`, fixed by the checkpoint's `id2label`.
- Input is a single string built from the checkpoint's `nli_template`: `Premise: {premise}\nHypothesis: {hypothesis}`.
- The classification head pools the **last non-pad token**, so the tokenizer is right-padded. This is not interchangeable with `[CLS]` or mean pooling.
- `max_length` defaults to 256 because the checkpoint's `train_result.json` records `max_len: 256` over 120k training examples. The upstream reference snippet uses 4096, which is both far more expensive and a train/inference mismatch.

Runtime choices worth keeping:

- `torch.inference_mode()` rather than `no_grad`, so no autograd graph is retained across activations.
- `attn_implementation="sdpa"` is set explicitly. Transformers silently downgrades to `eager` on CPU, which would materialize a roughly 1 GB attention matrix per full-attention layer.
- The vision tower (0.667 GB of the checkpoint) is never executed for text-only input, since both image branches sit behind an explicit `pixel_values is not None` guard. It is deleted after load unless `--keep-vision-tower` is passed.
- `--device auto` selects MPS only when the checkpoint is smaller than `torch.mps.recommended_max_memory()`; otherwise it stays on CPU. An unknown checkpoint size is treated as *not* fitting, so a failed metadata lookup degrades to CPU rather than attempting an allocation that would fail.
- Thread count is chosen from whether the checkpoint exceeds physical RAM. When it does, weights are paged in from disk and the work is I/O-bound, so extra threads only add competing requests for the same slow reads. Measured on this machine, going from 2 to 8 threads made a single classification **2.4x slower**. When the checkpoint does fit, the work is compute-bound and half the cores is the better choice.

## Performance

Measured on an Apple M2 with 8 GB RAM, CPU, bf16, `max_length=256`:

| Metric | Value |
|---|---|
| Model load | ~12 s |
| Classification, repeated in one process | ~26 s per pair |
| Classification, single pair including load and startup | 130–192 s |
| Rerank | ~37 s per pair |
| Maximum resident set size | 1.3–1.7 GB |
| Swap used | 0 |

Treat these as order-of-magnitude figures. Wall clock varies by nearly 50% run to run, because the workload is I/O-bound and the timing depends heavily on page-cache state; the same single-pair command has been observed at both 130 s and 192 s. Only comparisons made back to back within one process are reliable.

The checkpoint is 9.1 GB but the process peaks near 1.5 GB. Weights stay file-backed and the OS reclaims those pages rather than swapping, so the model does fit on a machine with less RAM than the checkpoint size — at the cost of speed. Roughly 440k page faults against 153k page reclaims, with CPU utilisation around 3%, show that per-pair latency is dominated by re-reading weights rather than by compute. A faster host volume is therefore the most direct speedup available.

The `qwen3_5` linear-attention layers fall back to pure-PyTorch reference implementations, since `causal_conv1d` and `flash-linear-attention` ship no CPU kernels. Transformers prints a warning about this on load; it is expected and the output is unaffected.

## Accuracy

The checkpoint's own `train_result.json` reports `eval_accuracy: 0.8985` on 2,000 held-out examples, and the model repository's `results/summary.md` reports MNLI-m 0.904 / MNLI-mm 0.907. Correct wiring on standard NLI pairs should land near 0.90. A result distribution that looks degenerate — one label pinned near 1.0 on every input — indicates the label order or last-token pooling has been broken.
