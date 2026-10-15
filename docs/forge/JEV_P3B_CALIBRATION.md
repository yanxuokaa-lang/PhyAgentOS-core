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
Chat Completions、同样的事实/选项及无工具的 JSON 答案。此采集器本身不改变生产 DecisionProvider。
v14.2.0 另行接通生产 adapter 的显式 `systemone` 协议，见下文；首轮测量仍仅属于校准器。

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

## v14.2.0：宿主协议接线与历史回放资格核查

本阶段只改变仓库代码和隔离测试；没有改变生产配置，没有使用密钥新增远程请求，也没有启动
Runtime、恢复旧任务、执行 Query/Action/Session、采集相机或运行仿真/硬件。

### 已修复的实现缺口

1. 原生产 provider 只发送 `{model, request}`，与实测 `/v1/systemone` 不兼容。
   现在 `apiFormat=systemone` 将宿主目标、事实及候选描述转换为 `state/questions`，
   将 `answers.decision.choice` 转回原 `DecisionResult`；返回的 `model` 保留为真实响应身份。
   不上传 task/revision/node/policy 引用；候选仍只携带 ID/描述，不允许服务提供执行参数。
2. 原 CLI 使用所有决策点中的第一个环境变量，可能取到关闭点的凭据或将一个服务的凭据发给另一个服务。
   现在仅加载 enabled 点，按点路由协议和凭据；文件读取复用 `read_api_key_file`，相对路径以配置文件目录解析。
   `apiKeyEnv` 和 `apiKeyFile` 二选一，显式环境变量缺失会报配置错误；off 点不读取文件或环境变量。
3. 既有宿主再次准入、scene/revision 新鲜度、Coordinator selection 所有权、deadline、取消和原 System-2 回退不变。
   HTTP 错误、畸形答案进入既有 unavailable 路径；未知候选由宿主拒绝；不新增自动重试。

配置示意（不要据此启用 active；生产仍未修改）：

```json
{
  "agents": {
    "decisions": {
      "queryInputSelection": {
        "mode": "off",
        "endpoint": "https://www.1949-x.xn--fiqs8s/v1/systemone",
        "model": "jev-latest",
        "apiFormat": "systemone",
        "apiKeyFile": "/absolute/path/to/owner-only-key",
        "timeoutCapS": 2.0,
        "fallbackReserveS": 0.25
      }
    }
  }
}
```

此适配器是协议转换，不是自由文本脱敏器。现场使用前仍需审核目标、facts、候选描述；用户允许的是
脱敏后的事实发送。当前回归只使用合成数据。2 秒保持原默认，不依据五题校准自动调参；此前 JEV
均值约 2.07 秒、p95 约 6 秒，说明真实配对时必须记录超时和 fallback，不能直接套用单请求提速结论。

### 核查结果与复现

2026-10-15 只读核查本地 SQLite，限定任务创建时间 `[2026-10-12, 2026-10-15T08:20:00)`：

| 检查项 | 结果 | 能证明什么 |
|---|---:|---|
| primary binding 中冻结的 `scene.bind` ToolSpec | 23 | 23 条 projection 和 projection_plan 均为 null |
| 这些时间范围任务的已存 Query selections | 144 | 已接受的输出，不是完整决策输入快照 |
| 其中 `scene.bind` selections | 18 | 不能从最终已选项倒推当时完整候选及准入上下文 |

此查询按创建时间、无会话前缀过滤，与首轮按更新窗口/会话前缀抽取的 24 个任务不是同一计数口径。
当前源码 `grounding.py` 的 BIND_TOOL_SPEC 已包含投影配置，但不会追溯更新旧任务冻结的绑定。
这意味着“重新打开旧任务”不能自动补齐输入，修改其绑定则属于反事实回放而非原版本重放。

