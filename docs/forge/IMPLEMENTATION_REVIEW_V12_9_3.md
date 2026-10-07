# v12.9.3 Implementation Review / 实现审核

## Scope / 范围

Review the shared capability-bound admission fix and the AgentLoop
`outcome_unknown` reconciliation projection against seven dimensions. The review
uses no-motion tests only and does not reconcile, retry, stop, or replace the live
unknown invocation.

审核共享 capability-bound 准入修复与 AgentLoop `outcome_unknown` 对账投影，覆盖七个维度。
验收只运行 no-motion 测试，不对账、重试、停止或替换当前未知 invocation。

## Findings Before Fixes / 修复前发现

### Major: Readiness used planner limits instead of execution capability limits

The first implementation shared a comparison function but route readiness still
passed CuRobo's float32 limits while execution used MotionCapability limits. That
did not prove cross-stage equivalence. Fixed by loading the validated per-arm
MotionCapability during route evaluation, canonicalizing before persistence, and
revalidating the persisted plan with the same limits before Action execution.

### Minor: Static quality violations

The new exception name violated the repository's error naming rule and two import
blocks were unsorted. Fixed as `CapabilityBoundError`; Ruff now passes.

## Seven-Dimension Acceptance / 七维验收

1. **Architecture / 架构: Pass.** Numerical command admission remains owned by the Adapter controller boundary. Readiness and prepared-plan admission reuse one pure rule; Core only changes recovery-state projection. No parallel planner, controller, state machine, or execution path was introduced.
2. **Correctness / 正确性: Pass.** Exact bounds pass, the observed float32 boundary value canonicalizes to the declared limit, and a material violation fails. Readiness, persisted plan, and controller write agree on the resulting command.
3. **Recovery and Idempotency / 恢复与幂等: Pass.** Unknown settlements remain immutable until a matching late terminal result. Stop and execution replan converge to `reconciliation_required`; reducer replay remains read-only. No invocation is resent.
4. **Robotics Safety / 机器人安全: Pass within declared scope.** Material position or velocity violations remain fail-closed. Persistent Action revalidates every prepared segment before constructing the execution generator. No limit is expanded and no motion test was run.
5. **Extensibility and Compatibility / 扩展兼容: Pass.** Logic is driven by generic joint vectors, MotionCapability documents, and settlement status. There are no RGB, color, arrangement, benchmark, entity, candidate, camera, or fixed-arm branches. Legacy planner-only test paths remain compatible but do not count as Persistent production safety proof.
6. **Observability and Maintainability / 可观测性与可维护性: Pass.** Material prepared-plan violations return `prepared_execution_capability_mismatch` with readiness ownership and reprepare guidance. Existing task events expose `planning_node_blocked` and `reconciliation_required:<node>`. Ruff, compileall, diagnostics, and focused regressions are present.
7. **AgentLoop Autonomy and Convergence / AgentLoop 自主性与收敛: Pass.** The Agent still selects tools, sources, and recovery intent. Coordinator does not auto-observe, choose an arm/candidate/target, retry, place, or replan. Unknown physical effects terminate the loop in a bounded reconciliation state.

Post-fix findings: **Blocker 0, Major 0, Minor 0.**

## Anti-OverDefense Check / Anti-OverDefense 检查

No hash, frozen contract, baseline, schema, or new gate was added. The existing Node
source digest changes naturally because controller code changed; existing runtime
capability and qualification evidence must therefore be regenerated at the normal
deployment boundary. Git and versioning cannot prove a running controller uses the
new source, but no additional integrity mechanism is needed.

## Validation / 验证

```text
Core planning/recovery changed path: 100 passed, 117 deselected
Core planning-loop full related set: 96 passed
Adapter focused chain: 112 passed; 1 unrelated cv2 environment failure
Adapter simulation-probe excluding video: 65 passed, 4 deselected
Persistent Action/route chain: 30 passed
Controller/planner focused chain: 14 passed
Skill version/release focused test: 1 passed, 74 deselected
Ruff: passed
compileall: passed
git diff --check: passed
```

The only full-group failure imports unavailable `cv2` in an existing video decode
test. All capability, prepared-plan, Persistent Action, route, and AgentLoop tests
ran and passed.

## Deployment Boundary / 部署边界

Do not stop or replace the currently running Runtime while
`invocation://object-acquire/d707ac058ab24306` or its task binding remains active.
After authoritative reconciliation and ownership cleanup, regenerate the
MotionCapability and ControllerQualification artifacts for Node `0.10.9`, then
install Skill `3.0.1` and verify the live Node/source binding without executing an
Action.
