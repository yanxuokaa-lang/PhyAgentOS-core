# Current Task: LabUtopia R03/R04 full-chain grasp coverage

## v16.7.1 qualified-grasp Action handoff / 执行衔接

- Diagnosis: `.task/labutopia-action-handoff-20261102.md`.
- Previous run explicitly prohibited Actions and had execute=false. Seven
  qualified combinations did not prove full-route readiness or authorize motion.
- Fix mode-specific deployment guidance and relaunch with explicit simulation
  execution and fresh evidence; preserve all Runtime route and recovery checks.
- Reuse Adapter phase recording; retain actual completed/failed phase receipts
  and videos. Generic AgentLoop/Coordinator ownership remains unchanged.
- First workspace: `out/lab-fullchain-truth-20261102-qualified-execute-r1/`.
- r1 reaches the R03 Action with exactly seven qualified references, then fails
  at the first preparation with a 900-second worker timeout; no world change.
- Adapter adds configurable first-feasible full-route selection (old default
  remains minimum travel) and private per-route/stage progress artifacts.
  Mixture deployment uses first-feasible. All safety checks remain unchanged.
- 425 Adapter/executor regressions pass. Fresh r2 in
  `out/lab-fullchain-truth-20261102-qualified-execute-r2/` qualifies a full
  acquire route in 8.182 s (candidate 367; r1 selected 420, not a controlled
  timing comparison), then executes actual transport/approach/insertion/close.
- Final r2 awaits reconciliation: grasp_transform_mismatch before lift,
  measured attachment error 34.220 mm / 0.197260 rad versus 8 mm / 0.08 rad.
  Single-finger contact during open-gripper insertion pushes the body 26.785 mm;
  closure raises displacement to 33.487 mm. Do not continue with uncertain hold.
- Raw 52.55-second/3153-frame video is intact; H.264 copies under videos/ include
  the completed transportation/approach prefix and the full failed attempt.
  stage-videos.json preserves exact frame boundaries and outcomes. No pour/stir.

## v16.7.0 local repair validated / 候选覆盖与提示修复已验证

- Diagnosis: `.task/labutopia-grasp-coverage-repair-20261102.md`.
- Same-cloud replay finds two native worker candidates satisfying existing
  process/aperture rules and a padded-palm/table-plane necessary condition;
  both disappear under the old retained cap of 64. They are not yet route-qualified.
- Align deployed retention with the existing 512 sampling cap, preserving
  original poses/scores, NMS, process rules, same-capture references and robot checks.
- Substituted production Provider regression reproduced 64 vs 70 contacts,
  then passes after the profile correction. No AgentLoop or public schema change.
- Fresh no-motion run: `out/lab-fullchain-truth-20261102-full-pool-no-motion-r1/`.
- Retention-only native result: task cancelled; 21 aperture failures, 144 final
  palm/table records and 16 final finger/table records. The recovered hypotheses
  remain blocked by finger sweep; no IK or controller action was reached.
- Continue within the existing Grasp Provider: full cloud plus at most three
  observed PCA intervals, native inference/inverse transforms and geometric
  sampling. Defaults stay compatible, public interfaces and all checks stay.
- 463 affected tests pass; regional historical inference yields 9855 native
  thresholded predictions sampled to 512. This is not a safety verdict.
- Regional r1 failed semantic label binding; r2 retained 508/506/24 candidates
  but failed at 339858-token prompt expansion. Generic task/node/working-set
  projections now summarize large arrays without changing complete Coordinator
  bindings, small process parameters, selection or Tool materialization.
- Regional r3: `out/lab-fullchain-truth-20261102-region-no-motion-r3/`,
  task `task_a87e6bb320964db7`, post-creation prompt 26594 tokens; process Query
  and all four R03 feature/affordance Query/preparation nodes completed.
