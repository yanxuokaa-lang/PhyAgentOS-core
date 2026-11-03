# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

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

## v16.9.7 (2026-11-03 20:11) - codex

### 完成范围 / Completed Scope
- [env] [fix] 为 acquire 路线搜索增加 600 秒 Adapter 私有预算，在 900 秒 worker transport deadline 前以 `route_search_timeout`、零动作和有界诊断返回；未放宽任何运动或抓取安全条件。 / Add a 600-second Adapter-private acquire-route budget that returns `route_search_timeout`, zero motion and bounded diagnostics before the 900-second worker transport deadline without relaxing motion or grasp safety criteria. (local)
- [env] [fix] transport/child failure 后永久失效 worker wrapper；Backend 清除匹配 session，并在 fresh observe/reset 前用 `fresh_observation_required` 阻止 prepare/qualify/execute 创建空白 worker。 / Permanently invalidate a worker wrapper after transport or child failure; clear the matching Backend session and block prepare/qualify/execute from creating a blank worker with `fresh_observation_required` until a fresh observe/reset occurs. (local)
- [env] [fix] socket 读取服从请求剩余 deadline，断连后不二次写响应；prepare transport failure 保持 known/no-world-change，execute transport loss 保持 conservative unknown。 / Make socket reads obey the remaining request deadline and avoid second writes after disconnect; keep prepare transport failure known/no-world-change and execute transport loss conservatively unknown. (local)

### 文件变更详情 / File Changes
- `phase_motion.py` L310-L320, L721, L1116-L1240; `worker_session.py` L51, L86-L98, L129-L136, L189-L204, L230
- `engine.py` L596-L639, L661-L674, L688-L700, L718-L730, L739, L839-L859, L898-L900; `worker.py` L182-L199
- `labutopia-mixture-motion.json` L14; `test_phase_motion.py` L15, L397-L468; `test_worker_session.py` L11, L287-L312; `test_engine.py` L277-L389
- `.task/current.md` L1-L35; `.task/labutopia-worker-session-timeout-repair-20261103.md` L1-L97; `docs/forge/IMPLEMENTATION_REVIEW_V16_9_7.md` L1-L44

```diff
+if now >= search_deadline: raise PhaseMotionError("route_search_timeout", ...)
+if recovery_requires_observation: return fresh_observation_required
+socket.settimeout(min(0.2, remaining_request_budget))
```

### 验证 / Validation
- [eval] [test] 聚焦 222 passed；完整 Adapter/executor 488 passed、2 skipped；Ruff、compileall、JSON 和 diff 检查通过；实现复核最终无 Blocker/Major。 / Focused tests pass 222 cases; full Adapter/executor passes 488 with two skips; Ruff, compileall, JSON and diff checks pass; final implementation review has no Blocker or Major. (local)
- [eval] [exp] fresh no-motion reset 创建新 task/revision/scene 与当前 capture 的唯一 R05 合格 opaque 候选，Action 记录为 0；独立原生 probe 记录零运动命令和约 0.04 m 的双指张开状态。 / A fresh no-motion reset creates a new task, revision and scene with the sole current-capture qualified R05 opaque candidate and zero Action records; an independent native probe records zero motion commands and both fingers open near 0.04 m. (local)
- [policy] [chore] 未恢复历史 task/readiness；未执行 R05 Action，R03 与 GLASS_ROD 保持阻塞。 / Do not restore historical tasks or readiness; no R05 Action executes, and R03 plus GLASS_ROD remain blocked. (local)

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`; implementation commit pending.

## v16.9.6 (2026-11-03 19:17) - codex

### 完成范围 / Completed Scope
- [policy] [test] 本轮目标严格固定为靠近机械臂的 R05 后 R03，不选择 R04；fresh execution 仅绑定当前 R05 直接前驱 preparation 的同集合 opaque 引用。 / Fix this run strictly to near-arm R05 followed by R03, excluding R04; fresh execution binds only the same-set opaque R05 reference from its direct predecessor preparation. (local)
- [env] [exp] R05 Action 在首个 preparation 阶段因 Isaac worker request timeout 失败；终态 `outcome_known=true`、`world_change_started=false`、`possession_state=empty`，R03 与搅拌未开始。 / R05 Action fails in its first preparation phase because the Isaac worker request times out; the outcome is known with no world change and empty possession, so R03 and stirring never start. (local)
- [docs] [docs] 诊断归属 Adapter worker/session 生命周期，不修改 AgentLoop、公共 Tool 合同、候选语义或安全阈值。 / Assign the diagnosis to Adapter worker/session lifetime without changing AgentLoop, public Tool contracts, candidate semantics or safety limits. (local)

### 文件变更详情 / File Changes
- `.task/labutopia-r05-r03-fresh-reset-runtime-timeout-20261103.md`
- `.task/current.md`
- `changelog/2026-11_part2.md`
- `CHANGELOG.md`

### 验证 / Validation
- Fresh no-motion and execution task/revision/scene/candidate identifiers are distinct.
- Execution lineage contains no historical task or no-motion readiness reference.
- No phase video exists because controller motion never began.

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`.
- Implementation/diagnosis commit: `f1b33f2cd6d949407ba85608af42baab670bacee`; 2026-11-03 19:54:49 Asia/Shanghai.

