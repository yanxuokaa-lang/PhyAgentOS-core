# Changelog

## Archive

- [2026-09 Part 16](changelog/2026-09_part16.md)
- [2026-09 Part 15](changelog/2026-09_part15.md)

- [2026-09 Part 14](changelog/2026-09_part14.md)

- [2026-09 Part 13](changelog/2026-09_part13.md)

- [2026-09 Part 12](changelog/2026-09_part12.md)

- [2026-09 Part 11](changelog/2026-09_part11.md)

- [2026-09 Part 10](changelog/2026-09_part10.md)
- [2026-09 Part 8](changelog/2026-09_part8.md)
- [2026-09 Part 9](changelog/2026-09_part9.md)
- [2026-09 Part 7](changelog/2026-09_part7.md)
- [2026-09 Part 6](changelog/2026-09_part6.md)
- [2026-09 Part 5](changelog/2026-09_part5.md)
- [2026-09 Part 4](changelog/2026-09_part4.md)

## 最近 5 条 / Latest Five Versions

## v11.7.10 (2026-09-25 15:58) - codex

### 预期修改 / Planned Changes [完成实现；全链路验收进行中]
- [policy] [fix] 根据 task_e36fbced0280470b 的失败证据，修复恢复规划返回值的结构解析与可修复校验反馈，保持 Coordinator 对 revision、执行和安全约束的唯一所有权。(local)
- [Policy] [Fix] Repair recovery proposal parsing and actionable validation feedback using task_e36fbced0280470b evidence while retaining Coordinator ownership of revisions, execution and safety constraints. (local)
- [eval] [fix] 在任务创建接口要求显式 verification.mode，阻止空对象意外关闭用户要求的验收；保持底层默认 off 的兼容语义，测试 enforce、off 和错误反馈。(local)
- [Eval] [Fix] Require an explicit verification.mode at the task creation tool to prevent empty objects silently disabling requested acceptance; retain internal default-off compatibility and test enforce, off and repair feedback. (local)
- [policy] [fix] 定位 released-target retreat 碰撞，记录机器人球体、障碍物和间距的无运动诊断；仅在证据定位根因后修复对应 Runtime 几何或路径处理，保留全部碰撞约束。(local)
- [Policy] [Fix] Diagnose released-target retreat collisions without motion using robot spheres, obstacles and clearances; repair the owning Runtime geometry or path handling only after locating the cause, preserving collision constraints. (local)
- [eval] [exp] 修复后执行聚焦回归和捕获场景回放，独立打包安装，使用 enforce 验收与视频留存重新运行 RGB 全链路并保存实际结果。(local)
- [Eval] [Exp] Run focused regressions and captured-scene replay, package and install independently, then rerun RGB end-to-end with enforce verification and retained video, recording actual outcomes. (local)

### 预计影响 / Expected Files
- PhyAgentOS/agent/recovery_decisions.py; PhyAgentOS/agent/tools/forge_task.py; corresponding tests.
- examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py and diagnostic tests; Runtime owner fixes if measured necessary.
- Runtime/Skill packaging metadata; CHANGELOG.md and this archive.

### 根因与补充计划 / Root Cause and Additional Plan
- [policy] [fix] 无运动捕获重放确认：retreat 的其他世界障碍无碰撞；released_target AABB 与右指球体重叠 9.3215 mm，而同一 704 个实测点的凸包与同一球体间隙 4.3126 mm。改用传感器目标凸包的释放到落稳扫掠包络，保留配置中的 1 mm 不确定度及原机器人碰撞球；CuRobo 原生 Mesh 检查继续负责整段退避。预计涉及 robotwin_observed_collision.py、robotwin_curobo_world_port.py、robotwin_simulation_probe_worker.py 及测试。(local)
- [Policy] [Fix] Captured no-motion replay found no other world collision: released_target AABB overlaps the right-finger sphere by 9.3215 mm, while the convex hull of the same 704 measured points clears that sphere by 4.3126 mm. Use the observed target convex hull swept from release to settled pose, retaining the configured 1 mm uncertainty and native robot spheres. CuRobo native mesh collision continues validating the entire retreat. Scope: robotwin_observed_collision.py, robotwin_curobo_world_port.py, robotwin_simulation_probe_worker.py and tests. (local)
- [policy] [fix] CuRobo 已有 Mesh cache；初始化时预留一个释放目标槽，世界替换/回滚时清除旧 Mesh 激活状态并重载完整世界，避免旧释放物体残留。观测路线执行与无运动准入使用同一几何表示，不读取 actor 真值生成规划几何。(local)
- [Policy] [Fix] Reserve one existing CuRobo mesh-cache slot for the released target; clear prior mesh activation during full-world replacement/restoration to avoid stale release obstacles. Observed-route execution and no-motion admission use the same geometry without generating planning geometry from actor truth. (local)

### 实际文件与 Diff / Changed Files and Diffs

#### [修改 / Modified] PhyAgentOS/agent/plan_proposal.py L22-L37

```diff
diff --git a/PhyAgentOS/agent/plan_proposal.py b/PhyAgentOS/agent/plan_proposal.py
index 945e5fb..b13e08e 100644
--- a/PhyAgentOS/agent/plan_proposal.py
+++ b/PhyAgentOS/agent/plan_proposal.py
@@ -22,6 +22,16 @@ from PhyAgentOS.planning import (
     validate_graph,
 )

+RECOVERY_NODE_GUIDANCE = (
+    "retry_of may reference only a node included in this replacement graph; "
+    "use reason and evidence refs for prior-revision history. Do not copy failed "
+    "nodes merely to preserve history. For a recovery Query, omit prior-revision "
+    "retry_of and submit only the recovery work; original execution records remain "
+    "persisted. Action retry admission is unchanged. Materialize only the current "
+    "scene-bound segment, or the next refresh Query when fresh evidence is needed; "
+    "continue after its result instead of inventing future bindings or evidence."
+)
+

 def compile_task_plan(
     task: AgentTaskRecord,
```

#### [修改 / Modified] PhyAgentOS/agent/recovery_decisions.py L5-L11, L22-L28, L62-L68, L74-L80, L110-L134

```diff
diff --git a/PhyAgentOS/agent/recovery_decisions.py b/PhyAgentOS/agent/recovery_decisions.py
index abdf5bf..0f53b95 100644
--- a/PhyAgentOS/agent/recovery_decisions.py
+++ b/PhyAgentOS/agent/recovery_decisions.py
@@ -5,7 +5,7 @@ from __future__ import annotations
 import json

 from PhyAgentOS.agent.experience.redaction import redact_text
-from PhyAgentOS.agent.plan_proposal import compile_task_plan
+from PhyAgentOS.agent.plan_proposal import RECOVERY_NODE_GUIDANCE, compile_task_plan
 from PhyAgentOS.agent.planner_plugin import ReplanProposal
 from PhyAgentOS.agent.planning_facts import response_facts
 from PhyAgentOS.planning import PlanNode
@@ -22,7 +22,7 @@ class AgentRecoveryDecisions:
         self.model = model
         self.coordinator = coordinator

-    async def _ask(self, graph, settlement, delta, context, *, replan=False):
+    async def _ask(self, graph, settlement, delta, context, *, replan=False, repair=None):
         task = self.coordinator.get_task(graph.task_id)
         failed_executions = []
         for record in task.execution_records:
@@ -62,7 +62,7 @@ class AgentRecoveryDecisions:
                     "configuration faults; stop when replanning cannot remedy the reported cause. "
                     "For replanning return the full replacement semantic node list. Preserve only "
                     "the delta's allowed nodes unchanged; refresh stale evidence before actions. "
-                    "Use submit_recovery to return the decision."
+                    + RECOVERY_NODE_GUIDANCE + " Use submit_recovery to return the decision."
                 )},
                 {"role": "user", "content": json.dumps({
                     "goal": task.task_description,
@@ -74,6 +74,7 @@ class AgentRecoveryDecisions:
                     "failed_executions": failed_executions,
                     "delta": delta.model_dump(mode="json"),
                     "context": context.model_dump(mode="json"),
+                    **({"repair": repair} if repair is not None else {}),
                 }, ensure_ascii=False)},
             ],
             tools=[{"type": "function", "function": {
@@ -109,8 +110,25 @@ class AgentRecoveryDecisions:

     async def propose_replan(self, *, graph, settlement, delta, context):
         value = await self._ask(graph, settlement, delta, context, replan=True)
-        task = self.coordinator.get_task(graph.task_id)
-        replacement = compile_task_plan(task, value["nodes"], reason=value["reason"])
+        for attempt in range(2):
+            task = self.coordinator.get_task(graph.task_id)
+            try:
+                replacement = compile_task_plan(task, value["nodes"], reason=value["reason"])
+                break
+            except ValueError as exc:
+                error = redact_text(str(exc))[:4000]
+                self.coordinator.store.update(
+                    graph.task_id, lambda task: None, event_type="agent_replan_proposal_rejected",
+                    payload={"revision_id": graph.revision_id, "node_id": settlement.node_id,
+                             "attempt": attempt + 1, "error": error},
+                )
+                if attempt == 1:
+                    raise
+                value = await self._ask(
+                    graph, settlement, delta, context, replan=True,
+                    repair={"rejected_proposal": value, "validation_error": error,
+                            "instruction": "Correct the rejected semantic proposal. No Tool was executed."},
+                )
         return ReplanProposal(
             delta=delta, plan_graph=replacement,
             plan_graph_ref=f"artifact://plans/{task.task_id}/{replacement.revision_id}",
```

#### [修改 / Modified] PhyAgentOS/agent/tools/forge_task.py L8-L14, L62-L70, L103-L114, L173-L179, L572-L582, L605-L611

