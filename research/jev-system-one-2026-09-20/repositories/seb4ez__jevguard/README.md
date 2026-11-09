# JevGuard: Deterministic Decision Runtime for TypeSafe AI (Jev)

JevGuard is a deterministic evaluation, caching, and calibration runtime for TypeSafe AI's Jev model (System One). It wraps standard System One evaluations with closed-world escape injection, certainty calibration, state pruning, volatile key masking, zero-token SHA-256 caching, resilient retry backoff, and episodic session memory using only the Python standard library.

## Why JevGuard

TypeSafe AI's Jev model produces sub-second probabilistic evaluations over structured state. In production, raw calls run into three operational bottlenecks:

1. **Closed-World False Positives**: When categorical choice criteria lack a neutral fallback, Jev distributes all probability across defined options. If an unhandled or off-topic input arrives, the model is forced into a false positive.
2. **Uncalibrated Ambiguity**: When inputs contain conflicting signals, probability distributions flatten. Selecting the top option without checking the runner-up margin leads to decisions made on near-coin-flip confidence.
3. **Repeated Query Cost & Cache Misses**: Identical state checks inside agent loops consume network latency and token budgets. If payloads contain timestamps or request IDs, naive caches miss on every call.

## Features

- **Closed-World Escape Injection**: Detects categorical choice rules without a fallback and automatically injects `UNRESOLVED_OR_OTHER`. Off-topic inputs route to this escape option instead of triggering false positives.
- **Strict Enum Support**: Set `closed_world=True` on `Choice` or `auto_inject_escapes=False` on the client when building strict, exhaustive enums where third-party options must not be introduced.
- **Certainty & Dispersion Calibrator**: Flags decisions where top probability is below 0.40 or the margin between the first and second choices is below 0.15 as `AMBIGUOUS_STATE`.
- **Volatile Metadata Masking**: Automatically ignores ephemeral fields (`timestamp`, `created_at`, `trace_id`, `request_id`, `nonce`) during SHA-256 fingerprinting, ensuring real-world production cache hits.
- **Sub-Millisecond Overhead**: Pure local CPU computation runs in under 0.20 ms (198 microseconds) per evaluation.
- **Zero-Token SHA-256 Cache**: Hashes canonical sorted JSON. Identical requests return in under 1 millisecond with zero network overhead and zero token cost.
- **Concurrent Batch & Async Support**: Built-in `batch_evaluate` with thread pooling and native `async_evaluate` for `asyncio` event loops.
- **Resilient Network Retries**: Exponential backoff with jitter and `Retry-After` header parsing for HTTP 429 and 5xx server errors.
- **Episodic SQLite Memory**: Records session interaction turns with thread-local connection reuse and builds rolling summaries without retransmitting raw history.
- **Zero Dependencies**: Pure Python 3.9+ standard library (`urllib`, `sqlite3`, `hashlib`, `json`, `threading`, `concurrent.futures`). No pip dependencies, no Node.js.

## Installation

Install locally with pip:

```bash
git clone https://github.com/seb4ez/jevguard.git
cd jevguard
pip install .
```

Or copy the `jevguard` directory directly into your project.

Set your TypeSafe AI API key:

```bash
export TYPESAFE_API_KEY="your_typesafe_api_key"
```

On Windows PowerShell:

```powershell
$env:TYPESAFE_API_KEY="your_typesafe_api_key"
```

## Quickstart

```python
from jevguard import JevGuardClient, Noul, Score, Choice

client = JevGuardClient()

state = {
    "ticket_id": "INC-4091",
    "customer_message": "Our payment gateway timed out during credit card settlement.",
    "account_tier": "enterprise",
    "timestamp": 1726778900
}

questions = {
    "is_billing": Noul(instructions="Does this ticket describe an invoice or payment issue?"),
    "severity": Score(
        instructions="Rate incident urgency",
        criteria=["Low", "Medium", "High", "Critical"]
    ),
    "route": Choice(
        instructions="Assign handling team",
        criteria={
            "database_team": "Database connection and replication issues",
            "payment_support": "Gateway timeouts and transaction errors",
            "frontend_ui": "CSS, rendering, and asset bundling issues"
        }
    )
}

response = client.evaluate(state, questions)

print(response.nouls["is_billing"].noul)       # 0.96
print(response.scores["severity"].score)       # 2.45
print(response.choices["route"].choice)        # "payment_support"
print(response.choices["route"].status)        # "CONFIDENT"
```

