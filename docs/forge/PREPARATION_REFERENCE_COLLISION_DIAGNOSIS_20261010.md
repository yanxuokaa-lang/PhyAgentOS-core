# Preparation Reference Collision Diagnosis - 2026-10-10

## 结论 / Conclusion

最近三次任务没有提交物理 Action：一次在 `red_acquire` 的 selection 无进展处被取消，两次在 `red_prepare` 的 Runtime Query 处失败。两次 preparation 失败的共同底层错误是 `preparation reference already identifies different geometry`；不是抓取失败、不是动作终态，也不是 Agent 手工填写了错误目标。

The latest three tasks did not submit a physical Action: one was cancelled at `red_acquire` after selection made no progress, and two failed in the Runtime Query at `red_prepare`. The two preparation failures share the lower-level error `preparation reference already identifies different geometry`; this was neither a grasp failure nor an Action terminal result, and the Agent did not hand-author a wrong destination.

## 证据 / Evidence

| Task | Terminal state | Authoritative boundary | Evidence |
| --- | --- | --- | --- |
| `task_f28ee6b978f94790` | `cancelled` | `red_acquire: node_selection_no_progress` | preparation and grasp Query facts existed; no physical Action record |
| `task_09dfea7a4e174bbc` | `failed` | `red_prepare` | `status=unavailable`, `error.code=preparation_provider_error`, `failure_owner=runtime_adapter`, `retryable_in_revision=false`, `requires_replan=false`, `simulator_steps=0` |
| `task_ac88e0b7a47f4599` | `failed` | `red_prepare` | same structured error and same lower-level geometry collision; `simulator_steps=0` |

The two Runtime artifacts were:

- `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/preparation-metrics/e9c65f51d54742329e0c8c554d2a49f0.json`
- `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/preparation-metrics/22c00f000fd94eb0869d56523d684ce5.json`

The corresponding task records were:

- `assignments/task_09dfea7a4e174bbc/revision_05786dd5b5a54da2/red_prepare.json`
- `assignments/task_ac88e0b7a47f4599/revision_d9ab78bb6b864983/red_prepare.json`

## 根因 / Root Cause

`manipulation.prepare` previously generated `preparation://{scene_revision}/{frame_id}`. The RobotWin Adapter indexed executable routes by `(preparation_ref, candidate_ref)`. Independent AgentTasks can legitimately observe the same scene revision and frame while carrying different task/revision/node intent, calibration lineage, or route geometry. The second registration then correctly refused to overwrite the first geometry, but the public error was only discovered after expensive no-motion preparation.

`manipulation.prepare` now uses the existing Coordinator-validated intent identity when a route is being materialized:

```text
preparation://{scene_revision}/{task_id}/{revision_id}/{node_id}/{frame_id}
```

Pure provider-only preparation requests without an executable intent retain the historical `preparation://{scene_revision}/{frame_id}` form. This does not authorize motion or make a provider result executable by itself.

## 七维审查 / Seven-Dimension Review

1. **架构归属 / Architecture**: identity construction lives in the provider-neutral Core contract; the RobotWin Adapter reuses it and remains the sole route-geometry owner. No second recovery or execution loop was introduced.
2. **正确性 / Correctness**: same task/revision/node/candidate remains idempotent; independent task scopes no longer collide; same scoped reference with changed geometry still fails closed instead of overwriting.
3. **状态与数据一致性 / Consistency**: acquire and place validate the preparation reference against the source observation scene component, while preserving existing candidate/entity, assignment, acquisition, and destination checks.
4. **恢复与幂等 / Recovery and idempotency**: the Runtime identity is stable across re-entry, so a repeated Query does not create a new route identity or duplicate geometry; an old route cannot be silently rebound to a new task.
5. **Robotics safety**: preparation remains Query-only with `motion_authorized=false`; no Action replay, route bypass, readiness relaxation, simulator step, camera read, or hardware IO was used during validation.
6. **扩展兼容 / Extension compatibility**: no RGB, color, arrangement, object class, camera, provider, or Tool-ID branch was added. The generic URI contract remains valid for other Skills and older no-intent Query callers.
7. **AgentLoop 与可观测性 / AgentLoop and observability**: `node_selection_no_progress` remains fail-closed. Repeated corrective turns with no new Coordinator facts are blocked rather than treated as progress or used to authorize an Action; the preparation collision now reports a scoped, auditable Runtime identity boundary.

## 修改边界 / Repair Boundary

- `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py` owns `preparation_ref_for_request()` and applies it at the public Query boundary.
- `examples/forge-adapters/robotwin20/.../persistent_preparation.py` uses the same helper before registering route geometry.
- `object_acquire.py` and `object_place.py` accept task-scoped preparation references only when their source scene and terminal frame components match the immutable observation lineage.
- No hash, new release gate, physical motion shortcut, or task-specific exception was added. Existing primary keys, assignment artifacts, route digest checks, and ordinary tests remain the integrity controls for geometry.

## 验证边界 / Validation Boundary

- Targeted Core/Skill/Adapter suite: `133 passed`.
- Planning/AgentLoop/context/foundation suite: `322 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- No live AgentTask was created or resumed; no Gateway Query/Action, Runtime start, camera read, simulator step, or physical movement was performed in this repair.

## Follow-up Review / 后续复审（v13.1.5）

The seven-dimension review found one Major boundary gap in the first repair:
`object.acquire` and `object.place` checked the preparation reference's scene
component but accepted a task-scoped preparation whose terminal frame differed
from the request's `frame_id`. That could reuse geometry from another
observation lineage within the same scene revision.

The fix is provider-neutral and narrow. Both Action validators now require the
preparation URI scene component and terminal frame component to match the
immutable source observation. Legacy `preparation://scene/frame` references
and Runtime-owned task-scoped references remain supported. The existing
candidate/entity, calibration, assignment, readiness, Gateway admission, and
motion authorization gates are unchanged.

Regression evidence:

- A task-scoped preparation with `camera_front` is accepted for a
  `camera_front` observation.
- A task-scoped preparation with `camera_side` is rejected as
  `invalid_preparation_binding` for that same `camera_front` observation.
- The targeted Core/Skill/Adapter suite passes with `134 passed`; Ruff,
  compileall, and `git diff --check` pass.

No Blocker or Major remains after this follow-up. No Runtime, AgentTask,
Gateway invocation, simulator step, camera read, or physical movement was
performed during the review or repair.
