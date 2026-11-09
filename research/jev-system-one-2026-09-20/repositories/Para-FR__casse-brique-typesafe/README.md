# Brick Breaker

A brick breaker you can play in the browser, built with Next.js 16, React 19, TypeScript and Tailwind CSS 4. The paddle can be handed over to an AI pilot powered by TypeSafe AI's Jev model.

The in-game interface is in French.

## Getting started

```bash
npm install
npm run dev
```

Then open http://localhost:3000.

The AI pilot needs a TypeSafe API key. Copy `.env.example` to `.env.local` and set `TYPESAFE_API_KEY`.

## Controls

| Action | Control |
| --- | --- |
| Move the paddle | Mouse, touch, arrow keys, Q/A and D |
| Launch the ball, restart | Click, Space or Enter |
| Pause | P or Escape |
| Hand the paddle to the AI pilot | I, or the button in the side panel |

## Rules

- The ball speeds up by 12 px/s for every brick destroyed, up to a cap of 900 px/s.
- The paddle's maximum speed scales with the ball's speed.
- Each level hides six surprise bricks at random, marked with a question mark.

| Surprise | Effect |
| --- | --- |
| Multiball ×3 | The ball that breaks the brick splits into three, up to 12 balls in play. |
| Wide paddle | The paddle grows from 110 to 170 px for 10 seconds. |
| Extra life | One more life, up to 5. |

You only lose a life when the last ball falls. Temporary effects end when you lose a life or move to the next level.

## Project structure

- `src/game/engine.ts`: game state and rules (collisions, lives, levels, score), with no DOM dependency.
- `src/game/render.ts`: draws the game state on a 2D canvas.
- `src/components/BrickBreaker.tsx`: client component that runs the animation loop and handles input.
- `src/app/page.tsx`: home page that displays the game.
- `src/components/GameInfoPanel.tsx`: real-time info panel, including the AI pilot's statistics.

## TypeSafe AI pilot

The pilot lets TypeSafe's Jev model decide where the paddle goes, through a Choice question.

1. The browser sends the ball's position and velocity to `/api/paddle`, at most every 150 ms.
2. The server route computes the ball's path to the paddle, wall bounces included. It then queries TypeSafe with the `@typesafe-ai/sdk` SDK. The API key never leaves the server.
3. The model picks one of 16 zones, each 50 px wide. The code moves the paddle toward that zone at the same maximum speed as the keyboard. That speed follows the ball's speed.
4. A response that arrives after the ball was lost is ignored.
5. With several balls in play, the code picks the one that will reach the paddle first, and the AI decides where to go to catch it.

The physics stays in the code. Without the computed path, the model picked the right zone for only 5% of descending balls. With it, the model gets it right about 90% of the time, and its target stays within the paddle's reach.

The panel compares every decision with the exact computation. It also shows confidence, latency and token usage.

The decision log lists every response with the ball's position and speed, the chosen zone, the computed zone, confidence and latency. A response is marked as ignored if it arrives after the ball was lost. The export button downloads the last 500 entries as JSON.

- `src/app/api/paddle/route.ts`: server route that asks TypeSafe the question.
- `src/game/ai/pilot.ts`: browser-side pilot, handling request pacing and response freshness.
- `src/game/ai/zones.ts`: zone definitions, shared by the client and the server.
