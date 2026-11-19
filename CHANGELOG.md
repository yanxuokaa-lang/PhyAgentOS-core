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

## v17.8.0 (2026-11-19 20:00) - codex

### 实施范围 / Implementation Scope [完成]
- [env] [tune] 仅调整机器人安装高度与位置；桌面物品、操作区及安全阈值保持原值。先依据桌面几何、生产 URDF 与实际抓取/倾倒目标计算单一部署，再修改并执行 fresh-reset 仿真。 / Adjust only robot mounting height and placement, retaining tabletop objects, operation area and safety thresholds; derive one deployment from measured table geometry, production URDF and actual grasp/pour targets before editing and fresh-reset simulation. (local)
- [env] [feat] 离线分析支持单一增高布局，已新增 Adapter 私有 USD 安装覆盖层，保持底盘落地、关节一致与增高支柱碰撞检查；不修改 LabUtopia 原始资产或公共接口。 / Offline analysis supports one elevated layout; add the Adapter-private elevated USD deployment with grounded chassis, coherent joints and pedestal collision checks, preserving original LabUtopia assets and public interfaces. (local)
- [eval] [exp] 已保存计算、无运动验证、终态反馈及视频到独立输出目录，补全精确Diff/行号及索引；实际Git提交/推送由主会话后续补收据。 / Preserve calculations, no-motion validation, terminal feedback and video in a separate output directory and complete exact diffs/lines and the index; the primary records actual Git receipts after performing those actions. (local)

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
- [docs] [docs] 更新本版本报告至实际C失败终态；月档仅修改v17.8.0条目并完整同步CHANGELOG最新五版本，历史版本内容保留。全文UTF-8及diff检查按本轮文档修改复核；代码测试沿用已通过194项，本次docs-only不重跑。实际Git hash与推送结果待主会话执行后记录。 / Finalize the report with C's actual failed terminal outcome, update only the current version and synchronize the complete latest five, preserving prior version contents. Validate UTF-8 and diff formatting for these documentation changes, retain the prior194-test evidence without rerunning code tests, and await actual Git receipts. (local)

- [env] [fix] [完成] 提交前`git diff --cached --check`发现新USD L97为多余EOF空行；此前普通`git diff --check`未覆盖该untracked文件，不能声称旧检查已验证它。仅删除末尾多余空行（rstrip()+换行），USD范围由L1-L97修正为L1-L96，并同步月档与索引。 / Pre-commit staged checking finds an extra EOF blank line at new USD L97; earlier ordinary diff checks did not cover this untracked file. Remove only the extra final blank line and correct the recorded range toL1-L96 in the archive and index. (local)
- [eval] [chore] 精确stage上述USD、月档与CHANGELOG后，`git diff --cached --check`通过；USD现为96行，仅移除最后空白行，其他staged文件未修改。 / Staged whitespace validation passes after adding exactly the USD, archive and index; the96-line USD differs only by removal of its final blank line, and other staged files are untouched. (local)

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

## v17.6.29 (2026-11-19) - claude

### 完成范围 / Scope
- run24e 死因闭环(跨 revision 过程特征管道):acquire 使场景前进后,绑定会自动刷新而 planner 选定的瓶口/烧杯口特征引用冻在旧 revision——pour 的 held 准备在 simulator-truth 链上永远拿不到当前特征(records 的 features=None,只有候选列表),run24e 成为全链历史第一次走到 pour prepare_held 即死。修复三件:① RuntimeSubtaskDriver 的 revision 刷新块对带过程特征的 pour/stir 子任务**重查重选**——同 planner 同构地跑 manipulation.process_features(propose)→按角色确定性选(pour:源 pour_lip rim+目的 rim 各一;stir:endpoint_a/b+目的 rim,首个可用者胜,同抓取候选"第一个可用即胜"原则)→manipulation.prepare_process_features(validate_selection)资格化→更新 spec 引用;拿不到当前特征即诚实 fail-closed(refresh_perception_before_motion 族)。② held 工具族输入 schema 新增**可选** process_feature_refs/process_feature_candidate_set_ref(不进 required;place/legacy 无特征照旧),刷新后的引用随 prepare_held 请求下行,经 prepared_arguments 回声流入 object.pour 执行;published contracts 同步再生(prepare_held/pour/stir;object.place 合同保持 legacy 形状不动)。③ paos_client.prepare_held 把合并请求的 process_type 透传给 refresh_process,任务条件化的倾倒方向(pour_direction)在刷新后与初始准备同语义存活。 / run24e's death closed (cross-revision process-feature plumbing): after the acquire advances the scene, the binding refreshes itself but the planner-selected rim references stay frozen at the old revision — pour held preparation on the simulator-truth chain can never see current features (record features=None, only candidate lists), and run24e was the first run in chain history to reach pour prepare_held and die there. Three fixes: ① the RuntimeSubtaskDriver revision-refresh block now **re-queries and re-selects** process features for pour/stir subtasks that carry them — the same Query/Preparation pair the planner used: manipulation.process_features (propose), deterministic role selection (pour: one source pour_lip rim plus one destination rim; stir: endpoint_a/b plus the destination rim; first available wins, the same principle as grasp candidates), manipulation.prepare_process_features (validate_selection), then the spec refs update; absent current features fail closed honestly (refresh_perception_before_motion family). ② the held tool family's input schema gains **optional** process_feature_refs/process_feature_candidate_set_ref (not required; place/legacy flows unchanged), so the refreshed refs ride the prepare_held request and, echoed through prepared_arguments, flow into object.pour execution; published contracts regenerated to match (prepare_held/pour/stir; the object.place contract keeps its legacy shape untouched). ③ paos_client.prepare_held passes the merged request's process_type through to refresh_process so the task-conditioned pour direction survives the refresh with the same semantics as the initial preparation.

