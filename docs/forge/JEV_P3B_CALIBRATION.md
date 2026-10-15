# P3b 真实日志抽象校准 / Real-record calibration

本交付完成真实记录抽取、同作者二次复核、双远程 API 校准采集及既有评测器出报告。
它不是 P3b active 验收完成：输入是既有 RGB 工作流的开发数据，候选为人工抽象的处理方式，
不是历史宿主的完整输入组合。生产保持 off/shadow，所有现场系统和运动接口均未调用。

This delivers extraction, same-author review, paired remote semantic probes and an evaluator
report, not active acceptance. Choices are authored abstractions of real facts, not replayed
host candidates. Production and physical execution remain unchanged.

## 数据与标注

- 来源：用户授权的本地 `agent_tasks` / `agent_task_events`；SQLite `mode=ro`，同一读事务。
- 时间窗：`2026-10-12T00:00:00+00:00` 至 `2026-10-15T08:20:00+00:00`，右端不含。
- 会话前缀：`cli:rgb-benchmark-injected-`。扫描 24 个任务，20 个任务贡献 38 条匹配事实。
- 归并为 5 个不同抽象题：缺身份字段 10 条、缺实体 1 条、Query 业务不可用 17 条、
  Action unknown 7 条、Action failed 3 条。38 条来源不是 38 个独立测试样本；全部属于一个工作流家族。
- 仅从结构化 rejection/执行状态抽取事实；不使用历史恢复模型的自由文本理由充当真值。
- 原目标、原始提示、图片、内部引用不进入模型请求；来源定位留在本地 `source_manifest.json`。
- 候选由 `SCENARIOS` 明确写出；正确选项位置交替，gold、case ID、来源和复核信息不发给模型。
- 标签表示“原 owner 应如何处理当前事实”，选中报告缺口/对账选项不等于实际调用恢复流程。
- `labeler_id == reviewer_id == codex-same-author`，复核文件明确 `independent_review=false`。
  全部 `split=calibration`，`planned_held_out_cases=0`；不为满足 schema 制造 held-out。

## 运行

从仓库根目录抽取，输出唯一时间戳目录：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/collect_jev_calibration.py extract \
  --database /home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3 \
  --since 2026-10-12T00:00:00+00:00 --until 2026-10-15T08:20:00+00:00 \
  --session-prefix cli:rgb-benchmark-injected- \
  --output-root artifacts/evals/jev-calibration-source
```

第二轮复核 `dataset.json` 和来源表后，在生成的 `label_review.json` 记录实际复核结论。
按 `evals/decisions/calibration_config.example.json` 建立本地配置，设置真实 dataset 路径。
凭据使用环境变量或 `api_key_file`，不能同时配置；文件读取复用既有 owner-only 凭据接口。
路径相对于配置文件解析。示例 endpoint 是本次指定的远程服务，不是官方 OpenAI endpoint。

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/collect_jev_calibration.py collect \
  --config /absolute/path/to/collection_config.json
```

采集器先检查两路凭据及请求上限，再串行交替 JEV/System-2 顺序。每题每路一次，无自动重试，
无并发、无回退调用、无 host admission、无 task/selection/execution 写入。默认最多 5 题/10 次请求，
每次最多 30 秒；System-2 输出上限 512 tokens。保留超时、HTTP 错误、非法响应，不丢弃失败分母。
取消保留已完成单路输出和 interrupted manifest，不编造未完成配对。重新运行创建新目录并重新计费。

JEV 使用真实 `model/state/questions` → `answers.decision` 协议；System-2 使用远程
Chat Completions、同样的事实/选项及无工具的 JSON 答案。此采集器不改变生产 typed DecisionProvider，
不能据此宣称现有生产 adapter 已支持 `/v1/systemone`。

## 产物与证据口径

每次保存实际请求/响应、模型返回身份、usage、逐请求耗时、输入数据、配置中的凭据引用（无密钥）、
交替顺序、请求上限、Git 基础提交和采集器/评测器源码快照。源码快照解决首次运行时实现仍在工作树、
单独 HEAD 不能复现执行代码的问题，不增加 hash 或发布门禁。服务随机性、网络等待、缓存及模型别名漂移仍存在。

`provider_metrics.json` 同时记录两路的正确数和失败分母；`measurements.json` 标为
`evidence_mode=provider_probe`、`host_outcome=not_evaluated`，没有伪造 `decision_trace_ref`。
这里 `system2_invoked=false` 指没有运行 B 路 fallback，不否认另行测量了 System-2 对照请求。
沿用时延字段时，报告明确 `measurement_scope=provider_only_not_host_or_fallback`：
这些数字是单独请求耗时，不是生产决策总耗时，不证明实际替代率。

既有评测器自动运行，也可以仅重算离线报告，不再调用 API：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/evaluate_jev_decisions.py \
  --config /absolute/path/to/collection-run/evaluation_config.json
```

该报告正常完成但 `active_eligible=false`，独立评测 CLI 返回 2；这不是采集程序崩溃。
正式 measured/held-out 路径保留原条件，并明确拒绝未评估 host admission 或非 Query 决策点。

## 2026-10-15 首轮实际结果

- 数据目录：`artifacts/evals/jev-calibration-source/20261015T083053.283710Z-1e895194/`。
- 测量目录：`artifacts/evals/jev-calibration-runs/20261015T083258.500799Z-a472acda/`。
- 评测目录：上述测量目录下 `evaluation/20261015T083404.087524Z-a9f736cb/`。
- 10 次请求全部 HTTP 200，无重试；JEV 5/5，System-2 5/5。
- 请求 `jev-latest`，服务返回 `jev-1.13.0`；请求/返回均为 `gpt-5.6-sol`。
  后者未提供更细快照身份，不将模型别名当作固定部署版本证明。

| 单请求耗时 | JEV | System-2 |
|---|---:|---:|
| 均值 | 2071.65 ms | 11033.79 ms |
| p95（5 条 nearest-rank，即最大值） | 5995.21 ms | 16288.80 ms |

这五道题是明显的边界判断，只有一个工作流家族，没有困难候选、独立样本或多次测量；
5/5 不证明节点选择泛化，也不能外推完整任务提速倍数。
首轮运行在基础提交 `d6b2b7dd` 加当时未提交实现上；事后补记实现来源，不改原请求/响应或测量。

## 验证与下一阶段

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  -q -p pytest_asyncio.plugin -p no:cacheprovider tests/test_decision_calibration.py \
  tests/test_decision_evaluation.py tests/test_decision_provider.py tests/test_planning_loop.py
.venv/bin/ruff check PhyAgentOS/agent/decision_calibration.py PhyAgentOS/agent/decision_evaluation.py \
  scripts/collect_jev_calibration.py tests/test_decision_calibration.py
```

下一阶段仍需：原 Query 候选生成/准入/Coordinator 的隔离回放、原 System-2 路径及真实 fallback
配对、带可审计 selection trace 的实际替代证据；随后准备独立六类 held-out、独立复核及实际版本确认。
最后依据工单报告和操作员授权启用单个 Query 点。临时校准数据不代替这些步骤，也不要求先建设 VPP2 或训练平台。
