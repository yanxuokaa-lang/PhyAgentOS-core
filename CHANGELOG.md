# Changelog
## Archive
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.5.15 (2026-10-03 10:58) - codex

### 预期修改 / Planned Changes [完成]
- [docs] [docs] 保存契约可用性丢失与无进展循环/任务状态分歧两份诊断，区分日志事实与压缩复现。 (local)
- [docs] [docs] Save both contract-availability and no-progress/status-divergence diagnoses, separating recorded facts from compaction reproductions. (local)
- [policy] [fix] 保留 discovery 正式 context/Skill 读取入口，按 Coordinator 事实与首次成功的不同契约获取识别进展；停滞一次纠正后明确失败，不自动观察、规划或重放动作。 (local)
- [policy] [fix] Keep discovery context/Skill retrieval available; track Coordinator facts and first successful distinct contract reads, correct stagnation once, and return explicit failure without automatic queries, planning, or action replay. (local)
- [eval] [fix] 补充无运动回归和七维 Review；保留未结算 Action 与 replan 恢复边界，不改 RGB、目标注入、Runtime 或已安装 Skill。 (local)
- [eval] [fix] Add no-motion regressions and seven-dimension review; retain unresolved Action/replan recovery boundaries and leave RGB, goal injection, Runtime and installed Skill unchanged. (local)

### 影响文件 / Planned Files
- `PhyAgentOS/agent/prompt_context.py`, `PhyAgentOS/agent/loop.py`, configuration/CLI wiring if needed, related tests.
- `docs/forge/DISCOVERY_CONTRACT_DIAGNOSIS_20261003.md`, `docs/forge/DISCOVERY_PROGRESS_DIAGNOSIS_20261003.md`, `docs/forge/IMPLEMENTATION_REVIEW_V12_5_15.md`, `CHANGELOG.md`.

### Review 补充计划 / Review Follow-up Plan
- [policy] [fix] 复用 `forge_task_get(include_skill_instructions=true)` 按需恢复 Coordinator 已保存的当前 Skill 约束；默认回执保持压缩。恢复正式任务读取入口，不依赖可能已更新的文件版本。 (local)
- [policy] [fix] Reuse an opt-in task getter to recover persisted current Skill instructions; keep default receipts compact and restore formal task reads instead of depending on potentially updated files. (local)
- 影响 / Affected: `PhyAgentOS/agent/tools/forge_task.py`, prompt compaction and related tests; no new Tool or execution gate.

### 防御机制说明 / Control-loop Rationale
- 具体失败：37 次 shell 核查未产生任何 Query，40 轮耗尽仍 executing。已有 iteration 上限不足，因为它不识别 Coordinator 进展且未返回失败码。本次只修复现有循环停止策略与状态收敛，不新增 hash、冻结契约或物理门禁。
- Concrete failure: 37 shell reads produced no Query; iteration exhaustion left the task executing. The existing cap neither measures Coordinator progress nor returns a failure code. Repair loop termination/status convergence only; add no hashes, frozen contracts or physical gates.

