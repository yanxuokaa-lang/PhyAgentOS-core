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
