# Changelog
## Archive
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.5.14 (2026-10-02 22:43) - codex

### 预期修改 / Planned Changes [完成]
- [env] [chore] 经 Coordinator 取消无未结算执行的旧任务 `task_5dbef31d4241497e`，正常停止并卸载旧 Skill `2.10.6`；不强停、不删除任务/证据历史。 (local)
- [env] [chore] Cancel the old task with no unsettled executions through Coordinator, normally stop and remove Skill `2.10.6`, and retain task/evidence history without force-stop. (local)
- [env] [chore] 发布安装 Skill `2.10.7`，保持未修改且已验证的 Node `0.10.2`；确认 PAOS Core 实际加载 v12.5.13 的恢复与实体映射修复，再使用原 profile/env 启动新 Runtime。 (local)
- [env] [chore] Publish/install Skill `2.10.7`, retain the unchanged verified Node `0.10.2`, verify PAOS Core loads the v12.5.13 recovery/identity fixes, and start the new Runtime with its existing profile/environment. (local)
- [eval] [test] 验证版本、既有 artifact lock、11 个 ToolSpec readiness、本地 Qwen 与模型/代理配置不变，以及无非终态任务；不创建验收 AgentTask，不调用 Query/Action。 (local)
- [eval] [test] Verify versions, the existing artifact lock, all 11 ToolSpecs, local Qwen and unchanged model/proxy settings, and zero non-terminal tasks; create no acceptance AgentTask and invoke no Query/Action. (local)

### 影响文件 / Planned Files
- `examples/forge-skills/pick-place-workflow/skill.yaml`, `pyproject.toml`, `CHANGELOG.md`, `tests/test_grasp_propose.py`
- `changelog/2026-10.md`, `CHANGELOG.md`

### 部署诊断 / Deployment Diagnosis
- [env] [fix] 旧 Dora daemon 的进程环境仍为 Skill `2.10.0` 和本地 Qwen fallback，覆盖部署 env 中的外部备用配置；Runtime key 与当前配置凭据不一致。经只读核对，Dora 唯一运行 flow 属于待替换 Skill，停止后无运行 flow；重建空闲 Dora 服务，再由正式 RuntimeManager 启动，确保进程继承当前部署配置。Qwen/Clash 不重启，密钥只注入进程环境。 (local)
- [env] [fix] The old Dora daemon retains Skill `2.10.0` and local-Qwen fallback environment; its Runtime key differs from the current configured credential. Only the replaced Skill had a running flow, and none remain after stop. Recreate idle Dora services before the formal RuntimeManager launch so the new process inherits current deployment settings; keep Qwen/Clash running and inject credentials only into process environment. (local)

### 实际修改 / Completed Changes
- [env] [chore] 旧任务 `task_5dbef31d4241497e` 已经 Coordinator 取消；正常停止并卸载 Skill `2.10.6`，安装 `2.10.7`，按既有 lock 重新安装校验 Node `0.10.2`。未删除任务、日志、证据或旧发布 archive。 (local)
- [env] [chore] Cancelled the old task through Coordinator, stopped/removed Skill `2.10.6`, installed `2.10.7`, and reinstalled/verified Node `0.10.2` against its existing lock. Task history, logs, evidence, and old release archives were retained. (local)
- [env] [fix] 空闲 Dora 服务重建后，由正式 RuntimeManager 使用原 profile/env 启动新 Runtime；实际 host PID `125465` 环境确认为 Skill `2.10.7`、外部 fallback `gpt-6.1-sol/high`、`benchmark_task_definition`、loopback `NO_PROXY`，凭据与配置一致且未写入文件或输出。 (local)
- [env] [fix] Recreated idle Dora services and launched through RuntimeManager with the original profile/env; host PID `125465` confirms Skill `2.10.7`, external fallback `gpt-6.1-sol/high`, benchmark goals, loopback proxy exemption, and the configured credential without writing or printing it. (local)
- [model] [chore] 新进程在仓库目录以外也加载 `/home/yanxu/PhyAgentOS-forge/PhyAgentOS/agent/planning_loop.py`，`_resume_node` 存在；Core v12.5.13 修复不依赖 Skill 嵌入。保持本地 Qwen primary、双图配额和 Clash 服务不变。 (local)
- [model] [chore] A fresh process outside the repository imports the corrected AgentLoop with `_resume_node`; Core v12.5.13 is loaded independently of the Skill bundle. Local Qwen primary, two-image allowance, and Clash services remain unchanged. (local)

### 文件变更详情 / File Changes
- [env] [chore] `examples/forge-skills/pick-place-workflow/skill.yaml:L3`、`pyproject.toml:L3`：`2.10.6` → `2.10.7`；`CHANGELOG.md:L3-L6` 新增中英文配套发布说明；`tests/test_grasp_propose.py:L270` 更新版本断言。 (local)
- [env] [chore] `skill.yaml:L3` and `pyproject.toml:L3` bump `2.10.6` to `2.10.7`; the Skill `CHANGELOG.md:L3-L6` adds bilingual release notes, and `tests/test_grasp_propose.py:L270` updates the version assertion. (local)
```diff
-version: "2.10.6"
+version: "2.10.7"
-version = "2.10.6"
+version = "2.10.7"
-assert bundle_manifest["version"] == "2.10.6"
+assert bundle_manifest["version"] == "2.10.7"
```

