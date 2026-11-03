# LabUtopia static-contact manifold diagnosis

## Scope

- Tier: C-Safety.
- Owner: Isaac Adapter contact sensing and phase execution.
- Unchanged owners: AgentLoop semantic planning and Action submission;
  Coordinator lifecycle, cancellation and settlement; Provider candidate
  generation and opaque references.
- Simulation only. No physical hardware and no ReMake.

## Fresh execution evidence

- Workspace: `out/lab-fullchain-truth-20261103-v16_9_4-execute-r1/`.
- Task: `task_1826699dc9cd456b`.
- Plan revision: `revision_45ff037f9c294bb7`.
- Prepared scene revision:
  `labutopia-tabletop-rod-rack-v1:1186db97869a4b4fa77992d0b85f3032:0`.
- Action invocation:
  `invocation://manipulation-execute_subtask/3c2d623f753a42f0`.
- The Action produced scene revision suffix `:1`, world change started and an
  unknown outcome. It must never be resumed or reused as readiness.
- Phase feedback:
  `artifact://labutopia/phase-feedback/6584c65280ef4d0cbb67e06c15ecdc7b.json`.
- Phase video:
  `artifact://labutopia/phase-video/6f7d3b9a95414b009368baec07f75de3.mp4`
  (3840x960, 60 fps, 1197 frames, 19.95 seconds).

## Failure sequence

R03 closure established a qualified bilateral hold. The first 17 retimed lift
samples retained positive impulse on both selected-body contact sensors. The
next sample retained fresh manifolds on both fingers but measured about
`[0.002397, 0.0] N*s`; the following sample retained the manifolds but measured
`[0.0, 0.0] N*s`. At the final sample:

- attachment position error: about `0.001919 m`;
- attachment rotation error: about `0.010212 rad`;
- both finger apertures: about `0.023815 m` with target `0.023479 m`;
- object still inside the support-departure band;
- selected-body contact points still present on both fingers.

The current `GripContactWindow.valid()` requires positive summed impulse on
both fingers. `_execute_motion()` therefore converts static selected-body
manifolds into `physical_grasp_lost`, even while the measured grasp transform
and support geometry remain inside existing tolerances.

## Concrete control gap

PhysX reports per-substep contact impulse. A settled body can retain a contact
manifold while the impulse for a control interval is zero. Positive impulse is
valid load evidence, but zero impulse is not by itself separation evidence.
Git, types, collision checks and the one-interval unilateral grace cannot
distinguish these states.

The correction must keep three facts separate:

1. raw selected-body impulse for the current control interval;
2. fresh bilateral selected-body manifold presence;
3. measured TCP-to-object transform error.

During acquire only, after closure has already been confirmed, an invalid load
sample may continue while all of the following are true:

- stage is the initial `lift`;
- the measured object remains in the existing support-contact departure band;
- both selected-body manifolds are fresh;
- attachment position and rotation remain inside the existing grasp limits.

The sample remains `contact_load_valid=false` and `grasp_valid=false`. Once the
object leaves the support band, positive bilateral load must be restored.
Missing/stale manifolds, excessive transform drift, collision, tracking error,
or a failed final lifted/holding postcondition remain fail-closed.

## Architecture acceptance

- No AgentLoop branch or environment path is added.
- No public Tool contract or domain object is widened.
- No Provider candidate is regenerated or recovered from the raw GraspNet pool.
- No action parameter, coordinate, prim path or candidate is hard-coded.
- No hash, frozen contract, baseline or generic gate is added.
- The smallest leak test is a production-shaped lift sequence containing one
  unilateral zero-impulse interval followed by bilateral static zero impulse,
  with failure variants for stale/missing manifolds, excessive drift and exit
  from the support band.

## Next live boundary

After implementation and regression, live validation must start from a fresh
simulator reset and a new workspace. It must generate a new scene revision,
fresh perception and fresh full-path preparation before any Action. The failed
task and its readiness are diagnostic evidence only.
