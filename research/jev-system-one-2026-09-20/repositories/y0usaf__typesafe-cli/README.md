# typesafe-cli

A shell command for [Jev](https://docs.typesafe.ai): state and typed questions in,
typed answers out. Jev does not write prose, so nothing here parses any. A noul
comes back as the probability that the answer is yes, a choice as one of the
options you supplied plus the confidence behind it, and a score as a position on
your rubric.

```
$ echo "I was charged twice for order A-104. Please refund the duplicate charge." |
    jev noul "Does the state request a refund?"
noul  0.93
```

Jev evaluates the questions in one request in parallel and in isolation, so
asking four costs one round trip of about 0.3s and not four. That is what `ask`
is for: a whole document per call, not a loop.

## Run it

```bash
nix run . -- noul "Is this a bug report?" --state "app crashed"   # from the checkout
node src/cli.ts --help
npm install -g @y0usaf/typesafe-cli && jev --help
```

Node 22.18 or newer. The checkout runs the TypeScript source directly, so
`nix run` and `node src/cli.ts` need no build step. npm is the exception: Node
refuses to strip types under `node_modules`, so `npm publish` compiles `src/`
to `dist/` first (`tsc -p tsconfig.build.json`).

The flake exposes `packages.default`, so a system or home configuration can
take this repository as an input and get a `jev` on `PATH`.

## Key

First hit wins:

1. `--key`
2. `TYPESAFE_API_KEY`
3. `TYPESAFE_API_KEY_FILE`, a path to read
4. `apiKey` in `~/.pi/agent/pi-jev.json`, then `apiKeyFile` there
5. `~/Tokens/TYPESAFE_API_KEY.txt`

Point 4 is the config the [pi-jev](https://github.com/y0usaf/pi-jev) extension
already reads, so one key file serves both. The same file may also set `model`
and `endpoint`. `--verbose` names the source it used.

## Commands

| Command | Answer | Notes |
| --- | --- | --- |
| `jev noul <question>` | `noul`, 0 to 1 | The probability that the answer is yes. There is no separate confidence: the probability is the whole answer. |
| `jev choice <question> --option NAME[=DESCRIPTION]` | `choice`, `confidence` | Two options minimum. The description is context for the model, not output. |
| `jev score <question> --level LABEL` | `score`, `confidence` | Two levels minimum, lowest first. The score can land between levels. |
| `jev ask [FILE]` | every answer | Many questions, one request. Format below. |

The state is `--state TEXT`, `--state-file FILE` (`-` reads stdin), or a pipe:

```bash
$ jev choice "What failed?" --state "ERROR: could not connect to server: connection refused (127.0.0.1:5432)" \
    --option db --option auth --option other --probs
choice  db  conf 0.99
  db     0.99
  other  0.01
  auth   0.00
```

`--json` prints the whole response instead, so stdout stays pipeable either way.

## Many questions, one request

```bash
$ cat > questions.json <<'JSON'
{
  "questions": [
    { "id": "refund_requested", "type": "noul",
      "instructions": "Does the state request a refund?" },
    { "id": "request_type", "type": "choice",
      "instructions": "What is the main request in the state?",
      "options": [
        { "name": "refund", "description": "The customer wants money returned" },
        "rebooking",
        "information"
      ] },
    { "id": "frustration", "type": "score",
      "instructions": "How frustrated does the customer appear in the state?",
      "levels": ["Calm and neutral", "Concerned but civil", "Very angry or using strong language"] }
  ]
}
JSON
$ printf '%s\n' 'My flight was cancelled. Can I get a refund? This is the third time and nobody has answered me.' > ticket.txt
$ jev ask questions.json --state-file ticket.txt --probs --verbose
refund_requested  0.65
request_type      refund  conf 1.00
  refund       1.00
  rebooking    0.00
  information  0.00
frustration       1.36/2  Concerned but civil  conf 0.45
  0 Calm and neutral                     0.00
  1 Concerned but civil                  0.64
  2 Very angry or using strong language  0.36
jev: jev-1.13.0, key from pi-jev.json, 3 question(s), 404 in, 74 out, 0.29s
```

One request, three answers, 404 in and 74 out tokens. Confidence is low on
`frustration` (0.45) because the levels split 0.64 / 0.36: Jev is saying the
rubric does not fit the state well, and 0.45 is worth branching on.
`refund_requested` at 0.65 is a lean, not a verdict, and that is what the
number is for.

`--id NAME` renames the answer key; without it the single-question commands use
the type name (`noul`, `choice`, `score`).

## The questions document

An array of questions, each with its own `id`, or an object keyed by id. A
document may also carry the state, and that state wins over `--state` and
`--state-file`:

```json
{ "state": { "ticket_message": "..." }, "questions": [ ... ] }
```

Choice `options` and score `levels` are sugar for the API's `criteria`: a map of
option to description for a choice, an ordered list of levels for a score. Both
spellings are accepted, so a question copied from the Jev docs works as is. A
noul takes an optional `criteria` of `{ "true": "...", "false": "..." }` text to
pin down what yes and no mean.

The document is validated before the request goes out: a missing instruction, a
duplicate id, a score with one level, or a choice with one option all fail with
exit 2 and cost nothing.

## Flags

```
--state TEXT          the state to judge, inline
--state-file FILE     the state to judge, from a file ('-' reads stdin)
--id NAME             the answer's key, on the single-question commands
--json                print the whole response as JSON
--probs               print the distribution for choice and score
-v, --verbose         model, key source, and token use on stderr
--model NAME          model id, default jev-latest
--endpoint URL        default https://api.typesafe.ai/v1/systemone
--key KEY             API key, ahead of the environment and the key file
--timeout MS          request timeout, default 20000
-h, --help            the usage text
--version             the version
```

Exit codes: 0 answered, 1 the request failed (a 429 or a 5xx is retried twice
first), 2 the command line or the document was wrong. Everything but the answer
goes to stderr.

## Notes

- **One request per run.** A second request is for a question whose options, or
  whose state, could not be built until the first answer arrived. Everything
  else belongs in the same document: asking a question you might not need is
  close to free, so ask the speculative ones and ignore the answers your code
  does not use.
- **State and questions share one budget of roughly 32,000 tokens** (about
  150,000 characters of English), so a large log eats the room the questions
  need.
- **Name the field a question is about.** The same refund question over the same
  sentence scored 0.65 as plain text, 0.88 once the sentence sat under a
  `ticket_message` key, and 0.99 once the instruction named that key with a
  backticked path. A handful of runs, not a study, but the direction matches the
  Jev docs and the spread is bigger than run-to-run noise.
- **Scores land between levels.** `1.36/2` is a position on a three-level
  rubric, not a rounded pick; the nearest level is printed after it.
- **Distributions are quantized.** A clear winner leaves the other options at
  `0.00` rather than at some small number, so treat the tail as ordered, not as
  calibrated probability.
- **Question ids are yours.** They are not sent to the model, so write the whole
  question in `instructions`; the id only labels the answer.
- The state, and only the state, is sent to `api.typesafe.ai`, with the key in
  the `Authorization` header.

## Layout

```
src/client.ts   the wire protocol: request shape, retries, timeout, key resolution
src/cli.ts      argv, commands, the questions document, output
flake.nix       the packaged `jev` binary: Node 24 running src/cli.ts
```

`src/client.ts` imports nothing from the CLI, so it runs standalone:

```bash
$ node --input-type=module -e '
const { askJev, loadSettings } = await import("./src/client.ts");
const { apiKey } = loadSettings();
console.log(await askJev({ state: "app crashed on start", questions: {
  crash: { type: "noul", instructions: "Does the state describe a crash?" } }, apiKey }));
'
{
  model: 'jev-1.13.0',
  answers: { crash: { type: 'noul', noul: 0.98 } },
  usage: { input_tokens: 277, output_tokens: 21 }
}
```