## v16.9.5 (2026-11-03 17:04) - codex

### 完成范围 / Completed Scope
- [env] [fix] 将当前控制窗口的双指正冲量与 fresh bilateral selected-body manifold 分离；只有 acquire 已确认闭合、物体仍在既有支撑离台窗口且夹持变换仍在既有阈值内时，静态 manifold 才可保持执行连续性。原始样本仍为无效 load/grasp。 / Separate bilateral positive impulse from fresh bilateral selected-body manifolds; static manifold continuity is allowed only after confirmed acquire closure inside existing support and grasp-transform bounds, while raw load/grasp remains invalid. (local)
- [policy] [chore] 修复保持在 Isaac Adapter；AgentLoop、Coordinator、Provider、opaque 引用、公共 Tool 合同、动作参数、碰撞/IK/workspace 阈值和 settlement 所有权不变。 / Keep the repair in the Isaac Adapter without changing AgentLoop, Coordinator, Providers, opaque references, public Tool contracts, process parameters, collision/IK/workspace limits or settlement ownership. (local)

### 文件变更详情 / File Changes
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L658-L672, L1726-L1744, L1847-L1881
- `examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py` L97-L230
- `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L1450-L1475
- `.task/labutopia-static-contact-manifold-20261103.md` L1-L92; `.task/current.md` L1-L18
- `docs/forge/IMPLEMENTATION_REVIEW_V16_9_5.md` L1-L55; `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L994-L1038

```diff
-def one_finger_unloaded(self): ...
+def fresh_bilateral_manifolds(self): ...
+contact_manifold_valid = contact_window.fresh_bilateral_manifolds()
-if ... not lift_contact_grace_used and contact_window.one_finger_unloaded():
+if ... measured_support_contact and samples[-1]["contact_manifold_valid"]:
+    measured_sample["support_manifold_continuity_used"] = True
```

### 验证 / Validation
- [eval] [chore] 聚焦回归 15 passed；Isaac Adapter + subtask executor 477 passed、2 skipped；Ruff、compileall 和 `git diff --check` 通过。 / Focused regression passes 15 tests; full Adapter plus subtask executor passes 477 with 2 skips; Ruff, compileall and diff checks pass. (local)
- [eval] [exp] 未发起新 Action；下一次 live 验证必须再次 reset，并生成新 scene revision、新感知和新完整 preparation。 / No new Action is issued; live validation requires another reset, scene revision, fresh perception and full preparation. (local)

### Git 提交 / Git Receipt
- Branch: `feature/planning-loop`.
- Implementation commit: `03d726f92bdee7a0a167b4398c908e5b4c696565`; 2026-11-03 19:11 Asia/Shanghai.

## v16.9.4 (2026-11-03 16:21) - codex

### 完成范围 / Completed Scope
- [eval] [exp] 独立 no-motion reset 确认 R03 在支撑面且夹爪为空；执行任务 `task_1826699dc9cd456b` 使用另一新 revision、scene revision、感知与完整 preparation，再提交唯一 R03 Action。 / An independent no-motion reset confirms R03 on support and an empty gripper; the execution task uses another fresh revision, scene revision, perception and full preparation before its only R03 Action. (local)
- [eval] [exp] acquire lift 以 `physical_grasp_lost`、unknown outcome、uncertain possession 和 world change 停止；R03 倾倒/归位、R04 和搅拌未启动，AgentLoop 正确取消后续流程。 / Acquire lift stops with physical grasp lost, unknown outcome, uncertain possession and world change; R03 pour/place, R04 and stirring do not start, and AgentLoop cancels the remaining workflow. (local)