### 验证 / Validation
- 发布、安装发现和抓取契约无运动回归：`PYTHONPATH=examples/forge-skills/pick-place-workflow/src:. PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q examples/forge-skills/pick-place-workflow/tests/test_release_bundle.py examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py`：`87 passed`。
- Skill `2.10.7` running，Gateway 和 11 个 ToolSpec ready；无非终态 AgentTask，无活动 invocation/session/task binding；Node verify、Qwen loopback、Ruff 和 `git diff --check` 通过。未创建验收任务或执行 Query/Action/物理运动。
- Release/install-discovery/grasp conformance: `87 passed`; Skill running, all 11 ToolSpecs ready, zero non-terminal tasks or owned invocations/sessions/bindings, Node verification, Qwen loopback, Ruff and diff checks passed. No acceptance task, Query/Action, or physical motion was executed.
- 包路径：`/home/yanxu/tmp/paos-v12.5.14-release.t9q5mc/skills/pick-place-workflow-2.10.7.tar.gz`；既有发布机制 SHA-256：`319084910f3962a98f0cc869c19919b57b7225594cf6720a7a6cf122cee4a862`。Node `0.10.2` 保持 `f052de5b30d917327d9be9ad47733120353eda9487bcc12764adeca470d9695b`。
- Archive and existing release-lock hashes above identify the installed Skill and unchanged Node; no additional hashing or safety gate was introduced.

### 停止边界 / Stop Boundary
- 未使用 `--force`；旧 Node 未在 Dora 的 5 秒停止宽限内响应，被 Dora SIGKILL（22:48:00），旧 flow 标记 failed。停止前无未结算执行；无残留旧 worker，随后新 Runtime 正常 ready。Qwen vLLM PID `2283011` 和 Clash 未重启。
- No force-stop was requested. Dora SIGKILLed the old Node after its 5-second grace period and marked that flow failed; there were no unsettled executions, no old worker remains, and the new Runtime is ready. Qwen vLLM and Clash were not restarted.

### Git 提交 / Git Commit
- Commit: `85e69a3` (Skill release and installation record)
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-02 Asia/Shanghai

## v12.5.13 (2026-10-02 20:57) - codex

### 诊断 / Diagnosis
- [policy] [fix] Review 复现：节点 turn 新生成 selection 后仍第二次请求模型；自动 wrapper 的错误字符串先于已持久化的 terminal/result 对账；单节点 grasp 的 execution alias 未归一化。 (local)
- [policy] [fix] Review reproduced a second model request after selection, wrapper errors outranking durable execution facts, and unresolved execution aliases in standalone grasp nodes. (local)

### 预期修改 / Planned Changes [计划]
- [policy] [fix] 在 `PhyAgentOS/agent/planning_loop.py` 统一每轮与模型返回后的恢复入口：执行记录优先、原 invocation 对账、pending selection 沿现有 Registry/guard 执行；无 registry 时明确阻断，不让模型替代恢复。 (local)
- [policy] [fix] Unify recovery before each turn and after model return: records first, original-invocation reconciliation, then pending selection through the existing registry/guard; explicitly block missing registries instead of model-driven recovery. (local)
- [policy] [fix] 在 `PhyAgentOS/agent/plan_proposal.py` 为 standalone `grasp.propose` 复用唯一 scene.bind execution-to-observed 映射，保持歧义与 freshness 现有语义。 (local)
- [policy] [fix] Reuse unique scene.bind execution-to-observed mapping for standalone grasp proposals, preserving existing ambiguity and freshness semantics. (local)
- [eval] [fix] 在 `tests/test_planning_loop.py`、`tests/test_plan_proposal_bindings.py` 覆盖 provider/turn failure、已成功/已受理/unknown invocation、wrapper 拒绝和单节点 grasp 投影；完成七维 review，并记录仍未通过的独立测试。 (local)
- [eval] [fix] Cover provider/turn failures, succeeded/accepted/unknown invocations, wrapper rejection, and standalone grasp projection; perform the seven-dimension review and report independent failing tests. (local)
- [docs] [docs] 新增本轮诊断与 `IMPLEMENTATION_REVIEW_V12_5_13.md`，保留历史 Review 原文；更新 CHANGELOG 最近五条，提交并推送当前分支。 (local)
- [docs] [docs] Add this diagnosis and the v12.5.13 review without rewriting historical review records; update the latest five changelog entries and commit/push the current branch. (local)

