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
- 每个抽象 case 在本地 `dataset.json` 和 `source_manifest.json` 中保留对应 task event/execution record 的 provenance refs；`decision_input_ref` 标为 `reconstructed-development-input://`，manifest 标记 `reconstructed_development_input`。这些是来源追溯，不代表还原了历史完整候选或原模型输入。
- 原目标、原始提示、图片、来源定位符不进入模型请求；来源映射仅保存在本地抽取产物中。
- 候选由 `SCENARIOS` 明确写出；正确选项位置交替，gold、case ID、来源和复核信息不发给模型。
- 每个 case 的 refs 指向抽取到的结构化事实来源；将多条重复事实归并为一个抽象题仍只有一个开发 case，不增加独立样本数，也不改变 `held_out=false`。
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

## v14.3.0：真实 no-motion 双视角输入采集

用户确认允许 Runtime/Query/相机读取后，实际核查历史 Gateway `127.0.0.1:19020` 未运行。
因此未恢复旧任务，而是从提交 `4059b373ba37857ae87f7a710af8e3d2ca34f1cc` 导出 Adapter 源码，
创建独立 RoboTwin 传感器场景，避开工作区中另一个任务的机器人实现改动。

### 已完成的实测

源码及产物根目录：
`/home/yanxu/robotwin20-runtime/artifacts/jev-source-4059b373.e38y6W/`。

1. 原 `check_persistent_runtime.py` 单视角 smoke：`capture/persistent-sensor-result.json` 为 passed，
   两次不同图像保持同一场景版本，公开 Observation Tool 返回 available，`motion_executed=false`。
2. 集成采集：`decision-snapshots/20261015T091928.651066Z-2be476a6/summary.json` 为 captured。
   使用原传感器 provider、ObservationEndpoint、Qwen provider 和 SceneUnderstandingEndpoint；
   未调用私有模拟器 actor/分割真值生成语义，没有远程模型 fallback。

| 字段 | 实际结果 |
|---|---|
| 场景 | `blocks_ranking_rgb`，seed 0，双 Franka 初始化传感器场景 |
| 图像 | `camera/head`、`camera/front`，实际渲染 RGB/depth |
| 同步 | capture_skew_ms = 0 |
| 入站年龄 | 112 ms；保留原 max_age_ms = 1000，未放宽 |
| 本地视觉 | `http://127.0.0.1:8012/v1`，`qwen3-vl-4b-awq`，temperature 0、top_p 1 |
| 预算 | 单次视觉请求 30 s、1536 tokens、SDK retries 0 |
| 结果 | 7 个实体，1 条歧义；公开 scene.understand 为 available |
| 视觉接口耗时 | 17336.11 ms；不是 JEV/System-2 决策时延 |
| 外部调用 | 远程模型 0，Action 0，Session 0 |

模型将三类方块描述为 red/blue/green cube，另四个 light gray surface 被明确标为身份不确定。
原歧义和全部实体保留在 `understanding.json`；这些是视觉模型输出，不是人工真值标签。
两路视觉输入只发本机 loopback 服务，不上传 JEV、System-2 或其他远程模型。

### 可复现入口

`scripts/capture_jev_observation.py --config ...` 每次创建新的时间戳目录，不覆盖既有结果。
配置路径相对配置文件解析。此轮实际配置是上述根目录的 `snapshot_config.json`，包含独立
Adapter 路径、声明的来源提交、runtime/profile、worker Python、输出根目录及本地模型预算。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" \
  /home/yanxu/miniconda3/envs/paos/bin/python scripts/capture_jev_observation.py \
  --config /home/yanxu/robotwin20-runtime/artifacts/jev-source-4059b373.e38y6W/snapshot_config.json
```

成功退出 0；观测/理解不可用或采集失败退出 2。每次执行都会新建模拟器场景并重新调用本地 VLM。
仅允许字面 loopback 模型地址，关闭代理继承；不增加远程备用路线。worker 启动/request/shutdown
预算分别为 90/30/15 秒。正常、失败和中断路径关闭 worker；失败保留 summary、已完成观测和日志。

每轮保存配置、运行 profile/seed、采集器源码、两份源 ToolSpec、实际 request/result、视觉诊断、
worker 日志及 summary。Git HEAD 是基础版本，首次实测额外使用尚未提交的 collector；其原源码已保存在
该 run 的 `collector_source.py`。实测后只补充日志写失败时仍关闭 worker、Python 元数据和测试，
不修改首轮请求、响应、耗时或原始 summary。Adapter 源码目录本身来自固定 Git 导出，未加载工作区机器人改动。
VLM 别名、GPU/网络负载和生成非确定性仍可能使重跑结果不同。

### 验证与验收边界

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  -q -p pytest_asyncio.plugin -p no:cacheprovider tests/test_decision_snapshot.py \
  tests/test_decision_calibration.py tests/test_decision_evaluation.py tests/test_decision_provider.py \
  tests/test_planning_loop.py tests/test_planning_task_integration.py
.venv/bin/ruff check PhyAgentOS/agent/decision_snapshot.py \
  scripts/capture_jev_observation.py tests/test_decision_snapshot.py
```

