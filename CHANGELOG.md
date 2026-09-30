# Changelog
## Archive
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.5.5 (2026-10-01 01:30) - codex

### 变更摘要 / Summary
- benchmark profile 的放置目标现在只能来自成功的 `task.goal` 外部注入；计划物化前拒绝 Agent 自写 destination 和 autonomous target/staging。
- Benchmark placement destinations now come only from successful external `task.goal` injection; Agent-authored destinations and autonomous target/staging are rejected before materialization.
- 完整 Diff、七维 Review 和验证记录见 `changelog/2026-10.md`。
- Full diff, seven-dimension review, and validation are recorded in `changelog/2026-10.md`。

## v12.5.4 (2026-10-01 00:20) - codex

### 变更摘要 / Summary
- 修复 AgentLoop discovery 连续性、重复 Skill 读取和 benchmark `destination_ref` 传播；Query lineage/freshness 继续由 Coordinator 投影。
- Fixed AgentLoop discovery continuity, repeated Skill reads, and benchmark `destination_ref` propagation; Query lineage/freshness remain Coordinator-projected.
- 完整 Diff、七维 Review 和验证记录见 `changelog/2026-10.md`。
- Full Diff, seven-dimension review, and validation are recorded in `changelog/2026-10.md`.

## v12.5.3 (2026-09-30 23:20) - codex

### 变更摘要 / Summary
- 将 v12.5.2 的通用 Query 阶段语义与证据型 Agent 取消修复以 editable、no-deps 方式安装到专用 `paos` 环境。
- Installed the generic v12.5.2 Query-phase semantics and evidence-bound Agent cancellation fix into the dedicated `paos` environment in editable no-deps mode.
- 验证模块路径、Coordinator 签名、取消 Tool schema 和聚焦回归；现有 RobotWin Runtime 与 Qwen 服务未重启，未创建任务或动作。
- Verified module provenance, Coordinator signature, cancellation Tool schema, and focused regressions; the existing RobotWin Runtime and Qwen service were not restarted, and no task or action was created.

### 详细记录 / Detailed Record
- 完整安装证据、安全边界和七维复核见 `changelog/2026-09_part21.md`。
- Complete installation evidence, safety boundary, and seven-dimension recheck are in `changelog/2026-09_part21.md`.

## v12.5.1 (2026-09-30 15:18) - codex

### 变更摘要 / Summary
- 发布并重新安装 `pick-place-workflow 2.10.2`，继续锁定已验证的 `robotwin20_persistent_host 0.10.1`。
- Publish and reinstall `pick-place-workflow 2.10.2` while retaining the verified `robotwin20_persistent_host 0.10.1` lock.
- Live `manipulation.prepare` 已加载具名多来源投影：候选来自 `grasp.propose`，可用机械臂来自 `manipulation.capabilities`，Coordinator 负责实体过滤和合并。
- Live `manipulation.prepare` now loads named multi-source projection: candidates come from `grasp.propose`, available arms come from `manipulation.capabilities`, and the Coordinator performs entity filtering and assembly.

### 影响文件 / Affected Files
- `examples/forge-skills/pick-place-workflow/CHANGELOG.md:L3-L9`
- `examples/forge-skills/pick-place-workflow/pyproject.toml:L3`
- `examples/forge-skills/pick-place-workflow/skill.yaml:L3`
- `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py:L270`
- `examples/forge-skills/pick-place-workflow/tests/test_release_bundle.py:L37`
- `changelog/2026-09_part21.md`

### 关键 Diff / Key Diff
```diff
-version: "2.10.1"
+version: "2.10.2"
```

### 验证 / Validation
- Release tests: 159 passed; Ruff, compileall, and `git diff --check` passed.
- Installed Skill `2.10.2`, Node `0.10.1`, Gateway/Tool contexts ready, and no active task/invocation/binding.
- No AgentTask, Gateway Query/Action, or physical motion was created during deployment verification.

## v12.5.0 (2026-09-30 14:36) - codex

### 变更摘要 / Summary
- 为 ToolSpec 增加具名多来源参数投影；`manipulation.prepare` 从直接前驱 `grasp.propose` 获取实体候选，从同场景 `manipulation.capabilities` 获取可用 arm 和 capability snapshot，Agent 不再手工组装参数。
- Add named multi-source ToolSpec projection; `manipulation.prepare` consumes entity candidates from direct-predecessor `grasp.propose` and available arms plus capability snapshot from same-scene `manipulation.capabilities`, without Agent value assembly.
- Coordinator 按 node-bound `entity_ref` 筛选候选，并校验来源 Tool、授权范围、scene、observation、frame 与 calibration；未声明/跨场景/Agent 手写投影字段 fail closed。
- Coordinator filters candidates by node-bound `entity_ref` and validates source Tool, scope, scene, observation, frame, and calibration; undeclared, cross-scene, or Agent-authored projected values fail closed.

### 影响文件 / Affected Files
- `PhyAgentOS/{planning,agent,forge/capability_runtime}` 多来源投影、选择、ready 描述与准备契约。
- `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml`
- `tests/test_multi_source_projection.py`, planning selection/source regressions
- `docs/diagnostics/multi-source-prepare-projection-20260930.md`
- `docs/forge/IMPLEMENTATION_REVIEW_V12_5_0.md`

### 验证 / Validation
- Control-plane/AgentLoop: 201 passed, 1 unrelated reducer replay test deselected.
- Skill/Runtime: 84 passed.
- Ruff, compileall, and `git diff --check`: passed.
- Seven-dimension review: Blocker 0, Major 0, Minor 1 unrelated pre-existing reducer replay failure.
- Implementation commit: `cd487d4` on `feature/planning-loop`.

