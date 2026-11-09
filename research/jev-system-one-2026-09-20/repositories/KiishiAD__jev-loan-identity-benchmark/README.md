# Jev temporal loan identity benchmark

A reproducible, synthetic benchmark for matching noisy loan observations to a canonical temporal loan store.

This standalone repository uses no Bloomberg, employer, client, licensed, or production data. The store is a generic bitemporal simulation with business-valid time and system-recorded time; it is **not** a reconstruction of Bloomberg internals.

## Architecture

```text
synthetic bitemporal store
        ↓ as-of filter
candidate retrieval + exact conflicts (Python)
        ↓ top four, permuted behind opaque option labels
Jev one-call fan-out
  • Choice: best candidate or none
  • Score per candidate: different / review / same
  • Noul per candidate: same borrower, same facility, material conflict
        ↓
deterministic precision-first policy
        ↓
match / review / no_match + auditable metrics
```

Jev never generates an identifier. Dates, numeric comparisons, temporal eligibility, hard conflicts, thresholding, and final authority stay in code. The request excludes gold IDs, split names, scenario tags, and canonical IDs.

## Dataset

`build_synthetic_fixture(seed=20260918)` creates:

- 180 bitemporal version rows for 60 canonical facilities;
- 30 development observations from 10 borrower families;
- 60 held-out observations from 20 disjoint borrower families;
- 40 held-out positives and 20 hard negatives.

Scenarios include spelling damage, abbreviations, legal suffixes, amendments, missing fields, same-borrower sibling facilities/tranches/liens, sponsor confusion, currency conflicts, refinancing, near-name affiliates, OCR-like corruption, and unseen facilities.

## Published run: 2026-09-18

The committed live run used Jev `1.13.0` on 90 development and held-out observations:

- held-out precision: **100%** (`39/39`) with **0 false merges**;
- held-out recall: **97.5%** (`39/40`), with one severe typo routed to review;
- retrieval Recall@1 and Recall@4: **100%**;
- live latency: p50 **1.837s**, p95 **2.796s**, p99/max **2.869s**;
- live wall time: **5.615s** for 90 calls at concurrency 6;
- throughput: **16.03 observations/second**;
- provider errors: **0**.

The much lower replay latency is cached local execution and is reported separately; it is not Jev API speed. Full metrics and evidence are in [`reports/semantic-loan-mapping-report-2026-09-18.md`](reports/semantic-loan-mapping-report-2026-09-18.md).

## Install and test

From the repository root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

The tests are offline and never call TypeSafe.

## Live benchmark

The live run uses synthetic data only and spends TypeSafe credits. Keep the key outside the repository.

```bash
export TYPESAFE_API_KEY=...
export TYPESAFE_LOG_LEVEL=off
.venv/bin/python -m loan_identity_jev.benchmark live \
  --repo-root . \
  --report-date 2026-09-18
```

The runner:

1. writes the fixed dataset and hash;
2. runs development rows with six concurrent Jev calls;
3. selects policy thresholds on development only, requiring no development false positives and at least 95% development precision;
4. freezes and hashes the policy;
5. evaluates the borrower-disjoint test split once;
6. saves sanitized response/result artifacts;
7. replays the cache without API calls and checks quality-metric equality;
8. writes a dated Markdown report and JSON metrics under `reports/`.

## Offline replay

```bash
.venv/bin/python -m loan_identity_jev.benchmark replay \
  --run-dir reports/loan-identity-jev-2026-09-18
```

A cache miss is a hard failure; replay never falls back to a live request.

## Acceptance gates

- confirmed precision >=90%;
- confirmed recall >=80%;
- retrieval Recall@4 >=98%;
- raw Jev top-1 accuracy >=90%;
- false-merge rate <=10% and zero false merges on the locked synthetic holdout;
- live p95 end-to-end latency <=10 seconds;
- zero provider errors.

Precision is the primary safety metric. `review` is a valid abstention, not a hidden match. The report keeps live and replay latency separate.

## Evidence limits

Passing this benchmark supports one narrow claim: the pinned architecture and Jev version performed at the reported level on the committed synthetic workload. It does not prove production loan-master accuracy, provider calibration, Bloomberg equivalence, or legal/identifier authority. Production use requires an independently labelled authorized dataset, stronger hard negatives, shadow deployment, human review, provenance, privacy/legal approval, and drift monitoring.