### 执行边界 / Execution Scope
- 本轮仅源代码、文档和无运动测试；不创建 AgentTask、不调用真实 Gateway、不中断 Runtime、不改代理或模型，不新增 hash/contract/gate。
- Source, documentation, and no-motion tests only: no live AgentTask/Gateway/Runtime or proxy/model changes and no new hash/contract/gate.

### 实际修改 / Completed Changes
- [policy] [完成] `PhyAgentOS/agent/planning_loop.py:L715-L816` 新增统一 `_resume_node` 恢复入口；模型 turn 前后均优先读取节点记录、对账原 invocation，再沿现有 Registry/guard 消费 pending selection。已持久化选择即使模型返回 provider/turn error 或 continuation budget 为 0 也不会再次请求模型。
- [policy] [Complete] `PhyAgentOS/agent/planning_loop.py:L715-L816` adds one `_resume_node` recovery path; before and after each model turn it prioritizes node records, reconciles the original invocation, and consumes pending selections through the existing Registry/guard. A persisted selection is not sent to the model again, including after provider/turn errors or with zero continuation budget.
- [policy] [完成] `PhyAgentOS/agent/plan_proposal.py:L507-L514` 对 standalone `grasp.propose` 使用当前 `scene.bind` 的唯一 execution-to-observed 映射；歧义或过期映射保持未解析并由既有 projection 失败路径拒绝。
- [policy] [Complete] `PhyAgentOS/agent/plan_proposal.py:L507-L514` applies the unique current `scene.bind` execution-to-observed mapping to standalone `grasp.propose`; ambiguous or stale mappings remain unresolved and are rejected by the existing projection path.
- [eval] [完成] `tests/test_planning_loop.py:L1719-L2217` 增加 terminal success/failed/unknown、Action/Session 原 invocation 对账、guard 拒绝、无记录阻断和模型返回后立即恢复测试；`tests/test_plan_proposal_bindings.py:L195-L310` 增加任意实体别名、歧义/过期映射和四类能力完整图入口测试。
- [eval] [Complete] `tests/test_planning_loop.py:L1719-L2217` covers terminal success/failed/unknown, original Action/Session reconciliation, guard rejection, missing-record blocking, and immediate post-turn recovery; `tests/test_plan_proposal_bindings.py:L195-L310` covers arbitrary aliases, ambiguous/stale mappings, and all four complete-graph capability entries.
- [docs] [完成] 新增 `docs/forge/IMPLEMENTATION_REVIEW_V12_5_13.md`，完成架构、正确性、恢复幂等、机器人安全、扩展兼容、可观测性维护、AgentLoop 自主性七维 Review；未修改历史 Review。
- [docs] [Complete] Added `docs/forge/IMPLEMENTATION_REVIEW_V12_5_13.md` with the seven-dimension review; historical reviews remain unchanged.

### 关键 Diff / Key Diff
```diff
- await self.agent_loop.run_node_turn(...)
+ resumed = await self._resume_node(context)
+ if resumed is not None:
+     return resumed
+ turn_result = await self.agent_loop.run_node_turn(...)
+ resumed = await self._resume_node(context)
```
```diff
- if isinstance(result, str) and result.startswith("Error"): raise ...
+ await self._reconcile_executions(...)
+ records = self._node_records(context)
+ if records: return self._result_from_records(context, records)
```
```diff
- entity_ref remains the Runtime execution alias for standalone grasp
+ unique scene.bind execution alias is mapped to the observed entity
```

### 验证 / Validation
- 聚焦无运动回归：`35 passed, 58 deselected`；全量核心套件：`748 passed, 2 failed in 26.94s`。
- Focused no-motion regression: `35 passed, 58 deselected`; full core suite: `748 passed, 2 failed in 26.94s`.
- 两项失败在父版本 `b83cb88` 的隔离 worktree 中以同一解释器和 pytest plugin 复现：fixture 缺少 `invocation_id`；RGB reducer 回放断言期望 `('verify',)` 但实际为 `('arrange-green',)`。它们未由本次修改引入。
- The two failures reproduce at parent `b83cb88` in an isolated worktree: a fixture omits `invocation_id`, and the RGB reducer replay expects `('verify',)` but returns `('arrange-green',)`. Neither was introduced by this patch.
- Ruff、compileall、`git diff --check` 通过；未创建 AgentTask、未调用 Gateway Query/Action、未重启 Runtime、未执行物理动作。
- Ruff, compileall, and `git diff --check` passed; no AgentTask, Gateway Query/Action, Runtime restart, or physical motion was performed.

### Git 提交 / Git Commit
- Commit: `9d72a3d` (`9d72a3dbccdd3c47ca1833e7ec667c6b798356a7`)
- Documentation commits: `b6cb7e6` (`b6cb7e604f6e856b492d5d21ee0a19f84e6409f6`), `cc41246` (`cc41246`)
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-02 Asia/Shanghai

## v12.5.12 (2026-10-02 19:38) - codex

