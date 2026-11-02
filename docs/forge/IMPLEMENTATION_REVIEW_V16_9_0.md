# Implementation Review: v16.9.0

## Findings

1. **Major, unresolved — no full acquire route reaches readiness.** The fresh
   authorized simulation run rejected 8 direct and 85 staged route variants.
   The 1200-second host turn ended with `awaiting_replan`; no readiness,
   controller outcome, video or physical grasp result was produced. This work
   must not be accepted as fixing the user's trajectory or bottle-retention
   problem.
2. **Fixed — the historical R05 candidate 69 had asymmetric sidewall support.**
   Provider qualification now uses the candidate's complete calibrated frame
   and same-capture point cloud to reject unbalanced or axis-misaligned bottle
   grasps. Replay rejects candidate 69 while retaining eight candidates,
   including candidate 100. This is not live grip proof.
3. **Fixed — the configured staged route is no longer the only route shape.**
   Adapter preparation tries a direct current-pose/pregrasp route and then the
   staged fallback. Both use the same complete route qualifier. Native result
   shows the direct strategy was attempted, but all its candidates failed
   current IK/collision checks; the route-shape improvement is not yet
   demonstrated as usable or visually natural.

## Architecture

- Generic task semantics, AgentLoop and Coordinator lifecycle remain unchanged.
- Grasp filtering/ranking stays in `LabGraspTaskAffordanceProvider` and emits
  only existing opaque candidate references.
- Route generation, frame transforms, IK and collision remain in Isaac Adapter.
- Preparation remains no-motion. Existing workspace, collision, continuity,
  aperture, contact and drift limits are unchanged.
- No Action recovery pose mutation, public schema widening, hashes or extra
  lifecycle owner were introduced.

## Evidence grades

- **Contract evidence:** 464 regression tests pass, 2 native-USD tests skip in
  the default Python runtime; the skipped cases are unrelated to route/grasp
  qualification. Ruff, compileall and diff checks pass.
- **Provider evidence:** historical same-capture replay rejects candidate 69
  for contact asymmetry; 8/503 historical candidates pass geometric filters.
  Fresh no-motion run admits candidate 178 through both geometry and short
  approach feasibility.
- **Preparation evidence:** fresh full route search rejects all 93 variants.
  No readiness was emitted.
- **Live execution evidence:** none. The simulation Action did not reach a
  qualified route or controller command. No video was generated.

## Acceptance

Do not mark the user's problem solved. Before a live grasp acceptance claim,
produce a fresh readiness for a full route, then inspect the selected grasp in
the scene and retain closure/lift feedback showing bilateral contact and
bounded object displacement. Save the resulting phase video. If full-route
preparation again fails, diagnose the actual current grasp frame, initial TCP
state and failing stages; do not loosen safety thresholds to force admission.
