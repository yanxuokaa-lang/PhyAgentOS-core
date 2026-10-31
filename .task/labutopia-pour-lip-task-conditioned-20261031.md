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

## R12 route-rejection diagnosis and recovery implementation

R12 selected exactly one R01 grasp candidate (`candidate://...-0`) for a
single-arm pour. It did not create two simultaneous grabs: R02 is a later
subtask and the glass rod is a separate stir subtask. The first internal
`manipulation.prepare` was no-motion and known: the Isaac Adapter rejected the
candidate with `no_admissible_grasp` because the approach route collided with
the R03 mesh. World state did not change, possession remained empty, and no
atomic Tool completed. The original implementation collapsed this into
`requires_replan=false`, so Coordinator recovery stopped before the Agent could
choose another candidate from the same capture.

The recovery path now preserves the architecture boundary:

- Isaac preparation facts explicitly carry `world_change_started=false`,
  `outcome_known=true`, `possession_state=empty`, and set `requires_replan=true`
  only for an explicit route-collision rejection.
- Subtask aggregation admits replan only for the first no-motion
  `manipulation.prepare` failure with `no_admissible_grasp`, runtime-adapter
  ownership, a route-collision diagnostic, empty possession, and zero completed
  Tools. It never retries internally.
- `AgentRecoveryDecisions` projects only opaque candidate/combination/process
  references from a successful same-revision
  `manipulation.grasp_task_affordances` record whose scene, observation,
  calibration, frame, entity, and underlying grasp candidate set match the
  failed Action binding. Failed candidates are excluded. Missing or stale
  provenance yields stop, not a new Action.
- The Agent must propose a replacement semantic graph and select one supplied
  candidate reference. Coordinator remains the sole revision, budget,
  admission, cancellation, and settlement owner; no provider geometry,
  USD path, pose, or automatic retry crosses the boundary.

This is a replan admission fix only. It does not bypass collision checks,
authorize motion, or prove that any alternative route is feasible. The next
runtime validation is a no-motion recovery run that confirms the Agent's
replacement candidate reaches preparation; Action remains disabled until that
new preparation is accepted.
