# Unknown World Reconciliation Diagnosis / 未知世界对账诊断

## Scope / 范围

This diagnosis covers the three recent AgentTask attempts that reused the
Runtime scene after an uncertain world-changing Action. It is intentionally
task-, object-, color-, and provider-neutral. No Query or Action was issued
while collecting this diagnosis.

本诊断覆盖最近三个在世界变化不确定后继续复用 Runtime 场景的 AgentTask。
诊断与任务、对象、颜色和 provider 无关；取证过程中未发起 Query 或 Action。

## Evidence / 证据

1. `task_6b93cd454ca34add` reached `object.acquire` with `status=unknown`,
   `world_change_started=true`, `outcome_known=false`, `requires_replan=true`,
   and `recommended_action=reconcile_world`. The result created a new scene
   revision with incomplete effects. Recovery then fell back to the model,
   which returned no unique decision, and the task became terminal `failed`.
2. `task_e06bb6f79c994a76` and `task_6934c57c29494114` observed the same
   post-change scene. Their understanding evidence did not contain all task
   entities, and `scene.bind` correctly returned
   `grounding_unavailable` because the scene was not stable. The latter also
   repeated understanding against unchanged evidence.

## Root causes / 根因

### A. Refresh capability projection dropped the deterministic path

The real `scene.observe` ToolSpec declared both `scene.observe` and auxiliary
`task.verify` capabilities. The old projection unioned capabilities and
required one total capability, returned `None`, and incorrectly invoked model
recovery. The model decision was not the source of truth for a mandatory fresh
scene Query.

### B. Recovery failure released world ownership too early

`fail_replan` turned a failed proposal into terminal `failed` even when the
same task still held an unknown world-changing settlement. The global
non-terminal task constraint therefore no longer protected the Runtime scene,
and a new task could start discovery against unresolved possession and scene
state.

### C. Grounding rejection was correct, but not a recovery path

`scene.bind` must reject missing or scene-inconsistent identities. A benchmark
goal cannot synthesize a perception identity, and `motion_authorized=false`
does not indicate a discovery failure. Repeating the same observation or bind
cannot create new evidence.

## Design resolution / 设计修复

- Select a single refresh Tool from `refreshes_scene=true` metadata. When that
  Tool advertises its own `tool_id` plus auxiliary capabilities, use the Tool
  ID. Multiple refresh Tools remain fail-closed and may still require a model
  decision.
- Keep recovery proposal failure in `awaiting_replan` while an
  `outcome_unknown` world-changing settlement or equivalent unknown Action
  fact requires reconciliation. The task remains the Coordinator-owned slot;
  no Action is replayed and no downstream Action is admitted.
- Compute recovery event payload from the post-mutation AgentTask inside the
  SQLite transaction. This keeps audit status aligned with the persisted
  lifecycle under concurrent changes.
- Let explicit operator cancellation/stop remain the only way to release a
  task whose world still needs reconciliation. A later fresh scene revision or
  authoritative known settlement can resume the existing task.

## Rejected shortcuts / 不采用的绕过

- Do not infer a missing entity from `task.goal`.
- Do not map robot or support surfaces to a missing object.
- Do not relax `scene.bind`, Action admission, motion authorization, or frame
  freshness requirements.
- Do not add RGB/color/object-count branches, hashes, or speculative gates.

## Validation / 验证

The no-motion suites passed: `255 passed`; Ruff, compileall, and `git diff
--check` passed. Runtime, Gateway Query/Action, camera capture, simulator
advancement, and physical motion were not used.
