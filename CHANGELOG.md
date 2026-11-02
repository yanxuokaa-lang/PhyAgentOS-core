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

## v16.7.0 (2026-11-02 12:59) - codex

### 预期修改 / Planned Changes [完成局部修复；完整流程尚未通过 / Local repairs complete; full workflow not accepted]
- [docs] [docs] 保存当前受检集合四个超开口、六个终态受阻的诊断；先检查模型原始候选覆盖、截断与工艺筛选各自丢失的区域，再选择有证据的 Provider 修复。 / Save four aperture and six final-pose failures; measure losses from model coverage, truncation and process qualification before choosing an evidenced Provider repair. (local)
- [sense] [feat] 在现有 Grasp/Task-Affordance Provider 接口后改善当前几何支持的候选覆盖；候选保持模型/观测来源与新 opaque 身份，不在 Action recovery 改位姿，不调低安全裕量或直接放松瓶口阈值。 / Improve geometry-supported coverage behind existing Provider ports, retaining model/observation provenance and new opaque identity; never shift poses in Action recovery, reduce margins or merely relax opening thresholds. (local)
- [eval] [chore] 先建立失败复现与替代机制/同捕获/零动作测试，再接入运行配置并做原生无动作验收，分别记录契约、Provider 和执行证据。 / Establish regression, substitution, same-capture and no-motion tests before runtime wiring and native no-motion validation; distinguish contract, Provider and execution evidence. (local)
- [docs] [docs] 遵守现有 AgentLoop/Coordinator 生命周期职责，完成架构审查、精确 Diff/行号、双语日志与当前分支提交推送；保留无关用户变更。 / Preserve AgentLoop/Coordinator lifecycle ownership; finish architecture review, precise diffs/ranges, bilingual logs and current-branch commits/push while preserving unrelated edits. (local)
- [sense] [fix] 配对历史实测：1057 个阈值后原始候选中 4 个通过现有工艺/开口且手掌 padded bounds 高于桌面，worker 512 中留 2 个，64 截断后为 0。优先将实验 profile 的 retained budget 恢复为现有 512 sampling 上限，让原始去重候选进入后续资格检查；不新增姿态生成或放松工艺规则。 / Paired historical measurement finds four process/aperture-qualified poses with padded palm above tabletop among 1057 native candidates, two in worker 512 and zero after retained 64. Align the experiment retained budget with its existing 512 sampling cap so deduplicated native poses reach qualification; add no pose synthesis or relaxed process rule. (local)
- [sense] [feat] 新捕获证明补回两候选仍因夹指/桌面拒绝。继续在 GraspNet worker 增加有界观测区域推理（保留全云，加最多三个 PCA 投影半区间），以原始点子集重新推理而非平移抓取；采样同时覆盖空间/朝向/开口，保留原模型分数与坐标逆变换。旧 profile 默认关闭区域推理。 / Fresh capture shows both recovered poses still fail finger/table clearance. Add bounded observed-region inference in the GraspNet worker (full cloud plus at most three half-intervals along its PCA projection), recomputing from real point subsets without shifting grasps; sample position/orientation/width while preserving scores and inverse frame transforms. Existing profiles default to no regional inference. (local)

### 文件变更详情 / File Changes

