# RGB Acceptance Run 1 AgentLoop Diagnosis

日期：2026-09-30（Asia/Shanghai）
任务：`task_3aac21bc500b4148`  运行：`cli:rgb-acceptance-20260930-run1`

## 结论

本轮没有执行任何 `grasp.propose`、`manipulation.prepare`、`object.acquire` 或
`object.place`，因此没有物理状态变化。失败发生在首次 discovery 完成后的
PlanGraph 物化阶段，不是 Runtime、Qwen、Gateway 或运动门禁失败。

## 权威记录

- 同一初始 revision 已成功记录 `scene.observe`、`scene.understand`、
  `manipulation.capabilities`、`task.goal` 和 `scene.bind`。
- `scene.observe` 使用了同步 `camera/head` 与 `camera/front`，并返回单一 scene
  revision `04bd35d427f1464f8ca22a7ff47d10fc-1`。
- `scene.bind` 成功绑定当前任务的三个实体；未使用环境对象替代任务实体。
- Agent 随后提交的语义图仍包含 `initial_observe`、`initial_understand`、
  `initial_capabilities` 和 `initial_bind` 四个已经成功落盘的 Query 节点。
- Coordinator 为 `initial_observe` 建立了新的 selection；由于该节点的冻结参数与
  已选参数/default 不一致，首次执行在控制面校验阶段被拒绝。后续修正留下未消费
  selection，任务进入 `awaiting_replan`，随后安全取消。

## 根因与边界

根因是 discovery 记录和新提交 PlanGraph 之间缺少通用的“已满足前缀”投影：
`forge_task_materialize_plan` 可以看到当前任务的成功 Query 证据，却直接把 Agent
提交的完整 discovery 前缀交给 Coordinator。这样会把已经完成的 Query 当成未来节点
重新选择，而不是从当前证据继续剩余 suffix。

这不是传感器、模型或动作重试问题。修复必须保持在 PAOS 控制面，不能复制 settlement、
伪造 opaque ref、重发 Query/Action，不能依赖 RGB、相机名称或某个 provider。

## 修复验收条件

1. 仅对当前 active revision 的成功、任务所有 Query 记录进行匹配。
2. 只裁剪连续的 leading Query prefix；传感器、freshness、实体或 evidence 不匹配时
   保留节点并继续 fail-closed。
3. 裁剪后从保留节点移除指向已完成前缀的依赖；Coordinator 仍持有原始 evidence
   refs，不生成新的 settlement 或 planning binding。
4. 记录结构化裁剪诊断，使 AgentLoop 日志能区分“继续 suffix”和“重发 Query”。
5. complete external `plan_graph` 路径不被静默改写。
