# jev-mcp

An MCP server that gives a coding agent one tool: **ask Jev a typed question and get a short answer
back.**

[Jev](https://typesafe.ai) is a model that generates no text. You hand it some state plus typed
questions; it returns a decision for each one with a calibrated probability. Answers come back in
roughly 300ms.

This server exists so an agent can reach for that mid-task, the same way it reaches for a file read,
instead of spending a turn reasoning about a question whose answer space is three words wide.

## What it is for

Small judgments that are bounded and that you would otherwise think about:

- *Are these two things really two things, or one?*
- *Which of these four categories does this belong to?*
- *Is this claim supported by the text above it?*

And what it is **not** for: anything that needs prose, code, a number it has to compute, or an answer
you cannot enumerate in advance. Jev writes nothing. It only chooses.

## Requirements

- **Node 20.12 or newer.** The server loads its own `.env` with `process.loadEnvFile`, which arrived
  in 20.12. On anything older it exits at startup with `TypeError: process.loadEnvFile is not a
  function` rather than pretending your key is missing.
- **A TypeSafe API key**, from [typesafe.ai](https://typesafe.ai).

## Setup

```sh
git clone https://github.com/CodeCampusCo/jev-mcp.git
cd jev-mcp
npm install
npm run build
```

`npm run build` compiles `src/` to `dist/`. `dist/` is not committed, so this step is required after
a clone and after a `git pull`.

Then put your key in a `.env` next to this README:

```sh
cp .env.example .env
```

```sh
TYPESAFE_API_KEY=your-key-here
```

The server reads that file at startup, resolved against its own directory rather than wherever
your agent happened to launch it from. The key stays with the server instead of being written
into your agent's configuration. An exported `TYPESAFE_API_KEY` still works and wins over the
file, so a one-off run can override it.

## Connect it to your agent

The server speaks MCP over stdio. Every client needs the same two things, the command `node` and
the absolute path to `dist/index.js`, written in whatever shape that client uses.

**Claude Code:**

```sh
claude mcp add jev -- node /absolute/path/to/jev-mcp/dist/index.js
```

**Claude Desktop, Cursor, and most other clients** take a JSON config with an `mcpServers` object.
That file is `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows, and `~/.cursor/mcp.json` for Cursor:

```json
{
  "mcpServers": {
    "jev": {
      "command": "node",
      "args": ["/absolute/path/to/jev-mcp/dist/index.js"]
    }
  }
}
```

**VS Code** uses the same entry under `servers` rather than `mcpServers`, in `.vscode/mcp.json`.

The path must be absolute: the client picks the working directory, and it is rarely this one.
Restart the client after editing its config, then check that a tool named `evaluate` has appeared.

If you would rather keep the key in the client's config than in `.env`, pass it as an environment
variable on the server entry instead. Note that most of these config files are not protected, and
some are synced.

## Configuration

| Variable | Required | What it does |
|---|---|---|
| `TYPESAFE_API_KEY` | yes | Your TypeSafe key. The server refuses to start without it. |
| `AXIOM_API_KEY` | no | An Axiom ingest token. Set it and every call is logged; leave it empty and nothing is sent. See [Logging](#logging). |
| `TYPESAFE_API_URL` | no | Points the server at a different endpoint. Defaults to `https://api.typesafe.ai/v1/systemone`. |
| `TYPESAFE_DEFAULT_MODEL` | no | The model used when a call does not name one. |

Each of these can live in `.env` or in the environment; the environment wins.

**The model is pinned to a version, not to `jev-latest`**, so probabilities cannot move underneath
you. The API advertises only the `jev-latest` and `jev-preview` aliases, so if the pinned version is
ever withdrawn, calls fail with `Unknown model` instead of quietly answering differently. Moving the
pin without a code change is what `TYPESAFE_DEFAULT_MODEL` is for.

## The tool

One tool, `evaluate`. It takes the state to judge and a map of questions, and returns the API's
response unchanged.

```jsonc
{
  "state": "The cat sat on the mat. It is a large orange tabby.",
  "questions": {
    "colour": {
      "type": "choice",
      "instructions": "What colour is the animal?",
      "criteria": { "orange": "The animal is orange.", "black": "The animal is black." }
    },
    "large": {
      "type": "noul",
      "instructions": "Is the animal large for its species?"
    }
  }
}
```

The answers come back under the ids you chose. This is a real response, passed through untouched:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "colour": {
      "type": "choice",
      "choice": "orange",
      "confidence": 1.0,
      "probabilities": { "orange": 1.0, "black": 0.0 }
    },
    "large": { "type": "noul", "noul": 0.82 }
  },
  "usage": { "input_tokens": 433, "output_tokens": 70 }
}
```

A `score` answer carries `score`, a probability-weighted level that lands *between* levels, so
expect `1.03` rather than `1`. It also carries `confidence`, a `legend` naming each level, and
`probabilities` keyed by level.

The fields above are the API's, not this server's. It adds nothing and removes nothing, so anything
the API starts returning arrives here without a change on this side.

### Question types

| type | ask it | returns |
|---|---|---|
| `noul` | a yes/no proposition | a probability between 0 and 1 |
| `choice` | pick one of up to 255 options | the option, a probability for each, and a confidence |
| `score` | rate against 2-10 ordered levels | the level, probabilities, a legend, and a confidence |

`criteria` is optional for `noul` (`{"true": …, "false": …}`), required for `choice` (a map of option
name to description), and required for `score` (an ordered array of at least two level
descriptions).

Ask several questions in one call whenever you can. They are answered in parallel against the same
state, so a question you might not need costs its own tokens and almost no extra time.

## Things worth knowing before you use it

**It cannot say "I don't know."** Forced into a yes/no or a fixed list, it will pick something even
when nothing fits, and it will pick confidently. Include a "none of these" option whenever one is
possible.

**It does not count and it does not do arithmetic.** It reads dates as text, not as quantities that
come before or after each other. Keep all of that in your own code.

**Accuracy falls as the state fills with material the question does not need.** Filter first; send
the fields the question actually reads.

**Probabilities are not comparable across questions.** The same question asked as a `noul` and as a
yes/no `choice` can disagree, and a question and its negation need not sum to one. Never carry a
threshold from one question type to another.

**Limits.** 255 options per choice, 10 levels per score, roughly 32k tokens of state and 64k for the
whole request.

## Errors

The server checks two things and lets the API reject everything else. Every failure comes back as an
MCP tool error, never as a crash:

| What went wrong | What the caller sees |
|---|---|
| No `state` | "`state` is required: give Jev the material the questions are about." |
| No `questions`, or an empty object | "`questions` must be a non-empty object mapping your own question ids to questions." |
| The API returned a non-2xx | `Jev API error (HTTP <status>): <body>` |
| The API could not be reached | `Could not reach the Jev API: <reason>` |

A request that fails on 408, 429, 529 or any 5xx is retried twice before it gives up, backing off
from 500ms towards 5s with jitter, and honouring a `retry-after-ms` or `Retry-After` header when one
is sent. Each attempt has a 10s deadline, so the worst case is roughly 31s and an error rather than a
hang.

## Troubleshooting

**The server exits immediately and the tool never appears.** Run it by hand with `npm start` and read
what it prints. `TYPESAFE_API_KEY is not set` means the `.env` is missing, empty, or not next to the
package root. A `TypeError` about `process.loadEnvFile` means the Node running it is older than
20.12; note that your agent may not launch it with the same Node you have on your `PATH`.

**`Cannot find module .../dist/index.js`.** `npm run build` has not been run, or was run before the
last `git pull`.

**`Jev API error (HTTP 401)`.** The key is wrong or expired. `HTTP 400` with `Unknown model` means
the pinned version is gone, so set `TYPESAFE_DEFAULT_MODEL` to a live one.

**Nothing shows up in Axiom.** Logging is silent by design and cannot report its own failure. Check
that `AXIOM_API_KEY` is set and that a dataset named `jev-mcp` exists in that account.

## Logging

Optional, and off unless you set it. Put an Axiom ingest token in `AXIOM_API_KEY` and every call is
shipped to the `jev-mcp` dataset. With no token nothing is sent and nothing else changes, so a clone
does not need an Axiom account.

The dataset name is fixed. Create one called `jev-mcp` in the account that token belongs to. Axiom
drops writes to a dataset that does not exist, and this server swallows the response, so a missing
dataset looks exactly like everything working.

**It logs the request, so a call can be replayed from the record.** The state, the instructions and
the criteria all go in: a row saying a fault was classified, with no state, tells you a fault was
classified but not a fault *in what*, and a replay without the state is not a replay. It is a new
experiment wearing the old question.

The response body does not. It is read for the scalars worth querying and then dropped, so neither
it nor an API error body quoting your input back is ever shipped. The per-answer rows already carry
the type, the value, the confidence and the probability, which is what a replay compares against.

**So assume everything you send through this server reaches your Axiom dataset**, including whatever
an agent happened to be holding in its context when it called.

Each call writes one `call` event, carrying hostname, outcome, duration, HTTP status, how many
attempts it took, the model that answered, token counts and question count. Alongside it goes one
`answer` event per question, carrying the type, the value chosen, the confidence, and the
probability Jev put on the answer it gave.

For provenance, `hostname` answers which machine and `server_instance_id` answers which run: MCP's
`initialize` carries no session id, so that is an id for this server process, and since a stdio
server is spawned per client it separates concurrent sessions on one machine. The client's own
`client_name` and `client_version` are recorded as it reports them.

The `answer` rows are what Jev actually said, one per question *asked*, so a call the API rejected
still records what was asked of it, with an empty probability.

The log is meant to be self-contained: reading a row should not send you looking for something else
to make sense of it. The question ids you choose are therefore not logged. They are keys into your
code, and whoever reads this log is not you. It is whoever maintains the server your agents call
into, and `urgency` means nothing to them. `instructions` is the question itself, in words, on the
row.

`state`, `instructions` and `criteria` are stored as text, serialised when they are not already a
string. Axiom turns each key of a nested object into a dataset column, and those keys would be the
caller's: option names, or every field name anyone ever puts in a state. Left nested, any agent
could add permanent columns to the schema just by naming a field, and the columns describing how the
server behaves would end up buried under them.

Failures are logged as well as successes, since a log of only what worked hides the pattern worth
finding. A rejected request, a non-2xx with its status, a timeout with the number of attempts it
burned, an oversized response.

It cannot delay or break a call: the write is not awaited and every failure inside it is swallowed,
so Axiom being down, slow or misconfigured is invisible to the caller.

Shutdown is the one place it waits, and only there. An MCP client ends stdin, gives the server two
seconds, then sends `SIGTERM`, which Node acts on immediately. A cold ingest takes about 2.6s from
Bangkok against 275ms warm, nearly all of it TLS, so the first write of a server that is closed soon
after its call would never land, and would fail silently. `SIGTERM` therefore drains what is already
in flight, capped at 1.9s so it stays inside the window before the client escalates to `SIGKILL`.
That is the only wait in the whole path, and the response is long gone by then.

## Design

The server is a passthrough. It does not interpret the response, reshape it, or summarise it. The
raw JSON goes back to the caller, so probabilities arrive intact and any field the API adds later
passes through without a change here.

It talks to the API over plain `fetch` rather than a vendor SDK. The request surface is a single
endpoint with three question types, and a passthrough gets no benefit from typed responses it never
reads. Retry behaviour is reimplemented deliberately, matching the official SDKs including the
`retry-after-ms` header that is not in the published API reference.

## Development

```sh
npm test
```

That builds and then runs the suite with Node's own test runner, with no test framework and no
extra dependencies. The tests stub `fetch`, so they never touch the network and need no API key. CI runs
the same command on every pull request.

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening one, and [SECURITY.md](SECURITY.md) for what
leaves your machine and how to report a vulnerability.

## Licence

MIT.
