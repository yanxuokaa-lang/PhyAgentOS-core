# SemDecide

**Typed semantic decisions for Unix pipelines and CI, powered by TypeSafe AI Jev.**

SemDecide is `grep` for meaning and `jq` for judgment. Pipe in text or JSONL and get a predicate, route, score, filtered stream, and stable process exit code without writing prompt, parsing, retry, or confidence-handling glue.

```bash
printf '%s' 'Login from a new country, followed by payout changes.' \
  | semdecide is 'This describes a plausible account takeover'
```

```text
TRUE probability=0.860 threshold=0.700
```

## Why

Exact string rules cannot express concepts such as:

- “This customer is likely to churn.”
- “This change introduces a breaking API behavior.”
- “This record may describe account takeover.”
- “This response is grounded and complete.”

General-purpose LLM calls can make those judgments, but they are awkward to place in shell scripts. They generate text that must be parsed, are comparatively slow and expensive, and often hide uncertainty.

Jev returns typed decisions instead. SemDecide gives those decisions predictable Unix input, output, limits, retries, schemas, and exit behavior.

## Install

SemDecide requires Python 3.10 or newer.

```bash
pipx install https://github.com/sharziki/semdecide/releases/download/v0.2.1/semdecide-0.2.1-py3-none-any.whl
# or, with uv
uv tool install https://github.com/sharziki/semdecide/releases/download/v0.2.1/semdecide-0.2.1-py3-none-any.whl
```

SemDecide is not yet published on PyPI. The commands above install the signed-off GitHub release artifact directly.

From a source checkout:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Set a [TypeSafe AI](https://typesafe.ai) API key:

```bash
export TYPESAFE_API_KEY='...'
```

SemDecide also reads `~/.config/typesafe/credentials.env`:

```bash
TYPESAFE_API_KEY='...'
```

Keep that file mode `600`. Do not pass credentials as command-line arguments.

## Commands

### `is`: semantic predicates

```bash
cat incident.txt | semdecide is \
  'This describes a security-sensitive incident requiring human attention'
```

Use `--json` for a stable machine interface:

```bash
cat incident.txt | semdecide is 'This is an account-takeover signal' --json
```

```json
{
  "schema_version": "1",
  "command": "is",
  "verdict": "true",
  "probability": 0.86,
  "confidence": null,
  "threshold": 0.7,
  "model": "jev-1.13.0",
  "usage": {
    "input_tokens": 120,
    "output_tokens": 8
  }
}
```

Configure local policy with `--threshold` and `--uncertainty-margin`. SemDecide does not silently force borderline results into true or false.

### `choose`: route among named options

```bash
cat ticket.txt | semdecide choose \
  'Which queue should receive this ticket?' \
  --option support='ordinary product support' \
  --option security='possible security incident' \
  --option billing='billing or payment issue' \
  --json
```

The result preserves the selected option, every option probability, and Jev confidence. `--min-confidence` controls whether the process exits as uncertain.

### `score`: ordered semantic rubrics

```bash
cat answer.txt | semdecide score \
  --criterion 'How trustworthy is this answer?' \
  --level 'unsafe or misleading' \
  --level 'mostly correct but incomplete' \
  --level 'correct, grounded, and complete' \
  --json
```

### `filter`: semantic JSONL filtering

```bash
cat tickets.jsonl | semdecide filter \
  'The record indicates urgent churn risk or active customer impact' \
  --field text
```

Input order is preserved. Matching records receive `_semdecide` metadata:

```json
{"id":42,"text":"We will cancel unless today's outage is fixed.","_semdecide":{"schema_version":"1","probability":0.9,"threshold":0.7,"model":"jev-1.13.0"}}
```

Use `--raw` to emit the original records without metadata.

### `guard`: an opinionated agent-safety recipe

The original REFLEX action firewall now ships as one recipe built on SemDecide's primitives:

```bash
semdecide guard \
  --action 'Delete the production customer database' \
  --context 'No exact approval or backup exists' \
  --json
```

Jev evaluates narrow signals such as authorization, destructiveness, ambiguity, secret exposure, and consequence. Deterministic local code returns `allow`, `escalate`, or `block`.

`semdecide check` remains a deprecated compatibility alias for one minor release. A temporary `reflex` executable alias also remains for users of the prototype.

## Input and output

Text commands accept exactly one of:

- stdin
- `--text '...'`
- `--file path`

SemDecide rejects empty, binary, invalid UTF-8, oversized, and malformed structured input before calling Jev.

Useful controls:

```text
--max-input-bytes   cap submitted input, default 1,000,000
--timeout           per-attempt provider timeout, default 10 seconds
--retries           transient retry count, default 2 and maximum 5
--quiet             emit no output and use only the exit code
--json              stable JSON output for is, choose, and score
```

`filter` accepts JSONL objects and additionally supports `--max-records`, `--field`, and `--raw`.

With `--json`, parsing and runtime failures are emitted as a versioned JSON error object on stderr. Provider details are intentionally redacted. `--quiet` suppresses both normal output and diagnostics, leaving only the exit code.

## Exit codes

Semantic commands follow grep-like behavior while keeping uncertainty and provider failure distinct:

| Code | Meaning |
|---:|---|
| `0` | true, selected, scored, or at least one definite filter match |
| `1` | false or no filter matches |
| `2` | invalid local input or command usage |
| `3` | uncertain result under the configured margin or confidence floor |
| `4` | provider, authentication, timeout, or invalid-response failure |

The `guard` recipe retains its compatibility contract:

| Code | Meaning |
|---:|---|
| `0` | allow |
| `10` | escalate |
| `20` | block |
| `2` | invalid local input |

Provider failures in `guard` fail closed to `escalate`.

## Safety and privacy

Input evaluated by SemDecide is sent to TypeSafe AI. Do not submit material your data policy forbids sending to that provider.

SemDecide is not an authorization system, sandbox, security proof, or tool executor. Semantic decisions can be wrong. Keep deterministic permission checks around money, credentials, production infrastructure, private data, and irreversible operations.

SemDecide is an independent open-source project and is not an official TypeSafe AI product.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q src tests
```

The runtime is dependency-free. Live-provider tests are acceptance checks, not part of the deterministic default suite.

See:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/spec/semdecide.md`](docs/spec/semdecide.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`SECURITY.md`](SECURITY.md)

## License

MIT
