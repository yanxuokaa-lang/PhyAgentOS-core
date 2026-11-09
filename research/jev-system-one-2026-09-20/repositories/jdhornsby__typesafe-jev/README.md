# Jev exploration

## Setup

```
uv sync
cp .env.sample .env   # add TYPESAFE_API_KEY   (needs the stockfish binary: brew install stockfish)
```

## Jev plays chess

Jev plays chess against stockfish.

### Run

```
uv run jev-plays-chess --state san           --opponent stockfish --stockfish-option UCI_LimitStrength=true --stockfish-option UCI_Elo=1320 --max-plies 30 --run-id char-san
uv run jev-plays-chess --state ascii         --opponent stockfish --stockfish-option UCI_LimitStrength=true --stockfish-option UCI_Elo=1320 --max-plies 30 --run-id char-ascii
uv run jev-plays-chess --state fen           --opponent stockfish --stockfish-option UCI_LimitStrength=true --stockfish-option UCI_Elo=1320 --max-plies 30 --run-id char-fen
uv run jev-plays-chess --state pgn_full      --opponent stockfish --stockfish-option UCI_LimitStrength=true --stockfish-option UCI_Elo=1320 --max-plies 30 --run-id char-pgn_full
uv run jev-plays-chess --state pgn_windowed  --opponent stockfish --stockfish-option UCI_LimitStrength=true --stockfish-option UCI_Elo=1320 --max-plies 30 --run-id char-pgn_windowed
uv run jev-plays-chess --state prose_1       --opponent stockfish --stockfish-option UCI_LimitStrength=true --stockfish-option UCI_Elo=1320 --max-plies 30 --run-id char-prose_1
uv run jev-plays-chess --state json_1        --opponent stockfish --stockfish-option UCI_LimitStrength=true --stockfish-option UCI_Elo=1320 --max-plies 30 --run-id char-json_1
```

### Results

Jev per-move confidence, one 30-ply game each vs Stockfish (UCI_Elo 1320):

| state | moves | mean | median | min | max |
|---|--:|--:|--:|--:|--:|
| san | 12 | 0.25 | 0.23 | 0.06 | 1.00 |
| ascii | 13 | 0.18 | 0.07 | 0.04 | 1.00 |
| fen | 15 | 0.18 | 0.14 | 0.03 | 0.57 |
| pgn_full | 15 | 0.19 | 0.10 | 0.05 | 0.56 |
| pgn_windowed | 15 | 0.22 | 0.20 | 0.04 | 0.55 |
| prose_1 | 15 | 0.29 | 0.30 | 0.08 | 0.54 |
| json_1 | 15 | 0.26 | 0.23 | 0.08 | 0.79 |

## Jev's world knowledge

Test Jev's general world knowledge by running through the [MMLU](https://huggingface.co/datasets/cais/mmlu) dataset.

### Run

```
uv run jev-knows --run-id mmlu-full --concurrency 12
```

### Results

It took 4:35 to run through the full 14k questions at concurrency level 12.

| category | accuracy | n |
|---|--:|--:|
| STEM | 94.7% | 3014 |
| Social sciences | 93.3% | 3074 |
| Other (business, health, misc.) | 91.7% | 3241 |
| Humanities | 88.4% | 4704 |

