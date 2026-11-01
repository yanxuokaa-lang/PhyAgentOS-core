# LabUtopia R03 Staging Corridor Diagnosis

## Scope

- Workspace: `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/`
- Session: `cli:lab-b11c91c66271`
- Task: `task_b16f8e5cbeb84dda`
- Action: `invocation://manipulation-execute_subtask/3ebe297dca4e4fbf`
- Scene revision: `labutopia-tabletop-rod-rack-v1:74e728eececc4cc590e7bd8dc431f73a:0`
- Mode: no-motion; `simulated_motion_enabled=false`.
- Perception: same-capture Isaac/LabUtopia labels, depth, point clouds, and final-composed USD geometry; no ReMake dependency.

## Implemented Boundary

The change remains private to the Isaac Adapter. `AgentLoop` and the shared manipulation Tool contracts still carry task semantics, user parameters, evidence references, and opaque grasp references only. The Adapter now reads a bounded corridor list from its motion profile and derives each route from the qualified grasp pose and approach vector:

- final approach distance;
- additional staging backoff along the measured approach direction;
- signed horizontal tangential offset;
- existing clearance, transport-orientation, and geometry-supported axial-symmetry alternatives.

Every resulting route still passes the unchanged workspace, full-pose IK, `0.5 rad` waypoint continuity, joint-limit, self-collision, environment-collision, payload-collision, and possession preparation. The implementation has no R03/R04 label branch, no fixed object coordinate, and no public-contract extension.

## Runtime Result

R03 process-feature Query/preparation and task-affordance Query/preparation succeeded. Action preparation consumed only the same-capture qualified opaque refs `16`, `23`, and `15`.

Each grasp exercised:

```text
3 clearances x 2 transport orientations x 4 corridors x 4 axial angles = 96 routes
```

All `288` routes failed before controller start:

| Candidate | IK discontinuity | IK unavailable | Self-collision | Environment collision | Total |
|---|---:|---:|---:|---:|---:|
| `16` | 45 | 13 | 6 | 32 | 96 |
| `23` | 51 | 18 | 12 | 15 | 96 |
| `15` | 44 | 18 | 3 | 31 | 96 |
| **Total** | **140** | **49** | **21** | **78** | **288** |

Failure phases:

| Phase | Count |
|---|---:|
| `staging_reorient` | 173 |
| `approach` | 92 |
| `transit_cross` | 23 |

The new corridor candidates were actually evaluated, but none converted the existing grasp orientations into a continuous collision-free Franka route. Corridor `1` and `2` reduced self-collision relative to the legacy corridor, while increasing staging IK discontinuities. Corridor `3` reduced discontinuities relative to corridor `1/2` but reintroduced more environment and self-collision failures. The remaining blocker is therefore not missing corridor enumeration; it is the compatibility between the qualified final grasp orientation/approach and the robot/table/neighbor geometry.

## Safety Settlement

- `outcome_known=true`
- `world_change_started=false`
- `possession_state=empty`
- `controller_outcomes=[]`
- `completed_tool_ids=[]`
- R04 and GLASS_ROD did not start.

No `--execute` rerun is permitted from this result because no complete R03 route qualified. The static five-second 1600x1200 preview at `artifacts/labutopia/no-motion-video/staging-corridor-observation.mp4` is labelled as no-motion observation evidence and is not an Action execution artifact.

## Review Finding Resolved

The first no-motion run exposed an unbounded diagnostic response: 96 full route exceptions per candidate produced an approximately 74 KB Action error and pushed the Agent context to about 174k tokens. The Adapter now reports bounded aggregate counts by failure code, phase, corridor, clearance, and transport orientation plus one truncated representative example per group. Search behavior and safety qualification are unchanged.

## Next Evidence-Driven Change

Do not add more global offsets or lower safety thresholds. The next Adapter/Provider experiment should test task-conditioned grasp-orientation feasibility before full route expansion:

1. Keep GraspNet/native candidate provenance and task-affordance opaque references unchanged.
2. Add an Adapter-private no-motion reachability score or Provider-side task-affordance feature that evaluates the final grasp orientation and short final approach against the embodiment, without exposing joints or USD paths to AgentLoop.
3. Prefer grasp alternatives whose final approach clears the table and adjacent R04 before spending the full corridor product.
4. Preserve the same-capture boundary and run no-motion qualification again.
5. Enable simulated motion only after one complete acquire route passes every current gate.
