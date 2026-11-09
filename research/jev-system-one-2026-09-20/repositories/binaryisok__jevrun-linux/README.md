# jevrun

A Linux port of [tiptour-macos](https://github.com/milind-soni/tiptour-macos)' JEV
mode. Type a task and an agent drives the computer: it detects real on-screen
controls locally, asks the **Jev** decision model (TypeSafe AI) which one to act
on, clicks it, validates the result, and repeats until the task is done.

Jev never sees pixels — only candidate metadata (label, source, centre). Actions
only ever target detected candidates, never invented coordinates.

## Install

```sh
sudo apt install tesseract-ocr at-spi2-core
cargo build --release
```

## Usage

```sh
# Real decisions via TypeSafe Jev
TYPESAFE_API_KEY=... jevrun --task "open firefox"

# Offline mock engine (deterministic, no network) — planned, see status below
jevrun --mock --task "open firefox"
```

The loop stops when Jev reports the task done (probability ≥ 0.70), Jev picks the
`__none__` "nothing on screen advances this" option, or after 12 steps.

> Note: the CLI (`jevrun --task/--mock`) is Phase 5. Until then, the decision
> layer is exercised through unit tests: `cargo test -p jevrun-jev`.

## Architecture

- **`jevrun-jev`** — Pure Jev grounding. Converts detections into one Jev request
  (state + done/absent/pick/kind questions), parses the answer back into a
  `JevDecision`, enforces thresholds and the `__none__` escape hatch. Ships a
  `DecisionEngine` trait, a real `JevClient` (`POST
  https://api.typesafe.ai/v1/systemone`, Bearer `TYPESAFE_API_KEY`), and a
  deterministic `MockEngine` for offline tests. No platform types; fully unit-tested.
- **`jevrun-perception`** — Detects actionable UI candidates locally. *Planned:*
  AT-SPI2 tree walker via D-Bus, `xcap` screenshots with perceptual hashing for
  change validation, tesseract OCR fallback for canvas-drawn UIs, multi-source
  merge/dedupe.
- **`jevrun-actions`** — Executes clicks on detected candidates. *Planned:* X11
  XTest via `x11rb`/`enigo` (move, click, double-click, right-click, type text,
  hotkeys). Rejects any target not backed by a detection — the no-invented-coordinates
  invariant.
- **`jevrun-core`** — The `JevPointerLoop`: perceive → decide → execute →
  validate, append history, repeat within a 12-step budget. *Planned:*
  structured per-step snapshots (probabilities, timings) for the UI.
- **`jevrun`** — CLI binary. *Planned:* `--task` input, `--mock` mode, global
  hotkey (Ctrl+K) + input UI (ratatui TUI first, tray/egui later), keyring API-key storage.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the loop data flow, grounding details,
and safety invariants. See [RESEARCH_PLAN.md](RESEARCH_PLAN.md) for the original
research and platform mapping.

## Wayland

X11-first. Screenshots (`xcap`) and input injection (`enigo`, X11 XTest) target
X11; under plain Xvfb this is the validated path. On Wayland, screenshot needs
the desktop portal and input injection needs `ydotool`/`wtype` — both are future
work (see RESEARCH_PLAN.md stretch goals).

## Permissions

Two privileges are required and must be granted to the user running jevrun:

- **Accessibility (AT-SPI bus access)** — to enumerate on-screen UI elements.
  Typically: run within the same session so the AT-SPI registry is reachable;
  under Xvfb, start `at-spi-bus-launcher` / `at-spi2-registryd`.
- **Input emulation** — XTest on X11 allows synthetic clicks and key events.
  Wayland compositors block this by default (hence ydotool's uinput requirement).

Screenshots never leave the machine; only task text, candidate labels/positions,
and action history are sent to TypeSafe.

## Learned UI detector (optional)

`jevrun-perception` ships a YOLOv8 interactable-icon detector — OmniParser v2's
`icon_detect` exported to ONNX — behind the `detector` cargo feature (off by
default). It finds *where* clickable things are; tesseract supplies *what*
they say, so each box is labeled from the OCR words inside it (`"icon"` when
the box holds no text).

Setup (one time):

```sh
pip install onnxruntime numpy pillow
mkdir -p ~/.local/share/jevrun/models
curl -sSL -o ~/.local/share/jevrun/models/omniparser_icon_detect.onnx \
  https://huggingface.co/onnx-community/OmniParser-v2.0_icon_detect/resolve/main/onnx/model.onnx
```

Build and test with the feature on:

```sh
cargo test -p jevrun-perception --features detector
```

Notes:

- The `ort` Rust bindings are intentionally not used — crates.io is unreachable
  from the build environment, so inference runs in `crates/jevrun-perception/python/detect.py`
  via onnxruntime (same subprocess pattern as tesseract OCR). All postprocessing
  (letterbox denormalization, NMS, label assignment) is Rust and unit-tested.
- Model: `onnx-community/OmniParser-v2.0_icon_detect` (`onnx/model.onnx`, 77 MB,
  640×640 input, AGPL-3.0). ~1 s inference on CPU for a 1280×800 screenshot.
- Weights are never committed to git; they live in `~/.local/share/jevrun/models/`.
  `OmniParserDetector::fetch_model()` downloads them on demand.
- Overrides: `JEVRUN_DETECTOR_MODEL`, `JEVRUN_DETECTOR_SCRIPT`,
  `JEVRUN_DETECTOR_PYTHON` env vars.

## Project status

| Phase | Work | Status |
|---|---|---|
| 0 | Research & stack decision | ✅ done ([RESEARCH_PLAN.md](RESEARCH_PLAN.md)) |
| 1 | Scaffold workspace + pure Jev core | ✅ done (`jevrun-jev` tested) |
| 2 | Linux perception (AT-SPI, screenshot, OCR) | planned |
| 3 | Action executor with validation | planned |
| 4 | JevPointerLoop agent loop | planned |
| 5 | Hotkey + input UI | planned |
| 6 | Integration run & evaluation (Xvfb) | planned |
| 7 | Docs & release | in progress |
