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

## v17.8.7 (2026-11-21 12:34) - codex

### v17.8.4 transport无动作诊断 / v17.8.4 Transport No-Motion Diagnosis [完成 / Completed]
- [eval] [exp] 1653条transport记录含1条重复终态；1652条动作样本精确对应125个路径点，零基waypoint61/样本1651复现首次姿态修正IK失败。位置残差0.578mm通过现行2mm值，角残差0.022648rad超过现行0.02rad。 / The1653 transport records include one duplicated terminal record; all1652 command samples exactly map to125 route points, reconstructing the first measured-pose correction IK failure at zero-based waypoint61/sample1651. Position residual0.578mm meets the existing2mm value, while angular residual0.022648rad exceeds0.02rad. (local)
- [eval] [exp] transport grasp_valid从样本150（37.718752s）起持续false至末尾；attachment旋转误差从0.080425rad升至0.409201rad，末端物体原点偏移18.659mm，但1653条样本contact_load_valid与contact_manifold_valid均为true。现有Lula在失败目标可求得数值合格且限位内候选，但未做路径碰撞/连续性资格验证。 / Transport grasp_valid remains false from sample150 (37.718752s) through the end; attachment rotation error grows from0.080425rad to0.409201rad, with18.659mm final object-origin offset, while contact_load_valid and contact_manifold_valid remain true across all1653 samples. Existing Lula finds a numerically qualified, in-limit candidate at the failure target, but route collision/continuity qualification remains undone. (local)
- [决策边界 / Decision boundary] 保留现有底盘位置、高度、物品布局和阈值。建议先只读诊断持瓶关系漂移，再决定是否验证Lula候选；没有把候选或路线资格等同真实执行成功，也未授权动作。 / Retain chassis position, height, tabletop layout and thresholds. Recommend a read-only held-object relation-drift diagnosis before deciding whether to qualify the Lula candidate; neither the candidate nor route qualification is treated as execution success, and no motion is authorized. (local)

### 文件变更详情 / File Changes
- [docs] [docs] [修改 / Modified] docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md L37-L63：新增transport对齐、IK残差与Lula候选、先发生的持瓶旋转误差漂移、复现命令和决策分支。 / Add transport accounting, IK residuals and Lula candidate, earlier held-object rotation drift, reproduction command and decision branch.
```diff
+ failure waypoint 61: local IK rotation residual 0.022648rad > 0.02rad.
+ Earlier sample 150: grasp_valid becomes false; contact/load flags remain true through sample 1652.
+ Lula endpoint candidate fits pose/joint limits, but full path and collision checks are unverified.
+ No motion commands; placement and thresholds unchanged; recommend read-only grip-drift diagnosis first.
```
- [docs] [docs] [修改 / Modified] changelog/2026-11_part3.md L612-L647：完成v17.8.7计划，补充失败边界、夹持漂移证据、验证和未决生产选择。 / Complete the v17.8.7 plan with failure boundary, grip-drift evidence, validation and pending production choice.
- [docs] [fix] CHANGELOG.md L53-L78：最近五版本更新为v17.8.7、v17.8.6、v17.8.5、v17.8.4、v17.8.3；更早版本详情留在月档。 / Update latest five to v17.8.7 through v17.8.3; retain earlier details in the monthly archive.

### 验证 / Validation
- [eval] [chore] 诊断脚本py_compile与fresh Isaac无动作运行通过；结果为exact_saved_boundary_accounting、失败点61、1652/1652动作样本消费、motion_commands=0、reset joints/time unchanged。 / Diagnostic py_compile and fresh Isaac no-motion run pass; result is exact_saved_boundary_accounting, failure point61, all1652/1652 command samples consumed, motion_commands=0 and unchanged reset joints/time. (local)
- [eval] [chore] Ridgebase运动源码、配置和部署资产均无差异；git diff --check通过，UTF-8双语文档可正常读取。 / Ridgebase motion source, configuration and deployment assets are unchanged; git diff --check passes and bilingual UTF-8 documents read correctly. (local)

