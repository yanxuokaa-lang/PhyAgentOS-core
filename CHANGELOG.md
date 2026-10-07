# Changelog
## Archive
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.9.0 (2026-10-07 14:59) - codex

### 变更摘要 / Change Summary
- [policy] [feat] 扩展 provider-neutral named projection：按 Coordinator-owned identity 从 producer 集合唯一匹配并展开 consumer 字段，同时支持 world-changing predecessor effect scene。 (local)
- [policy] [feat] Extend provider-neutral named projections to uniquely match and expand producer collection items by Coordinator-owned identity and support world-changing predecessor effect scenes. (local)
- [policy] [fix] 为 `object.acquire` 与 `object.place` 声明前驱投影；Agent 显式选择 Action/source record，Coordinator 只编译受权事实，不自动执行、重试或 replan。 (local)
- [policy] [fix] Declare predecessor projections for `object.acquire` and `object.place`; the Agent explicitly selects the Action/source record while the Coordinator only compiles authorized facts and never auto-executes, retries, or replans. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/planning/contracts.py:L95-L152,L206-L214,L426-L445`、`projection.py:L180-L319`：新增 `scene_relation`、source entity join 与 unique-item collection field map / add scene relations, source-entity joins, and unique-item collection field maps.
- [修改 / Modified] `PhyAgentOS/agent/planning_loop.py:L456-L530`、`planning_dispatch.py:L382-L396`：校验并暴露 Tool/scope/current-or-effect scene/identity 来源语义 / validate and expose Tool, scope, current-or-effect scene, and identity source semantics.
- [修改 / Modified] `object.acquire.tool.yaml:L6-L34`、`object_acquire.py:L263-L297`、`object.place.tool.yaml:L6-L34`、`object_place.py:L288-L321`：声明 prepare→acquire 与 acquire-effect→place 投影 / declare prepare-to-acquire and acquisition-effect-to-place projections.
- [新增测试 / Added Tests] `tests/test_action_selection_projection.py:L1-L446`：唯一/零/重复 join、两段 Action selection 与 effect-scene mismatch fail-closed 回归 / unique, zero, duplicate joins, two Action selections, and effect-scene mismatch regressions.
- [新增 / Added] `ACTION_SELECTION_PROJECTION_DIAGNOSIS_20261007.md:L1-L54`、`ACTION_NODE_AGENTLOOP_CONVERGENCE_DIAGNOSIS_20261007.md:L1-L45`、`IMPLEMENTATION_REVIEW_V12_9_0.md:L1-L69`：两份诊断与七维审核 / two diagnoses and a seven-dimension review.
- [修改 / Modified] Skill manifests/release notes/version test：发布 `pick-place-workflow 2.10.15`；Node `0.10.8`、Adapter `0.9.3` 不变 / publish Skill `2.10.15`; Node and Adapter remain unchanged.

### 关键 Diff / Key Diff
```diff
-Agent browses a predecessor and manually assembles 12/14 Action fields
+ToolSpec declares named predecessor slots and projection paths
+Agent selects one authorized record_id
+Coordinator validates Tool/scope/scene/entity and compiles arguments
```
```diff
-all projection sources must belong to the current scene
+scene_relation=current | predecessor_effect
+predecessor_effect.new_scene_revision must equal the current scene
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0、Minor 0。架构、正确性、恢复/幂等、机器人安全、扩展兼容、可观测性/可维护性、AgentLoop 自主性/收敛全部通过。
- Zero Blocker, Major, or Minor findings. Architecture, correctness, recovery/idempotency, robotics safety, extensibility, observability/maintainability, and AgentLoop autonomy/convergence pass.
- `node_selection_no_progress` 保持为有界收敛保护；没有 RGB/颜色/排列/benchmark/实体/相机/机械臂硬编码，也没有自动选择、Action、重试或 replan。
- `node_selection_no_progress` remains the bounded convergence guard; no RGB/color/order/benchmark/entity/camera/arm hardcoding or automatic selection, Action, retry, or replan was added.

### 验证 / Validation
- Focused planning/projection: `118 passed`; full Core: `785 passed`; full Skill: `375 passed`.
- Ruff、compileall、`git diff --check` passed.
- 未创建/恢复 AgentTask，未调用 Gateway Query/Action，未执行 simulator step、物理运动或 Runtime 生命周期操作。
- No AgentTask, Gateway Query/Action, simulator step, physical motion, or Runtime lifecycle operation was performed.

## v12.8.4 (2026-10-07 13:52) - codex

