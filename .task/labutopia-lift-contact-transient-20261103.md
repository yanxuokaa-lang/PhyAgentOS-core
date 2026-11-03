# LabUtopia acquire-lift contact transient diagnosis

## Scope and evidence

- Fresh task: `task_3ab10413aab34666`.
- Phase video: `out/lab-fullchain-truth-20261103-v16_9_1-execute-r1/artifacts/labutopia/phase-video/3a7c6036760444848d476edbceacd3aa.mp4`.
- R03 passed same-capture task-affordance selection, no-motion preparation and
  complete Action readiness. Closure then established bilateral selected-body
  load before lift.
- During the first lift interval, the right contact sensor reported a fresh
  selected-body contact manifold but zero accumulated impulse; the left finger
  remained loaded. Attachment error stayed about 1.69 mm / 0.0102 rad, below
  the existing configured limits. The old rule collapsed this one-interval
  unilateral unloading into `physical_grasp_lost`.
- World change had already begun. The terminal possession is uncertain, so this
  historical scene revision must not be resumed or used as proof of acquisition.

## Ownership and architecture

This is a Tier C-Safety, Adapter-private execution-evidence repair. The Isaac
Adapter owns PhysX contact sampling, control-interval aggregation and the
decision to stop its controller. AgentLoop and Coordinator continue to own task
semantics, opaque candidate selection, lifecycle, cancellation, settlement and
recovery. No USD path, sensor representation or transient flag enters a public
Tool contract.

The implementation reuses the existing selected-body contact window and grasp
pose thresholds. It does not add a hash, frozen contract or generic gate:
types, Git and ordinary planning tests cannot distinguish a fresh zero-impulse
manifold from persistent physical separation while a controller is running.
That distinction belongs at the existing motion safety boundary.

## Repair invariant

After a successful acquire closure, the initial lift point may continue through
exactly one unilateral-load sample only when both selected-body contact
manifolds are fresh, the other finger has positive interval load and the measured
attachment remains inside the existing pose limits. The observation stays
truthful: `contact_load_valid=false` and `grasp_valid=false`; only
`contact_transient_grace_used=true` records why the controller continued.

The next interval must restore bilateral positive load. Persistent unilateral
unloading, bilateral unloading, a missing or stale manifold, pose-limit failure,
or unilateral contact during initial closure remains fail-closed. Collision,
workspace, joint, aperture and settlement behavior is unchanged.

## Validation boundary

Replacement-plant regressions cover recovery after one transient interval,
persistent unilateral unloading, bilateral unloading, missing/stale manifolds,
and initial closure. These tests prove controller policy and evidence honesty,
not real R03 retention, pouring or stirring. A new live run requires a reset and
physical reconciliation of the prior uncertain-possession session.
