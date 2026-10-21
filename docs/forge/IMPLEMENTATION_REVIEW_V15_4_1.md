# Implementation Review v15.4.1: Semantic Binding into Subtask Plans

Date: 2026-10-21 (Asia/Shanghai)

## Findings and disposition

Added `bind_subtask_from_semantics`, a provider-neutral planning composition
entry. It accepts the existing measured-binding port, asks it for a current
binding, and constructs the existing `SubtaskSpec`. The returned object can be
compiled by `compose_subtask_plan` into one Agent-facing
`manipulation.execute_subtask` node. This helper does not create or persist a
task, invoke an Action, or settle a node.

The port is structural (`ready` plus `bind`) rather than tied to one concrete
adapter class. The production `PerceptionBindingAdapter` can be supplied, as
can another implementation that honors the same measured-binding contract.
Two independent providers are covered by tests through the same composition
entry.

## PAOS architecture / extension / Developer Guide / AgentLoop review

- Stable planning semantics remain in the pick-place Skill. Sensor/query
  mechanisms remain behind `SemanticBindingPort` and the existing Query
  contracts.
- The helper only composes read-only perception evidence into a semantic
  subtask; task/revision/node identity and trusted intent remain Coordinator
  owned, and execution remains Runtime owned.
- No Agent turn or settlement is introduced between internal Tool calls. The
  helper does not alter the one-subtask PlanNode contract.
- No Prim, USD, simulator, or RoboTwin dependency is added to the generic
  planning module.
- No new hash, gate, fallback-to-success, or motion authorization mechanism
  was introduced.

## Seven-dimension acceptance

1. Perception correctness: **partial**. The helper consumes a provider binding;
   tests prove provider substitution, not camera truth or correct real-world
   recognition.
2. Binding and freshness: **partial**. The existing `PerceptionBinding`
   validators and adapter Query lineage checks remain in force; the new helper
   does not create fresh evidence by itself.
3. Subtask-level AgentLoop boundary: **pass for planning composition**. The
   returned `SubtaskSpec` compiles through the existing one-node composition;
   no per-Tool replanning was added.
4. IK, workspace, and collision: **not validated**. This planning-only helper
   does not invoke route preparation or a controller.
5. Execution state: **not validated**. No Gateway Action or simulator step ran.
6. Process feedback: **not validated**. No pour/stir process ran.
7. Settlement and recovery: **partial**. The output preserves the existing
   subtask contract, but this stage did not execute or recover a persisted task.

Overall plan acceptance: **incomplete**. The helper is not yet called by the
production Agent task-creation path; task-specific semantic request propagation
and live seven-dimension execution remain open.

## Validation

- Agent planning and perception binding tests: **19 passed**.
- Ruff and `git diff --check`: passed.
- No Gateway Action, simulator step, or motion was run.
