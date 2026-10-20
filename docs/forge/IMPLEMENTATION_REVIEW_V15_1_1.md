# Implementation Review v15.1.1: Runtime-backed PAOS Subtasks

## Findings and disposition

- **Blocker fixed:** the first executor was only a synchronous injected-call
  helper. `RuntimeSubtaskDriver` now uses the existing `CapabilityRuntime`
  start/result/cancel lifecycle, and `SubtaskActionEndpoint` is registered only
  when the host supplies an observation refresh callback.
- **Major fixed:** acquire/place input provenance was incomplete. The binding
  now carries candidate-set, preparation, candidate, capability, and assignment
  references required by the existing PAOS Tool schemas.
- **Major fixed:** a scene revision change after acquire could otherwise reuse a
  stale grasp/pose. The driver requires a same-identity, same-calibration fresh
  binding before the next internal Tool; without it, the outer subtask settles
  as `unknown` and recommends `refresh_perception_before_motion`. The refresh
  now also requires a new observation reference, the same camera frame, and
  new candidate-set, preparation, candidate, and assignment references; old
  motion artifacts cannot be paired with a new scene revision.
- **Major fixed:** the plan node payload was nested under `subtask`, which did
  not match the public Tool input contract. It is now projected as the exact
  `manipulation.execute_subtask` input object.

## Architecture review

- Existing `CapabilityRuntime`, `ActionAdmission`, `ActionDriver`, receipts and
  Coordinator settlement remain the owners. No second scheduler or settlement
  store was added.
- One outer `manipulation.execute_subtask` invocation owns the subtask. Internal
  actions are normal Runtime invocations and never become AgentLoop nodes or
  model turns.
- The endpoint does not import Isaac Sim or resolve Prim paths. Provider access
  remains behind existing Tool endpoints.
- Registration requires `refresh_subtask_binding`; a host without a real
  observation refresh path does not advertise this motion-capable subtask Tool.

## AgentLoop review

`compose_subtask_plan()` emits one executable node per subtask and a single
verification join. The Runtime driver polls one internal lifecycle step at a
time, preserving AgentLoop's outer turn and PAOS cancellation/unknown behavior.
The existing AgentLoop reducer remains unchanged and can consume the outer
terminal result through its normal ToolExecutionRecord/NodeSettlement path.

## Robotics safety review

- No direct actuator, simulator, or provider call was introduced in the
  executor.
- Every internal Action goes through existing admission and cancellation.
- A changed scene revision is a hard boundary requiring refreshed perception,
  frame, calibration, identity, and motion-candidate provenance; no stale pose
  or grasp artifact is silently reused.
- This stage has no live Isaac Sim or hardware run. Motion authorization remains
  owned by the registered provider endpoints.

## Seven-dimension acceptance

| Dimension | Result | Evidence / remaining gap |
|---|---|---|
| 1. Perception source | Partial | Binding is observation-derived by contract; live camera/understanding adapter is not implemented here |
| 2. Binding/frame/calibration/freshness | Pass for contract | Complete acquire/place references, stale rejection, and refresh observation/frame/calibration/candidate provenance checks |
| 3. Agent subtask granularity | Pass | One PlanNode and one outer Runtime invocation per subtask |
| 4. IK/workspace/collision | Not evaluated | Existing acquire/preparation providers own this; no motion proof in this stage |
| 5. Acquire/hold/release/place feedback | Partial | Existing Runtime feedback is preserved in internal receipts and aggregate summary; no Isaac Sim execution |
| 6. Pour/stir process feedback | Partial | Measurements can flow through receipts; no live process evidence produced |
| 7. Settlement/unknown/cancel/recovery | Pass for Runtime contract | Outer cancel propagates to active inner invocation; unknown stops sequence and requests reconciliation |

## Verification

```text
123 passed: planning, Runtime subtask, persistent runtime, multi-object,
held manipulation, and composite manipulation regressions
ruff check: passed
compileall: passed
git diff --check: passed
```

No Isaac Sim process, Gateway service, or physical motion was run in this
stage. The next gate is to supply the LabUtopia observation refresh adapter and
run one dry-run subtask through the real adapter before any live motion.
