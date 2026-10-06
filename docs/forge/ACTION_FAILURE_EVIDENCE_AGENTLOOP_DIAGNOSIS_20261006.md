# Action Failure Evidence and AgentLoop Diagnosis / Action 失败证据与 AgentLoop 诊断

## Scope / 范围

本诊断记录 Action 失败被压缩成 `SimulationProbeError`、零动作结果却声明实体变化、以及 AgentLoop 无法获得足够结构化事实的问题。它与路线计划一致性诊断分离：前者解决“谁产生和消费路线计划”，本诊断解决“失败如何归属、持久化和驱动下一步决策”。

This diagnosis covers the generic `SimulationProbeError`, misleading zero-step entity-change claims, and insufficient structured facts for the AgentLoop. It is separate from route-plan ownership: that diagnosis defines who produces and consumes plans; this one defines failure ownership, persistence, and next-step decision facts.

## Observed Failure / 已观察失败

The Action artifact reported:

```json
{
  "status": "failed",
  "failure_code": "SimulationProbeError",
  "failure_owner": "execution",
  "world_change_started": false,
  "simulator_steps": 0,
  "phase": "acquire",
  "error_detail": "no arm can plan complete candidate route",
  "scene_effects": {
    "changed_entity_refs": ["entity://e1"],
    "new_scene_revision": null,
    "carry_forward_authorized": false
  }
}
```

The `changed_entity_refs` value is inconsistent with `world_change_started=false` and `simulator_steps=0`. Although `carry_forward_authorized=false` prevented unsafe continuation, the public record could mislead a planner into refreshing or reconciling the wrong physical effect.

`changed_entity_refs` 与 `world_change_started=false`、`simulator_steps=0` 不一致。虽然 `carry_forward_authorized=false` 阻止了不安全续接，但公共记录可能误导 Agent 去刷新或对账一个并不存在的物理效果。

## Failure Taxonomy / 失败分类

- `preflight_divergence`: input/scene/world/assignment/start-state binding changed before any motion; retryable in the same revision is false; Agent may refresh or replan only when its policy permits.
- `route_planning_failure`: the prepared plan was missing or invalid, or execution-side plan validation failed before motion; owner is `readiness` or `execution` according to the failing boundary; no automatic retry.
- `execution_failure`: a controller/simulator phase failed after the first simulator step; evidence must include phase, selected arm, step count, stop result, and reconciliation requirement.
- `evidence_failure`: physical phase completed but video/receipt persistence failed; outcome must remain known only when the Runtime proves it, and reconciliation remains explicit.

- `preflight_divergence`：动作前 input/scene/world/assignment/起始状态绑定发生变化；本 revision 不可直接重试；Agent 可按策略刷新或 replan。
- `route_planning_failure`：prepared plan 缺失/非法，或执行侧计划校验在动作前失败；根据边界归属 readiness 或 execution；不自动重试。
- `execution_failure`：首次 simulator step 后控制器/仿真阶段失败；必须记录 phase、selected arm、step count、stop 结果和 reconciliation 要求。
- `evidence_failure`：物理阶段完成但视频/receipt 持久化失败；只有 Runtime 能证明时才确认结果，且必须显式 reconciliation。

## AgentLoop Contract / AgentLoop 契约

Every terminal Action result must expose `failure_owner`, `failure_code`, `retryable_in_revision`, `requires_replan`, `recommended_action`, `phase`, `selected_arm`, `failed_phase`, and `evidence_refs`. The loop treats a repeated unchanged failure fingerprint as no progress and stops or requests operator intervention; it never infers recovery from `SimulationProbeError` text and never issues an unbounded Action retry.

每个终态 Action 结果必须公开 `failure_owner`、`failure_code`、`retryable_in_revision`、`requires_replan`、`recommended_action`、`phase`、`selected_arm`、`failed_phase` 与 `evidence_refs`。Loop 将重复且事实未变化的失败 fingerprint 视为无进展并停止或请求操作员介入；不解析 `SimulationProbeError` 文本推断恢复，也不进行无界 Action 重试。

## Acceptance / 验收

- Zero-step preflight failure has empty changed entities and explicit `requires_replan` semantics.
- Per-arm attempts and failed phase survive in the persisted Action artifact.
- Post-step execution failure carries stop/reconciliation facts and is not downgraded to a preflight failure.
- AgentLoop tests cover stop, refresh-evidence, and replan decisions from structured fields without hard-coded RGB/task branches.
