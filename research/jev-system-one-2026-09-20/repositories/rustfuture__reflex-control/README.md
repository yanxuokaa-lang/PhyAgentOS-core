# Reflex Control

[![CI](https://github.com/rustfuture/reflex-control/actions/workflows/ci.yml/badge.svg)](https://github.com/rustfuture/reflex-control/actions/workflows/ci.yml)
[![Rust 1.88+](https://img.shields.io/badge/rust-1.88%2B-orange.svg)](https://www.rust-lang.org)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Architecture: Guarded Hybrid](https://img.shields.io/badge/architecture-guarded--hybrid-purple.svg)](docs/experiments/live_experiment_hybrid_results.md)
[![Status: Evaluated](https://img.shields.io/badge/evaluation-frozen--v0.1-brightgreen.svg)](fixtures/README.md)

A deterministic, calibrated **System-1 control plane and policy engine** for AI agent runtimes. It arbitrates whether an agent execution step should continue, retry, accept autonomously, request local verification, or escalate to an expensive frontier reasoning model.

Reflex Control couples zero-cost deterministic runtime checks (test suites, git diffs, execution bounds) with atomic semantic signals from [TypeSafe Jev](https://typesafe.ai). Inviolable safety rules strictly take precedence over model confidence: high-risk actions are vetoed regardless of predicted likelihood.

```
                  ┌───────────────────────────────┐
                  │    Agent Execution / Task     │
                  └──────────────┬────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [Deterministic Checks]          [Atomic Semantic Signals]
        - Exit codes & tests            - Scoped Jev evaluation
        - Changed files & blast radius  - Safety & vulnerability probes
        - Retry budgets & loop counters - Objective completion signals
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
              ┌─────────────────────────────────────┐
              │  Layer 1: Inviolable Hard Veto Gate │
              │  (Critical risk / privilege bypass) │
              └──────────────┬───────────────┬──────┘
                   Veto Path │               │ Passed Safety
                             ▼               ▼
                 ┌──────────────────┐  ┌───────────────────────────────────┐
                 │ Mandatory Frontier│  │ Layer 2: Calibrated Decision Gate │
                 │ Reasoner Escalation│ │ (Accept, Retry, Small Reasoner)   │
                 └──────────────────┘  └───────────────────────────────────┘
```

---

## Key Capabilities

- **Guarded Hybrid Decision Architecture**: Combines deterministic invariants with narrow, model-evaluated atomic propositions.
- **Inviolable Hard Safety Veto**: Prevents defect leakage by enforcing policy overrides that no confidence score can bypass.
- **Calibrated Frontier Cost Elimination**: Safely handles routine tasks autonomously (69% autonomous coverage observed in frozen v0.1 benchmark) without incurring latency or financial cost from frontier calls.
- **Shadow Mode Telemetry**: Evaluates agent workflows side-by-side in production without blocking live orchestrator execution, recording decisions to SQLite (`reflex.db`).
- **Reproducible Evaluation Protocol**: Fully specified, frozen benchmark fixtures with reproducible seed runs and statistical confidence intervals.

---

## Workspace Architecture

The repository is organized as a clean Cargo workspace separating core abstractions from providers, policies, and tooling:

| Crate | Path | Responsibility |
| :--- | :--- | :--- |
| `reflex-core` | [`crates/reflex-core`](crates/reflex-core) | Core data models, task contexts, evidence vectors, decision action enums. |
| `reflex-provider` | [`crates/reflex-provider`](crates/reflex-provider) | Provider traits and local mock/synthetic implementations for zero-dependency runs. |
| `reflex-jev` | [`crates/reflex-jev`](crates/reflex-jev) | TypeSafe Jev API integration for atomic semantic signal extraction. |
| `reflex-policy` | [`crates/reflex-policy`](crates/reflex-policy) | Guarded Hybrid policy implementation, safety veto rules, and acceptance thresholds. |
| `reflex-telemetry` | [`crates/reflex-telemetry`](crates/reflex-telemetry) | SQLite-backed decision persistence, shadow-mode evaluation logs, cost and latency tracking. |
| `reflex-calibration` | [`crates/reflex-calibration`](crates/reflex-calibration) | Grid sweep routines for policy calibration, threshold optimization, and Pareto frontier generation. |
| `reflex-cli` | [`crates/reflex-cli`](crates/reflex-cli) | Unified CLI tool (`reflex`) for execution, benchmarks, shadow mode, and demos. |

---

## Quick Start

Rust **1.88** or newer is required.

### 1. Installation & CLI Initialization

```bash
# Clone the repository
git clone https://github.com/rustfuture/reflex-control.git
cd reflex-control

# Build and install the CLI
cargo install --path crates/reflex-cli

# Initialize local state (creates reflex.db)
reflex init
```

### 2. Evaluating a Decision (Local Mock Mode)

Local mock mode runs deterministically without network calls or credentials:

```bash
reflex run --provider mock \
  --context "Check whether this worker patch is safe" \
  --risk low
```

Output:
```text
================ Reflex Control Decision Execution ================
Provider:       Mock/Synthetic
Task ID:        session-synthetic-fd920f2f-e95b-4092-a185-0688e313fbd8
Risk Level:     low
Evaluating decision...

=== Decision Result ===
Decision ID:    cf419b9d-3e10-42d7-80c8-789a7451c205
Provider:       Mock/Synthetic
Selected:       true
Confidence:     0.9900
Probabilities:  [("true", 0.99), ("false", 0.01)]
Policy Action:  accept
Latency:        5 ms
Estimated Cost: $0.000100

Telemetry Record Stored: reflex.db
====================================================================
```

### 3. Using Live TypeSafe Jev

To evaluate tasks against live atomic semantic signals, set `JEV_API_KEY`:

```bash
export JEV_API_KEY="your_api_key_here"

reflex run --provider jev \
  --context "Add docstrings and verify the test suite" \
  --risk low
```

---

## Runnable Examples

The repository includes standalone runnable examples under [`examples/`](examples/):

### Verifier Gate Example

Demonstrates both autonomous acceptance of safe tasks and the inviolable safety veto against dangerous modifications (even when model confidence is high):

```bash
cargo run -p example-verifier-gate
```

Sample output:
```text
=== Reflex Control: Verifier Gate Example ===

--- Part 1: Policy Gate on Raw Observations ---
Task 1:     Fix typos in documentation
Risk:       low
Confidence: 0.96
Action:     accept
-> Action accepted directly without calling frontier verifier! (Saved $0.02, 1800ms)

Task 2:     Execute DROP COLUMN users.auth_token migration
Risk:       critical
Confidence: 0.96
Action:     escalate
-> Safety rule enforced: High/Critical risk cannot bypass mandatory verification, despite 0.96 confidence!

--- Part 2: Guarded Hybrid Architecture (Candidate E) ---
Clean Task Composite Quality: 0.74
Risk Score:                   0.08
Effective Action:             terminate
-> Clean execution passed autonomously with 0 frontier cost!

Defect Task Quality:          0.85
Risk Score:                   0.90
Effective Action:             defer_to_frontier
-> Inviolable Safety Veto: Security hazard intercepted and escalated despite green tests!

=== All Verifier Gate examples completed successfully. ===
```

### Shadow Mode Sidecar Example

Demonstrates running Reflex Control alongside an existing agent orchestrator to log shadow predictions without mutating execution:

```bash
cargo run -p example-shadow-mode
```

---

## Evaluation Benchmark & Measured Results

The official v0.1 evaluation is documented in [`docs/experiments/live_experiment_hybrid_results.md`](docs/experiments/live_experiment_hybrid_results.md) and evaluated on [`fixtures/v2_eval_blind_test.json`](fixtures/v2_eval_blind_test.json).

### Frozen v0.1 Performance

| Metric | Observed Count | Measured Rate |
| :--- | :---: | :---: |
| **Autonomous coverage** | 69 / 100 | **69.0%** |
| **Frontier calls eliminated** | 69 / 100 | **69.0%** |
| **Frontier-required tasks routed correctly** | 31 / 31 | **100.0%** |
| **Observed defect leakage (FNR)** | 0 / 31 | **0.0%** |
| **Observed false alarms (FPR)** | 0 / 69 | **0.0%** |

### Statistical Bounds

- **Autonomous Coverage (69/100)**: Approximate 95% Wilson score interval is **59.4% – 77.2%**.
- **Zero Observed Leakage (0/31)**: The 95% Wilson upper bound is **~11.0%**; one-sided 95% Clopper-Pearson upper bound is **~9.2%**.
- *Methodological note*: Controlled synthetic benchmarks evaluate decision-gate logic reproducibly but do not constitute unbounded production reliability guarantees.

---

## Datasets & Evaluation Fixtures

All fixture datasets and frozen policies reside in [`fixtures/`](fixtures/):

| Dataset File | Role | Sample Count |
| :--- | :--- | :---: |
| `fixtures/v2_eval_blind_test.json` | Held-out frozen evaluation benchmark evaluated under live Jev inference | 100 tasks |
| `fixtures/v2_eval_calibration.json` | Systematic grid sweep split for threshold calibration ($\tau_{\text{accept}}, \theta_{\text{clean}}$) | 40 tasks |
| `fixtures/v2_eval_validation.json` | Architecture comparison split (Guarded Hybrid vs Deterministic Rules) | 30 tasks |
| `fixtures/v2_eval_dev.json` | Development & connectivity smoke testing split | 30 tasks |
| `fixtures/frozen_hybrid_config.json` | Frozen v0.1 policy parameters ($\tau_{\text{accept}} = 0.28, \theta_{\text{clean}} = 0.38, \text{risk}_{\text{frontier}} = 0.70$) | Config |

---

## Development & Testing

Run the full verification suite locally:

```bash
# Code formatting check
cargo fmt --all -- --check

# Strict workspace clippy
cargo clippy --workspace --all-targets -- -D warnings

# Run all workspace unit and integration tests
cargo test --workspace

# Run interactive demo via CLI
cargo run -p reflex-cli -- demo verifier-gate
```

---

## License

This project is licensed under the [MIT License](LICENSE).
