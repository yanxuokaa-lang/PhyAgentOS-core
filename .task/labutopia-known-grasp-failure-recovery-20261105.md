# LabUtopia known grasp-failure recovery diagnosis

## Observed failure

Two fresh-reset R03 executions reached a qualified grasp, briefly established
bilateral contact, and then lost load during `lift`.  The Isaac phase feedback
reported `physical_grasp_lost`, while the outer `manipulation.execute_subtask`
remained `unknown`.  The task therefore stopped at reconciliation instead of
returning the arm to an observation posture and creating a fresh perception
revision.

## Root causes

1. `IsaacPhaseMotion` holds the measured joint state after a phase failure.  It
   does not distinguish a known, supported, empty-gripper failure that can be
   safely recovered from an uncertain possession outcome.
2. The outer subtask recovery projection only recognizes zero-motion
   preparation failures.  A known Action failure that has returned to a safe
   observation posture is not projected as a fresh-perception replan.
3. Same-capture alternative recovery is intentionally limited to no-motion
   route rejection.  It must not be used after a physical attempt changed the
   world.

## Required behavior

```text
qualified acquire Action
  -> known recoverable grasp failure
  -> hold current articulation state
  -> verify object supported with no grasp load or bilateral manifold
  -> open gripper
  -> reverse the executed, already-qualified arm path
  -> reach configured observation-home joints
  -> settle and report observation_ready=true
  -> advance scene revision
  -> fresh scene.observe / process features / grasp candidates
  -> new preparation
  -> new Action invocation
```

The Isaac worker process remains alive.  The task identity remains the same,
but the replacement plan uses a new PlanRevision and only evidence captured
from the new scene revision.

## PAOS ownership review

- **Generic domain / AgentLoop** owns task lifecycle, recovery decision,
  replacement PlanRevision, evidence freshness and the prohibition on reusing
  old Action inputs.
- **Pick-place workflow** projects an Adapter-declared, known and safely
  recovered Action failure into the generic
  `refresh_perception_before_motion` recovery semantic.
- **Isaac Adapter** owns possession measurement, configured robot posture,
  gripper release, reverse-path execution, collision checks and terminal phase
  feedback.
- **Perception and grasp Providers** create the next observation, candidate set
  and task-affordance set.  They receive no executable candidate reference from
  the failed revision.

No AgentLoop contract gains USD paths, joint vectors or simulator handles.

## Safety boundary

Automatic recovery is allowed only when all of the following are measured:

- the failed phase is `acquire`;
- the failure code is explicitly configured as recoverable;
- the selected object remains on its support within placement tolerances;
- no valid bilateral grasp, selected-body load, or fresh bilateral contact
  manifold remains;
- the object linear velocity is below the configured support threshold;
- the configured initial arm and gripper positions are available;
- the qualified route started at the configured observation-home joints, so no
  unqualified direct home trajectory is invented;
- every reverse arm command passes the existing joint, workspace and collision
  checks.

If any condition is false, if opening or retreat fails, or if cancellation is
requested, the result stays unknown/uncertain and no new grasp is authorized.

## Evidence and freshness boundary

The failed Action and its phase video remain historical diagnostic evidence.
After any world-changing command the worker advances the scene revision.  The
next Query must use a new observation reference, point cloud, labels,
simulator-truth geometry, candidate set and preparation generated from that
revision.  Old readiness, candidate references and preparation references are
not executable in the replacement revision.

## Acceptance matrix

1. Known `physical_grasp_lost` with a supported object returns to the configured
   observation posture, opens the gripper and reports `possession_state=empty`,
   `returned_to_safe_pose=true`, `observation_ready=true` and
   `requires_replan=true`.
2. Holding or uncertain possession never triggers retreat.
3. A collision, joint limit, cancellation or tracking failure during retreat
   returns an unknown/uncertain outcome and stops automatic recovery.
4. The workflow maps only an explicit Adapter recovery receipt to
   `refresh_perception_before_motion`.
5. Recovery decisions offer replan with a fresh Query for that receipt and do
   not expose same-capture opaque alternatives.
6. Existing no-motion alternative recovery remains unchanged.

## Implemented result

- `IsaacPhaseMotion` now records the arm commands actually issued from the
  qualified route.  For a configured known acquire failure it stops first,
  proves supported/empty state, opens at fixed arm joints, and replays only that
  measured command path in reverse.  Every reverse sample reuses the existing
  joint-limit, workspace, collision, cancellation, application-liveness and
  execution-step checks.
- The LabUtopia scene keeps initial arm/gripper values in Adapter-private
  session resources; no simulator path or joint vector was added to AgentLoop.
- `object.acquire` carries provider-neutral `returned_to_safe_pose` and
  `observation_ready` terminal facts.  `manipulation.execute_subtask` projects
  `refresh_perception_before_motion` only when the failure is known, the object
  is supported, possession is empty, the scene revision advanced, and all safe
  recovery facts agree.
- Recovery decisions inspect only the latest Action attempt for the node.  A
  safe older receipt cannot override a newer unsafe failure.  Physical recovery
  never exposes same-capture alternatives; the replacement revision is prompted
  to begin with fresh observation and fresh candidate Queries.
- Final implementation review found and fixed one Major postcondition gap: a
  residual fresh bilateral manifold with zero impulse could previously leave
  `held=false` after retreat.  Recovery completion now explicitly rejects both
  selected-body contact load and fresh bilateral manifolds before declaring
  observation readiness.
- Validation completed with 625 relevant Adapter/workflow tests (2 native-USD
  skips), 65 AgentLoop/long-horizon tests, focused residual-contact regression,
  Ruff, compile checks, JSON parsing and diff whitespace checks.  No live motion
  was executed by these tests.
