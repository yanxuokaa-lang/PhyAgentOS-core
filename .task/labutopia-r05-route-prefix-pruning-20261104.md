# LabUtopia R05 acquire-route prefix-pruning diagnosis

## Runtime evidence

- Fresh execution workspace:
  `out/lab-fullchain-truth-20261103-v16_9_7-execute-r1`.
- Session/task/revision:
  `cli:lab-8748787d1a83` / `task_1336d861021e48b7` /
  `revision_bffd0ee0b6a84de4`.
- Scene revision:
  `labutopia-tabletop-rod-rack-v1:4625a5fcf13e40e48db5681686a79e14:0`.
- R05 used the current-capture opaque candidate
  `candidate://simulator-truth-R05/57c6b3444dc3456ab3bf9fabe8ba88a5-178`.
- Preparation stopped with `route_search_timeout` after 607.655 seconds. It
  started 64 of 104 configured variants and timed out in `transit_orient`.
- The 63 completed failed variants contained 28 `self_collision`, 15
  `ik_discontinuity`, 10 `inverse_kinematics_failed` and 10 `route_collision`
  results. No controller motion occurred; `motion_authorized=false`,
  `world_change_started=false` and possession remained empty.
- R03 and GLASS_ROD stayed dependency-blocked. No phase video exists because
  execution never passed the zero-motion preparation boundary.

## Root cause

- The configured search space has 104 routes: eight direct routes plus 96
  staged routes from three clearances, two transport orientations, four
  staging corridors and four axial symmetries.
- `IsaacPhaseMotion.prepare()` currently performs a complete serial
  `qualify()` call for every combination. Staged routes share the same early
  waypoints (`open`, `transit_raise`, `transit_orient`) across many corridor
  and symmetry suffixes.
- A failure in one of those identical prefixes is recomputed for every
  descendant variant. The second configured transport orientation produced 20
  self-collisions in 23 completed attempts, including repeated
  `panda_link5 overlaps panda_hand` failures at effectively identical
  `transit_orient` prefixes.
- The existing enumeration orders clearance before transport orientation. It
  therefore spends budget on both orientations at 0.04 and 0.08 m before
  trying the preferred orientation at 0.12 m.
- This is an Adapter route-search performance defect. It is not an AgentLoop
  ordering error, a stale-evidence mix, a raw-GraspNet fallback or a reason to
  relax IK/collision/workspace criteria. Five current-capture R05 grasp
  candidates were checked; candidate 178 was the one that passed aperture,
  pregrasp IK, short-approach continuity, workspace and collision checks.

## PAOS ownership decision

- AgentLoop and Coordinator continue to own the semantic order
  `R05 -> R03 -> GLASS_ROD`, direct-predecessor opaque references, dependency
  blocking, cancellation and settlement.
- The Isaac Adapter owns route generation, configured search priority,
  full-route qualification, local pruning and timeout evidence.
- Public Tool schemas, task semantics and Provider candidate contracts remain
  unchanged. No USD path, task label, object coordinate or R05 identifier is
  introduced into generic code.
- Evidence freshness remains one chain. The pruning cache exists only inside
  one `prepare()` invocation and cannot cross a candidate, reset, scene
  revision or later preparation.

## Repair design

1. Generate all route waypoints exactly as before.
2. Represent each waypoint prefix as an exact in-memory tuple of ordered stage
   names and generated 4x4 pose values. Do not add hashes or persistent
   identities.
3. When full qualification fails after a stage has started, record that exact
   failed prefix, failure code and source attempt ordinal.
4. Before qualifying a later route, prune it only when it contains the exact
   same failed prefix. A route that diverges before the failed stage remains
   eligible.
5. Keep `attempted_count` for routes that actually enter qualification and
   record `pruned_count` separately. Pruning evidence remains zero-motion and
   points to the source failure attempt.
6. Enumerate staged routes by configured transport orientation, then
   clearance, corridor and symmetry. This preserves configuration priority and
   remains environment-generic.
7. Keep the existing wall-clock deadline. If unique prefixes themselves
   exhaust it, return `route_search_timeout` with known/no-world-change
   semantics.

## Safety and validation boundary

- Pruning reuses a prior failure result; it never turns a failed route into a
  success and never bypasses qualification for a route whose prefix differs.
- Collision, IK continuity, joint limits, workspace, aperture, contact and
  possession rules remain unchanged.
- The implementation must prove identical-prefix pruning, divergence safety,
  per-call cache lifetime, zero-motion evidence, attempted/pruned accounting,
  configured ordering, later-route reachability and unique-prefix timeout.
- Any live validation must start a new Isaac/LabUtopia process and workspace,
  reset the scene, observe an open empty gripper, and generate a new scene
  revision, perception capture, candidate set and complete preparation. No
  historical task, readiness or preparation may be resumed.

## Fresh live validation

- Native zero-motion reset probe:
  `out/lab-fullchain-truth-20261104-v16_9_8-reset-probe-r1`. It issued zero
  motion commands, read both finger joints near 0.04 m open and produced scene
  revision `labutopia-tabletop-rod-rack-v1:eb4dd9b97f0042068605a3e35b44a305:0`.
- Independent no-motion AgentLoop workspace:
  `out/lab-fullchain-truth-20261104-v16_9_8-reset-no-motion-r2`, task
  `task_36bbc2ddeac84e0a`, revision `revision_359359de053e485a` and scene
  `labutopia-tabletop-rod-rack-v1:0318efdf078e43ff9ae626f1275f2210:0`.
  It produced current-capture R05 candidate
  `candidate://simulator-truth-R05/bb2cb7836cc54dd9889fa0d061ccdfdd-178`,
  four available Query/preparation nodes and zero Action records.
- Fresh execution workspace:
  `out/lab-fullchain-truth-20261104-v16_9_8-execute-r1`, session
  `cli:lab-f0200a9db1cc`, task `task_9fa51be5ed0d4e3f`, revision
  `revision_2851da4273904a19` and scene
  `labutopia-tabletop-rod-rack-v1:5b1cef7b99374ccdadd16ad31207a7c2:0`.
  Its observation, candidate set, readiness and preparation are distinct from
  both the probe/no-motion workspaces and all historical tasks.
- R05 used only same-capture Query and direct-predecessor preparation evidence,
  then started Action invocation
  `invocation://manipulation-execute_subtask/86b8f68e1e9d4525`.
- Preparation timed out after 600 seconds at attempt 65 of 104. The 65 completed
  failures were 18 `self_collision`, 18 `ik_discontinuity`, 14
  `route_collision` and 14 `inverse_kinematics_failed`; the final record is one
  `route_search_timeout`.
- `pruned_count=0` and `failed_prefix_count=65`. Every observed failure happened
  after the route had diverged into a distinct exact prefix, so the repair
  correctly did not merge or skip any of them. This live run therefore validates
  fail-closed exactness and lifecycle isolation, but it does not demonstrate a
  runtime speedup for this capture.
- No controller outcome, phase feedback or phase video was produced.
  `motion_authorized=false`, `world_change_started=false` and possession stayed
  empty. AgentLoop finalized the task as failed and kept R03 and GLASS_ROD
  dependency-blocked.

## Result and next boundary

The implementation is accepted as an Adapter-local exact-prefix optimization:
its contract, failure behavior and cache lifetime are covered by regression and
fresh runtime evidence. It does not resolve the remaining R05 route-feasibility
problem because this capture's failures occur on unique post-divergence routes.
The next diagnosis must profile the expensive full-route qualification stages
and their concrete IK/collision witnesses. It must not broaden prefix equality,
relax safety thresholds or move route policy into AgentLoop merely to reduce the
search time.
