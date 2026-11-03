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

## v16.9.2 (2026-11-03 14:23) - codex

### 完成范围 / Completed Scope [Adapter 修复完成；等待新鲜仿真执行 / Adapter repair complete; fresh simulation execution pending]
- [env] [fix] acquire 闭合确认后的初始 lift 点最多容忍一个单指零载荷周期，仅当双侧 selected-body manifold 新鲜、另一指正载荷且夹持位姿仍在原阈值内；测量仍记录 `contact_load_valid=false`、`grasp_valid=false`。 / Tolerate at most one unilateral zero-load interval in the initial lift after confirmed closure, requiring fresh bilateral selected-body manifolds, positive load on the other finger and existing pose limits; measurements remain invalid load/grasp. (local)
- [eval] [chore] 下一周期必须恢复双指正载荷；持续/双侧卸载、缺失/过期 manifold 与闭合期单指接触 fail-closed。Adapter/executor 473 passed、2 skipped，Ruff、compileall 与 diff 检查通过。 / Require bilateral positive load in the next interval; persistent/bilateral unloading, missing/stale manifolds and unilateral closure fail closed. Adapter/executor passes 473 with 2 skips plus Ruff, compileall and diff checks. (local)
- [docs] [docs] 修复保持在 Isaac Adapter，AgentLoop、Coordinator、公共 Tool 合同、Provider 候选、阈值与碰撞策略不变；历史 uncertain-possession 场景未重跑。 / Keep the repair in Isaac Adapter without changing AgentLoop, Coordinator, public Tool contracts, Provider candidates, thresholds or collision policy; do not rerun the historical uncertain-possession scene. (local)

### 文件变更详情 / File Changes
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L668-L679, L1733-L1758, L1851-L1880
- `examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py` L22-L49, L97-L150
- `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L1411-L1412
- `.task/labutopia-lift-contact-transient-20261103.md` L1-L53; `.task/current.md` L3-L17
- `docs/forge/IMPLEMENTATION_REVIEW_V16_9_2.md` L1-L37; `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L994-L1009

```diff
+contact_load_valid = contacts()
+sample = {"grasp_valid": held, "contact_load_valid": contact_load_valid, ...}
+measured_sample["contact_transient_grace_used"] = True
+transient_lift_contact_grace = True
-measured_sample["grasp_valid"] = True
```

### Git 提交 / Git Commit
- Implementation commit: `01f8f5a8`; branch `feature/planning-loop`; 2026-11-03 15:07 Asia/Shanghai.

## v16.9.1 (2026-11-03 13:47) - codex

### 完成范围 / Completed Scope [支撑路径修复完成；实际抓取仍阻塞 / Support-path fix complete; live acquire still blocked]
- [env] [fix] Isaac Adapter 在既有 lift/lower 支撑窗口内将配置支撑 prim 匹配到 `/` 分隔的后代 collider；一般碰撞、IK、workspace、margin 与 AgentLoop 不变。 / Match configured support prims to slash-delimited descendant colliders only in the existing lift/lower support window; retain general collision, IK, workspace, margins and AgentLoop. (local)
- [eval] [chore] 回归覆盖子 collider、窗口外拒绝和前缀路径隔离；467 passed、2 skipped，Ruff、compileall 和 diff 检查通过。 / Regression covers descendant colliders, out-of-window rejection and prefix isolation; 467 pass, 2 skip, with Ruff, compileall and diff checks passing. (local)
- [eval] [exp] 新任务 `task_3ab10413aab34666` 通过 R03 完整 readiness 并进入真实 acquire；lift 以未知 possession 的 `physical_grasp_lost` 停止，R04/搅拌未开始。 / Fresh task passes full R03 readiness and enters live acquire; lift stops with `physical_grasp_lost` and uncertain possession, so R04/stir do not start. (local)

### 文件变更详情 / File Changes
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L59-L62, L1021-L1029
- `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L92-L140
- `.task/labutopia-support-collider-path-20261103.md` L1-L58
- `docs/forge/IMPLEMENTATION_REVIEW_V16_9_1.md` L1-L44
- `.task/current.md` L1-L20
- `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L975-L992

```diff
+return bool(root and (path == root or path.startswith(root + "/")))
-path in self.config["support_collision_paths"]
+any(prim_path_is_within(path, support) for support in support_collision_paths)
```

