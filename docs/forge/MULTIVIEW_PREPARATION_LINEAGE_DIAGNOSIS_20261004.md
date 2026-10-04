# Multi-view Preparation Lineage Diagnosis / 双视角 Preparation 血缘诊断

## Scope / 范围

This diagnosis is read-only and no-motion. It records the persisted facts from
`task_ff6ef719d8104832` and the owning Adapter boundary. It does not authorize a
Query, Action, simulator step, or physical motion.

本诊断为只读、无运动记录，固定 `task_ff6ef719d8104832` 的持久化事实与 Adapter
所有权边界；不授权 Query、Action、仿真步进或物理运动。

## Persisted event chain / 持久化事件链

1. `scene.observe` record `tool_a6916ad3969e4232` succeeded for one synchronized
   scene revision and returned two views. Each view carried its own
   `observation_ref`, frame, calibration, RGB, depth, and state artifacts.
2. `scene.understand`, `manipulation.capabilities`, `scene.bind`, and `task.goal`
   succeeded in the same task. The benchmark destination remained Coordinator-owned.
3. `red_grasp` persisted a planning selection and `grasp.propose` record
   `tool_d1a13054ed6a4bbb` succeeded with 32 candidates.
4. `red_prepare` persisted and consumed its selection. Runtime returned
   `observed_collision_unavailable: one target mask and complete scene depth are required`
   before any Action.
5. `action_count=0` and `simulator_steps=0`; no grasp or placement occurred.

## Root cause / 根因

`Grounding.scene_facts` selects the target mask by bound entity and then gathers
all top-level depth artifacts. It rejects unless there is exactly one mask and
exactly one depth. A synchronized multi-view observation legitimately contains
multiple depth artifacts, so the count assertion rejects valid evidence.

The binding already provides the correct selection key: current observation
identity, `frame_id`, and `calibration_ref`. The observation `views` collection
provides per-view identity and artifacts. The Adapter must select exactly one
view matching that lineage and then select exactly one depth artifact from that
view. Missing, duplicate, or mismatched lineage remains unavailable.

`Grounding.scene_facts` 已按绑定实体选择目标 mask，却从 observation 顶层收集全部 depth，
并要求 mask/depth 数量都等于一。同步双视角合法包含多张 depth，因此旧断言必然拒绝。
当前 binding 已提供 observation identity、`frame_id`、`calibration_ref`，observation 的
`views` 又提供逐视角身份和工件；Adapter 应据此唯一选择 view 及其唯一 depth。缺失、重复
或血缘不一致仍应 fail-closed。

## Ownership and extension boundary / 所有权与扩展边界

- Scene observation owns view artifacts and calibration provenance.
- Scene binding owns the execution entity and primary metric frame.
- The Adapter owns conversion of those private facts into observed collision input.
- `manipulation.prepare` does not expose mask/depth arguments; the Agent must not
  assemble private Runtime inputs.
- No concrete sensor ID, task color, benchmark name, or layout may participate in
  selection. Future fused geometry must be published as one explicit fused artifact
  by perception, not inferred by the Agent.

## Acceptance / 验收

- A synchronized observation with at least two views reaches `scene_facts` and
  selects the depth sharing the binding frame/calibration lineage.
- A duplicate or missing matching view/depth is rejected with
  `observed_collision_unavailable`.
- Single-view observations retain existing behavior.
- Tests remain no-motion and do not call Gateway Action routes.