```diff
diff --git a/PhyAgentOS/agent/tools/forge_task.py b/PhyAgentOS/agent/tools/forge_task.py
index 0331e98..ca58e0c 100644
--- a/PhyAgentOS/agent/tools/forge_task.py
+++ b/PhyAgentOS/agent/tools/forge_task.py
@@ -8,6 +8,7 @@ from collections.abc import Mapping, Sequence
 from enum import Enum
 from typing import Any

+from PhyAgentOS.agent.plan_proposal import RECOVERY_NODE_GUIDANCE
 from PhyAgentOS.agent.tools.base import Tool
 from PhyAgentOS.forge.binding import missing_preplan_queries
 from PhyAgentOS.forge.task import (
@@ -61,7 +62,9 @@ class ForgeTaskCreateTool(Tool):
     def description(self) -> str:
         return (
             "Create the single active AgentTask before a task-bound Forge Tool sequence. "
-            "This records planning and verification context but does not execute the robot."
+            "This records planning and verification context but does not execute the robot. "
+            "Set verification.mode explicitly; requested verification needs enforce, goal "
+            "and success_criteria."
         )

     @property
@@ -100,6 +103,12 @@ class ForgeTaskCreateTool(Tool):
     ) -> str:
         if task_description.strip().casefold() in {"noop", "no-op", "none"}:
             raise ValueError("AgentTask description must state an executable user task")
+        if "mode" not in verification:
+            raise ValueError(
+                "verification.mode must be explicit: use enforce with goal and "
+                "success_criteria when the user requests verification; use off only "
+                "when verification is intentionally disabled"
+            )
         try:
             task = self.coordinator.create_task(
                 task_description=task_description,
@@ -164,11 +173,7 @@ class ForgeTaskBeginRevisionTool(Tool):
             "replanning. Supply semantic nodes for a model-directed recovery; PAOS compiles "
             "revision IDs and integrity metadata. A complete plan_graph remains available "
             "for coordinator-owned callers. This call only changes the planning revision and "
-            "never invokes a Tool or motion. retry_of may reference only a node included in "
-            "this replacement graph; use reason and evidence refs for prior-revision history. "
-            "Do not copy failed nodes merely to preserve history. For a recovery Query, "
-            "omit prior-revision retry_of and submit only the recovery work; original "
-            "execution records remain persisted. Action retry admission is unchanged."
+            "never invokes a Tool or motion. " + RECOVERY_NODE_GUIDANCE
         )

     @property
@@ -567,6 +572,11 @@ def _task_id_schema() -> dict[str, Any]:
 def _verification_schema() -> dict[str, Any]:
     return {
         "type": "object",
+        "description": (
+            "Explicit task verification contract. For user-requested verification, "
+            "set mode=enforce and provide goal and success_criteria. An empty object "
+            "does not enable verification."
+        ),
         "properties": {
             "mode": {
                 "type": "string",
@@ -595,6 +605,7 @@ def _verification_schema() -> dict[str, Any]:
                 "additionalProperties": False,
             },
         },
+        "required": ["mode"],
         "additionalProperties": False,
     }

```

#### [修改 / Modified] docs/en/03-developer-manual.md L56-L63

```diff
diff --git a/docs/en/03-developer-manual.md b/docs/en/03-developer-manual.md
index 29169c4..d078f50 100644
--- a/docs/en/03-developer-manual.md
+++ b/docs/en/03-developer-manual.md
@@ -56,6 +56,8 @@ requires `attempt_id`. A timeout leaves an unknown record and recovery never rep

 Task lifecycle:

+Task creation requires an explicit verification.mode. Use enforce with goal and success_criteria for requested outcome verification; use off only when intentionally disabling verification. An empty verification object is rejected before task creation.
+
 - `forge_task_create(task_description, verification, activation_id)`;
 - `forge_task_get(task_id)`;
 - `forge_task_begin_revision(task_id, reason)`;
```

#### [修改 / Modified] docs/zh/03-developer-manual.md L56-L63

```diff
diff --git a/docs/zh/03-developer-manual.md b/docs/zh/03-developer-manual.md
index e717858..f4be4b0 100644
--- a/docs/zh/03-developer-manual.md
+++ b/docs/zh/03-developer-manual.md
@@ -56,6 +56,8 @@ Timeout 形成 unknown record，恢复不会重复 POST。

 Task lifecycle：

+创建工具要求显式提供 verification.mode。用户要求结果验收时使用 enforce，并填写 goal 和 success_criteria；只有明确不需要验收时才使用 off。空 verification 对象会在创建任务前返回可修复错误。
+
 - `forge_task_create(task_description, verification, activation_id)`；
 - `forge_task_get(task_id)`；
 - `forge_task_begin_revision(task_id, reason)`；
```

#### [修改 / Modified] examples/forge-adapters/robotwin20/pyproject.toml L1-L6

```diff
diff --git a/examples/forge-adapters/robotwin20/pyproject.toml b/examples/forge-adapters/robotwin20/pyproject.toml
index 6ea0828..9bcca91 100644
--- a/examples/forge-adapters/robotwin20/pyproject.toml
+++ b/examples/forge-adapters/robotwin20/pyproject.toml
@@ -1,6 +1,6 @@
 [project]
 name = "paos-robotwin20-adapter"
-version = "0.7.11"
+version = "0.7.12"
 description = "PAOS EnvironmentAdapter seam for RoboTwin20 sensor-backed observations."
 requires-python = ">=3.10"
 dependencies = []
```

#### [修改 / Modified] examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py L150-L156, L335-L349, L351-L375, L432-L439, L453-L461, L469-L475

```diff
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py b/examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py
index 2b273f3..3b7b8ff 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py
@@ -150,7 +150,7 @@ def _rebuild_motion_generators(
     common: dict[str, Any] = {
         "interpolation_dt": 1 / 250,
         "num_trajopt_seeds": 1,
-        "collision_cache": {"obb": cache_capacity},
+        "collision_cache": {"obb": cache_capacity, "mesh": 1},
         "use_cuda_graph": bool(getattr(existing, "use_cuda_graph", True)),
     }
     tensor_args = getattr(existing, "tensor_args", None)
@@ -335,7 +335,15 @@ def _world_config(
     return WorldConfig(cuboid=cuboids)


-def add_released_object(planner: Any, pose: Mapping[str, Any], half_extents: Sequence[float]) -> list[tuple[Any, Any]]:
+def restore_collision_world(model: Any, world: Any) -> None:
+    """Replace the complete world, clearing CuRobo's lingering mesh entries."""
+    if getattr(model.world_model, "mesh", []) or getattr(world, "mesh", []):
+        model.clear_world_cache()
+    model.update_world(world)
+
+
+def add_released_object(planner: Any, pose: Mapping[str, Any], half_extents: Sequence[float],
+                        *, observed_mesh=None) -> list[tuple[Any, Any]]:
     """Make the detached object an obstacle for retreat; return worlds to restore."""
     from curobo.geom.types import Cuboid

@@ -343,14 +351,25 @@ def add_released_object(planner: Any, pose: Mapping[str, Any], half_extents: Seq
     try:
         for model in (planner.motion_gen, planner.motion_gen_batch):
             world = model.world_model.clone()
-            if len(world.cuboid) + 1 > _obb_capacity(model):
+            if observed_mesh is not None:
+                from curobo.geom.types import Mesh
+
+                if len(world.mesh) + 1 > model.collision_cache.get("mesh", 0):
+                    raise CuroboWorldPortError("collision cache has no slot for released mesh")
+                world.mesh.append(Mesh(
+                    name="released_target", vertices=observed_mesh["vertices"],
+                    faces=observed_mesh["faces"], pose=_world_pose_for_planner(
+                        planner, {"position_m": [0., 0., 0.], "orientation_xyzw": [0., 0., 0., 1.]}),
+                ))
+            elif len(world.cuboid) + 1 > _obb_capacity(model):
                 raise CuroboWorldPortError("collision cache has no slot for released object")
+            else:
+                world.cuboid.append(Cuboid(name="released_target", dims=[2 * float(v) for v in half_extents], pose=_world_pose_for_planner(planner, pose)))
             previous.append((model, model.world_model.clone()))
-            world.cuboid.append(Cuboid(name="released_target", dims=[2 * float(v) for v in half_extents], pose=_world_pose_for_planner(planner, pose)))
-            model.update_world(world)
+            restore_collision_world(model, world)
     except Exception:
         for model, world in reversed(previous):
-            model.update_world(world)
+            restore_collision_world(model, world)
         raise
     return previous

@@ -413,6 +432,8 @@ def apply_collision_world(
         )
     rebuild_required = any(
         min(_obb_capacity(motion_gen), _obb_capacity(batch)) < required_capacity
+        or ("observed_collision" in world_artifact and any(
+            model.collision_cache.get("mesh", 0) < 1 for model in (motion_gen, batch)))
         for _, motion_gen, batch, _, required_capacity, _, _ in prepared
     )
     receipts = []
@@ -432,9 +453,9 @@ def apply_collision_world(
                 planner.motion_gen_batch = rebuilt_batch
         else:
             for planner, motion_gen, batch, world, _, old_world, old_batch_world in prepared:
-                motion_gen.update_world(world)
+                restore_collision_world(motion_gen, world)
                 applied.append((motion_gen, old_world))
-                batch.update_world(world)
+                restore_collision_world(batch, world)
                 applied.append((batch, old_batch_world))
         for planner, *_ in prepared:
             receipts.append({
@@ -448,7 +469,7 @@ def apply_collision_world(
     except Exception as exc:
         for motion_gen, previous_world in reversed(applied):
             try:
-                motion_gen.update_world(previous_world)
+                restore_collision_world(motion_gen, previous_world)
             except Exception:
                 pass
         if rebuild_required:
```

#### [修改 / Modified] examples/forge-adapters/robotwin20/runtime/robotwin_descent_diagnostic.py L25-L59

