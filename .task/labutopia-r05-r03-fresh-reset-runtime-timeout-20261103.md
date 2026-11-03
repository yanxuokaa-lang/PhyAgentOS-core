# LabUtopia R05/R03 fresh-reset runtime diagnosis

## Scope and target correction

- This run is simulator-only. No physical hardware or ReMake path is involved.
- The selected reagent vessels are fixed to the two near-arm inner vessels:
  `R05` in the left B zone first, then `R03` in the right A zone.
- `R04` and every other reagent vessel are out of scope. Recovery must not
  substitute another semantic label.
- Historical task `task_1826699dc9cd456b` and all of its readiness, candidate,
  preparation and scene-revision references remain diagnostic-only.

## Fresh no-motion evidence

- Workspace:
  `out/lab-fullchain-truth-20261103-v16_9_6-reset-no-motion-r1`.
- Session/task/revision:
  `cli:lab-10131b9e4340` / `task_99354ad932ac4e7d` /
  `revision_434f2c1914844bcc`.
- Scene revision:
  `labutopia-tabletop-rod-rack-v1:09527a7be6b942aa85bc512a36ceb79c:0`.
- Motion remained disabled and no controller outcome or world change occurred.
- R05 preparation produced an available, current-capture route for
  `candidate://simulator-truth-R05/557f58ecfe004154a74aa7b012296b83-178`
  in
  `artifacts/labutopia/grasp-approach-feasibility/26af01acac3a44948527cadf414419c2.json`.
  Pregrasp IK, short-approach continuity, workspace and collision checks passed.
- A separate fresh native readback in
  `out/lab-fullchain-truth-20261103-v16_9_6-reset-probe-r1` issued zero motion
  commands. Artifact
  `artifacts/labutopia/physics-probe/6c70bd0e478e48f58c5b309ac8babdc6.json`
  reports reset/readback preservation and finger joints
  `[0.03999999910593033, 0.03999999910593033]`, proving the reset gripper was
  open. The fresh scene contains no historical held-object state.

The no-motion candidate and preparation are diagnostics only. They do not
authorize execution in another workspace.

## Fresh execution evidence

- Workspace: `out/lab-fullchain-truth-20261103-v16_9_6-execute-r1`.
- Session/task/revision:
  `cli:lab-aaf460c87155` / `task_95c5f384b2074722` /
  `revision_e29ef6b31a064a1f`.
- Scene revision:
  `labutopia-tabletop-rod-rack-v1:a9e31ab5a4814e358df385eacedeccbd:0`.
- The execution workspace regenerated its own simulator-truth observation,
  process features, grasp/task-affordance set and preparation. It selected only
  `candidate://simulator-truth-R05/40e33ca5f6b64c39b3fe98c7e426cbb8-178`
  from the execution preparation's qualified set. The different capture prefix
  proves the no-motion candidate reference was not reused.
- Invocation:
  `invocation://manipulation-execute_subtask/e6b185c3b7a646b1`.
- The Action failed in its first `manipulation.prepare` phase. The primary
  receipt is `IsaacWorkerSessionError: Isaac worker request timed out`.
- Terminal Action evidence is known and safe:
  `status=failed`, `outcome_known=true`, `world_change_started=false`, and
  `possession_state=empty`. No acquire, pour, return, R03 or stir phase started,
  so no phase video was created.
- After the worker timeout, the top-level controller record reports
  `Isaac session has no current scene revision`. This is a follow-on symptom of
  the lost/timed-out worker session, not evidence that the target changed and
  not the primary Action failure.
- The host direct turn later reached its 1200-second limit while reconciling the
  already failed invocation. The task remains `awaiting_replan`; it must not be
  resumed because its Isaac process has terminated.

## PAOS architecture review

- AgentLoop/Coordinator correctly own the semantic order, direct-predecessor
  opaque-reference handoff, dependency blocking and terminal settlement.
- The task graph preserves `R05 -> R03 -> GLASS_ROD`; the `R03` nodes remain
  dependency-blocked after R05 failure. No target-selection leak occurred.
- Simulator reset, current scene revision, worker lifetime, route preparation,
  IK/collision/workspace validation and motion are Isaac Adapter/runtime
  responsibilities. The observed failure therefore belongs to the Adapter
  worker-session/request lifecycle, not AgentLoop target policy.
- No public Tool contract, AgentLoop route, candidate schema, safety threshold,
  hash, baseline or generic gate should be changed for this diagnosis.

## Required next step

Do not retry this task or workspace. Before another Action, diagnose the Isaac
worker request budget and session-lifetime boundary using the preserved
per-route `acquire-search` artifacts. Any later live attempt must again start a
fresh process, reset, confirm an empty open gripper, generate a new scene
revision and perform fresh perception and full preparation for `R05`. `R03`
remains blocked until a fresh R05 subtask reaches known successful settlement.