### 验证 / Validation
- Phase video: `out/lab-fullchain-truth-20261103-v16_9_1-execute-r1/artifacts/labutopia/phase-video/3a7c6036760444848d476edbceacd3aa.mp4` (19.93 s).
- No pour, R04 or stir success is claimed; the task remains `awaiting_replan` after unknown acquire outcome.

### Git 提交 / Git Commit
- Implementation commit: `72649a4e`; branch `feature/planning-loop`; 2026-11-03 14:14 America/Los_Angeles.

## v16.9.0 (2026-11-02 19:56) - codex

### 完成范围 / Completed Scope [局部实现完成；全路线资格阻塞 / Local implementation complete; full-route qualification blocked]
- [policy] [fix] Isaac Provider 使用同次点云和完整校准抓取帧拒绝瓶身侧夹持不对称、夹爪闭合轴沿瓶轴及夹指长度轴失配候选；只排序/过滤原有 opaque GraspNet 引用，不生成或平移抓取位姿。 / Isaac Provider uses same-capture points and calibrated grasp frames to reject asymmetric or axis-misaligned bottle grasps, ranking/filtering original opaque GraspNet refs without synthesizing or shifting poses. (local)
- [env] [feat] Isaac Adapter 在原 staged 全路径资格化前增加 direct current-pose/pregrasp route attempt，保留 staged fallback；碰撞、workspace、IK 连续性、aperture、接触及位移条件均未放宽。 / Isaac Adapter tries a direct current-pose/pregrasp route before the existing staged fallback, preserving all collision, workspace, IK-continuity, aperture, contact and drift checks. (local)
- [eval] [exp] 旧 R05 同捕获重放拒绝 candidate 69 的不对称夹持，8/503 候选通过几何过滤；新 no-motion 运行仅 candidate 178 通过工艺几何与短接近检查。该结果不是全路线 readiness 或夹持成功证明。 / Historical replay rejects asymmetric candidate 69 and retains 8/503 geometric candidates; fresh no-motion admits candidate 178 through geometry and short approach only, not full-route readiness or grip proof. (local)
- [eval] [exp] 新鲜授权仿真运行检查 8 条 direct、85 条 staged 路线，均未通过；Action preparation 超过 900 秒后前台 1200 秒限制结束，任务 awaiting_replan，无 readiness、controller outcome、运动视频或动作成功证据。 / Fresh authorized simulation rejects 8 direct and 85 staged routes; preparation exceeds 900 seconds and the foreground turn ends at 1200 seconds with awaiting_replan, no readiness/controller outcome/video/action success. (local)
- [docs] [docs] 更新当前任务、保存路线/夹持诊断、v16.9.0 实现复核与 PAOS 开发指南，区分 Provider、preparation、live evidence，并记录不放宽安全检查的后续路径。 / Update current task, preserve grasp/route diagnosis, add v16.9.0 review and document-guide boundaries distinguishing Provider, preparation and live evidence without relaxing safety checks. (local)

### 文件变更详情 / File Changes

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py` L239-L285, L577-L605, L632-L700
- [policy] [fix] 用 `candidate_world_pose` 应用 provider/TCP 标定，提取点云接触带分位数，拒绝单侧/偏心支持、开度不足和轴向错误；按几何质量对原候选做确定性排序。 / Apply calibrated provider/TCP transforms, measure point-cloud contact-band quantiles, reject one-sided/off-center/undersized/axis-misaligned grasps and deterministically rank original candidates.
```diff
pose, direction = candidate_world_pose(candidate, transform, provider_from_tcp)
closing_dot = abs(float(np.dot(closing_axis, axis)))
center_error / half_span > self.bottle_contact_center_ratio
return True, "", (approach_dot, center_error / half_span, closing_dot, -finger_dot)
```

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L304-L340, L1077-L1165
- [env] [feat] 新增 Adapter 私有 direct/staged route 策略和直达预抓取 waypoint；每个候选继续进入相同完整 `qualify()`，ready 结果记录选用策略。 / Add Adapter-private direct/staged route strategies and direct-pregrasp waypoints; every candidate still enters the same complete `qualify()` path and readiness records the chosen strategy.
```diff
"acquire_route_strategies": ["direct", "staged"]
current TCP -> direct_pregrasp -> grasp -> close -> lift
candidate = self.qualify(candidate_waypoints, ...)
```

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json` L14
- [env] [tune] mixture 部署优先尝试 direct，失败后保留 staged fallback。 / Configure the mixture deployment to try direct first while retaining staged fallback. (local)
```diff
+"acquire_route_strategies": ["direct", "staged"],
```

