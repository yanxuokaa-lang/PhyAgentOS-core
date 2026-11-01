# v16.3.3 Implementation Review

## Findings

### Major — resolved: stirring alternatives could change the working endpoint

- Location: `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py`.
- Risk: a task-affordance candidate set may contain GLASS_ROD combinations that use different process endpoints. Returning every qualified grasp as an Action alternative could preserve grasp qualification while silently changing the Agent-selected working end.
- Resolution: Preparation revalidates the complete same-capture candidate set and projects only grasp references whose `process_feature_refs` exactly match the selected combination. The selected grasp is first and duplicates are removed.
- Evidence: `test_visual_perception.py` covers endpoint-compatible alternatives; the expanded regression set passes.

### Blocker/Major — none remaining

- The raw 64-candidate GraspNet binding is retained as perception evidence, but `manipulation.prepare.candidates` is built only from the ordered task-qualified opaque references.
- Missing, duplicate, unbound, stale, or selected-not-first references fail before Adapter preparation and before motion.
- Non-task-affordance relocate/grasp routes retain their existing bounded raw-candidate recovery behavior.
- Adapter-owned aperture, frame, IK, self-collision, environment collision, payload, workspace, and route checks are unchanged and remain authoritative.

## Architecture Review

- Tier: `C-Safety` because the change affects the preparation path immediately before simulated manipulator motion.
- Generic domain owner: PlanGraph/Coordinator and AgentLoop own frozen task semantics, direct-predecessor receipt projection, opaque selection, lifecycle, cancellation, settlement, and recovery boundaries.
- Provider owner: Task-Affordance Provider owns task-conditioned grasp/process qualification and the selected-first ordered qualified grasp set.
- Adapter owner: Isaac Adapter owns final USD geometry, transforms, embodiment limits, IK, collision, route search, execution feedback, and stop behavior.
- Public surface: `manipulation.prepare_grasp_task_affordance` adds `qualified_grasp_candidate_refs`, a provider-neutral list of opaque candidate identities. No provider geometry, score, USD path, robot limit, or SDK object crosses the boundary.
- Substitutability: another task-affordance Provider can return the same opaque ordered semantics without changing AgentLoop or Isaac implementation details.
- Evidence lineage: observation and calibration -> grasp/process candidate sets -> task-affordance combinations -> selected-first qualified refs -> same-capture binding resolution -> no-motion Adapter preparation.
- Freshness boundary: observation, scene revision, frame, calibration, grasp candidate set, process-feature set, and selected combination remain identical through preparation.

## Safety Review

- Dry-run status: final validation uses `simulated_motion_enabled=false`; no controller outcomes or world changes occurred.
- Motion gate: Action preparation cannot authorize motion when any candidate fails aperture, IK, collision, payload, workspace, or frame validation.
- Stop behavior: the known R03 preparation failure settles with empty possession and stops R04 and stirring.
- Frame assumptions: task-affordance evidence is tied to one observation/frame/calibration; final execution targets and routes are resolved inside the Isaac Adapter in world/control frames.
- Live execution: not accepted. R03 has no admissible route in the current scene, so `--execute` must remain disabled.

## Runtime Evidence

- Run: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r9/`.
- Task: `task_114477e266344f0b`.
- Qualified/rejected order: `-45, -5, -32, -25, -31, -59, -38, -36` in both the preparation receipt and Adapter rejection list.
- Failure classes: payload collision, aperture exceeded, inverse kinematics failure, route collision, and self-collision.
- Outcome: `world_change_started=false`, `outcome_known=true`, `possession_state=empty`, `controller_outcomes=[]`.

## Validation

- Current focused regression suite: `244 passed, 1 warning` with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.
- Earlier staged focused/expanded suites: `123 + 351 = 474 passed`.
- Ruff: passed.
- `compileall`: passed.
- `git diff --check`: passed after the diagnostic and review update.
- A non-acceptance sweep across the entire planning/pick-place directories produced `914 passed, 233 failed`. The first failures are stale test doubles whose `_Dispatch.graph` is a `SimpleNamespace` without `nodes`; package-level suites also assume plugins/environment not present under the mandated autoload-disabled command. These failures are recorded, not presented as acceptance evidence for the changed route.

## Remaining Risks

- The current R03/scene arrangement still has no admissible route. The next work belongs to Adapter/scene no-motion investigation, not AgentLoop candidate selection.
- No successful pour, stir, liquid-transfer, or chemistry outcome is claimed.
- Repository-specific Hephaestus safety documents named by the generic runtime-safety skill are absent; this review used the project `AGENTS.md`, current task plan, PAOS architecture principles, existing Tool contracts, tests, and runtime receipts.
