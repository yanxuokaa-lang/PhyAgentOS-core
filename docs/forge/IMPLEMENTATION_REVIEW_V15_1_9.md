# Implementation Review v15.1.9: Coordinator-Owned Subtask Context

Date: 2026-10-20 (Asia/Shanghai)

## Findings

### Major remains: preparation assignment is still produced before subtask selection

The coordinator resolver now reconstructs the trusted `ManipulationIntent` from
the active PlanNode and rejects stale or mismatched caller records. The
perception adapter still creates its initial assignment through the injected
preparation provider before a selected subtask execution exists. The intent
resolved for the outer Action is not yet used to produce that assignment.
Therefore this increment closes the identity transport boundary but does not
complete the previous review's assignment-provenance blocker. Live execution
must remain disabled for this path.

The next implementation must preserve the ordering:

```text
observe / understand / grasp candidates
  -> materialize and select one subtask PlanNode
  -> Coordinator resolves its trusted intent
  -> manipulation.prepare creates the task-scoped assignment inside that subtask
  -> acquire -> held process -> place
  -> one Agent-facing subtask settlement
```

The provider may perform readiness and assignment work, but may not invent
task/revision/node identity. The internal preparation Query remains a receipt,
not an Agent turn or separate NodeSettlement.

## Architecture Review

- **PAOS ownership:** `AgentTaskCoordinator.resolve_subtask_context` reads the
  persisted active Action record and PlanNode; it does not create parallel task
  state. The Runtime endpoint only validates this projection.
- **Extension principles:** the resolver is injected through a provider-neutral
  callable seam. LabUtopia has no environment-specific intent builder. The
  subtask Action is not registered when the host omits the Coordinator resolver.
- **Developer Guide:** stale revision, absent planning binding, non-subtask
  caller, malformed intent, and perception-reference mismatch fail before an
  internal Tool is started. No inferred fallback identity is accepted.
- **AgentLoop:** the outer `manipulation.execute_subtask` invocation remains the
  sole Agent-facing lifecycle. Internal Tool ordering and settlement ownership
  are unchanged; no extra Agent turn was introduced.
- **Robotics safety:** all new tests are no-motion. The resolver sets
  `motion_authorized=false`; this is not an authorization to start a simulator
  or robot action.

## Seven-Dimension Acceptance

1. **Perception correctness:** partial. Existing provider-neutral perception
   remains unchanged; no live camera evidence was collected.
2. **Binding and freshness:** partial/pass for identity checks. Coordinator task,
   revision, node, digest, obligation, and intent are reconciled against the
   selected binding at subtask admission; live sensor provenance was not tested.
3. **Agent planning granularity:** pass at Runtime contract level. One outer
   subtask Action still contains the internal sequence and one settlement.
4. **IK, workspace, and collision:** partial. Existing readiness checks remain
   required; this increment uses fixtures, not a live planner/collision world.
5. **Execution state:** not verified. No acquire, possession, release, or retreat
   was executed.
6. **Process feedback:** not verified. No pour/stir measurements were produced.
7. **Settlement and recovery:** partial. Caller attribution and pre-admission
   failure boundaries are covered; persistent real-execution settlement and
   recovery remain unverified.

## Validation

- Focused Runtime/perception/LabUtopia tests: `28 passed`.
- Coordinator resolver tests: `2 passed, 37 deselected`.
- Ruff, `compileall`, and `git diff --check` passed.
- Default pytest plugin autoload could not start because the host ROS
  `launch_testing` plugin imports missing `lark`; tests passed with plugin
  autoload disabled. The existing `asyncio_mode` config warning remains.
- No Isaac Sim, Gateway Action, simulator step, or physical motion was run.

