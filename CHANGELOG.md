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
