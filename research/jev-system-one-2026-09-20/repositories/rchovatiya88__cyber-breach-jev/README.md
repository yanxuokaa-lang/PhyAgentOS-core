# Cyber-Breach: The Jev Protocol (3D Tron Infinite)

An infinite 3D arcade cyberpunk arena shooter built with **Three.js** and powered by **Jev**—the sub-100ms "System One" decision model developed by **TypeSafe AI** (released September 2026).

---

## 🌐 3D Infinite Tron Features

- **Boundless Infinite Movement**: The operative is no longer confined to a box. Move limitlessly across a seamless scrolling 3D Tron grid in all directions with dynamic tracking camera.
- **3D Tron Aesthetic**: Classic wireframe visuals, glowing neon cyan/magenta/amber palette, 3D Tron interceptor craft with **persistent luminous light-ribbon trails**, and iconic **3D Tron Recognizers**.
- **Dynamic 3D Camera**: Press `V` to toggle between **3D Chase Cam** (with smooth banking and pitching) and **Tactical Isometric Cam**.
- **Holographic Grid Radar**: Circular 3D radar in the upper right scans 360° for incoming hostile units, Recognizers, and supply drops across the infinite plane.
- **Voxel De-Rezzing Explosions**: Shattering 3D wireframe particles when cybernetic entities are eliminated.

---

## ⚡ What is Jev?

Unlike conventional Large Language Models (LLMs) that output conversational prose or code with token-by-token generation latency, **Jev** is designed as a **System One decision engine**:
- **Zero Hallucinations**: It does not generate text; it returns strictly typed, structured decisions.
- **Calibrated Probabilities (RLCD)**: Trained via *Reinforcement Learning for Calibrated Decisions*, returning statistical confidence alongside every judgment.
- **High-Speed Execution**: Evaluates decision schemas in parallel, enabling real-time loops like the famous DOOM demonstration.

### The Three Jev Primitives Used in the Game

1. **`Choice`**: Multi-option categorization with confidence and probability distribution across candidates (e.g., selecting tactical maneuvers like `flank_left`, `circle_strafe`, `retreat`).
2. **`Score`**: Ordinal evaluation along an ordered rubric (e.g., threat assessment from `minimal` to `fatal`).
3. **`Noul`**: Calibrated boolean probability ($0.0$ to $1.0$) indicating the likelihood of a state (e.g., `is_player_vulnerable`, `trigger_berserk`, `trigger_dash`).

---

## 🎮 Game Architecture & Jev Integration

The game features three distinct systems powered by Jev:

```
                          ┌───────────────────────────┐
                          │   TypeSafe AI Jev Model   │
                          │   (or Local RLCD Engine)  │
                          └─────────────┬─────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   Tactical Enemy AI   │   │  Adaptive AI Director │   │   Autonomous Jev Bot  │
│                       │   │                       │   │   (Doom Bot Mode)     │
│ • Choice: maneuvers   │   │ • Choice: encounters  │   │ • Choice: navigation  │
│ • Score: threat lvl   │   │ • Score: tension      │   │ • Choice: targeting   │
│ • Noul: vulnerability │   │ • Noul: pity aid      │   │ • Noul: fire / blink  │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
```

### 1. Tactical Enemy Brain (`backend/enemy_ai.py`)
- Enemies (Stalkers, EMP Drones, Heavies, Apex Boss) periodically formulate their combat state and query Jev.
- Jev decides:
  - `combat_action`: `Choice` (`flank_left`, `flank_right`, `direct_charge`, `take_cover`, `suppressive_fire`).
  - `threat_assessment`: `Score` (`minimal_threat` $\to$ `fatal_threat`).
  - `is_player_vulnerable`: `Noul` (detects if player is reloading or low on health).
  - `trigger_berserk`: `Noul` (triggers speed and damage overclock).

### 2. Adaptive Encounter Director (`backend/game_director.py`)
- Continuously monitors player health, survival time, kill streak, and battle tempo.
- Jev decides:
  - `director_event`: `Choice` (`tactical_supply_drop`, `swarming_ambush`, `laser_hazard_grid`, `glitch_overdrive`).
  - `pacing_tension`: `Score` (`downtime_calm` $\to$ `apocalyptic_chaos`).
  - `grant_emergency_aid`: `Noul` (airlifts health or shield caches when operative is critical).

### 3. Autonomous Jev Bot ("The Jev Protocol" / Doom Bot Mode) (`backend/bot_pilot.py`)
- Inspired by TypeSafe's DOOM showcase, pressing `P` engages full autopilot!
- Jev runs at 5–10 decisions per second to steer, circle-strafe, avoid incoming projectiles, acquire targets, and trigger emergency blinks.

### 4. Real-Time Telemetry HUD (`frontend/jev_hud.js`)
- Renders the live decision stream on the right side of the screen.
- Visualizes candidate probability bars, confidence ratings, rubric scoring steps, and latency gauges.

---

## 🕹️ Controls

