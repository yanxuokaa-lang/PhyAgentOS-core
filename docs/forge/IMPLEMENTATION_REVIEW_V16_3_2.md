# Implementation Review v16.3.2

Date: 2026-11-01

## Findings

### Blocker

None.

### Major

None.

### Minor

- `tests/test_planning_selection.py` has five pre-existing fixture failures in
  the broader selection suite because its `_Dispatch.graph` stub has no `nodes`;
  `ForgePlanSelectTool` returns `planning_selection_internal_error` before the
  assertions. The files involved are unchanged by v16.3.2. Focused real
  `AgentComposedDispatch` and AgentLoop suites are green.

## Architecture review

- Generic domain layer: PlanGraph ownership, trusted Tool argument construction,
  schema validation, semantic equality, DecisionTrace persistence, and AgentLoop
  guidance.
- Provider/Adapter layer: observation capture, geometry, GraspNet candidates,
  IK, collision, workspace checks, and execution.
- Replacement boundary: the Agent and Tool contract continue to consume stable
  semantic fields and opaque references; no USD path, simulator handle, or
  Adapter object is introduced.
- Evidence lineage: the exact persisted PlanNode binding flows into the Action;
  current Query-produced opaque process/grasp references remain caller-selected.
- Lifecycle owner: Coordinator remains the only owner of frozen node state,
  selection persistence, cancellation, settlement, and recovery.
- Smallest abstraction-leak test: a 32-candidate binding with one altered float
  must be rejected when supplied by the caller, while omission must inject the
  exact frozen binding.

## Change review

`AgentComposedDispatch._build_trusted_arguments` now injects every
`input_binding_keys` value for `manipulation.execute_subtask` from the frozen
PlanNode. A caller-supplied unequal value fails with
`semantic_binding_mismatch`. Existing input-schema validation and the final
`input_binding_keys` equality pass remain intact; the change does not relax
admission.

AgentLoop, the workflow Skill, and the manipulation developer guide now tell the
model to omit `subtask_id`, `operation`, `binding`, `parameters`, and
`tool_sequence` and to submit only the remaining schema-required opaque
selection references. The public ToolSpec and Adapter interfaces are unchanged.

## Robotics safety review

- The trusted intent still forces `motion_authorized=false`.
- No workspace, collision, IK, or Action check was bypassed.
- The validation run omitted `--execute` and recorded
  `simulated_motion_enabled=false`.
- The runtime stopped at `manipulation.prepare` with a known
  `route_collision`; `completed_tool_ids=[]`, `world_change_started=false`, and
  `possession_state=empty`.

## Validation

- `27 passed`: `tests/test_planning_dispatch.py`.
- `189 passed`: planning dispatch plus AgentLoop.
- `33 passed`: pick-place Agent planning and subtask execution.
- `40 passed`: Isaac Adapter phase pipeline, PAOS integration, and Agent host
  no-motion tests.
- Ruff, compileall, and `git diff --check` passed.
- Broader planning selection set: `218 passed, 5 failed`; the five fixture
  failures are the pre-existing `_Dispatch.graph.nodes` issue described above.

## Live-chain evidence

`out/lab-fullchain-truth-20261101-r03-r04-no-motion-r2/acceptance.json`
proves the fixed selection reached real Adapter preparation. The next blocker is
the selected R03 candidate's approach collision with the R03 bottle mesh. This
is no-motion provider evidence, not proof that every alternative grasp is
invalid and not authorization to retry or move.
