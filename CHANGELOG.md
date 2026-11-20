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

## v17.8.3 (2026-11-20 16:08) - codex

### 机座位置与高度调整 / Base Placement and Height Adjustment [完成；fresh运行失败 / Completed; fresh runtime failed]
- [env] [tune] 将 Ridgebase 底盘 `y` 从 `0.18m` 调整到 `0.10m`，保持 `x=-1.12m` 与桌面布局不变；将臂基由约 `0.72m` 增高到约 `0.82m`，安装柱由 `0.43m` 增至 `0.53m`。依据离线端点敏感性扫描选择该单一候选；扫描不等同完整路线资格或实测倾倒成功。 / Move the Ridgebase chassis `y` from `0.18m` to `0.10m` while retaining `x=-1.12m` and the tabletop layout; raise the arm root from about `0.72m` to `0.82m` by increasing the mount column from `0.43m` to `0.53m`. Select this single candidate from the offline endpoint sensitivity scan; the scan is not complete route qualification or runtime pour success. (local)
- [eval] [exp] 修改后针对性回归206项通过；fresh无动作初始化与home碰撞检查通过，抓取成功，但完整持瓶倾倒路线资格失败，实际倾倒未执行。保留失败证据和决策边界，不修改运动阈值、目标物品或公共契约。 / Focused regression passes206 tests; fresh no-motion initialization and home collision check pass, acquisition succeeds, but complete held-pour route qualification fails and pouring does not execute. Preserve failure evidence and decision boundaries without changing motion thresholds, task objects or public contracts. (local)

### 实际影响文件 / Actual Files
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-station.yaml`：修改底盘 `base_position.y`。
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-elevated.usda`：同步12个臂/末端刚体的 `z`、安装关节高度和碰撞柱尺寸。
- `examples/forge-adapters/isaacsim_lab/tests/test_ridgebase_elevated.py`：更新部署高度、碰撞柱边界和底盘坐标断言。
- `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md`：记录当前候选的fresh读回、路线资格拒绝分类、视频元数据和执行边界；本轮未修改 placement 报告。

### 本轮决策 / Current Decision
- fresh初始化、home碰撞检查和抓取通过；60/60条持瓶倾倒候选均被拒绝，故保留该部署为“初态与抓取通过、完整倾倒路线资格失败”的实验候选。
- 停止继续调整底盘位置、机座高度或现有运动阈值；若后续继续，先依据候选级transport/process拒绝详情定位路线问题，再提出新的部署决策，不把本轮证据描述为倾倒成功。