- Seven distinct task-qualified combinations (30 successful variant attempts)
  are available and the Agent selected one with exactly seven qualified opaque
  recovery refs. No source poses, thresholds or robot margins were relaxed.
- Final state `awaiting_replan`, long-horizon result `blocked` at the first
  Action node with `node_selection_no_progress`; motion disabled, four Query
  records and zero Action records. Full acquire/pour/return routes and R04/rod
  qualification remain unvalidated; the complete workflow is not yet successful.
- Expanded tests: 773 passed / five unchanged planning-selection mock failures;
  loading original HEAD modules reproduces those same five failures.

## v16.6.3 local repair validated / 手掌与终态诊断修复已验证

- Diagnosis: `.task/labutopia-palm-collision-repair-20261102.md`.
- Actual cooked palm at five recorded failures is 0.57–1.34 mm below tabletop
  height. The old sphere rejection cannot simply be removed as a false positive.
- Adapter now checks exact final gripper geometry before pregrasp IK and keeps
  all downstream route checks. No candidate shift, sphere reduction or opening
  rule relaxation. Public failure summaries no longer expose USD paths.
- Native fresh-capture no-motion run:
  `out/lab-fullchain-truth-20261102-final-gripper-no-motion-r1/` completed.
- Task `task_4972b9d477f048d2` cancelled after R03 task-affordance unavailable:
  four aperture failures; six candidates × four final orientations reject on
  cooked-palm padded bounds/table. Reused across two backoffs: 48 attempts.
- 450 affected tests pass. Native motion remains disabled with no controller
  outcomes. Final-pose preflight fixes failure attribution/early rejection; it
  does not yet supply a usable grasp candidate or complete the two pours/stir.
- Empty-source replay filtering is fixed with four reproduced regression cases;
  historical replay remains diagnostic, not current preparation authority.

## v16.6.2 completed local repair / 当前局部修复结果

- Saved diagnosis: `.task/labutopia-finger-envelope-repair-20261102.md`.
- Owner: Isaac Adapter only; cooked convex component bounds replace whole
  finger bounds, retaining full prismatic sweep and 3 mm per-axis margin.
- Native replay `out/lab-cooked-finger-geometry-20261102-r1/geometry.json`:
  eight cooked convex components per finger, 53/56 slab boxes; all five
  formerly rejected intermediate samples clear. Joints/time unchanged.
- Fresh Agent no-motion qualification:
  `out/lab-fullchain-truth-20261102-cooked-finger-no-motion-r1/` completed;
  task `task_9c72fe6c84e94594` cancelled, no Action/controller. The same 48
  failures remain (workspace 20/environment 20/self 4/IK 4), but candidate 17
  now advances beyond the old finger box and fails later at hand-sphere/table.
- Validation: 434 affected tests pass. No AgentLoop/public contract changes.
- Intermediate clearance is not proof of final grasp or complete-route safety;
  no controller, pour or stir success is claimed.

- Task ID: `labutopia-r03-r04-grasp-coverage-20261101`
- Goal: run the user-requested simulator-truth AgentLoop workflow for R03 and R04 pours followed by GLASS_ROD stirring, with all atomic action parameters supplied by the semantic subtasks and no ReMake dependency.
- Tier: `C-Safety`
- Stage: `candidate generation -> no-motion preparation -> authorized simulation action`
- Owner layers:
  - AgentLoop/Coordinator own semantic task ordering, frozen operation parameters, opaque reference selection, lifecycle, settlement, and recovery.
  - Grasp Provider owns model-candidate sampling and bounded provider-neutral candidate coverage.
  - Isaac Adapter owns final-composed geometry, embodiment aperture, frame transforms, IK, collision, workspace validation, execution feedback, and stop behavior.