## v12.4.8 (2026-09-30 13:35) - codex

### 变更摘要 / Summary
- 在 GraspNet worker 边界归一化非负 native score，保留原始排序/诊断；负分过滤、非有限值 fail-closed，公共候选继续满足 `[0,1]` 契约。
- Normalize non-negative GraspNet native scores at the worker boundary while retaining native ordering/diagnostics; filter negatives, fail closed on non-finite values, and preserve the public `[0,1]` contract.
- benchmark profile 以 `task.goal` 外部注入放置目标；自主 target/staging 不可规划且硬拒绝，Coordinator 只传播唯一 benchmark destination；observation-owned 自主规划保持兼容。
- Externally inject benchmark placement goals through `task.goal`; autonomous target/staging are non-plannable and rejected, Coordinator propagates only a unique benchmark destination, and observation-owned autonomous planning remains compatible.

### 影响文件 / Affected Files
- `PhyAgentOS/agent/plan_proposal.py`
- `examples/forge-adapters/robotwin20/runtime/graspnet_worker.py`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/{grasp_proposal.py,grounding.py,persistent_deployment.py}`
- `examples/forge-skills/pick-place-workflow/{SKILL.md,skill.yaml,pyproject.toml,CHANGELOG.md}`
- `docs/diagnostics/graspnet-score-and-benchmark-goal-injection-20260930.md`
- `docs/reviews/v12.4.8-graspnet-benchmark-goal-seven-dimension-review.md`

### 验证 / Validation
- Release pytest: 309 passed; Ruff, compileall and git diff check passed.
- Node `0.10.1` SHA: `5b61b5630109d676c6a29376016b50a6e135fddeab24477274b9216dd6985140`; Skill `2.10.1` bundle SHA: `dbd33301581a67a22b8132a2f39666156fb142371297a7ef3407958b4aba9749`, containing only the locked Node 0.10.1 archive.
- Seven-dimension review: Blocker 0, Major 0, Minor 1.
- Implementation commit: `2039287`; release packaging fix commit: `a5ceb5e` on `feature/planning-loop`.
- Deployment verification: installed Skill `2.10.1` and Node `0.10.1`, restarted `robotwin-blocks-ranking-graspnet`, confirmed live benchmark target/staging are non-plannable, and left Qwen service PID `2283011` unchanged; no AgentTask or Action was created.

## v12.4.7 (2026-09-30 09:20) - codex

### 变更摘要 / Summary
- 修复 GraspNet worker OOM 后 IPC 错误被压成通用 provider failure；增加 12,000 点 profile 预算、typed worker termination/resource errors 和 fail-closed provider code。
- Fix opaque GraspNet provider failures after Runtime OOM; add the 12,000-point profile budget, typed worker termination/resource errors, and fail-closed provider codes.
- RobotWin persistent profile now projects a live ToolSpec requiring at least two unique synchronized sensor views while preserving Core/legacy single-view compatibility.
- 新增 106 项 focused regression、诊断和七维 Review；Node SHA 更新为 `c83d8a8ccb86d2fd10373aecdee738c76f80130cb48afc506efbd8954443ca08`，正式 Skill bundle 构建通过。

### 影响文件 / Affected Files
- `PhyAgentOS/forge/capability_runtime/grasp_proposal.py`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/{process_worker.py,grasp_proposal.py,persistent_host.py}`
- `examples/forge-adapters/robotwin20/runtime/{graspnet_worker.py,robotwin_backend.py}`
- `examples/forge-skills/pick-place-workflow/{skill.yaml,SKILL.md}`
- `docs/diagnostics/rgb-run-graspnet-oom-and-single-view-20260930.md`
- `docs/reviews/v12.4.7-graspnet-multiview-seven-dimension-review.md`

### 验证 / Validation
- Focused pytest: 106 passed; release package smoke: 83 passed.
- Ruff, compileall, git diff --check, Node and Skill bundle builds: passed.
- Implementation commit: `d635af1` on `feature/planning-loop`.

## v12.4.6 (2026-09-30 08:51) - codex

### 变更摘要 / Summary
- 在 PlanProposal 到 Coordinator revision 接受边界验证结构化 manipulation intent，统一选择错误与 revision 状态语义，增加未知字段/合法 intent/旧式兼容回归。
- Validate structured manipulation intent at revision acceptance, align selection errors with authoritative revision state, and add unknown-field, valid-intent, and legacy compatibility regressions.

### 影响文件 / Affected Files
- `PhyAgentOS/forge/manipulation.py`, `PhyAgentOS/agent/planning_dispatch.py`, `PhyAgentOS/agent/plan_proposal.py`
- `tests/test_agent_foundation.py`, `docs/diagnostics/structured-intent-schema-and-revision-correction-20260930.md`, `docs/reviews/v12.4.6-structured-intent-admission-seven-dimension-review.md`

### 验证 / Validation
- Planning/proposal/selection regressions, Ruff, compileall, and git diff check passed.
## v12.5.2 (2026-09-30 09:45) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 统一 Query 阶段语义，`motion_authorized=false` 不再误阻塞成功的只读发现结果。 (local)
- [Policy] [Fix] Unified Query phase semantics so `motion_authorized=false` no longer blocks successful read-only discovery. (local)
- [policy] [fix] Agent 自主取消必须引用 Coordinator 验证的当前阻塞记录；操作员取消保持兼容。 (local)
- [Policy] [Fix] Agent cancellation must cite a Coordinator-validated current blocker record; operator cancellation remains compatible. (local)

### 详细记录 / Detailed Record
- 完整文件 Diff、行号、验证和七维审查见 `changelog/2026-09_part21.md`。
- Full file diffs, line ranges, validation, and seven-dimension review are in `changelog/2026-09_part21.md`.