七维核查：原 provider/endpoint 所有权不变；身份和时间戳来自实际传感器；失败结果落盘；唯一目录可重跑且无
自动重试；Action/Session 不可达、无硬件调用；现有校准/评测格式不变；采集和模型请求预算明确。

本阶段交付的是**真实观测与视觉解释快照**，尚未创建 Coordinator 任务、冻结 scene.bind 契约、生成宿主
候选或写入 selection。输出明确 `host_selection_measured=false`，不是完整的决策时刻快照，也不是配对测量。
下一步已不缺此次原始 RGB/depth/标定/理解材料，应将它们接入有明确离线来源的 Coordinator 回放，
由原 NodeContextProvider/候选生成/准入路径生成决策输入，再运行原 System-2 与 JEV+fallback 配对。
当前语义 provider 没有输出空间包围盒或几何派生产物；若后续测试要实际执行 scene.bind，还需原几何
enrichment/binding 服务，不能把视觉标签当成执行物体身份。生产 active 仍未启用。

## 2026-10-15 原宿主选择边界配对（v14.4.0）

已实现 `decision_host_replay.py`：同一脱敏理解事实、当前 `scene.bind` ToolSpec 和目标，分别创建隔离
Coordinator/SQLite，通过原 NodeContextProvider、投影候选生成、准入、selection/trace 持久化及
AgentLoopNodeExecutor 执行 A=原 System-2、B=JEV+原 System-2 fallback。不是另写 JSON 选择题。
新增 `run_node_turn(selection_only=True)` 只暴露 `forge_plan_ready/select`，成功持久化即交还宿主；
选择仍在认知 deadline 内，默认生产行为不变。评测执行器在 pending selection 处停止，不返回虚假 Tool 成功。

### 数据和安全边界

- 输入为上一节同一模拟器观测；保留 7 实体和 4 实体的原始身份歧义，原宿主生成 red/blue/green 三个候选。
- 三个目标由本次作者编写：选红、选蓝、仅选不存在的紫色。正例期望来自观测类别；负例期望升级。
  同一场景/工作流家族，全部 calibration，非历史同版本决策重放、非独立 held-out、非独立标签复核。
- 源事实以 `offline_replay_source_import` 显式导入现有事务存储；虚拟 Runtime 为 `no-runtime`，
  `ready_at_binding=false`，无 Gateway 客户端，不更改旧任务或伪造物理 readiness。
- 只保留身份、类别、置信度和歧义编码/实体引用；图片、路径、日志、视觉自由文本解释不出站。
  原 ContextBuilder 使用空的隔离 Skill/记忆目录，工作区及 home 路径脱敏；并非部署现场全部 Skill prompt 的性能证明。
- 隔离 B 路使用 active 分支以测接受行为，引用明确的 development-only 策略说明；这不是生产 active 授权或正式接受策略。
  Query/Action/Session 执行工具均未注册；不执行 `scene.bind`，不宣称几何绑定、物理身份或任务完成。
- 每路同为 60s 决策预算、最多 3 次模型迭代；JEV cap=10s、fallback reserve=15s；单轮最多 18 个 HTTP 请求，
  System-2 温度 0、2048 tokens、SDK retries=0，原宿主有界重试仍受预算限制。这些是本轮校准配置，不自动写入生产。

### 实测、发现和修复

首轮：`artifacts/evals/jev-host-replay-runs/20261015T100150.358472Z-4d173993/`。
15 个 HTTP 请求均 200；三个 JEV 答案附带 `confidence/probabilities`，被原适配器严格字段集合误拒绝，
全部走真实 System-2 fallback。保留此轮原始请求/响应/结果，不将它删除或改成修复后的成功数据。

Major 修复：`decision_provider.py` 允许这两个实际观察到的非执行元数据，但仍要求 type/choice，
拒绝未知字段及 arguments；不读取元数据作为置信度阈值，不放宽原候选 ID、场景或准入检查。

