![JevGPT](assets/banner.png)

# JevGPT

A chatbot built on a model that cannot generate text.

TypeSafe AI's `jev-latest` is a **decision** model: it does not generate text,
it only answers multiple-choice questions about a `state`. JevGPT is a chat
client built on top of that — the state is the conversation transcript, the
question is "Next word?", and the criteria are a 20,000-word dictionary. Ask it
a question and it answers, one word at a time, several hundred choices deep.

```
state:     "User: what is the capital of france?\nAssistant: the capital of france is"
question:  {"b0": {"type": "choice", "instructions": "Next word?",
                   "criteria": {"paris": "", "london": "", ... }}}
answer:    {"paris": 0.87, "p": 0.04, "namely": 0.02, ...}   →  Paris
```

## Demo

`demo/jevgpt.mp4` is a Remotion render of JevGPT building a reply word by word.

[![JevGPT demo — a still from the video](demo/frames/f3.png)](demo/jevgpt.mp4)

## Usage

```bash
uv run jevgpt                                   # interactive REPL
uv run jevgpt --say "what is the capital of france?"
uv run jevgpt --say "hi" --say "bye" --record demo/run.json
```

In the REPL: type a message, watch the reply build word by word. `/reset` clears
history, `/quit` exits.

| flag | default | meaning |
|---|---|---|
| `--max-words` | 150 | hard stop per reply |
| `--seed` | 0 | bucket-shuffle seed; decoding is otherwise deterministic |
| `--say MSG` | — | scripted, non-interactive turn; repeat for a conversation |
| `--record PATH` | — | JSON of the conversation: turns → per-word top-8 distributions, latency, tokens |

`TYPESAFE_API_KEY` is read from `.env` (gitignored).

## How a word is chosen

The API caps a `choice` at **255 criteria** and a call at about **64k input
tokens** — 32 questions of 255 fit, 39 return `max_tokens_exceeded`. So each step is:

1. **Propose.** The vocabulary is reshuffled, cut into 255-word buckets and
   packed 20 to a call, four calls concurrently. A `noul`, "Is the reply
   complete?", rides its own call at the same time.
2. **Run off.** Bucket probabilities are normalised *within* their bucket and
   are not comparable across buckets — a bucket of nonsense still returns a
   confident winner — so the top two from every bucket compete in one final
   `choice`. That distribution is what gets decoded.

Greedy, with three repetition penalties, all of them measured into existence:

- **local**, `1.5ⁿ` over the last 8 words, the last position counting triple —
  the model's favourite mistake is repeating what it just said;
- **content**, `2.5ⁿ` capped at four, over the whole reply — without it a reply
  becomes `Deep / Deep / Deep`; uncapped, and against a dictionary built from
  subtitle data, it drove the model off every good word and into near-miss
  fragments (`under` → `nder` → `der`), which is why the vocabulary is now
  filtered against a real dictionary;
- **stopword**, a gentler `1.6ⁿ` capped at six — content words alone left
  `is are i is are i` free to loop.

A reply may not end before **60 real words**: neither `<END>` nor the
completeness noul (threshold 0.9) is eligible until then. Punctuation and
newlines do not count toward that floor.

The dictionary is lowercase; display capitalises sentence starts. Every word the
conversation has already used is added to the candidate set each turn, so names
and rare words stay reachable.

## The model's ceiling

10 transcripts with a known next word:

| top-1 | top-5 |
|---|---|
| **7/10** | **8/10** |

```
the capital of france is   → paris       rank 1   [paris, p, namely, .]
the sky is                 → blue        rank 1   [blue, white, pink, cold]
the capital of japan is    → tokyo       rank 1   [tokyo, wrong, you, c]
a                          → cat         rank 1   [cat, cats, is, a]
there are                  → seven       rank 1   [seven, days, seventh, with]
the opposite of hot is     → cold        rank 1   [cold, cool, frost, polar]
grass is                   → green       rank 1   [green, greene, yellow, dark]
hamlet was written by      → shakespeare rank 2   [william, shakespeare, shake, sh]
2 plus 2 is                → 4           rank —   [four, yesterday, with, was]
the largest planet is      → jupiter     rank —   [saturn, j, is, in]
```

