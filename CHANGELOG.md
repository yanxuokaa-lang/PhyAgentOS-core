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

## v17.9.10 (2026-11-24 21:26) - codex

- [eval] [fix] [完成] 在 Coordinator 的任务结算中识别一次已经安全收尾的失抓后来由相同动作义务成功补做的情况。保留失败与成功的原始回执，核对成功是同一个物体、目标和工艺请求，其他未知及未恢复的结果仍阻止结算为成功。 / In Coordinator task finalization, recognize a safely recovered failed acquire when a later measured success fulfills the same original Action obligation with the same object, destination and process request. Retain both receipts and continue blocking success for unresolved or unrecovered effects.

### 文件变更详情 / File changes

- [eval] [fix] `PhyAgentOS/forge/task.py` L33–L37、L5118–L5253。结算时核对失败回撤、后续修订的同义务动作、物体与目标、归位要求和各阶段已知结果。 / Finalization links a proven failed-acquire recovery to a later known completion of the same obligation, objects, return request, and phases.
- [eval] [refactor] `PhyAgentOS/forge/manipulation.py` L26–L67 与 `PhyAgentOS/agent/recovery_decisions.py` L17、L167–L194。复用同一回执判定识别空夹、安全回撤和支撑面上的物体。 / Share recognition of known support, empty gripper, and safe retreat between recovery and finalization.
- [eval] [exp] `tests/test_subtask_finalization.py` L1–L179。以持久化任务验证补做成功、参数不匹配和不安全或未知结果。 / Exercise successful replacement, changed request semantics, and unknown or unsafe outcomes with persisted tasks.

```diff
-        for item in task.execution_records
+        or _subtask_failure_was_replaced(task, item)
+        for item in task.execution_records
```

### 验证 / Validation

- [eval] [exp] 定向测试 30 项通过，从已保存的仿真记录核对过真实失抓与成功回执。扩大测试 86 项通过，另 1 项缺少 `planning_selections` 的测试数据错误已在修改前重现。 / All 30 focused tests passed. Existing simulation ledgers supplied real failure and success receipts. The wider suite had 86 passes and one fixture failure for missing `planning_selections`, reproduced before the change.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `71ad9d7b`，`feature/planning-loop`，2026-11-24 21:41:50 +0800。

## v17.9.9 (2026-11-24 21:06) - codex

- [eval] [fix] [完成] 修改 Isaac 宿主的续接计划和测试。用 Coordinator 已持久化的当前场景查询及原始子任务语义编译新的准备段，失败恢复后从新观测继续，保留已经完成的动作，并在发现准备节点引用旧场景时先重规划观察。 / Use Coordinator-persisted current-scene queries and the original subtask semantics to compile fresh preparation after recovery. Preserve completed actions and refresh the scene when preparation is bound to an earlier revision.

### 文件变更详情 / File changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py` L28、L183–L184。给现有 AgentLoop 接入仿真续接插件。 / Attach the simulation continuation plugin to the existing AgentLoop.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/subtask_continuation.py` L1–L239。根据当前修订的查询回执恢复语义绑定，再通过既有准备段编译器保留工艺查询到实际动作的参数依赖。 / Rebind from current Query receipts and use the existing subtask composer to preserve argument dependencies from process Queries to the Action.
- [eval] [exp] `examples/forge-adapters/isaacsim_lab/tests/test_subtask_continuation.py` L1–L243。验证安全失抓后续接、第二瓶换用新场景、保留已完成动作，以及已发布查询的参数兼容性。 / Cover safe-failure continuation, scene refresh for the second bottle, retention of completed actions, and published Query argument compatibility.

```diff
- planner_plugin=AgentRecoveryDecisions(provider, model, coordinator, ...)
+ planner_plugin=LabSubtaskContinuation(provider, model, coordinator, sensor_ref=sensor_ref, ...)
+ records = current_scene_query_records(task)
+ rebound = spec.model_copy(update={"binding": binding, "depends_on": ()})
+ composed = compose_subtask_plan(..., (rebound,), ...)
```

### 验证 / Validation

- [eval] [exp] 17 项宿主和续接测试通过。21:18:30 轮已实测 R05 抓取抬升 58.01 mm，倾倒和第二瓶结果待该轮结算。 / All 17 host and continuation tests passed. The 21:18:30 replay measured a successful 58.01 mm R05 lift. The pour and second bottle remain in progress.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `bc841612`，`feature/planning-loop`，2026-11-24 21:37:20 +0800。
