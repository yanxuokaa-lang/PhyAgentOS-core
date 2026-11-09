# jev-voice-agent

**Flux STT → Jev → Flux TTS.** A voice agent with no language model in the loop.

There is no model writing text here. Every line the agent can ever say is
already in [`src/script.ts`](src/script.ts), written by a human. The only thing
the model does is *choose*: given what the caller just said, it picks one label
out of a fixed set, and reports how sure it is. That is the whole trick, and it
is why the loop is short. A decision does not have to be generated token by
token, so the reply does not wait on generation, and the agent cannot say
anything you have not already read and approved. What you give up is everything
open-ended, which is a real cost, and the
[When to stop using this](#when-to-stop-using-this) section says where that line
falls.

The pipeline is three services, each owning exactly one decision:

- **[Deepgram Flux](https://developers.deepgram.com)** (`/v2/listen`) owns *the
  turn*. It streams the transcript and decides when the caller has stopped
  talking.
- **[TypeSafe Jev](https://typesafe.ai)** owns *the branch*. It takes text or JSON
  plus a set of questions with fixed options, and returns a chosen option with
  probabilities. It has three primitives: `choice` (pick a label), `score` (rate
  against a rubric), `noul` (probability of yes).
- **[Deepgram Flux TTS](https://developers.deepgram.com)** (`/v2/speak`) owns
  *the voice*. It speaks the pre-written line, and its `Interrupt` message owns
  barge-in: give it a playback offset and it tells you which words the caller
  actually heard.

Flux has to own the turn because **Jev structurally cannot do endpointing**: it
never sees audio. That is not a workaround, it is the shape of the problem.

---

## Quickstart

### Offline, no API keys, about a minute

```sh
git clone https://github.com/dg-coreylweathers/jev-voice-agent.git
cd jev-voice-agent
npm install
npm run demo:offline
```

That replays five recorded conversations through the real turn loop, the real
gate and the real question builder. No network, no keys. It takes about 63
seconds because it replays at conversational pace, which is the only speed at
which barge-in and the speculative-judgment window mean anything. One scenario
instead of all five:

```sh
FIXTURES=1 node src/cli.ts clean-route     # about 13 seconds
FIXTURES=1 node src/cli.ts misheard-no
FIXTURES=1 node src/cli.ts wants-a-human
FIXTURES=1 node src/cli.ts jev-timeout
FIXTURES=1 node src/cli.ts barge-in
```

Human-readable output goes to **stderr**, one JSON object per turn goes to
**stdout**, so this gives you a clean machine-readable log and still shows you
the conversation:

```sh
npm run demo:offline > turns.jsonl
```

Tests, also offline:

```sh
npm test        # 55 tests, about 9 seconds
npm run typecheck
```

### With real keys

```sh
cp sample.env .env      # add DEEPGRAM_API_KEY and TYPESAFE_API_KEY
npm run demo -- --audio path/to/call.wav
```

`--audio` takes a mono `linear16` wav at `FLUX_SAMPLE_RATE` (16 kHz by default)
and streams it to Flux at roughly real time. Microphone capture is deliberately
out of scope: it needs a native dependency, and it is one function to replace
([`createFluxStt`](src/stt/flux.ts) is the only thing that produces turn events).

**Read [Honest caveats](#honest-caveats) before you trust the live path.** It is
code-complete and type-checked against both SDKs, and it has never been run.

#### Two Jev transports

Both are behind one small interface, selected by `JEV_TRANSPORT`:

| `JEV_TRANSPORT` | Endpoint | Key | Status |
|---|---|---|---|
| `direct` (default) | `https://api.typesafe.ai` | `TYPESAFE_API_KEY` | Waitlisted. Request shape verified against the SDK types. |
| `gateway` | Vercel AI Gateway, model `typesafe-ai/jev` | `AI_GATEWAY_API_KEY` | No waitlist. **Endpoint shape unverified**, see below. |

The `gateway` route exists because it needs no waitlist, and it is the one thing
in this repo that could not be checked. It refuses to send a request until you
set `JEV_GATEWAY_CONFIRMED=1`, and it prints the exact questions to answer
first. See the `TODO(verify)` at the top of
[`src/judge/typesafe.ts`](src/judge/typesafe.ts).

---

## Architecture

```
  caller audio
       │
       ▼
┌──────────────────────┐
│  Flux  /v2/listen    │  OWNS THE TURN
│  flux-general-en     │  StartOfTurn · Update · EagerEndOfTurn
│                      │  TurnResumed · EndOfTurn
└──────────┬───────────┘  + per-word confidence
           │
           │  transcript + words[].confidence + end_of_turn_confidence
           ▼
┌──────────────────────┐
│  src/questions.ts    │  ONE Jev call per turn, FOUR questions batched:
│                      │    branch      choice  → which option
│                      │    answered    noul    → did they answer at all
│                      │    escalating  noul    → do they want a human
│                      │    clarity     score   → was it ever branchable
└──────────┬───────────┘  (the four cannot see each other's answers)
           │
           ▼
┌──────────────────────┐
│  Jev  /v1/systemone  │  OWNS THE BRANCH
│                      │  returns a label + confidence + probabilities
└──────────┬───────────┘  writes nothing
           │
           ▼
┌──────────────────────┐
│  src/decide.ts       │  THE GATE (pure, no I/O)
│                      │  escalation ▸ reprompt budget ▸ confidence gates ▸ branch
└──────────┬───────────┘  on failure: fall back to the clarify line
           │
           │  a line, verbatim, from src/script.ts
           ▼
┌──────────────────────┐
│  Flux TTS /v2/speak  │  OWNS THE VOICE
│  flux-alexis-en      │  Speak ▸ Flush (ends the turn)
│                      │  Interrupt(playback_offset) ▸ SpeechInterrupted
└──────────┬───────────┘  → text_spoken / text_remaining
           │
           ▼
     audio to caller
```

Two things cross those boundaries and are worth calling out.

**Speculation.** Setting `eager_eot_threshold` makes Flux emit
`EagerEndOfTurn` when it has moderate confidence the caller has finished. The
turn loop starts the Jev call *then*, so when the guess holds, most of the round
trip is already paid for by the time `EndOfTurn` arrives. When the guess does not
hold, Flux sends `TurnResumed` and the call is cancelled. The reuse rule is
strict: the in-flight judgment is only used if the transcript did not change,
because a judgment made on half a sentence is exactly the silent correctness bug
that makes speculation not worth having.

**Cancellation.** Jev has no streaming, so there is nothing to interrupt and
nothing partial to keep. Cancellation is the only correct response to the caller
speaking again, and it happens in two places: `TurnResumed` kills a speculative
judgment, and `StartOfTurn` kills both any in-flight judgment and the agent's own
turn. On Flux TTS that is an `Interrupt` carrying a playback offset, and the
server answers with `SpeechInterrupted`, which splits the turn's text into
`text_spoken` and `text_remaining`. That split is worth more in a no-LLM pipeline
than in a generating one: every line is pre-written, so knowing exactly which
words landed is the difference between "they ignored the question" and "they
never heard it".

---

## The one file you'll edit

[**`src/script.ts`**](src/script.ts). It is the whole agent.

```ts
greet: {
  say: "Service desk. What can I help you with?",
  expects: "the kind of computer problem the caller is having",
  clarify: "Sorry, I didn't catch that. Signing in, the network, or a broken device?",
  options: {
    access: {
      when: "The caller cannot sign in, is locked out, forgot a password, or needs a multi-factor code reset.",
      to: "access_scope",
    },
    network: { when: "...", to: "network_scope" },
    // ...
  },
},
```

- `say` is spoken verbatim. If it is not written here, the agent cannot say it.
- The **keys** of `options` are the labels Jev returns. The `when` text is the
  description Jev reads to choose. The script tree *is* the label set, which is
  what makes the branching semantic rather than keyword matching. There is no NLU
  layer to train and no prompt to tune.
- `clarify` is what the agent says when the judgment is not confident enough to
  act on. Every node that asks a question needs one.
- `expects` describes the *answer* you want, and becomes the "did they actually
  answer?" question.

Adding a branch is: add a key to `options`, add the node it points at. Nothing
else. `validateScript` runs at startup and refuses to start on a dangling
target, a single-option "decision", a question node with no clarify line, a
non-terminal dead end or an unreachable node.

The example domain is a generic internal IT service desk that triages and routes.
Swap it.

---

## The transcript problem

This is the honest weak point of a no-LLM pipeline, and it deserves more than a
footnote.

With a generating model in the loop, a mis-heard word often washes out: the model
has the rest of the sentence, the conversation history and a lot of prior, and it
tends to recover. Here there is nothing downstream to recover. The transcript is
the input to the decision, so **STT error is decision error, directly**. The
canonical case is one syllable:

> Agent: "Are you locked out completely, or can you still get in somewhere?"
> Caller: "No, nothing works."
> Flux: `"know nothing works"`

`know` instead of `no` inverts the answer. Run `FIXTURES=1 node src/cli.ts
misheard-no` to watch it happen.

### What this repo actually does about it

Three things, none of which is a fix:

1. **Per-word confidence feeds the gate.** Flux returns
   `words[].confidence`. Any word below `GATE_MIN_WORD_CONFIDENCE` (0.6) marks
   the transcript *suspect* and raises the branch-confidence bar by
   `GATE_SUSPECT_PENALTY` (0.1), from 0.65 to 0.75. In the scenario above, the
   judgment comes back at 0.70: enough to pass normally, not enough on a suspect
   transcript. So it clarifies instead of branching.
2. **The evidence goes to Jev, not just the transcript.** The request `state` is
   JSON, not a sentence, and it carries `low_confidence_words` alongside
   `caller_said`, plus what the agent asked and how many times it has already
   re-asked. The judgment is at least made *in view of* the doubt.
3. **The clarify line is the recovery path.** The second ask is a different
   question ("can you sign in anywhere at all right now?") and gets a longer,
   unambiguous answer.

### What it does not do, and you should not pretend otherwise

- Confidence gating catches the case where the STT *knew* it was unsure. It does
  nothing for a confident mis-hear, which is the dangerous one.
- Raising the bar trades wrong branches for extra turns. That is a real cost: a
  caller who gets re-asked twice on a clean utterance has a worse call than one
  who gets routed slightly wrong. There is no setting that avoids both, only a
  choice about which failure you would rather have. `GATE_MIN_BRANCH_CONFIDENCE`
  and `GATE_SUSPECT_PENALTY` are where you make it, and the only honest way to
  set them is to replay real calls and count both failures.
- The one genuinely effective mitigation is not in the gate at all: it is
  `keyterm` on the Flux connection, which boosts recognition of the vocabulary
  your script actually branches on, plus writing script options that do not hinge
  on a single short word. "Are you locked out completely, or can you still get in
  somewhere?" is a better question than "Are you locked out?" precisely because a
  one-syllable answer cannot carry the whole decision.

---

## When to stop using this

Naming the ceiling is the point of this section. A decisions-only agent is the
right tool when the space of things the caller can usefully be told is finite and
known. Put a generating model back in the loop when any of these is true:

- **The reply depends on data you cannot enumerate.** "What's my balance?", "when
  does my warranty run out?", "read me the last note on my ticket." Jev can
  decide *that* the caller asked for their balance; it cannot say the number. You
  need either a template with slots (which is still this architecture, plus a
  lookup) or a model that can compose the sentence.
- **The caller needs to be taught something.** Troubleshooting that adapts, "why
  did that happen?", anything where a good answer is an explanation rather than a
  routing decision. A fixed line cannot explain a situation it did not
  anticipate.
- **The branch count is exploding.** If you are adding options to keep up with
  what callers actually say, and each one is a near-duplicate of another, the tree
  is modelling language instead of modelling your process. Somewhere past a few
  dozen options per node you are hand-building a classifier badly.
- **You need multi-turn state that is not a path through the tree.** Collecting
  five fields in any order, correcting an earlier answer, "actually, go back". A
  tree can encode some of this and it gets ugly fast.
- **The caller is upset and needs to be acknowledged specifically.** A
  pre-written empathy line that does not match what they said is worse than
  nothing. This repo's answer is to route to a human, which is honest but is not
  the same as handling it.

The realistic architecture for a production line is not a choice between the two.
It is this tree for the parts that are genuinely decisions (triage, routing,
confirmation, disambiguation, anything that ends in a handoff) with a generating
model behind specific nodes for the open-ended turns. The tree gives you the
guarantee that the agent cannot say something it should not; the model gives you
the turns that need composing. Keeping the boundary explicit, as a node in the
script rather than a prompt instruction, is what keeps the guarantee meaningful.

---

## Measured latency

**These are fixture-mode numbers.** They are real measurements of this repo's
plumbing, and they tell you nothing about the speed of Flux STT, Jev or Flux
TTS:

- `jev_ms` is an abortable sleep from `fixtures/judgments.json` plus loop
  overhead. It is not a Jev round trip.
- `tts_ttfb_ms` is local wav encoding. It is not Flux TTS.
- `eot_ms` is the fixture's own replay gap. It is not Flux STT's end-of-turn
  latency.

What they do show is that the loop itself costs essentially nothing, that
speculation works, and that the degradation path behaves. Live numbers need keys.

One full offline run, all five scenarios, 11 turns, Node 22.22.2. A single run,
not an average, so expect a few milliseconds of movement between runs:

| metric | n | p50 | p95 | max |
|---|---|---|---|---|
| `eot_ms` | 11 | 281 | 381 | 381 |
| `judge_ms` | 11 | 191 | 1202 | 1202 |
| `judge_wait_ms` | 11 | 186 | 1202 | 1202 |
| `tts_ttfb_ms` | 11 | 2 | 5 | 5 |
| `total_ms` | 11 | 187 | 1205 | 1205 |

`turns 11 · gated 2 · speculative hits 1 · judgment time discarded 261ms`

The p95 of 1202ms is the deliberate `jev-timeout` scenario hitting
`JEV_TIMEOUT_MS`, not a tail. The interesting pair is inside `clean-route`:

```
turn  1  greet           eot 241ms  jev 181ms  wait 181ms  ttfb 2ms  total 184ms  spec:miss  advance/branch
turn  2  hardware_scope  eot 191ms  jev 191ms  wait   0ms  ttfb 5ms  total   6ms  spec:hit   advance/branch
```

Same judgment cost on both turns. On turn 2 the caller waited **6ms** instead of
184ms, because `EagerEndOfTurn` let the call start before the turn ended.

`barge-in` is the other one worth looking at, because the interrupt reporting is
new in Flux TTS and the offline sink mirrors it:

```
turn  1  barge-in after 900ms of audio; caller never heard: "use it at all, or is it completely dead?"
```

The matching JSONL line carries the split, so you can tell after the fact exactly
what the caller was answering:

```json
{"evt":"utterance","scenario":"barge-in","turn":1,"interrupted":true,
 "audio_duration_ms":900,"billable_characters":54,"speech_id":"dg_sp_faa79e409114",
 "text_spoken":"Can you still","text_remaining":"use it at all, or is it completely dead?"}
```

### What the columns mean, precisely

| column | definition |
|---|---|
| `eot_ms` | Wall clock from the turn's last speech-bearing event to `EndOfTurn`. How long after the caller stopped producing new words Flux took to commit. Measured on our clock, on arrival. |
| `judge_ms` | Full duration of the Jev call, start to finish, whenever it started. Compare this against Jev's own timings. |
| `judge_wait_ms` | How long the loop actually waited after `EndOfTurn`. Near zero on a speculative hit. |
| `tts_ttfb_ms` | From handing the line to TTS to the first audio byte back. |
| `total_ms` | `EndOfTurn` observed to first audio byte out. **The number the caller experiences.** |

---

## Graceful degradation

Jev is a network call in the middle of a voice turn, so it will sometimes not
answer in time. The default here: **fall back to the node's clarify line.**

A default branch would silently route someone to the wrong place and they would
find out minutes later. A clarify costs one turn and keeps the caller in a state
we understand. The re-prompt budget (`GATE_MAX_REPROMPTS`, 2) still applies, so
repeated failures escalate to a human rather than looping forever.

| condition | behaviour |
|---|---|
| Timeout, connection error, 5xx | clarify, reason `judge_unavailable` |
| 429 | clarify, reason `judge_rate_limited` (reported separately so you can see it in the log) |
| Aborted (barge-in) | not a failure. The turn is dropped, nothing is spoken. |
| Any failure, budget exhausted | escalate to a human |

Two notes on retries. The TypeSafe SDK retries 408, 429 and 5xx by default with
exponential backoff and honours `Retry-After`; this repo caps `maxRetries` at 1,
because a retry inside a voice turn usually blows the latency budget that made
the retry worth attempting. And on the Deepgram side, a 429 means too many
*concurrent connections*, not too high a request rate, so retrying immediately
does not help there either.

`JEV_TIMEOUT_MS` defaults to **1200ms**, not the SDK's 10000ms. Ten seconds of
silence on a phone call is a hangup.

---

## Honest caveats

**What has been exercised.** The offline path, completely: 55 tests and five
replayed scenarios covering script traversal, every confidence gate, the
re-prompt budget, question batching, speculative hit and both kinds of
speculative discard, judgment cancellation, turn interruption including the
`text_spoken` / `text_remaining` split, the session-cumulative playback offset,
and every degradation branch. `npm run typecheck` is clean under `strict`,
`exactOptionalPropertyTypes` and `noUncheckedIndexedAccess`. The question batch is
additionally sent through a real `TypeSafeClient` with a stubbed `fetch`, so the
SDK's own request validation is asserted rather than assumed.

**What has not.** Any call to a real API. No Deepgram or TypeSafe key was
available, `api.deepgram.com` and `api.typesafe.ai` were unreachable, and so was
`ai-gateway.vercel.sh`. Concretely, this means:

- [`src/stt/flux.ts`](src/stt/flux.ts) and [`src/tts/flux.ts`](src/tts/flux.ts)
  are written against `@deepgram/sdk` 5.11.0's bundled type declarations and the
  published message contract. They have never opened a socket.
- [`src/judge/typesafe.ts`](src/judge/typesafe.ts) is written against
  `@typesafe-ai/sdk` 0.6.0's type declarations. It has never reached
  `api.typesafe.ai`.
- The fixtures in `fixtures/` are **hand-authored in the recorded shape**, not
  recordings. Field names, the event vocabulary, the `trigger` values and the
  answer shapes come from the SDK types. The timings are plausible, not measured.
  Both fixture files say so in a `_note`.
- The **Vercel AI Gateway** route for Jev is unverified end to end. See the
  `TODO(verify)`.

**Five `TODO(verify)` markers**, each with the exact question:

| where | question |
|---|---|
| [`src/judge/typesafe.ts`](src/judge/typesafe.ts) | Does the Vercel AI Gateway expose Jev's native `POST /v1/systemone`, at what base URL, with what auth header? The Gateway's documented surface is OpenAI-compatible `chat/completions`, and its catalogue types every model as language / embedding / reranking / image / video, none of which describes something that returns `probabilities`. `GET https://ai-gateway.vercel.sh/v1/models` needs no key and settles it. |
| [`src/stt/flux.ts`](src/stt/flux.ts) | On what timeline does `eot_timeout_ms` count? "After speech" could be the received-audio timeline or server wall clock, and the two diverge under any non-real-time sender, including the file streamer here. |
| [`src/stt/flux.ts`](src/stt/flux.ts) | What are the server-side defaults for `eot_threshold`, `eot_timeout_ms` and `eager_eot_threshold` when omitted? The SDK types all three as `unknown` and the generated reference lists no default, unlike neighbouring parameters. This repo sets all three explicitly, so anyone copying a subset needs to know. |
| [`src/tts/flux.ts`](src/tts/flux.ts) | What is the full Flux TTS voice catalogue? `SpeakV2Model` is typed as a bare `string` with no enum, unlike `SpeakV1Model` which enumerates all 100-odd Aura voices. The only Flux voice name anywhere in the SDK is `flux-alexis-en`, which appears as the example in that type's own doc comment, and is what this repo defaults to. A reader cannot get the list from the SDK. |
| [`src/tts/flux.ts`](src/tts/flux.ts) | What is the accepted `speed` range on Flux TTS? `SpeakV2Speed`'s doc comment says 0.5 to 1.5 in 0.05 increments, but the deprecated named constants retained on the same type from SDK 5.10.0 only cover 0.85 to 1.15, and the generated API reference also lists 0.85 to 1.15. A value between the two is either fine or a `SPEED_OUT_OF_RANGE`. This repo leaves `speed` at 1.0, where both agree. |

**Pin the SDKs exactly.** `package.json` uses exact versions on purpose.
`@typesafe-ai/sdk` is `0.x`, and `0.6.0` was a breaking release: `score` criteria
used to accept an object map keyed by score or a one-entry array, and now require
an array of **at least two** entries. The `ScoreMap` and `ScoreList` types were
removed. Upgrading a caret range across that boundary breaks
[`src/questions.ts`](src/questions.ts) at runtime, and the SDK validates
synchronously, so it throws rather than rejecting. `test/questions.test.ts` has a
regression guard.

**No third-party performance claims.** TypeSafe publishes speed, cost and
accuracy figures for Jev that are self-scored, so none of them are quoted here.
The only numbers in this README are the fixture measurements above, which measure
this repo. If you need to know how fast Jev is, measure it on your own traffic
with `judge_ms`, which exists for that.

**Moving from Aura to Flux TTS: five things that change, two that do not.**

Worth reading before you port anything, because two of the changes are silent
rather than loud. All of it is from the SDK's type declarations.

Changes:

1. **`Flush` ends the turn.** It is not a v1-style buffer flush and there is no
   separate `Finalize`. Audio starts streaming before you flush, so there is
   nothing to gain by holding it back.
2. **The end-of-turn signal is `SpeechMetadata`, not `Flushed`.** `Flushed` only
   acknowledges the message. `SpeechMetadata` arrives when all of the turn's
   audio has been sent and carries `audio_duration_ms`,
   `input_character_count` and `billable_character_count`, so you can drop
   client-side character tracking.
3. **Barge-in is `Interrupt`, not `Clear`, and it takes a `playback_offset`.**
   Send one: without it the server cannot split the turn's text, so
   `SpeechInterrupted` comes back with no `text_spoken` / `text_remaining`. Two
   traps in the offset: it is cumulative **from the start of the session**, not
   the turn, and each `Interrupt` must advance past the last one or the server
   ignores it with an `INVALID_INTERRUPT_OFFSET` warning. A barge-in that is
   silently a no-op is the worst failure mode there is, so
   [`src/tts/flux.ts`](src/tts/flux.ts) tracks the running offset and clamps it
   to advance.
4. **`speech_id` is minted by the server** and arrives on `SpeechStarted`. Never
   send one.
5. **`model` is required and must be `flux-{voice}-{language}`.** There is no
   default, unlike `/v1/speak` which defaults to `aura-asteria-en`, and an
   `aura-*` string is rejected outright. The two families never mix.

Plus one that will not bite this repo and will bite yours: successive `Speak`
messages are concatenated **verbatim**. The server will not insert whitespace, so
`"Hello world."` then `"How are you?"` synthesises as `"Hello world.How are
you?"`. One pre-written line per turn never hits it; stitching two script lines
together does.

Does not change:

1. `sample_rate` on the **websocket** is still a **string** union
   (`"8000" | "16000" | "24000" | "32000" | "44100" | "48000"`), while
   `sample_rate` on the REST `SpeakV2Request` is still a plain **number**. This
   is the same asymmetry `/v1/speak` has, and moving to v2 does **not** fix it.
   It fails the typecheck, which is the good outcome; it would be a silent 400 in
   JavaScript.
2. The typed `socket.on("message")` handler still runs `JSON.parse` on every
   frame unconditionally. `V2Socket`'s `handleMessage` is byte-for-byte the same
   bare `fromJson(event.data)` as `V1Socket`'s, and Flux TTS audio still arrives
   as binary frames, so routing audio through it still throws a `SyntaxError` per
   frame. Attach to the underlying
   `socket.socket.addEventListener("message", ...)` for audio and keep the typed
   handler for the JSON control messages.
   [`src/tts/flux.ts`](src/tts/flux.ts) uses both and says why.

---

## Layout

```
src/script.ts        the declarative tree, the one file you'll edit
src/questions.ts     one batch of four independent Jev questions per turn
src/decide.ts        the gate and the degradation policy (pure, no I/O)
src/agent.ts         the turn loop: speculation, cancellation, the clock
src/config.ts        every knob, env-overridable
src/metrics.ts       per-turn instrumentation, stderr + JSONL on stdout
src/cli.ts           entry point
src/judge/typesafe.ts  live Jev: direct and gateway transports
src/judge/fixture.ts   offline Jev: replay, abortable, can fail on demand
src/stt/flux.ts        live Flux over /v2/listen
src/stt/fixture.ts     offline Flux: replays recorded TurnInfo events
src/tts/flux.ts        live Flux TTS over /v2/speak
src/tts/fixture.ts     offline Flux TTS: writes wav, "plays" for the real duration,
                       mirrors the v2 turn lifecycle including the interrupt split
fixtures/              five scenarios and their judgments
test/                  node:test, offline, no mocking framework
```

Node **>= 22.18** and TypeScript, ESM, no build step, no agent framework. Two
runtime dependencies, both of them the SDKs this repo is about. Node 22.18 is
required rather than 20 because native TypeScript execution is what lets the repo
have no build step and no dev-dependency test runner: `node src/cli.ts` and
`node --test test/*.test.ts` run the TypeScript directly. On Node 20 you would add
a TS runner and nothing else changes.

### Starter-repo conventions

This repo follows the layout Deepgram's published starters use, so it drops into
that estate without reshaping: `LICENSE` (MIT), `README.md`, `sample.env` rather
than `.env.example`, `deepgram.toml` with `[meta]` / `[check]` / `[install]` /
`[start]` / `[test]` / `[clean]` blocks, a framework-agnostic `Makefile`, and
`AGENTS.md` with a `CLAUDE.md` pointing at it.

One deliberate deviation: the starter convention is
`deepgram-starters/{framework}-{feature}`, which would make this
`node-no-llm-voice-agent`. It is called **`jev-voice-agent`** instead, for
searchability, and because its first home is a personal account rather than the
`deepgram-starters` org. If it later moves there, the rename is the repo name and
`package.json`; nothing in `src/` depends on it. It also omits the git-submodule
frontend and the contracts test harness that the browser-facing starters carry,
because this one is headless.

## License

MIT. See [LICENSE](LICENSE).
