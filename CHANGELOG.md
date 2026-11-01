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

## v16.3.8 (2026-11-01 20:00) - codex

### Summary [Completed; no motion]
- [env] [feat] Isaac acquire preparation now raises with the current orientation, selects a configured transport orientation, translates laterally, reorients at staging, and only then approaches the grasp. / Isaac acquire preparation 现在依次执行当前姿态抬升、安全运输姿态、横移、staging 重定向和最终接近。
- [sense] [feat] Final-composed USD mesh slices provide optional axial grasp-symmetry evidence; labels, USD paths, and a circular opening alone do not authorize equivalent grasp rotations. / 轴对称候选来自最终组合网格横截面证据，不依据标签、路径或单一圆形瓶口推断。
- [env] [fix] Every clearance x transport x axial-angle combination passes the unchanged workspace, IK continuity, joint-limit, self/environment collision, and payload checks, then successful routes are ranked by joint travel and configured order. / 每个组合继续通过完整安全门禁，仅对全部通过的路线排序。
- [test] [test] Focused regression passed `135`; full Isaac Adapter plus subtask-executor boundary regression passed `329`; Ruff, compileall, JSON validation, and diff check passed. / 定向 135 项、完整边界 329 项及静态检查通过。
- [docs] [docs] The no-motion run exercised 24 route combinations per qualified R03 grasp and stopped at staging/approach qualification with no controller command or world change. / 无动作运行对每个 R03 资格 grasp 检查 24 条路线，均在 staging/approach 阶段停止。
- [docs] [docs] Preserved preview: `out/lab-fullchain-truth-20261101-staged-symmetry-no-motion-r1/artifacts/labutopia/no-motion-video/staged-symmetry-observation.mp4` (5 seconds, 1600x1200, controller disabled). / 保留 5 秒真实相机静态预览，明确禁用控制器。

### Key Diff / 关键 Diff
```diff
- lateral transit uses final grasp orientation and has no validated equivalent-orientation search
+ staged transport route plus final-mesh-supported axial alternatives
+ every variant remains subject to the existing complete safety qualification
```

See `changelog/2026-11.md` for exact files, line ranges, runtime evidence, and review findings.

### Git Commit
- Pending implementation commit; branch `feature/planning-loop`.

## v16.3.7 (2026-11-01 19:37) - codex

### Summary [Completed; no motion]
- [env] [fix] Isaac preparation now rejects a discontinuous primary/tool-feature IK branch before collision sampling unless nearby IK fully succeeds within the configured `0.5 rad` waypoint limit. / Isaac preparation 在碰撞采样前拒绝不连续 IK 分支，只有满足完整容差且连续的附近解才可替代。
- [env] [fix] Mixed clearance failures report `route_unavailable` with every original reason, and collision diagnostics include the actual checked joints and TCP. / 混合 clearance 保留逐项原因，碰撞诊断记录真实检查样本。
- [policy] [fix] The Skill consumes explicit Adapter `requires_replan` and `recommended_action` fields, preserves alternative-selection versus grasp-refresh semantics, and no longer parses error strings. / Skill 只消费显式恢复字段并保留两类重规划语义，不再解析错误文本。
- [test] [test] Focused regression passed `123`; full Isaac Adapter plus subtask-executor regression passed `312`; Ruff, compileall, JSON validation, and diff check passed. / 定向 123 项与完整 312 项回归及静态检查通过。
- [docs] [docs] Post-fix no-motion run `task_a5127feeb8c8476a` rejects R03 candidates `16/15/23` on `transit_cross` IK continuity/availability with no controller outcome or world change. / 修复后无动作运行确认旧碰撞标签受错误 IK 分支污染，当前真实阻塞为 transit 路线完整姿态 IK。

### Key Diff / 关键 Diff
```diff
- failed nearby IK leaves distant Lula branch for collision sampling
- recovery decision inferred/collapsed at the Skill boundary
+ fail closed on IK discontinuity before collision sampling
+ preserve typed Adapter recovery semantics through settlement
```

See `changelog/2026-11.md` for exact files, line ranges, validation commands, and runtime evidence.

### Git Commit
- Implementation commit: `38b46429`; branch `feature/planning-loop`; `2026-11-01 19:54:27 +0800`.
- Push failed because `github.com:443` was unreachable after `136405 ms`; commits remain local. / 推送因 GitHub 443 端口不可达而失败，提交保留在本地。

## v16.3.6 (2026-11-01 19:14) - codex