| Key | Action |
| :--- | :--- |
| `W, A, S, D` / Arrows | Move Operative Craft across Infinite Grid |
| `Mouse Aim + Left Click` | 3D Aim and Fire Plasma Blasters |
| `Space` | Quantum Blink / Dash (invulnerability frames & after-images) |
| `V` | **Toggle 3D Camera (Chase Cam / Tactical Isometric)** |
| `P` | **Toggle JEV Autopilot (Doom Bot Mode)** |
| `M` | Toggle Synthwave Music |
| `N` | Toggle Procedural Sound Effects |
| `C` | Toggle Retro CRT Scanlines |
| `Enter` / `Space` | Restart / Rematerialize upon De-Rezzing |

---

## 🚀 Quickstart

### 1. Launch the Server
```bash
./run.sh
```
*(or run `python3 -m backend.app` directly)*

### 2. Open in Browser
Visit **[http://localhost:8000](http://localhost:8000)**.

### 3. (Optional) Using Live TypeSafe AI API
The game runs out of the box with the built-in calibrated local decision engine (zero latency, zero API costs).

To connect directly to live TypeSafe AI servers:
- Set your environment variable:
  ```bash
  export TYPESAFE_API_KEY="ts_live_your_key_here"
  ./run.sh
  ```
- Or click **⚙ JEV CONFIG** in the top bar while playing to enter your key at runtime.

---

## 🧪 Testing & Verification

### 1. Unit Tests
Run the automated test suite verifying Jev schemas, Cua predicate evaluation, and endpoint behavior:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### 2. Autonomous Cua Browser & Jev Build Verification
Integrates **[Cua Driver / Cua Browser](https://github.com/trycua/cua)** with **TypeSafe Jev System One** to autonomously test, inspect, and certify web applications:

```
                      ┌────────────────────────────────────────────────────────┐
                      │              Web Application Under Test                │
                      │             (e.g., http://localhost:8000)             │
                      └───────────────────────────┬────────────────────────────┘
                                                  │
                      ┌───────────────────────────┴────────────────────────────┐
                      │                     CUA BROWSER                        │
                      │  (Cua Driver v0.28.2 · OS Accessibility · Chrome CDP)  │
                      ├────────────────────────────────────────────────────────┤
                      │ • browser_prepare / browser_navigate                   │
                      │ • get_browser_state (semantic_v2 / dom_refs_v1)        │
                      │ • verify_state (deterministic window & DOM predicates) │
                      │ • browser_click / browser_type / browser_pointer       │
                      │ • Visual screenshot & trajectory recording             │
                      └───────────────────────────┬────────────────────────────┘
                                                  │ Observations & Telemetry
                                                  ▼
                      ┌────────────────────────────────────────────────────────┐
                      │              JEV SYSTEM ONE DECISION LAYER             │
                      │        (TypeSafe AI SDK & Calibrated Local Engine)     │
                      ├────────────────────────────────────────────────────────┤
                      │ • Choice: Action selection, failure categorization     │
                      │ • Score: Rubric build health & UX quality assessment   │
                      │ • Noul: Calibrated pass probability & anomaly gate     │
                      └───────────────────────────┬────────────────────────────┘
                                                  │ Structured Verdicts
                                                  ▼
                      ┌────────────────────────────────────────────────────────┐
                      │        Autonomous Test Runner & Triage Reporter        │
                      │ • Smoke verification & DOM hierarchy validation        │
                      │ • Interactive flow simulation & telemetry analysis     │
                      │ • Visual diff & state predicate verification           │
                      │ • Markdown & JSON build verification artifacts         │
                      └────────────────────────────────────────────────────────┘
```

```bash
# Run full verification pipeline against the live application (headed or headless)
python3 -m testing.verify_app --url http://localhost:8000 --cdp-port 9225 --headed
```

#### What the Verification Pipeline Does:
1. **API & Connectivity**: Validates backend endpoints and Jev service availability.
2. **Cua Semantic Hierarchy**: Discovers and indexes interactive buttons, links, inputs, and canvases (`semantic_v2`).
3. **Interactive UI Flow Simulation**: Triggers user journeys (camera toggle, autopilot engage, configuration modal) and measures real-time DOM/engine reactions.
4. **WebGL & Telemetry Inspection**: Probes 3D Three.js scene object count, render context, flight speed, and frame stability.
5. **Deterministic State Predicates**: Evaluates Cua `verify_state` predicates on window bounds and element states.
6. **Action Trajectory Recording**: Records full Cua interaction trajectories (`cua_action_trajectory.json`) for benchmark and reproducibility.
7. **Jev System One Build Gate**: Formulates compact evidence into Jev schemas:
   - **`build_health_score` (`Score`)**: Rubric evaluation (`critical_breakage` $\to$ `production_verified`).
   - **`is_build_ready` (`Noul`)**: Calibrated boolean probability ($0.0 \to 1.0$) for release readiness.
   - **`failure_classification` (`Choice`)**: Identifies root cause if anomalies occur (`clean_pass`, `canvas_webgl_failure`, `missing_ui_controls`, `api_backend_offline`, `performance_frame_drop`).
   - **`recommended_action` (`Choice`)**: Prescribes immediate workflow step (`approve_and_ship`, `retest_interactive_suite`, `inspect_webgl_shaders`, `inspect_api_server`, `halt_and_block_ci`).
8. **Artifact Generation**: Outputs structured JSON (`verification_report.json`), Markdown summary (`verification_report.md`), and visual screenshots (`cua_verification_evidence.png`).
