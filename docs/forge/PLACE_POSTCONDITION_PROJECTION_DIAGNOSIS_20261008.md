# Place Postcondition Projection Diagnosis / 放置后置条件投影诊断

## Scope / 范围

本诊断针对 `task_03bf7df3afa246ea` 在 `object.place` 后进入
`reconciliation_required` 的结果投影问题。它不改变目标绑定、候选筛选、RGB
排列、碰撞策略或 Agent 的自主规划边界。

## Observed facts / 已核实事实

- `object.acquire` 的权威记录为 `succeeded`。
- `object.place` 的底层 Action artifact 与 task-video manifest 均记录
  `status=succeeded`、`world_change_started=true`、`outcome_known=true`，并有
  `simulator_steps=1905`、`new_scene_revision` 和 `placement_measurement`。
- `RoboTwinPersistentEngine.execute()` 在完整 route generator 终止后执行
  `_verify_release()`，随后完成 video artifact、scene revision 和 action artifact。
- 该返回值没有发布公共 `object.place` contract 要求的
  `release_confirmed`、`retreat_completed`、`clear_of_target`、
  `observation_ready` 四项字段。
- `pick_place_workflow._ProjectedDriver` 对成功但缺少任一 postcondition 的结果
  fail-closed 地降级为 `unknown`，因此 Controller 要求 reconciliation；这一步
  没有重复 Action，也没有证明物理动作失败。

## Failure boundary / 失败边界

这是 Adapter/Node producer 与公共 Tool contract 之间的投影缺口，不是
Coordinator 的候选选择错误，也不是 AgentLoop 的自动观察或 replan 错误。
transport status 和内部 artifact 不能替代已声明的 Tool result 字段，因为
上层 settlement 只消费经过 contract 投影的结果。

## Design decision / 设计决定

在成功路径中由已有的执行事实构造四项字段：释放验证通过支持
`release_confirmed`；route generator 已完整经过 retreat 支持
`retreat_completed`；retreat 完成且没有后续 route 阶段支持 `clear_of_target`；
视频/action artifact 与新 scene revision 均成功物化后支持 `observation_ready`。

失败、取消、视频写入失败或 route 未完整终止时不推断这些字段为真，继续由
`_ProjectedDriver` 保持未知/对账语义。修复不自动重试、不自动观察、不自动
重新放置，也不绕过 Gateway admission。

## Verification / 验证

增加 producer、runtime projection 和 AgentLoop 回归：完整成功结果保持
`succeeded`；任一字段缺失仍为 `unknown`；真实 unknown 仍要求 reconciliation；
且不会产生第二个 `object.place` invocation。所有验证均使用 no-motion 测试替身，
不调用 simulator step，不改变 `motion_authorized` 或真实世界状态。