```diff
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_descent_diagnostic.py b/examples/forge-adapters/robotwin20/runtime/robotwin_descent_diagnostic.py
index 5b02f8a..bb5ef10 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_descent_diagnostic.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_descent_diagnostic.py
@@ -25,6 +25,35 @@ def sphere_box_clearance(center, radius, pose, dimensions):
     return float(np.linalg.norm(np.maximum(distance, 0)) + min(float(distance.max()), 0) - radius)


+def diagnose_start_collisions(task, arm, start_qpos):
+    """Measure the unchanged planning start state against its loaded world."""
+    planner = getattr(task.robot, f"{arm}_planner")
+    model = planner.motion_gen
+    config = model.kinematics.kinematics_config
+    q = model.tensor_args.to_device(np.asarray(start_qpos[:7]).reshape(1, -1))
+    spheres = model.kinematics.get_state(q).get_link_spheres()[0].cpu().numpy()
+    links = {}
+    for name in config.link_name_to_idx_map:
+        for index in config.get_sphere_index_from_link_name(name).tolist():
+            links[index] = name
+    collisions = []
+    for index, sphere in enumerate(spheres):
+        if sphere[3] <= 0:
+            continue
+        for box in model.world_model.cuboid:
+            distance = sphere_box_clearance(sphere[:3], sphere[3], box.pose, box.dims)
+            if distance < 0:
+                collisions.append({
+                    "link": links.get(index), "sphere_index": index,
+                    "obstacle": box.name, "clearance_m": distance,
+                    "radius_m": float(sphere[3]),
+                })
+    return {
+        "diagnostic_only": True, "motion_authorized": False,
+        "start_qpos": list(start_qpos[:7]), "collisions": collisions,
+    }
+
+
 def diagnose_attached_segment(task: Any, candidate, arm, actor, pose, start_qpos):
     from curobo.types.robot import JointState

```

#### [修改 / Modified] examples/forge-adapters/robotwin20/runtime/robotwin_observed_collision.py L15-L60

```diff
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_observed_collision.py b/examples/forge-adapters/robotwin20/runtime/robotwin_observed_collision.py
index e8ef52b..f0f241a 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_observed_collision.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_observed_collision.py
@@ -15,6 +15,46 @@ from robotwin20_adapter.observed_collision import (
 from robotwin20_adapter.route_evidence import _artifact_path


+def released_target_mesh(task, candidate, source_matrix):
+    """Conservative observed convex hull swept over release-to-settled motion.
+
+    The same target mask/cloud and uncertainty already used for contact
+    qualification own this geometry. No actor shape or pose is queried.
+    """
+    from itertools import product
+
+    from scipy.spatial import ConvexHull
+
+    scene = getattr(task, "_paos_observed_collision", None)
+    if scene is None:
+        return None
+    if scene["descriptor"]["target_entity_ref"] != candidate["entity_ref"]:
+        raise ValueError("released target differs from observed collision binding")
+    source = rigid_transform(source_matrix)
+    target = candidate["placement_target"]["target_object_pose"]
+    q = target["orientation_xyzw"]
+    rotation = _quat_matrix_wxyz([q[3], *q[:3]])
+    local = (scene["target"] - source[:3, 3]) @ source[:3, :3]
+    settled = local @ rotation.T + np.asarray(target["position_m"])
+    clearance = candidate["placement_target"].get("release_clearance_m", 0.)
+    shift = np.asarray(candidate["execution_grasp"]["support_clear_direction"]["vector"]) * clearance
+    swept = np.concatenate((settled, settled + shift))
+    padding = np.asarray(list(product((-1., 1.), repeat=3))) * scene["policy"].uncertainty_m
+    points = (swept[:, None, :] + padding[None, :, :]).reshape(-1, 3)
+    hull = ConvexHull(points)
+    triangles = hull.simplices.copy()
+    vertices = points[triangles]
+    inward = (np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
+              * hull.equations[:, :3]).sum(axis=1) < 0
+    triangles[inward] = triangles[inward][:, [0, 2, 1]]
+    used, faces = np.unique(triangles, return_inverse=True)
+    return {
+        "vertices": points[used].tolist(), "faces": faces.reshape(-1, 3).tolist(),
+        "source": scene["evidence"], "geometry": "observed_convex_release_sweep",
+        "uncertainty_m": scene["policy"].uncertainty_m,
+    }
+
+
 def collision_components(component):
     """Keep separate convex shapes separate instead of filling their union hull."""
     pose = component.get_pose()
```

#### [修改 / Modified] examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py L10-L16, L179-L193, L199-L205, L235-L248, L270-L276

```diff
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py b/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py
index f305ccf..b96a5d8 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py
@@ -10,6 +10,7 @@ from robotwin_curobo_world_port import (
     apply_collision_world,
     bind_scene_table,
     capture_peer_projection,
+    restore_collision_world,
 )
 from robotwin_gripper_geometry import planner_gripper_state
 from robotwin_planning_geometry import (
@@ -178,6 +179,15 @@ def evaluate_route_arm(
     previous_worlds = []
     gripper = []
     try:
+        from robotwin_observed_collision import released_target_mesh
+
+        observed = getattr(task, "_paos_observed_bindings", {}).get(candidate.get("entity_ref"))
+        if observed is not None:
+            actor = ObservedGeometryActor(observed["model"]["world_T_object"])
+        if getattr(task, "_paos_observed_collision", None) is not None and not isinstance(actor, ObservedGeometryActor):
+            raise SimulationProbeError("observed route requires an observation-owned source pose")
+        mesh = (released_target_mesh(task, candidate, actor.get_pose().to_transformation_matrix())
+                if getattr(task, "_paos_observed_collision", None) is not None else None)
         limits = _joint_limits(planner)
         for phase in planned_candidate["route"]:
             phase_name = phase["phase"]
@@ -189,6 +199,7 @@ def evaluate_route_arm(
                     planner,
                     released_pose,
                     released_extents,
+                    **({"observed_mesh": mesh} if mesh is not None else {}),
                 )
             for index, waypoint in enumerate(phase["waypoints"]):
                 pose = _route_pose(waypoint, request["frame_id"])
@@ -224,6 +235,14 @@ def evaluate_route_arm(
         return {"arm": arm, "status": "pass", "segments": segments, "motion_authorized": False}
     except Exception as exc:
         diagnostic = None
+        if diagnose_failure and phase_name == "retreat":
+            from robotwin_descent_diagnostic import diagnose_start_collisions
+
+            try:
+                with planner_gripper_state(task, arm, phase["gripper_state"]):
+                    diagnostic = diagnose_start_collisions(task, arm, predicted)
+            except Exception as diagnostic_error:
+                diagnostic = {"error": str(diagnostic_error), "diagnostic_only": True}
         if diagnose_failure and attached and phase_name == "descent":
             from robotwin_descent_diagnostic import diagnose_attached_segment

@@ -251,7 +270,7 @@ def evaluate_route_arm(
         finally:
             try:
                 for model, world in previous_worlds:
-                    model.update_world(world)
+                    restore_collision_world(model, world)
             finally:
                 entity.set_qpos(original.tolist())

```

#### [修改 / Modified] examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py L1357-L1370, L1512-L1526

```diff
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py b/examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py
index 9b2a03d..48e5c7b 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py
@@ -1357,6 +1357,14 @@ def execute_candidate_phases(

     actor = _actor_for_entity(task, candidate["entity_ref"])
     before_actor = np.asarray(actor.get_pose().p, dtype=np.float64).copy()
+    released_mesh = None
+    if getattr(task, "_paos_observed_collision", None) is not None:
+        from robotwin_observed_collision import released_target_mesh
+
+        observed = getattr(task, "_paos_observed_bindings", {}).get(candidate["entity_ref"])
+        if observed is None:
+            raise SimulationProbeError("observed release geometry requires a current entity binding")
+        released_mesh = released_target_mesh(task, candidate, observed["model"]["world_T_object"])
     route_records: list[dict[str, Any]] = []
     contact_trace: list[dict[str, Any]] = []
     execution_state["contact_trace"] = contact_trace
@@ -1504,11 +1512,15 @@ def execute_candidate_phases(
                 planner.motion_gen.detach_object_from_robot()
                 detached = True
                 execution_state["planner_object_attached"] = False
-                observed = actor.get_pose()
-                add_released_object(planner, {
-                    "position_m": [float(v) for v in observed.p],
-                    "orientation_xyzw": [float(observed.q[i]) for i in (1, 2, 3, 0)],
-                }, half_extents)
+                if released_mesh is not None:
+                    add_released_object(planner, candidate["placement_target"]["target_object_pose"],
+                                        half_extents, observed_mesh=released_mesh)
+                else:
+                    observed = actor.get_pose()
+                    add_released_object(planner, {
+                        "position_m": [float(v) for v in observed.p],
+                        "orientation_xyzw": [float(observed.q[i]) for i in (1, 2, 3, 0)],
+                    }, half_extents)
             except Exception as exc:
                 raise SimulationProbeError("planner could not detach object after release") from exc
         route_records.append(
```

#### [修改 / Modified] examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py L9-L26, L36-L47, L65-L71, L132-L166

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py b/examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py
index 9458efd..b9d9017 100644
--- a/examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py
+++ b/examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py
@@ -9,12 +9,18 @@ from robotwin20_adapter.collision_world import build_collision_world, collision_


 class FakeWorld:
-    def __init__(self, cuboid=None):
+    def __init__(self, cuboid=None, mesh=None):
         self.cuboid = list(cuboid or [])
+        self.mesh = list(mesh or [])
         self.objects = self.cuboid

     def clone(self):
-        return FakeWorld(list(self.cuboid))
+        return FakeWorld(list(self.cuboid), list(self.mesh))
+
+
+class FakeMesh:
+    def __init__(self, **kwargs):
+        self.__dict__.update(kwargs)


 class FakeCuboid:
@@ -30,8 +36,12 @@ class FakeMotionGen:
             [FakeCuboid(name="table", dims=[1, 1, 1], pose=[0, 0, 0, 1, 0, 0, 0])]
         )
         self.fail = fail
-        self.collision_cache = {"obb": capacity}
+        self.collision_cache = {"obb": capacity, "mesh": 1}
         self.updates = []
