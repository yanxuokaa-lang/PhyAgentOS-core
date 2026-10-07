# Action Selection Projection Diagnosis / Action 选择投影诊断

## Scope / 范围

本诊断记录成功 `manipulation.prepare` 与 `object.acquire` 选择之间的契约缺口。修复必须适用于任意 provider、实体、任务目标、传感器和机械臂，不得绑定 RGB 排列或具体 benchmark。

This diagnosis records the contract gap between a successful `manipulation.prepare` result and `object.acquire` selection. The repair must apply to arbitrary providers, entities, task goals, sensors, and arms without binding behavior to RGB ordering or a concrete benchmark.

## Authoritative Event Chain / 权威事件链

- Task `task_cb2ff2de02cd44ca`, revision `revision_759e735958e84208`.
- `red_grasp`: selection persisted, `grasp.propose` terminal `succeeded`, node completed.
- `red_prepare`: selection persisted, `manipulation.prepare` transport `succeeded`, business status `available`, node completed.
- The preparation record contains one assignment for `entity://e1`, candidate `candidate://e1/27`, selected arm `left`, an assignment reference, a preparation reference, and route-readiness evidence.
- `red_acquire`: no selection, no rejection, no execution record, no invocation, and no simulator step.
- The controller stopped the node as `node_selection_no_progress` and moved the task to `awaiting_replan`.

## Root Cause / 根因

`object.acquire` requires twelve strict inputs but declares no `argument_projection_plan`. The Agent therefore has to browse one predecessor response and manually map top-level preparation fields, request-only freshness fields, and nested assignment fields. Historical successful traces show that this sometimes works, but it is model-dependent rather than contract-owned.

`object.acquire` 需要十二个严格输入，却没有声明 `argument_projection_plan`。因此 Agent 必须浏览一条前驱响应并手工映射 preparation 顶层字段、只存在于请求中的 freshness 字段以及嵌套 assignment 字段。历史成功 trace 证明该过程偶尔可行，但它依赖模型表现，而不是契约保证。

The existing projection protocol can filter a collection by a selected join identity, but can only emit the whole filtered list. It cannot require exactly one match and project selected item fields into top-level consumer arguments. Using array index zero would encode producer ordering as semantics and is rejected as a design choice.

现有投影协议可以按已选 join identity 过滤集合，但只能输出整个过滤列表；它不能要求唯一匹配并把该项字段展开到 consumer 顶层。使用数组下标零会把 producer 顺序当成业务语义，因此不采用。

## PAOS Ownership / PAOS 所有权

1. The producer Tool owns preparation/acquisition result facts.
2. ToolSpec owns the declarative producer-to-consumer field mapping.
3. The Agent owns whether to select the ready Action and which authorized source record to name.
4. The Coordinator validates source scope, Tool identity, scene/entity lineage, unique join, and final input schema, then persists the selection.
5. Gateway and Runtime alone own Action admission, motion authorization, execution, stop, reconciliation, and terminal outcome.

1. producer Tool 拥有 preparation/acquisition 结果事实。
2. ToolSpec 拥有声明式 producer-to-consumer 字段映射。
3. Agent 决定是否选择 ready Action，并显式指定哪条授权 source record。
4. Coordinator 校验 source scope、Tool identity、scene/entity 血缘、唯一 join 与最终输入 schema，再持久化 selection。
5. Gateway 与 Runtime 独占 Action admission、运动授权、执行、stop、reconciliation 与终态结果。

## Required Repair / 必需修复

- Extend named projection sources with a generic uniquely matched item field map.
- Add a preparation predecessor projection to `object.acquire`.
- Add a completed-acquisition predecessor projection to `object.place` so the same defect does not move one node later.
- Reject zero matches, duplicate matches, missing fields, wrong producer Tools, and wrong source scopes before a selection is persisted.
- Keep `destination_ref` as a frozen node input owned by the selected goal source; do not derive or replace it in the Action projection.

## Safety Boundary / 安全边界

This repair compiles selection arguments only. It grants no motion authorization, starts no Action, advances no simulator, changes no collision/IK/workspace policy, and introduces no retry or automatic replan.

本修复只编译 selection 参数，不授予运动权限、不启动 Action、不推进 simulator、不改变 collision/IK/workspace 策略，也不增加重试或自动 replan。
