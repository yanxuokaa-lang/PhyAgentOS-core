# jevkit

TypeSafe **Jev** as a bounded judgement layer for computer use. Code observes
(Cua Driver on the desktop, phone-harness on a phone), code builds the
candidate list, Jev returns typed answers with probabilities, code decides.
Jev never acts and never invents an element, coordinate or tool name. This is
the same boundary Cua's own `jev-use` recipe draws, applied to native apps and
phones as well as browser DOM.

Three judgements, one raw door:

| Call       | Question it answers                                  | Returns                                   |
|------------|------------------------------------------------------|-------------------------------------------|
| `verify`   | Did the expected change land after this action?      | landed, dialog, error, auth, gate         |
| `pick`     | Which listed element matches this description?       | one candidate or none, confidence, gate   |
| `classify` | What kind of screen is this, and is it consequential?| kind, flags, dialog kind, gate            |
| `ask`      | Anything, with your own Noul/Choice/Score questions   | raw answers                               |

`gate` is `act`, `caution` or `stop`, from confidence thresholds you tune on
your own data (`JEVKIT_HIGH`, `JEVKIT_LOW`). Auth and error screens always
gate to `stop`. A verify with no diff never calls Jev. An unknown or `none`
pick fails closed.

## Install

```bash
cd ~/Documents/jevkit
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e '.[dev]'
```

## Key

Read on demand, in this order: explicit argument, `TYPESAFE_API_KEY`, macOS
Keychain. Store it once (it never goes in a file, argument or log):

```bash
security add-generic-password -a "$USER" -s TYPESAFE_API_KEY -w '<key>' -U
.venv/bin/jev doctor --live
```

## Use from a shell (desktop, Cua Driver)

```bash
jev snapshot --pid 844 --window 10725 --save /tmp/before.json
cua-driver call click '{"pid":844,"element_token":"s0000002a:14"}'
jev verify   --pid 844 --window 10725 --expect "Dark mode is selected" --before /tmp/before.json
jev pick     --pid 844 --window 10725 --target "the Save button"
jev classify --pid 844 --window 10725
```

## Use from Python (phone-harness or anything else)

```python
from jevkit import Judge, compact
j = Judge()
before = compact.phone_boxes(ocr())
tap_text("General")
after = compact.phone_boxes(ocr())
r = j.verify("the General settings page is open", before, after)
if r["gate"] == "act": ...
```

## The recommended pattern

The LLM holds the plan and the context, takes the snapshot, and asks Jev
one narrow question per step: which element, did it land, what screen is
this. That is `pick`, `verify` and `classify`. It scored 37/38 picks on
real windows and drove the phone Settings walk first time. `jev run` below
inverts this (Jev holds the plan) and is kept only for trivially bounded
steps; it needed six attempts on the phone before it landed.

## Optional: let Jev drive one bounded step (`jev run`)

Give it a goal and a window. Code builds a menu of legal moves from the
screen (click each element, type only caller-supplied texts, scroll), strips
anything on the consent list (send, pay, delete, sign in, allow, call, ...),
Jev picks one move, the driver executes it, verify runs, repeat. It stops on
done, likely_done (goal-met leans yes but no confident move remains), unsure, an auth or error screen, a consequential dialog, a stuck
screen, or the step and time limits, and returns a trace.

```bash
jev run --pid 7466 --window 482 --goal "open the Appearance settings pane" --max-steps 6
# {"status": "done", "reason": "goal_met p=0.97", "steps": 2, "seconds": 9.5, ...}
```

Phone: `jev_run(goal, texts=(), max_steps=12)` inside phone-harness scripts.
Measured 2026-09-17: Settings root to About on the test iPhone in 4 steps,
33 s, goal_met 0.93. Jev never chooses coordinates, tokens or text; only a
menu id.

## Offline and CI

`JEVKIT_MOCK=1` answers deterministically without a key. `JEVKIT_DISABLE=1`
makes every judgement report `unavailable` so callers fall back. Tests run
against recorded Cua snapshots in `tests/fixtures` and never touch the
network; `JEVKIT_LIVE=1 pytest` adds one live smoke test.

## Log

Every call appends one line to `~/.local/state/jevkit/calls.jsonl`: timing,
model, token usage, question ids, answers, and a hash of the state. Never the
state text, never the key. Tune thresholds from it.
