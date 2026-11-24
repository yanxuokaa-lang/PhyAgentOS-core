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

## v17.9.5 (2026-11-22 17:28) - codex

- [eval] [exp] v17.9.4 复跑中 R03 实测 0.996807 rad、连续 2.800 s，末端补偿将瓶口误差从 3.419 降至 0.188 mm，瓶轴误差从 0.14755 降至 0.00371 rad。倾倒成功，随后的原位放回准备在 transport 报 `joint_limit_violation`，未归位或启动 R05。回执位于 `out/labutopia-elevated-20261122/v17.9.4-r03-r05-agent-controller-165606`。 / R03 completed the qualified pour. Terminal correction reduced tip error from 3.419 to 0.188 mm and axis error from 0.14755 to 0.00371 rad. Place preparation reported a joint-limit violation in transport and R05 remained pending.
- [eval] [fix] 在 `phase_motion.py` 的既有路线资格验证中，主逆解越界时尝试原有有界局部逆解。适配器负责关节解与碰撞，Agent 继续负责双瓶顺序和任务恢复。新增测试覆盖首解越界且局部解通过或同样不可用。 / Try the existing bounded local IK if the primary solution falls outside limits. The Adapter owns kinematics and collision, and the Agent owns task sequencing and recovery.

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L1832–1844 及 `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2145–2197。 / Test an in-bounds fallback, rejection of an unusable fallback, and collision after fallback.

```diff
- if not primary_success or primary_delta > maximum_delta or force_local:
+ if not primary_success or primary_delta > maximum_delta or force_local or place_limit_failure:
      local_goal, local_success = local_inverse_kinematics(...)
+     # Retain the joint-limit failure if the nearby solution is unusable.
```

- [eval] [exp] 225 项阶段运动测试通过。用历史实测终态回放找到 73 个满足关节约束的回程路点。此回放用于逆解诊断，完整场景复跑保存在 `out/labutopia-elevated-20261122/v17.9.5-r03-r05-agent-controller-173044`。 / Passed 225 motion tests. Kinematic replay from the historical measured pose found 73 in-limit return waypoints. The listed directory preserves the full simulation run.

- [eval] [exp] 在独立 Isaac 仿真中用历史终态关节、夹爪开度、瓶姿和点云回放，通过 73 个放回路点的碰撞验证。实际执行结果以完整复跑回执为准。 / A separate Isaac scene replayed the measured joints, finger openings, bottle pose and point cloud and passed all 73 placement waypoints. Full execution is tracked by the live simulation receipts.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `fcf879e7`，2026-11-22 17:31:09 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.

## v17.9.4 (2026-11-22 16:52) - codex

- [eval] [fix] `phase_motion.py` 与 `test_phase_motion.py` 补上重新验证后的撤离末端补偿。首轮 R03 为 0.996807 rad、2.800 s，撤离全段保持接触但末端瓶轴残差 0.14755 rad。继续使用相同验证与实测终态条件。 / Correct terminal drift after requalified pour exit. R03 held 0.996807 rad for 2.800 s and retained grip through exit, but the measured terminal tool axis error was 0.14755 rad. Reuse existing validation and terminal measurements.
- [eval] [fix] `held_manipulation.py` 和对应测试让分阶段倾倒结果采用既有倾倒轨迹测量中的合格保持时长。首轮 R03 已达到轨迹验收，运行时投影仍要求峰值达到 1.000000 rad，造成两处验收冲突。 / Use the existing qualified-interval measurement in the phase result projection. The measured R03 trajectory qualified within the configured band, but projection independently imposed a one-sided 1.000000 rad peak.

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L159–166、L2529、L2589–2612、L2959–2965、L2984–2985；`examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3390–3530。补偿一次后重新测量，碰撞与残余偏差仍返回失败。 / Apply one measured correction, then verify again. A collision or persistent endpoint error still fails.
- [eval] [fix] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/held_manipulation.py` L801–802；`examples/forge-skills/pick-place-workflow/tests/test_held_manipulation.py` L170–190。合格时长和完成标志均须有效，旧版反馈沿用既有峰值判定。 / Require the qualified interval and completion flag. Older providers retain their existing peak check.

```diff
- # Finish after the qualified exit.
+ # If there is residual tool drift, solve one measured terminal correction.
+ goal = self._pour_corrected_joints(start, planned, expected, relation, tool, "exit")
+ # Send the correction through the ordinary attached segment checks.
- return at_least("aligned_hold_s", params["hold_s"]) and at_least("maximum_tilt_rad", params["tilt_rad"])
+ if "qualified_tilt_hold_s" in metrics:
+     return metrics.get("process_completed") is True and at_least("qualified_tilt_hold_s", params["hold_s"])
+ return at_least("aligned_hold_s", params["hold_s"]) and at_least("maximum_tilt_rad", params["tilt_rad"])
```

- [eval] [exp] 311 项阶段运动、宿主和操作回归通过。修复后启动同场景双瓶复跑，目录 `out/labutopia-elevated-20261122/v17.9.4-r03-r05-agent-controller-165606`，保留命令、实施补丁和回执。 / Passed 311 motion, host and manipulation tests. The listed single-scene two-bottle replay preserves its command, implementation patch and receipts.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `6b6ce702`，2026-11-22 16:58:13 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.

## v17.9.3 (2026-11-22 16:19) - codex

- [eval] [fix] 所有实测倾倒修正解先检查关节连续性。若撤离修正解均不可用，确认双侧接触后，从实测关节与瓶姿重新验证剩余撤离路线一次。保留 R03/R05 通用的碰撞、连续性、夹持与终点检查。 / Check continuity for every measured pour correction. If no exit correction qualifies, verify bilateral contact and requalify the remaining exit once from measured joints and bottle pose. Preserve collision, continuity, contact, and end-pose checks. (local)
- [eval] [exp] 在同一 Isaac 场景和 Agent 任务中已启动 R03 → R05 首轮。任务 `task_e3ab1057c7384766`，运行配置和回执目录 `out/labutopia-elevated-20261122/v17.9.3-r03-r05-agent-recovery-162058`。 / Started the first R03 → R05 run in one Isaac scene and Agent task. The listed run directory preserves configuration and receipts. (local)

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2252–L2298、L2579–L2643；`examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3378–L3523。 / Cover continuous exit recovery, qualification collision, live collision and contact loss.
- [docs] [docs] `.task/current.md` L1–L7，记录层归属及仿真验收条件。 / Record layer ownership and simulation acceptance criteria.

