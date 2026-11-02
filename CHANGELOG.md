# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

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

## v16.6.2 (2026-11-02 12:24) - codex

### 预期修改 / Planned Changes [完成局部修复；完整抓取仍受阻 / Local repair complete; full grasp remains blocked]
- [docs] [docs] 保存复位修复后的真实拒绝分布，区分夹指保守包络、终态干涉、工作空间、开口及 IK 分支问题；在 `.task/` 记录证据与修复边界。 / Save post-reset rejection evidence and distinguish conservative finger bounds, final interference, workspace, aperture and IK branches in a task diagnosis. (local)
- [env] [fix] 在 Isaac Adapter 内修复有实测支持的夹指碰撞表示或候选准备缺陷；优先验证几何覆盖，再接入现有 preparation，保持裕量、全行程、同捕获及完整路线检查。 / Repair evidenced finger collision representation or candidate-preparation defects inside Isaac Adapter, verifying geometry coverage before integration and preserving margins, full travel, same-capture and full-route checks. (local)
- [eval] [chore] 先写失败复现，再运行替代机制/失败路径测试与真实场景无动作验证；不将局部净空或单元测试表述为抓取成功。 / Reproduce failures, run substitution/failure tests and actual-scene no-motion validation; do not equate local clearance or unit tests with grasp success. (local)
- [docs] [docs] 更新开发说明、架构复核、精确行号、Diff 与最近五版本，仅提交本任务文件并推送当前分支。 / Update guidance, architecture review, exact ranges/diffs and latest five entries; commit task-owned files and push the current branch. (local)

### 根因与修复 / Cause and Repair
- [env] [fix] 旧整夹指 AABB 把未占据角落纳入开合扫掠，叠加 3 mm 裕量后过早拒绝桌面附近路径。改为读取当前场景 PhysX cooked convex 全部组件，保守切片后逐盒覆盖完整 prismatic 行程；保持原裕量。 / Whole-finger AABBs swept empty corners and prematurely rejected near-table routes after padding. Read all current-scene PhysX cooked convex components, conservatively slice their solids, and sweep each bound over full prismatic travel with the original margin. (local)
- [env] [fix] 切片包含凸体边与切平面交点，覆盖没有原始顶点的切片；烹制失败、无回调、无组件或无效凸体均拒绝。 / Slice bounds include convex edge/plane intersections, covering slabs without original vertices; missing callbacks, failed cooking, empty components and invalid solids reject. (local)
- [policy] [chore] 机制留在 Isaac Adapter，AgentLoop 语义参数、opaque 选择、同捕获证据、qualified-only 恢复及完整路径检查保持原职责。 / Mechanisms remain inside Isaac Adapter; AgentLoop semantic parameters, opaque selection, same-capture evidence, qualified-only recovery and complete-route checks retain their owners. (local)

