# Current Task: LabUtopia R03/R04 full-chain grasp coverage

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
- Current blocker: R03 candidates `16`, `23`, and `15` each traversed 96 clearance x transport x corridor x axial-angle combinations, but no complete route passed. Across 288 routes the Adapter reported 140 IK discontinuities, 49 unavailable IK solutions, 21 self-collisions, and 78 environment collisions. Failures remain concentrated at `staging_reorient` (173) and `approach` (92); adding generic offsets alone is insufficient.
- Latest no-motion attempt: workspace `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/`, task `task_b16f8e5cbeb84dda`, session `cli:lab-b11c91c66271`, action `invocation://manipulation-execute_subtask/3ebe297dca4e4fbf`, scene revision `labutopia-tabletop-rod-rack-v1:74e728eececc4cc590e7bd8dc431f73a:0`. `simulated_motion_enabled=false`, `outcome_known=true`, `world_change_started=false`, `possession_state=empty`, and `controller_outcomes=[]`; R04/GLASS_ROD did not start.
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

## Next implementation

1. Keep the current corridor search, IK-continuity rejection, collision checks, and zero-motion evidence boundary unchanged.
2. Add task-conditioned final grasp-orientation/short-approach feasibility at the Provider/Adapter seam without exposing robot joints or USD paths to AgentLoop.
3. Rank or reject task-affordance grasp alternatives using measured table/neighbor clearance and embodiment reachability before the full corridor product.
4. Preserve same-capture provenance and test stale, ambiguous, all-unreachable, and replacement-provider paths.
5. Run a fresh no-motion AgentLoop workflow. Enable simulated execution only after one complete R03 route is qualified.

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