### 文件变更详情 / File Changes
- [env] [tune] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-station.yaml` L12：底盘 `base_position.y` 从0.18改为0.10，x/z不变。 / Change the chassis `base_position.y` from0.18 to0.10, retaining x/z. (local)
```diff
-  base_position: [-1.12, 0.18, 0.01]
+  base_position: [-1.12, 0.10, 0.01]
```
- [env] [tune] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-elevated.usda` L3,L13-L94：12个臂/手/手指/末端刚体z增量由0.43m改为0.53m，安装关节/柱尺寸/COM/惯量同步更新，保留米制、Z-up、原外部资产引用和碰撞API。 / Raise the12 arm/hand/finger/end-effector bodies by0.53m and update the mounting joint, column size, COM and inertia while retaining meters/Z-up, the external asset reference and collision API. (local)
```diff
-  "Adapter deployment: 0.43m arm elevation, grounded chassis, collision-enabled mount column."
+  "Adapter deployment: 0.53m arm elevation, grounded chassis, collision-enabled mount column."
-  point3f physics:centerOfMass = (0.3, 0, 0.215)
-  point3f physics:diagonalInertia = (0.09965, 0.09965, 0.0144)
+  point3f physics:centerOfMass = (0.3, 0, 0.265)
+  float3 physics:diagonalInertia = (0.14765, 0.14765, 0.0144)
-  point3f physics:localPos0 = (0.3, 0, 0.43)
+  point3f physics:localPos0 = (0.3, 0, 0.53)
-  float3 xformOp:scale = (0.12, 0.12, 0.43)
+  float3 xformOp:scale = (0.12, 0.12, 0.53)
```
- [eval] [chore] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_ridgebase_elevated.py` L36,L62,L65-L66,L72：同步验证0.53m刚体位移、柱z上界0.81、COM/inertia及底盘y=0.10；motion阈值和mount collision contract保持不变。 / Update assertions for0.53m body displacement,0.81 column bound, COM/inertia and chassis y=0.10 while retaining motion thresholds and the mount-collision contract. (local)
```diff
- expected[3, 2] = .43
+ expected[3, 2] = .53
- assert station["robot"]["base_position"] == [-1.12, .18, .01]
+ assert station["robot"]["base_position"] == [-1.12, .10, .01]
```
- [docs] [docs] [修改 / Modified] `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` L1-L158：区分历史C的0.43m失败证据与v17.8.3当前候选，补充fresh无动作实测坐标、home检查、60条路线拒绝分类、视频元数据及未执行pour/place边界。 / Distinguish historical C0.43m failure evidence from the v17.8.3 candidate, and document fresh no-motion coordinates, home check, all60 route-rejection categories, video metadata and the no-pour/no-place boundary. (local)

### 验证 / Validation
- [eval] [chore] 执行原回归命令：**206 passed**，5.60s，保留1项既有 `asyncio_mode` 配置警告。 / The focused production regression command passes **206 tests** in5.60s with one pre-existing `asyncio_mode` configuration warning. (local)
- [eval] [exp] fresh证据：`no-motion.json`中实测底盘`[-1.1200000048,0.1000000015,0.0099999998]m`、臂基`[-0.8199764490,0.1000000164,0.8199999928]m`，home collision passed且motion_commands=0；完整运行任务`task_1ec4c496cb464524`失败，60条候选首拒绝为transport无解25、transport连续性/关节跳变15、process碰撞20。 / Fresh evidence: `no-motion.json` measures the chassis at `[-1.1200000048,0.1000000015,0.0099999998]m` and arm root at `[-0.8199764490,0.1000000164,0.8199999928]m`, with home collision passed and zero motion commands; task `task_1ec4c496cb464524` fails, with first rejection counts of25 transport no-solution,15 transport continuity/joint-delta, and20 process collisions. (local)

### Fresh结果 / Fresh Outcome [完成 / Completed]
- [docs] [docs] 报告记录fresh home碰撞检查通过、抓取成功、60条held倾倒候选全部拒绝及分类、任务failed且未进入pour/place；视频仅作为抓取/持瓶证据，不作为倾倒成功证据。 / The report records the passed fresh home collision check, successful acquisition, all60 held-pour candidates rejected by category, task failure before pour/place, and the video as acquisition/holding evidence only, not pour-success evidence. (local)
- [docs] [docs] 月档与索引均记录报告L1-L158、配置/测试精确行号、关键Diff和本轮停止调参决策；CHANGELOG最近五版本已同步。本次不修改运行产物，不暂存`.task/`或`out/`。 / The archive and index record report linesL1-L158, exact configuration/test lines, key diffs and the current stop-tuning decision; the latest-five index is synchronized. Run artifacts are unchanged and `.task/`/`out/` are not staged. (local)

### Git回执更新 / Git Receipt Update [完成 / Completed]
- [docs] [chore] 报告L152/L154已将实现回执链接由历史v17.8.0改为当前v17.8.3；本条同时记录当前commit、分支、时间和待执行push状态。 / Report linesL152/L154 now link the implementation receipt to current v17.8.3 instead of historical v17.8.0; this entry records the current commit, branch, time and pending push status. (local)

### Git提交 / Git Commit
- Implementation commit / 实现提交：`82786e453bd43d37e5583f40e5491cfb2e1a81ca`。
- Branch / 分支：`feature/planning-loop`。
- 时间 / Time：2026-11-20 21:11:26 Asia/Shanghai (UTC+8)。
- [chore] [chore] 主实现提交已完成；push尚未执行，当前不记录成功或失败结果。 / The primary implementation commit is complete; push has not run and no success or failure is asserted yet. (82786e45)

## v17.8.2 (2026-11-20 15:31) - codex

### 推送历史修复 / Push History Repair [完成 / Completed]
- [chore] [fix] 待推送历史中的run10提交由`67e77c0b`重写为`14c8418b`，仅移除一个105,648,775字节视频对象；36个待推送提交仍以远端`09b9d32c`为基点。 / Rewrite the run10 commit from `67e77c0b` to `14c8418b`, removing only one105,648,775-byte video blob; all36 pending commits remain based on remote `09b9d32c`. (local)
- [chore] [docs] [修改 / Modified] `out/labutopia-oracle-run10/artifacts/labutopia/phase-video/162a9404e9ca4ec19f3eaadb6e18e152.mp4` 从待推送Git树移除，原视频继续保留在本地路径；此二进制文件无文本行号。 / Remove the video from pending Git trees while retaining the local file at its original path; this binary has no text line numbers. (local)

**历史Diff / History diff**
```diff
- out/labutopia-oracle-run10/artifacts/labutopia/phase-video/162a9404e9ca4ec19f3eaadb6e18e152.mp4 (Bin 105648775 bytes)
+ [not present in rewritten commit tree; local file retained]
```

**验证 / Validation**：重写前待推送范围为36个提交，merge-base未变，范围内无≥100,000,000字节对象；本地视频存在且不在HEAD树中。历史操作未运行测试，沿用原实现的206 passed结果；历史修复推送与日志回执推送均已成功。 / Before rewriting, the pending range contained36 commits with the same merge-base and no object ≥100,000,000 bytes; the local video remains present and is absent from the HEAD tree. No tests were run for this history-only change; the original implementation's206-passed result remains applicable, and both the history-repair push and log-receipt push succeeded.

### Git提交 / Git Commit
- Rewritten commit / 重写提交：`14c8418bc162f8ef8c445fbcdfda8d8609566f02`（替代`67e77c0b461af6141bc8ab7e5771d577ad8e6171`）。
- Branch / 分支：`feature/planning-loop`。
- Push / 推送：成功，`09b9d32c` → `ca1fee82`（`git ls-remote`已核验）。
- [chore] [chore] 2026-11-20 15:45:25 Asia/Shanghai 使用`git push --force-with-lease origin feature/planning-loop`成功，远端从`09b9d32c`更新至`ca1fee82`；`git ls-remote`确认远端指针为`ca1fee82575b8ae9eaccf860db6f5bafccf95001`。GitHub仅提示run9、run12、run13、run14视频超过50 MB建议值，未拒绝推送。 / At 2026-11-20 15:45:25 Asia/Shanghai, `git push --force-with-lease origin feature/planning-loop` succeeded, moving the remote from `09b9d32c` to `ca1fee82`; `git ls-remote` confirmed the remote ref at `ca1fee82575b8ae9eaccf860db6f5bafccf95001`. GitHub only warned that run9, run12, run13 and run14 videos exceed its 50 MB recommendation; the push was accepted. (ca1fee82)
- [chore] [chore] 日志回执提交`2389016288c0b981475dd155e6f37b7a0032aaa4`已通过`git push origin feature/planning-loop`成功推送；随后文案校正提交继续推送到同一分支，当前远端与本地分支同步。 / Log-receipt commit`2389016288c0b981475dd155e6f37b7a0032aaa4` was pushed successfully with`git push origin feature/planning-loop`; a subsequent wording-correction commit was then pushed to the same branch, which is synchronized with the local branch. (23890162)

## v17.8.1 (2026-11-19 20:54) - codex

### 初始诊断计划 / Initial Diagnostic Plan [已完成]
- [env] [fix] 仅研究Isaac Adapter倾倒几何与必要回归测试，保留公共Tool/AgentLoop接口、Runtime生命周期及全部碰撞/对准/接触阈值；机器人部署和桌面物品初始位置不改。 / Investigate only Isaac Adapter pour geometry and necessary regressions, preserving public Tool/AgentLoop contracts, Runtime lifecycle and every collision/alignment/contact threshold; retain robot deployment and initial tabletop positions. (local)
- [eval] [exp] 先新增`out/labutopia-pour-clearance-20261119/replay-clearance.py`，用生产Backend/WorkerSession fresh初始化、历史C末态及目标/点云做无动作完整路线诊断；先复现5条手/载荷碰杯候选，再测现有.048m对准预算内少量横移端点，不发apply/set命令、不扫高度。 / First add a production-backed fresh-initialization diagnostic using historical C end state and features/clouds; replay five hand/payload-beaker candidates and test a small set of lateral offsets inside the existing.048m alignment budget with full-route qualification, no apply/set commands or height scan. (local)
- [eval] [docs] 历史C仅为诊断输入，不代表新revision执行授权；fresh障碍与历史末态不同（烧杯约1mm差），查询结果只作机制诊断，不宣称新执行合格。生产改法由主会话根据证据裁决，初始诊断阶段不修改生产源码或提交；后续生产修改见下方主会话批准计划。 / Historical C is diagnostic input, not execution authority for a fresh revision; fresh obstacles differ from historical end state by about1mm at the beaker. Results diagnose mechanisms without granting execution qualification; the primary selects any later production change from evidence, without source edits or commits during the initial diagnostic stage; see the subsequently approved implementation below. (local)

### 生产修复实施计划 / Production Implementation Plan [实现完成；fresh D失败]
- [env] [fix] 经主会话批准，在`phase_motion.py`保留居中候选搜索/排序，全部拒绝后才尝试现有三维对准预算内三方向横移；每条调用完整qualify，首条fallback通过即停止，失败保留逐候选偏移与原始detail。倾倒最后upright exit返回首upright ingress，保留tilted上抬到原high点（横移候选在此回收横向偏移）；route持久化world横移向量和退路策略。 / Following primary approval, preserve centered search/ranking and only then try three lateral directions inside the existing three-dimensional alignment budget, qualifying every full route and stopping at the first passing fallback. Retain candidate offsets/details, return the final upright exit to the first upright ingress after rising tilted to the original high point (recovering lateral offset for shifted candidates), and persist world offset/retreat strategy. (local)
- [eval] [chore] 扩充`tests/test_phase_motion.py`验证真实waypoint、预算/只移process、target不变、center优先/fallback搜索与exit失败拒绝，重跑原194项命令；新增双语报告记录26条混合历史诊断及唯一成功对照，fresh正式结果pending。 / Extend real waypoint, budget/process-only translation, unchanged-target, centered-first/fallback and exit-rejection regressions; rerun the original194-test command and add a bilingual report describing the26 mixed-history diagnostics and sole passing comparison, with fresh formal outcome pending. (local)
- [docs] [docs] 通用层保持任务语义和公共契约；横移/退路由Isaac Adapter拥有，替换Provider不改AgentLoop。WorkerSession拥有scene revision，Runtime拥有取消/结算/恢复；只有fresh revision准备及runtime反馈能证明动作，历史混合诊断无执行授权效力。 / Generic task semantics/contracts stay unchanged; Isaac Adapter owns lateral/retreat mechanisms and Provider replacement leaves AgentLoop unchanged. WorkerSession owns scene revisions and Runtime owns cancellation/settlement/recovery; only fresh-revision preparation plus runtime feedback proves motion, and mixed historical diagnostics grant no execution authority. (local)

### 文件变更详情 / File Changes [实现完成]
- [env] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L752：pour最终upright exit返回首upright ingress位置及orientation，保留tilted上抬到原high点（横移候选在此回收横向偏移）。 / Return final upright pour exit to the first upright ingress pose while retaining the tilted rise to the original high point (recovering lateral offset for shifted candidates). (local)
```diff
- feature(high + other * config["process_clearance_m"], orientation, stage="exit")
+ feature(high + approach_direction * config["process_clearance_m"], orientation, stage="exit")
```
- [env] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L1646-L1705：保留居中候选顺序及排序，仅全失败后在现有三维预算内搜索3方向横移，逐条完整qualify，首条通过停止；route持久化world offset/退路，失败detail保留所有候选及offset。公共配置/契约、目标frame与安全阈值不改。 / Preserve centered order/ranking, add three budgeted lateral directions only after total centered failure, qualify complete routes and stop on first passing fallback; persist offset/retreat and retain detailed rejected candidates without changing public contracts/configuration, target frames or safety thresholds. (local)
```diff
- # centered clearance/yaw/azimuth qualification only
+ def qualify_pour(points, clearance, yaw, azimuth, offset):
+     candidate = self.qualify(points, source, tcp_from_object, operation, np.asarray(original_return))
+     candidate.update(pour_lip_offset_m=offset.tolist(),
+                      pour_retreat_strategy="same_side_ingress")
+ # all centered candidates retain their existing selection ranking
+ if not candidates:
+     radius_squared = clearance_limit ** 2 - clearance ** 2
+     # skip nonpositive budget or degenerate projected bottle origin
+     for direction in (bottle_side, tangent, -tangent):
+         offset = direction * math.sqrt(radius_squared)
+         # copy waypoint matrices; translate process TCP only
+         # qualify transport/process/exit; stop at first passing fallback
+ # all failures retain clearance/yaw/azimuth/offset and original detail
```
- [eval] [chore] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L270-L441：8项回归；真实waypoint与Cartesian测试臂上的生产prepare/qualify检验同侧退出、三维预算、只移process、center优先/旧排序、fallback停止，以及exit碰撞与IK连续性分别拒绝60候选。另覆盖无预算/退化投影跳过。 / Eight regressions exercise real waypoints and production prepare/qualify with a reversible Cartesian test arm, centered preference/ranking, bounded process-only offsets, first-passing fallback and60 complete-route exit rejections per collision/IK case, plus degenerate skips. These tests establish contract/algorithm behavior, not real-arm motion. (local)
```diff
+ test_pour_upright_exit_retraces_ingress_after_vertical_tilted_lift
+ test_pour_centered_candidates_keep_priority_and_existing_ranking
+ test_pour_lateral_fallback_stays_inside_3d_budget_and_only_translates_process
+ test_pour_every_candidate_still_rejects_exit_failure_and_keeps_offsets
+ test_pour_skips_lateral_when_projection_or_budget_is_zero
```
- [eval] [exp] [新增 / Added] `out/labutopia-pour-clearance-20261119/replay-clearance.py` L1-L179：生产Backend/WorkerSession初始化后只读历史C held状态及同revision1特征；完整路线诊断，不发apply/set命令。首次artifact root层级错误在bind读取点云时终止，修正为新reset输出目录+历史`artifacts/labutopia`只读点云后成功运行。 / Production-backed no-motion historical held-state and same-revision feature diagnostic; initial artifact-root error stops before qualification, then corrected fresh-output/history-cloud separation succeeds. (local)
```diff
+ source_lip = _task_conditioned_pour_feature(source_rim_rev1, destination_rim_rev1)
+ tip_offset = inverse(final_observed_object_pose) @ source_lip_world
+ model.qualify(full_waypoints, ...)  # no manipulation commands
+ # save every outcome, collision/IK detail, unchanged joints and simulation time
```
- [docs] [docs] [新增 / Added] `docs/forge/LABUTOPIA_POUR_CLEARANCE_20261119.md` L1-L52：双语机制、26诊断对照及局限、Adapter/Runtime所有权、完整测试命令与D pending状态。 / Bilingual mechanism, diagnostic comparisons/limitations, ownership, reproducible test command and pending fresh-D outcome. (local)

### 验证与证据 / Validation and Evidence
- [eval] [chore] 原194项命令：`PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py examples/forge-adapters/isaacsim_lab/tests/test_ridgebase_elevated.py -q` → **202 passed**（原194+新增8），5.22s，既有asyncio_mode警告1项。 / The original command passes202 tests, comprising194 existing and eight new regressions, with one existing warning. (local)
- [eval] [chore] 首轮200 passed/2 failed：新增skip测试错误把failure code匹配到message，修正为检查`exc.code`后重跑202全过；不把首轮记作整体通过。 / Initial200-pass/two-failure run exposes a new-test assertion error; checking the explicit error-code field yields the fully passing rerun. (local)
- [eval] [chore] `git diff --check`及诊断脚本py_compile通过；Ruff只保留3个旧问题：phase_motion.py L1015 I001、test_phase_motion.py L2810/L2896 E731（由旧L2637/L2723顺移），不声称整体lint通过。 / Diff/compile checks pass; whole-file lint retains the three pre-existing findings and is not claimed passing. (local)
- [eval] [exp] 历史held+fresh障碍完整诊断26条：1通过、25拒绝（payload4/route11/numericalIK6/continuity4），162.5s，实际reset关节与仿真时间全部不变；world offset[-.00467108245,+.02611859469,0]m、clearance.04/yaw0/az+π/2、lip/rim距离.048m，同侧退出完整127步通过（71transport/15process/41exit）。同横移原exit失败delta.624982>.5rad；无横移.04候选process payload/beaker碰撞。 / The stated26-route diagnostic has a single127-step pass with the measured offset and unchanged live reset state; original retreat rejects continuity and the unshifted control collides. Evidence: `out/labutopia-pour-clearance-20261119/replay-clearance.json`. (local)
- [eval] [docs] 历史held与fresh障碍约1mm烧杯差异使最近.048控制候选从旧C exit失败变为新process碰撞；两个.04控制TCP约1e-10m重现。诊断不是revision一致准备，不授予fresh执行资格、不证明机器人实际倾倒；只能支持机制选择。 / The approximately1mm obstacle difference changes the closest.048 control's failure phase despite near-exact.04 control TCP reproduction; mixed-history diagnostics support mechanism choice without proving fresh preparation or actual pouring. (local)
- [env] [chore] 主会话review当前实现无Blocker/Major后启动D，`out/labutopia-pour-clearance-20261119/D-fresh`；主会话owns仿真，生产源码保持不再修改。station相对C仅workspace变化、motion逐字节相同、USD仅旧EOF空行差异（rstrip相同）；部署/初始桌面布局未改。 / Primary review finds no Blocker/Major and launches fresh D; source remains fixed during the run. Station, motion and USD comparisons establish retained deployment/initial layout with only workspace and EOF formatting differences. (local)

### Fresh正式结果 / Formal Fresh Outcome [failed]
- [eval] [exp] D目录`out/labutopia-pour-clearance-20261119/D-fresh`，task`task_60462336366b41f8`已failed，2026-11-19T21:12:24.641851+08:00至21:32:46.593420+08:00，returncode1。28/28probe available，acquire succeeded2139样本/113lift，lift attach峰9.314366924mm；末样grasp_valid=false/contact_load_valid=true。 / D records the stated failed terminal task, timestamps and return code after available probes and successful acquisition; retain exact sample counts, attachment peak and final mixed validity. Evidence: `D-fresh/placement-summary.json`. (local)
- [eval] [exp] fresh ready`5e739d478ae84170bae9ba88ccf8b99a.json`在revision`labutopia-tabletop-rod-rack-v1:a6f7f35ca07c4a2ca05755a06c73c99c:1`选中居中`.048/yaw0/az+π/2`、offset[0,0,0]、same_side_ingress，125步（71transport/14process/40exit）完整资格通过；不能把混合诊断唯一横移候选写成本次selected。 / Fresh readiness admits the centered zero-offset125-step same-side route, distinct from the mixed diagnostic's sole lateral pass. (local)
- [eval] [exp] pour反馈`73990b0b189f4330a31a143903605cde.json`终态failed，1651样本均transport，`inverse_kinematics_failed: measured pour-pose correction is unreachable`；process0、qualified tilt hold0s、最大tilt.5951736459333297rad，未place。contact load/manifold均1651有效，grasp_valid229；末attach位置10.352944586mm/旋转.3821746528rad。 / Pour fails during transport before process/hold/placement with the stated correction-IK failure and attachment evidence; preparation success is not motion completion. (local)
- [eval] [exp] pour视频`phase-video/487f1976e3e94be5bfb786cf47b6b022.mp4`经主会话ffprobe为27.5s/1650帧/3840×960；反馈1651含额外终态重复record，不等同1651动作帧。 / The primary verifies the stated complete video metadata and extra terminal feedback record. No pour or transfer success is asserted. (local)

### Git 提交 / Git Commit [pending]
- [chore] [chore] 本子任务按主会话要求不提交；实现和文档待主会话fresh验收后提交/推送，当前无本版本commit hash。 / Per primary instruction, this coding subtask does not commit; the primary owns post-fresh acceptance, commit and push, and no current-version commit hash is asserted. (local)

- [docs] [fix] [完成] 按主review仅修正本v17.8.1月档/索引/报告中的退出几何措辞：横移候选从process回原high时同时回收横移，不写严格竖直上抬；源码/测试不改，formal pending保留。 / Correct only the current-version archive/index/report retreat wording: a lateral candidate recovers its lateral offset while rising from process to the original high point, rather than following a strictly vertical segment; preserve source/tests and pending formal status. (local)
- [docs] [fix] [修改 / Modified] 本月档L225/L230与对应CHANGELOG条目、`docs/forge/LABUTOPIA_POUR_CLEARANCE_20261119.md` L30：`tilted竖直上抬 / tilted vertical lift` → `tilted上抬到原high点（横移候选在此回收横向偏移） / tilted rise to the original high point, recovering lateral offset for shifted candidates`。仅措辞修正，源码/测试保持不变，fresh结果仍pending；文档UTF-8、索引同步及diff检查完成，不重跑代码测试。 / Correct geometry wording only at the stated lines; retain source/tests and pending fresh status. UTF-8, archive/index consistency and whitespace checks pass; no code-test rerun is needed. (local)

### D失败后无运动诊断计划 / Post-D No-Motion Diagnostic Plan [完成]
- [eval] [exp] D真实终态failed：居中零横移same-side路线125步fresh资格通过，但pour在transport因measured pour-pose correction IK失败停止，process/hold均未进入，不称倾倒成功。新增`out/labutopia-pour-clearance-20261119/diagnose-pour-correction.py`，生产Backend fresh只读初始化，按真实FK/limits及D ready/反馈重建point边界，比较原完整姿态IK与tip+axis IK，记录误差、delta、limits及重建精度；不发apply/set，不改生产/阈值，不新增完整仿真，改法由主会话裁决。 / D fails during transport after a125-step centered zero-offset same-side route passes fresh qualification; no process/hold or pour success is claimed. Add a production-backed no-motion diagnostic to reconstruct point boundaries from D readiness/feedback and real FK/limits, compare full-pose and tip/axis IK, and record residuals, deltas, limits and reconstruction accuracy. Issue no apply/set, change no production code or thresholds, and leave production decisions to the primary. (local)

- [docs] [docs] [完成] 根据D实际失败终态更新报告/月档/index，明确实际selected为居中零横移125步同侧退路、运行期transport correction IK失败而非process倾倒完成；保留回归与混合诊断证据边界。 / Update the report/archive/index with D's actual failed outcome, centered zero-offset readiness selection and transport correction-IK rejection, preserving the boundary between regressions, mixed diagnostics and runtime evidence. (local)

### D correction诊断结果 / D Correction Diagnostic Results
- [eval] [exp] [新增 / Added] `out/labutopia-pour-clearance-20261119/diagnose-pour-correction.py` L1-L199：生产Backend fresh FK/limits、D readyness/反馈只读输入，逐point原full correction与smooth长度重建；对失败点±2名义目标固定失败边界relation，比较当前/名义/上一名义seed的full local、primary Lula及tip+axis。不发apply/set、不做碰撞授权、不改生产或阈值。 / Add a production-backed no-motion saved-boundary reconstruction and bounded solver comparison, preserving full-pose semantics and unchanged production/thresholds without collision or execution admission. (local)
```diff
+ relation = inverse(FK(saved_boundary_q)) @ saved_observed_body
+ target_body = FK(nominal_point_q) @ route_tcp_from_object
+ full_target_tcp = target_body @ inverse(relation)
+ full_goal = local_inverse_kinematics(FK, full_target_tcp, current_q, limits, tolerance)
+ # segment frames consume saved samples; terminal duplicate excluded
+ # compare full local three seeds, primary Lula current, tip/axis diagnostic
```
- [eval] [exp] `diagnose-pour-correction.json`记录point index61（第62点transport）原full local首次拒绝；前61点1650 smooth命令帧恰好对应1650非重复sample，末额外record1，unused0；initial relation差0、所有边界saved TCP/FK位置误差0，故为exact_saved_boundary_accounting（保存边界匹配，不是物理重放）。fresh reset关节与simulation time不变，motion_commands0。 / Exact saved-boundary accounting locates rejection at zero-based point61 after all1650 commanded samples, distinguishing the extra terminal record and preserving unchanged reset state with zero commands. (local)
- [eval] [exp] 失败点current full local位置.795374mm但旋转.0238165rad超.02而invalid；名义seed full valid（位置5.04e-10m/旋转1.41e-8rad/current delta.110876rad），上一名义seed full valid（1.57e-12m/4.23e-11rad/delta.0846107），primary Lula current valid（.0982303mm/.000962118rad/delta.0803714）。均limits内、delta低于原.5；三个有效full解最小限位余量.741763/.736337/.723502rad。 / The current local seed rejects rotation while alternate planned seeds and primary Lula preserve full-pose tolerance, continuity and limits, with the stated measured residuals and margins. (local)
- [eval] [docs] tip+axis当前seed虽valid且tip残差2.47e-12m，但完整旋转.0408325rad超原.02；不能放松full语义。结果优先支持local数值分支失败，不证明full目标不可达；替代解未做完整collision路线，不能视为动作资格。失败点±2仅同失败边界relation目标对比，不杜撰未来状态。 / Tip/axis success exceeds the original full-rotation tolerance and cannot relax full-pose semantics. Results support a numerical-branch issue, not proven unreachability; alternatives lack complete collision qualification and neighboring comparisons share the failure-boundary relation. (local)
- [eval] [chore] 新诊断exit0、58.42s，py_compile通过；本阶段只新增诊断与文档，原production202项证据保留不重跑。报告新增诊断表与full语义裁决，月档/index同步，UTF-8及diff检查按本次修改执行。 / The diagnostic exits0 in58.42s and compiles; production tests remain the prior202-pass evidence, with no source changes requiring a rerun. Add the bounded diagnostic comparison to the report and synchronize/archive-check documentation. (local)

### D诊断后的生产修复计划 / Production Plan Following D Diagnosis [实现完成；follow-up待验证]
- [env] [fix] 经主会话裁决，仅当pour当前seed full-pose local IK无效时，使用当前point原planned joints对完全相同target TCP重试同一local solver；fallback有效且相对start最大joint delta不超原阈值才采用，超限返回ik_discontinuity，无解保留原inverse错误。不加Lula/tip-axis、不改frame/阈值/姿态语义/逐命令碰撞。 / Retry the identical pour TCP full-pose target once with the current point's planned joints only after current-seed local IK fails; accept only a valid solution inside the existing continuity bound, reject branch jumps explicitly and retain the original no-solution error otherwise. Preserve frames, thresholds, full-pose semantics and command-level collision checks without adding Lula or tip/axis solving. (local)
- [env] [chore] 具体失败场景：换seed可能找到远关节分支，preparation只约束原抓持关系，不能约束runtime实测抓持修正后的新解；因此在fallback动作边界复用既有maximum_waypoint_joint_delta_rad拒绝远跳，不新增配置或gate。 / A changed seed can find a distant joint branch after measured-attachment correction, beyond what original preparation constrains; reuse the existing maximum joint-delta bound at this fallback boundary without introducing configuration or a new gate. (local)
- [eval] [chore] 加入执行回归：同target nominal-seed fallback完整姿态成功、两seed失败/远跳均零动作、fallback路径碰撞在apply前停止；跑原202项命令后停改源码，主会话review并启动fresh E，正式结果待验证。 / Add execution regressions for identical-target full-pose fallback success, no-motion exhaustion/branch rejection and collision rejection before apply; rerun the existing202-test command, then freeze source for primary review and fresh E. (local)

### Full-pose重试实现与验证 / Full-Pose Retry Implementation and Validation
- [env] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2555-L2564：pour原local IK invalid时，对同一target用当前point原planned q重试；有效远跳复用原maximum delta拒绝，无解保留原inverse错误。完整姿态/阈值/frame/逐命令碰撞不改，未加入Lula/tip-axis。 / Retry the same full-pose target with planned joints only after current-seed failure, reject valid distant branches using the existing bound and preserve the original no-solution error without broader solvers or changed semantics. (local)
```diff
  goal, valid = local_inverse_kinematics(self.tcp, target, start, self.limits, tolerance)
