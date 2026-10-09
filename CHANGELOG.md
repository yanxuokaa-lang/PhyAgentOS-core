# Changelog
## Archive
- [2026-10 part4](changelog/2026-10_part4.md)
- [2026-10 part5](changelog/2026-10_part5.md)
- [2026-10 part3](changelog/2026-10_part3.md)
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v13.1.5 (2026-10-10 00:30) - codex

### 变更摘要 / Summary
- [policy] [fix] 七维 Code Review 修复 `object.acquire`/`object.place` 只校验 preparation scene、未校验 terminal frame 的 lineage 缺口；同一 scene 下跨观察帧 URI 现在 fail-closed。 (local)
- [Policy] [Fix] The seven-dimension review fixed the lineage gap where `object.acquire`/`object.place` checked only the preparation scene and not its terminal frame; cross-frame URIs in one scene now fail closed. (local)
- [eval] [test] 增加跨帧拒绝回归；目标 Core/Skill/Adapter suite `134 passed`，Ruff、compileall、`git diff --check` 通过。 (local)
- [Eval] [Test] Add cross-frame rejection regressions; the targeted Core/Skill/Adapter suite has `134 passed`, with Ruff, compileall, and `git diff --check` passing. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py:L38-L43,L420-L428`
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_place.py:L9-L14,L440-L447`
- `examples/forge-skills/pick-place-workflow/tests/test_object_acquire.py:L242` and `test_object_place.py:L166-L170`

```diff
- preparation_ref scene matched, frame component was not checked
+ preparation_ref scene and terminal frame both match the observation lineage
```

详见 [v13.1.5 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.5 detailed log](changelog/2026-10_part5.md).

## v13.1.4 (2026-10-10 00:00) - codex

### 变更摘要 / Summary
- [comm] [fix] Core/RobotWin 生成 task/revision/node-scoped preparation identity，解决跨任务 route geometry collision；Action route 保持 source scene 校验。 (local)
- [Comm] [Fix] Core/RobotWin now generate task/revision/node-scoped preparation identities to prevent cross-task route-geometry collisions while Action routes retain source-scene validation. (local)
- [eval] [test] 增加同输入幂等、跨任务隔离、scoped URI 与 `node_selection_no_progress` no-motion 回归；无 Runtime、AgentTask 或物理运动。 (local)
- [Eval] [Test] Add idempotency, cross-task isolation, scoped-URI, and `node_selection_no_progress` no-motion regressions; no Runtime, AgentTask, or physical motion was used. (local)

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L32-L56,L545-L562`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_preparation.py:L246-L249`
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py` and `object_place.py` preparation binding checks

```diff
- preparation://{scene_revision}/{frame_id}
+ preparation://{scene_revision}/{task_id}/{revision_id}/{node_id}/{frame_id}
```

详见 [v13.1.4 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.4 detailed log](changelog/2026-10_part5.md).

## v13.1.3 (2026-10-09 23:00) - codex

### 变更摘要 / Summary
- [env] [chore] 在用户授权下停止旧 Runtime，完成当前 checkout 的 editable Core 安装，复核 `pick-place-workflow 3.0.12` payload，并使用既有 operator-owned profile environment 启动新的 `robotwin-blocks-ranking-graspnet` Runtime。 (local)
- [Env] [Chore] Under user authorization, stop the old Runtime, install the checkout Core in editable mode, verify the `pick-place-workflow 3.0.12` payload, and start the new `robotwin-blocks-ranking-graspnet` Runtime with the existing operator-owned profile environment. (local)
- [eval] [test] 启动后只做状态验收：Runtime/Dora/Gateway 与 11/11 Tool context ready；任务库无非终态任务，未创建 AgentTask、调用 Query/Action、读取相机或推进物理运动。 (local)
- [Eval] [Test] Post-start validation only checked Runtime/Dora/Gateway and 11/11 Tool contexts ready; the task store has no non-terminal tasks, and no AgentTask, Query/Action, camera read, or physical motion was performed. (local)
- Git commit: `55478bc` on `feature/planning-loop`; detailed deployment record is in `changelog/2026-10_part5.md`.

### 文件与关键 Diff / Files and Key Diff
| 对象 / Object | 位置 / Location | 结果 / Result |
| --- | --- | --- |
| PAOS Core | `PhyAgentOS/` | editable import from current checkout |
| Skill | `pick-place-workflow 3.0.12` | local installer returned `already ready` |
| Runtime | `pick-place-workflow:robotwin-blocks-ranking-graspnet` | running; Dora running; Gateway ready |
| Task store | `/home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3` | non-terminal tasks = 0 |
| Detailed log | `changelog/2026-10_part5.md` | v13.1.3 deployment, exact runtime state, and no-motion boundary |

```diff
- Runtime stopped; Dora down; Gateway unavailable
+ Runtime running; Dora flow running; Gateway /tools ready; 11/11 Tool contexts ready
  Core editable-installed; Skill 3.0.12 unchanged; no live task or motion during validation
