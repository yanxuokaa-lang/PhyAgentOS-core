# Agent 模型 Provider 节点恢复诊断 / Agent Model Provider Node Recovery Diagnosis

日期 / Date: 2026-10-12

版本 / Version: v13.3.0

证据任务 / Evidence task: `task_506b5167c1164460`

证据 revision / Evidence revision: `revision_3befcc0def664850`

## 结论 / Conclusion

本次失败不是 `scene.bind`、Gateway、Query provider 或物理 Action 失败。执行当前规划节点的 Agent 模型回合在任何 Tool selection、Tool execution record 或 Gateway 调用产生前返回 `provider_error`。旧实现将所有 `NodeTurnProviderError` 投影为 `awaiting_replan`，从而把一个没有改变计划和世界的控制面传输故障错误升级成整图重规划。

This incident was not a `scene.bind`, Gateway, Query-provider, or physical Action failure. The Agent model turn for the active planning node returned `provider_error` before any Tool selection, Tool execution record, or Gateway call existed. The old implementation projected every `NodeTurnProviderError` into `awaiting_replan`, incorrectly escalating a control-plane transport failure that changed neither the plan nor the world into a graph replan.

通用修复是新增 Coordinator 所有的 `waiting_for_agent_provider` 生命周期：在同一 task、revision 和 node 上持久化 pre-Tool 模型阻塞，受限重试当前节点；只有当前 scene revision 已变化时才进入重规划。已完成 Action settlement 保持不可变，不重放抓取、放置或其他世界变化动作。

The generic fix adds a Coordinator-owned `waiting_for_agent_provider` lifecycle. It persists a pre-Tool model block against the same task, revision, and node and performs bounded same-node retries; replanning occurs only when the current scene revision has changed. Completed Action settlements remain immutable, and grasp, place, or any other world-changing Action is not replayed.

## 权威时间线 / Authoritative Timeline

1. 当前 revision 已完成六个节点：grasp proposal、preparation、acquire、place、post-Action observation 和 post-Action understanding。 / The active revision had completed six nodes: grasp proposal, preparation, acquire, place, post-Action observation, and post-Action understanding.
2. 放置 Action `invocation://object-place/0a4bc435492b48f5` 已有权威成功终态：`release_confirmed=true`、`retreat_completed=true`、`clear_of_target=true`、`observation_ready=true`、`recommended_action=continue`。 / The place Action had an authoritative successful terminal result with release, retreat, clearance, observation readiness, and continue recommendation confirmed.
3. Action 将场景推进到 `52f7b4bda25c44979d3e0ad421c268cc-3`，并声明 `effect_scope_complete=true`、`carry_forward_authorized=false`。 / The Action advanced the scene and explicitly disallowed carrying stale scene-bound evidence forward.
4. 新观察和新理解成功；待执行节点需要建立当前视觉实体到稳定执行实体的新绑定。 / New observation and understanding succeeded; the pending node needed to bind current visual entities to stable execution identities.
5. Agent 模型回合在 Tool 调用前停止：`node_turn_provider_error:...:provider_error`。该节点没有 planning selection、execution record 或 Gateway receipt。 / The Agent model turn stopped before Tool invocation, leaving no planning selection, execution record, or Gateway receipt for that node.
6. 旧 Core 把任务置为 `awaiting_replan`，LongHorizon loop 返回；这正是错误的恢复所有权转移。 / The old Core moved the task to `awaiting_replan` and the LongHorizon loop returned; that was the incorrect recovery-ownership transfer.

## 失败分层 / Failure Taxonomy

| 层级 / Layer | 权威证据 / Authority | 正确恢复 / Correct recovery |
|---|---|---|
| Agent 模型回合 / Agent model turn | 无 selection、无 Tool record、无 Gateway receipt / no selection, Tool record, or Gateway receipt | 同 revision、同 node 受限重试 / bounded same-revision, same-node retry |
| Query provider | 已有 Query execution record 和结构化 provider error / Query record and structured provider error exist | Runtime readiness 或 Query recovery policy / Runtime-readiness or Query recovery policy |
| Action/Session transport | 已有 invocation，结果可能未知 / invocation exists and outcome may be unknown | 只读对账，禁止重放 / read-only reconciliation, no replay |
| 物理/语义后置条件 | Action settlement 和新场景证据 / Action settlement and new-scene evidence | 保留效果、刷新场景、重规划剩余后缀 / preserve effects, refresh scene, replan remaining suffix |

