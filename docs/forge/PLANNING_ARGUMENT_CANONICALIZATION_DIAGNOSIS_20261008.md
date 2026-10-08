# Planning Argument Canonicalization Diagnosis / Planning 参数规范化诊断

## Scope / 范围

本诊断记录任务 `task_f717aae0737f4d63` 在 `red_checkpoint_observe` 节点停止的原因，以及不依赖 RGB 排列、颜色、相机名称或具体 Tool 的修复边界。

## Observed evidence / 观测证据

- `red_acquire` 和 `red_place` 已产生成功的 task-bound records；失败节点是放置后的只读 `scene.observe` checkpoint。
- Coordinator 持久化 selection 的 Tool arguments 为：

  ```json
  {"sensor_refs":["camera/head","camera/front"],"max_age_ms":1000}
  ```

- 该 selection 的 `input_binding_digest` 是上述精确参数的摘要。
- `scene.observe` ToolSpec 为 `max_capture_skew_ms` 声明 `default: 50`。
- 恢复路径先恢复 selection，再由 `AgentTaskCoordinator.invoke_query()` materialize schema defaults，最终参数变成：

  ```json
  {"sensor_refs":["camera/head","camera/front"],"max_age_ms":1000,"max_capture_skew_ms":50}
  ```

- `_append_execution()` 随后用带默认值的参数验证原始 selection binding，触发 `planning execution arguments do not match their binding`。
- Gateway 没有收到本次请求，没有 observation artifact、动作、simulator step 或运动授权变化。

## Failure scenario and existing mechanism gap / 失败场景与现有机制不足

同一个合法 Tool input 在 selection 阶段和 execution 阶段有两种 JSON 表示。普通主键、事务和已有 digest 只能证明各自输入未被篡改，不能让两个阶段使用相同的 schema-default 语义；因此 AgentLoop 会反复消费同一未消费 selection，得到同一个确定性拒绝。

## Design decision / 设计决策

在 `planning.input_schema` 增加 provider-neutral 的公共参数规范化函数：根据冻结 ToolSpec schema 复制顶层 defaults，并保留当前 oneOf 分支的 sibling suppression。planning dispatch 在生成 digest 前规范化；Coordinator query admission 在记录和 Gateway 调用前使用同一函数。校验同时保留对旧持久化 selection 的 raw digest 兼容，避免升级后丢失尚未消费的合法 selection。

该机制只解决已证实的 selection/execution 表示不一致，不添加新的 motion gate、hash、RGB 分支或自动重试。Query 仍是只读，Action 仍需独立 admission，`motion_authorized` 不被改变。

## Acceptance / 验收

- omitted default 与显式 default 产生同一 canonical arguments 和 digest。
- oneOf 选择不会注入未选分支字段。
- 新 selection 恢复执行产生 task-bound record。
- 旧 raw selection 在 schema canonicalization 后仍可一次性恢复，不重复执行。
- 回归全程不调用真实 Gateway、不创建或恢复任务、不推进 simulator 或物理动作。

## Implementation and review result / 实现与审查结果

The fix is implemented at the shared Core planning boundary rather than in a
workflow, color, camera, or Tool-specific branch:

- `PhyAgentOS/planning/input_schema.py:L42-L128` now owns
  `materialize_tool_arguments()`. It applies frozen top-level ToolSpec defaults
  and preserves the selected `oneOf` branch.
- `PhyAgentOS/agent/planning_dispatch.py:L636-L637` canonicalizes arguments
  before validation, persistence, and `input_binding_digest` creation.
- `PhyAgentOS/forge/task.py:L2654-L2700,L2702-L2819,L2914-L2995` uses the same
  canonical representation for Query, Action, and Session Gateway admission,
  execution records, and unknown-Action de-duplication. Action selection is
  checked before the before-snapshot side effect; `_append_execution()` keeps
  the transaction-boundary check.
- `PhyAgentOS/forge/task.py:L3824-L3917` accepts a legacy raw selection only
  when its persisted binding, identity fields, and frozen-schema canonical
  arguments all agree. A changed business argument remains rejected.

The implementation-review pass found and fixed one Major ordering issue: an
early version delayed Action selection validation until after before-snapshot
capture. The final order validates the Tool schema and planning selection before
any snapshot, record, Gateway, or motion boundary. The seven dimensions now
pass: architecture ownership, correctness, recovery/idempotency, robotics
safety, extensibility/compatibility, observability, and AgentLoop convergence.

Validation was no-motion and Gateway-free:

- focused planning/AgentLoop suite: `230 passed`;
- complete Core suite: `802 passed in 28.49s`;
- Ruff, `compileall`, and `git diff --check`: passed;
- Query, Action, and Session compatibility tests cover new canonical and legacy
  raw selections, oneOf suppression, and changed-argument fail-closed behavior.
- unknown legacy Action records are canonicalized before duplicate comparison,
  so adding an explicit default cannot resend an Action with unknown outcome.

No task was resumed, no Runtime was restarted, no real Gateway was called, and
no simulator or physical motion advanced.
