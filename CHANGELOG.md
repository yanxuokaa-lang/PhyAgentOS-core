# Changelog
## Archive
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)
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

## v12.4.5 (2026-09-30 08:42) - codex

### 变更摘要 / Summary
- AgentLoop 在首个 replan 模型请求前领取 bounded lease，避免 provider 决策时间消耗原始恢复窗口。
- AgentLoop claims the bounded lease before the first replan model request so provider decision time does not consume the original recovery window.
- 增加仅限 exact deadline-expired 且无在途执行的同 AgentTask 操作员恢复入口；91 项通过并完成七维 Review。
- Add same-AgentTask operator recovery only for exact deadline expiry with no in-flight execution; 91 tests pass with seven-dimension review complete.

### 影响文件 / Affected Files
- PhyAgentOS/agent/loop.py L825-L834
- PhyAgentOS/forge/task.py L2585-L2627
- PhyAgentOS/agent/long_horizon.py L89-L92
- PhyAgentOS/cli/commands.py L273-L292
- tests/test_agent_foundation.py L102-L187
- docs/diagnostics/replan-lease-and-expired-task-recovery-20260930.md
- docs/reviews/v12.4.5-replan-lease-recovery-seven-dimension-review.md