### 文件变更详情 / File Changes
- [env] [fix] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/finger_collision.py:L1-L70` 同步 cooked 组件读取与凸体保守切片。 / Synchronous cooked-component loading and conservative convex-solid slicing. (local)
- [env] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L714-L780,L890-L912,L1314` 接入实例代理/最终变换/cooked 包络，保存夹指环境与自碰撞私有几何诊断。 / Integrate instance proxies, final transforms and cooked bounds; retain private finger/environment/self-overlap geometry. (local)
- [eval] [chore] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_finger_collision.py:L1-L150` 13 项几何、完整扫掠、替代烹制/查询、失败路径与裕量回归。 / Thirteen geometry, full-sweep, substituted cooking/query, failure and margin regressions. (local)
- [eval] [chore] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/scripts/inspect_collision_receipt.py:L60-L61,L99-L100,L113` 保留实际 cooked 证据和新拒绝诊断。 / Preserve actual cooked evidence and replay rejection diagnostics. (local)
- [docs] [docs] [修改 / Modified] `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md:L194-L214` 记录 Isaac 所有权、凸体覆盖、全行程、失败与历史证据边界。 / Document Isaac ownership, convex coverage, travel, failure and historical evidence boundaries. (local)
- [docs] [docs] [新增 / Added] `.task/labutopia-finger-envelope-repair-20261102.md:L1-L108` 保存原始原因、架构决策、原生对照与后续真实阻塞。 / Save original cause, architecture decisions, native comparisons and remaining measured blockers. (local)
- [docs] [docs] [修改 / Modified] `.task/current.md:L3-L19` 更新当前局部修复与完整流程阻塞状态。 / Update local-repair and end-to-end blocker status. (local)
- [docs] [docs] [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V16_6_2.md:L1-L88` 完成问题分级、架构边界、测试命令与不同证据等级复核。 / Record severity, architecture boundaries, reproduction commands and evidence-level review. (local)
- [docs] [docs] [修改 / Modified] `CHANGELOG.md` 最近五版本滚动加入本记录，与月度归档保持全文一致；行号在 Git 回执中补齐。 / Roll this complete record into the latest five, identical to the monthly archive; record final line range in the Git receipt. (local)

### 关键代码 Diff / Key Code Diff
```diff
- box = bounds.ComputeRelativeBound(collider, body).ComputeAlignedBox()
- local_corners = np.array([*product(*zip(box.GetMin(), box.GetMax()))])
+ parts = cooked_convex_points(
+     get_physx_cooking_interface().request_convex_collision_representation,
+     UsdUtils.StageCache.Get().GetId(self.stage).ToLongInt(),
+     PhysicsSchemaTools.sdfPathToInt(collider.GetPath()),
+     PhysxCollisionRepresentationResult.RESULT_VALID,
+ )
+ parts = [points @ relative[:3, :3].T + relative[:3, 3] for points in parts]
+ boxes = [box for points in parts for box in
+          convex_slice_boxes(points, self.config["collision_margin_m"])]
+ # Each slab includes edge/plane intersections; no vertex-only clipping.
+ # Existing finger_boxes still sweeps every slab through joint limits.
```
```diff
- raise PhaseMotionError("self_collision", f"finger envelope overlaps {link}")
+ reject("self_collision", f"finger envelope overlaps {link}", link="finger",
+        other_link=link, primitive="oriented_box_sphere_group", ...)
```

### 已完成验证 / Completed Validation
- [eval] [chore] 受影响回归 434 passed；Ruff、compileall、`git diff --check` 通过。首次新增测试因模块尚未实现而收集失败；随后局部命令缺少工作流 PYTHONPATH 及零值数值断言容差导致失败，修正命令/浮点断言后全部通过。 / Affected regressions: 434 passed; Ruff, compileall and whitespace checks pass. Initial tests could not collect before implementation; a subsequent local run lacked the workflow PYTHONPATH and used an overly strict zero-value assertion, both corrected before the passing runs. (local)
- [eval] [exp] `out/lab-cooked-finger-geometry-20261102-r1/geometry.json`：左右夹指各 8 个实际 cooked 组件，53/56 个包络盒；5 个历史中间失败样本全部 clear，关节和物理时间未变。 / Native receipt: eight actual cooked components per finger, 53/56 boxes, all five historical intermediate failures clear, with unchanged joints and physics time. (local)
- [docs] [docs] 中间样本通过不代表最终抓取或整条路径通过；正式新捕获结果另记。 / Intermediate clearance does not prove final grasp or full-route feasibility; fresh-capture results are recorded separately. (local)

### 正式新捕获结果 / Formal Fresh-Capture Result
- [eval] [exp] `out/lab-fullchain-truth-20261102-cooked-finger-no-motion-r1/`，session `cli:lab-3c4728b402d2`，task `task_9c72fe6c84e94594`，revision `revision_3b1df384b60c41f4`；task-affordance unavailable，任务 cancelled，入口退出 1。 / The recorded workspace/session/task/revision completes with unavailable task-affordance, cancelled task and host exit 1. (local)
- [eval] [exp] 4 个开口拒绝与 48 次接近拒绝数量不变（workspace 20/environment 20/self 4/IK 4），但候选 17 的 5 个夹指拒绝变为更低位置的手掌球/桌面拒绝，首个 TCP Z 由 0.780287 降至 0.777973 m；修复实际推进了检查，未证明最终抓取可行。 / Four aperture and 48 approach failures persist, but candidate 17's five finger failures now become later hand-sphere/table failures, first TCP Z advancing from 0.780287 to 0.777973 m; the repair advances checking without proving final feasibility. (local)
- [eval] [exp] 候选 55 两次 refined finger/table 拒绝位于 TCP Z≈0.742 m。其余手臂环境/自碰撞与 IK 原因保持显式；未缩球半径、未调裕量、未添加绕过检查。 / Candidate 55 retains two refined finger/table failures near TCP Z 0.742 m. Remaining arm/environment/self/IK failures stay explicit; no sphere shrinking, margin tuning or bypass is added. (local)
- [eval] [chore] `simulated_motion_enabled=false`、`controller_outcomes=[]`，三个记录均为 Query；无 Action、R04 或搅拌执行证据。 / Motion remains disabled with no controller outcomes; all three records are Queries, with no Action, R04 or stirring execution evidence. (local)

### Git 提交 / Git Commit
- Implementation commit: `e91ba782` (`2026-11-02 12:36:12 +0800`).
- Branch: `feature/planning-loop`; push: `git push origin feature/planning-loop`.
- [docs] [docs] `CHANGELOG.md:L51-L112` 为本版本完整记录，另滚出第五旧版本；`changelog/2026-11.md:L717-L778` 为追加的月度记录。 / The complete entry occupies these index/archive ranges; the oldest index entry rolls out without changing its archive. (local)
- [chore] [chore] 仅提交本轮 10 个文件；无关报告、用户文件和运行输出未暂存。推送结果单独确认。 / Only ten task-owned files are committed; unrelated report, user files and runtime outputs remain unstaged. Push outcome is verified separately. (local)

## v16.6.1 (2026-11-02 12:03) - codex

### 预期修改 / Planned Changes [完成 / Completed; collision/IK workflow remains blocked]
- [docs] [docs] 保存 v16.6.0 正式无动作回执中的碰撞/IK 阻塞诊断，逐一核对实际夹指、手掌、桌面与邻瓶几何，区分碰撞模型判断与实测接触。 / Save the formal v16.6.0 collision/IK diagnosis and compare gripper, table and neighboring-object geometry, distinguishing model findings from measured contact. (local)
- [env] [fix] 在 Isaac Adapter 的 FK、夹爪几何及 preparation 边界定位并修复有证据支持的错误；保留 workspace、碰撞裕量、同捕获证据、qualified-only 恢复及完整路线检查，不将 USD/关节参数加入 AgentLoop。 / Identify and repair evidenced FK/gripper/preparation defects inside the Isaac Adapter, preserving workspace, collision margins, same-capture evidence, qualified-only recovery and full-route checks without leaking USD/joint details into AgentLoop. (local)
- [eval] [chore] 补充失败复现、机制替代和零动作测试，再运行受影响回归及实际无动作几何验证；按证据决定是否需要有界 IK 替代搜索，不预先放宽任何安全阈值。 / Add regression, mechanism-substitution and no-motion tests, then run affected tests and actual no-motion geometry verification; use evidence to decide whether bounded alternative IK search is needed, without relaxing safety thresholds. (local)
- [docs] [docs] 更新诊断、架构复核、精确行号与关键 Diff、最近五版本；仅提交本轮文件并推送当前 feature/planning-loop 分支，保留无关用户修改。 / Update diagnosis, architecture review, exact ranges/diffs and the latest five entries; commit only task-owned changes and push the current branch while preserving unrelated edits. (local)

### 根因与实际修复 / Cause and Repair
- [env] [fix] 实际 Isaac 对比证实复位先推进动力学、再恢复 qpos 导致 CPU USD 手掌变换滞后 6.561186 mm。改为显式更新 articulation kinematics 并发布 PhysX→USD，再 render；真实复核误差降为 0.000197 mm。 / Native Isaac comparison proves the step-then-reset sequence left CPU USD hand transforms 6.561186 mm behind qpos. Explicit kinematic update and PhysX-to-USD publication before rendering reduce the measured discrepancy to 0.000197 mm. (local)
- [env] [fix] 五个历史夹指/桌面拒绝在该中间样本处仍有约 16 mm 网格净空，是加裕量的全行程盒包络判断，不能说成实测撞击。保持原碰撞模型、裕量及完整路线验证，新增精确私有诊断辅助后续决策。 / Five historical finger/table failures have about 16 mm mesh clearance at the intermediate sample; they are padded full-travel box decisions, not measured impacts. Preserve the model, margins and full-route qualification while retaining exact private geometry for follow-up decisions. (local)

### 文件变更详情 / File Changes
- [env] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py:L2710-L2732` 修正初始/每次 reset 的 qpos→kinematics→USD 同步，异常时恢复 timeline。 / Correct initial/reset state publication and restore the caller's timeline on failure. (local)
- [env] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L27-L31,L818-L880,L1136,L1260-L1261` 保存球/夹指盒/自碰撞模型的关节、TCP、世界形状及碰撞对，并贯穿错误包装到私有回执；不扩展 AgentLoop 接口。 / Persist sphere/finger-box/self-sphere geometry, joints, TCP and pairs through error wrapping into private receipts without extending AgentLoop interfaces. (local)
- [eval] [chore] `examples/forge-adapters/isaacsim_lab/tests/test_engine.py:L1207-L1320` 补充 reset 前后顺序、零物理步、playing/paused 和同步失败测试；`examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py:L45-L89,L755-L773,L1007-L1008,L1017` 验证替代查询机制、精确裕量、错误传播和 private-only 诊断。 / Cover reset ordering, zero physics steps, timeline modes and failures; verify replacement queries, exact margins, propagation and private-only diagnostics. (local)
- [eval] [feat] `examples/forge-adapters/isaacsim_lab/scripts/inspect_collision_receipt.py:L1-L150` 新增真实场景零命令几何复核入口；`examples/forge-adapters/isaacsim_lab/tests/test_collision_receipt_inspector.py:L1-L27` 覆盖结构化/旧回执及缺失关节不臆造。 / Add a native zero-command geometry inspector and cover structured/legacy receipts without inventing absent joint samples. (local)
- [docs] [docs] `.task/labutopia-collision-geometry-repair-20261102.md:L1-L137`、`.task/current.md:L67-L98`、`docs/forge/IMPLEMENTATION_REVIEW_V16_6_1.md:L1-L67` 保存根因、PAOS 分层、验证与未完成操控边界。 / Save the cause, PAOS ownership, verification and incomplete manipulation boundary. (local)

### 关键 Diff / Key Diff
```diff
- world.step(render=True)
  _apply_initial_robot_state(robot, arm_positions, gripper_positions)
+ world.physics_sim_view.update_articulations_kinematic()
+ get_physx_interface().update_transformations(False, True)
  world.render()

- raise PhaseMotionError("route_collision", f"finger overlaps {found[0]}")
+ reject("route_collision", f"finger overlaps {found[0]}",
+        primitive="oriented_box", center_m=finger_center.tolist(),
+        half_extents_m=finger_half.tolist(), ...)
+ # Private diagnostics retain checked joints/TCP, frame, margin and sweep mode.
+ attempt["collision_diagnostic"] = exc.diagnostics
```

### 验证 / Validation
- [eval] [chore] 旧初始化路径先触发 7 项失败；修复后完整受影响套件 `421 passed`，Ruff、compileall、`git diff --check` 通过；不把 mock 测试当作动作证据。 / Seven tests first failed against the old reset path; the full affected suite now has 421 passes, with Ruff, compileall and whitespace checks passing. Mock tests are not motion evidence. (local)
- [eval] [exp] 实际场景 r1/r3：hand 误差 6.561186→0.000197 mm，修复后最大 link 误差 0.000201 mm；五个历史姿态的几何复核未改变关节/物理时间、零控制器命令。r2 启动停滞后终止，没有成功回执。 / Actual-scene r1/r3: hand error 6.561186→0.000197 mm; repaired maximum link error 0.000201 mm. Five historical samples leave joints/time unchanged with zero commands. Stalled r2 startup was terminated and has no successful receipt. (local)
- [docs] [docs] 本轮无需重构 AgentLoop/选择公共契约；新任务必须用新捕获。仍不声称完整抓取、倒液或搅拌成功。 / No AgentLoop/public-selection refactor is needed; a new task must bind a new capture. Complete acquisition, pouring and stirring are not claimed. (local)

### 正式新捕获结果 / Formal Fresh-Capture Result
- [eval] [exp] workspace `out/lab-fullchain-truth-20261102-reset-sync-no-motion-r1/`，session `cli:lab-3019a1d6c656`，task `task_ebea061a2ed841e3`，revision `revision_a274694de4f847f9`；R03 工艺特征 Query/preparation 通过，task-affordance unavailable 后任务 cancelled，入口退出 1。 / In the recorded workspace/session/task/revision, R03 process-feature Query/preparation pass, task-affordance remains unavailable, the task is cancelled and the host exits 1. (local)
- [eval] [exp] 4 个开口拒绝；48 次接近检查仍为 workspace 20、环境碰撞 20、自碰撞 4、IK 不可用 4。24 个碰撞拒绝均带新私有结构化几何证据，证明诊断链路接入；数量不变也证明状态同步缺陷不是这些接近拒绝的唯一/主要原因。 / Four aperture rejections and 48 approach failures remain: 20 workspace, 20 environment, four self-collision and four unavailable IK. All 24 collision failures carry structured private geometry, proving integration; unchanged counts show reset inconsistency was not the sole/main cause of approach rejection. (local)
- [eval] [chore] acceptance 明确 `simulated_motion_enabled=false`、`controller_outcomes=[]`；三个执行记录均为 Query，无 Action/controller，未执行 R04/玻璃棒。 / Acceptance records disabled motion and empty controller outcomes; all three records are Queries with no Action/controller, R04 or stirring. (local)
- [docs] [docs] 下一步仅在证明实际 cooked collider 和全开合扫掠覆盖后细化碰撞表示，或针对真实 IK 分支问题评估有界种子。不能以局部网格净空跳过现有碰撞检查。 / Refine collision geometry only after proving cooked-collider/full-sweep coverage, or evaluate bounded seeds for demonstrated IK branch issues. Local mesh clearance must not bypass existing checks. (local)

### Git 提交 / Git Commit
- Implementation commit: `34dcd61a` (`2026-11-02 12:20:21 +0800`).
- Branch: `feature/planning-loop`.
- Push command: `git push origin feature/planning-loop`; the remote outcome is reported separately. / 推送当前分支，单独报告远端结果。
- Only task-owned files are staged; unrelated report edits and runtime outputs remain excluded. / 仅暂存本轮文件，排除无关报告修改与运行输出。

## v16.6.0 (2026-11-02 11:28) - codex

### 预期修改 / Planned Changes [完成 / Completed; manipulation remains blocked]
- [docs] [docs] 保存 R03 接近段拒绝的修复决策，区分候选覆盖、运动参数与安全资格，评估局部重构边界；此前第二次推送因 HTTPS low-speed 超时失败。 / Save the R03 approach-rejection repair decision, distinguish candidate coverage, motion configuration and safety qualification, and bound the local refactor; the preceding second push failed with an HTTPS low-speed timeout. (local)
- [sense] [fix] 检查同捕获点云与原生候选覆盖，修复有证据支持的候选采样损失，保持原生位姿、opaque 引用和 Provider 替换边界。 / Inspect same-capture cloud/native candidate coverage and fix evidenced sampling loss while preserving native poses, opaque references and provider substitutability. (local)
- [env] [fix] 评估并在证据支持时修复接近距离/完整路线之间的候选一致性；不降低 workspace 或碰撞阈值，不在 AgentLoop 注入机器人参数。 / Evaluate and, where supported, repair approach-distance/full-route candidate consistency without lowering workspace/collision thresholds or leaking robot parameters into AgentLoop. (local)
- [eval] [chore] 先补失败路径与替代机制测试，再运行受影响回归及无动作验证，记录成功/失败边界；补全精确行号、Diff、最近五版本并提交推送当前分支。 / Add failure/substitution tests, run affected regressions and no-motion validation, record outcome boundaries, and complete exact ranges, diffs and latest-five entries before committing/pushing the current branch. (local)

### 定位后的实施范围 / Evidence-directed scope [完成 / Implemented]
- [sense] [fix] 本次 r2 保存的 decoded=44、NMS 后=24，小于 64 上限，不能将故障归因为 top-K 截断；24 个候选世界 approach z 全为正。在 GraspNet Worker 内新增可配置、最多四次的同点云坐标旋转推理，围绕输入质心旋转，模型重新预测后用严格逆变换回到捕获帧，再执行原有采样/资格化；不直接翻转预测，不制造新观测。 / The saved r2 result has 44 decoded and 24 post-NMS candidates, below the budget, all with positive world approach z. Add up to four configured coordinate-frame inference passes inside the worker: rotate the same cloud about its centroid, rerun the native model and invert the transform before existing selection/qualification. Never flip predicted grasps or claim new observations. (local)
- [eval] [chore] 新增旋转往返、原生位姿保真、单次兼容、任一推理失败拒绝与多次总预算测试；同一历史点云固定 seed 配对验证方向覆盖，保存配置/版本/证据身份，再决定是否启用实验配置。 / Test transform round-trips, native pose fidelity, one-pass compatibility, whole-request inference failure and aggregate budgets; pair runs on the same recorded cloud and seed, persist config/version/identity, then decide whether to enable the experimental profile. (local)
- [docs] [docs] 风险等级 C-Safety；本轮不重构 AgentLoop/公共选择契约，不改变接近距离与安全下界。Provider 负责候选机制，Adapter 负责 IK/碰撞/完整路线，Coordinator 独占恢复与 settlement。 / Tier C-Safety: do not refactor AgentLoop/public selection or change approach distances/safety limits. The Provider owns proposals, the Adapter owns IK/collision/full routes, and the Coordinator alone owns recovery/settlement. (local)

### 实际文件变更 / Actual File Changes
- [sense] [feat] `examples/forge-adapters/robotwin20/runtime/graspnet_worker.py:L66-L91,L95,L161-L192,L228-L229,L241-L242` 新增 1–4 次配置化输入坐标旋转、同点采样原生推理、预测逆变换与合并预算，默认保持单次推理。 / Add 1–4 configured coordinate-frame passes, same-point native inference, inverse-mapped predictions and aggregate budgeting; default remains one pass. (local)
- [env] [tune] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-perception.json:L88-L98` 经配对实测后启用 identity/X/Y/Z 半周输入旋转及 seed 0，不更改 motion 配置。 / Enable identity/X/Y/Z half-turn input passes and seed 0 after paired evidence, without changing motion configuration. (local)
- [eval] [chore] `examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py:L174-L313` 新增 13 项参数化/失败/替代路径用例，包括 90°/180°逆变换、缺失方向扩展、旧默认、空集合、失败不返回部分结果和既有 Provider 接口接入。 / Add 13 parametrized, failure and substitution cases including 90/180-degree inverse mapping, native regeneration, legacy defaults, empty results, partial-failure rejection and existing-provider integration. (local)
- [eval] [feat] `examples/forge-adapters/robotwin20/scripts/compare_grasp_input_frames.py:L1-L99` 新增固定捕获、固定种子配对推理工具，保存原生输出、输入身份、配置、版本、checkpoint 元数据和耗时；已有输出目录拒绝覆盖。 / Add paired same-capture seeded inference preserving native outputs, identity, config/version/checkpoint metadata and timing; refuse to overwrite an existing output directory. (local)
- [docs] [docs] `examples/forge-adapters/robotwin20/README.md:L348-L367` 说明配置、帧变换、兼容性和复现方式；`.task/current.md:L67-L105` 更新本轮结果与剩余阻塞；诊断和实现复核记录见下。 / Document configuration, transforms, compatibility and replay; update the result/remaining blocker and preserve diagnosis/review below. (local)
- [docs] [docs] `.task/labutopia-r03-native-coverage-repair-20261102.md:L1-L159`、`docs/forge/IMPLEMENTATION_REVIEW_V16_6_0.md:L1-L67` 保存根因纠正、PAOS 所有权、分阶段方案、配对数据与执行边界。 / Save the corrected cause, PAOS ownership, phased repair, paired measurements and execution boundary. (local)

### 关键代码 Diff / Key Code Diff
```diff
- end_points = network({"point_clouds": torch.from_numpy(sampled[None]).to(device)})
+ for input_rotation in rotations:
+     transformed = sampled if identity else ((sampled - pivot) @ input_rotation.T + pivot).astype(np.float32)
+     end_points = network({"point_clouds": torch.from_numpy(transformed[None]).to(device)})
+     # Decode each native result, then restore the original capture coordinates.
+     center = input_rotation.T @ (center - pivot) + pivot
+     rotation = input_rotation.T @ rotation

- "funnel": {"decoded": len(group), ...}
+ "funnel": {"decoded": sum(len(group) for group, _ in groups), ...}
+ # Merge before the existing total candidate budget; no per-pass public cap increase.
```

### 验证 / Validation
- 完整 Isaac Adapter、GraspNet Worker/Provider/profile 和 subtask executor 回归：`410 passed`；worker 定向 `19 passed`；Ruff、compileall、`git diff --check` 通过。 / Full Isaac Adapter, GraspNet worker/provider/profile and subtask-executor regression: 410 passed; focused worker: 19 passed; Ruff, compileall and diff checks passed. (local)
- 新测试先复现 10 个失败再实现通过；第一次 pytest 因继承 ROS PYTHONPATH 加载无关插件缺少 lark 而无法启动，显式使用项目 PYTHONPATH 后正常运行，未禁用异步测试插件。 / New tests first produced ten expected failures and then passed; an initial inherited ROS PYTHONPATH caused an unrelated missing-lark plugin startup failure, resolved by explicit project PYTHONPATH without disabling async test plugins. (local)
- 同捕获原生推理 `out/lab-grasp-coordinate-replay-20261102-r1/`：decoded 44→1058、返回 24→64、工艺几何合格 3→10；出现 approach Z<0 的原生候选，未调低门槛。 / Paired native inference: decoded 44→1058, public candidates 24→64, geometry-qualified 3→10, including native negative-world-Z approaches with unchanged thresholds. (local)
- 正式无动作 r1（session `cli:lab-99ebda8ffe51`）在初始 `scene.observe is unavailable or stale` 停止，`tasks=[]`、`controller_outcomes=[]`，尚未进入候选资格；已保存回执并原样发起 r2，不改变 freshness 阈值。 / Formal no-motion r1 stopped at initial unavailable/stale observation with no tasks/controller outcomes, before candidate qualification; its receipt was saved and unchanged r2 was launched without changing freshness limits. (local)

### 正式运行结果与剩余问题 / Formal Runtime and Remaining Blocker
- r2 workspace `out/lab-fullchain-truth-20261102-native-coordinate-no-motion-r2/`，session `cli:lab-2063ffedd5eb`，task `task_053053cf3a0b4804`，revision `revision_e4383c96834e44ec`；初始绑定与 R03 工艺特征 Query/preparation 通过。 / Initial binding and R03 process-feature Query/preparation passed in the recorded r2 workspace/session/task/revision. (local)
- 新捕获复现 R03 decoded=1058、NMS 后=389、返回=64；10 个几何合格候选中 4 个超过开口，余下 6 个各 8 次接近检查共 48 次失败：workspace 20、环境碰撞 20、自碰撞 4、IK 不可用 4。 / Fresh capture reproduces 1058 decoded, 389 post-NMS and 64 returned proposals; four of ten geometry-qualified candidates exceed aperture, while six produce 48 rejected approaches: 20 workspace, 20 environment collision, four self-collision and four unavailable IK. (local)
- 具体环境碰撞对：finger/table=7、link6/table=4、link5/table=3、hand/R01=2、link6/R02=1、link7/R02=1、link5/BEAKER=2；这是 Adapter 碰撞模型判断，不是实际撞击测量。 / Concrete environment pairs are finger/table=7, link6/table=4, link5/table=3, hand/R01=2, link6/R02=1, link7/R02=1 and link5/BEAKER=2; these are Adapter collision-model findings, not physical impact measurements. (local)
- Task-affordance 返回 unavailable，任务终态 cancelled，入口退出码 1；`acceptance.json` 记录 `simulated_motion_enabled=false`、`controller_outcomes=[]`，三个执行记录均为 Query，没有 Action/Session。R04/玻璃棒未执行。 / Task-affordance returned unavailable, the task ended cancelled and the host exited 1; acceptance records disabled motion, empty controller outcomes and three Query records with no Action/Session. R04/stirring did not execute. (local)
- 本轮方向覆盖局部修复已完成并接入；完整操控仍阻塞。后续按具体碰撞姿态复核真实夹指/手掌与场景几何，再评估夹持区域净空及有界 IK 种子；不通过 AgentLoop 重构或降低门槛绕过。 / The local coverage repair is integrated; manipulation remains blocked. Next review concrete gripper/scene geometry and then gripping-region clearance/bounded IK seeds, without bypassing checks or rewriting AgentLoop. (local)

### Git 提交 / Git Commit
- Implementation: `33d3bfb2` (`2026-11-02 11:43:10 +0800`).
- Branch: `feature/planning-loop`.
- This documentation follow-up records the completed r2 outcome and exact diagnosis/review ranges; unrelated user changes remain excluded. / 本次文档跟进记录 r2 终态及精确诊断/复核行号，未纳入无关用户修改。
- Push: `git push origin feature/planning-loop`; report the actual remote result after this receipt commit. / 提交回执后推送当前分支，并报告实际远端结果。

## v16.5.0 (2026-11-01 22:18) - codex

### 预期修改 / Planned Changes [完成 / Completed; runtime remains blocked]
- [sense] [feat] 在 Isaac Adapter 私有 Task-Affordance Provider 中接入同一捕获、同一场景修订的无动作 grasp approach 可行性探针，只保留至少一个最终抓取方向与短接近段通过 Franka IK、连续性、workspace、自碰撞及环境碰撞检查的 opaque grasp 引用；不向 AgentLoop 暴露关节、USD 路径或碰撞细节。 / Add a same-capture, same-scene-revision no-motion grasp-approach feasibility probe behind the Isaac task-affordance Provider, retaining only opaque grasp refs with at least one final orientation and short approach that passes Franka IK, continuity, workspace, self-collision, and environment-collision checks without exposing joints, USD paths, or collision details to AgentLoop. (local)
- [env] [feat] 在 Engine/Worker/PhaseMotion Adapter 边界增加只读 feasibility RPC 与 Adapter 私有证据，复用最终组合场景、观测到执行体绑定、抓取对称变体和现有安全检查；探针不得发出控制器命令、改变世界或替代完整 Action preparation。 / Add a read-only feasibility RPC and Adapter-private evidence across the Engine/Worker/PhaseMotion boundary, reusing the final composed scene, observation-to-body binding, grasp-symmetry variants, and existing safety checks; the probe must issue no controller command, change no world state, and never replace full Action preparation. (local)
- [policy] [fix] Task-Affordance Preparation 仅返回 Query 中已通过 feasibility 的同工艺特征 opaque refs，并在场景修订、捕获、候选集合或 feasibility 证据缺失/过期/歧义时 fail closed；现有 Action preparation 继续只遍历该有序集合。 / Make task-affordance Preparation return only same-process-feature opaque refs that passed feasibility in the Query, failing closed on stale/missing/ambiguous scene, capture, candidate-set, or feasibility evidence while the existing Action preparation continues to traverse only that ordered set. (local)
- [test] [test] 先覆盖替代 Provider 不依赖 Isaac 私有字段、一个候选可行、全部候选不可达、stale capture/revision、无效探针结果、对称方向选择、零动作与 Action 不重新引入被排除候选；随后运行定向和完整回归及一次不带 `--execute` 的全链路 Agent 验证。 / Cover provider substitution without Isaac-private fields, one feasible candidate, all candidates unreachable, stale capture/revision, invalid probe results, symmetry-orientation selection, zero motion, and prevention of Action reintroducing rejected candidates; then run focused/full regression and one full-chain Agent validation without `--execute`. (local)
- [docs] [docs] 保存本轮主因诊断、PAOS 所有权/替换边界、证据链与新鲜度边界、findings-first 实现复核、验证命令及 no-motion 运行回执；只有完整 R03 acquire preparation 通过后才允许后续模拟执行。 / Save the root-cause diagnosis, PAOS ownership/substitution boundary, evidence lineage and freshness boundary, findings-first implementation review, validation commands, and no-motion receipt; permit later simulated execution only after complete R03 acquire preparation succeeds. (local)

### 架构与安全边界 / Architecture and Safety Boundary
- 通用层继续只拥有 task semantics、opaque refs、生命周期、恢复与 settlement；机器人 IK、关节种子、短接近采样、USD/PhysX 查询及失败细节由 Isaac Adapter 独占。 / The generic layer continues to own task semantics, opaque refs, lifecycle, recovery, and settlement; robot IK, joint seeds, short-approach sampling, USD/PhysX queries, and failure details remain exclusively owned by the Isaac Adapter.
- feasibility 是 Query/Preparation 的只读证据，不是第二个调度器、路线存储或成功 settlement；完整路线仍由 `manipulation.prepare` 重新验证。 / Feasibility is read-only Query/Preparation evidence, not a second scheduler, route store, or success settlement; `manipulation.prepare` still revalidates the complete route.
- 不新增 hash、冻结 contract 或额外发布 gate，不降低 workspace、IK 连续性、关节限位、自碰撞、环境碰撞、payload collision 或 possession 门禁。 / Add no hashes, frozen contracts, or release gates, and weaken none of the workspace, IK-continuity, joint-limit, self-collision, environment-collision, payload-collision, or possession gates.

### 续作计划 / Continuation Plan (2026-11-02) [完成 / Completed]
- [docs] [fix] 保存 r3 的真实拒绝诊断：R03 候选 15/16/23 的 world grasp z≈0.750917 m、approach z≈0.634282，后退 0.12/0.18 m 后 pre-grasp z≈0.674803/0.636746 m，小于既有 workspace z_min=0.7 m；该结论只证明现有候选/接近距离不合格，不证明物体不能抓取。 / Save the measured r3 rejection: the three qualified grasps backtrack below the existing workspace floor; this rejects the present approaches, not all possible grasps of the object. (local)
- [env] [fix] 补齐 feasibility artifact 的 capture identity、失败变体及工作空间坐标证据，保留 worker 拒绝的原始原因；验证探针与完整 preparation 的几何一致性，不修改安全阈值。 / Complete feasibility artifact capture identity and variant/workspace diagnostics, preserve worker rejection causes, and test geometric agreement with full preparation without changing safety thresholds. (local)
- [sense] [fix] 审查并修复探针替代实现、过期/错误 identity、缺失证据和 Provider 异常的失败路径；真实不可达与基础设施异常必须可区分。 / Review and repair substitution, stale/wrong identity, missing evidence, and provider-error paths; distinguish geometric infeasibility from infrastructure failure. (local)
- [eval] [chore] 运行定向/完整回归及新的无动作正式入口验证，保存诊断与实现复核，补齐当前任务、双语行号/Diff 和最近五版本后提交并推送当前分支；不纳入无关未提交文件。 / Run focused/full regressions and a fresh formal no-motion validation, save diagnosis/review, update task and bilingual line/diff records and latest five entries, then commit and push the current branch without unrelated changes. (local)

### 实际文件变更 / Actual File Changes
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py:L123-L125` 注入只读 feasibility 回调；继续使用原 Task-Affordance Query/Preparation 与 AgentLoop。 / Inject the read-only feasibility callback into the existing Task-Affordance and AgentLoop path. (local)
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py:L504-L526,L631-L663,L730-L749` 新增 Adapter backend 分发、同一 worker RPC 与失败身份保留；未增加 Core Tool 或 Action。 / Add Adapter/backend dispatch, same-worker RPC and failure identity preservation without a Core Tool or Action. (local)
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L1014-L1046,L1129-L1311` 允许显式虚拟 IK 种子并用 FK 验证一致性；生成几何轴对称短接近候选并复用既有 qualification；保存逐候选坐标、世界边界、capture identity 与失败原因。 / Support explicit hypothetical IK seeds with FK agreement, qualify geometry-equivalent short approaches through existing checks, and persist coordinates, world bounds, capture identity and causes. (local)
- [sense] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py:L9,L239-L240,L267-L269,L355-L459,L473,L538-L551,L1295-L1375` 组合过滤只保留可行 opaque grasp refs；复核回执并保存 Provider 异常/缺失证据诊断；解析私有执行 target 不扩大公共契约。 / Retain only feasible opaque grasp refs, revalidate receipts, record provider/missing-evidence errors and resolve private execution targets without widening public contracts. (local)
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/worker.py:L116-L151`、`examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/worker_session.py:L61-L62` 接入串行只读 RPC，拒绝缺失/过期场景，保持原 request identity 且不推进 revision。 / Wire a serialized read-only RPC, reject missing/stale scenes, preserve request identity and leave revision unchanged. (local)
- [eval] [chore] `examples/forge-adapters/isaacsim_lab/tests/test_engine.py:L1128-L1172`、`tests/test_phase_motion.py:L612-L820`、`tests/test_visual_perception.py:L1039-L1295`、`tests/test_worker_session.py:L7-L8,L65-L78,L151-L176,L193-L213`（后三者同属该 Adapter）覆盖替代回调、混合候选过滤、实际短路线 qualifier、workspace 复现、stale/invalid/missing/error 及零调用拒绝。 / Cover replacement callbacks, mixed-candidate filtering, the real short-route qualifier, recorded workspace rejection, stale/invalid/missing/error outcomes and zero-dispatch rejection. (local)
- [docs] [docs] `.task/current.md:L25-L26,L40-L76`、`.task/labutopia-r03-approach-feasibility-diagnosis-20261102.md:L1-L130`、`docs/forge/IMPLEMENTATION_REVIEW_V16_5_0.md:L1-L79` 保存继续任务、定量诊断及 PAOS 分层复核；诊断 L81-L130 包含验证命令和新的终态回执。 / Save the current task, quantitative diagnosis and PAOS ownership review; diagnosis lines 81–130 include validation commands and the fresh terminal receipt. (local)

### 关键代码 Diff / Key Code Diff

```diff
- grasp_task_affordance_provider=LabGraspTaskAffordanceProvider(visual)
+ grasp_task_affordance_provider=LabGraspTaskAffordanceProvider(
+     visual, approach_feasibility=visual.qualify_grasp_approach
+ )

- def qualify(self, waypoints, source, tcp_from_object, operation, supported_pose=None, tool_frame=None):
-     joints = self.joints()
+ def qualify(self, waypoints, source, tcp_from_object, operation, supported_pose=None,
+             tool_frame=None, *, initial_joints=None, initial_pose=None):
+     joints = self.joints() if initial_joints is None else np.asarray(initial_joints, dtype=float).copy()
+     # A supplied initial_pose must agree with FK before route qualification.

- # Body/process-compatible grasps immediately enter the task-affordance set.
+ # Same-capture private probe checks pre-grasp and grasp/close first.
+ # Only candidates with available, no-motion evidence enter the set.
+ # Full Action preparation still qualifies the entire route from live joints.

- raise PhaseMotionError("workspace_violation", "pre-grasp TCP is outside workspace")
+ raise PhaseMotionError("workspace_violation",
+     f"pre-grasp TCP={pre[:3, 3].tolist()} outside world workspace "
+     f"min={self.config['workspace_min_m']}, max={self.config['workspace_max_m']}")
```

### 验证 / Validation
- 完整 Isaac Adapter + subtask executor 回归 `370 passed`；定向 phase/visual/worker 回归 `185 passed`；混合候选及无效 artifact ref 测试补强后 visual 回归 `67 passed`。 / Full Isaac Adapter plus subtask-executor regression passed 370; focused phase/visual/worker passed 185; strengthened mixed-candidate and invalid-artifact visual tests passed 67. (local)
- 十个代码/测试文件 Ruff、compileall 与 `git diff --check` 通过；没有禁用 async 插件或把未运行测试计为通过。 / Ruff on ten code/test files, compileall and diff checks passed; asynchronous tests were not disabled or reported as passed without running. (local)
- 初次新增 worker 参数化测试漏导入 pytest，收集失败后已补齐并重新通过；该失败不作为运行能力证据。 / An initial parametrized worker test missed its pytest import; collection was fixed and rerun successfully, with no runtime claim inferred. (local)

### 运行边界 / Runtime Boundary
- 2026-11-01 r3 已证明三个合格几何 grasp 的 24 个接近变体都越过 workspace 下界；该结论只覆盖当前候选和既有 approach 配置。 / The November 1 r3 artifacts prove all 24 short-approach variants violate the existing lower workspace bound; this covers only current candidates/configuration. (local)
- 2026-11-02 r1 在会话中断前写出相机、state 和 understanding，但进程已结束且没有 acceptance.json；标记为中断，不能作为最终资格化结果。 / November 2 r1 wrote camera/state/understanding artifacts before interruption; its process ended without acceptance.json, so it is incomplete rather than qualification evidence. (local)
- 2026-11-02 r2 使用相同正式 `python -m isaacsim_lab.agent_host` 入口和原提示词重跑，不传 `--execute`；task `task_51ae038c97d246fd`、session `cli:lab-5fe426934fb3` 最终 cancelled。R03 工艺 Query/preparation 通过；task-affordance 的三个 grasp 共 24 个变体全部 workspace rejection，未进入 IK/Action。 / November 2 r2 used the same formal Agent Host entry/instruction without `--execute`; the recorded task/session ended cancelled after process-feature preparation passed and all 24 grasp approaches failed workspace checks before IK/Action. (local)
- 新 artifact 包含完整 capture identity、world grasp/pre-grasp、approach 和 workspace 边界，复现 z=0.674803/0.636746 m；`acceptance.json` 记录 `simulated_motion_enabled=false`、`controller_outcomes=[]`；R04/GLASS_ROD 未执行。 / Fresh artifacts reproduce the measured low pre-grasp heights with full identity/geometry; acceptance confirms disabled motion, empty controller outcomes and no downstream execution. (local)
- 本次完成资格化前移和诊断修复；当前抓取方向/接近距离仍不可行，未宣称全链路倾倒/搅拌成功。 / Early qualification and diagnostic fixes are complete; current grasp directions/backoffs remain infeasible, with no full manipulation success claimed. (local)

### 实现复核 / Implementation Review
- [docs] [docs] 修复完整路线前缺失 embodiment 接近资格检查、artifact 身份/坐标不足、Provider 异常被泛化、测试完全桩替短路线等四项 Major；当前实现无剩余已识别 Blocker/Major。 / Resolve four Major findings in early embodiment qualification, artifact identity/coordinates, provider-error differentiation and real short-route test coverage; no identified implementation Blocker/Major remains. (local)
- [docs] [docs] `CHANGELOG.md` 最近五条恢复为与月度归档一致的完整记录；保留所有历史月度版本，不纳入无关报告修改或运行大文件。 / Restore the latest five full entries in CHANGELOG to match the monthly archive, preserve historical entries and exclude unrelated edits/large run artifacts. (local)

### Git 提交 / Git Commit
- Implementation commit: `8f3fa34e`.
- Log receipt commit: `134d4ed8`.
- Branch: `feature/planning-loop`.
- Time: `2026-11-02 11:04:50 +0800` (Asia/Shanghai, implementation commit).
- Receipt: this log-only follow-up records the implementation commit and corrects the task-file line references; the rolling index contains the same complete entry. / 本次纯日志跟进回填实现提交并校正任务文件行号，滚动索引保留同一完整记录。
- Push command: `git push origin feature/planning-loop` (current branch; no branch switch). / 推送当前分支，不切换分支。
- First push attempt: `timeout 60s git push origin feature/planning-loop` ended with exit `124` and no remote acknowledgement. Commits remain local; one bounded retry follows this receipt. / 首次推送 60 秒超时且无远端确认；提交保留本地，记录后进行一次有界重试。

## v16.4.0 (2026-11-01 20:57) - codex

### 变更摘要 / Summary [完成 / Completed; no motion]
- [env] [feat] 在 Isaac Adapter 内将 acquire 路线搜索从单一固定 XY 的 `staging_reorient -> approach` 扩展为配置驱动的 staging 高度、沿 approach 的额外后退距离与切向偏移候选；候选继续使用原始 task-affordance opaque grasp 引用，不修改 AgentLoop 或共享 Tool contract。 / Extend Isaac Adapter acquire route search from one fixed-XY staging/approach corridor to configuration-driven staging heights, additional approach backoffs, and tangential offsets while preserving the original task-affordance opaque grasp refs and leaving AgentLoop/shared Tool contracts unchanged. (local)
- [env] [fix] 对每个新路线候选继续执行 workspace、完整姿态 IK、`0.5 rad` 连续性、关节限位、自碰撞、环境碰撞、payload collision 与 possession 门禁；不放宽阈值，不将失败转换为成功。 / Run every new route candidate through the unchanged workspace, full-pose IK, `0.5 rad` continuity, joint-limit, self/environment collision, payload-collision, and possession gates without weakening thresholds or converting failures to success. (local)
- [env] [refactor] 将 staging/approach 候选的配置解析、几何构造与确定性排序提取为 Adapter 私有帮助函数，避免在 `prepare` 中继续扩张嵌套且便于替换测试。 / Extract Adapter-private configuration parsing, geometry construction, and deterministic ordering helpers for staging/approach candidates instead of expanding nested preparation logic. (local)
- [test] [test] 增加配置拒绝、几何候选生成、切向偏移、额外后退、完整安全资格化、确定性排序及全部路线失败保持零动作的测试；先运行离线单元测试和 no-motion preparation，只有至少一条完整 R03 路线通过后才允许再次 `--execute`。 / Add tests for invalid configuration, geometric candidate generation, tangential offsets, extra backoff, complete safety qualification, deterministic ordering, and zero-motion all-route failure; run offline tests and no-motion preparation before any new `--execute`. (local)
- [docs] [docs] 保存主因诊断、PAOS 所有权/替换边界、证据新鲜度、失败优先路径和验证命令，并更新当前任务与最近五版本。 / Save the root-cause diagnosis, PAOS ownership/substitution boundary, evidence freshness, failure-first paths, and validation commands, then update the current task and latest-five index. (local)

### 架构与安全边界 / Architecture and Safety Boundary
- 通用层继续只拥有任务语义、opaque 引用、生命周期、恢复与 settlement；staging/approach 几何、IK 种子、关节与碰撞全部留在 Isaac Adapter。 / The generic layer continues to own only task semantics, opaque refs, lifecycle, recovery, and settlement; staging/approach geometry, IK seeds, joints, and collision remain inside the Isaac Adapter.
- 新候选由最终 grasp pose、approach 向量和配置生成，不读取 R03/R04 标签或硬编码物体坐标。 / New candidates derive from the final grasp pose, approach vector, and Adapter configuration without reading R03/R04 labels or hard-coding object coordinates.
- 本轮先完成 no-motion qualification；未经完整 preparation 通过，不启动控制器。 / This iteration completes no-motion qualification first and does not start the controller until full preparation passes.

### 实际实现 / Implementation
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L242-L374,L617-L620,L921-L974` 新增 Adapter 私有 corridor 配置验证、基于最终 grasp/approach 的 pre-grasp 与 staging 几何、确定性路线选择，以及有界失败聚合；旧 profile 缺少新字段时回退到原单 corridor。 / Add Adapter-private corridor validation, final-grasp/approach-derived pre-grasp and staging geometry, deterministic route selection, and bounded failure aggregation with legacy single-corridor fallback. (local)
- [env] [tune] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json:L13-L34` 配置 4 个有界候选：旧 `0.12 m` approach、`0.18 m` approach + `0.08 m` backoff，以及 `-0.06/0/+0.06 m` 水平切向偏移。 / Configure four bounded candidates covering the legacy approach plus longer approach/backoff and signed horizontal tangential offsets. (local)
- [test] [test] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py:L10-L22,L176-L517` 覆盖旧配置回退、去重、非法数值、水平/垂直 approach、逐 corridor 完整 qualification、确定性选择、全部失败零动作及 96 路线错误摘要上限。 / Cover legacy fallback, deduplication, invalid values, horizontal/vertical approaches, complete per-corridor qualification, deterministic selection, zero-motion all-route failure, and bounded 96-route diagnostics. (local)
- [docs] [docs] `.task/labutopia-r03-staging-corridor-diagnosis-20261101.md:L1-L76`、`.task/current.md:L1-L71`、`docs/forge/IMPLEMENTATION_REVIEW_V16_4_0.md:L1-L42` 保存运行诊断、当前阻塞、findings-first 复核和下一条证据驱动路线。 / Save runtime diagnosis, current blocker, findings-first review, and the next evidence-driven route. (local)

### 关键代码 Diff / Key Code Diff
```diff
- acquire preparation uses one fixed pre-grasp XY corridor
- every failed route is appended as a full exception string
+ acquire preparation enumerates configured approach/backoff/tangential corridors
+ every corridor still passes the unchanged qualify() safety path
+ failure output aggregates code/phase/corridor/clearance/transport counts with bounded examples
```

### 验证 / Validation
- 定向回归：`151 passed`（`test_phase_motion.py`、`test_paos_integration.py`、`test_subtask_executor.py`）。 / Focused regression: `151 passed`.
- 完整回归：`346 passed`（全部 Isaac Adapter tests + subtask executor boundary）。 / Full regression: `346 passed`.
- `ruff check`、`compileall`、JSON parse、`git diff --check` 全部通过。 / Ruff, compileall, JSON parsing, and diff check passed.

### No-Motion 运行 / Runtime Evidence
- Workspace `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/`；session `cli:lab-b11c91c66271`；task `task_b16f8e5cbeb84dda`；action `invocation://manipulation-execute_subtask/3ebe297dca4e4fbf`；scene `labutopia-tabletop-rod-rack-v1:74e728eececc4cc590e7bd8dc431f73a:0`。 / Record the no-motion workspace, session, task, action, and scene revision. (local)
- Action 仅消费同次捕获 refs `16/23/15`；每个检查 `3 clearance x 2 transport x 4 corridor x 4 axial = 96` 条，共 288 条。 / Action consumed only same-capture refs `16/23/15`; each exercised 96 routes for 288 total. (local)
- 全部失败：140 IK discontinuity、49 IK unavailable、21 self-collision、78 environment collision；阶段为 `staging_reorient=173`、`approach=92`、`transit_cross=23`。 / All routes failed with the recorded IK/collision and phase distribution. (local)
- `simulated_motion_enabled=false`、`outcome_known=true`、`world_change_started=false`、`possession_state=empty`、`controller_outcomes=[]`；未启动 R04/GLASS_ROD，也未发起 `--execute`。 / The run remained known zero-motion with empty possession and no downstream execution. (local)
- 保留静态预览 `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/artifacts/labutopia/no-motion-video/staging-corridor-observation.mp4`，5 秒、1600x1200、30 fps，明确标注 controller disabled，不作为动作证据。 / Preserve a labelled five-second static observation preview, not Action evidence. (local)

### 实现复核 / Implementation Review
- Major（已修复）：96 条完整异常/候选导致约 74 KB Action error 与约 174k Agent context；改为有界聚合并由单元测试验证。 / Fixed the Major unbounded-diagnostics finding with bounded aggregation and a regression test.
- Blocker/Major：无剩余实现问题；公共 contract、AgentLoop 所有权、opaque refs 与完整运动安全门禁均未改变。 / No remaining implementation Blocker/Major; contracts, ownership, opaque refs, and safety gates remain unchanged.
- 运行阻塞仍存在：新 corridor 未产生完整可行路线，因此本轮不允许 simulated execution。 / Runtime feasibility remains blocked, so simulated execution is not authorized.

### Git 提交 / Git Commit
- Implementation commit: `fa0800a7`.
- Branch: `feature/planning-loop`.
- Time: `2026-11-01 21:20:30 +0800`.
- Log receipt commit: `9a4e8fdd`.
- Push: succeeded to `origin/feature/planning-loop`; remote advanced from `a5615644` to `9a4e8fdd`. / 已成功推送当前分支，远端从 `a5615644` 前进到 `9a4e8fdd`。
