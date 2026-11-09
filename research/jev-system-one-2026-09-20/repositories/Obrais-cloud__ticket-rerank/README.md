# Ticket Urgency Reranker

FastAPI service that reranks support tickets by urgency using TypeSafe (Jev / System One).
Each ticket gets one comparable **Score** (0–4, probability-weighted); the batch is sorted
by score descending. The `norm` (0–1) field is meant to be combined in your own code with
other signals (plan tier, ticket age, SLA) — *composite scoring* — without re-calling the model.

## Run locally

```bash
pip install -r requirements.txt
export TYPESAFE_API_KEY=...            # required; never hard-code
uvicorn app:app --port 8000
```

## Docker

```bash
docker build -t ticket-rerank .
docker run -p 8000:8000 -e TYPESAFE_API_KEY=$TYPESAFE_API_KEY ticket-rerank
```

## API

`GET /health` → `{"ok": true, ...}`

`POST /rerank`
```json
{ "tickets": [ {"id": "T-1", "subject": "...", "body": "..."} ], "model": "jev-latest" }
```
Response: `{ "model", "ranked": [ {id, subject, score, norm, confidence, level, error} ], "input_tokens" }`

- `tickets`: 1–200 per request. `model` optional (default `jev-latest`).
- One ticket failing does not fail the batch — it sinks to the bottom with an `error`.
  If **all** upstream calls fail → HTTP 502.

## Behavior notes

- **Concurrency**: upstream calls run in parallel, capped at `MAX_CONCURRENCY` (8).
- **Retries**: 429 and 5xx / network errors retried up to `MAX_RETRIES` (3) with exponential
  backoff + full jitter, honoring `Retry-After`. 4xx (except 429) are not retried.
- **Secret**: `TYPESAFE_API_KEY` is read from the environment only; the app refuses to start
  without it and it is never baked into the image.

## Tests

```bash
python3 test_retries.py     # offline retry logic (MockTransport, no network)
```

## Tuning

Urgency levels live in `URGENCY_LEVELS` in `app.py`. Edit the level descriptions to match
your product; keep them concrete and independently describable (each level is judged alone).
