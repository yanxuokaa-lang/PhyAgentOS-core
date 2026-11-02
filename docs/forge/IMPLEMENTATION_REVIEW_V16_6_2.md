# v16.6.2 implementation review / 实现复核

## Findings and disposition / 发现与处理

- **Major — whole-finger bounds caused conservative early rejections.**
  `IsaacPhaseMotion.finger_geometry` bounded each complete authored collider
  before sweeping it. Five recorded intermediate samples had mesh clearance
  but padded empty corners touched the table. Replaced that representation with
  all PhysX cooked convex components, each conservatively sliced as a solid.
- **Blocker for an unsafe alternative — render vertices are not cooked solids.**
  This implementation reads synchronous cooked collision results, preserves
  all components, and includes convex edge/plane intersections in each slab.
  It does not trim vertices, shrink collision margins or exempt the table.
- **Major — geometry failure must not mean clear.** Cooking errors, missing
  callbacks, empty components and invalid solids reject before motion. Native
  callback exceptions are preserved and raised after the callback returns.
- **Minor — finger self-overlap lost structured geometry.** The existing
  rejection now records its box and non-adjacent sphere group, consistent with
  the environment-overlap diagnostics. Public result fields remain unchanged.

No unresolved Blocker/Major was found in the modified representation and its
integration. This is not acceptance of complete acquisition, pouring or stirring.
修复范围内无未处理的 Blocker/Major；完整流程仍以新捕获实测结果为准。

## Architecture / 架构

- Owner: Isaac Adapter (`finger_collision.py` pure geometry/cooking helper,
  `phase_motion.py` current articulation, transforms and overlap queries).
- Generic domain/AgentLoop: semantic parameters and opaque references only.
  No change to task selection, public capability schemas or lifecycle owners.
- Substitution: cooking callback and PhysX query are replaced in unit tests;
  existing provider and qualified-only recovery regressions remain applicable.
- Evidence freshness: components are from the current worker stage. Historical
  replay records original and current identities separately; fresh preparation
  still binds current observation/revision/calibration and all existing checks.
- Safety: full opening/closure travel, held opening uncertainty, original 3 mm
  margin, workspace, joint limits/continuity, robot/payload collision, cancellation
  and settlement are retained. No controller commands or hypothetical joint
  teleportation are used in geometry replay.
- No new hash, public contract, scheduler, policy gate or task-specific pose.

## Evidence / 验证证据

Contract/algorithm tests cover whole-box failure reproduction, full convex
interior/edge coverage, prismatic travel, transformed body/joint frames, measured
opening uncertainty, missing/failed/invalid cooking and unchanged margin rejection.
The affected suite passes 434 tests; Ruff, compileall and whitespace checks pass.

Provider evidence: native replay
`out/lab-cooked-finger-geometry-20261102-r1/geometry.json` returns eight cooked
components per finger, bounded by 53/56 boxes. All five historical intermediate
samples are clear; joints and physics time are unchanged. It replays without
source-contact exemptions. Its lowest unpadded box Z is 0.727045404 m,
versus tabletop Z=0.712386069 m. Padding is still applied during overlap queries.

Live motion evidence: none. No grasp, pour, stir or liquid-transfer success is
claimed. Formal fresh-capture no-motion result:
`out/lab-fullchain-truth-20261102-cooked-finger-no-motion-r1/`, session
`cli:lab-3c4728b402d2`, task `task_9c72fe6c84e94594`, revision
`revision_3b1df384b60c41f4`: cancelled, host exit 1, disabled motion, no controller
outcomes. All three execution records are Queries; task-affordance is unavailable.
Four aperture and 48 approach failures persist (workspace 20, environment 20,
self 4, IK 4). Candidate 17's five finger/table failures have moved to later
hand-sphere/table failures (first TCP Z 0.777973 m versus 0.780287 m before),
confirming the local repair but not final-pose clearance. Candidate 55 still
fails refined finger/table checks near TCP Z 0.742 m. Actual cooked-palm and
final-pose analysis remains separate work; no collision radius is reduced and
no IK branch is declared exhaustive.

## Reproduction / 复现

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_profile.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py

OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/labutopia/bin/python \
  examples/forge-adapters/isaacsim_lab/scripts/inspect_collision_receipt.py \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --receipt out/lab-fullchain-truth-20261102-native-coordinate-no-motion-r2/artifacts/labutopia/grasp-approach-feasibility/ce11776449c344e299f7b6af02cdfed8.json \
  --output out/lab-cooked-finger-geometry-NEW
```