Both misses are the dictionary, not the model: it answered `four` where the test
wanted `4`, and `jupiter` is not in a 10,000-word frequency list, so it offered
`saturn`. Read that way it is 9/10.

## A real conversation

Verbatim, `--max-words 150`, recorded in `demo/run.json`.

```
you › hi, who are you?
jev › I is are assistant your garbled.? Sorry i apologize. For about ago long
      awhile was been now? Unintelligible. None what?.? Can? Can understand me you
      me understand you hi unanswered? Hi?.? Unknown? Who i who? My is? Is?.? I? My
      a name is called me named?.? An ant ant ants ants ads adds adds? Adds? Asses
      asses stop stops stops
      60 words · stopped: END · 173s

you › write me a paragraph about the sea at night
jev › The sea is dark. And blue. Stops stops stop stars twinkle are twinkle are
      asses asses. Moon shines reflects moonlight on surface. Surface. Sparkling.
      Glittering. Glittering inconclusive conclusive? Serene. Serene.?.? None
      none?.? Unknown?.? Inconclusive?.? Conclusive.? Of of?.? Unclear unclear?
      Conclusive.?.? Nan nan nan non non gibberish gibberish? Endlessly endlessly
      endless? Endless end end ends ends ends endlessly? Next next next
      60 words · stopped: END · 195s
```

Two turns, 368 seconds, 1,092 API calls, 26.8M input tokens, **$1.13**.

`The sea is dark. And blue. … Moon shines reflects moonlight on surface.
Sparkling. Glittering. … Serene.` is real writing, and it comes out of a model
that cannot write. Around it is the seam: asked for sixty words when it wanted
to stop at six, the model runs out of things to classify, and the repetition
penalty pushes it off each word it has just used and onto a morphological
neighbour — `shines` → `shine` → `shining`, `end` → `ends` → `endlessly`. Left
to itself it stops after a sentence and the sentence is usually right.

## Cost of a word

**2.02 s and 147,329 input tokens per word — $0.0062.** Six calls a step: four
that carry the 20,000-word dictionary in 255-word buckets, one that carries the
completeness noul, and the run-off. A 60-word reply costs about 37 cents.

## Probed API limits

| thing | limit |
|---|---|
| `criteria` per `choice` | **255** (`"Too many choices. Must have at most 255 choices."`) |
| questions per call | **32** at 255 criteria each; 39 returns `max_tokens_exceeded` (~64k input tokens) |
| `state` size | 12 KB accepted |
| `criteria` description | may be `""` — identical ranking, about half the tokens (1025 vs 1776 for 100 criteria) |
| criteria order | biases the answer; the vocabulary is reshuffled every step |
| sustained rate | bursts come back 401 `authentication_error`; it clears on its own |

## History: the character-level version

## Prediction vs evaluation

`jev-latest` judges finished text well — it scores `paris` at 0.70 and `pariis`
at 0.10 — so the obvious question is whether judging beats predicting. Measured
on the same 15 pairs:

| method | calls/step | top-1 | top-5 | mean p | tokens/step |
|---|---|---|---|---|---|
| predict: `choice` over 49 characters | 2 | 7/15 | 13/15 | 0.299 | 3.1k |
| evaluate: 49 `noul`, one per candidate appended to the state | 49 | 1/15 | 7/15 | 0.042 | 15.0k |
| evaluate: 49 `score`, rubric gibberish / partial / fluent | 49 | 8/15 | 12/15 | 0.043 | 16.0k |
| **propose with `choice`, re-rank the top 5 with `score`** | **7** | **9/15** | **13/15** | **0.401** | **3.8k** |

Pure evaluation is not worth it: the `noul` judge is blind (1/15) and the
`score` judge buys one case for 25× the calls. The hybrid wins on every axis
and is what `jevgpt` does — `choice` proposes five characters, `score` rates the
reply with each one appended, and the final weight is `p · e^level`.