重测：`artifacts/evals/jev-host-replay-runs/20261015T100427.281975Z-d7981ba9/`。
11 个 HTTP 请求均 200：JEV 3，System-2 8。返回身份 JEV=`jev-1.13.0`、System-2=`gpt-5.6-sol`；
后者仍是返回模型名，未取得更细部署快照证明。

| 目标 | 原 System-2 总耗时 / 调用数 | JEV+fallback 总耗时 / JEV、System-2 调用数 | 实际结果 |
| --- | --- | --- | --- |
| red cube | 22524.15ms / 2 | 1209.46ms / 1、0 | 两路均持久化 e1 |
| blue cube | 23724.72ms / 2 | 768.82ms / 1、0 | 两路均持久化 e2 |
| 不存在的 purple cube | 15186.78ms / 2 | 17407.46ms / 1、2 | JEV 弃权；两路均无 selection |

负例没有强选，但原 executor 以 `node_turn_incomplete` 结束；保留 `failed` 状态和耗时，不把它改写成节点成功。
六路均 `node_execution_count=0`，无节点 settlement；正确接受的两例确实免去 System-2。
含负例和 fallback 的均值为 6461.91ms vs 20478.55ms，p95 为 17407.46ms vs 23724.72ms。
每路只有 3 例，nearest-rank p95 就是最大值；该结果不是泛化、部署吞吐或整任务提速结论。

### 已交付评测器的结果

导出真实 context/candidates、宿主 decision telemetry、调用数、trace 和总时延；两路 context/candidates
不一致时拒绝导出。数据仍全部标为 calibration、同一 labeler/reviewer，正式 acceptance policy 留空。
使用原 `run_decision_evaluation`，不改变任何 active 条件。报告目录：
`artifacts/evals/jev-host-replay-runs/20261015T100427.281975Z-d7981ba9/evaluation/20261015T100701.468019Z-46cc74c6/`。

- 实际替代 2/3；错误接受 0/2；必须升级 1/1。错误接受 Wilson 95% 区间上限约 0.658，不能由零观测错误推断风险为零。
- `active_eligible=false`，CLI 退出 2 为未达 active，不是评测器崩溃。
- 未通过：held_out_only、required_category_coverage、planned_sample_size_reached、independent_label_review、acceptance_policy_recorded。
- 部署 provenance 的人工确认仍未完成；报告中 model_version 有值不等于服务端部署快照已固定。

### 重跑与验证

示例配置：`evals/decisions/host_replay.example.json`。真实配置仅在本地
`artifacts/evals/jev-host-replay-config.json`，凭据只引用 owner-only 文件，不写入输出或 Git。

```bash
# 会产生已授权远程模型请求；无 Runtime/运动。每次创建独立目录。
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/replay_jev_host.py \
  --config artifacts/evals/jev-host-replay-config.json
# 只读取已记录结果，不调用模型；当前 calibration 返回 2。
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/replay_jev_host.py \
  --evaluate-run artifacts/evals/jev-host-replay-runs/20261015T100427.281975Z-d7981ba9
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  -q -p pytest_asyncio.plugin -p no:cacheprovider tests/test_decision_host_replay.py \
  tests/test_decision_provider.py tests/test_planning_loop.py tests/test_planning_task_integration.py
```

保留 config、脱敏 facts、ToolSpec、每路 context/candidates/task/selection、真实请求响应、失败及宿主日志。
重测基于 Git `94eb7202` 加未提交 JEV 实现，实际 runner/loop/provider 源码随产物保存；随后增加只读评测导出
及其测试，不追溯修改测量。网络负载、模型生成和服务部署漂移仍影响重跑。

七维结论：所有权仍在原 Coordinator；原准入/候选和协议回归通过；失败及模型身份可追踪；重开可恢复 selection；
no-motion 与脱敏边界成立；生产默认路径不变；一次 JEV 与原 deadline/fallback 保持。
下一步不再缺配对 runner，而是分组采集六类独立专项样例、独立标签复核、部署身份确认及测量形成的接受策略。
此前三例已被查看和用于修复，不能回填成 held-out；生产继续 off/shadow。

最终定向及扩展回归共 `412 passed in 7.91s`，Ruff、CLI help、diff 检查通过；出站请求记录未含
home 路径、image_url 或 Authorization。扩展回归修复一处 HEAD 已存在的测试漏传 decision_deadline，
不修改恢复代码。核心命令上再加 `tests/test_planning_{context,dispatch,dispatch_bootstrap,effect_recovery,end_to_end,module,projection,selection,source_assembly}.py`
和 `tests/test_recovery_decisions.py` 可覆盖扩展集；412 总数还包含 snapshot/calibration/evaluation 测试。
