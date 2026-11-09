# System One Gemma — Open-Source Jev-Style Decision Model

> **LLMs generate text. This just decides. 200x faster. 200x cheaper.**

An open-source implementation of the **System One** scoring architecture, inspired by [TypeSafe.ai's Jev model](https://typesafe.ai) — the AI that famously [plays Doom in real-time](https://www.theregister.com/ai-and-ml/2026/09/16/typesafe-ai-debuts-model-for-machines-that-plays-doom/5296711).

Jev is a massive breakthrough in AI — a model designed for **machines**, not humans. It doesn't generate text. It makes **fast, calibrated decisions** from a fixed set of options in a single forward pass. The problem? **Jev is closed-source.**

So I built this. I used **Google's Gemma 3 270M** — one of the smallest LLMs available (268M parameters) — because that's all I could run locally with no GPU. And it works **shockingly well** for its size. Imagine what this architecture could do with a bigger model.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/akash-kamat/system-one-gemma/blob/main/system_one_gemma3_270m.ipynb)

---

## What Is a System One Model?

Traditional LLMs work like this:
```
Input → Generate tokens one by one → Parse the text → Extract answer
         (slow, expensive, 2-10 seconds)
```

System One works like this:
```
Input → Score all options at once → Softmax → Probabilities
         (single forward pass, 50ms)
```

No text generation. No chain-of-thought. No parsing. Just: **"given this situation and these choices, which one?"** — with calibrated confidence scores.

### The Three Question Types

| Type | What it does | Example |
|------|-------------|---------|
| **Choice** | Pick from unordered options | "Route this ticket to: billing / technical / sales" |
| **Noul** (Yes/No) | Binary decision | "Is this message written in English?" |
| **Score** | Pick from an ordered scale | "Rate this review: 1 star / 2 stars / 3 stars / 4 stars / 5 stars" |

### How It Actually Works (Under the Hood)

For each option, the model builds a text sequence:

```
State:
  My internet is down since yesterday. I work from home.

Question:
  Which support queue?

Option:
  technical support
```

Each sequence goes through the transformer → last token hidden state → linear scoring head → **one number**.

Do this for all options, softmax across them:

```
technical support  →  78.3%   ████████████████████████████████
billing            →  11.2%   ████
general inquiry    →   6.1%   ██
sales              →   2.8%   █
cancellation       →   1.6%   █
```

All options scored in **one batched forward pass**. That's it.

---

## How Jev Plays Doom (And How This Could Too)

Jev plays Doom by reading the **game state as structured text** every frame:

```json
{
  "health": 73, "ammo_shotgun": 4,
  "enemies": [{"type": "imp", "distance": 150, "angle": 12}],
  "nearby_items": ["medikit at distance 80"]
}
```

Then it asks: **"What action? Options: shoot, move_forward, turn_left, retreat..."**

And picks the best one. 10+ times per second. No text generation, no reasoning — just fast reflexes. Like System 1 thinking in humans (hence the name).

This repo includes a Doom-style demo scenario you can try right now.

---

## Results

Trained on 12,913 questions across 6 tasks, evaluated on held-out data:

| Metric | Value |
|--------|-------|
| **Overall Accuracy** | 64.4% |
| **ECE (Calibration Error)** | 0.047 |
| **Brier Score** | 0.454 |
| **Model Size** | 268M parameters (LoRA: ~2.6M trainable) |
| **Training Time** | ~15 min on free Colab T4 |