### 诊断基线 / Diagnostic Baseline
- [agent] [诊断] 保存重复失败诊断：当前任务 `task_5dbef31d4241497e` 的 `grasp.propose` 仅为只读成功查询，`world_change_started=false`，没有 `object.acquire/object.place` 或 Gateway Action；后续失败不代表抓取或放置成功。 (local)
- [agent] [diagnosis] Persist repeated failure diagnosis: task `task_5dbef31d4241497e` completed only a read-only `grasp.propose` query with `world_change_started=false`; no `object.acquire/object.place` or Gateway Action occurred, so the failure does not prove grasp or placement. (local)
- [agent] [诊断] 保存重复失败诊断：`scene.bind` 的 observed entity `entity://e1` 与后续模型提交的 execution alias `entity://block-red-1` 未在物化边界统一，导致 `projection source collection has no entity_ref matching selected entity`；同类问题适用于任意实体标识，不限 RGB。 (local)
- [agent] [diagnosis] Persist repeated failure diagnosis: `scene.bind` observed entity `entity://e1` was not canonicalized against the later execution alias `entity://block-red-1` at the materialization boundary, causing `projection source collection has no entity_ref matching selected entity`; this is provider-neutral and not RGB-specific. (local)

### 预期修改 / Planned Changes
- [agent] [fix] 在统一 semantic/full-graph 物化边界规范化 observed/execution/binding/destination 绑定；projection join 只使用 Coordinator 解析出的 canonical observed entity，无法唯一映射时结构化拒绝。 (local)
- [agent] [fix] 将当前 revision 的 pending selection 设为恢复最高优先级，按 node/consumer 精确一次性消费；模型 turn 中断后不得重新 discovery、重新 select 或重发 invocation。 (local)
- [agent] [fix] 将 continuation 路由改为显式 `CONTINUE/REPLAN/FINALIZE/STOP/WAIT_FOR_USER` 决策；Query-only 节点不自动触发观测，只有成功 world-changing Action 才要求 fresh scene evidence，只有成功 `object.place` 才进入 post-placement verification。 (local)
- [eval] [test] 增加跨入口实体规范化、pending selection 恢复、Query-only continuation、Action 后刷新和未完成 place 禁止 post-placement 的无运动回归。 (local)
- [docs] [docs] 保存实体身份/projection 与 continuation 状态收敛诊断，作为后续七维 Code Review 的验收基线。 (local)
- [Agent] [Fix] Normalize observed/execution/binding/destination bindings at one semantic/full-graph materialization boundary; projection joins use only the Coordinator-resolved canonical observed entity, with structured rejection for non-unique mappings. (local)
- [Agent] [Fix] Make the current revision's pending selection the highest-priority recovery input and consume it exactly once by node/consumer; an interrupted model turn must not rediscover, reselect, or replay an invocation. (local)
- [Agent] [Fix] Route continuation through explicit `CONTINUE/REPLAN/FINALIZE/STOP/WAIT_FOR_USER` decisions; Query-only nodes do not auto-refresh, successful world-changing Actions require fresh scene evidence, and only a successful `object.place` permits post-placement verification. (local)
- [Eval] [Test] Add no-motion regressions for cross-entry entity normalization, pending-selection recovery, Query-only continuation, post-Action refresh, and rejection of post-placement routing before a completed place. (local)
- [Docs] [Docs] Persist entity/projection and continuation-convergence diagnoses as the acceptance baseline for the seven-dimension Code Review. (local)

