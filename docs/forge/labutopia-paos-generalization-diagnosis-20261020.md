# LabUtopia PAOS Generalization Diagnosis

Date: 2026-10-20 (Asia/Shanghai)
Status: diagnosis saved; implementation in progress.

## Scope

Review the PAOS grasp/place tools and the LabUtopia `pour`/`stir` complete-cycle adapter against the requirement that scene perception supplies current object pose, grasp pose, tool geometry frame, and placement support pose. The adapter must not treat task names, object dimensions, a fixed grasp orientation, or an initial position as manipulation targets.

## Existing PAOS Boundary

PAOS already supports a perception-to-grasp path:

1. `grasp.propose` returns `grasp_frame`, `approach_direction`, and optional `grasp_geometry` bound to observation, frame, calibration, and scene revision.
2. `manipulation.prepare` evaluates candidates for kinematic, collision, and workspace readiness without motion.
3. `object.acquire` consumes the prepared `candidate_ref` and assignment evidence.
4. `object.place` consumes the completed acquisition and a semantic `destination_ref`.

The PAOS endpoints retain candidate and destination references, but the LabUtopia complete-cycle adapter is a separate route. It accepts semantic refs and operation parameters, then executes its own task/controller path without resolving the candidate pose from PAOS.

## Findings

### Blocker: Candidate grasp pose is not consumed

The LabUtopia worker uses the profile-bound source prim and the task's `object_position`; LabUtopia's stir task controller supplies a fixed end-effector quaternion. Candidate `position_m`, `orientation_xyzw`, and `approach_direction` do not reach RMPFlow/IK.

Relevant locations:

- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py`
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py`
- `/home/yanxu/LabUtopia/controllers/stirglassrod_controller.py`

### Blocker: Placement is reset-position based

Pour returns to a position captured from the episode; stir returns to `initial_control_position`. `destination_ref` is not resolved to a support pose, normal/orientation, or placement tolerance. This cannot satisfy arbitrary destination locations or rack slots.

### Blocker: Scene/geometry assumptions remain

The adapter binds specific source/destination prim paths in a profile, and stir falls back to `<source_path>/Cylinder`. The task reset also randomizes fixed task assets. These are valid deployment bindings for one scene, not scene-independent perception targets; a different asset hierarchy or task requires code/config assumptions beyond an observed candidate.

### Major: Stir request does not fully control motion

The controller maps radius and speed but fixes the movement plane and vertical offset. Requested axis, depth, and turns do not generate the actual target trajectory. The observed live artifact failed the process: requested radius `0.009 m`, measured tool-tip radius approximately `0.0033-0.1003 m`, result `stir_observation_not_qualified`.

Artifact:

- `/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.json`
- `/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.mp4`

### Major: Pour geometry remains profile/task dependent

Pour axis and bottle-mouth offset derive from the configured profile axis and an axis-aligned size extent, while the LabUtopia controller has object-name offsets. This is not equivalent to a perceived bottle-mouth frame and does not generalize to arbitrary bottle geometry/orientation.

## Reviewed Implementation Plan

The implementation adds an explicit manipulation-target payload at the PAOS cycle boundary. It carries current entity pose and identity, selected grasp candidate pose and approach vector, measured/object geometry reference, tool frame where applicable, and destination support pose with orientation/tolerance. The adapter validates observation, scene revision, frame, units, finite values, and candidate/entity binding before any simulator motion.

The worker will use the payload as the episode's object/target state and controller targets. Profile USD paths remain only scene bindings for loading/resolving prims; they are not pose sources. Missing or stale required target data returns an invalid/unavailable no-motion result. The implementation does not claim generic IK/collision success from pose injection: live capability remains bounded by the existing controller APIs, and unsupported pose capabilities fail closed.

## Acceptance Dimensions

The existing seven dimensions remain authoritative:

1. Capability discovery.
2. PAOS parameter mapping.
3. One Action and task ownership.
4. Frame, calibration, and scene-revision binding.
5. Measured feedback.
6. Seven-phase lifecycle.
7. Dry-run, safety, and failure closure.

Additional evidence for this generalization review is required across different source prim hierarchies, object sizes, and destination poses. Unit/dry-run coverage cannot establish actual IK, grasp stability, collision clearance, or successful live placement. Until a controlled Isaac Sim run meets those requirements, no live success claim is made.

## Validation Status Before Implementation

- Focused adapter/protocol tests: `53 passed`.
- `compileall`: passed.
- `git diff --check`: passed.
- Existing real stir artifact: failed as recorded above.