```

详见 [v13.1.3 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.3 detailed log](changelog/2026-10_part5.md).

## v13.1.2 (2026-10-09 22:33) - codex

### 变更摘要 / Summary
- [policy] [fix] 将非重试型 Query provider unavailable 从 failed settlement 分流为 Coordinator-owned `waiting_for_runtime`，只在冻结 Runtime Tool readiness 发生可观测转换后释放旧失败尝试并重试同一未结算节点。 (local)
- [Policy] [Fix] Divert non-retryable Query provider unavailability from failed settlement into Coordinator-owned `waiting_for_runtime`, releasing the old failed attempt and retrying the same unsettled node only after an observable readiness transition on the frozen Runtime Tool. (local)
- [policy] [fix] 保持失败 Query append-only 审计，同时从 predecessor、source browsing、projection、reducer、admission evidence 和 discovery progress 的有效视图排除；并发 stop、prompt 工具可见性和 `ready -> unavailable -> ready` 均按 fail-closed 状态机处理。 (local)
- [Policy] [Fix] Preserve the failed Query as append-only audit history while excluding it from effective predecessor, source-browsing, projection, reducer, admission-evidence, and discovery-progress views; handle concurrent stop, prompt-tool visibility, and `ready -> unavailable -> ready` through the fail-closed state machine. (local)
- [eval] [test] 七维审查发现并修复 11 项 Major；provider-neutral fake/no-motion 回归覆盖任务占用、下游关闭、同节点恢复、证据隔离、operator stop 与 AgentLoop 自主收敛。 (local)
- [Eval] [Test] The seven-dimension review found and fixed eleven Major issues; provider-neutral fake/no-motion regressions cover active-task ownership, downstream closure, same-node recovery, evidence isolation, operator stop, and AgentLoop convergence. (local)

### 文件与关键 Diff / Files and Key Diff

| 文件 / File | 行号 / Lines | 摘要 / Summary |
| --- | --- | --- |
| `PhyAgentOS/forge/binding.py` | L171-L189 | provider-neutral block 分类 / Provider-neutral block classification |
| `PhyAgentOS/forge/task.py` | L120-L159, L1297-L1318, L1518-L1821, L3895-L3916 | 等待态、事件、状态转换、有效记录视图与并发复核 / Wait state, events, transitions, effective-record view, and concurrency validation |
| `PhyAgentOS/agent/planning_loop.py` | L133-L245, L897-L906, L1485-L1548 | settlement 前分流、有效上下文与 stop 收敛 / Pre-settlement diversion, effective context, and stop convergence |
| `PhyAgentOS/agent/long_horizon.py` | L138-L169, L189-L334 | 只读 readiness 轮询与可中断恢复 / Read-only readiness polling and interruptible recovery |
| `PhyAgentOS/agent/loop.py` | L42, L152-L176, L340-L349, L537-L541, L1562-L1567 | 等待态保护、生产/prompt wiring 和语义 discovery progress / Wait-state protection, production/prompt wiring, and semantic discovery progress |
| `PhyAgentOS/agent/planning_context.py` | L13-L15, L61-L151, L203-L230 | admission/current-capture 证据隔离 / Admission and current-capture evidence isolation |
| `PhyAgentOS/agent/prompt_context.py` | L763-L835, L1402-L1491 | 等待 phase、最小只读工具面与有效任务投影 / Wait phase, minimal read-only tool surface, and effective task projection |
| `PhyAgentOS/agent/tools/planning.py` | L73-L84, L322-L338, L433-L449 | source/projection 有效视图 / Effective source and projection view |
| `tests/test_planning_loop.py` | L92-L190, L3094-L3629 | provider recovery 与并发无运动回归 / Provider recovery and concurrency no-motion regressions |
| `tests/test_planning_context.py` | L214-L244 | 失败 Query admission 隔离 / Failed-Query admission isolation |
| `tests/test_prompt_context.py` | L329-L485 | Runtime wait phase/tool visibility and released-receipt isolation / Runtime-wait phase/tool visibility and released-receipt isolation |
| `docs/forge/QUERY_PROVIDER_BLOCK_RECOVERY_DIAGNOSIS_20261009.md` | L1-L175 | 事故诊断、通用状态机、权责与审查 / Incident diagnosis, generic state machine, ownership, and review |
| `changelog/2026-10_part5.md` | L3-L112 | 完整双语变更、七维审查、Diff 与验证 / Full bilingual changes, seven-dimension review, diff, and validation |

```diff
- semantic Query unavailable -> failed settlement -> stop -> failed task
+ provider-blocked Query -> waiting_for_runtime -> GET Tool context only
+ observable readiness transition -> release old attempt -> retry same node
- failed Query receipt could leak into planning/admission evidence
+ immutable audit record retained; effective planning and admission views exclude it
- concurrent operator stop could race the awaited context read
+ post-await state validation preserves cancelled/cancelling as authoritative
```

### 验证 / Validation
- No-motion Core/AgentLoop/Skill suites: `452 passed in 11.64s`.
- Ruff、compileall、`git diff --check` 通过；未创建/恢复 live AgentTask，未调用 Gateway Query/Action，未推进 simulator、读取相机或产生物理运动。 / Ruff, compileall, and `git diff --check` passed; no live AgentTask was created or resumed, no Gateway Query/Action was invoked, and no simulator, camera, or physical motion was used.
- Implementation, diagnosis, and tests commit: `d482828`.

详见 [v13.1.2 月度日志](changelog/2026-10_part5.md)和[诊断](docs/forge/QUERY_PROVIDER_BLOCK_RECOVERY_DIAGNOSIS_20261009.md)。
See the [v13.1.2 detailed log](changelog/2026-10_part5.md) and [diagnosis](docs/forge/QUERY_PROVIDER_BLOCK_RECOVERY_DIAGNOSIS_20261009.md).

## v13.1.1 (2026-10-09 21:20) - codex

### 变更摘要 / Summary
- [env] [chore] 使用既有 operator-owned profile environment 启动新安装的 `pick-place-workflow 3.0.12`，恢复 `robotwin-blocks-ranking-graspnet` Runtime、Dora flow 与 Gateway readiness。 (local)
- [Env] [Chore] Start the newly installed `pick-place-workflow 3.0.12` with the existing operator-owned profile environment, restoring `robotwin-blocks-ranking-graspnet` Runtime, Dora flow, and Gateway readiness. (local)
- [env] [chore] readiness 验收覆盖 11 个 required Tool context，未创建 AgentTask、调用 Query/Action、推进 simulator 或产生物理运动；无 env-file 的首次启动被 PAOS preflight 安全拒绝。 (local)
- [Env] [Chore] Readiness validation covered all 11 required Tool contexts without creating an AgentTask, invoking Query/Action, advancing the simulator, or producing physical motion; the first start without an env-file was safely rejected by PAOS preflight. (local)

### 文件与关键 Diff / Files and Key Diff
| 对象 / Object | 位置 / Location | 结果 / Result |
| --- | --- | --- |
| Runtime environment | `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env` | 复用既有 operator-owned 配置，不记录 secret / Reused operator-owned configuration without recording secrets |
| Runtime | `pick-place-workflow:robotwin-blocks-ranking-graspnet` | `running`；Dora `running`；Gateway `ready` / Running; Dora running; Gateway ready |
| Tools | Gateway `/tools` | 11/11 required contexts ready / 11/11 required contexts ready |
| 任务库 / Task store | `/home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3` | 非终态任务=`0` / non-terminal tasks=`0` |
| 日志 / Log | `changelog/2026-10_part5.md` L3-L45 | 双语启动、预检失败分支和无运动验收 / Bilingual startup, preflight-failure branch, and no-motion validation |

```diff
- Runtime stopped; Gateway unavailable; Agent sees no ready Forge Skill runtime
+ Runtime running; Gateway ready; all 11 required Tool contexts ready
  no AgentTask, live Query/Action, simulator advancement, or physical motion during readiness check
