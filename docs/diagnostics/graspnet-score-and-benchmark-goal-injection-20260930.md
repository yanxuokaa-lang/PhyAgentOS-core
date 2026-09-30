# GraspNet score and benchmark goal injection

## Evidence and diagnosis

Task `task_204c6a8d4d6a4de7` failed at record `tool_a65a0e5e282a4085`
with `grasp_proposal_adapter_error: grasp worker score is invalid` after successful
observe, understand, bind and task.goal. GraspNet pred_decode weights native
scores by predicted tolerance; its native ranking value is not guaranteed to
fit the provider-neutral [0,1] range. The worker emitted it unchanged.

task.goal returned benchmark-task-definition destinations, but the Runtime also
published manipulation.staging. Skill guidance recommended staging without
qualifying the goal-source mode. The Agent replaced externally injected goals
with observation-owned destinations. This is a policy/wiring error, not missing
benchmark geometry, and does not require simulator geometry for perception.

## Required behavior / 需求

- Benchmark mode: task.goal externally injects placement regions; exact entity
  correspondence comes from current scene.bind. Agent chooses order and grasp,
  not replacement goals. Occupied or unreachable goals remain unavailable.
- Autonomous observation-owned mode: existing target/staging behavior remains.
- Saturate native scores above 1 at the GraspNet worker boundary, preserve native
  ranking and diagnostic values, filter negative scores and reject non-finite
  values. Scores remain advisory, not probabilities or motion authorization.
- Preparation resolves benchmark destination against task-definition facts even
  if an observation-owned target is present in an old cache. No new safety gate
  or hash is needed: the existing goal_source and unique destination/entity
  correspondence are sufficient at the existing preparation boundary.
- No old task is resumed, no invocation is repeated and no motion is tested.

## Validation

Focused worker/adapter tests, both goal-source modes, cached-target bypass,
Runtime tool visibility, Coordinator destination propagation, packaging and
seven-dimension review must pass. Real grasp success and full video/verifier
acceptance require a subsequent user-run task, not these no-motion tests.
