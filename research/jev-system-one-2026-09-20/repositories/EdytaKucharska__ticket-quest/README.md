# Ticket Quest

A playful ticket triage app that shows product managers how [TypeSafe Jev](https://docs.typesafe.ai) works and why a typed decision model suits prioritisation better than prompting an LLM.

Jev does not write anything. For each ticket it answers six narrow questions in one call and returns typed values **with probabilities**. The app's code does the rest: it combines three scores into a Cost of Delay rank, and uses Jev's certainty to decide which tickets can go straight to engineering and which need a person.

The demo workspace is a B2B marketplace where restaurant chefs order from local food producers.

**Live demo (simulated answers, no keys):** https://ticket-quest-three.vercel.app

## Run it

```bash
npm install
npm run dev        # http://localhost:3000
```

With no configuration the app runs in **fixture mode**: the ten demo tickets replay recorded-style answers and timings, and any ticket you add is scored by a keyword heuristic. Everything is labelled "Simulated". Nothing leaves your machine.

To use the real models, copy `.env.example` to `.env.local` and fill in:

| Variable | What it does |
|---|---|
| `TYPESAFE_API_KEY` | Turns on live Jev calls to `POST https://api.typesafe.ai/v1/systemone`. |
| `LLM_PROVIDER` | `anthropic`, or `openai` for any OpenAI-compatible endpoint. |
| `LLM_API_KEY`, `LLM_MODEL` | Your own key and model for the comparison. Anthropic defaults to `claude-opus-5`. |
| `LLM_BASE_URL` | Optional. Point the `openai` provider at OpenRouter, Groq, Ollama and so on. |
| `WORKSPACE_CONTEXT` | One line about your product, sent with every ticket. |
| `FIXTURE_MODE=1` | Forces simulated answers even with keys set, for offline or repeatable demos. |

Keys are read only by the server routes in `src/app/api`. The footer shows which side is live. Restart the dev server after changing env vars, then press **Run triage** to replace the simulated answers with real ones.

## What to try

1. **Run triage.** Both sides get the same tickets, three requests at a time. The backlog fills from Jev while the LLM is still streaming.
2. **Drag "Auto-route at or above" down to 0.75.** The allergen ticket (certainty about 0.77) moves to "Auto-routed to eng". The Jev call counter does not move: routing is computed from stored answers.
3. **Raise the "Risk if ignored" weight.** The price-list leak climbs past the failed payouts.
4. **Open Ask your LLM.** Same questions, same wording, JSON requested. You see wall-clock time, where the answers differ from Jev, replies that broke the JSON format, and, after **Run the LLM again**, how many answers changed on identical input.
5. **Click any ticket for the X-ray.** Two decision trails (how Jev decided, how your LLM decided), then every question with Jev's probability bars, the LLM's bare answer beside them, your own override, and the single request behind all six answers.
6. **Open Compare.** Both models' answers pushed through the identical Cost of Delay arithmetic, as two ranked backlogs side by side: which tickets land in a different band, which ones the LLM scores identically (bare integers collapse into ties), and which routes the LLM side can't decide because it returns no certainty.
7. **Add your own ticket**, or paste a JSON or CSV export. A vague ticket gets flat distributions and lands in Needs review.

## How it decides

- **Questions** (`src/lib/questions.ts`): three `score` questions (Value, Time criticality, Risk if ignored, each with four concrete levels), one `choice` (work type), two `noul` yes/no questions (PM call needed, Eng can start). This one file feeds the Jev request, the LLM prompt and the X-ray, so adding a dimension is one entry.
- **Rank** (`src/lib/scoring.ts`): Cost of Delay = weighted mean of the three scores, 0 to 100. P0 at 75, P1 at 55, P2 at 30. With WSJF on, it is divided by a job size that only a human sets.
- **Certainty**: the mean of the three scores' confidence, as returned by Jev. Yes/no answers carry no confidence; a probability near 50% means "unsure".
- **Route** (`src/lib/routing.ts`): Needs review if certainty is under the review gate, a PM call is likely (70%+), or both yes/no answers sit near 50%. Auto-routed if certainty clears the auto gate and "Eng can start" is 80%+. P0s always appear under Incidents, whatever their route.
- **The LLM comparison is strict on purpose.** The reply must be one valid JSON object with allowed values, the bar any downstream code would hold it to. There is no fence-stripping and no retry.

## Project layout

```
src/lib/          pure logic, unit tested: questions, scoring, routing, agreement,
                  compare (LLM-side ranking, decision trails), import (JSON/CSV), Jev request + response validation, LLM prompt + reply parsing,
                  fixtures and the offline simulator, the useQuest state hook
src/server/       env config, Jev client with retry on 429/529, Anthropic and OpenAI-compatible adapters
src/app/api/      /api/jev, /api/llm (text stream), /api/status
src/components/   Backlog, Needs review, Incidents, Ask your LLM, Compare, X-ray, New ticket
```

```bash
npm test           # vitest
npm run typecheck
npm run lint
```

## Notes

- Tickets, dials and results are saved in your browser's localStorage only. "Restore the demo pack" in the footer resets them.
- The fixtures in `src/lib/demo-tickets.ts` are hand-written to look like real responses. To refresh them, run with live keys and copy the answers in.
- Pixel art and names are original. No Nintendo assets or character names are used.

## License

MIT. See [LICENSE](LICENSE).
