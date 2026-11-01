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

## v16.3.3 (2026-11-01 13:44) - codex

### Summary [Completed; no motion]
- [policy] [feat] Task-Affordance Preparation now returns selected-first ordered `qualified_grasp_candidate_refs`; AgentLoop projects them from the unique direct predecessor, and Action preparation resolves only those opaque refs from the unchanged same-capture binding. / Task-Affordance Preparation 返回 selected-first 有序资格引用，AgentLoop 从唯一直接前驱投影，Action 只从同次捕获 binding 解析这些引用。
- [sense] [fix] GraspNet keeps a 512-candidate native pool and retains 64 deterministic geometry-diverse proposals; final-composed USD mesh vertices provide simulator-truth object points, and bottle support-end grasps are filtered before embodiment preparation. / 保留 512 原生候选并选择 64 个几何多样候选；最终组合 USD mesh 提供真值点云，并在 embodiment preparation 前过滤瓶底候选。
- [env] [fix] Isaac preparation validates final Franka aperture and searches configured route clearances while preserving IK, self/environment collision, payload, workspace and frame gates. / Isaac preparation 校验最终 Franka 开口并搜索配置化 clearance，保留 IK、碰撞、payload、workspace 与坐标系门禁。
- [test] [test] Current focused regression: `244 passed, 1 warning`; earlier staged suites: `474 passed`; Ruff, compileall and diff check passed. A broader non-acceptance sweep exposed stale fixtures and is recorded in the monthly log. / 当前聚焦回归 244 项通过，先前分阶段累计 474 项通过，静态检查通过；更广 sweep 的旧 fixture 失败已记录于月度日志。
- [docs] [docs] Diagnosis: `.task/labutopia-r03-grasp-candidate-exhaustion-20261101.md:L1-L183`; review: `docs/forge/IMPLEMENTATION_REVIEW_V16_3_3.md:L1-L59`. / 保存 r3-r9 诊断及 C-Safety 实现审查。

### Key Diff / 关键 Diff
```diff
- Action alternative recovery reads the raw 64-candidate GraspNet binding
+ Preparation returns selected-first task-qualified opaque grasp refs
+ Action preparation iterates only that same-capture qualified set
```