`provider_error` 字符串本身不能决定恢复方式；决定权来自失败发生在哪个所有权边界，以及 selection、execution record、invocation 和 world-change settlement 是否存在。

The `provider_error` string alone cannot select recovery. Recovery is determined by the ownership boundary where the failure occurred and by whether a selection, execution record, invocation, or world-change settlement exists.

## 历史效果与当前场景边界 / Historical Effects vs. Current Scene

可以继承 / May be carried as bounded historical context:

- 已完成节点和不可变 settlement； / completed nodes and immutable settlements;
- Action invocation identity 与权威终态； / Action invocation identity and authoritative terminal outcome;
- 稳定执行实体身份； / stable execution identity;
- 目标引用作为“已执行事实”； / destination reference as a fact of the completed execution;
- source/new scene revision、释放、退避、clear、observation-ready 和 recommended action。 / source/new scene revisions and release, retreat, clearance, observation-ready, and recommended-action facts.

不能继承 / Must not be carried as current-scene truth:

- 旧视觉 `entity_ref`； / old visual `entity_ref`;
- 旧 `binding_ref`； / old `binding_ref`;
- 旧几何、位姿、transform 或 calibration lineage； / old geometry, poses, transforms, or calibration lineage;
- 将 Action success 当成最终视觉位置验证。 / treating Action success as final visual-position verification.

因此恢复节点获得 `completed_effect_context` 来理解已完成阶段并禁止重放，但当前 scene binding 仍必须来自新观察/理解。视觉实体编号在世界变化后可以重分配，不能用旧编号覆盖当前证据。

The recovered node therefore receives `completed_effect_context` to understand completed stages and prohibit replay, while current scene binding must still come from new observation and understanding. Visual entity identifiers may be reassigned after a world change and must never override current evidence.

## PAOS 所有权设计 / PAOS Ownership Design

- `AgentLoopNodeExecutor` 只分类模型回合结果；不修改任务状态。 / `AgentLoopNodeExecutor` classifies the model-turn result and does not own task state.
- `PlanningLoopAdapter` 将 pre-Tool `NodeTurnProviderError` 交给 Coordinator。 / `PlanningLoopAdapter` hands pre-Tool `NodeTurnProviderError` to the Coordinator.
- `AgentTaskCoordinator` 持久化 block、重试次数、scene identity 和释放事件，并在同一 SQLite 事务中复核 node/Tool/settlement 所有权。 / `AgentTaskCoordinator` persists the block, retry count, scene identity, and release events and rechecks node, Tool, and settlement ownership in one SQLite transaction.
- `LongHorizonTaskController` 只在 bounded delay 后请求 Coordinator 释放同一节点；不调用 Tool、不重放 Action。 / `LongHorizonTaskController` asks the Coordinator to release the same node after a bounded delay; it invokes no Tool and replays no Action.
- `NodeContextProvider` 从既有 `(revision_id, node_id, invocation_id)` 关系投影 bounded Action effect；不建立平行世界状态。 / `NodeContextProvider` projects bounded Action effects from existing `(revision_id, node_id, invocation_id)` relations and creates no parallel world state.
- Prompt visibility 在 provider wait 期间隐藏 planning selection 和 Tool invocation，只允许通用任务/上下文读取。 / Prompt visibility hides planning selection and Tool invocation during provider wait and permits only generic task/context reads.

该设计复用现有 task 主键、revision 主键、node identity、invocation identity、事务和普通测试。没有新增 hash、baseline、冻结 contract 或 RGB 专用 gate。

This design reuses existing task, revision, node, and invocation identities, transactions, and ordinary tests. It adds no hash, baseline, frozen contract, or RGB-specific gate.

## 恢复状态机 / Recovery State Machine

```text
node model turn
  | provider failure before selection/Tool record
  v
waiting_for_agent_provider
  |-- same scene + retry budget --> executing, same revision/node
  |-- same scene + budget exhausted --> persisted wait for operator resume
  |-- scene changed --> awaiting_replan
  |-- pause/cancel --> preserve requested lifecycle

completed Action settlement --------------------> immutable, never replayed
Query provider failure -------------------------> existing Query recovery path
unknown Action/Session -------------------------> existing reconciliation path
```

