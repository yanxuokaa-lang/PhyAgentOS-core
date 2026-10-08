# Scene Bind Stale-Lineage Diagnosis / Scene Bind 过期血缘诊断

## Scope / 范围

This diagnosis covers the two repeated `scene.bind` failures after the latest
action-driven scene revision. It is provider-neutral and does not encode the
RGB benchmark, object colors, ordering, camera names, or a fixed arm.

本诊断覆盖最近两次动作驱动场景版本变化后的 `scene.bind` 失败。诊断基于
provider-neutral 的场景血缘，不编码 RGB benchmark、颜色、排列、相机名称或固定机械臂。

## Evidence Chain / 证据链

- Task: `task_a582c54dd1b54462`
- Revision: `revision_6177fe4fc0d64e1b`
- Previous place invocation: `invocation://object-place/dfe2fed0a6544411`
- Runtime result: `status=unknown`, `world_change_started=true`,
  `requires_replan=true`, `recommended_action=reconcile_world`,
  `new_scene_revision=f89206a95b74495c8e201b0915d2ab1e-3`.
- The two bind attempts referenced the pre-action identity revision
  `f89206a95b74495c8e201b0915d2ab1e-1`.
- `Grounding._current()` read the Runtime snapshot and rejected the mismatch
  with `grounding requires the current stable action-driven scene`.
- The endpoint mapped that fact to `grounding_unavailable`, losing the expected
  and actual lineage values at the Core boundary.

The same causal chain occurred twice:

```text
action changed world
  -> Runtime advanced scene revision
  -> old observation/binding was submitted again
  -> grounding rejected stale lineage
  -> no new observation record was produced
  -> discovery repeated the same request
```

## Ownership Boundary / 所有权边界

- Adapter/Runtime owns the authoritative current-scene snapshot and must
  reject stale bindings fail-closed. It reports facts, expected/actual lineage,
  and a recovery recommendation; it does not observe or bind on behalf of the
  Agent.
- Coordinator/Core owns task-bound records, binding admission, and revision
  lineage. It must not replace an old revision with the current one silently.
- AgentLoop owns the decision to request fresh observation/understanding and
  the decision to replan. It must not auto-invoke a Tool or retry an unknown
  Action.

## Required Contract / 所需契约

The rejection remains a failure, but its structured payload includes:

```json
{
  "code": "scene_revision_mismatch",
  "failure_stage": "current_scene",
  "retryable": true,
  "recommended_action": "refresh_declared_evidence",
  "requires_replan": true,
  "expected_scene_revision": "...-1",
  "actual_scene_revision": "...-3"
}
```

The contract is generic for any action-driven scene and any binding consumer.
It does not authorize an automatic refresh; the Agent must choose the next
legal evidence-producing node.

## Safety and No-Motion Boundary / 安全与无运动边界

- No Action is retried from this diagnosis.
- No simulator, hardware, or Gateway invocation is started by the fix.
- A stale binding remains fail-closed until fresh declared evidence establishes
  a new lineage.
- Existing unknown-action reconciliation remains authoritative before any new
  manipulation is considered.

## Acceptance Baseline / 验收基线

1. Adapter returns structured expected/actual lineage on mismatch.
2. The same stale selection cannot create a new binding artifact.
3. Core can distinguish Tool readiness from lineage freshness.
4. No RGB/colour/order/camera-specific branch exists.
5. Focused adapter and Core tests run with fake records only.