### 实际修改 / Completed Changes
- [agent] [完成] `PhyAgentOS/agent/plan_proposal.py:L321-L335,L528-L536` 新增完整 PlanGraph canonicalization，并在 `manipulation.prepare/object.acquire/object.place` 物化前把唯一 Runtime execution alias 解析回 observed entity；重算规范化后的 graph digest。 (local)
- [agent] [完成] `PhyAgentOS/agent/tools/forge_task.py:L394-L398,L532-L535` 让 begin-revision 与 materialize-plan 的完整 graph 入口复用同一 canonicalization，不再绕过语义节点路径的绑定补全。 (local)
- [agent] [完成] `PhyAgentOS/agent/planning_loop.py:L726-L756` 在模型 turn 前优先消费当前 revision 唯一 pending selection，沿现有 governed Tool wrapper 和 terminal reconciliation 执行，不重新 discovery、selection 或 invocation。 (local)
- [agent] [完成] `PhyAgentOS/agent/loop.py:L1634-L1671` 将 continuation 暴露为显式 `CONTINUE/REPLAN/FINALIZE/STOP/WAIT_FOR_USER` 工具决策；Query-only/reconcile 路由隐藏 refresh Query，只有 world-changing Action 路由可读取新场景。 (local)
- [eval] [完成] `tests/test_plan_proposal_bindings.py:L162-L214` 覆盖 execution alias 与完整 graph 入口规范化；`tests/test_planning_loop.py:L1717-L1801` 覆盖 pending selection 恢复；`tests/test_agent_foundation.py:L1520-L1526` 覆盖 continuation 控制工具集合。 (local)
- [docs] [完成] 新增 `docs/forge/AGENTLOOP_DIAGNOSIS_ENTITY_PROJECTION_20261002.md`、`docs/forge/AGENTLOOP_DIAGNOSIS_CONTINUATION_CONVERGENCE_20261002.md` 和 `docs/forge/IMPLEMENTATION_REVIEW_V12_5_12.md`，保存两次诊断和七维 review。 (local)
- [Agent] [Complete] `PhyAgentOS/agent/plan_proposal.py:L321-L335,L528-L536` adds complete-PlanGraph canonicalization and resolves a unique Runtime execution alias back to the observed entity before `manipulation.prepare/object.acquire/object.place`; the normalized graph digest is recomputed. (local)
- [Agent] [Complete] `PhyAgentOS/agent/tools/forge_task.py:L394-L398,L532-L535` routes complete graph inputs for begin-revision and materialize-plan through the same canonicalization used by semantic nodes. (local)
- [Agent] [Complete] `PhyAgentOS/agent/planning_loop.py:L726-L756` consumes the active revision's unique pending selection before a model turn through the existing governed Tool wrapper and terminal reconciliation, without rediscovery, reselection, or invocation replay. (local)
- [Agent] [Complete] `PhyAgentOS/agent/loop.py:L1634-L1671` exposes explicit `CONTINUE/REPLAN/FINALIZE/STOP/WAIT_FOR_USER` continuation tools; Query-only/reconciliation routes hide refresh Query while world-changing Action routes may read fresh scene evidence. (local)
- [Eval] [Complete] `tests/test_plan_proposal_bindings.py:L162-L214` covers execution-alias and complete-graph normalization; `tests/test_planning_loop.py:L1717-L1801` covers pending-selection recovery; `tests/test_agent_foundation.py:L1520-L1526` covers the continuation control-tool set. (local)
- [Docs] [Complete] Added `docs/forge/AGENTLOOP_DIAGNOSIS_ENTITY_PROJECTION_20261002.md`, `docs/forge/AGENTLOOP_DIAGNOSIS_CONTINUATION_CONVERGENCE_20261002.md`, and `docs/forge/IMPLEMENTATION_REVIEW_V12_5_12.md` for the two diagnoses and seven-dimension review. (local)

### 关键 Diff / Key Diff
```diff
- graph = PlanGraph.model_validate(plan_graph)
+ graph = canonicalize_plan_graph(task, PlanGraph.model_validate(plan_graph))
```
```diff
- await self.agent_loop.run_node_turn(...)
+ pending = self._pending_selection(context)
+ await governed_execution_tool(pending)
```
```diff
- allowed continuation tools always included forge_tool_query
+ forge_tool_query is exposed only when the latest settled result is a
+ successful world-changing Action; task tools encode the Agent's next decision.
```

### 七维 Code Review / Seven-Dimension Code Review
- Architecture：通过。统一入口位于 Agent semantic-plan/Coordinator boundary，Runtime/Gateway ownership unchanged。
- Correctness：通过。Projection joins use canonical observed entity; complete graph and semantic node paths agree。
- Recovery/Idempotency：通过。Pending selection is consumed once through existing selection binding; no Action replay or unknown-result bypass。
- Robotics Safety：通过。Freshness, calibration, workspace, collision, IK, authorization, admission, and terminal settlement are unchanged。
- Extension Compatibility：通过。Logic uses scene.bind correspondence and Tool semantics; no RGB/profile/task-name branch。
- Observability/Maintainability：通过。Diagnosis docs, structured continuation tools, persisted selection and existing failure codes remain inspectable。
- AgentLoop Autonomy：通过。Query-only continuation requires an explicit Agent control outcome; only proven world-change facts authorize refresh。
- Review result：Blocker 0，Major 0，Minor 0。