#### [新增 / Added] `.task/labutopia-stable-grasp-direct-route-20261102.md` L1-L117; `docs/forge/IMPLEMENTATION_REVIEW_V16_9_0.md` L1-L57
#### [修改 / Modified] `.task/current.md` L1-L30; `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L496-L532
- [docs] [docs] 保存候选几何诊断、原生 no-motion 与 Action preparation 结果、分层证据限制、架构复核和安全的下一分支。 / Preserve candidate geometry diagnosis, native no-motion/Action-preparation evidence, layered evidence limits, architecture review and safe next steps. (local)
```diff
+No route passed: 8 direct + 85 staged; no readiness or controller outcome.
+Do not claim bottle retention or natural trajectory is fixed.
+Preserve IK/collision limits; inspect fresh grasp frame and measured initial state.
```

### 验证 / Validation
- [eval] [chore] Provider/motion 聚焦回归 201 passed；Adapter + subtask executor 全量回归 464 passed、2 native USD skipped。 / Focused Provider/motion suite passes 201; full Adapter + subtask executor passes 464 with 2 native USD skips. (local)
- [eval] [chore] Ruff、compileall、`git diff --check` 通过；初始外部 pytest plugin 自动加载缺 `lark`，使用隔离插件加载后回归成功。 / Ruff, compileall and whitespace checks pass; initial system pytest auto-plugin import lacked `lark`, and isolated plugin loading then passed. (local)
- [eval] [exp] no-motion 任务 `task_894ef705415247a9` 在 Action 前停止；执行任务 `task_5f4231225e424e73` / `invocation://manipulation-execute_subtask/aba88568ff884e9d` 无完整路线 readiness，1200 秒后 awaiting_replan。 / No-motion task stops before Action; authorized simulation invocation has no full-route readiness and ends awaiting_replan after 1200 seconds. (local)
- [docs] [docs] 没有执行抓取/倾倒/搅拌控制动作，无 controller outcome 和 motion video；物理抓取稳定性与自然轨迹仍未验证。 / No grasp/pour/stir controller command, controller outcome or motion video exists; physical retention and natural trajectory remain unverified. (local)

### Git Receipt
- Branch: `feature/planning-loop`
- Commit: `2763945cb42cb2d12c631deaf609b15733f6aeda` (2026-11-02 20:27:17 Asia/Shanghai)
- [docs] [chore] 索引严格保留最新五版本；v16.6.3 完整内容留在月归档。 / Keep exactly the latest five versions in the index; retain v16.6.3 in the monthly archive.

## v16.8.0 (2026-11-02 16:05) - codex

### 完成范围 / Completed Scope [完成；真实抓取待验证 / Implemented; live grasp not yet verified]
- [docs] [docs] 保存 R03/R05 轨迹逐点起停、R05 异常密度与闭爪瞬态接触诊断；按 PAOS 开发指南明确 Adapter 归属、证据边界和未知项。 / Preserve the stop-start trajectory, inherited R05 density and closure-transient diagnosis with Adapter ownership and explicit evidence limits. (local)
- [env] [fix] 在 Isaac Adapter 的场景初始化边界应用版本化物理配置并记录实际质量/惯量/材质；保留外部 LabUtopia 用户修改，不将物理参数带入 AgentLoop。 / Apply configured physics at the Isaac scene initialization boundary and report runtime mass/inertia/material evidence, preserving external edits and keeping physics out of AgentLoop. (local)
- [policy] [fix] 以阶段连续时间参数化替代 acquire 逐点起停；对重新采样路径保留完整限位、工作空间及碰撞校验。 / Replace per-waypoint acquire stops with stage-continuous timing and validate retimed samples against existing joint, workspace and collision checks. (local)
- [policy] [fix] 渐进闭爪并在接触建立后保持夹持目标；实时检测目标漂移/接触丢失，补充有方向的接触证据，不放宽原抓取限值。 / Ramp gripper closure, retain the grip target after contact and detect drift/contact loss with directional evidence without relaxing existing grasp tolerances. (local)
- [eval] [chore] 增加无动作、替代机制、失效路径和执行器集成测试；进行实际 USD/Isaac 无动作物理核查，明确区分测试通过与真实抓取成功。 / Add no-motion, substitution, failure-path and executor integration tests plus a native USD/Isaac physics audit; distinguish tested mechanisms from live grasp success. (local)
- [docs] [chore] 预期影响 phase_motion.py、engine.py、profile.py、Adapter 私有物理模块及配置/测试、诊断、开发指南与 CHANGELOG；完成后记录精确 Diff/行号并定向提交推送当前分支。 / Expected changes cover motion, engine, profile, private physics/config/tests and diagnosis/guide/logs; record exact diffs/lines and commit/push only task-owned files on the current branch. (local)

