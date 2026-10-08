# Persistent Action Receipt Transport Diagnosis / 持久化 Action Receipt 传输诊断

## Incident / 事件

`task_acf4468c297e43ef` completed `green_grasp` and `green_prepare`, admitted one
`green_acquire`, and then stopped at `reconciliation_required:green_acquire`.
The Runtime-facing result said `persistent_world_connection_lost`, while the
engine artifact and task-video manifest recorded the same invocation as
`succeeded` after 789 simulator steps.

`task_acf4468c297e43ef` 已完成 `green_grasp` 与 `green_prepare`，并准入一次
`green_acquire`，随后停止于 `reconciliation_required:green_acquire`。Runtime
侧结果为 `persistent_world_connection_lost`，但 engine artifact 与 task-video
manifest 将同一 invocation 记录为执行 789 simulator steps 后 `succeeded`。

## Root Cause / 根因

The complete Action artifact is 1,882,147 bytes. Its raw `arm_attempts` alone
serialize to 1,053,201 bytes, exceeding `ProcessWorkerConfig.max_line_bytes`
(1,048,576 bytes). `RoboTwinPersistentEngine.execute()` wrote the complete
artifact and then returned the same nested planner/execution data through the
JSONL poll response. `JsonlProcessWorkerClient` rejected the response and
aborted the worker. `PersistentWorkerClient` subsequently exposed only a lost
connection, so Core could not settle the known-success result.

完整 Action artifact 为 1,882,147 bytes，其中原始 `arm_attempts` 序列化后即为
1,053,201 bytes，超过 `ProcessWorkerConfig.max_line_bytes` 的 1,048,576 bytes。
`RoboTwinPersistentEngine.execute()` 在写入完整 artifact 后又通过 JSONL poll
返回同一份嵌套规划/执行数据。`JsonlProcessWorkerClient` 拒绝响应并终止 worker，
`PersistentWorkerClient` 随后只暴露连接丢失，Core 无法结算底层已知成功结果。

## Ownership Boundary / 所有权边界

- Runtime engine owns complete trajectories, contacts, controller traces, and
  immutable Action artifacts.
- Persistent provider owns the bounded terminal receipt crossing the process
  boundary.
- Gateway owns invocation lifecycle and terminal result publication.
- Coordinator owns execution records and late settlement resolution.
- Agent owns explicit next-step decisions, but may not retry an unknown Action
  or infer success from a filesystem artifact.

- Runtime engine 持有完整轨迹、接触、控制器 trace 与不可变 Action artifact。
- Persistent provider 持有跨进程的有界 terminal receipt。
- Gateway 持有 invocation 生命周期与终态发布。
- Coordinator 持有执行记录与 late settlement resolution。
- Agent 显式决定下一步，但不能重试 unknown Action，也不能从文件 artifact
  自行推断成功。

## Generic Repair / 通用修复

1. `PersistentManipulationProvider` projects every engine result into a
   256-KiB receipt containing lifecycle facts, evidence references,
   conservative scene effects, and ToolSpec-declared arm summaries.
2. Full execution plans and provider-private diagnostics remain in the Action
   artifact. The artifact now also records invocation identity, owner, its own
   evidence references, and video references for authoritative reconciliation.
3. Oversized scene-effect lists fail closed by disabling carry-forward rather
   than deleting the Action outcome or enlarging the transport limit.
4. Protocol-limit errors retain `worker_request_too_large` or
   `worker_response_too_large`; process termination and resource exhaustion
   remain distinct.
5. If receipt projection fails after the engine settles, the provider returns
   infrastructure-owned `outcome_unknown`, preserves artifact refs, marks
   possession uncertain, and recommends stop. It never repeats the Action.

1. `PersistentManipulationProvider` 将每个 engine 结果投影为 256-KiB receipt，
   仅包含生命周期事实、证据引用、保守 scene effects 和 ToolSpec 声明的机械臂摘要。
2. 完整执行计划和 provider 私有诊断保留在 Action artifact；artifact 同时记录
   invocation identity、owner、自身证据引用及视频引用，以支持权威对账。
3. 过大的 scene-effect 列表通过关闭 carry-forward fail-closed，而不是删除 Action
   结果或放大 transport 上限。
4. 协议上限保留 `worker_request_too_large` / `worker_response_too_large`；进程终止
   和资源耗尽仍是独立错误。
5. engine 结算后若 receipt 投影失败，provider 返回 infrastructure-owned
   `outcome_unknown`、保留 artifact refs、将 possession 标为 uncertain 并建议 stop，
   绝不重复 Action。

The implementation contains no color, arrangement, object-count, benchmark,
camera, or fixed-arm branch. It applies to every persistent Action result.

实现不包含颜色、排列、对象数量、benchmark、相机或固定机械臂分支，适用于所有
persistent Action 结果。

## Validation Boundary / 验证边界

All regression tests are no-motion. They use fake engines or existing artifacts;
no AgentTask, Gateway Action, simulator step, or physical command is created.
The current failed invocation is not retried or automatically resolved.

全部回归均为 no-motion，使用 fake engine 或已有 artifact；未创建 AgentTask，未调用
Gateway Action，未推进 simulator step 或物理命令。当前失败 invocation 未被重试或
自动结算。
