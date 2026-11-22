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

## v17.8.14 (2026-11-22 13:05) - codex

### 双瓶流程实测 / Two-bottle simulation

- [eval] [exp] 40 N 驱动上限、2 mm 预紧下，R05 抬升时瓶身相对夹爪的峰值位移从历史轮的 9.5 mm 降到 3.5 mm。但向烧杯搬运期间仍累计约 1.008 rad 相对转动，2,058 个采样均维持双侧接触。修正姿态需要 0.822 rad 关节变化，超过 0.500 rad 上限；峰值瓶身倾角 0.764 rad，合格保持 0 秒。未进入原位放回或 R06。 / At a 40 N drive cap and 2 mm preload, R05 peak relative travel during lift fell from 9.5 mm in the earlier run to 3.5 mm. During transport, relative rotation reached 1.008 rad despite 2,058 bilateral samples. Pose correction required a 0.822 rad joint change, exceeding the 0.500 rad limit. Peak tilt was 0.764 rad with zero aligned hold. Neither return nor R06 was reached.
- [eval] [exp] 终态和影片见 `out/labutopia-elevated-20261122/v17.8.13-r05-r06-124313` 的 `acceptance.json`、`artifacts/labutopia/phase-feedback/6eba1492b59c4213a497a3ddbc20f96f.json` 和 `artifacts/labutopia/phase-video/8aeeba8020fa410b88af1768936ae874.mp4`。 / See these files for the terminal receipt, detailed feedback, and video.
- [eval] [exp] 指垫对照轮启动于 `out/labutopia-elevated-20261122/v17.8.14-r05-r06-pad-130444`，`labutopia-ridgebase-physics.json` L2–L11 记录唯一物理参数差异。沿用双瓶顺序、夹爪驱动上限、预紧、碰撞和关节连续性检查。 / The pad comparison run uses the same two-bottle order, drive cap, preload, collision checks, and joint continuity limit. Its simulation physics file records the parameter change.

```diff
- "static_friction": 0.8,
- "dynamic_friction": 0.6,
+ "static_friction": 2.0,
+ "dynamic_friction": 1.5,
```

### Git 提交 / Git Commit

- 回执记录提交 / Receipt-record commit `020b97de`，2026-11-22 13:05:46 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.

## v17.8.13 (2026-11-22 12:41) - codex

### 瓶口与瓶轴求解 / Bottle tip and axis IK [完成 / Completed]