### 架构与结果 / Architecture and Outcome
- [policy] [fix] 按 Tier C-Safety 复核；物理、时序、控制与原始接触证据全部留在 Isaac Adapter。AgentLoop、Skill Tool、opaque 候选链及 Coordinator 生命周期/取消/对账归属不变；无新增 Core 字段、hash 或重复门禁。 / Keep physics, timing, control and raw contact evidence Adapter-private; preserve AgentLoop, Tool contracts, opaque candidate lineage and Coordinator ownership without new core fields, hashes or redundant gates. (local)
- [env] [tune] 显式仿真假设：每瓶 0.10 kg（0.06 kg 空瓶加 0.04 kg 固定载荷），玻璃/手指/桌面摩擦与主指驱动 2 N 上限；不是测得的实验室参数或液体转移模型。 / Use documented development assumptions for mass, friction and drive cap, not measured lab properties or fluid transfer. (local)
- [eval] [exp] 离线同轨迹节点、60 Hz 指令时序比较：R03 50.683→22.366 秒，R05 51.300→24.167 秒，排除开闭爪/抬起/停留；不是原生执行提速证明，约 1 m 的几何绕路不变。 / Offline command timing improves with the same knots, excluding grip/lift/holds; no new runtime speed or route-optimality proof. (local)

### 文件变更详情 / File Changes

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L172-L194, L580-L623, L650-L651, L1131-L1184, L1622-L1764
- [policy] [fix] 新增阶段连续重定时、实际采样全路径校验、接触渐进闭爪/保持/失效停止与子步向量证据；复核补齐双指接触但夹持变换失配时立即停止。 / Add stage retiming, swept-sample qualification, ramp/hold/failure closure and substep vector evidence; reject bilateral transform mismatch immediately. (local)
```diff
-def continuous_joint_path(points, dt, duration, velocity_limit, acceleration_limit):
+def continuous_joint_path(points, dt, duration, velocity_limit, acceleration_limit, *, ease_endpoints=False):
+    # Global quintic clock; analytic chain-rule velocity/acceleration bounds.
+    # _time_acquire_route validates limits, FK workspace and swept collisions.
-points = route["steps"]
+points = route.get("execution_steps", route["steps"])
-finger_target = .04 if operation == "acquire" else 0.
+finger_target = np.full(2, .04) if operation == "acquire" else np.asarray(
+    self.robot.get_joint_positions())[finger_indices].copy()
-elif stage == "close":
-    finger_target = 0.
+closure = list(smooth_joint_segment(measured_fingers, np.zeros(2), dt, finger_speed, finger_acceleration))
+# Freeze target on qualified bilateral contact; require stable settling.
+if contacts() and not held:
+    raise PhaseMotionError("grasp_transform_mismatch", ...)
+# Existing drift tolerances and contact loss stop before lift.
```
The excerpt abbreviates local variable expressions/comments; exact source ranges above are authoritative. / 摘要 Diff 中局部表达式与注释经缩写，以上源文件行号为准。

