# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

- [2026-11_part5](changelog/2026-11_part5.md)
- [2026-11_part4](changelog/2026-11_part4.md)
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

## v18.2.1 (2026-11-27 14:55) - codex

### 计划与完成 / Plan and completion

- [eval] [exp] [完成] 保存 Runtime 代理对原始采集的可复跑生产 Grounding 诊断CLI与 production-diagnostic.json 到新 out/robotwin-stack-20261127 目录，保留原始 artifact 来源和离线/无运动范围。 / Preserve a reproducible production-Grounding diagnostic and measurements from the original capture in a new output directory with explicit provenance and offline/no-motion scope. (local)
- [docs] [fix] [完成] 纠正接续文档将 camera AABB 世界变换误称生产包络的归因；生产已使用完整世界点云，依据新测量区分掩码污染与包络机制。原历史日志及原始测量不修改。 / Correct the camera-AABB attribution using measured production geometry and distinguish mask contamination from envelope construction; retain historical logs and original measurements. (local)
- [docs] [docs] [完成] 补本版本精确行号、关键 Diff、复跑命令与结果，完整同步最近五版本；不修改运动、生产几何或阈值，不提交/推送，由主审处理。 / Record exact lines, diffs and reproduction results, synchronize the latest five versions, and leave production geometry/motion unchanged; parent owns commit/push. (local)
- [eval] [fix] [完成] 按主审要求合并临时诊断为单一 --source/--output CLI，消除硬编码源目录、exec耦合与支撑拟合失败后median回退；原脚本/测量保留external，CLI新增完整采集身份与HEAD并对原artifact实跑验证。 / Consolidate the diagnostic into a standalone CLI with explicit paths, fail on support-fit errors, retain external sources and verify against the original capture. (local)

- [eval] [exp] [范围补充] 保存本轮新同步head/front采集小型metadata和front真实视觉链结果摘要，原大图/完整产物保留external；按主审去除冗余旧脚本/JSON副本。 / Preserve fresh synchronized capture metadata and front perception summary, retaining full artifacts externally and removing redundant diagnostic copies. (local)

- [sense] [fix] [完成] 主审通过候选front图确认三块完整入镜，批准正式stack-blocks-three.yaml仅position [0,-.45,.85]→[0,-.7,1.1]、forward [0,1,-.1]→[0,1,-.5]两行；保存候选采集metadata并用既有profile loader验证，不宣称几何污染或stack成功。 / Apply the reviewed two-line front-camera pose correction and validate the existing profile loader; coverage is not a geometry or stacking success claim. (local)

### 文件变更详情 / Exact file changes

- [docs] [fix] [修改] `docs/forge/ROBOTWIN_STACK_CONTINUATION_20261126.md` L1-L3、L48-L89、L93：纠正camera-corner误归因，记录真实生产包络/掩码边缘证据、诊断限制与独立复跑命令；旧验证标明v18.2.0。 / Correct attribution and document measured production geometry, limitations and reproduction, labeling prior validation. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/diagnose.py` L1-L183：单一CLI真实调用Grounding投影与support拟合；显式source/output、原像素顺序核验、原采集只读。 / Standalone production-method replay with explicit paths and verified pixel association. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/production-diagnostic.json` L1-L1057：CLI输出，包含采集身份、分析HEAD、来源与离线范围。 / CLI measurements with capture lineage and offline scope. (local)
- [docs] [docs] [追加/同步] `changelog/2026-11_part5.md` L819-L899、`CHANGELOG.md` L55-L135：本版完整双语日志和最近五版本同步，历史归档不改。 / Append this version and synchronize the latest five complete records without altering historical archives. (local)

- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/fresh-run.json` L1-L10：复制新采集来源metadata/结果，完整产物保留external。 / Preserve fresh-capture metadata/results with full artifacts retained externally. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/fresh-capture-result.json` L1-L1：复制新采集来源metadata/结果，完整产物保留external。 / Preserve fresh-capture metadata/results with full artifacts retained externally. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/fresh-capture.json` L1-L52：复制新采集来源metadata/结果，完整产物保留external。 / Preserve fresh-capture metadata/results with full artifacts retained externally. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/fresh-visual-result.json` L1-L6：复制新采集来源metadata/结果，完整产物保留external。 / Preserve fresh-capture metadata/results with full artifacts retained externally. (local)

- [sense] [fix] [修改] `examples/forge-adapters/robotwin20/profiles/robotwin20/stack-blocks-three.yaml` L8-L9：相机位置/朝向改为[0,-.7,1.1]/[0,1,-.5]，修复三块视域覆盖。 / Correct front-camera field-of-view coverage. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/candidate-run.json` L1-L10：候选相机实验配置与新采集身份。 / Candidate-camera experiment configuration and capture lineage. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/candidate-experiment.json` L1-L34：候选相机实验配置与新采集身份。 / Candidate-camera experiment configuration and capture lineage. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/candidate-capture.json` L1-L52：候选相机实验配置与新采集身份。 / Candidate-camera experiment configuration and capture lineage. (local)

- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/candidate-front-measurement.json` L1-L1173：候选front真实生产包络、mask边界与桌面污染负结果。 / Candidate front bounds, mask coverage and remaining contamination. (local)

- [eval] [exp] [新增] `out/robotwin-stack-20261127/145656/candidate-summary.json` L1-L279：Runtime最终命令/exit0/同步身份/视觉上下文与污染负结果统一摘要。 / Final Runtime summary of commands, synchronized lineage, perception scope and remaining contamination. (local)

### 关键 Diff / Key diff

```diff
- camera-corner world Y 0.12980/0.12290/0.10829 m described as production envelope
+ real Grounding world-cloud Y 0.10824136/0.10056025/0.08158460 m
+ max-Y mask-edge points lie 52.91/9.57/0 µm above observed table
- temporary hard-coded source, exec-linked scripts and median fallback
+ standalone diagnose.py --source --output, actual production projection and support fit
+ propagate fitting errors; diagnostic_not_production labels band-removal measurements
- front position [0,-.45,.85], forward [0,1,-.1]
+ front position [0,-.7,1.1], forward [0,1,-.5]
```

### 实测与验证 / Measurement and validation

- [eval] [exp] 新采集2026-11-27T06:57:15.379471Z（北京时间14:57:15），同backend head/front同步、seed0、exit0；front Qwen→LA/SAM2 exit0/available但红缺失、绿蓝切边，无三块覆盖/融合证据。旧诊断原采集为2026-11-26，不可混用。 / Fresh synchronized views and successful front inference have incomplete coverage and are distinct from the older capture. (local)
- [eval] [exp] 主审独立CLI复跑成功，输出 `/tmp/robotwin-production-diagnostic-review-20261127.json`。 / Parent independent replay passed. (local)
- [eval] [docs] External source: `/home/yanxu/robotwin20-runtime/stack-blocks-three/dual-observation-20261127-145639/`；原诊断：`/home/yanxu/robotwin20-runtime/stack-blocks-three/envelope-diagnosis-20261127/`。 / Full original artifacts remain in these source directories. (local)

