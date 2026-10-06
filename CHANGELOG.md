# Changelog
## Archive
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

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
- Commit: `7daa161`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-06 Asia/Shanghai

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
