# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

- [2026-11_part3](changelog/2026-11_part3.md)
- [2026-11_part2](changelog/2026-11_part2.md)
- [2026-11](changelog/2026-11.md)
- [2026-10_part16](changelog/2026-10_part16.md)
- [2026-10_part15](changelog/2026-10_part15.md)
- [2026-10_part14](changelog/2026-10_part14.md)
- [2026-10_part13](changelog/2026-10_part13.md)
- [2026-10_part12](changelog/2026-10_part12.md)
- [2026-10_part11](changelog/2026-10_part11.md)
- [2026-10_part9](changelog/2026-10_part9.md)
- [2026-10_part10](changelog/2026-10_part10.md)
- [2026-10_part8](changelog/2026-10_part8.md)
- [2026-10_part7](changelog/2026-10_part7.md)
- [2026-10_part6](changelog/2026-10_part6.md)
- [2026-10_part5](changelog/2026-10_part5.md)
- [2026-10_part4](changelog/2026-10_part4.md)
- [2026-10_part3](changelog/2026-10_part3.md)
- [2026-10_part2](changelog/2026-10_part2.md)
- [2026-10_index_archive](changelog/2026-10_index_archive.md)
- [2026-10](changelog/2026-10.md)
- [2026-09_part9](changelog/2026-09_part9.md)
- [2026-09_part8](changelog/2026-09_part8.md)
- [2026-09_part7](changelog/2026-09_part7.md)
- [2026-09_part6](changelog/2026-09_part6.md)
- [2026-09_part5](changelog/2026-09_part5.md)
- [2026-09_part4](changelog/2026-09_part4.md)
- [2026-09_part3](changelog/2026-09_part3.md)
- [2026-09_part21](changelog/2026-09_part21.md)
- [2026-09_part20](changelog/2026-09_part20.md)
- [2026-09_part2](changelog/2026-09_part2.md)
- [2026-09_part19](changelog/2026-09_part19.md)
- [2026-09_part18](changelog/2026-09_part18.md)
- [2026-09_part17](changelog/2026-09_part17.md)
- [2026-09_part16](changelog/2026-09_part16.md)
- [2026-09_part15](changelog/2026-09_part15.md)
- [2026-09_part14](changelog/2026-09_part14.md)
- [2026-09_part13](changelog/2026-09_part13.md)
- [2026-09_part12](changelog/2026-09_part12.md)
- [2026-09_part11](changelog/2026-09_part11.md)
- [2026-09_part10](changelog/2026-09_part10.md)
- [2026-09](changelog/2026-09.md)

## 最近五版本 / Latest five versions

## v17.9.15 (2026-11-25 01:19) - codex

- [env] [fix] [完成] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` 在瓶体仍处于原支撑位置、低速且双指反馈新鲜时，让失抓恢复在实测臂关节与指距处限时采样。`001734` 的 R03 失败帧中瓶体仍直立，单指窗口有约 0.00328 N·s 的瞬时冲量。仅靠最后一个运动窗口无法知道停止后是否卸载，Git、类型与普通测试也不能提供这一仿真物理事实。使用原有 `settle_s`、碰撞和停机约束，保留开爪与回撤的原有判据和 AgentLoop 的重试所有权。 / Sample at the measured arm and finger positions for a bounded interval after grasp loss when the body remains within its support band at low speed and both fingers have fresh feedback. In the `001734` R03 receipt, the body remained upright and one finger measured about 0.00328 N·s over the aborted-motion window. That window cannot establish whether the fingers unload after stopping. Reuse `settle_s`, collision and stop checks, the existing opening and retreat criteria, and AgentLoop ownership of retries.
- [env] [exp] [完成] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` 覆盖固定指距下瞬时载荷消退、持续载荷、状态失效和碰撞中止。 / Verify transient unload at fixed aperture, persistent load, invalidated feedback and collision abort.

### 文件变更详情 / File changes

- [env] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L848–L866、L2443、L2485–L2557、L2679–L2682、L2991–L2994、L3010–L3011。双指必须在当前窗口提交有效数据，固定姿态采样必须取得晚于该步开始的双指反馈。原开爪判据、全指距包络碰撞检查、继续执行的步数及取消控制均保留。反馈记录最近下发的停止、固定、开爪及回撤指距。 / Both fingers must contribute current feedback, and fixed-position sampling requires fresh frames after the step starts. Retain the existing opening criteria, full finger-sweep collision checks, execution budget and cancellation. Record the most recent commanded aperture when stopping, holding, opening or retreating.
- [env] [exp] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2451–L2540。以真实执行入口和无运动夹具覆盖瞬时与持续单指载荷，以及离开支撑、重新检测到持有、帧不更新、碰撞、取消。验证固定期间指距不变，且开爪发生在新窗口卸载之后。 / Exercise transient and persistent unilateral load, loss of support, renewed grasp, stale frames, collision, and cancellation through the execution entry point in a no-motion fixture. Assert fixed aperture throughout sampling and fresh unloading before opening.