- [eval] [exp] 采集为 2026-11-26T09:48:52.061150Z，scene=stack_blocks_three-0-1；分析HEAD=6479a0535eec9799ac0a8096fc9b06c228131607。Runtime原目录为 `/home/yanxu/robotwin20-runtime/stack-blocks-three/envelope-diagnosis-20261127`；原capture/mask/cloud/标定未修改。 / Measurements replay the original timestamped capture and preserve its source artifacts. (local)
- [eval] [exp] 对原capture运行CLI，exit0；生产尺寸、camera-corner、像素、支撑拟合及诊断删带尺寸与原测量JSON逐值一致。原三个临时脚本亦在独立临时目录依次复跑，exit0，三个JSON与源副本相等。CLI完整Ruff和git diff --check通过。 / The CLI and isolated original-script replay pass; compared values match exactly, and lint/whitespace checks pass. (local)
- [eval] [docs] 桌面70795点/65379 inlier，height=0.7405738729m；掩码边缘深度跳变约67/63/62mm。诊断删桌面2mm带38/44/29点后Y变为0.06281347/0.06287808/0.05037463m，同时会删真实底边，不是生产修复或堆叠通过证据。 / Edge-depth evidence identifies contamination; band exclusion is diagnostic and cannot certify a corrected object or successful stack. (local)
- [env] [docs] 本版生产Python不变，仅修正正式front相机profile两行；离线诊断之外有独立新同步采集和front视觉链，无运动，不改生产几何/足迹阈值。当前路线/接触/停止资格及三块执行仍待后续；本版不复跑旧564项功能回归。 / This version adds diagnostics and separate fresh observation metadata; live qualification remains open and prior functional tests were not rerun. (local)

```bash
export PYTHONPATH=examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src
stack_replay_dir=$(mktemp -d)
.venv/bin/python out/robotwin-stack-20261127/145656/diagnose.py \
  --source /home/yanxu/robotwin20-runtime/stack-blocks-three/continuation-20261126-174549 \
  --output "$stack_replay_dir/production-diagnostic.json"
.venv/bin/ruff check out/robotwin-stack-20261127/145656/diagnose.py
git diff --check
```

- [eval] [exp] 候选采集2026-11-27T07:03:41.024775Z，同backend同步；front真实Qwen→LA/SAM2 exit0/available，red/green/blue cube与white surface四实体，ambiguities=[]，三块mask/cloud/geometry齐全。主审看图确认三块不切边；既有load_runtime_profile返回修正配置和head/front两路。不能称几何污染已修或stack成功。 / Candidate front perception covers all three cubes and profile loading passes; contamination and stack execution remain unproven. (local)

- [eval] [exp] 候选mask bbox红[25,93,53,124]绿[60,109,96,144]蓝[235,112,266,145]均不触边；生产Y却为0.174711/0.156621/0.142315m，桌面2mm带31/51/30点，污染未修。后续视觉metric前景深度分层，保留原点/残差。 / FOV is corrected but slanted-view table contamination enlarges production bounds; depth foreground separation remains necessary. (local)
- [eval] [exp] 主审独立backend/task-adapter两套件42 passed in0.29s。 / Parent regression passed all42 checks. (local)

```bash
PYTHONPATH=examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/robotwin20/tests/test_robotwin_backend_contract.py examples/forge-adapters/robotwin20/tests/test_robotwin_task_adapters.py --tb=short
```

### Git 提交 / Git receipt

- Commit: `1da81fbb`; Branch: `feature/planning-loop`; 时间 / Time: 2026-11-27 15:10:56 +0800.
- [chore] [docs] 主审确认 `git push origin feature/planning-loop` 成功，exit 0，范围 `6479a053..1da81fbb`。 / Parent confirmed successful push to `origin/feature/planning-loop`, exit 0, range `6479a053..1da81fbb`. (commit 1da81fbb)

## v18.2.0 (2026-11-26 17:44) - codex

### 计划与完成 / Plan and completion

- [policy] [feat] [完成] 接续 2026-11-26 中断工作；relation.target 新增可选 binding_ref 和 scene.bind 直接前置参数来源，编译器保留四个 Query 依赖，Adapter 目标投影保留原 benchmark goal/subtask 及全部三个视觉实体。 / Resume the interrupted work with explicit binding evidence, four direct Queries and Adapter-owned goal projection that preserves benchmark semantics and complete scene coverage. (local)
- [env] [feat] [完成] 新增观测关系目标 Provider，使用当前标定/点云/深度估计 block/table 支撑并核验视觉/执行对应；observed/oracle 按显式来源装配，准备解析器核对持久 Query、binding、映射、pose 与来源证据。 / Add observed block/table targets and validate current identity, geometry and persisted preparation evidence through explicit observed/oracle composition. (local)
- [env] [fix] [完成] 最高 2 mm 顶面点带消除完整方块点云的侧面干扰，复用原点数/倾斜/污染/完整足迹限制；提取已有空闲支撑目标搜索，带来源的关系目标可用于 benchmark 语义准备。 / Select the highest observed 2 mm band using unchanged support constraints and reuse existing free-support search and provenance-bound relation targets. (local)
- [env] [feat] [完成] 将无运动路线准备与执行能力分离，仅修改 engine 的 readiness/contact Query 能力判断；保留 Stack motion_execution_supported=False、实际 _prepare/oracle grasp 拒绝及原控制器校验。 / Separate planning-only support from execution through the Query boundary while preserving Stack motion rejection and controller validation. (local)
- [eval] [exp] [完成] 补齐真实编译/选择/Coordinator 持久记录→Provider→artifact resolver→Preparation 贯通，覆盖不同视觉/执行身份、完整碰撞覆盖、证据漂移和几何失败；修复新测试 fixture 的先写后读与缓存变更。 / Exercise production preparation with differing identities and complete collision coverage, failure cases and corrected fixture creation/cache mutation. (local)
- [policy] [fix] [完成] 主审发现本轮 relation.target 发布 YAML 漏同步；补齐来源和参数，保留既有 implementation_id/unknown_semantics 并同步 Runtime，新增完整相等和合法 binding 输入/严格输出回归。 / Resolve the review finding by synchronizing the published relation contract, retaining metadata and testing complete equality and normalized bound-query output. (local)
- [eval] [exp] [完成] 保存 seed0 的真实历史 RGB-D 离线诊断：原采集 2026-11-26T09:48:52.061150Z，最高点带拟合成功，保守包络仍超过方块足迹。未启动新仿真、感知模型或 Action。 / Preserve an offline diagnostic of the original capture; top fitting succeeds but conservative envelopes still exceed support, with no new simulator, perception run or Action. (local)
- [model] [docs] 所有权：通用层负责关系语义/依赖，Adapter 负责几何/身份/来源，Coordinator 独有任务修订/结算/恢复，Runtime/Gateway 独有执行/取消。新鲜度边界为当前 scene/observation/calibration/binding；最小贯通用例以不同视觉/执行实体准备成功，client.start=0；未新增 hash、gate 或并行状态库。 / Preserve domain and lifecycle owners and the existing evidence freshness boundary, verified through differing-identity preparation with zero starts and no new defensive mechanism. (local)

### 文件变更详情 / Exact file changes

