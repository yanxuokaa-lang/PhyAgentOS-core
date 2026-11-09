# GraspNet Task-Affordance Selection

- Date: 2026-10-30 Asia/Shanghai
- Stage: Tier C-Safety, design/implementation
- Goal: turn current-observation GraspNet proposals into task-qualified grasp choices for reagent-bottle pouring and stir-rod use, without assigning task policy to GraspNet or the Isaac Adapter.
- Authority: repository `AGENTS.md`; `docs/forge/PLANNING_MODULE_DESIGN.md`; `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`; `docs/forge/AGENT_TOOL_INPUT_SELECTION_DESIGN.md`; `docs/forge/VISUAL_GEOMETRY_EVIDENCE_ARCHITECTURE.md`.
- Existing-worktree note: implementation files already contain unrelated/uncommitted user changes. Preserve them and inspect overlapping hunks before editing. Never use broad `git add .`.

## Diagnosis

GraspNet proposes generic 6-DoF gripper poses from the current object point cloud. Each candidate has an opaque `candidate_ref`, entity binding, grasp frame, approach direction, score, optional gripper geometry, and evidence provenance. Its score does not mean "good for pouring" or "preserves the stir working end".

The process-feature path separately returns opaque feature references for rims/rod endpoints. Existing AgentLoop planning already has a Query -> direct-predecessor selection -> no-motion Preparation pattern for process features. However, the composite grasp binding currently carries a preferred candidate and candidate collection into `manipulation.prepare`; there is no explicit task-affordance qualification that relates a grasp proposal to process-feature evidence, and the task-level workflow does not record a grasp/process combination selection.

The correct unit of qualification is a relation between (a) one grasp candidate, (b) the relevant task feature/role, and (c) current observation identity. It is not a fabricated XYZ rule or a score-only rank. The Agent chooses among provider-qualified opaque combination refs; the Adapter resolves them privately against same-capture model output and geometry.

## Ownership

- Generic domain/ToolSpec: task operation and semantic requirement, such as pouring with a bottle-body grasp or stirring while preserving a selected working-end role; observation/scene/frame/calibration lineage; opaque candidate-set and combination refs; failure status.
- Grasp Provider: proposes grasp poses from point clouds and records model evidence. It does not identify bottle lips, decide rod end roles, or authorize motion.
- Process-feature Provider: proposes geometric feature candidates from current point cloud/final geometry; it does not select a grasp.
- Task-affordance qualification Provider: evaluates grasp/feature combinations using provider-private geometry and embodiment/gripper constraints, returning a queryable set of eligible opaque refs. No USD path, object coordinates, SDK handle, or hard-coded scene coordinate crosses into AgentLoop.
- AgentLoop/Coordinator: selects refs only from a successful direct predecessor, records existing execution/decision receipts, owns lifecycle and cancellation.
- Preparation: re-resolves and revalidates exact candidate refs, same observation/scene/frame/calibration, geometry qualification, gripper fit, workspace/reachability/collision and task-feature relationship without motion.
- Action: may consume only successful Preparation output. Missing, ambiguous, stale, mismatched, unsupported, failed, or unknown results must stop before Action.

## Candidate relationships

- Reagent bottle pour: choose one candidate whose contact geometry is on a supported bottle-body region and whose attached-object pose preserves access to the pour opening and can reach the destination process pose. Rim/lip evidence is related to the grasp through the same entity and capture; a rim alone does not prove a pour lip or liquid direction.
- Stir tool: choose a grasp on the rod shaft, not at either end, and preserve clearance/length for the task-selected working-end candidate. If endpoint roles are symmetric and no task/geometry evidence disambiguates them, return ambiguous. Do not convert a rod endpoint into a grasp target.
- Selection operates over qualified `(grasp_ref, feature_ref...)` combinations rather than maximizing raw score. Score may order otherwise eligible alternatives but cannot make an ineligible grasp valid.

## Evidence and stop conditions

Identity tuple: `candidate_set_ref`, `candidate_ref`, process-feature set/ref(s), `entity_ref`, `observation_ref`, `scene_revision`, `frame_id`, `calibration_ref`. Query and Preparation must agree exactly. Freshness is checked at each call. Provider geometry evidence stays private; public response contains only statuses, opaque refs, role semantics, and evidence refs.

Return explicit unavailable/ambiguous/stale/invalid outcomes for insufficient visible geometry, occlusion, uncertain feature roles, wrong entity, unsupported geometry, stale capture, or provider error. An unsuccessful qualification must fail the PlanNode settlement, keep dependent Action not-ready, and yield zero Action calls.

## Planned implementation and tests

1. Add a provider-neutral qualification Query/Preparation contract only if it composes existing ToolSpec and lifecycle seams; keep provider fields private.
2. Add the qualification Query and explicit direct-predecessor reference selection to the Agent-composed plan; preserve current user-supplied process parameters and avoid AgentLoop access to simulator details.
3. Implement replaceable provider behavior; Isaac-specific geometric evidence lookup stays in Isaac Adapter. If current geometry cannot justify bottle-body contact or rod role, return unavailable/ambiguous.
4. Preparation revalidates candidate/evidence identity and reports no motion authorization. Action arguments are projected only from successful Preparation.
5. Test replacement Provider, explicit source lineage, same-entity/same-capture joins, candidate score not overriding qualification, stale evidence, ambiguous rod ends, missing geometry, provider failure, preparation failure, and zero Action invocation.
6. Run focused tests, full Skill + Isaac Adapter tests, lint/compile/diff checks. Do not launch Isaac motion. Report contract tests separately from actual scene qualification.

## Implementation status (2026-10-30)

Partial groundwork was added: the Skill has a provider-neutral combination Query/Preparation contract, optional persistent/Fake Gateway registration, and contract tests. This does not yet satisfy the requested end-to-end implementation. The Agent-composed PlanGraph has not been extended with qualification and selection nodes, the selected combination is not projected into Subtask Action from Preparation, and LabUtopia has no geometry qualification Provider. Those are explicit remaining blockers; no candidate is treated as task-qualified by the current code.

## Acceptance limits

Passing unit/contract tests proves PAOS dataflow and stop behavior, not the real LabUtopia glass geometry. Before any execution authorization, obtain fresh no-motion scene evidence proving candidate geometry, gripper fit, frame transforms, approach/reachability, collisions, and task-feature usability. No pouring/stirring or robot motion is authorized by this task.