#### [修改 / Modified] `examples/forge-adapters/robotwin20/runtime/graspnet_worker.py` L26-L67、L78-L108、L206-L233、L285-L287
- [sense] [feat] 新增几何多样性采样与最多三个真实观测子区域推理；区域保持原点，输出保持原始模型位姿/分数/开口。默认 count=0，与原推理路径兼容。 / Add geometric-diversity sampling and at most three real observed subsets; preserve observed points and native poses/scores/apertures, with count=0 preserving the original path. (local)
```diff
-if policy != "orientation_diverse":
+if policy not in ("orientation_diverse", "geometry_diverse"):
     raise WorkerUnavailableError("unsupported GraspNet sampling policy")
+if policy == "geometry_diverse":
+    distances += np.mean((positions - positions[index]) ** 2, axis=1) + np.abs(widths - widths[index])

+def _input_regions(points, count):
+    # Full cloud plus bounded overlapping PCA projection intervals;
+    # subsets retain only existing points, not synthetic grasp positions.
+    regions = [points]
+    ...
+    regions.append(points[mask])
+    return regions

-sampled = _sample_points(points, max_points, seed=seed)
+sampled_regions = [_sample_points(region, max_points, seed=seed) for region in regions]
-for input_rotation in rotations:
+for sampled, input_rotation in ((sample, rotation) for sample in sampled_regions for rotation in rotations):
     # Existing inference and inverse mapping; one request-wide output budget.
```
- [sense] [feat] 单一完整点云 pivot 维持坐标逆变换，每区域在各旋转间共享采样；任一推理 pass 失败即拒绝整个请求，不发布局部成功。PCA 仅是采样方向，不冒充瓶轴或棒轴。 / A common full-cloud pivot preserves inverse transforms; rotations share each region's sampled points. Any pass failure rejects the request without partial success; PCA is a sampling direction, not a physical bottle/rod axis. (local)

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-perception.json` L31、L87-L90
- [env] [fix] 实验 profile 保留上限与已有 sample_count=512 对齐，启用区域推理和几何采样；旧部署默认行为不变，不放松 NMS、瓶口/支撑规则或机器人检查。 / Align experiment retention with its existing sample_count=512 and enable regional/geometric coverage without changing other defaults, NMS, process exclusions or robot checks. (local)
```diff
-"max_candidates": 64,
+"max_candidates": 512,
-"orientation_diverse",
+"geometry_diverse",
+"--input-region-count",
+"3",
```

#### [新增 / Added] `examples/forge-adapters/isaacsim_lab/scripts/inspect_grasp_sampling.py` L1-L71
- [eval] [feat] 独立模型环境回放历史请求，保存 native/worker 集合、配置、输入、命令、Git 版本及精确 worker 源码；输出目录禁止覆盖，失败显式保存，不生成准备/动作权限。 / Replay historical requests in the isolated model environment; save native/worker pools, config, inputs, command, Git revision and exact worker source in a unique directory, persisting explicit failure and never granting preparation/action authority. (local)
```diff
+original = worker._sample_candidates
+def capture(candidates, limit, policy):
+    native.extend(candidates)
+    return original(candidates, limit, policy)
+worker._sample_candidates = capture
+# Persist evidence_kind='historical_grasp_sampling_diagnostic',
+# motion_authorized=False, configuration, commit and worker_source.
```

#### [新增/修改 / Added/Modified] 回归测试 / Regression Tests
- [eval] [chore] 新增 `examples/forge-adapters/isaacsim_lab/tests/test_grasp_coverage.py:L1-L127`：真实部署组合下 70 个替代候选先复现 64 截断，再验证原值保留、同捕获 opaque 身份、Provider 失败零发布及诊断元数据。 / Production-composition tests first reproduce 64-of-70 truncation, then verify unchanged candidates, capture-scoped opaque identity, no publication on Provider failure and diagnostic metadata. (local)
- [eval] [chore] 修改 `examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py:L162-L198,L311-L345`：六个区域/多样性测试先失败再修复，补每 pass 逆变换、输出预算、默认兼容、后续区域失败不返回局部成功。 / Six region/diversity tests fail before implementation; add every-pass inverse transforms, total output budget, compatible defaults and no partial success after regional failure. (local)
```diff
+assert selected == [candidates[0], different_region]
+assert regions[0] is points and len(regions) == 4
+assert len(seen) == 8
+np.testing.assert_allclose(matrix[:3, 3], expected, atol=2e-7)
+with pytest.raises(module.WorkerUnavailableError, match="inference failed"):
+    module._handle(request)
```

### 架构与验证 / Architecture and Validation
- [policy] [docs] 通用层继续拥有任务语义、opaque 选择、取消/恢复/结算；Provider 拥有模型覆盖与工艺资格，Isaac 拥有真实几何/坐标/IK/完整路径。无公共契约、AgentLoop 分支或第二生命周期；替代 Provider 测试通过。 / Generic owners retain semantics, opaque selection and lifecycle; Providers own coverage/qualification, Isaac owns geometry/transforms/IK/full routes. No public-contract expansion, AgentLoop branch or shadow lifecycle; substitution tests pass. (local)
- [eval] [chore] 受影响回归 463 passed（12.46s），Ruff/compileall/`git diff --check` 通过；实际动作证据与契约/模型证据分别记录。 / 463 affected tests pass (12.46s), as do Ruff/compileall/whitespace checks; distinguish motion proof from contract/model evidence. (local)
- [eval] [exp] 历史 replay r2 为 1057 个阈值后原始候选，512 worker 中两个候选通过工艺/开口及手掌桌面必要条件，64 截断后为零；完整 NMS 保留 389。区域 replay r3 为 9855 原始候选→512，仍不代表可执行。 / Historical replay r2 has 1057 thresholded native candidates, two qualifying worker hypotheses lost at retained=64 despite surviving NMS (389). Regional replay r3 yields 9855→512; neither diagnostic constitutes admission. (local)
- [eval] [exp] 仅 retention 修复的原生任务 `task_b32f6dea14194fe8` cancelled：21 超开口、144 最终手掌/桌面、16 最终夹指/桌面记录，无 IK/控制动作。区域 r1 因 destination semantic selection 歧义未建任务；保留记录后明确 BEAKER 标签重跑 r2。 / Retention-only native task cancels with 21 aperture failures, 144 final palm/table and 16 final finger/table records, no IK/controller action. Regional r1 fails destination semantic binding before task creation; preserve it and rerun r2 with explicit BEAKER label. (local)
- [eval] [docs] 该实验最多 16 个推理 pass、每次 12000 点、总输出 512；seed 不保证 GPU 位级复现。完整观测仍用于资格/碰撞，crop 不代表空闲空间；旧门禁、裕量与 qualified-only recovery 保留。 / Bound inference to 16 passes, 12000 points each and 512 outputs; seed does not ensure bitwise GPU determinism. Full observation remains authoritative for qualification/collision; crops are not free-space proof, and existing margins/qualified-only recovery remain. (local)
- [policy] [fix] [计划扩展] 区域 r2 已复现 task prompt 339858+8192 超 272000：PlanNode input_bindings 含完整候选数组并原样注入提示。仅在现有 prompt projection 将大数组投影为明确的非权威数量摘要，小语义值/参数保持，Coordinator 完整绑定、候选池与选择解析不改；同时覆盖 task/node/working-set 三处，增加通用非机器人和原值不变回归。 / [Plan extension] Regional r2 reproduces prompt overflow (339858+8192 >272000) because complete candidate arrays in PlanNode input_bindings are injected verbatim. Bound large arrays only in existing prompt projections with explicit non-authoritative summaries; keep small semantic parameters and exact Coordinator bindings/pools/resolution unchanged. Cover task/node/working-set views with generic non-robot and immutability regressions. (local)

#### [修改 / Modified] `PhyAgentOS/agent/prompt_context.py` L540-L559、L960、L1852；`PhyAgentOS/agent/planning_loop.py` L709-L714
- [policy] [fix] 大于现有 64-item 提示显示上限的绑定数组改为 count/非权威摘要，所有精确值保留 Coordinator；task/node/working-set 共用一份纯投影，不加机器人分支。 / Arrays beyond the existing 64-item display bound become count/non-authoritative summaries; Coordinator retains exact values. Task/node/working-set share one pure projection with no robot-specific branch. (local)
```diff
-"input_bindings": _safe_json(getattr(node, "input_bindings", {})),
+"input_bindings": input_binding_prompt_projection(getattr(node, "input_bindings", {})),
+# Large list projection only:
+{"type": "array", "count": len(value), "authority": "prompt_summary_only",
+ "source_of_truth": "Coordinator PlanNode input_bindings", ...}
+payload["input_bindings"] = input_binding_prompt_projection(context.input_bindings)
```
- [eval] [chore] `tests/test_prompt_context.py:L126-L154` 新增机器人/文档检索两类数据，先复现单个输入 1051154 字符，再断言三种提示视图小于 2000 字符、语义数值与完整记录不变。62 项 prompt 回归通过。 / Robot/document fixtures first reproduce a 1051154-character input, then assert all three prompt views stay below 2000 characters without changing semantic values or complete records; 62 prompt regressions pass. (local)
- [eval] [exp] 原生区域 r3 创建后提示 26594 token（node_facts 18150），不再溢出，已经进入 planning_execution；修改前 r2 为 339858 token。 / Native regional r3 enters planning_execution with 26594 prompt tokens (18150 node facts), compared with 339858 before the fix. (local)
- [eval] [chore] 扩展测试共 773 passed / 5 failed；五项均在未修改的 `test_planning_selection.py`，其 mock graph 缺少 nodes。将两个修改模块以 Git HEAD 源码加载后重跑该文件仍为同样 5 failed / 35 passed，确认非本次新增回归，未修改旧 fixture 或降低验证。 / Expanded tests report 773 passed / 5 failed; all five are unchanged planning-selection fixtures missing graph nodes. Reloading both touched modules from Git HEAD reproduces the same 5 failed / 35 passed, so old fixtures and validation were not weakened. (local)

#### [新增/修改 / Added/Modified] 诊断与规范文档 / Diagnosis and Guidance
- [docs] [docs] 新增 `.task/labutopia-grasp-coverage-repair-20261102.md:L1-L184` 与 `docs/forge/IMPLEMENTATION_REVIEW_V16_7_0.md:L1-L158`，保存实测、修复归属、替代/失败测试、最终状态、剩余无动作流程边界与复现命令。 / Add diagnosis and implementation review with measurements, ownership, substitution/failure tests, final state, remaining no-motion boundary and reproduction commands. (local)
- [docs] [docs] 修改 `.task/current.md:L3-L38`、`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md:L231-L252` 与 `docs/forge/AGENT_TOOL_INPUT_SELECTION_DESIGN.md:L160-L168`，分别记录当前任务结果、Provider 区域覆盖和非权威提示投影规则。 / Update task state, Provider regional coverage guidance and non-authoritative prompt projection rules at these exact ranges. (local)
```diff
+Full cloud plus at most three observed subsets; qualification still uses complete evidence.
+Prompt summaries do not replace Coordinator input bindings or grant execution authority.
+Seven R03 combinations qualify; full acquire/pour/return and R04/rod remain unvalidated.
```

### 最终原生结果 / Final Native Result
- [eval] [exp] `out/lab-fullchain-truth-20261102-region-no-motion-r3/`，task `task_a87e6bb320964db7`、revision `revision_acc11d27415a4747`、session `cli:lab-ff91b390d264`：R03/R04/棒分别保留 508/506/24 个候选，四个 R03 工艺/资格 Query/preparation 节点全部 completed。 / Fresh workspace/task/revision/session retains 508/506/24 proposals; all four R03 process/affordance Query/preparation nodes complete. (local)
- [eval] [exp] R03 108 个 probe 请求中 41 超开口、60 不可用、7 个独立合格组合。536 条变体记录为 472 最终手掌/桌面、8 最终夹指/桌面、12 自碰撞、9 后续路径碰撞、5 IK 失败、30 available。先前中途“20 通过”是变体记录，不是候选数。 / Of 108 R03 probes, 41 exceed aperture, 60 are unavailable and seven distinct combinations qualify. The 536 variant records comprise 472 palm/table, eight finger/table, 12 self-collision, nine later route collisions, five IK failures and 30 available; the earlier intermediate 20 successes were attempts, not candidates. (local)
- [policy] [exp] Agent 已选择 `grasp-affordance://8986e73849994e3db75ecaef78536dd7`，准备结果仅含同集合七个 qualified opaque 引用。任务最终 `awaiting_replan`，长期调度结果 blocked，首个 Action 节点出现 `node_turn_incomplete:pour_r03:node_selection_no_progress`，host exit 1。 / Agent selects that combination and preparation returns only seven same-set qualified opaque refs. Final task is awaiting_replan, long-horizon result blocked at the first Action node with the stated failure, host exit 1. (local)
- [eval] [docs] `simulated_motion_enabled=false`，四条 Query、零条 Action 记录。controller_outcomes 保存 blocked 调度回执，不是机械臂运动回执；早期 agent_response 早于后续长期执行，以最终持久化状态为准。不声明完整路径、R04/棒资格、抓取/倾倒/搅拌成功。 / Motion is disabled, with four Query and zero Action records. controller_outcomes holds a blocked orchestration receipt, not motion feedback; the early agent_response predates later progress, so final persisted state is authoritative. No complete-route, R04/rod or manipulation success is claimed. (local)

