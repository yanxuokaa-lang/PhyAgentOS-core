# jev.mcp

An MCP server that gives an AI agent **typed decisions instead of prose**. It
exposes [Jev](https://docs.typesafe.ai), TypeSafe's flagship System One model, as
five tools:

- **`classify`** — choose one option from a list you define. Returns the chosen
  option, the probability of every option, and confidence.
- **`score`** — rate content against ordered rubric levels. Returns a
  probability-weighted score, the level legend, and confidence.
- **`check`** — ask a yes/no question. Returns the probability that the answer is
  yes.
- **`ask`** — evaluate many typed questions, of mixed types, against one state in
  a single call.
- **`models`** — list the models and aliases the account can request.

## What Jev is

Large language models generate text. When your code needs a judgment, coercing a
text generator into structured output and parsing it back is the weak link. Jev
is a *System One model*: you send a **state** and a set of **typed questions**,
and it returns typed values and probability distributions directly, in 70–500 ms,
with no text generation and nothing to parse.

It answers three question types:

| Type       | Question                                     | Answer                                                        |
| ---------- | -------------------------------------------- | ------------------------------------------------------------- |
| `noul`     | Is this statement true?                      | `noul` — the probability that yes, from 0 to 1                |
| `choice`   | Which one of these options is it?            | `choice`, `probabilities`, `confidence`                       |
| `score`    | How does this rate against ordered levels?    | `score`, `legend`, `probabilities`, `confidence`              |

Every question is evaluated in parallel and in isolation against the same state,
so adding questions barely changes latency and does not cause context rot.
Questions stay atomic and code does the composing: ask separately about severity,
category, and sentiment, then combine the answers with your own weights.

## Requirements

An API key from the [TypeSafe console](https://console.typesafe.ai/settings/keys),
passed as `TYPESAFE_API_KEY`.

## Usage

### MCP client config

```json
{
  "mcpServers": {
    "jev": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "TYPESAFE_API_KEY",
        "hangarbay/jev.mcp:latest"
      ]
    }
  }
}
```

Or run the binary directly:

```json
{
  "mcpServers": {
    "jev": {
      "command": "jev-mcp",
      "args": ["serve"],
      "env": { "TYPESAFE_API_KEY": "ts_..." }
    }
  }
}
```

### Tools

- **`classify`** — pick one option from a list.
  - `state` (string | object | array, required): the content to evaluate
  - `instructions` (string, required): what to decide
  - `options` (array, required): at least two `{name, description?}` entries
  - `model` (string, optional): model override, defaults to `jev-latest`
- **`score`** — rate against ordered levels.
  - `state` (string | object | array, required)
  - `instructions` (string, required): what to rate
  - `levels` (array, required): at least two descriptions, lowest first
  - `model` (string, optional)
- **`check`** — ask a yes/no question.
  - `state` (string | object | array, required)
  - `instructions` (string, required): the yes/no statement, stated as one thing
  - `true` (string, optional): what a yes means
  - `false` (string, optional): what a no means
  - `model` (string, optional)
- **`ask`** — many typed questions in one call.
  - `state` (string | object | array, required)
  - `questions` (object, required): ids mapped to
    `{type, instructions, criteria}`, where `criteria` is an object of option to
    description for `choice`, an array of levels for `score`, and an optional
    `{true, false}` object for `noul`
  - `model` (string, optional)
- **`models`** — no arguments.

Every tool returns both a short text rendering and structured content: a client
can show the text and read `choice`, `score`, `noul`, `probabilities`,
`confidence`, and `input_tokens` as data.

### CLI

The same surface is available one-shot, which is handy for scripting and for
checking a threshold:

```bash
export TYPESAFE_API_KEY=ts_...

jev-mcp classify -state "My payout failed 3 days ago!" \
  -instructions "Which team should handle this?" \
  -options "billing: payments and refunds
technical: bugs and outages
sales: pricing and upgrades"

jev-mcp score -state "$(cat ticket.txt)" \
  -instructions "How frustrated is the customer?" \
  -levels "Calm
Frustrated
Angry"

jev-mcp check -state "$(cat ticket.txt)" -instructions "Does this convey urgency?" -json

jev-mcp ask -state "$(cat ticket.txt)" -questions questions.json
jev-mcp models
jev-mcp serve
```

`-state` accepts plain text, or JSON if you pass an object or array. Use
`-state-file -` to read the state from stdin, and `-json` to print the structured
answer instead of the text rendering.

`questions.json` for `ask`, either bare or wrapped:

```json
{
  "department": {
    "type": "choice",
    "instructions": "Which team should handle this?",
    "criteria": { "billing": "payments and refunds", "technical": null }
  },
  "frustration": {
    "type": "score",
    "instructions": "How frustrated is the customer?",
    "criteria": ["Calm", "Frustrated", "Angry"]
  },
  "urgency": {
    "type": "noul",
    "instructions": "Does this convey urgency?"
  }
}
```

### Environment

| Variable                | Meaning                                                | Default                  |
| ----------------------- | ------------------------------------------------------ | ------------------------ |
| `TYPESAFE_API_KEY`      | API key (required)                                     | —                        |
| `TYPESAFE_BASE_URL`     | API root                                               | `https://api.typesafe.ai` |
| `TYPESAFE_MODEL`        | model alias used when a call does not name one         | `jev-latest`             |
| `TYPESAFE_TIMEOUT`      | per-request timeout                                    | `60s`                    |
| `TYPESAFE_MAX_RETRIES`  | retries after the first attempt                        | `3`                      |

Rate limits (429) and overload (529) are retried with exponential backoff,
honoring `Retry-After`. Other 4xx responses, such as a bad key or an invalid
question, fail immediately with the API's own message.

## Docker

```bash
make docker        # build jev.mcp:local
make test          # go vet ./... && go test ./...

docker run --rm -i -e TYPESAFE_API_KEY hangarbay/jev.mcp:latest
```

The image is a static binary on Alpine, runs as a non-root user, and speaks MCP
over stdio, so `-i` is required. CI publishes `hangarbay/jev.mcp:latest` and
`hangarbay/jev.mcp:<sha>` on every push to `main`; `make update` pulls the newest
image and restarts the local container.

## Layout

```
cmd/jev-mcp          CLI entrypoint and the MCP server wiring
internal/typesafe    System One HTTP client: requests, answers, retries, errors
internal/render      text rendering of answers
internal/classify    classify tool  (choice)
internal/score       score tool     (score)
internal/check       check tool     (noul)
internal/ask         ask tool       (many typed questions in one call)
internal/models      models tool
```

## Notes

- Jev is a decision model, not a chat model. Ask it one specific, well-scoped
  thing at a time; decompose broad judgments into several questions and combine
  the answers in code.
- Confidence is not probability. `probabilities` tells you what the answer is;
  `confidence` tells you whether to act on it. Gate automation on both.
- Only input tokens are billed, and output tokens are free, so batching questions
  into one call is the cheap path.

## License

MIT. See [LICENSE.md](LICENSE.md).