+ if not valid:
+     goal, valid = local_inverse_kinematics(self.tcp, target, np.asarray(point["joints"]),
+                                           self.limits, tolerance)
+     delta = joint_delta(start, goal)
+     maximum_delta = self.config["maximum_waypoint_joint_delta_rad"]
+     if valid and delta > maximum_delta:
+         raise PhaseMotionError("ik_discontinuity", "stage/delta/configured maximum detail")
  if not valid:
      raise PhaseMotionError("inverse_kinematics_failed", "measured pour-pose correction is unreachable")
```
- [eval] [chore] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3140-L3249：4执行回归及复用fixture，真实full local solver fallback核对target不变、planned seed、body完整姿态及tip/axis误差；全失败与远跳均零动作，fallback路径碰撞在首次apply前拒绝。 / Four execution regressions and a shared fixture verify identical-target planned-seed full solving and final body/tip/axis residuals, zero-motion exhaustion/branch rejection and collision rejection before apply. (local)
- [eval] [chore] 原测试命令最新 **206 passed**（此前202+新增4），5.68s，既有asyncio_mode warning1；git diff --check通过，Ruff仍仅旧L1015 I001及测试L2810/L2896 E731。源码/测试自本次通过后停止修改，交主会话review与fresh E；不以unit/诊断代替runtime。 / The same command passes206 tests in5.68s with the existing warning and lint findings; whitespace validation passes. Freeze source/tests for primary review/fresh E without substituting unit or diagnostic evidence for runtime results. (local)
- [docs] [docs] [修改 / Modified] `docs/forge/LABUTOPIA_POUR_CLEARANCE_20261119.md` L1-L110：D真实failed、居中零横移125步fresh资格与transport失败、无动作精确1650帧边界诊断、bounded full-pose retry及follow-up pending；完整同步本版本月档/index。 / Document D's failed runtime, actual centered readiness route, exact saved-boundary diagnostic, bounded full-pose retry and pending follow-up, synchronizing the full current-version archive/index. (local)

- [eval] [exp] 主会话review本次10行full fallback+4执行回归无Blocker/Major后启动fresh E：`out/labutopia-pour-clearance-20261119/E-fresh`，HEAD`91b910840e56a15e0a73d4dea72ad2ca5a54deaa`+保存的implementation.diff标识当前代码；E正式终态pending，主会话owns执行，源码/测试继续固定。D仍failed，报告顶部明确D failed/E pending。 / Primary review admits the ten-line correction/four regressions and launches E with recorded HEAD plus implementation.diff; E remains pending, the primary owns execution and source/tests stay fixed while D remains failed. (local)

### E失败后手指指令连续性修复计划 / Post-E Finger Command Continuity Plan [实现完成；F待验证]
- [eval] [exp] 先保存E完整summarizer，记录E依旧transport失败/process0/hold0，不能将full-pose数值fallback描述为已解决真实倾倒。对比D/E反馈确认acquire末实际已施加finger target与实测开度不同，pour初始化却复制实测开度，替换原压紧指令。 / First summarize E's persisted failed transport outcome without process/hold, preserving that numerical fallback has not solved pouring. Compare saved commanded and measured finger values across acquire/pour boundaries. (local)
- [env] [fix] 仅非acquire初始化从现有SDK controller.get_applied_action().joint_positions按finger索引读取上一dense指令并保留；缺action/positions、索引不可取或finger非有限则在已有held动作边界以明确PreconditionError零motion拒绝，不以测量开度替代未知servo指令。具体风险是丢失previous commanded压紧值，测量位置不能重建servo目标；不新增shadow状态/overshoot/follow/力/阈值。acquire与release仍.04。 / Preserve the controller's previous dense applied finger command for non-acquire phases. Missing/unindexable/nonfinite targets reject with an explicit precondition error before motion rather than substituting measurements, because measured openings cannot reconstruct servo targets. Add no shadow state, force, overshoot, follow or thresholds; retain acquire/release opening. (local)
- [eval] [chore] 更新execution fixture模拟真实controller已施加目标，新增acquire→pour指令/测量不同的继承、release开爪、缺失/非有限零动作回归；跑原206命令后停改源码，交主会话review/fresh F，因果修复仍待实测。 / Model actual controller-applied targets in the execution fixture and test cross-phase command continuity, release opening and no-motion invalid inputs; rerun the206-test command and freeze for primary review/fresh F without claiming causal resolution. (local)

### E终态 / E Terminal Outcome [failed]
- [eval] [exp] `E-fresh/placement-summary.json`保存task`task_46b67f1aaa20470c` failed，2026-11-19T21:43:16.559192+08:00至22:05:21.927886+08:00/returncode1。acquire`ab87d968d4e54cbeb14b520b4b2ec604.json` succeeded2139；pour`aa03d16ad38040c29238017b432b9bf0.json`2062样本均transport，仍measured pour-pose correction inverse错误，process0/hold0，最大tilt.8227368211517622rad，末attach10.141432925mm/.5132515595rad。 / E persists the stated failed task, acquisition success and transport-only correction-IK failure without process/hold; numerical fallback is not claimed to solve pouring. (local)
- [eval] [exp] 相对D1651样本/tiltmax.59517，E推进至2062/.82274但仍失败；主会话ffprobe pour视频`e456e5e8e26d45e4b0a7000eeab5c252.mp4`为34.35s/2061帧/3840×960/45003107bytes。 / E advances beyond D but remains failed; the primary verifies the complete stated video metadata. (local)
- [env] [fix] D/E反馈共同证实acquire末finger_target[.01592840626835823,.015569766983389854]与实测[.019920673221349716,.015569900162518024]不同，而旧pour首target采用后者，左指目标向外3.992267mm。此证据直接定位servo目标交接bug，不证明它是失败充分原因或F可成功。 / Both runs establish measured-opening substitution at the held-phase command handoff, without claiming proven causal resolution. (local)

### 已施加手指指令继承 / Applied Finger Command Handoff [实现完成]
- [env] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2454-L2467：非acquire读取controller上一dense applied action finger目标；缺失/索引不可取/非有限以held_finger_target_unavailable PreconditionError在play/apply前拒绝，acquire/release .04保留。SDK本地`articulation_controller.py` L231-L248已确认dense无indices；不引入shadow状态/额外力或阈值。 / Retain applied finger targets across held phases and reject missing/unindexable/nonfinite targets before motion, preserving acquire/release opening and existing control ownership. (local)
```diff
- finger_target = np.full(2, .04) if operation == "acquire" else measured_joint_positions[finger_indices]
+ if operation == "acquire":
+     finger_target = np.full(2, .04)
+ else:
+     applied = self.robot.get_articulation_controller().get_applied_action()
+     finger_target = np.asarray(applied.joint_positions, dtype=float)[finger_indices].copy()
+     # missing/index errors and nonfinite finger targets raise PreconditionError
```
- [eval] [chore] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2190-L2199：controller double独立保留最近applied dense target，apply时保存copy，不把测量位置当命令。 [新增 / Added] L3252-L3305：6项执行回归验证真实acquire→pour指令/实测不同仍保持首及carry目标、release开爪、missing action/positions/短数组/NaN/Inf零motion且callback清理。 / Model the latest applied command and test actual cross-phase preservation, release opening and no-motion invalid-target rejection. (local)
- [eval] [chore] 原命令最新 **212 passed**（206+6），5.58s，既有asyncio_mode warning1；git diff --check通过，Ruff只旧source L1015 I001及测试现L2816/L2902 E731。实现和测试通过后停改，主会话review/F待执行，不宣称因果已解决。 / The same command passes212 tests with the existing warning/lint findings; freeze source/tests for primary review and pending F without claiming runtime causal success. (local)
- [docs] [docs] [修改 / Modified] 报告追加E实际失败、D/E差异及指令交接证据、SDK所有权与212项测试、F pending，并同步本版本月档/index。 / Record E's failure, D/E differences, command-handoff evidence, SDK ownership,212 regressions and pending F in the synchronized report/archive/index. (local)

- [eval] [exp] 主会话review后已启动fresh F：`out/labutopia-pour-clearance-20261119/F-fresh`，正式task/阶段/终态及因果修复结论pending；主会话owns仿真与验收，运行期间源码/测试固定。 / Primary review launches F in the stated workspace; task/phase/terminal evidence and causal resolution remain pending. The primary owns execution/acceptance and source/tests stay fixed. (local)

- [docs] [fix] [完成] 先记录F-fresh初次上游LLM流中断且tasks为空、未进入仿真/无phase反馈，文档不写motion失败；同步相同代码配置F-retry-fresh已启动pending，源码/测试继续固定。 / Record the initial F-fresh upstream LLM stream interruption with empty tasks and no simulation/phase feedback, not a motion failure; document the identical-code/configuration F-retry-fresh as pending while keeping source/tests fixed. (local)

- [eval] [exp] F-fresh首次于2026-11-19 22:10:33至22:11:10（Asia/Shanghai）退出returncode1，host.log为`LLM upstream response stream interrupted`，tasks=[]、无phase反馈/新动作，未进入仿真；这是上游失败而非motion失败。主会话以同源代码/配置启动`out/labutopia-pour-clearance-20261119/F-retry-fresh`，actual结果pending；源码/测试固定。 / Initial F stops upstream before simulation with empty tasks and no phase feedback/new motion; it is not a motion failure. The primary retries identical source/configuration in the stated workspace, with actual outcome pending and source/tests frozen. (local)

- [docs] [docs] [完成] 补入主会话对三处修复及新增18项回归的review结论，以及F retry/E七个输入文件strip并归一workspace后、profile归一后完全一致的对照证据；正式motion结果仍pending，仅更新当前版本报告/月档/索引。 / Record the primary review of three fixes and18 new regressions, plus normalized equality of seven F-retry/E input files and the profile; retain pending runtime outcome and change only the current report/archive/index. (local)

- [eval] [docs] F运行前的代码review对三处修复及新增18项回归未见Blocker/Major（后续F失败已推翻手指patch验收，最终撤回见下文）：变更仅Isaac Adapter，source/target语义与阈值保留，full fallback保持原target/连续性/逐命令碰撞；现有controller持有手指指令，无shadow状态。F retry/E七个输入strip并归一workspace后完全相同，profile归一后相等，实际motion结果仍pending。 / Pre-runtime code review finds no Blocker/Major across three fixes and18 new regressions (F later overturns finger-patch acceptance; it is reverted below), retaining Adapter ownership, target semantics, thresholds, full-target continuity/collision checks and controller-owned finger commands. Seven normalized input files and normalized profiles match between F retry and E; runtime evidence remains pending. (local)

- [docs] [docs] [修改 / Modified] `docs/forge/LABUTOPIA_POUR_CLEARANCE_20261119.md` L112与本月档L365-L369、对应CHANGELOG本版本完整条目：新增上述review及输入对照结果，未改源码/测试或正式pending判定；UTF-8、当前版本索引完全一致及diff whitespace检查通过。 / Add the stated review/input-comparison evidence at these lines and synchronize the complete current index entry; source/tests and pending runtime status remain unchanged. UTF-8, exact entry consistency and whitespace validation pass. (local)

### F失败后无动作对照计划 / Post-F No-Motion Comparison Plan [计划]
- [eval] [exp] 主会话只读比较E/F相同时间段的joints、手指目标/实测、接触几何及已有视频，判断保留原手指指令后为何更早失去双边接触；不得把指令继承正确等同夹持修复成功。暂不改生产源码、阈值或配置，不启动新增完整仿真；下一步生产改法由主会话依据证据裁决。 / The primary will compare saved E/F joints, commanded/measured fingers, contact geometry and videos over matching time windows without motion, investigating earlier bilateral-contact loss after command preservation. Correct command inheritance does not establish successful grasp correction. Keep production source, thresholds and configuration fixed, start no additional full simulation and leave the next production decision to the primary. (local)
- [docs] [docs] [完成] 补齐F-retry真实failed task、fresh readiness、transport阶段physical_grasp_lost、指令继承及完整视频数据；保留首F上游失败与D/E运行失败历史，将报告/月档/index同步，文档验证后等待主会话对照诊断。 / Record the actual failed F-retry task, fresh readiness, transport-stage physical_grasp_lost, correct command inheritance and complete video metadata; preserve initial F upstream failure and D/E runtime failures, synchronize the report/archive/index and await the primary comparison. (local)

### F-retry真实终态 / F-Retry Actual Outcome [failed]
- [eval] [exp] task`task_26d6248c2657456e`，2026-11-19T22:11:23.962067+08:00至22:28:53.830262+08:00，failed/returncode1。acquire`a643a6c9cb8b4765b24304c6fca59065.json` succeeded2139/113lift，末target与measurement逐项同E；末attach9.314366924mm/.01352641545rad，grasp_valid=false/contact_load=true，不能写全程夹稳。 / F-retry records the stated failed task and times after successful acquisition; final commands/measurements match E, while the stated attachment errors and validity flags remain explicit. (local)
- [eval] [exp] readiness`fb3f00aef189438ca9a918eca0f725a8.json`、revision后缀`bd21cd9e8fb64cf38dd07e23d421372e:1`通过居中.048/yaw0/azimuth+π/2/zerooffset125step same-side路线。pour首target已正确继承acquire[.01592840626835823,.015569766983389854]m，交接改法生效但未解决真实夹持。 / Fresh readiness admits the stated centered zero-offset125-step route; the first pour command correctly inherits acquire's applied target, without establishing successful grasp. (local)
- [eval] [exp] pour`7a5700228fe34c4e807959b1f682b4e2.json` failed，physical_grasp_lost/bilateral contact lost during attached motion；411样本全transport、process0/hold0、max tilt.07209758523rad，attach位置/旋转峰.02303421763m/.1794298536rad。主会话ffprobe视频`85585f0c9c1f4c96ac8edfc8c9d56b13.mp4`6.833333s/410frames/3840×960/8855228bytes，额外终态record1。 / Pour fails with the stated bilateral-contact loss, transport-only samples and attachment/tilt evidence; the primary verifies the complete410-frame video and extra terminal feedback record. (local)
- [eval] [docs] 正式结果边界：指令交接正确不代表夹持或倾倒成功。F比E更早失去接触，后续仅主会话执行上述无动作同时间段比较；生产源码、阈值、配置继续固定，下一步生产改法由主会话裁决。 / Correct command inheritance is not successful grasp or pouring. F loses contact earlier than E; only the primary's planned no-motion comparison follows, with source/thresholds/configuration fixed until its production decision. (local)

- [docs] [docs] [修改 / Modified] 报告L3及L94-L122、本月档L371-L381和对应CHANGELOG当前版本完整条目：`F pending` → `F failed`，新增终态/视频/指令继承及无动作比较计划，保留D/E和首F上游失败事实；UTF-8、索引完全一致、git diff --check通过。 / Update the stated report/archive lines and complete current index entry with actual F failure, video, command inheritance and the no-motion comparison plan, preserving earlier outcomes; UTF-8, exact index consistency and whitespace checks pass. (local)

### F夹持几何无动作诊断实施计划 / F Grip-Geometry No-Motion Diagnostic Plan [完成]
- [eval] [exp] 新增`out/labutopia-pour-clearance-20261119/diagnose-grip-geometry.py`，复用既有SimulationApp、F-retry profile、LabUtopiaBackend与WorkerSessionContext reset初始化；读取R05唯一RigidBody，调用生产cooked_body_boxes取得每个body-frame convex并按collider_profile_artifact方式转world保存。保存DOF、hand/finger Drive/Physx/mimic/tendon属性、world transforms、finger_geometry及oracle approach；前后验证reset time/joints不变，不发apply/set/step或物体变更，app.close清理。 / Add the specified production-backed read-only reset diagnostic, preserving every cooked R05 convex in body/world frames, DOF/drive/PhysX/mimic/tendon metadata, transforms, finger geometry and oracle approach. Verify unchanged reset time/joints, issue no action/set/step or object change and close the app. (local)
- [eval] [docs] 用既有labutopia conda Python运行并保存JSON/log，输出仅初始化与结果路径；范围为不同revision的无动作诊断，不授予历史F执行资格，不修改生产/tests/config，不启动完整仿真，主会话分析JSON并裁决生产下一步。 / Run with the existing labutopia environment and persist JSON/log with bounded console output; this different-revision no-motion diagnostic grants no historical-F execution authority, changes no production/tests/config and leaves analysis/production decisions to the primary. (local)

- [eval] [exp] [完成] 按主会话补充规格，同一几何诊断JSON只读保存F readiness fb3f00aef189438ca9a918eca0f725a8的125个原step joints及各自model.tcp(joints)、model.limits、dt/config；用于离线核对nominal目标旋转，不重演/求解或发运动命令。 / Extend the same diagnostic JSON with read-only FK matrices for all125 original F-readiness step joints, plus model limits, dt and config, enabling offline nominal-rotation comparison without replay, solving or motion commands. (local)

### F运行证据后的收敛撤回计划 / Scope-Convergence Revert Plan After F Runtime Evidence [完成]
- [env] [fix] 按主会话裁决撤回F手指目标继承patch及仅服务该patch的6项测试/fixture修改，保留路线/同侧退出和full-pose单次IK重试；源码与E保存implementation.diff重建结果逐字核对，以E真实failed运行作为最终源码证据。F推翻该手指patch实际验收，先前无Major仅为运行前review。 / Revert the F finger-command patch and its six dedicated tests/fixture changes while retaining route/retreat and single full-pose IK retry; compare source byte-for-byte against E reconstructed from its saved implementation.diff and use E's failed runtime as final-source evidence. F overturns acceptance of the finger patch; the earlier review was pre-runtime only. (local)
- [eval] [docs] 记录无动作诊断、20N/1200N实际force caps及其session/asset opinions、无mimic/tendon证据和完整convex；不单凭cap不对称认定根因。原始大JSON保留，一次解析另存轻量convex/drive/FK摘要和near-axis范围；不改force/config，不新增完整仿真。同步报告/月档/index，显眼结论为路线资格修复通过、实际倾倒失败，首段标F尝试reverted；运行回归后交主会话提交/推送。 / Record the no-motion geometry/drive evidence without claiming asymmetric caps alone establish cause; preserve the raw JSON and extract a compact convex/drive/FK summary with explicit near-axis ranges. Change no force/config and start no full simulation. Synchronize documentation, state route qualification passes but actual pouring fails, mark F reverted and leave commit/push to the primary after regressions. (local)

### 几何诊断完成与F撤回 / Geometry Diagnostic Completion and F Revert [完成]
- [eval] [exp] [新增 / Added] `out/labutopia-pour-clearance-20261119/diagnose-grip-geometry.py` L1-L213：production fresh reset、R05 cooked完整convex的USD world转换、DOF与hand/joint全部属性和逐层opinions、robot PhysX/mimic/tendon属性/关系、finger geometry、oracle approach及125原step只读FK/limits/dt/config；前后time/joints验证和app.close。 / Add the specified fresh read-only geometry/drive/FK diagnostic with unchanged reset-state verification and app cleanup. (local)
```diff
+ boxes, evidence = cooked_body_boxes(stage, body, model.config['collision_margin_m'])
+ body_world = np.asarray(UsdGeom.Xformable(body).ComputeLocalToWorldTransform(0)).T
+ world = (body_world[:3, :3] @ vertices.T).T + body_world[:3, 3]
+ tcp_matrix = model.tcp(np.asarray(point['joints'], dtype=float))
+ # Save authored property-stack opinions and composed default/time-zero readback.
+ # Verify unchanged reset joints/time; issue no action, set, step or IK solve.
```
- [eval] [exp] 诊断exit0、202.2089667378459s，py_compile通过，time始末.0020833334419876337s、joints完全不变/motion_commands0，保存125FK。首次缺既有EULA变量的启动在Kit前退出，补齐环境后本次完成。完整raw JSON保留，轻量summary4,393,907bytes保留全部32convex/907 world vertices及drive/FK；原1.195GB来自5,081,094body-frame slabs。显式near-axis诊断范围r≤.1/span[-.02,.20]m下32保留/0排除，rmax34.375804mm、span[-.000890,116.202456]mm，无foreign convex；不同fresh revision不授予执行资格。 / The completed no-motion diagnostic records the stated unchanged reset, all125 FK matrices and complete convex evidence; preserve raw geometry and use the compact summary, with no foreign convex under the explicit diagnostic range and no execution authority across revisions. (local)
- [eval] [exp] 两指stiffness1e7/damping1e5；joint1实际maxForce20N来自session layer覆盖asset1200N，joint2 asset1200N，DOF maxEffort吻合；robot子树未见mimic/tendon schema/属性/关系。不单凭cap差异宣称滑脱根因，不改force/config，作为后续夹持问题线索。 / Both drives share stiffness/damping but session composition sets finger1 to20N while finger2 retains asset1200N, matching runtime effort limits. No authored mimic/tendon evidence is found; this alone does not establish slip causality or justify force/config changes. (local)
- [env] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2454-L2456：撤回F get_applied_action/held_finger_target_unavailable，恢复E measured opening初始化；路线L752/L1646-L1705及full-pose重试现L2544-L2553保留。 / Revert only the failed F command-inheritance/precondition patch and restore E initialization, retaining route/retreat and full-pose retry. (local)
```diff
- applied = self.robot.get_articulation_controller().get_applied_action()
- finger_target = np.asarray(applied.joint_positions)[finger_indices].copy()
- # Reject missing/unindexable/nonfinite previous targets before play/apply.
+ finger_target = np.full(2, .04) if operation == "acquire" else np.asarray(
+     self.robot.get_joint_positions())[finger_indices].copy()
```
- [eval] [chore] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2187-L2193恢复原fixture仅记录apply命令；删除F专用6项回归（撤回前L3252-L3305），保留geometry L270-L441与full-pose fixture/4项回归现L3134-L3243。source及tests均逐字等于E implementation.diff基于原blob重建结果，最终motion证据适用E。 / Restore the original command-recording fixture and remove only the six F regressions, retaining geometry and full-pose regressions; final source/tests exactly match E reconstructed from its saved diff/base blobs. (local)
```diff
- applied_positions = positions.copy()
- robot.get_applied_action = lambda: SimpleNamespace(joint_positions=applied_positions.copy())
- # Six command-inheritance/precondition regression cases.
+ robot.apply_action = lambda action: commands.append(action.joint_positions.copy())
```
- [eval] [chore] 主会话final tests同命令 **206 passed**、5.65s、既有asyncio warning1项，git diff --check通过；final review接受本轮路线/退出及full-pose重试，搜索预算/完整qualify/full target/原连续性/逐命令碰撞均保留。F运行证据推翻其手指patch验收，该patch已撤回；此前三处无Major为运行前review，不能作为最终全接受。 / The primary's final regressions pass206 tests with one existing warning and clean whitespace checks; final review accepts route/retreat and full-pose retry within unchanged qualification, target, continuity and collision semantics. F overturns acceptance of its finger patch, now reverted; pre-runtime review is not final acceptance of all experiments. (local)
- [eval] [docs] 最终结论：路线资格修复通过，实际倾倒失败。E源码与最终相同，E2062样本全transport、process0/hold0、仍correction IK失败；F作为reverted尝试保留。force/config/初始布局不改，不继续完整仿真；源码/测试停止修改，Git主提交/推送由主会话执行，当前本版本commit pending。 / Final route qualification passes but actual pouring fails; E is the applicable identical-source failed runtime and F remains a reverted experiment. Preserve force/config/initial layout, stop further full simulation and source/test changes, and leave commit/push to the primary. (local)

- [docs] [docs] [修改 / Modified] `docs/forge/LABUTOPIA_POUR_CLEARANCE_20261119.md` L3/L94-L140、本月档L383-L423与CHANGELOG完整当前条目：首段标明路线资格通过/实际倾倒失败/F reverted，补诊断及最终206项验收范围，限定此前review证据；文档UTF-8、完整索引一致性与diff检查通过，后续仅待主commit receipt。 / Synchronize the stated report/archive/index lines with the final failed-runtime conclusion, reverted F experiment, diagnostic and206-test acceptance scope, preserving evidence limits; UTF-8, exact entry consistency and whitespace checks pass, awaiting only the primary commit receipt. (local)

- [docs] [chore] [完成] 仅追加主实现commit 5aa50f07、当前分支及北京时间receipt，并同步CHANGELOG本版本完整条目；主commit已完成、push待主会话执行，不新增版本或修改report/source/tests，不自行commit/push。 / Append only the primary implementation commit5aa50f07, branch and current Beijing-time receipt, synchronizing this complete index entry; implementation commit is complete and push remains with the primary, with no new version, report/source/test edits or independent commit/push. (local)

### 主实现 Git Receipt / Primary Implementation Git Receipt
- Commit: `5aa50f07`
- Branch: `feature/planning-loop`
- 时间 / Time: `2026-11-19 22:50:27 Asia/Shanghai (UTC+8)`
- [chore] [chore] 主实现commit已完成；push待主会话执行。本receipt仅记录实现提交，不追记receipt自身提交。 / Primary implementation commit is complete; push remains pending with the primary. This receipt records the implementation commit without recursively recording its own commit. (5aa50f07)

## v17.8.0 (2026-11-19 20:00) - codex

### 实施范围 / Implementation Scope [完成]
- [env] [tune] 仅调整机器人安装高度与位置；桌面物品、操作区及安全阈值保持原值。先依据桌面几何、生产 URDF 与实际抓取/倾倒目标计算单一部署，再修改并执行 fresh-reset 仿真。 / Adjust only robot mounting height and placement, retaining tabletop objects, operation area and safety thresholds; derive one deployment from measured table geometry, production URDF and actual grasp/pour targets before editing and fresh-reset simulation. (local)
- [env] [feat] 离线分析支持单一增高布局，已新增 Adapter 私有 USD 安装覆盖层，保持底盘落地、关节一致与增高支柱碰撞检查；不修改 LabUtopia 原始资产或公共接口。 / Offline analysis supports one elevated layout; add the Adapter-private elevated USD deployment with grounded chassis, coherent joints and pedestal collision checks, preserving original LabUtopia assets and public interfaces. (local)
- [eval] [exp] 已保存计算、无运动验证、终态反馈及视频到独立输出目录，补全精确Diff/行号及索引；实际实现提交已记录于下方收据，push尚待主会话执行。 / Preserve calculations, no-motion validation, terminal feedback and video in a separate output directory and complete exact diffs/lines and the index; the completed implementation commit is recorded below, while the push is not yet performed. (local)

### 具体实施文件 / Concrete Implementation Files [完成]
- [env] [feat] 新增 `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-elevated.usda`，引用原机器人并仅上移全部12个臂/末端刚体0.43m；添加0.12×0.12×0.43m碰撞柱、同步安装关节与质量惯量。 / Reference the source robot, raise its 12 arm/end bodies by0.43m, add the collision column and update the mounting joint and mass properties. (local)
- [env] [tune] 修改 `configs/labutopia-ridgebase-station.yaml`（路径均相对于Isaac Adapter）机器人位置至[-1.12,.18,.01]及机器人资产路径；修改 `configs/labutopia-ridgebase.json` 选择新机器人与新增 `configs/labutopia-ridgebase-elevated-motion.json`，后者仅追加支柱碰撞路径。桌面layout逐字保留。 / Update robot placement and asset paths, select the elevated asset/motion configuration, and append only the column mount collider; preserve tabletop layout verbatim. (local)
- [env] [fix] 修改 `src/isaacsim_lab/phase_motion.py` 的 `_collisions`，显式mount碰撞体不再随机器人子树被忽略，保留link0连接豁免。 / Keep explicitly configured internal mount colliders visible to sphere/finger/payload checks while preserving link0 connection exemption. (local)
- [eval] [chore] 扩充 `tests/test_phase_motion.py`，新增 `tests/test_ridgebase_elevated.py`，验证真实碰撞函数与无运动USD组合；新增 `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` 记录设计、限制及命令。 / Exercise actual collision logic and no-motion USD composition, and document design, limitations and commands. (local)
- [eval] [exp] `out/labutopia-elevated-20261119/offline-placement-analysis.py/.json/.log` 记录单一布局离线计算。主会话纠正规格：第二lip clearance由错误请求.078m改为现行profile允许的.048m，重算24个候选；运行时阈值不改。 / Correct the caller's second analysis clearance from the initially requested.078m to the existing.048m allowance and recompute24 candidates, changing no runtime threshold. (local)
- [env] [fix] 新USD显式声明metersPerUnit=1与upAxis=Z，避免独立打开wrapper时使用USD默认厘米单位；组合测试一并断言。 / Declare meter units and Z up explicitly so standalone wrapper reads retain the source frame, and assert them in composition tests. (local)
- [eval] [exp] 新增 `out/labutopia-elevated-20261119/no-motion-check.py` 与 `run-elevated.py`：前者调用生产Backend/WorkerSession初始化并读回臂基、柱边界、关节及home碰撞；后者保存独立workspace/config/metadata/命令和终态；主会话已触发C并保留失败终态。 / Add production-backed no-motion initialization/readback and a separate full-run launcher preserving workspace, configs, metadata, command and terminal outcome; the primary runs C and retains its failed terminal outcome. (local)

### 文件变更详情 / File Changes [实现完成]
- [env] [feat] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-elevated.usda` L1-L96：米/Z-up stage、原asset reference、12个arm/end刚体z+.43、安装joint localPos0[.3,0,.43]、6kg质量/COM/惯量及CollisionAPI柱。 / Meter/Z-up reference wrapper raises12 bodies, updates the mounting joint and mass properties and adds the collision-enabled column. (local)
```diff
+ metersPerUnit = 1
+ upAxis = "Z"
+ prepend references = @/home/yanxu/LabUtopia/assets/robots/ridgeback_franka.usd@
- # source arm-root translate z = .2800000011920929
+ double3 xformOp:translate = (.3000003695487976, 3.960444860950929e-9, .7100000011920928)
+ point3f physics:localPos0 = (.3,0,.43)
+ float physics:mass = 6
+ point3f physics:centerOfMass = (.3,0,.215)
+ float3 physics:diagonalInertia = (.09965,.09965,.0144)
+ def Cube "elevation_column" (prepend apiSchemas=["PhysicsCollisionAPI"])
+ # local translate [.3,0,.215], scale [.12,.12,.43], size1
```
- [env] [tune] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-station.yaml` L11-L12；`labutopia-ridgebase.json` L4/L7。 / Update station asset/position and profile robot/motion selection. (local)
```diff
- usd_asset: assets/robots/ridgeback_franka.usd
- base_position: [-1.05, 0.18, 0.01]
+ usd_asset: /home/yanxu/PhyAgentOS-forge/examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-elevated.usda
+ base_position: [-1.12, 0.18, 0.01]
- "motion_config_path": "labutopia-oracle-motion.json"
- "robot_usd_path": "/home/yanxu/LabUtopia/assets/robots/ridgeback_franka.usd"
+ "motion_config_path": "labutopia-ridgebase-elevated-motion.json"
+ "robot_usd_path": "labutopia-ridgebase-elevated.usda"
```
- [env] [feat] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-elevated-motion.json` L1-L112：复制oracle，仅新增mount路径；其他值全等。 / Copy oracle and add only the column mount path; all other values match. (local)
```diff
- "mount_collision_paths": ["/World/table"]
+ "mount_collision_paths": ["/World/table", "/World/Ridgebase/arm_mount_link/elevation_column"]
```
- [env] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L1238-L1239/L1250/L1274/L1317：sphere、finger、payload共享局部predicate；原link0 exact-path连接豁免保留。 / Apply the local predicate to all three collision shapes while retaining the original link0 exact-path connection exemption. (local)
```diff
+ def ignore_robot(path):
+     return path.startswith(robot_path) and path not in self.config["mount_collision_paths"]
- path.startswith(robot_path) or ...
+ ignore_robot(path) or ...  # sphere / finger / payload
```
- [eval] [chore] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2996-L3038，8种生产`_collisions`回归；新增`tests/test_ridgebase_elevated.py` L1-L89，4个配置/USD组合测试。 / Eight actual-collision regressions and four configuration/USD composition tests. (local)
```diff
+ @pytest.mark.parametrize("kind", ["panda_link0", "panda_link2", "finger", "payload"])
+ @pytest.mark.parametrize("explicit_mount", [False, True])
+ # explicit mount hit rejects link2/finger/payload; link0 connection allowed
+ # ordinary robot geometry remains ignored
+ # no-motion USD checks all arm bodies, unchanged chassis, joint anchors, column and units
+ # pure config test compares complete motion values except the added mount path
```
- [docs] [docs] [新增 / Added] `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` L1-L124：双语部署、原装区别、离线限制、所有权、完整命令、验证及当前实测状态。 / Bilingual deployment design, source differences, offline limits, ownership, commands, validation and current run status. (local)
```diff
+ Fixed armroot [-.82,.18,.72]m; one0.43m elevation; table layout preserved.
+ Endpoint sensitivity only; full fresh-revision qualification still required.
+ 194 tests pass; production home collision passes; C acquires then fails all24 pour candidates.
```