## Strict Closed-World Enums

When building strict finite-state machines where unhandled options must not be injected:

```python
# Pass closed_world=True to prevent UNRESOLVED_OR_OTHER injection
approval_choice = Choice(
    instructions="Review status",
    criteria={"APPROVED": "Request accepted", "REJECTED": "Request denied"},
    closed_world=True
)

resp = client.evaluate(state, {"decision": approval_choice})
```

## Production Caching with Volatile Metadata

JevGuard masks ephemeral fields during fingerprint computation so dynamic timestamps or trace IDs do not bust the cache:

```python
# First call (cold)
resp1 = client.evaluate({"query": "Check balance", "timestamp": 1726778900, "trace_id": "t-1"}, questions)

# Second call 10 seconds later with new timestamp and trace_id hits local cache
resp2 = client.evaluate({"query": "Check balance", "timestamp": 1726778910, "trace_id": "t-2"}, questions)

print(resp2.cached)                             # True
print(resp2.telemetry["latency_total_ms"])      # 0.10 ms
print(resp2.telemetry["tokens_saved"])          # 159 tokens
```

> Note: Volatile masking operates on structured dictionary keys (for example `{"timestamp": 123}`). If dynamic timestamps are embedded inside raw unstructured strings (for example `{"log": "2026-09-19T22:00:00Z error"}`), the SHA-256 fingerprint will change. To ensure cache hits, extract dynamic timestamps and request IDs into distinct dictionary keys in `state`.

## Concurrent Batch and Async Execution

```python
# Synchronous parallel batch evaluation
items = [
    (state_1, questions),
    (state_2, questions),
    (state_3, questions)
]
results = client.batch_evaluate(items, max_workers=5)

# Native asynchronous execution in asyncio event loops (no manual thread wrapping required)
import asyncio

async def main():
    res = await client.async_evaluate(state, questions)
    print(res.choices["route"].choice)

asyncio.run(main())
```

## Empirical Upstream Benchmark (5 Scenarios: Vanilla vs JevGuard)

The following tests were executed against the live official TypeSafe AI endpoint (`https://api.typesafe.ai/v1/systemone` using model `jev-latest`):

![JevGuard Benchmark Results](benchmark_results.png)

> Note on repository binaries: `benchmark_results.png` is tracked for direct presentation on the GitHub repository page. For automated CI pipelines executing continuous benchmarks, configure artifacts to upload to GitHub Releases or an asset branch to maintain minimal `.git` history size.

| Scenario & Workload | Vanilla TypeSafe AI | JevGuard Runtime | Empirical Advantage |
| :--- | :--- | :--- | :--- |
| **1. Cloud SRE Incident Triage** | 810.85 ms (139 tokens) | 735.88 ms (147 tokens) | State pruned; status verified `CONFIDENT` |
| **2. Fintech Gateway Timeout** | 733.24 ms (149 tokens) | 766.83 ms (164 tokens) | Ordinal score and decision calibrated |
| **3. Off-Topic Query (Closed-World)** | 773.57 ms (Forced False Positive: `credit_card_chargeback`) | 778.96 ms (Safe Escape: `UNRESOLVED_OR_OTHER`) | **Zero false positive**; unhandled inquiry safely isolated |
| **4. Strict Enum FSM** | 730.58 ms (Decision: `APPROVED`) | 766.93 ms (Decision: `APPROVED`) | Closed-world contract preserved; 0 escapes injected |
| **5. Repeated Query with Volatile Timestamps** | 763.40 ms (Full network repeat, 144 tokens charged) | **0.099 ms** (Local RAM cache hit, **0 tokens**) | **7,711x latency speedup; 100% token savings** |

## Testing

Run the full test suite (28 unit, concurrency, lifecycle, heterogeneous types, and CLI tests):

```bash
python test_jevguard.py
```

Run the standalone local latency audit:

```bash
python benchmark.py
```

Run the live 5 vs 5 upstream comparison test (requires `TYPESAFE_API_KEY`):

```bash
python run_live_certification_tests.py
```

## License

MIT License. See [LICENSE](LICENSE) for details.
