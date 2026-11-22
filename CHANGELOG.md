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

## v17.8.10 (2026-11-21 21:51) - codex

### 静态烧杯几何与载荷盒关系复核 / Static Beaker Geometry and Payload-Box Relationship Review [完成 / Completed]
- [eval] [exp] 以保存的R05点云/标定和生产坐标变换重算9个观测表面盒，确认waypoint71命中最低层box0；其局部半尺寸范数上界为50.60mm，失败中心至烧杯mesh世界Z上界相距30.73mm，故局部half不能与世界AABB逐轴直接比较。失败时盒旋转未保存，不能精确重放查询。 / Recompute 9 observed-surface boxes from the saved R05 cloud/calibration using production transforms and confirm waypoint71 hits lowest slab box0. Its local half-extent norm is an upper bound of50.60mm versus a30.73mm vertical gap from the failure center to the beaker mesh world-Z bound, so local half-extents cannot be compared directly to the world AABB. The hit-time box rotation is absent, preventing exact query replay. (local)
- [eval] [exp] 静态USD显示烧杯1698点/3408面、collision enabled、`convexDecomposition`、scale `[0.0004,0.0005,0.0004]`；PhysX日志另有ScaleOrientation warning。根scene无单位/up-axis元数据、tabletop sublayer为1m/Z-up；静态根stage读取的`.01m`/Y-up是fallback，运行时显式构造传入`stage_units_in_meters=1.0`，但运行时up-axis没有落盘读回。不能据此确认cook错误、物理穿透或坐标根因。 / Static USD shows a1,698-point/3,408-face beaker mesh, collision enabled, `convexDecomposition` and scale `[0.0004,0.0005,0.0004]`; the PhysX log also contains a ScaleOrientation warning. The scene root omits units/up-axis while its tabletop sublayer authors1m/Z-up; `.01m`/Y-up from static root-stage opening is a fallback, and runtime construction explicitly passes `stage_units_in_meters=1.0`, but runtime up-axis was not read back. This does not establish a cooking defect, physical penetration or frame root cause. / (local)
- [决策边界 / Decision boundary] 维持布局、阈值和运动代码；下一步若继续，只读检查命中时实际cook凸分解与OBB姿态。持瓶关系漂移仍为独立未决问题，未执行仿真、物理步进或机械臂动作。 / Retain placement, thresholds and motion code; if continued, read-only inspect the cooked convex decomposition and OBB pose at the hit. Held-object relation drift remains a separate open issue; no simulation, physics step or arm motion was performed. (local)

### 文件变更详情 / File Changes
- [docs] [docs] [修改 / Modified] `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` L100-L120：记录生产观测盒复算、失败box0、烧杯mesh/碰撞近似、OBB投影边界、USD静态单位来源及未决项。 / Record the production-box recomputation, failure box0, beaker mesh/collision approximation, OBB projection bound, static USD metadata source and open questions.
```diff
- 下一步：静态复核首个process目标与9个观测载荷盒。
+ 结果：box0的OBB局部半尺寸不能与世界AABB逐轴比较；cook后凸分解及命中姿态仍待只读核对。
```
- [docs] [docs] [修改 / Modified] `changelog/2026-11_part3.md` L707-L733：归档静态几何复核、范围受限的OBB投影解释、USD元数据来源、Diff和验证。 / Archive the static geometry review, bounded OBB projection interpretation, USD metadata provenance, diff and validation.

### 验证 / Validation
- [eval] [chore] 使用本机pxr静态读取保存的scene root、tabletop sublayer和TargetBeaker mesh；Python离线读取点云/calibration/route并按生产变换重算9盒及OBB投影上界。UTF-8回读与`git diff --check`通过；未启动Isaac、未推进仿真、无动作命令。 / Use local pxr to statically inspect the saved scene root, tabletop sublayer and TargetBeaker mesh; offline Python reads the saved cloud/calibration/route and recomputes9 boxes and the OBB projection bound using production transforms. UTF-8 readback and `git diff --check` pass; Isaac was not started, simulation did not advance, and no motion command was issued. (local)
- [eval] [chore] 受跟踪源码、运动配置、USD部署资产、布局及阈值均未改；仅更新诊断报告与日志。 / Tracked source, motion configuration, USD deployment assets, placement and thresholds are unchanged; only the diagnostic report and logs are updated. (local)

