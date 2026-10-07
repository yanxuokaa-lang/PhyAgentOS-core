# Action Node AgentLoop Convergence Diagnosis / Action 节点 AgentLoop 收敛诊断

## Scope / 范围

本诊断区分循环收敛机制与 Action selection 配方缺失。目标不是延长模型回合或自动执行，而是让每个 ready 节点向 Agent 暴露由 ToolSpec 声明且可满足的下一步。

This diagnosis separates loop convergence from a missing Action-selection recipe. The goal is not to extend model turns or auto-execute, but to expose a ToolSpec-declared, satisfiable next step for every ready node.

## What Worked / 已正确工作的部分

- Planning progress is measured from durable Coordinator facts: selections, rejections, and execution records.
- Repeated readiness/context reads do not count as progress.
- One corrective turn is allowed, followed by deterministic `node_selection_no_progress` convergence.
- No Tool or Action is automatically dispatched, so an empty model turn cannot cause motion.

These properties prevented the earlier forty-turn read loop and must remain unchanged.

上述属性阻止了此前四十轮只读空转，必须保留。

## Contract Failure / 契约故障

The corrective prompt tells the Agent to inspect ToolSpec source slots and submit one governed selection. For `object.acquire`, the live ToolSpec had no projection slots, so the prompt described a mechanism that the current consumer did not provide. The Agent could only return to manual field browsing, and no new Coordinator fact was produced.

纠正提示要求 Agent 检查 ToolSpec source slots 并提交一次受治理选择，但 live `object.acquire` ToolSpec 没有 projection slots。提示描述了当前 consumer 并未提供的机制，Agent 只能继续手工浏览字段，无法产生新的 Coordinator fact。

## Required Loop Behavior / 必需循环行为

1. `forge_plan_ready` exposes named source slots declared by the selected ToolSpec.
2. The Agent chooses a candidate Tool and supplies only authorized record IDs for those slots.
3. The Coordinator compiles arguments and either persists a selection or emits one structured rejection.
4. A persisted selection is resumed and executed through the existing Action wrapper; an admitted invocation is reconciled rather than replayed.
5. If no selection/rejection/execution fact appears after the bounded corrective turn, no-progress still stops the node.

No-progress is therefore a convergence guard, not a source-recipe generator. Projection availability belongs to ToolSpec and plan admission.

因此 no-progress 是收敛保护，不负责生成 source recipe；投影可用性属于 ToolSpec 与计划准入边界。

## Generic Acceptance / 通用验收

- A unique preparation assignment can be selected for acquisition using one predecessor record ID.
- Zero or duplicate entity matches fail before selection persistence.
- A successful acquisition can be selected for placement using one predecessor record ID plus the frozen destination.
- Wrong Tool or evidence/predecessor scope is rejected.
- Tests create no AgentTask in the live workspace, call no Gateway Query/Action, and produce no simulator or hardware motion.
- No implementation branch refers to a color, arrangement, benchmark ID, entity number, candidate number, sensor name, or arm name.
