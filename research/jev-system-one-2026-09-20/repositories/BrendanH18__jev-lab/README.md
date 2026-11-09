# Jev Lab

Six small apps and a workbench that show what [TypeSafe's **Jev**](https://docs.typesafe.ai) can do.

Jev is a *System One* model: you send it some state and a set of typed questions, and it returns
a choice, a score, or a probability for each one, with calibrated confidence, in about 100 ms.
It never generates prose, so your code branches on the answers directly. Jev Lab puts that inside
ordinary software in six different ways, then hands you a Workbench to build your own.

Jev Lab is an independent, open-source demo. It is not affiliated with or endorsed by TypeSafe;
"TypeSafe" and "Jev" are their names. Latency and price figures quoted here come from
[TypeSafe's docs](https://docs.typesafe.ai/models) as of September 2026 and will change; the app
shows the real latency and cost of every call it makes, and no answer is ever canned.

```
git clone https://github.com/BrendanH18/jev-lab && cd jev-lab
uv run server.py          # or: python3 server.py  (Python 3.10+, or 3.9 with a stdlib fallback)
open http://127.0.0.1:8321
```

You need a TypeSafe API key: get one at [console.typesafe.ai](https://console.typesafe.ai/settings/keys),
press **Connect API key** in the app, and it is validated and (optionally) saved to a gitignored
`.env` for you. Every answer in Jev Lab is a live Jev call; nothing is canned or replayed.

Stop the server with `Ctrl+C`. If it's running in the background, `kill $(lsof -ti :8321)` (or
`pkill -f server.py`).

## What's inside

All six apps run on one fictional business, **Harbor Coffee Co.**: orders, vendors with invoices,
a weekly calendar, a staff handbook, and an inbox.

| App | What it shows | Jev pattern |
| --- | --- | --- |
| 🛡️ **Shield** | Screens inbound email for prompt injection, phishing, vendor impersonation, and payment-redirect fraud. Ten questions per email, one call. Move a weight slider and every message re-scores with no new call. | Decomposed judgments, weighted in code; hard rules; parallel batch |
| ⚡ **Dispatch** | Plain-English commands become typed function calls (`refund_order(order="A-1041", reason="damaged")`). Live preview while you type. Confidence and risk decide: run, confirm, or clarify. | Speculative fan-out (one call fills every function's arguments); confidence-gated routing |
| 🧭 **Autopilot** | Shield + Dispatch in **one** call per email. Side by side with Dispatch alone, which cannot see who is asking: it refunds a stranger's claim on someone else's order, and on the fake-invoice email it either pays $4,250 to the attacker's account or asks you to confirm with no warning attached. Autopilot quarantines both, with reasons. A built-in benchmark measures merged vs. separate calls. | Composition: one verdict gates another's actions; sender facts feed permission checks |
| 🔎 **Find** | Semantic search over the staff handbook with no embeddings and no index. Eight questions, one request. A separate Noul says whether the document answers at all. | Choice over line IDs (up to 255); existence check |
| 🎲 **Play** | 20 Questions with Jev as the referee, in real time. "Probably" means P(yes) is between 60 % and 85 %. | Hidden state + free text → four Nouls per turn |
| 🧰 **Workbench** | Your state, your questions. Run, save as tests with expectations, run a question set over hundreds of rows, export Python / JavaScript / curl. Twelve example patterns to start from. | Everything above, on your own data |

Every result shows the model, latency, tokens, and cost of the call it came from, with an
**Inspect JSON** drawer that shows the exact request and response.

## What it looks like

Live answers from `jev-1.13.0` on 17 September 2026, unedited.

![Autopilot: ten emails handled in ten calls, three scams quarantined, Dispatch alone shown beside it](docs/screenshots/autopilot.png)

![Shield: one email, ten questions, the weighted verdict, and the whole inbox screened in parallel](docs/screenshots/shield.png)

![Find: six questions asked of the handbook in one request, two correctly reported as not in the document](docs/screenshots/find.png)

![Workbench bulk mode: forty tickets classified on four dimensions in under a second](docs/screenshots/workbench-bulk.png)

## The Workbench

The Workbench is the part that turns "cool demo" into "how do I build with this":

- **Build.** A state (text or JSON) and a list of questions with a visual editor or raw JSON.
  Run, read the probabilities, then edit the wording and run again.
- **Tests.** Save a run as a test. Expectations start from the answers you got (`choice ==
  billing`, `P(yes) ≥ 0.5`, `score in [1, 2]`); edit them to what you believe is right. Tests are
  JSON files in `data/workbench/`, so they can be committed and run again when you change a
  question or the model version.
- **Bulk.** Paste rows (one per line, or a JSON array), run the same questions over all of them
  eight at a time, sort by any column, download the CSV. At $0.042 per million input tokens, a
  question set over a million short messages costs about ten dollars.
- **Examples.** Guardrails, citation checking, tool-call verification, model routing, date
  extraction without date math, entity matching, résumé screening, moderation, semantic lint,
  lead scoring, review feature extraction, support triage.
- **Export code.** Any request as working Python (official SDK), JavaScript (official SDK), or
  curl.

## Security

The server binds to `127.0.0.1` and checks every request (Host allow-list against DNS rebinding,
`Sec-Fetch-Site`, `Origin`, a per-run session token, JSON-only bodies, a strict CSP). The key is
never sent to the browser or written to logs. When the app saves the key to `.env` it first
checks that `.env` is gitignored and not tracked, then writes it atomically with `0600`
permissions. A per-run spend guard (`JEV_LAB_BUDGET_USD`, default $2) and a local rate limit stop
runaway loops. Details in [SECURITY.md](SECURITY.md).

## Configuration

Set these in the environment or in `.env` (see `.env.example`). The first three are the official
SDK's names.

| Variable | Default | Meaning |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | | Your key |
| `TYPESAFE_DEFAULT_MODEL` | `jev-latest` | Model or alias |
| `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` | API root |
| `JEV_LAB_BUDGET_USD` | `2.00` | Stop live calls after this much spend in one server run |
| `JEV_LAB_RPM` | `120` | Local cap on live calls per minute |
| `PORT` | `8321` | Listen port |

## Project layout

```
server.py             stdlib HTTP server: pages + JSON API, security checks, key onboarding
jev/client.py         one place that calls TypeSafe (official SDK, stdlib fallback on 3.9),
                      spend guard, request/response capture
jev/shield.py         Shield questions, sender-domain facts, verdict composition
jev/dispatch.py       Dispatch questions, regex candidates, resolution, policy checks, gating
jev/autopilot.py      merged request, integrated vs. Dispatch-alone pipelines, benchmark
jev/find.py           line-ID search over a document
jev/play.py           20 Questions game state and turn logic
jev/workbench.py      validation, saved tests, expectations, bulk runs, code export
jev/examples.py       the twelve example patterns
jev/security.py       request checks (host, fetch metadata, origin, token, content type)
jev/envfile.py        safe .env read/write (gitignore + tracked checks, 0600, atomic)
jev/world.py          Harbor Coffee state and the actions that change it
data/samples/         handbook, 20 Questions words, sample tickets
data/workbench/       your saved tests (JSON)
static/               vanilla JS + CSS, no build step
tests/                offline tests with fake answers; SDK transport tests via MockTransport
```

## Tests

```
uv run python -m unittest discover tests        # or: python3 -m unittest discover tests
```

No key or network needed. The tests feed API-shaped fake answers through the real composition
code and drive the official SDK through an in-memory transport. CI runs them on Python 3.9, 3.12,
and 3.13 (`.github/workflows/test.yml`).

To see what the live model actually says for every built-in scenario (after changing a question,
a threshold, or the model version):

```
uv run scripts/validate.py          # ~100 small calls, well under a cent; prints a report
```

## Design principles (from TypeSafe's docs)

- **Code owns the workflow.** Jev appears only where a judgment is needed. Deterministic rules,
  arithmetic, dates, lookups, and side effects stay in code.
- **Atomic questions, composed in code.** "Is this a scam?" becomes seven narrow questions and a
  weighted formula you can edit without touching the model.
- **Select, don't generate.** Amounts, times, and dates are found in code and Jev picks the
  intended one. Replies come from templates Jev chooses between.
- **Confidence scales with risk.** Low-risk actions run at 50 % confidence, refunds at 80 %,
  payments at 90 %, and every action also has to pass the code checks.
- **Test the wording.** Question text is code; the Workbench's tests treat it that way.

The weights, thresholds, and question wording were written from the docs and the
[known jagged edges of jev-1.13](https://docs.typesafe.ai/model-jaggedness/jev-1.13). Treat them
as starting points and tune them on real answers.

## License

MIT. See [LICENSE](LICENSE).
