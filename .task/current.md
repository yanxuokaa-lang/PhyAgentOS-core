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
- Motion boundary: no live action until a fresh no-motion run produces an admissible R03 route; any unknown outcome or world change stops the workflow.
- User parameters:
  - R03 -> BEAKER: `tilt_rad=0.87`, `hold_s=0.60`
  - R04 -> BEAKER: `tilt_rad=0.87`, `hold_s=0.60`
  - GLASS_ROD stir: `radius_m=0.009`, `depth_m=0.04`, `turns=2.0`, `duration_s=4.0`, `direction=ccw`
- Forbidden shortcuts: hard-coded object coordinates, task-specific grasp poses, AgentLoop access to USD paths or gripper limits, bypassing preparation, automatic retry after uncertain motion, fabricated liquid-transfer claims.
- Resolved defect: task-affordance Preparation now returns a selected-first ordered `qualified_grasp_candidate_refs` list, and Action preparation resolves only those opaque references from the unchanged same-capture binding. Provider-rejected raw GraspNet candidates cannot re-enter embodiment preparation.
- Current blocker: the eight R03 task-qualified candidates in no-motion run `r9` all fail Adapter-owned aperture, IK, collision, self-collision, or payload checks. Motion remains unauthorized; R04 and GLASS_ROD are not started.

## Failure-first behavior

- Missing or stale same-capture evidence: fail closed before preparation.
- `task_qualified` selected grasp absent from the current same-capture binding: fail closed before Adapter preparation; do not fall back to the raw candidate set.
- Candidate width above composed Franka aperture: reject candidate with `gripper_aperture_exceeded` and continue only within the same captured candidate set.
- IK, collision, self-collision, payload collision, or workspace failure: reject candidate without motion.
- No admissible candidate: known zero-motion failure with empty possession; refresh grasp candidates through Agent replan.
- Unknown execution outcome or any unconfirmed world change: stop; do not continue to R04 or stirring.

## Planned implementation

1. Save the R03 32-candidate exhaustion and 512-candidate no-motion diagnostic.
2. Add deterministic geometry-diverse bounded selection in the replaceable Grasp Provider, after validation/NMS and before public candidate projection.
3. Configure LabUtopia to request a 512-candidate native pool and retain a bounded 64-candidate geometry-diverse subset.
4. Add provider and profile regressions proving narrow/spatially distinct candidates survive without changing scores, geometry, opaque refs, or motion authority.
5. Run focused Provider/Isaac/planning/Skill tests, Ruff, compileall, and diff checks.
6. Run a passive scene-state probe and a fresh no-motion AgentLoop workflow. Record measured arm/gripper joints, TCP and wrist-camera world poses, then start live simulated motion only if R03 preparation passes all aperture, frame, IK, collision, and workspace checks.
7. Perform implementation review and fix every Blocker/Major before acceptance.
8. Complete bilingual changelog, update recent-five index, commit scoped files, and attempt push on the current branch.
9. Preserve the task-affordance selection through `execute_subtask`: the Adapter preparation request must contain only the selected qualified grasp, while non-task-affordance operations retain their existing bounded alternative-candidate recovery.
10. Extend the existing task-affordance preparation receipt with an ordered opaque qualified-grasp reference list, selected first. Resolve those refs against the unchanged same-capture binding before Adapter preparation so recovery stays inside the qualified set.

## Architecture review

- Generic domain behavior: task semantics, opaque selections, evidence lineage, lifecycle, and settlement.
- Provider behavior: model-native candidate coverage and deterministic bounded selection.
- Adapter behavior: simulator/robot mechanism, final-world transforms, aperture, IK, collision, and execution.
- Replaceability: another Grasp Provider may produce the same public candidates without changing AgentLoop, ToolSpec, or Isaac preparation.
- Smallest abstraction-leak test: geometry-diverse selection changes only which validated native candidates survive the provider budget; no USD path, robot joint limit, R03/R04 label, or task operation enters the shared candidate contract.
- Smallest selection-leak test: a `task_qualified` subtask whose binding contains one qualified and one rejected raw grasp must pass exactly the qualified reference to `manipulation.prepare`; deleting that selected reference must fail before the provider is called.

## Validation commands

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src \
  ./.venv/bin/python -m pytest -q \
  examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_profile.py

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  ./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py \
  examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py
```