- Public contract impact: none. Existing `grasp.propose` candidates and `manipulation.prepare` evidence remain unchanged.
- Evidence lineage: same-capture simulator-truth observation and object point cloud -> GraspNet native proposals -> geometry-diverse bounded candidates -> task-affordance selection -> no-motion preparation -> Action feedback.
- Freshness boundary: observation, scene revision, frame, calibration, candidate set, process-feature set, and task-affordance selection must remain identical through preparation.
- Motion boundary: simulation execution remains disabled until a complete no-motion route passes every preparation gate; any unknown outcome or world change stops the workflow.
- User parameters:
  - R03 -> BEAKER: `tilt_rad=0.87`, `hold_s=0.60`
  - R04 -> BEAKER: `tilt_rad=0.87`, `hold_s=0.60`
  - GLASS_ROD stir: `radius_m=0.009`, `depth_m=0.04`, `turns=2.0`, `duration_s=4.0`, `direction=ccw`
- Forbidden shortcuts: hard-coded object coordinates, task-specific grasp poses, AgentLoop access to USD paths or gripper limits, bypassing preparation, automatic retry after uncertain motion, fabricated liquid-transfer claims.
- Resolved defect: task-affordance Preparation now returns a selected-first ordered `qualified_grasp_candidate_refs` list, and Action preparation resolves only those opaque references from the unchanged same-capture binding. Provider-rejected raw GraspNet candidates cannot re-enter embodiment preparation.
- Resolved defect: the prior `self_collision` and table `route_collision` labels were produced after a discontinuous Lula IK branch was incorrectly retained when nearby IK failed. Isaac preparation now rejects that branch as `ik_discontinuity` before collision sampling and records the actual checked joint sample/TCP for genuine collision failures.
- Resolved defect: acquire preparation now separates current-orientation raise, configured transport reorientation, raised lateral translation, staging reorientation, and final approach. It enumerates only geometry-supported bottle-axis equivalents and sends every route through the unchanged safety qualification.
- Resolved defect: acquire preparation now enumerates bounded Adapter-private approach distance, staging backoff, and signed tangential-offset corridors. Missing new configuration falls back to the legacy single corridor, and every alternative still enters the same complete safety qualification.
- Resolved defect: repeated route failures are summarized by code, phase, corridor, clearance, and transport orientation with bounded representative examples instead of injecting every full exception into AgentLoop context.
- Previous full-route blocker: R03 candidates `16`, `23`, and `15` each traversed 96 clearance x transport x corridor x axial-angle combinations, but no complete route passed. Across 288 routes the Adapter reported 140 IK discontinuities, 49 unavailable IK solutions, 21 self-collisions, and 78 environment collisions. Failures remain concentrated at `staging_reorient` (173) and `approach` (92); adding generic offsets alone is insufficient.
- Previous full-route attempt: workspace `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/`, task `task_b16f8e5cbeb84dda`, session `cli:lab-b11c91c66271`, action `invocation://manipulation-execute_subtask/3ebe297dca4e4fbf`, scene revision `labutopia-tabletop-rod-rack-v1:74e728eececc4cc590e7bd8dc431f73a:0`. `simulated_motion_enabled=false`, `outcome_known=true`, `world_change_started=false`, `possession_state=empty`, and `controller_outcomes=[]`; R04/GLASS_ROD did not start.
- Preserved preview: `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/artifacts/labutopia/no-motion-video/staging-corridor-observation.mp4` is a 5-second 1600x1200, 30 fps static observation labelled as controller-disabled. It is diagnostic observation evidence, not action evidence.
- Saved diagnosis: `.task/labutopia-r03-staging-corridor-diagnosis-20261101.md`.

## Failure-first behavior

- Missing or stale same-capture evidence: fail closed before preparation.
- `task_qualified` selected grasp absent from the current same-capture binding: fail closed before Adapter preparation; do not fall back to the raw candidate set.
- Candidate width above composed Franka aperture: reject candidate with `gripper_aperture_exceeded` and continue only within the same captured candidate set.
- IK, collision, self-collision, payload collision, or workspace failure: reject candidate without motion.
- Per-waypoint IK branch jump above the configured continuity threshold: attempt nearby IK from the previous accepted joint state; if it cannot satisfy the full pose tolerance within the threshold, reject as `ik_discontinuity` before collision sampling.
- No admissible candidate: known zero-motion failure with empty possession; refresh grasp candidates through Agent replan.
- Unknown execution outcome or any unconfirmed world change: stop; do not continue to R04 or stirring.

