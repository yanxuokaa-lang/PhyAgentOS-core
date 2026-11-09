# Jev plays Snake

[TypeSafe's Jev](https://typesafe.ai) is a "System One" model: no text generation, only typed answers (a Choice, a Score, or a yes/no Noul) with probabilities and confidence, in about 300 ms and at $0.042 per million input tokens. This repo puts it in charge of a snake, live in the browser, and then lets it study its own deaths.

![demo](.github/demo.gif)

[Full clip with the side panel updating live (mp4)](.github/demo.mp4)

## Run

```
npm install
export TYPESAFE_API_KEY=...   # https://console.typesafe.ai/keys
npm start                     # http://localhost:3000
```

Needs Node 24 (runs `.ts` files directly, no build step).

## How it works

A Node server owns the game loop. Every tick it serialises the board and sends Jev one request with seven questions:

- `move`: Choice over up / down / left / right
- `intent`: Choice over food / bonus / shrink / freeze / survive, so the panel shows the plan behind the move
- `safe_up`, `safe_down`, `safe_left`, `safe_right`: four speculative Nouls, answered in the same request
- `trap_risk`: Noul, is the snake about to enclose itself

Code does the arithmetic (distances, flood-fill reachable cells, nearest spider and item per direction) and the model judges. Code also vetoes any fatal move and sends the most probable safe one instead. The answer streams to the page over server-sent events; the API key never reaches the browser.

- `src/snake/game.ts` — pure game: snake, food, walls, spiders, four items (bonus +3, shrink −3 length, freeze spiders, poison −2 and +2 length), per-direction features
- `src/snake/bot.ts` — the questions, state shaping, veto, and a greedy no-model baseline
- `src/snake/server.ts` — loop, stats, SSE, controls
- `web/` — canvas board and a side panel: move bars, safety dots, intent, lab switches, stats, recent decisions

## Lab

The panel lets you test what the model adds:

- **coach**: a plain-English line added to the move question ("hug the walls", "just survive"). Nothing in code parses it.
- **player**: `jev` or the `greedy` heuristic. Scores are tracked per configuration.
- **features**: off sends only an ASCII board, so the model has to read it.
- **veto**: off sends whatever the model says, even into a wall.
- **spiders**, **walls** (click or drag on the board), and the tick floor.

## Headless eval and self-improvement

```
npm run eval -- --games 6 --parallel 6 [--coach "..."] [--player greedy] [--spiders 2] [--no-rules]
npm run learn -- --iterations 3 --games 6
```

`eval` plays N games with no browser and prints score, ticks, and cause of death per game plus the average, tokens, and cost. It is the yardstick for any change to the questions or state.

`learn` is Jev improving its own harness. Jev cannot learn between requests, so what improves is the prompt, and only in a bounded way:

1. Play N games with the current rules. Keep the last 8 ticks of every death.
2. For each death, ask Jev whether it was avoidable (Noul), which tick was the mistake (Choice over the ticks), and which rule from the fixed catalog in `src/snake/rules.ts` would have avoided it (Choice). Jev picks a rule; it never writes one.
3. Add the most voted rule and play N more games. Keep it only if the average score rose by at least half a point. Otherwise mark it rejected.

The active set is capped at four one-sentence rules, so the prompt grows by about 60 tokens at most and then plateaus. A new rule past the cap replaces the oldest and has to beat it. Rules live in `data/rules.json`; the server loads them on start and shows them under Lab.

First run on this repo: Jev blamed every spider death on "keep two cells from spiders", trialled it twice, and the gate rejected it both times because it halved the score. Four games per side is noisy; use eight or more for real decisions.

## Numbers

Typical: 270–330 ms per move, 3.5 ticks per second, about 1,300 input tokens per move, under two cents for a 400-tick game.
