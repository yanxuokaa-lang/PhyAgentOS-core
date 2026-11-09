# JEV Decision Benchmarks

We use these three benchmarks to evaluate whether JEV selects the right tools, knows when to call or abstain, and avoids choosing tool calls when no tools are available.

English | [简体中文](README.zh-CN.md)

## MetaTool

MetaTool tests whether a model selects the right tool or combination of tools for a user's request and abstains when no suitable tool is available.

| Model / mode | Similar 0-shot ↑ | Similar 5-shot ↑ | Abstain 0-shot ↑ | Abstain 5-shot ↑ | At most two ↑ | Exactly two ↑ |
|---|---:|---:|---:|---:|---:|---:|
| **JEV 1.13 (Choice)** | **77.79%** | **77.79%** | **87.04%** | **88.54%** | 81.29% | 88.33% |
| **ChatGPT** | 69.05% | 72.94% | 50.35% | 78.49% | **88.28%** | 88.53% |
| ChatGLM2 | 54.17% | 57.44% | 6.63% | 15.68% | 20.20% | 23.34% |
| Llama2-7b | 45.95% | 51.12% | 0.90% | 2.51% | 35.69% | 57.34% |
| Llama2-13b | 44.06% | 49.85% | 2.31% | 5.93% | 81.49% | 77.87% |
| Vicuna-7b | 73.46% | 63.67% | 1.50% | 1.81% | 44.06% | 64.34% |
| Vicuna-13b | 58.23% | 63.15% | 2.51% | 3.42% | 83.70% | 78.47% |
| **Vicuna-33b** | 53.96% | 60.54% | 2.81% | 3.11% | 48.69% | **91.15%** |
| Koala-13b | 56.34% | 60.85% | 1.70% | 5.83% | 39.03% | 25.10% |

