# Implementation Review v15.1.7: Runtime-Bound Preparation Query

Date: 2026-10-20 (Asia/Shanghai)

## Findings

### Major: Task-scoped assignment still lacks Coordinator-owned intent

The generic binding adapter now invokes the standard PAOS `manipulation.prepare`
Query when attached to a Runtime and refuses to continue unless the selected
candidate has current kinematic, collision, and workspace readiness evidence.
The existing preparation provider still supplies the task assignment. The
standard Query creates an assignment only when it receives a PAOS
`ManipulationIntent`, but the current subtask refresh callback carries only the
previous binding and expected scene revision. The adapter must not invent task,
revision, node, or node-digest identity to fill that gap.

This is a remaining integration blocker for claiming a complete
Coordinator-owned preparation chain. The next implementation must route trusted
task/node intent from the existing planning execution binding into the internal
Query while preserving one Agent-facing subtask settlement. Do not enable live
motion based on this stage alone.

## Architecture Review

- **PAOS ownership:** readiness remains the registered `manipulation.prepare`
  Query. The generic adapter only composes Queries and validates their evidence;
  assignment ownership is explicitly still unresolved as described above.
- **Extension principles:** no environment imports, Prim paths, device handles,
  or environment-specific perception class were added. Provider substitutions
  continue through the same adapter and ToolSpec.
- **Developer Guide:** Query remains read-only and reports unavailable, stale,
  ambiguous, or mismatched preparation as failure; no fallback creates success.
- **AgentLoop:** the extra preparation Query runs inside the existing subtask
  Action driver. It creates no additional Agent-facing PlanNode or settlement.
  Internal Tool records remain distinct from the one subtask settlement.
- **Safety:** no simulator, Gateway, Action, simulator step, or physical motion
  was started. Readiness is not motion authorization.

## Seven-Dimension Acceptance

1. **Perception correctness:** partial. Provider-neutral Query composition and
   semantic selection are tested; no real camera observation was collected.
2. **Binding and freshness:** pass at contract level. Observation, scene,
   frame, calibration, candidate, and preparation references are checked;
   no live sensor provenance was verified.
3. **Agent planning granularity:** pass at Runtime contract level. Preparation
   remains internal to the subtask Action; no second Agent turn is introduced.
4. **IK, workspace, and collision:** partial. The adapter requires all three
   standard Query checks to pass, but tests use no-motion fixtures rather than a
   live planner or collision world.
5. **Execution state:** not verified. No acquire, possession, or placement
   execution was run.
6. **Process feedback:** not verified and outside this binding increment; no
   pour/stir feedback was produced.
7. **Subtask settlement and recovery:** partial. Existing Runtime/subtask tests
   pass and this change does not alter their settlement owner; a full real
   perception-to-subtask settlement remains unverified.

## Validation

- `48 passed`: perception binding, persistent Runtime, subtask executor, and
  LabUtopia Runtime integration tests.
- Full workflow/LabUtopia directories: `589 passed, 2 failed`. Both failures
  are pre-existing RoboTwin release metadata/package-lock drift (`1.0.16` vs
  expected `1.0.15`, and the generated bundle digest differs from the checked-in
  lock); no RoboTwin files were changed.
- Ruff, compileall, and `git diff --check` passed.
- Pytest emitted an existing `asyncio_mode` configuration warning.
- No Isaac Sim, Gateway, Action invocation, simulator step, or robot motion was
  run.
