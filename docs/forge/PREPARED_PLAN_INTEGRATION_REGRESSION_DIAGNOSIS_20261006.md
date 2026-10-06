# Prepared Plan Integration Regression Diagnosis / Prepared Plan 集成回归诊断

## Scope / 范围

本诊断记录 v12.8.2 测试只在 `execute_candidate_phases()` 内部注入 `_prepared_execution_plan`，没有验证 Readiness artifact、assignment 和 Persistent Action `_prepare` 的真实连接。该缺口可能让内部单元测试通过而跨边界运行仍失败。

This diagnosis records that v12.8.2 tested `execute_candidate_phases()` with an internally injected `_prepared_execution_plan` instead of exercising the real Readiness artifact, assignment, and Persistent Action `_prepare` boundary. Such a test can pass while the cross-boundary runtime contract remains broken.

## Evidence / 证据

- The direct regression monkeypatches `evaluate_route_arm()` and manually writes `_prepared_execution_plan` into the fixture state.
- The loader test separately validates a synthetic artifact, but does not invoke Persistent Action `_prepare`.
- The original failure occurred across `manipulation.prepare -> assignment -> object.acquire`, so both halves must be tested together without motion.

- 原有回归 monkeypatch `evaluate_route_arm()` 后直接把 `_prepared_execution_plan` 写入 fixture state。
- loader 测试单独检查 synthetic artifact，但没有调用 Persistent Action `_prepare`。
- 原始故障发生在 `manipulation.prepare -> assignment -> object.acquire` 跨边界，因此必须用无运动集成测试覆盖完整链路。

## Test Contract / 测试契约

The regression must:

1. Build a valid Readiness artifact containing the prepared route and dynamic world state.
2. Give Persistent Action an assignment referring to that artifact.
3. Call the real `_prepare()` method.
4. Make any Action-side route solve fail the test.
5. Assert the prepared plan is loaded and Action reaches the execution generator without a second complete-route solve.
6. Mutate the dynamic state and assert a structured zero-motion rejection.

回归必须：

1. 构造包含 prepared route 与动态世界状态的有效 Readiness artifact；
2. 让 Persistent Action assignment 引用该 artifact；
3. 调用真实 `_prepare()`；
4. 让 Action 侧任意 route solve 都使测试失败；
5. 断言 plan 已加载且 Action 没有二次完整路线规划；
6. 改变动态状态后断言结构化零步拒绝。

## Boundary / 边界

This is a no-motion regression. It does not grant authorization, invoke Gateway Action, advance a simulator, or infer task-specific recovery. The AgentLoop still chooses stop, evidence refresh, or replan from structured facts.

这是无运动回归，不授予授权、不调用 Gateway Action、不推进 simulator，也不推断任务专用恢复。AgentLoop 仍根据结构化事实自主选择停止、刷新证据或 replan。