```diff
@@ -846,12 +846,19 @@ class GripContactWindow:
         )

-    def current_unloaded(self, *, require_clear=False, whole_interval=True):
-        """Judge both fingers using their latest capture and current interval."""
+    def has_current_feedback(self, *, after=None):
+        """Check that both fingers contributed a fresh frame to this interval."""
         if self.error is not None:
             raise PhaseMotionError("contact_sampling_failed", str(self.error)) from self.error
         now = float(self.world.current_time)
         return len(self.sensors) == 2 and all(
-            latest is not None and latest[0] in frames and now - latest[0] <= self.dt * 2
-            and frames[latest[0]] == 0.
+            latest is not None and latest[0] in frames and 0. <= now - latest[0] <= self.dt * 2
+            and (after is None or after < latest[0])
+            for latest, frames in zip(self.latest, self.frames, strict=True)
+        )
+
+    def current_unloaded(self, *, require_clear=False, whole_interval=True):
+        """Judge both fingers using their latest capture and current interval."""
+        return self.has_current_feedback() and all(
+            frames[latest[0]] == 0.
             and (not whole_interval or all(impulse == 0. for impulse in frames.values()))
             and (not require_clear or not latest[1])
@@ -2434,5 +2441,5 @@ class IsaacPhaseMotion:
         qualified_start,
     ):
-        """Open at a fixed arm pose, then reverse the qualified path once clear."""
+        """Confirm unload at a fixed pose, then open and reverse the qualified path."""
         if failure not in acquire_failure_recovery_codes(self.config):
             raise PhaseMotionError("acquire_recovery_not_allowed", failure)
@@ -2476,16 +2483,10 @@ class IsaacPhaseMotion:
             return supported, position_error, rotation_error

-        held, physical_body = record("recovery_check")
-        supported, _, _ = measure_support(physical_body)
-        clear = contact_window.current_unloaded(require_clear=True, whole_interval=False)
-        residual_unloaded = (
-            failure == "physical_grasp_lost"
-            and support_contact_allowed("lift", physical_body, original, tolerance)
-            and contact_window.current_unloaded()
-        )
-        if held or not supported or not (clear or residual_unloaded):
-            raise PhaseMotionError(
-                "acquire_recovery_possession_uncertain",
-                "safe opening requires a stable supported object and current unloaded fingers",
+        def in_support_band(pose):
+            return support_contact_allowed("lift", pose, original, tolerance)
+
+        def safe_to_open(pose):
+            return contact_window.current_unloaded(require_clear=True, whole_interval=False) or (
+                failure == "physical_grasp_lost" and in_support_band(pose) and contact_window.current_unloaded()
             )

@@ -2509,4 +2510,6 @@ class IsaacPhaseMotion:
             ):
                 raise PhaseMotionError("joint_limit_violation", "safe acquire recovery joint target is invalid")
+            if fingers.shape != initial_gripper.shape or not np.isfinite(fingers).all():
+                raise PhaseMotionError("joint_limit_violation", "safe acquire recovery finger target is invalid")
             measured_relation = np.linalg.inv(self.tcp()) @ self.observed_pose(source)
             self._collisions(
@@ -2527,7 +2530,30 @@ class IsaacPhaseMotion:
             step_count += 1
             record_frame(stage)
-            record(stage)
+            feedback = record(stage, commanded_fingers=fingers)
             if np.max(np.abs(self.joints() - arm)) > self.config["joint_tracking_tolerance_rad"]:
                 raise PhaseMotionError("joint_tracking_failed", f"tracking tolerance exceeded in {stage}")
+            return feedback
+
+        held, physical_body = record("recovery_check")
+        supported, _, _ = measure_support(physical_body)
+        can_open = not held and supported and safe_to_open(physical_body)
+        if (not can_open and failure == "physical_grasp_lost" and not held and supported
+                and in_support_band(physical_body) and contact_window.has_current_feedback()):
+            hold_arm = self.joints()
+            hold_fingers = np.asarray(self.robot.get_joint_positions())[finger_indices]
+            for _ in range(math.ceil(self.config.get("settle_s", 0.) / self.dt)):
+                held, physical_body = command(hold_arm, hold_fingers, "recovery_settle", True)
+                supported, _, _ = measure_support(physical_body)
+                if (held or not supported or not in_support_band(physical_body)
+                        or not contact_window.has_current_feedback(after=contact_window.start)):
+                    break
+                if safe_to_open(physical_body):
+                    can_open = True
+                    break
+        if not can_open:
+            raise PhaseMotionError(
+                "acquire_recovery_possession_uncertain",
+                "safe opening requires a stable supported object and current unloaded fingers",
+            )

         opening_arm = self.joints().copy()
@@ -2651,5 +2677,8 @@ class IsaacPhaseMotion:
             return contact_window.valid()

-        def record(stage):
+        def record(stage, *, commanded_fingers=None):
+            nonlocal finger_target
+            if commanded_fingers is not None:
+                finger_target = commanded_fingers
             physical_body = self.observed_pose(source)
             tcp = self.tcp()
@@ -2960,6 +2989,8 @@ class IsaacPhaseMotion:
             try:
                 if changed:
+                    stop_positions = np.asarray(self.robot.get_joint_positions()).copy()
                     self.robot.get_articulation_controller().apply_action(
-                        ArticulationAction(joint_positions=np.asarray(self.robot.get_joint_positions()).copy()))
+                        ArticulationAction(joint_positions=stop_positions))
+                    finger_target = stop_positions[finger_indices]
             except Exception as stop_exc:
                 reference = self._artifact("phase-feedback", {"operation": operation,
@@ -2978,5 +3009,4 @@ class IsaacPhaseMotion:
             ):
                 try:
-                    finger_target = np.asarray(self.scene.get("initial_gripper_positions"), dtype=float)
                     recovery = self._recover_failed_acquire(
                         failure=failure,
```