### 实际修改 / Completed Changes
- [policy] [fix] discovery 不再按历史计数隐藏正式 context、task getter 或文件读取；按需取回已保存的当前 Skill 约束，不重复注入默认请求。 (local)
- [policy] [fix] Discovery keeps formal context/task/file reads available; an opt-in getter restores persisted current Skill constraints without adding prose to ordinary requests. (local)
- [policy] [fix] 使用任务/revision/binding、执行记录和首次不同契约读取识别进展；连续无进展默认 6 轮纠正一次，再连续 6 轮返回 `discovery_no_progress`。总轮数耗尽返回 `tool_iteration_limit`。 (local)
- [policy] [fix] Track task/revision/binding/record facts and first distinct contract reads; default to one correction after six unchanged rounds, then fail after another unchanged window. Overall exhaustion returns `tool_iteration_limit`. (local)
- [policy] [fix] 用户与 system 两入口共用 Coordinator 状态收敛；保护 replan、等待用户、暂停/取消以及 uncertain invocation，不自动生成后续观察或动作。 (local)
- [policy] [fix] Both entrypoints converge through Coordinator while preserving replan, clarification, pause/cancellation and uncertain invocation ownership; never auto-generate a next observation or Action. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/agent/loop.py` L150-L170、L202-L214、L794-L797、L829-L890、L1152-L1174、L1430、L1953-L1978、L2015、L2183：恢复边界、可配置预算、进展检测与共享失败收敛 / recovery boundaries, configurable budget, progress detection and shared failure convergence.
- [修改 / Modified] `PhyAgentOS/agent/prompt_context.py` L277-L339、L574-L577、L724-L730：删除双计数工具隐藏，保留按需 Skill 文本和正式恢复指引 / remove double-count hiding and retain opt-in Skill prose/formal recovery guidance.
- [修改 / Modified] `PhyAgentOS/agent/tools/forge_task.py` L256-L288：现有 getter 增加默认 false 的约束恢复选项 / opt-in persisted constraints on the existing getter.
- [修改 / Modified] `PhyAgentOS/config/schema.py` L245；`PhyAgentOS/cli/commands.py` L814、L1029：`discovery_no_progress_limit` 默认 6，CLI/Gateway 均接线 / validated default and both entrypoints wired.
- [修改 / Modified] `tests/test_agent_foundation.py` L15、L104-L128、L304-L308、L2445-L2630；`tests/test_prompt_context.py` L439-L512：配对回执、压缩、正式 Query、纠正恢复、反复核查、两入口收敛及安全恢复回归 / paired receipts, compaction, real local Query wrapper, corrective recovery, repeated reads, entrypoint settlement and ownership regressions.
- [新增 / Added] `docs/forge/DISCOVERY_CONTRACT_DIAGNOSIS_20261003.md` L1-L30；`docs/forge/DISCOVERY_PROGRESS_DIAGNOSIS_20261003.md` L1-L27；`docs/forge/IMPLEMENTATION_REVIEW_V12_5_15.md` L1-L39：两份诊断与七维 Review / two diagnoses and seven-dimension review.
- [修改 / Modified] 本月日志的新 v12.5.15 节与 `CHANGELOG.md` 最近五条同步 / this new monthly entry and the latest five complete index entries.

### 关键 Diff / Key Diff
```diff
-discovery_context_calls = _tool_call_names(messages).count("forge_tool_context")
-if discovery_context_calls >= max(5, len(missing_preplan_queries(task)) * 2):
-    allowed.discard("forge_tool_context")
+# Keep formal context/task reads available after compaction.

-async def execute(self, task_id: str) -> str:
+async def execute(self, task_id: str, include_skill_instructions: bool = False) -> str:
+    if include_skill_instructions:
+        data["requested_skill_instructions"] = (
+            task.active_skill_instructions
+            if task.active_skill_instructions is not None
+            else task.primary_skill_instructions
+        )

+if progress != discovery_progress:
+    discovery_progress = progress
+    discovery_stalled_rounds = 0
+    discovery_correction_used = False
+else:
+    discovery_stalled_rounds += 1
+# Existing loop dispatch remains model-selected; stagnation returns a failure.

 if final_content is None and iteration >= self.max_iterations:
+    turn_failure_code = "tool_iteration_limit"
+self._settle_turn_failure(run_result, key)
```

### 验证 / Validation
- 专项 / Focused: `179 passed`; full Core: `764 passed, 2 failed`; Ruff and `git diff --check` passed.
- 两项已知基线失败保持原样：`tests/test_planning_effect_recovery.py:66` 的夹具缺少 `invocation_id`；`tests/test_planning_loop.py:909` 的 reducer 断言不匹配。之前已在 parent `b83cb88` 隔离复现；本轮不修改这些文件，不宣称全绿。
- Two known baseline failures remain: missing fixture invocation identity and the reducer expectation mismatch, previously reproduced on the parent. Neither file is changed and the full suite is not claimed green.
- 验证命令 / Commands:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q tests/test_prompt_context.py tests/test_agent_foundation.py tests/test_long_horizon_controller.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q tests
```
- 七维 Review 已完成，新增路径无未修复 Blocker/Major；脚本模型只证明控制流，不证明真实 provider 的任务成功。 / Seven-dimension review is complete with no remaining new-path Blocker/Major; fixture providers prove control flow, not real-model task success.
- 不取消当前部署任务、不安装/重启 Skill/Node/Runtime/Qwen/Clash，不执行真实 Query/Action，不修改外部 benchmark 目标来源。 / No live-task cancellation, installation, service restart, live Query/Action or benchmark-goal mutation.

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`
- Commit: pending implementation commit; record its identity in the documentation follow-up.

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