## v16.6.3 (2026-11-02 12:38) - codex

### 预期修改 / Planned Changes [完成局部修复；可用抓取候选仍缺失 / Local repair complete; usable grasp candidate still missing]
- [docs] [docs] 根据用户继续修复的指令，保存 v16.6.2 新捕获中的手掌球/桌面、较低夹指位置与 IK 阻塞诊断，不把碰撞球模型重叠描述成实测接触。 / Following the user's continuation request, save the fresh palm-sphere/table, lower-finger and IK blockers without describing model overlap as measured contact. (local)
- [env] [fix] 先用当前 cooked 刚体几何复核具体失败姿态，再在 Isaac Adapter 内修复已证明的碰撞表示或规划分支缺陷；保留同捕获、完整路径、原裕量和现有生命周期。 / First compare current cooked rigid-body geometry at failed poses, then repair evidenced collision-representation or planning-branch defects inside Isaac Adapter, preserving lineage, full routes, margins and lifecycle. (local)
- [eval] [chore] 增加实际缺陷复现、机制替代、失败与零动作测试，运行原生无动作验证；保存精确 Diff/行号，提交并推送当前分支。 / Add defect, substitution, failure and no-motion tests, run native validation, record exact diffs/ranges, and commit/push the current branch. (local)
- [env] [fix] 原生复核已发现手掌 cooked 凸体低于桌面 0.57–1.34 mm，不缩小碰撞球；新增最终夹爪位姿预检，在 pregrasp IK 前用真实手掌/夹指及完整开合扫掠拒绝终态阻塞，保留后续全部检查。 / Native measurement finds the cooked palm below tabletop by 0.57–1.34 mm; do not shrink spheres. Add final-gripper-pose preflight using actual palm/fingers and full opening sweep before pregrasp IK, retaining all subsequent checks. (local)
- [policy] [fix] 复现现有 probe error 字符串泄漏 USD 路径的问题；公共错误仅保留失败码/阶段/计数与 opaque 回执，精确路径和几何保留私有制品。 / Reproduce USD-path leakage through existing probe error text; public errors retain only failure codes/stages/counts and the opaque receipt, with exact paths/geometry in private artifacts. (local)
- [eval] [fix] 复核发现新回放传空 source 时路径前缀会匹配全部绝对路径；先补回归，再让空 source 表示不豁免任何物体。正式绑定的非空 source 行为不变。 / Review found that the new replay's empty source matched every absolute path; add a regression then make empty source exempt no object, retaining bound nonempty-source behavior. (local)

