# Implementation review v15.8.0

Date: 2026-10-23, Asia/Shanghai

## Scope and acceptance

The target is an Agent-directed, no-liquid Isaac Sim task: identify REAGENT A
and REAGENT B from visible labels, acquire/pour/return each bottle, then
acquire/stir/return STIR ROD in the same BEAKER. The full physical task remains
open pending one complete Agent task. Camera capture, task
creation, route qualification and mechanism-only tests are recorded separately.

## Architecture

- AgentLoop owns language interaction. The existing semantic plan builder binds
  selectors through observation, understanding, grasp and capability Queries.
- Coordinator owns the task graph, admission, Tool contracts and settlement.
  The capability host supplies an explicit Tool allowlist to the existing
  Runtime binding resolver; managed Skills retain manifest authorization.
- Runtime owns Action invocations, cancellation and possession. One public
  `manipulation.execute_subtask` contains the six prepare/action calls needed
  for acquisition, held processing and return. Unknown grip stops the chain.
- The LabUtopia adapter owns RGB-D association, scene setup, FK/IK, collision
  qualification, bounded joint commands and measured physical feedback.
  Simulator handles and Prim paths stay inside private route storage.
- The SQLite assignment store keeps the existing canonical preparation data.
  There is no additional scheduler, task state machine or settlement store.

A simulator or perception Provider can be replaced without changing AgentLoop
or the public semantic request. The substitution test uses the production
Runtime, endpoints and storage with a no-motion mechanism, then checks nine
internal Actions, three outer settlements and failure closure.

## Resolved findings

- Runtime query injection now precedes checking a perception adapter's readiness.
  The host registers the outer subtask Tool and enrolls its real ToolSpec through
  Coordinator before Agent dispatch.
- `forge_task_create` declares the existing semantic intent fields. Trusted node
  identity and measured binding still come from Coordinator and Query outputs.
- Visual outputs pass actual understanding/grasp schemas: metric dimensions,
  orientation confidence, candidate funnel and entity-owned candidate URIs.
  Nested grasp envelopes exclude the outer entity identifier.
- Binding refresh uses the previous entity/category and receiving vessel,
  preventing the shared adapter from substituting reagent A for B or the rod.
  New captures may publish new calibration artifact URIs. Every understanding,
  grasp and capability Query must match that capture's calibration; refresh
  retains entity/vessel/frame identity and requires new observation/candidates.
- Later preparation uses fresh observation and capability evidence. Held route
  preparation reads the latest stored assignment and original return pose;
  it does not replay the acquisition controller.
  The Coordinator also projects the current persisted selection's scene for
  the first preparation of later subtasks. The Runtime refreshes the same
  entity/vessel before preparing, updates internal intent perception fields
  from that validated binding, and preserves outer input and task/node/semantic
  identity. The substitution test now binds the whole plan at scene 0, matching
  actual Agent behavior, and checks eight refreshes through nine Actions.
- The first pending Action can be reconciled from the host's real Query receipts
  and the worker's current scene before a terminal Action supplies scene evidence.
  Missing receipts or an unresolved terminal outcome still cannot take this
  initial-context path. The host exposes the existing Action reconciliation
  budget through `--execution-timeout-s` (1800 seconds by default), joins the
  existing long-horizon controller and records its returned outcome.
- Known outcome facts are consumed from endpoint summaries. Private route
  arguments are removed from Agent-facing receipts.
- Capture renders before reading, uses optical/ROS camera coordinates for depth
  projection and point clouds, and records calibration from the same capture.
  Initial paused capture activates the annotator timeline only for render-only
  updates, samples each rendered frame and restores the original timeline state
  on success or failure. The camera diagnostic retains simulation time
  2.002083437750116 s while recovering RGB-D; no observation physics step is added.
- Nonfinite unused meshes are reported and excluded from geometry association.
  A selected pixel must still match exactly one measurable rigid body.
- The physical qualifier reads actual PhysX OverlapHit attributes and propagates
  callback failures. It checks intermediate FK workspace positions, individual
  finger envelopes, payload geometry and nearby IK branches before motion.
- Execution predicts payload motion from the current measured grip and checks
  actual robot/payload collision after each control step. The original grip
  relation remains the reference for slip detection. Translation is measured at
  the bound physical grasp anchor, independent of the body's arbitrary frame
  origin. Bottles retain full rotation checks; the explicitly configured
  cylindrical rod permits axial roll while constraining axis tilt. Full rotation
  is retained diagnostically. Support contact uses vertical clearance from the
  measured grasp pose during lift and original target during return. Tests cover coordinate-frame
  invariance and true translational/angular slip. Body-origin displacement is
  retained as a diagnostic.
- The mixture deployment reuses its authored PhysicsScene, with 960 Hz physics
  and 60 Hz control/rendering, and settles once before its first observation.
  Scene configuration supplies measured arm-drive gains. Substeps are owned by
  World; video and feedback use the actual control interval.
- Contact evidence now spans the physics substeps of the current control
  interval. It requires each finger to load the selected body during that
  interval and still report a fresh selected-body contact pair at its end.
  Missing pairs, fully unloaded intervals, wrong bodies, stale readings and
  sampling errors reject; a preceding interval cannot carry possession forward.
  The World callback is removed after execution, including failures.
- Stir transport uses the qualified joint path continuously to avoid repeated
  stops. Fresh r40 reduces maximum transport grip-axis drift to 0.011919 rad
  and completes 2.240281 qualified turns, but return stops on a zero-impulse
  final physics substep while both contact pairs remain present. This exposes
  the sampling defect above. Fresh r41 completes acquisition, first-attempt stirring
  and return with final empty/on-support possession and 0.278 mm return error.
  The callback records current-interval substep loads and resolves the r40 stop.
  Fresh real Agent r14 is now checking the complete three-operation task.