## v16.5.0 implementation scope (completed)

1. Keep the current corridor search, IK-continuity rejection, collision checks, and zero-motion evidence boundary unchanged.
2. Add task-conditioned final grasp-orientation/short-approach feasibility at the Provider/Adapter seam without exposing robot joints or USD paths to AgentLoop.
3. Rank or reject task-affordance grasp alternatives using measured table/neighbor clearance and embodiment reachability before the full corridor product.
4. Preserve same-capture provenance and test stale, ambiguous, all-unreachable, and replacement-provider paths.
5. Run a fresh no-motion AgentLoop workflow. Enable simulated execution only after one complete R03 route is qualified.

## v16.5.0 continuation (2026-11-02)

- Implemented Adapter-private `qualify_grasp_approach` through the existing
  worker/session and injected it into task-affordance qualification; no public
  contract or AgentLoop implementation changes.
- r3 isolates the final-approach obstruction: same-capture R03 grasps 15/16/23
  have z=0.750917 m and positive approach z=0.634282. The configured 0.12/0.18 m
  backoffs produce z=0.674803/0.636746 m, below workspace z_min=0.700 m.
  All eight variants per candidate reject before IK. This is not proof that
  every possible R03 grasp is impossible.
- Save diagnosis in `.task/labutopia-r03-approach-feasibility-diagnosis-20261102.md`.
- Complete capture/variant diagnostic receipts, preserve worker stale-revision
  causes, distinguish provider infrastructure failures, and exercise replacement
  callbacks, stale evidence, zero-motion and qualified-only recovery tests.
- Verify through the formal no-motion Agent entry point; do not start motion
  unless a complete route passes the existing preparation boundary.

## Latest result and next step

### v16.6.1 reset synchronization and collision diagnosis

- Save plan first in `changelog/2026-11.md`; use the recorded candidate 17/55
  failures to compare FK, composed USD geometry and queried collision envelopes.
- Owner: Isaac Adapter only (Tier C-Safety). The generic task/Tool interfaces,
  AgentLoop selection and Coordinator lifecycle/recovery remain unchanged.
- Historical joint replay is diagnostic, not same-capture preparation. It must
  issue no controller commands, preserve joints/physics time after initialization,
  and retain both historical capture identity and current scene revision.
- Smallest leak test: replace the geometry/IK mechanism without changing public
  candidate references; malformed geometry or unsafe candidates must still reject
  before motion. Do not create a second recovery path or weaken safety margins.
- Diagnose before choosing between geometry correction and bounded IK seeds;
  neither more sampling nor scene rearrangement is assumed to be the solution.
- Confirmed/fixed: resetting qpos after a dynamics step left hand USD transforms
  6.56 mm from measured-joint FK. Kinematic update plus explicit USD publication
  now yields 0.000197 mm hand error on the actual scene, without that extra step.
- Five historical finger/table rejections are conservative swept-box overlaps;
  the authored mesh remains about 16 mm above the table at the first rejected
  intermediate sample. This does not qualify the final grasp or justify reducing
  margins. Exact queried primitives/joints now persist in private receipts.
- Full affected regression: 421 passed. Native diagnostic r3 completes with
  unchanged joints/time; interrupted startup r2 has no successful result.
- Diagnosis: `.task/labutopia-collision-geometry-repair-20261102.md`;
  review: `docs/forge/IMPLEMENTATION_REVIEW_V16_6_1.md`.
- Fresh formal no-motion follow-up:
  `out/lab-fullchain-truth-20261102-reset-sync-no-motion-r1/`.