- [eval] [fix] 对照轮在进倾倒时因完整姿态补偿无解而停止，仍有双侧接触。完整姿态补偿失败时，倾倒和撤离阶段尝试求解瓶口位置与瓶轴方向。仍按关节位移上限、实测碰撞、倾角与保持时间判断执行结果。 / The comparison run could not solve a full pose at pour entry despite bilateral contact. If full pose correction fails, process and exit try tip position and bottle axis. Joint continuity, measured collisions, tilt, and hold still determine the outcome.
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2563–L2595；`examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3313–L3390。 / Cover feature IK failure, successful process tracking, exit seed retry and joint continuity.
```diff
- if stage != "transport" or not point["attached"]:
-     raise PhaseMotionError("inverse_kinematics_failed", ...)
+ elif point["attached"] and stage in {"process", "exit"}:
+     for seed in (start, planned):
+         goal, valid = local_tool_inverse_kinematics(
+             self.tcp, target_body, relation, tool, seed, self.limits,
+             self.config["position_tolerance_m"])
+         if valid:
+             break
+ if not valid:
+     raise PhaseMotionError("inverse_kinematics_failed", ...)
```
- [eval] [exp] 214 项 Isaac motion 测试通过。以 40 N 驱动上限、2 mm 保压位移进行下一轮同场景双瓶仿真，配置、复现命令和反馈目录为 `out/labutopia-elevated-20261122/v17.8.13-r05-r06-124313`。 / 214 Isaac motion tests passed. The next same-scene two-bottle run uses a 40 N drive cap and 2 mm preload offset. Its directory records configuration, replay command and feedback.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `a5a9835b`，2026-11-22 12:44:11 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送。 / Pushed.

## v17.8.12 (2026-11-22 12:15) - codex

### 夹爪保压和原位归还 / Grip preload and return to the original slot [完成 / Completed]

- [eval] [fix] 倾倒、放置和搅拌接棒时，对启用保压的配置沿用有界预紧位移，释放时按既有指令开爪。 / For deployments with hold following enabled, apply the configured preload once when entering pour, place, or stir. Release uses the existing opening target. (local)
- [eval] [fix] 历史 R05 归位在回程积累了 0.240 rad 的夹持旋转偏移，之后下降时撞入桌面包络。新版下降前若发现超出既有运动容差的偏移，使用实测 TCP 和瓶身关系重新验证余下路线，保持原归位姿态，验证失败时不执行下降和释放。 / The historical R05 return accumulated 0.240 rad of attachment rotation before descent hit the table envelope. When the measured relation now differs beyond existing motion tolerances, requalify leveling, descent, release, and retreat to the same original pose. Failed qualification stops before descent and release. (local)

### 文件变更详情 / File Changes

- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L707–L713、L1369–L1370、L2458–L2464、L2527–L2543、L2840–L2846。 / Share placement waypoints with preparation, keep hold preload, and execute the freshly qualified placement suffix using the measured terminal target.
```diff
- finger_target = measured_fingers
+ finger_target = np.maximum(measured_fingers - retain_overshoot, 0.0)  # opted-in held phases
- waypoints = [(above, 0., "transport"), ...]  # preparation only
+ waypoints = place_waypoints(original_return, tcp_from_object, self.config)
+ if operation == "place" and stage == "lower" and not place_pose_checked:
+     relation = np.linalg.inv(self.tcp(start)) @ self.observed_pose(source)
+     # If drift exceeds existing tolerances, qualify before issuing commands.
+     waypoints = place_waypoints(supported_pose, relation, self.config)
+     points = iter(self.qualify(waypoints, source, relation, operation,
+                                supported_pose, initial_joints=start)["steps"])
```
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3167–L3282。 / Covers configured preload, default grip target, opening on release, measured pose correction, the unchanged route without drift, and blocking descent on failed qualification.
```diff
+ assert all(command[7:] == pytest.approx(expected) for command in commands)
+ assert commands[-1][7:] == pytest.approx([.04, .04])
+ assert len(qualification_calls) == int(drift)
+ assert route == saved_route
+ assert all(command[7] < .035 for command in commands)  # blocked correction
```
- [docs] [docs] `.task/current.md` L730–L731、`CHANGELOG.md` L53 及月度归档 L780 起记录安全边界、验证与复现。 / Record ownership, validation and reproduction in the task note, index and monthly archive.

### 验证 / Validation

- [eval] [exp] 211 项 Isaac phase-motion、4 项 elevated USD 和 49 项工作流回归通过。测试覆盖动态重验通过与碰撞失败，实测完整链路以单独的 Isaac 回馈为准。 / Passed 211 Isaac phase-motion, 4 elevated USD and 49 workflow tests. Full physical simulation proof comes from the independent Isaac feedback.
- [eval] [exp] 仿真专用配置将指爪驱动上限从 20 N 提高到 40 N，预紧位移从 2 mm 提高到 4 mm。R05 与相邻的 R06 已排入同一任务，角度 1.0 rad，各自对准保持至少 2.0 s，共用原有碰撞检查、回馈和归位后再继续的流程。配置、命令、回执和视频路径保存于 `out/labutopia-elevated-20261122/v17.8.12-r05-r06-corrected-122218`，完整运行在 R05 搬运时丢失双侧接触，未进入归位或开始 R06。仅调高驱动上限和预紧量的对照轮保持 2052 帧双侧接触，但未求得倾倒姿态。 / The simulation trial uses a 40 N drive cap and 4 mm preload offset in place of 20 N and 2 mm. R05 and its neighbor R06 are ordered in one scene at 1.0 rad for at least 2.0 s of aligned hold each and advance only after return. The run directory holds configuration, command and feedback. The corrected run lost bilateral contact during R05 transport, before placement or R06. The comparison run preserved 2,052 bilateral samples but could not solve the pour pose.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `f4c08ec6`，2026-11-22 12:27:24 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送并核对远端引用。 / Pushed and verified against the remote ref.

## v17.8.11 (2026-11-22 10:53) - codex

### 持瓶搬运与倾倒回馈 / Held Transport and Pour Feedback [完成 / Completed]
- [eval] [fix] 倾倒搬运的两次姿态补偿求解均失败时，以现有关节位移上限检查原计划点，再逐步按实测瓶姿检查碰撞。倾倒保持按双侧接触、瓶口对准和实际倾角计时。 / If both pose correction attempts fail during pour transport, check the planned waypoint against the existing joint-step limit, then check each step for collisions using the measured bottle pose. Evaluate the pour hold using bilateral contact, lip alignment and measured tilt. (local)
- [eval] [fix] IsaacSim Adapter 负责实测持瓶反馈、候选关节目标与碰撞检查。任务参数和实测反馈继续通过既有接口交给工作流结算。 / The IsaacSim Adapter owns measured grip feedback, candidate joint targets and collision checks. The workflow settles the operation using the existing task parameters and feedback interface. (local)

### 文件变更详情 / File Changes
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2476-L2483、L2541-L2561、L2585-L2593、L2698-L2712。
```diff
- "grasp_valid": held
+ grasp_valid = contact_load_valid if operation == "pour" else held
+ "grasp_valid": grasp_valid
- if not valid: raise PhaseMotionError("inverse_kinematics_failed", ...)
+ if not valid:
+     if stage != "transport" or not point["attached"]:
+         raise PhaseMotionError("inverse_kinematics_failed", ...)
+     goal = np.asarray(point["joints"])
- if valid and delta > maximum_delta:
+ if delta > maximum_delta:
```
- [eval] [fix] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3196-L3290。 / Cover motion with drift, measured hold, discontinuity, and pre-command collisions.
```diff
+ assert result["measurements"]["qualified_tilt_hold_s"] >= .1
+ assert all(sample["attachment_rotation_error_rad"] > model.config["grasp_rotation_tolerance_rad"]
+            and sample["grasp_valid"] for sample in process_samples)
+ assert relation == pytest.approx(observed_relation)
```
- [docs] [docs] `CHANGELOG.md` L53-L88 与 `changelog/2026-11_part3.md` L744-L779 收录双语记录。 / Record the complete entry in the latest five versions and the monthly archive.

### 验证 / Validation
- [eval] [exp] IsaacSim phase-motion / elevated USD 回归 209 项通过，工作流 cycle protocol / feedback adapter / held manipulation 回归 49 项通过。 / 209 IsaacSim phase-motion and elevated USD tests plus 49 workflow tests passed. 旧样本 1651 到计划点 61 的最大关节差为 0.3920 rad，低于现有 0.5 rad 上限。 / The largest joint delta from historical sample 1651 to planned waypoint 61 was 0.3920 rad, within the existing 0.5 rad limit.
- [eval] [exp] LabUtopia R05→BEAKER 仿真（`out/labutopia-elevated-20261122/v17.8.11-full-run`）抓取与倾倒成功，实测峰值 1.0068 rad，连续对准保持 2.8333 s，4073 条倾倒回馈均有双侧接触，最大相对旋转偏差 0.5184 rad。未测量液体转移。放回在 lower 阶段以 `payload_collision` 拒绝，瓶身包络与桌面重叠，仍有双侧接触，整任务失败。 / The R05→BEAKER simulation completed acquisition and pour with 1.0068 rad peak tilt, 2.8333 s of continuous aligned hold, bilateral contact in all 4,073 pour samples and 0.5184 rad maximum attachment rotation error. Liquid transfer was unmeasured. Placement stopped during lowering on a payload-envelope overlap with the table while bilateral contact persisted. The overall task failed.

### Git 提交 / Git Commit
- 实现提交 / Implementation commit `243803f1`，2026-11-22 11:08:52 Asia/Shanghai，分支 / branch `feature/planning-loop`。已推送并核对远端引用。 / Pushed and verified against the remote ref.