### 架构与实施结果 / Architecture and Implementation
- [env] [fix] 将真实 cooked 刚体提取复用于手掌和夹指；每个轴对称终态只做一次无动作预检，结果复用于不同接近距离。终态失败保留精确 TCP 与私有几何，不伪造关节解。 / Reuse cooked-body extraction for palm/fingers and preflight each axial final pose once across approach distances; retain exact TCP/private geometry without inventing joints. (local)
- [policy] [fix] AgentLoop、公共 Tool schema、候选身份与生命周期不变；公共 probe 错误仅汇总失败码/阶段/计数，USD 路径留在 opaque 引用对应的私有制品。 / AgentLoop, public Tool schemas, candidate identities and lifecycle remain unchanged; public probe errors summarize codes/phases/counts, with USD details behind opaque private receipts. (local)
- [env] [fix] 保留 3 mm 逐轴裕量、完整夹指开合扫掠、原碰撞球及后续全部 IK/连续性/自碰撞/环境与载荷/完整路径检查；不挪动候选、不放松瓶口排除区、不新增 hash 或共享 gate。 / Preserve 3 mm per-axis padding, full finger travel, existing spheres and every downstream IK/continuity/collision/full-route check; no shifted candidates, relaxed opening exclusions, hashes or shared gates. (local)

