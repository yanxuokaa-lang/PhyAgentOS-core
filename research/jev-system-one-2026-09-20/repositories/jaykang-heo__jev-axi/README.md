# jev-axi

Typed judgments about a text from TypeSafe's Jev — it picks one option from a closed set, gives a yes/no probability, or scores against a rubric. **Jev returns numbers, never prose, code, or explanations.** A result is evidence to threshold on in your own code, not an authoritative decision.

## Install

```sh
npm install -g github:jaykang-heo/jev-axi#jev-axi-v0.1.0
jev-axi          # dashboard: key presence, pinned model, examples
jev-axi --help   # command index
```

Private repository; installs from GitHub tags, never from npm. `jev-axi update --check` compares your install against the newest `jev-axi-v*` tag.

## Key

`jev-axi` reads `TYPESAFE_API_KEY` from the environment, else from `~/.config/jev-axi/env` (a `TYPESAFE_API_KEY=` line, file mode `600` — anything looser is refused). The key is sent only as an `Authorization` header passed to curl on file descriptor 3: never on a command line, in a child environment, in output, or in a log.

## Commands

Every question needs `--state <file|->` — the text Jev judges, read verbatim (`-` reads stdin). If the file parses as JSON it is sent as structured `state`; otherwise as a string.

### choice — pick one option

```sh
jev-axi choice --state bug.txt \
  --option code="The fault is in application code" \
  --option env="The fault is in the environment" \
  --none
```

```text
"jev-axi":
  question: q
  type: choice
  choice: code
  confidence: 0.78
  winning_probability: 0.71
  probabilities[3]{option,p}:
    code,0.71
    env,0.22
    none,0.07
  model: jev-1.13.0
  latency_ms: 412
  tokens: 55
help[1]:
  Threshold on confidence AND winning_probability in your own code; a noul's number is not on the same scale as a choice's confidence
```

Options come from repeated `--option name="<criterion>"` or `--options-file options.json` (`{"name": "criterion"}` — equivalent requests). `--none` appends `none: "Neither of the above / none apply"` so Jev can decline instead of forcing a pick.

### noul — yes/no as a probability

```sh
jev-axi noul --state diff.txt --ask "The new code handles the empty case correctly"
```

```text
"jev-axi":
  question: q
  type: noul
  noul: 0.24
  model: jev-1.13.0
  latency_ms: 388
  tokens: 27
help[1]:
  Threshold on confidence AND winning_probability in your own code; a noul's number is not on the same scale as a choice's confidence
```

### score — rate against a rubric

```sh
jev-axi score --state post.txt --rubric publishability.txt
```

```text
"jev-axi":
  question: q
  type: score
  score: 6.2
  legend:
    "0": unusable
    "1": poor
    ...
    "9": exemplary
  probabilities[10]{level,p}:
    "6",0.25
    "5",0.18
    ...
  confidence: 0.77
  winning_probability: 0.25
  model: jev-1.13.0
  latency_ms: 405
  tokens: 52
help[1]:
  Threshold on confidence AND winning_probability in your own code; a noul's number is not on the same scale as a choice's confidence
```

The score is probability-weighted across the levels and can land between them.

### ask — several questions, one request

Up to 32 questions ride one call for almost no extra cost or latency — the question, not the call, is the unit worth thinking in.

```sh
jev-axi ask --state post.txt --questions-file questions.json
```

`questions.json` is the vendor schema verbatim — forwarded exactly as written:

```json
{
  "audience": {"type": "choice", "criteria": {"devs": "For developers", "execs": "For executives"}},
  "accurate": {"type": "noul", "question": "Every claim in this text is accurate"},
  "clarity": {"type": "score", "rubric": "0=incoherent ... 9=crystal clear"}
}
```

Output is `answers{<id>}` — each question id maps to the same typed fields the single commands return.

## The two numbers

Choice and Score answers carry **two distinct numbers**: `winning_probability` is the probability Jev assigned to the winning option/level; `confidence` is Jev's confidence in the overall answer. They move independently — threshold on **both** (`winning_probability ≥ floor` AND `confidence ≥ floor`), not confidence alone. A `noul` is a single 0–1 probability and is **not** on the same scale as a `confidence` — do not compare them.

## Model pin

Requests pin `jev-1.13.0` (not a moving alias). The `model:` field in every result reports what actually answered — if a pin or `--model` override ever resolves to something unexpected, that field is the tell.

## Exit codes

| Exit | Code | Meaning |
|---:|---|---|
| 0 | — | success |
| 1 | `AUTH` | HTTP 401/403 — key rejected |
| 1 | `REJECTED` | HTTP 400/404/422 — vendor refused the request |
| 1 | `RATE_LIMITED` | HTTP 429/529 (suggests retry delay) |
| 1 | `HTTP` | other non-2xx |
| 1 | `TIMEOUT` | curl failed or timed out |
| 1 | `BAD_RESPONSE` | HTTP 200 but the body failed schema validation — reported as failure, never repaired into a judgment |
| 2 | `NO_KEY` | no key in env or `~/.config/jev-axi/env` |
| 2 | `VALIDATION_ERROR` | bad flag, unreadable/malformed file, unknown command |

## Current guidance lives in the CLI

This README orients; the CLI is the source of truth: `jev-axi` (dashboard), `jev-axi --help`, `jev-axi <command> --help`.