### Runtime Evidence
- r9: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r9/`, task `task_114477e266344f0b`. The eight qualified refs and Adapter rejection refs match exactly in order; no raw candidate re-entered. / 八个资格引用与 Adapter 拒绝列表顺序完全一致，原始候选未回流。
- `simulated_motion_enabled=false`, `controller_outcomes=[]`, `world_change_started=false`, `outcome_known=true`, `possession_state=empty`; R04 and GLASS_ROD were not started. R03 still has no admissible route, so execution remains blocked. / 保持零动作、空持有；R04 和玻璃棒未启动，R03 仍无可行路线。

### Git Commit
- Implementation commit: `9a78d8e7`; branch `feature/planning-loop`; `2026-11-01 16:27:01 +0800`.
- Push withheld pending explicit approval under robotics runtime-safety guidance. / 按机器人运行安全规则，未获明确批准前不推送。

## v16.3.2 (2026-11-01 12:47) - codex

### Summary [Completed; no motion]
- [policy] [fix] `PhyAgentOS/agent/planning_dispatch.py:L887-L906` injects the exact Coordinator-owned `subtask_id`, `operation`, full `binding`, `parameters`, and `tool_sequence` for `manipulation.execute_subtask`; conflicting caller values still fail with `semantic_binding_mismatch`. / 从冻结 PlanNode 注入五个子任务字段，冲突调用值继续显式拒绝。
- [policy] [fix] `PhyAgentOS/agent/planning_loop.py:L1847-L1851` plus `SKILL.md:L361-L370` and the developer guide require AgentLoop to submit only current task-qualified process/grasp opaque references instead of reconstructing the full observation binding. / AgentLoop 仅提交当前 task-qualified opaque 引用，不再重构完整观测绑定。
- [test] [test] `tests/test_planning_dispatch.py:L447-L607` reproduces the 32-candidate R03 float mismatch and covers omission plus conflicts for all five frozen fields; focused validation passed `27 + 189 + 33 + 40`, Ruff, compileall, and diff check. / 回归覆盖大型候选绑定的精确注入与五字段冲突，定向测试及静态检查通过。
- [docs] [docs] Diagnosis: `.task/labutopia-r03-r04-semantic-binding-diagnosis-20261101.md:L1-L138`; review: `docs/forge/IMPLEMENTATION_REVIEW_V16_3_2.md:L1-L82`. / 保存诊断和 PAOS/AgentLoop/机器人安全复核。
- [env] [test] `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r2/acceptance.json` proves the selection passed the former mismatch and reached real preparation. R03 then stopped on provider-owned `no_admissible_grasp/route_collision`; motion remained disabled, no Tool atom completed, no world change, and possession stayed empty. / 新无动作链路越过原绑定失败，下一阻塞为 R03 路径碰撞，未运动、未持物、场景未变化。

### Key Diff / 关键 Diff
```diff
- model round-trips the complete observation-owned binding
+ Coordinator injects exact frozen input_binding_keys
+ Agent selects only process/grasp opaque references
```

### Git Commit
- Implementation commit: `e7783db4`; log receipt: `194ecedf`; branch `feature/planning-loop`.
- Push failed because `github.com:443` was unreachable after 134079 ms; commits remain local. / 推送因 GitHub 443 端口不可达而失败，提交仍在本地。

## v16.3.1 (2026-10-31 19:50) - codex

### Summary [Completed; dual-arm execution remains unavailable]
- [env] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L67-L95` rejects non-single-arm or non-`franka` requests before creating an assignment, including held-object preparation. / 对非单臂或非 `franka` 请求在创建 assignment 前拒绝，包含持有物体后的重新准备。
- [env] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py:L147-L157` preserves `unsupported_capability_topology` as an explicit Adapter failure. / 保留明确的 Adapter 能力拓扑错误，不转成抓取重试。
- [test] [test] `test_phase_pipeline.py:L216-L253` covers initial and held bimanual rejection; 63 focused tests passed, Ruff, compileall, and diff check passed. No Isaac or Action started. / 覆盖初始及持有状态的双臂请求拒绝；定向测试 63 项通过，Ruff、compileall、diff check 通过；未启动 Isaac 或动作。
- [docs] [docs] Saved the R01/R02 scene-entity versus manipulator-capability diagnosis and required second-Articulation work in `.task/labutopia-dual-arm-capability-diagnosis-20261031.md:L1-L38`. / 保存 R01/R02 场景实体与机械臂能力的诊断，以及增加第二个 Articulation 的前置工作。

### Git Commit
- Implementation commit: `077b5338`; branch `feature/planning-loop`; `2026-10-31 23:35 Asia/Shanghai`. / 实现提交 `077b5338`；分支 `feature/planning-loop`；北京时间 `2026-10-31 23:35`。

## v16.3.0 (2026-10-31 19:05) - codex

### Summary [Completed]
- [policy] [fix] `PhyAgentOS/agent/recovery_decisions.py:L37-L163,L235-L266,L396-L489` now projects only same-capture opaque grasp alternatives for a known zero-motion route-collision failure; stale provenance, missing alternatives, and provider-rejected candidates stop recovery. / 仅为已知零动作路线碰撞失败投影同捕获 opaque 替代候选；证据过期、无替代候选或已被 Provider 拒绝的候选保持停止。
- [env] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py:L145-L184` reports bounded `requires_replan` and all rejected candidate refs without changing collision checks. / 报告有界重规划提示和全部拒绝候选引用，不改变碰撞检查。
- [policy] [fix] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py:L477-L517,L765-L799,L1068-L1090` admits replan only for the first known no-motion preparation failure with empty possession and zero completed atoms; no automatic retry. / 仅在首个已知零动作准备失败、空持有且零原子动作时允许重规划，不自动重试。
- [test] [test] Added positive and negative recovery/Adapter tests; focused suites `124 passed`, Ruff, compileall and diff check passed. No Isaac or physical Action was started. / 增加正负恢复与 Adapter 测试；定向测试 `124 passed`，Ruff、compileall、diff check 通过；未启动 Isaac 或物理动作。

### Files and Diff / 文件与 Diff
- `PhyAgentOS/agent/recovery_decisions.py:L37-L163,L235-L266,L396-L489`: before, generic failure recovery lacked a same-capture alternative projection; after, only exact task/revision/observation/scene/frame/calibration/entity/candidate-set matches contribute opaque refs, excluding the failed and provider-rejected candidates. / 修改前无同捕获候选恢复投影；修改后只投影完整身份匹配的 opaque 引用并排除失败和 Provider 已拒绝候选。
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py:L145-L184`: before, all rejected routes produced a generic no-admissible-grasp error; after, explicit route collision carries bounded `requires_replan`, recommendation and rejected refs without changing collision evaluation. / 修改前只返回通用错误；修改后路线碰撞显式携带有限重规划信号和拒绝引用，不改变碰撞判断。
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py:L397-L432,L477-L517,L765-L799,L1068-L1090`: before, known zero-motion preparation failure settled with no replan; after, only the first known no-motion prepare failure with empty possession, zero completed atoms, explicit adapter ownership and route-collision code propagates replan; internal retry remains absent. / 修改前已知零动作准备失败不能重规划；修改后仅满足完整零动作事实的路线碰撞进入 Agent replan，不做内部重试。
- `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L65-L83,L291-L321,L674-L702` and `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml:L535-L561`: add provider-neutral no-motion facts and opaque `rejected_candidate_refs`. / 增加 Provider 中立的零动作事实和 opaque 拒绝候选引用。
- Tests: `examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py:L610-L680`; `tests/test_recovery_decisions.py:L165-L345`; `examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py:L932-L963`. Docs/diagnosis: `.task/labutopia-pour-lip-task-conditioned-20261031.md:L74-L110`; `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md:L585-L599`; `docs/forge/IMPLEMENTATION_REVIEW_V16_3_0.md:L1-L68`; detailed bilingual record: `changelog/2026-10_part16.md:L1-L72`. / 测试覆盖正例及过期、歧义、已拒绝候选和不满足零动作条件的负例；诊断、开发指南及实现审查已更新。
- Key Diff: `requires_replan = false` for the generic failure path -> `requires_replan = explicit_known_zero_motion_route_collision`; candidate retry -> Agent-proposed replacement revision using same-capture opaque alternatives. / 关键差异：通用失败固定不可重规划改为只允许明确的已知零动作路线碰撞；自动重试改为 Agent 在替代 revision 中选择同捕获 opaque 候选。

### Git Commit
- Implementation commit: `f27c01e5`; branch `feature/planning-loop`; `2026-10-31 19:42 Asia/Shanghai`. / 实现提交 `f27c01e5`；分支 `feature/planning-loop`；北京时间 `2026-10-31 19:42`。
