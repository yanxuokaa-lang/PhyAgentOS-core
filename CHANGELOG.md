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

## v17.9.8 (2026-11-24 20:55) - codex

- [eval] [fix] [完成] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py` 与宿主测试。预先绑定同运行时已有的语义抓取发现查询，让任务恢复可以在新观测上获取理解、候选与能力回执。补充宿主计划指引，使用当前场景发现证据，保持已完成动作及原有动作准入。 / Enroll existing semantic discovery Queries so a task can collect understanding, candidates and capabilities from a fresh observation. Guide the host to keep settled effects and use current scene evidence before preparing the next bottle. (local)

### 文件变更详情 / File changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py` L50–L54、L124。登记四个语义发现查询，说明恢复后重新获取当前观测与候选。 / Enroll all four semantic discovery queries and describe the current observation and candidate requirements for recovery.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py` L62–L63、L178–L182。验证真实运行时查询绑定和计划指引。 / Check real Runtime Query bindings and host guidance.

```diff
-        ("scene.observe", "query"),
+        *((tool_id, "query") for tool_id in PerceptionBindingAdapter._QUERY_SPECS),
```

### 验证 / Validation

- [eval] [exp] 12 项宿主测试通过。21:01:49 启动复跑，R05 和 R03 同任务完成及恢复后重抓仍待实测。 / All 12 host tests passed. The 21:01:49 replay is running, with same-task completion and reacquisition still to verify.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `c0ca2529`，`feature/planning-loop`，2026-11-24 21:06:09 +0800。

## v17.9.7 (2026-11-24 20:29) - codex

- [eval] [fix] [完成] 修改 `phase_motion.py` 与阶段测试。实测 R05 抬升失败时瓶底回到支撑高度，已无双侧承载但仍报告双侧零载接触；允许仅原地开夹，验证空夹与稳定支撑后沿已验证路径回撤，交接同任务恢复决策。 / In the measured R05 lift failure the bottle was back at support height with zero-load residual contact. Permit opening at the fixed arm pose and verify empty grip and stable support before the qualified reverse path and same-task recovery. (local)

### 文件变更详情 / File changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L844–L856、L2353、L2382–L2405、L2449–L2485。检查两指最新采样、接触负载、瓶位与支撑高度。冻结开夹时的手臂目标，开夹后和撤离后确认瓶身稳定及双指脱离。 / Check current finger samples, load, bottle pose and support height. Hold the arm target fixed during opening and verify stable support and clearance before and after retreat.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2331–L2394。覆盖零载接触成功、单侧载荷、过期采样、支撑高度异常、开夹后残留接触或负载、瓶身移动。 / Cover zero-load residual contact recovery and rejection of unilateral load, stale samples, unsupported height, continued contact or load, and bottle movement.
- [docs] [docs] `.task/current.md` L744–L746。记录适配器与 AgentLoop 的职责和证据边界。 / Record ownership and evidence boundaries.

```diff
- if held or contact_load_valid or contact_manifold_valid or not supported:
+ clear = contact_window.current_unloaded(require_clear=True, whole_interval=False)
+ residual_unloaded = (
+     failure == "physical_grasp_lost"
+     and support_contact_allowed("lift", physical_body, original, tolerance)
+     and contact_window.current_unloaded()
+ )
+ if held or not supported or not (clear or residual_unloaded):
      raise PhaseMotionError("acquire_recovery_possession_uncertain", ...)
- command(self.joints(), fingers, "recovery_open", True)
+ command(opening_arm, fingers, "recovery_open", True)
+ verify_empty("recovery_open_check")
```

### 验证 / Validation

- [eval] [exp] 232 项运动阶段测试通过，包含新增的 7 种失抓恢复场景。使用 20:03:32 的仿真配置启动同任务复跑，证据保存在 `out/labutopia-elevated-20261124/v17.9.7-r05-r03-agent-loop-recovery-203551`。 / All 232 motion phase tests passed, including seven recovery cases. A same-task replay using the 20:03:32 simulation profile was started and its evidence is stored at the listed path.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `e85b9628`，`feature/planning-loop`，2026-11-24 20:36:17 +0800。

## v17.9.6 (2026-11-24 20:00) - codex

- [eval] [fix] [完成] 修改 `phase_motion.py` 中已完成归位运输后的下降重验证，从实测关节和夹持姿态求解剩余下降、释放和后撤。上一轮高位重复修正遇腕限位，跳过已完成的运输段后 13 个实测回放路点通过碰撞和限位资格检查。 / Requalify the remaining descent, release and retreat from measured joints and attachment after return transport completes. The repeat high approach hit a wrist limit, while all 13 remaining waypoints passed simulator collision and limit qualification. (local)
- [eval] [fix] [完成] 更新 `test_phase_motion.py` 以验证重验证的阶段范围和失败时保持夹持。 / Verify remaining-stage qualification and retained possession when qualification fails. (local)


### 文件变更详情 / File changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2622–L2632，运输结束后，从实测状态验证剩余三个阶段。 / After completed transport, qualify the remaining three stages from the measured state.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3310–L3327，验证重算顺序，保留碰撞拒绝后继续持瓶的断言。 / Assert remaining-stage order and retained grip upon collision rejection.
- [docs] [docs] `.task/current.md` L740–L742，记录适配器与 AgentLoop 的职责及实测验收。 / Record adapter and AgentLoop ownership and measured acceptance criteria.

```diff
  waypoints = place_waypoints(supported_pose, relation, self.config)
+ if last_stage == "transport":
+     waypoints = waypoints[1:]
  points = iter(self.qualify(waypoints, source, relation, operation, supported_pose,
                             initial_joints=start)["steps"])
```

### 验证 / Validation

- [eval] [exp] 225 项阶段运动测试通过。历史实测腕部终态回放中，重复运输触及限位，剩余下降、释放、撤离的 13 个路点通过原有仿真碰撞和限位检查。 / All 225 phase-motion tests pass. In the measured-state replay, repeating transport hits the joint limit, and the 13 remaining descent, release and retreat waypoints pass the existing simulation collision and limit checks.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `005fc4be`，`feature/planning-loop`，2026-11-24 20:03:02 +0800。