```

详见 [v13.1.1 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.1 detailed log](changelog/2026-10_part5.md).

## v13.1.0 (2026-10-09 21:04) - codex

### 变更摘要 / Summary
- [env] [chore] 按明确授权强制停止旧 `pick-place-workflow` Runtime，并刷新当前仓库的 editable `PhyAgentOS-ai 1.0.2` Core，使 unknown-world scene-refresh bootstrap 修复由 `paos` CLI 加载。 (local)
- [Env] [Chore] Force-stop the old `pick-place-workflow` Runtime under explicit authorization and refresh the checkout's editable `PhyAgentOS-ai 1.0.2` Core so the `paos` CLI loads the unknown-world scene-refresh bootstrap repair. (local)
- [env] [chore] 核对已安装 Skill 仍为已验证的 `3.0.12` payload；部署后保持 Runtime stopped、Dora down、Gateway unavailable，未执行 live Query/Action 或推进 simulator。 (local)
- [Env] [Chore] Confirm that the installed Skill remains the verified `3.0.12` payload; keep the Runtime stopped, Dora down, and Gateway unavailable after deployment, with no live Query/Action or simulator advancement. (local)

### 文件与关键 Diff / Files and Key Diff

| 对象 / Object | 位置 / Location | 结果 / Result |
| --- | --- | --- |
| PAOS Core | `PhyAgentOS/agent/recovery_decisions.py` L11-L62, L219-L250 | editable install 从当前 checkout 导入恢复逻辑 / Editable install imports the recovery logic from this checkout |
| Skill | `pick-place-workflow 3.0.12` | installer 返回 `already ready`；payload 未变 / Installer returned `already ready`; payload unchanged |
| Runtime | `robotwin-blocks-ranking-graspnet` | stopped；Dora down；Gateway unavailable；非终态任务 0 / Stopped; Dora down; Gateway unavailable; zero non-terminal tasks |
| 日志 / Log | `changelog/2026-10_part5.md` L3-L58 | 完整双语部署记录 / Complete bilingual deployment record |

```diff
- old Runtime running against the previous process lifetime
+ old Runtime force-stopped; editable Core refreshed from the repaired checkout
  Skill payload remains verified version 3.0.12
  no Runtime restart, live Action, simulator advancement, or physical motion