### 文件变更详情 / File Changes

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/finger_collision.py` L1-L52、L73-L110
- [env] [refactor] 提取 `cooked_body_boxes`，遍历当前组合刚体的实际 collider，保留所有 cooked 凸体组件与 analytic bounds；通用错误文字由 finger 改为 gripper。 / Extract current-body cooked collider traversal, retaining every convex component and analytic bounds; generalize private wording from finger to gripper. (local)
```diff
-# Mesh cooking/traversal lived only in IsaacPhaseMotion.finger_geometry.
+def cooked_body_boxes(stage, body, maximum_slice_m):
+    # Copy all cooked components, transform collider -> body, conservatively slice.
+    return boxes, evidence
```

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L719-L790、L1246-L1264、L1332-L1368
- [env] [fix] 夹指复用提取函数，新增 cached palm geometry 与 final-grasp preflight；空 source 不豁免任何外部物体。 / Reuse extraction for fingers and add cached palm geometry/final-grasp preflight; empty source exempts no external object. (local)
```diff
-# Probe began with pregrasp workspace / IK checks.
+try:
+    self.check_final_gripper_pose(variant_desired, source)
+except PhaseMotionError as exc:
+    final_error = exc
+# Each distance keeps this final-pose result, then all original checks if clear.
+if final_error is not None:
+    raise final_error
```
```diff
-return path.startswith(robot_path) or path == source_path or path.startswith(source_path + "/")
+return path.startswith(robot_path) or bool(source_path and (
+    path == source_path or path.startswith(source_path + "/")))
-"error": detail,
+"error": public_detail or "no grasp approach variant was configured",
```
- [docs] [docs] 第二段前两行是本次实现复核发现并修正的中间版本；公共错误 Diff 针对最终返回值，私有制品继续保存 detail。 / The first comparison in the second block records the intermediate review correction; the error comparison applies to the public return only, retaining private detail. (local)

#### [修改 / Modified] `examples/forge-adapters/isaacsim_lab/scripts/inspect_collision_receipt.py` L32-L43、L84-L106、L131-L158
- [eval] [feat] 回放支持被报告刚体的 cooked 几何与最低顶点；区分有 checked joints 和仅 final TCP 的证据，禁止伪造关节，全部为无动作诊断。 / Replay reported-body cooked geometry/lowest vertices and distinguish checked-joint from final-TCP-only evidence without inventing joints or commanding motion. (local)
```diff
+def checked_final_poses(receipt):
+    # Only final_grasp diagnostics without checked_joints.
+    ...
+model.check_final_gripper_pose(pose, "")
+"final_pose_samples": final_samples,
-"unreplayed_attempts": len(receipt.get("attempts", [])) - len(samples)
+"unreplayed_attempts": len(receipt.get("attempts", [])) - len(samples) - len(final_samples)
```

#### [修改 / Modified] 测试 / Tests
- [eval] [chore] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py:L681,L756-L798,L806-L817`：失败终态必须先于 IK、clear 不能跳过 approach、缺失几何必须 unavailable、公共 error 无 USD 路径。 / Assert blocked final poses precede IK, clear endpoints still require approach, missing geometry is unavailable and public errors omit USD paths. (local)
- [eval] [chore] `examples/forge-adapters/isaacsim_lab/tests/test_finger_collision.py:L153-L193`：手掌/夹指的替代 overlap 查询，验证 TCP→hand、原裕量、源物体/机器人豁免与邻物/空源拒绝。 / Substitute overlap queries for palm/fingers and verify TCP-to-hand, original padding, intended source/robot exemptions, neighbor/empty-source rejection. (local)
- [eval] [chore] `examples/forge-adapters/isaacsim_lab/tests/test_collision_receipt_inspector.py:L30-L39`：仅位姿回执不变造 checked joints。 / Pose-only receipts never invent checked joints. (local)
```diff
+model.solver.compute_inverse_kinematics = lambda *_a, **_k: pytest.fail("blocked endpoint must precede IK")
+assert "checked_joints" not in attempt["collision_diagnostic"]
+assert "/World/table/mesh" not in result["error"]
+assert "/World/table/mesh" in saved[0]["attempts"][0]["error"]
```

