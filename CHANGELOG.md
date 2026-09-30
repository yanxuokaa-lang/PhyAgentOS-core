# Changelog
## Archive
- [2026-09 part20](changelog/2026-09_part20.md)
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
- Release pytest: 308 passed; Ruff, compileall and git diff check passed.
- Node `0.10.1` SHA: `5b61b5630109d676c6a29376016b50a6e135fddeab24477274b9216dd6985140`; Skill `2.10.1` bundle SHA: `bebc83fee136c00964a3e7d23e12896140cec528843a0f3e0042c42e92e94673`.
- Seven-dimension review: Blocker 0, Major 0, Minor 1.

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

## v12.4.4 (2026-09-30 08:32) - codex

### 变更摘要 / Summary
- 隔离结构化节点 intent 与 AgentTask 级验证语义，修复 Coordinator 嵌套/扁平语义冲突。
- Separate structured node intent from AgentTask-level verification semantics, fixing Coordinator nested/flat semantic conflicts.
- 新增结构化 intent、旧式扁平兼容及 manipulation_intent_v2 构造回归；107 项通过并完成七维 Review。
- Add structured-intent, legacy-flat compatibility, and manipulation_intent_v2 construction regressions; 107 tests pass with seven-dimension review complete.

### 影响文件 / Affected Files
- PhyAgentOS/agent/plan_proposal.py L36-L48, L402-L410
- tests/test_agent_foundation.py L221-L251
- tests/test_planning_dispatch.py L199-L265
- docs/diagnostics/local-node-intent-task-verification-contamination-20260930.md L1-L40
- docs/reviews/v12.4.4-plan-materialization-seven-dimension-review.md L1-L33

### 验证 / Validation
- Focused pytest: 107 passed.
- Ruff, compileall, and git diff --check: passed.
