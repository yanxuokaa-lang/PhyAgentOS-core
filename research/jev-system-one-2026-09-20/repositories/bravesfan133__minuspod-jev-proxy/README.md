# minuspod-jev-proxy

Thin OpenAI-compatible proxy that lets [MinusPod](https://github.com/) use
**Jev** (a decision model, not a chat model) for podcast ad detection.
Jev-only: there is deliberately **no Gemini/general-LLM fallback** inside
this proxy. MinusPod already supports Gemini natively, so if Jev doesn't
work out, point MinusPod straight back at Gemini and stop this container.

## How it works

```
MinusPod → POST /v1/chat/completions → proxy → Jev Decisions API → OpenAI-style JSON back
```

The proxy classifies each incoming chat request (by `response_format`
schema name, then stable prompt markers, then transcript structure) and:

| Request type | Handling |
|---|---|
| Primary ad detection (`ad_detection` schema, pass 1) | Jev, two levels: L1 classifies ~20–30s blocks (`choice` + `noul` per segment); L2 subdivides only the boundary blocks of each ad run into ~5s pieces and re-asks Jev per piece with tight local context, shrink-only. Consecutive runs merged on existing timestamps, bare JSON array returned exactly as MinusPod expects |
| Verification re-scan (pass 2, same schema) | Same Jev path, with transition-tone/orphan-URL guidance |
| Reviewer (`ad_review`) | Jev yes/no on the candidate span; confirms original bounds or rejects. Bounds are never adjusted (Jev can't emit timestamps) |
| Category repair (`segment_categories`) | Jev `choice` per listed segment |
| Trim recovery | `{"ad_start": null, "ad_end": null}` (keep original span — matches MinusPod's native null path) |
| Probes / test-connection | `{"ok": true}` |
| Chapters | HTTP 500 → MinusPod falls back to generic chapters on its own |
| Unknown | HTTP 400, fail loudly rather than guess |

Jev chain: **primary** TypeSafe direct (`jev-latest` rolling alias, needs
`JEV_PRIMARY_API_KEY`/`TYPESAFE_API_KEY`) → **secondary** OpenCode Zen
(`jev-1.13-free`, free, keyless). Paid-first because free tiers burst-limit
under MinusPod's parallel windows; Zen absorbs overflow.

Rate limiting is handled, not hidden: concurrent Jev calls are capped
(`JEV_MAX_CONCURRENT_REQS`, default 4), each backend gets bounded retries
with backoff honoring `Retry-After`, and if both backends are limited the
proxy answers HTTP 429 so MinusPod defers + retries the episode instead of
dropping windows. Other total failures return 502. All other MinusPod
stages degrade gracefully on their own (reviewer keeps candidates,
verification keeps pass-1 cuts, repair defaults to `sponsor`, chapters go
generic, trim keeps the span).

Jev thresholds are split by role: L1 (`JEV_AD_THRESHOLD`, default 0.6) is the
recall gate and deliberately permissive; L2 edge agreement
(`JEV_EDGE_THRESHOLD`, default 0.5, requires low probability AND non-ad
choice to trim) is the precision gate. Uncertain segments stay in the
episode. Tune after measuring.

## Run

```bash
cp .env.example .env   # no keys needed for Zen free; TypeSafe key for primary
docker compose up -d --build
```

On Dockhand: create a stack from this repo (`docker-compose.yml`) and set
the variables in the stack environment UI — at minimum `JEV_PRIMARY_API_KEY`.
No `.env` file needed there.

Point MinusPod at it (Settings → provider `openai-compatible`,
Base URL `http://<host>:8787/v1`, model `jev-ad-detection`), test the
connection, process one episode. Rollback: set Base URL back to
`https://generativelanguage.googleapis.com/v1beta/openai/` and stop this
container. Nothing inside MinusPod is modified.

## Endpoints

- `GET /v1/models` — lists `jev-ad-detection`
- `POST /v1/chat/completions` — non-streaming only
- `GET /health` — status + configured backends (no keys)

## Configuration

All via environment (see `.env.example`). Never hard-code keys; keys are
never logged. Per-request logs are one line: kind, backend, transcript
span, segments, Jev latency, ads found, total time. No transcripts in logs.

## Testing

```bash
cargo test   # 19 unit tests: classifier, transcript parse/segment/merge, Jev shapes
```

For accuracy evaluation, process real episodes and compare against
MinusPod-on-Gemini results: same real ads found? missed? false flags?
boundary deltas? detection-stage time? Do not claim improvement until
measured. Start with `JEV_SEGMENT_TARGET_SECS=30` and thresholds above.

## Notes / limits

- Jev classifies fixed transcript segments; rough boundaries are expected.
  MinusPod's downstream boundary snap/audio analysis still refines them.
- Reviewer is off by default in MinusPod (`enable_ad_review=false`); if you
  enable it, the proxy confirms/rejects but never adjusts bounds.
- `jev-1.13-free` on Zen is a limited-time offer; if it disappears, set the
  primary to TypeSafe direct or paid `jev-1.13`.
