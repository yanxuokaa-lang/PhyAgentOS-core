# switchboard

A guardrail and model router for LLM gateways, built on **Jev**, TypeSafe AI's
"System One" model (launched 2026-09-15), plus an independent evaluation of
whether Jev's probabilities can be trusted.

Jev does not generate text. You send a state and typed questions; one parallel
query returns typed answers with probabilities: `Noul` (is this true?),
`Choice` (which option?), `Score` (where on this rubric?). Claimed 70–500 ms and
$0.042 per million input tokens. That is the shape of decision an inference
gateway needs on every request and cannot afford to ask a frontier LLM.

```
client ─► POST /v1/chat/completions
            │
            ├─ 1 Jev call, 4 questions in parallel (questions.py)
            │     injection? harmful? pii?  (Noul each)      tier: small | large | unclear (Choice)
            ├─ policy.py (pure code)   risk ≥ 0.80 → 403 block · 0.40–0.80 → allow + flag for review
            │                          "small" only if confidence ≥ 0.60, otherwise large
            ├─ forward to BACKEND_SMALL or BACKEND_LARGE (any OpenAI-compatible server)
            └─ if the request carries "context": 1 more Jev call
                  grounded: supports | contradicts | says_nothing   leak? → 422 block / flag
          GET /metrics   requests, actions, routes, pre-check ms, Jev spend (Prometheus)
```

Design rules taken from TypeSafe's own guidance and held to in code: all
questions and thresholds live in one file; the model supplies judgments and
`policy.py` owns the outcome; low confidence never auto-acts in the risky
direction; if Jev is unreachable the gateway **fails open** to the large model
and flags the request (`FAIL_MODE=closed` to reject instead).

## Evaluation (the point of the repo)

`eval_guardrail.py` runs the `injection` question over
[deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections)
(662 labeled prompts, 263 injections, English + German) and reports precision /
recall / F1 across thresholds, ROC-AUC, **ECE and a reliability table**, Brier
score, latency percentiles, tokens, and dollars per 1k requests, against a regex
baseline. Calibration is the claim that matters: Jev is trained with "RL for
Calibrated Decisions", and a gateway that blocks at p ≥ 0.8 is only sound if
0.8 means 0.8.

**Results: pending first live run.** TypeSafe is in early access; the numbers
go here after one recorded run, and the cassette is committed so anyone can
re-score without a key. Nothing in this README is estimated.

```bash
TYPESAFE_API_KEY=... python3 eval_guardrail.py --record   # ~662 calls, under $0.01 at list price
python3 eval_guardrail.py                                 # re-score offline from data/cassette_guardrail.jsonl
python3 eval_guardrail.py --full                          # all 4 questions per call: real fan-out latency
```

## Run it

```bash
python3 test_switchboard.py        # 11 offline tests: policy, cassette replay, gateway flow, metric math
python3 gateway.py                 # :8080; echo backend unless BACKEND_SMALL / BACKEND_LARGE are set
curl -s localhost:8080/v1/chat/completions -d '{"messages":[{"role":"user","content":"hello"}]}'
```

No dependencies: `jev.py` is a 90-line stdlib client for the single
`POST /v1/systemone` endpoint with record / replay cassettes keyed by request
hash, so tests and CI never need the network.

## Files

- `jev.py`: client, retries with backoff on 429/529, cassettes, cost accounting
- `questions.py`: every question and threshold
- `policy.py`: answers → allow / review / block and route; pure functions
- `gateway.py`: OpenAI-compatible proxy, fail-open, `/metrics`
- `eval_guardrail.py`: the evaluation
- `PLAN.md`: what Jev is, why this project, non-goals

## Deliberate simplifications

- Only the last user message is judged. Multi-turn injection needs the transcript in `state`.
- Thresholds are starting points from TypeSafe's cookbooks; the eval's sweep is how to pick real ones.
- Routing quality (does "small" actually suffice?) needs a live backend and an answer-quality judge; not measured here.
- No streaming pass-through yet; the proxy buffers the backend response so the post-check can run.
