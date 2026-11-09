# 🚀 JevSpace

**A DarkOrbit-style space game piloted by [Jev](https://typesafe.ai/) — TypeSafe's System One model.**

A Three.js prototype where an AI model flies your ship: mining ore from asteroids,
hunting hostile bots, and completing a mission **you define** — while every rule of
the world stays in deterministic code.

<p align="center">
  <img src="docs/screenshot-setup.png" width="49%" alt="Mission setup" />
  <img src="docs/screenshot-win.png" width="49%" alt="Mission complete" />
</p>

## The idea

Jev is not a chatbot. It is a **System One** model: you send it program state plus
typed questions, and it returns **constrained, typed answers with probabilities** —
not free-form text. That makes it a great fit for *game AI pilots*: fast, bounded,
probabilistic decisions that your code can consume directly.

JevSpace follows the canonical **System One split**:

| Layer | Owner | Responsibilities |
|---|---|---|
| **World** | Deterministic code (client JS) | Physics, steering, mining, lasers, damage, respawns, collision — bugs and exploits are impossible by construction |
| **Pilot** | Jev (server round-trip) | Which target to pursue (`choice`), how dangerous the situation is (`noul`) |

The game can never break because of the model: Jev only ever picks from a
candidate list the engine computed, and if the API is unreachable, a heuristic in
code takes over and the ship keeps flying.

## How Jev pilots the ship

Every 3 seconds the game builds a **candidate list** from live world state —
each asteroid (distance, remaining ore, how much the mission still needs) and each
bot (distance, hull, threat) — and sends it as structured `state` with two typed
questions:

- **`target` — `choice`** *"Which target next?"*
  Jev returns the selected candidate **plus the full probability distribution**
  (rendered live in the JEV PILOT panel — you can literally watch it reason).
  Strategy is encoded in the question: mine ore the mission still needs, attack
  when the hull is healthy, flee when it isn't.
- **`danger` — `noul`** *"Is the ship about to die?"*
  A 0–1 probability of immediate destruction. Shown as the danger gauge; the
  engine also hard-codes an emergency-flee override that the model cannot talk
  itself out of.

```jsonc
// POST /api/decide — one request, two independent judgments (run in parallel)
{
  "state": {
    "ship": { "hull_hp": 74, "cargo": { "uridium": 3, "pentium": 9 },
              "mission_remaining": { "uridium": 7, "pentium": 11, "kills": 1 } },
    "candidates": {
      "aXk2f": { "kind": "asteroid", "description": "Mine pentium asteroid — distance 14, 12 ore left, mission needs 11 more pentium" },
      "b8s1q": { "kind": "bot", "description": "Attack hostile bot — distance 22, bot hp 28/40" },
      "flee":  { "kind": "flee", "description": "Flee to safety — choose if hull hp (74) is low and bots are close" }
    }
  },
  "model": "jev-latest",
  "questions": {
    "target": { "type": "choice", "instructions": "You are the pilot. Choose the next target…", "criteria": { "…": "…" } },
    "danger": { "type": "noul",   "instructions": "Is the ship in immediate danger…?", "criteria": { "true": "…", "false": "…" } }
  }
}
```

```jsonc
// Response — typed, constrained, probabilistic
{
  "target": "aXk2f",
  "probabilities": { "aXk2f": 0.71, "b8s1q": 0.27, "flee": 0.02 },
  "confidence": 0.83,
  "danger": 0.11
}
```

In live testing Jev completed missions like *10 Uridium + 20 Pentium + 2 bot kills*
end-to-end — switching between mining and hunting as bots closed in, and finishing
with hull to spare.

## Features

- 🎮 **User-defined missions** — set your own goals with sliders: Uridium target,
  Pentium target, bot kills. The engine scales the world to your mission.
- 🤖 **Live AI telemetry** — watch Jev's move probabilities, confidence and danger
  gauge update in real time while it flies.
- 🧱 **Deterministic core** — all rules live in code; the model picks among
  engine-validated options only.
- 🛟 **Graceful degradation** — API down? A heuristic pilot takes over, the game
  never stops.
- 🌌 **Three.js world** — starfield, glowing ships, ore asteroids, laser bolts,
  dynamic chase camera.

## Run it

```bash
git clone https://github.com/imserhatdemir/jevspace
cd jevspace

python3 -m venv .venv && source .venv/bin/activate
pip install flask requests

export TYPESAFE_API_KEY="your-key"   # get one at https://console.typesafe.ai/keys
python server.py                     # → http://127.0.0.1:5175
```

Requires a TypeSafe API key (`TYPESAFE_API_KEY`). The key never leaves the server —
the browser only talks to your local Flask backend.

## Project layout

```
├── server.py          # Flask: /api/decide → builds state + questions, calls Jev
├── jev.py             # Minimal System One HTTP client (retries with backoff)
└── static/index.html  # Three.js world, game engine, HUD and Jev telemetry panel
```

## Caveats

Schema-valid output is not the same as a correct decision. Jev is trained for
calibrated judgment, but thresholds (when to flee, when to fight) should be
evaluated on your own scenarios. JevSpace treats every model answer as *advice to
a deterministic engine* — the same principle you want in any production system.

## Built with

- [Jev / TypeSafe System One](https://docs.typesafe.ai/) — the pilot
- [Three.js](https://threejs.org/) — the universe
- Flask — the bridge

---

*Part of exploring what "AI as a decision primitive" looks like in games. If you
build something similar, I'd love to see it.*
