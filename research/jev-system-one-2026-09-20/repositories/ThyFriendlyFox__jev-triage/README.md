# jev-triage

Route unlabeled training data with [TypeSafe Jev](https://typesafe.ai): **accept** cheap high-confidence judgments, **queue** the rest for a frontier teacher or humans, and **log soft labels** for optional local distillation.

| | |
|---|---|
| **Repo purpose** | Confidence-gated **labeling budget** allocator (pattern #3: active learning triage) |
| **Sibling** | [jev-curate](https://github.com/ThyFriendlyFox/jev-curate) — drop bad rows *before* triage (pattern #1) |
| **Deep dive** | [GOALS.md](GOALS.md) — success criteria, anti-goals, mock vs live |
| **Both repos** | [docs/STACK.md](docs/STACK.md) — recommended order |

---

## What problem this solves

You have a large corpus and several questions per row (valid? category? urgency?). An LLM judge on every row is too slow and too expensive. Jev answers typed questions in one parallel call with **probabilities**, so you can:

- Auto-label the easy majority (`accepted.jsonl`)
- Send middling cases to GPT/Claude/VLM (`teacher_queue.jsonl`)
- Send boundaries and low confidence to annotators (`human_queue.jsonl`)

**Jev does not replace ground truth.** Success means you still label teacher/human queues and train on **real outcomes** where they exist — Jev is the router, not the teacher of record.

---

## What success looks like (short)

Read the full checklist in [GOALS.md](GOALS.md). In one paragraph:

> You ran live Jev over JSONL with a rubric you trust, got three queues plus `soft_labels.jsonl`, finished labeling teacher/human rows authoritatively, built a training set from **accepted + relabeled** rows, and measured your model on **held-out human (or outcome) labels** — not on “Jev agreed with itself.”

---

## Quick start

```bash
pip install -e ".[dev]"
export TYPESAFE_API_KEY="sk-..."   # production

jev-triage run \
  --rubric examples/support-tickets/rubric.yaml \
  --input examples/support-tickets/corpus.jsonl \
  --output .output/support-tickets

jev-triage stats --output .output/support-tickets
```

| Flag / env | Meaning |
|------------|---------|
| `TYPESAFE_API_KEY` | Live Jev via `typesafe-sdk` |
| `--mock` | Deterministic fake Jev — **tests and plumbing only** |
| (no key, no flag) | Defaults to mock — install key before real datasets |

---

## Examples

Worked scenarios with **SUCCESS.md** per folder:

| Example | Command output intent |
|---------|------------------------|
| [support-tickets](examples/support-tickets/) | Department + urgency routing |
| [audio-transcripts](examples/audio-transcripts/) | Post-Whisper lexical triage |
| [weak-labels](examples/weak-labels/) | Vendor labels — trust vs re-label |

Index: [examples/README.md](examples/README.md)

Legacy paths `examples/rubric.yaml` and `examples/corpus.jsonl` mirror **support-tickets** for backward compatibility.

---

## Outputs

| File | Use |
|------|-----|
| `accepted.jsonl` | Provisional labels at your accept thresholds |
| `teacher_queue.jsonl` | Batch for expensive model labeling |
| `human_queue.jsonl` | Annotator tool import |
| `soft_labels.jsonl` | Distributions for KL/BCE distillation experiments |
| `errors.jsonl` | Fix and re-run; completed `id`s are skipped |

---

## Rubric (thresholds)

Each question is a Jev `noul`, `choice`, or `score` with **accept_confidence** and **teacher_confidence**:

- Above **accept** → contributes toward **accept** route (worst question wins overall)
- Between **teacher** and **accept** → **teacher**
- Below **teacher**, or Noul ≈ 0.5, or Choice top-2 within 0.15 → **human**

```yaml
questions:
  - name: department
    type: choice
    instructions: Which team should handle this?
    criteria:
      billing: Payment or refund issues
      technical: Bugs or outages
    accept_confidence: 0.85
    teacher_confidence: 0.55
```

---

## Pipeline placement

```
Raw JSONL
  → jev-curate (optional)     drop garbage / label mismatch
  → jev-triage (this repo)     accept | teacher | human
  → label queues               humans / frontier models
  → train                      targets = real outcomes
  → optional local student     distill from soft_labels.jsonl
```

---

## Mock vs live (read this)

| | Live Jev | Mock |
|---|----------|------|
| **Use when** | Production triage, threshold tuning | `pytest`, CI, learning the CLI |
| **Probabilities** | Calibrated enough to route | Heuristic keyword toy |
| **Success** | Queues match spot-checks | Exit 0 + resume works |

**Never** publish a dataset or model based only on mock routing.

---

## Development

```bash
pytest
jev-triage validate-rubric --rubric examples/support-tickets/rubric.yaml
```

## License

MIT