### File Changes
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py`(刷新块 +_refresh_process_features/_select_process_features;prepare_held 参数注入 spec 特征引用)。`held_manipulation.py`(可选特征属性,不进 required)。`contracts/{manipulation.prepare_held,object.pour,tool.stir}.tool.yaml` 再生。`examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py`(refresh_process 透传 process_type)。测试:`test_subtask_executor.py` +3(revision 前进→prepare_held 收到 :N 引用而非 :0;特征不可用→诚实 refresh_perception_before_motion 且不动 pour;held schema 接受可选特征);`test_phase_pipeline.py` 夹具注册特征 Query/Preparation(生产 pour/stir 必带特征);`runtime_with_subtask_endpoint` 同步。 / subtask_executor.py (refresh block + _refresh_process_features/_select_process_features; prepare_held arguments inject the spec's feature refs); held_manipulation.py (optional feature properties, excluded from required); contracts/{manipulation.prepare_held,object.pour,tool.stir}.tool.yaml regenerated; paos_client.py (refresh_process receives process_type). Tests: +3 in test_subtask_executor.py (revision advance → prepare_held receives :N refs, never :0; features unavailable → honest refresh_perception_before_motion without touching pour; the held schema accepts optional features); test_phase_pipeline.py fixture registers the feature Query/Preparation (production pour/stir always carry features); runtime_with_subtask_endpoint likewise.

### 架构与验证 / Architecture and Validation
- 规范门 598 passed / 2 预存(scene_physics);全技能套件(async 开启)663/666,失败 13 项与 HEAD 基线逐一相同(环境性,worktree 对照验证)。判据 run24f(同 profile 同配置,工作区 out/labutopia-oracle-run24f):acquire 成功后 pour 准备应首次拿到 :1 特征并执行倾倒(对准由其自身尖端/轴门裁决),随后放置/回归;若倾倒物理判负,如实体审。 / Canonical gate 598 passed / 2 pre-existing; full skill suite (async enabled) 663/666 with the 13 failures identical to the HEAD baseline (environmental, verified by worktree comparison). Criteria for run24f (same profile and config, workspace out/labutopia-oracle-run24f): after the acquire succeeds, pour preparation should receive :1 features for the first time and execute the pour (alignment adjudicated by its own tip/axis gates), then placement and return; if the pour physics fails its gates, that fact stands.

## v17.6.28 (2026-11-19) - claude

### 完成范围 / Scope
- 用户裁决 run24d:"一直还夹着没掉 这不就是成功了吗"——attached 段(lift/携带)失持判据改为与 close settle 相同的语义:**只有真实双侧接触丢失才停**;携带中的 mm 级相对滑移是平行爪的物理,只记录不判死。具体:①attached 段逐步门从"接触+变换容差"改为只认接触丢失(support_manifold 瞬态窗口照旧);②终点判(possession="holding" 与 acquire/pour 完成后置条件)同改接触语义(`carried`)。8mm 容差数值与全部冻结不变量零变化——它仍诚实地活着在 lift 入口 grasp_check(一次判)与倾倒尖端/轴误差、放置各自门里;遥测 grasp_valid 保持变换语义如实记录。 / Per the user's ruling on run24d ("it never dropped — that's a success"): the attached-phase (lift/carry) grasp-loss gate now carries the same semantics as the close settle — only a real loss of bilateral contact stops; mm-level relative slip during a carry is parallel-jaw physics, recorded but not fatal. Specifically: ① the per-step attached gate drops its transform bound (contact loss only; the support-manifold transient window unchanged); ② the terminal judgment (possession="holding" and the acquire/pour completion postconditions) moves to the same contact semantics (`carried`). The 8mm tolerance value and every frozen invariant are unchanged — it still lives honestly in the lift-entry grasp check (judged once) and in the pour tip/axis and placement gates; telemetry keeps recording grasp_valid with the transform semantics.

### File Changes
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py`(attached 逐步门改接触键;终点 possession/completed 改 carried)。`tests/test_contact_timing.py` +1(run24d 形态:双指持续带载+携带滑移超容差→跑完,possession=holding,遥测如实记 grasp_valid=False)。 / phase_motion.py (per-step attached gate keyed on contact; terminal possession/completed via carried); +1 test_contact_timing test (the run24d shape: persistent bilateral load with carry slip past the bound runs to completion, possession=holding, telemetry honestly records grasp_valid=False).

