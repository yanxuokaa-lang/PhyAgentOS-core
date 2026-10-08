# Changelog
## Archive
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.10.1 (2026-10-08 14:46) - codex

### 变更摘要 / Change Summary
- [env] [chore] 通过 Coordinator 将旧任务置为终态并清空 Runtime ownership 后正常停止旧实例，刷新 Core editable 安装，并使用原 profile/env 启动新 Runtime `runtime_b08a1a96e9f74415`。 (local)
- [env] [chore] After moving the old task to a terminal state through the Coordinator and clearing Runtime ownership, normally stopped the old instance, refreshed the Core editable installation, and started Runtime `runtime_b08a1a96e9f74415` with the existing profile/environment. (local)
- [eval] [test] Skill `3.0.7`、Node `0.10.15`、Dora、Gateway 与 11/11 Tool contexts ready；ownership 与非终态任务均为空。 (local)
- [eval] [test] Skill `3.0.7`, Node `0.10.15`, Dora, Gateway, and all 11 Tool contexts are ready; Runtime ownership and non-terminal tasks are empty. (local)

### 验证边界 / Validation Boundary
- 仅执行 task stop、Runtime lifecycle、editable install 与只读状态检查；未创建/恢复任务，未调用 Query/Action，未推进 simulator 或物理运动。 (local)
- Only task stop, Runtime lifecycle, editable installation, and read-only state checks ran; no task was created/resumed, no Query/Action was invoked, and no simulator or physical motion advanced. (local)

### Git 提交 / Git Commit
- Commit: `e9cf9a0`; Branch: `feature/planning-loop`; 时间: 2026-10-08 Asia/Shanghai

## v12.10.0 (2026-10-08 14:33) - codex

### 变更摘要 / Change Summary
- [comm] [fix] AgentLoop 现在保留 persisted selection wrapper 的结构化拒绝码与有界脱敏 detail，不再把确定性错误降级成无 task-bound record。 (local)
- [comm] [fix] AgentLoop now preserves structured rejection codes and bounded redacted details from persisted-selection wrappers instead of degrading deterministic errors to a missing task-bound record. (local)
- [comm] [fix] stale observation freshness 校验现在基于最终 Coordinator-resolved arguments，持久化 selection 不能通过空 literal arguments 放宽 `max_age_ms`。 (local)
- [comm] [fix] Stale-observation freshness validation now uses final Coordinator-resolved arguments, so persisted selections cannot relax `max_age_ms` through empty literal arguments. (local)

### 文件与审查 / Files and Review
- `PhyAgentOS/agent/planning_loop.py:L873-L881,L1193-L1226`、`PhyAgentOS/agent/tools/forge_tool_api.py:L370-L389`。
- `tests/test_planning_loop.py:L2180-L2318`、`tests/test_forge_tool_api.py:L714-L759`、`docs/forge/IMPLEMENTATION_REVIEW_V12_10_0.md:L1-L67`。
- 初审 Major 2 已全部修复；最终七维 Blocker 0、Major 0、Minor 0。 / Both initial Major findings are fixed; final seven-dimension review has zero Blocker, Major, or Minor findings.

### 验证边界 / Validation Boundary
- 专项 `139 passed`，完整 Core `795 passed`；Ruff、compileall、diff check 通过。全部 no-motion；未创建任务、未调用真实 Gateway、未推进 simulator/物理运动。 (local)
- Focused tests passed (`139 passed`) and the full Core suite passed (`795 passed`); Ruff, compileall, and diff checks passed. All validation was no-motion with no task creation, real Gateway invocation, or simulator/physical motion. (local)

### Git 提交 / Git Commit
- Commit: `ac5ef79`; Branch: `feature/planning-loop`; 时间: 2026-10-08 Asia/Shanghai

## v12.9.15 (2026-10-08 13:43) - codex

### 变更摘要 / Change Summary
- [comm] [fix] 修复持久化 `scene.bind` selection 的消费顺序：先解析 Coordinator 参数，再执行实体引用校验，避免合法空参数在 Gateway 前被拒绝。 (local)
- [comm] [fix] Fix persisted `scene.bind` selection consumption ordering by resolving Coordinator arguments before entity-reference validation, preventing valid empty arguments from being rejected before Gateway admission. (local)
- [eval] [test] 新增成功消费和非法 selection fail-closed 回归；Core focused suite `136 passed`，Ruff、compileall 与 diff check 通过。 (local)
- [eval] [test] Add successful-consumption and invalid-selection fail-closed regressions; the Core focused suite passed (`136 passed`) with Ruff, compileall, and diff checks. (local)

