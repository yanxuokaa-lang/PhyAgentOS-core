# v11.4.2 Post-place observation retreat review

## Finding

The persistent RoboTwin route already executed `release -> retreat`, but its
retreat contained only one provider-profile waypoint: a 0.10 m world-Z offset
from the release pose. The Action could therefore be terminal-successful while
the end effector remained above the destination and occluded the next camera
observation.

This is an execution-route issue, not an AgentLoop or Coordinator issue. The
Agent still owns the semantic destination and recovery decision; the Runtime
owns the physical retreat geometry.

## Disposition

The selected arm's end-effector pose is captured immediately before route
execution. A second waypoint is appended to the existing `retreat` phase. Both
no-motion route evaluation and the persistent Action use the same Runtime-owned
waypoint helper. The waypoint is passed through the existing planner, workspace,
joint-limit, collision, table-clearance, stop, and trajectory validation. A
planning or execution failure in this final retreat keeps the route rejected or
the Action failed; there is no direct robot reset and no Agent-side gate.

## Seven dimensions

| Dimension | Result | Evidence |
|---|---|---|
| Architecture integration | PASS | Change is confined to RoboTwin Runtime route geometry and the existing no-motion/Action route; PAOS Core, Coordinator, AgentLoop, and Skill contracts are unchanged. |
| Profile/configuration | PASS | Existing `route_policy` still controls the release offset and retreat direction/distance; the additional target is derived from the selected Runtime arm state, not a hard-coded coordinate. |
| AgentLoop and semantic binding | PASS | Agent continues to select entity, candidate, arm, and destination. Runtime adds only execution-owned post-place retreat state; no semantic identity or target is rewritten. |
| Errors/observability | PASS | The extra segment is represented in the existing `retreat` phase records; planner failure remains attributed to the route phase and cannot be hidden by release success. |
| Safety/no-motion boundary | PASS | No-motion evaluation and Action execution use the same helper and existing safety checks. The change does not call `reset`, bypass Gateway admission, or authorize motion. |
| Tests/reproducibility | PASS | Focused route/probe tests: 74 passed. Adapter suite: 639 passed, 1 skipped. `compileall` and `git diff --check` passed. |
| Documentation/release/E2E | PARTIAL | The implementation and changelog are complete. A fresh isolated Oracle run is still required to verify that the post-place camera view is clear and that the final three-block verifier can continue. |

## Acceptance boundary

The fix is code-level accepted at the stated scope. The previous task remains a
valid failed recovery run and is not rewritten. Before the next benchmark run,
install this Runtime version in isolation and verify one complete three-block
task. The acceptance must inspect the post-place pose and camera frame, not only
the Gateway terminal status.
