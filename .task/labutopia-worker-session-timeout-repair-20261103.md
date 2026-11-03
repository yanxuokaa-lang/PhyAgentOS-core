# LabUtopia worker timeout and session-lifetime repair

## Failure diagnosis

- Historical execution workspace
  `out/lab-fullchain-truth-20261103-v16_9_6-execute-r1` failed during the first
  R05 Action preparation with `IsaacWorkerSessionError: Isaac worker request
  timed out` before any controller motion.
- `IsaacPhaseMotion.prepare()` could enumerate complete direct/staged route
  variants without an Adapter-owned deadline. The parent RPC had a fixed
  900-second deadline, so the transport could terminate a still-searching
  worker before the Provider returned a domain-level result.
- `IsaacWorkerSession` discarded the child process after transport failure but
  remained reusable. A later `scene_revision()` call could therefore start a
  blank worker behind the same wrapper, producing the misleading follow-on
  error `Isaac session has no current scene revision`.
- The worker receive loop also used a fixed 0.2-second socket wait. A response
  arriving after a shorter remaining request budget could be accepted late.
  When the client closed on timeout, the worker tried to write a second error
  response after `BrokenPipeError`.

## Architecture decision

- AgentLoop and Coordinator remain unchanged. They continue to own semantic
  ordering, opaque-reference selection, dependency blocking and settlement for
  `R05 -> R03 -> GLASS_ROD`.
- `IsaacPhaseMotion` owns the Adapter-private complete-route search budget and
  emits `route_search_timeout` with search lineage before the transport budget.
- `IsaacWorkerSession` owns transport validity. Once a request transport or
  child process fails, that wrapper is permanently invalid and cannot start a
  replacement worker.
- `LabUtopiaBackend` clears only the matching failed session. After transport
  failure, prepare/qualify/execute cannot create a replacement; a fresh
  observation must create the next worker and scene. Provider-level
  `status=unavailable`, including `route_search_timeout`, leaves a healthy
  session and scene revision intact.
- Preparation failure remains known/no-world-change. Execute transport failure
  remains conservative unknown/possible-world-change. No collision, IK,
  workspace, aperture, grasp, contact or possession threshold was relaxed.

## Implementation

- `acquire_route_search_timeout_s=600.0` is deployment configuration, below the
  900-second Forge client/worker request deadline and 1200-second Agent turn
  deadline.
- Route search checks the deadline before each variant and from every
  qualification stage progress callback, so one slow variant cannot consume
  the parent transport deadline.
- Timeout evidence records search ref, attempted/total variants, last stage,
  failure-code distribution, elapsed time and configured budget; it explicitly
  states `motion_authorized=false` and `world_change_started=false`.
- The parent receive loop bounds each socket read by the remaining deadline.
  A timed-out/failed wrapper is marked invalid before process cleanup.
- Backend session helpers centralize creation, matched invalidation and fresh
  observation recovery. Scene-revision reads never create a worker.
- Worker response-channel loss is treated as connection termination without a
  second write attempt.

## Validation

- Focused Adapter regression: `222 passed`.
- Full Isaac Adapter plus subtask executor regression: `488 passed, 2 skipped`.
- Ruff, compileall, JSON parsing and `git diff --check` pass.
- implementation-review found one Major: prepare could recreate a blank worker
  immediately after transport failure. It was fixed with an Adapter-private
  fresh-observation recovery state; no Blocker or remaining Major was found.

## Fresh no-motion evidence

- Workspace:
  `out/lab-fullchain-truth-20261103-v16_9_7-reset-no-motion-r1`.
- Session/task/revision:
  `cli:lab-ec50f5af9c34` / `task_e458a7389cbf4ea6` /
  `revision_732d21f885844630`.
- Scene revision:
  `labutopia-tabletop-rod-rack-v1:b9a9599540cd434dbc142583814fe242:0`.
- The four R05 process/task-affordance Query and preparation nodes completed
  from that revision. The only qualified opaque grasp was
  `candidate://simulator-truth-R05/3bf746a845824bfc8ae93859875cb56b-178`.
- `simulated_motion_enabled=false`; Action execution records are zero. The
  Agent stopped at `pour_r05`, leaving R03 and GLASS_ROD dependency-blocked.
  No phase video or controller motion exists.
- Searches find none of `task_95c5f384b2074722`,
  `task_1826699dc9cd456b`, their scene revisions or historical candidate capture
  prefixes in the new workspace.
- Independent native probe workspace
  `out/lab-fullchain-truth-20261103-v16_9_7-reset-probe-r1` records scene
  revision `labutopia-tabletop-rod-rack-v1:52197e87947c4c5d9bd1da06874f33cb:0`,
  zero motion commands, reset/readback preservation and initial finger joints
  `[0.03999999910593033, 0.03999999910593033]`.

## Safe next step

The repair and fresh-reset no-motion evidence are accepted. A later Action run
must use another independent workspace, worker, reset, scene revision,
observation and complete preparation. It must start with R05; R03 and stirring
remain blocked until that fresh R05 Action settles as known successful.
