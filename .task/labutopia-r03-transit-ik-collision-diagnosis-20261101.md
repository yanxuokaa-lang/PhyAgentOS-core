# LabUtopia R03 transit IK and collision diagnosis

## Scope

- Run workspace: `out/lab-fullchain-truth-20261101-all-small-vessel-execute-r3/`
- Task: `task_135e08bbdf8e429b`
- Scene revision: `labutopia-tabletop-rod-rack-v1:0e65f1fb903d4ef88a533d530cec59c1:0`
- Qualified R03 opaque grasp candidates: `15`, `16`, `23`
- Motion result: preparation-only failure; no controller outcome, world change, or possession.

## Diagnosis

1. `self_collision` and `route_collision` were representative Adapter rejection labels, not root-cause summaries. Mixed clearance failures previously preferred any `route_collision` even when most attempts failed IK.
2. Candidate `16` exposed an IK branch leak. Lula returned a solution with `4.201 rad` maximum joint displacement. The code attempted nearby IK, but when nearby IK failed it retained the distant Lula solution and collision-sampled the joint interpolation.
3. Collision diagnostics reported the Cartesian waypoint and final IK TCP, not the intermediate joint sample that actually collided. A high final TCP therefore did not prove the fingers were high at the collision sample.
4. Candidate `15` at `0.08 m` clearance also exceeded the intended continuity threshold (`0.678 rad`). Candidate `15` at `0.04 m` and candidate `23` at `0.04 m` still require comparison of the conservative Lula collision-sphere proxy against final-composed collision geometry before declaring a physical self-collision.
5. Candidate `15` and `16` share the same grasp orientation and differ by only millimetres, yet the IK displacement changes from a bounded solution to `4.201 rad`. This is consistent with branch discontinuity or a near-singular wrist configuration.
6. The active evidence frame is `tabletop_third_person`; wrist-camera visibility is a separate scene/readiness issue and did not cause this preparation rejection.

## PAOS ownership

- AgentLoop/Coordinator: semantic order, user parameters, opaque selection, lifecycle, settlement, and stop behavior.
- Task-Affordance Provider: process-compatible grasp qualification without robot or USD mechanisms.
- Isaac Adapter: robot reset state, frame transforms, continuous IK, route construction, workspace, self/environment/payload collision, and measured execution feedback.
- No joint angles, USD paths, collision geometry, or IK policy may enter AgentLoop or the shared task-affordance contract.

## Implemented repair plan

1. Configure a maximum per-waypoint joint displacement in the LabUtopia motion profile.
2. Accept the primary Lula solution only when it is finite, successful, and continuous from the previous accepted joint state.
3. If the primary solution is discontinuous, accept only a successful nearby IK solution inside the same limit; otherwise reject with `ik_discontinuity` before collision sampling.
4. Record the actual collision-check joint sample and TCP in the failure evidence.
5. Report mixed clearance failures as `route_unavailable` while retaining every clearance-specific failure in the detail.
6. Keep all workspace, IK, collision, payload, Action, and zero-motion safety gates unchanged.

## Acceptance criteria

- A `4.201 rad` primary IK solution cannot reach collision sampling when nearby IK fails.
- A continuous nearby solution replaces the distant primary solution and remains collision-qualified.
- Collision errors identify the checked joint sample and checked TCP.
- Mixed self-collision/route-collision/IK clearance results are not mislabeled as one dominant collision cause.
- Adapter preparation continues to try the next same-capture qualified opaque candidate after `ik_discontinuity`.
- Focused tests, Ruff, compileall, and `git diff --check` pass without starting Isaac motion.

## Implemented result

- `maximum_waypoint_joint_delta_rad=0.5` is an Isaac motion-profile parameter, not an AgentLoop or task-definition field.
- A discontinuous primary Lula solution can proceed only if nearby IK returns a successful, finite solution within the same joint-delta limit. Otherwise preparation returns `ik_discontinuity` before collision sampling.
- Collision failures now report the actual checked joint sample and checked TCP in addition to the target and final IK TCP.
- Mixed clearance failures return `route_unavailable` while retaining each clearance's original `ik_discontinuity`, IK, or collision evidence.
- `paos_client` preserves `ik_discontinuity` and `route_unavailable` as Adapter-owned no-motion failures. The Skill boundary consumes explicit `requires_replan` and `recommended_action`; it does not search diagnostic strings and it preserves the difference between selecting a same-capture alternative and refreshing grasp candidates.

## Post-fix no-motion evidence

- Workspace: `out/lab-fullchain-truth-20261101-ik-continuity-no-motion-r1/`
- Session: `cli:lab-2a6cdb5274e6`
- Task: `task_a5127feeb8c8476a`
- `simulated_motion_enabled=false`, `controller_outcomes=[]`, `world_change_started=false`, `outcome_known=true`, `possession_state=empty`.
- Candidate `16`: primary joint deltas `4.420/4.201 rad` at `0.04/0.08 m`; candidate `15`: `4.431/4.232 rad`; candidate `23`: `3.972/3.575 rad`. All are rejected before collision sampling when nearby IK cannot satisfy the full pose tolerance.
- All three candidates return `inverse_kinematics_failed` at `0.12 m` clearance.
- The prior `finger overlaps table` and `link2 overlaps link5/link6` labels do not recur because the invalid distant branch no longer reaches collision sampling.
- A small nearby joint delta alone is not acceptance evidence: candidate `16` reports `0.021493 rad`, but the nearby solver still returned failure and therefore did not meet the complete position/orientation tolerance.

## Remaining blocker

The remaining blocker is the Cartesian route and orientation schedule for `transit_cross`. The next change should remain Adapter-private: raise using the current orientation, translate with a safe transport orientation, reorient at staging, and then approach; bottle-axis-equivalent grasp orientations should be enumerated and ranked by continuous IK plus the unchanged safety checks. Collision thresholds must not be relaxed to hide the route-construction failure.
