# Replan Projection and AgentLoop Convergence Diagnosis / Replan Projection 与 AgentLoop 收敛诊断

## Scope / 范围

This diagnosis covers generic PlanGraph and AgentLoop behavior. RGB ordering is
only the recorded reproducer; no proposed rule depends on colors, benchmark task
names, robot profiles, concrete Tools, or camera IDs.

本诊断覆盖通用 PlanGraph 与 AgentLoop 行为。RGB 排列仅是已记录复现，不作为规则输入；
任何修复不得依赖颜色、benchmark 任务名、机器人 profile、具体 Tool 或相机 ID。

## Persisted event chain / 持久化事件链

1. The original plan had `red_grasp -> red_prepare`; both selections were persisted
   and consumed. `red_grasp` completed and `red_prepare` settled failed.
2. Recovery began revision `revision_1cd8a03165ec4db8` with
   `preserved_node_ids=["red_grasp"]` but the replacement graph contained only
   `red_prepare_observed_collision_recovery` and its settlement list was empty.
3. The recovery node had no dependency. It cited the old grasp record as evidence,
   while the frozen `manipulation.prepare` ToolSpec requires its candidate slot from
   `source_scope: predecessor`.
4. Readiness exposed the node to the Agent because DAG dependencies and node bindings
   were satisfied. The required projection source was nevertheless unreachable.
5. No selection, selection rejection, or Tool execution was persisted in that
   revision. Repeated model turns ended with the generic
   `Agent produced no planning-bound Tool execution` message.

## Architectural causes / 架构原因

### Projection admission

DAG readiness answers whether dependencies/evidence/conditions are settled. ToolSpec
projection readiness answers whether every declared source slot can consume a record
of the required scope and Tool identity. These are distinct checks. Plan materialize
and replan admission must reject a node whose frozen Tool candidates all have
unsatisfiable source slots, before a model execution turn starts.

### Preserve semantics

A preserved node is not metadata alone. Its unchanged PlanNode and completed
settlement must both be present in the replacement revision if downstream nodes use
it as a predecessor. A preserve ID absent from the replacement graph must be rejected;
silently retaining only the ID produces a graph that cannot reconstruct predecessor
context.

### Failure ownership

A Runtime/Adapter implementation failure is not Agent-correctable simply because a
Query returned `unavailable`. Query diagnostics must state owner, whether retry is
valid in the same revision, whether replanning can change the outcome, and the
recommended control action. Fresh evidence requirements are separate from software
faults. The Agent chooses among the exposed control outcomes; the host does not infer
recovery from diagnostic prose.

### Planning convergence

Planning progress is a change in Coordinator facts: active revision, persisted
selection, persisted selection rejection, or task-bound execution record/status.
Repeated context/readiness reads are not progress. One corrective model turn is
allowed; a second unchanged fingerprint returns `node_selection_no_progress` and
hands control to existing recovery without auto-selecting or auto-executing a Tool.

### Revision replay

Historical replay must reduce each graph with that revision's effective settlements.
Using active-revision settlements for every historical graph violates append-only
replay and produces incorrect ready nodes.

## PAOS design boundary / PAOS 设计边界

- Agent: selects semantic next steps and recovery outcomes.
- ToolSpec: declares candidate implementations and projection-source requirements.
- Coordinator: validates revisions, persists selections/rejections/records, and owns
  task status.
- Runtime/Adapter: owns private perception and preparation inputs and typed failures.
- Gateway: remains the only Action admission/execution boundary.

The repair adds no automatic observation, candidate choice, replan, or Action. It
adds no RGB/task-specific branch and no new hash/frozen-contract mechanism. Existing
immutable revisions, ToolSpec declarations, typed records, and ordinary tests are
sufficient once their semantics are validated at the correct boundary.

## Acceptance / 验收

- A node with an unreachable predecessor/evidence projection slot is rejected during
  materialize/replan admission with the missing slot and Tool identity.
- Preserve IDs absent from the replacement graph are rejected; unchanged included
  nodes carry settlements forward.
- Runtime-owned non-recoverable Query failures do not produce an Agent-authored input
  repair revision.
- Repeated planning reads receive one correction and then terminate with a stable
  no-progress code, without Tool execution.
- Historical reducer replay uses revision-local effective settlements.
- Existing freshness, calibration, collision, IK, authorization, Gateway, and terminal
  settlement gates remain unchanged.