The accuracy is modest (it's a 270M model!) but the **calibration is excellent** — when it says 80% confidence, it's right ~80% of the time. That's the real value: you can trust the probabilities.

### Why Calibration Matters More Than Accuracy

An LLM that says "I'm 95% sure it's billing" but is wrong 40% of the time is **dangerous**.
A System One model that says "62% technical, 28% billing, 10% other" and is **actually right 62% of the time** is **useful** — you can set thresholds, escalate low-confidence cases, and build reliable pipelines.

---

## Quick Start

### Option 1: Try it in Colab (No Setup Required)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/akash-kamat/system-one-gemma/blob/main/system_one_gemma3_270m.ipynb)

The notebook trains the model from scratch on a free T4 GPU in ~15 minutes.

### Option 2: Run Locally (CPU Works Fine)

```bash
git clone https://github.com/akash-kamat/system-one-gemma.git
cd system-one-gemma
pip install -r requirements.txt
```

**Note:** Gemma is a gated model. You need to:
1. Accept the license at https://huggingface.co/google/gemma-3-270m
2. Log in: `huggingface-cli login`

#### CLI Inference

```bash
python infer.py \
  --state "My internet has been down since yesterday" \
  --question "Which support queue?" \
  --options "billing,technical,sales,general"
```

Output:
```
  78.3%  ################################  technical
  11.2%  ####                              billing
   6.1%  ##                                general
   4.4%  #                                 sales

Answer: technical (confidence: 78.3%)
```

#### Web Interface (Gradio)

```bash
python app.py
```

Opens a browser UI with preset demos and custom input.

#### Python API

```python
from infer import load_trained_model, score

tok, model = load_trained_model("./pretrained-scorer")

probs = score(model, tok,
    state="Patient has chest pain radiating to left arm, ST elevation on ECG",
    question="What is the triage level?",
    options=["non-urgent", "semi-urgent", "urgent", "emergency"])

# probs = [0.02, 0.05, 0.31, 0.62]  → emergency
```

---

## Train Your Own Model

### On Google Colab (Recommended)

1. Open the [notebook](https://colab.research.google.com/github/akash-kamat/system-one-gemma/blob/main/system_one_gemma3_270m.ipynb)
2. Set runtime to **T4 GPU** (Runtime → Change runtime type)
3. Run all cells
4. Download the trained model as a zip

The notebook trains on 6 public datasets:
- **banking77** — 77-class banking intent classification
- **go_emotions** — emotion detection (yes/no per emotion)
- **ag_news** — 4-class news topic classification
- **MMLU** — multiple choice knowledge questions
- **yelp_score** — 1-5 star review rating
- **customer support tickets** — queue routing, priority, ticket type

### With Your Own Data

Format your data as a list of dicts:

```python
{"task": "my_task", "question_type": "choice", "ordered": False,
 "state": "the context text",
 "question": "What category?",
 "options": ["cat_a", "cat_b", "cat_c"],
 "answer_index": 1}
```

Then use `system_one.py`:

```bash
python system_one.py train --local-data-dir ./my-data --out-dir ./my-model
```

### With a Bigger Model

The architecture works with any Gemma model. To use a larger one:

```bash
python system_one.py train --base-model google/gemma-3-1b --out-dir ./my-model-1b
```

Bigger models = better accuracy, same architecture. The 1B model should significantly outperform the 270M one.

---

## Architecture

```
                    ┌─────────────────────────────────┐
                    │     For each option:             │
                    │                                  │
Input text ───────► │  "State: ...\nQuestion: ...\n    │
(state +            │   Option: billing"               │
question +          │           │                      │
one option)         │     ┌─────▼──────┐               │
                    │     │ Gemma 3    │               │
                    │     │ Transformer│               │
                    │     │  (270M)    │               │
                    │     └─────┬──────┘               │
                    │           │                      │
                    │     last token                   │
                    │     hidden state                 │
                    │           │                      │
                    │     ┌─────▼──────┐               │
                    │     │  Linear    │──► 1 scalar   │
                    │     │  (score)   │    (logit)    │
                    │     └────────────┘               │
                    └─────────────────────────────────┘
                                 │
              Repeat for all options, then softmax
                                 │
                                 ▼
                    [0.78, 0.11, 0.06, 0.03, 0.02]
                    probabilities over option set
```

**Key design choices:**
- **LoRA fine-tuning** (rank 16) — only 2.6M trainable params out of 268M
- **Scoring head** — single linear layer, not a classification head
- **Last-token pooling** — the option text is always at the end so it's never truncated
- **Temperature calibration** — fitted on validation set, applied at inference

---

## Repo Structure

```
system-one-gemma/
├── README.md                          # this file
├── system_one.py                      # full training script (CLI)
├── infer.py                           # standalone inference
├── app.py                             # Gradio web interface
├── demos.json                         # preset demo scenarios
├── requirements.txt                   # pip dependencies
├── system_one_gemma3_270m.ipynb       # Colab notebook (train from scratch)
└── pretrained-scorer/                 # pre-trained LoRA adapter
    ├── adapter_config.json
    ├── adapter_model.safetensors
    ├── metrics.json
    ├── tokenizer.json
    └── tokenizer_config.json
```

---

## Comparison: System One vs LLM

| | System One (270M) | GPT-4o / Claude | Notes |
|---|---|---|---|
| **Latency** | ~50ms | 2-10 seconds | 40-200x faster |
| **Output** | Probabilities | Free-form text | System One is deterministic |
| **Cost** | ~$0.001 / 1K decisions | ~$0.15 / 1K calls | 150x cheaper |
| **Can generate text?** | No | Yes | Use an LLM for that |
| **Calibrated confidence?** | Yes (ECE: 0.047) | No | System One's key advantage |
| **Can run on CPU?** | Yes, fast | Impractical | 270M model fits anywhere |

**Use them together:** System One handles the fast, repetitive decisions (routing, scoring, classifying). LLM handles the creative, open-ended work (writing, reasoning, conversation). You save 90%+ on the decisions that don't need an LLM.

---

## Inspired By

- **[TypeSafe.ai's Jev](https://typesafe.ai)** — the original System One model. Closed-source, but a genuine breakthrough in AI architecture. This project exists because Jev showed that non-generative decision models are viable and powerful.
- **[The Register: TypeSafe AI debuts model for machines that plays Doom](https://www.theregister.com/ai-and-ml/2026/09/16/typesafe-ai-debuts-model-for-machines-that-plays-doom/5296711)** — the article that explains what Jev is and why it matters.
- **Daniel Kahneman's "Thinking, Fast and Slow"** — System 1 (fast, intuitive) vs System 2 (slow, deliberate). This model is System 1.

---

## License

Apache 2.0 — use it however you want.

Note: The customer support tickets training data component is CC-BY-NC-4.0, so the pretrained weights inherit a non-commercial restriction. Train on your own data to remove this.

---

## Contributing

This is early. Ideas welcome:
- Train on more/better data
- Try larger Gemma models (1B, 4B)
- Build a game integration (Doom, anyone?)
- Add streaming / WebSocket API for real-time scoring
- Benchmark against Jev when/if they publish numbers

Open an issue or PR.
