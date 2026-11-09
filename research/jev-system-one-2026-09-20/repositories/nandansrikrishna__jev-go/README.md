# Jev Go CLI

A standalone Go CLI and MCP server for TypeSafe's Jev model. Every command runs
in a single binary with no Python dependency. The separate
[Python integration](https://github.com/nandansrikrishna/jev-agent-tool) remains available.

**Public beta 0.1.0-beta.2.** An independent community integration, not an official
TypeSafe product. Bring your own [TypeSafe API key](https://console.typesafe.ai/).
No account with this project, hosted proxy, or shared API key is needed.

## Install and authenticate

Download a prebuilt archive from the
[v0.1.0-beta.2 release](https://github.com/nandansrikrishna/jev-go/releases/tag/v0.1.0-beta.2).
Choose your OS and architecture, verify it with `SHA256SUMS`, and extract it.
Every archive contains the binary, license, and [installation instructions](INSTALL.md).
No Go or Python installation is needed for the binary.

With Go 1.25 or newer, install the tagged version directly:

```sh
go install github.com/nandansrikrishna/jev-go/cmd/jev@v0.1.0-beta.2
```

Or build from this checkout:

```sh
go build -o bin/jev ./cmd/jev
# Or install to $(go env GOPATH)/bin (add that directory to PATH):
go install ./cmd/jev
jev auth
jev init
jev evaluate --input jev-demo/tickets.jsonl --questions jev-demo/questions.json --output results.jsonl
python3 jev-demo/summarize.py results.jsonl
```

The compiled binary has no Python runtime dependency. `jev mcp` runs a native
stdio server using the [official MCP Go SDK](https://github.com/modelcontextprotocol/go-sdk)
(v1.8.0). No sibling checkout, Python package, or `JEV_PYTHON` setting is needed.
The optional example summary script uses Python 3; you can process JSONL output
with any language or tool.

Both the Go and Python CLIs are named `jev`; use this project's `bin/jev`
explicitly if both are installed.

`jev auth` prompts without echoing your key. On macOS/Linux it saves the key to
`~/.config/jev/api-key` with mode `0600`; on Windows it uses Windows Credential
Manager (compatible with the Python package). `TYPESAFE_API_KEY` overrides saved credentials.
For automated setup, pipe a key to `jev auth --stdin`. Never put keys in question
files, source code, or MCP arguments. Your records and questions go directly to
TypeSafe and use your account's API quota. This tool has no analytics or telemetry
of its own. Local result files contain model judgments and your record IDs.

`jev init` creates a new `jev-demo` directory containing the example questions,
tickets, and summary script; `--directory` chooses a different directory.
The examples below use the repository's `examples/` directory; for a package-only
installation, substitute `jev-demo/`.

## Evaluate a dataset

```sh
jev validate --questions examples/questions.json --input examples/tickets.jsonl
jev evaluate --input examples/tickets.jsonl --questions examples/questions.json --output results.jsonl
python examples/summarize.py results.jsonl
```

Input is JSONL, one `{"id":"unique-string", "state":"context to evaluate"}` per
line. State can also be a JSON object or array. The questions file maps IDs to:

- `choice`: `instructions` plus `criteria` mapping option names to descriptions.
- `score`: `instructions` plus an ordered `criteria` list, at least two levels.
- `noul`: `instructions` for a yes/no judgment; returns probability of yes.

See `examples/questions.json` for all three. Use `jev schema` for the underlying
SDK JSON Schema (embedded from typesafe-sdk 0.7). Jev additionally requires nonempty question IDs, instructions,
and at least two criteria for choice/score; `jev validate` checks these rules.

Output preserves the input ID and includes `answers`, `model`, `usage`, and a
request fingerprint. Failed records contain `error` instead of answers.
Errors intentionally omit upstream bodies and private input. All JSONL results
go to the output file or stdout; progress and diagnostics go to stderr.
Input and configuration errors on stderr include a stable machine-readable
`code` and, when applicable, a safe `field`, `path`, or JSONL `line` so an agent
can repair the invocation without inspecting private record contents.

```sh
# stdin/stdout pipelines
cat examples/tickets.jsonl | jev evaluate --input - --questions examples/questions.json > results-pipe.jsonl

# Continue an interrupted run, retry failed records, skip unchanged successes
jev evaluate --input examples/tickets.jsonl --questions examples/questions.json --output results.jsonl --resume
```

`--workers 4` is the default (1–32 supported). `--model jev-latest` is configurable.
The Go CLI validates responses and retries connection failures, HTTP 408/429,
and HTTP 5xx twice, with exponential backoff and Retry-After support. Requests
have a 60-second timeout; retries have a 30-second budget including elapsed time.
`TYPESAFE_BASE_URL` can override the default `https://api.typesafe.ai` API root. Each record is one API request containing
all its questions. Resume fingerprints cover record contents, questions, and model
name. A change to any of these triggers another evaluation. The `jev-latest` alias
can change upstream without changing the fingerprint: start a new output file if
you want to refresh old predictions. Resume appends attempts; use the latest result
per ID when aggregating. The example summary does this.

Existing output files are protected unless `--resume` is supplied. A malformed or
partially written JSONL output fails safely; repair its final line before resuming.
Exit codes: `0` success, `1` evaluation failures, `2` input/configuration error,
`130` interrupted. The CLI loads input records in memory and uses a bounded Go worker pool; it has
no hosted queue or distributed workers. Do not run concurrent writers on one output.

## MCP

`jev mcp` runs a native Go stdio server with three tools:

- `question_schema`: discover the question format.
- `evaluate`: evaluate a single context with dynamically authored questions.
- `evaluate_batch`: evaluate 1–50 `{id, state}` records with per-record results.

Tool results include JSON text and structured content. Batch results preserve
input order and include per-record errors, a failure count, and an `ok`,
`partial_failure`, or `failed` status. An entirely failed batch and single-record
failures set MCP `isError`; input errors are sanitized to omit private content.
Cancellation propagates to in-flight HTTP requests. Schema discovery and tool
listing work without credentials; evaluation reads the normal CLI credentials.

For Codex, after installing the binary and authenticating:

```sh
codex mcp add jev -- jev mcp
```

If your desktop app cannot find `jev` on PATH, use its absolute path (`which jev`
on macOS/Linux, `where jev` on Windows). Other MCP clients can use:

```json
{
  "mcpServers": {
    "jev": {
      "command": "/absolute/path/to/jev",
      "args": ["mcp"]
    }
  }
}
```

The server reads the same local credential file or environment variable as the
CLI (including Windows Credential Manager). Restart/reconnect your agent after registration. For batches that exceed the
client's tool timeout, use fewer records or run the CLI; MCP batch results are
returned inline and are not resumable. No remote hosting or OAuth is included.

## Agent usage

Define narrow questions with complete instructions. Group all independent
questions about one record into one call. Aggregate, threshold, and rank in code;
inspect representative records before drawing conclusions. Questions do not see
each other's answers. Probabilities and scores are predictions, not proof.
Use the CLI for large file-based jobs and MCP for direct interactive calls.

## Development

```sh
go test -race ./...
go vet ./...
go build -o bin/jev ./cmd/jev
# Optional integration tests using the sibling Python environment:
"../Jev 3/.venv/bin/python" -m pytest -q tests
```

Go tests exercise real stdio MCP sessions with an empty PATH (no Python),
evaluation against a mock API, validation, and cancellation. The optional Python
tests provide an independent MCP client and ensure
its embedded question schema and templates match the installed Python package.
Set `JEV_TEST_BIN` to test a different binary. Go CI runs on Linux, macOS, and
Windows without needing the sibling project or an API key.

See [RELEASING.md](RELEASING.md) for Go binary release instructions.
API documentation: https://docs.typesafe.ai/api
