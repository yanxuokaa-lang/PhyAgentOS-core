# RGB Run Diagnosis: GraspNet OOM and Single-View Acceptance

## Scope

This record covers the latest no-motion run `task_dc64c12d631040ca` on
2026-09-30. Discovery completed, no invocation was created, and the task
stopped at `grasp.propose`.

## Failure A: GraspNet worker resource exhaustion

The RobotWin Runtime log recorded the GraspNet worker being killed by Linux
OOM handling inside `paos-pick-place-workflow-runtime-288.service`. The worker
had approximately 29.9 GiB virtual memory and 9.25 GiB RSS when killed; the
Runtime cgroup peaked at approximately 12.1 GiB with 2 GiB swap. Dora then
reported `failed to send request message to coordinator` / `failed to fill
whole buffer`. The public endpoint reduced this to
`grasp_proposal_provider_error`, so the AgentLoop could not distinguish a
resource failure from an invalid provider result.

The failure is downstream of the worker process boundary, not a Qwen scene
understanding failure: understanding had already succeeded and the killed
process was the GraspNet Python worker. The missing mechanism was bounded
worker input and typed termination evidence. Version numbers and invocation
identities identify a run but cannot prevent the worker from exceeding the
Runtime memory budget; ordinary provider tests did not exercise a SIGKILL.
Without the fix, the process can be killed and the control plane receives an
opaque provider error, encouraging an unsafe retry decision even though no
motion should be attempted.

## Failure B: single-view evidence accepted as multi-view

The successful observation record contained `sensor_ref: camera/head` and one
entry in `views`; it did not contain `camera/front`. The pick-place path was
nevertheless described as synchronized dual-view evidence and downstream
understanding/binding was allowed to consume it. `max_capture_skew_ms` only
bounds timestamp skew; it does not establish that two sensors were captured.

The provider-neutral Core observation endpoint intentionally supports
single-view callers, so its generic schema cannot reject every single-view
record. The previous Skill contract still exposed a `sensor_ref` branch and
the Runtime profile defaulted to it. Primary keys, scene revisions, and
ordinary JSON-Schema validation proved identity and shape, but not the
workflow's declared minimum view cardinality. Without a workflow-owned
acceptance rule, occluded entities can be treated as cross-view identities and
the AgentLoop can proceed with stale or incomplete geometry.

## Repair boundary and acceptance

- The existing ProcessWorker seam classifies SIGKILL/137 termination as
  `worker_resource_exhausted`, preserves return code/stderr tail for logs, and
  fails closed. GraspNet receives a profile-controlled point budget (12,000
  for the affected profile) and no provider fallback is introduced.
- The RobotWin pick-place Runtime profile projects a live ToolSpec requiring at
  least two unique synchronized sensors. The provider-neutral Skill/Core
  contract remains backward compatible for single-view users outside this
  deployment profile.
- Regression tests cover worker classification, resource error propagation,
  point-budget validation, synchronized-view schema, legacy single-view Core
  compatibility, and runtime-profile sensor-set loading.