### 已完成验证 / Completed Validation
- [eval] [exp] 离线seed20261119、12 seeds、单一臂基布局，FK最大24.0067µm；8 grasp有5条grasp+lift可达，24 pour有4条各端点可达，其中2条各端点桌/柱余量≥3mm，yaw=-π/2 az0 clearance=.04/.048。最小所选端点余量57.6135mm，最小关节限位余量.1807476rad。只证明独立端点敏感性，不证明路径、自碰撞、载荷、其他物体或夹取接触。 / Offline results establish the stated endpoint sensitivity with deterministic analysis seeds, not full route or physical success. Evidence: `out/labutopia-elevated-20261119/offline-placement-analysis.json`. (local)
- [eval] [chore] `PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py examples/forge-adapters/isaacsim_lab/tests/test_ridgebase_elevated.py -q` → **194 passed**；既有asyncio_mode警告保留。 / All194 tests pass with the existing plugin-disabled asyncio configuration warning. (local)
- [eval] [chore] 首次pytest漏workflow PYTHONPATH致28项导入失败，另1项测试未处理world joint无Body0，均修正后重跑通过；首次no-motion缺repo root路径在Backend导入前停止，retry已通过，原日志保留不记通过。 / Initial harness/import failures were corrected before successful reruns; failed initial logs remain explicit. (local)
- [eval] [chore] 新`test_ridgebase_elevated.py` Ruff通过，`git diff --check`通过；整体旧文件Ruff保留3个既有问题（phase_motion.py:1015 I001，test_phase_motion.py:2637/2723 E731），不记整体lint通过。 / New-file lint and diff checks pass; three existing old-file lint findings remain and whole-file lint is not reported passing. (local)
- [data] [exp] `deployment-diff-evidence.json`证明station除位置/机器人资产路径外逐字一致，layout后文本完全相同。主会话filecmp确认外部原robot USD、tabletop scene USDA、tabletop_station.yaml与A/B既有external-scene-snapshot逐字节一致，并独立确认motion JSON移除mount_collision_paths后与oracle逐值相等。 / Exact station/layout and bytewise external-asset comparisons confirm preserved tabletop and sources; independent comparison confirms identical oracle motion values except mount_collision_paths. (local)
- [env] [exp] 生产Backend/WorkerSession fresh初始化 `status=initialized`、home_collision_check=passed、manipulation_commands=0、读回期间joints不变；actual armroot[-.8199764490,.1800000221,.7199999690]m。柱world bounds=[[-.8799765223,.1200000209,.2899999881],[-.7599765188,.2400000244,.7199999952]]m，collision启用、旧臂inactive、旧碰撞体空。mount joint世界锚点差6.6643e-8m；不声称所有关节锚点零差。 / Production initialization and home collision pass with the stated actual frame and column bounds; mounting-joint alignment is measured without claiming every joint has zero separation. Evidence: `out/labutopia-elevated-20261119/no-motion.json`, fresh revision `labutopia-tabletop-rod-rack-v1:2faca503a5de4b20bc3e3a4ea8b08e03:0`. (local)
- [env] [chore] 通用层与公共接口未改；部署与碰撞属于Adapter，WorkerSession拥有reset/revision，Runtime保留取消、结算、恢复。临时测试依赖和USD单位review发现均已解决，主会话当前无其余Major。 / Generic contracts remain unchanged; Adapter, WorkerSession and Runtime ownership remains explicit, and the identified test-portability and stage-unit review findings are resolved. (local)