One thing the judge cannot do: rate punctuation. Given `.` or `<END>` it rewards
anything that looks terminal, so `Paris` decoded as `Pars.. s r e` until the
re-rank was restricted to letters and digits. Punctuation keeps the weight the
`choice` question gave it.

Candidate characters must each go in their own call — `state` is one field, so
49 candidates is 49 states. Putting the candidate in the instruction instead
("With 'u' added next, is the reply natural English?") collapses completely:
`u` did not make the top eight for `bl`.

## The model's ceiling

Same 15 pairs, best format:

| top-1 | top-5 | mean p(correct) |
|---|---|---|
| 7/15 (47%) | 13/15 (87%) | 0.299 |

```
what is 2 plus 2?                     +''            want '4' rank  1 p=0.977
what is the capital of france?        +''            want 'p' rank  1 p=0.683
how many days are in a week?          +''            want '7' rank  1 p=0.905
what is the boiling point of water?   +'10'          want '0' rank  1 p=0.708
what color is grass?                  +'gre'         want 'e' rank  1 p=0.363
what animal says meow?                +'c'           want 'a' rank  1 p=0.242
what color is the sky?                +'bl'          want 'u' rank  2 p=0.120   top 'l' 0.17
what is the capital of france?        +'par'         want 'i' rank  2 p=0.125
what is the opposite of hot?          +'co'          want 'l' rank  3 p=0.108   top 'd' 0.34
who wrote hamlet?                     +'shakespear'  want 'e' rank  3 p=0.102   top 'r' 0.16
what is the first month of the year?  +'janua'       want 'r' rank  5 p=0.045   top 'a' 0.24
what is the largest planet?           +'jupit'       want 'e' rank  6 p=0.038   top 't' 0.27
what is the capital of italy?         +'ro'          want 'm' rank  7 p=0.038   top 'o' 0.12
what is the capital of japan?         +'tok'         want 'y' rank 17 p=0.013   top 'o' 0.36
```

This is the whole story. 47% per character compounds to 0.47⁴ ≈ 5% for a
four-letter word. The model answers a *first* character very well — `4`, `7`,
`p`, `b` — because that is a classification it can do. Continuing requires
remembering which answer it committed to, and it does not; it falls back on a
space, `<END>`, or the character it just used. Beam search plus the repetition
penalty is what gets `Paris` out of it at all.

## A real conversation

Verbatim, `--decode greedy --max-chars 300`, recorded in `demo/run.json`.

```
you › hi, who are you?
jev › I ari .
      7 chars · 0.97s/char · stopped: noul

you › write me a short poem about the sea
jev › W rt eete a a aet e s a a a e t a a a e ta a a a ta t a a at a a t at a aea
      ae a aea ae a aea ae a aeaeaea a a a ae aea a ae aea a ae aea a ae aea aea a
      ea aea aea a ea aea a ea aea a ea aea a ea aea aea a ea aea a ea aea a eaea
      aea a ea aeaea ae a aea ae a aeaeae a a aeae a a aeaea ae a aea ae a ae
      300 chars · 0.74s/char · stopped: max-chars

you › thanks, bye
jev › A
      1 char · stopped: END
```

Three turns, 229 seconds, 1,539 API calls, 1.47M input tokens.

Put next to the ceiling table this is exactly what should happen. `hi, who are
you?` has no factual continuation to classify, so every character draws on the
generic prior, the repetition penalty forbids a straight run, and what is left
is an alternation between the two commonest letters. The model is not failing at
chat; it was never asked to do chat, and asking it 1,539 multiple-choice
questions does not add up to one.

Where there *is* something to classify it does far better — `what is 2 plus 2?`
returns `4` every time, and `what is the capital of france?` gets to `Pariis`
under beam search.

## Cost of a character

Greedy: ~0.40 s and ~3,100 input tokens. Beam width 5: ~0.6 s and ~10,300
input tokens (six shuffled questions per beam plus the judgements, all beams
expanded concurrently, so wall-clock is one round-trip either way).

`demo/run.json` is a recorded three-turn conversation with the full per-character
distribution at every step — the part worth watching even when the text is not.
