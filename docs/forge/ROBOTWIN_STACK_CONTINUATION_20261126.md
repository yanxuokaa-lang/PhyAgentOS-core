# RoboTwin stack continuation — v18.2.1

状态 / Status（2026-11-27）：已完成观测驱动关系目标与视觉/执行身份映射的生产准备链。当前实测断点是对象掩码边缘混入桌面深度，扩大生产世界点云包络；运动保持关闭。 / Observation-driven relation targets and identity mapping reach production preparation. Measured table-depth contamination at mask edges enlarges the production world-cloud envelope; motion remains disabled.

## 当前实现与所有权 / Implementation and ownership

`ObservedRelationTargetProvider` 由 Adapter 持有，使用当前 scene binding 的一对一视觉→执行映射。`project_relation_goal(...)` 保存原始 benchmark goal/subtask 与来源，只把执行实体投影为当前视觉实体；`task_goal_facts` 和原目标关系保持不变。 / The Adapter owns measured identity correspondence and preserves benchmark semantics and source evidence during goal projection.

通用 `compose_executable_relation_plan(...)` 接受可选领域 `relation_projection`，验证实体、目标种类、非自指、证据与场景覆盖。`scene_entity_refs` 保留本场景全部三个观测方块，避免准备时丢失支撑物或其他碰撞障碍。编译结果保留四个实际 Query 直接依赖： / The generic compiler validates domain values and preserves all three observed objects and four direct Query dependencies.

```text
current observation + authorized understanding + goal-projection evidence
    ├─ scene.bind ── grasp.propose ──────────┐
    │       └────── relation.target ────────┤
    ├─ manipulation.capabilities ───────────┤
    └─ scene.bind (direct evidence) ────────┤
                                relation.establish
```

`relation.target` 的可选 `binding_ref` 由已有 `argument_source_requirements` 从直接前置 `scene.bind` 的持久结果解析。发布 YAML 与 Runtime ToolSpec 完整一致，并保留原 `implementation_id` / `unknown_semantics` 元数据。Endpoint 将 binding 交给 Provider，同时按严格输出 schema 返回规范结果。 / Existing source projection supplies the binding; packaged and runtime specifications agree, and normalized output preserves its strict schema.

Core/Coordinator 继续持有当前 revision、可信 intent、直接前置记录、任务/节点结算和恢复；AgentLoop 驱动工作流。Adapter 持有来源、几何与映射，Preparation/selector/PreparedRoutes 持有准备机制，Runtime/Gateway/worker 持有执行、取消和执行结算。 / Lifecycle ownership remains with the existing components; no parallel state store or scheduler is introduced.

## 几何与准备边界 / Geometry and preparation

- `route_geometry_source: observed` 装配 `ObservedRelationTargetProvider`；`oracle` 保留 `PersistentRelationTargetProvider`。观测模式的目标来自点云、深度、标定和当前 binding；原始 actor 数据只保留既有身份/漂移对应职责。 / Geometry-source selection composes the observed or oracle provider explicitly.
- 方块支撑：从完整物体点云选取最高处现有 `inlier_distance_m=0.002` m 点带，再调用原 `estimate_support`。最小点数、水平度、倾斜、污染和完整足迹条件保持。桌面支撑复用未被对象掩码覆盖的场景深度与既有空闲支撑目标搜索。 / Block tops use the highest 2 mm band with unchanged support constraints; table goals reuse observed scene-depth support and free-space search.
- 世界坐标以当前标定 `world_T_observation` 转换；输入点云、binding、observation、scene、camera frame 与 calibration 必须属于同一证据链。准备输入解析器核对持久 Query、目标 pose、来源和完整执行映射。 / Calibrated world geometry and preparation are bound to one current evidence lineage.
- 带显式来源/证据的已注册关系目标可用于 benchmark 语义的 observed 准备；普通 `target` / `staging` 的目标策略继续生效。对象 `geometry_source` 与 `target_geometry_source` 分别保留。 / Registered relation geometry preserves benchmark semantics and independent object/target provenance.
- Stack/RGB 声明 `route_preparation_supported=True`，engine 仅 `route_readiness` / `contact_qualification` Query 改用该能力；Stack 的 `motion_execution_supported=False`、oracle grasp 限制和实际 `_prepare` 执行拒绝保持。 / Planning capability is separate from motion admission and controller checks.