### 完整仿真实测 / Complete Simulation [失败终态 / Failed terminal outcome]
- [eval] [exp] C目录`out/labutopia-elevated-20261119/C-elevated/`，任务`task_535f6c998fb04d52`已failed；metadata时间2026-11-19T20:12:24.275076+08:00至20:28:19.962926+08:00，returncode=1。28/28 approach probes available，`object.acquire=succeeded`、possession=holding、newrev=`labutopia-tabletop-rod-rack-v1:087c1ba6869a4d73825e4096ee6ddefd:1`；未执行pour/place。 / C records the stated failed terminal task, timestamps and return code1 after available probes and successful acquisition with holding possession; pour/place do not execute. (local)
- [eval] [exp] C反馈`phase-feedback/1cb8383e4ab8467db70bcf71d3f1bddc.json`共2139样本/113lift，其中42个lift样本grasp_valid，所有阶段79 grasp_valid/150 contact_load_valid；lift attach位置误差峰9.314366924mm。末样grasp_valid=false、contact_load_valid=true，不能写所有样本夹稳有效。 / C retains2139 samples,113 lift samples with42 grasp-valid lift samples,79 total grasp-valid and150 contact-load-valid samples, and a9.314366924mm peak lift attachment error. The final grasp is invalid despite valid load, so success is not generalized to every sample. (local)
- [eval] [exp] `prepare_held=unavailable/pour_route_unavailable`，24候选按各自报告的首个拒绝原因分类：12 transport数值未找到解、5 IK连续解失败、4 panda_hand撞TargetBeaker、2 panda_link6撞桌、1 payload撞TargetBeaker；不排除候选还存在其他问题，数值未找到解不证明数学不可达。完整detail保存在acceptance与placement-summary，零倾倒路线获准。 / All24 held-pour candidates fail; their first reported rejections classify as12 transport numerical no-solution,5 continuous-IK failures,4 hand/beaker collisions,2 link6/table collisions and1 payload/beaker collision. Additional issues remain possible, and numerical no-solution does not prove mathematical unreachability. Full raw reasons remain in acceptance and summary. (local)
- [eval] [exp] acquire阶段视频`out/labutopia-elevated-20261119/C-elevated/artifacts/labutopia/phase-video/7e063e88c039442db11750ea220ea68b.mp4`经主会话独立ffprobe确认35.616667秒/2137帧/3840×960/46641276bytes；抽帧目视确认增高部署。视频仅含acquire，无倾倒运动。 / Independent video inspection confirms the stated duration, frame count, resolution, bytes and elevated deployment. The video covers acquisition only, with no pouring motion. (local)
- [eval] [docs] C相对B恢复成功抓取，24倾倒候选中不再出现原A主导的link2撞桌失败，但仍因连续IK及腕部/载荷碰撞拒绝倾倒，不能归因为仅距离过远。离线端点可达不等于连续路径合格。按用户限制桌面初始位置不动，只采用一个计算布局，未继续逐次试高度或放松阈值。 / C restores acquisition beyond B and removes A's dominant link2/table reason from the observed candidate set, while continuous IK and wrist/payload collisions still prevent pouring. Endpoint reachability does not establish a continuous route or isolate distance as the cause. Initial tabletop positions and thresholds remain fixed with no successive height trials. (local)
- [eval] [chore] [完成] 新增 `out/labutopia-elevated-20261119/summarize-run.py`，只读acceptance/metadata/phase-feedback/assignment SQLite，输出有证据路径的阶段统计、抓取参数、视频与完整失败候选；缺文件不猜终态，不执行仿真或改部署。 / Add a read-only artifact summarizer for phase metrics, grasp parameters, videos and complete candidate failures, marking missing evidence without guessing terminal state or changing deployment. (local)
- [eval] [chore] [新增 / Added] `out/labutopia-elevated-20261119/summarize-run.py` L1-L224：按已落盘acceptance与feedback分别抽取task/phase状态，SQLite只读摘要acquire/pour参数，完整保留failure detail与逐候选原文；无lift时峰值null，无acceptance时task状态null。 / Summarize persisted task/phase evidence, read-only assignment routes, complete failures and candidate reasons, retaining unknown peaks/status when corresponding evidence is absent. (local)
```diff
+ summarize(workspace) -> tasks, phase_receipts, phase_feedback, assignments
+ failure_evidence, pour_route_failures[raw_detail, candidates], videos
+ missing_evidence; no_saved_phase_feedback means execution_not_inferred
```
- [eval] [chore] 抽取器历史A/B临时输出验证：A1791样本/108lift/24候选（22link2撞桌）及attach峰9.6809016469mm完全一致；B1248样本/0lift/失败detail保留；空目录task_status=null，terminal_task_status_recorded=false；Ruff通过。主会话现已抽取C并保存placement-summary.json，任务状态failed、24逐候选原因保留；缺失phase反馈仍标缺证据，不直接推断执行。 / Historical A/B and empty-workspace checks confirm exact stored counts/details and explicit unknown pending status; Ruff passes. The primary has also extracted C's persisted failed state and all24 candidate reasons, retaining explicit missing evidence without inferring execution from absence. (local)