#### [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/scene_physics.py` L1-L152
- [env] [fix] 验证并解析全部目标后在 session layer 应用质量、凸分解、材质和驱动；初始化后独立读取并检查实际质量/惯量/COM，保留外部源资产。 / Resolve targets before applying session opinions and independently check actual initialized mass/inertia/COM without modifying source assets. (local)
```diff
+with Usd.EditContext(stage, stage.GetSessionLayer()):
+    mass.CreateMassAttr(spec["mass_kg"])
+    mass.CreateDensityAttr(0.)
+    # Bind physical materials to collider and subsets.
+mass = float(np.asarray(view.get_masses()).reshape(-1)[0])
+inertia = np.asarray(view.get_inertias()).reshape(3, 3)
+com, orientation = view.get_coms()
```

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py` L1035-L1046, L2497-L2498, L2506-L2510, L2519-L2520
- [env] [fix] 在原有场景初始化边界、reset 前应用物理，之后记录实际读数；禁止同会话切换物理配置。 / Apply physics at existing initialization before reset, persist actual readback afterwards, and reject switching profiles in one loaded session. (local)
```diff
+if profile.physics_config_path is not None:
+    physics_report = apply_scene_physics(stage, load_physics_config(profile.physics_config_path))
+report = read_runtime_physics(scene["physics_report"])
+scene["physics_evidence_ref"] = store.write("scene-physics", report)
```

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/profile.py` L67, L141, L189-L190
- [env] [feat] 可选私有 physics_config_path 按配置文件位置解析并检查存在性，未配置的部署保持原行为。 / Add optional relative private physics profile with file-existence validation; deployments without it preserve behavior. (local)
```diff
+physics_config_path: Path | None = None
+physics_config_path=path_value("physics_config_path") if value.get("physics_config_path") else None,
```

#### [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-physics.json` L1-L16
#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json` L14, L75-L76; `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json` L5
- [env] [tune] 集中部署假设与开关，不修改外部 LabUtopia 场景或在代码硬编码物体位置。 / Centralize deployment assumptions/settings without modifying external scenes or hardcoding object positions. (local)
```diff
+"physics_config_path": "labutopia-mixture-physics.json",
+"acquire_timing": "stage_continuous",
+"finger_velocity_m_s": 0.015,
+"finger_acceleration_m_s2": 0.15,
+"bodies": [{"asset_type": "reagent_bottle", "mass_kg": 0.10, "material": "glass", "hull_vertex_limit": 36, "max_convex_hulls": 32}],
```

#### [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/physics_probe.py` L1-L69
- [eval] [feat] 通过真实 backend 启动/复位，核对八瓶实际物理属性与关节；只写证据、不发 motion command、不伪装抓取成功。 / Probe actual backend initialization/reset and measured body/joint state, recording evidence without motion commands or fake grasp success. (local)
```diff
+backend.ensure_action_scene(session)
+first = read_runtime_physics(scene["physics_report"])
+world.reset()
+reset = read_runtime_physics(scene["physics_report"])
+# Assert mass/inertia and configured initial joints survive reset.
+report = {"status": "passed", ..., "motion_commands": 0, "grasp_success_proven": False}
```

#### [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py` L1-L187; `examples/forge-adapters/isaacsim_lab/tests/test_scene_physics.py` L1-L103
#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_engine.py` L556-L581; `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L222-L243, L328-L331, L1384, L1406
- [eval] [fix] 补充变换失配、瞬态接触丢失、漂移、取消、后续开度、采样消费、阶段时序与 swept 碰撞失效测试；补齐 prepare→readiness 接线、reset 前物理应用及替代 USD 测试。 / Cover mismatch, transient loss, drift, cancellation, subsequent aperture, sample consumption, timing/swept failures, readiness wiring and alternative USD initialization. (local)
```diff
+assert result["failure_code"] == "grasp_transform_mismatch"
+assert model.world.steps == 1
+assert all(c[7] > .039 for c in commands)
+assert model.world.steps == len(route["execution_steps"])
+assert stage.GetRootLayer().ExportToString() == original
-shift = .012 if model.world.steps else 0.
+shift = .006 if model.world.steps else 0.  # Within the unchanged 8 mm pre-lift drift limit.
```
- [eval] [docs] 旧 measured-grasp 测试位移改为 6 mm 使其继续验证合法夹持跟踪；新增 9 mm 漂移拒绝测试独立覆盖原 8 mm 限值，不以改测试隐藏拒绝行为。 / Keep the measured-grasp test within tolerance and separately prove 9 mm drift rejection against the unchanged 8 mm bound. (local)