### Summary [Completed; all-small-vessel scene still stopped before motion]
- [env] [exp] Started the authorized R03 -> R04 -> GLASS_ROD full chain against LabUtopia v0.2.9; R03 measured `63.215 x 63.215 x 79.948 mm` and R04 measured `65.474 x 65.046 x 115.680 mm`. / 在全部小型瓶体场景发起授权仿真执行并确认最终组合尺寸。
- [sense] [test] Used same-capture simulator-truth labels, depth, point clouds and final USD geometry; no ReMake/DFNet/SAM2 or transparent-recovery artifact was created. / 使用同次捕获仿真真值，未调用透明几何恢复。
- [policy] [test] Task-Affordance qualified only R03 candidates `15/16/23`; Action preparation consumed exactly those opaque refs and did not recover from the raw GraspNet set. / Action 仅遍历三个资格引用，没有候选集合泄漏。
- [env] [test] All three failed pre-motion on self-collision, table route collision or IK. `controller_outcomes=[]`, `world_change_started=false`, `outcome_known=true`, `possession_state=empty`; R04 and stirring did not start. / 三个候选均在动作前失败，场景未变化，后续子任务未启动。

See `changelog/2026-11.md` for the command, safety boundary, and runtime evidence.

## v16.3.5 (2026-11-01 18:51) - codex

### Summary [Completed; small-vessel scene still stopped before motion]
- [env] [exp] Started a new `--execute` R03 -> R04 -> GLASS_ROD Agent run against the LabUtopia v0.2.8 small-vessel scene; task `task_b4d730ffb7f043b7`, session `cli:lab-d099bf7187df`. / 在 LabUtopia v0.2.8 小瓶场景发起新的全链路 Agent 仿真执行。
- [sense] [test] Fresh simulator-truth evidence measured R03 at `77 x 77 x 97 mm` and R04 at `93 x 93 x 165 mm`; no ReMake/DFNet/SAM2 worker or recovery artifact was created. / 新鲜仿真真值确认小瓶尺寸，未调用透明几何恢复。
- [env] [test] R03 returned 19 same-capture task-qualified grasps, but all failed preparation: 13 aperture, 4 route collision, 1 self-collision and 1 IK failure. / R03 产生 19 个同次捕获资格候选，但全部未通过物理准备。
- [policy] [test] Prompt parameters were preserved exactly; `controller_outcomes=[]`, `world_change_started=false`, `outcome_known=true`, `possession_state=empty`. R04 and stirring did not start. / 指令参数原样保留；控制器未启动，世界未变化，R04 与搅拌未开始。

See `changelog/2026-11.md` for the execution command and evidence boundary.

## v16.3.4 (2026-11-01 16:33) - codex

### Summary [Completed; authorized simulation stopped before motion]
- [env] [exp] Started the R03 -> R04 -> GLASS_ROD full-chain Agent with `--execute`, simulator-truth labels/depth/point clouds/final USD geometry, and no ReMake invocation. / 使用 `--execute` 启动 R03、R04、玻璃棒全链路，采用 simulator-truth 真值，不调用 ReMake。
- [policy] [test] PlanGraph preserved the exact prompt parameters: both pours `tilt_rad=0.87, hold_s=0.6`; stir `radius_m=0.009, depth_m=0.04, turns=2, duration_s=4, direction=ccw`. / PlanGraph 原样保存用户提示词中的两次倾倒和搅拌参数。
- [env] [test] R03 process/task-affordance preparation was available, but all eight qualified grasps failed aperture, IK, self/environment collision, or payload checks. The Adapter rejection list exactly matched the qualified set. / R03 工艺和 task-affordance preparation 可用，但八个资格 grasp 均未通过物理准备，Adapter 拒绝列表与资格集合完全一致。
- [env] [test] `simulated_motion_enabled=true`, but `controller_outcomes=[]`, `world_change_started=false`, `outcome_known=true`, and `possession_state=empty`; R04 and stirring did not start. / Host 已授权仿真运动，但 preparation 在首个控制器命令前停止，场景未变化、夹爪为空，R04 和搅拌未启动。
- [docs] [docs] Workspace: `out/lab-fullchain-truth-20261101-r03-r04-execute-r3/`; task `task_bf1d10503ac04534`; session `cli:lab-a3347a964178`. / 保存运行目录、任务和 session 证据。

### Key Diff / 关键 Diff
```diff
- no-motion Host authorization
+ --execute authorized at Host boundary
+ preparation still blocks every controller command
```

### Git Commit
- Runtime evidence commit: `2f155d08`; branch `feature/planning-loop`; `2026-11-01 16:41:36 +0800`.
- Push withheld pending explicit approval under robotics runtime-safety guidance. / 按机器人运行安全规则，未获明确批准前不推送。