- Stir direction is preserved in both route generation and measured settlement.
  The declared cylindrical fixture compensates the measured tip/axis, requalifies
  the circle after insertion and streams a velocity/acceleration-bounded joint
  path with clamped cubic interpolation and analytic timing bounds. Circle IK
  solves tip position and axis direction with the rod's declared axial freedom,
  retaining nearby solutions. A configured quarter-turn entry reserve serves the existing minimum-turn
  criterion; feedback still has to prove continuous qualified turns. Exit adds
  the configured settling interval and checks actual tool-feature error.
  Tests cover direction, feature correction, continuous-path limits and fresh
  requalification after insertion without issuing commands.
- Pour segments compensate full object pose from the measured grip before
  bounded interpolation. The original grip remains the slip reference, each
  command and physical step retains collision checks, and exit verifies both
  corrected TCP tracking and the original tool-tip/axis target.

## Evidence and limits

The RGB model receives the image, literal label/category guidance and an object
surface-pixel request. It receives no simulator object names. Calibrated depth
associates the pixel with a rigid body; the subsequent geometry is simulator
mesh geometry, not a reconstructed point cloud. Stable opaque entity IDs are
assigned only after that association.

Preparation is read-only. Acquisition requires contact from both fingers and
measured lift. Held execution checks the grasp relation each control step.
Pour/stir completion uses measured feature motion and continuous process
feedback. Return requires support, release and retreat evidence. No fixed joint or object teleport is used for execution. The cylindrical rod's
free axial rotation is explicit fixture policy; axis tilt and anchor displacement
remain measured, as do all bottle rotations.

The existing ArmAssignment and CapabilitySnapshot digest fields remain filled
as required by their contracts; no new hash protocol or execution gate is added.

## Validation

- `pytest-integration-r26.txt`: 856 passed (including the core Tool API); two pre-existing release version/lock
  failures reproduced at HEAD. Robotwin release artifacts are outside this change.
- Actual RGB-D recognition: `visual-runtime-r3/result.json` recognizes the two
  reagent labels, vessel and rod through the real visual association chain.
- Actual Agent r4 creates and activates the three-node graph; r5/r6 reach the
  internal acquisition boundary and expose the candidate URI defect now fixed.
- Real Agent r7 acquires A with a measured 0.120036 m lift, then stops on a
  visual refresh failure. Per-object uncertainty now excludes occluded objects
  without discarding independently resolved ones. Agent r8 stops on grip slip
  before pouring; no later action is executed.
- Mechanism r26 reaches the requested 1.3 rad pour tilt and maintains a qualified
  1.67 s hold, but stops at vessel collision on exit. Recovery placement also
  rejects that path. This is not a completed pour Action.
- Alternative grasp yaw, increased finger force and added neck pads did not
  complete pouring and are not adopted. The 960 Hz mechanism r30 completes
  A acquire/pour/return (1.833 s qualified hold, 4.25 mm return error), then stops
  during B pouring. Fresh r31/r32 B runs still fail on measured angular slip after correcting
  the origin-dependent grasp-translation metric. The supported fixture now uses
  two independent short bottles selected by visible labels. Rod qualification
  r33 found an obstructing 12 mm support rail around the 6 mm rod; retaining
  rails are now 3 mm high, with contact evaluated by support-normal clearance.
  r36 then exposed free axial rod roll; the private fixture policy and geometric
  refresh now represent that symmetry explicitly.
  Fresh r39 acquisition succeeds. Its first stir stops before insertion on
  full-pose IK; the corrected five-constraint tool IK then completes 2.240429
  continuous qualified turns, with 0.578 mm exit tip error and 0.001050 rad
  axis error. Rod return then completes with 2.748 mm position error and
  empty/on-support possession. The same scene completes standard B
  acquire/pour/return: maximum tilt 1.344697 rad, continuous qualified hold
  1.833333 s, return error 3.780 mm and final empty possession.
  These mechanism successes do not establish full Agent acceptance. Fresh
  Agent r9 stops before task creation on missing initial camera frames. The
  render-only timeline correction resolves that failure. Agent r10 acquires A
  and obtains fresh post-lift RGB-D, then exposes an incorrect requirement that
  calibration artifact URIs remain identical across captures. The correction
  retains within-capture calibration checks; 40 focused refresh/Runtime tests
  pass, including three mixed-calibration rejection cases. Agent r11 passes
  refresh but stops during pouring at the measured payload collision boundary
  after 0.866667 qualified seconds. It also exposes missing initial pending-Action
  context in the host join. The corrections above are exercised by fresh r12;
  r12 completes A acquisition, pouring and return with 0.611 mm return error
  and empty possession. Its B preparation then rejects the stale original
  binding before motion. The entry-scene correction above passes 81 focused
  Runtime/core tests and a read-only replay of r12's actual Coordinator record
  (original scene 0, selection scene 3). Fresh r13 completes both reagent
  cycles and rod acquisition, but stirring fails at 0.745589 qualified turns
  with actual grip-axis drift 0.080220 rad. Its task awaits replanning,
  stirring is outcome_unknown and rod return is not executed. Full acceptance
  remains open. The earlier r39 stir success began after stopped transport,
  so it does not prove the fresh horizontal-start cycle. Camera/engine/worker regressions: 79 passed;
  existing core Tool API regressions: 58 passed.

Evidence lives under `out/releases/v15.8.0/` on the acceptance host. The current
execution outcome and reproduction commands are maintained in
`labutopia-paos-acceptance.md`.
