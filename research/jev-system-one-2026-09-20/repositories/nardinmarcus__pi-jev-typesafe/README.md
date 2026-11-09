# pi-jev-typesafe

**TypeSafe Jev inside [Pi](https://pi.dev).** Jev is TypeSafe's System One judgment model: send it some state and typed questions, get calibrated probabilities back in about a second, for a fraction of a cent. This package gives Pi one thing done carefully:

- **`jev_ask` tool** — batched Choice / Score / Noul evaluation with **question linting** that catches the failure modes the TypeSafe docs warn about *before* your tokens are spent, **model discovery** (`/jev models`), per-request model pinning, and **probability-bar rendering** in the terminal.
- **`/jev` command** — `enable · disable · status · test · models`.
- **Budget rails** — per-session attempt cap, optional daily caps (requests / input tokens / USD), persisted across restarts, checked *before* a request is submitted.

Independent project. Not affiliated with TypeSafe AI or the Pi authors.

## Install

```bash
pi install npm:pi-jev-typesafe
# or from git:
pi install git:github.com/nardinmarcus/pi-jev-typesafe@v0.1.0
# or from a local checkout:
pi install /path/to/pi-jev-typesafe
```

Requires Pi 0.85+ and Node.js 22+. Zero runtime dependencies — pi bundles everything the extension imports (`typebox`, `pi-ai`, `pi-tui`).

## Setup

1. Get a key at [console.typesafe.ai](https://console.typesafe.ai/).
2. `export TYPESAFE_API_KEY=...` in your environment (`~/.zshrc` works; the extension also reads it as a fallback if the env var is absent from the pi process).
3. Inside Pi, run `/jev enable` and confirm the data notice — or set `PI_TYPESAFE_JEV_ENABLED=1` for headless runs.

`/jev status` shows the key source, opt-in state, session attempt count, today's persisted usage, estimated spend, and active caps.

## The three question types

| Type | Asks | Criteria | Returns |
| --- | --- | --- | --- |
| `choice` | Which of these options fits? | options map `{ label: description \| null }` — include a no-match option | chosen option, probability per option, confidence |
| `score` | Where on this ordered rubric? | array of ≥ 2 **concrete** level descriptions | position (may be fractional), probabilities, confidence |
| `noul` | Is this true? | optional `{ true, false }` descriptions | P(yes) |

Questions run in parallel and cannot see each other. Put each item in a named state field (`reports.r1`) and ask one narrow judgment per question per dimension.

## Question linting

Before submitting, `jev_ask` checks your questions and appends non-blocking warnings to the result:

- a `choice` with **no no-match option** (`other`, `unclear`, `其他`…) — the model cannot pick an option you omitted;
- `score` levels that are **bare degree words** (`low / medium / high / 中等 / 一般`) instead of concrete situations;
- instructions so short they cannot carry the full judgment.

Question text is the whole program: Jev answers exactly what is asked, and ambiguity shows up as a middling probability rather than an error.

## Budget and safety

- Per session: 20 attempts by default (`PI_TYPESAFE_JEV_MAX_REQUESTS`), reset on session start/reload.
- Per day (persisted in `~/.pi/agent/pi-jev-typesafe/usage.json`, rolls over at local midnight):
  - `PI_TYPESAFE_JEV_MAX_REQUESTS_PER_DAY`
  - `PI_TYPESAFE_JEV_MAX_INPUT_TOKENS_PER_DAY`
  - `PI_TYPESAFE_JEV_MAX_USD_PER_DAY` (input tokens only — output is free)
- 20s timeout, one retry on transient faults (429 / 5xx / network), response shape validated before you see it.
- Only the submitted state and questions go to `api.typesafe.ai`. Nothing else is collected. Error messages never contain upstream response bodies, headers, keys, or your submitted content. The API key is never logged.

## Model selection

`model` defaults to `jev-latest`. `/jev models` lists what your account can use.

- `jev-latest` — most recent stable release (currently `jev-1.13.0`)
- `jev-preview` — may move ahead of stable
- pinned ids (`jev-1.13.0`) — use when confidence thresholds were tuned against a specific version

## Library use

Internal helpers are exported for reuse and testing:

```ts
import { validateRequest, lintRequest, prepareArguments, formatResult } from "pi-jev-typesafe";
```

## Development

```bash
npm install
npm run check        # typecheck + tests
npm run build        # emit extensions/index.js (committed: git installs do not build)
```

## License

MIT