### 验证 / Validation
- 聚焦无运动回归：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q tests/test_plan_proposal_bindings.py tests/test_long_horizon_controller.py tests/test_prompt_context.py tests/test_agent_foundation.py`：`178 passed`。
- 全量回归（显式 async plugin）：`726 passed`；两个既有失败保留并记录于 review：`tests/test_planning_effect_recovery.py::test_query_error_survives_live_and_persisted_settlement_and_recovery_prompt` 的 SimpleNamespace 缺 `invocation_id`，以及 `tests/test_planning_loop.py::test_rgb_attribute_sorting_loop_replans_after_drop_and_reducer_replays` 的既有 reducer 断言漂移。
- `compileall`、Ruff、`git diff --check`：通过；未创建 AgentTask、未调用 Gateway Query/Action、未重启 Runtime、未执行物理动作。
- Focused no-motion regression: `178 passed` with the explicit async plugin.
- Full regression with the explicit async plugin: `726 passed`; two pre-existing failures are recorded in the review: the `SimpleNamespace` fixture missing `invocation_id` and the existing RGB reducer expectation drift.
- `compileall`, Ruff, and `git diff --check`: passed; no AgentTask, Gateway Query/Action, Runtime restart, or physical motion was performed.

### Git 提交 / Git Commit
- Commit: `5288018`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-02 19:38 Asia/Shanghai

## v12.5.11 (2026-10-02 09:30) - codex

### 预期修改 / Planned Changes
- [env] [chore] 安全停止当前 `pick-place-workflow 2.10.5` Runtime，构建并安装包含 v12.5.10 AgentLoop 修复的新 Skill 发布包；重新安装并校验锁定的 `robotwin20_persistent_host 0.10.2` Node，随后启动 `robotwin-blocks-ranking-graspnet`。 (local)
- [env] [chore] Safely stop the current `pick-place-workflow 2.10.5` Runtime, build and install a new Skill release containing the v12.5.10 AgentLoop fix, reinstall and verify the locked `robotwin20_persistent_host 0.10.2` Node, then start `robotwin-blocks-ranking-graspnet`. (local)
- [eval] [test] 验证 Skill/Node 版本、artifact lock、Gateway/ToolSpec readiness、Qwen loopback、无非终态任务；不创建 AgentTask，不调用 Query/Action。 (local)
- [eval] [test] Verify Skill/Node versions, artifact lock, Gateway/ToolSpec readiness, Qwen loopback, and no non-terminal tasks; create no AgentTask and invoke no Query/Action. (local)

### 实际修改 / Completed Changes
- [env] [完成] 已通过 Coordinator 取消遗留非终态任务 `task_bd10f103947c41f7`，正常停止旧 `pick-place-workflow 2.10.5` Runtime；未使用 `--force`。 (local)
- [env] [完成] 已卸载旧 Skill 并安装 `pick-place-workflow 2.10.6`，包路径为 `/home/yanxu/tmp/paos-v12.5.11-release.LNzjZu/skills/pick-place-workflow-2.10.6.tar.gz`，SHA-256 为 `42a990f4bf1c2305e2f0af34832943acf63081fa6b087c985289113b962994f1`。 (local)
- [env] [完成] 已重新安装并校验 Node `robotwin20_persistent_host 0.10.2`，SHA-256 为 `f052de5b30d917327d9be9ad47733120353eda9487bcc12764adeca470d9695b`。 (local)
- [env] [完成] 已用 profile `robotwin-blocks-ranking-graspnet` 和 `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env` 启动新 Runtime；Gateway 与 11 个 ToolSpec context 全部 ready。 (local)
- [eval] [完成] Skill 发布回归 `PYTHONPATH=examples/forge-skills/pick-place-workflow/src ... pytest ...`：`87 passed`；Node verify、Qwen `qwen3-vl-4b-awq` loopback 和任务数据库非终态数 `0` 均通过。 (local)
- [Env] [Complete] Cancelled the stale non-terminal task `task_bd10f103947c41f7` through the Coordinator and normally stopped the old `pick-place-workflow 2.10.5` Runtime without `--force`. (local)
- [Env] [Complete] Removed the old Skill and installed `pick-place-workflow 2.10.6` from `/home/yanxu/tmp/paos-v12.5.11-release.LNzjZu/skills/pick-place-workflow-2.10.6.tar.gz` with SHA-256 `42a990f4bf1c2305e2f0af34832943acf63081fa6b087c985289113b962994f1`. (local)
- [Env] [Complete] Reinstalled and verified Node `robotwin20_persistent_host 0.10.2` with SHA-256 `f052de5b30d917327d9be9ad47733120353eda9487bcc12764adeca470d9695b`. (local)
- [Env] [Complete] Started the new Runtime with profile `robotwin-blocks-ranking-graspnet` and `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env`; Gateway and all 11 ToolSpec contexts are ready. (local)
- [Eval] [Complete] Skill release regression: `87 passed`; Node verification, Qwen `qwen3-vl-4b-awq` loopback, and zero non-terminal tasks all passed. (local)

### 文件变更详情 / File Change Details
- [修改] `examples/forge-skills/pick-place-workflow/skill.yaml:L3`、`pyproject.toml:L3`：Skill 版本 `2.10.5` → `2.10.6`。
- [修改] `examples/forge-skills/pick-place-workflow/CHANGELOG.md:L3-L6`：记录 AgentLoop continuation 路由发布说明。
- [修改] `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py:L270`：更新发布版本回归断言。
- [Modified] `examples/forge-skills/pick-place-workflow/skill.yaml:L3`, `pyproject.toml:L3`: bump Skill version from `2.10.5` to `2.10.6`.
- [Modified] `examples/forge-skills/pick-place-workflow/CHANGELOG.md:L3-L6`: record the AgentLoop continuation routing release.
- [Modified] `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py:L270`: update the release-version regression assertion.

### 验证边界 / Validation Boundary
- 未创建新的 AgentTask，未调用 Gateway Query/Action，未执行物理动作；本次仅做 Runtime 生命周期、安装、版本和 readiness 验证。
- No new AgentTask, Gateway Query/Action, or physical motion was created; validation was limited to Runtime lifecycle, installation, version, and readiness checks.

## v12.5.10 (2026-10-02 09:03) - codex

### 诊断基线 / Diagnostic Baseline
- [agent] [诊断] 保存诊断一：只读 `grasp.propose` 成功且 `world_change_started=false` 后，AgentLoop continuation 仍要求先执行 `scene.observe → scene.understand → manipulation.capabilities → scene.bind`，导致没有进入直接后继的 `manipulation.prepare`。 (local)
- [agent] [diagnosis] Saved diagnosis one: after read-only `grasp.propose` succeeded with `world_change_started=false`, AgentLoop continuation still required `scene.observe → scene.understand → manipulation.capabilities → scene.bind`, preventing direct continuation to `manipulation.prepare`. (local)
- [agent] [诊断] 保存诊断二：未产生 `object.acquire/object.place` terminal result 时，模型仍把 continuation 描述为“放置后的实时证据链”；LongHorizon 返回 `blocked` 但 Coordinator 任务仍为 `executing`，形成状态分裂。 (local)
- [agent] [diagnosis] Saved diagnosis two: before any terminal `object.acquire/object.place` result, the model still described continuation as a post-placement evidence chain; LongHorizon returned `blocked` while the Coordinator task remained `executing`, creating state divergence. (local)

### 预期修改 / Planned Changes
- [agent] [fix] 将 continuation 路由改为读取最近结算节点的 `semantics`、`scene_write_behavior`、`world_change_started`、`new_scene_revision` 和可用后继节点；只有成功世界变化 Action 才强制刷新场景，Query-only 节点允许 Agent 直接选择后继或 replan。 (local)
- [agent] [fix] 将 continuation prompt 的“强制先观察”改为 Coordinator 事实驱动的选择边界，明确未发生 Action 时不得声称进入放置后证据链；保留 Agent 选择 continue/replan/stop 的自主权。 (local)
- [agent] [fix] 让 LongHorizon 的 blocked/continuation failure 通过 Coordinator 持久化收敛，并补充结构化诊断字段；不重发 Action、不改变 Runtime/Gateway 安全门禁。 (local)
- [eval] [test] 增加通用回归：Query-only 后直接续接、world-changing Action 后强制刷新、未发生 place 时禁止 post-place 路由、continuation blocked 状态收敛。 (local)
- [agent] [fix] 补充通用 `placement_terminal` 事实投影；只有当前 revision 中已成功结算且来源工具为 `object.place` 的 terminal record 才允许 continuation 描述放置后验证，其他 world-changing Action 仍只触发普通场景刷新。 (local)
- [eval] [test] 增加 acquire 与 place 的 continuation 路由回归，确保未完成放置不会进入 post-placement evidence chain。 (local)
- [Agent] [Fix] Route continuation from the latest settled node's `semantics`, `scene_write_behavior`, `world_change_started`, `new_scene_revision`, and available successors; only a successful world-changing Action mandates refresh, while Query-only nodes let the Agent choose continuation or replan. (local)
- [Agent] [Fix] Replace the unconditional refresh instruction with a Coordinator-fact-driven choice boundary; prohibit post-placement claims without an Action while preserving Agent autonomy to choose continue/replan/stop. (local)
- [Agent] [Fix] Persist LongHorizon blocked/continuation failures through the Coordinator with structured diagnostics; do not replay Actions or alter Runtime/Gateway safety gates. (local)
- [Eval] [Test] Add provider-neutral regressions for direct Query-only continuation, mandatory refresh after world-changing Actions, rejection of post-place routing before a place result, and blocked-state convergence. (local)
- [Agent] [Fix] Add the provider-neutral `placement_terminal` fact projection; continuation may describe post-placement verification only when the current revision has a successfully settled `object.place` terminal record, while other world-changing Actions still require ordinary scene refresh. (local)
- [Eval] [Test] Add acquire/place continuation regressions to keep incomplete placement out of the post-placement evidence chain. (local)

### 实际修改 / Completed Changes
- [agent] [完成] `PhyAgentOS/agent/prompt_context.py:L1040-L1048,L1135-L1147,L1161-L1187` 增加当前 revision 的 `placement_terminal` 投影；仅成功结算的 `object.place` Action 允许 post-placement 语义，`object.acquire` 和其他世界变化 Action 只允许普通 post-action 刷新。 (local)
- [agent] [完成] `PhyAgentOS/agent/loop.py:L1573-L1590,L1617-L1626` 按 Coordinator 事实分别生成 place 后验证、普通 Action 刷新、Query-only 续接和 reconcile/replan 提示；删除把所有刷新都描述为放置后证据的路径。 (local)
- [agent] [完成] `PhyAgentOS/agent/long_horizon.py:L352-L385,L409-L428` 将 continuation/runner 失败持久化为 `awaiting_replan` 或终态失败，并把 `last_failure` 写入结构化结果；存在未结算 Action/Session 时不重规划或重发。 (local)
- [eval] [完成] `tests/test_prompt_context.py:L559-L664` 覆盖 Query-only、acquire 与成功 place terminal 三种路由；`tests/test_long_horizon_controller.py:L302-L343,L420-L496` 覆盖 continuation/runner 状态收敛。 (local)
- [Agent] [Complete] `PhyAgentOS/agent/prompt_context.py:L1040-L1048,L1135-L1147,L1161-L1187` adds the current-revision `placement_terminal` projection; only a successfully settled `object.place` Action permits post-placement semantics, while acquire and other world-changing Actions permit ordinary post-action refresh only. (local)
- [Agent] [Complete] `PhyAgentOS/agent/loop.py:L1573-L1590,L1617-L1626` emits Coordinator-fact-driven instructions for place verification, ordinary Action refresh, Query-only continuation, and reconciliation/replan; it no longer labels every refresh as post-placement evidence. (local)
- [Agent] [Complete] `PhyAgentOS/agent/long_horizon.py:L352-L385,L409-L428` persists continuation/runner failures as `awaiting_replan` or terminal failure and exposes structured `last_failure`; unresolved Action/Session records are never replanned or replayed. (local)
- [Eval] [Complete] `tests/test_prompt_context.py:L559-L664` covers Query-only, acquire, and successful place-terminal routes; `tests/test_long_horizon_controller.py:L302-L343,L420-L496` covers continuation/runner state convergence. (local)

### 关键 Diff / Key Diff
```diff
+placement_terminal = (
+    latest_settlement.status == "completed"
+    and latest_record.tool_id == "object.place"
+    and latest_record.semantics == "action"
+    and latest_record.status == "succeeded"
+)
```
```diff
-These reads are mandatory after object.place ...
+This is ordinary post-action refresh; do not describe it as post-placement verification.
```

### 七维 Code Review / Seven-Dimension Review
- 架构 Architecture：通过。事实投影位于 AgentLoop 控制面，Coordinator/Runtime/Gateway 仍是状态、证据和动作所有者；没有 RGB 或 benchmark 分支。
- 正确性 Correctness：通过。`placement_terminal` 同时要求当前 revision settlement、`object.place`、成功 Action 和已知终态；Query-only 不触发观察刷新，world-changing Action 仍触发刷新。
- 恢复与幂等 Recovery/Idempotency：通过。续接失败收敛到 Coordinator 的 `awaiting_replan`/失败状态；未结算 Action/Session 不自动 replan、不重发 invocation。
- 机器人安全 Robotics Safety：通过。未改变 motion authorization、freshness、workspace、collision、IK、Gateway admission 或 terminal settlement 门禁。
- 扩展兼容 Extension Compatibility：通过。逻辑按通用 `object.place` capability 和 execution record 工作，不依赖颜色、任务名或 RobotWin profile。
- 可观测性与可维护性 Observability/Maintainability：通过。投影暴露 route、latest settlement、placement terminal 和 `last_failure`，提示与结构化事实一致。
- AgentLoop 自主性 AgentLoop Autonomy：通过。Query-only 后由 Agent 选择后继/replan/finalize；只有已证明的世界变化或失败事实约束下一步，不硬编码 RGB 流程。
- Review result：Blocker 0，Major 0，Minor 0（本次改动范围）。

### 验证 / Validation
- 聚焦回归：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q tests/test_prompt_context.py tests/test_long_horizon_controller.py`：`62 passed`。
- 控制面回归：同环境运行 `tests/test_agent_foundation.py tests/test_planning_dispatch.py tests/test_planning_selection.py tests/test_multi_source_projection.py`：`217 passed`。
- Ruff、compileall、`git diff --check`：通过。
- 三文件扩展回归另有既有失败：`tests/test_planning_loop.py::test_rgb_attribute_sorting_loop_replans_after_drop_and_reducer_replays`，断言期望 `('verify',)`、实际 `('arrange-green',)`；本次未修改 `planning_loop.py`，不归因于本修复。
- 未启动 Runtime、未创建 AgentTask、未调用 Gateway Query/Action、未执行物理动作。
- Focused regression: `... tests/test_prompt_context.py tests/test_long_horizon_controller.py`: `62 passed`.
- Control-plane regression: `... tests/test_agent_foundation.py tests/test_planning_dispatch.py tests/test_planning_selection.py tests/test_multi_source_projection.py`: `217 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- The wider three-file run retains one pre-existing failure in `tests/test_planning_loop.py::test_rgb_attribute_sorting_loop_replans_after_drop_and_reducer_replays`; expected `('verify',)`, actual `('arrange-green',)`. `planning_loop.py` was not modified.
- No Runtime restart, AgentTask creation, Gateway Query/Action, or physical motion was performed.

### Git 提交 / Git Commit
- Commit: `4faa3ac` (implementation and changelog), `ab66827` (documentation follow-up)
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-02 Asia/Shanghai