```

详见 [v13.1.0 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.0 detailed log](changelog/2026-10_part5.md).

## v13.0.15 (2026-10-09 19:22) - codex

### 变更摘要 / Summary
- [docs] [docs] 新增 Laya/Jev System 1 入口意图与路由正式对比报告，覆盖 RLCD 原理、80 条数据与样例、分类/可用性/概率指标、失败分析和 PAOS 适用边界。(local)
- [docs] [docs] Add the formal Laya/Jev System 1 intent-routing report covering RLCD principles, the 80-case dataset and examples, classification/availability/probability metrics, failure analysis, and PAOS applicability boundaries. (local)
- [eval] [feat] 为 Decisions、Laya 和 Jev scorer 增加共享的 10-bin ECE、multiclass Brier、NLL 与 probability coverage，并用已有原始响应重算全部 development/evaluation 结果。(local)
- [eval] [feat] Add shared 10-bin ECE, multiclass Brier, NLL, and probability coverage to the Decisions, Laya, and Jev scorers, then rescore every development/evaluation run from preserved raw responses. (local)

### 文件与关键 Diff / Files and Key Diff
`research/decision-api-intent-probe/{decision,jev,laya}_intent_probe.py`, probability-metric tests,
`docs/forge/SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md`, and the existing
result summary.

```diff
+ shared probability-distribution validation and normalization
+ intent/route ECE-10, multiclass Brier, NLL, and probability coverage
+ formal report with RLCD, dataset examples, metrics, failures, and replacement boundary
- do not count Jev timeouts inside valid-response probability metrics
```

详见 [v13.0.15 月度日志](changelog/2026-10_part4.md)和[正式实验报告](docs/forge/SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md)。
See the [v13.0.15 detailed log](changelog/2026-10_part4.md) and [formal experiment report](docs/forge/SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md).

## v13.0.14 (2026-10-09 18:36) - codex

### 变更摘要 / Summary
- [policy] [fix] 对 Runtime 明确声明的未知世界变化，使用冻结 ToolSpec 中唯一可空绑定的 `refreshes_scene` Query capability 建立场景刷新 bootstrap revision；不 replay 原 Action，不推断实体位姿或持有状态。 (local)
- [Policy] [Fix] For an explicit Runtime-declared unknown world change, bootstrap a scene-refresh revision from the one bindable `refreshes_scene` Query capability in frozen ToolSpecs; never replay the original Action or infer entity pose or possession. (local)
- [eval] [test] 增加 no-motion Core/Skill-loop 回归与七维审查，修复随机/固定恢复节点 ID 的幂等性与 settlement 继承风险。 (local)
- [Eval] [Test] Add no-motion Core/Skill-loop regressions and a seven-dimension review, fixing idempotency and settlement-inheritance risks from random or fixed recovery node IDs. (local)
- [docs] [docs] 保存 `task_f6fcda0556d14245` 的 910-step lift failure、Runtime recovery facts、视频 manifest、失败链、PAOS ownership 与通用修复边界。 (local)
- [Docs] [Docs] Preserve the 910-step lift failure, Runtime recovery facts, video manifest, failure chain, PAOS ownership, and generic repair boundary for `task_f6fcda0556d14245`. (local)

### 文件与关键 Diff / Files and Key Diff

| 文件 / File | 行号 / Lines | 摘要 / Summary |
| --- | --- | --- |
| `PhyAgentOS/agent/recovery_decisions.py` | L11-L62, L219-L250 | 唯一 refresh capability 发现、Query-only replan、确定性冲突安全节点 ID / Unique refresh capability discovery, Query-only replan, deterministic collision-safe node ID |
| `tests/test_agent_foundation.py` | L28-L32, L2339-L2544 | bootstrap、歧义、旧绑定、identity 回归 / Bootstrap, ambiguity, stale-binding, and identity regressions |
| `examples/forge-skills/pick-place-workflow/tests/test_unknown_action_recovery.py` | L12-L24, L61-L155, L307-L364 | 完整 PlanningLoop 新 revision 无运动回归 / Full PlanningLoop replacement-revision no-motion regression |
| `docs/forge/UNKNOWN_ACTION_REFRESH_BOOTSTRAP_DIAGNOSIS_20261009.md` | L1-L161 | 诊断、架构边界与七维审查 / Diagnosis, architecture boundary, and seven-dimension review |
| `changelog/2026-10_part5.md` | v13.0.14 | 完整双语记录 / Complete bilingual record |

```diff
- unknown world-changing Action -> model must return complete replacement graph
+ unknown world-changing Action -> unique ToolSpec refresh Query bootstrap revision
+ same source revision -> stable node identity
+ source-node collision -> first free deterministic suffix
+ ambiguous or stale-bound refresh capability -> existing fail-closed model path
```

### 验证 / Validation
- Recovery-focused Core/AgentLoop/Skill suites: `263 passed in 13.64s`.
- Ruff、compileall、`git diff --check` 通过；没有 live AgentTask、Gateway、simulator 或物理运动。 / Ruff, compileall, and `git diff --check` pass; no live AgentTask, Gateway, simulator, or physical motion was run.

详见 [v13.0.14 月度日志](changelog/2026-10_part5.md)和[诊断](docs/forge/UNKNOWN_ACTION_REFRESH_BOOTSTRAP_DIAGNOSIS_20261009.md)。
See the [v13.0.14 detailed log](changelog/2026-10_part5.md) and [diagnosis](docs/forge/UNKNOWN_ACTION_REFRESH_BOOTSTRAP_DIAGNOSIS_20261009.md).