```diff
+@pytest.mark.parametrize("outcome", [
+    "transient", "persistent", "support_lost", "held_again", "stale", "collision", "cancelled",
+])
+def test_failed_lift_samples_unload_before_opening_at_fixed_pose(monkeypatch, outcome):
+    ...
+    assert settling[-1]["selected_contact_impulse_ns"] == [0., 0.]
+    assert opening[0]["timestamp_s"] > settling[-1]["timestamp_s"]
```

### 验证 / Validation

- [env] [exp] 阶段动作和接触时序测试共 273 项通过，`git diff --check` 通过。完整 Isaac 仿真另行验证。 / All 273 phase-motion and contact-timing tests passed, as did the diff check. The full Isaac replay is tracked separately.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `0e192705`，`feature/planning-loop`，2026-11-25 01:27:04 +0800。

## v17.9.14 (2026-11-25 00:16) - codex

- [policy] [fix] [完成] PlanningLoop 接续已通过原调用结算的动作时，复用 Coordinator 已保存的同调用结算，避免用执行后的场景重算成 stale。保留不同调用的冲突检查、未知结果、实际重试与场景刷新。 / Reuse the Coordinator settlement of the same invocation during handoff to the planning loop. Preserve checks for distinct invocations, unknown outcomes, actual retries, and scene refresh.

### 文件变更详情 / File changes

- [policy] [fix] `PhyAgentOS/agent/planning_loop.py` L1664–L1666、L2286–L2308。转发单条终态执行的调用 ID，以同任务、活动修订、节点、工具及调用 ID 查找 Coordinator 有效结算。匹配时继续原有场景刷新和后续执行。 / Forward the invocation ID of a single terminal record and reuse the Coordinator's effective settlement only when task, active revision, node, tool, and invocation match. Continue through the existing scene refresh and execution paths.
- [policy] [exp] `tests/test_planning_loop.py` L3767–L3867。覆盖同一调用继续下一节点，以及不同或缺失调用 ID 时仍报告冲突。 / Assert continuation for the same invocation and preserved conflict detection when the invocation differs or is absent.

