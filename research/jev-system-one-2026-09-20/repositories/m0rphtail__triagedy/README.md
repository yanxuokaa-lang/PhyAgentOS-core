# triagedy

> Because alert triage shouldn't be a tragedy.

![ci](https://github.com/m0rphtail/triagedy/actions/workflows/ci.yml/badge.svg)
![license](https://img.shields.io/badge/license-MIT-blue.svg)

**Alert triage as a UNIX filter: JSONL security alerts in, typed decisions out.**

Powered by [TypeSafe Jev](https://typesafe.ai) (System One) by default — typed
decisions with calibrated probabilities in ~200 ms, cheap enough to run a screen
in front of *every* alert so your expensive triage tools (and your humans) only
see what survives it.

One binary. No daemon, no database, no framework. Pipe it, host it, cron it.

```
cat alerts.jsonl | triagedy run | jq '.action'
```

---

## Why

Analysts drown in alerts, and the real problem is rarely the malicious ones — it's
the volume of everything else. triagedy asks a decision model five specific
questions about each alert, gets back typed answers with probabilities, and then
routes the outcome with **ordinary code you control**. The model judges; your
code decides.

No prompt-parsing. No JSON-in-a-sentence. No agent framework. Just a filter.

**Not ready for Jev, or need to keep data on-prem?** Point `--backend openai` at
any OpenAI-compatible server — Ollama, vLLM, LM Studio, llama.cpp, OpenRouter —
and the pipeline is identical. Confidence values there are the model's
self-report, so treat them as uncalibrated.

## What it does

For each alert it asks five questions and returns a typed, validated decision:

| Question | Type | Answer |
|---|---|---|
| What is the correct triage disposition? | **Choice** | `close` \| `escalate` \| `contain` \| `investigate` + confidence |
| How severe if true positive? | **Score** | 0.0–3.0 + confidence |
| Is this a false positive? | **Noul** | probability 0.0–1.0 |
| Does it need immediate IR escalation? | **Noul** | probability 0.0–1.0 |
| Which attacker technique category? | **Choice** | `none` \| `execution` \| `credential_access` \| `persistence` \| `lateral_movement` \| `exfiltration` |

The shape mirrors TypeSafe's [System One primitives](https://docs.typesafe.ai)
(Choice / Score / Noul). Every answer is validated against the allowed options
and ranges before it becomes a decision — an invalid answer is an error record,
never a silent default.

---

## Install

Requires a Rust toolchain (edition 2024 — Rust 1.85+).

```bash
git clone https://github.com/m0rphtail/triagedy
cd triagedy
cargo build --release          # binary at target/release/triagedy
./target/release/triagedy --version
```

Or drop the binary on your `PATH`:

```bash
install -m 755 target/release/triagedy ~/.local/bin/triagedy
```

## Setup

### 1. Store your TypeSafe API key

```bash
triagedy init
```

It prompts with hidden input, writes `~/.config/triagedy/env` at mode `0600`,
and prints only the key's length and last four characters. It never echoes the
key, and it never goes on a command line — process arguments are visible to
other users via `ps`.

### 2. Verify the connection

```bash
triagedy doctor --backend jev
```

Expected:

```
typesafe endpoint: https://api.typesafe.ai/v1/systemone
model: jev-latest
decision round-trip OK in … ms: disposition=… severity=… fp=… escalate=… attack_class=…
```

### 3. Run it

```bash
triagedy run < alerts.jsonl
```

That's the default path — `jev` is the default backend, so no flag is needed.

### API keys, precisely

Keys are resolved **per backend**, so a key for one is never sent to the other:

| Backend | Resolution order |
|---|---|
| `jev` | `--api-key` → `$TYPESAFE_API_KEY` → `~/.config/triagedy/env` |
| `openai` | `--api-key` → `$OPENAI_API_KEY` |

The `--api-key` flag exists for scripting and CI; prefer `triagedy init` or the
environment on a workstation.

### Choosing a model

Jev needs no model flag — `jev-latest` is the service default. For the `openai`
fallback, pass whatever the server serves (`--model`, or `$TRIAGEDY_MODEL`). With
no model given, triagedy stops with a config error rather than guessing.

| Where | How |
|---|---|
| Jev (the product) | `--backend jev` (default) — needs a key |
| any local Ollama model | `--backend openai --model <name>` (see `ollama list`) |
| a hosted OpenAI-compatible API | `--backend openai --openai-url https://… --api-key $OPENAI_API_KEY` |
| a model too big for your box | an Ollama cloud model — `ollama signin`, `-cloud` tags |
| your own transport | add a variant in `src/backends/` — one `assess()` method |

```
# the intended path — Jev
triagedy run < alerts.jsonl

# fallback: any OpenAI-compatible server
triagedy run --backend openai --model gemma4:e2b --openai-url http://127.0.0.1:11434/v1 < alerts.jsonl
```

### Backends

| Backend | Status | Notes |
|---|---|---|
| `jev` | **default, intended path** | TypeSafe System One (`POST /v1/systemone`). Typed answers, calibrated confidence. |
| `openai` | fallback / optional | Any OpenAI-compatible `POST {base}/chat/completions` — Ollama, OpenRouter, vLLM, LM Studio, llama.cpp, Groq. Probes a response-format ladder (`json_schema` → `json_object` → none) once per run and caches what works. Confidence is uncalibrated. |
| `mock` | always available | Offline, deterministic. For tests, dry runs, CI. |

Legacy aliases are accepted: `--backend ollama` and `--ollama-url`.

---

## Usage

```bash
# the intended path — Jev, typed decisions with calibrated confidence
triagedy run < alerts.jsonl

# fallback: any OpenAI-compatible server (Ollama here), same output shape
triagedy run --backend openai --model gemma4:e2b < alerts.jsonl

# pin the fallback model in the environment instead of the command line
TRIAGEDY_MODEL=gemma4:e2b triagedy run --backend openai < alerts.jsonl

# parallel assessments (4 in flight), output order still matches input order
triagedy run --jobs 4 < alerts.jsonl

# files instead of pipes
triagedy run --backend mock --input alerts.jsonl --output decisions.jsonl

# give the model recent activity so it can spot restatements (see below)
triagedy run --context yesterday-decisions.jsonl < today.jsonl

# convert a Windows Event Log XML export, then triage it — one pipe
triagedy convert --format sysmon-xml < windows-sysmon.log | triagedy run

# check your backend before a real run
triagedy doctor --backend jev
triagedy doctor --backend openai --model gemma4:e2b
```

Exit codes: `0` all records ok, `1` at least one record failed, `2` config/runtime error.

### Input formats

| Format | Support |
|---|---|
| JSONL | native — any alert object with an `id` |
| Elastic ECS | native — both flat-dotted (`"rule.name"`) and nested (`{"rule":{"name":…}}`) |
| CrowdStrike FDR | native — `event_simpleName`, `ComputerName`, `ImageFileName`, `CommandLine`, `ParentBaseFileName`, `SourceIp`, `ContextTimeStamp` |
| Windows Event Log XML | via `triagedy convert --format sysmon-xml` |

`convert` rejects DTD and entity declarations (no XXE surface) and reports how
many lines it converted and skipped.

### Output record

One JSON object per input alert, **in input order** (parallelism never reorders):

```json
{
  "input_index": 0,
  "id": "alert-0001",
  "ok": true,
  "backend": "jev",
  "model": "jev-latest",
  "rule": "Suspicious process execution",
  "host": "WORKSTATION-01",
  "user": "CORP\\analyst",
  "decision": {
    "disposition": "investigate",
    "disposition_confidence": 0.85,
    "severity": 2.5,
    "severity_confidence": 0.9,
    "false_positive_probability": 0.15,
    "requires_escalation": 0.7,
    "attack_class": "execution",
    "attack_class_confidence": 0.95
  },
  "action": "investigate",
  "review_required": false,
  "notes": []
}
```

Bad input lines produce an error record (`"ok": false`, `"error": "..."`) and
never take down the batch.

### Recent-activity context

Feed a previous run's output back in so the model can recognise restatements of
activity that is already being handled:

```bash
triagedy run --context yesterday-decisions.jsonl < today.jsonl
```

- The context file is triagedy's own JSONL output; any JSONL with an `id` works.
- The last 20 items travel with every request.
- Jev additionally answers `duplicate_of_recent`, and a high probability can
  downgrade `escalate` → `investigate` — **only** below severity 2.0. `contain`
  is never downgraded, and high-severity escalation is never suppressed.
- Runs stay deterministic: the context is fixed for the whole run, so the same
  inputs always produce the same outputs.

## How routing works

The policy lives in `src/policy.rs` — ordinary Rust, no prompts:

1. The disposition leads: `escalate` → escalate, `contain` → contain.
2. A `close` verdict must survive a false-positive-probability gate that gets
   stricter as severity rises (fp ≥ 0.5, or ≥ 0.7 at severity ≥ 2.0).
3. `investigate` upgrades to `escalate` when `requires_escalation ≥ 0.9` **and**
   `severity ≥ 2.0`.
4. A high `duplicate_of_recent` (≥ 0.8) can downgrade `escalate` → `investigate`
   below severity 2.0.
5. Any confidence below 0.6 sets `review_required` with a note explaining why.

Change the thresholds and the tests in the same file tell you what you broke.

## Design notes

- **Order-preserving parallelism**: `futures::stream::buffered`, not
  `unordered`. Record N always corresponds to alert N.
- **Validation is not optional**: every backend output is checked against the
  defined option sets and ranges before it becomes a decision. An invalid
  answer is an error record, never a silent default.
- **Confidence honesty**: with the `openai` fallback, confidence values are the
  model's self-report — treat them as *uncalibrated*. Jev returns calibrated
  probabilities; that difference is the reason Jev is the default.
- **Self-contained records**: the output carries the alert's identifying
  fields, so a downstream tool needs no join back to the input.
- **No alert data in the repo**: corpora stay on your side; `fixtures/` is
  gitignored.

## Benchmarks

No alert data ships with this repo — supply your own JSONL.

**Jev** (8 synthetic alerts, one covering each disposition): **8/8 exact
disposition, 1.4 s total, zero drift across two runs** (confidence moved ≤0.04).

**Jev on real telemetry** (Splunk [`attack_data`](https://github.com/splunk/attack_data),
1,185 Sysmon events from an Atomic Red Team encoded-PowerShell run, converted
with `triagedy convert`): 64 process-creation events triaged in **5.1 s**; the
single genuine attack event ranked **#1 of 64 by severity** and was escalated,
while all 63 benign events closed. Noise ratio in that corpus: **1,185:1**.

**Fallback model for comparison** (`gemma4:e2b` on an RPi5, CPU inference,
`--jobs 1`): 8/8 records ok in 490 s (~61 s/alert), **6/8 exact disposition**,
zero dangerous errors.

| Alert | Expected | Local model | Jev |
|---|---|---|---|
| Encoded PowerShell from Word | escalate/investigate | `investigate` (execution) | `escalate` |
| rundll32 from temp path | escalate/investigate | `investigate` (execution) | `investigate` |
| LSASS access from Downloads | escalate/investigate | `investigate` (credential_access) | `escalate` |
| Sanctioned GPO maintenance w/ change ticket | close | `close` | `close` |
| Authorized scanner (asset registry says so) | close | `close` | `close` |
| RDP brute-force → success from TOR exit | escalate/contain | `investigate` ⚠️ | `contain` |
| Encrypted archive outbound from DB server | escalate/contain | `investigate` ⚠️ | `investigate` |
| New admin account, no change ticket | investigate | `investigate` | `investigate` |

Both models produced **zero dangerous errors** — no malicious activity was ever
dismissed. The local model's two deviations were conservative (flag for
investigation). On small hardware the model is the whole memory story:
`gemma4:e2b` sits at ~6.8 GB resident, so keep one inference slot (`--jobs 1`)
and use `--backend mock` for iteration.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
workflow, the local gate, and what a good change looks like.

## Security

See [SECURITY.md](SECURITY.md). Report vulnerabilities through GitHub's private
advisory flow, not a public issue.

## License

MIT — see [LICENSE](LICENSE).