默认自动恢复最多 `max_agent_provider_retries` 次，间隔由 `agent_provider_retry_delay_s` 配置。预算耗尽后任务返回持久化等待，而不是无限 `thinking`。operator resume 只授权一次后续释放尝试；真实 runner 仍需重新读取可信 scene identity。

Automatic recovery is limited by `max_agent_provider_retries`, with delay configured by `agent_provider_retry_delay_s`. Exhaustion returns a persisted wait instead of infinite thinking. Operator resume authorizes a later release attempt; the real runner must still read a trusted scene identity.

## 七维审查 / Seven-Dimension Review

1. **Architecture**：状态归 Coordinator，轮询归 LongHorizon，模型错误分类归 node executor，效果投影归 context provider；无旁路 Runtime 或任务专用分支。 / Ownership stays with the established Coordinator, LongHorizon, node-executor, and context-provider boundaries; no parallel Runtime or task-specific branch.
2. **Correctness**：同 scene 保持 revision/node；scene 改变才 replan；completed effect 以 revision/node/invocation 三元组匹配。 / Same-scene recovery preserves revision/node; only scene change replans; completed effects match by revision/node/invocation.
3. **Errors and observability**：持久化 bounded failure code、attempt、scene 和 release/invalidation event；不保存 prompt、原始异常或 provider payload。 / Persist bounded failure code, attempt, scene, and release/invalidation events without prompts, raw exceptions, or provider payloads.
4. **Recovery and idempotency**：Coordinator 在事务内重验无 settlement、无 Tool record、无未结执行；legacy 迁移只接受最新 provider block 和已完成同场景前驱。 / The Coordinator transactionally rechecks the absence of settlement, Tool record, and unsettled execution; legacy migration requires the latest provider block and completed same-scene predecessors.
5. **Robotics safety**：不改变 motion authorization、Action admission、calibration 或轨迹；已完成/未知 Action 均不重放，scene 变化 fail closed 到 replan。 / Motion authorization, Action admission, calibration, and trajectories are unchanged; completed and unknown Actions are never replayed, and scene change fails closed to replan.
6. **Extension compatibility**：逻辑仅依赖通用 semantics、status、revision、node、invocation 和 scene identity；适用于任意 Skill/Query/Action DAG。 / Logic depends only on generic semantics, status, revision, node, invocation, and scene identity and applies to any Skill/Query/Action DAG.
7. **AgentLoop convergence and maintainability**：bounded retry 后明确进入 executing、awaiting_replan 或 persisted wait；无无限 readiness-transition 等待；配置接入既有 verification config。 / Bounded retry converges to executing, awaiting-replan, or persisted wait; there is no infinite readiness-transition wait, and configuration uses the existing verification config.

审查发现并修复三项 Major：跨 revision effect 丢失/同名节点误配、恢复所有权事务竞争、legacy block 选择和前驱条件过宽。另修复旧 Query settlement 无 `invocation_id` 的兼容性。无 Blocker 或未修复 Major。

The review found and fixed three Major issues: cross-revision effect loss or same-name mismatch, transactional recovery-ownership races, and over-broad legacy block/predecessor selection. It also fixed compatibility with older Query settlements without `invocation_id`. No Blocker or unresolved Major remains.

## 验证与安全边界 / Validation and Safety Boundary

- Ruff、`compileall` 和 `git diff --check`。 / Ruff, `compileall`, and `git diff --check`.
- Core planning/LongHorizon/AgentLoop 定向回归。 / Focused Core planning, LongHorizon, and AgentLoop regressions.
- 包含 pick-place planning、continuation 和 unknown-Action recovery 的广泛 no-motion suite。 / Broader no-motion suite including pick-place planning, continuation, and unknown-Action recovery.
- 验证未启动 Runtime、未创建 AgentTask、未调用 Gateway Query/Action、未读取相机、未推进 simulator、未执行物理运动。 / Validation starts no Runtime, creates no AgentTask, invokes no Gateway Query/Action, reads no camera, advances no simulator, and performs no physical motion.

本次实现尚未部署到运行中的 Runtime。部署必须在用户另行授权后执行旧 Runtime 停止、editable Core 刷新和新 Runtime 启动。

This implementation has not been deployed to the running Runtime. Deployment requires separate user authorization to stop the old Runtime, refresh the editable Core, and start the new Runtime.