```diff
- goal, valid = local_inverse_kinematics(..., start, ...)
- # Check joint delta only for the fallback solution.
+ goal = self._pour_corrected_joints(start, goal, target_body, relation, tool, stage)
+ # After rejecting all corrections in exit, requalify the remaining path
+ # once from measured joints and attachment, only with bilateral contact.
+ qualified = self._qualify_pour_exit(route, remaining_exit, start, relation,
+                                     supported_pose, exc, tracking_refs)
```

- [eval] [exp] 217 项阶段运动测试、138 项恢复/调度/宿主回归通过。首轮启动补丁存于 `implementation.diff`，启动后增加的接触前置检查已独立通过回归。 / Passed 217 motion tests and 138 recovery, controller and host tests. The first run records its startup patch, and the subsequently added contact precheck has separate regression coverage.

### Agent 恢复接线 / Agent recovery wiring

- [eval] [fix] Isaac 宿主注入既有 Agent 恢复规划插件，并在语义建任务时登记 `scene.observe`。Coordinator 根据反馈启动恢复。 / The Isaac host injects the existing Agent recovery planner and enrolls `scene.observe` during semantic task creation. The Coordinator owns recovery.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py` L13、L50–L56、L177–L184；`examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py` L2、L11、L125–L184。
- [eval] [exp] 56 项恢复决策及宿主回归通过。 / Passed 56 recovery and host tests.

```diff
- semantic_plan_builder=AsyncQuerySemanticPlanBuilder(queries)
+ semantic_plan_builder=LabSemanticPlanBuilder(queries)  # enrolls scene.observe
+ planner_plugin=AgentRecoveryDecisions(provider, model, coordinator, ...)
```

### Git 提交 / Git Commit

- 撤离修复 / Exit implementation `56c5ee27`，2026-11-22 16:27:42 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.
- 宿主接线 / Agent host wiring `99f016b0`，2026-11-22 16:36:18 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.

## v17.9.2 (2026-11-22 15:01) - codex

- [eval] [exp] 更正流程顺序为 R03 → R05。同一仿真场景中，R03 倾倒、归位和松夹后撤成功才为 R05 采集新观测。 / Correct the sequence to R03 → R05. In one continuing simulation, acquire a fresh observation for R05 after R03 completes its pour, return, release and retreat.
- [eval] [exp] 40 N 与 60 N 两轮在 R03 抬升开始约 0.18 s 后失去一侧接触，峰值相对位移分别为 7.87 mm 与 8.83 mm。 / With 40 N and 60 N drive caps, R03 lost contact on one side about 0.18 s into the lift. Peak relative displacements were 7.87 mm and 8.83 mm.
- [eval] [exp] 水平预选路线在转腕段触及关节限位。完整路线搜索找到了可执行的水平入夹路径，实测抬升 11/22 样本有效，最大滑移 8.85 mm，未进入倾倒或 R05。 / The preselected level grip route hit a joint limit during transit orientation. Full route search found an executable level approach, but only 11/22 lift samples had a valid grip with 8.85 mm peak slip. Neither pour nor R05 started.
- [eval] [exp] 两个最靠近瓶口的抓取候选均未通过瓶口间隙检查，仿真未运动。 / Both highest grasp candidates failed opening clearance and no motion occurred.

### 本地仿真配置 Diff / Simulation configuration diff

文件位于 / Files under `out/labutopia-elevated-20261122/`。Tracked source stayed unchanged.

- `v17.9.2-r03-r05-level-search-150747/labutopia-oracle-perception.json` L40–L42: `tilt_angles_rad: [0.0, 0.2618, 0.5236, 0.6981] → [0.0]`。
- `v17.9.2-r03-r05-level-search-150747/labutopia-ridgebase-elevated-motion.json` L13–L18: `acquire_route_selection: simulator_truth_preselected → first_feasible`, `acquire_route_strategies: ["staged"] → ["staged", "direct"]`。
- `v17.9.2-r03-r05-high-151906/labutopia-oracle-perception.json` L43–L46: 新增 / add `bottle_depth_fractions: [0.30, 0.35]`。
- `v17.9.2-r03-r05-band-152152/labutopia-oracle-perception.json` L43–L52: `bottle_depth_fractions: [0.30, 0.35] → [0.37, 0.38, 0.39, 0.45, 0.50, 0.55, 0.60, 0.65]`。
- [eval] [exp] 调整候选高度后，整条路线通过验证，但 R03 抬升时仍失去一侧接触，13/25 样本有效，最大滑移 8.76 mm。 / With revised grasp bands, the full route passed validation but R03 still lost contact on one side in lift, with 13/25 valid samples and 8.76 mm peak slip.

### 验证 / Validation

- 执行命令与运行配置见各次本地仿真的 `command.json`、`metadata.json`。用 `ffprobe -v error -show_entries format=duration` 检查可播放视频。 / Each replay preserves its invocation and configuration in those files. Use the listed ffprobe command to check finalized videos.

- [eval] [exp] 4 mm 预紧完成 R03 抬升和倾倒保持（峰值 1.0002 rad，持续 2.90 s），抬升及倾倒过程峰值相对位移 8.58 mm 和 5.51 mm。后撤阶段实测姿态修正逆解不可达，未归位。 / With 4 mm preload, R03 lifted and reached the pour goal (1.0002 rad, 2.90 s). Peak relative displacement was 8.58 mm in lift and 5.51 mm in the pour stage. The measured exit correction was unreachable, so return did not run.

- [eval] [exp] 将倾倒进出间隙从 0.18 m 改为 0.14 m 后，R03 峰值 0.9968 rad，连续保持 2.80 s。撤离修正需跳变 1.01936 rad，超过 0.5 rad 上限，未归位或启动 R05。 / Reducing the process distance from 0.18 m to 0.14 m yielded 0.9968 rad peak tilt and 2.80 s qualified hold. An exit correction required 1.01936 rad versus a 0.5 rad limit. R03 did not return and R05 did not start. (local)
