# Jev plays SameGame: the benchmark and its data

What should a decision model be shown so that it plays a board game well? This repository holds
the experiment behind the post [Jev plays SameGame](https://objectgraph.com/blog/jev-plays-samegame/):
21 ways ("strategies") of putting a SameGame board in front of TypeSafe's Jev, each played three
times on the same 20 boards and three times on 20 more that nothing was tuned on. That is 76,795
API calls. **Every request sent and every response received is kept**, so the results can be
checked, re-analysed or disagreed with without asking us for anything.

Gavi Narra, ObjectGraph LLC, September 18, 2026. Questions: info@objectgraph.com. MIT licence,
code and data.

## What we found, in one paragraph

Jev cannot play from the board itself: a character grid, in three formats, scores like random
moves, with near-flat probabilities (confidence 0.10). It plays well from one-move-ahead facts that
code computes and states in words. How a fact is worded matters more than the fact: telling Jev
that the most common colour is "worth saving" did not help (−9 % on one board set, −3 % and within
noise on the other), and the same fact written as a fault on the offending moves ("spends purple
tiles too early") made it play 23 to 37 % better. Instructions that change with the stage of the
game are worth 15 to 22 %. The best prompts score 36 to 71 % more than the first one and keep pace
with a search that plays every move out to the end greedily, with no lookahead of their own: they
outscore it in total by 3 to 25 % but win only about half the boards against it, and only one of
those six intervals excludes 1. A fixed rule with no model (never clear the most common colour
while anything else can be cleared) is a strong baseline that outscored our first prompt; Jev on
top of the rule beats the rule alone on 15 to 19 of 20 boards. `python3 compare.py` prints the
board-by-board comparisons with bootstrap intervals behind each of these sentences.

| 20 boards, mean of 3 runs | `bench` (tuned on) | `fresh` (never tuned on) |
| --- | ---: | ---: |
| `spare`: the saving rule in code, Jev chooses among the rest | 146,993 | **183,440** |
| `spare+staged` | **161,047** | 177,860 |
| `warn+staged`: "too early" warning, instructions by stage | 152,120 | 178,907 |
| `warn` | 137,413 | 147,067 |
| `staged` | 128,447 | 130,440 |
| `words`: what samegame.app shipped first | 112,013 | 107,100 |
| `main`: the same fact as `warn`, worded as "worth saving" | 101,687 | 104,380 |
| `words+grid` | 95,393 | 90,973 |
| `grid` / `grid-string` / `labels` | 77,907 / 77,560 / 77,440 | 83,367 / 79,133 / 75,953 |
| (search: hint solver), no model | 147,020 | 146,500 |
| (save the main colour, largest of the rest), no model | 118,080 | 152,760 |
| (save the main colour, random of the rest), no model, 8 seeds | 127,828 | 139,445 |
| (largest first), no model | 77,420 | 76,080 |
| (random), no model, 8 seeds | 74,715 | 78,468 |

`npm run report` prints every strategy with its range over the three runs, boards cleared, tiles
left, confidence, tokens and cost.

## The game

SameGame is played on a board of coloured tiles. A *group* is two or more tiles of one colour
connected side by side or one above the other. A move clears one group: the tiles above fall
straight down, and a column left empty closes up to the left. The game ends when no group is left.

- A group of *n* tiles scores **n(n−1)×10**: 2 tiles 20, 5 tiles 200, 10 tiles 900, 20 tiles 3,800.
- When the game ends, the tiles left give a bonus: 0 left **2,000**, 1 left 1,600, 2 left 1,300,
  3 left 1,000, 4 left 500, 5 left 300, more than 5 nothing.
- **Classic** is 8 columns by 12 rows, **Expert** 12 by 18, both in 5 colours (red, blue, green,
  yellow, purple). Every board was dealt by the iSameGame generator, which only deals boards that
  can be cleared completely, so 2,000 bonus points are always possible.

The skill is patience: spend small groups so that one colour falls together into something big.

## The boards

`boards.json` has two sets of 20 boards (16 Classic, 4 Expert), each as a picture: top row first,
one digit per tile (0 red, 1 blue, 2 green, 3 yellow, 4 purple). Each can be played in a browser
at `https://samegame.app/b/<code>`.

- **`bench`**: the boards every strategy was tried on, and the ones prompts were adjusted against.
- **`fresh`**: 20 more boards that no prompt was adjusted against. Only finished strategies played
  them. Trust these numbers more.

## The model

[TypeSafe](https://typesafe.ai)'s Jev through `POST https://api.typesafe.ai/v1/systemone`, model
`jev-latest`, which the API reported as **`jev-1.13.0`** on every call (`runs.jsonl` has the time
of each run). Jev does not generate text: it takes a `state` and typed `questions` (Choice, Score,
Noul) and returns probabilities. TypeSafe says it is trained with "reinforcement learning for
calibrated decisions"; it publishes nothing about data, size or architecture. Jev is not
deterministic: the same request can return slightly different probabilities, which is why every
strategy was run three times.

## The strategies

Every strategy asks on every move that has more than one legal group (a move with one legal group
is played without asking). Unless noted it is **one call with one Choice question** whose options
are the legal moves, and the move with the highest probability is played. The instructions are the
same four strategy sentences and scoring note everywhere unless noted; read any
`results/bench/<strategy>.request.json` for the exact words.

| Strategy | State Jev sees | Each option (a legal move) | Decision |
| --- | --- | --- | --- |
| `words` | tiles left, moves available, tiles per colour, lone tiles | one-move-ahead facts in words: colour, size, points, whether it joins a colour into a bigger group, lone tiles stranded or connected, a single tile left of a colour, last tiles of a colour, ends the game | highest probability. **This is what samegame.app ships.** |
| `grid` | the board as characters, one letter per tile, rows numbered, columns lettered | only a cell: "the group that includes the tile at column c, row 5" | highest probability |
| `grid-string` | the same grid as one multi-line string instead of a list of rows | as `grid` | highest probability |
| `labels` | a grid where each tile is its colour and the label of the move that clears it (`Ra Ra B-`) | only the label | highest probability |
| `grid+size` | as `grid` | colour, size, points and the cell | highest probability |
| `size-only` | as `words` | colour, size and points, nothing else (control for `grid+size`) | highest probability |
| `words+grid` | `words` state plus the grid | `words` facts plus the cell | highest probability |
| `nonum` | colours ordered from most tiles to fewest | `words` facts with every digit replaced by a word (tiny, small, medium, large, huge; one, two, several) | highest probability |
| `main` | `words` state plus the colour to save | `words` facts plus whether the move spends or spares the colour with the most tiles | highest probability |
| `staged` | as `words` | as `words`; the strategy sentences change with the stage of the game (above 60 % of tiles left: build; below 30 %: clear the board) | highest probability |
| `main+staged` | as `main` | as `main`, with the staged instructions | highest probability |
| `warn` | as `words` | `words` facts; a move that spends the colour with the most tiles while another colour can still be cleared also carries `too_early: "spends purple tiles too early: purple is the colour to keep until the end"`; other moves carry nothing extra | highest probability |
| `warn+staged` | as `words` | as `warn`, with the staged instructions | highest probability |
| `spare` | as `words` | `words` facts, but **code removes** every move that spends the colour with the most tiles while another colour can still be cleared (one move left is played without asking) | highest probability among the moves shown |
| `spare+staged` | as `words` | as `spare`, with the staged instructions | as `spare` |
| `spare+staged+rate` | | | `spare+staged` while more than 30 % of the tiles are left, then `rate` |
| `warn+staged+rate` | | | `warn+staged` while more than 30 % of the tiles are left, then `rate` |
| `shuffle3` | as `words` | as `words` | one call, the same question three times with the options in three orders; probabilities averaged |
| `split` | as `words` | as `words` | one call, three Choice questions (the whole judgment; which move builds most; which is safest for clearing the board); geometric mean of the three probabilities |
| `rate` | as `words` | — | one call, one **Score** question per move with its facts in the instructions, four described levels from bad to strong; the best expected level plays |
| `shortlist` | as `main` | as `main` | **two calls**: every move, then the same question over only the four most probable |

Players that use no model, for scale: `(random)` and `(save the main colour, random of the rest)`
average 8 seeded games a board; `(largest first)`; `(save the main colour, largest of the rest)`
never clears the colour with the most tiles while another colour has a group, which is the saving
fact of `main` played as a fixed rule with no judgment; `(search: hint solver)` tries every legal
move, finishes each one largest-first, and plays the best, which is the app's Hint button.

Nothing given to Jev looks more than one move ahead, on purpose. An earlier version gave each move
the score a largest-first finish would reach from there; Jev picked the move with the best such
number about 90 % of the time, which is the search playing, so it was removed.

## The files

`results/<set>/`, one group of files per strategy:

- **`<strategy>.jsonl`** — one line per game. `code`, `run` (0–2), `total` (score plus bonus),
  `cleared`, `left` (tiles left), `moves`, `asked` (decisions put to Jev), `calls`, `ms` and
  `tokens` (summed over the game; tokens are input tokens as billed), `confidence` (summed over
  decisions; divide by `asked`), `largest` (decisions where the pick was a largest group, ties
  count), `solver` (decisions where the pick was the hint solver's move), `options` (legal moves
  summed over decisions), `model`.
- **`<strategy>.moves.jsonl.gz`** — one line per decision. `code`, `run`, `move` (0-based), `left`,
  `board` (the picture before the move), `pick`, and `options`: for each legal move `id`, `w` (the
  weight it got: Jev's probability for Choice strategies; for `shuffle3` the mean of three, for
  `split` the normalised geometric mean, for `rate` the normalised expected level, for `shortlist`
  the second call's probability, 0 for moves not shortlisted), `at` (`[column, row]` of the group's
  lowest-leftmost tile, from 0 at the bottom left), `colour`, `n` (size), `h` and `v` (longest
  straight run along a row and up a column), `line` (the text line of its top tile in the grid,
  from 0), `builds`, `lone` (change in lone tiles), `single` (leaves one tile of a colour), `main`
  (it is the colour with the most tiles). Options are listed in the order they were sent.
- **`<strategy>.calls.jsonl.gz`** — one line per API call: `code`, `run`, `move`, `ms` (round trip
  from a Mac in New York), `request` (the body exactly as sent) and `response` (the body exactly
  as received: `model`, `answers`, `usage`). This is the raw data; everything else derives from it.
- **`<strategy>.request.json`** — the first request of the first board, pretty-printed.
- **`runs.jsonl`** — when each strategy ran, calls, input tokens, the model version reported.
- **`no-model.json`** — the players that need no model, per board and per seed (written by
  `npm run report`), so `compare.py` can set them against a strategy.

## Reproduce

```
npm install
npm run report                  # the bench table from the files, no API calls
npm run report -- --set fresh   # the fresh table
python3 verify.py               # replays all 2,520 games with a second implementation of the rules; checks picks against raw responses
python3 compare.py              # board by board: boards won, ratio of totals, 95 % bootstrap interval
python3 compare.py warn main --set fresh
python3 analyse.py grid size-only words main warn shuffle3   # what moves the probabilities

export TYPESAFE_API_KEY=...     # only to play new games
npm run bench -- warn+staged --runs 3 --set fresh
npm run bench -- grid --boards C-046191      # a trial, written to results/trial/
```

`jev-bench.ts` is the benchmark: every strategy is a few lines in `STRATEGIES`, and the players that
need no model are in `CODE_PLAYERS`. `lib/engine/` is the rules of the game (groups, gravity,
scoring, the largest-first finish and the hint search) and `lib/jev/moves.ts` the one-move-ahead
facts and the instructions, as samegame.app ships them. `analyse.py` prints, per kind of option,
its *lift* (the weight Jev gave it times the number of options on that move, 1.0 is a fair share),
the row-against-column test within one decision, and for `shuffle3` the option-order test.
A re-run replaces that strategy's files for that board set; the key is only ever sent as a header
and is never written to a log.

## Reading the numbers with care

- The data is internally checked: `verify.py` re-implements the rules in Python, replays every
  logged game from `boards.json` and the move logs, and reaches every published total; every
  logged pick and weight of the one-question strategies equals the raw response of that move.
- Totals over 20 boards hide that the 4 Expert boards carry about 40 % of the points. Use
  `compare.py` before believing a difference: it counts boards won and resamples the boards.
  Solid on both sets: words over any grid, grid equal to random, "too early" over "worth saving",
  staged over fixed instructions, the best prompts over the first one, Jev plus the rule over the
  rule alone. Not solid: any ordering among the top four, and the lead over the search.
- Prompts were adjusted while looking at the `bench` boards. The `fresh` boards are the check.
- Three runs, 20 boards, 4 of them Expert: differences of a few percent between two strategies
  are not findings. The spread between runs is in the `range` column.
- One model version (`jev-1.13.0`), one week. TypeSafe documents the weaknesses we leaned on or
  ran into (numbers, counting, indirection, large state) and says later versions will change them.
- `solver` measures agreement with a weak search, not with the best move; nobody here knows the
  best move.
- The top four strategies on the fresh boards are within each other's run-to-run range. We do not
  claim an order among them.
- The no-model saving rule swings a lot between board sets (118,080 and 152,760 for the same
  rule). Twenty boards is a small sample for a rule that bets a whole game on one colour.
- Lifts compare options across moves, so they mix in when a kind of option occurs. The claim that
  Jev notices letters side by side but not stacked rests on the within-decision test in
  `analyse.py` against the `size-only` control (pairs 1.35× against 1.10×, triples 2.9× against
  1.4× on `bench`; 1.40× and 2.0× against 1.13× and 1.1× on `fresh`), not on the lifts.
- For `spare`, moves decided without a question (one move left after the rule) are not counted in
  `asked`, `confidence`, `largest` or `solver`.
- Option order is the engine's scan order (column by column from the left, bottom to top).
  `shuffle3` is the only strategy that varies it.
- Costs are input tokens at TypeSafe's list price of $0.042 per million; output is not billed.