### Git提交与推送 / Git Commit and Push [完成 / Completed]
- 实现提交aead469a854dcdc29feab4bd12577f2669c17c39与回执提交b06cdc7d9693d00321e70ffb06dbbb0de76835d7均位于feature/planning-loop。 / Implementation commit aead469a854dcdc29feab4bd12577f2669c17c39 and receipt commit b06cdc7d9693d00321e70ffb06dbbb0de76835d7 are on feature/planning-loop.
- git push origin feature/planning-loop成功；git ls-remote于2026-11-21 13:09:32 Asia/Shanghai核验远端指针为b06cdc7d9693d00321e70ffb06dbbb0de76835d7。 / Push succeeded; git ls-remote verified the remote ref at the stated time.
- 最终回执提交a92adcdb7166654ecdc5cdee57d188acd4382289亦已推送；远端由b06cdc7d更新，git ls-remote于2026-11-21 13:13:59 Asia/Shanghai核验。 / Final receipt commit a92adcdb7166654ecdc5cdee57d188acd4382289 was also pushed and verified at the stated time.

## v17.8.6 (2026-11-20 23:50) - codex

### Git回执核对 / Git Receipt Verification [完成 / Completed]
- [docs] [chore] 核验v17.8.4 Ridgebase实现提交`c7c616621832adc0314f967537b2a42ac5500d14`已推送至`feature/planning-loop`；远端从`9495b724`更新，并由`git ls-remote`核实指针为该提交。 / Verify that the v17.8.4 Ridgebase implementation commit was pushed to the stated branch and that `git ls-remote` confirmed the full remote ref. (c7c61662)
- [docs] [fix] 更新v17.8.4/v17.8.5 Git回执并移出索引中的v17.8.1完整副本；v17.8.1详细记录仍保留于`changelog/2026-11_part3.md`。 / Correct the v17.8.4/v17.8.5 Git receipts and remove the v17.8.1 full copy from this index while retaining its detailed monthly archive entry. (local)

### 文件变更详情 / File Changes
- [docs] [fix] [修改 / Modified] `CHANGELOG.md`：加入v17.8.6完整回执，最近五版本改为v17.8.6、v17.8.5、v17.8.4、v17.8.3、v17.8.2；v17.8.1详情已归档至月档。 / Add the full v17.8.6 receipt, set the latest five versions to v17.8.6 through v17.8.2, and leave v17.8.1 details in the monthly archive.
```diff
+## v17.8.6 (2026-11-20 23:50) - codex
-## v17.8.1 (2026-11-19 20:54) - codex
```

### Git提交 / Git Commit
- 实现提交 / Implementation commit：`c7c616621832adc0314f967537b2a42ac5500d14`；2026-11-20 23:44:49 Asia/Shanghai，`feature/planning-loop`。推送成功，远端从`9495b724`更新至`c7c61662`；2026-11-20 23:50 Asia/Shanghai经`git ls-remote`确认远端指针。 / Commit and push succeeded; the verified remote ref is `c7c616621832adc0314f967537b2a42ac5500d14`. (c7c61662)
- 回执提交 / Receipt commit：`756c31db60f409858bbb06815fc9805e3a371886`；2026-11-21 00:12:54 Asia/Shanghai，`feature/planning-loop`。随后推送成功，远端从`c7c61662`更新至`756c31db`；2026-11-21 00:14:27 Asia/Shanghai经`git ls-remote`确认。 / Receipt commit `756c31db60f409858bbb06815fc9805e3a371886` was pushed successfully, advancing the remote from `c7c61662` to `756c31db`; verified at 2026-11-21 00:14:27 Asia/Shanghai. (756c31db)

## v17.8.5 (2026-11-20 23:33) - codex