#### [新增 / Added] `.task/labutopia-contact-and-timing-repair-20261102.md` L1-L164; `docs/forge/IMPLEMENTATION_REVIEW_V16_8_0.md` L1-L68
#### [修改 / Modified] `.task/current.md` L1-L25; `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L495-L532
- [docs] [docs] 保存原生证据、诊断限制、PAOS 归属、完整复现命令、分层验收、实现复核和下一次接触验证分支。 / Save diagnosis/evidence limits, ownership, reproduction commands, layered acceptance, review and next contact-validation branches. (local)
```diff
+No new physical grasp/pour/stir execution, video, or hardware proof.
+Physics and control remain Adapter-private; AgentLoop retains opaque semantics.
+Readback success is not effective-friction, fluid-transfer or live-grasp proof.
```

### 验证 / Validation
- [eval] [chore] Adapter + Skill subtask executor：450 passed, 2 skipped，10.10 秒；默认环境无 pxr，两项跳过在原生 USD 环境单独执行，物理模块 10 项全通过。 / Full regression passes; the two pxr-dependent skips separately pass with actual native USD libraries. (local)
- [eval] [exp] Isaac 原生 probe 退出码 0、8 个刚体质量均约 0.10000000149 kg，惯量/COM 合法；读数不推进时间/不改变关节，reset 保持质量/惯量及初始关节，0 条运动指令。 / Native readback/reset succeeds with valid physical values, unchanged read-only state and zero motion commands. (local)
- [data] [docs] 制品 `out/lab-contact-timing-20261102-r1/artifacts/labutopia/physics-probe/202c33511beb4a099fd157965af89e8e.json` 与 `scene-physics/629bde4671b0440fbaefa73a7c6632a0.json`；Kit 原始 scale/MDL/CPU particle 错误保留，未声称液体物理或渲染验收通过。 / Preserve native receipts and source scene warnings/errors; no fluid/rendering acceptance claim. (local)
- [eval] [chore] 修改 Python 文件 Ruff 通过、git diff --check 通过；初始 pytest 缺 async 插件及独立 USD 缺原生库/插件路径的失败已记录，只有修正后的结果计为通过。 / Lint/diff checks pass; distinguish corrected successful validations from initial environment failures. (local)
- [docs] [docs] 本次不重放旧 readiness，不执行新的倒液/搅拌，不生成运动视频；旧 R05 录像保留。实际夹持稳定性与 R03 插入几何仍须新捕获、新 preparation、新 Action 验证。 / Do not replay stale readiness or claim new process/video success; fresh capture/preparation/Action remains required for physical grip and insertion validation. (local)

### Git 提交 / Git Receipt
- Branch: `feature/planning-loop`
- [docs] [chore] 本版本任务文件定向提交；提交 hash 在后续回执中记录后与索引一同推送当前分支。无关工作区与 out/ 制品不纳入提交。 / Commit only task-owned files; record the commit in a follow-up receipt and push the current branch, excluding unrelated changes and runtime artifacts. (local)
- Commit: `b05978df`
- 时间 / Time: 2026-11-02 16:26 Asia/Shanghai
- [docs] [chore] 18 个任务相关文件已提交；本回执同步索引后另作文档提交，两个提交共同推送当前工作分支。月日志新增范围 L1146-L1270，索引最新条目范围 L51-L175；其余四条与月归档一致。 / Commit 18 task-owned files; synchronize this receipt to the index, then push implementation and receipt commits on the current branch. Monthly entry spans L1146-L1270 and latest index entry L51-L175; other four entries match their archive. (local)

## v16.7.2 (2026-11-02 14:56) - codex

