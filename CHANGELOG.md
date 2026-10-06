# Changelog
## Archive
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.7.1 (2026-10-06 00:00) - codex

### 变更摘要 / Change Summary
- [env] [chore] 停止无 ownership 的旧 `pick-place-workflow 2.10.8`，安装 Skill `2.10.9` 与 Node `0.10.3`，保留 `robotwin-blocks-ranking-graspnet` profile 和本地 Qwen。 (local)
- [env] [chore] Gracefully stop the old ownership-free `pick-place-workflow 2.10.8`, install Skill `2.10.9` and Node `0.10.3`, and retain the `robotwin-blocks-ranking-graspnet` profile and local Qwen. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `changelog/2026-10.md:L3-L43`：记录停止、安装、preflight 分支、启动和运行验证 / record stop, installation, preflight branch, startup, and runtime validation.
- [修改 / Modified] `CHANGELOG.md:L7-L25`：加入最近版本的完整部署摘要 / add the latest deployment summary to the recent-version index.

### 关键 Diff / Key Diff
```diff
-pick-place-workflow 2.10.8 (running)
+pick-place-workflow 2.10.9 (running)
-robotwin20_persistent_host 0.10.2
+robotwin20_persistent_host 0.10.3
```

### 验证 / Validation
- `paos skill status`：Skill `2.10.9`、Dora running、Gateway ready，11 个 Tool context 全部 ready；`paos forge-node verify`：Node `0.10.3` SHA-256 verified。
- `paos skill status`: Skill `2.10.9`, Dora running, Gateway ready, all 11 Tool contexts ready; `paos forge-node verify`: Node `0.10.3` SHA-256 verified.
- Runtime ownership 为空，AgentTask 无非终态；Qwen `/v1/models` 返回 `qwen3-vl-4b-awq`；未创建 AgentTask、未调用 Query/Action、未执行运动。
- Runtime ownership is empty with no non-terminal AgentTask; Qwen `/v1/models` returns `qwen3-vl-4b-awq`; no AgentTask, Query/Action, or motion was performed.
- Skill SHA-256 `be328fdc12f9a8065365e1be8c2da1017ef660bdb9430119a8bc964a5b59e28a`；Node SHA-256 `f1379e2aff8162397bab08e313118f6222f7b0f5192673e7a7b82ea1543fb69a`。

### Git 提交 / Git Commit
- Commit: pending (deployment log commit)
- Branch: `feature/planning-loop`

## v12.7.0 (2026-10-04 23:44) - codex

### 变更摘要 / Change Summary
- [sense] [fix] Adapter 按当前 binding 的 observation/frame/calibration 血缘唯一选择多视角 depth，support 与 collision 共用解析边界；缺失或歧义仍 fail-closed。 (local)
- [sense] [fix] The Adapter uniquely selects multi-view depth from current binding observation/frame/calibration lineage, sharing the resolver across support and collision while failing closed on missing or ambiguous lineage. (local)
- [policy] [fix] Coordinator 在 materialize/replan admission 校验 ToolSpec projection source 可达性与 preserve 事务语义；preparation 暴露结构化失败所有权，planning loop 依据持久化事实有界收敛。 (local)
- [policy] [fix] Coordinator validates ToolSpec projection-source reachability and preserve transaction semantics during materialize/replan admission; preparation exposes structured failure ownership and the planning loop converges from persisted facts. (local)
- [chore] [release] 发布源码与临时包元数据：Skill `2.10.9`、Node `0.10.3`、Adapter `0.7.16`；未安装或启动 Runtime。 (local)
- [chore] [release] Publish source and temporary package metadata for Skill `2.10.9`, Node `0.10.3`, and Adapter `0.7.16`; no Runtime installation or startup was performed. (local)