- [docs] [docs] [完成] 根据已落盘C终态更新增高设计报告、v17.8.0月档及最新五版本：如实记录抓取成功后24条倾倒候选拒绝与任务失败、视频、样本有效性和用户桌面初始位置不动限制；不修改代码/config，不新增仿真。 / Update the deployment report, current version archive and latest five with C's persisted failed outcome, grasp evidence, candidate failures, video and unchanged initial tabletop layout; change no code/config and run no new simulation. (local)

### 文档收尾 / Documentation Finalization
- [docs] [docs] 更新本版本报告至实际C失败终态；月档仅修改v17.8.0条目并完整同步CHANGELOG最新五版本，历史版本内容保留。全文UTF-8及diff检查按本轮文档修改复核；代码测试沿用已通过194项，本次docs-only不重跑。实现Git hash已记录于下方收据；push结果在实际执行后另记。 / Finalize the report with C's actual failed terminal outcome, update only the current version and synchronize the complete latest five, preserving prior version contents. Validate UTF-8 and diff formatting for these documentation changes, retain the prior194-test evidence without rerunning code tests, record the completed implementation commit below, and await the actual push outcome. (local)

- [env] [fix] [完成] 提交前`git diff --cached --check`发现新USD L97为多余EOF空行；此前普通`git diff --check`未覆盖该untracked文件，不能声称旧检查已验证它。仅删除末尾多余空行（rstrip()+换行），USD范围由L1-L97修正为L1-L96，并同步月档与索引。 / Pre-commit staged checking finds an extra EOF blank line at new USD L97; earlier ordinary diff checks did not cover this untracked file. Remove only the extra final blank line and correct the recorded range toL1-L96 in the archive and index. (local)
- [eval] [chore] 精确stage上述USD、月档与CHANGELOG后，`git diff --cached --check`通过；USD现为96行，仅移除最后空白行，其他staged文件未修改。 / Staged whitespace validation passes after adding exactly the USD, archive and index; the96-line USD differs only by removal of its final blank line, and other staged files are untouched. (local)

