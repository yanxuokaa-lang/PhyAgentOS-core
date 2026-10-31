# LabUtopia R9 task-conditioned pour geometry

## Diagnosis saved

Run `out/lab-fullchain-truth-20261031-r9/` reached the AgentLoop
`manipulation.grasp_task_affordances` Query and stopped before any Action.
R01 and BEAKER had same-capture final-USD rim candidates, but R01 had no
independent lateral spout boundary. The previous provider therefore returned
`unavailable: source geometry does not identify a pour lip and outward flow
direction`. This was a geometric qualification failure, not a workspace or
coordinate-range failure. `execution_records=[]` and `controller_outcomes=[]`.

## Architecture decision

- Isaac Adapter owns final-USD mesh/rim evidence and task-conditioned geometric
  qualification. No USD paths, simulator handles, authored manifest positions,
  configuration XY values, or AABB fallbacks cross the PAOS boundary.
- The process-feature Query still returns opaque refs. For a pour Query, a
  circular source opening may be composed with a destination opening from the
  same capture. The Provider projects the destination rim centre into the
  source rim plane and emits a private `pour_lip` candidate only when the
  projection is finite and non-degenerate.
- AgentLoop/Coordinator keep candidate selection, receipts, lifecycle,
  cancellation, and Action admission. Preparation revalidates current refs;
  task semantics and user parameters remain caller-owned.
- A target with no resolvable in-plane direction, mismatched destination, stale
  refs, or missing evidence remains unavailable/stale. No automatic retry or
  motion authorization is introduced.

## Implementation

- `visual_perception.py` adds the task-conditioned source-opening candidate and
  resolves selected process refs into the adapter-private target. The resolved
  `process_frame` carries the evidence-backed pour direction.
- `manipulation_target.py` accepts the optional provider-owned
  `process_frame.pour_direction` vector and validates it as a finite non-zero
  vector.
- `phase_motion.py` uses that direction for the pour approach/tilt axis while
  retaining user-provided `tilt_rad` and `hold_s`.
- Existing legacy held-refresh behavior remains supported when a legacy
  provider already supplies validated `features`; simulator-truth task routes
  use selected opaque process refs.

## Follow-up Runs

- R10 (`out/lab-fullchain-truth-20261031-r10/`) confirmed that the R9
  task-conditioned source opening passes the process-feature and task-affordance
  Queries. It then stopped inside the first no-motion `manipulation.prepare`:
  `LabVisualPerception.resolve()` built a selection-validation request without
  its required `operation`, causing `KeyError('operation')`. The outer Action
  reported `perception_target_resolution_failed`; `world_change_started=false`,
  possession was empty, and no motion atoms completed.
- The adapter now passes its provider-owned `process_type` as `operation` into
  the same-capture selection validator. A regression exercises the complete
  adapter `resolve()` path against selected opaque pour refs.
- R11 (`out/lab-fullchain-truth-20261031-r11/`) passed that target-resolution
  point and reached no-motion route qualification. Preparation rejected every
  R01 grasp candidate with `no_admissible_grasp / route_collision`: the finger
  approach overlaps `/World/ReagentZones/A/R03/Model/mesh`. It reported
  `world_change_started=false`, `possession_state=empty`, and no completed
  motion atoms. R02, stirring, and placement were not started.
- Current next blocker is physical route feasibility for an otherwise valid
  GraspNet candidate set, not process geometry. Do not bypass the collision
  check or hand-edit the grasp pose; inspect candidate approach geometry and
  the scene's collision representation, then rerun no-motion preparation.

## Acceptance boundary

This qualifies a no-motion geometric target and route input only. It does not
prove liquid transfer, vessel capacity/interior volume, IK/collision readiness,
controller success, or chemical mixing. The full task must still stop if any
later preparation or execution evidence is missing or ambiguous.
