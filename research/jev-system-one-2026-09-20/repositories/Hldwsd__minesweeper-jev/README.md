# Minesweeper × Jev

> 中文版: [README.zh-CN.md](README.zh-CN.md)

A Minesweeper game where **TypeSafe Jev** plays. Deterministic code owns the
rules and everything logic can prove; Jev supplies the judgment when the board
forces a guess.

```bash
pnpm install
cp .env.example .env      # put your TYPESAFE_API_KEY in it
pnpm build
pnpm start                # http://127.0.0.1:5180
```

---

## What you can do

| Control | What it does |
| --- | --- |
| **Jev's next move** | Play exactly one move. |
| **Let Jev play it out** | Play the game to the end (the same button turns into **Stop**). |
| **Replay this board** | Deal the same seed and size again — the way to compare two strategies on one board. |
| **New game** | Fresh board, fresh seed, same difficulty. |
| **Beginner / Intermediate / Expert** | 9×9 with 10 mines, 16×16 with 40, 16×30 with 99. Switching deals a new board at once. |
| **Seed box** | Shows the seed of the board on screen; type one and press Enter (or **Deal this seed**) to deal exactly that board. |
| **Jev as advisor / Jev in charge** | Switch who decides. See below. |
| **Jev probability / Exact probability** | Switch what the heat colours and in-cell numbers show. |
| **Match stats** | Every finished game with per-strategy win rates; **Reset stats** clears it. Any row's seed is clickable to replay that board. |
| **中文** | Switches every label to Chinese, and back to English. |
| Click a cell | Play it yourself. |
| Right-click a cell | Flag it (a player annotation; it never feeds the solver). |
| Hover anything | A custom bubble, never a native browser tooltip. Hidden cells show all three probabilities, the logic verdict, and whether the cell is boundary or interior. |

The page opens in **English**; the **中文** button in the header switches the
whole interface, and the choice is remembered per browser. That covers the text
the server produces as well — decision reasons and the move log are sent as
codes (`{code: "jev-lowest", cell, probability}`), never as sentences, so
switching the language re-renders games that were played before the switch.

Colours run green (safer) to red (riskier). A green outline means the solvers
*proved* the cell safe; a red outline means they proved it is a mine. A dashed
edge marks an **interior cell** — one that no constraint covers at all.

---

## Who decides what

This split is the point of the project, and it is not arbitrary — it is what the
measurements demanded.

**Code owns:** board generation, mine placement, flood fill, win/loss, and the
two solvers — constraint propagation (`deterministicFacts`) and exact
per-cell probabilities by weighted enumeration (`exactProbabilities`).

**Jev owns:** the read on cells when no proof exists and a guess is forced.

Two strategies expose the difference:

