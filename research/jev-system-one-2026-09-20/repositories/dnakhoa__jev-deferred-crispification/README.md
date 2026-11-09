# What Jev Is Missing — Calibration Does Not Compose, Types Destroy Vagueness

**Your decision pipeline is calibrated per hop and blind per trajectory. This repo contains the math that proves it, the architecture that fixes it, and two audit metrics you can run today — no model weights required.**

[![preprint v1.2](https://img.shields.io/badge/preprint-v1.2-b31b1b.svg)](paper.pdf)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22801506.svg)](https://doi.org/10.5281/zenodo.22801506)
[![ResearchGate](https://img.shields.io/badge/ResearchGate-publication-00CCBB.svg)](https://www.researchgate.net/publication/414384305)
[![license](https://img.shields.io/badge/license-CC--BY--4.0-blue.svg)](LICENSE)
[![reproduce](https://img.shields.io/badge/reproduce-CPU%20%C2%B7%20~2%20min-brightgreen.svg)](#reproduce-everything)
[![integrity](https://img.shields.io/badge/integrity-headline%20withdrawn%20when%20wrong-orange.svg)](#integrity-changelog)

> **30-second version.** TypeSafe AI's **Jev** (15 Sept 2026) launched the *System-One* class: no text, just typed probabilistic decisions (`Choice`, `Score`, `Noul`), calibrated via RLCD, at 70–500 ms and $0.042/1M tokens. Brilliant interface. Two missing primitives: **(1)** no Hidden-Markov belief over latent regimes, **(2)** no fuzzy membership for borderline predicates. We prove what breaks when you compose such heads in a pipeline (**Lemma 1**: calibration does not compose; **Lemma 2**: cliff cascade), state one design law (**Deferred Crispification**), specify one reference architecture (**BSF-S1**), and ship two weight-free audit metrics (**TCE**, **AMS**). Everything reproduces on CPU in ~2 minutes.

---

## Why your ECE dashboard is lying to you

Per-hop Expected Calibration Error is **permutation-invariant**: shuffle your decision stream and ECE does not move. But regime-shift errors are *clustered* — their cluster length is the latent regime's sojourn time. Therefore:

> **ECE has exactly zero statistical power to detect the failure mode that kills trajectories.**

Two models with identical ECE can differ in trajectory risk by an arbitrary factor. If your stack routes, scores, and escalates through memoryless calibrated heads, you are auditing the wrong quantity. This paper gives you the right ones.

```
TODAY (double collapse):                    THIS PAPER (deferred crispification):

evidence → [head] → p → [τ] → act           evidence → [BSF-S1] → (μ, Q, Δb) → …hops… → [actuator] → act
                    ↑ cliff #1                              ↑ structure preserved           ↑ collapse ONCE
                    → [harness τ] → act
                           ↑ cliff #2
```

## The two holes, and what we prove

| Missing primitive | Failure mode | Result |
|---|---|---|
| **Hidden-Markov belief** over latent regime | Scores stay "calibrated" against a frozen prior that no longer exists after regime shift; errors cluster; hop-ECE is blind to it | **Lemma 1** — closed-form variance inflation; finite-T form (Eq. 3.5) matches simulation to 3 decimals; P(all-correct) ≈ **70×** the independent baseline hop-calibration implies |
| **Fuzzy membership** for borderline predicates | Ontological vagueness ("is this *urgent*?") forced into epistemic p≈0.5; thresholding makes actions discontinuous in evidence; flips cascade under common-mode shocks | **Lemma 2** — cliff cascade: all-hops-flip event has Θ(ε) measure, not Θ(ε^H); fuzzy t-norm composition + single Lipschitz defuzzification removes the cliff |

Both holes are **structural, not capacity-related**: they survive any scaling of the network. Both are **cheap to repair**: O(K² + KM) per step, no generative decode.

## The fix: Deferred Crispification

> *No structure may be collapsed before the actuator. Collapse — defuzzify, threshold, sample — happens exactly once, with full decision context.*

The reference architecture **BSF-S1** emits, per hop, an uncollapsed object:

```
O(x) = ( μ ∈ [0,1]^{K×M},   Q[μ],        Δb )
        membership per      type-2        scaled likelihood
        regime & predicate  spread        (posterior ÷ prior)
```

- `Δb` composes across hops by **pointwise product** inside an exact forward filter — because *posteriors don't compose; likelihoods do* (Bourlard–Morgan hybrid-HMM trick).
- `μ` is emitted **per regime** and mixed only at the actuator — mixing over regimes is itself a collapse.
- `Q` is a calibrated distribution *over the degree* (type-2), audited by proper scoring rules, kept separate from the degree itself.

Full pseudocode (filter step, single-collapse actuator, training) in [`paper.pdf`](paper.pdf) §6.5.

## Audit your pipeline today (no weights needed)

- **TCE — Trajectory Calibration Error.** Does the implied distribution of *errors per window* match reality? Primary statistic: dispersion ratio, with a **shuffled-stream control** (v1.2 definition). Hop-ECE cannot see this; TCE can.
- **AMS — Action-Mass Sensitivity.** How much action mass moves under an ε-perturbation of evidence? Discontinuous (typed+threshold) vs Lipschitz (fuzzy+deferred) pipelines separate cleanly here.

Reference implementations: [`experiments/e2_trajectory_calibration.py`](experiments/e2_trajectory_calibration.py), [`experiments/e3_cliff_cascade.py`](experiments/e3_cliff_cascade.py).

## Reproduce everything

```bash
git clone https://github.com/dnakhoa/jev-deferred-crispification
cd jev-deferred-crispification
python3 experiments/run_all.py          # E1–E5 + lemma checks, CPU, ~2 min
```

| Script | What it shows | v1.2 protocol |
|---|---|---|
| [`verify_lemma1.py`](experiments/verify_lemma1.py) | variance inflation & P(all-correct) vs closed forms | e.g. `var: sim 20.304 / pred 20.314 / binomial 6.944`; `P(all-correct): 0.0071 vs 0.0001` |
| [`verify_lemma2.py`](experiments/verify_lemma2.py) | discontinuity of typed+threshold vs Lipschitz fuzzy actuator | slope estimates at N=4e6 |
| [`e1_regime_shift.py`](experiments/e1_regime_shift.py) | window-conditional calibration after regime shift | 5 seeds; exact-filter floor; Bayes-optimal memoryless head |
| [`e2_trajectory_calibration.py`](experiments/e2_trajectory_calibration.py) | TCE separates pipelines that hop-ECE calls identical | 5 seeds; shuffled-stream control; online-Platt & history-window baselines |
| [`e3_cliff_cascade.py`](experiments/e3_cliff_cascade.py) | action-mass flip under ε-perturbation; cascade vs coupling weight | matched base rates; own adversary; thresholded-mean comparison |
| [`e4_composition_algebra.py`](experiments/e4_composition_algebra.py) | t-norm vs product vs naive-Bayes composition in rule bases | min t-norm identity checks |
| [`e5_type2_separation.py`](experiments/e5_type2_separation.py) | degree vs degree-uncertainty conflation in single-number outputs | synthetic borderline populations |

<!-- FILL: paste run_all.py summary table (mean±sd over 5 seeds) here -->

## Integrity changelog

We review adversarially and publish the scars.

- **v1.2 — headline withdrawn.** An earlier draft claimed a "25–60×" cascade effect. Adversarial review showed the comparison was unfair (unmatched base rates); the experiment was rebuilt fair and **the headline was withdrawn**. The fair version stands in [`e3_cliff_cascade.py`](experiments/e3_cliff_cascade.py).
- **v1.2 — bounds corrected.** Cascade bound re-conditioned; sequential fuzzy bound fixed; Lemma 1 assumptions stated precisely; upper tail proved; π fixed to the training-time marginal; symbols de-overloaded.
- **v1.1 — authorship corrected.** Human-only author line + explicit AI-usage statement, per venue policies and COPE guidance.
- **v1.0 → v1.2:** misquotes fixed; Mendel record corrected; all Jev claims traced to primary sources (TypeSafe launch post, docs, The Register).

> If a repo tells you only what survived review, ask what didn't. This one tells you both.

## Paper & citation

- **PDF:** [`paper.pdf`](paper.pdf) (15 pp., compiled LaTeX)
- **LaTeX:** [`paper.tex`](paper.tex) · **Markdown:** [`paper.md`](paper.md) · **Outline:** [`outline.md`](outline.md)
- **ResearchGate:** [publication page](https://www.researchgate.net/publication/414384305)
- **Zenodo archive:** [10.5281/zenodo.22801506](https://doi.org/10.5281/zenodo.22801506)

```bibtex
@article{doan2026calibration,
  title     = {Calibration Does Not Compose, Types Destroy Vagueness:
               The Hidden-Markov and Fuzzy Primitives Missing from
               System-One Decision Models},
  author    = {Doan, Ngoc Anh Khoa},
  year      = {2026},
  month     = sep,
  doi       = {10.5281/zenodo.22801506},
  url       = {https://github.com/dnakhoa/jev-deferred-crispification},
  note      = {Position paper, preprint v1.2},
  license   = {CC BY 4.0}
}
```

## About the author

**Ngoc Anh Khoa Doan (Anh Khoa)** — Senior AI/ML Engineer specializing in **Agent Systems & Production ML**, 10 years shipping production ML systems; published author (ACM, DBLP-listed); **ADPList Top-50 AI/ML mentor**; incoming PhD student at **Auckland University of Technology**, New Zealand.

He designs agent pipelines for a living, which is why this paper attacks the quantity pipelines actually fail on — not the one benchmarks celebrate. The research direction emerged from conversations with an LLM sparring partner (Qwen 3.8) in September 2026; Fable 5.1 expanded the prose; adversarial self-review (rounds 1–3) shaped the final form.

- **GitHub:** [@dnakhoa](https://github.com/dnakhoa)
- **LinkedIn:** [/in/kay-doan](https://vn.linkedin.com/in/kay-doan)
- **ResearchGate:** [Ngoc-Anh-Khoa-Doan](https://www.researchgate.net/profile/Ngoc-Anh-Khoa-Doan)
- **Open to:** collaboration on trajectory-level calibration, regime-aware forecasting, production audits of System-One stacks; mentorship calls via [ADPList](https://adplist.org/).

## Contribute

Good first issues:

1. **Real-world regime-shift decision streams** (fraud / ops / ticketing) to replace synthetic generators in `experiments/common.py`.
2. A **TypeScript/Python harness-auditor library** exposing `tce()` and `ams()` as drop-in metrics.
3. **Notebook versions** of E1–E5 for teaching (Jupyter + binder).
4. **Alternative t-norm families** benchmarked in `e4_composition_algebra.py`.

See [`experiments/common.py`](experiments/common.py) for the shared protocol. Please read the [integrity changelog](#integrity-changelog) before proposing claims — the project has a policy of publishing withdrawals alongside results.

## Share

If you want to signal-boost this work, copy-paste is fine:

- **Hacker News title that works:** *"Calibration does not compose: per-hop ECE cannot see regime-shift errors (proofs + CPU repro)"*
- **Tweet that works:** *"Your System-One decisions are calibrated per hop and blind per trajectory. Two lemmas, one principle (Deferred Crispification), two weight-free audit metrics (TCE/AMS). Reproduces in 2 min on CPU. The repo even lists the headline it withdrew for being unfair. DOI: 10.5281/zenodo.22801506"*
- **LinkedIn angle:** *"Three review rounds, one headline withdrawn, five experiments across five seeds — what I learned writing a position paper that attacks the metric production teams actually fail on, instead of the one benchmarks celebrate."*

## AI-usage disclosure

This work was developed through structured dialogue with AI assistants (Qwen 3.8 for mathematical sparring; Fable 5.1 for prose expansion). All claims, proofs, design choices, and the decision to withdraw an unfair headline rest solely with the author. The paper's honesty anchor (§8.4): learning parameters is approximation; inference — the filter recursion, the t-norm composition, the single defuzzification — is exact given the model.

## License

[CC BY 4.0](LICENSE) — reuse freely, cite honestly, collapse nothing before the actuator.

---

<p align="center"><em>"The approximation should live in the parameters, not in the algebra."</em></p>