## Host 装配 / Host composition

在既有有效 stack host profile 上保持相同 Coordinator、`binding_request` 和 workspace： / Use the existing stack profile and the same Coordinator.

```yaml
stack_relation_preparation_enabled: true
simulation_action_mode: runtime_monitored
route_geometry_source: observed
```

该组合复用 `build_stack_relation_execution_provider_factory(prepare_inputs=...)` 与 Coordinator 的 `resolve_relation_context`。四个 Query 实际完成并持久化后，关系 Action 才取得可信 intent；无运动准备通过独立 `prepare_route` 路径验证。Action 工厂的 `motion_supported()` 仍返回 False。 / The same production factory and context resolver feed preparation while relation motion admission remains closed.

## 保存采集的离线实测 / Offline analysis of a saved capture

证据：`out/robotwin-stack-20261127/114119/observed-cloud-diagnostic.json`。来源采集时间为 **2026-11-26T09:48:52.061150Z**（北京时间 17:48:52），seed 0，scene `stack_blocks_three-0-1`。本轮读取原 RGB-D/understanding 和标定，保存源 refs、源提交、分析 HEAD、策略及逐对象结果；报告标明 `offline_saved_capture`、`current_scene_claim=false`、`motion_started=false`。 / This analysis reuses the timestamped capture and retains its original provenance; it starts no new simulator, perception run or Action.

**v18.2.1 归因纠正 / Attribution correction:** 旧报告中的 0.12980/0.12290/0.10829 m 是 camera AABB 八角点变换后的 Y 尺寸，并非生产包络。真实 `Grounding._project_visual_geometry` 已使用完整世界点云，返回 `observed-envelope/world/*` 与单位旋转；该调用的原 padding 仅约 10⁻⁸ m。历史测量及日志保留，以下为调用生产方法的新诊断。 / The old camera-corner dimensions were incorrectly attributed to production; production already uses calibrated world-cloud bounds with negligible padding.

证据目录：`out/robotwin-stack-20261127/145656/`。`production-diagnostic.json` 为单一 CLI 的生产调用结果；原临时脚本和测量保留在 `/home/yanxu/robotwin20-runtime/stack-blocks-three/envelope-diagnosis-20261127/`。 / The repository retains the standalone CLI and production replay; original temporary scripts and measurements remain in the external diagnostic directory.

| 实体 / Entity | 生产世界 Y / Production Y (m) | 最大 Y 像素 / Pixel (x,y) | 距桌面高度 / Height above table (µm) | 桌面 2 mm 带点数 / Band points |
|---|---:|---|---:|---:|
| e1 | 0.10824136 | (53,86) | 52.91 | 38 |
| e2 | 0.10056025 | (88,119) | 9.57 | 44 |
| e3 | 0.08158460 | (283,127) | 0.00 | 29 |

桌面 e4 点云 70,795 点，原 `estimate_support` 拟合 65,379 个 inlier，桌面高度 0.7405738729 m。三个最大 Y 点均在掩码边缘，邻域深度跳变约 67/63/62 mm，说明桌面背景进入了对象点云。仅作诊断剔除桌面 2 mm 带后 Y 为 0.06281347/0.06287808/0.05037463 m；该分类也会删除真实底边，**不能作为生产修复或堆叠成功证据**，原 cloud/mask 未改。 / Pixel neighborhoods tie the enlarged bounds to table-depth contamination. Band removal is diagnostic only and also removes genuine bottom edges; no production geometry or success evidence is produced.

后续修复应在视觉 metric 层验证深度连通的前景/背景分离，原始点与残差继续保留供碰撞分析；关系 Provider 不裁剪点云，不放宽完整足迹条件。此离线分析没有新视觉推理或运动证据；独立的新采集见下节，仍没有路线/接触/停止资格或运动证据。 / Investigate foreground/background separation while retaining raw/residual collision evidence. This offline analysis is distinct from the new capture below; neither qualifies motion.

