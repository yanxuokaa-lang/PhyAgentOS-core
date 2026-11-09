# Jev Plays Brogue

A web app that watches [Jev](https://typesafe.ai), TypeSafe's System One model, play the roguelike [Brogue](https://sites.google.com/site/broguegame/) (specifically [BrogueCE](https://github.com/tmewett/BrogueCE), the actively maintained fork) live, showing its decisions, confidence, running dollar cost, and how its behavior changes as it plays more games.

## How it works

The whole project is built around a dual-process split, plus a real self-learning layer underneath it:

- **Jev supplies fast judgment, nothing else.** Every turn, code narrows the situation down to a small set of real options -- legal moves, whether an item is worth using, which item -- and Jev picks among them as a typed `choice`, never free text. `src/typesafeAgent.ts` builds the request; a second, speculative `itemChoice` question is asked in parallel whenever an item action is on the menu, so "should I use an item" and "which one" are answered together in one call without Jev ever seeing raw inventory management as its own puzzle.
- **A hand-built expert system owns everything with a clear right answer.** `src/expertSystem/` (`facts.ts` derives a structured snapshot of the game state; `rules.ts` is an ordered, inspectable rule ladder) decides eat-when-hungry, flee-at-critical-HP, auto-equip strictly-better gear, auto-read a scroll of identify, and a handful of mined tactical interactions (`src/knowledge/strategies.ts`) -- all without spending a Jev call. Jev is only asked when there's a genuine judgment call left.
- **A real learning layer, calibrated by outcomes, not hand-picked constants.** `src/learning/` runs Thompson Sampling (`bandit.ts`) over the expert system's own tunable thresholds, correlates each reward dimension's weight against actual terminal outcomes once enough evidence exists (`dimensionWeights.ts`), tracks continuous instrumental goal-state (`goalState.ts`) and epistemic coverage (`coverage.ts`), and scores every completed run as a composite reward (`reward.ts`) broken down by dimension, never collapsed to just a total.
- **Real Brogue mechanics are hand-encoded knowledge, not something the agent has to rediscover.** `src/knowledge/` documents monsters, items, terrain, and vault/key/lock/guardian-puzzle mechanics straight from the wiki and strategy guides -- the same way a human player would already know the rules before playing. The learning that actually happens is calibrating strategy and behavior across many dungeons, not re-deriving documented mechanics from scratch.

`vendor/brogue-ce/` is a vendored, lightly patched copy of BrogueCE. The patch adds one new platform file, `src/platform/bot-platform.c`, implementing the same `brogueConsole` interface the SDL2/curses builds use: after each turn it prints one line of JSON to stdout (player stats, inventory, hunger, visible monsters, discovered door/lock/lever/vault features, legal moves, the rendered screen) and blocks reading one command from stdin. A handful of already-public engine functions (`apply`, `throwItem`, `equip`, `unequip`, `drop`, `zap`, `identify`) are called directly for item-use commands, bypassing Brogue's own interactive item-picker/targeting prompts, which this stdin/stdout protocol has no way to answer. See `NOTICE.md` for exactly what changed and why this project is AGPL-3.0.

## What's in the UI

- **Live view** (`/`) -- watch one game turn by turn: the rendered dungeon, stats, decision log with Jev's confidence and reasoning, and past-run history. Start / Pause / Reset (same dungeon) / New Dungeon controls.
- **Learning detail** (`/learning.html`) -- the actual point of building all this: full run history, bandit posteriors for every tunable parameter, mined-strategy evidence, epistemic coverage trend, recent mistakes, and a **training pass** control that plays a batch of games in the background (same dungeon or a fresh one each time) with no screen streaming, so a long unattended run doesn't cost anything to watch. Also where you archive a training generation -- nothing is ever deleted, a full generation gets copied out with a composed summary and the live tables reset for a fresh one.
- **Run detail** (`/run.html?id=<N>`) -- turn-by-turn drill-down into exactly one run: every captured decision, goal-state event, and mistake.

The live view and a background training pass are two genuinely independent sessions and can run at the same time; a training pass never streams the screen/decision feed nobody's watching.

## Setup

```sh
npm install
npm run build:brogue
cp .env.example .env   # then fill in TYPESAFE_API_KEY
npm run dev
```

Open `http://localhost:3000` and press Start.

Run the test suite with `npm test`.

## Known scope limits

- **ASCII rendering, not the graphical tile set.** BrogueCE ships its real tile sprite sheet (`vendor/brogue-ce/bin/assets/tiles.png`), but the current state protocol only carries the text glyph grid. Matching the graphical look is a separate, larger piece of work.
- **Staff/wand targeting is deliberately simple.** `zapat:` targets the nearest hunting monster for offensive items, an ally for the handful of ally-only staves/wands, or the player's own tile otherwise -- not full general targeting (e.g. staff of obstruction doesn't get an optimal blocking tile).
- **The anti-stall safety net resets on any movement, not genuine progress.** `GameState.update`'s stuck-search bookkeeping treats any position change as "not stuck," so a genuine back-and-forth between two tiles can still slip past it rather than fall through to the fallback rules that would otherwise catch it. The no-turn-progress watchdog (`gameSession.ts`) still prevents a true hang, but not a long unproductive stretch.
- **Cost uses published Jev pricing.** $0.042 per million input tokens, output tokens free, per [TypeSafe's announcement post](https://typesafe.ai/blog/introducing-system-one-models-and-jev) (2026-09-17). TypeSafe describes Jev as early access and expects this rate to fall rather than rise, so treat it as a snapshot -- override with `TYPESAFE_INPUT_PRICE_PER_MILLION` / `TYPESAFE_OUTPUT_PRICE_PER_MILLION` in `.env` if it changes.