### 变更摘要 / Change Summary
- [env] [chore] 在三类 ownership 为空且非终态任务为 0 后，无 `--force` 正常停止旧 Runtime，安装 Skill `2.10.14` 与 Node `0.10.8`，并启动新 Runtime `runtime_1c512b49353c4b23`。 (local)
- [env] [chore] After proving all three ownership collections empty and zero non-terminal tasks, normally stopped the old Runtime without `--force`, installed Skill `2.10.14` and Node `0.10.8`, and started new Runtime `runtime_1c512b49353c4b23`. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `changelog/2026-10_part2.md:L3-L52`：记录停止、安装、启动、版本/哈希与 no-motion 验收 / record stop, install, start, version/hash, and no-motion acceptance.
- [修改 / Modified] `CHANGELOG.md:L8-L32`：维护最近五个版本 / maintain the latest five versions.

### 关键 Diff / Key Diff
```diff
-Skill 2.10.12; Node 0.10.6; runtime_e8d8a9855ce641bf
+Skill 2.10.14; Node 0.10.8; runtime_1c512b49353c4b23
```

### 验证 / Validation
- Dora running、Gateway ready、11/11 Tool context ready；Node lock 和运行环境 binary 均验证为 `0.10.8`，ownership 为空，非终态任务为 0。
- 本地场景理解 primary 为 `qwen3-vl-4b-awq`；fallback 与 Agent 默认均为 `gpt-6.1-sol`、`reasoning_effort=high`；operator env 保持 `0600`。
- 未创建/恢复 AgentTask，未调用 Gateway Query/Action，未执行 simulator step 或物理运动。

### Git 提交 / Git Commit
- Commit: `de2dcb6`（deployment record）
- Branch: `feature/planning-loop`
- 时间 / Time: `2026-10-07 13:59 Asia/Shanghai`

## v12.8.3 (2026-10-06 23:39) - codex

### 变更摘要 / Change Summary
- [sense] [fix] prepared execution plan v2 绑定 Readiness 的完整 provider-owned 双臂动态状态；Persistent Action 在任何 simulator step 前验证当前规划世界。 (local)
- [sense] [fix] Bind prepared execution plan v2 to Readiness's complete provider-owned dual-arm dynamic state and validate the current planning world before any Persistent Action simulator step. (local)
- [eval] [test] 增加真实 Readiness artifact → Persistent `_prepare()` 的无运动回归，证明 Action 不二次规划并在 peer-arm/world drift 时零步拒绝。 (local)
- [eval] [test] Add a no-motion regression through the real Readiness-artifact-to-Persistent-`_prepare()` path, proving no second solve and zero-step rejection on peer-arm/world drift. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `dual_arm_state.py:L138-L199,L346`：比较 scene/state/frame/policy/provenance identity、两臂 qpos/drive target/gripper、link identity 与 link pose / compare complete planning-relevant dual-arm state.
- [修改 / Modified] `robotwin_route_planner.py:L155-L340,L471-L481`：Readiness 将同源 `dual_arm_state` 写入 prepared plan v2 / persist the source `dual_arm_state` in prepared plan v2.
- [修改 / Modified] `robotwin_simulation_probe_worker.py:L534-L687`、`robotwin_persistent_engine.py:L520-L560`：Action `_prepare()` 全状态校验和结构化零步拒绝 / full-state Action admission and structured zero-step rejection.
- [新增测试 / Added Tests] `test_dual_arm_state.py:L57-L93`、`test_route_planner.py:L89-L124`、`test_simulation_probe.py:L1828-L1968`、`test_persistent_action_approval.py:L31-L115,L347-L444`、`test_persistent_route_evaluator.py:L135-L185`：v2、动态漂移、真实 `_prepare()`、不二次规划回归 / v2, drift, real `_prepare()`, and no-second-solve regressions.
- [新增 / Added] `PREPARED_PLAN_DYNAMIC_WORLD_DIAGNOSIS_20261006.md:L1-L41`、`PREPARED_PLAN_INTEGRATION_REGRESSION_DIAGNOSIS_20261006.md:L1-L43`、`IMPLEMENTATION_REVIEW_V12_8_3.md:L1-L61`：两份诊断与七维审核 / two diagnoses and seven-dimension review.
- [修改 / Modified] Adapter `0.9.3`、Node `0.10.8`、Skill `2.10.14` manifests, release notes, and version tests.

