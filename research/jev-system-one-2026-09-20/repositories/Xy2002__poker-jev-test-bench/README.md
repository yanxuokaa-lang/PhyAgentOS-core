# Jev Test Bench — Texas Hold'em Edition

A live-fire testing playground for [Jev](https://vercel.com/ai-gateway/models/jev) — TypeSafe AI's "System One" evaluation model — served either through the [Vercel AI Gateway](https://vercel.com/docs/ai-gateway) or directly against TypeSafe's official API. The test domain is a full React (CSR) Texas Hold'em game: every betting decision you face is fed to Jev in real time as a typed-questions probe, displayed side-by-side with a rule-based poker coach so machine judgment and classical heuristics can be compared hand by hand.

![React 19](https://img.shields.io/badge/react-19-61dafb)
![Vite 7](https://img.shields.io/badge/vite-7-646cff)
![License](https://img.shields.io/badge/license-MIT-blue)

## Quick Start

```bash
git clone https://github.com/Xy2002/poker-jev-test-bench.git
cd poker-jev-test-bench
npm install

# Development (Vite dev server + Jev proxy)
npm run dev

# Production
npm run build
node serve.mjs        # serves dist/ with strict CSP + Jev proxy → http://127.0.0.1:8364/
```

The game itself is fully offline; the only network call is the opt-in Jev panel.

## Features

**Interactive 4-Player Game**
- Play against 3 AI opponents with adaptive aggression
- Full betting rounds: preflop, flop, turn, river
- Side pot calculation for all-in scenarios
- Dynamic blind escalation (10/20 → 15/30 → 25/50 → 40/80 → 75/150 → 100/200)

**Real-Time Coaching Panel**
- Hand strength meter with 5-tier rating (Weak → Premium)
- Position-aware advice (adjusts for heads-up, 3-handed, full table)
- **Monte Carlo equity engine** — draws random opponent holdings and remaining board cards (13k+ samples/sec) to compute your real equity at every decision point, with sample count and 95% confidence interval; on the river heads-up it enumerates all C(45,2) = 990 opponent holdings exactly
- Draw and out calculations (flush draws, straight draws, combo draws)
- Pot odds analysis arbitrated against simulated equity — call/fold is math, not vibes
- Bluff spot detection: c-bet opportunities, semi-bluff raises, position steals
- Opponent read hints based on bet sizing patterns

**Jev Live Evaluation (the headline feature)**
- Integrates [Jev](https://vercel.com/ai-gateway/models/jev) (`typesafe-ai/jev`) — TypeSafe AI's "System One" evaluation model
- Two API routes, switchable in the panel header:
  - **Direct** — TypeSafe's official API (`api.typesafe.ai`, `ts_` keys, model `jev-latest`); `boolean` questions are translated to TypeSafe's native `noul` type automatically. Get a key at docs.typesafe.ai → Quick Start
  - **Gateway** — [Vercel AI Gateway](https://vercel.com/docs/ai-gateway) (`vck_` keys, model `typesafe-ai/jev`); get one at vercel.com → AI Gateway → API Keys
- Pasting a key auto-selects the matching route (prefix `ts_` → Direct, `vck_` → Gateway); the choice persists in `localStorage`
- Jev is not a chat model: it receives the table state plus typed questions and returns calibrated probabilities, no generated text
- At every decision point it evaluates in parallel: best action (choice), hand strength (score 0–4), whether the villain's last bet is a bluff (boolean), whether calling is profitable (boolean), and — for aggressive actions — how much to raise (choice over min-raise / pot / big / all-in sizing buckets, translated into a dollar amount matching the raise-slider semantics)
- Toggle the **Jev AI** button in the coach panel and paste your key — Direct route takes a TypeSafe key (starts with `ts_`), Gateway route takes an AI Gateway key (starts with `vck_`)
- Results appear as a second opinion alongside the rule-based coach, with per-question probability bars and latency

**Bilingual UI (中英双语)**
- Full Chinese and English localization of every visible string: game messages, all coach sections, history, stats, menus, and the Jev panel
- Toggle with the **中文 / EN** button in the coach header; the choice persists in `localStorage`
- First visit auto-detects the browser language; the engine emits `{key, params}` messages so UI text is resolved at render time
- The state and questions sent to the Jev model stay in English regardless of UI locale — that's model input, not UI copy

**Difficulty Modes**
- **Beginner**: Shows coaching recommendations and bluff-spot guidance
- **Expert**: Hides recommendations — test your own reads

**Stats & History**
- Tracks hands played, win rate, and bluff success
- Collapsible hand history panel (last 20 hands)
- Current blind level display

**Keyboard Controls**
- `F` — Fold · `C` — Check/Call · `R` — Raise · `A` — All-In · `N`/`Enter` — Next hand · `D` — Deal

## Architecture

```
index.html              Vite entry (root div only)
src/
  main.jsx              React bootstrap
  App.jsx               store subscription, keyboard controls, layout
  styles.css            all styling (ported from the original single-file game)
  game/                 framework-free engine — no React imports
    cards.js            deck, shuffle, 7-card hand evaluator
    engine.js           betting flow, side pots, AI opponents, pub/sub store,
                        plus the whitelisted jevSnapshot() network boundary
  coach/                rule-based coach UI
    lib.js              hand tiering, draw detection, cached equity lookup
    monteCarlo.js       Monte Carlo equity simulator (packed-card kernel)
    sections.jsx        coach panel sections
    CoachPanel.jsx      stats, difficulty toggle, history
  components/
    Table.jsx           felt table, seats, cards, showdown overlay
    ActionPanel.jsx     fold/check/call/raise controls with slider
  jev/
    jevClient.js        state builder, typed questions, route + protocol handling
    JevPanel.jsx        route toggle, key management + probability display
serve.mjs               prod static server (strict CSP) + /jev proxies (gateway + TypeSafe direct)
jev-test.mjs            standalone capability test harness for Jev
```

The game engine is a mutable store with a version counter: React subscribes via `useSyncExternalStore`, and every engine mutation calls `notify()`. All poker logic (hand evaluation, side pots, AI) is plain JavaScript with no framework imports, so it stays testable and portable.

## Testing Jev's capabilities

`jev-test.mjs` probes the model directly — boolean, choice, and score question types, parallel multi-question requests, and poker-specific reasoning (hand-strength ordering, draw decisions, fold discipline, bluff reads):

```bash
# Via Vercel AI Gateway (recommended — this is what the game uses)
AI_GATEWAY_API_KEY=vck_xxx node jev-test.mjs

# TypeSafe direct API
TYPESAFE_API_KEY=ts_xxx node jev-test.mjs --direct

# Just the poker tests, custom model ID
AI_GATEWAY_API_KEY=vck_xxx node jev-test.mjs --only poker --model typesafe-ai/jev-latest
```

Each test prints ✓/✗ checks with the returned probabilities plus latency stats. Exit code is non-zero if any hard check fails.

## Security

- The production server (`serve.mjs`) sends a strict CSP: `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'` — no external scripts, styles, or iframes
- The only network destinations are the two same-origin `/jev` proxies (Vercel AI Gateway and TypeSafe's official API), and only when you opt in via the Jev AI toggle
- Your API key is stored in this browser's `localStorage` and forwarded by the proxy verbatim to the selected upstream (`ai-gateway.vercel.sh` or `api.typesafe.ai`) over HTTPS — never logged or stored by the proxy
- `serve.mjs` listens on `127.0.0.1` only
- The game state object `G` (which contains the deck with future cards and opponents' private hole cards) is **never** serialized or sent anywhere. The Jev panel can only transmit the whitelisted snapshot built by `jevSnapshot()` in `engine.js` — an explicit list of what the player can legitimately see: own cards, board, pot, bet sizes, and opponents' public actions. The request body is exactly `{ state, questions }`

## Credits

This project is a heavily reworked derivative of [dnevins/poker](https://github.com/dnevins/poker) — the original single-file vanilla JS Texas Hold'em learning game (MIT). This repository rewrote it as a React CSR app and added the Jev test-bench layer: bilingual UI, Monte Carlo equity engine, the AI Gateway security boundary, and the capability test harness.

## License

MIT. Both copyrights are preserved in [LICENSE](LICENSE):

- Original poker learning game © 2026 dnevins
- React rewrite, Jev integration, i18n, Monte Carlo equity © 2026 Xy2002

MIT permits use, modification, and redistribution — keep both copyright notices intact in copies.
