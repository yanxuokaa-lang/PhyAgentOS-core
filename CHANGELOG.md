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

## v17.6.26 (2026-11-19) - claude

### 完成范围 / Scope
- close 瞬态判据语义按用户裁决落地(2026-11-19"这种几个mm的移动没啥问题 之后后面稳定加持住了就可以……你现在杀得太早了";run24b 现场:瓶被双侧实持、grip z 恒定、旋转 ≤0.016rad,却被 hold-follow 深推拖行 7.7mm 撞 8mm 资格线中止):**资格抓取关系核对从 close 每帧挪到 settle 点一次判**(既有 lift 入口 grasp_check,冻结 8mm/0.08rad 零变化);close 瞬态期间唯一停止条件=双侧接触丢失(真失持;physical_grasp_lost 改按 contacts() 判,不再被关系误差染指)与既有碰撞/界限门;displaced 锚点门在双侧接触建立后让位(settle 判接手),approach/grasp/接触前的 close 照旧;stable_frames 改数接触保持帧。容差值零变化——变的是判定时机语义。 / Close-transient gating semantics per the user's ruling (a few mm of settling motion is fine as long as the grip later stabilizes; "you are killing it too early"; run24b died exactly this way — a bilaterally held bottle dragged 7.7mm by the hold-follow squeeze into the frozen 8mm line): the qualified-grasp comparison moves from per-frame during close to a single settled judgment at the existing lift-entry grasp check (frozen 8mm/0.08rad untouched); during the closure transient the only grasp stop is a real loss of bilateral contact (physical_grasp_lost now keyed on contacts(), not the relation-tainted held) plus the existing collision/bound gates; the displaced anchor gate stands down once both pads hold the body (the settled judgment takes over) and stays active for approach/grasp/pre-contact close; stable_frames now counts maintained contact. Zero tolerance-value changes — the change is when the judgment is made.

### File Changes
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py`(displaced 门加"接触建立后让位"条件与注释;closure 块:mid-close mismatch 删除、physical_grasp_lost 改接触键、freeze/stable_frames 改 contacts())。`tests/test_phase_motion.py` +2(横移瞬态存活至 lift 入口判负并留 grasp_check 采样;接触丢失照杀)。`tests/test_contact_timing.py` 旧"错位即停"测试改语义(错位接触闭夹续推、lift 入口一次判负;设 retain 0.002 令生产冻结深度在伪装置可见)。 / phase_motion.py (displaced gate gains a post-contact stand-down; closure block rewritten: mid-close mismatch removed, physical_grasp_lost contact-keyed, freeze/stable_frames on contacts()); +2 phase_motion tests; the old misaligned-contact-stops test rewritten to the settled semantics with retain 0.002 to make the production freeze depth visible in the fake plant.

### 架构与验证 / Architecture and Validation
- 规范门 593 passed / 2 预存(scene_physics 环境)。判据 run24c(同 profile 同配置,工作区 out/labutopia-oracle-run24c):close 存活至完成 + grasp_check——若行走稳定于 8mm 内则进 lift(预期指部物理下蠕变初测,attach 曲线);若 lift 入口判负,经 v17.6.25 路由 replan_with_fresh_perception,agent 重新感知重抓(可换带),即用户裁定的"掉落/失败后重新感知规划"闭环首次在 oracle 线实跑。 / Canonical gate 593 passed / 2 pre-existing (scene_physics env). Criteria for run24c (same profile and config, workspace out/labutopia-oracle-run24c): close survives to completion plus grasp_check — if the walk settles inside 8mm the chain enters lift (the first creep measurement under intended finger physics); if the lift-entry judgment fails, v17.6.25 routes it to replan_with_fresh_perception and the agent re-perceives and re-grasps (possibly on a different band) — the user-ruled drop-recovery loop running live for the first time.
- **run24c 判决(10:15 终态,失败)**:v17.6.26 机械全效——close 走完全程(192 采样/36 接触有效,run24b 死于第 10 个),settle 判一次执行(grasp_check:err 18.10mm、rot 0.0075rad、双侧接触仍在)。**物理翻页:行走无平衡点**——首触完美(err 0.22mm、双指对称 [0.0183,0.0183])后,hold-follow 每步 −2mm 的追深把桥接凸包凸轮变成持续侧拖,误差 0.0002→0.0181 单调走至**关节限位**(右指打满 0.0000、左指被顶到 0.0365,瓶仍被双侧夹持、世界横移 [7.8,15.9]mm)——"后面会夹稳"在此几何下不成立,行走 100% 由接触后追深驱动。recovery 撤退拒绝(瓶仍被夹、接触实测→possession uncertain),agent 诚实一次即停(acquire-unknown-with-contact 无安全撤退路径,recovery_decisions 的 refresh 路由需要 safely_recovered 全条件——独立已知缺口,另档处理)。 / run24c verdict: v17.6.26 mechanically complete — close runs to completion (192 samples / 36 contact-valid vs run24b's death at the tenth) and the settle judgment fires once (grasp_check: err 18.10mm, rot 0.0075rad, bilateral contact held). The physics turns the page: the walk has NO equilibrium — after a perfect first touch (err 0.22mm, symmetric fingers) the hold-follow -2mm-per-step chase turns the bridged-hull cam into a sustained drag, error monotone 0.0002→0.0181 all the way to the joint limit (right finger bottomed at 0.0000, left forced to 0.0365, bottle still held, world walk [7.8,15.9]mm). "It will stabilize" does not hold in this geometry; the walk is 100% driven by the post-contact squeeze chase. Recovery retreat refused (bottle still gripped, contact measured → possession uncertain); the agent honestly stopped after one attempt (acquire-unknown-with-contact has no safe retreat, and recovery_decisions' refresh route requires the full safely_recovered conjunction — a separate known gap, filed separately).
