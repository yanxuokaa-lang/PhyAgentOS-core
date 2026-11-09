# Jev Takes Mauboussin: Calibrating TypeSafe's Jev on Decision Calibration

Evaluating TypeSafe's System One model (**Jev**, trained via RLCD on 100% synthetic data) against **Michael Mauboussin's 50-question confidence calibration test** from *The Success Equation* ([confidence.success-equation.com](https://confidence.success-equation.com/)).

🌐 **Interactive Live Web Results**: [https://confidence.success-equation.com/r/xm43zab3](https://confidence.success-equation.com/r/xm43zab3)

---

## Executive Summary & Findings

Michael Mauboussin's classic calibration exercise tests **two-alternative forced choice (2AFC)** decisions on 50 factual questions across history, science, geography, sports, and culture. Takers choose **True** or **False**, and rate their confidence on a slider from **50% to 100%** in 5% increments.

We asked: **How does Jev—a System One decision model trained entirely on synthetic data with Reinforcement Learning from Calibrated Decisions (RLCD)—perform on human calibration?**

### Scorecard

```
======================================================================
  Jev (TypeSafe System One) on Mauboussin Calibration Quiz
======================================================================
Total Questions:       50
Correct Answers:       45 / 50 (90.0%)
Mean Confidence:       91.4%
Calibration Gap:       +1.4 points (Well Calibrated)
Brier Score:           0.0903 (lower is better)
Expected Cal Error:    10.4%
Confidence on Correct: 92.3%
Confidence on Wrong:   83.0%
Confidence Spread:     +9.3 points
======================================================================
```

### Jev vs. The Human Crowd (948 Participants)

Comparing Jev directly against Mauboussin's live benchmark database ($N = 948$ people):

| Metric | Typical Human | Jev (`jev-latest`) | Jev's Standing |
| :--- | :--- | :--- | :--- |
| **Accuracy** | **60.0%** (mean: 60.2%) | **90.0%** (45 / 50) | **Top 1.1%** (beats 98.9% of human takers) |
| **Stated Confidence** | **71.0%** (mean: 70.8%) | **91.4%** | Higher certainty driven by deep knowledge |
| **Calibration Gap** | **+10.0 pts** overconfident | **+1.4 pts** (near zero) | **Top 7.5%** (better calibrated than 92.5% of humans) |

The typical human runs **10 points overconfident** (claiming ~71% certainty while being right only ~60% of the time). Jev's stated confidence tracks its actual accuracy within **1.4 points**, placing it in the top tier of well-calibrated decision makers.

---

## Confidence Level Breakdown

```
----------------------------------------------------------------------
  Stated Conf | Questions | Correct |  Accuracy  |  Gap (Actual - Stated)
----------------------------------------------------------------------
         55%  |     1     |    1    |   100.0%   |    +45.0 pts
         60%  |     2     |    2    |   100.0%   |    +40.0 pts
         65%  |     1     |    1    |   100.0%   |    +35.0 pts
         70%  |     2     |    1    |    50.0%   |    -20.0 pts
         80%  |     3     |    2    |    66.7%   |    -13.3 pts
         85%  |     3     |    2    |    66.7%   |    -18.3 pts
         90%  |     4     |    2    |    50.0%   |    -40.0 pts
         95%  |    13     |   13    |   100.0%   |     +5.0 pts
        100%  |    21     |   21    |   100.0%   |     +0.0 pts
----------------------------------------------------------------------
```

### High Certainty Performance
On the 34 questions where Jev stated top certainty (**95% or 100%**):
* **13 of 13 correct** at 95% confidence.
* **21 of 21 correct** at 100% confidence.
* **Combined 95%+ certainty:** **34 / 34 (100.0% accuracy)**. Unlike generative LLMs prone to confabulation, when Jev expressed high certainty it never hallucinated false confidence.

---

## What Did Jev Miss? (The 5 Errors)

All 5 of Jev's misses were classic cognitive/geographic illusions that famously trap human decision-makers:

1. **Q4**: *"Australia is larger in area than Brazil"* (Answer: **False**).
   * Jev picked `True` ($p = 0.82$). Brazil is $8.51\text{M km}^2$; Australia is $7.69\text{M km}^2$.
2. **Q27**: *"Milan, Italy has a higher latitude than Toronto, Canada"* (Answer: **True**).
   * Jev picked `False` ($p = 0.09$). Milan is $45.5^\circ\text{N}$; Toronto is $43.6^\circ\text{N}$. (A classic geographic misconception due to climate perception: people assume freezing Toronto is further north than Mediterranean Italy).
3. **Q37**: *"In 2010, more people in the US died from Alzheimer's than from strokes"* (Answer: **False**).
   * Jev picked `True` ($p = 0.71$). In 2010 CDC records, strokes were the 4th leading cause; Alzheimer's was 6th.
4. **Q40**: *"Helen Clark was New Zealand's first female prime minister"* (Answer: **False**).
   * Jev picked `True` ($p = 0.92$). Jenny Shipley was the first female PM (1997); Helen Clark was the second (1999).
5. **Q43**: *"California is larger in area than Montana"* (Answer: **True**).
   * Jev picked `False` ($p = 0.13$). California is $163,696\text{ sq mi}$; Montana is $147,040\text{ sq mi}$. (Mercator projection and Montana's shape frequently mislead intuitions).

---

## Native Jev Representation

In TypeSafe's System One architecture, we support two native representations:

### 1. `Noul` (Direct Bayesian Truth Probability) — *Primary*
A `Noul` question evaluates a yes/no statement and returns a single calibrated probability $p \in [0.0, 1.0]$:

```python
from typesafe_sdk import Noul

questions = {
    "veracity": Noul(
        instructions='Is this statement factually true: "The capital of Morocco is Rabat"?',
        criteria={
            "true": "The statement is factually accurate.",
            "false": "The statement is factually false or inaccurate.",
        },
    )
}
```

* **Decision Pick**: $\text{pick} = \text{True if } p \ge 0.5 \text{ else False}$
* **Continuous Confidence**: $C_{\text{raw}} = \max(p, 1.0 - p) \in [0.5, 1.0]$
* **Quantized Slider Step (50%–100%)**:
  $$C_{\text{slider}} = 5 \times \left\lfloor \frac{C_{\text{raw}} \times 100}{5} + 0.5 \right\rfloor$$

### 2. Execution Modes: Batched vs. Per-Question
* **Single Batched Request (`--batch`)**: Uses an empty state (`state: ""`) with all 50 questions evaluated independently in parallel on TypeSafe's backend in a **single round-trip** (~500ms total).
* **Per-Question Requests**: Evaluates each question as an isolated state concurrently with an `asyncio.Semaphore`.

Both raw continuous metrics and quantized slider steps are preserved in output JSONs.

---

## Project Structure

```
├── data/questions.json                 # Audited 50 questions (Version 2)
├── src/jev_mauboussin/
│   ├── models.py                       # Pydantic data schemas
│   ├── representation.py               # Request builders, Noul/Choice mapping, quantization
│   ├── questions.py                    # Dataset loader
│   ├── calibration.py                  # Scoring, bucket analysis, Brier score, reports
│   ├── runner.py                       # Async runner using typesafe-sdk
│   └── cli.py                          # CLI runner with dry-run and submission support
├── tests/                              # 14 unit and integration tests
├── results_batch_noul.json             # Full raw results from live batch run
├── results_individual_noul.json        # Full raw results from live per-question run
├── main.py                             # Root entry point
└── pyproject.toml
```

---

## Quickstart

### 1. Installation
```bash
git clone https://github.com/eggmasonvalue/jev-takes-mauboussin.git
cd jev-takes-mauboussin
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Run Tests
```bash
pytest -v
```

### 3. Run Offline (Dry Run)
```bash
python main.py --dry-run
```

### 4. Run Live with Jev
Set your API key (`TYPESAFE_API_KEY` or `JEV_API_KEY`):
```bash
export TYPESAFE_API_KEY="your_api_key_here"

# Fast single-request batch mode (Noul)
python main.py --batch --output my_results.json

# Submit to https://confidence.success-equation.com and print live share URL
python main.py --batch --submit
```

---

## Epistemic Takeaways

1. **Synthetic Training Yields Real Calibration**: Jev was trained with RLCD on 100% synthetic data. Its $+1.4$ point calibration gap confirms that calibration learned in synthetic environments generalizes to real-world factual trivia.
2. **Confidence Resolution**: Jev expressed an average confidence of $92.3\%$ on correct answers versus $83.0\%$ on misses ($\Delta = +9.3$ points), showing its confidence can serve as a dependable gating signal.
3. **No False Bravado**: Jev demonstrated $100\%$ accuracy across all 34 questions where it claimed $\ge 95\%$ certainty.