```diff
@@ -1661,6 +1661,9 @@ class AgentLoopNodeExecutor:
             revision_id=context.revision_id,
             node_id=context.node_id,
             tool_id=records[-1].tool_id,
+            invocation_id=(
+                getattr(records[0], "invocation_id", None) if len(records) == 1 else None
+            ),
             status=status,
             scene_write_behavior=scene_write_behavior,
             world_changed=world_changed,
@@ -2280,12 +2283,29 @@ class PlanningLoopAdapter:
                 )
             ):
                 continue
-            settlement = settle_node(
-                graph.nodes[[node.node_id for node in graph.nodes].index(node_id)],
-                result,
-                current_scene_revision=scene_revision,
-            )
-            self.coordinator.record_node_settlement(settlement)
+            settlement = None
+            if result.invocation_id and task.active_revision_id == result.revision_id:
+                # Foreground reconciliation can settle an invocation before its
+                # background node turn returns against the already updated scene.
+                settlement = next(
+                    (
+                        item
+                        for item in self.coordinator.effective_node_settlements(task_id)
+                        if item.task_id == result.task_id
+                        and item.revision_id == result.revision_id
+                        and item.node_id == result.node_id
+                        and item.source_tool_id == result.tool_id
+                        and item.invocation_id == result.invocation_id
+                    ),
+                    None,
+                )
+            if settlement is None:
+                settlement = settle_node(
+                    graph.nodes[[node.node_id for node in graph.nodes].index(node_id)],
+                    result,
+                    current_scene_revision=scene_revision,
+                )
+                self.coordinator.record_node_settlement(settlement)
             if settlement.status == "completed":
                 completed.append(node_id)
                 if result.world_changed and result.new_scene_revision:
```

### 验证 / Validation

- [policy] [exp] 214 项 PlanningLoop、长程续接、多物体及未知动作恢复测试通过，`git diff --check` 通过。原仿真轮次 R05 三阶段完成，宿主因冲突关闭，新一轮用于验证 R03 续接。 / All 214 PlanningLoop, long-horizon, multi-object and unknown-action recovery tests passed, as did the diff check. The original run completed all R05 phases before its host exited on the conflict. A new run will validate continuation to R03.
### Git 提交 / Git Commit

- 实现提交 / Implementation commit `3a449a99`，`feature/planning-loop`，2026-11-25 00:21:25 +0800。

## v17.9.13 (2026-11-24 23:33) - codex

- [eval] [fix] [完成] 失抓后可沿已执行路线退回本次安全起点。R05 归位后从退让姿态接续 R03 时，Adapter 可在满足原有卸载和支撑条件后恢复。 / Recover from a failed acquire by reversing the route to its qualified start. The Adapter can recover R03 after R05's retreat when the existing unloading and support checks pass.

### 文件变更详情 / File changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L807–L817、L2380–L2418、L2434–L2464、L2568–L2583、L2627–L2633、L2994–L3012、L3055、L3074–L3077、L3108–L3110。进场记录已张开且无对应瓶身接触的夹爪与经过碰撞验证的路线起点。反馈区分固定观察原点和本次抓取起点。 / Capture an open gripper, fresh source-clear frames, and a collision-checked route start before motion. Keep observation home and the current route start distinct in feedback.
- [eval] [exp] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2601–L2602、L2613–L2683。验证非原点回撤、过期或缺失读数、闭夹、接触和起终点碰撞。 / Cover non-home retreat and rejection for stale or missing readings, closed fingers, body contact, or blocked endpoints.

```diff
@@ -2411,5 +2455,5 @@ class IsaacPhaseMotion:
-        if (
-            route_start.shape != initial_arm.shape
-            or np.max(np.abs(route_start - initial_arm))
-            > self.config["joint_tracking_tolerance_rad"]
-        ):
+        joint_tolerance = self.config["joint_tracking_tolerance_rad"]
+        if route_start.shape != initial_arm.shape or not np.isfinite(route_start).all():
+            raise PhaseMotionError("acquire_recovery_start_not_safe_pose", "qualified route start is invalid")
+        at_home = np.max(np.abs(route_start - initial_arm)) <= joint_tolerance
+        if not at_home and (qualified_start is None or qualified_start["joints_rad"] != route_start.tolist()):
@@ -2418 +2462 @@ class IsaacPhaseMotion:
-                "automatic recovery requires the qualified route to start at observation home",
+                "non-home recovery requires open fingers, fresh clear contact frames and collision clearance at route start",
@@ -2419,0 +2464 @@ class IsaacPhaseMotion:
+        recovery_target = initial_arm if at_home else route_start
@@ -2523,2 +2568,2 @@ class IsaacPhaseMotion:
-        home_error = float(np.max(np.abs(self.joints() - initial_arm)))
-        if home_error > self.config["joint_tracking_tolerance_rad"]:
+        endpoint_error = float(np.max(np.abs(self.joints() - recovery_target)))
+        if not math.isfinite(endpoint_error) or endpoint_error > joint_tolerance:
@@ -2528,0 +2574,3 @@ class IsaacPhaseMotion:
+        if not at_home:
+            self._collisions(self.joints(), source, False, False,
+                             np.linalg.inv(self.tcp()) @ self.observed_pose(source), held_fingers=False)
```