### 关键 Diff / Key Diff
```diff
-prepared plan v1: selected-arm initial_qpos only
+prepared plan v2: initial_dual_arm_state
-Action loader compares selected-arm qpos
+Action loader compares complete dynamic planning world
+prepared_execution_world_state_drift -> Agent recovery facts
```
```diff
-unit test injects internal _prepared_execution_plan
+RoboTwinPersistentEngine._prepare loads the Readiness artifact
+Action evaluate_route_arm() is forbidden by the integration regression
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0、Minor 0。架构、正确性、恢复/幂等、机器人安全、扩展兼容、可观测性和 AgentLoop 自主性/收敛全部通过。
- Zero Blocker, Major, or Minor findings. Architecture, correctness, recovery/idempotency, robotics safety, extensibility, observability, and AgentLoop autonomy/convergence pass.
- 未加入颜色/排列/benchmark/相机/实体/固定机械臂分支，未自动观察、换臂、换候选、重试、replan 或 Action。
- No color/arrangement/benchmark/camera/entity/fixed-arm branch and no automatic observation, arm/candidate switch, retry, replan, or Action.

### 验证 / Validation
- Adapter changed path `126 passed, 1 deselected`；Core `781 passed`；Skill `375 passed`；release/package `87 passed`；Ruff、compileall、digest 校验和 `git diff --check` 通过。
- Full Adapter `796 passed, 16 failed, 1 deselected`; the 16 failures are existing missing-dependency/fixture issues outside the changed path.
- Node SHA-256 `6b5fd5c92d0fd420013a59ee69bffcc87a807c9a7e8b5b48e2883718fb423dc8`；Skill bundle SHA-256 `dc2714336fc85141f1d416605bbd42cee39d4acbe427fa336a9b67561571a8c0`。
- 未安装/停止/重启 Runtime，未创建/恢复 AgentTask，未调用 Gateway Query/Action，未执行 simulator step 或物理运动。

### Git 提交 / Git Commit
- Commit: `6baf973`（实现、诊断与七维审核 / implementation, diagnoses, and seven-dimension review）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-07 Asia/Shanghai

## v12.8.2 (2026-10-06 20:10) - codex

### 变更摘要 / Change Summary
- [sense] [fix] Readiness 持久化选定机械臂的可执行路线，Persistent Action 校验 scene/route/assignment/arm/frame/起始关节状态后直接消费，禁止对同一路线二次规划。 (local)
- [sense] [fix] Persist the selected arm's executable route in readiness and make Persistent Action consume it after scene/route/assignment/arm/frame/start-state validation, prohibiting a second solve of the same route. (local)
- [comm] [fix] Action 失败以 provider-neutral owner/retry/replan/phase 事实进入 AgentLoop；零步失败不声明实体变化，公开结果不泄露私有轨迹。 (local)
- [comm] [fix] Feed provider-neutral owner/retry/replan/phase facts to the AgentLoop; zero-step failures claim no entity changes and public results expose no private trajectory. (local)

### 文件变更详情 / File Changes
- [新增 / Added] `PREPARE_ACTION_ROUTE_PLAN_DIAGNOSIS_20261006.md:L1-L49`、`ACTION_FAILURE_EVIDENCE_AGENTLOOP_DIAGNOSIS_20261006.md:L1-L57`、`IMPLEMENTATION_REVIEW_V12_8_2.md:L1-L68`：两份诊断与七维审核 / two diagnoses and seven-dimension review.
- [修改 / Modified] `robotwin_route_planner.py:L180-L299`、`robotwin_simulation_probe_worker.py:L104-L121,L533-L660,L1500-L1640`、`robotwin_persistent_engine.py:L487-L564,L627-L730`：Readiness 产出、Action 校验/消费 prepared execution plan，结构化失败并修正零步 effects / produce, validate, and consume the prepared plan, structure failures, and correct zero-step effects.
- [修改 / Modified] `recovery_decisions.py:L25-L46,L107-L139`、`outcome_projection.py:L24-L69,L189-L310` 与 Skill Action contract/projection：将有界失败事实交给 Agent，自主选择恢复且不暴露轨迹 / present bounded failure facts to the Agent for autonomous recovery decisions without exposing trajectories.
- [修改 / Modified] Adapter `0.9.2`、Skill `2.10.13`、Node `0.10.7` manifests, profiles, tests, and release records.

### 关键 Diff / Key Diff
```diff
-Action calls evaluate_route_arm() again
+Action loads readiness execution_plan and executes its validated segments
-zero-step failure changed_entity_refs=[target]
+zero-step failure changed_entity_refs=[]
+owner/retry/replan/phase/arm failure facts -> AgentLoop
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0。七个维度均通过；未增加 RGB/任务/相机硬编码或自动观察、选择、重试、replan、Action。保留限制是简化世界仍不覆盖未识别及 unknown/occluded 障碍物。
- Zero Blocker or Major findings. All seven dimensions pass; no RGB/task/camera hardcoding or automatic observation, selection, retry, replan, or Action was added. The simplified world still excludes unidentified and unknown/occluded obstacles.

