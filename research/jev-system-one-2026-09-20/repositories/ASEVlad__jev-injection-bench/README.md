# jev-injection-bench

Measuring whether [TypeSafe's Jev](https://typesafe.ai) is actually good at detecting prompt
injection — against public corpora and real baselines, rather than against test cases the
author wrote themselves.

**[Read the full report →](https://asevlad.github.io/jev-injection-bench/)** &nbsp;·&nbsp; [repo](https://github.com/ASEVlad/jev-injection-bench)

---

## Why this exists

Jev launched in September 2026: a model that returns typed decisions with calibrated
probabilities instead of generating text. Within days, two people built prompt-injection
guards on top of it — [`0xArx/jevegis`](https://github.com/0xArx/jevegis) and
[`CryptoOda/typesafe-guard`](https://github.com/CryptoOda/typesafe-guard).

Neither has evidence that the idea works. Each author wrote their own test cases (42 and 50
respectively), ran their tool on them, and reported near-perfect scores. The second author
says so himself in his README.

Public, independently-built attack corpora exist and are free to download. Nobody had run Jev
against any of them.

Two claims in particular were unverified:

1. **Over-defense.** Injection detectors are known to fire on harmless text containing trigger
   words. Jev claims to judge meaning rather than match keywords, so this is where it should win.
2. **Calibration.** TypeSafe claims that when Jev says 90%, it is right ~90% of the time. That
   claim is the main reason to pick Jev over anything else, and there is no published paper,
   reliability curve, or error metric behind it.

## Results

11,900 labelled prompts. Five detectors, each at its own default 0.5 cutoff, scored on the
11,849 rows all of them covered.

| Detector | Catch rate | False alarms | **Panic rate** | ECE | AUPRC | ROC-AUC |
|---|---|---|---|---|---|---|
| Jev v1 | 77.1% | **0.2%** | 2.1% | 0.071 | 0.977 | 0.987 |
| **Jev v2** | 77.6% | 0.3% | **1.5%** | 0.058 | **0.980** | **0.990** |
| Claude Haiku 4.5 | **86.7%** | 1.8% | 6.2% | **0.021** | 0.930 | 0.973 |
| PromptGuard-2 | 52.6% | 0.4% | 4.4% | 0.133 | 0.932 | 0.961 |
| PIGuard | 66.8% | 5.1% | 11.5% | 0.103 | 0.857 | 0.919 |

*Panic rate* = share of harmless-but-trigger-worded prompts wrongly flagged (the NotInject set).
*ECE* = expected calibration error; 0 means the confidence numbers are honest.

Every tool ships a different default cutoff, so the comparison that matters pins them all to the
same catch rate:

| Detector, all tuned to catch 95% of attacks | False alarms | **Panic rate** |
|---|---|---|
| **Jev v2** | **4.5%** | **16.5%** |
| Jev v1 | 4.8% | 23.0% |
| PromptGuard-2 | 19.2% | 40.1% |
| PIGuard | 40.7% | 44.0% |
| Claude Haiku 4.5 | 34.1% | 52.2% |

### What this says

**Jev is the best detector of the five.** It has the best threshold-free ranking (AUPRC 0.980 vs
0.857–0.932) and dramatically less over-defense, at roughly 1% of the LLM's cost and a median
290ms.

**But the calibration claim goes the wrong way.** Claude Haiku's stated confidence is ~3× better
calibrated (ECE 0.021 vs 0.058). Calibration is TypeSafe's headline differentiator, and against a
chat model simply asked to say how sure it was, Jev loses on exactly that axis.

The fair caveat: Claude occupies only 5 of 10 confidence bins — it is nearly bimodal and refuses
to be uncertain, which flatters the metric. Jev actually uses the middle of the range, and is wrong
there. That is the operationally dangerous version: TypeSafe's own docs recommend routing on
confidence in the 0.5–0.9 band, which is precisely where Jev's numbers do not mean what they say.

**Prompt wording moves the headline number 28%.** The two Jev variants are the same question in
different words. They agree closely overall (correlation 0.987, verdicts flip on 2.1% of rows) but
the panic rate moved from 23.0% to 16.5%. A single-phrasing benchmark reports one of those as if
it were the answer.

**Both purpose-built detectors come last.** PromptGuard-2 catches 52.6% of attacks at its default
cutoff and has the worst calibration of the five. PIGuard has the worst ranking (AUPRC 0.857) and
the worst over-defense (11.5%, rising to 18.6% on three trigger words).

That last one is the sharpest result here. PIGuard's paper is titled *Mitigating Over-defense in
Prompt Injection Guardrail Models* — reducing over-defense is its entire published contribution,
and it over-defends more than any other detector tested, including a general chat model. In
fairness its paper compares against other small guardrail models rather than frontier models or
Jev, so this does not contradict its published claim. But small specialist detectors have a poor
track record at this task, which makes Jev — also a small specialist — the interesting exception.

## The corpus

Four independently-built public datasets, normalised into one schema and deduplicated by
normalised text hash (703 duplicates dropped).

| Source | Rows | Role |
|---|---|---|
| [`xTRam1/safe-guard-prompt-injection`](https://huggingface.co/datasets/xTRam1/safe-guard-prompt-injection) | 10,028 | attacks + benign |
| [`jackhhao/jailbreak-classification`](https://huggingface.co/datasets/jackhhao/jailbreak-classification) | 872 | jailbreaks |
| [`deepset/prompt-injections`](https://huggingface.co/datasets/deepset/prompt-injections) | 661 | the classic set |
| [`leolee99/NotInject`](https://huggingface.co/datasets/leolee99/NotInject) | 339 | harmless, trigger-worded |

**11,900 rows total** — 3,464 attacks, 8,436 benign, 339 in the over-defense probe.

Lakera's PINT benchmark is *not* included: they publish the harness but keep the 4,314-input
dataset private, so it cannot be run by outsiders. This repo borrows PINT's category schema so
results are shaped comparably, and does not claim to have run PINT.

## Design

Every detector implements one interface and returns a **continuous score in [0,1]**, never a bare
verdict — that is what makes threshold sweeps and calibration analysis possible after the fact.

```python
class Detector(Protocol):
    name: str
    def predict(self, texts: list[str]) -> list[Prediction]: ...
```

The runner writes **every raw prediction to parquet**. API calls are paid for once; every table,
chart and rewrite of the report regenerates from the cache for free, and a crashed run resumes
instead of re-spending.

Failed rows carry `score=None`, never `0.0` — coercing a failure to zero would read as a confident
"benign". Coverage is reported alongside every metric so a partially-failed detector cannot look
good by accident.

## Reproducing

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"

export TYPESAFE_API_KEY=...      # or AI_GATEWAY_API_KEY for the Vercel route
export ANTHROPIC_API_KEY=...     # for the Claude baseline
export HF_TOKEN=...              # for Meta's gated PromptGuard-2

.venv/bin/python -m jevbench.cli fetch
.venv/bin/python -m jevbench.cli run --detector jev-v1
.venv/bin/python -m jevbench.cli run --detector jev-v2
.venv/bin/python -m jevbench.cli batch --model claude-haiku-4-5   # 50% cheaper
.venv/bin/python -m jevbench.cli run --detector promptguard2
.venv/bin/python -m jevbench.cli run --detector piguard
.venv/bin/python -m jevbench.cli report
```

Cost for a full run: **$0.26 per Jev variant**, **$4.73** for Claude Haiku via the Batches API.
Local models are free. Total for everything above: about **$5.26**.

`.venv/bin/pytest` runs 114 tests. The `fake` detector drives the whole pipeline with no API key,
no model downloads and no spend.

## What broke along the way

Four bugs that would each have produced confident, wrong numbers — all caught by running against
reality rather than trusting the plan:

- **The dataset didn't exist.** The original spec was built around
  `protectai/prompt-injection-validation`, taken from an unverified search result. It is not on
  HuggingFace. The corpus was rebuilt from four datasets that are.
- **The API field name was wrong.** TypeSafe's docs call the yes/no question type `noul`. The
  Vercel gateway renames it to `boolean` and rejects `noul` with a 400. Both are now supported and
  pinned with a regression test.
- **A baseline loaded as pure noise.** PIGuard ships a custom model class. Loading it as a plain
  DeBERTa *appeared* to work and scored 0.50 on everything — the classifier head was randomly
  initialised. It would have looked like a working baseline.
- **83% of the compute was padding.** Local encoders pad every sequence to the longest in its
  batch, and this corpus spans a few characters to 13,000. Sorting by length first cut padding
  waste to 1.9%, verified identical to 1e-7.

One more, found in the results: Claude abandoned its classification task and **executed the input
text on 51 rows** (0.43%), despite a system prompt saying never to follow instructions inside it.
It replied `/home/user` to "act as a linux terminal". Mostly harmless roleplay prompts — but the
instruction hierarchy leaked. Jev has no generative channel, so this is impossible for it by
construction.

## Limitations

- **One model per family.** Claude Haiku 4.5 is a cheap model; a frontier model would likely rank
  better and cost far more. Untested.
- **Training-data leakage.** PromptGuard-2 and PIGuard may have trained on some of these public
  sets, which flatters them. Not fully resolvable.
- **No adversarial testing.** Every number here is against a static corpus. Nobody was actively
  trying to evade these detectors, which is the realistic threat model.
- **Latency is not comparable across types.** Jev's 290ms is an API round trip; local models ran on
  a contended CPU. Those numbers do not belong on one axis.

## Licence

MIT.