### 完成范围 / Completed Scope [目标纠正与重跑完成；抓取未成功 / Target correction and rerun complete; grasp unsuccessful]
- [docs] [fix] 审核用户指定的左右区域近机械臂内侧角：历史最终组合几何显示 R03/R04 同属 A，目标应为 B/R05 与 A/R03；以新无动作观测和标注图确认，保存诊断。 / Audit the requested near-arm inner corners: composed geometry places both previous R03/R04 in A; verify B/R05 and A/R03 through a fresh no-motion observation and annotated view, then save diagnosis. (local)
- [policy] [fix] 修正本次任务输入及复现指令，按左侧 R05、右侧 R03 运行；不硬编码 Provider 选择、不改 AgentLoop 生命周期、不改场景标签/几何、不放松动作校验。 / Correct task input and reproducible instruction to left R05 then right R03 without hardcoding Provider selection, changing AgentLoop ownership, relabeling geometry or weakening checks. (local)
- [eval] [exp] 从新仿真会话重新发起原生 Agent，保留同次真值感知、参数化动作与阶段录像；区分位置确认、路线资格、执行与成功。 / Relaunch the native Agent from a fresh simulator session with same-capture truth, parameterized actions and videos; distinguish identity, readiness, execution and success. (local)
- [docs] [docs] 更新 .task/current.md、选择诊断、任务指令、开发指南和最近五条索引；记录精确行号、Diff、验证与当前分支提交推送。 / Update current task, selection diagnosis, instruction, developer guide and latest-five index with ranges, diffs, validation and current-branch commit/push. (local)

### 位置审核 / Position Audit
- [eval] [exp] 新无动作观测 revision `49cc517596d64d959d7ad15742f91573:0` 的最终 Model 世界包围盒与相机标定投影证实：左区右下 R05 像素 (432.35,653.46)，右区左下 R03 (1063.63,807.74)；R04 在右区后排 (1124.47,685.95)。 / Fresh composed Model bounds and calibrated projection confirm left-inner-front R05 and right-inner-front R03; R04 is in the rear row of the right zone. (local)
- [data] [docs] `out/lab-near-arm-selection-20261102-observe-r1/selected-bottles.png` 保留八瓶标注与两目标绿圈；selection-audit.json 保留同次几何/标定来源、各中心与距离。R05/R03 在各自区域到基座水平距离最短，约 0.40249 m；距离不作为抓取成功证据。 / Preserve annotated image and same-capture audit; selected objects are nearest within their respective zones, without treating distance as grasp proof. (local)
- [eval] [chore] 51 项现有 host、semantic task creation、perception binding 测试通过；只修正任务输入，不增加无关运行时逻辑。 / 51 existing host/semantic-task/binding tests pass; correct task input without unrelated runtime changes. (local)

### 文件变更详情 / File Changes

#### [修改 / Modified] `.task/current.md` L1-L28
- [docs] [fix] 当前目标由旧 R03/R04 改为已审核的 R05/R03，并保存新任务、检查结果、实际闭爪失败与停止边界；历史条目不改写。 / Replace the current target pair with verified R05/R03 and record the new task, checks, closure failure and stop boundary without rewriting historical entries. (local)
```diff
-# Current Task: LabUtopia R03/R04 full-chain grasp coverage
+# Current Task: LabUtopia near-arm inner-corner selection
+R05 -> R03 -> GLASS_ROD; fresh observation and parameter-preserving bindings
+R05 close: grasp_not_confirmed; task awaiting_replan; no lift/pour/R03/stir
```

#### [新增 / Added] `.task/labutopia-near-arm-instruction.txt` L1
- [policy] [fix] 保存可复现任务输入：左侧 B/R05 后右侧 A/R03，沿用 tilt_rad=0.87、hold_s=0.6 以及原搅拌参数；禁止选择 R04，不改变场景标签/物体位置。 / Save reproducible input for B/R05 then A/R03 with unchanged pour/stir parameters; exclude R04 without relabeling or moving objects. (local)
```diff
+用户指定左边区域右下角、右边区域左下角；审核对应左侧 B/R05、右侧 A/R03。
+先 R05、再 R03 倾倒至 BEAKER，然后 GLASS_ROD 搅拌；使用新捕获的合格引用。
```

#### [新增 / Added] `.task/labutopia-near-arm-selection-20261102.md` L1-L153
- [docs] [docs] 保存最终几何/标定位置审核、模块归属、原生运行命令、51 项测试命令、持久化 Action 绑定、终态反馈、录像边界及剩余接触问题。 / Save composed-geometry/calibration audit, ownership, native/test commands, persisted Action bindings, terminal feedback, video boundaries and remaining contact issue. (local)
```diff
+Previous R03/R04 request selected two bottles in A; verified intended pair is B/R05 and A/R03.
+Fresh graph and readiness bind the verified physical R05; complete route passes.
+Closure displaces R05 393.292 mm; final finger impulses [0,0]; stop before lift.
```