复跑（仓库根目录；读取原采集，输出到新临时目录，失败的支撑拟合直接报错）： / Reproduce from the repository root; read the original capture, write a new output and propagate support-fit failures.

```bash
export PYTHONPATH=examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src
stack_replay_dir=$(mktemp -d)
.venv/bin/python out/robotwin-stack-20261127/145656/diagnose.py \
  --source /home/yanxu/robotwin20-runtime/stack-blocks-three/continuation-20261126-174549 \
  --output "$stack_replay_dir/production-diagnostic.json"
.venv/bin/ruff check out/robotwin-stack-20261127/145656/diagnose.py
```

独立 CLI 实跑退出 0；生产尺寸、camera-corner 对照、像素位置、支撑拟合、诊断删带尺寸与原三个 JSON 逐值一致。JSON 记录采集时间、scene/observation/calibration/depth/cloud/mask refs、分析 HEAD、`current_scene_claim=false` 和 `motion_started=false`。 / Replay succeeds and all compared values match the original measurements, with explicit capture lineage and offline scope.

## 独立的新同步采集 / Separate fresh synchronized capture

Runtime代理在同一backend调用现有 `observe_many(["camera/head", "camera/front"])`；两路均为 **2026-11-27 06:57:15.379471+00:00**（北京时间14:57:15），seed0、sensor_available=true、exit0、无运动。完整源目录为 `/home/yanxu/robotwin20-runtime/stack-blocks-three/dual-observation-20261127-145639/`；本仓库保存 `145656/fresh-run.json`、`fresh-capture.json`、`fresh-capture-result.json` 和 `fresh-visual-result.json`。 / A separate same-backend capture synchronizes both cameras; small metadata is retained locally and full artifacts remain at the source directory.

Front真实Qwen→LA/SAM2链 exit0/status available，只识别绿色/蓝色方块及背景；红块缺失，图像边缘裁切绿蓝方块。主审亦查看front图确认覆盖缺口，不能称完整三块观测或多视角融合。本节的新观测不能与前节2026-11-26采集混用，虽复用seed和scene字符串仍是不同采集根目录。 / Front perception succeeds but lacks red and clips the visible cubes; it does not establish complete coverage or fusion. Keep this capture separate from the older diagnostic despite reused scene labels.

候选front相机已由主审查看图像确认三块完整入镜，并采纳到正式 `examples/forge-adapters/robotwin20/profiles/robotwin20/stack-blocks-three.yaml`：`position=[0,-0.7,1.1]`、`forward=[0,1,-0.5]`。同backend新采集时间为2026-11-27T07:03:41.024775Z（北京时间15:03:41）；完整源目录 `/home/yanxu/robotwin20-runtime/stack-blocks-three/front-fov-20261127-150158/`，小型run/experiment/capture metadata以 `candidate-*` 保存在本版out。 / Reviewed candidate camera coverage is adopted into the official profile, with separate capture provenance.

候选front真实Qwen→LA/SAM2链 exit0/status available，识别red/green/blue cube和white surface，ambiguities为空；三块均有mask/cloud/geometry。既有 `load_runtime_profile` 实跑通过，仍包含head/front两路。此改动修正视域覆盖，不代表掩码污染已消除、多视角融合或stack执行成功。 / Candidate front perception covers all three cubes with metric artifacts; profile loading passes, while geometry contamination, fusion and stack execution remain separate validation work.

候选测量 `145656/candidate-front-measurement.json` 的mask bbox分别为红[25,93,53,124]、绿[60,109,96,144]、蓝[235,112,266,145]，均在320×240图像内。但生产世界Y尺寸为0.174711/0.156621/0.142315 m，桌面2 mm带仍含31/51/30点，斜视下污染扩大。下一步仍是视觉metric前景深度分层，不能以FOV修复替代几何修复。 / All masks are inside the image, but production bounds remain enlarged by table contamination; foreground-depth separation is still required.

本版主审运行backend/task-adapter两套件：**42 passed in 0.29s**。 / Parent profile/backend regression: 42 passed.