### 收尾校正 / Closeout Corrections [完成 / Completed]
- [docs] [chore] 核验最近五版本顺序为v17.8.6、v17.8.5、v17.8.4、v17.8.3、v17.8.2；v17.8.1及更早版本保留在月档归档。 / Verify the latest-five sequence as v17.8.6, v17.8.5, v17.8.4, v17.8.3 and v17.8.2; retain v17.8.1 and older versions in the monthly archive. (local)
- [docs] [fix] `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` L91-L95将v17.8.3复现与结果抽取命令标为历史候选命令，避免与当前v17.8.4 fresh终态混用。 / Mark the v17.8.3 reproduction and extraction commands at L91-L95 as historical candidate commands so they are not confused with the current v17.8.4 fresh outcome. (local)
- [chore] [eval] 206项回归通过（5.14s，保留既有`asyncio_mode`警告），`git diff --check`通过；本轮不改运动逻辑或运行产物。 / The206-test regression passes in5.14s with the existing`asyncio_mode` warning, and `git diff --check` passes; no motion logic or run artifacts change in this closeout. (local)

### 文件变更详情 / File Changes
- [docs] [fix] [修改 / Modified] `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` L91-L95：将复现注释从当前C运行改为历史v17.8.3候选复现。 / Change the reproduction comments from current-C wording to historical-v17.8.3-candidate wording.
```diff
-# 复现使用新目录；本次C已执行完毕 / Reproduce in a fresh directory; C is complete:
+# 历史v17.8.3候选复现命令；不代表当前v17.8.4结果 / Historical v17.8.3 candidate reproduction; does not represent the current v17.8.4 result:
```

### Git提交与推送回执 / Git Commit and Push Receipt [完成 / Completed]
- 本收尾记录与v17.8.4实现一并包含于`c7c616621832adc0314f967537b2a42ac5500d14`；推送成功，远端指针已由`git ls-remote`核验。 / This closeout record was included with the v17.8.4 implementation commit; push succeeded and the remote ref was verified. (c7c61662)

## v17.8.4 (2026-11-20 22:15) - codex

### Ridgebase候选布局复核 / Ridgebase Candidate Placement Recheck [完成 / Completed]
- [env] [tune] 基于`results-v3`选定并实现单一候选：底盘由`[-1.12,0.10,0.01]m`调整为`[-1.105,0.04,0.01]m`，臂安装增量由`0.53m`降至`0.48m`，fresh读回臂基约`[-0.805,0.04,0.77]m`；桌面布局和运动/碰撞阈值不变。 / Select and implement one candidate: move the chassis to`[-1.105,0.04,0.01]m`, lower mount elevation to`0.48m`, obtain the stated fresh arm-root readback, and preserve tabletop layout and motion/collision thresholds. (local)
- [eval] [exp] fresh无动作初始化与home碰撞检查通过；125步居中零偏移same-side路线的kinematic/collision/workspace资格检查通过，但完整运行在transport因`inverse_kinematics_failed: measured pour-pose correction is unreachable`失败，未进入process或倾倒保持。 / Fresh initialization and home collision pass; the125-step centered zero-offset same-side route qualifies, but runtime fails in transport with the stated correction-IK error before process or pour hold. (local)
- [决策边界 / Decision boundary] 最终结论为“路线资格检查通过，实际倾倒失败”；停止继续扫描底盘位置或安装高度，下一决策点仅针对transport实测姿态修正的IK残差、seed连续性和失败边界。 / Final conclusion: route qualification passes but actual pouring fails; stop further chassis or mount-height scanning and limit the next decision point to transport correction residuals, seed continuity and the failure boundary. (local)

