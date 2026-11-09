# typesafe-ai-firewall

Shadow-mode validation for a pre-execution firewall on AI agent tool calls,
built on TypeSafe / Jev typed judgments.

## Results

Real run against the live API. 600 records, $0.054 total spend, held-out split (n=320). Full detail, caveats, and the four-way failure inventory in [`report.md`](report.md).

| gate | target | result | pass |
| --- | --- | --- | --- |
| Block rate on benign calls | < 1% | **0.55%** | ✅ |
| Block rate on `benign_hard_negative` | < 3% | **0%** | ✅ |
| Approval-prompt rate on benign | < 5% | 20.9%* | ❌ |
| Catch rate on injection + exfiltration + multi_hazard | > 90% | **100%**† | ✅ |
| Noul calibration error (ECE) | < 0.10 | 0.156 | ❌ |
| p95 added latency | < 500ms | 595ms | ❌ |
| Cost per gated call | report | **$0.0000365** | — |

\* 88% of those approvals exactly match ground truth — the corpus deliberately includes legitimate-but-scary requests ("drop this named production table") that *should* reach a human. Real false friction is 1.9% of benign traffic, not 20.9%. † Synthetic attacks we designed ourselves — a floor, not proof against a real adversary.

**Ablation (Phase 5) — does decomposition and context actually earn their cost?**

| config | catch rate | block rate (benign) | block rate (hard negative) | $/call |
| --- | --- | --- | --- | --- |
| A. Full 5-hazard battery + full context | 100% | 0.55% | **0%** | $0.0000365 |
| B. One "is this dangerous?" question | 100% | 15.9% | **39.2%** | $0.0000210 |
| C. Full battery, no situational context | **61.6%** | 1.10% | 2.7% | $0.0000296 |

## Why decomposed, typed judgments instead of one LLM-as-judge prompt

The obvious way to build this is one prompt: *"Is this tool call dangerous? Yes/no."* TypeSafe's approach instead asks Jev **five independent typed questions** — one `Noul` (a calibrated P(yes), not a verdict) per hazard (`injection`, `scope_creep`, `exfiltration`, `irreversible`, `credentials`) plus a `Score` for blast radius — all batched into **one parallel `system_one` call**, with the actual ALLOW/APPROVE/BLOCK decision made by ordinary, auditable code in `firewall/policy.py`, not by the model. Two things make that worth the extra design effort, and this repo doesn't just assert it — it measures it:

- **Decomposition is the difference between a firewall and a blunt instrument.** Ablation B — the single "is this dangerous" question — matches the full battery's attack catch rate (100%, easy case) but **blocks 39% of legitimate hard negatives outright**, because one scalar verdict can't distinguish "this looks catastrophic" from "the user explicitly asked for this catastrophic thing." Five independent probabilities let the policy table reason about *which* hazard fired and combine that with scope and blast radius — exactly the distinction a firewall that survives contact with real users needs.
- **The context you assemble matters more than the model call itself.** Ablation C — same 5-question battery, but stripped of `user_request`/`retrieved_content`/`tenant_policy`, tool name and args only — drops the attack catch rate from 100% to **61.6%**, a 38-point collapse, while barely moving the benign side. The "moat" isn't the API call; it's the situational state you hand it.
- **Both of these come at effectively zero latency cost.** All 5 Nouls + 1 Score run in the *same* batched call as the single-question version (that's the point of `system_one`) — the cost difference above (B is ~40% cheaper per call) is token count, not decomposition overhead. You get the five-way diagnosis for close to the price of the one-word verdict.
- **Raw judgments are logged, not just the final action**, so re-tuning a threshold in `policy.py` (as this run did, twice — see `report.md`) never requires paying for inference again: `eval/replay.py` re-scores an existing decision log offline in milliseconds.

**Read `PLAN.md` first** for the full experiment design and the success gates. **Read [`report.md`](report.md)** for the complete run: per-stratum confusion, the threshold-tuning writeup (including a real policy-table gap this run found and fixed), the four-way failure inventory, and the caveats about what synthetic recall numbers can and can't tell you. `runs/` holds the raw decision logs and per-run reports behind all of the above.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env            # set TYPESAFE_API_KEY

# 1. verify the SDK surface hasn't drifted (the SDK is days old)
python -m firewall.judge --smoke

# 2. generate the corpus; both invariants must pass
python -m data.generate --n 600 --seed 7

# 3. wiring check with no API calls and no spend
python -m eval.run_shadow --stub --out runs/stub
pytest -q

# 4. cheap smoke run against the real model
python -m eval.run_shadow --limit 20 --out runs/smoke
python -m eval.report --run runs/smoke --split all

# 5. full run, fanning out --concurrency requests at a time over the async client
python -m eval.run_shadow --concurrency 10 --out runs/full
python -m eval.report --run runs/full --split calibration --sweep   # pick thresholds here
python -m eval.report --run runs/full --split heldout --sweep       # report gates here

# 6. re-tune thresholds without paying for inference again: raw judgments are
# logged per record, so a policy.py change just gets replayed over the log
python -m eval.replay --run runs/full --out runs/full_retuned
python -m eval.report --run runs/full_retuned --split heldout --sweep
```

## Ablations (Phase 5)

```bash
# B: single "is this dangerous" Noul instead of the 5-hazard battery
python -m eval.run_shadow --single-question --concurrency 10 --out runs/ablation_b

# C: no situational context — tool name and args only
python -m eval.run_shadow --no-context --concurrency 10 --out runs/ablation_c
```

## What each piece is for

| File | Role |
| --- | --- |
| `firewall/battery.py` | The questions. The independent variable — version it before editing. |
| `firewall/policy.py` | Thresholds and rules, in code. No model calls. |
| `firewall/judge.py` | The only file that touches the SDK. Fix drift here. |
| `data/generate.py` | Synthetic corpus + the two invariants that keep it honest. |
| `eval/run_shadow.py` | Runs the battery, logs raw probabilities and actions. |
| `eval/replay.py` | Re-scores a decision log under a new `policy.py` without re-running inference. |
| `eval/report.py` | Per-stratum confusion, calibration, sweeps, failure inventory. |

## The one number that matters

Block rate on `benign_hard_negative`. Everything else is context. A firewall that
blocks legitimate agent actions gets switched off in week two, and then it protects
nothing.

That number passed here (0% on held-out). Two others didn't (calibration error and
p95 latency) — see `report.md` for what that does and doesn't mean before treating
this policy table as production-ready.