```bash
sqlite3 -readonly /home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3 <<'SQL'
SELECT count(*) AS bindings,
       json_extract(b.value,'$.planning_policy.argument_projection') AS projection,
       json_extract(b.value,'$.planning_policy.argument_projection_plan') AS plan
FROM agent_tasks t, json_each(t.record_json,'$.primary_skill_binding.required_tools') b
WHERE t.created_at >= '2026-10-12' AND t.created_at < '2026-10-15T08:20:00'
  AND json_extract(b.value,'$.tool_id')='scene.bind'
GROUP BY projection,plan;
SELECT count(*) AS query_selections,
       sum(json_extract(s.value,'$.selected_tool_id')='scene.bind') AS bind_selections
FROM agent_tasks t, json_each(t.record_json,'$.revisions') r,
     json_each(r.value,'$.planning_selections') s
WHERE t.created_at >= '2026-10-12' AND t.created_at < '2026-10-15T08:20:00'
  AND json_extract(s.value,'$.resumable_selection.semantics')='query';
SQL
```

### 测试证据及七维复审

测试 `test_systemone_selection_uses_real_isolated_coordinator` 使用合成 NodeExecutionContext、
MockTransport 和真实隔离 Coordinator/SQLite：成功选择可重开存储恢复；拒答、未知 ID、畸形响应、
过期场景、503、超时均无 selection/执行记录。失败后原 AgentLoopNodeExecutor 能进入 `run_node_turn`
入口并保持同一 deadline；测试在那里停止，没有执行 System-2。上下文刷新仍为受控测试替身，
不是真实 NodeContextProvider 快照回放。测试数、trace 及 mock 时延均不计入正式评测。

1. 所有权：HTTP adapter 只转换选择结果，原 Coordinator 持有 selection/trace，Runtime 无调用。
2. 正确性：实际协议形状、拒答、畸形答案、未知候选、过期场景被覆盖；旧数据缺口不被合成输入填平。
3. 可观测：真实模型身份沿原 decision telemetry 记录；本地真实 selection trace 可持久化，不编造配对指标。
4. 恢复幂等：SQLite 重开验证 pending selection；没有重试或旧任务恢复，两种协议取消均向上传播。
5. 安全：密钥逐点隔离、owner-only 读取；无现场调用，无 frame/calibration 假定变化，无 motion 授权。
6. 兼容：默认 typed 协议、off 模式保留；新增配置可显式选择 systemone，旧模型失败仍沿原 fallback。
7. 收敛预算：每次认知周期一次 JEV；timeout cap、fallback reserve 和绝对截止时间不变；不自动调大预算。

执行上文 pytest 命令并追加 `tests/test_planning_task_integration.py`；静态检查：

```bash
.venv/bin/ruff check PhyAgentOS/agent/decision_provider.py PhyAgentOS/config/schema.py \
  PhyAgentOS/cli/commands.py tests/test_decision_provider.py tests/test_planning_loop.py
```

### 下一步的真实输入与权限边界

推荐：使用当前已带投影配置的 ToolSpec，在新任务的决策时刻保存真实只读上下文，包括来源记录、
场景/标定身份、目标、完整候选及准入输入。若需启动现场 Runtime/Query/相机来获得这些材料，应单独取得
该范围的授权；本次没有执行。只导出既有快照无需运动，但仍需避免包含后续结果或标签。

获得合格输入后，才可在隔离宿主上对同一输入测量 A=原 System-2、B=JEV+原 System-2 fallback，
两路使用相同宿主代码、gpt-5.6-sol 配置和预算；保留失败分母、模型返回身份、真实 trace 和总时延。
尚需实现这一有界配对 runner，不能把当前校准器换个名字当作它。

备选：用历史事实在当前契约下重构输入，仅作反事实开发校准，不能补充独立 held-out 或宣称原历史重放。
正式 active 仍需独立六类 held-out、独立标签复核、模型部署 provenance 确认和全部工单指标通过。
同一执行者自审不变成独立复核；生产保持 off/shadow。当前无需以 active 开启作为继续离线开发的前提。
