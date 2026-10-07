# Outcome-Unknown Reconciliation Diagnosis / 未知结果对账诊断

## Scope / 范围

This diagnosis covers the generic AgentLoop lifecycle after a world-changing Action
settles as `outcome_unknown`. It does not define a pick-place sequence and contains
no RGB, benchmark, object, camera, candidate, or robot-specific branch.

本文覆盖 world-changing Action 以 `outcome_unknown` 结算后的通用 AgentLoop 生命周期，
不定义搬放顺序，也不包含 RGB、benchmark、对象、相机、候选或机器人专用分支。

## Observed Facts / 已观察事实

For `task_e3949a368fad4e3d`:

```text
node                 = red_acquire
settlement           = outcome_unknown
world_change_started = true
outcome_known        = false
stop_confirmed       = true
decision             = stop
invocation           = invocation://object-acquire/d707ac058ab24306
```

The Agent's decision was correct: do not retry the Action, do not advance the
dependent place, do not infer an outcome from video, and reconcile the existing
invocation first. However, `_recover` returned directly inside `decision == stop`
before reaching the existing `outcome_unknown` reconciliation branch. The planning
result remained `outcome_unknown` and the task projection remained `executing`, even
though Runtime ownership correctly retained the unresolved invocation and binding.

## Root Cause / 根因

The defect is control-flow ordering, not Agent reasoning and not missing retries.
Reconciliation is a safety prerequisite that must dominate physical-stop and
execution-replan choices. Previously it dominated only `replan` because its check
appeared after the `stop` return. Reducer replay remains a read-only recomputation
over existing records and does not repeat the Action.

该缺陷是控制流顺序错误，不是 Agent 推理失败，也不是缺少重试。对账是安全前置条件，
必须优先于 Agent 的物理停止和执行 replan 选择；旧代码只对 replan 生效，因为检查位于
stop 的提前返回之后。Reducer replay 仍只是已有记录的只读重算，不会重复 Action。

## PAOS Ownership Resolution / PAOS 所有权修复

1. The Agent remains the recovery decision owner and its decision event is retained.
2. Coordinator settlement truth remains immutable: the node stays `outcome_unknown` until a matching terminal result is appended.
3. AgentLoop projects unknown outcomes as `blocked` with `reconciliation_required:<node>` before stop or execution replan; reducer-only replay remains available.
4. The existing task recovery owner moves the task out of misleading `executing` into `awaiting_replan` with the reconciliation reason.
5. Runtime invocation and task-binding ownership remain active until authoritative reconciliation; no cleanup is inferred from `stop_confirmed` alone.
6. Late known results continue through `record_node_settlement_resolution`; no second invocation or graph is synthesized.

No new state machine, hash, frozen contract, retry daemon, or automatic recovery
executor is introduced. The existing Coordinator event store, settlement reducer,
and blocked-node mechanism are sufficient once the control-flow order is corrected.

## AgentLoop Requirements / AgentLoop 要求

- A model decision cannot bypass an unresolved physical effect.
- Repeated loop turns cannot resend the Action while the invocation is unresolved.
- Replay remains reducer-only and never resends the Action.
- Replan remains Agent-authored and is not entered before reconciliation.
- Observation or scene refresh is not automatically dispatched.
- Dependent nodes remain blocked.
- The loop terminates deterministically with a structured reconciliation reason.

## Required Regression / 必需回归

- Default recovery with an unknown result executes the Action once and returns `blocked`.
- Agent decisions `stop` and `replan` converge to reconciliation first; replay remains reducer-only.
- No replan proposer is called before reconciliation.
- The task leaves `executing`, while the immutable unknown settlement remains available for late resolution.
- Known failures without unresolved ownership retain their existing stop/fail semantics.