### 文件变更详情 / File Changes
- [新增 / Added] `docs/forge/MULTIVIEW_PREPARATION_LINEAGE_DIAGNOSIS_20261004.md:L1-L64`、`REPLAN_PROJECTION_CONVERGENCE_DIAGNOSIS_20261004.md:L1-L95`、`IMPLEMENTATION_REVIEW_V12_7_0.md:L1-L80`：两份诊断与七维审核 / two diagnoses and seven-dimension review.
- [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py:L25-L36,L673-L724,L901-L1001`：通用多视角血缘解析与 evidence-owned failure / generic multi-view lineage resolution and evidence-owned failures.
- [修改 / Modified] `PhyAgentOS/agent/plan_proposal.py:L147-L168,L326-L431`、`PhyAgentOS/forge/task.py:L2663-L2695`：projection source admission 与 preserve 一致性 / projection-source admission and preserve consistency.
- [修改 / Modified] `PhyAgentOS/agent/loop.py:L200-L221,L798-L801,L898-L973`、`planning_loop.py:L715-L828,L1437-L1455`、`recovery_decisions.py:L100-L135`：planning no-progress、历史 replay 与 failure-guided recovery / planning no-progress, historical replay, and failure-guided recovery.
- [修改 / Modified] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L32-L53,L529-L623` 与 `manipulation.prepare.tool.yaml:L406-L421`：结构化失败语义 / structured failure semantics.
- [修改 / Modified] Adapter/Skill/Core tests：覆盖多视角、projection、preserve、Runtime failure 与默认一次纠正后收敛 / cover multi-view, projection, preserve, Runtime failure, and convergence after one corrective turn.

### 关键 Diff / Key Diff
```diff
-assert len(depths) == 1
+depth = resolve_by(observation_ref, frame_id, calibration_ref)
+validate_projection_source_reachability(tool_spec.source_slots)
+failure_owner, retryable_in_revision, requires_replan, recommended_action
+node_selection_no_progress  # after one unchanged corrective turn
```

### 七维 Code Review / Seven-Dimension Review
- 七个维度通过，无未处理 Blocker/Major。没有 RGB/颜色/布局/相机专用分支；Host 不自动观察、筛选、replan 或执行 Action；既有 freshness、calibration、collision、IK、authorization、Gateway 与 terminal settlement 门禁保持不变。
- All seven dimensions pass with no unresolved Blocker/Major. No RGB/color/layout/camera-specific branch and no host-driven observation, selection, replan, or Action; existing safety and settlement gates remain unchanged.

### 验证 / Validation
- 聚焦 Core `263 passed`、完整 Core `773 passed`；聚焦 Adapter/Skill `250 passed`；完整 Adapter/Skill `1136 passed, 1 skipped, 5 个在干净 HEAD 同样失败的既有基线`；Ruff、compileall、`git diff --check` 通过。
- Node SHA-256 `f1379e2aff8162397bab08e313118f6222f7b0f5192673e7a7b82ea1543fb69a`；Skill SHA-256 `be328fdc12f9a8065365e1be8c2da1017ef660bdb9430119a8bc964a5b59e28a`。未安装、未启动 Runtime/Gateway、未创建任务、未调用 Query/Action、未执行运动。

### Git 提交 / Git Commit
- Commit: `7e23edf`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-05 Asia/Shanghai

## v12.6.3 (2026-10-04 02:32) - codex

### 变更摘要 / Change Summary
- [chore] [release] 发布并安装 `pick-place-workflow 2.10.8`，配套已提交的 PAOS Core v12.6.2 task-scoped AgentLoop 修复；复用未修改的 Node `0.10.2`。 (local)
- [chore] [release] Published and installed `pick-place-workflow 2.10.8` alongside the committed PAOS Core v12.6.2 task-scoped AgentLoop repair, retaining the unchanged Node `0.10.2`. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/skill.yaml:L3`、`pyproject.toml:L3`：`2.10.7` -> `2.10.8`。
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/CHANGELOG.md:L3-L6`：新增中英文配套发布说明 / add bilingual compatibility release notes.
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py:L270`：更新版本一致性断言 / update the version consistency assertion.
- [修改 / Modified] `changelog/2026-10.md:L3-L50`：记录停止、安装、Dora 环境诊断、实际加载、no-motion 验证与 Git 提交 / record stop, installation, Dora environment diagnosis, actual loading, no-motion validation, and the Git commit.

### 关键 Diff / Key Diff
```diff
-version: "2.10.7"
+version: "2.10.8"
-version = "2.10.7"
+version = "2.10.8"
-assert bundle_manifest["version"] == "2.10.7"
+assert bundle_manifest["version"] == "2.10.8"
```

### 验证 / Validation
- Skill `2.10.8` running；11 个 Tool context ready；host PID `2144506` 加载 `PAOS_SKILL_VERSION=2.10.8`；Node `0.10.2` SHA-256 verified；聚焦 no-motion 测试 `87 passed`。
- Runtime ownership sets and non-terminal AgentTasks are empty; local `qwen3-vl-4b-awq` remains available. No AgentTask, Gateway Query/Action, or physical motion was created.

### Git 提交 / Git Commit
- Commit: `50adbf8` (Skill release and installation record)
- Branch: `feature/planning-loop`

## v12.6.2 (2026-10-04 03:10) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 移除 continuation projection 中固定的 `scene.observe/scene.understand/scene.bind` 提示，改由 Skill、ToolSpec 与 freshness contract 决定证据需求；新增通用回归断言。 (local)
- [policy] [fix] Removed fixed observation-chain wording from continuation projection; Skill, ToolSpec, and freshness contracts now determine evidence needs, with a generic regression assertion. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/agent/prompt_context.py:L1266-L1274`：使用 active Skill、ToolSpec 与 `fresh_evidence_requirements` 的通用依赖约束 / use a generic dependency constraint from the active Skill, ToolSpec, and `fresh_evidence_requirements`.
- [修改 / Modified] `tests/test_prompt_context.py:L600-L609`：确认固定观察链不再出现在 continuation 边界提示 / verify the fixed observation chain is absent from the continuation boundary prompt.

### 七维 Code Review / Seven-Dimension Review
- 七个维度均通过；无新 Blocker/Major。该修复不增加 Query、PlanGraph、Action、hash 或专用任务分支 / all seven dimensions pass with no new Blocker/Major; no Query, PlanGraph, Action, hash, or task-specific branch was added.

### 验证 / Validation
- 核心回归 `165 passed`；聚焦套件 `301 passed, 2 failed`，两项均为既有基线失败 / core regressions passed; focused suite had two unchanged baseline failures.

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`
- Commit: `e6d1392`

## v12.6.1 (2026-10-04 02:30) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 只读 context/Query 保持在 Agent 当前决策回合；task-scoped discovery working set 防止历史任务 ToolSpec 污染；不自动调度 Query、PlanGraph 或 Action。 (local)
- [policy] [fix] Kept read-only context/Query in the current Agent decision turn and isolated the task-scoped discovery working set from historical ToolSpecs; no Query, PlanGraph, or Action is auto-dispatched. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/agent/loop.py:L1750-L1779`：区分只读工具与显式 long-horizon 状态转换 / separate read-only tools from explicit long-horizon state transitions.
- [修改 / Modified] `PhyAgentOS/agent/prompt_context.py:L548-L647,L1471-L1477`：压缩后保留当前任务所需 ToolSpec/Skill 投影 / retain current-task ToolSpec/Skill projections after compaction.
- [修改 / Modified] `tests/test_agent_foundation.py:L1536-L1581`、`tests/test_prompt_context.py:L1265-L1415`：增加 continuation、compaction、跨任务隔离回归 / add continuation, compaction, and cross-task isolation regressions.

### 七维 Code Review / Seven-Dimension Review
- 架构、正确性、恢复/幂等、机器人安全、扩展兼容、可观测性/可维护性、AgentLoop 自主性均通过；无新 Blocker/Major / architecture, correctness, recovery/idempotency, robotics safety, extension compatibility, observability/maintainability, and AgentLoop autonomy all pass with no new Blocker/Major.

### 验证 / Validation
- 核心回归 `165 passed`；聚焦套件 `301 passed, 2 failed`，两项为既有基线失败 / core regressions passed; focused suite had two unchanged baseline failures.

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`
- Commit: `e6d1392`

## v12.6.0 (2026-10-04 01:10) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 发现阶段新增 provider-neutral working-set 投影，在压缩后同时保留当前任务所需的不同 ToolSpec 与显式恢复的 Skill 约束；不自动调度 Query、PlanGraph 或 Action。 (local)
- [policy] [fix] Add a provider-neutral discovery working-set projection that retains distinct required ToolSpecs and explicitly recovered Skill constraints after compaction; it does not auto-dispatch a Query, PlanGraph, or Action. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/agent/prompt_context.py:L15,L545-L625,L1447-L1452`：按 Skill binding 的 `required_preplan_queries`/`missing_preplan_queries` 汇总各 `tool_id` 最新成功 context，并在 discovery/replan 的只读任务投影中保留 recovered Skill text / collect each required `tool_id`'s latest successful context and retain recovered Skill text in the read-only discovery/replan task projection.
- [修改 / Modified] `tests/test_prompt_context.py:L1263-L1359`：验证多个不同 ToolSpec 与恢复 Skill 在强制 compaction 后同一请求中可见 / verify multiple distinct ToolSpecs and recovered Skill content remain visible in one request after forced compaction.
- [修改 / Modified] `changelog/2026-10.md:L3-L64` 与 `CHANGELOG.md:L7-L30`：记录诊断、实现、七维 Review 和验证 / record diagnosis, implementation, seven-dimension review, and validation.

### 关键 Diff / Key Diff
```diff
+working_set = _discovery_working_set_projection(messages, task)
+projection["discovery_working_set"] = working_set

+relevant_ids = required | missing
+tool_specs = {tool_id: latest_successful_context[tool_id] ...}
```

### 七维 Code Review / Seven-Dimension Review
- 架构、正确性、恢复/幂等、机器人安全、扩展兼容、可观测性/可维护性、AgentLoop 自主性：通过。无 RGB/benchmark/相机专用逻辑，Coordinator/Gateway 仍是权威，Host 不执行自动动作。
- Architecture, correctness, recovery/idempotency, robotics safety, extension compatibility, observability/maintainability, and AgentLoop autonomy: pass. No RGB/benchmark/camera specialization; Coordinator/Gateway remain authoritative and the host performs no automatic action.

### 验证 / Validation
- `tests/test_prompt_context.py tests/test_agent_foundation.py`: `163 passed`。
- Focused AgentLoop/planning suite: `299 passed, 2 known baseline failures` (`test_planning_loop` reducer expectation; `test_planning_effect_recovery` fixture missing `invocation_id`)。
- Ruff、compileall、`git diff --check`: passed; no Runtime, AgentTask, Gateway Query/Action, or physical motion.

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`
- Commit: `e6d1392`
