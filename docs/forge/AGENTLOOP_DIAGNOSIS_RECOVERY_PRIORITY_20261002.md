# AgentLoop recovery priority diagnosis — v12.5.13

## Observed failures / 已确认问题

1. v12.5.12 consumes a persisted selection only on executor entry. A model turn
   that persists a selection and then times out enters another model turn instead
   of consuming the checkpoint. The no-motion reproduction made two model calls,
   zero registry calls, and no execution record before `NodeTurnProviderError`.
   节点内新生成 selection 后仍请求模型；入口恢复未覆盖循环内恢复。
2. The automatic wrapper path raises on an `Error...` string before reading
   durable execution records. A succeeded record plus a later wrapper error
   incorrectly becomes `NodeTurnIncompleteError`; an accepted invocation can
   miss its original status/result reconciliation.
   wrapper 文本错误不应覆盖成功终态或跳过原 invocation 对账。
3. A standalone `grasp.propose` using only an execution alias in `entity_ref`
   does not resolve the unique current `scene.bind` observed identity. Its
   geometry projection then cannot join the observed entity collection.
   单节点抓取缺少后继提示时，同一唯一实体映射没有应用。

## Ownership and repair / 职责与修复

The Agent chooses a semantic next segment, replan, finalize, stop, or clarification
from settled facts. Coordinator owns selection, bindings, execution records, and
settlement. Runtime/Gateway retain physical admission and invocation truth.
Consuming an existing selection is execution recovery, not a new Agent decision.
Agent 根据事实规划；Coordinator 恢复已确定执行；Runtime 保持物理真值与准入。

Use the same recovery path both before a model turn and after it returns:
existing records → original-invocation reconciliation → result; otherwise consume
pending selection through the existing registry and execution guard. Read and
reconcile records before interpreting wrapper text. Without a registry, stop with
an explicit incomplete-node error rather than ask the model to reselect.
模型前后均执行事实优先恢复，已受理动作只查询原 invocation，不创建替代动作。

Apply the existing unique execution-to-observed correspondence to standalone grasp
nodes. Ambiguous correspondence remains unresolved; no color/name heuristic or
provider-specific behavior is introduced. 本次不是 RGB 特例，不添加新门禁。

## Acceptance / 验收

- A selection produced by a successful, failed, or timed-out turn executes once
  without a second model call, even with zero additional model-turn budget.
- Existing terminal records outrank wrapper errors; accepted actions/sessions
  poll their original identity; unknown outcomes never become success or replay.
- Guard rejection with no record remains incomplete and is not blindly retried.
- A single-node grasp resolves a unique alias and can join geometry; ambiguous
  or stale mappings cannot authorize selection.
- Query-only completion remains distinct from placement and post-action refresh.

All checks are local/no-motion. They do not prove grasp, placement, benchmark
acceptance, installed Skill behavior, or hardware safety.

The v12.5.12 review's all-pass conclusion is superseded for these surfaces by
`IMPLEMENTATION_REVIEW_V12_5_13.md`; the historical document is retained.
