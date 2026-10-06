# Changelog
## Archive
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.8.0 (2026-10-06 17:49) - codex

### 变更摘要 / Change Summary
- [policy] [feat] 新增 Adapter-owned `contact_qualification.mode`：当前 GraspNet profile 使用 `planner_world_only`，关闭完整 depth occupancy、unknown/occluded 分类及局部手掌/手指点云扫掠；完整 `observed_occupancy` 模式保持可选。 (local)
- [policy] [feat] Add Adapter-owned `contact_qualification.mode`: the current GraspNet profile uses `planner_world_only`, disabling full-depth occupancy, unknown/occluded classification, and local palm/finger point-cloud sweeps while retaining optional `observed_occupancy`. (local)
- [sense] [fix] 简化模式仍先安装 Curobo planning world，保留其他绑定对象、原生桌面/观测支撑面与 peer arms，并继续执行接触和完整搬放路线的碰撞、IK、关节限位及桌面净空检查。 (local)
- [sense] [fix] Simplified mode still installs the Curobo planning world first, retaining other bound objects, the native table/observed support, and peer arms, and continues collision, IK, joint-limit, and table-clearance checks for contact and the complete route. (local)

### 文件变更详情 / File Changes
- [新增 / Added] `robotwin20_adapter/contact_qualification.py:L1-L36`：共享策略枚举与 profile 组合校验 / shared policy enum and profile-combination validation.
- [修改 / Modified] `persistent_deployment.py:L19,L192-L212`、`persistent_route_builder.py:L19,L54-L66,L257-L323`、`robotwin_persistent_engine.py:L428`、`robotwin_route_planner.py:L311-L437`：从 profile 到 Runtime 传播并分派策略 / propagate and dispatch policy from profile to Runtime.
- [修改 / Modified] `robotwin_contact_qualification.py:L75-L160`：新增仅由规划世界执行的接触资格路径 / add planner-world-only contact qualification.
- [修改 / Modified] route-input profiles `L1-L10` 与 materializer/replay：schema v4、显式模式和一致 replay / schema v4, explicit mode, and consistent replay.
- [修改 / Modified] Adapter tests：新增模式、planner fail-closed、无 observed 指标与非法 profile 回归；`README.md:L689-L707` 记录范围 / add mode, planner-failure, no-observed-metric, and invalid-profile regressions and document scope.
- [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V12_8_0.md:L1-L63`：七维审核 / seven-dimension review.

### 关键 Diff / Key Diff
```diff
-observed_collision: {depth/voxel/unknown policy...}
+contact_qualification:
+  mode: planner_world_only
```
```diff
-local_contact(...) + visibility_counts(...)
+evaluate_contact(...) + finite non-negative table clearance
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0、Minor 1。架构、正确性、恢复/幂等、声明范围内机器人安全、扩展、可观测性和 AgentLoop 自主性通过；Minor 是简化世界不保证未识别或 unknown/occluded 障碍物，不能作为开放场景/硬件完整安全证明。
- Zero Blocker, zero Major, one Minor. Architecture, correctness, recovery/idempotency, robotics safety within scope, extensibility, observability, and AgentLoop autonomy pass; simplified mode does not cover unidentified or unknown/occluded obstacles and is not an open-world or hardware safety proof.

### 验证 / Validation
- Adapter focused `79 passed`; Skill/release/install `87 passed`; Ruff、compileall、`git diff --check` passed.
- Full Adapter `773 passed, 17 failed`; failures are existing environment/fixture gaps (`scipy`, `cv2`, unrelated Action/Backend fixtures), not changed-path regressions.
- Adapter `0.9.0`、Skill `2.10.11`、Node `0.10.5`; Node SHA-256 `a431812a48ab34a9aab77142bacb4a3583133da585361351f94e24f97c052088`，Skill bundle SHA-256 `86bcffb6d484f88e9dd453006cfca3a128f33c6e60680bc50fcc64ce099aee40`。
- No AgentTask, Gateway Query/Action, simulator step, physical motion, install, or Runtime restart.

## v12.7.5 (2026-10-06 16:09) - codex

### 变更摘要 / Change Summary
- [env] [chore] 取消旧 `awaiting_replan` 任务并确认 ownership/非终态任务清空后，正常停止旧 flow；旧 host 超过 Dora 停止宽限期后被 Dora SIGKILL 清理，无残留 flow 或在途 Action。 (local)
- [env] [chore] Cancel the old `awaiting_replan` task and clear ownership/non-terminal tasks before normally stopping the old flow; Dora cleaned up the old host with SIGKILL after its stop grace period, with no residual flow or in-flight Action. (local)
- [chore] [release] 将 Core distribution 从 `PhyAgentOS-ai 1.0.1` 更新为当前 editable `1.0.2`，保留未变的 Skill `2.10.10` 与 Node `0.10.4`，并启动新 Runtime `runtime_d3c5b3210a094cb9`。 (local)
- [chore] [release] Upgrade the Core distribution from `PhyAgentOS-ai 1.0.1` to current editable `1.0.2`, retain unchanged Skill `2.10.10` and Node `0.10.4`, and start new Runtime `runtime_d3c5b3210a094cb9`. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `changelog/2026-10.md:L3-L56`：记录任务取消、停止告警、Core 安装、Runtime 启动与 no-motion 验收 / record task cancellation, stop warning, Core installation, Runtime startup, and no-motion validation.
- [修改 / Modified] `CHANGELOG.md:L7-L34`：维护最近五个版本 / maintain the latest five versions.

### 关键 Diff / Key Diff
```diff
-PhyAgentOS-ai 1.0.1; runtime_029203e0cad84b94
+PhyAgentOS-ai 1.0.2 editable; runtime_d3c5b3210a094cb9
-task_444c570eae644b9a awaiting_replan
+task_444c570eae644b9a cancelled; nonterminal_count=0
```

### 验证 / Validation
- Skill `2.10.10`、Node `0.10.4` verified、Dora running、Gateway ready、11/11 Tool context ready；ownership 为空，非终态任务为 0，本地 Qwen 为 `qwen3-vl-4b-awq`。
- 未创建新任务、未调用 Gateway Query/Action、未执行 simulator step 或物理运动。

### Git 提交 / Git Commit
- Commit: `abd192e`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-06 16:09 Asia/Shanghai

## v12.7.4 (2026-10-06 15:05) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 在 replacement graph 产生后计算 effective replan delta：省略的历史节点不再虚假声明 preserved，原样节点继续 carry settlement，同名变更节点在 admission 前被拒绝。 (local)
- [policy] [fix] Derive the effective replan delta after the replacement graph exists: omitted historical nodes are no longer falsely declared preserved, unchanged nodes continue to carry settlement, and changed same-ID nodes are rejected before admission. (local)
- [policy] [fix] 默认 Agent recovery 与通用 `PlannerPlugin` 接纳边界共享同一纯 planning 规则；Coordinator 的严格 settlement 校验保持不变。 (local)
- [policy] [fix] Apply the same pure planning rule to default Agent recovery and the generic `PlannerPlugin` admission boundary while retaining strict Coordinator settlement validation. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/planning/replan.py:L43-L83`、`planning/__init__.py:L54-L85`：新增并导出 effective-delta 归一化 / add and export effective-delta reconciliation.
- [修改 / Modified] `PhyAgentOS/agent/recovery_decisions.py:L137-L163`、`planning_loop.py:L1547-L1622`：接入默认模型纠正与通用 plugin 边界 / integrate default-model correction and generic plugin handling.
- [修改 / Modified] `tests/test_planning_loop.py:L958-L1011,L1085-L1180`、`test_agent_foundation.py:L2266-L2353`：覆盖 recovery-only、严格 admission、preserve 三态、纠正与无副作用 / cover recovery-only flow, strict admission, preserve states, correction, and no side effects.
- [新增 / Added] `REPLAN_PRESERVE_EVENT_DIAGNOSIS_20261006.md:L1-L68`、`REPLAN_EFFECTIVE_DELTA_CONTRACT_DIAGNOSIS_20261006.md:L1-L93`、`IMPLEMENTATION_REVIEW_V12_7_4.md:L1-L108`：两份诊断与七维审核 / two diagnoses and seven-dimension review.

### 关键 Diff / Key Diff
```diff
-return ReplanProposal(delta=delta, plan_graph=replacement, ...)
+effective_delta = reconcile_replan_delta(graph, delta, replacement)
+return ReplanProposal(delta=effective_delta, plan_graph=replacement, ...)
```
```diff
+absent preserve candidate -> historical only
+unchanged included candidate -> preserve settlement
+changed included candidate -> reject before admission
```

### 七维 Code Review / Seven-Dimension Review
- 架构、正确性、恢复/幂等、机器人安全、扩展兼容、可观测性/可维护性、AgentLoop 自主性与收敛均通过；Blocker 0、Major 0、Minor 0。无任务、Tool、provider 或相机专用分支，不自动观察、复制节点、选择 Tool 或执行 Action。
- Architecture, correctness, recovery/idempotency, robotics safety, extension compatibility, observability/maintainability, and AgentLoop autonomy/convergence pass with zero Blocker, Major, or Minor findings. No task, Tool, provider, or camera-specific branch and no automatic observation, node copying, Tool selection, or Action.

### 验证 / Validation
- 聚焦 recovery/planning `54 passed, 143 deselected`；完整 Core `780 passed`；Ruff、compileall、`git diff --check` 通过。
- 未安装/重启 Runtime，未变更 live AgentTask，未调用 Gateway Query/Action，未执行 simulator step 或物理运动。

### Git 提交 / Git Commit
- Commit: `cf7ed3a`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-06 15:18 Asia/Shanghai

## v12.7.3 (2026-10-06 14:43) - codex

### 变更摘要 / Change Summary
- [env] [chore] 在零 active ownership 和零非终态 AgentTask 下正常停止旧 Skill `2.10.9`，安装 Skill `2.10.10` 与 Node `0.10.4`，并使用原 profile 和 operator-owned env 文件启动新 Runtime。 (local)
- [env] [chore] With zero active ownership and zero non-terminal AgentTasks, normally stop old Skill `2.10.9`, install Skill `2.10.10` and Node `0.10.4`, and start the new Runtime with the existing profile and operator-owned env file. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `changelog/2026-10.md:L3-L43`：记录部署计划、停止条件、实际停止/安装/启动、无动作验收与提交 / record deployment planning, stop conditions, actual stop/install/start, no-motion acceptance, and the commit.
- [修改 / Modified] `CHANGELOG.md:L7-L33`：维护最近五个版本的完整记录 / maintain complete records for the latest five versions.

### 关键 Diff / Key Diff
```diff
-pick-place-workflow 2.10.9 (running)
+pick-place-workflow 2.10.10 (running)
-robotwin20_persistent_host 0.10.3
+robotwin20_persistent_host 0.10.4 (SHA-256 verified)
```

### 验证 / Validation
- `paos skill status`：Skill `2.10.10`、Dora running、Gateway ready、11 个 Tool context ready；实际 host 路径为 `robotwin20_persistent_host-0.10.4-linux-x86_64`，Node lock SHA-256 verified。
- Runtime ownership 为空、非终态 AgentTask 为 0、本地 Qwen 为 `qwen3-vl-4b-awq`；未创建任务、未调用 Query/Action、未执行仿真或物理运动。
- Skill archive SHA-256 `fe6ef2db9bd02bca339003267d0f8e3927ee8ff5cb041126c4b4b1bee2b5e18b`；Node archive SHA-256 `074edf599aafae8cf820feee777550e05cdec0fe1148b314ba8769c1664cc440`。

### Git 提交 / Git Commit
- Commit: `a3fa0d5`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-06 14:48 Asia/Shanghai

## v12.7.2 (2026-10-06 14:11) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 将 RoboTwin Runtime profile 的解析收敛到 Adapter `0.8.0` 共享边界，使 Runtime backend 与 route materializer 同时支持 `sensor_ref`/`sensor_refs`，修复候选成功后稳定失败的 `route_materialization_invalid`。 (local)
- [sense] [fix] Consolidate RoboTwin Runtime-profile parsing in the shared Adapter `0.8.0` boundary so the Runtime backend and route materializer both support `sensor_ref`/`sensor_refs`, fixing deterministic `route_materialization_invalid` after successful proposal generation. (local)
- [policy] [fix] 静态 profile/schema/materializer 故障明确为 Runtime-provider 所有、不可同 revision 重试且不要求 replan；候选耗尽与 evidence refresh 保留各自恢复语义。 (local)
- [policy] [fix] Classify static profile/schema/materializer faults as Runtime-provider-owned, non-retryable in the same revision, and non-replannable while retaining candidate-exhaustion and evidence-refresh semantics. (local)
- [chore] [release] 构建 Skill `2.10.10`、Node `0.10.4` 与 Adapter `0.8.0`，未安装或重启 Runtime。 (local)
- [chore] [release] Build Skill `2.10.10`, Node `0.10.4`, and Adapter `0.8.0` without installing or restarting the Runtime. (local)

### 文件变更详情 / File Changes
- [新增 / Added] `runtime_profile.py:L1-L209`：共享 Runtime profile schema 与规范化 / shared Runtime-profile schema and normalization.
- [修改 / Modified] `robotwin_backend.py:L30-L83`、`materialize_complete_route.py:L52-L233`：共同消费共享 parser / consume the shared parser.
- [修改 / Modified] `manipulation_prepare.py:L35-L52,L528-L557`、`persistent_route_builder.py:L162-L226,L311-L321`、`persistent_preparation.py:L73-L116,L158-L192`：一致的结构化恢复语义 / consistent structured recovery semantics.
- [新增 / Added] `RUNTIME_PROFILE_CONSUMER_DRIFT_DIAGNOSIS_20261006.md:L1-L109`、`PREPARATION_FAILURE_RECOVERY_CONTRACT_DIAGNOSIS_20261006.md:L1-L103`、`IMPLEMENTATION_REVIEW_V12_7_2.md:L1-L87`：两份诊断与七维审核 / two diagnoses and seven-dimension review.

### 关键 Diff / Key Diff
```diff
-materializer requires only legacy sensor_ref
+Runtime backend and materializer use one Adapter-owned profile parser
-failure_owner=runtime_provider, requires_replan=true
+failure_owner=runtime_provider, retryable_in_revision=false
+requires_replan=false, recommended_action=fix_runtime_contract
```

### 七维 Code Review / Seven-Dimension Review
- 架构、正确性、恢复/幂等、机器人安全、扩展兼容、可观测性/可维护性、AgentLoop 自主性与收敛均通过；Blocker 0、Major 0、Minor 0。无 RGB/颜色/排列/benchmark/task ID/provider/具体相机组合分支，不自动观察、筛选、replan 或执行 Action。
- Architecture, correctness, recovery/idempotency, robotics safety, extension compatibility, observability/maintainability, and AgentLoop autonomy/convergence pass with zero Blocker, Major, or Minor findings. No RGB/color/arrangement/benchmark/task-ID/provider/concrete-camera-combination branch and no automatic observation, selection, replan, or Action.

### 验证 / Validation
- 聚焦回归 `348 passed`；发布聚焦 `435 passed`；完整 Core `773 passed`；完整 Adapter/Skill `1144 passed, 1 skipped, 4 个既有基线失败`，原 runtime profile identity 基线已修复。
- Ruff、compileall、`git diff --check` 通过；Node `0.10.4` SHA-256 `074edf599aafae8cf820feee777550e05cdec0fe1148b314ba8769c1664cc440`；Skill `2.10.10` SHA-256 `fe6ef2db9bd02bca339003267d0f8e3927ee8ff5cb041126c4b4b1bee2b5e18b`。
- 未安装/重启 Runtime，未创建 AgentTask，未调用 Gateway Query/Action，未执行仿真或物理运动 / no Runtime install/restart, AgentTask, Gateway Query/Action, simulator motion, or physical motion.

### Git 提交 / Git Commit
- Commit: `c52a5c4`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-06 14:38 Asia/Shanghai
