# Implementation Review: v16.9.3

## Findings

1. **Major, fixed - production retiming invalidated the v16.9.2 state test.**
   `phase_motion.py` used `last_stage == "close"`, which is true for the first
   lift point only. The fresh run failed on the eighteenth retimed lift point.
   The Adapter now persists closure confirmation across the initial lift.
2. **Major, fixed - a persistent closure fact alone would be too broad.** A
   one-cycle unload later in free-space transport must not be tolerated. The
   grace now also requires the measured body pose to remain inside the existing
   support-contact departure window.
3. **Major, fixed - the original replacement-plant test did not model
   production `execution_steps`.** The new delayed-transient regression retimes
   the route before execution and therefore reproduces the observed
   point-per-control-period lifecycle.
4. **No public-contract leak found.** The new state is local to
   `IsaacPhaseMotion`; no PhysX manifold, USD path, threshold or transient field
   is added to AgentLoop, Coordinator, Provider or Tool contracts.
5. **Live workflow remains unresolved.** The latest Action has unknown outcome
   and uncertain possession after world change. This repair cannot be accepted
   as proof of acquisition, pouring or stirring; another reset is mandatory
   before motion.

## Architecture and safety acceptance

- Generic domain behavior is unchanged: semantic ordering, opaque references,
  lifecycle, cancellation, settlement and recovery remain Coordinator/AgentLoop
  responsibilities.
- Environment-specific behavior stays in the Isaac Adapter: contact sampling,
  support-window interpretation and controller stop/continue decisions.
- Evidence remains truthful. A tolerated sample still records
  `contact_load_valid=false` and `grasp_valid=false`, plus the private decision
  marker `contact_transient_grace_used=true`.
- No collision, IK, workspace, aperture, pose or contact threshold is relaxed.
- The next interval and every later unload remain fail-closed after the single
  grace is consumed.

## Acceptance

Accept the local Adapter timing-boundary repair after focused and full
regressions, static checks and log review pass. Do not accept the requested
two-pour/stir workflow as complete. Do not reuse the v16.9.2 execution scene.
