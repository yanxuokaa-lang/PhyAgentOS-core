# Unknown World-Change Refresh Bootstrap Diagnosis

Date: 2026-10-09 (Asia/Shanghai)

## 结论 / Conclusion

本次不是规划参数、readiness 或 Gateway admission 失败。物理 Action 已执行并改变世界，
但 Runtime 无法确认最终抓取状态。正确恢复不是在旧 revision 重试 Action，也不是停止整个
AgentTask，而是追加一个只包含场景刷新 Query 的恢复 revision。刷新成功后，再由正常的
long-horizon AgentLoop 基于新证据继续理解、绑定、候选生成、准备和后续 Action。

This was not a planning-argument, readiness, or Gateway-admission failure. The
physical Action ran and changed the world, while Runtime could not establish the
final grasp state. Recovery must append a scene-refresh-only revision, then let
the normal long-horizon AgentLoop rebuild understanding, binding, candidates,
preparation, and any later Action from current evidence.

## 权威证据 / Authoritative Evidence

- AgentTask: `task_f6fcda0556d14245`
- Revision: `revision_1eea4bf7848f4e6a`
- Node: `red_acquire`
- Invocation: `invocation://object-acquire/a3eb80be38094bd3`
- Runtime artifact: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/48acd9cec4474b22a106bec8b1304f35/action-27490077fbd54595852ea798c7238844.json`
- Planning trace: `/home/yanxu/.PhyAgentOS/workspace/artifacts/planning-traces/task_f6fcda0556d14245/revision_1eea4bf7848f4e6a/red_acquire/dd66c6e65f9945a9.json`
- Session log: `/home/yanxu/.PhyAgentOS/workspace/sessions/cli_rgb-benchmark-injected-20261001-39.jsonl`

Runtime 的结构化终态为：

```text
status=unknown
phase=acquire
failed_phase=lift
failure_code=SimulationProbeError
error_detail=attached object did not lift with the gripper
simulator_steps=910
world_change_started=true
outcome_known=false
retryable_in_revision=false
requires_replan=true
recommended_action=reconcile_world
new_scene_revision=48acd9cec4474b22a106bec8b1304f35-2
```

`scene_effects` 同时声明 `entity://e1`、robot configuration、end-effector
pose、camera visibility 和 possession state 已变化，`effect_scope_complete=false`
且 `carry_forward_authorized=false`。因此旧 scene、候选、preparation 和 possession
均不能直接继承。

视频 manifest：

- Manifest: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/48acd9cec4474b22a106bec8b1304f35/task-video-4a69b123f87f4c3eb16e93d98ee5403e/cumulative/action-0001/manifest.json`
- Head: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/48acd9cec4474b22a106bec8b1304f35/task-video-4a69b123f87f4c3eb16e93d98ee5403e/cumulative/action-0001/video/head-camera.mp4`
- Observer: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/48acd9cec4474b22a106bec8b1304f35/task-video-4a69b123f87f4c3eb16e93d98ee5403e/cumulative/action-0001/video/observer-camera.mp4`

Manifest 记录一个 `status=unknown` Action、910 simulator steps、两个视角各
229 帧。视频显示对象在闭合和抬升尝试期间发生位移，但没有建立随夹爪稳定抬升的事实；
这与 Runtime 的 unknown terminal truth 一致。

任务之后由 CLI stop 变为 `failed`。该人工停止发生在 recovery proposer 失败之后，
不是本次物理失败的原始终态，也不能作为自动恢复成功或失败的证据。

## 原失败链 / Original Failure Chain

```text
Runtime unknown world-changing Action
  -> NodeSettlement(outcome_unknown, requires_replan=true)
  -> AgentRecoveryDecisions.select_recovery() = replan
  -> propose_replan() asks the model for a complete replacement graph
  -> model returns no unique submit_recovery Tool Call
  -> ValueError: recovery model returned no unique decision
  -> awaiting_replan