#### [修改 / Modified] `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L461-L470
- [docs] [docs] 明确空间目标纠正应基于新观测的图像/标定/最终几何关联，再修改任务请求；不得把固定位置映射放入 AgentLoop/Grasp Provider 或把靠近当作可抓取。 / Document fresh observation-based spatial correction at the task boundary, without fixed scene mapping in AgentLoop/Grasp Provider or proximity-as-graspability claims. (local)
```diff
+For a spatial target correction, establish the requested viewpoint and resolve
+the requested objects against a fresh composed-scene observation.
+The corrected request then uses the existing semantic selectors and current
+Query bindings; proximity alone is not graspability or full-route evidence.
```

### 原生验证与录像 / Native Validation and Video
- [eval] [exp] `task_8983ebbef39b4da4` / `revision_3eb048c8f12047eb` / `cli:lab-68c0bd18324b` 的持久化图按 R05、R03、GLASS_ROD 排序，参数保持；四个 R05 Query succeeded。 / Persisted graph confirms the corrected ordered identities and parameters; four R05 Queries succeed. (local)
- [eval] [exp] 完整 acquire 选择同次候选 69，前两路线分别 IK 连续性、payload/table 拒绝，第三条 8.731 秒通过、146 轨迹点；readiness target 是 B/R05/Model/mesh。 / Full acquire selects current candidate 69; first two variants fail IK continuity and payload/table checks, third passes in 8.731 s with 146 waypoints and correct B/R05 binding. (local)
- [eval] [exp] 真实运输/接近/插入完成，目标位移不超过 1.006 mm；闭爪才出现快速位移，最终 393.292 mm，双指最终接触冲量 [0,0]，grasp_not_confirmed 在抬起前停止。Action unknown、possession uncertain、task awaiting_replan；未执行 R03、倾倒、归位或搅拌。 / Actual transport/approach/insertion retain <1.006 mm drift; closure causes 393.292 mm final displacement and loses finger contact, stopping before lift. Preserve unknown/uncertain states; no later operations occur. (local)
- [eval] [docs] 前台 40 次调用上限不等于物理终态；原 host 等待既有 Runtime 对账，没有重复 Action。反馈不足以进一步断言摩擦、驱动力或接触几何中的哪一个是根因，不放宽任何检查。 / Foreground iteration exhaustion is not physical settlement; host waits for Runtime without duplicate Action. Evidence does not yet isolate friction, drive force or contact geometry; checks stay unchanged. (local)
- [data] [docs] `out/lab-fullchain-truth-20261102-near-arm-r05-r03-r1/` 保存 acceptance.json、host.log、run-context.json、stage-videos.json。原 MP4 3191 帧/60 fps/53.183 秒/88,733,263 bytes；全部帧解码通过。 / Preserve task/log/context/stage records and fully decoded raw footage with the stated frame count, rate, duration and size. (local)
- [data] [docs] H.264 审阅视频：`r05-motion-through-approach.mp4` 47.333 秒/1420 帧；`r05-acquire-stopped-before-lift.mp4` 53.200 秒/1596 帧；`r05-close-quarter-speed.mp4` 6.533 秒/196 帧，明确四分之一速度。三份均完整解码，原视频未改；末帧已视觉复核。 / Three fully decoded H.264 copies cover completed approach, full failed attempt and explicitly quarter-speed closure; original stays intact and final image is reviewed. (local)
- [docs] [chore] 月日志与 CHANGELOG 最近五版本同步；本轮只提交任务输入/诊断/指南/日志，out 下录像与诊断制品保留本地，无关工作区修改不纳入提交。 / Synchronize latest-five index; commit only task input/diagnosis/guide/logs, retain local runtime artifacts and leave unrelated changes unstaged. (local)

### Git 提交 / Git Receipt
- Commit: `66f1c11a`
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-11-02 15:21 Asia/Shanghai
- [docs] [chore] 提交 6 个任务相关文件；此回执与索引另作文档提交后共同推送当前分支。 / Commit six task-owned files; record this receipt and index in a follow-up documentation commit and push the current branch. (local)
