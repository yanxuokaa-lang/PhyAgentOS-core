# 架构推断、评测与仍未公开的细节

## 1. 官方公开信息与外部重建不能混写

官方确认：state + typed questions、并行概率输出、Choice/Score/Noul、RLCD 的目标是 calibrated decisions。当前公开组织里有 SDK、Adapter、Skills 与基础设施 fork。

本次没有取得 Jev 本身的完整参数、backbone 身份、训练规模、网络定义、训练损失、数据集和权重。`typesafe-ai/vllm` 或 `typesafe-ai/LLaDA` 存在不等于架构声明；也不能把社区“same API”当作同一个模型。

## 2. Archer Hume 的黑盒重建文章

- 原文：https://archerhume.com/posts/jevs-architecture-unmasked
- 日期：2026-09-17；作者称进行了约 10,000 次 API 调用。
- [本地可读正文](web/community-architecture-unmasked.txt) / [HTML](web/community-architecture-unmasked.html)。
- 这是 kev README 引用的架构推断来源，不是官方技术报告；本次未重跑其 API probes。

**文章提出的结构**：共享 state 的表征 → 独立 question branch → 对候选直接 readout → 概率校准；causal transformer 与 sparse MoE 是不同确定度的推断，其中 MoE 尤其不确定。

有技术价值的观测设计：

1. 把 secret 放在 sibling question 与放在 state 两种条件下对照，测另一个问题能否读到它。支持“问题之间的行为隔离”，但不能唯一确定用了 block mask 还是独立调用。
2. 改变 question 数与 state 长度，观察延迟和 token accounting。支持共享计算的解释，但不能仅凭计费字段还原 GPU execution graph。
3. 把 reference card 放在不同选项位置，再交换条件与候选顺序，探测选项是否交互。它可区分部分独立 pair-scoring 假设，却不能证明某个具体 pointer head。
4. 比较 output_tokens 随问题 ID 和序列化结构变化。文章认为它是回答序列化计数，不是神经网络 decode 步数，因此不能用 output_tokens/latency 宣称生成吞吐量。
5. 比较大量公开 tokenizer；作者报告没有完全匹配。它既不能证明 private base model，也不能排除换 tokenizer、继续预训练或 API 计数口径不同。

**对源码阅读的实际意义**：kev 实现了这类可行架构；LitJev/SemIf 利用已有 vocab head；openjev-sglang 走 serving API；它们都能给相近接口，但训练、隔离、成本和正确性仍不同。

## 3. 保存的独立评测代码

| 项目 | 本地入口 | 能进一步回答的问题 |
|---|---|---|
| AbdelStark/jev-benchmarks | [源码](code-snapshots/AbdelStark__jev-benchmarks/) | calibration、selective risk、latency 的测量方式 |
| RINNECODER/jev-behavior-study | [源码与保存的结果](code-snapshots/RINNECODER__jev-behavior-study/) | phrasing、语义等价改写、否定/边界等行为失败 |
| baibizhe/jev-decision-benchmarks | [源码](code-snapshots/baibizhe__jev-decision-benchmarks/) | MetaTool、When2Call、BFCL 相关工具决策设置 |
| yodablocks/jev-orderby-bench | [源码](code-snapshots/yodablocks__jev-orderby-bench/) | 分数跨行/跨批次能否排序，batching 对排序的影响 |
| jaredpalmer/kev | [runs](code-snapshots/jaredpalmer__kev/runs/) | 同配方、不同 backbone、域内/域外与 Jev reference |
| logan-markewich/jeff | [bench](code-snapshots/logan-markewich__jeff/bench/) | 端到端 HTTP 延迟、硬件、成本、质量折中 |
| tamaratran/jev-pruner | [evals](code-snapshots/tamaratran__jev-pruner/evals/) | 裁剪对后续正确回答/信息保留的影响 |

这里是可继续阅读的证据入口，不代表逐一通过了本次审核。文本快照跳过大文件、权重、二进制与多数 JSONL 数据；复跑需回原仓库获取相应数据/资产。本次没有安装依赖或执行上述 runner。

## 4. 不应直接合并的实验数字

- GPU forward 时间、包含 tokenizer 的本地时间、HTTP 端到端时间、排队后的批量吞吐量是不同量。
- 一个 K-way question 与 K 个 binary questions 的问题语义和计算量都不同。
- 并行 N 个完整 state 副本，不等于共享一次 state 计算。
- 概率 sum=1、softmax 存在、返回类型正确，均不自动证明 calibration。
- 温度拟合用 teacher soft labels 时，衡量的是与 teacher 分布对齐；用人工 gold labels 时才直接优化那些标注上的 NLL。
- ECE、Brier、准确率、coverage 与 selective error 需要一起看；减少覆盖后降低错误率不是免费提高整体准确率。
- 候选顺序、候选数量、“none/abstain”选项、state 长度、语言和 framing 都可能改变结果。
- 新仓库成绩不能贴在旧仓库实现上；同作者多个仓库应分别检查模型、数据、代码版本。

## 5. 建议的下一轮具体研究任务

1. **本地模型实现**：选 kev 与 minojev，对同一 small labeled set 比较 pointer/readout、head-only/LoRA、question isolation 与 calibration；这需要下载权重及独立运行授权范围。
2. **纯推理优化**：选 LitJev 与 openjev-sglang，比较一个 prefix + N branches 的实际 GPU 内存、forward 次数与 wall time；先核对相同 backbone/tokenizer。
3. **问法自我改进**：沿 jev-align 的 acquisition → human labels → GEPA → candidate comparison 深入，确认改善的是新样本，而非同一被优化批次。
4. **Agent 集成**：先以只返回建议的 Skill routing/检索 rerank 做离线比较，考察 none-of-the-above、缺答案及错误成本。
5. **个人开发续作**：跟进 openJev-verdict-2.0、kev 大模型配方、Von marker checkpoint 与 jev-pruner Codex 评测；目录只是入口，不能以星标替代实现核实。
