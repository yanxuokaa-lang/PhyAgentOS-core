# Jev Flight School

**Jev Flight School is a small experiment in AI decision-making.** Jev controls a Flappy Bird game by choosing one of two actions, `flap` or `coast`, over and over again.

**[Play the live game](https://jev-flight-school.yusufkusibati.chatgpt.site)**

## What is Jev?

[Jev](https://docs.typesafe.ai/concepts/system-one) is TypeSafe's first System One model. It reads natural-language or structured text, then returns a typed judgment with probabilities. It does not generate prose, code, images, or an explanation of its reasoning.

This game uses a [Choice](https://docs.typesafe.ai/primitives/choice) question. The only possible answers are:

```text
flap
coast
```

Jev returns the selected action, a probability for each action, and confidence. The game can use that response directly without parsing a paragraph or asking the model to format JSON correctly.

## Why I built this

I got access to Jev and wanted to understand where a decision model fits next to an LLM.

An LLM is useful when an application needs language, code, research, or multi-step reasoning. Many software loops need something smaller: look at the current state, choose from known actions, expose uncertainty, and hand control back to code.

Flappy Bird makes that difference visible. The model cannot hide behind a polished answer. Each judgment immediately changes the world, and a bad sequence ends the run.

This project explores a simple division of labor:

| | LLM | Jev in this experiment |
| --- | --- | --- |
| Main output | Generated text or code | One typed choice with probabilities |
| Role in software | Produce or reason through an answer | Make a bounded judgment inside a code loop |
| Available actions | Open-ended | Defined by the application |
| Uncertainty | Often handled through prompting or extra logic | Returned with the decision |
| Game use | Could explain how to play or write a controller | Chooses the next move directly |

This is not a benchmark proving that one model class is better. It is a working example of a different interface between AI and software.

## How one move works

1. The game measures the bird's height, vertical speed, and position relative to the next pipe.
2. The physics engine projects `flap` and `coast` 320 milliseconds forward.
3. Jev receives the current state and a text description of both projections.
4. Jev chooses an action.
5. The game applies that action for 160 milliseconds and asks again.

The game pauses while the request is in flight, so internet latency does not move the bird. The forecast dots are only a visualization for the player; Jev receives text and structured values, not the canvas image.

There is no safety controller. If Jev returns a bad action, the game still applies it.

## What the interface shows

- Jev's flap and coast probabilities
- The action applied to the bird
- Request latency
- Input-token usage and estimated API cost
- The exact state description sent for the decision
- A decision history for the current flight
- A human mode using Space or tap, with no API requests

## What changed during development

The first controller sent mostly raw coordinates. It crashed before the first pipe after 14 decisions.

The revised controller also describes the situation in plain terms, such as "above the opening and still rising," and includes a short physics forecast for each action. On the saved seed-42 run, it cleared five pipes in 67 decisions.

That run used 43,003 input tokens. At Jev 1.13's listed price of $0.042 per million input tokens, the model cost was about **$0.0018**. It is one development run, not a general performance claim. Both traces are available in [`research/`](research/).

## Project structure

- [`game.mjs`](game.mjs) contains deterministic physics, observations, and the Jev Choice request.
- [`public/`](public/) contains the Canvas game and interface.
- [`server.mjs`](server.mjs) runs the local Node version.
- [`worker.mjs`](worker.mjs) runs the hosted version and keeps the API key server-side.
- [`game.test.mjs`](game.test.mjs) and [`worker.test.mjs`](worker.test.mjs) verify physics, decision handling, session isolation, and failure behavior.

The browser never receives the TypeSafe API key. Hosted flight state is stored in a signed, HttpOnly cookie. A failed model request pauses the flight instead of silently choosing an action.

## Run it

You need Node.js 22+ and a [TypeSafe](https://typesafe.ai/) API key.

```sh
cp .env.example .env
# Add TYPESAFE_API_KEY to .env
npm start
```

Open `http://localhost:3218`.

Run the checks with:

```sh
npm test
npm run build
npm run test:hosting
```

`npm run check:jev` makes paid API calls and reruns the saved flight probe. `.env` is ignored by Git.

## Limits

- Jev 1.13 accepts text, JSON objects, and arrays of text. It does not accept images, audio, or video.
- The physics forecasts are calculated by code. Jev chooses between them.
- The simulation is decision-paced rather than 60 Hz model control.
- Probabilities describe uncertainty across predictions; they do not guarantee that one move or one flight will succeed.
- The prompt and state shape were developed for this game and should not be treated as a universal controller.
