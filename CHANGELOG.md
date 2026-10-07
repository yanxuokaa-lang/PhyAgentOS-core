# Changelog
## Archive
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.9.4 (2026-10-07 18:45) - codex

### 变更摘要 / Change Summary
- [sense] [fix] Readiness 与 Action 复用同一 capability validation/controller qualification evidence 准入，并仅接受声明限位的精确 float32 往返表示。 (local)
- [sense] [fix] Make Readiness and Action reuse the same capability-validation/controller-qualification evidence admission and admit only exact float32 round-trip representations of declared limits. (local)
- [comm] [fix] `outcome_unknown + replay` 在一次只读 reducer replay 后进入 `reconciliation_required`，不重发 Action。 (local)
- [comm] [fix] Make `outcome_unknown + replay` enter `reconciliation_required` after one read-only reducer replay without resending the Action. (local)

### 文件变更详情 / File Changes
- [新增 / Added] `robotwin_motion_policy.py:L1-L174`：共享 capability/qualification evidence 准入与 controller-limit 适配。 (local)
- [修改 / Modified] `robotwin_route_planner.py:L17,L389-L399`、`robotwin_simulation_probe_worker.py:L45-L49,L1113-L1135`：Readiness 与 Action 共用 motion-policy validator。 (local)
- [修改 / Modified] `robotwin_capability_controller.py:L25-L61`：精确 float32 boundary encoding 匹配；`planning_loop.py:L1488-L1503`：未知结果 replay 后统一阻塞对账。 (local)
- [新增测试 / Added Tests] controller、persistent route evaluator 与 planning-loop 回归覆盖伪近界值、evidence gate、单次 replay 与任务收敛。 (local)
- [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V12_9_4.md:L1-L84`：两个 Major、一个 Minor、修复与七维验收。 (local)

### 关键 Diff / Key Diff
```diff
-Readiness validates capability JSON only
+Readiness and Action call validate_motion_policy_bindings()
-outcome_unknown + replay -> replay_required
+outcome_unknown + replay -> reducer-only replay -> reconciliation_required
-near-bound distance window
+exact float32(bound) match
```

### 七维 Code Review / Seven-Dimension Review
- 初审 Blocker 0、Major 2、Minor 1；全部修复。修复后七个维度均通过，Blocker 0、Major 0、Minor 0。 (local)
- Initial review found zero Blocker, two Major, and one Minor issue; all are fixed. All seven dimensions pass after fixes with zero remaining findings. (local)
- 没有 RGB/颜色/排列/benchmark/实体/候选/相机/固定机械臂分支，也没有自动观察、Action、重试、放置或 replan。 (local)

### 验证 / Validation
- Adapter `143 passed, 4 deselected`；Core `164 passed`；Skill/release `75 passed`；Ruff、compileall、`git diff --check` 通过。 (local)
- Node `0.10.10` SHA-256 `d807b1b3e6b9a86f6cc597da8ab6de9643b8b23a75bc72372889ac1d45fd195e`；Skill `3.0.2` SHA-256 `c9992caa9c256780307e1a4de33a15f90971292e5db82c7ebd5f49f0800f1772`。未安装或启动。 (local)
- 当前解释器缺少 `cv2`，4 个既有 video 用例未计入通过证据；未创建任务、调用 Gateway、推进模拟器/物理运动或改变 Runtime 生命周期。 (local)

### Git 提交 / Git Commit
- Commit: `b0fa615`（实现、修复与七维审核 / implementation, fixes, and seven-dimension review）
- Branch: `feature/planning-loop`
- 时间 / Time: `2026-10-07 Asia/Shanghai`

## v12.9.3 (2026-10-07 18:09) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 统一 route readiness、prepared-plan admission 与 live controller 的 MotionCapability 数值边界语义，仅规范化 float32 往返边界误差，实质越界继续 fail-closed。 (local)
- [sense] [fix] Unify MotionCapability numerical-bound semantics across route readiness, prepared-plan admission, and the live controller, canonicalizing only float32 round-trip boundary error while material violations remain fail-closed. (local)
- [comm] [fix] 未知 Action 结果的 stop/replan 决策现在进入 `reconciliation_required` 阻塞投影；不自动重试、观察、放置、换臂、换候选或 replan。 (local)
- [comm] [fix] Stop/replan decisions after an unknown Action outcome now enter `reconciliation_required`; no automatic retry, observation, placement, arm/candidate switch, or replan is introduced. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `robotwin_capability_controller.py:L11-L65,L148-L169`、`robotwin_planning_geometry.py:L136-L174`、`robotwin_route_planner.py:L166-L224,L328-L410,L502-L509`：共享 capability-bound 规范化并接入逐臂 Readiness。 (local)
- [修改 / Modified] `robotwin_simulation_probe_worker.py:L554-L709,L1580-L1604`、`robotwin_persistent_engine.py:L555-L557`：Action 前重验并执行规范化的持久化轨迹。 (local)
- [修改 / Modified] `PhyAgentOS/agent/planning_loop.py:L1488-L1536`：未知结果优先进入 reconciliation；replay 保持 reducer-only。 (local)
- [新增测试 / Added Tests] `tests/test_planning_loop.py:L1291-L1350` 及 Adapter controller/planner/simulation/persistent tests：边界一致性、实质越界和未知结果收敛的 no-motion 回归。 (local)
- [新增 / Added] `CAPABILITY_BOUND_ADMISSION_DIAGNOSIS_20261007.md:L1-L75`、`OUTCOME_UNKNOWN_RECONCILIATION_DIAGNOSIS_20261007.md:L1-L74`、`IMPLEMENTATION_REVIEW_V12_9_3.md:L1-L74`：两份诊断与七维审核。 (local)

### 关键 Diff / Key Diff
```diff
-planner/controller use different numerical admission
+one controller-owned rule is reused before persistence, before Action, and before provider write
-outcome_unknown stop/replan can bypass lifecycle convergence
+outcome_unknown stop/replan -> blocked: reconciliation_required:<node>
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0、Minor 0；七个维度全部通过。没有 RGB/颜色/排列/benchmark/实体/候选/相机/固定机械臂专用分支，也没有自动 Action 或 replan。 (local)
- Zero Blocker, Major, or Minor findings; all seven dimensions pass. No RGB/color/order/benchmark/entity/candidate/camera/fixed-arm branch or automatic Action/replan was added. (local)

### 验证 / Validation
- Core `187 passed`；Adapter capability/Persistent chains `93 passed, 4 deselected` 与 `78 passed`；Skill/release `75 passed`；Ruff、compileall、`git diff --check` 通过。 (local)
- Node `0.10.9` SHA-256 `523ce506eeee3ffc143715ddd1bb98671dfa3ef7847d6de143da45214bfe4d8f`；Skill `3.0.1` SHA-256 `b323781c830e98259b8bb47b65a08f627b3b80ebd1fa1733a177f9f78da8865f`。未安装或启动。 (local)
- 当前解释器缺少现有视频测试依赖 `cv2`；验证未创建 AgentTask、调用 Gateway、推进 simulator/物理运动或改变 Runtime 生命周期。 (local)

### Git 提交 / Git Commit
- Commit: `3a1014a`（实现、诊断与七维审核 / implementation, diagnoses, and seven-dimension review）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-07 18:36 Asia/Shanghai

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
