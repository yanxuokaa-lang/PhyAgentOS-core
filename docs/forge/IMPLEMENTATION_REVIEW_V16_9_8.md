# Implementation Review v16.9.8

## Findings

### Blocker

None.

### Major

None after review.

### Minor - accepted: pruning evidence remains linear in configured variants

Each pruned route writes one bounded `acquire-search` artifact. This remains
O(configured variants), but it replaces multiple stage-start/stage-complete,
IK and collision-query artifacts for every eliminated route. The deployment
has 104 configured variants, and the artifact includes only configuration
orders, failed stage, source failure code/attempt ordinal and zero-motion
lifecycle fields. No additional aggregation mechanism is justified at this
scale.

## Architecture review

- Generic domain / AgentLoop still owns the semantic order
  `R05 -> R03 -> GLASS_ROD`, same-set opaque-reference selection, dependency
  blocking, cancellation and settlement.
- The implementation is confined to `IsaacPhaseMotion.prepare()`, the Adapter
  owner of route generation, qualification, search priority and timeout
  evidence. No public Tool schema or Provider candidate contract changed.
- Exact prefix identities contain only invocation-local generated stage names
  and pose matrices. There is no hash, persistent cache, baseline, USD path,
  coordinate constant or target label in production logic.
- A route is pruned only when it contains an exact prefix previously rejected
  during the same preparation. Routes diverging before the failed stage still
  run the complete existing qualification path.
- Staged enumeration follows the declared configuration priority: transport
  orientation, clearance, corridor and symmetry. Minimum-joint-travel ranking
  remains unchanged after qualification.

## Safety review

- Preparation remains read-only and zero-motion. Pruning can only preserve an
  earlier failure; it cannot admit a route or authorize motion.
- IK, joint-continuity, workspace, aperture, swept-collision, payload, contact
  and possession checks are unchanged.
- Timeout remains fail-closed for unique prefixes and produces
  `route_search_timeout` before the worker transport deadline.
- `attempted_count` now means routes that actually entered full qualification;
  `pruned_count` reports exact-prefix eliminations. Prune artifacts retain the
  source failure code and attempt ordinal with
  `motion_authorized=false` and `world_change_started=false`.
- The cache is a local variable inside one `prepare()` call. It cannot survive
  candidate replacement, reset, scene-revision change or a later preparation.

## Evidence

- Focused prefix/search regression: 11 passed.
- Complete phase-motion regression: 143 passed.
- Full Isaac Adapter plus subtask executor regression: 494 passed, 2 skipped.
- Ruff, compileall, motion-profile JSON parsing and `git diff --check` pass.

## Fresh runtime evidence

- Independent native reset and no-motion AgentLoop workspaces confirmed an open
  empty gripper, zero commands and new scene revisions, observations, candidates
  and preparations. No historical task or readiness was reused.
- Fresh execution task `task_9fa51be5ed0d4e3f` selected only the current-capture
  R05 evidence and direct-predecessor opaque references before Action.
- Route preparation reached 65 of 104 variants and returned
  `route_search_timeout` at the 600-second Adapter deadline. Failure counts were
  18 self-collisions, 18 IK discontinuities, 14 route collisions and 14 inverse
  kinematics failures.
- `pruned_count=0` with 65 failed prefixes is expected for this capture: every
  failure was recorded after a distinct post-divergence route prefix. The
  implementation did not incorrectly collapse near-equal or differently staged
  routes.
- Motion remained unauthorized, no world change started, possession stayed
  empty and no controller outcome, phase feedback or phase video exists. R03
  and GLASS_ROD remained dependency-blocked.

## Acceptance boundary

The implementation is accepted as an Adapter-local exact-prefix optimization.
Fresh runtime evidence proves its fail-closed behavior and lifecycle isolation,
but not a speedup for the current capture because all failures had unique exact
prefixes. It does not prove that R05 has a feasible complete route or that
grasp/pour/stir execution succeeds. Any later live retry must again create a new
process, workspace, scene revision, perception capture, candidate set and
preparation; historical task/readiness state remains ineligible.
