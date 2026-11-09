# jev-sales-calls

An example of using [TypeSafe AI](https://typesafe.ai)'s **Jev** model to read a sales call
transcript and answer structured questions about it — no free-text parsing, no JSON wrangling.

The task: given a recorded discovery call and a library of product capability definitions, work out
**which capabilities the prospect actually asked for**, what is blocking the deal, and how warm it
is.

## How it works

Jev's `system_one` endpoint takes a **state** (the thing being evaluated) and a set of named
**questions**, and returns a typed answer for each. This example uses all three question
primitives:

| Primitive | Returns | Used here for |
| :--- | :--- | :--- |
| `Noul` | a 0–1 truth value | "Did the prospect ask for *this* capability?" — one per capability |
| `Choice` | one of your labels | What is primarily blocking the deal |
| `Score` | a position on your rubric | How close the deal is to closing |

Three further `Noul` questions — `unlisted_request`, `rep_declined` and `rep_misinformed` — are
triage flags rather than findings; see below.

The capability questions aren't hand-written. Each file in `data/capabilities/` is a markdown
document with YAML frontmatter:

```markdown
---
id: workload_heat_map
name: Workload Heat Map
category: Resource Management
summary: "A manager view showing each team member's task load as a color-coded bar,
  revealing who is over capacity at a glance."
tiers:
  starter: not_included
  professional: included
  enterprise: included
---

# Workload Heat Map

A manager-facing view that shows each team member's current task load as a color-coded bar...
```

`capabilities.py` parses those into `Capability` records, and `app.py` turns each one into a
`Noul`. The **`summary`** is what goes to the model, so it knows what it's looking for rather than
matching on a bare feature name; the prose body stays behind as documentation for humans. Drop a
new file into the directory and it becomes a new question automatically.

All 26 questions ride in a **single** API call — `system_one` evaluates the state once against
every question.

### Watch the payload

Every question carries its own copy of its criteria, so per-question text is multiplied by the
number of capabilities. Sending each file's full prose body instead of a one-line summary, with
roomier criteria, put the request at ~7,100 tokens; the version here is ~5,000 for the same
answers. Each run prints its actual usage so the cost is visible rather than estimated.

### Criteria do the real work

The naive version of this question scores nearly everything high, because the sales rep demos most
of the product during the call. The `Noul` criteria are what separate a prospect's request from a
rep's pitch:

```python
Noul(
    instructions={
        "question": "The prospect asked for this capability",
        "capability": capability.name,
        "category": capability.category,
        "description": capability.summary,
    },
    criteria={
        "true": "The prospect asked for it or said they need it",
        "false": "The prospect never raised it; the rep pitching it does not count",
    },
)
```

Note that `instructions` takes structured JSON, not just a string — the capability is handed over
as fields rather than flattened into a sentence.

### Ask the model only what needs judgment

The recommended tier is **not** a question. Once the `Noul` answers say what the prospect asked
for, the tier is a lookup: take the capabilities above threshold and pick the cheapest tier whose
frontmatter marks them all `included`. `cheapest_tier()` does that in five lines.

An earlier version did ask Jev to choose the tier. It got the right answer, but the answer was
derived from the transcript rather than from the `Noul` results, so nothing stopped the two from
contradicting each other — a capability could score 0.9 while the tier that includes it went
unrecommended.

What is left for `Choice` is the question that genuinely needs reading the room:

```python
Choice(
    instructions="What is the main thing standing between this prospect and a purchase?",
    criteria={
        "missing_capability": "Something they need is unavailable or only on the roadmap",
        "internal_approval": "They need buy-in from someone else before they can proceed",
        "pricing": "Cost or how the tiers are packaged is the sticking point",
        "none": "Nothing is holding them back; they are ready to move forward",
    },
)
```

On the sample call this returns `internal_approval` — Sarah's stated next step is talking to her
Creative Director — over the more obvious `missing_capability`. Both are defensible, which is what
makes it a question worth asking a model.

## Running it

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14.

```sh
export TYPESAFE_API_KEY=...      # required
uv run jev-sales-calls
```

With no arguments it picks a random call from `data/transcripts/` — the filename is the first line
of the output, so you always know which one you got. Optional positional arguments override the
defaults in `data/`:

```sh
uv run jev-sales-calls data/transcripts/002_north_light.txt
uv run jev-sales-calls path/to/call.txt path/to/capabilities/
```

Other environment variables the SDK reads: `TYPESAFE_BASE_URL`, `TYPESAFE_DEFAULT_MODEL`
(defaults to `jev-latest`), `TYPESAFE_LOG_LEVEL`.

## Generating more test transcripts

One sample call isn't much to judge the questions against. `jev-capabilities` renders the
capability library as a plain-text brief to hand to a *different* model, which writes new
transcripts to run this against:

```sh
uv run jev-capabilities                    # writes build/capabilities-brief.txt
uv run jev-capabilities -                  # or dump it to stdout
uv run jev-capabilities --scenario=clean   # force a particular kind of call
uv run jev-capabilities out.txt data/capabilities/
```

The brief lists every capability grouped by category, with its summary and which tiers include it,
and tells the writing model to pick capabilities the prospect asks for **and** a separate set the
rep merely demos — the distinction the `Noul` criteria exist to catch.

Each run also picks one of four **scenarios** at random, so a batch of generated calls exercises
the triage questions rather than only the capability ones:

| Scenario | The call it asks for | Flag it should trip |
| :--- | :--- | :--- |
| `standard` | at least one request that ships in no tier | `rep_declined` |
| `unlisted` | two or three requests the list does not cover at all | `unlisted_request` |
| `rep_error` | the rep wrongly denies a named capability the product has | `rep_misinformed` |
| `clean` | everything asked for is available; the rep refuses nothing | none — the control |

`rep_error` names a specific shipping capability, drawn at random, so the generated mistake is
concrete rather than left to the writing model to invent. `--scenario=<name>` forces one when you
want a particular case. The scenario is echoed on stdout and recorded in the answer key, which also
gained fields for off-list requests and wrongly-denied capabilities.

The writing model is asked to print everything in its reply, split by `===== TRANSCRIPT =====` and
`===== ANSWER KEY =====` markers, so it needs no file-writing tools — paste the brief into a local
model and copy the two halves back out. The answer key is what makes a generated call scoreable.

Regenerate it whenever `data/capabilities/` changes; it is derived, and lands in gitignored
`build/`.

## Example output

```
001_creative_pulse.txt

  Recommended tier:  Professional  (cheapest tier covering what they asked for)
  Primary blocker:   internal approval
  Deal temperature:  2.00  (Warm)

Asked for by the prospect:

  0.98  MudBrick Creative Suite           roadmap in Professional
  0.97  Multi-level Sub-tasks             included in Professional
  0.95  Hard Task Dependencies            roadmap in Professional
  0.87  Workload Heat Map                 included in Professional
  0.84  Timeline / Gantt View             included in Professional
  0.60  Dependency Mapping (Visual)       included in Professional

Asked for but not available in any tier:

        MudBrick Creative Suite
        Hard Task Dependencies

6 of 24 capabilities above 0.50.
1 call, 26 questions, jev-1.13.0: 5,081 in / 536 out
```

The "not available in any tier" list is the point of the exercise: capabilities this prospect asked
for that can't ship today. In the sample transcript those are exactly the two gaps the call's own
summary flags.

Scores are not deterministic — expect them to move a little between runs.

### The other transcripts

`data/transcripts/` holds five calls that between them exercise the parts of this worth doubting.

**`002_north_light.txt`** is where the `Noul` criteria earn their keep. The rep demos Kanban Boards
and Custom Tags & Labels that the prospect never asked for; both stay below threshold, while the
five capabilities Jordan actually raises come back 0.72 and above. It also lands on Enterprise
rather than Professional, since Resource Capacity Forecasting is Enterprise-only — the
deterministic tier following the answers without being told.

**`003_meridian_labs.txt`** was written to break a tie. On the first two calls `primary_blocker`
answered `internal_approval` both times and `deal_temperature` answered 2.00 both times, which is
not evidence that either question works — a constant would look the same. This one is a regulated
lab where enforced sequencing is a compliance requirement, so the gap ends the deal instead of
deferring it:

```
  Recommended tier:  Professional
  Primary blocker:   missing capability
  Deal temperature:  0.47  (Cold)

  0.97  Multi-level Sub-tasks             included in Professional
  0.96  Hard Task Dependencies            roadmap in Professional
  0.93  Recurring Tasks                   included in Professional
  0.90  Time Tracking & Audit Logs        included in Professional
  0.66  Individual Task Assignment        included in Professional
```

Both signals moved. Its answer key is Hard Task Dependencies, Time Tracking & Audit Logs, Recurring
Tasks and Multi-level Sub-tasks as the requests, with Calendar View and Zapier Integration demoed
but never asked for — all six sorted correctly.

Worth noticing that **Dependency Mapping (Visual)** stays below threshold here despite the rep
discussing it at length, having scored 0.62 on the first call. Priya asks only about *enforcement*,
so the two dependency capabilities are being told apart on meaning rather than on the shared word —
which is what the `summary` fields are there to support.

Individual Task Assignment at 0.66 is not on that key, but it isn't clearly wrong either: Priya does
ask whether each stage can have a separate owner.

**`004_vantage_federal.txt`** asks for three things the library has no entry for at all, and
**`005_harlow_media.txt`** is the control: every request is available, the rep refuses nothing.
005 is also the only call so far to reach the ends of two scales — `primary_blocker` answers `none`
and `deal_temperature` answers 3.00, Hot. Its answer key is Kanban Boards, Calendar View,
Multi-level Sub-tasks, Custom Tags & Labels and In-app Comments & @mentions as requests, with
Workload Heat Map and Timeline / Gantt View demoed and explicitly brushed aside; all seven sorted
correctly.

### Knowing what you cannot see

Every answer type is closed-world. A `Noul` is a float, a `Choice` returns one of your own labels,
a `Score` is a position on your rubric — there is no free-text field anywhere in the response. Jev
reads the whole transcript, so it perceives a request for something outside the library perfectly
well; it has no channel to name it. Ask about 24 capabilities and you learn about 24 capabilities.

That silence is the dangerous part: a transcript whose most important request isn't in
`data/capabilities/` produces a confident, clean, wrong-by-omission report.

So one more `Noul` carries the capability names in its instructions and asks whether anything was
requested that none of them cover:

```python
Noul(
    instructions={
        "question": "The prospect asked for a capability that is not in this list",
        "known_capabilities": [c.name for c in capabilities],
    },
    criteria={
        "true": "The prospect asked for something no entry in the list covers",
        "false": "Everything the prospect asked for is covered by some entry in the list",
    },
)
```

It cannot say *what* was asked for — that needs a generative model. What it gives you is the
decision of whether to spend one:

```
  ! 0.92  asked for something not in the library — run an extraction
           pass over this transcript to find out what.
```

A second `Noul`, `rep_declined`, comes at the same blind spot from the other side. Instead of
checking the request against the library, it keys on what the rep *said* — "we don't have that",
"that's on the roadmap", "I can log it as a feature request". That needs no list at all.

Across the five sample calls:

| Transcript | `unlisted_request` | `rep_declined` |
| :--- | ---: | ---: |
| `001_creative_pulse.txt` | 0.21 | 0.98 |
| `002_north_light.txt` | 0.22 | 0.95 |
| `003_meridian_labs.txt` | 0.16 | 0.98 |
| `004_vantage_federal.txt` | **0.92** | 0.95 |
| `005_harlow_media.txt` | 0.10 | 0.02 |

Read them as a pair, because only one combination needs a second model:

- **Declined, not unlisted** (001, 002, 003) — a real gap, and the report already names it:
  MudBrick Creative Suite, Hard Task Dependencies. Nothing further to do.
- **Declined and unlisted** (004) — a gap the library cannot name. Run the extraction pass.
- **Neither** (005) — the rep said yes to everything asked. Nothing was missed.

`rep_declined` is the wrong thing to trigger on by itself: four of five calls score above 0.95,
because a discovery call where nothing is refused is rare. Its value is corroboration, especially
when `unlisted_request` lands mid-range — a 0.45 next to a 0.97 decline is worth a look, a 0.45 next
to 005's 0.02 is noise.

### Was the rep right?

A third flag, `rep_misinformed`, asks whether a refusal was *wrong* — whether the rep denied
something the product actually ships. It carries the capabilities that exist, annotated with the
tiers that include them, and its `false` criterion excuses tier-scoping so an accurate "that's
Enterprise only" is not counted as an error.

This is a coaching signal rather than a deal signal: it finds AEs talking prospects out of
capabilities that exist. It separates cleanly from `rep_declined`, which fires on any refusal:

| Case | `rep_declined` | `rep_misinformed` |
| :--- | ---: | ---: |
| 005, nothing refused | 0.02 | 0.05 |
| 005 + a correct no (hard dependencies, genuinely absent) | 0.98 | 0.07 |
| 005 + a wrong no (email-to-task, actually Professional+) | 0.95 | **0.90** |
| 005 + a wrong no (Slack, actually Professional+) | 0.95 | **0.93** |
| `001_creative_pulse.txt` | 0.98 | 0.27 |
| `004_vantage_federal.txt` | 0.93 | 0.06 |

None of the five real transcripts trips it — 001's 0.27 is the highest, plausibly because Alex
correctly denies hard dependencies while visual dependency mapping does ship, and the two are
adjacent enough to read as a partial contradiction. The wrong-denial cases above are variants of
005 kept outside the repo; they exist to prove the flag fires, since a corpus where every rep is
accurate cannot demonstrate that.

004 is the case that justifies the whole mechanism. Marcus asks for SAML single sign-on, data
residency or on-premise hosting, and an offline mobile app — none of which exist as capabilities.
The ordinary output for that call shows three capabilities matched, all `included in Enterprise`,
which reads like a deal with no product gap whatsoever. The three things that actually killed it are
invisible without the flag.

## Layout

```
data/transcripts/*.txt          sales call transcripts; one is picked at random (the state)
data/capabilities/*.md          one file per capability (the question source)
src/jev_sales_calls/app.py           builds the questions, makes the call, prints results
src/jev_sales_calls/capabilities.py  parses frontmatter + prose into Capability records
src/jev_sales_calls/brief.py         renders the capability brief for generating transcripts
build/capabilities-brief.txt         generated; not checked in
```

## Extending it

- **More capabilities** — add a markdown file to `data/capabilities/`; `summary` is required.
  Re-run `uv run jev-capabilities` afterwards so the brief matches.
- **Other transcripts** — pass a path; nothing is specific to the sample call.
- **Other questions** — `Score` rubrics are ordered lists of descriptions, `Choice` criteria are a
  label-to-description mapping, and both accept JSON as well as text.