- [docs] [chore] [完成] 补充已完成的v17.8.0实现提交收据，同步月档与索引，并将设计报告Git待补文字替换为月档收据链接；仅记录已发生提交，尚未发生的push结果不预写。 / Record the completed implementation commit, synchronize archive/index and replace the report's pending-commit text with a receipt link; record no unperformed push outcome. (local)

### v17.8.0 Git 实现提交收据 / Git Implementation Receipt
- Implementation commit / 实现提交：`f8a0c4a9`（完整 / full：`f8a0c4a9a7a2f3ae7e18a7d584bac235264e885c`）。
- Branch / 分支：`feature/planning-loop`。
- 时间 / Time：2026-11-19T20:38:04+08:00（Asia/Shanghai）。
- [docs] [chore] 上述hash标识已完成的实现提交；下一收据提交只记录该实现hash，不自引用。 / The hash identifies the completed implementation commit; the next receipt commit records this implementation hash without self-reference. (local)
- [chore] [chore] 本次push尚未执行，当前不记录成功或失败；主会话将在执行后把实际结果保存到`out/labutopia-elevated-20261119/git-push-result.json`，不据历史push失败预判本次结果。 / This push is not yet performed and no outcome is asserted; the primary records the actual result at the stated path after execution, without treating an earlier push failure as this attempt's outcome. (local)

## v17.7.0 (2026-11-19 18:44) - codex

### 完成修改 / Completed Changes [完成]
- [env] [fix] 通过独立 USD 覆盖层停用旧桌面 `/World/Franka`，仅保留本轮使用的底盘 Franka；原始资产不改。 / Deactivate the legacy tabletop `/World/Franka` through a separate USD composition layer, leaving the deployed Ridgebase Franka; preserve the source asset. (local)
- [env] [tune] 将底盘世界坐标从 `[-1.201, 0.36, 0.01]` 调整为 `[-1.05, 0.18, 0.01]`，保留既有姿态、控制周期、物理与感知配置。 / Move the base in world metres from `[-1.201, 0.36, 0.01]` to `[-1.05, 0.18, 0.01]`, retaining orientation, control timing, physics and perception configuration. (local)
- [comm] [fix] held 准备失败响应同时保留 failure_code 与 engine 逐候选 error，供重跑区分 IK、碰撞与对准失败；不改变路线选择或安全阈值。 / Preserve both failure_code and per-candidate engine error in held-preparation failures so reruns distinguish IK, collision and alignment failures; retain route selection and safety thresholds. (local)
- [eval] [exp] 已验证 USD 组合、配置路径和失败详情回归，并完成A/B仿真对照；两轮任务均失败，原因如下记录。 / Validate USD composition, configuration paths and failure-detail regressions, and complete the A/B simulation comparison; both tasks fail as documented below. (local)
- [docs] [chore] 新建月档第三部分（前档已超过 300KB），同步 Archive 与最近五版本；部署变化按 minor 升级为 v17.7.0。 / Start the third monthly archive because the prior part exceeds 300KB, update Archive and latest five, and classify the deployment change as minor v17.7.0. (local)

### 影响文件 / Affected Files
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-scene.usda`（新增 / new）
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-station.yaml`（新增 / new）
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase.json`（新增 / new）
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py`（修改 / modified）
- `examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py`（修改 / modified）
- `CHANGELOG.md`（索引 / index）
- `docs/forge/LABUTOPIA_RIDGEBASE_PLACEMENT_20261119.md`（新增 / new）

### 所有权与验证边界 / Ownership and Validation Boundaries
- [env] [chore] 场景覆盖与机器人位置属于 Isaac Adapter 部署层；Runtime 继续独占生命周期、取消、结算和恢复。公共 Tool/AgentLoop 不变，初始姿态与 IK 臂基仍由现行配置及 panda_link0 世界变换确定。 / Scene composition and robot placement belong to Isaac Adapter deployment; Runtime retains sole lifecycle, cancellation, settlement and recovery ownership. Public Tool/AgentLoop remain unchanged; the existing initial pose and panda_link0 world transform define the IK arm base. (local)
- [eval] [chore] 最小验证为组合场景无旧臂子树、原资产旧臂仍活动、新 profile 路径可解析，以及 held 失败详情在传输后仍可见；契约证据、Provider 证据和仿真实测分别记录。 / Minimum checks establish that the composed scene excludes the old arm subtree, the source still contains it, the new profile resolves its paths, and held failure details survive transport; distinguish contract, Provider and simulation evidence. (local)

### 实测设计 / Simulation Comparison [完成]
- [eval] [exp] A 轮仅移除旧臂、保留旧底盘位置；B 轮移除旧臂并启用新位置。每轮 fresh reset、新 scene revision、新感知及新 preparation，历史输出保留。 / Run A removes only the old arm at the original base position; run B also enables the new base position. Each run starts with a fresh reset, scene revision, perception and preparation while preserving prior outputs. (local)
- [env] [docs] 旧臂含 11 个碰撞体，世界包围盒 x[-0.604,0.117]、y[-0.286,0.146]、z[0.712,1.400]m；桌边 xmin=-0.735087m。底盘前缘当前约 -0.73477m，已贴桌边，新位置将伸入桌下约 15.1cm；机身顶部约 0.29m，低于桌底约 0.697m，仍须完整姿态/路线碰撞检查。 / The old arm has 11 colliders with world bounds x[-0.604,0.117], y[-0.286,0.146], z[0.712,1.400]m; the table edge is xmin=-0.735087m. The existing chassis front is about -0.73477m, already beside the table, and the new position extends about 15.1cm below it. The chassis top is about 0.29m below the 0.697m tabletop bottom; full pose/route collision checks still apply. (local)
- [env] [docs] 臂基由约[-0.901,0.36,0.29]移至[-0.75,0.18,0.29]m，至烧杯的水平距离由约0.897m减至0.694m；此几何变化不等于倾倒可达结论。 / The arm base moves from about[-0.901,0.36,0.29] to[-0.75,0.18,0.29]m, reducing the horizontal beaker distance from about0.897m to0.694m; this geometry alone does not establish pour reachability. (local)

