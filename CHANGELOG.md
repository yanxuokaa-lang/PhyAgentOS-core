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

## v17.9.1 (2026-11-22 14:25) - codex

- [eval] [exp] R05 的 Isaac 抓取、倾倒和归位均成功。倾倒峰值 1.0103 rad，对准连续保持 2.85 s。倾倒阶段滑移最大 2.65 mm，610/610 采样双侧接触。松夹后撤后归位误差 0.736 mm、0.00275 rad。 / R05 passed acquisition, pour and placement. Peak tilt was 1.0103 rad, continuous aligned hold 2.85 s, and peak slip during the tilt phase 2.65 mm with bilateral contact in all 610 samples. After release and retreat, return errors were 0.736 mm and 0.00275 rad.
- [eval] [exp] 原双瓶任务在 R05 归位后继续准备 R06。28 个通过几何筛选的候选因场景观测过期而被拒绝，未启动 R06 运动。终态回执、抓取漏斗和三段可播放录像保存在 `out/labutopia-elevated-20261122/v17.8.16-r05-r06-qualified-135042`。 / The original two-bottle task advanced to R06 planning after R05 returned. Its 28 geometry-qualified candidates were rejected because their scene observation was stale, before R06 motion. The run directory contains the terminal receipt, qualification funnel, and three playable videos.
- [eval] [exp] 已启动同一 Isaac 场景内的顺序复跑，由两个独立任务在各自启动时取像，见 `out/labutopia-elevated-20261122/v17.9.0-r05-r06-fresh-142453`。 / Started a sequential replay in one Isaac scene with separate, freshly observed tasks. The replay directory contains the launcher and run output.

- [docs] [docs] `CHANGELOG.md` L53–L61；`changelog/2026-11_part3.md` L905–L913。本次只追加仿真证据。 / Added simulation evidence only.

## v17.9.0 (2026-11-22 13:48) - codex

- [eval] [fix] R05 搬运第 67 个零基路点实测需 0.635 rad 才能切回原路径，相邻原路点的最大关节位移只有 0.054 rad。持瓶搬运现在始终沿已验证的关节路点，每步仍从实测关节检查限制，按实测瓶姿检查碰撞和双侧接触。倾倒与撤离仍根据实测瓶姿求解。 / At zero-based transport waypoint 67, R05 needed 0.635 rad to return to the qualified route, while neighboring route points were only 0.054 rad apart. Attached transport now follows the qualified waypoints throughout, with live joint continuity, payload collision and bilateral contact checks. Process and exit continue to solve from measured bottle pose.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2563–L2599；`examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3153–L3154、L3312–L3341、L3389–L3457。 / Verify qualified transport without a pose solve, collision and joint-limit rejection before command, and subsequent measured alignment and hold.

```diff
- # Try measured pose correction throughout transport, then fall back.
+ elif operation == "pour" and stage == "transport" and point["attached"]:
+     delta = joint_delta(start, goal)
+     if delta > maximum_delta:
+         raise PhaseMotionError("ik_discontinuity", ...)
```

- [eval] [exp] 213 项 phase-motion 回归通过。前一轮失败回执见 `out/labutopia-elevated-20261122/v17.8.15-r05-r06-continuity-132709/acceptance.json`；本轮沿用相同夹爪参数，输出保存于 `out/labutopia-elevated-20261122/v17.8.16-r05-r06-qualified-135042`。 / Passed 213 phase-motion regressions. The previous run directory contains the failure receipt. The replay uses the same gripper settings and stores outputs in the new run directory.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `f36095fb`，2026-11-22 13:52:29 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.

## v17.8.15 (2026-11-22 13:25) - codex

- [eval] [fix] 持瓶搬运中的补偿解超过现有 0.50 rad 上限时，先以原路点为初值重试；再不可用时，只在原路点本身通过同一上限时采用。执行器仍按实测瓶姿检查碰撞和双侧接触。倾倒过程和归位的验收不变。 / During attached transport, retry an out-of-range compensation from the planned seed. If neither correction qualifies, use the original waypoint only within the same 0.50 rad bound. The runtime still checks the measured payload for collisions and bilateral contact. Process and placement acceptance are unchanged.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2563–L2595；`examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3312–L3343、L3433–L3490。 / Cover alternate-seed retry, qualified nominal continuation, over-limit rejection, and collision rejection before a command.

```diff
- if not valid:
+ if not valid or (attached_transport and joint_delta(start, goal) > maximum_delta):
      goal, valid = local_inverse_kinematics(self.tcp, target, planned, ...)
+     if attached_transport and (not valid or joint_delta(start, goal) > maximum_delta):
+         goal, valid = planned, True
      # The existing joint-delta check still applies.
```

- [eval] [exp] 指垫对照轮 `out/labutopia-elevated-20261122/v17.8.14-r05-r06-pad-130444` 的 R05 搬运最大相对位移由 9.1 降至 3.5 mm，最大相对旋转由 1.008 降至 0.515 rad；1,967 个采样均有双侧接触。姿态补偿仍需 0.635 rad，未完成倾倒、归位或 R06。 / The pad trial reduced peak relative transport displacement from 9.1 to 3.5 mm and rotation from 1.008 to 0.515 rad with 1,967 bilateral samples. Correction still required 0.635 rad, leaving pour, placement and R06 incomplete.
- [eval] [exp] 218 项 phase-motion 测试通过。修复后由同配置重新运行，命令、配置和回执目录为 `out/labutopia-elevated-20261122/v17.8.15-r05-r06-continuity-132709`。 / Passed 218 phase-motion tests. The same-configuration replay stores its command, configuration and receipts in that directory.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `3ebacfef`，2026-11-22 13:28:02 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.