| category | subject | n | accuracy | confidence when correct | confidence when wrong |
|---|---|--:|--:|--:|--:|
| STEM | college_physics | 102 | 99% | 0.97 | 0.93 |
| STEM | college_biology | 144 | 99% | 0.99 | 0.89 |
| STEM | college_computer_science | 100 | 98% | 0.94 | 0.64 |
| STEM | high_school_computer_science | 100 | 98% | 0.97 | 0.91 |
| STEM | elementary_mathematics | 377 | 97% | 0.97 | 0.79 |
| STEM | college_mathematics | 100 | 97% | 0.93 | 0.75 |
| STEM | astronomy | 152 | 97% | 0.98 | 0.87 |
| STEM | abstract_algebra | 100 | 96% | 0.95 | 0.94 |
| STEM | high_school_chemistry | 202 | 96% | 0.95 | 0.72 |
| STEM | high_school_biology | 310 | 95% | 0.98 | 0.89 |
| STEM | conceptual_physics | 235 | 95% | 0.95 | 0.71 |
| STEM | high_school_mathematics | 270 | 95% | 0.88 | 0.46 |
| STEM | high_school_physics | 150 | 94% | 0.96 | 0.70 |
| STEM | high_school_statistics | 216 | 94% | 0.93 | 0.72 |
| STEM | computer_security | 100 | 91% | 0.95 | 0.71 |
| STEM | machine_learning | 112 | 90% | 0.93 | 0.70 |
| STEM | electrical_engineering | 144 | 89% | 0.94 | 0.65 |
| STEM | college_chemistry | 100 | 75% | 0.95 | 0.67 |
| Social sciences | high_school_microeconomics | 238 | 99% | 0.98 | 0.47 |
| Social sciences | high_school_government_and_politics | 193 | 98% | 0.99 | 0.55 |
| Social sciences | high_school_psychology | 545 | 97% | 0.98 | 0.71 |
| Social sciences | us_foreign_policy | 100 | 96% | 0.95 | 0.51 |
| Social sciences | high_school_macroeconomics | 389 | 95% | 0.96 | 0.80 |
| Social sciences | high_school_geography | 198 | 94% | 0.97 | 0.87 |
| Social sciences | sociology | 200 | 92% | 0.97 | 0.73 |
| Social sciences | professional_psychology | 612 | 92% | 0.95 | 0.70 |
| Social sciences | human_sexuality | 131 | 92% | 0.92 | 0.57 |
| Social sciences | econometrics | 114 | 86% | 0.94 | 0.70 |
| Social sciences | security_studies | 245 | 84% | 0.86 | 0.65 |
| Social sciences | public_relations | 109 | 81% | 0.90 | 0.62 |
| Other | medical_genetics | 100 | 100% | 0.98 | - |
| Other | miscellaneous | 783 | 97% | 0.97 | 0.69 |
| Other | professional_medicine | 272 | 97% | 0.98 | 0.77 |
| Other | marketing | 234 | 97% | 0.96 | 0.51 |
| Other | clinical_knowledge | 265 | 95% | 0.96 | 0.62 |
| Other | professional_accounting | 282 | 95% | 0.92 | 0.51 |
| Other | nutrition | 306 | 94% | 0.94 | 0.74 |
| Other | management | 103 | 93% | 0.95 | 0.71 |
| Other | anatomy | 135 | 93% | 0.96 | 0.84 |
| Other | college_medicine | 173 | 89% | 0.95 | 0.71 |
| Other | human_aging | 223 | 84% | 0.92 | 0.70 |
| Other | business_ethics | 99 | 84% | 0.93 | 0.39 |
| Other | global_facts | 100 | 74% | 0.81 | 0.60 |
| Other | virology | 166 | 56% | 0.92 | 0.87 |
| Humanities | formal_logic | 126 | 98% | 0.93 | 0.76 |
| Humanities | high_school_world_history | 237 | 96% | 0.98 | 0.60 |
| Humanities | high_school_us_history | 204 | 95% | 0.98 | 0.74 |
| Humanities | world_religions | 171 | 94% | 0.96 | 0.73 |
| Humanities | international_law | 120 | 93% | 0.97 | 0.66 |
| Humanities | prehistory | 324 | 93% | 0.94 | 0.62 |
| Humanities | logical_fallacies | 163 | 93% | 0.96 | 0.76 |
| Humanities | philosophy | 311 | 93% | 0.92 | 0.64 |
| Humanities | jurisprudence | 108 | 92% | 0.96 | 0.70 |
| Humanities | high_school_european_history | 165 | 91% | 0.97 | 0.84 |
| Humanities | moral_disputes | 346 | 85% | 0.91 | 0.71 |
| Humanities | professional_law | 1534 | 85% | 0.85 | 0.64 |
| Humanities | moral_scenarios | 895 | 84% | 0.86 | 0.60 |

## Prompt routing

Route customer queries to intents using [banking77](https://huggingface.co/datasets/mteb/banking77).

### Run

```
uv run jev-routes --run-id routing-full --concurrency 12
```

### Results

It took 0:58 to route all 3076 queries at concurrency level 12.

| correct | confidence when right | confidence when wrong |
|--:|--:|--:|
| 79.2% | 0.92 | 0.70 |

## Compliance

Classify statements against a legal rule using [LegalBench](https://huggingface.co/datasets/nguha/legalbench). The task's rule is supplied in the instruction (the `hearsay` task shown here).

### Run

```
uv run jev-complies --task hearsay --run-id hearsay-full --concurrency 12
```

### Results

It took 0:03 to classify all 94 statements at concurrency level 12.

76.6% correct (72/94). Confidence averaged 0.66 on correct answers, 0.40 on wrong.

| slice | n | accuracy |
|---|--:|--:|
| Non-assertive conduct | 19 | 100% |
| Statement made in-court | 14 | 100% |
| Not introduced to prove truth | 20 | 85% |
| Standard hearsay | 29 | 66% |
| Non-verbal hearsay | 12 | 25% |