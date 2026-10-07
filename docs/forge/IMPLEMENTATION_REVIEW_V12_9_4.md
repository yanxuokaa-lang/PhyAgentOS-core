# v12.9.4 Implementation Review / 实现审核

## Scope / 范围

This review re-audits v12.9.3 across architecture, correctness,
recovery/idempotency, robotics safety, extensibility, observability and
maintainability, and AgentLoop autonomy/convergence. It supersedes the
post-fix zero-finding conclusion in `IMPLEMENTATION_REVIEW_V12_9_3.md`.

本审核按架构、正确性、恢复/幂等、机器人安全、扩展兼容、可观测性/可维护性和
AgentLoop 自主性/收敛七个维度复审 v12.9.3，并取代该版本审核中修复后零发现的结论。

## Findings / 发现

### Major 1: Readiness did not validate the evidence authorizing capability limits

`RoboTwinRouteEvaluator` loaded each MotionCapability artifact and its digest, but
did not validate the paired `MotionCapabilityValidation` or the complete
`ControllerQualification` package. Action admission did validate that evidence.
Readiness could therefore persist a route against capability limits that Action
would later reject before motion. This preserved physical fail-closed behavior but
violated cross-stage equivalence and could return the Agent to another recovery loop.

Fixed by extracting the existing capability/qualification block into
`_validate_motion_policy_bindings()`. Both Readiness and Action now call that one
implementation before using capability limits. No new schema, hash, or parallel
gate was added; existing release-bound evidence is consumed at the earlier stage.

### Major 2: Unknown-outcome reducer replay did not converge task lifecycle

For `outcome_unknown`, stop and replan entered `reconciliation_required`, but
replay returned `replay_required` and left the task outside the reconciliation
projection. Repeated outer recovery could request the same reducer replay again.

Fixed by retaining the Agent-authored replay decision, performing exactly one
read-only reducer replay, and then recording the same reconciliation block used by
stop and replan. The original invocation is never resent and dependent nodes do not
advance.

### Minor 1: Float32 admission accepted a distance interval

The v12.9.3 function accepted any value within the distance between a declared
bound and its float32 representation. Such a value could be close to the bound
without actually being the float32 round-trip value described by the contract.

Fixed by comparing an out-of-bound command to the exact finite float32 encoding of
the declared bound. Exact bounds and genuine float32 boundary values pass; arbitrary
near-bound values and material violations fail closed.

## Seven-Dimension Acceptance / 七维验收

1. **Architecture / 架构: Pass.** Readiness and Action reuse the existing Runtime motion-policy validator; controller numerical ownership remains in the controller module. No parallel state machine or planner was introduced.
2. **Correctness / 正确性: Pass.** Capability documents, validation evidence, qualification package, arm binding, provider identity, and numerical commands agree before a route is persisted and again before execution.
3. **Recovery and Idempotency / 恢复与幂等: Pass.** Unknown outcomes preserve immutable settlement and invocation identity. Stop, replay, and replan all converge to reconciliation; replay remains reducer-only.
4. **Robotics Safety / 机器人安全: Pass within scope.** Invalid or unqualified limits fail before Readiness planning-world evaluation; false near-bound values fail before provider write. No motion or simulator step was used in review.
5. **Extensibility and Compatibility / 扩展兼容: Pass.** Logic is driven by public capability/qualification documents, arm identity, declared joint vectors, and settlement status. There is no RGB, color, order, benchmark, entity, candidate, camera, or fixed-arm branch.
6. **Observability and Maintainability / 可观测性/可维护性: Pass.** Existing structured validation errors remain visible; the shared helper removes evidence-validation drift. Release versions and regression tests cover the changed paths.
7. **AgentLoop Autonomy and Convergence / AgentLoop 自主性/收敛: Pass.** The Agent still chooses recovery intent. Coordinator performs no automatic observation, candidate/arm/target choice, Action retry, placement, or replan; unresolved physical effects terminate in one reconciliation state.

Post-fix findings: **Blocker 0, Major 0, Minor 0.**

## Anti-OverDefense Check / Anti-OverDefense 检查

No new hash, frozen contract, baseline, or independent gate was introduced. The
concrete failure was disagreement between two consumers of already required
validation evidence; the fix reuses the existing validator. Ordinary types alone
cannot prove that an artifact is the independently qualified artifact referenced by
the request.

## Validation Boundary / 验证边界

Validation is no-motion: no AgentTask is created or resumed, no Gateway Query or
Action is invoked, no simulator step or hardware motion occurs, and no Runtime is
stopped, installed, or replaced. The existing video tests still require `cv2`,
which is unavailable in the current interpreter and is reported separately.

```text
Adapter motion-policy/qualification/route/Persistent: 143 passed, 4 deselected
Core planning/recovery: 164 passed
Skill version/release: 75 passed
Ruff: passed
compileall: passed
git diff --check: passed
```
