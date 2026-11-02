# LabUtopia stable bottle grasp and route diagnosis

## Objective and ownership

Address two observed failures without changing AgentLoop or public Tool contracts:

1. The bottle moves during closure because the selected grasp can have unequal
   finger clearance or a poor relationship between the grasp frame and bottle
   axis.
2. The acquire trajectory has an unnatural staged shape and spends excessive
   time searching routes that are rejected by existing IK/collision checks.

The Isaac task-affordance Provider owns evidence-derived bottle-grasp
qualification and opaque candidate ordering. Isaac phase preparation owns
route generation, IK, joint continuity, workspace, swept collision and the
readiness boundary. AgentLoop/Coordinator retain task meaning, candidate
references, Action lifecycle, cancellation and settlement. No public contract,
USD path or robot parameter was added to the generic layer.

## Implementation

The Provider now transforms each predicted pose with the configured calibrated
`provider_from_tcp` transform and same-capture camera pose. It rejects candidates
whose closing axis follows the bottle axis, whose finger-height axis is not
aligned with the bottle axis, whose observed point-cloud cross-section is
one-sided/asymmetric, or whose proposed width is smaller than the observed
contact band. Passing opaque references are deterministically ranked by
approach axiality, contact-center error, closing-axis alignment and finger-axis
alignment. It does not translate or synthesize a GraspNet pose.

The Adapter can now try `direct` and then `staged` route strategies. Direct
means current TCP -> candidate-orientation pregrasp -> grasp -> close -> lift;
it is still fully checked through the existing route qualifier. The LabUtopia
mixture profile tries this strategy first and retains the staged strategy as a
fallback. No collision, workspace, aperture, joint-continuity, contact or drift
limit was relaxed.

## Evidence

### Historical same-capture replay

Workspace: `out/lab-fullchain-truth-20261102-near-arm-r05-r03-r1/`.

The original R05 candidate 69 is rejected by the new sidewall qualification for
asymmetric finger clearance. Eight of 503 raw predictions pass the geometric
filter; candidate 100 remains admitted. The best rank in this replay is
candidate 59. This is diagnostic evidence over a historical capture, not current
execution authority.

### Fresh no-motion run

Workspace: `out/lab-stable-grasp-direct-route-20261102-v16_9-no-motion-r1/`.
Task: `task_894ef705415247a9`, state `awaiting_replan`.

The current capture produced a task-affordance set; only candidate 178 passed
both bottle geometry qualification and short-approach feasibility. Candidates
100, 60 and 56 did not pass short-approach feasibility. The Agent stopped at
the Action boundary as requested by this no-motion invocation. No controller
motion occurred.

### Fresh authorized simulation run

Workspace: `out/lab-stable-grasp-direct-route-20261102-v16_9-execute-r1/`.
Task: `task_5f4231225e424e73`, state `awaiting_replan` after the 1200-second
foreground turn limit. Action invocation:
`invocation://manipulation-execute_subtask/aba88568ff884e9d`.

The complete route search examined 8 direct and 85 staged variants. No route
passed, no readiness artifact was produced, and no controller outcome, motion
video, grasp, pour or stir evidence exists. Direct failures were:

| Failure | Count |
|---|---:|
| IK discontinuity | 4 |
| IK unavailable | 2 |
| Scene collision | 2 |

Staged failures were 45 self-collisions, 16 IK discontinuities, 12 unavailable
IK solutions and 12 scene collisions. Therefore the “flying bottle” symptom was
not reproduced in this run: the system rejected the route before motion. The
user's physical grasp-retention problem remains unresolved.

One direct-route failure records a primary IK branch delta of 4.950158 rad,
above the unchanged 0.5 rad limit; nearby IK was 0.020582 rad away but did not
meet the full pose qualification. This is a continuity/pose-qualification
failure, not evidence that the 0.5 rad threshold should be raised.

## Validation and architecture review

- Targeted Provider and motion tests: 201 passed.
- Full Adapter plus subtask executor regression: 464 passed, 2 native-USD
  tests skipped in the default Python environment.
- Ruff, compileall and `git diff --check` passed.
- Same-capture replay confirms candidate filtering, not live grasp stability.
- Fresh no-motion qualification confirms short-approach filtering, not full
  route readiness.
- Fresh Action attempt confirms zero qualified full routes; it does not prove
  controller motion or physical grasp behavior.

No Blocker/Major public architecture leak was introduced. The implementation
respects Provider/Adapter ownership and opaque references. A remaining Major
acceptance blocker is operational: the selected candidate's full route search
can consume about 15 minutes and end with no route. Do not claim the trajectory
is fixed or the bottle no longer flies.

## Next resolution branch

Use the preserved per-stage `acquire-search` records to identify whether the
next attempt should change the grasp candidate, robot initial configuration,
or route geometry. First inspect the selected candidate's actual world grasp
frame and the measured initial TCP/joints together with the exact stage failure.
Prefer selecting another same-capture, Provider-qualified opaque candidate if
it passes full-route preparation. If all candidates fail, change only
Adapter-private, evidence-derived route/initial-state mechanisms and repeat
no-motion full preparation. Do not relax collision or continuity limits, shift
the selected pose in Action recovery, or start controller motion without a new
readiness artifact. Live closure/contact validation and stage video are still
required after a full route passes.