#### [新增/修改 / Added/Modified] 文档 / Documentation
- [docs] [docs] 新增 `.task/labutopia-palm-collision-repair-20261102.md:L1-L128`：保存历史/新捕获诊断、职责、修复、候选分布、下一步 Provider 覆盖改进路线。 / Add diagnosis, ownership, implementation, fresh candidate distribution and next Provider-coverage work. (local)
- [docs] [docs] 新增 `docs/forge/IMPLEMENTATION_REVIEW_V16_6_3.md:L1-L100`：发现处置、架构、分层证据与复现命令；修改 `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md:L215-L230`：终态预检和公共/私有证据边界；修改 `.task/current.md:L3-L21`：最新结果及未完成的抓取目标。 / Add findings/architecture/evidence/reproduction review, document final-pose and public/private evidence boundaries, and update task status including the unresolved grasp goal. (local)
```diff
+Before the Isaac short-approach probe searches pre-grasp IK, it checks each exact
+candidate final TCP pose against current cooked palm and full-travel finger
+geometry, with the same padding and intentional source-contact exemption as
+the grasp stage.
```

### 验证与剩余阻塞 / Validation and Remaining Blocker
- [eval] [chore] 受影响回归 450 passed（24.49s），Ruff/compileall/`git diff --check` 通过；缺少 preflight、公共路径泄漏、空 source 豁免均先复现失败后修复。 / 450 affected regressions pass (24.49s), with Ruff/compileall/whitespace checks passing; missing preflight, public path leakage and empty-source exemption were reproduced before fixes. (local)
- [eval] [exp] 新捕获 workspace `out/lab-fullchain-truth-20261102-final-gripper-no-motion-r1/`，task `task_4972b9d477f048d2`，revision `revision_d41e73623a814c98`，session `cli:lab-ca9ce2f70682`：R03 工艺查询/准备 available；task-affordance unavailable，任务 cancelled，host exit 1。 / Fresh workspace/task/revision/session has available R03 process queries/preparation but unavailable task-affordance; task cancelled, host exit 1. (local)
- [eval] [exp] 候选 4/16/44/57 超开口；10/17/23/27/52/55 各四种轴向终态均为手掌 padded cooked bounds/table 拒绝，24 次终态检查复用于两种接近距离，形成 48 条记录。旧 workspace/IK/自碰撞检查没有被证明已消失，也不代表所有可能抓取无解。 / Four candidates exceed aperture; six candidates each reject at four final orientations on padded cooked-palm/table overlap, giving 24 endpoint checks reused for two backoffs and 48 records. Earlier workspace/IK/self limitations are not disproven, and all possible grasps are not ruled out. (local)
- [eval] [exp] 原生仅位姿回放 `out/lab-final-gripper-geometry-20261102-r1/geometry.json` exit 0；8 条终态拒绝重现、无未回放记录、关节/物理时间未变、控制命令 0；初始 FK/USD 平移最大误差 2.01e-7 m。 / Native pose-only replay exits 0, reproduces eight endpoint rejections, leaves no unplayed attempts, changes neither joints nor physics time and issues zero commands; initial FK/USD position error is at most 2.01e-7 m. (local)
- [eval] [chore] `simulated_motion_enabled=false`、`controller_outcomes=[]`；无抓取、R04 倾倒或搅拌执行证据。Kit 材质/GPU particle 错误保留，未验证液体/粒子动力学。 / Motion remains disabled with empty controller outcomes and no grasp/R04 pour/stir execution evidence; Kit material/GPU particle errors remain, and liquid/particle dynamics are unvalidated. (local)
- [docs] [docs] 后续应在 Grasp/Task-Affordance Provider 改善真实几何下的可抓区域覆盖与工艺净空，生成新的合格 opaque 候选；不得在 Action recovery 内平移候选或恢复被排除的 raw 集合。 / Next improve geometry-grounded grasp-region coverage/process clearance in Providers and generate newly qualified opaque candidates, never shifting poses or restoring rejected raw candidates inside Action recovery. (local)

### Git 提交 / Git Commit
- Implementation commit: `5f83c2a3`.
- Branch: `feature/planning-loop`; time: `2026-11-02 12:53:47 +0800`.
- [docs] [docs] 月度完整记录 `changelog/2026-11.md:L780-L872`；索引对应 `CHANGELOG.md:L51-L143`，最近五版本与归档逐字一致。 / The complete archive/index entry occupies these ranges; latest five entries match their archive exactly. (local)
- [chore] [chore] 仅暂存本任务 12 个文件，无关报告与运行输出保留未暂存；提交回执随后以文档提交保存并推送当前分支。 / Stage only twelve task-owned files, preserving unrelated report/runtime outputs; save this receipt in a following docs commit and push the current branch. (local)

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
