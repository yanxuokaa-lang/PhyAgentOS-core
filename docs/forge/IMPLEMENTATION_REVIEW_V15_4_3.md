# Implementation Review v15.4.3: Semantic Task Creation Boundary

Date: 2026-10-21 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Findings and disposition

### Fixed Blocker: semantic requests previously stopped before production task creation

`forge_task_create` accepted a concrete `PlanGraph`, while the provider-neutral
semantic binding helper was only callable by workflow code. The Agent-facing
task creation path could therefore persist a graph without invoking the
observation/understanding/grasp Query chain. The fix adds an injected
`semantic_plan_builder` port to `AgentLoop`, `build_forge_task_tools`, and
`ForgeTaskCreateTool`. The Core validates the returned graph and derives the
required `artifact://plans/<task>/<revision>` reference, then delegates all
task persistence to `AgentTaskCoordinator`.

### Fixed Major: semantic targets now bind through measured evidence

`QuerySemanticPlanBuilder` validates semantic-only subtask requests, constructs
the provider-neutral `BindingRequest`, invokes `PerceptionBindingAdapter`, and
compiles the resulting `SubtaskSpec` objects with `compose_subtask_plan`.
Selectors are JSON field matches, so the Agent can identify a label without
passing a Prim path, file path, pose, or device handle. Every subtask must
share one observed scene revision. Two independent provider fixtures produce
different measured entity references through the same builder.

### Preserved AgentLoop boundary

The generated graph contains one `manipulation.execute_subtask` node per
semantic request plus one final `task.verify` join. The existing
`SubtaskExecutor` still owns the internal acquire/prepare/process/place calls,
retains internal receipts, and emits one `NodeSettlement` at the subtask
boundary. This change adds no model turn or settlement between internal Tools.

## Architecture review

- PAOS architecture: Core owns task persistence and validation; workflow owns
  semantic binding and graph composition; provider owns Query facts.
- Extensibility: the builder accepts a structural Query port and can be reused
  with a second provider without changing Core or the PlanGraph schema.
- Developer Guide: implementation is in production modules, has explicit
  failure paths, no placeholder success, and reproducible focused tests.
- AgentLoop: builder is injected at construction and registered before the
  Agent sees `forge_task_create`; task creation remains one Agent operation.
- Anti-OverDefense: no new hash or gate was added. The graph reference is the
  existing Coordinator requirement, not a new integrity mechanism.

## Seven-dimension acceptance

1. Perception correctness: **partial**. Provider-neutral Query results and
   semantic label/category selection are proven with fixtures; live camera
   perception is not run.
2. Binding and freshness: **passed for no-motion**. Observation, scene
   revision, frame, calibration, candidate and freshness are checked by the
   existing adapter; cross-revision multi-subtask input is rejected.
3. Subtask AgentLoop boundary: **passed for no-motion**. One Agent-facing node
   and one final verify join are produced; internal Tool calls remain inside
   `SubtaskExecutor`.
4. IK, workspace, collision: **not verified live**. The Query contract carries
   capability/readiness evidence, but no Lula/RMPFlow or collision run occurred.
5. Real execution state: **not verified**. No acquire, place, actuator or
   simulator Action was invoked.
6. Pour/stir process feedback: **not verified**. No live pour or stir telemetry,
   trajectory, tilt/depth, or collision feedback was produced.
7. Settlement and recovery: **partial**. Existing executor and Runtime tests
   prove one subtask settlement and internal receipts; a live AgentLoop recovery
   run remains pending.

## Validation

- `245 passed` across semantic task creation, perception binding, subtask
  executor, persistent runtime, AgentTask, and planning-loop tests.
- Ruff, compileall, and `git diff --check` passed.
- No Isaac Sim, Gateway Action, simulator step, robot motion, or hardware IO
  was run.

## Remaining work

The complete solution still needs a real host to inject the builder backed by
its live Query Runtime, then a no-motion AgentLoop task creation proof followed
by separately authorized Isaac Sim validation of measured IK/collision,
acquire/place state, pour/stir feedback, and recovery. This stage does not
claim those seven-dimension live results.
