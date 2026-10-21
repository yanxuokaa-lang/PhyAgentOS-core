# Implementation Review v15.4.0: Persistent Host Coordinator Composition

Date: 2026-10-21 (Asia/Shanghai)

## Findings and disposition

The persistent host can now construct the existing provider-neutral
`PerceptionBindingAdapter` and a read-only `AgentTaskCoordinator` resolver from
an explicitly shared PAOS workspace. The binding request accepts sensor refs,
semantic source/destination categories, freshness, and an optional process
frame; fixed Prim/path fields are rejected. Existing explicit port injection
remains supported, and partial or mixed configuration fails closed.

This closes the missing production-host composition seam for a configured
semantic selector. It does not mean the Agent dynamically supplied that
selector for a particular task: the current persistent-host profile is static
configuration. Initial binding remains task-plan input, while the adapter
re-runs measured observation/understanding/grasp/capability Queries when the
subtask needs a scene refresh. A future Core integration must connect the
selected PlanNode's Coordinator-owned semantic request to this adapter without
adding environment-specific perception classes.

## PAOS architecture / extension / Developer Guide / AgentLoop review

- PAOS `AgentTaskCoordinator` remains the authority for task identity, active
  revision, selected execution record, PlanNode, and trusted intent. The host
  resolver uses the same workspace store and does not create tasks or plans.
- `PerceptionBindingAdapter` remains in the generic Skill package. The host
  supplies semantic configuration and the Runtime Query transport; it does
  not implement perception choreography or derive targets from Prim paths.
- Runtime still exposes one `manipulation.execute_subtask` Action. Internal
  prepare/acquire/process/place calls and receipts remain below the outer
  Agent settlement boundary.
- The Coordinator workspace is a local shared-store transport, not an HTTP
  service. Deployment must ensure both processes use the same PAOS workspace.
- This stage adds no hashes, new motion gate, simulator-specific perception
  class, or automatic motion authorization.

## Seven-dimension acceptance

1. Perception correctness: **partial**. Query-provider composition is wired;
   no live camera observation or Agent-selected semantic binding was run.
2. Binding and freshness: **partial**. The generic adapter retains its lineage
   checks; this stage validates configuration and port composition only.
3. Subtask-level AgentLoop boundary: **pass for composition**. One outer
   subtask Action still contains the internal sequence; no per-Tool Agent turn
   was introduced.
4. IK, workspace, and collision: **not validated**. No planner or controller
   execution ran.
5. Execution state: **not validated**. No Gateway Action or simulator step ran.
6. Process feedback: **not validated**. No pour or stir process ran.
7. Settlement and recovery: **partial**. The host now reads Coordinator-owned
   caller context from the shared store, but this stage did not execute a full
   task through one terminal NodeSettlement or process restart recovery.

Overall plan acceptance: **incomplete**. This stage completes only the
production-host composition seam. Dynamic Agent semantic request propagation,
live perception, motion qualification, process feedback, and end-to-end
subtask settlement remain open.

## Validation

- Persistent host, deployment, and subtask tests: **48 passed**.
- Ruff, compileall, and `git diff --check`: passed.
- No Isaac Sim, Gateway Action, simulator step, or robot motion was run.
- The initial test collection lacked the optional RoboTwin runtime path; adding
  `examples/forge-adapters/robotwin20/runtime` to `PYTHONPATH` resolved the
  collection issue. The suite then passed.

## Remaining blocker

The Agent/Coordinator planning path still needs to supply the selected
PlanNode's semantic binding request to the persistent host through an explicit
generic Core port. Do not replace this with environment profile paths, object
names, or host-created task identity.