+        self.clears = 0
+
+    def clear_world_cache(self):
+        self.clears += 1

     def update_world(self, world):
         if self.fail:
@@ -55,6 +65,7 @@ class FakePlanner:
 def fake_curobo(monkeypatch):
     module = ModuleType("curobo.geom.types")
     module.Cuboid = FakeCuboid
+    module.Mesh = FakeMesh
     module.WorldConfig = FakeWorld
     monkeypatch.setitem(sys.modules, "curobo.geom.types", module)

@@ -121,6 +132,35 @@ def test_released_target_cannot_silently_overflow_collision_cache():
     assert len(planner.motion_gen.world_model.cuboid) == 1


+def test_observed_release_mesh_keeps_world_and_clears_mesh_on_restoration():
+    from robotwin_curobo_world_port import add_released_object, restore_collision_world
+
+    planner = FakePlanner()
+    mesh = {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
+            "faces": [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]]}
+    previous = add_released_object(planner, {}, [], observed_mesh=mesh)
+    for model, old_world in previous:
+        assert [x.name for x in model.world_model.cuboid] == ["table"]
+        assert model.world_model.mesh[0].vertices == mesh["vertices"]
+        assert model.world_model.mesh[0].pose == [0, 0, 0, 1, 0, 0, 0]
+        assert model.clears == 1
+        restore_collision_world(model, old_world)
+        assert not model.world_model.mesh
+        assert model.clears == 2
+        assert [x.name for x in model.world_model.cuboid] == ["table"]
+
+
+def test_observed_release_mesh_requires_reserved_capacity_and_rolls_back():
+    from robotwin_curobo_world_port import add_released_object
+
+    planner = FakePlanner()
+    planner.motion_gen_batch.collision_cache["mesh"] = 0
+    with pytest.raises(CuroboWorldPortError, match="no slot for released mesh"):
+        add_released_object(planner, {}, [], observed_mesh={"vertices": [], "faces": []})
+    assert not planner.motion_gen.world_model.mesh
+    assert planner.motion_gen.clears == 2
+
+
 def test_port_projects_bound_scene_table_pose_into_each_planner_frame():
     planners = {"left": FakePlanner(), "right": FakePlanner()}
     for planner in planners.values():
```

#### [修改 / Modified] examples/forge-adapters/robotwin20/tests/test_route_planner.py L158-L183

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_route_planner.py b/examples/forge-adapters/robotwin20/tests/test_route_planner.py
index a2d02ac..fbf2df3 100644
--- a/examples/forge-adapters/robotwin20/tests/test_route_planner.py
+++ b/examples/forge-adapters/robotwin20/tests/test_route_planner.py
@@ -158,3 +158,26 @@ def test_retreat_obstacle_covers_both_release_and_landing(route):
     assert pose["position_m"] == pytest.approx([0, 0, 1.0025])
     assert extents == pytest.approx([.02, .02, .0225])
     assert candidate["placement_target"]["target_object_pose"]["position_m"] == [0, 0, 1]
+
+
+def test_retreat_diagnostic_keeps_world_and_never_promotes_failure(route, monkeypatch):
+    task, request, candidate, entity, events, starts = route
+    original_plan = task.robot.left_plan_path
+
+    def plan(pose, last_qpos):
+        if len(starts) == 7:
+            return {"status": "Fail"}
+        return original_plan(pose, last_qpos)
+
+    def diagnose(task, arm, qpos):
+        assert events[-1] == "released_obstacle"
+        assert qpos[:7] == pytest.approx([.07] * 7)
+        return {"collisions": [{"obstacle": "released_target"}], "diagnostic_only": True}
+
+    task.robot.left_plan_path = plan
+    monkeypatch.setattr("robotwin_descent_diagnostic.diagnose_start_collisions", diagnose)
+    result = module.evaluate_route_arm(task, request, candidate, "left", object(), diagnose_failure=True)
+    assert result["status"] == "fail"
+    assert result["diagnostic"]["collisions"][0]["obstacle"] == "released_target"
+    assert entity.qpos == [0.] * 9
+    assert result["motion_authorized"] is False
```

#### [修改 / Modified] examples/forge-adapters/robotwin20/tests/test_runtime_observed_collision.py L10-L46

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_runtime_observed_collision.py b/examples/forge-adapters/robotwin20/tests/test_runtime_observed_collision.py
index baa8872..ba27ab6 100644
--- a/examples/forge-adapters/robotwin20/tests/test_runtime_observed_collision.py
+++ b/examples/forge-adapters/robotwin20/tests/test_runtime_observed_collision.py
@@ -10,6 +10,37 @@ from robotwin_planning_geometry import SimulationProbeError, _validate_gripper_t
 from robotwin20_adapter.observed_collision import ObservedCollisionPolicy


+def test_released_mesh_encloses_all_observed_points_uncertainty_and_release_sweep():
+    from scipy.spatial import ConvexHull
+
+    points = np.array(list(product([-.02, .02], [-.01, .01], [-.015, .015])))
+    source = np.eye(4)
+    source[:3, 3] = [.3, -.2, .8]
+    scene = {"descriptor": {"target_entity_ref": "red"}, "target": points + source[:3, 3],
+             "policy": ObservedCollisionPolicy(), "evidence": {"target_mask_ref": "mask"}}
+    task = SimpleNamespace(_paos_observed_collision=scene)
+    candidate = {"entity_ref": "red", "placement_target": {
+        "target_object_pose": {"position_m": [-.1, .2, .8],
+                               "orientation_xyzw": [0, 0, np.sqrt(.5), np.sqrt(.5)]},
+        "release_clearance_m": .005},
+        "execution_grasp": {"support_clear_direction": {"vector": [0, 0, 1]}}}
+    mesh = observed.released_target_mesh(task, candidate, source.reshape(-1).tolist())
+    vertices = np.array(mesh["vertices"])
+    hull = ConvexHull(vertices)
+    transformed = points @ np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]) + [-.1, .2, .8]
+    for shift in (0., .005):
+        for offset in product([-.001, .001], repeat=3):
+            samples = transformed + [0, 0, shift] + offset
+            assert np.max(samples @ hull.equations[:, :3].T + hull.equations[:, 3]) < 1e-10
+    triangles = vertices[mesh["faces"]]
+    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
+    assert np.all(np.sum(normals * (triangles.mean(axis=1) - vertices.mean(axis=0)), axis=1) > 0)
+    assert mesh["source"] == scene["evidence"]
+    candidate["entity_ref"] = "blue"
+    with pytest.raises(ValueError, match="differs from observed collision binding"):
+        observed.released_target_mesh(task, candidate, source.reshape(-1).tolist())
+
+
 class Link:
     def __init__(self, position, name="panda_hand"):
         self.position = np.asarray(position, dtype=float)
```

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/pyproject.toml L1-L6

```diff
diff --git a/examples/forge-skills/pick-place-workflow/pyproject.toml b/examples/forge-skills/pick-place-workflow/pyproject.toml
index 2e724ac..20916d6 100644
--- a/examples/forge-skills/pick-place-workflow/pyproject.toml
+++ b/examples/forge-skills/pick-place-workflow/pyproject.toml
@@ -1,6 +1,6 @@
 [project]
 name = "paos-pick-place-workflow"
-version = "2.7.8"
+version = "2.7.9"
 description = "Provider-neutral Forge capability contracts and no-motion conformance fixtures."
 requires-python = ">=3.11"
 dependencies = ["httpx>=0.28,<1.0"]
```

#### [修改 / Modified] examples/forge-skills/pick-place-workflow/skill.yaml L1-L6, L190-L199

```diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index d9e4f36..5b96ff4 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -1,6 +1,6 @@
 manifest_version: 2
 name: pick-place-workflow
-version: "2.7.8"
+version: "2.7.9"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
 skill_document: SKILL.md
 gateway_url: http://127.0.0.1:19020
@@ -190,10 +190,10 @@ artifacts:
   resolver: local
   nodes:
     robotwin20_persistent_host:
-      artifact_id: robotwin20_persistent_host-0.7.11-linux-x86_64
-      version: "0.7.11"
+      artifact_id: robotwin20_persistent_host-0.7.12-linux-x86_64
+      version: "0.7.12"
       platform: linux
       arch: x86_64
       artifact_type: executable_tar_gz
       entrypoint: robotwin20_persistent_host
-      sha256: fdd328bad8c7594893b4d48e7e5c4f7ce54e239122d94118c2d52cb2e04b03db
+      sha256: 106da563b7d43b0b64845b55640f69630c9430d5b762aedaedc32c29205601a2
```

#### [修改 / Modified] tests/test_agent_foundation.py L1224-L1261

```diff
diff --git a/tests/test_agent_foundation.py b/tests/test_agent_foundation.py
index 7206ad1..716fbc3 100644
--- a/tests/test_agent_foundation.py
+++ b/tests/test_agent_foundation.py
@@ -1224,6 +1224,38 @@ def test_model_replan_preserves_task_identity_without_executing(tmp_path):
     asyncio.run(exercise())


