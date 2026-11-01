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
- Motion boundary: simulation execution is authorized only after preparation; any unknown outcome or world change stops the workflow. The latest authorized run stopped before the first controller command.
- User parameters:
  - R03 -> BEAKER: `tilt_rad=0.87`, `hold_s=0.60`
  - R04 -> BEAKER: `tilt_rad=0.87`, `hold_s=0.60`
  - GLASS_ROD stir: `radius_m=0.009`, `depth_m=0.04`, `turns=2.0`, `duration_s=4.0`, `direction=ccw`
- Forbidden shortcuts: hard-coded object coordinates, task-specific grasp poses, AgentLoop access to USD paths or gripper limits, bypassing preparation, automatic retry after uncertain motion, fabricated liquid-transfer claims.
- Resolved defect: task-affordance Preparation now returns a selected-first ordered `qualified_grasp_candidate_refs` list, and Action preparation resolves only those opaque references from the unchanged same-capture binding. Provider-rejected raw GraspNet candidates cannot re-enter embodiment preparation.
- Resolved defect: the prior `self_collision` and table `route_collision` labels were produced after a discontinuous Lula IK branch was incorrectly retained when nearby IK failed. Isaac preparation now rejects that branch as `ik_discontinuity` before collision sampling and records the actual checked joint sample/TCP for genuine collision failures.
- Current blocker: all three task-qualified R03 candidates `16`, `15`, and `23` now fail the Adapter-owned `transit_cross` route. Clearances `0.04/0.08 m` require discontinuous primary IK branches (`3.575-4.431 rad`) and nearby IK does not satisfy the full pose tolerance; clearance `0.12 m` has no IK solution. The remaining work is route/orientation construction and equivalent bottle-axis grasp orientation search inside Isaac preparation, not collision-threshold tuning, vessel size, AgentLoop, prompt parameters, or candidate-set recovery.
- Latest no-motion verification: workspace `out/lab-fullchain-truth-20261101-ik-continuity-no-motion-r1/`, task `task_a5127feeb8c8476a`, session `cli:lab-2a6cdb5274e6`, scene revision `labutopia-tabletop-rod-rack-v1:4f9352af31ed4977bb74a26481bfdf37:0`. `simulated_motion_enabled=false`, `controller_outcomes=[]`, `world_change_started=false`, `outcome_known=true`, and `possession_state=empty`; R04 and GLASS_ROD did not start.

## Failure-first behavior

- Missing or stale same-capture evidence: fail closed before preparation.
- `task_qualified` selected grasp absent from the current same-capture binding: fail closed before Adapter preparation; do not fall back to the raw candidate set.
- Candidate width above composed Franka aperture: reject candidate with `gripper_aperture_exceeded` and continue only within the same captured candidate set.
- IK, collision, self-collision, payload collision, or workspace failure: reject candidate without motion.
- Per-waypoint IK branch jump above the configured continuity threshold: attempt nearby IK from the previous accepted joint state; if it cannot satisfy the full pose tolerance within the threshold, reject as `ik_discontinuity` before collision sampling.
- No admissible candidate: known zero-motion failure with empty possession; refresh grasp candidates through Agent replan.
- Unknown execution outcome or any unconfirmed world change: stop; do not continue to R04 or stirring.

## Next implementation

1. Keep the current IK-continuity rejection and zero-motion evidence boundary unchanged.
2. In Isaac Adapter preparation, split `transit_cross` into raise with current orientation, translate with a safe transport orientation, reorient at staging, then approach the grasp.
3. Enumerate bottle-axis-equivalent grasp orientations from the same opaque grasp candidate and rank only routes that pass continuous IK, limits, workspace, self/environment collision, and payload checks.
4. Add no-motion tests for every new route segment, equivalent-orientation ordering, stale evidence, and all-routes-unavailable behavior.
5. Run a fresh no-motion AgentLoop workflow. Enable simulated execution only after one complete R03 route is qualified; any unknown outcome or world change still stops R04 and stirring.

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
