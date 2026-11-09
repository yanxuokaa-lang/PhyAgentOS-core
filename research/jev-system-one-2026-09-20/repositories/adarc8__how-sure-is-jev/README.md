<h1 align="center">How sure is Jev?</h1>

<p align="center">
  <img src="https://img.shields.io/badge/pip-jev--confidence-2dd4bf" alt="pip">
  <img src="https://img.shields.io/badge/python-3.9%2B-38bdf8" alt="python">
  <img src="https://img.shields.io/badge/deps-zero-4ade80" alt="zero deps">
  <img src="https://img.shields.io/badge/model-TypeSafe%20Jev-a78bfa" alt="jev">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-fbbf24" alt="MIT"></a>
</p>

<p align="center">
  <a href="#what-is-this">What is this?</a>&nbsp;•&nbsp;
  <a href="#quick-start">Quick start</a>&nbsp;•&nbsp;
  <a href="#the-metrics">The metrics</a>&nbsp;•&nbsp;
  <a href="#jevs-secret-formula">Jev's secret formula</a>
</p>

---

<p align="center">
  <img src="assets/hero.png" width="100%" alt="one question, three messages, three gauges">
</p>

## What is this?

[Jev](https://docs.typesafe.ai) is TypeSafe's "System One" model. You ask it a question with a few options
and it returns **probabilities** instead of text:

```json
{ "billing": 0.72, "technical": 0.28, "returns": 0.0, "shipping": 0.0 }
```

Is 0.72 "sure"? Should your code act on it, or send it to a human?

That is a math question, and nobody wants to think about entropy at 2am. So this is a **math black box**:
give it Jev's probabilities, get back one number from 0 to 1 and a plain-English verdict.

```
CERTAIN   - Jev knows. Act on it.
CONFIDENT - Solid pick. Safe for most automation.
LEANING   - Has a favorite, but it is not a lock.
TORN      - Two or more options are fighting. Route to a human.
CLUELESS  - The distribution is basically flat. Do not trust the pick.
```

Zero dependencies. Pure Python. Six formulas inside so you can pick a strict one or a generous one, or take the consensus.

## Quick start

```bash
pip install git+https://github.com/adarc8/how-sure-is-jev
```

```python
from jev_confidence import Sureness

s = Sureness({"billing": 0.72, "technical": 0.28, "returns": 0.0, "shipping": 0.0})

s.winner      # 'billing'
s.sureness    # 0.57
s.verdict     # 'LEANING'
s.scores      # {'max_prob': 0.63, 'margin': 0.44, 'entropy': 0.57, 'gini': 0.46, 'perplexity': 0.73}
```

Or feed it a raw Jev response. Every choice/score answer inside gets its own verdict:

```python
from jev_confidence import from_response

for qid, s in from_response(jev_response).items():
    if s.verdict in ("TORN", "CLUELESS"):
        escalate_to_human(qid)
    else:
        act_on(s.winner)
```

Or from the terminal:

```bash
jev-confidence '{"billing": 0.72, "technical": 0.28, "returns": 0, "shipping": 0}'
```

```
winner: billing  (72%)

  billing       #################        0.72
  technical     #######                  0.28
  returns                                0.00
  shipping                               0.00

sureness metrics:
  max_prob      ===============          0.63
  margin        ===========              0.44
  entropy       ==============           0.57
  gini          ===========              0.46
  perplexity    ==================       0.73

log odds (top vs 2nd): 0.94  ->  evidence: barely worth mentioning
consensus sureness:    0.57

VERDICT: LEANING - Has a favorite, but it is not a lock. Consider a threshold.
```

## The metrics

Every metric maps a distribution to `[0, 1]`. Flat = 0. All mass on one option = 1.
They agree at the extremes and disagree in the middle, which is exactly where you need them.

<p align="center">
  <img src="assets/metrics_sweep.png" width="100%" alt="metric curves">
</p>

| Metric | What it measures | Personality |
| --- | --- | --- |
| `max_prob` | Winner's share, rescaled so `1/n` = 0 | Generous. Only looks at the winner. **This is Jev's own formula** (see below). |
| `margin` | Winner minus runner-up | Only cares about the top-2 fight. |
| `entropy` | `1 - H(p) / ln(n)` | The information-theory answer. Strict. |
| `gini` | Normalized sum of squares | Like entropy, cheaper, punishes spread quadratically. |
| `perplexity` | How many options Jev is "really" choosing between | Reads naturally: "it is picking between 1.4 options". |
| `spread` | `1 - std / max_std` over option **positions** | Only for ordered options (Score levels). Far-apart mass is punished, adjacent mass is not. |
| `log_odds` | `ln(p1 / p2)` | Unbounded. Comes with a Kass-Raftery label: "positive" / "strong" / "very strong". |

`s.sureness` is the mean of the bounded ones. Thresholds are opinions, not physics. Tune them on your own data.

<p align="center">
  <img src="assets/verdict_bands.png" width="100%" alt="verdict bands">
</p>

Same message, four questions. The shape tells you *why* Jev is unsure, not just that it is:

<p align="center">
  <img src="assets/radar.png" width="70%" alt="radar">
</p>

<details>
<summary>Bonus: what every metric looks like across all possible 3-option distributions</summary>
<br>
<p align="center">
  <img src="assets/ternary.png" width="100%" alt="ternary plots">
</p>
Corners are certain, center is clueless. <code>max_prob</code> and <code>margin</code> have straight edges (piecewise linear), <code>entropy</code> and <code>gini</code> are smooth bowls.
</details>

## Jev's secret formula

Jev returns its own `confidence` field but the docs do not say how it is computed.
So we asked Jev 72 real questions and compared its number to ours.

<p align="center">
  <img src="assets/jev_vs_ours.png" width="100%" alt="jev vs our metrics">
</p>

- **Choice questions: `confidence == max_prob`** on every answer (largest gap 0.02, which is rounding). That is `(p_max - 1/n) / (1 - 1/n)`.
- **Score questions: mostly `max_prob`**, but with an extra penalty when mass lands on non-adjacent levels
  (`{0: 0.18, 1: 0.21, 2: 0.61}` gets 0.14 from Jev, 0.41 from `max_prob`). We could not pin the exact formula. PR welcome :))))

Why it matters: `max_prob` is the *most generous* metric in the table. A 2-option answer at 75/25 gets
`0.50` from Jev but `0.19` from entropy. If you gate automation on Jev's number alone, the story is a bit rosier
than the distribution supports.

## Links

- [TypeSafe docs](https://docs.typesafe.ai)
- [TypeSafe on confidence](https://docs.typesafe.ai/confidence)
- [Kass & Raftery (1995)](https://www.jstor.org/stable/2291091), where the log-odds labels come from

## License

MIT