- Formal task `task_ebea061a2ed841e3` ends cancelled at R03 task-affordance:
  aperture=4; approach failures workspace=20, environment=20, self=4, IK=4.
  All 24 collision failures now retain structured geometry. No Action or
  controller starts. The synchronized initial state is repaired; the unchanged
  approach counts prove that collision/IK infeasibility remains a separate issue.

### v16.6.0 completed coverage repair (2026-11-02)

- Save the selection/refactor decision in `.task/labutopia-r03-native-coverage-repair-20261102.md`.
- Recorded r2 has 44 decoded proposals and 24 post-NMS candidates, not a saturated
  64-candidate budget. All 24 world approach Z components are positive; current
  qualified refs share one upward family. Do not change top-K without evidence.
- Add configurable bounded same-cloud coordinate-frame inference inside the
  GraspNet Worker, inverse-map native predictions, then use existing sampling,
  same-capture task-affordance and complete route preparation. No public contract
  or AgentLoop changes; do not rotate an already predicted grasp into a new one.
- Validate round-trip frames, one-pass compatibility, aggregate budgets and
  inference failures; pair real model runs using one captured cloud and fixed
  seed. Enable configuration only after evidence shows useful coverage.
- All-unavailable returns to existing Agent recovery. No new scheduler, hashes,
  release gates, workspace changes or automatic world-changing retries.

- Implementation commit `33d3bfb2`; full affected regression 410 passed.
- Paired native replay shows geometry-qualified candidates 3 -> 10. Formal r2
  reproduces 1058 decoded / 64 returned R03 candidates; four of ten geometrically
  qualified candidates exceed aperture, and six yield 48 rejected approaches:
  workspace=20, environment collision=20, self-collision=4, IK unavailable=4.
- Formal r2 task `task_053053cf3a0b4804` (session `cli:lab-2063ffedd5eb`) is
  cancelled at task-affordance; no downstream acquisition/pour/stir is qualified.
- Next: no-motion overlay of checked gripper/link geometry against the specific
  table/R01/R02/BEAKER collision pairs; then assess actual gripping-region/solid
  clearance and bounded IK seed alternatives. Preserve same-capture references
  and full-route qualification; do not change AgentLoop or bypass collision.

### Previous v16.5.0 runtime

- Fresh run `out/lab-fullchain-truth-20261102-approach-feasibility-no-motion-r2/`,
  session `cli:lab-5fe426934fb3`, task `task_51ae038c97d246fd`: process-feature
  Query/preparation available, task-affordance unavailable, task cancelled.
- Three R03 grasps x eight approaches = 24 workspace rejections before IK.
  Full capture/variant artifacts persisted; no Action or controller start,
  `simulated_motion_enabled=false`, `controller_outcomes=[]`.
- This earlier direction-coverage blocker is addressed by v16.6.0 above.
  Approach distances and safety limits remain unchanged; full-route qualification
  remains mandatory and is not established by the coverage repair.

## Architecture review

- Generic domain behavior: task semantics, opaque selections, evidence lineage, lifecycle, and settlement.
- Provider behavior: model-native candidate coverage and deterministic bounded selection.
- Adapter behavior: simulator/robot mechanism, final-world transforms, aperture, IK, collision, and execution.
- Replaceability: another Grasp Provider may produce the same public candidates without changing AgentLoop, ToolSpec, or Isaac preparation.
- Smallest abstraction-leak test: geometry-diverse selection changes only which validated native candidates survive the provider budget; no USD path, robot joint limit, R03/R04 label, or task operation enters the shared candidate contract.
- Smallest selection-leak test: a `task_qualified` subtask whose binding contains one qualified and one rejected raw grasp must pass exactly the qualified reference to `manipulation.prepare`; deleting that selected reference must fail before the provider is called.

## Validation commands

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src \
  ./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py \
  examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py

PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  ./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py
```
