# Held entity projection diagnosis / 持有实体投影诊断

## Evidence and stage / 证据与进行阶段

Task `task_27ae6821f50643f9`, revision `revision_f6529405127d43db`, stopped at
`red_acquired_bind` with `node_selection_no_progress`. The authoritative records
show that acquisition, post-acquisition observation, capability refresh, and
understanding had already succeeded. No selection or execution record exists
for the bind node. Placement had not started in this sequence.

任务停在“抓取后重新绑定”阶段。抓取并非失败，也没有调用放置；绑定节点没有 selection、
rejection 或 execution record，不能将本次错误归为绑定参数错误或 provider 拒绝。

The persisted snapshot is [HELD_ENTITY_DIAGNOSTIC_SNAPSHOT_20261009.json](HELD_ENTITY_DIAGNOSTIC_SNAPSHOT_20261009.json).
It was extracted read-only from the task SQLite database on 2026-10-09. The
original CLI reported `blocked`; the database now reports `failed`, updated at
`2026-10-09T01:07:53.227170Z`. The later task status does not rewrite the earlier
successful Action terminal result. This repair does not mutate that task.

原 CLI 的 `blocked` 是当时 loop 的停止结果；本次读取数据库已为 `failed`，不能把二者
混同，也不能因此把成功的抓取追溯改为失败。诊断过程未恢复或重试旧任务。

| Node / 节点 | Record / 记录 | Authoritative result / 权威结果 |
| --- | --- | --- |
| `red_acquire` | `tool_ad32f7025b414a49` | succeeded, outcome_known=true |
| `red_acquired_observe` | `tool_d85aad197cd44a7d` | available |
| `red_acquired_capabilities` | `tool_fecc1009ca064139` | available |
| `red_acquired_understand` | `tool_366ef0847c0948b7` | available, held identity missing |
| `red_acquired_bind` | none / 无 | selection count=0 |

Acquisition invocation: `invocation://object-acquire/c7e09749373548d2`.
Scene revision advanced from `7b0f5684bd5a4cdaa40dcc6eef4f6c7a-1` to `...-2`.
The Action effect record lists all three bound entities in `changed_entity_refs`,
not just the acquired entity; `unaffected_entity_refs=[]`,
`effect_scope_complete=true`, and `carry_forward_authorized=false`.
That classification does not establish why the other two entities changed.

抓取后的理解将 `entity://e1` 解释成 `white and black robot`，并将其列入遮挡相关身份歧义；
旧理解中的同一个字符串代表被抓取物体。视觉 provider 的 observation-local ID
并不是跨场景的物理身份凭证。

## Root cause / 根因

There are four connected gaps:

1. The engine has a verified successful acquisition, and the persistent provider
   owns possession state, owner, entity, and acquisition invocation. The existing
   scene-effects receipt had no independent representation of the held entity.
2. `_coordinator_carried_entities()` intentionally selected only Runtime-proven
   unchanged entities. A legitimately moved, held entity could not use that
   path, so no held identity reached post-acquisition understanding.
3. A new visual snapshot reused the old entity ID for a robot. Simply appending
   the old claim would either drop the held object due to duplicate-ID handling,
   or attach robot geometry/ambiguity to the held object.
4. Grounding treated every carried object as unchanged and required identical
   old/new execution poses. Adding a held claim alone would therefore fail at
   the next layer. Injecting it only immediately before execution would also
   invalidate the already-persisted planning binding.

本次属于“成功动作后的身份连续性 / 契约投影缺失”，区别于动作前探针失败、控制器结果未知、
worker 连接丢失或 `scene.bind_missing_entity_refs`。AgentLoop 在没有合法选择时停止是
正确行为；修复应补全事实链，而不是增加无证据重试、强行跳过绑定或自动推进下一节点。

## Repair and ownership / 修复与职责边界

- Runtime engine emits `scene_effects.held_entity` only for a known successful
  acquisition with complete effects. The persistent provider compares it with
  its settled possession snapshot. Oversized effect records lose held evidence
  when the existing bounded receipt falls back to an incomplete effect summary.
- Coordinator joins the latest known successful Action with prior task-owned
  understanding and binding records. It verifies task owner, entity, acquisition
  invocation, current effect revision, and changed-entity membership, then emits
  `carry_state=held` plus possession. A later unknown Action blocks inheritance.
- Selection receives this Coordinator projection before schema validation,
  digest creation, and persistence. Execution uses the same durable arguments;
  if authoritative carry facts changed, it rejects instead of silently editing
  the bound arguments. Agent-supplied carried entities remain rejected.
- The understanding endpoint keeps Runtime identity outside visual inference.
  A conflicting visual ID is deterministically remapped, including its relations,
  envelopes, artifacts, and ambiguities; the remap is recorded. The original
  visual claim is preserved, and the held entity has no fabricated fresh visual
  localization. Legacy unchanged merge semantics remain compatible.
- Grounding checks current Runtime possession on first binding and cached reuse.
  Held geometry is the old observation-derived model transported by
  `current_world_T_actor @ inverse(source_world_T_actor)`. Existing visual
  dimensions and functional-frame offsets are retained. Unchanged entities
  still require pose stability. Both paths return `motion_authorized=false`.

Runtime 证明当前持有；Coordinator 负责 task-owned 身份投影；视觉 provider 只理解当前
观察；Adapter 负责执行身份与几何变换；AgentLoop 继续决定观察、选参、绑定和后续动作。
实现不含颜色、排列、对象数量、固定相机、固定机械臂或任务 ID 分支。

Frames and units: old and current execution poses are rigid transforms in world
coordinates, in metres; the source visual model already passed the existing
observation calibration check. Unknown possession, stale scene, missing source
binding, or mismatched ownership stops binding. Existing collision planning,
Action admission, stop controls, and motion authorization remain in force.

## Videos / 视频证据

The manifest and both videos exist on disk. Paths and sizes are preserved in the
JSON snapshot: `head-camera.mp4` is 918627 bytes, `observer-camera.mp4` is 747198
bytes, and `manifest.json` is 1019 bytes. These are acquisition-stage evidence;
their existence is not evidence of placement or complete task success.

## Validation and deployment / 验证与部署

Validation uses fake workers/providers, temporary task stores, and synthetic
rigid transforms. It covers engine artifact emission, receipt truncation,
possession mismatch, Core selection persistence, conflicting visual IDs,
unchanged pose drift, held translation/rotation, and cached-binding checks.
No live Gateway Query/Action, simulator step, or physical motion is used.

This is a source repair. Existing archived tasks and receipts are not upgraded
by inventing possession evidence. Deployment must rebuild the node and Skill
contract together and bind a fresh task to the new published schema. The old
task should not be resumed or its Action repeated merely to test this repair.

本轮未安装、重启或执行完整任务；自动化通过证明修复链路，不代表现场完整任务已成功。