+@pytest.mark.parametrize("repaired", [True, False])
+def test_automatic_replan_repairs_cross_revision_retry_once_without_execution(tmp_path, repaired):
+    async def exercise():
+        c, task = setup_task(tmp_path)
+        graph = compile_task_plan(task, semantic_nodes(2), reason="first")
+        settlement = NodeSettlement(task_id=task.task_id, revision_id=graph.revision_id,
+                                    node_id="chosen-0", status="failed")
+        invalid = semantic_nodes(2)
+        invalid[0]["retry_of"] = "prior-revision-prepare"
+        provider = ScriptedProvider([LLMResponse(content=None, tool_calls=[ToolCallRequest(
+            str(i), "submit_recovery", {"nodes": nodes, "reason": "Refresh current evidence"},
+        )]) for i, nodes in enumerate((invalid, semantic_nodes(2) if repaired else invalid))])
+        operation = AgentRecoveryDecisions(provider, "fixture", c).propose_replan(
+            graph=graph, settlement=settlement, delta=build_replan_delta(graph, settlement), context=settlement)
+        if repaired:
+            proposal = await operation
+            assert proposal.plan_graph.nodes[0].retry_of is None
+        else:
+            with pytest.raises(ValueError, match="retry_of references an unknown node"):
+                await operation
+        assert len(provider.requests) == 2
+        context = json.loads(provider.requests[1]["messages"][1]["content"])
+        assert "retry_of references an unknown node" in context["repair"]["validation_error"]
+        assert context["repair"]["rejected_proposal"]["nodes"] == invalid
+        assert "omit prior-revision retry_of" in provider.requests[0]["messages"][0]["content"]
+        current = c.get_task(task.task_id)
+        assert len(current.revisions) == 1
+        assert current.execution_records == []
+        assert any(e["event_type"] == "agent_replan_proposal_rejected" for e in c.store.events(task.task_id))
+    asyncio.run(exercise())
+
+
 @pytest.mark.parametrize("status", ["available", "unavailable"])
 def test_query_receipt_is_persisted_identity_not_gateway_verdict(tmp_path, status):
     async def exercise():
```

#### [修改 / Modified] tests/test_agent_task_tool.py L2-L36

```diff
diff --git a/tests/test_agent_task_tool.py b/tests/test_agent_task_tool.py
index fef45ea..3bca808 100644
--- a/tests/test_agent_task_tool.py
+++ b/tests/test_agent_task_tool.py
@@ -2,10 +2,35 @@ from __future__ import annotations

 import asyncio
 import json
+from unittest.mock import Mock
+
+import pytest

 from PhyAgentOS.agent.tools.forge_task import ForgeTaskCreateTool
 from PhyAgentOS.config.schema import ForgeConfig
 from PhyAgentOS.forge.task import AgentTaskBusyError, AgentTaskCoordinator
+from PhyAgentOS.verification.contracts import TaskVerificationContract
+
+
+def test_task_create_requires_explicit_verification_choice():
+    coordinator = Mock()
+    tool = ForgeTaskCreateTool(coordinator)
+    assert tool.parameters["properties"]["verification"]["required"] == ["mode"]
+    with pytest.raises(ValueError, match="verification.mode must be explicit"):
+        asyncio.run(tool.execute("Arrange RGB and verify", {}))
+    coordinator.create_task.assert_not_called()
+    assert TaskVerificationContract().mode == "off"
+
+
+def test_task_create_preserves_enforced_verification(tmp_path):
+    coordinator = AgentTaskCoordinator(workspace=tmp_path, config=ForgeConfig(), client=object(), verifier=Mock())
+    tool = ForgeTaskCreateTool(coordinator)
+    contract = {"mode": "enforce", "goal": "Arrange RGB",
+                "success_criteria": ["All three blocks occupy their destinations"]}
+    created = json.loads(asyncio.run(tool.execute("Arrange RGB", contract)))
+    task = coordinator.get_task(created["data"]["task_id"])
+    assert task.verification.mode == "enforce"
+    assert task.verification.success_criteria == contract["success_criteria"]


 def test_task_create_reports_cross_session_owner_without_takeover(tmp_path):
```

### 验证 / Validation
- 241 tests passed, including Agent recovery and verification contracts, PlanningLoop, collision-world mesh lifecycle, observed hull coverage, simulation execution, persistent preparation, and task video.
- Command: PYTHONPATH=examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin tests/test_agent_task_tool.py tests/test_agent_foundation.py tests/test_planning_loop.py examples/forge-adapters/robotwin20/tests/test_route_planner.py examples/forge-adapters/robotwin20/tests/test_descent_diagnostic.py examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py examples/forge-adapters/robotwin20/tests/test_runtime_observed_collision.py examples/forge-adapters/robotwin20/tests/test_simulation_probe.py examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py examples/forge-adapters/robotwin20/tests/test_persistent_route_evaluator.py examples/forge-adapters/robotwin20/tests/test_persistent_task_video.py
- Captured no-motion replay: candidate://e3/1, right arm passes all 11 route segments including retreat and return; left arm remains rejected at approach IK. Zero Gateway calls and zero trajectory execution steps.
- Evidence: /home/yanxu/robotwin20-runtime/artifacts/rgb-retreat-diagnostic-20260925T1605/{start-collisions.json,full-route-mesh.json,full_route.py}.
- Independent packages: Node 0.7.12 and Skill 2.7.9 under /tmp/paos-rgb-observed-v11710/. Existing installation digest validation retained.
- Full-chain RGB success and video are still required; no-motion route readiness is not task acceptance.

- Ruff and git diff --check passed.

### Git 提交 / Git Commit
- Commit: 27d1e4e
- Branch: feature/planning-loop

## v11.7.9 (2026-09-25 14:01) - codex

### 实际修改 / Implemented Changes [完成代码；复验运行中]
- [sense] [fix] 本轮 task_a4a35f90a9984a28 的视觉语义关系为 is_on，Grounding 只接受 on，导致已存在的 70,606 点支撑点云未进入规划路线。修复 Adapter 对这两个等价支撑谓词的解析，并测试 lineage、歧义及默认无支撑行为；不补造支撑平面或使用仿真几何。(local)
- [Sense] [Fix] Task task_a4a35f90a9984a28 produced is_on relations, while Grounding accepted only on, dropping the existing 70,606-point support cloud from planning. Accept both equivalent support predicates and test lineage, ambiguity and absent-support behavior; do not fabricate a plane or use simulator geometry. (local)
- [eval] [exp] 保留首次全链路失败证据，更新独立 Node/Skill 包后重新发起修复验收，继续检查真实物理与 AgentLoop 结果。(local)
- [Eval] [Exp] Preserve the first end-to-end failure evidence, update the independently versioned Node/Skill packages and rerun acceptance to continue checking physical and AgentLoop outcomes. (local)

#### [修改 / Modified] `examples/forge-adapters/robotwin20/pyproject.toml` L1-L5

```diff
diff --git a/examples/forge-adapters/robotwin20/pyproject.toml b/examples/forge-adapters/robotwin20/pyproject.toml
index 614f803..6ea0828 100644
--- a/examples/forge-adapters/robotwin20/pyproject.toml
+++ b/examples/forge-adapters/robotwin20/pyproject.toml
@@ -1,5 +1,5 @@
 [project]
 name = "paos-robotwin20-adapter"
-version = "0.7.10"
+version = "0.7.11"
 description = "PAOS EnvironmentAdapter seam for RoboTwin20 sensor-backed observations."
 requires-python = ">=3.10"
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py` L621-L625

```diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
index 0829b37..7819f73 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
@@ -621,5 +621,5 @@ class Grounding:
         understanding = self.understandings[identity]
         refs = {r["object_ref"] for r in understanding.get("relations", [])
-                if r.get("predicate") == "on" and r.get("subject_ref") in binding["objects"]}
+                if r.get("predicate") in {"on", "is_on"} and r.get("subject_ref") in binding["objects"]}
         if not refs:
             return None  # Consumers requiring support must reject missing evidence.
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_grounding.py` L798-L838

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_grounding.py b/examples/forge-adapters/robotwin20/tests/test_grounding.py
index 365ce5b..1e1297a 100644
--- a/examples/forge-adapters/robotwin20/tests/test_grounding.py
+++ b/examples/forge-adapters/robotwin20/tests/test_grounding.py
@@ -798,2 +798,41 @@ def test_observed_targets_do_not_fall_back_to_benchmark_goals(tmp_path):
         g.scene_facts({**request, "intent": {"entity_ref": "entity://seen"},
                        "destination_ref": "destination://blocks-ranking-rgb/red-slot"})
+
+
+@pytest.mark.parametrize("predicate", ["on", "is_on", "is_near"])
+@pytest.mark.parametrize("defect", [None, "stale_cloud", "ambiguous_support"])
+def test_observed_support_consumes_semantic_relation_and_preserves_lineage(tmp_path, predicate, defect):
+    g, request, _ = setup(tmp_path)
+    understanding = next(iter(g.understandings.values()))
+    understanding["relations"] = [{"subject_ref": "entity://seen", "predicate": predicate,
+                                  "object_ref": "entity://support"}]
+    points = np.array([[x, y, -.025] for x in np.linspace(-.4, .4, 8)
+                       for y in np.linspace(-.3, .3, 8)])
+    np.save(tmp_path / "capture/support.npy", points)
+    cloud = {k: request[k] for k in ("observation_ref", "scene_revision", "calibration_ref")}
+    cloud.update(kind="object_point_cloud", entity_ref="entity://support", frame_id="camera",
+                 artifact_ref="artifact://capture/support")
+    understanding["derived_artifacts"].append(cloud)
+    if defect == "stale_cloud":
+        cloud["scene_revision"] = "old-scene"
+    if defect == "ambiguous_support":
+        understanding["relations"].append({"subject_ref": "entity://seen", "predicate": predicate,
+                                           "object_ref": "entity://other-support"})
+    bound = g.bind(request)
+    target = g.target(dict(binding_ref=bound["binding_ref"], entity_ref="entity://seen",
+                          frame_id="world", unit="m", frame_T_object_target=pose(.35)))
+    inputs = {**request, "intent": {"entity_ref": "entity://seen"},
+              "destination_ref": target["destination_ref"]}
+    if predicate != "is_near" and defect:
+        match = "lineage differs" if defect == "stale_cloud" else "surface is ambiguous"
+        with pytest.raises(ValueError, match=match):
+            g.scene_facts(inputs)
+    else:
+        facts = g.scene_facts(inputs)
+        if predicate == "is_near":
+            assert "support_surface" not in facts
+        else:
+            support = facts["support_surface"]
+            assert support["evidence_ref"] == "artifact://capture/support"
+            assert support["estimation"]["point_count"] == len(points)
+            assert support["estimation"]["height_m"] == pytest.approx(-.025)
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/pyproject.toml` L1-L5