### 文件与诊断 / Files and Diagnosis
- `PhyAgentOS/agent/tools/forge_tool_api.py:L373-L387`、`tests/test_forge_tool_api.py:L302-L395`。
- `docs/forge/SCENE_BIND_SELECTION_CONSUMPTION_DIAGNOSIS_20261008.md:L1-L51`、`docs/forge/IMPLEMENTATION_REVIEW_V12_9_15.md:L1-L39`。

### 验证边界 / Validation Boundary
- 仅 Query/no-motion 验证；未创建任务、未调用真实 Gateway、未推进 simulator 或物理运动；未改变 Action admission、Runtime 安全门禁或运动授权。 (local)
- Query-only/no-motion validation; no task was created, no real Gateway was invoked, and no simulator or physical motion advanced; Action admission, Runtime safety gates, and motion authorization were unchanged.

### Git 提交 / Git Commit
- Commit: `3d89785`; Branch: `feature/planning-loop`; 时间: 2026-10-08 Asia/Shanghai

## v12.9.14 (2026-10-08 13:08) - codex

### 变更摘要 / Change Summary
- [env] [chore] 停止旧 Runtime 后安装 Adapter `0.9.10`、Skill `3.0.7`、Node `0.10.15`，启动并只读验收新 Runtime `runtime_3d10c4dfaf5c4382`；Gateway 和 11/11 Tool contexts ready，ownership 为空。 (local)
- [env] [chore] After stopping the old Runtime, install Adapter `0.9.10`, Skill `3.0.7`, and Node `0.10.15`, then start and read-only accept new Runtime `runtime_3d10c4dfaf5c4382`; Gateway and all 11/11 Tool contexts are ready with empty ownership. (local)
- [eval] [test] 未创建任务、未调用 Query/Action、未推进 simulator 或物理运动；旧 Runtime 残留 binding 按用户授权 force-stop，未重试未知的旧 `object.place` Action。 (local)
- [eval] [test] No task was created, no Query/Action was invoked, and no simulator or physical motion was advanced; the old Runtime's residual binding was force-stopped under user authorization, without retrying the unknown old `object.place` Action. (local)

### 制品 / Artifacts
- Skill bundle SHA-256: `cfa6854d2dceaae5c07d364de8d9556284a3537254199439efb3268fb85a9f86`
- Node SHA-256: `b7557228b537b7cb73c46dcee288d3c31e90729cef40bd9c70d40bf20ffa14b5`
- 实际 spawn: `robotwin20_persistent_host-0.10.15-linux-x86_64` / Actual spawn: `robotwin20_persistent_host-0.10.15-linux-x86_64`

### Git 提交 / Git Commit
- Commit: `82e078a` / Branch: `feature/planning-loop`

## v12.9.13 (2026-10-08 12:27) - codex

### 变更摘要 / Change Summary
- [comm] [fix] persistent place producer 现在将已验证的 release、retreat、clearance 与 observation postconditions 投影到 public result 和 action artifact，避免真实成功被 `_ProjectedDriver` 错误降级为 `unknown`。 (local)
- [comm] [fix] The persistent place producer now projects verified release, retreat, clearance, and observation postconditions into the public result and action artifact, preventing a real success from being downgraded to `unknown` by `_ProjectedDriver`. (local)
- [eval] [test] 增加 no-video producer、不完整 route、逐字段缺失 fail-closed、视频 artifact 字段回归；focused `59 passed`，视频测试因环境缺少 `cv2` 未计入成功证据。 (local)
- [eval] [test] Add no-video producer, incomplete-route, per-field fail-closed, and video-artifact field regressions; focused tests passed (`59 passed`), while video tests are not counted because `cv2` is unavailable in the environment. (local)

### 文件与审查 / Files and Review
- `robotwin_persistent_engine.py:L580-L721`、`test_persistent_manipulation.py:L154-L245`、`test_persistent_task_video.py:L63-L78`、`test_persistent_runtime.py:L189-L213`。
- `docs/forge/PLACE_POSTCONDITION_PROJECTION_DIAGNOSIS_20261008.md:L1-L47`、`docs/forge/IMPLEMENTATION_REVIEW_V12_9_13.md:L1-L49`；复审修复 scene revision 类型边界，七维审查 Blocker 0、Major 0。

### Git 提交 / Git Commit
- Commit: `464cebd`（放置后置条件结果投影与无运动回归 / place postcondition projection and no-motion regressions）
- Branch: `feature/planning-loop`