### Git提交与推送回执 / Git Commit and Push Receipt [完成 / Completed]
- 实现提交 / Implementation commit：`4fd42f64207ea2614940a72a5a2c048336e0b3a9`；2026-11-21 22:58:08 Asia/Shanghai，`feature/planning-loop`。 / Implementation commit `4fd42f64207ea2614940a72a5a2c048336e0b3a9` at 2026-11-21 22:58:08 Asia/Shanghai on `feature/planning-loop`.
- `git push origin feature/planning-loop`成功；22:58:54由`git ls-remote`核验远端完整指针为`4fd42f64207ea2614940a72a5a2c048336e0b3a9`。 / Push succeeded; `git ls-remote` verified the full remote ref at 22:58:54 Asia/Shanghai.

## v17.8.9 (2026-11-21 14:19) - codex

### 失败边界Lula路线后缀无动作资格复核 / No-Motion Lula Route-Suffix Qualification at the Failure Boundary [完成 / Completed]
- [eval] [exp] 使用sample 1651的实测TCP/object关系检查zero-based waypoint 61至124共64点后缀。与readiness的scene revision/calibration匹配的R05点云有1,214个有限点，生产变换生成9个观测表面载荷盒；首个process目标waypoint 71的插值因载荷盒与烧杯mesh重叠而拒绝。 / Qualify the 64-waypoint suffix from zero-based waypoint 61 through 124 using the measured TCP/object relation at sample 1651. The R05 cloud matching readiness scene revision/calibration has 1,214 finite points and yields 9 observed-surface payload boxes with the production transform; interpolation toward the first process target, waypoint 71, is rejected on overlap with the beaker mesh. (local)
- [eval] [exp] 拒绝前完成9,992次overlap查询，local-IK fallback为0；64点后缀未全部检查，不能据此断言整段路线失败或发生物理穿透。`simulation_steps`和`motion_commands`均为0，reset关节/时间不变。 / The run completes 9,992 overlap queries with 0 local-IK fallbacks before rejection. The 64-point suffix is incomplete, so this does not establish whole-route failure or physical interpenetration. `simulation_steps` and `motion_commands` are 0; reset joints/time are unchanged. (local)
- [决策边界 / Decision boundary] 保留机座布局与阈值；下一步只读复核首个process姿态、烧杯碰撞几何及观测表面载荷盒。持瓶关系漂移仍未解决，本检查不授权动作。 / Preserve placement and thresholds. Next, review the first process pose, beaker collision geometry and observed-surface payload boxes. Held-object relation drift remains unresolved; this check does not authorize motion. (local)

### 文件变更详情 / File Changes
- [docs] [docs] [修改 / Modified] `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` L79-L102：新增点云/坐标绑定、payload collision拒绝、检查中止范围、无动作读回和下一决策。 / Add cloud/frame binding, payload-collision rejection, stop boundary, no-motion readbacks and next decision.
- 关键Diff / Key diff：原计划“检查64点路线后缀” → 实际“waypoint71首个process插值触发payload_collision，后续点未检查”。 / Key change: planned 64-point suffix check → actual `payload_collision` at interpolation toward waypoint71; later points remain unchecked.
- [docs] [chore] `out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/qualify-lula-route-suffix.py` L83-L114：验证point-cloud、calibration与geometry sidecar的scene/frame/entity引用，将R05点云复制至隔离artifact store，并用生产坐标变换与route关系绑定观测载荷几何；脚本和JSON保留本地，不纳入Git。 / Validate point-cloud, calibration and geometry-sidecar identities, copy R05 to an isolated artifact store, and bind observed payload geometry using the production transform and route relation; keep the script and JSON local and outside Git. (local)
- [docs] [chore] `changelog/2026-11_part3.md` L673-L705：记录本版本计划、结果、报告/脚本行号、验证及实现/回执提交和推送核验。 / Record this version's plan, result, report/script line references, validation, implementation/receipt commits and push verification.
```diff
- route suffix qualification pending
+ payload_collision at process waypoint71; remaining suffix unchecked
```

### 验证 / Validation
- [eval] [chore] 诊断脚本`py_compile`及已保存JSON字段断言通过；JSON记录`route_suffix_rejected`、`payload_collision`、9,992次查询、0次local-IK fallback、后缀未完成、0步进/0运动命令及reset关节/时间不变。此前的LabUtopia无动作运行已记录于JSON，本次收尾未重启仿真。 / Script byte-compilation and assertions against the saved JSON pass. The JSON records `route_suffix_rejected`, `payload_collision`, 9,992 queries, 0 local-IK fallbacks, an incomplete suffix, 0 simulation steps/commands and unchanged reset joints/time. The earlier no-motion LabUtopia run is recorded there; simulation was not restarted for this closeout. (local)
- [eval] [chore] 三份文档UTF-8回读、最近五版本核对与`git diff --check`通过；生产源码、配置、布局和阈值未改。 / UTF-8 readback of all three documents, latest-five verification and `git diff --check` pass; production source, configuration, placement and thresholds are unchanged. (local)