### 文件变更详情 / File Changes
- [env] [feat] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-scene.usda` L1-L14：通过 subLayers 继承原场景并停用旧臂。 / Inherit the original scene through subLayers and deactivate the old arm. (local)
```diff
+#usda 1.0
+(
+    defaultPrim = "World"
+    subLayers = [@/home/yanxu/LabUtopia/assets/chemistry_lab/tabletop_station/tabletop_station.usda@]
+)
+over "World" {
+    over "Franka" (active = false) {}
+}
```
- [env] [tune] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-station.yaml` L1-L93，基于现行 `/tmp/ts_run21.yaml`，仅 L12 改位置。 / Copy the current station deployment with only L12 changing base position. (local)
```diff
-  base_position: [-1.201, 0.36, 0.01]
+  base_position: [-1.05, 0.18, 0.01]
```
- [env] [feat] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase.json` L1-L29：以现行 `/tmp/profile_run21.json` 为来源，L3/L6 接新站点与覆盖场景，L4-L5/L26/L28 使用同目录配置相对路径。 / Derive from the current profile; L3/L6 select the station and overlay, and L4-L5/L26/L28 resolve sibling config paths. (local)
```diff
- "config_path": "/tmp/ts_run21.yaml"
- "scene_usd_path": "/home/yanxu/LabUtopia/assets/chemistry_lab/tabletop_station/tabletop_station.usda"
+ "config_path": "labutopia-ridgebase-station.yaml"
+ "scene_usd_path": "labutopia-ridgebase-scene.usda"
```
- [comm] [fix] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py` L239-L244：传回 failure_code 与逐候选 error；error-only、code-only 和非 Mapping 响应保留。 / Forward both failure_code and per-candidate error, retaining error-only, code-only and non-mapping handling. (local)
```diff
- "error": str(result.get("failure_code", result.get("error", "held_route_unavailable")))
+ "error": ": ".join(str(result[key]) for key in ("failure_code", "error")
+                    if result.get(key)) or "held_route_unavailable"
```
- [eval] [fix] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py` L1029-L1058：一个参数化回归覆盖四种失败响应，实际调用生产 prepare_held，断言状态不可用且未授权运动。 / One parametrized regression exercises production prepare_held across four failure response shapes and asserts unavailable status with no motion authorization. (local)
```diff
+({"status": "unavailable", "failure_code": "pour_route_unavailable",
+  "error": "clearance=0.08: inverse_kinematics_failed; yaw=0.2: route_collision"},
+ "pour_route_unavailable: clearance=0.08: inverse_kinematics_failed; yaw=0.2: route_collision")
+assert result == {"status": "unavailable", "motion_authorized": False, "error": expected_error}
```
- [docs] [chore] `CHANGELOG.md` L9 新增 Archive，L53 起同步本版本与 v17.6.29/.28/.27/.26 的完整月档内容；索引行号会随本条实测记录补齐而滚动。 / Add the archive link at L9 and synchronize this entry plus the four preceding version entries from L53 onward; index line numbers move as measurements are completed. (local)

### 已执行验证 / Completed Validation（无动作 / No motion）
- [eval] [chore] `PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py -q` → **28 passed**（插件禁用产生既有 asyncio_mode 配置警告）。 / The complete PAOS integration file passes 28 tests; plugin disabling emits the existing asyncio_mode configuration warning. (local)
- [eval] [chore] `.venv/bin/python -m ruff check examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py` 与 `git diff --check` 通过。 / Ruff on the changed Python files and diff whitespace checks pass. (local)
- [eval] [exp] pxr 无运动组合验证通过：覆盖层旧臂 inactive 且遍历无其子树，原 USD 旧臂仍 active 且有 11 个 CollisionAPI；profile.validate_paths() 通过；station 与现行配置仅位置文本一行差异；新旧 profile 除 profile/config/scene 路径外各 dataclass 字段完全相等。 / A no-motion pxr check confirms old-arm inactivity and subtree exclusion while the source retains its active arm and 11 colliders; profile paths validate, the station differs by one position line, and profile fields otherwise match exactly. (local)
- [eval] [chore] 首次组合验证脚本导入 OmegaConf 时因主 venv 未安装而停止；后续验证移除该无必要依赖，用精确文本比较通过，未把首次记为通过。 / The first composition script stopped because OmegaConf is absent from the main venv; the corrected check uses exact text comparison and passes without that unnecessary dependency. (local)

### 真实无运动初始化证据 / Actual No-Motion Initialization Evidence
- [env] [exp] Isaac 新场景初始化读回：`/World/Ridgebase` 底盘世界坐标 `[-1.04999995, 0.180000007, 0.0099999998]`m，臂基 `[-0.75402671, 0.18063676, 0.28999999]`m；`old_franka_active=false`、`active_legacy_colliders=[]`、`home_collision_check=passed`、`status=initialized`。证据：`out/labutopia-placement-20261119-1847/no-motion.json`，scene revision `labutopia-tabletop-rod-rack-v1:45be9393627949ea9432e094d45fce83:0`。 / Fresh Isaac initialization reads the deployed base at `[-1.04999995, 0.180000007, 0.0099999998]`m and the arm base at `[-0.75402671, 0.18063676, 0.28999999]`m, with the old arm inactive, no active legacy colliders, a passed home collision check, and initialized status. The JSON evidence carries the stated fresh scene revision. (local)
- [eval] [docs] 上述证据证明 frame、初始状态和 home 碰撞检查通过；它属于 Provider 初始化证据，不证明完整倾倒路线或执行成功。 / These Provider initialization measurements establish the frame, initial state and home collision check; they do not establish full pour-route availability or execution success. (local)
- [docs] [chore] 主会话实现复核目前未发现 Blocker/Major；场景与配置保留在 Adapter 部署层，公共界面未改，现有碰撞资格检查与接触阈值继续适用。 / The primary implementation review currently finds no Blocker/Major issue; scene and configuration remain Adapter deployment concerns, public interfaces stay unchanged, and existing collision qualification and contact thresholds apply. (local)

### A/B 失败终态 / A/B Failed Terminal Outcomes
- [eval] [exp] A（仅移除旧臂）任务 `task_5e60fae54b2f41ba` 已失败终态，`metadata.returncode=1`；28/28 approach probes available，acquire succeeded，总1791采样、108个lift采样，attach峰值 `0.009680901646895916m`。视频 `A-remove-only/artifacts/labutopia/phase-video/752e43f86efa4f94bf9b96a28c4fb223.mp4`，反馈 `phase-feedback/50b86ddbee92461aaffdb57cc101399d.json`，根目录为 `out/labutopia-placement-20261119-1847/`。 / Run A terminates failed with return code1 after 28/28 available approach probes and a successful acquire; 1791 total samples include 108 lift samples with the stated peak attach error. Video and feedback are retained under the stated run root. (local)
- [eval] [exp] A的24条held pour候选全部拒绝，22条明确 `panda_link2 overlaps /World/table/surface/mesh`，余2条仅 `transport` 未细分，不确诊为关节限位；终态仍holding，未执行pour/place。完整详情见A的 `placement-summary.json` 与 `acceptance.json`。 / All 24 held-pour candidates fail, 22 explicitly naming link2/table collision and two retaining only the transport stage without a confirmed joint-limit diagnosis. The arm remains holding; pour/place do not execute. Full details are saved in the run summary and acceptance record. (local)
- [eval] [docs] A实际候选后缀−0，轴向π、切向+0.06m；run24f轴向π/2、切向−0.06m，因此不声称相同轨迹或逐位重放。移除旧臂不足以恢复倾倒，旧臂存在及路线选择影响成立，但不能仅由A唯一归因run24f为旧臂或距离问题。 / A uses candidate suffix−0 with axial branchπ and tangent+0.06m, while run24f used axial branchπ/2 and tangent−0.06m; these are not identical trajectories. Removal alone does not restore pouring, and A cannot uniquely attribute all of run24f's failure to the old arm or distance. (local)
- [eval] [exp] B目录 `out/labutopia-placement-20261119-1847/B-remove-and-near/`，底盘 `[-1.05,.18,.01]`，任务 `task_7b3ca51a7ec34239` 于19:03:58至19:16:12执行后失败，returncode=1。28/28 approach probes available，acquire因 `grasp_object_displaced: object moved before a qualified lift` 失败；1248反馈记录（含异常结束重复record），lift/grasp_valid/contact_load_valid均为0，倾倒准备/pour/place未到达，returned_to_safe_pose与observation_ready均为false。 / B runs between the stated times and terminates failed with return code1. All 28 approach probes are available, but acquire fails before a qualified lift. Its 1248 feedback records include a repeated exception-ending record; lift and qualified grip/load counts are zero, pour preparation/pour/place never execute, and safe-pose return and observation readiness are false. (local)
- [eval] [exp] B末帧以生产 `grasp_anchor_drift` / `grasp_pose_errors` 重算，锚点漂移 `0.007132053241597708m≤0.008m`，物体完整旋转 `0.08129748240811713rad>0.08rad`；R05不在axial_grip_paths，无轴对称豁免。该旋转不是attachment_rotation_error_rad=0.08183650103083709；左右冲量 `[0,0.010030197765445337]N·s`，双侧负载无效。 / Production helper recomputation puts anchor drift inside its position tolerance but full object rotation beyond the existing angular tolerance, with no R05 axial-symmetry exemption. This is distinct from attachment rotation error; the stated unilateral impulse does not satisfy bilateral load. (local)
- [eval] [exp] B视频 `artifacts/labutopia/phase-video/a49242a7d8c74e58ac62bd1275c1ba33.mp4`（20.783333秒、1247帧、3840×960），反馈 `artifacts/labutopia/phase-feedback/b152d2bf3e3943bd8b40376f173538bb.json`；摘要见本轮placement-summary.json。B保存的motion/physics/perception配置与执行后仓库配置逐字节一致，故阈值重算适用。 / B retains the stated video and feedback plus the complete run summary. Saved motion, physics and perception configurations match the repository versions after execution byte for byte, supporting the tolerance recomputation. (local)
- [eval] [docs] B候选−0、轴向π、切向+0.06m与A同分支，但底盘改变IK/接触实现。移除旧臂不足以恢复倾倒；A的22/24条指向link2撞桌，B先抓取失败，尚不能判定新位置倾倒可达性，也不能归结为只因距离。后续应先检查新位置双指对称接触/瓶体旋转并测量桌面及低臂基的无动作路线；本轮不继续前移或调阈值。 / B shares A's candidate branch, while placement changes IK/contact. Removal alone is insufficient; A names link2/table collision in22/24 candidates, and B fails before testing pour reachability. Follow-up should inspect grip symmetry/rotation and no-motion routes against the table and low arm base, without further position or threshold changes in this task. (local)
- [docs] [docs] A/B视频右侧固定标签视图沿用profile的R01检查视角，实际assignment与phase-feedback均为R05；本轮不改摄像头。 / A/B videos retain the profile's fixed R01 inspection pane; assignments and phase feedback identify the actual R05 target. Camera configuration is unchanged. (local)
- [docs] [docs] [新增 / Added] `docs/forge/LABUTOPIA_RIDGEBASE_PLACEMENT_20261119.md` L1-L118：双语记录A/B失败终态、部署与坐标、完整复现命令、外部资产快照、元数据和因果边界；runner未配置显式seed，不声称确定性。 / Add the bilingual deployment report with both failed terminal outcomes, frame assumptions, exact reproduction commands, external-asset snapshots, metadata and causal limits; no explicit seed is configured and determinism is not claimed. (local)
```diff
+ A: acquire succeeded; 24 pour candidates rejected, 22 link2/table collisions.
+ B: acquire failed before lift; object rotation 0.0812974824rad > 0.08rad.
+ External scene/config/robot snapshots preserve pre-existing LabUtopia edits.
+ Evidence: fresh reset/revision, saved instruction/profile/config/metadata/diff.
```

### 外部资产保存 / External Asset Preservation
- [data] [chore] LabUtopia基础提交 `2224bb815fedeff91f82021ec661761682f99310`，源scene/config在本轮前已有本地修改。本轮未改外部源资产；实际scene/config/robot、tracked-assets.diff及metadata保存在 `out/labutopia-placement-20261119-1847/external-scene-snapshot/`，A/B metadata均包含外部证据指针。 / The external LabUtopia base revision has pre-existing local scene/config edits. This task preserves those sources and records actual scene/config/robot files, tracked diff and metadata in the external snapshot, referenced by both runs. (local)

### Git 提交 / Git Commit
- Implementation commit / 实现提交：`70373035`（完整 / full：`70373035f9bfeb02e107a6b4638b1a5d00ef5b3f`）。
- Branch / 分支：`feature/planning-loop`。
- 时间 / Time：2026-11-19 19:24:39 Asia/Shanghai。
- [docs] [chore] 上述hash标识本版本实现提交；后续收据记录提交不自引用。 / The hash identifies this version's implementation commit; the subsequent receipt commit does not self-reference. (local)
