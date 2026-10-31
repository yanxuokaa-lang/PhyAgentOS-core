# Grasp Candidate Capture Index Collision

## Diagnosis

- Run: `out/lab-fullchain-truth-20261031-r7/`.
- The public `candidate-set://{scene_revision}/{frame_id}` ref is stable across
  multiple GraspNet proposals in the same scene/frame.
- The run persisted proposals for R01, R02, and GLASS_ROD with the same
  `observation_ref`, `scene_revision`, and `frame_id`, but distinct
  `calibration_ref` values (`af130...`, `ae012...`, and `d189...`).
- `RecordedGraspProvider` keyed its private index only by the public ref. Later
  proposals therefore replaced the earlier capture's calibration/entity set.
- `LabGraspTaskAffordanceProvider` then compared the overwritten entry against
  the R01 process-feature query's `af130...` calibration and returned the
  generic stale error `grasp/process evidence is not from the same capture`.
- The public PAOS ref is not wrong or incomplete for its domain semantics; it
  identifies the scene/frame candidate namespace. The collision is in the
  Adapter-private index, which omitted the capture discriminator already
  carried by `calibration_ref`.

## Architecture Decision

- Tier: C-Safety, because the defect is at a robotics evidence boundary that
  gates Action admission.
- Owner: Isaac Adapter's `RecordedGraspProvider` and
  `LabGraspTaskAffordanceProvider` private capture index.
- Keep PAOS Tool schemas, AgentLoop selection/receipt flow, Coordinator task
  lifecycle, and Gateway Action boundary unchanged.
- Preserve the public candidate-set ref. Index private entries by the pair
  `(candidate_set_ref, calibration_ref)`; merge entity/candidate membership
  only when the pair resolves to the same immutable capture identity.
- A missing entry, identity conflict, or cross-calibration lookup remains
  stale/unavailable. No fallback to scene/frame-only lookup is permitted.

## Concrete Failure and Existing Controls

- Failure: a later per-entity proposal with the same scene/frame overwrites a
  prior proposal, causing valid current-capture evidence to be rejected (or,
  without the calibration check, stale candidates to be accepted).
- Existing public scene/frame refs cannot distinguish repeated captures; Git,
  version numbers, types, or ordinary public-contract validation do not stop
  an in-memory dictionary overwrite. The capture-specific `calibration_ref`
  is already available, so a provider-private composite key resolves the
  collision without hashes, new contracts, or extra gates.
- Any identity mismatch continues to fail closed before grasp qualification,
  no-motion Preparation, and Action admission.

## Implementation and Validation Plan

1. Add a provider-private composite-key helper and use it for grasp index writes,
   task-affordance Query reads, and affordance Preparation revalidation.
2. For repeated proposals under the same composite key, require identical
   observation/scene/frame/calibration identity, then union entity and candidate
   refs; different calibration refs remain isolated.
3. Add regression coverage for R01/R02/GLASS_ROD proposals sharing the public
   scene/frame ref but using distinct calibrations; verify R01 Query and later
   Preparation resolve its own candidate, while cross-calibration or conflicting
   identity evidence fails closed.
4. Run affected Isaac Adapter and PAOS planning/AgentLoop selection tests,
   Ruff, compileall, and `git diff --check`. Do not run manipulation actions.

## Scope Notes

- `.task/current.md` belongs to an unrelated active planning task and is not
  modified by this work.
- No live Isaac run is needed to prove the index regression after the recorded
  r7 artifacts establish the collision. A later fresh no-motion/full-chain run
  may validate runtime integration; motion remains blocked until all subsequent
  task-affordance and Preparation checks pass.
