# Jev Tetris Benchmark

A reproducible demo that gives the same Tetris board and legal placement candidates to **Jev**, TypeSafe's System One model, and the general-purpose language model **Claude Haiku 4.5**, then compares their placement decisions.

The game itself is deterministic code. The models only decide which placement to select from at most 12 legal candidates. The decision policy prioritizes avoiding new holes, followed by clearing lines, reducing existing holes, keeping the stack low, and smoothing the surface.

## What this repository demonstrates

- Using a Jev `Choice` question for decision-making over application state
- Connecting to Jev through either Vercel AI Gateway or the TypeSafe API directly
- Comparing Jev and Claude Haiku 4.5 under identical game conditions
- An English-first interface with an in-page Japanese language switch
- Tracking progress to 20 cleared lines, game overs, decision latency, input tokens, and estimated API cost
- Inspecting the candidate probabilities and confidence returned by Jev

## Requirements

- Node.js 22 or later
- One of the following for Jev:
  - A [Vercel AI Gateway](https://vercel.com/ai-gateway) API key
  - A [TypeSafe AI](https://typesafe.ai/) API key
- An Anthropic API key if you want to run the head-to-head comparison

API usage is billed to your own service accounts. The costs shown in the UI are estimates based on the rates encoded in this repository. Always check each provider's current pricing.

## Run locally

```bash
git clone https://github.com/planstack-ai/jev-tetris-benchmark.git
cd jev-tetris-benchmark
npm install
cp .env.example .env.local
```

Add your own API keys to `.env.local`.

### Use Jev through Vercel AI Gateway

```dotenv
AI_GATEWAY_API_KEY=your_gateway_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### Connect directly to TypeSafe

```dotenv
TYPESAFE_API_KEY=your_typesafe_key
TETRIS_JEV_MODEL=jev-latest
ANTHROPIC_API_KEY=your_anthropic_key
```

Start the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and click the primary start button. API keys are read only by the Next.js Route Handlers and are never sent to the browser.

If no Anthropic key is configured, the demo runs in Jev-only mode. If no Jev key is configured, it runs in Haiku-only mode.

## How it works

```text
Current board + tetromino
          ↓
Code enumerates legal rotations and horizontal positions
          ↓
Code measures holes, cleared lines, height, and bumpiness
          ↓
The top 12 candidates are sent to each model as identical JSON
          ↓
Jev Choice or Haiku tool use returns one candidate ID
          ↓
Code validates the selection and applies it to the board
```

Jev receives one `Choice` question. Candidate generation, Tetris rules, input validation, and board updates remain in deterministic code. This is an example of the TypeSafe pattern: keep known operations in code and use the model only for the bounded semantic decision.

## Key files

- `app/engine.ts` — Board state, rotations, drops, line clears, and candidate generation
- `app/tetris-demo.tsx` — Race orchestration and visualization
- `lib/tetris-jev.mjs` — Jev Choice request, validation, and Gateway/direct connections
- `lib/tetris-haiku.mjs` — Haiku tool-use request and validation
- `app/api/` — Route Handlers that keep API keys on the server
- `tests/` — Tests for API boundaries, invalid choices, rate limits, and candidate generation

## Verification

```bash
npm test
npm run lint
npm run build
```

The tests mock all external APIs, so input validation and response handling can be verified without incurring usage charges. Use the browser demo to reproduce the experiment with live models.

## Security

- Never put API keys in `NEXT_PUBLIC_` environment variables.
- `.env.local` is excluded from Git.
- API endpoints verify the same origin and a dedicated request header.
- Candidate count, board dimensions, numeric ranges, and returned candidate IDs are validated.
- Requests made through Vercel AI Gateway enable Zero Data Retention per request.

## Limitations

This is a use-case benchmark, not a rigorous model evaluation. Results may change with model updates, rate limits, network conditions, prompt changes, or candidate-generation changes.

## License

[MIT](./LICENSE)
