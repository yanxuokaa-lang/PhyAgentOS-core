# Tonight's build

JEV picks which stream idea we turn into a live MVP.

The board sends TypeSafe one System One request: a structured briefing of the eleven notes, plus typed questions. JEV answers them in parallel. Code gates blocked ideas, weights fitness / shippability / native-JEV fit, and prints a winner.

## The shortlist

| Mark | Idea |
| --- | --- |
| | LangChain plugin with JEV as a tool |
| * | Teach JEV to play Factorio |
| X | OSPF router from a new arXiv paper |
| X | Drop JEV into a Kubernetes cluster |
| * | OpenRouter-style LLM autorouter driven by JEV |
| | Pydantic / PyTorch Geometric plugin (ask endo) |
| | Local log / net-traffic SIEM |
| | Teacher / student / grader boost classifier |
| | Rerank a top-100 vector shortlist with JEV |
| | Scan game demos for something suspicious |
| | Benchmark Hugging Face classification leaderboards |

Stars are interest. X is caution. Live shippability in this environment outranks a star.

## Run it

```bash
npm install
cp .env.example .env.local
# paste TYPESAFE_API_KEY from https://console.typesafe.ai
npm run dev -- --port 4317
```

Open [http://127.0.0.1:4317](http://127.0.0.1:4317). You can also paste a key in the board without putting it in the env file. The key is sent to `/api/decide` and is not written to disk.

## Live

GitHub: [https://github.com/tylerjharden/harden-jev-decides](https://github.com/tylerjharden/harden-jev-decides)

Production: [https://harden-jev-decides.vercel.app](https://harden-jev-decides.vercel.app)

The board works without a server-side key. Paste a TypeSafe key in the Ask JEV panel, or set `TYPESAFE_API_KEY` on the Vercel project if you want a default.

## How the judgment is built

1. **State** (`src/lib/jev/briefing.ts`) — goal, constraints, what this machine actually has, and a card for every option.
2. **Questions** (`src/lib/jev/questions.ts`) — one Choice for the pick, three shared questions, and four questions per option (fitness, shippable, JEV-native, blocked).
3. **Composition** (`src/lib/jev/compose.ts`) — code, not the model, applies gates and weights.

This follows TypeSafe's System One model: keep control flow in code, ask narrow questions, compose probabilities.

## After JEV picks

The winning idea is the MVP we build next on stream.