CSR measures exact tool-set selection. JEV uses a Choice adapter; paper baselines generate tool names followed by answer extraction. The public similar-tool and abstention sets each contain 995 examples, versus 975 each in the paper; each multi-tool condition has 497 examples. [Paper v6, Tables 3–4](https://arxiv.org/html/2310.03128v6) · [Full results and protocol (中文)](reports/metatool.zh-CN.md) · [CSV](data/metatool/comparison.csv)

## When2Call

When2Call tests whether a model chooses the right next step: answer directly, call a tool, ask for missing information, or say it cannot complete the request. It also measures how often the model chooses a tool call when no tools are available.

| Model / mode | Accuracy ↑ | Macro F1 ↑ | Tool hallucination ↓ |
|---|---:|---:|---:|
| **JEV 1.13 (Choice)** | **74.84%** | **56.55** | 76.36% |
| Llama 3.2 1B Instruct | — | 21.70 | 43.00% |
| Llama 3.2 3B Instruct | — | 17.90 | 52.00% |
| Llama 3.1 8B Instruct | — | 16.60 | 67.00% |
| Llama 3.1 70B Instruct | — | 37.80 | 57.00% |
| Qwen 2.5 0.5B Instruct | — | 32.00 | 20.00% |
| Qwen 2.5 1.5B Instruct | — | 29.90 | 23.00% |
| Qwen 2.5 3B Instruct | — | 29.80 | 23.00% |
| Qwen 2.5 7B Instruct | 49.01% | 32.00 | 21.00% |
| Qwen 2.5 14B Instruct | — | 36.20 | 21.00% |
| Qwen 2.5 32B Instruct | — | 32.90 | 17.00% |
| Qwen 2.5 72B Instruct | 50.82% | 32.80 | 23.00% |
| xLAM 1B FC-R | — | 25.60 | 40.00% |
| xLAM 7B FC-R | 42.72% | 31.50 | 24.00% |
| xLAM 8x7B R | — | 32.90 | 13.00% |
| xLAM 8x22B R | — | 34.30 | 9.00% |
| MNM 4B SFT (baseline) | — | 29.70 | 16.00% |
| MNM 4B dataset-SFT | — | 48.10 | 4.30% |
| MNM 4B dataset-RPO | — | 51.00 | 1.90% |
| MNM 8B SFT (baseline) | 48.38% | 31.90 | 19.00% |
| MNM 8B dataset-SFT | 66.13% | 49.40 | 7.00% |
| **MNM 8B dataset-RPO** | 69.09% | 52.40 | **1.20%** |

All 3,652 test examples. JEV reads four candidates together and selects one; official MCQ scores candidate continuation likelihoods separately. Ordinary accuracy is reliably recoverable from paper matrices for only six official models; `—` means unavailable. F1 uses a 0–100 scale and four fixed classes, with a maximum of 75 on this dataset. Hallucination measures the 258 no-tool examples requiring `cannot_answer`; JEV selects `tool_call` on 197. [Official MCQ](https://github.com/NVIDIA/When2Call/blob/ecc8d42388e91ab37e7e737d48e16e8ecea3d1dc/README.md#mcq-1) · [Report and real error example (中文)](reports/when2call.zh-CN.md) · [CSV](data/when2call/comparison.csv)

## BFCL V4

This table uses BFCL's action/abstention tasks to test whether a model calls a tool when it should and refrains when no tool is suitable or required information is missing.

| Model / mode | Irrelevance: correct abstention ↑ | Relevance: correct action ↑ |
|---|---:|---:|
| **JEV 1.13 (binary adapter; 3-run mean)** | 86.74% | **87.50%** |
| Claude-Opus-4-5-20251101 (FC) | 84.72% | 62.50% |
| Claude-Sonnet-4-5-20250929 (FC) | 86.61% | 68.75% |
| Gemini-3-Pro-Preview (FC) | 77.85% | 75.00% |
| **Gemini-2.5-Flash (FC)** | **93.67%** | 75.00% |
| GPT-5.2-2025-12-11 (FC) | 79.42% | 75.00% |
| GPT-5-mini-2025-08-07 (FC) | 91.01% | 62.50% |
| **GPT-4.1-2025-04-14 (FC)** | 86.52% | **87.50%** |
| o3-2025-04-16 (FC) | 86.13% | 81.25% |
| DeepSeek-V3.2-Exp (FC) | 93.18% | 37.50% |
| Moonshotai-Kimi-K2-Instruct (FC) | 87.34% | 75.00% |
| **Qwen3-235B-A22B-Instruct-2507 (FC)** | 81.73% | **87.50%** |
| GLM-4.6 (FC thinking) | 84.96% | 75.00% |
| Grok-4-1-fast-reasoning (FC) | 79.43% | 81.25% |

These are the 13 requested official model configurations; all 109 model/mode records appear in the [full report (中文)](reports/bfcl.zh-CN.md) and [CSV](data/bfcl/comparison.csv). Baselines use FC mode, retaining GLM's thinking tag. JEV uses a binary adapter and the mean of three runs. Irrelevance equally weights the 240- and 884-example subset accuracies; Relevance has 16 examples, with 14 correct in every JEV run. Retrieved **2026-09-19**; the page states last updated **2026-04-12**. [Official leaderboard](https://gorilla.cs.berkeley.edu/leaderboard)

## Reading the tables

**Bold marks the best displayed-table value per metric and its model; all exact ties are marked.** A bold model name means it leads at least one column, not every column or an overall score. ↑ Higher is better; ↓ lower is better. Comparisons use saved source precision; display values have two decimal places. Missing values do not compete.

These are descriptive comparisons between published scores and JEV adapter experiments. Differences in inputs, outputs, samples, or repetitions described below each table prevent strict same-protocol rankings or significance claims. BFCL highlighting applies only to the displayed selection. No aggregate score combines the three benchmarks.

## Evaluation record

The actual JEV version is `typesafe/jev-1.13-20260917`, evaluated on 2026-09-19. MetaTool completed 8,574 inputs (different prompt conditions over 4,287 source records); When2Call completed 3,652 inputs; BFCL completed 10,938 requests, including repeats, tool-order variations, and schema ablation. All saved evaluation responses are valid.

Baseline numbers come from the original papers or official leaderboard; other models were not rerun. BFCL covers action/abstention and separate name-only selection diagnostics; full argument generation, tool execution, and BFCL Overall were not evaluated. When2Call Acc-Norm is excluded, and the 300-example Judge route is kept separate in the detailed report.

## Data, verification, and sources

- [MetaTool report (中文)](reports/metatool.zh-CN.md): all 24 CSR conditions, eight paper baselines, and multi-tool outcome distributions.
- [When2Call report (中文)](reports/when2call.zh-CN.md): confusion matrix, derived ordinary accuracies, separate Judge references, and a verified hallucination example.
- [BFCL report (中文)](reports/bfcl.zh-CN.md): individual repetitions, all published decision scores, and adapter limitations.
- [Long-form CSV](results.csv): all included metrics across the three benchmarks, with conditions, protocols, sources, and explicit missing values.
- [Source hashes](data/manifest.json) and [source notes](SOURCES.md). This package includes statistics, source excerpts, per-example scores, and one original When2Call interaction. Full evaluation programs and the remaining API interactions belong to the original experiment archive.

Python 3.10+, standard library only. From the repository root:

```bash
python3 scripts/build_tables.py --check
python3 scripts/build_tables.py
```

The first command checks source hashes, numerical derivations, report consistency, and local links. The second rebuilds both READMEs, detailed reports, and the long-form CSV from saved data. Both run offline without model API calls. Narrative templates are in `templates/`.