```diff
diff --git a/examples/forge-skills/pick-place-workflow/pyproject.toml b/examples/forge-skills/pick-place-workflow/pyproject.toml
index c807e18..2e724ac 100644
--- a/examples/forge-skills/pick-place-workflow/pyproject.toml
+++ b/examples/forge-skills/pick-place-workflow/pyproject.toml
@@ -1,5 +1,5 @@
 [project]
 name = "paos-pick-place-workflow"
-version = "2.7.7"
+version = "2.7.8"
 description = "Provider-neutral Forge capability contracts and no-motion conformance fixtures."
 requires-python = ">=3.11"
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/skill.yaml` L1-L5, L191-L199

```diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index e681d73..d9e4f36 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -1,5 +1,5 @@
 manifest_version: 2
 name: pick-place-workflow
-version: "2.7.7"
+version: "2.7.8"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
 skill_document: SKILL.md
@@ -191,9 +191,9 @@ artifacts:
   nodes:
     robotwin20_persistent_host:
-      artifact_id: robotwin20_persistent_host-0.7.10-linux-x86_64
-      version: "0.7.10"
+      artifact_id: robotwin20_persistent_host-0.7.11-linux-x86_64
+      version: "0.7.11"
       platform: linux
       arch: x86_64
       artifact_type: executable_tar_gz
       entrypoint: robotwin20_persistent_host
-      sha256: 369d1aa9f50bbace48bafec363907c5ccedfe557d93a369a8f062e8f23045fa8
+      sha256: fdd328bad8c7594893b4d48e7e5c4f7ce54e239122d94118c2d52cb2e04b03db
```

### 验证 / Validation
- 76 tests passed: Grounding, observed support and persistent preparation; Ruff and git diff --check passed.
- 真实点云重放 / Captured-cloud replay: 70,606 points, 65,117 plane inliers, 5,489 residual points retained in 47 boxes; estimated height 0.7405762693 m. Read-only replay, no motion or fabricated support.
- Command: PYTHONPATH=examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests/test_grounding.py examples/forge-adapters/robotwin20/tests/test_observed_support.py examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py

### Git 提交 / Git Commit
- Commit: 952fe6b
- Branch: feature/planning-loop

## v11.7.8 (2026-09-25 13:42) - codex

### 实际修改 / Implemented Changes [完成代码；验收运行中]
- [eval] [fix] 为本轮全链路验收补齐观测几何与 benchmark 目标的显式 Adapter 组合：当前 host 把 runtime_monitored 硬限定为 oracle，observed 路径也无法解析 task.goal 的 destination_ref，导致用户要求的纯感知几何路线不可执行。复用完整路线准入、仿真 Action approval、接触和停止监测，不新增 hash、gate 或独立任务控制器。(local)
- [Eval] [Fix] Compose observation-owned geometry with benchmark destinations explicitly for this acceptance run: the current host restricts runtime_monitored to oracle and observed grounding cannot resolve task.goal destinations. Reuse complete-route admission, simulation Action approval, contact and stop monitoring; introduce no additional hashes, gates or task controllers. (local)
- [eval] [exp] 启动一个独立 RGB 全链路任务，记录 GraspGen 24 个真实样本生成后才筛选、最多 10 个进入 prepare、动作终态、Verifier 和累计视频；不把软件测试或 oracle 路线结果计作本轮通过。(local)
- [Eval] [Exp] Launch an independent RGB end-to-end task and preserve evidence for generation of 24 real GraspGen samples before filtering, at most ten prepare candidates, terminal Actions, verifier and cumulative video; software tests and oracle routes do not constitute acceptance. (local)
- 预期影响 / Expected files: adapter grounding, persistent host/deployment, Skill runtime profile, corresponding tests, acceptance documentation and this changelog.

### 文件变更详情 / File Change Details

#### [修改 / Modified] `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md` L20-L34

```diff
diff --git a/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md b/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md
index 4c91605..e447d50 100644
--- a/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md
+++ b/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md
@@ -20,5 +20,15 @@ Run three independent tasks with current observations and fresh task identities.
 ## Ownership and remaining simulation scope

-The grasp provider is selected from the adapter grasp profile independently of route geometry. The supplied graspgen profile names GraspGen and samples 200 real candidates and retains at most ten after existing score/NMS filtering. Sampling and retained counts are configured separately; shortages are reported without padding. Benchmark destination_ref may still originate from task.goal. Existing oracle route/collision geometry and simulation Action admission remain explicitly simulator-owned; they are not sensor evidence and do not generate grasp poses. This stage is simulation execution, not hardware acceptance.
+The grasp provider is selected from the adapter grasp profile independently of route geometry. The supplied graspgen profile names GraspGen and samples 24 real candidates and retains at most ten after existing score/NMS filtering. Sampling and retained counts are configured separately; shortages are reported without padding. Benchmark destination_ref may still originate from task.goal. The acceptance profile uses observed route/collision geometry. Benchmark destinations remain task-specification input, while simulation dynamics and Action monitoring remain Runtime-owned. This stage is simulation execution, not hardware acceptance.

 PAOS remains gpt-5.6-sol/high. Preserve architecture, extension boundaries, developer guidance, Coordinator ownership and AgentLoop recovery. The existing external goal has an unfinished objective and the goal tool cannot edit its text; this document records the user's supplemental acceptance requirements without falsely completing that goal.
+
+## Observed geometry acceptance profile (2026-09-25)
+
+Use `robotwin-blocks-ranking-graspgen` for the requested full-chain run.
+Its explicit profile uses observation-owned route/collision geometry,
+benchmark task destinations and monitored simulation Actions. The old oracle
+profile is retained for diagnostic comparisons and is not a passing result for
+this acceptance. Generate all 24 GraspGen candidates before canonicalization,
+deduplication and filtering retain at most ten. Run the normal Coordinator and
+AgentLoop, retain each invocation and require the final verifier/video evidence.
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/pyproject.toml` L1-L5

```diff
diff --git a/examples/forge-adapters/robotwin20/pyproject.toml b/examples/forge-adapters/robotwin20/pyproject.toml
index 9e3fa39..614f803 100644
--- a/examples/forge-adapters/robotwin20/pyproject.toml
+++ b/examples/forge-adapters/robotwin20/pyproject.toml
@@ -1,5 +1,5 @@
 [project]
 name = "paos-robotwin20-adapter"
-version = "0.7.9"
+version = "0.7.10"
 description = "PAOS EnvironmentAdapter seam for RoboTwin20 sensor-backed observations."
 requires-python = ">=3.10"
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py` L24-L33, L440-L448, L554-L558, L562-L566, L577-L584, L589-L596, L598-L605

```diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
index 913b80a..0829b37 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
@@ -24,8 +24,10 @@ _DEFERRED_BINDING_AMBIGUITIES = {

 class Grounding:
-    def __init__(self, client, root, scene_source, *, support_policy=None, collision_policy=None):
+    def __init__(self, client, root, scene_source, *, support_policy=None, collision_policy=None,
+                 goal_source="observation_owned"):
         self.client, self.root, self.source = client, root, scene_source
         self.support_policy = support_policy or SupportEstimationPolicy()
         self.collision_policy = collision_policy
+        self.goal_source = goal_source
         self.observations = {}
         self.understandings = {}
@@ -438,5 +440,9 @@ class Grounding:

     def scene_facts(self, request, *, deadline=None):
-        value = self.targets[request["destination_ref"]]
+        value = self.targets.get(request["destination_ref"])
+        if value is None:
+            if self.goal_source != "benchmark_task_definition":
+                raise ValueError("destination is not an observation-owned target")
+            value = self._benchmark_goal_target(request, deadline=deadline)
         if any(value[k] != request[k] for k in IDENTITY_KEYS):
             raise ValueError("target observation identity mismatch")
@@ -548,5 +554,5 @@ class Grounding:
         destination_ref = request.get("destination_ref")
         if not isinstance(target_entity, str) or not isinstance(destination_ref, str):
-            raise ValueError("oracle benchmark target request is incomplete")
+            raise ValueError("benchmark target request is incomplete")
         matches = [
             (reference, binding)
@@ -556,5 +562,5 @@ class Grounding:
         ]
         if len(matches) != 1:
-            raise ValueError("oracle benchmark target binding is absent or ambiguous")
+            raise ValueError("benchmark target binding is absent or ambiguous")
         binding_ref, binding = matches[0]
         observed_object = binding["objects"][target_entity]
@@ -571,8 +577,8 @@ class Grounding:
             or goal_facts.get("geometry_source") != "benchmark_task_definition"
         ):
-            raise ValueError("oracle benchmark goal facts are unavailable")
+            raise ValueError("benchmark goal facts are unavailable")
         goals = goal_facts.get("goals")
         if not isinstance(goals, list):
-            raise ValueError("oracle benchmark goals are invalid")
+            raise ValueError("benchmark goals are invalid")
         goal_matches = [
             goal
@@ -583,8 +589,8 @@ class Grounding:
         ]
         if len(goal_matches) != 1:
-            raise ValueError("oracle benchmark destination does not uniquely match binding")
+            raise ValueError("benchmark destination does not uniquely match binding")
         goal = goal_matches[0]
         if goal.get("frame_id") != "world" or goal.get("unit") != "m":
-            raise ValueError("oracle benchmark destination frame or unit is invalid")
+            raise ValueError("benchmark destination frame or unit is invalid")
         pose = rigid_transform(goal.get("world_T_object_target"))
         target = deepcopy(observed_object)
@@ -592,4 +598,8 @@ class Grounding:
             entity_ref=target_entity,
             world_T_object_target=pose.reshape(-1).tolist(),
+            world_T_functional_target=(
+                pose @ np.linalg.inv(rigid_transform(observed_object["world_T_object"]))
+                @ rigid_transform(observed_object["world_T_functional_point"])
+            ).reshape(-1).tolist(),
         )
         return {
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py` L174-L178, L191-L194

```diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py
index b72ec99..ad406ea 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py
@@ -174,4 +174,5 @@ def build_persistent_deployment(*, client, artifact_root: Path, scene_source,
     )
     grounding = Grounding(client, artifact_root, scene_source,
+                          goal_source=goal_source,
                           support_policy=SupportEstimationPolicy(**profile.get("observed_support", {})),
                           collision_policy=(ObservedCollisionPolicy(**profile["observed_collision"])
@@ -190,6 +191,4 @@ def build_persistent_deployment(*, client, artifact_root: Path, scene_source,
     if goal_source not in {"benchmark_task_definition", "observation_owned"}:
         raise ValueError("goal_source must be benchmark_task_definition or observation_owned")
-    if simulation_action_mode == RUNTIME_MONITORED_ACTION_MODE and route_geometry_source != "oracle":
-        raise ValueError("runtime_monitored simulation Actions require oracle route geometry")
     routes = PreparedRoutes(client, artifact_root)
     evaluator = readiness_evaluator if readiness_evaluator is not None else RouteReadinessEvaluationAdapter(
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py` L228-L231

```diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py
index 24e4a88..7894af7 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py
@@ -228,11 +228,4 @@ def build_persistent_host(
             "simulation_action_mode must be disabled or runtime_monitored"
         )
-    if (
-        simulation_action_mode == RUNTIME_MONITORED_ACTION_MODE
-        and route_geometry_source != "oracle"
-    ):
-        raise PersistentHostConfigurationError(
-            "runtime_monitored simulation Actions require oracle route geometry"
-        )
     goal_source = profile.get("goal_source", "observation_owned")
     if goal_source not in {"benchmark_task_definition", "observation_owned"}:
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_grounding.py` L149-L157, L175-L180, L184-L190, L787-L799

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_grounding.py b/examples/forge-adapters/robotwin20/tests/test_grounding.py
index c47cbdb..365ce5b 100644
--- a/examples/forge-adapters/robotwin20/tests/test_grounding.py
+++ b/examples/forge-adapters/robotwin20/tests/test_grounding.py
@@ -149,7 +149,9 @@ def test_oracle_scene_uses_bound_actor_geometry_without_changing_observed_identi


-def test_oracle_scene_resolves_runtime_goal_without_target_matrix_transcription(tmp_path):
+@pytest.mark.parametrize("geometry_source", ["oracle", "observed"])
+def test_scene_resolves_runtime_goal_without_target_matrix_transcription(tmp_path, geometry_source):
     g, request, _ = setup(tmp_path)
     g.bind(request)
+    g.goal_source = "benchmark_task_definition"
     destination = "destination://blocks-ranking-rgb/red-slot"
     calls = []
