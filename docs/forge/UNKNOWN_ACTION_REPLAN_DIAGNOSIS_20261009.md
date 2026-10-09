# Unknown Action Recovery Diagnosis / 未知 Action 恢复诊断

Date: 2026-10-09 (Asia/Shanghai)

## Incident Facts / 事件事实

The failed execution is `task_e55f689d261244e4`, node `red_acquire`. The task had
completed its discovery, binding, grasp proposal, and preparation stages. The
Action was admitted and ran; it was not a readiness or planning-selection
failure.

The Runtime Action artifact records:

- `status=unknown`, `phase=acquire`, `failed_phase=lift`.
- `failure_code=SimulationProbeError` and `error_detail=attached object did not
  lift with the gripper`.
- `simulator_steps=910`, `world_change_started=true`,
  `outcome_known=false`, `requires_replan=true`,
  `recommended_action=reconcile_world`.
- `new_scene_revision=c237cf1f42b24eec911312a6d6b560ba-2`.
- Scene effect scope is incomplete and carry-forward is not authorized. The
  held/empty state therefore remains uncertain; neither PAOS nor the Agent may
  infer that the object is held or that the world is unchanged.

The action video manifest records one Action, 910 simulator steps, 229 frames
per view, and terminal status `unknown`:

- Head view: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/c237cf1f42b24eec911312a6d6b560ba/task-video-d89c9d813aa842aa9f4564a0e6700e46/cumulative/action-0001/video/head-camera.mp4`
- Observer view: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/c237cf1f42b24eec911312a6d6b560ba/task-video-d89c9d813aa842aa9f4564a0e6700e46/cumulative/action-0001/video/observer-camera.mp4`
- Manifest: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/c237cf1f42b24eec911312a6d6b560ba/task-video-d89c9d813aa842aa9f4564a0e6700e46/cumulative/action-0001/manifest.json`

The subsequent task `task_8d6849cf8bd64ed3` had successful observe,
understand, capability, and goal queries, but binding rejected the uncertain
Runtime possession state. This was the correct Runtime safety response. It did
not prove that the old object had been recovered or that a new physical Action
was safe.

## Root Cause / 根因

Recovery facts were lost at the PAOS planning boundary. The persistent Action
receipt carried `requires_replan=true`, but the persisted execution-to-planning
projection did not include `retryable_in_revision`, `requires_replan`, or
`recommended_action` in `ToolResultEnvelope` or `NodeSettlement`. Consequently,
`PlanningLoopAdapter._recover()` treated every `outcome_unknown` settlement as
reconciliation-only and returned `reconciliation_required` before invoking the
already configured recovery planner. The Runtime had explicitly requested a
replacement plan, but the AgentLoop could not see that request in its typed
facts.

The `unknown` outcome status itself is correct: physical final possession was
not established. The defect is the unconditional control-flow stop, not the
unknown classification. A replacement plan is not permission to retry the
Action. It is a path to gather new scene evidence and let Runtime grounding
decide whether any later operation is admissible.

## Repair / 修复

1. Add provider-neutral recovery fields to `ToolResultEnvelope` and
   `NodeSettlement`; project them from persisted Runtime receipts and preserve
   them during settlement.
2. For `outcome_unknown`, retain reconciliation blocking by default. Allow the
   existing replan lifecycle only when all are true: Runtime selected replan,
   `world_change_started=true`, and `requires_replan=true`.
3. Make the built-in recovery decision deterministic for this explicit Runtime
   combination. The model is not asked to reinterpret or suppress the Runtime
   recovery declaration.
4. Require an unknown-world replacement graph to contain a new Query, and
   require each new Action to have that Query in its dependency ancestry.
   Tool semantics come from the currently bound Runtime ToolSpecs; ambiguous or
   missing semantics fail closed.
5. Keep the original Action settlement and invocation immutable. No action POST,
   automatic observation, possession inference, world reset, or safety-gate
   bypass is introduced by this change.

## Seven-Dimension Review / 七维审查

- Architecture: recovery ownership stays in PAOS planning contracts,
  Coordinator persistence, and AgentLoop; adapter-specific facts are projected
  through the existing Runtime receipt boundary.
- Correctness: explicit recovery fields survive receipt -> result -> settlement;
  unknown remains unknown and only the declared recovery case changes control
  flow.
- Recovery/idempotency: the original invocation is never resent. Recovery uses
  the existing append-only revision and replan budget.
- Robotics safety: no assumption of empty/holding state; a fresh Query must
  precede any new Action and the Runtime/Gateway continue to gate physical work.
- Extensibility/compatibility: no RGB, color, object, camera, or benchmark
  branch; older records deserialize with optional recovery fields unset and
  retain the prior reconciliation-only behavior.
- Observability/maintenance: the settlement retains retry/replan/recommended
  action facts, while plan-proposal failure remains visible as a persisted
  replan reason.
- AgentLoop autonomy/convergence: an explicit Runtime recovery request reaches
  the replan proposer; missing/ambiguous facts or a graph without a Query stays
  blocked, and replan limits remain Coordinator-owned.

## Validation / 验证

No live Runtime, Gateway, simulator, or physical Action was invoked. Focused
no-motion regression coverage verifies receipt projection, settlement
preservation, replan to a new Query-only revision without redispatch,
reconciliation blocking when Runtime did not request replanning, and the
replacement-graph rule that every new Action depends on a new Query.

The combined Runtime/AgentLoop/Skill regression command completed with
`178 passed`. Ruff, Python compilation, and `git diff --check` are recorded in
the implementation review and changelog. Two separate Adapter readiness tests
remain failing on this checkout: one expects `motion_started_in_no_motion_mode`
but receives the earlier `missing_new_scene_revision`; another has a placement
fixture rejected as `object placement result failed contract validation`. The
changed recovery files do not include the Adapter gate, provider, or those test
fixtures; these failures are outside this repair and are not represented as
passing.

The fix does not claim that the stopped task's physical state was reconciled.
The Runtime still needs an authorized observation/reconciliation or operator
recovery before any later Action can pass its own admission checks.
