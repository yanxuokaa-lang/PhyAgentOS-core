# openjev Tetris: Zero-Shot NLI Game Controller

Wiring [`AlexWortega/openjev`](https://huggingface.co/AlexWortega/openjev) (`Qwen3.5-4B` trained as an NLI cross-encoder) to play Tetris locally.

---

## 1. How it Works

`openjev` is a sequence classification cross-encoder that takes a `(premise, hypothesis)` pair and outputs probabilities for `[contradiction, entailment, neutral]`.

Following the same zero-shot formulation demonstrated in `openjev`'s Flappy Bird and Doom benchmarks:
1. **State Simulation**: For the active tetromino, we simulate every legal placement `(rotation, column)` dropped to the bottom.
2. **Outcome Premise**: The simulated board properties (cleared lines, landing height, holes created, bumpiness, max height) are rendered as a factual premise describing the result of the move.
3. **Desirability Hypothesis**: A normative or factual statement about game health (e.g. *"The piece is placed cleanly and safely, clearing lines without creating trapped holes under the stack."*).
4. **NLI Scoring**: `openjev` predicts `P(entailment)` and `P(contradiction)`. Clean moves that clear lines and create 0 holes are strongly entailed; moves that bury empty spaces or create towers are contradicted.
5. **Decision**: The agent selects the move with the highest net entailment score:
   $$\arg\max_{m} \left( P(\text{entailment}) - P(\text{contradiction}) \right)$$

---

## 2. Quickstart

### Run with the openjev Zero-Shot Controller
```bash
# ANSI animated terminal game
./run_tetris.sh play --render --delay 0.05

# Or headless evaluation over N episodes
./run_tetris.sh play --episodes 5 --max-steps 500
```

### Run the Web Visualizer
```bash
./run_tetris.sh web 8088
# Open http://localhost:8088 in your browser
```
Features:
- Live 10x20 dark-mode board with color-coded tetrominoes.
- Real-time NLI probability bars (Entailment / Contradiction / Neutral).
- Candidate moves breakdown with exact Premise and Hypothesis texts.
- Play / Pause / Step controls.

### Compare Against the Heuristic Oracle (Pierre Dellacherie)
```bash
./run_tetris.sh oracle --render
```

### Play with SalesRLAgent (Reinforcement Learning Sales Conversion Model)
Uses [`DeepMostInnovations/sales-conversion-model-reinf-learning`](https://huggingface.co/DeepMostInnovations/sales-conversion-model-reinf-learning) (arXiv:2503.23303). The agent treats the Tetris board as the customer, candidate moves as value pitches, and chooses the placement that maximizes deal conversion probability:
```bash
# Terminal execution with live deal closing probability telemetry
./run_tetris.sh sales-rl --render

# Co-op Web UI with real-time neural activation graph and spectrogram
./run_tetris.sh coop 8088 --with-sales-rl --with-heuristic
```

### Play with kev-0.5b (Jev Decision Model Reconstruction)
Uses [`jaredpalmer/kev-0.5b`](https://huggingface.co/jaredpalmer/kev-0.5b). A non-autoregressive decision model built on `Qwen2.5-0.5B` with a LoRA adapter and pointer readout head. All candidate placements are evaluated in a single forward pass with block-causal branch masking (~1.3s/move on CPU, ~18x faster than openjev 4B):
```bash
# Terminal execution with live ANSI board
./run_tetris.sh kev --render

# Web co-op UI with live Decision Confidence and neural activations
./run_tetris.sh coop 8088 --with-kev --with-heuristic
```

### Play with Laya (RLCD Decision Model)
Uses [`convaiinnovations/laya`](https://huggingface.co/convaiinnovations/laya). A non-autoregressive System 1 decision model based on `ModernBERT-large` (395M) and a 2-layer transformer decision head trained with Reinforcement Learning for Calibrated Decisions (RLCD). Evaluates option markers and predicts escalation/act probability (~800ms/move on CPU):
```bash
# Terminal execution with live ANSI board
./run_tetris.sh laya --render

# Web co-op UI with act probability and calibrated confidence
./run_tetris.sh coop 8088 --with-laya --with-kev --with-heuristic
```

### Train / Run Latent MLP
```bash
./run_tetris.sh train-mlp --episodes 15
```

### Fine-tune RoBERTa for Tetris

The GPU RoBERTa server can provide pooled embeddings while a local listwise ranking
head learns from a one-piece lookahead teacher. The transformer remains frozen, so this
fits quickly without requiring a training-capable Vulkan backend:

```bash
./run_tetris.sh vulkan 8088 --with-vulkan
.venv/bin/python finetune_roberta_tetris.py --episodes 15 --max-steps 150 \
  --out roberta_tetris_head
./run_tetris.sh versus 8088 --with-vulkan --policy-head roberta_tetris_head
```

`qualitative` remains the best measured zero-shot prompt. The trainer uses
`qualitative_fine`, which includes distinct human-readable values and the placement
identity so different moves do not receive the same embedding. A positive `--top-k`
uses the cheap board filter before model scoring; zero evaluates every legal placement.

---

## 5. Performance Optimization & Real Tetris Physics (BRRRR Pass)

The engine features a complete bitboard-accelerated physics core with official modern Tetris mechanics:

### 1. Bitboard Acceleration (`tetris_engine.py`)
- 10-bit integer rows with precomputed bitmask lookups for $O(1)$ collision checks (3.63M checks/sec).
- Vectorized feature extraction via bitwise operations and `POPCNT` (`int.bit_count()`).
- High-throughput placement simulation: 115k drops/sec.
- End-to-end 500-piece simulation throughput increased from ~180 pieces/s to **878.1 pieces/s (4.87x speedup)**.

### 2. Full Super Rotation System (SRS)
- 4 rotation states: `0` (spawn), `R` (clockwise), `2` (180°), `L` (counter-clockwise).
- Center-of-rotation bounding boxes: 3x3 (J, L, S, T, Z), 4x4 (I), 2x2 (O).
- Official 5-test kick translation tables for JLSTZ and I pieces.
- Wall kicks, floor kicks, and block climbing.

### 3. Lock-Delay State Machine
- Grounded state detection (`collides(piece, rot, x, y + 1)`).
- 0.5s lock timer with up to 15 lateral movement / rotation resets.
- Soft drop increases fall speed without instant locking.
- Hard drop instantly locks and bypasses lock delay.

### 4. Modern HOLD Functionality
- Single-hold queue with piece swapping and next-piece spawn.
- Hold lockout resets upon locking into the matrix.
- Full state exposure for human UI and AI agents.

### 5. Reproducible Benchmark Harness
```bash
.venv/bin/python benchmark_tetris.py
.venv/bin/python test_tetris_engine.py
```

| Subsystem | Baseline Metric | Optimized (Bitboard) | Speedup Factor |
|---|---|---|---|
| Collision Check | 1,188,949 checks/s (841.1 ns) | **3,630,402 checks/s (275.5 ns)** | **3.05x** |
| Feature Extraction | 14,787 calls/s (67.6 µs) | **31,794 calls/s (31.5 µs)** | **2.15x** |
| Hard-Drop Simulation | 54,922 drops/s (18.2 µs) | **115,457 drops/s (8.7 µs)** | **2.10x** |
| SRS Kick Resolution | — | **877,612 tests/s (1139.5 ns)** | **Real-Time** |
| End-to-End Game Loop | 180.4 pieces/s | **878.1 pieces/s** | **4.87x** |

---

## 6. mmastrac/djev-spark DiffusionGemma System 1

Integration with [`mmastrac/djev-spark`](https://github.com/mmastrac/diffgemma), Google's DiffusionGemma adapted for non-autoregressive parallel canvas denoising:
- **Architecture Analysis:** Documented in [`djev_spark_architecture.md`](djev_spark_architecture.md).
- **Transport Adapter:** Connects to remote DGX Spark clusters (`POST /v1/systemone`) when available.
- **Local Surrogate:** Simulates multi-step Langevin reverse diffusion across candidate placements with real-time confidence calibration and act vs escalate probability:
```bash
./run_tetris.sh spark --render
./run_tetris.sh coop 8088 --with-spark --with-kev --with-laya --with-heuristic
```