### 架构与验证 / Architecture and Validation
- 规范门 595 passed / 2 预存(scene_physics)。判据 run24e(同 profile 同配置,工作区 out/labutopia-oracle-run24e):lift 携带段不再被 8mm 中途杀,链路应首次走完 lift→transport→倾倒→放回;倾倒对准由其自身尖端/轴误差门诚实裁决;若终点 carried 判负(接触真丢)则物理事实如实上报。 / Canonical gate 595 passed / 2 pre-existing. Criteria for run24e (same profile and config, workspace out/labutopia-oracle-run24e): the lift carry is no longer killed mid-way at 8mm, and the chain should complete lift→transport→pour→return for the first time; pour alignment is honestly adjudicated by its own tip/axis gates; if the terminal carried check fails (contact truly lost) the physical fact is reported as-is.

### run24e 判决(2026-11-19 11:53 终态,失败,acquire 历史首次成功)/ run24e verdict (2026-11-19 11:53 terminal, failed, first-ever successful acquire)
- **v17.6.28 全效**:acquire 操作 status=succeeded(全链历史首次)——135 个 lift 采样全部双侧带载,attach 误差峰值 17.5mm(旧 8mm 判据 2.2 倍)运完,物体跟 TCP 71%,终点 possession=holding。机器人首次把 R05 提起并保持在握。 / v17.6.28 fully effective: the acquire operation reports status=succeeded (first time in the chain's history) — all 135 lift samples carry bilateral load, a peak attach error of 17.5mm (2.2× the old bound) is carried through, the object follows the TCP at 71%, and possession=holding at the finish. The robot lifts and holds R05 for the first time.
- **新失败面=倾倒准备的跨 revision 过程特征管道(非物理)**:acquire 使场景 revision :0→:1;refresh_binding 正常重跑完整绑定链(第二轮感知全绿,空中瓶+BEAKER 均被感知),但 subtask spec 的 process_feature_refs 冻结在 :0 证据 → pour 准备 stale 失败,倾倒未执行;agent 诚实 finalize(subtask_failed——replan 路由缺口第三处:subtask_executor._result 对运动后失败不给 replan 建议),机械臂终态仍持瓶。修复方向:pour/stir 子任务在 revision 前进后重查+重选过程特征(与绑定刷新同构)。 / New failure face is the cross-revision process-feature plumbing in pour preparation (not physics): the acquire advanced the scene revision :0→:1; refresh_binding correctly re-ran the full binding chain (second perception wave all green, held bottle and BEAKER both perceived), but the subtask spec's process_feature_refs stay frozen on :0 evidence → pour preparation failed as stale, the pour never executed; the agent honestly finalized (subtask_failed — a third instance of the replan-routing gap: subtask_executor._result gives no replan recommendation for post-motion failures), the arm still holding the bottle. Fix direction: pour/stir subtasks re-query and re-select process features after a revision advance, mirroring the binding refresh.

## v17.6.27 (2026-11-19) - claude

### 完成范围 / Scope
- 行走杠杆 (C) 落地(用户裁决"追深发散即冻结"):hold-follow 的每步 −retain 重冻追深仅在双指**对称推进**(合法锥面退让跟随,v17.6.13 本意)时继续;检出**发散**——一指绝对回退(被顶回 >0.1mm)而另一指推进,即 run24b/c 侧走特征——立即冻结指目标(粘性,贯穿 close+lift),不再喂深。retain 0.002/hold_follow 本体与全部冻结容差零变化——变的是跟随的适用条件。run24c 证明首触即达标(0.22mm),追深是行走唯一驱动,冻结后 settle 误差预计停在 ~1-2mm。 / Walk lever (C) per the user's ruling: the hold-follow -retain re-freeze chase continues only while both fingers advance symmetrically (legitimate taper-recession tracking, the v17.6.13 intent); on divergence — one finger forced back in absolute terms (>0.1mm) while the other advances, the run24b/c lateral-walk signature — the finger target freezes (sticky across close and lift) and stops feeding depth. retain 0.002, hold_follow itself, and every frozen tolerance unchanged — what changes is the chase's applicability condition. run24c proved the first touch already qualifies (0.22mm) and the chase is the walk's only driver; with the freeze the settled error should stop at ~1-2mm.

### File Changes
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py`(循环态 +follow_diverged/last_follow_fingers;closure 块追深分支加发散检测与冻结;attached-motion 跟随分支加 not follow_diverged 守卫)。`tests/test_contact_timing.py` +1(左指绝对回退伪装置:发散后目标恒定不追深,含 lift;断言冻结值=首触实测−retain)。 / phase_motion.py (loop state + follow_diverged/last_follow_fingers; divergence detection and freeze in the closure chase branch; the attached-motion follow gains the not-follow_diverged guard); +1 test_contact_timing test (absolute left-finger retreat fake plant: targets constant after divergence through lift; the frozen value equals first-contact measured minus retain).

### 架构与验证 / Architecture and Validation
- 规范门 594 passed / 2 预存(scene_physics 环境)。判据 run24d(同 profile 同配置,工作区 out/labutopia-oracle-run24d):close 完成 + grasp_check 误差显著缩小(<8mm)→ 进 lift;lift 段 attach 曲线=预期物理下蠕变初测(冻结握持下的残余蠕变率);若残余行走仍越 8mm,settle 判负→(D) 换带升级为主杠杆。 / Canonical gate 594 passed / 2 pre-existing. Criteria for run24d (same profile and config, workspace out/labutopia-oracle-run24d): close completes and the grasp_check error shrinks decisively (<8mm) into lift; the lift attach curve then measures the residual creep under intended physics (frozen grip); if the residual walk still crosses 8mm, the settle judgment fails honestly and (D) band selection becomes the primary lever.

### run24d 判决(2026-11-19 10:42 终态,失败,但双重翻页)/ run24d verdict (2026-11-19 10:42 terminal, failed, but two page-turns
- **(C) 全效,侧走族死亡**:close 完整走完(err 峰 2.24mm),settle 点 grasp_check **1.86mm 通过**(run24c 同点 18.1mm 关节限位),lift 首次进入——预测→路线→抓→闭合→资格核对→提升全链贯通;指目标全程冻结 [0.01633,0.01631](48 个 lift 采样逐帧核对)。 / Lever (C) fully effective, the lateral-walk family is dead: close runs to completion (peak err 2.24mm), the settle-point grasp_check passes at 1.86mm (18.1mm at the joint limit in run24c), and lift is entered for the first time — prediction→route→grasp→closure→qualification→lift all chained; finger targets stay frozen at [0.01633,0.01631] through every one of the 48 lift samples.
- **第二重翻页:残余蠕变=轴向挤出**:物体世界行走 [0.09,0.27,20.49]mm vs TCP [0.06,0.12,28.69]mm(横向仅 0.3mm),瓶沿轴下滑 8.2mm(跟随率 71%),0.78s 内 err 0→8.20mm 触线判 physical_grasp_lost(2639-2641 attached 逐步变换判),双侧接触全程未丢。机制:发散冻结把目标冻在行走中途→右指 3.9mm 稳态位置误差→挤压饱和 20N cap 作用于肩带斜面→轴向射流(run21b 跟随模式小挤压同族 9.85%,本轮 28.6%)。斜带几何是根因;(c) 提距再证死路(~10.5mm/s 时间性)。 / Second page-turn: the residual creep is axial extrusion: object world walk [0.09,0.27,20.49]mm vs TCP [0.06,0.12,28.69]mm (lateral only 0.3mm), the bottle slides down its own axis 8.2mm (71% follow), err 0→8.20mm in 0.78s trips the per-step attached-transform check as physical_grasp_lost, bilateral contact never lost. Mechanism: the divergence freeze froze the targets mid-walk — the right finger sits 3.9mm open of target (squeeze saturated at the 20N cap) pressing the sloped shoulder band, producing an axial jet (the run21b small-squeeze family was 9.85%; saturated squeeze here 28.6%). The sloped band is the root cause; the lift-distance lever (c) is confirmed dead again (~10.5mm/s, time-based).
- **(D) 换带升为主杠杆**:肩带 z0.7700(r18.3)→平坦颈带 z0.792-0.817(r14.0-14.5,|dr/dz|≤0.19,run21b 微观分析估价裕度 ×2.9);实现前先取证 rank 为何在 28/32 合格候选中选中肩带;喇叭缘 0.817-0.827 由既有碰撞资格化诚实裁决。 / (D) band selection becomes the primary lever: shoulder band z0.7700 (r18.3) → flat neck band z0.792-0.817 (r14.0-14.5, |dr/dz|≤0.19, run21b microanalysis rated this direction ×2.9 margin); first a forensic on why the ranker picked the shoulder band among 28/32 qualified candidates; the flared lip at 0.817-0.827 is honestly adjudicated by the existing collision qualification.
