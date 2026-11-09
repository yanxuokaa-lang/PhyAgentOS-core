# JEV 与 BFCL V4 行动／弃权分项对照

实际模型：`typesafe/jev-1.13-20260917`。推理日期：2026-09-19。官方榜单读取于 2026-09-19，页面标注最后更新为 2026-04-12。

## 1. 版本与协议

固定官方 commit 为 `f7cf7359b7ac615a0b294831c5ba2bc95ee4a000`，evaluator 版本为 `2025.12.17`。[源码](https://github.com/ShishirPatil/gorilla/tree/f7cf7359b7ac615a0b294831c5ba2bc95ee4a000/berkeley-function-call-leaderboard)。读取时官方页面声明的版本一致。

JEV 读取原对话与完整工具列表，回答是否应调用至少一个工具；`p_call ≥ 0.5` 为行动，其他为弃权，再映射到官方二元判分结构。没有生成或执行真实函数。

官方模型通过各自 handler 解码实际调用，输出负担、提示、失败处理和重复次数与 JEV 二元适配不同。官方解码失败可能被视为弃权，JEV 无效响应不获得正确弃权奖励。因此不能将适配成绩称为同协议官方成绩。

## 2. 三次主实验

| 重复 | irrelevance | live_irrelevance | 两子集等权 Irrelevance | Relevance |
|---|---:|---:|---:|---:|
| 1 | 214/240 | 744/884 | 86.6648% | 14/16 = 87.50% |
| 2 | 215/240 | 740/884 | 86.6469% | 14/16 = 87.50% |
| 3 | 216/240 | 741/884 | 86.9118% | 14/16 = 87.50% |

Irrelevance 三次均值为 **86.74%**，样本标准差为 **0.1480 个百分点**。Relevance 三次均为 **87.50%**。重复不增加独立样本数，也没有集成预测。

两列必须联合解释：始终弃权可得到 100% Irrelevance、0% Relevance。Relevance 只有 16 题，一题相当于 6.25 个百分点，不宜根据细小差距声称显著领先。

## 3. 全部官方模型／模式

共 109 条官方记录，加 1 行 JEV。JEV 在第一行，官方模型保留 CSV 原顺序。FC、Prompt 和 thinking 标签保留，未将同名不同模式合并。这里的加粗按完整表格每列最优标记；首页按指定的 13 个官方配置标记，范围不同。

| 模型 / 模式 | Irrelevance ↑ | Relevance ↑ |
|---|---:|---:|
| JEV 1.13（二元适配；三次均值） | 86.74% | 87.50% |
| Claude-Opus-4-5-20251101 (FC) | 84.72% | 62.50% |
| Claude-Sonnet-4-5-20250929 (FC) | 86.61% | 68.75% |
| Gemini-3-Pro-Preview (Prompt) | 85.59% | 68.75% |
| GLM-4.6 (FC thinking) | 84.96% | 75.00% |
| Grok-4-1-fast-reasoning (FC) | 79.43% | 81.25% |
| Claude-Haiku-4-5-20251001 (FC) | 85.11% | 62.50% |
| Gemini-3-Pro-Preview (FC) | 77.85% | 75.00% |
| o3-2025-04-16 (Prompt) | 83.98% | 93.75% |
| Grok-4-0709 (Prompt) | 84.30% | 81.25% |
| Grok-4-0709 (FC) | 75.40% | 87.50% |
| Moonshotai-Kimi-K2-Instruct (FC) | 87.34% | 75.00% |
| Grok-4-1-fast-non-reasoning (FC) | 74.09% | 81.25% |
| Command A Reasoning (FC) | 86.75% | 68.75% |
| DeepSeek-V3.2-Exp (Prompt + Thinking) | 67.00% | 93.75% |
| Gemini-2.5-Flash (FC) | 93.67% | 75.00% |
| GPT-5.2-2025-12-11 (FC) | 79.42% | 75.00% |
| GPT-5-mini-2025-08-07 (FC) | 91.01% | 62.50% |
| xLAM-2-32b-fc-r (FC) | 80.23% | 81.25% |
| DeepSeek-V3.2-Exp (FC) | 93.18% | 37.50% |
| GPT-4.1-2025-04-14 (FC) | 86.52% | 87.50% |
| o4-mini-2025-04-16 (FC) | 83.91% | 81.25% |
| xLAM-2-70b-fc-r (FC) | 79.11% | 75.00% |
| Qwen3-235B-A22B-Instruct-2507 (Prompt) | 78.89% | 93.75% |
| GPT-5-nano-2025-08-07 (FC) | 89.10% | 75.00% |
| Nanbeige4-3B-Thinking-2511 (FC) | 83.09% | 75.00% |
| Gemini-2.5-Flash (Prompt) | 91.09% | 62.50% |
| GPT-4.1-mini-2025-04-14 (FC) | 81.69% | 81.25% |
| o4-mini-2025-04-16 (Prompt) | 87.16% | 81.25% |
| Qwen3-32B (FC) | 76.37% | 93.75% |
| o3-2025-04-16 (FC) | 86.13% | 81.25% |
| Qwen3-235B-A22B-Instruct-2507 (FC) | 81.73% | 87.50% |
| **Nanbeige3.5-Pro-Thinking (FC)** | 74.20% | **100.00%** |
| Qwen3-32B (Prompt) | 82.39% | 81.25% |
| xLAM-2-8b-fc-r (FC) | 63.28% | 87.50% |
| Command A (FC) | 84.19% | 81.25% |
| BitAgent-Bounty-8B | 97.48% | 68.75% |
| Arch-Agent-32B | 82.15% | 81.25% |
| GPT-5.2-2025-12-11 (Prompt) | 87.26% | 75.00% |
| Qwen3-8B (FC) | 79.07% | 93.75% |
| ToolACE-2-8B (FC) | 90.79% | 75.00% |
| Qwen3-30B-A3B-Instruct-2507 (FC) | 79.90% | 81.25% |
| xLAM-2-3b-fc-r (FC) | 63.45% | 87.50% |
| Qwen3-14B (FC) | 81.94% | 87.50% |
| Qwen3-8B (Prompt) | 82.27% | 75.00% |
| **GPT-4.1-2025-04-14 (Prompt)** | 83.99% | **100.00%** |
| mistral-large-2411 (FC) | 68.92% | 93.75% |
| Qwen3-14B (Prompt) | 87.18% | 81.25% |
| Mistral-Medium-2505 | 74.49% | 75.00% |
| Mistral-Medium-2505 (FC) | 91.95% | 62.50% |
| **Llama-4-Maverick-17B-128E-Instruct-FP8 (FC)** | 55.97% | **100.00%** |
| Mistral-small-2506 (FC) | 87.94% | 87.50% |
| Gemini-2.5-Flash-Lite (FC) | 92.50% | 43.75% |
| Qwen3-30B-A3B-Instruct-2507 (Prompt) | 74.85% | 93.75% |
| Qwen3-4B-Instruct-2507 (FC) | 84.93% | 87.50% |
| Qwen3-4B-Instruct-2507 (Prompt) | 75.87% | 87.50% |
| Arch-Agent-3B | 74.67% | 68.75% |
| Claude-Opus-4-5-20251101 (Prompt) | 90.75% | 68.75% |
| GPT-4.1-nano-2025-04-14 (FC) | 66.00% | 93.75% |
| Mistral-Small-2506 (Prompt) | 65.73% | 93.75% |
| Arch-Agent-1.5B | 74.83% | 75.00% |
| Command R7B (FC) | 81.65% | 68.75% |
| **Llama-3.3-70B-Instruct (FC)** | 53.53% | **100.00%** |
| mistral-large-2411 (Prompt) | 38.77% | 93.75% |
| Hammer2.1-7b (FC) | 90.12% | 50.00% |
| xLAM-2-1b-fc-r (FC) | 64.47% | 87.50% |
| Gemma-3-12b-it (Prompt) | 70.29% | 93.75% |
| GPT-4.1-mini-2025-04-14 (Prompt) | 73.88% | 87.50% |
| Hammer2.1-3b (FC) | 86.12% | 56.25% |
| Gemma-3-27b-it (Prompt) | 73.67% | 81.25% |
| Phi-4 (Prompt) | 87.55% | 50.00% |
| Qwen3-1.7B (FC) | 76.54% | 81.25% |
| **Llama-4-Scout-17B-16E-Instruct (FC)** | 44.92% | **100.00%** |
| Gemini-2.5-Flash-Lite (Prompt) | 93.33% | 50.00% |
| CoALM-70B | 85.65% | 93.75% |
| Hammer2.1-1.5b (FC) | 79.40% | 75.00% |
| palmyra-x-004 (FC) | 80.99% | 81.25% |
| GPT-5-mini-2025-08-07 (Prompt) | 55.71% | 93.75% |
| Open-Mistral-Nemo-2407 (FC) | 61.77% | 81.25% |
| GPT-5-nano-2025-08-07 (Prompt) | 45.75% | 93.75% |
| Amazon-Nova-2-Lite-v1:0 (FC) | 82.11% | 75.00% |
| Granite-3.1-8B-Instruct (FC) | 79.98% | 68.75% |
| Falcon3-10B-Instruct (FC) | 32.09% | 93.75% |
| Granite-3.2-8B-Instruct (FC) | 80.53% | 75.00% |
| CoALM-8B | 86.90% | 87.50% |
| Llama-3.1-8B-Instruct (Prompt) | 42.70% | 93.75% |
| MiniCPM3-4B-FC (FC) | 72.84% | 68.75% |
| Claude-Haiku-4-5-20251001 (Prompt) | 95.29% | 31.25% |
| Amazon-Nova-Pro-v1:0 (FC) | 70.06% | 93.75% |
| Claude-Sonnet-4-5-20250929 (Prompt) | 95.03% | 37.50% |
| GPT-4.1-nano-2025-04-14 (Prompt) | 83.44% | 68.75% |
| **Falcon3-7B-Instruct (FC)** | 31.99% | **100.00%** |
| Qwen3-0.6B (FC) | 80.84% | 75.00% |
| Granite-20b-FunctionCalling (FC) | 75.13% | 87.50% |
| Qwen3-0.6B (Prompt) | 82.50% | 75.00% |
| Amazon-Nova-Micro-v1:0 (FC) | 70.65% | 81.25% |
| RZN-T (Prompt) | 82.41% | 81.25% |
| MiniCPM3-4B (Prompt) | 73.71% | 56.25% |
| Llama-3.2-3B-Instruct (FC) | 52.06% | 87.50% |
| Bielik-11B-v2.3-Instruct (Prompt) | 36.01% | 93.75% |
| Hammer2.1-0.5b (FC) | 80.79% | 68.75% |
| **Gemma-3-4b-it (Prompt)** | 53.94% | **100.00%** |
| Open-Mistral-Nemo-2407 (Prompt) | 6.28% | 93.75% |
| Granite-4.0-350m (FC) | 60.84% | 81.25% |
| Falcon3-3B-Instruct (FC) | 32.92% | 81.25% |
| **Ministral-8B-Instruct-2410 (FC)** | **100.00%** | 0.00% |
| Falcon3-1B-Instruct (FC) | 87.30% | 0.00% |
| Llama-3.2-1B-Instruct (FC) | 51.57% | 43.75% |
| **Llama-3.1-Nemotron-Ultra-253B-v1 (FC)** | **100.00%** | 0.00% |
| Gemma-3-1b-it (Prompt) | 33.18% | 37.50% |

## 4. 单独诊断：工具名称选择

原实验还评测了 Choice 工具名称选择，通过名称投影使用官方 checker。这些指标只看函数名称，不能作为完整 AST Accuracy 或 BFCL Overall。

| 条件 | Multiple（200 题） | Live Multiple（1,053 题） |
|---|---:|---:|
| 主实验 1 | 100.00% | 98.77% |
| 主实验 2 | 100.00% | 98.48% |
| 主实验 3 | 100.00% | 98.86% |
| 顺序种子 20260919 | 100.00% | 98.29% |
| 顺序种子 20260920 | 100.00% | 98.10% |
| 删除参数 schema | 99.50% | 97.34% |

名称选择三次均值分别为 100.00% 和 98.70%；Full AST 与 BFCL Overall 均未评测。完整保存统计还包含校准、重复性与鲁棒性结果。

## 5. 证据与复查

[官网](https://gorilla.cs.berkeley.edu/leaderboard) · [官方 CSV](https://gorilla.cs.berkeley.edu/data_overall.csv) · [保存的官方 CSV](../data/bfcl/official_leaderboard.csv) · [对照 CSV](../data/bfcl/comparison.csv) · [JEV 统计](../data/bfcl/summary.json) · [榜单版本记录](../data/bfcl/leaderboard_metadata.json) · [来源哈希](../data/manifest.json)

基线直接引用官方发布值，未重跑其他模型，也未重新评分其逐题输出。读取日期不代表每个官方模型的推理日期。没有跨模型逐题配对结果，不能据此进行配对显著性检验。

本仓库验证脚本将全部 109 条决策分项与保存的官方 CSV 逐项核对，并从 JEV 三次正确数复算等权均值。
