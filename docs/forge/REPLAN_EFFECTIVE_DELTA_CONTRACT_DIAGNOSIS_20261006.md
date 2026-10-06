# Replan Effective Delta Contract Diagnosis / Replan Effective Delta 契约诊断

## Conflicting Contracts / 冲突契约

The current recovery path combines three individually reasonable rules that are
jointly inconsistent:

1. `build_replan_delta()` marks every node outside the failed node's descendant
   closure as a preserve candidate.
2. Recovery guidance permits a segmented replacement graph containing only the
   next recovery work and forbids copying prior nodes merely for history.
3. `begin_revision_from_delta()` requires every declared preserved node to be
   present unchanged in the replacement graph before carrying its settlement.

现状把“旧图中允许保留的节点集合”误当成“新图中实际保留的节点集合”。前者可在 replacement
产生前计算，后者只有看到 replacement graph 后才能确定。

## Ownership / 所有权

- The Agent owns the semantic choice of replacement nodes.
- The planning layer owns pure reconciliation between a candidate delta and the
  submitted replacement graph.
- Coordinator owns revision admission, persisted settlement carry-forward, and
  the final fail-closed consistency check.
- Runtime/Gateway own Tool execution and motion admission; this repair does not
  enter either boundary.

The planning layer must not synthesize recovery nodes, copy old graph nodes into
the proposal, invoke a Tool, or decide that recovery should continue.

## Required Effective-Delta Rule / Effective Delta 规则

Given old graph `G`, candidate delta `D`, and Agent-selected replacement graph
`R`, derive an effective delta `D'` as follows:

```text
effective_preserve = []
for node_id in D.preserve_node_ids:
    if node_id is absent from R:
        keep it only in old-revision history
    elif digest(G[node_id]) == digest(R[node_id]):
        add node_id to effective_preserve
    else:
        reject the proposal as changed preserved content
```

All other delta fields remain unchanged. The operation is pure and creates no
task event, execution record, Query, Action, simulator step, or world change.

## Why Existing Mechanisms Are Insufficient / 现有机制为何不足

- Git and versions identify source revisions, not the semantic relationship
  between two runtime PlanGraphs.
- Primary keys and types permit both an omitted string ID and a structurally
  valid changed node.
- DAG validation checks graph shape but cannot determine whether settlement
  carry-forward is truthful.
- Coordinator's strict check detects the contradiction only after the model turn
  and replan state transition; it cannot infer whether omission was intentional.

The effective-delta step removes a false declaration rather than adding a new
release gate. Coordinator admission remains the authoritative safety boundary.

## Rejected Alternatives / 未采用方案

- Do not weaken `begin_revision_from_delta()`: that would allow settlement
  carry-forward for a node that has no replacement obligation.
- Do not force the Agent to copy every historical node: that contradicts
  segmented recovery and grows each continuation graph with irrelevant history.
- Do not silently treat a changed same-ID node as preserved or new: a completed
  settlement could then attach to different semantics or be repeated without an
  explicit identity change.
- Do not special-case `red_grasp`, `manipulation.prepare`, RGB, benchmark goals,
  colors, task IDs, or camera names.

## Acceptance Cases / 验收用例

1. A recovery-only replacement omits a completed sibling: the effective delta
   omits that sibling from `preserve_node_ids`, and admission may proceed.
2. A replacement includes an allowed node byte-for-byte semantically unchanged:
   it remains preserved and its settlement is carried into the new revision.
3. A replacement includes an allowed same-ID node with changed content: proposal
   validation fails before revision admission and uses the existing bounded
   correction turn.
4. A node not allowed by the candidate delta is never promoted to preserved.
5. Proposal normalization performs no Tool or motion side effect.

## Safety and Extension Boundary / 安全与扩展边界

Frame, calibration, freshness, collision, IK, authorization, Gateway admission,
Action ownership, and terminal settlement rules remain unchanged. The rule uses
only generic PlanGraph identity and digest semantics, so future Skills and Tools
receive the same behavior without task-specific code.
