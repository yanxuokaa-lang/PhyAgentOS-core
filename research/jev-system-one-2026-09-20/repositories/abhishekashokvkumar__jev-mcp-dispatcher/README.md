# jev-mcp-dispatcher

**Zero general-purpose LLM calls — anywhere in this pipeline, not for
picking the tool, not for reading a parameter's value out of a sentence, not
for anything.** This is a proof of concept for a different way to do MCP
tool dispatch: given a **simple** MCP (Model Context Protocol) server — one
whose tools take primitive-typed parameters — this script dynamically
discovers its tool signatures at runtime and uses
[Jev](https://docs.typesafe.ai) — [TypeSafe](https://typesafe.ai)'s System One
reasoning model — to route a plain natural-language command to the correct
tool and extract its arguments straight out of the sentence, using only
Jev's typed primitives (`Choice` / `Noul`) instead of free-text generation.
The dispatcher logic never hardcodes a specific tool name, parameter name,
or parameter count. It is *not* a claim that this works against an
arbitrary MCP server unconditionally — see
[Scope and caveats](#scope-and-caveats) for exactly what the input text and
the tool registry need to look like.

> Every decision — which tool to call, which words belong to which
> argument, how many independent actions a command describes, whether a
> number is spelled out in words — is made by asking Jev one typed question
> and reading back a probability, never by asking a model to generate text.

```
"Play Blinding Lights by The Weeknd on the speaker"
        │
        ▼
  discover tools from the MCP server (list_tools())
        │
        ▼
  Jev picks the tool: play_song  (confidence 1.00)
        │
        ▼
  for each parameter Jev declared:
    title  (string) -> "Blinding Lights"
    artist (string) -> "The Weeknd"
    device (enum)   -> "speaker"
        │
        ▼
  play_song(title="Blinding Lights", artist="The Weeknd", device="speaker")
        │
        ▼
  "Playing 'Blinding Lights' by 'The Weeknd' on the speaker."
```

## Why this is interesting

Traditional function-calling asks one model to both pick a tool *and*
free-form-generate its arguments as text, then hopes the JSON parses and the
types line up. This does the same job with Jev's typed primitives instead,
which keeps every step inspectable and cheap:

1. **Tool selection is a `Choice`, not free text.** Jev is given the
   command plus every tool's name and description as fixed options and
   returns a full probability distribution over them — not just a guess,
   but a confidence-scored ranking.
2. **Enum-typed parameters are also a `Choice`.** If a parameter's JSON
   schema declares an `enum` (e.g. a Python `Literal["speaker", "headphones",
   "tv"]` type hint), the value has to be one of a fixed set, so it's
   selection, not extraction.
3. **Everything else is highlighted, not generated.** For a non-enum
   parameter, Jev is asked one `Noul` (yes/no probability) question *per word*
   in the command — "does this word belong to this parameter's value?" —
   all sent as a single parallel request. The words that come back "yes"
   form the value. **That value is always the exact substring copied out of
   `command` — never a new, paraphrased, or normalized string.** This is
   what lets the same code path handle a one-word value (`volume=67`) and a
   multi-word value (`artist="The Weeknd"`) with no special-casing, and it
   guarantees the model can't invent, misspell, or hallucinate a value — it
   can only point at text that's actually there.
4. **Type conversion is classic Python**, not the model's problem: the
   highlighted text is converted with `int()` / `float()` / `str()` / a
   boolean-keyword check, chosen by the parameter's declared JSON-schema
   type.
5. **A number spelled out in words is judged, not regex-guessed.** A digit
   converter has no way to know "sixty seven" means 67 — there's nothing to
   regex-match. So Pass 1 also asks a `Noul`: does this command write any
   number out in words rather than digits? Only when the answer is yes does
   a classic (non-LLM), deterministic pre-processing step rewrite the whole
   command's word-numbers as digits, once, before anything else runs — so
   word-highlighting and type conversion never have to special-case words vs.
   digits. Jev decides *whether* normalization is needed; it never does the
   normalization itself.
6. **A compound command ("set the volume to 50 and play some jazz") is
   detected and split, at no extra cost in the common case.** Pass 1 also
   asks a `Choice` from 1 to 5: how many independent actions does this
   command actually describe? That question — and a speculative function
   pick for the whole text — ride along in the *same* batched request as
   everything else in Pass 1. When the count is 1 (the common case), the
   speculative pick is simply used, so a single-intent command costs exactly
   the same number of round trips as it always did. Only when the count is
   greater than 1 does the dispatcher pay for more: one extra batched
   request (one `Choice` per word, assigning it to sub-command 1..N or
   "none" for connective filler like "and"/"also") splits the command into
   N independent spans of real text, each of which is then run back through
   the entire single-command pipeline on its own.

## Scope and caveats

This is not "works with any MCP server, unconditionally." It works with a
**simple** MCP server, on input text in a fairly specific shape, without any
general-purpose LLM call — but only when the following hold:

**Input format**
- **Up to 5 independent actions per command.** A compound sentence like
  "set the volume to 50 and play some jazz" is detected and split into
  separate dispatches (see point 6 above) — but the count is capped at 5,
  and each sub-command still has to satisfy every other criterion on this
  list on its own (one clear intent, values present in its own words, etc).
- **Sub-command splitting can be imperfect.** The words assigned to a given
  sub-command aren't guaranteed to be perfectly contiguous or complete —
  filler words in between can break up a span, and trailing words are
  occasionally dropped. This is usually harmless for a zero-parameter
  action, but could matter for a sub-command whose parameters need to be
  extracted from the exact words it was split off with.
- **Parameter values need to actually appear in the text.** Non-enum
  parameters are resolved by highlighting real words in the command, not by
  computing or inferring a value — "turn it up a bit" has no literal number
  in it, so there's nothing for word-highlighting to point at. Enum
  parameters are the exception: their value only has to be *implied*
  strongly enough for `Choice` to pick the right option (e.g. "dark mode" ->
  `mode="dark"`).
- **A string parameter's value is the exact substring extracted from the
  command — never a new, generated, or paraphrased string.** If the "right"
  value requires rewriting what the user typed (normalizing casing, fixing
  a typo, resolving a pronoun), that's out of scope.
- **Word-form number normalization covers standard English number words**
  (via `text2num`'s rule-based parser). Idiomatic or derived quantities
  ("half an hour", "a dozen", "a couple") don't resolve to a number, and
  non-English input isn't covered.

**Tool registry**
- **Only primitive parameter types are supported**: string, integer,
  number, boolean, and enum (`Literal[...]`). A parameter typed as a nested
  JSON object or an array is out of scope — there's no primitive here for
  Jev to structurally decompose one from a sentence.
- **Tools need distinguishable names/descriptions.** Function selection is
  only as good as the semantic gap between tools — a registry with several
  near-duplicate tools will lower Pass 1's confidence.

**Known gaps in the current implementation** (not fundamental limits of the
approach, just not built yet):
- **No cross-parameter bookkeeping.** Each parameter's word-highlighting
  pass runs independently over the whole command; nothing prevents two
  parameters of the same type from both claiming the same word (e.g. two
  integer parameters in one sentence, like source/destination slot numbers).
- **No confidence gating.** Every `Choice`/`Noul` result is used as-is,
  however low its confidence — there's no threshold below which the
  dispatcher asks for clarification instead of guessing.
- **JSON Schema's `required`/optional/default isn't respected.** The
  parameter loop tries to extract every property a tool declares; an
  optional parameter the command doesn't mention still gets a forced
  (likely wrong) extraction attempt rather than being skipped or defaulted.
- **Boolean conversion never raises.** Unlike the numeric converters (which
  raise if no digits are found), a boolean parameter silently defaults to
  `False` whenever none of a fixed set of truthy keywords appear in the
  highlighted span — masking a failed extraction as a legitimate value.
- This is a proof of concept generally: no argument-schema validation
  beyond type conversion (e.g. no min/max bounds-checking), no retry logic,
  no multi-turn clarification.

## How it works

`jev_mcp_dispatcher.py` is the generic piece. It never imports or mentions a
specific tool:

1. Connects to an MCP server over stdio once and calls `list_tools()` to
   fetch every tool's name, description, and JSON-schema parameters — live,
   at startup. That one session and tool list are then reused for every
   command that follows, rather than reconnecting per command.
2. **Pass 1 — three independent questions, one batched request.** A `Choice`
   over every tool's name/description (a speculative pick for the whole
   command), a `Noul` asking whether the command writes any number out in
   words (e.g. "sixty seven") instead of digits, and a `Choice` from 1 to 5
   asking how many independent actions the command describes.
3. If the word-numbers check came back true, the command text is normalized
   once — word-numbers rewritten as digits — using a classic, deterministic,
   rule-based parser (the `text2num` package's `alpha2digit`), *not* another
   model call. Everything from here on operates on the normalized text.
4. **If the count from Pass 1 is 1** (the common case), the speculative
   function pick from Pass 1 is used directly — no extra request. **If it's
   greater than 1**, that pick is discarded and one more batched request (one
   `Choice` per word, assigning it to sub-command 1..N or "none" for
   connective filler like "and"/"also") splits the command into N
   independent spans of real text. Each span is then run back through
   function selection and dispatch on its own, as if it were its own
   command — including its own actual MCP tool invocation.
5. For the resolved tool + command text (whether that's the original command
   or one split-off piece): if the tool takes zero parameters, invoke it
   immediately. Otherwise, **for each declared parameter, in schema order**
   (any number of them):
   - If the parameter's schema has an `enum`, resolve it with a `Choice`
     over the enum options.
   - Otherwise, resolve it by asking one `Noul` question per word in the
     command (all parallel, one request), grouping the words that scored
     above threshold into contiguous runs, and keeping the strongest run as
     the parameter's raw text.
   - Convert the raw text to the parameter's declared type with a plain
     digit regex + `int()`/`float()`/`str()`/a boolean check — safe because
     any word-form numbers were already normalized in step 3.
6. Invoke the tool with the assembled, type-converted arguments via the MCP
   session.

Every step above — the exact state and instructions sent to Jev, the raw
probabilities that came back, the decision made from them, each type
conversion, and the final dispatch and result — is printed live to the
console by a `Tracer` as it happens, so the whole reasoning chain is visible
directly in the command's output.

`example_mcp_server.py` is **not** part of the core logic — it's a demo
server standing in for whatever MCP server you point the dispatcher at. It's
a small song-player tool registry chosen to exercise every parameter shape
the dispatcher handles:

| Tool | Parameters | Shape demonstrated |
| --- | --- | --- |
| `play`, `pause`, `skip` | none | zero-parameter dispatch |
| `set_volume(volume)` | one `integer` | single-word extraction |
| `search(query)` | one `string` | multi-word extraction |
| `set_repeat_mode(mode)` | one `enum` | enum selection |
| `set_sleep_timer(duration, unit)` | `integer` + `enum` | two parameters, mixed kinds |
| `play_song(title, artist, device)` | `string` + `string` + `enum` | three parameters, two independent multi-word spans in one sentence |

## Using it against your own MCP server

The dispatcher doesn't know `example_mcp_server.py` exists except as a
default. Point `MCP_SERVER_COMMAND` at any other MCP server's stdio launch
command and it routes against that server's tools instead — no code changes:

```bash
MCP_SERVER_COMMAND="python my_other_server.py" python jev_mcp_dispatcher.py "your command here"
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.sample .env
# then edit .env and set TYPESAFE_API_KEY to a real key from
# https://console.typesafe.ai/
```

## Running

```bash
# interactive mode: probe the server, then try your own commands
python jev_mcp_dispatcher.py

# scripted mode: run exactly the given commands and exit (no prompt)
python jev_mcp_dispatcher.py "Set the volume to 40 percent" "Skip this song"
```

With no arguments, the program:

1. Connects to the MCP server and prints one line per discovered tool —
   its signature (e.g. `set_volume(int volume)`) and a one-sentence
   description — straight from `list_tools()`.
2. Prints one suggested example invocation (not run — just shown, so
   nothing executes before you've typed something yourself).
3. Drops you straight into a prompt (`>`) where you type any
   natural-language command against the same tool registry. Type `quit` or
   `exit` (or Ctrl-D) to stop.

A handful of other example commands are kept as comments near
`EXAMPLE_COMMAND` in `jev_mcp_dispatcher.py`, for reference/copy-paste —
none of them run automatically.

Every step is printed live and color-coded so the two kinds of activity are
visually distinct in a terminal: **cyan** for Jev's reasoning (every
question asked and answer received — pure judgment, nothing has executed
yet) and **green** for what actually runs against the MCP server (the
discovered signatures, the final tool invocation, and its result). A
compound command that gets split (e.g. "set the volume to 50 and play some
jazz") prints each sub-command's own header in **magenta**, so it's clear
where one independent dispatch ends and the next begins. Colors are skipped
automatically when output isn't a terminal (e.g. piped to a file), or if
`NO_COLOR` is set.

## Files

| File | Role |
| --- | --- |
| `jev_mcp_dispatcher.py` | The generic dispatcher: tool selection, parameter extraction, type conversion, color-coded tracing, and the interactive CLI. |
| `example_mcp_server.py` | Demo MCP server (song player) used to exercise the dispatcher. |
| `requirements.txt` | Pinned dependencies. |
| `.env.sample` | Template for the `.env` file the dispatcher loads via `python-dotenv`. Copy to `.env` and fill in your key — `.env` itself is gitignored. |
