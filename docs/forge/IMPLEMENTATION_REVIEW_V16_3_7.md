# Implementation Review v16.3.7

## Findings

### Major - fixed: Skill collapsed distinct Adapter recovery recommendations

- Location: `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py`
- Before the review fix, the Skill correctly stopped parsing `route_collision` from error text, but every admitted zero-motion preparation failure was still rewritten to `agent_replan_select_alternative_candidate`.
- This lost the Adapter's distinction between `select_alternative_candidate` and `refresh_grasp_candidates`, so AgentLoop could receive the wrong recovery objective even though the Provider had already supplied a typed recommendation.
- Fixed by projecting only supported explicit Adapter recommendations into corresponding Agent-level actions. Unsupported recommendations, unknown outcomes, world changes, non-empty possession, completed actions, and non-Adapter failures remain non-replannable through this path.
- Regression coverage proves that arbitrary error-message text cannot change the decision and that both supported recommendations remain distinct in the subtask result and settlement.

### Blocker - none remaining in the implementation

No implementation Blocker remains. The runtime task is still blocked before motion because the current `transit_cross` Cartesian route has no continuous full-pose IK solution for the three task-qualified R03 candidates. That is an unresolved capability limitation, not an accepted execution success.

### Major - none remaining after fixes

The review found no remaining Major architecture, safety, validation, or maintainability issue in the scoped change.

## Architecture acceptance

- Generic domain and AgentLoop: own task semantics, opaque references, lifecycle, settlement, stopping, and typed recovery intent only.
- Task-Affordance Provider: owns process-compatible candidate qualification.
- Isaac Adapter: owns the motion-profile continuity limit, robot state, frame transforms, IK mechanisms, route construction, collision checks, and preparation evidence.
- Replacement test: another Adapter may produce the same provider-neutral failure fields without exposing joint arrays, USD paths, or simulator objects to AgentLoop.
- Smallest abstraction-leak test: changing the diagnostic message while preserving `requires_replan` and `recommended_action` must not change Skill recovery behavior.

## Safety acceptance

- Validation is no-motion only; no controller or simulator action was started by the implementation checks.
- Workspace, joint limits, IK pose tolerance, self/environment collision, payload collision, frame, and Action authorization gates remain enabled.
- A discontinuous primary IK solution is rejected before collision sampling unless nearby IK returns a successful solution within the configured joint-delta limit.
- Unknown execution outcome or any world change remains outside this zero-motion recovery path.

## Evidence

- Contract evidence: focused Adapter and Skill tests cover discontinuous primary IK, continuous nearby recovery, checked collision samples, mixed route failures, explicit recovery mapping, and negative zero-motion conditions.
- Provider evidence: the no-motion Agent run records `ik_discontinuity` for clearances `0.04/0.08 m` and `inverse_kinematics_failed` at `0.12 m` for candidates `16`, `15`, and `23`.
- Live execution evidence: none. `simulated_motion_enabled=false`, `controller_outcomes=[]`, and `world_change_started=false` in `out/lab-fullchain-truth-20261101-ik-continuity-no-motion-r1/`.

## Remaining risk and next step

The current route uses the grasp orientation during the lateral `transit_cross` segment. The next Adapter-private iteration should separate raise, safe-orientation translation, staging reorientation, and approach, then rank bottle-axis-equivalent orientations with continuous IK and the unchanged collision/workspace gates. It must first pass no-motion preparation before any simulated execution is authorized.
