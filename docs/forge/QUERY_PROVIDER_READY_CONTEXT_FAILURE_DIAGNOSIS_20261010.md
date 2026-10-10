# Query Provider Failure with Ready Runtime Context (2026-10-10)

## Scope and evidence

This diagnosis covers the two latest AgentTask incidents, `task_0303fe68739b4338` and
`task_839576ea2bfe4ca3`, without coupling the repair to RGB ordering, a color, a
scene-understanding implementation, or a particular provider.

In the first task, the post-action Query reached the Gateway and persisted a
semantic provider failure (`status=unavailable`, `failure_stage=provider`,
`retryable=false`). The live Tool context remained `ready=true` and
`provider_state=ready`. The task was then recorded as `query_provider_blocked`
and `waiting_for_runtime`; no readiness transition occurred, so the long-horizon
controller kept polling while the CLI remained in `thinking`.

The second task had an additional real `object.acquire` unknown outcome
(`SimulationProbeError`, `world_change_started=true`, `requires_replan=true`).
That unknown Action correctly entered scene-refresh reconciliation and produced
a fresh revision. The same ready-context Query provider failure then occurred in
the refreshed revision and entered the same non-converging Runtime wait. The
physical recovery path was therefore not the common final blocker.

## Root cause

The Core classified every structured non-retryable Query provider failure as
`waiting_for_runtime`. `LongHorizonTaskController._wait_for_runtime()` is
intentionally conservative: it releases a blocked Query only after a live Tool
context transition. With `ready=true` before and after the failure, the required
transition cannot occur:

```text
provider failure -> waiting_for_runtime -> context stays ready -> no transition
```

This is a lifecycle classification error, not a transport readiness failure.
The existing primary keys, append-only execution records, transaction, and
readiness gate preserve the facts but cannot express the missing distinction.

## Generic repair

`AgentTaskCoordinator.record_query_provider_blocked()` now reads the frozen
Tool's live context before its atomic state mutation:

- explicit `ready=false` or an unconfirmed context remains
  `waiting_for_runtime`; the host may wait for a readiness transition and must
  not invoke the Query again;
- explicit `ready=true` records the same immutable provider-block event but
  transfers the task to the existing bounded `awaiting_replan` lifecycle;
- if the replan budget is exhausted, the Coordinator records a terminal failure
  instead of creating an unbounded wait;
- the failed Query is never a successful evidence record and no Action is
  replayed or authorized by this branch.

`PlanningLoopAdapter` returns the Coordinator's resulting status instead of
unconditionally reporting `waiting_for_runtime`, allowing the AgentLoop to
perform a fresh governed replan turn for the same AgentTask. The Runtime,
Gateway, Action admission, motion authorization, scene binding, target
injection, and unknown-world reconciliation contracts are unchanged.

## Extension and safety boundary

The rule is based only on Query semantics, structured provider facts, and the
live boolean Tool readiness. It applies to any Skill and provider exposing the
existing contract. No RGB/object/provider branch, hash, baseline, frozen
contract, parallel global state, automatic Query retry, camera read, simulator
step, or physical Action is added.

Validation uses fake Tool records and scripted contexts only. The historical
tasks remain terminal/diagnostic artifacts; this repair governs future tasks
without reviving or replaying them.
