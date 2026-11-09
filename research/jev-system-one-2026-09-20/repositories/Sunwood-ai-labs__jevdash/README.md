<div align="center">
  <img src="assets/icon.svg" alt="JevDash Logo" width="160">
  <h1>JevDash: System One</h1>
  <p><strong>100% Clean-Room, Copyright-Free 2D Autonomous AI Platformer Benchmark (60 FPS)</strong></p>

  <p>
    <a href="https://github.com/Sunwood-ai-labs/jevdash/actions/workflows/ci.yml">
      <img src="https://img.shields.io/badge/CI-Passing-34d399?logo=githubactions&logoColor=white" alt="CI Status">
    </a>
    <a href="https://sunwood-ai-labs.github.io/jevdash/">
      <img src="https://img.shields.io/badge/Docs-VitePress-c084fc?logo=vitepress&logoColor=white" alt="Documentation">
    </a>
    <img src="https://img.shields.io/badge/Physics-60_FPS_Deterministic-38bdf8?logo=python&logoColor=white" alt="60 FPS Physics">
    <img src="https://img.shields.io/badge/Model-TypeSafe_Jev-fbbf24" alt="TypeSafe Jev">
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-slate" alt="License: MIT">
    </a>
  </p>

  <p>
    <a href="README.md">
      <img src="https://img.shields.io/badge/Language-English-blue.svg" alt="English">
    </a>
    <a href="README.ja.md">
      <img src="https://img.shields.io/badge/Language-日本語-lightgrey.svg" alt="日本語">
    </a>
  </p>
</div>

---

<p align="center">
  <img src="assets/gameplay.gif" alt="JevDash Live Gameplay" width="100%">
</p>

> **JevDash: System One** is a 100% clean-room, copyright-free 2D side-scrolling platformer designed specifically for testing, benchmarking, and demonstrating **TypeSafe AI's Jev** model in real-time control scenarios at 60 FPS. It completely eliminates all copyright and ROM risks associated with commercial games like `gym-super-mario-bros`.

---

## 🌟 Key Features

1. **🛡️ 100% Clean-Room Architecture**:
   - Built entirely from scratch with custom physics, procedural levels, and programmatic cyber-minimalist graphics. Free from proprietary game ROMs or commercial assets.
2. **⚡ Live TypeSafe Jev Integration (Vercel Free Tier)**:
   - Connects directly to the real `typesafe-ai/jev` model via Vercel AI Gateway's free tier (Hobby plan). Experience real-time physical control and benchmarking without costly GPU servers or paid enterprise API subscriptions. Supports sub-frame asynchronous decision pipelines so network latency never stutters the 60 FPS physics loop.
3. **🎥 Continuous MP4 Video Recording**:
   - Integrated FFmpeg pipeline captures every frame into a crisp 1280×720 @ 60 FPS H.264 video (`.mp4`) automatically.
4. **🚀 Zero-Key Ultra-Fast Mock Engine**:
   - Works immediately out of the box without any API key. Includes an analytical decision engine matching Jev's output format with a 100% stage-clear rate.
5. **📊 Apple HIG / Keynote Style HUD**:
   - Real-time display showing Choice probability distribution bar charts, Danger Score (1–10), inference latency counter, and 7×11 ASCII spatial radar.
6. **🎮 Seamless AI & Human Control**:
   - Play manually with smooth keyboard controls, or toggle instant AI autopilot at any moment with the `Tab` key.

---

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                   Pygame 2D Engine (60 FPS)                 │
│        Player velocity, jump arc, stomp & terrain physics   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Every 8 frames (~133ms)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Telemetry Extractor (Pydantic)              │
│     Coordinates, velocities, time-to-collision, pit horizons │
└──────────────────────────────┬──────────────────────────────┘
                               │ Structured JSON (JevObservation)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Decision Layer (Live Jev / Mock)              │
│   ・Choice  : Discrete action macro & probability logits    │
│   ・Boolean : Critical jump urgency                         │
│   ・Score   : Immediate physical danger (1-10)              │
└──────────────────────────────┬──────────────────────────────┘
                               │ Committed action (e.g. right_run_jump)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            HUD Dashboard (Keynote Style Live View)          │
│       Probability bars, latency timer, danger meter, radar  │
└─────────────────────────────────────────────────────────────┘
```

![JevDash Split-Screen Gameplay](assets/gameplay_screenshot.png)

---

## 📦 Quick Start (Powered by `uv`)

This project is managed with the ultra-fast Python package manager [`uv`](https://docs.astral.sh/uv/).

```powershell
# 1. Clone repository
git clone https://github.com/Sunwood-ai-labs/jevdash.git
cd jevdash

# 2. Sync virtual environment and dependencies
uv sync --extra dev

# 3. Launch interactive game!
# (A) Play manually with keyboard (Tab to toggle AI Autopilot)
uv run jevdash play --mode human

# (B) Run with built-in simulated AI (No API key required)
uv run jevdash play --mode mock

# (C) Run with live Jev via Vercel AI Gateway
# Copy .env.example to .env and set your AI_GATEWAY_API_KEY first:
uv run jevdash play --mode live --record jevdash_live.mp4
```

---

## 🕹️ Controls

| Action | Keys | Description |
| :--- | :--- | :--- |
| **Move** | `←` / `→` or `A` / `D` | Walk / steer horizontally |
| **Dash** | `Shift` (Hold) | Sprint at top dash speed |
| **Jump** | `Space` or `W` / `↑` | Jump (hold for maximum leap height) |
| **Enemy Stomp**| Land on enemy top | Defeat enemy and bounce upwards |
| **Toggle Autopilot**| `Tab` | **Switch between AI and Manual control instantly** |
| **Restart** | `R` | Reset level to starting position |
| **Quit** | `Q` or `Esc` | Exit game cleanly |

---

## 🚀 CLI Commands

```powershell
# Interactive gameplay with live HUD and MP4 recording
uv run jevdash play --mode live --record jevdash_live.mp4

# Inspect canonical JSON telemetry sent to Jev without opening a window
uv run jevdash state-demo

# Fast headless benchmark (1,000+ frames in 0.1s)
uv run jevdash benchmark --episodes 5
```

---

## 🧪 Automated Testing

```powershell
uv run pytest -v
```

All 13 unit tests covering physics collision, stomp dynamics, telemetry extraction, Vercel AI Gateway connectivity, and FFmpeg video recording are verified automatically.

---

## 📚 Documentation

- English Documentation: [https://sunwood-ai-labs.github.io/jevdash/](https://sunwood-ai-labs.github.io/jevdash/)
- Japanese Documentation: [https://sunwood-ai-labs.github.io/jevdash/ja/](https://sunwood-ai-labs.github.io/jevdash/ja/)

---

## 📄 License

[MIT License](LICENSE) - Free for commercial, personal, and research use.
