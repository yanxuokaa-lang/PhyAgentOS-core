# hermes-jev-fastpath

[![CI](https://github.com/scursel/hermes-jev-fastpath/actions/workflows/test.yml/badge.svg)](https://github.com/scursel/hermes-jev-fastpath/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Hermes_Agent-%3E%3D0.21.3-6f42c1)](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins/)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.11-3776ab)](https://www.python.org/)

Profile-scoped [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that uses
[TypeSafe Jev](https://docs.typesafe.ai/introduction) to short-circuit narrow,
deterministic turns **before** the configured LLM provider is called — with fail-open
behavior on every uncertainty, timeout, or error.

## Project status

This is an **experimental reference implementation**, not a general-purpose agent
accelerator. It is production-shaped, security-gated, and fully tested, but its value is
workload-dependent: it saves a large provider call only when a real turn matches one of
five deliberately narrow deterministic handlers.

The author's deployment is currently **disabled** after a replay of 7,513 real human
turns found one eligible turn (0.0133% coverage). A controlled five-prompt A/B still
showed that accepted hits work as intended: five provider calls avoided, 94,771 net
tokens avoided after subtracting Jev usage, and 37.63% lower median wall time. These
figures are evidence for the mechanism, **not** a claim of broad production ROI. See
[`docs/benchmark.md`](docs/benchmark.md) for method, raw aggregate results, and limits.

Use this plugin when your workload repeatedly contains the supported narrow intents and
your normal Hermes request carries a large prompt/context. Do not expect it to improve
coding, tool-heavy tasks, open-ended chat, or `no_agent` cron jobs.

## What this is (and is not)

**Jev here is a typed router, not a writer.** For each eligible turn the plugin sends the
redacted user text plus a list of locally-detected candidate handlers to TypeSafe's
`jev-latest` model. Jev answers exactly two typed fields: one handler ID chosen from the
candidate allowlist (or `normal_llm`) and a short-circuit probability. It can never
produce shell commands, URLs, code, tool names, tool arguments, files, or response prose —
the answer text is always rendered locally by an allowlisted handler.

It is **not** a replacement for 9Router, provider routing, semantic caching, or token
compression. It does not execute tools, run actions, block dangerous work, make approval
decisions, or report gateway/systemd/quota health.

## How it differs from other Jev integrations

Jev is a typed decision service; these projects apply it at different boundaries:

| Project | Host boundary | What Jev decides | Calls the main LLM? |
|---|---|---|---|
| **hermes-jev-fastpath** (this repo) | Hermes `llm_execution` middleware | Whether one allowlisted local handler can fully answer the current turn | **No** on an accepted active hit; otherwise normal fallthrough |
| [`ajensenwaud/hermes-jev-plugin`](https://github.com/ajensenwaud/hermes-jev-plugin) | Hermes tools | Typed checks, routes, scores, and evaluations requested by an agent | Yes — the agent chooses and calls the Jev tools |
| [`litshing/hermes-jev-plugins`](https://github.com/litshing/hermes-jev-plugins) | Hermes context and memory hooks | Which old tool results or memory candidates should survive | Independent of current-turn response routing |
| [`tamaratran/fast-jev-compaction`](https://github.com/tamaratran/fast-jev-compaction) | Claude Code compaction hook | Which historical tool calls/results to retain | Independent of current-turn response routing |

The projects are independent and are not interchangeable. Running more than one Jev
integration in the same host can create duplicate TypeSafe calls; verify the active hook
surfaces before combining them.

## Deterministic handlers (v1)

| Handler | Answers | Example |
|---|---|---|
| `calculator` | Pure arithmetic reducible to a bounded safe AST (`+ - * / // % **`, parentheses, unary signs) with an explicit operator; exact rational results | `quanto é (17 * 9) - 4?` |
| `clock` | Current date, time, or both in the configured IANA timezone | `que horas são?` |
| `runtime_identity` | Which provider, model, API mode, or platform is serving this turn (middleware context only) | `qual é o seu modelo?` |
| `acknowledgement` | Exact, allowlisted **gratitude** only (`obrigado`, `valeu`, `thanks`, …) — go-ahead/approval words like `ok`, `certo`, or `got it` are context-dependent replies and always fall through | `obrigado` |
| `fastpath_status` | This plugin's own mode, handlers, thresholds, and the PRIOR decision timestamp | `fastpath status` |

Everything else — reasoning, writing, tools, context, ambiguity — routes to `normal_llm`
and Hermes runs the real provider call exactly once.

## How a turn flows

1. Hermes fires the `llm_execution` middleware with the built provider request.
2. Only the **first middleware invocation for a `(session_id, turn_id)` pair** is
   eligible: an atomic, bounded per-turn claim is taken before anything else, so Hermes
   retries, fallbacks, and restarts that re-deliver `api_call_count == [1, 1]` can never
   re-evaluate the turn (no second Jev call, no duplicate telemetry). Turns with a
   missing `api_call_count` or a missing turn ID are never eligible. Bare numbers
   (phones, OTP codes, menu replies), unspaced phone-shaped fragments such as
   `98765-4321`, and confirmation replies never become candidates.
3. A conservative local detector proposes candidate handlers. No candidates, slash
   commands, code blocks, URLs, credential-shaped strings, shell metacharacters, action
   requests, or oversized input → straight to `next_call(request)` with no Jev call.
4. Jev classifies once (hard wall-clock deadline, 3 s default; ≤64 KiB response cap;
   redirects rejected; failure circuit breaker), and the typed decision is validated
   locally: known handler from the candidate set, confidence ≥ 0.92, short-circuit
   probability ≥ 0.90 (both configurable).
5. `shadow` mode (the default): render locally, record `would_short_circuit` telemetry,
   then call `next_call(request)` — the provider answer is returned unchanged.
6. `active` mode: return a provider-shaped synthetic response for the active `api_mode`
   (`chat_completions`, `codex_responses`, `anthropic_messages`, `bedrock_converse`) and
   call the provider **zero** times.
7. Any timeout, HTTP error, malformed Jev answer, parser rejection, handler error,
   telemetry failure, or cache inconsistency fails open to `next_call(request)` exactly
   once. Prompt cache invariants are preserved: messages, system prompt, history, and
   tool definitions are never mutated.

## Prerequisites

- Hermes Agent `>= 0.21.3` with the native directory-plugin loader (manifest declares
  `requires_hermes: ">=0.21.3"`).
- Python `>= 3.11` (stdlib only at runtime; no pip dependencies).
- `TYPESAFE_API_KEY` obtained from the [TypeSafe console](https://console.typesafe.ai/keys)
  and resolved through the **active Hermes secret scope**. In multiplexed
  multi-profile gateways the plugin never reads the ambient launch-profile environment
  while a profile scope is installed: an empty or missing scoped credential fails open
  (fast path disabled for that turn) instead of silently using another profile's value.
  Standalone (non-Hermes) usage falls back to the process environment for test
  compatibility. The credential is never read from `.env`, `auth.json`, or another
  profile, never logged, and only ever sent as the authorization header to the TypeSafe
  endpoint.

## Installation (one profile)

For a quick trial from the public default branch (the plugin starts in `shadow` mode):

```bash
hermes --profile <profile> plugins install scursel/hermes-jev-fastpath --enable
```

For a reproducible deployment, install from the pinned commit you audited (L5):
`hermes plugins install` verifies provenance, installs into the profile's plugin directory,
and never drags `.git`, tests, or virtualenvs along.

```bash
# Resolve the full 40-character commit SHA you audited (example: 5ce7679...), then:
hermes --profile <profile> plugins install scursel/hermes-jev-fastpath --ref <full-40-char-commit-sha> --enable
```

Update and rollback are the same pinned operation against a different SHA:

```bash
hermes --profile <profile> plugins install scursel/hermes-jev-fastpath --ref <new-full-sha> --force   # update
hermes --profile <profile> plugins install scursel/hermes-jev-fastpath --ref <old-full-sha> --force   # rollback
```

Never `cp -r` a working checkout into a profile: a copied `.git`/`.venv` poisons the
`hermes plugins validate` security scan and installs untracked code. Development
virtualenvs belong outside this repository (see below).

Enable and configure in that profile's `config.yaml`:

```yaml
plugins:
  enabled:
    - jev-fastpath
  entries:
    jev-fastpath:
      enabled: true
      settings:
        mode: "shadow"              # "off" | "shadow" | "active" — ALWAYS quote the value
        confidence_threshold: 0.92  # minimum Jev choice confidence [0, 1]
        short_circuit_threshold: 0.90
        timeout_seconds: 3.0        # 0.2 – 10.0
        timezone: America/Sao_Paulo
        locale: pt-BR               # pt-BR | en
        max_input_chars: 4000       # 32 – 12000
        enabled_handlers:
          - calculator
          - clock
          - runtime_identity
          - acknowledgement
          - fastpath_status
```

**YAML quoting matters:** YAML 1.1 parses a bare `off` (also `yes`/`on`) as a boolean, not
a string. The plugin refuses to coerce it — it logs one warning and stays disabled — so
always quote the mode value (`mode: "off"`). Settings are read once when the plugin
registers at gateway start: **every settings change, including mode changes, requires
restarting that profile's gateway to take effect.**

Keep development virtualenvs OUTSIDE this directory: `hermes plugins validate` runs a
security scan over the whole plugin tree, and a `.venv`/`.git` checkout inside it poisons
the scan (and bloats installs).

Invalid settings emit one bounded warning and disable the fast path (the plugin stays
discovered and Hermes keeps booting normally).

## Why shadow is the default

Shadow mode performs the full classification and local rendering but always returns the
real provider response, recording what *would* have been short-circuited. Collect shadow
telemetry, compare suggested fast paths against normal Hermes answers, verify no other
Jev plugin duplicates the TypeSafe call, and only then set `mode: active` on **one**
profile.

## Coexistence warning

Another Jev-based plugin (for example an existing `jev-triage` style plugin) in the same
profile will call TypeSafe for the same turns. Disable or reconfigure it before enabling
`active` mode here to avoid duplicate TypeSafe calls and cost.

## Telemetry and privacy

Decisions append one JSON object per line to
`<HERMES_HOME>/artifacts/jev_fastpath/decisions.jsonl` with: UTC timestamp, mode, hashed
(not raw) session/turn IDs, platform/provider/model/api mode, the input text hash and
length, local candidates, selected handler, Jev confidence and short-circuit probability,
Jev latency and reported cost/tokens when present, the outcome (`no_candidate`,
`normal_llm`, `would_short_circuit`, `short_circuit`, `fallback`), a bounded non-secret
fallback reason code (missing credential, timeout, network, HTTP/auth, redirect,
oversized response, invalid response, open circuit), and a `provider_call_avoided`
boolean.

Preview policy: turns with **no candidate store no input preview** — only the text hash
and length. Candidate turns may store a redacted, bounded input preview. Accepted shadow
and active decisions additionally store a bounded redacted **answer preview and answer
hash** so fast-path effectiveness is diagnosable without exposing sensitive text.
Bounding happens before any redaction regex runs. The log file is created with
owner-only permissions (0600 where supported) and rotates to a single
`decisions.jsonl.1` backup when it exceeds 5 MiB. Request bodies, full conversation
history, credentials, tool arguments, and the TypeSafe authorization header are never
logged; logging failures are swallowed and never affect the turn.

## Verification

After installing into a profile:

```bash
# Discovery and registration
HERMES_HOME=~/.hermes/profiles/<profile> hermes plugins list
HERMES_HOME=~/.hermes/profiles/<profile> hermes plugins doctor \
  ~/.hermes/profiles/<profile>/plugins/jev-fastpath --ci

# Gateway identity and health (record the PID before and after any restart)
systemctl --user status hermes-<profile>   # or your profile's gateway unit
curl -s localhost:8642/health              # adjust to the profile's gateway port
```

Then, on that one profile:

1. Send `2 + 2` (or `que horas são?`) with `mode: shadow` — expect the normal LLM answer
   and a `would_short_circuit` row in `decisions.jsonl`.
2. Set `mode: active` and send `2 + 2` — expect the deterministic answer with **no**
   provider usage and a `short_circuit` telemetry row.
3. Send an open question such as `fale sobre arte moderna` — expect a normal provider
   answer and a `no_candidate` or `normal_llm` row (exactly one provider call).
4. Check transcript/session persistence: the assistant message appears in the session
   exactly once, in the normal message shape (`hermes --resume` or your session viewer).

## Rollback

Settings are loaded once at plugin registration, so every step below ends with a gateway
restart of ONLY the affected profile:

1. Edit the profile's `config.yaml` and set the mode to the quoted string `"off"`
   (a bare `off` is parsed by YAML as a boolean and the plugin refuses it):

   ```yaml
   plugins:
     entries:
       jev-fastpath:
         enabled: true
         settings:
           mode: "off"
   ```

   Restart only that profile's gateway; the fast path is now inert (every turn goes to
   the provider exactly once).

2. Full unenroll: remove `jev-fastpath` from `plugins.enabled` (or
   `hermes plugins disable jev-fastpath` / remove the installed plugin directory).

3. Restart only the affected profile's gateway again.

4. Verify the gateway came back with a **new PID** and `/health` is green, and that a
   normal turn answers via the provider:

   ```bash
   systemctl --user status hermes-<profile>   # record the new PID
   curl -s localhost:8642/health              # adjust to the profile's gateway port
   ```

## Development

```bash
python -m pip install -e '.[test]'
python -m pytest -q                                  # unit suite (no network, no credentials)
PYTHONPATH=/path/to/hermes-agent python -m pytest -q # full suite incl. Hermes-hosted integration
python scripts/smoke_plugin.py                       # credential-free end-to-end smoke
```

The Hermes-hosted tests (transports, plugin discovery, `AIAgent.run_conversation`) skip
automatically when the Hermes source tree is not importable.

Static verification is mandatory for release and runs `python scripts/check_forbidden_patterns.py`
(fails on `eval`/`exec`/subprocess/shell/dynamic-import/forbidden-hook patterns in runtime
code) plus `scripts/skillspector_gate.sh`, which scans every executable/plugin runtime
scope (`jev_fastpath/`, `scripts/`) with SkillSpector `--no-llm --format json` (v2.5.3,
pinned in CI to immutable source commit `0562b964ec5ceac67ee15c163738e5404f14a908`; it is
not published on PyPI) and fails on scanner errors or any CRITICAL finding parsed
from the JSON report by `scripts/skillspector_findings.py` — the scanner's exit code alone
only signals execution errors, so the report is the gating signal. The runtime package
currently scans with no critical findings; the two advisory signals are intentional,
spec-mandated behavior: the TypeSafe
endpoint constant in `jev.py` (E1) and the required credential read (E2), which is
resolved through the Hermes secret scope and only sent as the authorization header to
that endpoint. The SkillSpector **root scan is not authoritative for this repository**:
the scanner walks the whole tree it is given, so packaged third-party data (botocore
fixtures with fake AWS keys), `.git` objects, or a virtualenv inside the checkout drown
the report or hang it outright — the scoped gate above is the authoritative signal.

## Limitations

- No tools, no actions, no approval or blocking behavior, no gateway health reporting.
- No prose generation of any kind; the five allowlisted handlers produce fixed-shape
  answers only.
- The synthetic response marker (`_jev_fastpath`) is best-effort; telemetry never relies
  on it surviving Hermes normalization.
- Production benefit depends on workload coverage. Large savings per accepted hit do not
  imply useful aggregate savings when eligible turns are rare.

## Contributing and security

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the local verification gates. Please report
security issues privately through [GitHub Security Advisories](https://github.com/scursel/hermes-jev-fastpath/security/advisories/new),
not through a public issue. See [`SECURITY.md`](SECURITY.md).

## License

MIT © Gabriel Scursel. See [`LICENSE`](LICENSE).