- **Jev as advisor** — logic plays every provable cell (propagation first,
  then enumeration's certainties); Jev is asked to break ties only when the
  board genuinely requires a guess.
- **Jev in charge** — Jev's probabilities drive every move, even where logic
  already knows the answer. This exists so you can watch what happens.

### Why Jev does not compute the probabilities alone

Before building the game, Jev was probed directly on Minesweeper positions and
scored against an exact constraint solver:

| Representation | Mean absolute error vs exact |
| --- | --- |
| Board grid only | 0.381 |
| Board grid + explicit constraint list | 0.207 |
| Board grid + per-cell local constraints | 0.202 |
| Board grid + constraints, 5-level safety Score | 0.206 |

The constraint list helps a lot, and Jev reliably leans the right way on forced
mines (0.85–0.95 for cells the solver proves are mines). But it compresses
everything toward the middle and, crucially, sometimes rates a **provably safe**
cell as the riskiest cell on the board. Playing pure Jev-probability-greedy lost
3 of 3 games, dying after a mean of 3 moves.

Hence the architecture: the provable part is not left to a language model, and
Jev is used for what it actually is — a judgment model — rather than as a
constraint solver. The request Jev receives still carries the board grid *and*
the explicit constraint list, because that representation measurably helps.

---

## Measured results

Everything below was produced by the scripts in this repository against the live
TypeSafe API on a 9x9 board with 10 mines. Raw per-step records are written to
`traces/`.

### How well does Jev judge a Minesweeper position?

The same positions were put to Jev four ways and scored against exact
enumeration (mean absolute error per cell):

| State representation | MAE vs exact |
| --- | --- |
| Board grid only | 0.381 |
| Board grid + explicit constraint list | 0.207 |
| Board grid + per-cell local constraints | 0.202 |
| Board grid + constraints, 5-level safety Score | 0.206 |

The explicit constraint list is worth more than any prompt phrasing tried here.
Even so, Jev compresses probabilities toward the middle and sometimes rates a
*provably safe* cell as the riskiest one on the board. Greedy play on Jev's
probabilities alone lost 3 of 3 games, dying after a mean of 3 moves.

A later experiment on 40 positions and 428 labelled cells reopened the question
of *how* to ask, and picked a different winner. Its numbers are not comparable
with this table — different sampling — so read the next section as the current
answer and this one as the first pass. The complete record of that experiment is
in **[docs/jev-prompt-experiments.md](docs/jev-prompt-experiments.md)**.

### Full games

| Configuration | Games | Won | Mean steps | Jev calls | Tokens in/out | Mean latency |
| --- | --- | --- | --- | --- | --- | --- |
| Advisor | 3 | **3** | 14.7 | 41 | 91,188 / 12,362 | 352 ms |
| Logic + exact only, no Jev | 3 | **3** | 14.7 | 0 | 0 / 0 | — |
| Lead, before the pool fix (seeds 1–10) | 10 | **4** | 9.7 | 87 | 198,557 / 28,620 | 319 ms |
| Lead, pool widened, scales mixed (seeds 1–10) | 10 | **2** | 8.9 | 79 | 190,015 / 26,574 | 340 ms |
| Lead, pool widened, scales unified (seeds 11–18) | 8 | **0** | 7.1 | 57 | 134,648 / 20,558 | 361 ms |
| Lead, focused per-cell prompts (seeds 11–18) | 8 | **1** | 7.1 | 57 | 371,183 / 19,190 | 337 ms |
| Advisor, focused per-cell prompts (seeds 11–18) | 8 | **8** | 20.3 | 162 | 1,028,941 / 53,183 | 398 ms |

In advisor mode Jev was never the deciding voice on these boards: logic and
enumeration solved every one of them outright, which is exactly what the design
predicts. Lead mode is where Jev actually plays, and it wins less than half the
time because a single bad guess ends the game.

**Do not read a trend into the lead-mode rows.** The first two share seeds 1–10
and still differ by two wins, and Jev's answers are not reproducible run to run
(see the caveat below); replaying lead mode on seed 1 has produced both a 4-step
loss and a 12-step win. Eight to ten games cannot separate these configurations.
The A/B block below is the measurement that can, because it compares both rules
on the *same* position.

### How good is Jev when it is the one deciding?

Across the 87 lead-mode decisions (exact probabilities for the same candidate
pool are the baseline):

| | Mean exact P(mine) |
| --- | --- |
| **Jev's pick** | **0.090** |
| A random pick from the same pool | 0.519 |
| The best possible pick | 0.000 |

- Jev picked the exact-best candidate 18/87 times (21%).
- Jev picked a cell that really was a mine 6/87 times (7%).
- In **all 87** decisions a provably safe cell existed.

So Jev's judgment carries real signal — roughly six times better than picking at
random from the same pool — while still being far from what the constraint
solver can prove.

Re-running the same seeds (11–18, 49 lead-mode decisions) after the prompt change
moved the decision quality:

| | Old prompt | Focused per-cell prompts |
| --- | --- | --- |
| Jev picked the exact-best candidate | 1/49 | **5/49** |
| Jev picked a cell that really was a mine | 8/49 | 7/49 |
| Mean exact P(mine) of Jev's pick | 0.139 (a random pick: 0.395) | 0.114 (a random pick: 0.448) |
| Mean boundary MAE | 0.211 | 0.252 |

Hitting the best candidate five times as often is the clearest gain. Two caveats
belong next to it. First, mean boundary MAE got **worse** on the live
distribution (0.211 → 0.252) even though the sampled experiment shows a clear
gain — the two measure different mixes of cells, and it is the live number that
describes play. So the focused prompt made Jev better at *choosing*, not better
at *estimating*. Second, the focused prompt is not free: it sends a 5x5 window
per candidate, so the same 57 lead decisions that cost 134,648 input tokens now
cost 371,183.

### How should the question be phrased?

The full measurement record lives in
**[docs/jev-prompt-experiments.md](docs/jev-prompt-experiments.md)** — all eight
variants, the paired comparison, the bias breakdowns and every archived game run,
regenerated offline (no API calls) by `scripts/lab-report.ts`. This section keeps
the conclusions.

The starting hypothesis was about *where* Jev goes wrong. Cells along the board
edge touch fewer revealed numbers, and the claim was that thin evidence makes Jev
report a **lower** mine probability than it gives cells deeper in, so Jev reads
the edge as safe and steps on a mine. That is a measurable claim, so it was
measured rather than assumed.

`scripts/prompt-lab.ts` generates 40 positions offline with logic and exact
enumeration (costing nothing), labels every sampled cell with how many revealed
numbers count it, and asks each prompt variant about the same cells. Answers are
cached, so re-running an unchanged variant is free; `scripts/lab-analyze.ts`
reports the paired comparison on the cells every variant answered.

**The hypothesis is backwards.** Cells with thin evidence are not under-rated —
they are over-rated, and the cells whose value the numbers pin down exactly are
dragged toward the middle instead:

| Revealed numbers counting the cell | n | Mean exact P(mine) | Mean Jev | Bias |
| --- | --- | --- | --- | --- |
| 0 (no number mentions it) | 28 | 0.106 | 0.291 | +0.185 |
| 1–2 | 202 | 0.202 | 0.390 | +0.188 |
| 3–4 | 106 | 0.575 | 0.551 | −0.025 |
| 5–6 | 33 | 1.000 | 0.756 | −0.244 |
| 7–8 | 47 | 1.000 | 0.757 | −0.243 |

Jev gets the *direction* right — fewer numbers really do mean a safer cell, and
it does give those cells lower numbers. What it cannot do is keep the scale: a
cell that is certainly a mine comes back at 0.756, and one that is genuinely five
times safer comes back at 0.390. Truth separates those two groups by 0.798, Jev
by 0.366. That compression, not the edge itself, is what makes the ranking
between close candidates fail, and it matches the model documentation, which is
explicit that `jev-1.13` does not count and struggles with numeric precision.

Four prompt shapes were tried against that baseline. The winner crops the board
to what each question actually needs — the model docs warn that accuracy falls as
`state` grows with unrelated detail, and that a question requiring several hops
loses accuracy, both of which the original request did:

| Variant | What changed | MAE | Mean exact P(mine) of Jev's pick | Picked the truly safest |
| --- | --- | --- | --- | --- |
| v0 baseline | whole grid plus the whole constraint list in `state`; the question is one sentence telling Jev where to look | 0.342 | 0.012 | 12/40 |
| **v4 focused** | `state` is a two-sentence board summary; each question carries a 5x5 window around its own cell and the numbers that count it, spelled out | **0.273** | **0.003** | **15/40** |
| v5 focused + warning | v4 plus a sentence saying thin evidence is not safety | 0.286 | 0.000 | 13/40 |
| v7 focused + density | v4 plus the board-wide mine rate stated in words | 0.293 | 0.029 | 13/40 |

v4 is what the app now sends. Paired against the baseline on the same positions,
it is better on 3, worse on 0 and tied on 37 (t = −1.61); the per-cell MAE gain
is the solid result, and 40 positions is not enough to make the decision-quality
gain significant on its own. The clearest single improvement is on the cells the
numbers pin down exactly: "certainly a mine" rose from 0.756/0.757 to
0.934/0.889.

Three ideas were rejected outright, each by measurement rather than taste:

- **One Choice over every candidate** (asking Jev to compare the cells instead of
  scoring them) was the worst variant tried: MAE 0.421 on the shared cell set and
  a mean true mine probability of **0.204** for the cell it called safest,
  seventeen times worse than the baseline. It also walked onto a real mine in
  8 of the 40 sampled positions. A Choice's probabilities are relative and normalise across
  options, so most options collapse toward zero and the ordering becomes noise.
- **A 5-level descriptive Score** instead of a probability was worse than the
  baseline (MAE 0.394 on the 20 positions it ran on) — a reminder that a Score's
  levels are weakly calibrated as numbers.
- **Local constraints with a minimal `state`** (MAE 0.328) and the same plus a
  board summary (0.335) both lost to the baseline: telling Jev *which* numbers
  count a cell is not enough if it cannot also see those numbers' own neighbours,
  which is where the second-order evidence lives.

The one thing that reliably did **not** help was adding an explanatory sentence.
Both the "thin evidence is not safety" warning and the density anchor made things
worse, the anchor markedly so.

### Does widening the candidate pool actually help?

The observation that started this: in lead mode every guess landed on the
frontier — cells touching a revealed number — because Jev is only asked about
those, and the move chooser consulted Jev before anything else. Intuition says a
guess in the untouched middle should be safer, and the interior is *provably*
uniform: no constraint mentions those cells at all.

Turning that intuition into code took two attempts, and the first one was wrong.

**Attempt 1 — widen the pool, rank by whatever number is available.** Interior
cells entered with their exact free-cell probability, boundary cells with Jev's
judgment, and the lowest number won. That mixes two scales. Jev's probabilities
are compressed toward the middle (MAE 0.207 against exact), so a boundary cell
Jev rates 0.30 may really be 0.05. Comparing that 0.30 against an interior
cell's honest 0.10 picks the interior cell — and picks worse.

The A/B harness in `scripts/live-play.ts` computes, for every position, what the
old frontier-only rule would have chosen, and scores both choices with exact
probabilities:

| | Attempt 1 (scales mixed) | Attempt 2 (scales unified) |
| --- | --- | --- |
| Positions where the rules disagreed | 22 / 32 | 9 / 57 |
| Mean exact P(mine), new pick | 0.136 | 0.176 |
| Mean exact P(mine), old pick | 0.131 | 0.110 |
| New pick strictly safer / riskier | 4 / **10** | 0 / **1** |
| New pick really was a mine | 3 / 22 | 1 / 9 |
| Old pick really was a mine | 1 / 22 | 2 / 9 |

Attempt 1 made two thirds of its disagreements strictly riskier — the defect it
was meant to fix, reproduced in the opposite direction.

**Attempt 2 — put every candidate on one scale.** Jev is now asked about one
interior cell as well, as a stand-in for the whole unconstrained region (no
constraint tells those cells apart, so one number covers them all), and the
request states how many mines the constraints leave unaccounted for. Every
candidate then carries a Jev number, the ranking compares like with like, and
the widening turns neutral instead of harmful: 8 of 9 disagreements are now
equal-risk, and in the ninth the new pick is safer.

**The honest conclusion:** widening the pool is *correct* — the old rule really
could not leave the frontier — but it is not what costs lead mode its games. In
the 49 lead-mode decisions measured with the unified pool, a provably safe cell
existed every single time, Jev found it once, and Jev walked onto a mine 8
times. The bottleneck is the quality of Jev's judgment, not the size of the pool
it chooses from.

A second, unintended benefit showed up in the same runs: mean boundary MAE fell
to 0.211 across seeds 11–18, against 0.316 on seeds 11–15 before the request
described the unconstrained region to Jev. Overlapping seeds but different game
counts, so treat it as suggestive rather than established.

### How often does the board actually force a guess?

Playing 60 offline games with logic + exact enumeration only (926 moves):

- **3 moves (0.3%)** had no provably safe boundary cell: a real guess.
- The baseline won **58 of 60** games.

Guessing is rare on this board size once combination reasoning is available,
which is why the advisor strategy almost never needs Jev and why the lead
strategy's mistakes are so costly.

### One caveat: Jev's answers are not bit-for-bit reproducible

The same position asked three times returned slightly different per-cell
probabilities (largest spread 0.040, e.g. `0.36 / 0.37 / 0.34` for one cell). The
differences are small, but a decision chain can amplify them: replaying lead mode
on seed 1 produced a 4-step loss in one run and a 12-step win in another. Treat
single-run comparisons between strategies as indicative, not conclusive.

### Reproducing these numbers

```bash
LIVE_SEEDS=1,2,3 pnpm test:live                 # full games, all three configurations
LIVE_SEEDS=1,...,10 LIVE_MODES=lead pnpm test:live   # more lead-mode decisions
LIVE_SEEDS=11,...,18 LIVE_MODES=lead pnpm test:live  # also prints the A/B pool comparison
GUESS_POSITIONS=12 GUESS_SEEDS=60 pnpm exec tsx scripts/live-guess.ts

# Prompt experiment: sample 40 positions, ask every variant, then compare them
# on the cells they all answered. Answers are cached, so a re-run is free.
LAB_VARIANTS=v0,v4,v5,v6,v7 LAB_POSITIONS=40 pnpm exec tsx scripts/prompt-lab.ts
LAB_VARIANTS=v0,v4,v5,v7 pnpm exec tsx scripts/lab-analyze.ts

# Every table in docs/jev-prompt-experiments.md, recomputed from the cache and
# the archived traces. Offline: no API calls, no cost.
pnpm exec tsx scripts/lab-report.ts
```

---

## Bugs found by testing

These were not hypothetical: each was caught by a test or by a measurement
script, and each was fixed.

1. **Revealed zeroes were thrown away.** `constraintsOf` skipped any revealed
   cell with `adj === 0`. A revealed 0 is the strongest constraint on the board
   ("everything around me is safe"), so the solver was discarding its best
   evidence. Caught by a unit test whose expected safe cells came back unknown.
2. **"Truncated" was decided by the wrong quantity.** The enumeration marked
   itself incomplete when the accumulated *weight* exceeded the budget — but the
   weight is a sum of binomials and is legitimately enormous for a complete
   search. Nearly every mid-game position was being declared untrustworthy, which
   silently disabled exact-probability proofs everywhere. Caught by a script that
   collected forced-guess positions and found exactly zero of them.
3. **The advisor guessed when it did not have to.** Tie-breaking handed the move
   to Jev while exact enumeration could already prove a safe cell existed. Live
   measurement showed all 87 Jev decisions in lead mode had a provably safe cell
   available. Fixed by folding enumeration's certainties into the fact set.
4. **The record of *why* a move was made was erased.** `step()` cleared the
   probability cache, so every logged decision had `null` probabilities and the
   "what was Jev thinking" data was unusable. Caught while writing the live
   harness.
5. **Tests poisoned each other.** The E2E suite shared one server, so once a test
   played a game to completion the buttons stayed disabled and eight later tests
   failed on timeouts. Fixed by resetting through the API in `beforeEach`.
6. **A finished analysis could never be re-run.** `#analysing` was assigned after
   the async body started, so a path with no `await` left a settled promise in
   place and every later call short-circuited to it. Restructured so the flag is
   cleared in `finally`.
7. **UI polish:** after a game ended, hidden cells kept their stale heat colours
   and probability numbers; decision labels and the move log were English inside
   an otherwise Chinese UI. The mismatch turned out to be structural rather than
   cosmetic — the server was writing the prose — so it was fixed at the root:
   the server now sends reason and log codes and the UI owns the wording, which
   is what makes the English/Chinese switch possible at all.
8. **Jev-lead could only ever guess on the frontier.** The move chooser consulted
   Jev first and fell through to anything else only when Jev had said nothing —
   and Jev was never asked about interior cells. So whenever a single boundary
   cell had an answer, the frontier monopolised the decision, even though the
   exact solver had already priced every interior cell and the chooser never
   looked at them. Found by reading `#chooseMove` against the observation that
   lead mode lost more than half its games; confirmed by a regression test
   (`candidate pool` in `tests/engine.test.ts`). Fixed by ranking boundary and
   interior cells in one pool. What that fix is actually worth is measured in
   the A/B section above: the structural defect was real, but it was not the
   bottleneck.
9. **The fix for #8 was itself wrong, and only the A/B harness caught it.**
   Widening the pool while ranking by "whatever probability is available" put
   Jev's compressed judgments and the solver's exact numbers on one axis. Two
   thirds of the resulting disagreements were strictly riskier than the old
   rule: the fix meant to make guesses safer made them worse. Win rates could
   not see this — the table looked like noise. Fixed by having Jev judge one
   interior cell as a stand-in for the whole region, so every candidate carries
   a number from the same source.
10. **Tests that asserted the old mechanism instead of the contract.** Both #8
    and #9 broke assertions describing how the previous rule worked internally
    ("only asks Jev about boundary cells", and a pool test expecting
    `source: "exact"`). Rewritten to assert the behaviour that must hold either
    way. Related: the API tests leaked state through the shared engine — the
    match table is module state and the server keeps one board, so a game left
    running by an earlier test was filed as abandoned and inflated the next
    test's row count. Fixed with a helper that closes the running game before
    draining the table.

---

## HTTP API


The server keeps one game in memory and serialises every mutating request.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/state` | Full board, probabilities, analysis stats, match summary. |
| `POST /api/new` | `{rows, cols, mines, seed, strategy}` — new game. The previous unfinished game is filed as abandoned. |
| `POST /api/reveal` | `{row, col}` — human click. |
| `POST /api/flag` | `{row, col}` — toggle a flag. |
| `POST /api/analyze` | Recompute logic + ask Jev about the boundary cells. |
| `POST /api/step` | `{strategy}` — play one move, returns the decision record. |
| `POST /api/auto` | `{strategy, maxSteps}` — play a whole game server-side. |
| `GET /api/matches` | The match table (`records`, newest first) and its `summary`. |
| `POST /api/matches/reset` | Clear the match table. |

The match log lives in server memory only: one process, one board at a time. A
restart empties it, which keeps the numbers honest about what that process
actually observed.

## Configuration

`.env` (see `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | — | Server-side only. Never reaches the browser. |
| `TYPESAFE_BASE_URL` | SDK default | Point at a different endpoint. |
| `JEV_TIMEOUT_MS` | `10000` | Per-call timeout. |
| `JEV_MAX_CALLS` | `300` | Advertised call budget. |
| `JEV_ENABLED` | `1` | Set `0` to run logic-only (the UI says so). |
| `JEV_FAKE` | `0` | Set `1` for a deterministic offline stand-in used by E2E. |
| `PORT` / `HOST` | `5180` / `127.0.0.1` | Where the server listens. |
| `BOARD_ROWS` / `BOARD_COLS` / `BOARD_MINES` | `9` / `9` / `10` | Starting board. |

Without a key the game still runs: logic and exact probabilities are fully
available, Jev-specific fields show `—`, and the UI tells you Jev is off.

---

## Tests

```bash
pnpm typecheck     # tsc --noEmit
pnpm test          # 106 unit tests, hermetic, no network
pnpm test:e2e      # 23 Playwright tests against a built app with a fake Jev
pnpm test:live     # real games against the TypeSafe API (costs tokens)
```

The hermetic suite covers the rules (first click safety, flood fill, flags,
win/loss, seeding), the solvers (subset rule, exact enumeration invariants such
as "probabilities sum to the remaining mine count" and "probability 0 is never a
mine"), the engine's strategy behaviour and candidate pool, the match log, the
Jev request compiler (each question carries the numbers that count its own cell,
a cropped local view, and an explicit "no revealed number touches this cell"
when there is nothing to show), the HTTP API, and the interface dictionary. The
dictionary tests are the guard against a half-translated UI: both languages must
define exactly the same keys with exactly the same placeholders, only an explicit
allow-list of proper nouns may be identical in the two, and every decision reason
and log code the server can emit must render in both. The end-to-end suite drives
the real UI, including the language switch, hovering for all three probabilities,
the custom bubble versus native tooltips, seed replay, difficulty switching, and
the match table.

`pnpm test:live` plays real games and writes raw per-step records to `traces/`.
It also runs an A/B comparison of the candidate-pool rules on identical
positions.

`scripts/prompt-lab.ts` and `scripts/lab-analyze.ts` are the prompt experiment
described above. They stay out of `pnpm test` because they call the live API:
`prompt-lab.ts` caches every answer under `traces/`, and `lab-analyze.ts` is
purely offline and can be re-run at no cost.

## Design notes and limits

- **Every question carries its own evidence.** A question names the revealed
  numbers that count its cell, with the neighbours each of them restricts, and
  ships a 5x5 window of the grid around it — instead of handing Jev the whole
  board and a global constraint list and leaving it to find the cell. On 416
  labelled cells that cut mean absolute error from 0.342 to 0.273; the cost is
  roughly 2.8x the input tokens, because the window is sent once per candidate.
- **Jev is asked about boundary cells plus one interior stand-in.** Boundary
  cells are where the evidence is. One interior cell is asked about as well,
  standing in for the whole unconstrained region — no constraint tells those
  cells apart, so a single number covers all of them. That stand-in is what
  keeps the ranking on one scale: without it the chooser would compare Jev's
  compressed judgments against exact numbers, which measured out as strictly
  worse (see the A/B section above). `DecisionRecord.pool` reports the split for
  every move, so any decision can be checked after the fact.
- **A constraint can only reach a boundary cell**, which is why interior cells
  are provably uniform and why one stand-in is enough to cover all of them.
- **Exact enumeration has a budget.** On wide-open boards the search stops early
  and the UI says so; those probabilities are approximations and are not used as
  proofs.
- **Flags are annotations.** The solvers and Jev both treat a flagged cell as an
  unknown cell, so a mis-placed flag can never corrupt reasoning or the cache key.
- **The board is deterministic from its seed**, and analysis is cached per board
  fingerprint, so hovering never triggers a redundant API call.
- **Analysis is invalidated on every reveal**, and the UI re-runs it in the
  background. Until it lands, the displayed probabilities are the previous
  position's, and the analysis panel says `stale`.
- **Jev's probabilities are judgments, not measurements.** The probe table above
  is the honest calibration for this domain; the app shows exact probabilities
  next to Jev's precisely so the difference stays visible.

---

## License

MIT — see [LICENSE](LICENSE). You need your own `TYPESAFE_API_KEY` to run the
Jev-backed modes; nothing in this repository contains one.
