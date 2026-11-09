# Jev Playground

An interactive playground for learning how [Jev](https://docs.typesafe.ai/introduction) works. Jev is TypeSafe's
"System One" model. It doesn't generate text: you give it some **state** (text or JSON) and a set of typed
**questions**, and it answers all of them at once with **probabilities** your code can use directly.

There are three question types:

- **choice**: pick one option, with a probability for each option and a confidence
- **score**: rate against ordered levels, with a probability for each level and a confidence
- **boolean**: the probability that the answer is yes

![Workbench: build questions and see each answer's probability distribution](docs/workbench.png)

![Vibe Check: any spectrum becomes a score, with the request and response shown below](docs/vibe-check.png)

## What's inside

| Widget | What it teaches |
| --- | --- |
| Workbench | Build any mix of questions and see the raw answers |
| Live Router | Intent routing as you type, with actions gated on confidence |
| Inbox Triage | Asking many questions per item, and sending many items in parallel |
| Composite Scorer | Scoring separate criteria, then combining them with weights in code |
| Agent Pilot | Deciding an agent's next step from structured JSON state |
| Guardrail | Checking an LLM's draft reply against a policy before it's sent |
| Vibe Check | Turning any spectrum you describe into a score |
| Race vs LLM | Speed and cost compared with a general-purpose LLM |

Under every widget you'll see the exact request and response side by side. The sidebar log tracks latency, time
spent inside the model, and cost.

## Run it yourself

You'll need Node 20+ and a [Vercel AI Gateway](https://vercel.com/docs/ai-gateway) API key.

```bash
git clone https://github.com/ClemannD/jev-playground.git
cd jev-playground
npm install
echo "AI_GATEWAY_API_KEY=your_key_here" > .env
npm run dev
```

Open http://localhost:3000.

All Jev calls go through one route, `src/app/api/evaluate/route.ts`, which uses the AI SDK:

```ts
import { experimental_evaluate as evaluate } from "ai";

const { answers } = await evaluate({
  model: "typesafe-ai/jev",
  state: "The support agent issued a full refund to the customer.",
  questions: {
    refunded: { type: "boolean", instructions: "Was a refund issued?" },
  },
});
```

To add your own experiment, copy a widget in `src/components/widgets/`, call `ask()` from `src/lib/client.ts`, and
register it in `src/components/App.tsx`.

> **Note:** AI Gateway's free tier rate-limits Jev requests. If you see a rate-limit message, wait a couple of
> minutes or add credits to your Vercel team.
