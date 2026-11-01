# LabUtopia R03 staged acquire and axial-symmetry diagnosis

## Scope

This record covers the no-motion implementation and runtime verification for the first R03 acquire in the user-requested R03 -> R04 -> GLASS_ROD workflow. It does not claim that a grasp, pour, or stir action executed.

## Architecture decision

- AgentLoop and the Coordinator keep ownership of task semantics, opaque candidate selection, lifecycle, recovery, and settlement.
- The Task-Affordance Provider keeps ownership of process-compatible grasp qualification.
- The simulator-truth geometry Provider derives process features and optional grasp-symmetry evidence from the final composed USD mesh.
- The Isaac Adapter alone owns robot joints, TCP poses, transport orientations, IK branches, route construction, collision checks, and execution.
- No public Tool contract, PlanGraph node, task definition, or opaque-reference format was widened for Isaac-specific geometry or motion data.

## Implemented route

The acquire preparation route is now:

```text
open
-> transit_raise       (current TCP orientation, vertical motion only)
-> transit_orient      (configured safe transport orientation)
-> transit_cross       (lateral translation at raised height)
-> staging_reorient    (selected final grasp orientation)
-> approach
-> grasp
-> close
-> lift
```

Preparation enumerates the configured Cartesian product of clearance, transport orientation, and geometry-supported axial grasp angle. Every combination passes through the existing workspace, full-pose IK, continuity, joint-limit, self-collision, environment-collision, payload-collision, and support-contact checks. Successful routes are ranked by total joint travel and then deterministic configuration order.

## Geometry evidence

An opening rim identifies an axis but does not prove that the bottle body is rotationally equivalent for grasping. The Provider therefore checks multiple intermediate final-mesh cross-sections for radial consistency and angular coverage. R03 produced:

```json
{
  "kind": "axial",
  "axis_world": [0.0, 0.0, 1.0],
  "origin_world": [-0.2700049, -0.3600001, 0.7523713],
  "validated_slices": 4,
  "maximum_radial_deviation_m": 0.00214499,
  "maximum_angular_gap_rad": 0.19639738
}
```

The evidence is projected only into the Adapter-private execution context after a valid non-empty `destination://` binding and selected process-feature set are present. Missing or invalid evidence leaves the original grasp unchanged; it does not infer symmetry from R03, a USD path, or an object label.

## No-motion runtime result

- Workspace: `out/lab-fullchain-truth-20261101-staged-symmetry-no-motion-r1/`
- Session: `cli:lab-91c7fcbbb264`
- Task: `task_a7a9e1dc56014b26`
- Scene revision: `labutopia-tabletop-rod-rack-v1:e3821a001bc84d8aaaa53bb89d8e7937:0`
- Motion state: `simulated_motion_enabled=false`, `world_change_started=false`, `possession_state=empty`
- R03 task-qualified grasp refs: `23`, `16`, `15`
- Search per grasp: 3 clearances x 2 transport orientations x 4 axial angles = 24 fully qualified route combinations

The former direct `transit_cross` use of the final grasp orientation is removed. The remaining failures now occur later:

- `staging_reorient`: `ik_discontinuity`, `inverse_kinematics_failed`, or genuine self-collision such as `panda_link1 overlaps panda_link5`.
- `approach`: table collision such as `panda_link6 overlaps /World/table/surface/mesh`, or collision with adjacent R04 geometry such as `panda_link7 overlaps /World/ReagentZones/A/R04/Model/mesh`.

No route passed preparation, so no controller command was issued and R04/stirring did not start. The next blocker is staging/approach feasibility and local scene clearance, not AgentLoop routing, task parameters, task-affordance candidate leakage, or the former transport-orientation defect.

## Video evidence

The no-motion run saved three identical 1600x1200 rendered camera captures. Because Action execution never started, the phase-motion recorder did not produce an action video. A five-second H.264 preview was generated from the real capture and explicitly marked as controller-disabled observation:

`out/lab-fullchain-truth-20261101-staged-symmetry-no-motion-r1/artifacts/labutopia/no-motion-video/staged-symmetry-observation.mp4`

Metadata: 1600x1200, 30 fps, 150 frames, 5.0 seconds. This artifact is a static no-motion scene preview, not evidence of a grasp or pour. Future admitted Action runs retain the existing per-phase MP4 recorder output under `artifacts/labutopia/phase-video/`.

## Validation

- Focused phase-motion and visual-perception regression: `135 passed`.
- Full Isaac Adapter plus subtask-executor boundary regression: `329 passed`.
- Ruff, compileall, motion JSON parsing, and `git diff --check` passed.
- Invalid transport quaternions containing booleans or strings now fail as `invalid_motion_configuration` rather than escaping as NumPy conversion errors.
- Missing, empty, malformed, or already-converted destination references cannot trigger private symmetry projection.

## Next safe step

Keep execution disabled while testing additional staging poses or approach-direction alternatives inside the Isaac Adapter. Do not lower collision margins, IK continuity limits, pose tolerances, or candidate freshness checks. Simulated motion may be retried only after one complete route passes preparation.