主审独立复跑CLI成功，输出 `/tmp/robotwin-production-diagnostic-review-20261127.json`。 / Parent independently reran the diagnostic successfully.

既有控制器资格包已在 `qualification-20261126-175135/old-qualification-compatibility.json` 完成兼容性审计，结果为 `valid approved_pass`。本轮未重跑 controller qualification；后续仍需实际 stack route/contact/stop 证据，然后在同一 AgentTask 内逐块重观察并连续执行三块。 / Existing controller qualification is compatible; stack-specific execution evidence and the three-block closed loop remain the next stages.

## v18.2.0 验证记录 / Prior-version validation

执行代理：关系契约同步后的 `test_relation_target.py` + `test_stack_relation_context.py` **37 passed in 6.60s**；之前五个聚焦套件 **96 passed in 6.84s**。真实 compiler、选择、持久记录、Endpoint、Grounding、Preparation、selector 和 PreparedRoutes 执行，外部规划/碰撞/接触/worker 由 fixture 替换。测试覆盖 table/block、不同视觉/执行身份、三物体覆盖、过期/缺失/错误证据、倾斜/稀疏/高点、无运动 Query 与 Action 拒绝；`client.start=0`。 / The implementation agent exercised production preparation boundaries with substituted external mechanisms and zero Action starts.

主审最终 20 套件回归为 **564 passed in 20.99s**，覆盖发布 YAML/runtime 完整一致性与合法 binding 参数；本任务全部 15 个 Python 文件完整 Ruff 通过。 / Final parent review passed 564 tests across 20 suites and all changed Python files pass Ruff.

主审在最后新增两个契约测试前的扩大回归得到 **1802 passed, 15 failed, 1 skipped**；全部 15 项在隔离 HEAD `6be7fb35` 精确复现（15 failed in 2.77s，`/tmp/robotwin-head-check-skfeu8qb`）。范围为旧视频 fixture、工具发现/版本、capability/composite/动作发布 schema、binding/release manifest 锁及 workflow/verifier fixture；本轮保持这些旧测试与发布产物原状。 / The parent reproduced every broad-suite failure against HEAD; the broad run is not reported as green.

```bash
export PYTHONPATH=examples/forge-adapters/robotwin20/scripts:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src
test_files=(
  tests/test_planning_dispatch.py
  tests/test_planning_loop.py
  tests/test_planning_task_integration.py
  tests/test_planning_projection.py
  tests/test_planning_source_assembly.py
  tests/test_planning_dispatch_bootstrap.py
  tests/test_planning_end_to_end.py
  examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py
  examples/forge-skills/pick-place-workflow/tests/test_relation_execution.py
  examples/forge-skills/pick-place-workflow/tests/test_relation_target.py
  examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py
  examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py
  examples/forge-adapters/robotwin20/tests/test_stack_relation_execution.py
  examples/forge-adapters/robotwin20/tests/test_persistent_host.py
  examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py
  examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py
  examples/forge-adapters/robotwin20/tests/test_grounding.py
  examples/forge-adapters/robotwin20/tests/test_route_inputs.py
  examples/forge-adapters/robotwin20/tests/test_observed_relation_target.py
  examples/forge-adapters/robotwin20/tests/test_robotwin_task_adapters.py
)
.venv/bin/python -m pytest -q "${test_files[@]}" --tb=short
python_files=(
  examples/forge-adapters/robotwin20/runtime/robotwin_blocks_ranking_adapter.py
  examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
  examples/forge-adapters/robotwin20/src/robotwin20_adapter/observed_relation_target.py
  examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
  examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py
  examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_inputs.py
  examples/forge-adapters/robotwin20/tests/test_observed_relation_target.py
  examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py
  examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py
  examples/forge-adapters/robotwin20/tests/test_robotwin_task_adapters.py
  examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py
  examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py
  examples/forge-skills/pick-place-workflow/src/pick_place_workflow/relation_target.py
  examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py
  examples/forge-skills/pick-place-workflow/tests/test_relation_target.py
)
.venv/bin/ruff check "${python_files[@]}"
git diff --check
```