```

Runtime 和 PlanningLoop 已正确识别“世界已改变、旧 revision 不可重试、需要 replan”。
真正缺口是第一项必需恢复义务仍依赖模型完整输出。只要模型 transport 或结构化 Tool Call
失败，即使 ToolSpec 已明确提供场景刷新能力，AgentLoop 仍无法前进。

## 通用修复 / Generic Repair

`AgentRecoveryDecisions.propose_replan()` 现在只在以下三个 Runtime settlement 事实同时成立时
尝试 bootstrap：

```text
status == outcome_unknown
world_change_started is true
requires_replan is true
```

然后从当前 Coordinator-owned frozen ToolSpecs 中查找唯一能力：

- Tool semantics 为 `query`；
- planning policy 声明 `refreshes_scene=true`；
- 节点不需要旧场景才能满足的 frozen binding keys；
- 最终只有一个 capability。

若唯一匹配，则生成只含一个 semantic Query obligation 的 replacement PlanGraph。它不调用
Tool，不选择具体 provider，不填相机或传感器参数，不继承旧实体 pose/possession，不创建
Action。若能力缺失、不可空绑定或存在歧义，继续原有 model-proposed recovery；模型仍失败时
保持 fail-closed。

恢复节点 ID 由源 `revision_id` 确定性生成。同一失败事实重复提议得到同一 identity；若源图
已经包含该 ID，则确定性使用 `_2`、`_3` 等首个空闲后缀。这样既避免随机图 identity，也避免
后续恢复通过 `preserve_node_ids` 继承旧完成 settlement。这里使用已有 revision 主键和节点
唯一约束，不新增 hash、baseline 或 gate。

实现不包含 RGB、颜色、排列、对象类别、固定相机、固定 Tool ID 或 benchmark 分支。

## PAOS 所有权 / PAOS Ownership

- Runtime owns physical facts, the changed scene revision, possession uncertainty,
  Action terminal truth, and the recommendation to reconcile the world.
- Gateway owns readiness, admission, invocation, cancellation, and Action result
  reconciliation. The repair does not bypass it.
- Coordinator owns the frozen ToolSpecs, append-only PlanRevision, settlement,
  evidence authority, graph reconciliation, and replan budget.
- Agent owns selection of the concrete Query and arguments within the refreshed
  semantic obligation, then later semantic planning from newly observed facts.
- Long-horizon continuation owns forward progress after the refresh segment; the
  bootstrap itself does not claim task completion or schedule another Action.

## 七维 Code Review / Seven-Dimension Code Review

1. **Architecture**: 修复位于 recovery decision 层，复用 `compile_task_plan()`、
   `reconcile_replan_delta()` 和现有 selection/execution 流程，没有在 Skill 或 Adapter 建立第二套循环。
2. **Correctness**: 仅响应三个明确 Runtime facts；bootstrap 只生成 Query obligation，旧 Action
   settlement 与 invocation 保持不变。
3. **Recovery and idempotency**: 不 replay Action；同一源 revision 的提议 identity 稳定，节点
   冲突时确定性取新 ID，防止旧 settlement 被误继承。
4. **Robotics safety**: unknown 仍是 unknown；不假定对象掉落、被夹持或留在原位。任何后续
   Action 仍须经过新观察、理解、绑定、prepare、Gateway admission 和 terminal settlement。
5. **Extension compatibility**: capability discovery 完全基于 ToolSpec semantics、
   `refreshes_scene` 和 binding contract；无任务名、颜色、相机或 provider 特判。
6. **Observability and maintainability**: replacement reason 明确记录 unknown world change；逻辑为
   两个窄 helper，并有 capability 歧义、无绑定、确定性 identity 与完整 loop 回归。
7. **AgentLoop autonomy**: 确定性的第一步 reconciliation 不再依赖模型格式；刷新完成后仍回到
   正常 AgentLoop，而不是把 bootstrap 扩张为硬编码任务工作流。

Review 中发现并修复两项 Major：随机恢复节点 ID 会破坏同一失败事实的重入对账；固定节点 ID
又可能继承旧 settlement。最终实现使用源 revision 的确定性且冲突安全的节点 ID。未发现遗留
Blocker 或 Major。

## 验证边界 / Validation Boundary

验证仅使用 fake Coordinator、scripted provider、typed envelopes 和本地单元/集成测试。
没有创建或恢复 live AgentTask，没有调用 live Gateway Query/Action，没有推进 simulator，
没有安装或重启 Runtime，也没有执行真实运动。

回归覆盖：

- Runtime unknown world change 自动进入 Query-only replacement revision；
- recovery model 不被调用，原 acquire 不被再次执行；
- refresh Query 在新 revision 执行并完成 segment；
- refresh capability 缺失或歧义时不猜测；
- 非 unknown failure 保留原 model replan 行为；
- 恢复节点 identity 重入稳定且避开源图冲突；
- planning loop、long-horizon continuation 和 effect recovery 未回归。

剩余边界：刷新 Query 成功只证明获得了当前观察。对象是否掉落、是否仍被夹持、实体身份如何
延续以及下一次动作是否安全，仍必须由新的理解、绑定、planning preparation 与 Runtime/Gateway
准入决定，Core 不作推断。