- [env] [feat] [新增] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/observed_relation_target.py` L1-L175：当前 binding/标定/完整映射、原目标投影、点云世界变换、最高顶面/table 支撑与来源工件。 / Implement current-binding identity projection, calibrated support geometry and source artifacts. (local)
- [env] [refactor] [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py` L605-L631、L633-L683、L713-L745、L775-L780：提取复用空闲支撑搜索，允许带来源/证据的关系目标准备，并保留普通目标策略。 / Reuse support search and provenance-bound relation targets while preserving ordinary target policy. (local)
- [env] [feat] [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py` L32、L393-L394：按 route_geometry_source 选择 observed/oracle Provider。 / Select the explicit geometry provider. (local)
- [env] [feat] [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_inputs.py` L53-L95：观测输入核对绑定/完整映射/目标 pose/标定/点云/深度/支撑工件，oracle 保留执行身份要求。 / Validate observed evidence while preserving oracle identity requirements. (local)
- [env] [feat] [修改] `examples/forge-adapters/robotwin20/runtime/robotwin_blocks_ranking_adapter.py` L18、L228；`examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py` L499：声明路线准备能力，两个准备 Query 消费该能力，实际执行能力不变。 / Declare planning capability without changing motion support. (local)
- [policy] [feat] [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py` L442、L469-L500、L505、L518：可选领域 projection、证据与场景实体校验，bind 同时成为 grasp/target 依赖。 / Compile projected identities, full scene coverage and explicit binding dependencies. (local)
- [policy] [fix] [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/relation_target.py` L17、L32-L37、L49、L97；`examples/forge-skills/pick-place-workflow/contracts/relation.target.tool.yaml` L10-L14、L17、L23：同步参数来源、可选 binding 与既有发布元数据/说明。 / Synchronize runtime and published relation specifications. (local)
- [eval] [exp] [新增] `examples/forge-adapters/robotwin20/tests/test_observed_relation_target.py` L1-L179：真实绑定、保留 benchmark 目标、非单位相机位姿、block/table、密集侧面和 11 类失败。 / Test real binding, source retention, calibrated geometry and support failure cases. (local)
- [eval] [exp] [修改] `examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py` L37-L42、L57-L396、L423-L467：真实选择/持久记录/Query 到 observed Preparation 贯通与 6 类工件漂移拒绝。 / Exercise durable production preparation and six artifact-drift cases. (local)
- [eval] [refactor] [修改] `examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py` L19-L26、L38-L43、L64-L65：组合 fixture 接受真实 Grounding，保留原 oracle 用例。 / Let preparation fixtures use real observed Grounding. (local)
- [eval] [exp] [修改] `examples/forge-adapters/robotwin20/tests/test_robotwin_task_adapters.py` L199-L245；`examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py` L11、L44-L45、L53、L128：验证无运动 Query/执行拒绝和显式来源装配。 / Verify planning-only entry, motion rejection and deployment source selection. (local)
- [eval] [exp] [修改] `examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py` L3-L4、L25、L372-L418；`examples/forge-skills/pick-place-workflow/tests/test_relation_target.py` L1-L17、L64-L78：projection 合法/非法值，发布完整一致性和 binding 规范输出。 / Test projected domain values and published bound-query behavior. (local)
- [eval] [exp] [新增] `out/robotwin-stack-20261127/114119/observed-cloud-diagnostic.json` L1-L264：源采集时间/scene/calibration、源提交/分析 HEAD、seed、原全云失败、最高点带拟合、足迹与保守世界包络；offline_saved_capture / current_scene_claim=false / motion_started=false。 / Persist traceable offline geometry measurements and execution scope. (local)
- [docs] [docs] [修改] `docs/forge/ROBOTWIN_STACK_CONTINUATION_20261126.md` L1-L110：当前实现、所有权、依赖、配置、真实负结果和下步路线；`changelog/2026-11_part5.md` L689-L817、`CHANGELOG.md` L55-L183：完整双语条目和最近五版本同步。 / Update continuation and synchronized detailed latest-five records. (local)

### 关键 Diff / Key before-and-after diff

```diff
# Domain plan / Adapter target composition
- bind only the moving entity; relation.target independent of scene.bind
+ preserve relation_projection.scene_entity_refs for all three observed objects
+ scene.bind -> grasp.propose and relation.target; four direct Queries -> relation.establish
- PersistentRelationTargetProvider(client) for all route sources
+ ObservedRelationTargetProvider(grounding, task_name=task_name) if observed else existing oracle provider
```

```diff
# Measured support and preparation
- support = estimate_support(points, support_ref, policy)
+ top = points[points[:, 2] >= points[:, 2].max() - policy.inlier_distance_m]
+ support = estimate_support(top, support_ref, policy)
- require relation entity identity to equal execution identity for all sources
+ observed evidence must match the persisted binding, complete execution mapping, pose and calibration
+ oracle evidence retains execution-identity equality
- scene_facts always resolves benchmark target under benchmark_task_definition
+ an explicitly registered relation target with source evidence uses its selected geometry
```

```diff
# Planning-only Runtime capability and publication
- if not self.task_adapter.motion_execution_supported:  # readiness/contact Queries
+ if getattr(self.task_adapter, "route_preparation_supported", False) is not True:
+ Stack/RGB.route_preparation_supported = True
# Stack.motion_execution_supported remains False; _prepare/oracle grasp checks remain.
+ relation.target optional binding_ref and scene.bind argument_source_requirements in YAML and runtime
+ retain implementation_id/unknown_semantics in both; assert parsed YAML == runtime ToolSpec
- calibration = _artifact_path(tmp_path, not_yet_created_ref)
+ create fixture calibration path first; use strict artifact reads only after creation
```

### 真实离线测量与接续 / Offline measurements and continuation

- [eval] [exp] 保存采集时间 **2026-11-26T09:48:52.061150Z**，scene `stack_blocks_three-0-1`，seed0；e1/e2/e3 原云 860/1095/1108 点，全云水平共识均失败；最高 2 mm 点带 458/580/600 点均通过既有支撑拟合。 / All three highest bands fit the unchanged policy after full-cloud side-face contamination is removed. (local)
- [eval] [exp] 顶面 XY 依次为 0.06153×0.06174、0.06164×0.06242、0.05146×0.05022 m；原 camera envelope 的保守世界 Y 尺寸为 0.12980/0.12290/0.10829 m，完整足迹堆叠继续拒绝。保留原包络、阈值和原始采集新鲜度。 / Measured footprints remain smaller than conservative world envelopes, so stacking is unavailable under the unchanged full-footprint rule. (local)
- [env] [docs] 既有 `/home/yanxu/robotwin20-runtime/stack-blocks-three/qualification-20261126-175135/old-qualification-compatibility.json` 记录 valid approved_pass，已确认旧控制器包兼容当前 sources/runtime；本轮未重跑控制器。后续先改善观测对象几何/稳定支撑，再实测 stack route/contact/stop，最后同一 AgentTask 连续三块。 / Existing controller qualification is compatible; observed geometry and stack-specific execution evidence are the remaining stages. (local)

### 验证与已复现旧失败 / Validation and reproduced existing failures

- [eval] [exp] 主审最终原 18 套件加 observed_relation_target / robotwin_task_adapters 共 **20 套件 564 passed in 20.99s**；覆盖 YAML/runtime equality 和新增合法 binding 回归。执行代理最终定向 relation_target/context **37 passed in 6.60s**，此前五套件 **96 passed in 6.84s**。 / Parent final review passed 564 scoped tests; implementation-agent focused validation passed 37 after contract synchronization and 96 in the preceding five-suite run. (local)
- [eval] [exp] 主审在最后新增两个契约测试前扩大到 Adapter/Skill 两目录：**1802 passed, 15 failed, 1 skipped**。另一清单执行代理在隔离 HEAD `6be7fb35` 精确重跑同 15 项，**15 failed in 2.77s**；主审核对 `/tmp/robotwin-head-check-skfeu8qb` 的 import-proof/结果确认不是工作树导入。 / Every broad-run failure reproduces against the isolated original HEAD, with imports verified by the parent; the broad run is not green. (local)
- [eval] [docs] 旧失败范围：persistent_task_video(1)、binding_freeze(1)、capabilities(1)、composite_manipulation(4)、full_workflow(1)、grasp_propose(2)、manipulation_prepare(1)、object_acquire(1)、persistent_runtime(1)、release_bundle(1)、task_verification_context(1)。保留这些旧 fixture、发布 schema/版本/锁和历史输出，不扩大本轮修改。 / These existing fixture, discovery, publication and release failures remain outside this observed-relation change. (local)
- [chore] [fix] 主审对本任务全部 **15 个** 新增/修改 Python 文件执行完整 Ruff，全部通过；执行代理亦通过本轮文件 Ruff、git diff --check。Blocker/Major 已处理：发布 relation YAML 缺字段已修并加回归。 / All changed Python files pass full lint, and the review's relation-publication Major is resolved with a regression test. (local)
- [eval] [docs] 契约/Provider 证据覆盖生产准备，外部规划/碰撞/接触/worker 由 fixture 替换；真实证据为历史采集的离线几何测量。client.start=0，未启动新仿真/感知/动作，尚无本轮 stack route/contact/stop 或三块连续执行成功证据。 / Preparation contracts and offline measurements have explicit evidence scope; stack execution qualification remains open. (local)

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

### Git 提交 / Git receipt

- Commit: `23730d4c319604ec66fed588a2d82b48d5302d65`; Branch: `feature/planning-loop`; 时间 / Time: 2026-11-27 12:34:46 +0800.
- [chore] [docs] 主审于 2026-11-27 12:35:50 +0800 确认 `git push origin feature/planning-loop` 成功（exit 0），推送范围 `6be7fb35..23730d4c`，远端分支 `feature/planning-loop`。 / At 2026-11-27 12:35:50 +0800, the parent confirmed successful push (exit 0) of `6be7fb35..23730d4c` to `origin/feature/planning-loop`. (commit 23730d4c)

## v18.1.0 (2026-11-26 16:03) - codex

### 计划与完成 / Plan and completion

- [policy] [feat] [完成] 接通 relation 公开 schema 的可信 intent 构造、Coordinator 当前 revision 直接前置查询解析、显式可执行关系片段；保留原语义计划和 subtask 行为，不向 Core 加入 RoboTwin 特判。 / Implement trusted relation intent, current-plan direct Query evidence and explicit executable segments while preserving existing semantics and subtask behavior. (local)
- [env] [feat] [完成] Adapter 私有 resolver 读取真实 evidence JSON 并核对 query/source；host 以默认 false 的 stack_relation_preparation_enabled 显式装配同一 Coordinator 与 preparation factory。 / Resolve actual evidence artifacts and opt in to production composition with the same Coordinator. (local)
- [eval] [exp] [完成] 真实五 ToolSpec 的编译/选择、持久查询/结算、endpoint、实际 artifact resolver 与真实 Preparation 贯通；覆盖身份/来源失败和 host 配置，无仿真启动且 client.start=0。 / Exercise actual schemas, durable evidence and real preparation with failure/configuration coverage and zero Action starts. (local)
- [model] [docs] 架构审核：Core 持有可信意图与当前计划记录，Adapter 持有 JSON 来源核验与关系目标投影；Coordinator 仍持有任务/节点结算，Runtime/Gateway/worker 持有动作/取消/执行结算。复用原 caller/record/node/input 验证和现有跨 revision 持久 schema；撤去冗余全局 NodeContext 检查，不新增 hash/gate/状态库。 / Architecture review retains Core, Adapter, Coordinator and Runtime ownership and relies on existing persistence revision validation without new hashes, gates or stores. (local)

### 文件变更详情 / Exact file changes

- [policy] [feat] [新增] `PhyAgentOS/forge/manipulation_context.py` L1-L61：唯一成功直接前置 Query 的 arguments/result 投影与共享关系 intent 构造，校验当前 scene、实体和真实 frame.frame_id。 / Project exact successful direct Queries and construct the shared relation intent from current scene/entity/frame evidence. (local)
- [policy] [feat] [修改] `PhyAgentOS/agent/planning_dispatch.py` L123、L131、L144、L181、L890-L909、L1172-L1173：只读 node_context_provider 注入，relation 可信参数构造与 schema 兼容 runtime 字段；prepare 数组要求保持。 / Inject the read-only node context and implement relation-specific trusted inputs without weakening preparation requirements. (local)
- [policy] [fix] [修改] `PhyAgentOS/planning/contracts.py` L467；`PhyAgentOS/forge/capability_runtime/manipulation_capabilities.py` L32：relation 不要求 prepare-only destination/capability 冻结字段，真实 capability ToolSpec 显式声明可选能力。 / Separate relation node bindings and declare the real capability Query for selection. (local)
- [policy] [feat] [修改] `PhyAgentOS/forge/task.py` L1208-L1288：提取共用 Action caller/record/graph 验证并增加 resolve_relation_context，完整可信 intent 与直接前置查询私有投影。 / Share Action context validation and add relation context using persisted direct predecessors. (local)
- [policy] [feat] [修改] `PhyAgentOS/agent/tools/planning.py` L788-L792；`PhyAgentOS/agent/loop.py` L494、L501-L505：首次激活与恢复重建均动态读取同一 Coordinator。 / Both activation paths use the live Coordinator context provider. (local)
- [policy] [feat] [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py` L14、L425-L500；同目录 `__init__.py` L15、L212：新增并导出 compose_executable_relation_plan；bind→grasp、capability、relation.target 均成为 Action 直接依赖。 / Export the executable relation compiler with explicit evidence dependencies. (local)
- [policy] [feat] [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/relation_execution.py` L6、L153-L154：endpoint 在解析真实 Coordinator context 后仅向内部 Provider request 注入 coordinator_context，公共 schema 不变。 / Supply resolved context only inside the Provider composition boundary. (local)
- [env] [feat] [新增] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_inputs.py` L1-L90：读取已有 JSON artifact 路径机制，比较真实 schema/task/query/motion/source，区分 bind world frame 与 observation frame，校验当前直通 Provider 的 execution identity。 / Resolve existing JSON artifacts and actual identity/frame/provenance representations before preparation. (local)
- [env] [feat] [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py` L309、L314-L315、L329、L379-L380、L385、L420-L430、L466、L504-L505、L963-L972：新增默认关闭的显式 profile 字段，同一 Coordinator 三端口，runtime_monitored/stack 配置约束及注入冲突拒绝。 / Add opt-in host composition with one Coordinator and explicit configuration compatibility checks. (local)
- [eval] [exp] [新增] `examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py` L1-L500：完整公开选择→持久记录→实际 endpoint→artifact→真实准备链，20 个成功/失败用例；仅外部规划与 worker 机制替换。 / Twenty integrated success/failure cases cover production boundaries with external mechanism fixtures. (local)
- [eval] [exp] [修改] `examples/forge-adapters/robotwin20/tests/test_persistent_host.py` L264-L266、L471、L494-L501、L600、L603-L606、L610、L635-L644、L881-L897：实际 profile factory/discovery、同 Coordinator、默认关闭/冲突/非 stack/mode/type 测试。 / Verify real host composition, discovery and configuration failures. (local)
- [eval] [fix] [修改] `examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py` L20-L21；`examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py` L19-L20：fixture 接受真实 Coordinator intent，未改写 Query candidate set。 / Let existing preparation fixtures consume the actual intent without altering Query results. (local)
- [eval] [fix] [修改] `tests/test_planning_task_integration.py` L154：原 fixture 补 planning_selections，HEAD 动态载入已复现缺字段 AttributeError。 / Initialize missing fixture state after reproducing its failure against HEAD. (local)
- [docs] [docs] [修改] `docs/forge/ROBOTWIN_STACK_CONTINUATION_20261126.md` L1-L63：当前范围、所有权、编译/host 使用与 observed/身份/实测缺口。`changelog/2026-11_part5.md` L607-L687、`CHANGELOG.md` L55-L135：双语完整记录及最新五条同步。 / Document continuation, ownership and remaining evidence gaps and synchronize the full latest-five entry. (local)

### 关键 Diff / Key diff

```diff
# Core trusted construction and required arguments
- all manipulation_intent_v2 consumers except execute_subtask require prepare arrays/destination/capability
+ relation.establish consumes a read-only NodeContextProvider and persisted direct grasp Query
+ relation_manipulation_intent(graph, node, context)
+ relation runtime arguments = ("relation_query_result", "candidate_ref")
# Shared Coordinator validation
- resolve_subtask_context owns all caller/record/graph checks inline
+ _resolve_action_context(caller_id, capability)
+ resolve_relation_context -> trusted intent + {tool_id: {arguments, result}}
```

```diff
# Skill compiler and endpoint
+ compose_executable_relation_plan(..., understanding_evidence_ref, semantic_intent, freshness_ms, max_age_ms)
+ scene.bind -> grasp.propose; all four Queries -> relation.establish
+ request["coordinator_context"] = deepcopy(dict(context))
# Adapter source resolution
- embedding must invent/provide a resolver independently
+ build_stack_relation_preparation_inputs(artifact_root, task_name=...)
+ json.loads(_artifact_path(...).read_text())
+ evidence.query == persisted_relation_arguments
+ target_geometry_source = evidence.geometry_source
```

```diff
# Host opt-in and same Coordinator
- return perception_adapter, coordinator.resolve_subtask_context
+ return perception_adapter, coordinator.resolve_subtask_context, coordinator.resolve_relation_context
+ stack_relation_preparation_enabled: bool = False
+ build_stack_relation_execution_provider_factory(prepare_inputs=actual_artifact_resolver)
# Motion remains closed; no worker start is introduced.
```

### 验证与失败分析 / Validation and failure analysis

- [eval] [exp] 主审18套件 **517 passed in12.44s**；新增 context+host 定向组合 **63 passed in5.75s**。真实 Preparation/selector/PreparedRoutes 和 scene_facts/validator 执行，外部规划、碰撞/接触反馈、snapshot 使用 fixture，不能当作完整 GPU route readiness 或真实物理试验。 / Parent review passed517 tests; the focused integration passed63. Production preparation runs with substituted external mechanisms, not live route/physics validation. (local)
- [eval] [fix] 首轮297 passed/2 failed：冗余全局 revision 检查误拒绝合法 discovery provenance，已撤销并使用既有 store 拒绝跨 revision；关联 subtask fixture 缺字段经 HEAD 重现后补初始化。 / Remove the redundant global check and repair the directly related fixture after reproducing the original failure. (local)
- [eval] [exp] 额外 planning_selection 扩展集63 passed/5 failed；三个测试名（含三参数）共5项全部通过 git show HEAD:PhyAgentOS/agent/tools/planning.py 动态载入逐一重现相同 planning_selection_internal_error：test_plan_select_is_control_plane_only_and_returns_binding、test_plan_select_resolves_catalogued_predecessor_source_before_persistence（三参数）、test_missing_node_source_context_requires_plan_recovery。本轮未修改这些旧 fixture。 / All five additional selection-fixture failures reproduce against HEAD and remain outside this change. (local)
- [chore] [fix] Ruff 修复4处 import 顺序与新测试15处单行if；主审对本轮所有改动 Python 文件执行完整 Ruff 检查，全部通过；git diff --check 通过。 / After import/conditional formatting fixes, parent review ran full Ruff checks on every changed Python file; all lint and diff whitespace checks pass. (commit 41ff5c94)
- [docs] [docs] 完成的是生产组合入口与可信准备链；尚缺 Adapter relation Provider 的 observed→execution identity 映射、observed support Provider、真实 route/contact/stop 和三块连续执行。当前目标 artifact 明确为 simulator_actor_geometry；motion_supported 仍 False，client.start=0。 / The production composition entry and evidence chain are complete; identity conversion, observed support and live execution qualification remain, with motion disabled. (local)

```bash
PYTHONPATH=examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q tests/test_planning_dispatch.py tests/test_planning_loop.py tests/test_planning_task_integration.py tests/test_planning_projection.py tests/test_planning_source_assembly.py tests/test_planning_dispatch_bootstrap.py tests/test_planning_end_to_end.py examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py examples/forge-skills/pick-place-workflow/tests/test_relation_execution.py examples/forge-skills/pick-place-workflow/tests/test_relation_target.py examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py examples/forge-adapters/robotwin20/tests/test_stack_relation_execution.py examples/forge-adapters/robotwin20/tests/test_persistent_host.py examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py examples/forge-adapters/robotwin20/tests/test_grounding.py examples/forge-adapters/robotwin20/tests/test_route_inputs.py --tb=short
.venv/bin/ruff check --select I,E701 PhyAgentOS/forge/task.py examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_inputs.py examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py
.venv/bin/ruff check PhyAgentOS/forge/manipulation_context.py examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_inputs.py examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py
git diff --check
```

### Git

- Commit: `41ff5c94`; Branch: `feature/planning-loop`; 时间 / Time: 2026-11-26 16:48:19 +0800.
- [chore] [docs] 主审确认代码提交已成功推送至 `origin/feature/planning-loop`（`142e1606..41ff5c94`）；18套件517项通过，所有改动 Python 完整 Ruff 通过。 / Parent confirmed the code commit was successfully pushed to `origin/feature/planning-loop` (`142e1606..41ff5c94`); all517 tests across18 suites and full Ruff checks for every changed Python file passed. (commit 41ff5c94)

## v18.0.5 (2026-11-26 15:35) - codex

### 计划 / Plan

- [policy] [fix] [完成] 修复 RoboTwin stack 关系路线准备的真实输入链，保留可信 ManipulationIntent、当前抓取/能力证据与关系目标；Adapter 私有组合，不改公共工具或开启运动。 / Repair the real stack preparation input chain with trusted intent, current grasp/capability evidence and the selected relation target through Adapter-private composition; retain public tools and disabled motion. (local)
- [eval] [exp] [完成] 用真实 PersistentPreparationProvider 做无运动集成验证，覆盖成功、缺失/过期/身份漂移、失败不触发动作和输入不变；补接续说明。 / Exercise the real preparation provider without motion, covering success, missing/stale/mismatched evidence, no-action failures and immutable input; document continuation boundaries. (local)
- [model] [docs] 归属：Coordinator 持有任务/修订/结算，AgentLoop 驱动流程，Adapter 组合当前观测准备输入，Provider 负责路线/执行机制；fresh 边界为 scene/observation/calibration，替换外部机制不改调用方，最小泄漏测试直接经过真实 Preparation。不新增 hash/gate。 / Coordinator owns task/revision/settlement, AgentLoop drives workflow, Adapter composes observation-bound inputs and Providers own route/execution mechanisms. Freshness spans scene/observation/calibration; test the real preparation boundary with substituted mechanisms, without new hashes or gates. (local)

- [eval] [fix] [完成] 主审对照HEAD复现12个旧Grounding fixture失败；补object.__new__测试实例的真实reserved entity/actor映射初始化，不改生产默认或放宽身份检查。 / Parent reproduced 12 existing fixture failures against HEAD; initialize test-only reserved entity mappings consistently with production without relaxing checks. (local)

### 结果、精确范围与验证 / Results, exact ranges and validation

- [policy] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_preparation.py` L8-L9、L22、L34-L35、L39-L41、L57-L102、L109-L120、L132-L134：显式可信输入resolver、保留intent与完整route lineage、补task_id；缺resolver明确失败。 / Explicit trusted input resolver, preserved intent/full route lineage and task_id; missing resolver fails explicitly. (local)
- [env] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py` L707-L745、L806-L808：当前绑定投影relation目标与功能点，独立保留目标来源/evidence。 / Project relation targets and functional points from the current binding and retain separate target provenance. (local)
- [env] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_inputs.py` L146-L147、L155-L160：已有Adapter-private facts允许成对目标来源/证据字段，普通类型检查；真实生产validator验证。 / Existing private facts accept paired target provenance fields with ordinary validation. (local)
- [env] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_execution.py` L109、L116-L117：核对生产route_arguments目的地及选中候选placement目标，修复原假fixture隐藏的接口错误。 / Validate actual registered destination and selected placement target, fixing the interface mismatch hidden by the old fixture. (local)
- [eval] [exp] `examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py` L1-L185：真实Grounding/scene validator/Preparation/selector/PreparedRoutes组合；外部规划/控制反馈替换，不是GPU完整路线实测；`tests/test_stack_relation_execution.py` L40、L47更新实际route形态；`tests/test_route_inputs.py` L203-L215覆盖来源缺失/坏证据（两个短路径均相对examples/forge-adapters/robotwin20）。 / Real composition with substituted external mechanisms, actual route fixture and invalid provenance coverage. (local)
- [eval] [fix] `examples/forge-adapters/robotwin20/tests/test_grounding.py` L569-L572、L606-L609、L654-L657、L698-L701、L731-L734、L1054-L1057：补六处Engine fixture的reserved mapping，保留reserved-identity拒绝语义。 / Initialize six Engine fixtures with reserved mappings while preserving identity rejection semantics. (local)
- [docs] [docs] `docs/forge/ROBOTWIN_STACK_CONTINUATION_20261126.md` L1-L44：接续范围、所有权、来源与显式注入示例、准确验证边界。 / Continuation scope, ownership, provenance, injection example and validation boundaries. (local)
- [eval] [exp] 准备/执行/Preparation/route_inputs四套件69 passed；Grounding/host/deployment三套件128 passed，合计197。最初无runtime PYTHONPATH导致14导入失败；补路径后12失败经主审HEAD复现为旧fixture缺初始化，本版修fixture后128通过。 / Four focused suites pass69 and three broader suites pass128 (197 total). Initial import/path and pre-existing fixture failures were diagnosed; fixtures are corrected without production relaxation. (local)
- [docs] [docs] 仍待具体Coordinator evidence resolver、observed支撑Provider、生产成对接线和真实route/contact/stop及三块执行；motion保持关闭。目标来源由私有resolver显式提供，尚未自动读取核验artifact内容。 / Concrete evidence resolution, observed support, production wiring and actual route/contact/stop/stack execution remain; motion stays disabled and artifact provenance content is not yet automatically verified. (local)

### 关键 Diff / Key diff

```diff
- remove intent; forward relation request to preparation
+ resolve trusted current preparation inputs; preserve and validate ManipulationIntent
+ bind selected world target through Grounding; preserve independent target provenance
- return seven route fields; check route_request.destination_ref
+ preserve complete registered route and task_id; check destination and selected placement target
- FakePreparation mirrors invented response
+ real Grounding/validator/Preparation/selector/PreparedRoutes with external mechanism fixtures
```

### 验证命令 / Validation commands

```bash
PYTHONPATH=examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py examples/forge-adapters/robotwin20/tests/test_stack_relation_execution.py examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py examples/forge-adapters/robotwin20/tests/test_route_inputs.py --tb=short
PYTHONPATH=examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/robotwin20/tests/test_grounding.py examples/forge-adapters/robotwin20/tests/test_persistent_host.py examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py --tb=short
```

### Git

- Commit: `c9808c74`; Branch: `feature/planning-loop`; 时间 / Time: 2026-11-26 15:50:06 +0800.
- [chore] [docs] 主审确认代码提交已成功推送至 `origin/feature/planning-loop`；review验证197项测试通过。 / Parent confirmed the code commit was successfully pushed to `origin/feature/planning-loop`; review validation passed all197 tests. (commit c9808c74)

## v18.0.4 (2026-11-26 14:18) - codex

### 计划与归属 / Plan and ownership

- [policy] [fix] [完成] 132940任务首次R03 process_features stale已由既有机制刷新scene:3；随后grasp-affordance Preparation因请求calibration多一个0返回stale但缺少既有evidence恢复字段，Agent未接入query_evidence确定刷新分支并stop，预算未耗尽。补齐通用Preparation端确凿stale的failure_owner/code、known/no-world-change、requires_replan与refresh_declared_evidence语义；保留原identity/error及motion_authorized=false，不静默修复opaque引用，invalid/unavailable/exception不伪装stale。 / [Completed] The first stale process query already recovered through the existing scene refresh, but the later stale grasp-affordance preparation lacked evidence-recovery fields and stopped before the budget was exhausted. Add existing evidence-refresh diagnostics only to definite stale outcomes, preserving identity/errors and no-motion semantics without repairing opaque references or relabelling other failures. (local)
- [policy] [fix] [完成] 调整AgentRecoveryDecisions提示，区分只读证据刷新、已知Action失败与未知物理后果；沿用_evidence_refresh_kind、声明scene-refresh Query及Coordinator预算/生命周期，保持unknown Action不能重试/下游运动。 / [Completed] Clarify recovery guidance for read-only evidence failures, known Action failures and unknown physical effects. Reuse declared refresh Queries and Coordinator-owned budget/lifecycle, retaining unknown-action restrictions. (local)
- [eval] [exp] [完成] Provider-neutral替代fixture覆盖输入身份/过期/provider身份与status stale、schema、invalid/unavailable不刷新；真实Preparation回执→execution record/settlement→Agent恢复replan→仅声明refresh Query，验证已完成动作保留、预算/unknown回归。按相关风险跑集中无运动测试，不启动仿真。 / [Completed] Test provider-neutral stale branches/schema and non-stale failures, then the real endpoint-to-settlement-to-Agent refresh path with completed-action preservation and budget/unknown regressions. Run focused no-motion tests only. (local)
- [model] [docs] 架构：通用endpoint拥有stale领域诊断；Provider拥有capture/候选匹配；替换Provider不影响调用者；fresh边界为新capture/scene/calibration整链；Coordinator独有修订/预算/settlement/恢复；最小泄漏测试为替代Provider同stale导向同声明Query、无R03或Isaac特判。沿用anti-minimal、robotics-safety、experiment-reproducibility；不新增hash/gate/schema机制。 / Ownership: the generic endpoint supplies stale diagnostics, Providers match captures/candidates, fresh evidence spans the new capture/scene/calibration chain, and the Coordinator retains sole lifecycle ownership. A replacement provider must yield the same declared refresh without environment/object special cases. Apply the three repository skills without new defensive mechanisms. (local)
- [docs] [docs] [完成] 保存旧task/events stop理由、修复诊断、精确行号/diff与测试结果。后续仅在实验harness一次性注入R03 calibration错字验证真实恢复，并保持双窗无字配置；本轮不实现/启动新sim、不改旧终态、不commit/push，待主审。 / [Completed] Document original stop evidence, the fix and exact validation. A later authorized experiment may inject one preparation-reference typo through the harness and retain the dual views; this patch does not start simulation, alter prior outcomes or commit/push. (local)

### Git 来源 / Git source

- [chore] [docs] v18.0.3收尾提交2e27eb23已由主审确认push，branch feature/planning-loop；本次以其为代码/文档来源。 / Parent confirmed the preceding closeout commit2e27eb23 was pushed on feature/planning-loop; use it as this patch's source. (commit 2e27eb23)

### 单次故障恢复实跑准备计划 / One-shot recovery-run preparation plan

- [eval] [exp] [完成] 2026-11-26T14:30:36.608227+08:00主审授权仅准备`out/labutopia-elevated-20261126/v18.0.4-r05-r03-evidence-recovery-143036`，从132940复制11必要配置/脚本、不带DB/工件；保持原双窗无字、运动阈值/原指令、replan4、provider retry12/delay15、execute2700/3600。local host在首次R03 Preparation入口仅修改deepcopy请求的calibration_ref一次，再调用原生产endpoint/Provider，保存原/改参数及实际响应；后续透传，Agent/Coordinator自己恢复，不伪造成功。 / [Completed] Prepare one isolated run from132940 without old databases/artifacts. Preserve all recording/motion/instruction/budget/timeouts; inject one calibration-reference typo into a copied first R03 preparation request at the local host endpoint boundary, call the real endpoint/provider and record both requests plus the actual result. Subsequent calls pass through and recovery remains Agent/Coordinator-owned. (local)
- [eval] [docs] 普通持久record.arguments可能为注入前参数，fault-injection.json单独说明边界后的实际参数；不称本次故障为LLM随机拼错。只做无运动harness检查/配置差异与语法检查，主审提交后再更新实际code metadata；当前未启动。 / Persisted invocation arguments may precede injection; the separate fault receipt identifies actual endpoint-boundary arguments. Do not attribute the injected fault to the model. Validate only the harness/configuration/syntax and refresh code metadata after review; do not launch. (local)

### 结果与验证 / Result and validation

- [policy] [fix] Preparation确凿stale统一输出既有evidence刷新诊断；invalid/unavailable/异常保持原状态，即使省略identity也不误转stale。实时与持久投影显式false/true一致。Agent提示区分只读刷新、已知Action失败及unknown；生产不含R03特判、引用修复或新的恢复owner。 / Definite stale preparations now carry existing refresh diagnostics, while other failures retain their status. Explicit no-motion/known-outcome fields align live and persisted projections; guidance separates Query refresh and known/unknown Action outcomes without object-specific production behavior. (local)
- [eval] [exp] 集中5文件234passed/10.28s，PlanningLoop预算与unknown子集17passed/2.50s（148 deselected），共251；五个改动生产/测试文件Ruff通过，diff检查通过。真实端点→live/persisted settlement→Agent replan→仅scene.observe→Coordinator预算/历史Action保留；Lab同scene-super接线及fresh continuation只续R03亦通过，unknown/partial保持原拒绝。 / Focused suites pass251 tests, lint and diff checks. The real endpoint reaches identical settlements and an existing Query-only recovery with Coordinator budget/history preservation; actual Lab superclass continuation retains completed work and unknown/partial restrictions. (local)
- [eval] [exp] 143036目录准备完成：11源文件中7字节相同、3仅路径改变，唯一其余差异为local host一次性注入。真实endpoint的无运动harness检查通过（R05正常→一次R03 stale→下一次正常、原参数不变）；正式目录无fault receipt/DB/artifacts。资源RAM21Gi/GPU8573MiB空闲、/home48Gi、/tmp11Gi，无旧Isaac进程。当前仅准备，未启动；metadata待主审实际新commit。 / The isolated run is prepared with seven byte-identical files, three path-only changes and one local injection harness. Its no-motion endpoint check passed without creating run evidence; resources are recorded and the full simulation remains unstarted pending the reviewed commit. (local)
- [docs] [docs] 新诊断文档保存event2063既有scene恢复与event2103实际stop理由，明确旧live三字段null与persisted推断差别；本轮不改旧task终态。原始恢复事件、测试输出、配置diff和harness检查保留于新目录。来源2e27eb23已push，本patch暂不提交/推送。 / Document both old recovery decisions and distinguish live null diagnostics from later replay inference. Preserve previous outcomes and local validation artifacts; source2e27eb23 is pushed, while this patch remains uncommitted. (local)

### 精确变更范围 / Exact changed ranges

- [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/grasp_task_affordance.py` L141-L147、L227-L247、L279-L289：恢复字段schema、stale分支与统一诊断 / existing recovery fields, stale branches and helper。 (local)
- [修改 / Modified] `PhyAgentOS/agent/recovery_decisions.py` L500-L507：只读证据刷新与未知物理后果提示 / Query-refresh versus unknown-effect guidance。 (local)
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_grasp_task_affordance.py` L3-L7、L177-L249：stale/非stale替代Provider和schema / replacement-provider status/schema cases；`tests/test_agent_foundation.py` L3583-L3704：live/persisted到有界恢复与完成历史 / projection-to-bounded-recovery history；`examples/forge-adapters/isaacsim_lab/tests/test_subtask_continuation.py` L29、L185-L220、L230-L254：实际Lab同scene-super与原fresh continuation / actual Lab same-scene superclass path。 (local)
- [新增 / Added] `docs/forge/LABUTOPIA_AFFORDANCE_STALE_RECOVERY_20261126.md` L1-L44：旧失败、归属、测试命令和待启动实验 / failure, ownership, tests and unstarted experiment。 (local)
- [本地 / Local] `out/labutopia-elevated-20261126/v18.0.4-r05-r03-evidence-recovery-143036/host_with_replay_timeout.py` L1-L53：保留2700s transport、仅local边界一次注入；11源文件configuration.diff、metadata、harness-check和测试日志不作为生产提交 / retain timeout and add one local fault, with config and validation artifacts kept local。 (local)

### 关键 Diff / Key diff

```diff
- stale preparation -> status/error/motion_authorized only
+ stale preparation -> original identity/error + failure_owner=evidence
+ world_change_started=false; outcome_known=true; retryable_in_revision=false
+ requires_replan=true; recommended_action=refresh_declared_evidence
- recovery prompt: without world_change_started=true, reconciliation or stop
+ read-only evidence failure -> declared refresh Query; unknown effects remain unresolved
+ local experiment only: copy first R03 request -> one calibration typo -> real endpoint
+ no new motion/Coordinator/Provider mechanism; original arguments and task history retained
```


### 实际提交与启动计划 / Commit receipt and launch plan

- [chore] [docs] 主审已提交并核验push：43e45bd6562d1242bc524456297271c262294753，feature/planning-loop，2026-11-26T14:37:16+08:00；本轮实际使用该代码。 / Parent committed and verified the pushed revision43e45bd6562d1242bc524456297271c262294753 on feature/planning-loop at2026-11-26T14:37:16+08:00; this is the run code. (commit 43e45bd6)
- [eval] [exp] [完成] 2026-11-26T14:38:51.852600+08:00主审授权启动143036唯一完整R05→R03任务。保持原参数/指令、12次Provider重试/15s间隔、replan4与双窗无字，不启用observer；一次性local calibration故障后由Agent自行刷新。记录PID/时间/实际回执，完整保留所有动作段至终态；不人工修请求、不重启或改生产。 / [Completed] Launch the single approved143036 task with unchanged instruction, motion, retries, budget and unlabelled dual views. Let the Agent recover from the one local calibration fault; preserve process receipts and every action clip through settlement without manual request repair or restart. (local)
- [eval] [docs] [完成] 按实际receipt时间顺序合成全部动作段为R05_R03_自主恢复_全局与腕部.mp4，验证H264/yuv420p2560×960/60fps、帧数/PTS/完整decode/首末画面；保存fault原改参数、task/events/receipts、恢复时间线与配置/code证据，区分无运动测试和本轮无液体执行。终态后同步报告与Latest5，交主审且不commit/push。 / [Completed] Compile every actual clip in receipt order without cards/text, validate media properties, frame timing and full decoding, and preserve the fault and recovery evidence. Synchronize final documentation for parent review without committing or claiming liquid transfer. (local)

### 143036 实跑收尾 / Live recovery closeout

- [eval] [exp] 2026-11-26T14:38:51.853577+08启动task_3886ebe6c8bf4b68，launcher1527769/host1527770/worker1530951；15:39:59.837558+08终态succeeded，11 revisions、2/4 replans、last_failure=null，三个PID均退出。实际代码43e45bd6已push；本轮无重启/重复任务、无人为修请求或运动参数修改。 / The single task started at14:38:51 and settled succeeded at15:39:59 with11 revisions and2/4 replans; all processes exited. It used pushed43e45bd6 with no restart, duplicate task or manual request/motion changes. (local)
- [policy] [exp] 受控calibration错字仅注入一次：15:08:06将136a73fa…→0136a73fa…，真实Preparation返回stale、known/no-world-change及refresh_declared_evidence。event2067由现有query_evidence确定replan，新revision_fa9231281d9d4d85首记录scene.observe，继而原continuation重建calibration=e984fbc…/candidate_set=9de984…/selected=c6ab78…并成功准备R03；旧candidate=0aed617…/selected=bbdee6…。 / One controlled endpoint-boundary typo produced a real stale result and the existing Query-only recovery; fresh capture/calibration/candidates then enabled R03 preparation. (local)
- [sense] [docs] 新capture/calibration/candidates已经更新；observation_ref仍为scene:3/sensor标识，物理scene未变，不声称所有ref字符串变化。持久arguments可能为注入前值，fault-injection.json保留原/改参数和实际响应；故障不是LLM再次随机打错。先前event2027的scene:0→:3恢复与本次同scene故障分开记录，4条历史evidence_errors保留。 / A new capture regenerated calibration/candidates while the scene:3/sensor observation identity remained unchanged. Preserve pre/post-injection requests and distinguish this controlled fault from both model errors and the earlier scene refresh, retaining all four historical recovery messages. (local)
- [eval] [exp] R05/R03实际Action各1（tool_a1914159202f4c85/tool_634db4643bc14d27），六阶段均succeeded，两瓶completed/outcome_known=true/empty/requires_replan=false。R05 lift117/117、rise60.074618104mm、末attachment0.047140511mm、tilt1.001442185rad、hold2.816666814s、归位0.202404870mm；R03分别118/118、60.093074015mm、0.024408880mm、1.001487669rad、2.866666816s、0.164189428mm，末旋转误差0.000907724rad。末retreat双指约0.04m/contact与grasp=false。 / Both Actions ran once and all six phases succeeded, ending released and empty. Record measured lift, attachment, tilt/hold and return errors for each bottle; final open fingers and absent load/grasp confirm release. (local)
- [eval] [exp] R03 pour fresh scene:4的132steps（85transport/11process/36exit）全检查通过，使用process_only_lowest_qualified_opening_rim；两瓶motion_goal_reached但transfer_verified=false、液体量未测。251项无运动契约/接线测试与本轮真实Provider/Agent/动作证据分别保留，不重复跑测试。 / R03's fresh-scene132-step derived-rim route passed all checks. Motion goals were reached without liquid-transfer verification; distinguish the existing251 contract tests from live provider/recovery/execution evidence. (local)
- [eval] [docs] 成片R05_R03_自主恢复_全局与腕部.mp4按receipt顺序包含全部6段2112/3561/1455/3696/3923/1925帧，共16672帧/277.866667s；H264/yuv420p2560×960/60fps、0章节，无卡/叠字/新增空白，未替换旧帧或重建。源视频与receipt集合一致、PTS最大误差0.333微秒、完整decode exit0且日志空；成片首末目视正常，主审已独立核对terminal-summary、恢复链、ffprobe、manifest、Latest5及首末/倾倒三张实际帧，全部通过，无Blocker/Major。 / All six original clips form the unlabelled dual-view video with16672 frames/277.866667seconds. Parent independently verified the terminal summary, recovery chain, ffprobe, manifest, Latest5 and actual first/last/tilt frames; all passed without Blocker/Major findings. (local)
- [docs] [docs] 保存原始acceptance/task/events/receipts、fault、lineage、recovery-summary/timeline、phase/release evidence与视频manifest；metadata关联实际code/config。主审验收完成，交主会话提交归档；保留并行v18.0.5日志与文件。 / Preserve raw and compact task/fault/recovery/release/video evidence linked to code/config. Parent acceptance is complete; hand off to the main session for archival commit while preserving concurrentv18.0.5 work. (local)

### 收尾行号与 Diff / Closeout ranges and diff

- [修改 / Modified] `docs/forge/LABUTOPIA_AFFORDANCE_STALE_RECOVERY_20261126.md` L47-L76：追加真实受控故障、恢复链、六阶段测量和视频验收 / append controlled-fault recovery, six-phase metrics and video acceptance。 (local)
- [修改 / Modified] `changelog/2026-11_part5.md` L524-L554、`CHANGELOG.md`当前v18.0.4完整条目：本次启动/收尾计划完成与实测回执；旧准备时点保留，Latest5读取当前月档同步，保留并行版本 / complete this run's plans and receipts while preserving historical preparation and concurrent versions。 (local)
- [本地 / Local] 143036的`extract_terminal_evidence.py` L1-L108、`compile_live_video.py` L1-L107、metadata/launch/fault/recovery/media工件：只读归档及完整原视频拼接，不进入生产或stage整个out / read-only evidence extraction and complete original-video compilation, without production changes or staging outputs。 (local)

```diff
- full run: launch/terminal evidence pending
+ code43e45bd6; one controlled calibration typo; real stale -> Query refresh
+ new capture/calibration/candidates; same scene:3 observation identity
+ preserved R05 Action; R05 and R03 each executed once; six phases succeeded
+ task succeeded; replans2/4; last_failure=null; historical recovery errors retained
+ final released/empty; liquid transfer remains unverified
+ complete dual-view video16672frames/277.866667s; no cards/text; decode passed
```

### Git 提交与推送回执 / Commit and push receipt

- [chore] [docs] 主审已提交收尾结果：`441e9d86b03084d0b0e6f3c820c065279e9a5dce`；branch `feature/planning-loop`；实际提交时间 `2026-11-26T15:57:19+08:00`（git show）；提交说明 `v18.0.4: [eval] 归档标定引用故障自主恢复与双视角实跑结果`。主审确认已成功push至`origin/feature/planning-loop`。 / Parent committed the accepted closeout as `441e9d86b03084d0b0e6f3c820c065279e9a5dce` on `feature/planning-loop` at `2026-11-26T15:57:19+08:00` (git show), and confirmed a successful push to `origin/feature/planning-loop`. (commit 441e9d86)
