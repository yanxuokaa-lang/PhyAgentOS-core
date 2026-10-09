# System 1 入口意图与路由能力实验结果

日期：2026-10-09。范围：离线标签判断；未接入或替换 PAOS 入口、AgentLoop、Coordinator、
Runtime 或 handler。

方法、RLCD 原理、数据示例、概率指标和完整结论见
[正式对比实验报告](SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md)。

## 1. 实验对象

三类 backend 使用 `intent-routing-v1` 数据集、同一 `message + recent_turns + capability_state`
输入投影、七类 intent、五类 route 和同一 gold scorer：

| Backend | 执行状态 |
| --- | --- |
| Laya English / multilingual / typed-decisions | 各完成 5 条 smoke、20 条 development 与 60 条 evaluation |
| Jev `jev-latest` (`jev-1.13.0`) | 完成 20 条 development 与 60 条 evaluation |
| GPT-6 Luna Decisions | 未执行；已知代理 `/v1/decisions` 返回 404 |

## 2. Laya 本地环境和模型核验

- 独立解释器：`/home/yanxu/laya-system1/.venv/bin/python`；Laya `0.4.1`，Torch
  `2.14.1+cu130`。
- 独立缓存：`/home/yanxu/laya-system1/huggingface`；snapshot
  `7b928d828b7b0e022f929d9bd2e44165aa270148`。
- 设备：NVIDIA GeForce RTX 5060 Ti，三个 checkpoint 均实际加载到 CUDA。
- 文件：root English、`multilingual/`、`typed-decisions/` 均包含各自配置、tokenizer 和完整
  `model.safetensors`。
- 三模型均返回合法 `choice`、全量 `probabilities` 和 `confidence`。加载时 English 与
  typed-decisions 报告 11+ options 温度值被夹到 0.5；本实验的 7/5 options 不直接使用该桶，
  但 confidence 不用于后端等价比较。

## 3. 结果

| Backend / checkpoint | Cases | Coverage | Intent | Route | Joint | Mean successful latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Laya English evaluation | 60 | 1.00 | 0.70 | 0.333 | 0.25 | 0.055 s |
| Laya multilingual evaluation | 60 | 1.00 | 0.75 | 0.483 | 0.383 | 0.034 s |
| Laya typed-decisions evaluation | 60 | 1.00 | 0.65 | 0.45 | 0.417 | 0.061 s |
| Jev development | 20 | 0.95 | 0.895 | 0.947 | 0.842 | 1.371 s |
| Jev evaluation | 60 | 0.90 | 1.00 | 0.944 | 0.944 | 1.351 s |

Evaluation 概率指标（10-bin ECE / multiclass Brier / NLL）：

| Backend | Intent | Route |
| --- | --- | --- |
| Laya English | 0.250 / 0.421 / 0.946 | 0.213 / 0.770 / 1.533 |
| Laya multilingual | 0.100 / 0.407 / 0.975 | 0.274 / 0.843 / 1.951 |
| Laya typed-decisions | 0.364 / 0.582 / 1.258 | 0.210 / 0.756 / 1.506 |
| Jev `jev-1.13.0` | 0.047 / 0.021 / 0.055 | 0.104 / 0.084 / 0.186 |

Jev evaluation 用量为 `48,253` input tokens 和 `7,144` output tokens。60 条中 54 条返回
合法联合答案；6 条在有限重试后仍 network timeout。分类准确率只以 54 条有效响应为分母，
因此不能把 0.944 joint accuracy 解读为 94.4% 端到端路由成功率。

Jev 的三个有效 evaluation route 错误都是 `system2 -> conversation`。development 还出现一次
`mixed_or_unclear -> analysis`、一次 `new_task -> task_control`，以及一次无任务状态查询被路由到
conversation。Laya evaluation 的主要问题是 route 塌向 `status_read`、`clarification_reply` 或
`task_control`，对能力条件和任务对象的利用不足。Multilingual 的 intent/route 单项准确率最高，
typed-decisions 的 joint accuracy 最高，但三者 route accuracy 均低于 0.50。

## 4. 产物

- Laya English：`out/laya-intent-probe/english/20261009T101050Z-bb4dc069/`
- Laya multilingual：`out/laya-intent-probe/multilingual/20261009T101057Z-004af2e1/`
- Laya typed-decisions：`out/laya-intent-probe/typed-decisions/20261009T101104Z-ed52dd8f/`
- Laya English development：`out/laya-intent-probe/english/20261009T110027Z-6faac00c/`
- Laya multilingual development：`out/laya-intent-probe/multilingual/20261009T110035Z-dcaa3ce7/`
- Laya typed-decisions development：`out/laya-intent-probe/typed-decisions/20261009T110042Z-ce4188b4/`
- Laya English evaluation：`out/laya-intent-probe/english/20261009T110226Z-8a1d7dee/`
- Laya multilingual evaluation：`out/laya-intent-probe/multilingual/20261009T110235Z-72267c19/`
- Laya typed-decisions evaluation：`out/laya-intent-probe/typed-decisions/20261009T110243Z-10158043/`
- Jev development：`out/jev-intent-probe/20261009T102016Z-0b81d79f/`
- Jev evaluation：`out/jev-intent-probe/20261009T102953Z-4c8740d6/`

每个 run 保存 config、environment、requests、raw responses、predictions、metrics 和报告；Jev
另存 attempts/errors。API key 未写入任一产物。

## 5. 结论

Jev 在有限候选的中文入口 intent/route 上显示出明显的 System 1 判断能力，值得进入下一阶段
shadow 验证；但当前远程 endpoint 的 evaluation coverage 只有 0.90，且错误集中在应升级至
System 2 的边界，因此不能直接替换现有入口。

Laya 的三个 checkpoint 均已证明本地部署、结构化输出与低延迟可行，但 60 条 evaluation 的
route accuracy 仅为 0.333/0.483/0.45，当前零样本能力不足以进入替换讨论。后续若继续 Laya，
应基于新的训练 split 微调或校准，再用未参与优化的新 evaluation 验证；不能用本次 evaluation
反向调参后仍把它当作独立测试集。

GPT-6 Luna Decisions 尚未在有效 `/v1/decisions` endpoint 上执行，因此三者不存在完整横向排名。
