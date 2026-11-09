# Autonomous PS2 AI Agent Pipeline

An end-to-end autonomous gaming agent architecture for PlayStation 2 emulation, equipped with low-latency window frame capture, virtual controller input injection, real-time broadcast-quality visual telemetry HUD, and modular decision-making powered by **TypeSafe Jev System One**.

---

## 🏗️ Architecture Blueprint

```
+---------------------------------------------------------------------------------+
|                              PS2 Emulator (PCSX2)                               |
|        Video Render Canvas                         Controller Input Port        |
+-------------------------+-----------------------------------------+-------------+
                          | [Low-Latency Capture]                   ^ [Virtual Inputs]
                          v                                         |
+-------------------------------------------------------------------+-------------+
|                            Autonomous Python Agent Core                         |
|                                                                                 |
|   [WindowCapture]  ------>  [Agent Bridge]  ------>  [VirtualPS2Controller]     |
|   - Bounding-box tracker    - TypeSafe Jev System 1   - Win: ViGEmBus (vgamepad)|
|   - Win: bettercam (DXGI)   - Heuristic Vision        - Mac: pynput / Keybinds  |
|   - Mac: mss / Quartz       - Async worker (30-60fps) - Digital & Analog mapping|
|                                     |                                           |
|                                     v                                           |
|                          [VisualTelemetryHUD]                                   |
|                          - Real-time Dual Analog Stick Deflection Vector        |
|                          - PlayStation Face Buttons (Cross, Circle, [], ^)      |
|                          - Triggers (L2/R2) & Bumpers (L1/R1) gauges            |
|                          - Sub-second decision label, confidence bar, & FPS     |
|                          - Direct MP4 recording for TikTok/Reels/YouTube/OBS    |
+---------------------------------------------------------------------------------+
```

---

## ⚡ Quickstart

### 1. Setup Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)
Defaults are pre-configured in `config.py`. To override:
```bash
export TYPESAFE_API_KEY="your_api_key_here"
export TYPESAFE_MODEL="jev-latest"
export EMULATOR_WINDOW_TITLE="PCSX2"
export TARGET_FPS="30"
```

---

## 🎮 Controller Configuration

The pipeline features a **Dual-Mode Controller Engine**:

### On Windows (Native Virtual Gamepad via ViGEmBus)
1. Install the free **[ViGEmBus Driver](https://github.com/nefarius/ViGEmBus/releases)**.
2. In **PCSX2** > **Settings** > **Controllers** > **Controller Port 1**, select **XInput / Xbox 360 Controller**.
3. The controller backend (`vgamepad`) injects kernel-level gamepad signals with 360° analog sticks and pressure-sensitive triggers.

### On macOS (Direct Keyboard Mapping Mode)
In **PCSX2** > **Settings** > **Controllers** > **Controller Port 1**, configure the keyboard bindings to match `config.py`:
- **D-Pad / Left Stick**: `W` (Up), `S` (Down), `A` (Left), `D` (Right)
- **Face Buttons**: `K` (Cross / X), `L` (Circle / O), `J` (Square), `I` (Triangle)
- **Shoulders / Triggers**: `Q` (L1), `E` (R1), `U` (L2), `O` (R2)
- **System**: `Return` (Start), `Tab` (Select)

---

## 🚀 Running the Pipeline

### Mode 1: Interactive Test Drive (Mock PS2 Window)
To test the pipeline immediately without launching PCSX2:

1. In Terminal 1, launch the mock emulator:
   ```bash
   ./.venv/bin/python test_emulator.py
   ```
2. In Terminal 2, launch the AI Agent:
   ```bash
   ./.venv/bin/python main.py --window "Mock PS2"
   ```

### Mode 2: Live Game Emulation (PCSX2)
1. Launch PCSX2 and boot your PS2 ISO game.
2. Run the agent orchestrator:
   ```bash
   ./.venv/bin/python main.py --agent jev --fps 30
   ```

### Mode 3: Record Direct to MP4 for Social Media
Capture gameplay and the live telemetry HUD directly into a 720p/1080p MP4 file ready for editing or social media posting:
```bash
./.venv/bin/python main.py --agent jev --record "ai_agent_gameplay.mp4"
```

---

## 🧩 Project File Structure

| File | Description |
| :--- | :--- |
| `config.py` | Global settings, TypeSafe credentials, window keywords, and keybindings. |
| `capture.py` | Low-latency window capture with dynamic window tracking (`bettercam` / `mss`). |
| `controller.py` | Virtual DualShock 2 controller mapper (`vgamepad` on Win, `pynput` on Mac). |
| `hud.py` | Real-time visual overlay rendering analog stick vectors, buttons, and confidence bar. |
| `agent_bridge.py` | Decision engines: `TypeSafeJevAgent` (System One), `HeuristicVisionAgent`, and `RandomAgent`. |
| `test_emulator.py` | Mock PS2 emulator window for end-to-end verification and testing. |
| `main.py` | Core loop connecting frame capture, inference, controller injection, and HUD. |

---

## 🧠 Plugging in Custom Models (VLM / RL)

To connect your own localized VLM (e.g. Qwen2-VL, Moondream) or Reinforcement Learning agent (e.g., Stable-Baselines3 PPO/DQN), subclass `BaseAgent` in `agent_bridge.py`:

```python
from agent_bridge import BaseAgent
from controller import ControllerState

class CustomRLAgent(BaseAgent):
    def __init__(self, model_weights_path: str):
        # Load your PyTorch / ONNX / TensorRT model
        pass

    def act(self, frame: np.ndarray) -> tuple[ControllerState, str, float, float]:
        # Preprocess frame and run inference
        ctrl = ControllerState()
        ctrl.left_y = 1.0     # Accelerate
        ctrl.cross = True      # Throttle button
        return ctrl, "ACCELERATE", 0.98, 8.5
```
