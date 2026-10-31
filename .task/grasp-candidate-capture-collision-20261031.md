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

## R8 Runtime Validation and Updated Blocker

- Run: `out/lab-fullchain-truth-20261031-r8/`.
- AgentLoop session: `cli:lab-d7a500a743a9`; task: `task_454d6babe12548b1`;
  scene revision: `labutopia-tabletop-rod-rack-v1:bb4ff98ae16543b8ab9665f6e2841e25:0`.
- The run used `perception_mode=simulator_truth`, `OMNI_KIT_ACCEPT_EULA=Y`,
  and explicit `--execute`; the user parameters and R01 -> R02 -> GLASS_ROD
  order were included in the task instruction.
- R01 `manipulation.process_features` and its no-motion
  `manipulation.prepare_process_features` Query both completed. Grasp/process
  evidence was accepted far enough to proceed into task-affordance Query; the
  prior stale error `grasp/process evidence is not from the same capture` did
  not recur.
- Task-affordance Query returned `unavailable` with
  `source geometry does not identify a pour lip and outward flow direction`.
  The candidate-set composite index therefore resolves the previous blocker;
  the next independent blocker is insufficient process geometry to qualify a
  bottle pour lip and outward flow direction.
- Coordinator acceptance has zero `execution_records` and zero
  `controller_outcomes`; R01 acquire/pour, R02 pour, stirring, and stow were
  not started. No affordance Preparation or Action was entered. The task was
  cancelled at the explicit fail-closed boundary.
- The run configuration selected the simulator-truth Provider; no ReMake,
  DFNet, or SAM2 worker was started. No liquid-transfer or chemistry outcome
  was measured.

### Next Implementation Boundary

- Do not weaken `LabGraspTaskAffordanceProvider._valid_pour_direction` or
  synthesize a pour lip from the current opening/axis fields. The process
  geometry Provider must establish, from current final-USD geometry or
  independently qualified evidence, which rim region is the pour lip and the
  outward flow direction. If the mesh cannot distinguish that feature, the
  correct result remains `unavailable` until geometry evidence or scene asset
  authoring supplies the distinction.
- The r8 artifact is a live no-motion integration result, not evidence of a
  successful physical action. Further action execution remains blocked until
  the task-affordance Query and its no-motion Preparation succeed.
