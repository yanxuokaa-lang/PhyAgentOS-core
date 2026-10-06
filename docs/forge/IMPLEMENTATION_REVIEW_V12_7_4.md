# Implementation Review v12.7.4

## Review Result / 审核结论

- Blocker: 0
- Major: 0
- Minor: 0
- Acceptance: pass for source integration; deployment and live-task resumption
  are outside this implementation review.

The review covers the recovery replacement/preserve repair only. Validation was
no-motion: no AgentTask creation or mutation outside isolated test workspaces,
no Gateway Query/Action, no simulator step, and no physical movement.

## 1. Architecture Integration / 架构集成

Pass. `reconcile_replan_delta()` is a pure planning calculation in
`PhyAgentOS/planning/replan.py`. The default model recovery plugin calls it while
the bounded correction turn is still available. `PlanningLoopAdapter` calls it
again at the generic plugin boundary, so external `PlannerPlugin`
implementations receive the same contract. Coordinator remains the only owner
of revision persistence and settlement carry-forward.

No parallel state machine, Runtime branch, or task-specific recovery executor
was added.

## 2. Correctness / 正确性

Pass. Preserve candidates are resolved against the actual replacement graph:

- absent candidate: historical only, not declared preserved;
- present and unchanged candidate: retained for Coordinator carry-forward;
- present but changed candidate: rejected before admission;
- non-candidate replacement node: never promoted to preserved.

Task and revision identity are checked before reconciliation. Coordinator's
existing strict checks remain unchanged and still reject direct inconsistent
deltas.

## 3. Recovery and Idempotency / 恢复与幂等

Pass. Reconciliation is deterministic and side-effect free. Reapplying it to an
already effective delta produces the same preserve set. A default model proposal
with changed preserve content receives the existing single corrective turn. A
plugin proposal error is persisted through the existing `awaiting_replan` path
instead of partially admitting a revision.

Historical execution records remain in their original revision. No completed
settlement is copied unless its unchanged node is present in the replacement.

## 4. Robotics Safety / 机器人安全

Pass. The change does not modify frame, calibration, freshness, workspace,
collision, IK, authorization, Gateway admission, invocation reconciliation,
Action execution, retreat, or terminal settlement gates. It cannot synthesize a
motion command or turn a Query result into Action authorization.

The reported task still proves zero Action and zero world change; it must not be
described as grasped or placed.

## 5. Extension Compatibility / 扩展兼容

Pass. The algorithm depends only on `PlanGraph`, `ReplanDelta`, node identity,
and the existing semantic node digest. It has no RGB, color, arrangement,
benchmark, task-ID, Tool-ID, provider, sensor, or camera branch. The generic
planning loop applies it to every `ReplanProposal`, not only the built-in model
plugin.

## 6. Observability and Maintainability / 可观测性与可维护性

Pass. Existing `agent_replan_proposal_rejected` events report changed preserve
content during model repair. Existing replan-proposer error persistence covers
invalid third-party plugin proposals. Two diagnosis documents separate the
runtime event facts from the generic contract analysis.

The helper has one responsibility and reuses the established
`plan_node_digest()` identity rule rather than adding another comparison format,
hash, schema, or gate.

## 7. AgentLoop Autonomy and Convergence / AgentLoop 自主性与收敛

Pass. The Agent still chooses stop/replay/replan and supplies all replacement
nodes. Core does not insert a recovery Query, copy an old node, select a Tool, or
execute anything. It only makes preserve metadata truthful after the Agent has
chosen the replacement graph.

The previous deterministic loop failure is removed: a recovery-only graph no
longer carries an impossible preserve declaration. Changed same-ID content
converges through one bounded correction turn and then fails closed if still
invalid.

## Validation / 验证

- Focused recovery/planning tests: `54 passed, 143 deselected`.
- Full Core tests: `780 passed`.
- Ruff: passed for all modified Python files.
- `python -m compileall`: passed.
- `git diff --check`: passed.
- No Runtime install/restart, live AgentTask mutation, Gateway invocation,
  simulator step, or physical motion was used for this review.

## Residual Boundary / 剩余边界

This change makes the next revision admissible when the Agent chooses a valid
recovery-only graph. It does not assert that a future observation will improve
contact geometry or that a later preparation will find a qualified route. Those
remain evidence-dependent Agent/Runtime outcomes under the existing safety
gates.