### 验证 / Validation
- Core `781 passed`；Skill `375 passed`；Adapter changed path `79 passed, 5 deselected`；Ruff、compileall、`git diff --check` 通过。
- Node SHA-256 `cf2b799baa5283efbd74f24126fea7890423ec198598814bacfea53bef420084`；Skill bundle SHA-256 `1bb7f5803a910889c6fe2d2c29e1b829b75acba8ef289d81b7ce1255aaf2f99f`。
- 未创建/恢复 AgentTask，未调用 Gateway Query/Action，未执行 simulator step 或物理运动，未安装或重启 Runtime。

### Git 提交 / Git Commit
- Commit: `ed49b7a`（实现与诊断 / implementation and diagnoses）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-06 21:27 Asia/Shanghai

## v12.8.1 (2026-10-06 18:30) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 将 `planner_world_only` contact diagnostic 与旧 observed 模式一样传播到最终 prepared candidate evidence，补齐审计链。 (local)
- [sense] [fix] Propagate `planner_world_only` contact diagnostics into final prepared-candidate evidence alongside legacy observed-mode diagnostics, completing the audit chain. (local)
- [eval] [test] 新增真实 artifact 边界的 Runtime 回归，验证 collision configuration、planning-world 安装、planner-world qualification 顺序及 no-motion 结果。 (local)
- [eval] [test] Add a Runtime regression using real artifact boundaries to verify collision configuration, planning-world installation, planner-world qualification ordering, and no-motion results. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `persistent_preparation.py:L251-L263`：传播所有同候选 contact diagnostic refs / propagate all same-candidate contact diagnostic refs.
- [新增测试 / Added Tests] `test_persistent_preparation.py:L216-L231`、`test_persistent_route_evaluator.py:L10-L123`：公共 evidence 与 Runtime 顺序回归 / public-evidence and Runtime-ordering regressions.
- [修改 / Modified] Adapter `0.9.1`、Skill `2.10.12`、Node `0.10.6` manifests and release records.

### 关键 Diff / Key Diff
```diff
-and "observed_collision" in item
+and isinstance(item.get("evidence_ref"), str)
+assert events == ["configure_collision_world", "prepare_planning_world", "qualify_planner_world_contact"]
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0。七个维度均通过；未增加 RGB/任务/相机硬编码，未自动观察、选择、replan 或执行 Action。简化世界仍不覆盖未识别及 unknown/occluded 障碍物。
- Zero Blocker or Major findings. All seven dimensions pass; no RGB/task/camera hardcoding and no automatic observe, select, replan, or Action. The simplified world still excludes unidentified and unknown/occluded obstacles.

### 验证 / Validation
- 专项 `73 passed`；相关链路 `93 passed`；Skill/release/install `87 passed`；完整 Adapter `788 passed, 2 failed, 1 skipped`，两项失败位于既有无关 fixture。
- Node SHA-256 `fd67b41c0d575e7b8d3a9d4da0d0c23f8c6d8df96a4a6ee981f9689ee7ef2412`；Skill bundle SHA-256 `f086762539bfbc2b4388c4e5a0fc44bdda1befb9b97bbd74942c032367dc3ca3`。
- 构建和回归无 AgentTask、Gateway Query/Action、simulator step 或物理运动。
- 已通过 Coordinator 取消旧 `awaiting_replan` 任务并清空 ownership，再无 `--force` 停止旧 Runtime；Dora 在停止宽限期后 SIGKILL 未响应的旧 host，当时无在途 invocation、session、task binding 或 world change。
- Installed Skill `2.10.12` and Node `0.10.6`; Runtime `runtime_e8d8a9855ce641bf`, Dora, Gateway, and 11/11 Tool contexts are ready with zero active ownership and zero non-terminal tasks.
- 启动日志确认实际 host 路径为 `robotwin20_persistent_host-0.10.6-linux-x86_64`；本地场景理解 primary 为 `qwen3-vl-4b-awq`，fallback 为 `gpt-6.1-sol` 且 `reasoning_effort=high`。部署验收未调用 Query/Action 或执行仿真/物理运动。

### Git 提交 / Git Commit
- Commit: `715e8e9`（实现 / implementation）
- Branch: `feature/planning-loop`
