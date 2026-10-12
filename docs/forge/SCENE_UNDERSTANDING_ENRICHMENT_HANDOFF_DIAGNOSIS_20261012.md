# Scene-understanding enrichment handoff diagnosis / 场景理解 enrichment handoff 诊断

## Scope / 范围

This record diagnoses `task_f08b2e6093f246cb`, revision
`revision_6cd8b2db652243a3`, without invoking a Runtime Tool, reading a camera,
or changing task state. The repair is provider- and workflow-neutral; it does
not name RGB, colors, blocks, or a Skill node.

本记录诊断 `task_f08b2e6093f246cb`（revision
`revision_6cd8b2db652243a3`），未调用 Runtime Tool、未读取相机、未修改任务状态。
修复与 provider 和工作流无关，不包含 RGB、颜色、方块或 Skill 节点专用分支。

## Authoritative failure chain / 权威失败链

- The read-only observation was fresh (`116 ms`) and synchronized (`0 ms` skew).
- Qwen primary returned HTTP success but violated the semantic contract
  (`contract_output`).
- GPT fallback returned a valid semantic result.
- Proposal enrichment then failed with a `ProcessWorkerError` in the
  `enrichment/proposal` stage while the primary lifecycle still held its GPU
  residency. The primary slept about four seconds later.
- The adapter projected the enrichment failure as `retryable=false`; Core
  consequently settled the Query as `understanding_provider_error` and stopped
  the task, despite completed Action facts being authoritative.

- 双视角观察新鲜（`116 ms`）且同步偏差为 `0 ms`。
- Qwen 主路由 HTTP 成功但语义输出违反 contract（`contract_output`）。
- GPT fallback 已返回合法语义结果。
- 随后的 proposal enrichment 在 primary lifecycle 仍占用 GPU 时出现
  `ProcessWorkerError`；primary 约四秒后才进入 sleep。
- Adapter 将 enrichment failure 投影为 `retryable=false`，Core 因此把 Query
  结算为 `understanding_provider_error` 并终止任务，尽管此前 Action 事实已权威完成。

## Architectural root cause / 架构根因

1. `FallbackSceneUnderstandingInference` keyed primary release on the final
   semantic route. A successful fallback therefore skipped release of an
   attempted primary provider.
2. Enrichment worker lifecycle errors were collapsed into a non-retryable
   failure. The nested provider `retryable` fact was not projected into the
   planning result's `retryable_in_revision` field.
3. The AgentLoop had no generic bounded same-revision Query retry seam, so a
   transient read-only failure could terminate the whole Action-plus-Query
   chain.

1. `FallbackSceneUnderstandingInference` 依据最终语义 route 判断释放；fallback 成功时
   反而跳过了已经尝试的 primary provider 释放。
2. Enrichment worker 生命周期错误被压扁为不可重试；嵌套 provider `retryable` 事实没有
   投影到 planning result 的 `retryable_in_revision`。
3. AgentLoop 缺少通用的同 revision Query 有界重试 seam，瞬态只读失败可能终止整个
   Action + Query 链。

## Implemented generic repair / 已实施的通用修复

- Track primary-attempted state per inference call. Handoff releases the
  primary whenever it was attempted, independent of the final route. If
  fallback already produced semantics, a handoff failure is surfaced without
  running fallback a second time.
- Classify worker timeout/termination/resource/transport errors as retryable;
  protocol-limit and semantic contract errors remain fail-closed.
- Normalize nested Query error retryability at the existing facts projection
  seam. Coordinator authorizes at most the configured
  `max_query_provider_retries` (default `2`) and excludes released attempts
  from effective planning records while retaining append-only, transactionally
  counted `query_retry_decided` audit events.
- Retry is eligible only for a Query with `failure_stage` provider/enrichment,
  explicit retryable `true`, and `world_change_started=false`. Action and
  Session records cannot enter this path. Once the budget is exhausted, the
  existing settlement/recovery policy owns the result.

- 每次 inference 记录本轮 primary 是否被尝试；无论最终 route，都释放已尝试的 primary。
  fallback 已产生语义后 handoff 失败只报告失败，不再次调用 fallback。
- worker timeout/termination/resource/transport 错误可重试；protocol-limit 和语义
  contract 错误继续 fail-closed。
- 在既有 facts projection seam 归一化 Query 嵌套 retryability。Coordinator 使用
  `max_query_provider_retries`（默认 `2`）有界授权，并从 effective planning records
  排除已释放失败记录，同时保留 append-only 审计事件。
- 只有 `failure_stage` 为 provider/enrichment、明确 `retryable=true` 且
  `world_change_started=false` 的 Query 可进入路径；Action/Session 不可进入。预算用尽后
  仍由既有 settlement/recovery policy 决定结果。

## Safety and convergence boundary / 安全与收敛边界

The repair never retries an Action, never infers possession or geometry, never
changes motion authorization, and never substitutes old scene evidence for a
new scene. The completed Action prefix remains settled; only a failed,
read-only Query may be retried. Repeated transient failure is bounded and
terminal/recovery semantics remain fail-closed.

本修复不会重试 Action，不推断持有或几何，不改变运动授权，也不会用旧场景证据替代新
场景。已完成 Action 前缀保持 settlement；只有失败的只读 Query 可以重试。重复瞬态失败
有界，终态/恢复语义继续 fail-closed。

## Verification / 验证

No-motion focused validation passed:

```text
447 passed  (provider fallback, perception, planning/recovery and config suites)
874 passed, 10 failed  (root tests; the same 10 failures reproduce at clean bb698ee7)
```

The tests did not start Runtime, create AgentTasks, invoke Gateway Query/Action,
read sensors, advance a simulator, or move hardware.

The ten root-suite failures are pre-existing projection-fixture/source-scope
expectations in `test_action_selection_projection.py`,
`test_multi_source_projection.py`, `test_plan_proposal_bindings.py`, and
`test_planning_selection.py`. They reproduce unchanged on the clean comparison
commit and are not caused by this repair.

全程 no-motion；测试未启动 Runtime、未创建 AgentTask、未调用 Gateway Query/Action、未读取
传感器、未推进 simulator、未执行硬件运动。

root suite 的 10 个失败来自既有 projection fixture/source-scope 预期，且在干净对照提交
`bb698ee7` 上完全复现；它们不由本修复引入。