### 文件变更详情 / File Changes
- [env] [tune] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-station.yaml` L12：`base_position`由`[-1.12,0.10,0.01]`改为`[-1.105,0.04,0.01]`。 / Change the chassis base position to the selected candidate. (local)
```diff
-  base_position: [-1.12, 0.10, 0.01]
+  base_position: [-1.105, 0.04, 0.01]
```
- [env] [tune] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase-elevated.usda` L3,L13-L94：12个臂/手/手指/末端刚体z增量由`0.53m`改为`0.48m`，同步安装关节、柱尺寸、COM与惯量。 / Lower the12 arm/end bodies to`0.48m` and update the mounting joint, column geometry, COM and inertia. (local)
```diff
-  point3f physics:centerOfMass = (0.3, 0, 0.265)
+  point3f physics:centerOfMass = (0.3, 0, 0.24)
-  point3f physics:localPos0 = (0.3, 0, 0.53)
+  point3f physics:localPos0 = (0.3, 0, 0.48)
-  float3 xformOp:scale = (0.12, 0.12, 0.53)
+  float3 xformOp:scale = (0.12, 0.12, 0.48)
```
- [eval] [chore] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_ridgebase_elevated.py` L36,L62-L72：同步0.48m刚体位移、柱z上界0.76、COM/inertia及底盘坐标断言。 / Update the deployment, column-bound, COM/inertia and chassis assertions for the selected candidate. (local)
- [docs] [docs] [修改 / Modified] `docs/forge/LABUTOPIA_RIDGEBASE_ELEVATED_20261119.md` L1-L178：区分v17.8.3历史候选与v17.8.4当前候选，记录fresh读回、125步路线资格、transport失败、视频证据和停止继续扫描的决策边界。 / Distinguish the v17.8.3 historical candidate from the v17.8.4 current candidate and record fresh readback, route qualification, transport failure, videos and the stop-scan decision boundary. (local)

### 验证与证据 / Validation and Evidence
- [eval] [chore] 原回归命令通过**206 passed**，5.12s，保留1项既有`asyncio_mode`配置警告；`git diff --check`通过。 / The focused regression command passes**206 tests** in5.12s with one pre-existing`asyncio_mode` warning; `git diff --check` passes. (local)
- [eval] [exp] `out/labutopia-elevated-20261120/v17.8.4-candidate/no-motion.json`读回底盘`[-1.1050000191,0.0399999991,0.0099999998]m`、臂基`[-0.8049764633,0.0400000103,0.7700000405]m`，home collision passed、motion_commands=0、柱碰撞启用、旧Franka未激活。 / The no-motion evidence records the stated chassis and arm-root positions, a passed home check, zero motion commands, enabled column collision and no active legacy Franka. (local)
- [eval] [exp] readiness`a3079b268c5c4b9fab4aebbdb666279d.json`选择125步居中零偏移same-side路线且三项资格均通过；task`task_724bb801fcf742a5`于2026-11-20 22:31:20至22:50:28以return code1失败，pour反馈1653样本全transport，最大倾角0.590846rad，process/hold/transfer均未完成。 / Readiness selects the125-step centered route with all qualification checks passing; the task fails in the stated window with1653 transport-only samples, maximum tilt0.590846rad and no process/hold/transfer completion. (local)
- [eval] [docs] 证据边界保持为：路线资格通过不等同于实际倾倒成功；当前回执没有失败目标的逐候选执行态IK残差或关节解，因此不继续修改运动逻辑、力配置或位置/高度。 / Preserve the evidence boundary that route qualification is not pour success; receipts lack per-target runtime IK residuals or joint solutions, so motion logic, force configuration and placement/height remain unchanged. (local)

### Git提交与推送回执 / Git Commit and Push Receipt [完成 / Completed]
- 本版本实现与日志包含于`c7c616621832adc0314f967537b2a42ac5500d14`；推送成功并由远端指针核验。 / This version's implementation and log were included in the stated commit; push succeeded and the remote ref was verified. (c7c61662)

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

### 推送回执 / Push Receipt [完成 / Completed]
- [docs] [chore] 报告L152/L154已将push pending措辞更新为成功并由远端核验；当前实现提交、回执提交和本次push结果均已记录。 / Report linesL152/L154 now state the verified successful push; the implementation commit, receipt commit and push result are recorded. (local)
- Push / 推送：`git push origin feature/planning-loop`成功，远端从`b362bd85`更新至`f1df61b9`。
- Remote ref / 远端指针：`f1df61b9571c6f32d31e39edd8325522672fbd2e`（`git ls-remote`核验）。
- [chore] [chore] 推送验证时间：2026-11-20 21:17:43 Asia/Shanghai；未把本地未跟踪`.task/`或`out/`产物加入提交。 / Push verification time: 2026-11-20 21:17:43 Asia/Shanghai; local untracked `.task` and `out` artifacts were not staged. (f1df61b9)

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