### 验证 / Validation

- [eval] [exp] 240 项阶段动作测试及 `git diff --check` 通过。下一轮 Isaac 实跑沿用 R05→R03 任务和原有物理配置，并从抓取角候选移除 R03 上次失抓的 −π/2。 / All 240 phase motion tests and the diff check passed. The next Isaac run keeps the R05→R03 task and the prior physics profile, omitting the −π/2 angle used by the failed R03 grasp.
### Git 提交 / Git Commit

- 实现提交 / Implementation commit `6f35b2f0`，`feature/planning-loop`，2026-11-24 23:41:26 +0800。

## v17.9.12 (2026-11-24 22:34) - codex

- [eval] [fix] [完成] Isaac 宿主接入现有 Agent Provider 重试预算及间隔配置。22:12:23 轮失抓后已通过新观察，但短时上游故障耗尽宿主默认重试并关闭仿真，使同一任务无法重抓。保持 Coordinator 对原节点、场景与重试权限的判定。 / Wire the existing Agent Provider retry budget and delay into the Isaac host. The 22:12:23 run obtained a fresh observation after grasp recovery, but an upstream outage exhausted the host defaults and closed the simulation before reacquisition. Preserve the Coordinator's node, scene and retry authorization checks.

### 文件变更详情 / File changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py` L130–L132、L144–L148、L208–L214。转发现有配置给同一个任务协调器。 / Forward the existing settings to the task's Coordinator.
- [eval] [exp] `examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py` L136–L143。验证宿主使用传入的非默认重试预算和间隔。 / Assert that the host applies a supplied retry budget and delay.

```diff
-    coordinator = AgentTaskCoordinator(workspace=workspace, config=..., client=None)
+    coordinator = AgentTaskCoordinator(
+        workspace=workspace, config=..., client=None,
+        max_agent_provider_retries=max_agent_provider_retries,
+        agent_provider_retry_delay_s=agent_provider_retry_delay_s,
+    )
```

### 验证 / Validation

- [eval] [exp] 17 项宿主和续接测试通过，`git diff --check` 通过。上游已恢复响应，实跑使用单次复跑配置来延长重试等待。 / All 17 host and continuation tests and the diff check passed. The upstream provider is responding. The simulation replay uses a run-specific configuration to allow longer retries.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `36af57c9`，`feature/planning-loop`，2026-11-24 22:36:07 +0800。

## v17.9.11 (2026-11-24 22:08) - codex

- [eval] [fix] [完成] 修改 Isaac 抓取准备与相应测试。预选路线未通过全路径检查时，尝试已有的完整路线搜索，保留原运动检查和准备证据。21:18:30 轮的 R03 在当前关节姿态下多次出现转腕 IK 不连续，而预选模式提前裁掉了其他策略。 / In Isaac acquire preparation, let a rejected preselected route fall back to the existing full route search with the same qualification and evidence. The current replay repeatedly found wrist IK discontinuities for R03 while preselection excluded alternate strategies.

### 文件变更详情 / File changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L1424–L1429、L1459–L1470、L1500–L1501、L1519–L1544、L1573–L1574、L1659、L1695、L1708–L1709。预选候选全部失败后，复用现有路径检查和失败前缀缓存，寻找配置中的首条合格路线。两次搜索共用超时，并在准备结果中记录进入备选搜索的证据。 / After the preselected candidates are exhausted, use the existing qualification and failed-prefix cache to find the first eligible configured route. Both passes share a deadline and link the fallback evidence.
- [eval] [exp] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L973–L1028。覆盖预选成功、备选成功和共用超时导致拒绝准备。 / Cover preselected success, fallback success, and fail-closed expiration on the original deadline.

```diff
-            for strategy in strategies:
+            for strategy, dimensions, first_feasible in ordered_strategies:
                  ...
-                        if policy == "first_feasible":
+                        if first_feasible:
                              break
```

### 验证 / Validation

- [eval] [exp] 234 项 Isaac 阶段运动测试通过。`git diff --check` 通过。21:18:30 轮 R05 已完成，R03 尚未发生动作。备选选择待复跑实测。 / All 234 Isaac phase-motion tests and the diff check passed. The 21:18:30 run completed R05 and reported no motion for R03. Simulation of alternative selection remains pending.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `af2ea7ee`，`feature/planning-loop`，2026-11-24 22:14:18 +0800。
