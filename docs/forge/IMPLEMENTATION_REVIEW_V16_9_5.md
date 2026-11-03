# Implementation Review: v16.9.5

## Findings

1. **Major, fixed - positive impulse was conflated with continued contact.**
   `GripContactWindow.valid()` correctly requires bilateral positive impulse
   for load validity, but the execution state machine had no separate way to
   observe fresh bilateral selected-body manifolds. The fresh v16.9.4 run
   therefore converted static zero-impulse contact into
   `physical_grasp_lost`. The Adapter now records manifold freshness separately.
2. **Major, fixed - an unrestricted manifold fallback would hide a dropped
   payload.** Continuity is limited to acquire lift after confirmed closure,
   the existing measured support-departure band and the existing attachment
   position/rotation limits. It ends immediately outside that band.
3. **Major, fixed - measured truth must not be upgraded by execution policy.**
   Static continuity samples remain `contact_load_valid=false` and
   `grasp_valid=false`. The new `support_manifold_continuity_used` field records
   only the Adapter-private continue decision.
4. **Major, fixed - the regression needed the actual failure sequence.** The
   production-shaped test now covers bilateral load, one unilateral zero-
   impulse interval, one bilateral static zero-impulse interval and bilateral
   recovery at support departure. Missing/stale manifolds, excessive transform
   drift and zero load outside the support window still fail closed.
5. **No public-contract or AgentLoop leak found.** No USD path, PhysX handle,
   manifold, contact threshold or controller state is added to domain objects,
   Tool contracts, Provider candidates, Coordinator settlement or AgentLoop.
6. **Live workflow remains unproven.** The prior task has world change started,
   unknown outcome and uncertain possession. Unit/integration regressions do
   not prove R03 acquisition, pouring, R04 or stirring.

## Architecture and safety acceptance

- Stable domain semantics are unchanged: task order, user-supplied process
  parameters, opaque candidate lineage, lifecycle, cancellation and settlement
  retain their existing owners.
- Environment-specific sensor interpretation stays in the Isaac Adapter.
- Existing frame/calibration, workspace, joint, collision, aperture, attachment
  and final possession checks remain active.
- No hash, frozen contract, baseline or new general-purpose gate was added.
- The failed v16.9.4 task and readiness are never reusable. A future Action
  requires a fresh simulator reset, scene revision, perception and full-path
  preparation.

## Validation

- Focused contact and execution regression: `15 passed`.
- Isaac Adapter plus subtask executor: `477 passed, 2 skipped`.
- Ruff, compileall and `git diff --check`: passed.

## Acceptance

Accept the Adapter-private repair as a bounded correction to contact evidence
interpretation. Do not claim live acquisition or the two-pour/stir workflow is
complete until a separate fresh-reset execution produces known possession and
phase receipts.
