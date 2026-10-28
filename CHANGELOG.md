# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

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

## v16.1.2 (2026-10-28 20:02) - codex

### 变更摘要 / Summary
- [sense] [feat] 增加 `simulator_truth` 感知模式：同一次 Isaac 观测直接使用仿真深度、点云和 authored 标签/过程几何，跳过 SAM2 与 ReMake/DFNet；保留标准 `scene.observe → scene.understand → grasp → binding` 链路。 / Added `simulator_truth` perception: use same-capture Isaac depth, point cloud and authored labels/process geometry, skipping SAM2 and ReMake/DFNet while retaining the standard perception and binding chain.
- [policy] [feat] 保持两个 `pour` 后一个 `stir` 的语义计划顺序与必填参数契约；原子动作仍只消费用户指令参数。 / Retained the two-pour-then-stir semantic ordering and required parameter contracts; atomic actions consume caller-supplied parameters only.
- [env] [feat] 新增 LabUtopia truth manifest，按 R01-R08、BEAKER、GLASS_ROD 标签绑定仿真 prim 与过程特征。 / Added a LabUtopia truth manifest binding R01-R08, BEAKER and GLASS_ROD labels to simulator prims and process features.

### 文件变更详情 / File Change Details
- [新增] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/simulator_truth_perception.py:L1-L86`：校验 manifest，按 authored pose 从同帧相机点云提取对象云；不启动模型 worker。 / Validates the manifest and extracts object clouds from same-frame camera point clouds using authored poses; no model worker is started.
- [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/perception_runtime.py:L18-L56`：按配置选择 model 或 simulator truth；truth 模式不实例化 SAM2/geometry workers，仍复用 GraspNet。 / Selects model or simulator truth by configuration; truth mode does not instantiate SAM2/geometry workers and still reuses GraspNet.
- [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py:L166-L529`：增加 truth understanding、同帧深度/点云 provenance、`simulator_ground_truth` 资格，并允许其进入现有 resolve/held refresh；关闭时兼容空 worker。 / Adds truth understanding, same-capture depth/point-cloud provenance, `simulator_ground_truth` qualification, existing resolve/held-refresh admission, and empty-worker shutdown compatibility.
- [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/profile.py:L65-L194`、`agent_host.py:L89-L104`：增加模式/manifest 配置和不调用 ReMake 的 host guidance。 / Added mode/manifest configuration and host guidance not to invoke ReMake.
- [新增] `examples/forge-adapters/isaacsim_lab/configs/labutopia-simulator-truth.json:L1-L16`；修改两个 LabUtopia 配置文件 `L1-L28`、`L1-L166`。 / Added the truth manifest and updated both LabUtopia configuration files.
- [修改] `tests/test_visual_perception.py:L322-L361`、`tests/test_profile.py:L94-L117`：覆盖 truth 注入不调用 SAM2/ReMake、capture lineage 和 manifest 配置边界。 / Covered worker bypass, capture lineage and manifest configuration boundaries.

### 关键 Diff / Key Diff
```diff
- geometry = WorkerGeometryRecoveryProvider(...)
+ if mode == "simulator_truth":
+     segmentation = geometry = None
+     truth_manifest = load_truth_manifest(manifest_path)
```
```diff
- geometry_qualification != "validated_observation"
+ geometry_qualification not in {"validated_observation", "simulator_ground_truth"}
```

### 验证 / Validation
- `pytest -q ...test_visual_perception.py ...test_profile.py ...test_agent_host.py ...test_semantic_task_creation.py ...test_subtask_executor.py`: `81 passed`。 / Focused suite: `81 passed`.
- `python -m compileall`、`git diff --check`、truth config/manifest load check passed. / Compileall, diff check and truth config/manifest loading passed.
- 未启动 Isaac Sim、未执行机械臂动作；`execute=False` 仍为默认，未宣称液体体积、化学反应或真实硬件成功。 / Isaac Sim and robot motion were not run; `execute=False` remains the default, with no claim of liquid volume, chemistry or hardware success.

### Git 提交 / Git Commit
- Implementation commit: `5ae79fd0`.
- Branch: `feature/planning-loop`; push failed because GitHub port 443 was unreachable after 132.9 s. The local commit remains available for a later push.

## v16.1.1 (2026-10-24 23:10) - codex

### 原计划 / Original Plan [完成执行与诊断 / Implementation and Diagnosis Completed]
- [eval] [exp] 按已批准方案运行原场景 ReMake → 标签理解 → 目标绑定 → GraspNet → prepare/acquire/process/return 的 PAOS Agent 仿真验收；工艺值显式写入本次实验指令，保存每次失败与复测。 / Run the approved original-scene PAOS simulated acceptance through ReMake, label interpretation, binding, GraspNet and manipulation phases; explicitly record experiment parameters and preserve failed attempts.
- [sense] [fix] 修复实际运行暴露的标签多视图关联、观测或动作参数传递问题；领域语义归 workflow，模型和相机机制归 Adapter，任务/取消/结算归现有 Runtime/Coordinator。 / Fix observed label/view association, observation or parameter propagation failures at existing domain/adapter boundaries; retain Runtime/Coordinator lifecycle ownership.
- [eval] [exp] 使用项目 .venv 运行无运动参数变化与失败路径测试，再启动授权的仿真链路；保持已有坐标、碰撞、夹持和结果未知检查。 / Use the project environment for no-motion parameter variation and failure tests before authorized simulation, retaining existing frame, collision, possession and unknown-outcome checks.
- [docs] [docs] 更新原诊断、汇报和验收文档，区分契约、真实模型、准备与实际执行证据，记录配置、命令和 Git 版本。 / Update diagnosis, report and acceptance documentation with distinct contract, model, preparation and execution evidence plus configuration, commands and Git version.

### 预计影响文件 / Planned Files
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/{agent_host,visual_perception,engine,phase_motion}.py`（仅修复复现的问题 / only reproduced issues）
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/observation.py`、`tests/test_observation.py`：先读多路帧再持久化，消除已复现的 PNG/点云写盘延迟对后一路采样时间的污染；各 view 仍保留独立采样时间，真实采样偏差继续由既有 50 ms 规则判断。 / Read all sensor snapshots before persistence so serialization does not delay subsequent samples; retain per-view acquisition times and existing skew checks.
- 23:39 复测仍报 `capture_skew_exceeded`：点云读取/计算延迟同样不是渲染采样时间。拟读取 Isaac 已有 `rendering_frame`，仅在所有相机读取前后稳定、帧编号相同时采用共同采样时刻；不同帧不能伪装成同步，缺少该 API 的现有 Provider 保留独立时刻路径。现有普通时间差检查无法区分 CPU 导出耗时和真实采样差，必须使用相机帧证据修正采样时间语义，不增加 hash 或新公开契约。 / The rerun still exceeded capture skew because point-cloud export latency is not sampling latency. Use existing stable Isaac rendering-frame evidence to timestamp only proven same-frame snapshots together; retain independent times for legacy providers and never report different frames as synchronous. This repairs the existing timing check without adding hashes or public contracts.
- 对应 tests、configs；`out/releases/v16.1.1/`。 / Corresponding tests, configs and run artifacts.
- `out/releases/v16.1.1/query_recorded_grasp.py`：对 Agent 实际读出的 R01 保存观测点云发起 GraspNet 查询，保留原采集身份和模型结果；仅作为历史观测候选诊断，不启动动作或提升几何资格。 / Query GraspNet against the actual Agent-identified R01 saved cloud, retaining capture identity and model output as offline candidate diagnostics only.
- 离线查询脚本允许指定新输出文件，并在模型启动前拒绝覆盖已有结果，以便复测同一保存观测并保留各次候选。 / Allow a new output path for repeated recorded-capture queries and reject existing outputs before model startup, preserving each trial.
- `docs/diagnostics/transparent-model-comparison-20261023.md`、`docs/reports/transparent-model-selection-report-20261024.md`、`docs/forge/labutopia-paos-acceptance.md`、`CHANGELOG.md`。

### 架构与验收 / Architecture and Acceptance
- 通用层仅拥有语义参数/证据引用；相机位姿、像素变换和轨迹机制留在 Adapter，可替换感知实现而不改 Agent/Tool。 / Domain owns semantic parameters and evidence references; camera/pixel/trajectory mechanisms stay in the Adapter and can be replaced without caller changes.
- 每次观测使用当前 scene revision 与 calibration；准备、持有刷新及结算沿既有链路。参数变化测试应能区分不同倾角、保持时间、半径、深度、圈数、时长、方向。 / Preserve current observation revision/calibration through preparation, held refresh and settlement; parameter-variation tests must distinguish each process input.
- 用户已要求按此前方案完成全链路仿真；实验参数取既有配置并显式传入指令，不增加产品默认值。 / The user requested full-chain simulation under the existing plan; experiment values come from existing settings and are explicitly supplied, not introduced as product defaults.


### 实际修改 / Actual Changes [完成 / Completed]
- [sense] [fix] 修复多相机读取中的写盘/点云计算延迟导致的假采样偏差；先复制各路数据，再持久化，Isaac 同帧证据前后稳定时共享采样时刻，保留旧 Provider 的独立时间。 / Separate acquisition snapshots from persistence and use stable Isaac same-frame evidence to avoid counting export latency as capture skew, preserving legacy timestamps.
- [sense] [fix] 标签提示读取边角编号和每行文字，不注入预期身份；首轮漏读 R01，同图复测 3/3 成功，第二、三轮新采集再读出完整标签。 / Read corner identifiers and all legible lines without expected-identity injection; three replay calls and both fresh reruns read the complete R01 label.
- [eval] [exp] 完成三轮启用执行的原场景 Agent 尝试，最终联合查询可用、新鲜度 539 ms，ReMake 全景/近景 0.394/0.102 s；R02 身份、实例关联、功能点和几何资格不足，未创建动作任务，全链路未通过。 / Ran three execution-enabled original-scene Agent attempts; the final joint query was available at 539 ms freshness, with ReMake panorama/close-up inference at 0.394/0.102 s. Identity, association, process features and geometry qualification blocked task creation; full-chain acceptance failed.
- [eval] [exp] 第二轮实际 R01 保存点云运行真实 GraspNet，返回 32 个候选；历史查询不产生当前准备或执行证据。 / Actual GraspNet returned 32 candidates for the second run's recorded R01 cloud; historical replay does not establish current preparation or execution.
- [eval] [exp] 参数变化测试测量瓶口/棒尖轨迹及部署限值，补齐旧 fixture 的必填搅拌方向。最终 6 文件 175 passed；更早 10 文件 250 passed 单独留存。 / Parameter-variation tests measure lip/tip trajectories and deployment bounds; update the old fixture with required stir direction. Final six-file suite: 175 passed; the earlier ten-file 250-pass run is retained separately.
- [docs] [docs] 保存三轮错误、修复对比和阶段结果，区分标签、模型、离线候选、测试和真实执行；同步最近五版本，补存原索引独有 v16.0.6 记录，不改既有归档正文。 / Preserve all failures, fixes and stage outcomes, distinguishing labels, model output, offline candidates, tests and execution. Synchronize the latest five entries and archive the index-only v16.0.6 record without changing existing archive bodies.

### 文件变更详情 / File Change Details

#### [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/observation.py` L8-L11,L187-L277,L297-L318
**修改前 / Before:** 逐相机读取后立即持久化，以逐次 UTC 计算偏差，PNG 保存和点云 getter 耗时污染后一路时间。
**修改后 / After:** 复制所有视图再写盘；读取前后校验 Isaac 帧号/渲染时间，只有全部视图同帧才统一采样时间，异帧与换帧返回不可用。
```diff
- view = self._capture_view(ref)
- views.append(view)
+ snapshot = self._read_view(ref)
+ snapshots.append(snapshot)
+ # After all reads: require stable matching render metadata, then persist.
+ payloads.append((kind, deepcopy(value)))
+ frame_after = _camera_render_metadata(frame_reader)
+ if supports_frame_metadata and (frame_after is None or frame_after != frame_before):
+     return None
```
**说明 / Rationale:** 两轮实际 `capture_skew_exceeded` 证明现有 UTC 差混淆采样和计算；复用已有帧元数据修复语义，不增加公开契约、hash 或新门禁。

#### [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py` L54-L58
```diff
- "Read attached labels literally; use null when unreadable."
+ "Read attached labels literally, including short alphanumeric identifiers at the edges or corners "
+ "and every legible line; preserve line breaks."
+ "Never fill missing characters from expected names or surrounding objects;"
```
提示范围仍为实际可见图像。 / The prompt remains grounded in visible image content.

#### [修改] `examples/forge-adapters/isaacsim_lab/tests/test_observation.py` L2,L34-L48,L120-L386
新增慢 getter 同帧、异帧、读取中换帧、无效/缺失元数据、numpy 有理时间、缓冲快照和旧/混合 Provider 时间兼容用例。 / Cover same-frame slow getters, frame mismatch/change, invalid metadata, NumPy rational times, buffer copies and legacy/mixed-provider timestamps.
```diff
+ assert result["status"] == "unavailable"
+ assert result["error"]["code"] == "capture_skew_exceeded"
+ assert captured_at[1] - captured_at[0] == timedelta(milliseconds=100)
```

#### [修改] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L58-L127
六组半径/深度/圈数/时长 × 双方向及四组倾角/停留，按挂载关系重建实际瓶口或棒尖；检查部署边界。 / Exercise six stir parameter combinations in both directions and four pour settings, reconstructing the lip/tip through attachment transforms and checking deployment bounds.
```diff
- def test_absolute_stir_circle_does_not_accumulate_positions(direction, sign):
+ def test_absolute_stir_circle_does_not_accumulate_positions(direction, sign, radius, depth, turns, duration):
- assert actual[:, 2] == pytest.approx(np.full(len(actual), .84))
+ assert actual[:, 2] == pytest.approx(np.full(len(actual), .88 - depth))
+ assert seconds == pytest.approx(hold + config()["settle_s"])
```

#### [修改] `examples/forge-adapters/isaacsim_lab/tests/test_phase_pipeline.py` L150
```diff
- {"radius_m": .009, "depth_m": .04, "turns": 2., "duration_s": 4.}
+ {"radius_m": .009, "depth_m": .04, "turns": 2., "duration_s": 4., "direction": "ccw"}
```
修复旧 fixture 引发的四项失败，不引入产品默认方向。 / Fix four old-fixture failures without a product default.

#### [新增] `out/releases/v16.1.1/query_recorded_grasp.py` L1-L70
按实际标签匹配唯一保存实体，复用 RecordedGraspProvider 和 GraspNet；接受 `--output`，保留已有结果，明确历史观测查询不执行动作。 / Match a uniquely labelled saved entity and reuse existing providers; allow a new output path and explicitly keep historical replay separate from motion.
```diff
+ request.update(freshness_ms=0, max_age_ms=1000, targets=[...])
+ report = {"scope": "offline GraspNet query; historical capture; no preparation or motion", ...}
+ with destination.open("x", encoding="utf-8") as output:
+     json.dump(report, output, ensure_ascii=False, indent=2)
```
零 freshness 仅相对保存采集时刻，脚本没有引擎/准备/执行入口。 / Zero freshness refers to the historical capture; the script exposes no engine/preparation/execution entry point.

#### [修改] 诊断、报告与验收文档 / Diagnosis, Report and Acceptance
- `docs/diagnostics/transparent-model-comparison-20261023.md` L204-L274：三轮结果、错误原因/修复前后、偏差统计和阶段表。 / Three runs, failure/fix comparisons, depth-change statistics and stage table.
- `docs/reports/transparent-model-selection-report-20261024.md` L126-L164：R01 可读性、动作参数抽象及全链路未通过。 / R01 legibility, parameterized actions and failed full-chain acceptance.
- `docs/forge/labutopia-paos-acceptance.md` L336-L386：参数、失败边界、回归与重跑命令。 / Parameters, blockers and reproducible regression/rerun commands.
- `docs/forge/evidence/remake-label-fullchain-20261024.png`：首轮实际传感器 RGB。 / Actual first-run sensor RGB.
- `out/releases/v16.1.1/`：三轮 acceptance、run-metadata、Agent 会话、运行日志与模型 JSON 中间记录；32 候选、3 次标签回放、回归日志。各文本文件精确范围见本版本 `artifact-index.md`。原始 NPY 数组保留在本地，不把只含文本的 Git checkout 称为可直接模型回放。 / Acceptance, metadata, Agent sessions, runtime logs, intermediate model JSON, 32 candidates, three label replays and validation logs; exact text-file ranges are listed in artifact-index.md. Raw arrays remain local.

### 验证 / Validation
- 最终 6 文件 175 passed / Final six-file suite: 175 passed. 命令 / command: `docs/forge/labutopia-paos-acceptance.md:L363-L371`；输出 / output: `out/releases/v16.1.1/validation-final.log`。
- Ruff 检查五个变更 Python 文件及离线脚本通过。 / Ruff passed for the five changed Python files and replay script.
- 脚本 `--help` 正常；已有输出在模型启动前报 FileExistsError，原结果保留。 / Help succeeds; existing output is rejected before model startup and preserved.
- 第三轮观察摘要为 available、539 ms，但原始同步时间缺失；不能把 Agent 请求填入的 0 当作实测偏差。 / Final observation summary is available at 539 ms, but original synchronization timestamps are missing; request-supplied zero skew is not a measurement.
- 第三轮 `tasks=[]`、`controller_outcomes=[]`、退出码 1；无抓取/倾倒/搅拌/归位执行，DFNet 同场景对照仍未完成。 / Final run: no tasks or controller outcomes, exit code 1; no manipulation execution and no completed DFNet comparison.
- 独立实现复核未发现本次变更新的 Blocker/Major；当前感知/几何能力不足仍阻断实际动作验收。 / Independent review found no new Blocker/Major in these changes; perception/geometry capability still blocks live simulated manipulation.

### Git 提交 / Git Commit
- Commit: `37d42d17`（实现、文档与验收证据 / implementation, docs and evidence）。
- Branch: `feature/planning-loop`；推送目标 / push target: `origin/feature/planning-loop`。
- 回执时间 / receipt time: 2026-10-25 00:04 Asia/Shanghai；本条随独立日志回执提交保存。 / Recorded in a separate log-receipt commit.
- 历史五提交 `cd23c1ed..cd885ed4` 已推送原分支；本次不包含既有 robotwin20 worker/依赖及其他无关工作区修改。 / Five preceding commits were pushed to the same branch; unrelated worker/dependency and workspace edits are excluded.

## v16.1.0 (2026-10-24 21:08) - codex

### 变更摘要 / Summary [完成 / Completed]
- [sense] [feat] 为 LabUtopia 增加可配置的静态标签检查观察相机，并沿既有 `scene.observe → scene.understand` 接入 ReMake；相机配置仅在 Adapter/配置层生效，不驱动机械臂。 / Add a configurable static label-inspection camera for LabUtopia and route it through the existing `scene.observe → scene.understand` ReMake path; keep camera configuration in the Adapter/config layer and do not move the arm.
- [eval] [exp] 使用该近景相机重新发起只读 Agent 标签检查，记录 RGB-D、ReMake、understanding 和 task settlement 证据；另运行已有 pour/stir 契约测试，禁止执行工艺动作。 / Relaunch a read-only Agent label inspection through the close-up camera and record RGB-D, ReMake, understanding, and task settlement evidence; run existing pour/stir contract tests without executing process actions.
- [docs] [docs] 更新诊断与汇报，分别说明标签可读性实测和动作参数契约验证范围，不把视觉检查或测试写成动作运行验收。 / Update the diagnosis and report with the measured label-legibility result and action-contract validation scope, without presenting visual inspection/tests as motion acceptance.

### 预计影响文件 / Planned Files
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/profile.py`
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py`
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json`
- `examples/forge-adapters/isaacsim_lab/tests/test_profile.py`
- `examples/forge-adapters/isaacsim_lab/tests/test_engine.py`
- `docs/diagnostics/transparent-model-comparison-20261023.md`
- `docs/reports/transparent-model-selection-report-20261024.md`
- `out/releases/v16.1.0/agent-label-closeup-20261024/`
- `out/releases/v16.1.0/agent-label-closeup-r2-20261024/`
- `CHANGELOG.md`

### 实际修改记录 / Actual Changes
- [sense] [feat] `profile.py` 和 `labutopia-mixture.json` 增加 R01 检查 prim 与焦距配置；`engine.py` 从场景 inspection 属性定位虚拟静态相机并注册到既有 RGB-D/点云观察源。 / Added configurable R01 inspection prim and focal length; the Adapter reads authored inspection attributes and registers a virtual static camera in the existing RGB-D/point-cloud observation source.
- [eval] [exp] 第二次 Agent 运行成功识别六行标签文本；同次 ReMake CUDA 推理 0.430 s，输出 1280×960 恢复深度；首轮失败和焦距调整均保存在两个独立运行目录。 / The second Agent run read all six label lines; ReMake CUDA inference took 0.430 s and produced 1280x960 recovered depth. First-run failure and focal-length adjustment remain in separate run directories.
- [docs] [docs] 诊断及汇报补充依赖缺失/修复、标签结果、遮挡/视野限制、ReMake artifact 与参数动作测试范围。 / Updated diagnosis and report with the missing dependency and fix, label result, view limits, ReMake artifacts, and action-contract test scope.

### 文件变更详情 / File Change Details

#### [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/profile.py`
**修改前：** 配置没有标签检查观察目标和焦距字段。 / No configurable label-inspection target or focal length.
**修改后：** `L68-L69,L139-L142` 增加 `label_inspection_prim_path`、`label_inspection_focal_length_mm`，复用现有 `/World` 路径和正数校验。 / Added target-prim and focal-length settings with existing `/World` path and positive-number validation.

#### [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py`
**修改前：** 仅注册第三人称与腕部相机。 / Registered only third-person and wrist cameras.
**修改后：** `L916-L920,L997-L1032,L2308-L2343` 按 profile 为 R01 建立静态 inspection 相机；从 USD authored eye/target 属性计算相机朝向，沿原 observation source 输出 RGB、depth、point cloud。 / Adds a static R01 inspection camera from profile settings and authored eye/target attributes, using the existing RGB/depth/point-cloud source.

**关键 Diff：**
```diff
- cfg = _observation_scene_config(OmegaConf.load(str(self.profile.config_path)))
+ cfg = _observation_scene_config(
+     OmegaConf.load(str(self.profile.config_path)),
+     label_inspection_prim_path=self.profile.label_inspection_prim_path,
+     label_inspection_focal_length_mm=self.profile.label_inspection_focal_length_mm,
+ )
```

#### [修改] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json:L10-L11`、`tests/test_profile.py:L72-L92`、`tests/test_engine.py:L1033-L1038`
增加 R01 路径及 3.5 mm 焦距配置；覆盖配置校验、相机投影。 / Added R01 path and 3.5 mm focal length; tests cover profile validation and camera projection.

#### [修改] `docs/diagnostics/transparent-model-comparison-20261023.md`、`docs/reports/transparent-model-selection-report-20261024.md`
**修改前：** 标签识别仅有人眼近景预览，Agent 标签读取待复测。 / Label evidence was limited to human-readable viewport preview; Agent recognition remained pending.
**修改后：** 加入 Agent 真实传感器帧、ReMake 结果、首轮 PIL 失败及修复、无任务/无运动边界。 / Added actual Agent sensor-frame results, ReMake output, initial PIL failure and fix, and no-task/no-motion boundary.

### 验证 / Validation
- `test_profile.py`、`test_engine.py`、`test_agent_host.py` 与 3 个 pour/stir 参数测试：`78 passed`；Ruff 与 `git diff --check` 通过。 / Focused suites: 78 passed; Ruff and `git diff --check` passed.
- Agent 读取标签：`R01`, `LAB REAGENT`, `蒸馏水`, `Distilled water`, `H2O`, `Simulation reagent`；`tasks=[]`、`simulated_motion_enabled=false`。ReMake metadata: CUDA `cuda:0`, 0.430 s, `unverified_estimate`. / Agent read the six label lines; no task or simulated motion. ReMake metadata records CUDA, latency, and estimate status.
- 4 项动作参数契约测试通过；无倾倒、搅拌、抓取候选或机械臂运动运行证据。 / Four action-contract checks passed; no pour, stir, grasp-candidate, or arm-motion run.
- 运行环境 `paos` 补装了已声明依赖 `Pillow 13.0.0`，解决 `No module named PIL`。 / Installed the declared Pillow 13.0.0 dependency in the `paos` environment, fixing the `No module named PIL` provider error.

### Git 提交 / Git Commit
- Implementation: `e6c2e174`; Branch: `feature/planning-loop`; push failed because GitHub port 443 was unreachable. / 实现提交：`e6c2e174`；分支：`feature/planning-loop`；GitHub 443 端口连接失败，推送未完成。

## v16.0.6 (2026-10-24 20:27) - codex

### 变更摘要 / Summary [完成 / Completed]
- [eval] [exp] 同一 LabUtopia 场景完成第三人称全景与静态腕部近景对照；全景标签过小，R01 近景的人眼可读性明显提升。 / Compared third-person panorama with a static wrist close-up in the same LabUtopia scene; labels are too small in panorama while R01 is substantially more legible to a human in close-up.
- [docs] [docs] 诊断和汇报记录标签位置核验、可读字段与识别验证边界；未改仿真资产，未宣称 OCR/Agent 识别通过。 / Recorded label placement inspection, readable fields, and recognition evidence limits; no simulation assets changed and no OCR/Agent success claimed.

### 文件变更详情 / Change Details
- [docs] [docs] `docs/diagnostics/transparent-model-comparison-20261023.md:L148-L169` 加入同场景视角结果与截图；`docs/reports/transparent-model-selection-report-20261024.md:L110-L116` 加入汇报结论。 / Added same-scene viewpoint findings and screenshots to the diagnosis and report.
- [eval] [exp] `out/releases/v16.0.6/label-viewpoint-comparison-20261024/` 保存两张 `950x532` 视口截图及 `run-metadata.json:L1-L28`。 / Saved two 950x532 viewport captures and run metadata.

### 验证 / Validation
- LabUtopia inspect 确认 8/8 标签面存在；third-person 和 wrist-preview 均打开成功，Physics paused、无控制器/运动命令。 / LabUtopia inspection found 8/8 label surfaces; both previews opened with physics paused and no controller/motion commands.
- 人眼可读 R01、蒸馏水、Distilled water、H2O；未运行 OCR、LocateAnything、Agent 或运动。 / R01, 蒸馏水, Distilled water, and H2O are human-readable; no OCR, LocateAnything, Agent, or motion was run.

### 关键 Diff / Key Diff
```diff
- panoramic view: label text too small; recognition unresolved
+ wrist close-up: R01 label fields human-readable
+ keep existing outward label placement; Agent/OCR qualification remains pending
```

### Git 提交 / Git Commit
- Pending.

## v16.0.5 (2026-10-24 19:57) - codex

### 预期修改 / Planned Changes [计划 / Planned]
- [policy] [fix] 对齐 `pour` / `stir` 子任务参数契约与 held-operation Schema，支持搅拌方向，禁止缺少动作参数的子任务进入 acquire/process 流程。 / Align `pour` / `stir` subtask parameters with the held-operation schema, support stir direction, and prevent subtasks missing process parameters from entering acquire/process.
- [policy] [fix] 修正 Agent 指引的操作名，使其匹配真实 `semantic_subtasks` 接口；更新契约、Agent Host 与 Runtime 测试。 / Correct Agent guidance operation names to match the actual `semantic_subtasks` interface; update contract, Agent Host, and Runtime tests.
- [policy] [refactor] 在 workflow 领域层定义可复用的 pour/stir 参数契约，让任务创建、复合子任务和 held-operation ToolSpec 使用同一必需字段及方向枚举。 / Define a reusable pour/stir parameter contract in the workflow domain layer so task creation, composite subtasks, and held-operation ToolSpecs share required fields and direction values.
- [docs] [docs] 将标签观测限制、动作契约缺陷、修复内容与验证边界追加到既有诊断和汇报；标签仍需更适合的近景/多视角观测，不将未执行采集写成已修复。 / Append label-observation limits, action-contract defects, fixes, and validation boundaries to the existing diagnosis and report; retain close-up/multi-view capture as pending rather than claiming an unrun capture was fixed.

### 预计影响文件 / Planned Files
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py`
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/semantic_task_creation.py`
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/operation_parameters.py`
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/held_manipulation.py`
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py`
- `examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py`
- `examples/forge-skills/pick-place-workflow/tests/test_semantic_task_creation.py`
- `examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py`
- `examples/forge-skills/pick-place-workflow/tests/test_held_manipulation.py`
- `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare_held.tool.yaml`
- `examples/forge-skills/pick-place-workflow/contracts/object.pour.tool.yaml`
- `examples/forge-skills/pick-place-workflow/contracts/tool.stir.tool.yaml`
- `examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py`
- `docs/diagnostics/transparent-model-comparison-20261023.md`
- `docs/reports/transparent-model-selection-report-20261024.md`
- `CHANGELOG.md`

### 实际修改 / Actual Changes [完成 / Completed]
- [policy] [refactor] `operation_parameters.py:L1-L48` 新增统一的 provider-neutral pour/stir 参数属性、Schema 生成与有限数值验证；stir 的 `direction` 为必需 `cw`/`ccw`。 / Added shared provider-neutral pour/stir parameter properties, schema generation, and finite-value validation; stir requires `direction` in `cw`/`ccw`.
- [policy] [fix] `semantic_task_creation.py:L31-L74,L97-L104` 与 `subtask_executor.py:L279-L303,L1113-L1206` 在语义任务创建及复合动作契约阶段校验完整参数；缺参/非法值在 Query、acquire 前失败。 / Validate complete values at semantic task creation and composite-action contract stages; missing/invalid values fail before Queries or acquire.
- [policy] [fix] `held_manipulation.py:L21-L35,L182-L185` 让 held operation 与 legacy cycle ToolSpec 共用动作参数；三个发布 YAML ToolSpec 同步 `direction` 字段。 / Reused the shared parameters in held-operation and legacy-cycle ToolSpecs; synchronized `direction` into all three published YAML ToolSpecs.
- [policy] [fix] `agent_host.py:L88-L103` 指引改为真实 `pour` / `stir` operation，并说明内部 `object.pour` / `tool.stir`、必需字段及缺参先询问；测试在 `test_agent_host.py:L47-L57`。 / Updated guidance to actual `pour` / `stir` operations, internal tools, required fields, and ask-before-task behavior; tested in `test_agent_host.py:L47-L57`.
- [test] [test] `test_semantic_task_creation.py:L198-L217`、`test_subtask_executor.py:L472-L501` 覆盖缺少/非法方向在感知前拒绝、方向进入 held preparation、缺少 pour 参数拒绝。 / Cover pre-perception rejection of missing/invalid stir direction, direction projection into held preparation, and missing pour parameter rejection.
- [docs] [docs] `transparent-model-comparison-20261023.md:L145-L174` 和 `transparent-model-selection-report-20261024.md:L96-L108` 更正先前过宽的参数化结论，记录标签成像瓶颈、建议采集流程、修复前后契约和未执行运动的证据边界。 / Corrected the earlier overbroad parameterization claim and recorded label-imaging limits, capture recommendations, before/after contracts, and no-motion evidence boundary.

### 关键 Diff / Key Diff
```diff
- Agent operation names: pour_cycle / stir_cycle; held stir schema omitted direction
+ Agent operation names: pour / stir; matching internal object.pour / tool.stir
+ Shared required parameter schemas; stir direction: required enum [cw, ccw]
+ Validate semantic request and SubtaskSpec before any internal Tool/action
```

### 验证 / Validation
- 定向测试：`88 passed`（SubtaskExecutor、held manipulation、semantic task creation、agent planning、Agent Host）。 / Focused tests: `88 passed`.
- `.venv/bin/ruff check` 与 `git diff --check` 通过。 / Passed.
- 标签复拍待办：无相机移动或新采集；未声称标签已改善。未执行倾倒/搅拌/机械臂运动。 / Label recapture remains pending; no camera motion/new capture and no claim of improved legibility. No pour, stir, or arm motion was run.

### Git 提交 / Git Commit
- Commits: `0c322042` (implementation), `5ae98a21` (log receipt); Branch: `feature/planning-loop`. Push failed twice with a TLS connection termination (`GnuTLS recv error (-110)`); remote was not updated and branch is ahead by two commits. / 两次 push 均因 TLS 连接提前终止失败；远端未更新，本地分支 ahead 2。

## v16.0.4 (2026-10-24 18:20) - codex

### 变更摘要 / Summary [完成 / Completed]
- [policy] [fix] Agent Host 将倾倒/搅拌表达为通用 `pour_cycle` / `stir_cycle` 子任务，从任务 `parameters` 传值；删除固定瓶数、流程顺序和工艺默认值指引。 / Agent Host expresses pouring/stirring as generic `pour_cycle` / `stir_cycle` subtasks, forwards task `parameters`, and removes fixed bottle counts, operation order, and process defaults.
- [sense] [fix] 将结构化视觉输出预算从 2048 提高至 4096，并在 JSON 解码失败 artifact 中保存有界响应摘录和解析位置；实测根因为八目标响应被截断。 / Raised structured-vision output budget from 2048 to 4096 and recorded bounded response excerpts and parse positions on JSON decode failure; run evidence showed truncation of the eight-object response.
- [eval] [exp] ReMake 同场景只读 Agent 检查成功结算；八个锥形试剂瓶标签不可可靠读取，身份未解析；未启用运动。 / The read-only ReMake Agent inspection settled successfully in the same scene; labels on eight conical reagent bottles were unreadable and identities unresolved; motion remained disabled.
- [docs] [docs] 更新透明材质诊断和汇报，加入失败原因/修复对比、标签结论、参数动作验证边界及运行产物。 / Updated the transparent-material diagnosis and report with failure cause/fix comparison, label findings, parameterized-action validation boundary, and run artifacts.

### 影响文件 / Affected Files
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py`
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py`
- `examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py`
- `examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py`
- `docs/diagnostics/transparent-model-comparison-20261023.md`
- `docs/reports/transparent-model-selection-report-20261024.md`
- `out/releases/v16.0.4/agent-label-qualification-final/`
- `out/releases/v16.0.4/agent-label-qualification-token-budget/`

### 文件变更详情 / File Change Details

#### [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py:L88-L103`
**修改前：** 指引固定两次倾倒再搅拌，并给倾倒/搅拌写入部署默认数值。 / Guidance fixed a two-pour-then-stir sequence and deployment-default process values.
**修改后：** 组合通用 `pour_cycle` / `stir_cycle`，参数来自各子任务 `parameters`；不固定数量、顺序或数值，参数不足时先询问。 / Compose generic `pour_cycle` / `stir_cycle` actions with values from each subtask's `parameters`; do not fix count, order, or values, and ask when required parameters are absent.

```diff
- Default pour parameters: tilt_rad=1.3, hold_s=1.0.
- Default stir parameters: radius_m=0.009, depth_m=0.04, turns=2.0, duration_s=4.0.
+ Pass each requested operation's values in that subtask's parameters object.
+ Do not hard-code a bottle count, operation sequence, or numeric process values.
```

#### [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py:L23-L27,L71-L84,L197-L204`
**修改前：** 视觉响应上限为 2048 tokens；JSON 解析错误只记录错误类型和消息。 / Vision responses were limited to 2048 tokens; JSON parse failures retained only the error type and message.
**修改后：** 默认上限为 4096 tokens（构造参数可覆盖）；解码失败时记录有界摘录、输出长度和解析位置，保留 Provider failure 状态。 / Default limit is 4096 tokens (overridable through the constructor); parse failures record a bounded excerpt, output length, and parse location while remaining Provider failures.

#### [修改] Tests
- `examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py:L47-L55` 验证通用动作和缺参处理指引。 / Verifies generic actions and missing-parameter guidance.
- `examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py:L147-L193` 验证输出预算、截断诊断和失败 artifact 持久化。 / Verifies output budget, truncation diagnostics, and failure-artifact persistence.

#### [修改] Diagnostics and Report
- `docs/diagnostics/transparent-model-comparison-20261023.md:L117-L142` 加入运行结果、根因修复表、标签观察及动作测试范围。 / Adds run results, root-cause/fix table, label observations, and action-test scope.
- `docs/reports/transparent-model-selection-report-20261024.md:L79-L96` 加入面向汇报的 Agent 复核结论。 / Adds the Agent review findings for reporting.

### Agent 运行结论 / Agent Run Result
- 首轮失败响应长度为 4060 字符，JSON 解析停在 `line 136, column 31, position 4060`，确认结构化输出被 2048-token 上限截断。 / The first failed response was 4060 characters; JSON parsing stopped at `line 136, column 31, position 4060`, confirming truncation by the 2048-token output limit.
- 提高上限后，`task_1d02787c63b24544` 成功完成 `complete_read_only_inspection`。八个锥形试剂瓶标签仍不可可靠读取；左后方大瓶被机械臂遮挡。 / After increasing the limit, `task_1d02787c63b24544` completed `complete_read_only_inspection`. Labels on eight conical reagent bottles remained unreadable; the large rear-left flask was occluded by the arm.
- 两条此前 provider failure 且没有动作记录的任务已通过 Coordinator `cancel_task` 正常取消；没有直接写 SQLite。 / Two prior provider-failed tasks with no action records were cancelled through Coordinator `cancel_task`; SQLite was not edited directly.
- 没有提供工艺参数，标签/功能点和动作准备也未通过；本轮没有创建倾倒/搅拌节点或执行运动。动作参数验证来自集成测试，不是运行效果证据。 / Process parameters were not provided, and labels/landmarks/preparation were unqualified; no pour/stir nodes or motion were executed. Parameter behavior is supported by integration tests, not runtime action evidence.

### 验证 / Validation
- `61 passed`：视觉 Provider、Agent Host、PAOS 集成和 subtask executor 测试。 / Visual Provider, Agent Host, PAOS integration, and subtask executor tests passed.
- `git diff --check` passed. / Passed.
- Isaac Sim EULA explicitly accepted for observation; simulated motion disabled; no physical hardware connected. / EULA was explicitly accepted for observation; simulated motion was disabled; no physical hardware was connected.

### Git 提交 / Git Commit
- Commit: `b621414a` (implementation), `ba19b43f` (log receipt); Branch: `feature/planning-loop`; pushed to origin. / 提交：`b621414a`（实现）、`ba19b43f`（日志回执）；分支：`feature/planning-loop`；已推送。