### 运行证据 / Runtime Evidence
- Workspace: `out/lab-fullchain-truth-20261103-v16_9_4-execute-r1/`.
- Task/revision: `task_1826699dc9cd456b` / `revision_45ff037f9c294bb7`.
- Scene revision before Action: `labutopia-tabletop-rod-rack-v1:1186db97869a4b4fa77992d0b85f3032:0`; after world change: suffix `:1`.
- Video: `artifacts/labutopia/phase-video/6f7d3b9a95414b009368baec07f75de3.mp4` (19.95 s, 3840x960, 60 fps, 1197 frames).
- Feedback: `artifacts/labutopia/phase-feedback/6584c65280ef4d0cbb67e06c15ecdc7b.json`.
- [policy] [exp] 该任务和 readiness 不可恢复；后续必须重新 reset、感知和 preparation。 / The task and readiness are not reusable; any later Action requires another reset, perception and preparation. (local)

## v16.9.3 (2026-11-03 15:50) - codex

### 完成范围 / Completed Scope [Adapter 修复完成；等待新鲜 reset 后执行 / Adapter repair complete; fresh post-reset execution pending]
- [eval] [exp] 新鲜 reset 确认 R03 回到支撑面且夹爪为空；授权任务 `task_448f4e2bf09042fe` 使用新 revision 与同集合 opaque 引用进入 acquire，在第 18 个 retimed lift 采样以 `physical_grasp_lost` 和 uncertain possession 停止。 / A fresh reset confirms R03 on support and an empty gripper; authorized task `task_448f4e2bf09042fe` uses a new revision and same-set opaque references, then stops on retimed lift sample 18 with `physical_grasp_lost` and uncertain possession. (local)
- [env] [fix] 将闭合确认保存为 Isaac Adapter 私有 lift 状态，并只在当前测得物体仍处于已有支撑离台窗口时允许一次单指零载荷瞬态；样本仍记录无效，下一周期必须恢复双指载荷。 / Persist closure confirmation as Isaac Adapter-private lift state and allow one unilateral zero-load transient only while the measured object remains in the existing support-departure window; keep the sample invalid and require bilateral recovery on the next interval. (local)
- [eval] [fix] 生产形状的 retimed 回归覆盖延迟瞬态恢复与支撑窗口外拒绝；不改变 AgentLoop、Coordinator、Provider、公共 Tool 合同或碰撞/IK/workspace/接触阈值。 / Production-shaped retimed regressions cover delayed transient recovery and out-of-support rejection without changing AgentLoop, Coordinator, Providers, public Tool contracts or collision/IK/workspace/contact thresholds. (local)

### 文件变更详情 / File Changes
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L1731-L1891
- `examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py` L114-L137
- `.task/labutopia-lift-support-window-20261103.md` L1-L79; `.task/current.md` L1-L18
- `docs/forge/IMPLEMENTATION_REVIEW_V16_9_3.md` L1-L43; `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L1011-L1029

```diff
+lift_grip_confirmed = last_stage == "close"
+measured_support_contact = support_contact_allowed(...)
-if operation == "acquire" and last_stage == "close" ...
+if operation == "acquire" and lift_grip_confirmed ... and measured_support_contact ...
+model._time_acquire_route(args["phase_route"])
```

### 验证 / Validation
- [eval] [chore] 接触/时序 22 passed；显式加载已安装的 async pytest 插件后，Isaac Adapter + subtask executor 475 passed、2 skipped；Ruff、compileall 与 diff 检查通过。 / Contact/timing passes 22 tests; with the installed async pytest plugin explicitly loaded, Isaac Adapter plus subtask executor passes 475 with 2 skips; Ruff, compileall and diff checks pass. (local)
- [eval] [exp] 当前失败场景已发生 world change 且 outcome unknown，不得继续；后续 live 验证必须重新 reset，生成新 scene revision、新感知、新 preparation 后再 Action。 / The current failed scene has world change and unknown outcome and must not continue; live validation requires another reset, new scene revision, fresh perception and fresh preparation before Action. (local)

### Git 提交 / Git Receipt
- Branch: `feature/planning-loop`.
- Implementation commit: `7e880acd231da23392d90a228be18e62d9c85361`; 2026-11-03 16:13 Asia/Shanghai. Monthly entry L1415-L1462; latest-five index entry L51-L78.
