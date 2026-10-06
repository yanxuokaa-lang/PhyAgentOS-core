# Replan Preserve Event Diagnosis / Replan Preserve 事件诊断

## Scope / 范围

This diagnosis freezes the control-plane facts for AgentTask
`task_444c570eae644b9a`, active revision
`revision_01d4cba4fc54490b`. It does not infer physical success from a Query
receipt and does not authorize task resumption.

本文固定 AgentTask `task_444c570eae644b9a`、活动 revision
`revision_01d4cba4fc54490b` 的控制面事实。它不从 Query receipt 推断物理成功，
也不授权恢复任务。

## Persisted Event Chain / 持久化事件链

1. Discovery in `revision_926351f7cd60474f` succeeded for
   `scene.observe`, `scene.understand`, `manipulation.capabilities`,
   `scene.bind`, and `task.goal`.
2. `red_grasp` in `revision_01d4cba4fc54490b` settled `completed` after the
   read-only `grasp.propose` record `tool_27210b3da22744e5` succeeded.
3. `red_prepare` selected and invoked the read-only
   `manipulation.prepare` Query. Transport record `tool_908352b4b7394f90`
   succeeded, while its planning result was `failed/no_qualified_contacts`.
4. The rejection diagnostics reported contact/collision evidence including
   `mesh_support_penetration=46`, `occluded_samples=3304`, and
   `unobserved_samples=3526`.
5. Recovery events were persisted in order:
   `query_failure_recovery_projected`, `agent_recovery_decided` with
   `decision=replan`, and `plan_replan_requested`.
6. The recovery model proposed one current recovery Query and explicitly
   omitted historical `red_grasp`. Before a new revision could be admitted,
   `begin_revision_from_delta()` rejected the proposal with
   `cannot preserve node(s) absent from replacement graph: red_grasp`.

对应事实是：发现链成功，抓取候选 Query 成功，准备 Query 的 transport 成功但业务结果为
`no_qualified_contacts`；随后 replan 在新 revision admission 之前失败。没有 acquire、
place 或其他 Action 被调用。

## Physical-State Boundary / 物理状态边界

- `invocation_id` is null for the failed preparation path.
- No Action execution record exists for acquire or place.
- `world_change_started=0`; no simulator step or physical motion is proven.
- The object was not grasped or placed. `red_grasp` names a grasp-proposal
  planning node; its completion is not a physical grasp.

因此，本次不能表述为“已经放置成功”或“抓取后失败”。失败位置是 read-only preparation
之后的 recovery revision 构造边界。

## Excluded Causes / 已排除原因

- Candidate selection was persisted and `grasp.propose` completed.
- The benchmark destination was injected into the `red_prepare` planning
  binding by Coordinator.
- The failure was not a Gateway transport error.
- The terminal error was not caused by collision or IK admission being
  bypassed; those gates remained fail-closed and no Action was reached.

## Immediate Root Cause / 直接根因

`build_replan_delta()` computed `preserve_node_ids=("red_grasp",)` from the
old graph before the replacement graph existed. Recovery guidance then told the
Agent to submit only current recovery work and not duplicate historical nodes.
The strict Coordinator admission correctly rejected metadata that claimed to
preserve a node absent from the submitted replacement graph.

This is a generic planning-contract timing defect, not an RGB arrangement,
color, benchmark, camera, or provider-specific failure.
