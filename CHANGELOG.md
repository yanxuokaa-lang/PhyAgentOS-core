# Changelog
## Archive
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.9.2 (2026-10-07 15:45) - codex

### 变更摘要 / Change Summary
- [env] [chore] 正常取消唯一 `awaiting_replan` 旧任务；在 invocation/session/task-binding ownership 清空且非终态任务为 0 后，无 `--force` 停止旧 Runtime。 (local)
- [env] [chore] Normally cancel the only old `awaiting_replan` task and stop the old Runtime without `--force` after invocation/session/task-binding ownership is empty and non-terminal tasks reach zero. (local)
- [chore] [release] 安装 Skill `pick-place-workflow 3.0.0`，保持 Node `robotwin20_persistent_host 0.10.8`、profile、operator env、权限和模型配置不变。 (local)
- [chore] [release] Install Skill `pick-place-workflow 3.0.0` while preserving Node `robotwin20_persistent_host 0.10.8`, the runtime profile, operator environment, permissions, and model configuration. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `changelog/2026-10_part2.md:L3-L57`：记录任务取消、正常 stop、安装/启动、版本/摘要和 no-motion 验收 / record task cancellation, normal stop, install/start, versions/digests, and no-motion acceptance.
- [修改 / Modified] `CHANGELOG.md:L8-L37`：维护最近五个版本 / maintain the latest five versions.

### 部署关键 Diff / Deployment Key Diff
```diff
-pick-place-workflow 2.10.14; runtime_1c512b49353c4b23; task_cb2ff2de02cd44ca awaiting_replan
+pick-place-workflow 3.0.0; runtime_c1c591d68c0b46aa; nonterminal_tasks=0
 robotwin20_persistent_host 0.10.8; robotwin-blocks-ranking-graspnet
```

### 验证 / Validation
- Runtime `runtime_c1c591d68c0b46aa` running，Dora flow running，Gateway ready，11/11 Tool context ready；Node lock 与实际 spawn 均为 `0.10.8`，Runtime ownership 为空，非终态任务为 0。
- 本地场景理解 primary 保持 `qwen3-vl-4b-awq`；fallback 保持 `gpt-6.1-sol`、`reasoning_effort=high`；operator env 权限保持 `0600`。
- Skill bundle SHA-256 `5b05405ba07e0831260ef2cd8e6fde2d42355c0299656ea693a1807d288b8805`；Node archive SHA-256 `6b5fd5c92d0fd420013a59ee69bffcc87a807c9a7e8b5b48e2883718fb423dc8`。
- 未创建/恢复 AgentTask，未调用 Gateway Query/Action，未执行 simulator step 或物理运动。

### Git 提交 / Git Commit
- Commit: `10daf18`（部署记录 / deployment record）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-07 16:09 Asia/Shanghai

## v12.9.1 (2026-10-07 15:37) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 修正 `object.place` 从 acquisition effect scene 投影 `scene_revision`，并从 Gateway envelope 的 `invocation_id` 投影 acquisition identity；移除对 Persistent Runtime 私有业务结果字段的依赖。 (local)
- [policy] [fix] Correct `object.place` projection to consume the acquisition effect scene and Gateway-envelope `invocation_id`, removing dependence on Persistent Runtime-private business result fields. (local)
- [policy] [fix] 将成功且已知世界变化的 `object.acquire` effect scene 纳入 provider-neutral output contract；缺失时 fail-closed/unknown。 (local)
- [policy] [fix] Add the effect scene to the provider-neutral successful world-changing `object.acquire` output contract; missing identity remains fail-closed/unknown. (local)
- [eval] [test] 增加公开 producer schema compatibility、Persistent missing-effect、effect-scene projection 与 DSL 结构校验回归；Skill 版本按上限规则进位到 `3.0.0`。 (local)
- [eval] [test] Add public producer-schema compatibility, Persistent missing-effect, effect-scene projection, and DSL-shape regressions; roll the Skill version to `3.0.0` under the repository version cap. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/planning/contracts.py:L112-L152`：拒绝 evidence/effect scope 冲突和不完整 unique-item join / reject incoherent source scope and incomplete unique-item joins.
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/object.acquire.tool.yaml:L63-L90`、`object_acquire.py:L207-L250,L480-L585`：公开声明 effect scene，并要求已知成功 world change 发布 `new_scene_revision` / publish the effect scene and require it for known successful world changes.
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/object.place.tool.yaml:L21-L33`、`object_place.py:L302-L315`：从 effect scene 与 outer `invocation_id` 编译 place 参数 / compile place arguments from the effect scene and outer invocation identity.
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/persistent_runtime.py:L124-L229,L268-L276`：移除 acquire 私有 invocation 输出，缺 effect scene 时生成结构化 unknown / remove private invocation output and produce structured unknown when the effect scene is missing.
- [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V12_9_1.md:L1-L58`：记录三个发现、修复与七维验收 / record the three findings, fixes, and seven-dimension acceptance.
- [新增测试 / Added Tests] `tests/test_action_selection_projection.py:L78-L130,L380-L400`、`tests/test_planning_projection.py:L10-L30`、Skill Action/Persistent tests：公开 schema、effect scene、invalid DSL 与 no-motion failure-path regression / public schema, effect scene, invalid DSL, and no-motion failure-path regressions.

### 关键 Diff / Key Diff
```diff
-scene_revision: [result, scene_revision]
-acquire_invocation_ref: [result, acquire_invocation_ref]
+scene_revision: [result, new_scene_revision]
+acquire_invocation_ref: [invocation_id]
```
```diff
+successful + world_change_started + outcome_known + missing new_scene_revision
+-> structured unknown, world_change_started=true, outcome_known=false
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0、Minor 0。v12.9.0 的两个 Major 和一个 Minor 均已修复；AgentLoop 仍保持显式选择与有界 no-progress 收敛，不自动选择、执行、重试、续接、刷新或 replan。 / Zero Blocker, Major, or Minor findings. The two Major and one Minor findings from v12.9.0 are fixed; AgentLoop keeps explicit selection and bounded no-progress convergence with no automatic selection, execution, retry, continuation, refresh, or replan.
- 无 RGB/颜色/排列/benchmark/实体/候选/相机/机械臂专用分支。 / No RGB, color, arrangement, benchmark, entity, candidate, camera, or arm-specific branch was added.

### 验证 / Validation
- Core focused `129 passed`；Core full `787 passed in 28.12s`；Skill full `379 passed in 8.12s`；Ruff、compileall、`git diff --check` 通过。 / Core focused `129 passed`; Core full `787 passed in 28.12s`; Skill full `379 passed in 8.12s`; Ruff, compileall, and `git diff --check` passed.
- 未创建/恢复 AgentTask，未调用 Gateway Query/Action，未启动/停止 Runtime，未执行 simulator step 或物理运动。 / No AgentTask, Gateway Query/Action, Runtime lifecycle operation, simulator step, or physical motion was performed.

### Git 提交 / Git Commit
- Commit: `b6afdc7`（实现与七维审核 / implementation and seven-dimension review）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-07 15:37 Asia/Shanghai

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

### Git 提交 / Git Commit
- Commit: `3550c50`（implementation, diagnoses, and review）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-07 Asia/Shanghai

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
