# Scene Bind Selection Consumption Diagnosis / Scene Bind Selection 消费诊断

## Scope / 范围

本诊断记录 `scene.bind` 在 AgentLoop 恢复持久化 selection 时没有进入 Gateway 的失败。
修复面向所有使用 Coordinator selection 的 task-bound Query，不包含 RGB、颜色、排列、
benchmark、固定相机、固定实体或固定机械臂逻辑，也不改变 Action、Runtime 或运动授权。

## Observed evidence / 已核实证据

- 任务 `task_e801fe61a0474dda` 的 `red_checkpoint_bind` 已产生
  `planning_selection_persisted` 和 planning binding。
- selection 消费约定是 `arguments={}`、`use_selected_arguments=true`；实体引用由
  Coordinator 根据当前 task/revision 的 selection 解析，Agent 不直接传私有投影参数。
- 事件流在 selection 持久化后没有 `query_started` 或 `tool_execution_finished`，最终错误为
  `persisted selection execution produced no task-bound record`。
- `ForgeToolQueryTool` 原先在解析 selection 前调用 `_scene_bind_argument_error(task,
  arguments)`。因此合法的空 literal arguments 被误判为缺少 `entity_refs`，Gateway 没有收到
  Query。错误随后被 `_call` 序列化为 JSON，planning loop 只能看到没有 task-bound record，
  不能获得实际的 Query 失败事实。

## Ownership diagnosis / 所有权诊断

这是 Core Forge Tool wrapper 的消费顺序错误，不是场景理解、候选筛选、Provider、Runtime、
ToolSpec 或视频链路错误：

1. Agent 只声明使用已持久化的 selection；Coordinator 负责解析 binding 和参数。
2. Forge Tool wrapper 负责在调用 Gateway 前执行 `scene.bind` 的通用实体引用校验。
3. Gateway/Runtime 仍负责真正的 task-bound Query 执行和结果记录。
4. AgentLoop 只消费持久化 selection、Query record 和 settlement，不自动选择实体、不自动
   观察、不自动重试、不自动 replan，也不执行 Action。

## Resolution / 修复方案

`use_selected_arguments=true` 时，wrapper 现在先调用
`selected_execution_binding()` 和 `selected_execution_arguments()`，再对解析后的
`resolved_arguments["entity_refs"]` 执行原有校验。该顺序使合法 selection 能到达
`coordinator.invoke_query()`；空 literal arguments 不再被当作用户缺参。

校验没有被删除或放宽：空数组、非字符串引用、使用 `entities` 而非 `entity_refs`、以及
当前理解记录中的歧义实体仍 fail-closed，并且在校验失败时不会触发 Gateway。该修复不新增
哈希、专用对象分支或自动决策，符合 PAOS 的 Coordinator-owned projection、显式 admission
和 AgentLoop 事实驱动收敛原则。

## Verification boundary / 验证边界

- 成功回归证明空 literal arguments 能由持久化 selection 解析为 task-bound Query。
- 失败回归证明非法解析结果仍返回 `scene_bind_missing_entity_refs`，且 Gateway 不会被调用。
- Core focused suite：`136 passed`；Ruff、compileall、`git diff --check` 通过。
- 这是 Query-only、no-motion 验证；未创建任务、未恢复任务、未调用真实 Gateway、未推进
  simulator，也未改变 Runtime ownership 或运动授权。