@@ -173,5 +175,6 @@ def test_oracle_scene_resolves_runtime_goal_without_target_matrix_transcription(

     g.client.query = query
-    facts = g.oracle_scene_facts({
+    resolve = g.oracle_scene_facts if geometry_source == "oracle" else g.scene_facts
+    facts = resolve({
         **request,
         "intent": {"entity_ref": "entity://seen"},
@@ -181,5 +184,7 @@ def test_oracle_scene_resolves_runtime_goal_without_target_matrix_transcription(
     assert facts["objects"][0]["target_ref"] == destination
     assert facts["objects"][0]["world_T_object_target"] == pose(0.35)
-    assert facts["geometry_source"] == "oracle_actor"
+    assert facts["geometry_source"] == ("oracle_actor" if geometry_source == "oracle" else "observation")
+    assert facts["objects"][0]["half_extents_m"] == ([0.04] * 3 if geometry_source == "oracle" else [0.02] * 3)
+    assert facts["objects"][0]["world_T_functional_target"] == pose(0.35)
     assert not g.targets
     assert calls.count("task_goal_facts") == 1
@@ -782,2 +787,13 @@ def test_correspondence_and_target_fail_closed(tmp_path, failure):
     assert GroundingEndpoint(g.target).invoke(args)["status"] == "unavailable"
     assert not g.targets
+
+
+def test_observed_targets_do_not_fall_back_to_benchmark_goals(tmp_path):
+    g, request, _ = setup(tmp_path)
+    g.bind(request)
+    def query(*args, **kwargs):
+        raise AssertionError("unexpected Runtime request")
+    g.client.query = query
+    with pytest.raises(ValueError, match="not an observation-owned target"):
+        g.scene_facts({**request, "intent": {"entity_ref": "entity://seen"},
+                       "destination_ref": "destination://blocks-ranking-rgb/red-slot"})
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py` L55-L69

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py b/examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py
index 56079f1..79c3fb4 100644
--- a/examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py
+++ b/examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py
@@ -55,11 +55,15 @@ def test_deployment_wires_shared_cache_and_requires_persistent_stop_policy(tmp_p
         {"contact_dynamics", "stop_control"}
     )
-    with pytest.raises(ValueError, match="require oracle route geometry"):
-        build_persistent_deployment(
-            client=client, artifact_root=tmp_path, scene_source=lambda request: None,
-            materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
-            arm_profile_digest="a" * 64, route_geometry_source="observed",
-            simulation_action_mode="runtime_monitored", task_name="blocks_ranking_rgb",
-        )
+    observed = build_persistent_deployment(
+        client=client, artifact_root=tmp_path, scene_source=lambda request: None,
+        materializer_command=("python", "materializer.py"), materializer_arguments=arguments,
+        arm_profile_digest="a" * 64, route_geometry_source="observed",
+        simulation_action_mode="runtime_monitored", task_name="blocks_ranking_rgb",
+        goal_source="benchmark_task_definition",
+    )
+    assert observed.preparation_provider.route_builder.scene_source.__name__ == "scene_facts"
+    assert observed.grounding.goal_source == "benchmark_task_definition"
+    assert isinstance(observed.preparation_provider.approval_issuer, PersistentSimulationActionApprover)
+    assert observed.preparation_provider.selector.deferred_checks == monitored.preparation_provider.selector.deferred_checks
     with pytest.raises(ValueError, match="observed or oracle"):
         build_persistent_deployment(
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_persistent_host.py` L219-L228, L286-L290

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_persistent_host.py b/examples/forge-adapters/robotwin20/tests/test_persistent_host.py
index 03ae28d..020200b 100644
--- a/examples/forge-adapters/robotwin20/tests/test_persistent_host.py
+++ b/examples/forge-adapters/robotwin20/tests/test_persistent_host.py
@@ -219,19 +219,10 @@ def test_host_rejects_unknown_route_geometry_source(tmp_path):


-def test_host_rejects_runtime_monitored_observed_profile_before_worker_start(tmp_path):
-    profile, environ = _profile(tmp_path)
-    profile["simulation_action_mode"] = "runtime_monitored"
-
-    with pytest.raises(
-        PersistentHostConfigurationError,
-        match="require oracle route geometry",
-    ):
-        build_persistent_host(profile, environ=environ)
-
-
 @pytest.mark.parametrize("route_source", ["observed", "oracle"])
-def test_host_composes_tools_around_one_persistent_worker_client(tmp_path, monkeypatch, route_source):
+@pytest.mark.parametrize("action_mode", ["disabled", "runtime_monitored"])
+def test_host_composes_tools_around_one_persistent_worker_client(tmp_path, monkeypatch, route_source, action_mode):
     profile, environ = _profile(tmp_path)
     profile["route_geometry_source"] = route_source
+    profile["simulation_action_mode"] = action_mode
     closed = []

@@ -295,4 +286,5 @@ def test_host_composes_tools_around_one_persistent_worker_client(tmp_path, monke
     assert captured["preparation_timeout_s"] == 4.0
     assert captured["route_geometry_source"] == route_source
+    assert captured["simulation_action_mode"] == action_mode
     assert grasp_profiles == [{"provider_id": "graspgen", "max_candidates": 10}]
     assert captured["goal_source"] == "observation_owned"
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/SKILL.md` L50-L62

```diff
diff --git a/examples/forge-skills/pick-place-workflow/SKILL.md b/examples/forge-skills/pick-place-workflow/SKILL.md
index 9c7440e..4f2eed0 100644
--- a/examples/forge-skills/pick-place-workflow/SKILL.md
+++ b/examples/forge-skills/pick-place-workflow/SKILL.md
@@ -50,4 +50,13 @@ evidence, task success, readiness, or motion approval. The Runtime must not fall
 back between oracle and observed profiles.

+The explicitly named `robotwin-blocks-ranking-graspgen` profile combines
+observation-owned object geometry, support and collision occupancy with only
+benchmark task descriptions and destinations. GraspGen generates 24 real samples
+before canonicalization and filtering retains at most ten for preparation.
+Use `task.goal` destinations directly; do not add `manipulation.target` nodes.
+The profile retains complete-route readiness and monitored simulation Action
+approval, contact/stop checks, reconciliation and cumulative video. It does not
+fall back to oracle geometry or template grasps.
+
 The graph represents your chosen obligations and dependencies. One PlanNode is one
 settlement unit completed by one selected Tool. A composite intention such as
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/pyproject.toml` L1-L5

```diff
diff --git a/examples/forge-skills/pick-place-workflow/pyproject.toml b/examples/forge-skills/pick-place-workflow/pyproject.toml
index 7048766..c807e18 100644
--- a/examples/forge-skills/pick-place-workflow/pyproject.toml
+++ b/examples/forge-skills/pick-place-workflow/pyproject.toml
@@ -1,5 +1,5 @@
 [project]
 name = "paos-pick-place-workflow"
-version = "2.7.6"
+version = "2.7.7"
 description = "Provider-neutral Forge capability contracts and no-motion conformance fixtures."
 requires-python = ">=3.11"
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/skill.yaml` L1-L5, L23-L67, L191-L199

```diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index 620e6ba..e681d73 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -1,5 +1,5 @@
 manifest_version: 2
 name: pick-place-workflow
-version: "2.7.6"
+version: "2.7.7"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
 skill_document: SKILL.md
@@ -23,4 +23,45 @@ profiles:
     required_environment: []
     environment: {}
+  robotwin-blocks-ranking-graspgen:
+    dataflow: profiles/robotwin-persistent/dataflow.yaml
+    required_binaries:
+      - robotwin20_persistent_host
+    required_assets: []
+    required_environment:
+      - ROBOTWIN20_PAOS_PYTHON
+      - ROBOTWIN20_ARTIFACT_ROOT
+      - ROBOTWIN20_RUNTIME_ROOT
+      - ROBOTWIN20_RUNTIME_PROFILE
+      - ROBOTWIN20_WORKER_PYTHON
+      - ROBOTWIN20_MATERIALIZER_PYTHON
+      - ROBOTWIN20_MODEL_API_BASE
+      - ROBOTWIN20_MODEL_API_KEY
+      - ROBOTWIN20_MODEL
+      - ROBOTWIN20_REASONING_EFFORT
+      - ROBOTWIN20_ROUTE_GEOMETRY_SOURCE
+      - ROBOTWIN20_SIMULATION_ACTION_MODE
+      - ROBOTWIN20_GOAL_SOURCE
+      - LOCATEANYTHING_PYTHON
+      - LOCATEANYTHING_CACHE_DIR
+      - LOCATEANYTHING_MODULES_CACHE_DIR
+      - SAM2_PYTHON
+      - SAM2_REPO_ROOT
+      - SAM2_CHECKPOINT
+      - GRASPGEN_PYTHON
+      - GRASPGEN_CHECKPOINT
+      - GRASPGEN_CONFIG
+      - GRASPGEN_SOURCE_ROOT
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION_PLAN
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION_EVIDENCE
+      - ROBOTWIN20_CONTROLLER_QUALIFICATION_VALIDATION
+      - ROBOTWIN20_LEFT_MOTION_CAPABILITY
+      - ROBOTWIN20_LEFT_MOTION_CAPABILITY_VALIDATION
+      - ROBOTWIN20_RIGHT_MOTION_CAPABILITY
+      - ROBOTWIN20_RIGHT_MOTION_CAPABILITY_VALIDATION
+    environment:
+      ROBOTWIN20_ROUTE_GEOMETRY_SOURCE: observed
+      ROBOTWIN20_SIMULATION_ACTION_MODE: runtime_monitored
+      ROBOTWIN20_GOAL_SOURCE: benchmark_task_definition
   robotwin-blocks-ranking-observed:
     dataflow: profiles/robotwin-persistent/dataflow.yaml
@@ -150,9 +191,9 @@ artifacts:
   nodes:
     robotwin20_persistent_host:
-      artifact_id: robotwin20_persistent_host-0.7.9-linux-x86_64
-      version: "0.7.9"
+      artifact_id: robotwin20_persistent_host-0.7.10-linux-x86_64
+      version: "0.7.10"
       platform: linux
       arch: x86_64
       artifact_type: executable_tar_gz
       entrypoint: robotwin20_persistent_host
-      sha256: 02a6786f93605302a6a22d5d49ca6cab2e247d6eaab767f06b9243afb9332a8a
+      sha256: 369d1aa9f50bbace48bafec363907c5ccedfe557d93a369a8f062e8f23045fa8
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py` L70-L78

```diff
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py b/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py
index 4ec1427..11f5b07 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py
@@ -70,4 +70,9 @@ def test_manifest_v2_bundle_installs_and_catalog_reloads_required_tools(tmp_path
         "ROBOTWIN20_GOAL_SOURCE": "benchmark_task_definition",
     }
+    assert manifest.profiles["robotwin-blocks-ranking-graspgen"].environment == {
+        "ROBOTWIN20_ROUTE_GEOMETRY_SOURCE": "observed",
+        "ROBOTWIN20_SIMULATION_ACTION_MODE": "runtime_monitored",
+        "ROBOTWIN20_GOAL_SOURCE": "benchmark_task_definition",
+    }
     assert (tmp_path / "skills" / "pick-place-workflow" / "SKILL.md").is_file()

```

### 验证与架构复核 / Validation and Architecture Review
- 112 tests passed: Grounding, persistent host/deployment/preparation, Action approval, candidate admission and Skill install/discovery. The first collection attempts lacked package/runtime PYTHONPATH; rerunning with the declared source and runtime roots passed. Ruff and git diff --check passed.
- 验证命令 / Command: PYTHONPATH=examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests/test_grounding.py examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py examples/forge-adapters/robotwin20/tests/test_persistent_host.py examples/forge-adapters/robotwin20/tests/test_persistent_action_approval.py examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py examples/forge-adapters/robotwin20/tests/test_arm_candidates.py examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py.
- [eval] [fix] 目标事实独立于感知几何；新 profile 显式组合已有 provider。原 observed 和 oracle profile 不变。完整路线、碰撞、assignment、Action approval 与运行中接触/停止检查仍负责准入；无新增哈希/门禁/任务调度器。(local)
- [Eval] [Fix] Goal facts remain separate from observed geometry; the new profile explicitly composes existing providers. Existing observed and oracle profiles remain unchanged. Complete-route, collision, assignment, Action approval and runtime contact/stop checks still own admission; no new hashes, gates or task scheduler. (local)
- Runtime installed: Node 0.7.10, Skill 2.7.7, profile robotwin-blocks-ranking-graspgen.
- 验收运行中 / Acceptance running: cli:rgb-e2e-observed-20260925T134706; artifact root /home/yanxu/robotwin20-runtime/artifacts/paos-rgb-e2e-observed-20260925T134706. Tests are not a physical success claim.
### Git 提交 / Git Commit
- Commit: 479e849
- Branch: feature/planning-loop

## v11.7.6 (2026-09-25 05:15) - codex

### 预期修改 / Planned Changes [计划]
- [agent] [fix] 在 `waiting_for_user` 恢复上下文重新暴露已有 `forge_task_begin_revision` Coordinator 入口，使错误的语义 `produced_evidence` 计划可通过追加 revision 修复；不改变 Gateway、Action 或运动授权。
- [Agent] [Fix] Re-expose the existing `forge_task_begin_revision` Coordinator entry in the `waiting_for_user` recovery context so a plan with semantic `produced_evidence` can be repaired through an appended revision, without changing Gateway, Action, or motion authorization.
- [eval] [test] 增加 prompt visibility 回归，验证 waiting-for-user 任务可见追加修订工具，且普通工具集合保持不变。
- [Eval] [Test] Add prompt-visibility regression coverage proving waiting-for-user tasks see the append-revision tool while the ordinary tool set remains unchanged.

### 实际修改 / Implemented Changes [完成]
- [agent] [fix] `PhyAgentOS/agent/prompt_context.py:L321-L327` 在 `waiting_for_user` 可见工具集合中加入 Coordinator-owned `forge_task_begin_revision`；仍隐藏 Gateway Query/Action，避免恢复阶段越权执行。
- [Agent] [Fix] `PhyAgentOS/agent/prompt_context.py:L321-L327` adds Coordinator-owned `forge_task_begin_revision` to the `waiting_for_user` visible tools while keeping Gateway Query/Action hidden during recovery.
- [eval] [test] `tests/test_prompt_context.py:L407-L412` 验证 waiting-for-user 任务可见追加修订工具；测试 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_prompt_context.py` 通过 34 项，Ruff 与 `git diff --check` 通过。
- [Eval] [Test] `tests/test_prompt_context.py:L407-L412` verifies append-revision visibility for waiting-for-user tasks; `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_prompt_context.py` passed 34 tests, with Ruff and `git diff --check` passing.

### Git 提交 / Git Commit
- Commit: `b220bc5`
- Branch: `feature/planning-loop`

## v11.7.5 (2026-09-25 02:30) - codex

### 预期修改 / Planned Changes [计划]
- [agent] [fix] 在未物化 AgentTask 的模型上下文中明确投影当前 discovery 阶段、缺失前置 Query 和下一步 `forge_tool_query` 路径，避免模型把尚未满足前置条件的 PlanGraph 工具误判为未注册并取消任务。
- [Agent] [Fix] Project the active discovery phase, missing prerequisite Queries, and the next `forge_tool_query` path into the model context for unmaterialized AgentTasks, preventing the model from mistaking gated PlanGraph tools for unregistered tools and cancelling the task.
- [eval] [test] 增加 prompt projection 回归，验证未完成 discovery 时保留 Query guidance，完成 discovery 后切换为 PlanGraph guidance。
- [Eval] [Test] Add prompt projection regressions proving Query guidance remains visible before discovery completion and switches to PlanGraph guidance after discovery completion.

### 实际修改 / Implemented Changes [完成]
- [agent] [fix] `PhyAgentOS/agent/prompt_context.py:L612-L630,L698-L702` 增加只读 `planning_phase`、`missing_preplan_queries` 和 `planning_next_step` 投影；在前置 Query 未完成时明确要求使用 `forge_tool_query`，并说明 PlanGraph 工具会在 discovery 完成后出现。
- [Agent] [Fix] `PhyAgentOS/agent/prompt_context.py:L612-L630,L698-L702` adds read-only `planning_phase`, `missing_preplan_queries`, and `planning_next_step` projections; before prerequisite Queries complete it explicitly directs the model to use `forge_tool_query` and explains that PlanGraph tools appear after discovery.
- [eval] [test] `tests/test_prompt_context.py:L490-L521` 覆盖 discovery 阶段和物化就绪阶段的上下文切换；`tests/test_prompt_context.py`: 34 passed，Ruff 和 `git diff --check` 通过。
- [Eval] [Test] `tests/test_prompt_context.py:L490-L521` covers discovery and materialization-ready context transitions; 34 tests passed, with Ruff and `git diff --check` passing.
- [Eval] [Test] `tests/test_prompt_context.py:L490-L521` covers discovery and materialization-ready context transitions; 34 tests passed, with Ruff and `git diff --check` passing.
