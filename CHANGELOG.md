# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

- [2026-10_part9](changelog/2026-10_part9.md)
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

## v16.0.3 (2026-10-24 09:35) - codex

### 变更摘要 / Summary [完成 / Completed]
- [eval] [exp] 用 LocateAnything 缩放输入定位同一场景右侧锥形瓶，SAM2 分割后以同一 mask 对比 raw-depth 与 ReMake 的深度、点云和 GraspNet 位姿。 / Used scaled LocateAnything input to locate the right-side flask in the same scene, then compared raw-depth and ReMake depth, clouds, and GraspNet poses from one SAM2 mask. (local)
- [docs] [feat] 生成目标裁剪五行左右双列图、完整中间 artifact、数值摘要和 DFNet 待权重说明；DFNet 官方入口访问失败，未伪造第三模型结果。 / Generated the cropped five-row paired image, intermediate artifacts, metrics summary, and DFNet checkpoint note; official DFNet download access failed, so no third-model result was fabricated. (local)

### 文件变更详情 / Change Details
- [新增 / Added] `scripts/render_locateanything_remake_grasp_comparison.py:L1-L212`：渲染同目标 RGB、分割、深度、点云和抓取位姿。 / Renders paired RGB, segmentation, depth, cloud, and grasp-pose rows for one target.
- [新增 / Added] `docs/diagnostics/transparent-model-comparison-20261023-locateanything.md:L1-L63`：记录实际流程、指标、复现命令和安全边界。 / Records the actual flow, metrics, reproduction command, and safety boundary.
- [修改 / Modified] `docs/diagnostics/transparent-model-comparison-20261023.md:L85-L116`：并入五行对比图、错误原因和修复说明。 / Appended the five-row comparison, failure causes, and fixes.
- [新增 / Added] `docs/reports/transparent-model-selection-report-20261024.md:L1-L76`：汇报同场景结果、错误修复、证据边界及暂定选型；明确 DFNet 待权重。 / Reports same-scene results, failure fixes, evidence limits, and provisional selection; marks DFNet as awaiting weights.
- [新增 / Added] `docs/diagnostics/assets/transparent-model-comparison-20261023-locateanything/*`：保存图、mask、点云、LocateAnything 响应及候选摘要。 / Saves the image, mask, clouds, LocateAnything response, and candidate summary.

### 验证 / Validation
- LocateAnything/SAM2/GraspNet/渲染完成；图像尺寸 `1280x2160`，mask 与两路点云均为 `25,546`。 / Completed; image is `1280x2160`, mask and both clouds contain `25,546` entries.
- GraspNet 解码 raw/ReMake 分别为 `915/259`，各保留 `32`；未执行运动。 / Raw/ReMake GraspNet decoded `915/259` and retained `32` each; no motion was executed.
- DFNet 未运行：本地 checkpoint 缺失且官方入口本轮无法下载；报告未将此写成效果结论。 / DFNet was not run: the local checkpoint is missing and official download endpoints were unavailable; the report does not treat this as an effect result.
- Commit/Push: pending.

## v16.0.2 (2026-10-23 19:02) - codex

### 结果 / Outcome [未完成：LocateAnything 模型文件缺失且网络不可达 / Incomplete: LocateAnything model files missing and network unavailable]
- [eval] [exp] 验证 LocateAnything 配置及专用 CUDA 环境；缺少完整缓存且 Hugging Face 不可达，未生成模型框、SAM2 配对分割或 GraspNet 对比。 / Verified LocateAnything configuration and dedicated CUDA environment; incomplete cache and unreachable Hugging Face prevented model boxes, paired SAM2 segmentation, or GraspNet comparison. (local)
- [docs] [docs] 在月度日志记录复跑条件与证据边界；未使用旧实例框冒充 LocateAnything 输出、未借用其他目标抓取位姿。 / Logged rerun prerequisites and evidence limits; did not relabel old instance boxes as LocateAnything output or borrow grasps from other targets. (local)

### 变更详情 / Change Details
- [修改 / Modified] `changelog/2026-10.md:L3-L11` 记录计划、模型加载实测失败阶段和恢复条件；未修改诊断图或推理结果。 / Recorded plan, observed model-load failure phase, and recovery conditions; no diagnosis image or inference result was changed.

### 验证 / Validation
- 专用环境确认 Torch 2.8.0+cu128/CUDA 可用；LocateAnything `AutoProcessor.from_pretrained` 因缺少 `processor_config.json` 并尝试连接 Hugging Face 而失败（网络不可达）。 / Dedicated Torch 2.8.0+cu128/CUDA available; `AutoProcessor.from_pretrained` failed because `processor_config.json` was missing and Hugging Face was unreachable.
- 当前记录帧无 LocateAnything 调用结果；因此不能合法声称完成用户要求的左/右模型位姿对比。 / The recorded frame has no LocateAnything result; the requested left/right model-pose comparison cannot be claimed as completed.
- Commit: `9270d9f3`; Branch: `feature/planning-loop`; Push: 已成功推送至 `origin/feature/planning-loop`。 / Successfully pushed to `origin/feature/planning-loop`.

## v16.0.1 (2026-10-23 13:38) - codex

### 变更摘要 / Summary [完成 / Completed]
- [eval] [exp] 基于同一第三人称 RGB-D、实例 mask 和标定，对比 raw-depth 基线、ReMake 与 DFNet 状态，聚焦工作流目标锥形瓶。 / Compared raw depth, ReMake and DFNet status on one third-person RGB-D capture, focusing on the workflow conical-flask target. (local)
- [docs] [feat] 生成全景及逐目标可视化、数值摘要和模型选型诊断；DFNet 不可用时明确显示无输出。 / Generated panorama/target visualizations, metrics and model-selection diagnosis; unavailable DFNet is shown without fabricated output. (local)

### 文件变更详情 / File Change Details

#### [新增 / Added] `scripts/render_transparent_model_diagnosis.py` L1-L277

```diff
+raw_cloud_target = raw_mask_cloud(target_mask, raw_depth, intrinsics)
+target_strip.save(args.out / "target-conical-flask-comparison.png")
+overview.save(args.out / "panorama-model-comparison.png")
```

#### [新增 / Added] `docs/diagnostics/transparent-model-comparison-20261023.md` L1-L84

```diff
+| raw depth | mask 内 q50≈2.043 m；历史 cloud 3,213 点 | 失败/未验证基线 |
+| ReMake | 恢复 cloud 4,100 点；geometry qualification 未验证 | 下一轮主候选 |
+| DFNet | 缺 checkpoint，无可比较输出 | 补权重后重跑 |
```

#### [新增 / Added] `docs/diagnostics/assets/transparent-model-comparison-20261023/*`

- `panorama-model-comparison.png`：RGB/mask、raw/ReMake depth、union mask 和全景点云。 / RGB/masks, raw/ReMake depth, union mask and panorama clouds.
- `target-conical-flask-comparison.png`：目标锥形瓶 RGB/mask、depth、共享范围点云和候选状态。 / Target-flask RGB/mask, depth, shared-range clouds and candidate status.
- `target-summary.json`：目标引用、mask/cloud 计数及无候选原因。 / Target reference, mask/cloud counts and no-candidate reason.

### 验证 / Validation
- 离线渲染成功：全景 `1280x1572`，目标图 `1280x2096`；JSON 引用和图片读取均通过。 / Offline rendering passed: panorama `1280x1572`, target view `1280x2096`; JSON references and PNG decoding passed.
- 目标为 `mixing_vessel`，4,100 mask 像素/点；候选数 0 是因其未作为抓取源，不代表模型失败。DFNet run 因缺权重失败。 / Target is `mixing_vessel`, with 4,100 mask pixels/points; zero candidates reflects its exclusion as a grasp source, not model failure. DFNet run lacks weights.
- 未执行运动；模型深度无独立真值精度结论。 / No motion; no independent ground-truth accuracy claim.

### Git 提交 / Git receipt
- Commit: `085de764`; Branch: `feature/planning-loop`; Push: 两次尝试超时，远端未确认 / two attempts timed out; remote receipt unconfirmed.

## v16.0.0 (2026-10-23 12:51) - codex

### 变更摘要 / Summary [完成 / Completed]
- [sense] [feat] 实施透明几何恢复 Provider（ReMake 主候选、DFNet 对照）和进程 worker，复用既有 artifact、SAM2、GraspNet 接缝；加入显式输入单位/范围/尺寸适配与可复现回放。 / Implement a transparent-geometry provider and process worker (ReMake primary, DFNet comparison), reusing artifact/SAM2/GraspNet seams with explicit unit/range/size adaptation and reproducible replay. (local)
- [sense] [fix] 分离视觉实体与私有执行对应，保存逐对象失败，删除无证据的最高边瓶口/可见棒端推断及深度有效比例伪置信度；原始/估计几何和功能点证据分别保留。 / Separate visual entities from private execution correspondence, persist per-object failures, remove unsupported top-edge rim/visible-endpoint inference and depth-validity pseudo-confidence, and preserve raw/estimated geometry and feature evidence separately. (local)
- [eval] [exp] 先写替换/失败路径测试，再接真实模型并回放原场景；准备不足时不发运动；继续保存真实失败和本任务未完成边界。 / Write substitution/failure tests before wiring real models and replaying the original scene; issue no motion without readiness and retain real failures and incomplete acceptance boundaries. (local)
- [docs] [chore] 补全诊断/实施记录、精确行号/Diff、验证及提交回执，只提交 PAOS 当前分支；模型源码/权重在仓库外缓存，LabUtopia 不提交。 / Complete diagnosis/implementation records, precise lines/diffs, validation and receipts on the current PAOS branch only; keep model sources/weights in external cache and do not commit LabUtopia. (local)

### 定级与责任 / Version and ownership
本次为显著新机制 minor，15.10.2 的 minor 达上限后进位至 16.0.0。通用层拥有语义、实体/候选与生命周期；可替换 Provider 拥有模型机制；Isaac Adapter 拥有相机和私有物理对应。沿用 observation/revision/frame/calibration 新鲜度及 Runtime/Coordinator 的持有、取消、结算。最小替换测试验证无仿真映射的 RGB-D 仍可生成模型候选、两个恢复机制不改变调用者；缺功能点/模型故障/过期/候选篡改均不能通过准备。不新增 hash 或第二套门禁/状态机。 / This is a significant minor feature, rolling 15.10.2 to 16.0.0 at the minor limit. Generic code owns semantics/entities/candidates/lifecycle; replaceable providers own models; Isaac owns cameras/private physics correspondence. Preserve capture freshness and Runtime/Coordinator possession/cancellation/settlement. Substitution tests cover simulator-independent RGB-D queries and two recovery mechanisms; missing features, model failures, stale evidence and altered candidates cannot qualify. No additional hash or parallel lifecycle/gate.

### 预计范围 / Planned scope
现有 v15.9.0/v15.10.0 的任务文件，新增可复用几何 Provider/worker 与测试，Isaac 感知/身份/探针/配置及必要准备接线、诊断/验收/日志。 / Existing task-owned v15.9.0/v15.10.0 files plus reusable geometry provider/worker/tests, Isaac perception/identity/probe/configuration and necessary readiness wiring, diagnosis/acceptance/logs.

- [sense] [fix] [完成 / Completed] 在 PAOS 保存 ReMake 推理依赖补丁，仅删除上游模型未使用的可视化导入，并应用到仓库外专用缓存；不改模型计算。恢复预处理插值与上游一致。 / Track an inference-only ReMake patch removing an unused visualization import in the external model cache; preserve model math and upstream interpolation. (local)

- [sense] [fix] [完成 / Completed] 抓取查询现契约强制有带数值置信度的 envelope；实际 GraspNet/GraspGen Provider 均支持已绑定点云。允许有非空 geometry_artifacts 时不传 envelope，保留原 envelope 路径和来源校验，避免为未知几何编造置信度。新旧输入均加测试。 / Permit geometry-only grasp queries for the independent GraspNet/GraspGen mechanisms; preserve legacy envelope validation and bound-cloud lineage without invented confidence. Test both forms. (local)

- [sense] [fix] [完成 / Completed] 实测 ReMake 远景输出有约米级偏移，且旧单点深度连通过滤切断恢复表面；恢复链只按模型有效值与实例 mask 投影，原始深度过滤不再参与。准备仍拒绝未验证几何，具体失败是把偏移点云/局部棒段用于运动，既有碰撞检查不能验证几何正确性。 / Measured far-view ReMake output has metre-scale shifts; remove raw-depth seed connectivity from restored clouds. Existing preparation rejects unverified geometry because collision checking cannot establish reconstruction correctness or hidden payload coverage. (local)
- [policy] [fix] [完成 / Completed] 同步 Agent 参数投影支持点云独立输入，保持歧义 envelope 拒绝与缺来源失败，测试标准查询和 Agent 投影两个入口。 / Support cloud-only Agent projection while preserving ambiguous-envelope rejection and missing-evidence failures; test both entry points. (local)

### 实际结果 / Actual outcome

- [sense] [feat] 已交付可替换恢复 Provider、实际 ReMake/DFNet worker 实现、来源侧车、纯感知实体、标准点云抓取及 Agent 投影；恢复与抓取不读取仿真几何。 / Delivered replaceable recovery providers, actual model backends, lineage sidecars, sensor-owned identities and cloud-only grasp/Agent projection. Recovery and grasp inference do not read simulator geometry. (local)
- [sense] [fix] 已删除最高边瓶口、可见棒端和原始深度种子连通规则；执行对应只在准备側进行，当前源与目标功能点共同刷新，不重写 acquisition 候选。 / Removed top-edge rim, visible-endpoint and raw-depth seed rules; private correspondence occurs at preparation and both process endpoints refresh without rewriting acquisition candidates. (local)
- [eval] [exp] 第三人称原观测回放产生 13 点云/256 个真实 GraspNet 候选；腕部新观测产生 11 点云/192 候选。官方模型同帧数值对照最大差 0 m。 / Recorded third-person replay produced 13 clouds/256 actual GraspNet candidates; a fresh wrist capture produced 11 clouds/192 candidates. Same-input upstream arithmetic comparison had maximum difference 0 m. (local)
- [eval] [exp] 完整动作验收仍未通过：远景恢复位置偏移、腕部自遮挡、标签不可读和棒端不明。DFNet 权重官方下载配额限制，未运行训练权重推理。未执行机械臂运动。 / Full action acceptance remains open: displaced far-view estimates, wrist self-occlusion, unreadable labels and unknown rod endpoint. DFNet's official download quota prevented trained inference. No arm motion was executed. (local)
- [docs] [docs] 保存诊断、实施进展、结构化证据、同尺度深度对比图、部署复现说明和审查。仅 PAOS 提交；LabUtopia 保持原提交 `61e1fba`。 / Saved diagnosis, progress, structured evidence, equal-scale depth comparison, reproduction instructions and review. Commit PAOS only; LabUtopia remains at 61e1fba. (local)

### 重点前后差异 / Focused before-after excerpts

以下“修改前”来自本次修复前的任务代码；完整提交还纳入此前同任务未提交的接入文件。 / Before snippets refer to pre-refactor task code; this commit also incorporates earlier pending integration files from the same task.

```diff
- rim = points[points[:, 2] >= high[2] - .004]
- tip = points.mean(0) + axis * np.max((points - points.mean(0)) @ axis)
+ if not support:
+     raise ValueError("process features require explicit image landmark support")
+ if support.get("fully_visible") is not True:
+     raise ValueError("required process landmarks are not fully visible")
- confidence = float(claim["confidence"]) * measured.valid_depth_ratio
+ # No spatial envelope/object_geometry confidence is invented for an
+ # unqualified model estimate. Grasp Query accepts point clouds alone.
- result = self.engine.bind_observed_entities({**request, "claims": claims})
+ # Correspondence moved to _bind_execution in the preparation boundary.
+ # Public entities and candidate poses originate in observed/model evidence.
```

### 文件、行号与关键 Diff / Files, exact ranges and key diffs

摘录仅展示关键增删行；完整内容见同版本 Git diff。 / Excerpts show selected changed lines; the same-version Git diff contains complete changes.

- [sense] [refactor] [修改 / Modified] `PhyAgentOS/agent/tools/forge_task.py` L233-L243, L299-L306：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+                        "semantic_intent": {
+                            "type": "object", "additionalProperties": False,
+                            "required": ["goal", "success_criteria", "allowed_arms", "coordination_mode"],
+                            "properties": {
+                                "goal": {"type": "string", "minLength": 1},
```

- [sense] [refactor] [修改 / Modified] `PhyAgentOS/forge/binding.py` L332-L333, L336-L338, L468-L471：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-    def __init__(self, runtime_registry: Any, *, catalog: SkillCatalog | None = None) -> None:
-        manifest = self.catalog.get(runtime.skill_name)
-        if tool_id not in manifest.required_tools:
+    def __init__(self, runtime_registry: Any, *, catalog: SkillCatalog | None = None,
+                 authorized_tool_ids: frozenset[str] | None = None) -> None:
+        self.authorized_tool_ids = authorized_tool_ids
+        authorized = self.authorized_tool_ids
+        if authorized is None:
```

- [sense] [refactor] [修改 / Modified] `PhyAgentOS/forge/capability_runtime/grasp_proposal.py` L119-L121, L398-L398, L406-L430, 删除旧 / deleted old L423-L426, L827-L827：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-                    "required": ["entity_ref", "category", "confidence", "spatial_envelope"],
-        or not {"entity_ref", "category", "confidence", "spatial_envelope"} <= set(target)
-    envelope = target["spatial_envelope"]
+                    "required": ["entity_ref", "category", "confidence"],
+                    "anyOf": [{"required": ["spatial_envelope"]},
+                              {"required": ["geometry_artifacts"], "properties": {"geometry_artifacts": {"minItems": 1}}}],
+        or not {"entity_ref", "category", "confidence"} <= set(target)
+    if "spatial_envelope" in target:
```

- [sense] [refactor] [修改 / Modified] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py` L348-L348：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+        "grasp_candidates": {"type": "array", "items": {"type": "object"}},
```

- [sense] [refactor] [修改 / Modified] `PhyAgentOS/forge/capability_runtime/understanding.py` L304-L304, L391-L401, L623-L625, L905-L906, L911-L911：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-            or set(entity) != {"entity_ref", "category", "confidence", "provenance"}
-            or set(entity) != {"entity_ref", "category", "confidence", "provenance"}
+                        "label": {"type": "string", "minLength": 1},
+}
+TOOL_SPEC["output_schema"]["properties"]["views"] = {
+    **deepcopy(TOOL_SPEC["input_schema"]["properties"]["views"]),
+    "minItems": 0,
```

- [sense] [refactor] [修改 / Modified] `PhyAgentOS/forge/task.py` L1289-L1293, L1308-L1308, L4501-L4506：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+        selected_scene_revision = next((
+            trace.scene_revision for trace in task.active_revision.planning_selections
+            if trace.resumable_selection is not None
+            and trace.resumable_selection.planning_binding.decision_trace_ref == record.decision_trace_ref
+        ), intent.scene_revision)
```

- [sense] [refactor] [修改 / Modified] `PhyAgentOS/planning/projection.py` L432-L432, 删除旧 / deleted old L438-L438, L448-L462, L488-L490：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-    if len(envelopes) != 1:
-    envelope = envelopes[0]
-    target[plan.envelope_output_field] = {
+    if len(envelopes) > 1:
+    if envelopes:
+        envelope = envelopes[0]
+        target[plan.envelope_output_field] = {
+            field: envelope[field]
```

- [docs] [refactor] [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V15_8_0.md` L1-L194：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+Date: 2026-10-23, Asia/Shanghai
+The target is an Agent-directed, no-liquid Isaac Sim task: identify REAGENT A
+and REAGENT B from visible labels, acquire/pour/return each bottle, then
+acquire/stir/return STIR ROD in the same BEAKER. The full physical task remains
+open pending one complete Agent task. Camera capture, task
```

- [docs] [refactor] [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V16_0_0.md` L1-L46：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+2026-10-23。审查范围为 PAOS 的可替换几何恢复、视觉实体、点云抓取查询和准备边界。本阶段交付查询接入；完整 Agent 混合搅拌任务尚未验收。使用 anti-minimal-implementation、robotics-safety-implementation、experiment-reproducibility 和 implementation-review。
+| 严重度 | 发现 | 修改与证据 |
+|---|---|---|
+| Blocker | 透明区域的有效深度可能是背景，不能直接当瓶壁 | 新增恢复 Provider/worker；无权重或 worker 故障显式失败，无原始深度假成功回退；真实 ReMake 已运行 |
+| Major | scene.understand 必须依赖仿真刚体，离线图像不能独立查询 | 观测实体由视觉侧生成；执行对应移至准备/能力侧，读取恢复点云并保留原 entity_ref；离线实测不创建 Isaac engine |
```

- [docs] [refactor] [修改 / Modified] `docs/forge/LAB_PERCEPTION_GRASPNET_REFACTOR_20261023.md` L74-L87：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+已经接入可替换几何恢复 Provider/worker、标准点云抓取查询和 Agent 参数投影。原始深度不再通过单点连通过滤冒充完整玻璃几何；最高点拟合瓶口、PCA 可见端当棒尖的代码已删除。视觉实体在感知阶段生成，仿真刚体对应移到准备侧，只读取恢复点云，不修改候选。
+- 第三人称原观测回放：真实 ReMake 推理 → 13 份恢复点云 → 256 个真实 GraspNet 候选。原始 VLM/SAM2 输出明确标注为回放。
+- 原场景腕部相机新观测：真实 RGB-D/VLM/SAM2/ReMake/GraspNet → 11 份点云、192 个候选；当前相机被机器人本体大面积遮挡，没有读出可用试剂标签。
+- 上游数值对照：同一训练权重、同一原始观测，PAOS 与上游 ReMake 推理最大绝对差为 0 m。
+- 第三人称恢复瓶体的世界 z 中位数约 1.27–1.32 m，与此前该桌面约 0.714 m 的观测及桌上器材位置不一致。原始与恢复深度差不是玻璃表面真值 RMSE；不能据此接受几何。
```

- [docs] [refactor] [修改 / Modified] `docs/forge/LAB_TRANSPARENT_PERCEPTION_IMPLEMENTATION_20261023.md` L11-L11, L107-L107, L111-L111, L122-L122, L145-L172：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-ReMake 是待验证的首选机制，尚无本项目实际推理结果；它的官方 PCF-Grasp 流程不进入 PAOS。近景观测和功能点证据是该方案的一部分，不能只装一个深度模型就认为链路成立。
-以上文件是待实施范围，不表示本轮已修改实现。新增 worker 的具体文件放在现有可复用感知层，与 SAM2/GraspNet worker 同一机制层；不用临时脚本承担正式推理，也不为此迁移整个项目目录。
-以下为现有探针命令；它仍运行当前待修实现，不能宣称包含 ReMake。每次使用新的输出目录，保留失败产物：
+ReMake 已完成本项目真实推理，但当前观测几何未通过执行验证；它的官方 PCF-Grasp 流程不进入 PAOS。近景观测和功能点证据是该方案的一部分，不能只装一个深度模型就认为链路成立。
+以上是完整计划范围；v16.0.0 已交付 Provider/查询接入及真实推理，阶段状态见文末。新增 worker 的具体文件放在现有可复用感知层，与 SAM2/GraspNet worker 同一机制层；不用临时脚本承担正式推理，也不为此迁移整个项目目录。
+以下探针现已接入 ReMake；成功状态仅说明感知与候选查询完成，不代表几何或动作验收。每次使用新的输出目录，保留失败产物：
+观察已有腕部相机时可将 sensor-ref 改为 `sensor://tabletop_wrist`；这只选择相机，不会自动把机械臂移动到近景位置。现已支持 `--replay`、`--geometry-method` 和 `--perception-config`，实际命令见文末及 worker 说明。
+当前交付状态见下节；旧方案的“尚未实施”状态由本次真实运行证据更新。
```

- [docs] [docs] [新增 / Added] `docs/forge/evidence/transparent-depth-comparison-20261023.png`：二进制 PNG，无文本行号；1950×650 像素；原始/恢复深度共用 0–3 m 色标。 / Binary PNG, no text line numbers; equal-scale raw/recovered depth comparison. (local)

- [docs] [refactor] [新增 / Added] `docs/forge/evidence/transparent-implementation-20261023.json` L1-L1062：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+{
+  "date": "2026-10-23",
+  "version": "16.0.0",
+  "runs": [
+    {
```

- [docs] [refactor] [修改 / Modified] `docs/forge/labutopia-paos-acceptance.md` L3-L261, L326-L335：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-This adapter exposes LabUtopia's existing `PourController` and `StirController`
-through the PAOS complete-cycle endpoint.  A task such as “将标签为试剂A的
-试剂瓶倒入烧杯” is projected by `project_pour_task()` into the profile-bound
+The Agent-facing path uses semantic requests and current observation bindings:
+`manipulation.execute_subtask` runs prepare, acquire, held preparation, pour/stir,
+held return preparation and place inside one outer Action. The Runtime owns
+invocations and possession; the adapter owns private simulator routes.
+`project_pour_task()` requires an observation-derived binding and does not infer
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json` L1-L41：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+{
+  "workspace_min_m": [
+    -0.7,
+    -0.7,
+    0.7
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-perception.json` L1-L164：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+{
+  "provider_from_tcp": [
+    [
+      0,
+      0,
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json` L1-L24：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+{
+  "lab_root": "/home/yanxu/LabUtopia",
+  "config_path": "/home/yanxu/LabUtopia/config/tabletop_station.yaml",
+  "motion_config_path": "labutopia-mixture-motion.json",
+  "scene_usd_path": "/home/yanxu/LabUtopia/assets/chemistry_lab/tabletop_station/tabletop_station.usda",
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/pyproject.toml` L6-L9, L12-L12：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-dependencies = ["Pillow>=10"]
+dependencies = ["Pillow>=10", "numpy>=1.24", "scipy>=1.10", "PyYAML>=6"]
+[project.optional-dependencies]
+agent = ["openai>=1.0", "paos-robotwin20-adapter>=0.1.0"]
+paos-isaacsim-lab-agent = "isaacsim_lab.agent_host:main"
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py` L1-L214：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Compose the existing PAOS Agent and Runtime with a persistent Isaac worker."""
+class ObservedQueryPort:
+    """Retain successful observation receipts used by the semantic plan builder."""
+    def __init__(self, client):
+        self.client = client
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/cli.py` L21-L23, L26-L35：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    parser.add_argument("--observe", action="store_true", help="render and capture the simulator cameras without issuing robot commands")
+    parser.add_argument("--sensor-ref", action="append", help="camera reference for --observe; may be repeated")
+    parser.add_argument("--artifact-root", type=Path, help="directory for captured observation artifacts")
+    if args.observe:
+        if not args.sensor_ref:
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py` L359-L361, L504-L520, L599-L599, L626-L626, L636-L658, L662-L684, L689-L709, L732-L732, L799-L799, L873-L890, L892-L899, L916-L916, L929-L930, L941-L947, L984-L985, L991-L992, L1104-L1105, L1335-L1336, L1516-L1517, L2275-L2299, L2318-L2319, 删除旧 / deleted old L2182-L2182, L2334-L2340：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-        """Return unavailable until a measured IK/collision route provider exists."""
-        del session, arguments
-        return {
+    def bind_observed_entities(self, request: Mapping[str, Any]) -> dict[str, Any]:
+        return dict(self.backend.bind_observed_entities(request))
+    def prepare_held(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
+        """Request a current held route through the same backend boundary."""
+        prepare = getattr(self.backend, "prepare_held", None)
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/execution_identity.py` L1-L111：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Private RGB-D-to-rigid-body correspondence; never produces visual geometry."""
+def bind_observed_entities(model, request):
+    revision = model.session.current_scene_revision()
+    captures = model.session.resolve("observation_captures") or {}
+    capture = captures.get(request["calibration_ref"])
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/observation.py` L109-L109, L115-L115, L218-L218：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-            position, orientation = get_pose(camera_axes="world")
-            value = getter()
+            position, orientation = get_pose(camera_axes="ros")
+                "camera_axes": "ros",
+            value = getter(world_frame=False) if kind == "point_cloud" else getter()
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py` L29-L30, L33-L34, L106-L109, L111-L111, L115-L115, L117-L118, 删除旧 / deleted old L117-L130, L122-L176, L178-L226, L481-L482, L532-L532, 删除旧 / deleted old L482-L482, L563-L563：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-    def __init__(self, engine: Any, *, target_resolver: Any | None = None):
-            return {"status": "invalid", "provider_available": False,
-                    "error": "standard_preparation_request_must_be_object"}
+    def __init__(self, engine: Any, *, target_resolver: Any | None = None,
+                 assignment_store: Any | None = None):
+        self.assignment_store = assignment_store
+        self.result_resolver: Callable | None = None
+            PreparationProviderError,
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/perception_probe.py` L1-L169：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Exercise camera/replayed observations through geometry and grasp Query ports."""
+class RecordedSegmentation:
+    """Replay recorded masks by their image proposal, without model claims."""
+    def __init__(self, source, records):
+        self.source, self.records = source, records
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/perception_runtime.py` L1-L40：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Lab deployment composition of reusable model Providers and their workers."""
+def build_visual_providers(config_path, engine, artifact_root, inference, *, segmentation=None, geometry_method=None):
+    if config_path is None:
+        raise ValueError("the lab Agent requires perception_config_path with segmentation, geometry recovery and GraspNet workers")
+    config_path = Path(config_path).resolve()
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L1-L1046：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Session-owned, measured phase preparation for the Isaac laboratory adapter.
+The route contains joint targets, not controller completion flags. Preparation
+only reads physics state and performs FK, IK and overlap queries. Execution
+uses articulation commands; it never teleports an object or attaches it by
+editing a USD transform. Runtime remains the owner of possession/settlement.
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/profile.py` L65-L72, L134-L141, L144-L150, L174-L179：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    camera_render_frames: int = 4
+    motion_config_path: Path | None = None
+    perception_config_path: Path | None = None
+    worker_python_path: Path | None = None
+    physics_scene_path: str = "/physicsScene"
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_geometry.py` L1-L105：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Geometry estimated from segmented RGB-D; no simulator state or grasp rules."""
+def world_from_camera(calibration):
+    pose = calibration["camera_pose_world"]
+    transform = np.eye(4)
+    transform[:3, :3] = Rotation.from_quat(np.roll(pose["orientation_wxyz"], -1)).as_matrix()
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py` L1-L439：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Visual labels, model segmentation and observed depth behind standard Query ports."""
+    candidate_world_pose,
+    pixel_to_world,
+    process_features,
+    world_from_camera,
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/worker.py` L64-L65：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+                        elif method == "bind_observed_entities":
+                            result = backend.bind_observed_entities_in_session(context, payload.get("arguments", {}))
```

- [sense] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/worker_session.py` L33-L33, L37-L37, L61-L61, L137-L137：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-            "execute_cycle", "prepare_manipulation", "execute_phase", "observe", "scene_revision"
-            [sys.executable, "-m", "isaacsim_lab.worker"],
+        python_executable: str | Path | None = None,
+        self.python_executable = str(python_executable or sys.executable)
+            "execute_cycle", "prepare_manipulation", "execute_phase", "observe", "scene_revision", "bind_observed_entities"
+            [self.python_executable, "-m", "isaacsim_lab.worker"],
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py` L1-L101：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    LabPlanningContext,
+    ObservedQueryPort,
+    compose_host,
+    environment_guidance,
+)
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_cli.py` L1-L26：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+@pytest.mark.parametrize("status,exit_code", [("available", 0), ("unavailable", 2)])
+def test_observation_cli_captures_and_closes_without_cycle_execution(monkeypatch, capsys, status, exit_code):
+    calls = []
+    class Backend:
+        def __init__(self, profile, *, observation_artifact_root):
```

- [eval] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_engine.py` L158-L158, L217-L218, L226-L226, L286-L286, L339-L342, L345-L345, L347-L356, L371-L371, L417-L417, L658-L659, L674-L674, L956-L1053：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-        def __init__(self, profile_path, *, observation_artifact_root):
-        def get_pointcloud(self):
-            assert camera_axes == "world"
+        def __init__(self, profile_path, *, observation_artifact_root, python_executable=None):
+        def get_pointcloud(self, *, world_frame):
+            assert world_frame is False
+            assert camera_axes == "ros"
+    assert all(camera.kwargs["frequency"] == -1 for camera in session.resolve("camera_registry").values())
```

- [eval] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_observation.py` L28-L29, L40-L40：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-    def get_pointcloud(self):
-        assert camera_axes == "world"
+    def get_pointcloud(self, *, world_frame):
+        assert world_frame is False
+        assert camera_axes == "ros"
```

- [eval] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py` L140-L140, L223-L224, L894-L929：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-            assert observed == binding
-            assert observed == binding
+            assert all(observed[key] == value for key, value in binding.items())
+            assert all(observed[key] == value for key, value in binding.items())
+            assert observed["grasp_candidate"]["candidate_ref"] == observed["candidate_ref"]
+def test_preparation_tries_predicted_candidates_and_preserves_selected_pose(tmp_path):
+    profile = _profile(tmp_path)
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_perception_probe.py` L1-L40：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Recorded input is explicit and never starts an execution environment."""
+def test_recorded_masks_use_the_same_provider_proposal(tmp_path):
+    records = [{'index': 0, 'claim': {'bbox_xyxy': [1, 2, 3, 4]}}]
+    np.save(tmp_path/'replay-mask-0.npy', np.ones((5, 5), dtype=bool))
+    provider = RecordedSegmentation(tmp_path, records)
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L1-L714：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    IsaacPhaseMotion,
+    PhaseMotionError,
+    collision_hits,
+    held_tool_pose,
+    interpolate_pose,
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_phase_pipeline.py` L1-L273：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Exercise real Runtime endpoints and storage; only the simulator is substituted."""
+def observed(entity, revision):
+    frame = "front"
+    pose = {"frame_id": frame, "unit": "m", "position_m": [0.2, 0.1, 0.8],
+            "orientation_xyzw": [0, 0, 0, 1]}
```

- [eval] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_profile.py` L133-L149：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+@pytest.mark.parametrize("values", [
+    {"physics_dt_s": .02, "control_dt_s": .01},
+    {"physics_dt_s": .01, "control_dt_s": .015},
+    {"startup_settle_s": -1}, {"startup_settle_s": float("nan")},
+    {"physics_scene_path": "relative"},
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py` L1-L285：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Sensor/model substitution tests: no Isaac imports, meshes or rule grasps."""
+    LabArtifactStore,
+    LabVisualPerception,
+    RecordedGraspProvider,
+    RGBLabelPointInference,
```

- [eval] [refactor] [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_worker_session.py` L68-L71, L268-L299：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    def bind_observed_entities_in_session(self, session, arguments):
+        self.methods.append(("bind_observed_entities", session))
+        return {"status": "unavailable", "failure_code": "visual_body_association_ambiguous"}
+def test_worker_uses_configured_interpreter_without_changing_session_protocol(tmp_path, monkeypatch):
+    session, _, processes, _ = make_session(tmp_path, monkeypatch)
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/robotwin20/patches/remake-inference-import.patch` L1-L12：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+diff --git a/models/remake.py b/models/remake.py
+index 5ae7fc6..7fc0f97 100755
+--- a/models/remake.py
++++ b/models/remake.py
+@@ -6,7 +6,6 @@ import torch.nn.functional as F
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/robotwin20/runtime/transparent-geometry.md` L1-L77：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+This worker composes the actual ReMake or DFNet model with the existing PAOS JSONL process transport. It returns aligned metre-valued depth and model provenance. It does not generate grasps, select objects, qualify motion, or own task state. GraspNet remains a separate Provider.
+The laboratory deployment is configured in `../../isaacsim_lab/configs/labutopia-mixture-perception.json`. `geometry_method` selects one of the `geometry_workers`; Python, source, weights, device, image dimensions, depth range and seed are explicit. The supplied profile uses a 0–3 m input range for the original third-person view. This is a diagnostic range, not evidence that either model generalizes to that distance.
+Official sources:
+- ReMake: https://github.com/ChengYaofeng/ReMake (tested source `4f568148c8421544136bf49bb941149e0c990a34`). Its README links the released checkpoint.
+- DFNet: https://github.com/Galaxies99/TransCG. Its README links Google Drive and Baidu releases.
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/robotwin20/runtime/transparent_geometry_worker.py` L1-L213：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""RGB-D transparent-geometry inference using the shared worker protocol."""
+class DepthRecoveryWorker:
+    def __init__(self, *, method, repo_root, checkpoint, relative_checkpoint, device,
+                 source_artifact_root, worker_artifact_root, image_size,
+                 depth_min_m, depth_max_m, depth_scale_to_m=1., seed=0):
```

- [sense] [refactor] [新增 / Added] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/geometry_recovery.py` L1-L88：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Camera-geometry recovery port and the existing process-worker transport.
+The port has no simulator or grasp policy. Returned geometry remains an estimate;
+availability establishes aligned metric output, not manipulation readiness.
+"""
+class GeometryRecoveryError(RuntimeError):
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/robotwin20/tests/test_geometry_recovery.py` L1-L60：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Recovery crosses the existing worker seam, without simulator state."""
+    GeometryRecoveryError,
+    GeometryRecoveryRequest,
+    WorkerGeometryRecoveryProvider,
+)
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/robotwin20/tests/test_geometry_upstream.py` L1-L70：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Optional trained-model parity with the upstream ReMake inference method.
+Run in the geometry runtime with PAOS_GEOMETRY_CACHE, PAOS_GEOMETRY_REPLAY and
+PAOS_GEOMETRY_PARITY_OUTPUT set. Default unit suites skip the external model.
+"""
+pytestmark = pytest.mark.skipif(not os.environ.get('PAOS_GEOMETRY_CACHE'), reason='external trained model not requested')
```

- [eval] [refactor] [新增 / Added] `examples/forge-adapters/robotwin20/tests/test_geometry_worker.py` L1-L67：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+"""Exercise actual input/output adaptation with a deterministic model substitute."""
+RUNTIME = Path(__file__).parents[1] / "runtime"
+sys.path.insert(0, str(RUNTIME))
+spec = importlib.util.spec_from_file_location("transparent_geometry_worker", RUNTIME / "transparent_geometry_worker.py")
+module = importlib.util.module_from_spec(spec)
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/grasp.propose.tool.yaml` L43-L48：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-        required: [entity_ref, category, confidence, spatial_envelope]
+        required: [entity_ref, category, confidence]
+        anyOf:
+          - required: [spatial_envelope]
+          - required: [geometry_artifacts]
+            properties:
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/manipulation.cycle.tool.yaml` L56-L58, L505-L507：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    binding_ref:
+      type: string
+      pattern: ^artifact://\S+$
+        binding_ref:
+          type: string
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml` L8-L9, L19-L33, L41-L42, L45-L46, L156-L159, L161-L171, 删除旧 / deleted old L215-L219, L237-L240, L295-L392, 删除旧 / deleted old L418-L418, L539-L539：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-  capabilities: [manipulation.prepare]
-          observation_ref: [observation_ref]
-          scene_revision: [scene_revision]
+  capabilities:
+  - manipulation.prepare
+          observation_ref:
+          - observation_ref
+          scene_revision:
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare_cycle.tool.yaml` L45-L47, L484-L486：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    binding_ref:
+      type: string
+      pattern: ^artifact://\S+$
+          binding_ref:
+            type: string
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/object.pour_cycle.tool.yaml` L101-L103, L542-L544：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    binding_ref:
+      type: string
+      pattern: ^artifact://\S+$
+        binding_ref:
+          type: string
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/scene.understand.tool.yaml` L148-L153, L155-L157, L161-L165, 删除旧 / deleted old L166-L171, L272-L274, L547-L614：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-            enum: [unchanged, held]
-            required: [holding_state, entity_ref, owner, acquire_invocation_id]
-          effect_evidence_refs: &id001
+          effect_evidence_refs: &id001
+            type: array
+            minItems: 1
+            items:
+              type: string
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/tool.stir_cycle.tool.yaml` L101-L103, L542-L544：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    binding_ref:
+      type: string
+      pattern: ^artifact://\S+$
+        binding_ref:
+          type: string
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/held_manipulation.py` L908-L913：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-            resolved = deepcopy(dict(self.resolve(self.operation, deepcopy(public))))
+            task_resolver = getattr(self.resolve, "resolve_for_task", None)
+            resolved = deepcopy(dict(
+                task_resolver(self.operation, deepcopy(public), task_id=parts[1])
+                if callable(task_resolver)
+                else self.resolve(self.operation, deepcopy(public))
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/perception_binding.py` L17-L17, L126-L132, L186-L187, L199-L200, L243-L243, L309-L310, L469-L478：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-        binding = self.bind()
-                        "spatial_envelope": source_envelope,
-        if len(candidates) != 1:
+        request = replace(self.request, source_category=previous.category,
+                          source_selector={"entity_ref": previous.entity_ref},
+                          destination_category=previous.destination_category,
+                          destination_selector=lambda entity: self.destination_ref_factory(entity) == previous.destination_ref)
+        binding = PerceptionBindingAdapter(
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/persistent_runtime.py` L576-L576, L578-L579, L592-L593, L746-L746：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-        if register_legacy_held_operations and spec["tool_id"] == "object.place":
+        held_request = phase != "acquire" and "held_invocation_ref" in request
+            if key == "candidate_ref" and held_request and key not in request:
+                continue  # Held Tools identify their route by its canonical assignment.
+            if key == "candidate_ref" and held_request and key not in request:
+                continue
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/semantic_task_creation.py` L76-L77：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+    required_tool_contracts = (("manipulation.execute_subtask", "action"),)
```

- [sense] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py` L14-L14, L65-L65, L158-L164, L455-L455, 删除旧 / deleted old L521-L521, L536-L536, L571-L571, L579-L584, L599-L600, L603-L604, L607-L608, L684-L684, L695-L695, L731-L742, L781-L787, L789-L789, L795-L796, L870-L874, L878-L878, L895-L895, L909-L909, L973-L975, 删除旧 / deleted old L936-L936, L984-L984, L1085-L1085, L1138-L1138：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-        for value in (self.measured_pose, self.measured_geometry, self.destination_pose):
-                    response=response,
-        binding.pop("max_age_ms", None)
+    grasp_candidates: tuple[Mapping[str, Any], ...] = ()
+        if self.grasp_candidates:
+            refs = [item.get("candidate_ref") for item in self.grasp_candidates]
+            if len(set(refs)) != len(refs) or self.candidate_ref not in refs:
+                raise ValueError("candidate collection must be unique and contain the preferred candidate")
```

- [eval] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py` L259-L274：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+@pytest.mark.parametrize("kind", ["object_point_cloud", "fused_entity_perception"])
+def test_cloud_only_target_needs_bound_geometry_but_no_fabricated_envelope(kind):
+    geometry = {"artifact_ref": "artifact://obs-7/points", "kind": kind,
+        "observation_ref": "observation://scene-7/camera_front", "scene_revision": "scene-7",
+        "entity_ref": "entity://bottle-1", "frame_id": "camera_front",
```

- [eval] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py` L4-L4, L125-L197：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+@pytest.mark.asyncio
+@pytest.mark.parametrize("asynchronous", [False, True])
+async def test_binding_projects_understanding_envelope_through_real_grasp_endpoint(asynchronous):
+    query = QueryChain()
+    for envelope in query.understanding["spatial_envelopes"]:
```

- [eval] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py` L534-L555：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+@pytest.mark.parametrize("label", [None, "REAGENT A"])
+def test_visible_label_is_optional_in_real_query_contract(label):
+    entity = deepcopy(understanding_snapshot().entities[0])
+    if label is not None:
+        entity["label"] = label
```

- [eval] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_semantic_task_creation.py` L322-L327, L331-L331：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
-    result = json.loads(asyncio.run(tool.execute("pour reagent", {"mode": "off"}, semantic_subtasks=_request())))
+    subtasks = _request()
+    subtasks[0]["semantic_intent"] = {"goal": "pour selected reagent", "success_criteria": ["bottle returned"],
+                                       "allowed_arms": ["franka"], "coordination_mode": "single_arm"}
+    arguments = {"task_description": "pour reagent", "verification": {"mode": "off"}, "semantic_subtasks": subtasks}
+    assert tool.validate_params(arguments) == []
```

- [eval] [refactor] [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py` L595-L619：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+def test_preparation_can_select_second_candidate_and_acquire_keeps_that_selection():
+    first = binding().grasp_candidate
+    second = deepcopy(first)
+    second['candidate_ref'] = 'candidate://reagent-a/second'
+    second['grasp_frame']['position_m'][0] += .025
```

- [eval] [refactor] [修改 / Modified] `tests/test_planning_projection.py` L143-L162：本任务接入、修复或验证记录，关键差异如下。 / Task-owned integration, repair or validation; key diff below. (local)

```diff
+def test_entity_projection_accepts_bound_cloud_without_an_envelope():
+    plan = project_tool_spec(GRASP_TOOL_SPEC).argument_projection_plan
+    entity = {'entity_ref': 'entity://glass', 'category': 'container', 'confidence': .9}
+    artifact = {'artifact_ref': 'artifact://capture/cloud', 'kind': 'object_point_cloud',
+        'entity_ref': 'entity://glass', 'observation_ref': 'observation://capture/camera',
```

### 验证 / Validation

- `PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/pytest -q examples/forge-adapters/isaacsim_lab/tests examples/forge-adapters/robotwin20/tests/test_geometry_recovery.py examples/forge-adapters/robotwin20/tests/test_geometry_worker.py examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py examples/forge-skills/pick-place-workflow/tests tests/test_planning_projection.py tests/test_planning_loop.py tests/test_multi_source_projection.py`：998 passed，2 failed。与此前相同的失败为 node 版本断言、发布锁一致性，未修改发布锁。 / 998 passed, 2 previously recorded node-version/release-lock failures; release locks unchanged.
- 清理后视觉/投影/可选外部模型测试 19 passed、1 skipped；探针/准备相关 31 passed。 / Post-cleanup visual/projection/optional external-model tests: 19 passed, 1 skipped; probe/preparation subset: 31 passed.
- 真实训练权重数值检查 `test_geometry_upstream.py`：1 passed，CPU 最大差 0 m；单元套件默认跳过该外部依赖，未计作已运行。 / Trained-weight upstream parity: 1 passed, maximum CPU difference 0 m; default unit-suite skip is reported separately.
- Ruff、Git diff whitespace、JSON/UTF-8/代码围栏和最近五版本对应检查通过；模型运行、配置、失败、图像与候选保留在 `out/releases/v16.0.0/`。 / Ruff, scoped whitespace, JSON/UTF-8/fences and latest-five consistency passed; model runs and evidence remain in out/releases/v16.0.0.

### Git 范围 / Git scope

只提交 `/tmp/paos-v16-task-files.json` 对应的 PAOS 任务文件，不暂存 LabUtopia、其他 lab-assets 修改、会话/项目数据或模型缓存。完整动作验收仍开放；本版本提交的是查询接入与真实失败证据。 / Stage only the PAOS task-owned file list, excluding LabUtopia, unrelated lab-assets changes, session/project data and model caches. Full action acceptance remains open; this version commits query integration and measured failure evidence.

- [docs] [chore] 本记录位置 / Record locations: `changelog/2026-10_part9.md:L472-L1246`；`CHANGELOG.md:L43-L955`。 (local)

### Git 提交回执 / Git receipt

- Implementation commit: `367b099b`; Branch: `feature/planning-loop`; Push: `origin/feature/planning-loop` 已成功 / succeeded; 时间 / Time: 2026-10-23 13:30 CST.
- 本回执随同版本的日志提交保存；完整 Agent 混合搅拌验收仍开放。 / Persist this receipt in a same-version log commit; full Agent mixing/stirring acceptance remains open.

## v15.10.2 (2026-10-23 12:30) - codex

### 变更摘要 / Summary [完成 / Completed]
- [docs] [docs] 将已保存透明感知诊断落实为单一可执行方案：输入改善、ReMake/DFNet Provider 接入、观测实体与执行关联分离、功能点证据、GraspNet 准备及原场景验收，列明依赖、文件、产物与失败分叉。 / Turn the saved diagnosis into one actionable plan covering observation improvements, ReMake/DFNet providers, observation/execution identity separation, process-feature evidence, GraspNet preparation and original-scene acceptance, with dependencies, files, outputs and failure branches. (local)
- [docs] [fix] 补充抓取前功能点依赖及遮挡玻璃棒的完整观测路径，避免用“先抓后看”掩盖准备所需证据；保留生命周期与运动控制边界。 / Document pre-acquisition process-feature dependencies and a full-observation path for an occluded rod, avoiding an unsupported grasp-first workaround while retaining lifecycle and motion boundaries. (local)
- [docs] [chore] 更新诊断、实施方案、日志和最近五条；验证文档及现有命令入口，仅向 PAOS 当前分支提交文档。 / Update the diagnosis, implementation plan, logs and latest-five index; validate documents and existing CLI entry points, committing only documentation to the current PAOS branch. (local)

### 预计文件 / Planned files
`docs/forge/LAB_TRANSPARENT_PERCEPTION_IMPLEMENTATION_20261023.md`、`docs/forge/LAB_PERCEPTION_GRASPNET_REFACTOR_20261023.md`、`changelog/2026-10_part9.md`、`CHANGELOG.md`。

### 实际修改 / Actual changes
- [docs] [docs] [新增 / Added] `docs/forge/LAB_TRANSPARENT_PERCEPTION_IMPLEMENTATION_20261023.md:L1-L145`：确定近景 RGB-D＋ReMake＋现有 GraspNet 主线，列出 P0–P5 的依赖、责任、改动位置、产物、验证及失败分叉；DFNet 为同输入对照。 / Define the near-view RGB-D + ReMake + existing GraspNet route, with P0–P5 dependencies, ownership, change locations, outputs, validation and failure branches; use DFNet as the same-input comparison. (local)
- [docs] [fix] [修改 / Modified] `docs/forge/LAB_PERCEPTION_GRASPNET_REFACTOR_20261023.md:L65-L73`：追加抓取前功能点依赖与持有刷新诊断，以及遮挡玻璃棒的完整相机观测登记/当前定位路径。 / Append pre-acquisition process-feature and held-refresh findings plus a full-camera-observation/current-localization path for the occluded rod. (local)
- [docs] [chore] 更新本日志与最近五版本，保留之前未完成实现的状态。 / Update this log and the latest five versions, preserving the pending status of previous implementation. (local)

### 关键 Diff / Key diff (documentation only)
```diff
- 仅列出透明几何模型的推荐顺序
+ P0 失败路径 → P1 Provider/输入适配 → P2 观测 → P3 几何测量
+ → P4 GraspNet/准备 → P5 原场景动作/Agent 验收
- 假定当前链路可以先抓取再补看工作端
+ 初版抓取前收齐任务功能点；完全遮挡时先建立适用完整相机观测
+ 保留 acquisition 候选历史证据，持有准备使用当前观测和持有收据
```
这是方案差异；本轮没有修改模型或运动实现。 / These are plan changes; this slice changes no model or motion implementation.

### 验证 / Validation
- `PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m isaacsim_lab.perception_probe --help`：退出码 0，确认现有 profile/workspace/config/sensor-ref 参数。 / Exit 0, confirming the existing profile/workspace/config/sensor-ref arguments.
- 两份文档的 UTF-8、代码围栏、本地链接、现有测试与配置路径检查通过；`git diff --check` 通过。 / UTF-8, fences, local links and existing test/config paths passed for both documents; scoped diff whitespace checks passed.
- 最近五条与月度归档完整对应。未下载模型、启动仿真或重跑未改动实现的测试。 / Latest-five entries match the complete archive records. No model download, simulator startup or rerun of unchanged implementation tests.

### Git 范围 / Git scope
仅 PAOS 当前 `feature/planning-loop` 的实施方案、诊断和两份日志；未完成代码继续保留，不提交 LabUtopia。 / Only the implementation plan, diagnosis and two logs on PAOS feature/planning-loop; preserve pending code and do not commit LabUtopia.

- [docs] [chore] 修改位置 / Changed ranges: `changelog/2026-10_part9.md:L431-L465`；`CHANGELOG.md:L43-L206`（最近五条滚动更新 / latest-five rolling update）。 (local)

### Git 提交回执 / Git receipt
- Plan commit: `c15500d6`; Branch: `feature/planning-loop`; Push: `origin/feature/planning-loop` 已成功 / succeeded; 时间 / Time: 2026-10-23 12:34 CST.
- 本回执随同版本的文档日志提交保存；P0–P5 尚待实施。 / Persist this receipt in a same-version documentation-log commit; P0–P5 implementation remains pending.

## v15.10.1 (2026-10-23 11:48) - codex

### 变更摘要 / Summary [完成 / Completed]
- [docs] [docs] 保存透明物体感知检索结果、原始论文/官方仓库来源与访问日期；依据现有 RGB-D、GraspNet、原场景失败证据审核 DFNet、ClearGrasp、ASGrasp、多视角及新近相关方案的可行性，明确首选与备选。 / Save transparent-object perception findings, primary sources and access dates; assess DFNet, ClearGrasp, ASGrasp, multiview and newer relevant approaches against the current RGB-D/GraspNet stack and observed failures, identifying preferred and fallback paths. (local)
- [docs] [fix] 更新诊断：背景剔除不能恢复玻璃，标签上沿和可见棒端不能直接当作过程功能点；记录输入适配、估计证据与运动验收边界。 / Update diagnosis: foreground filtering does not recover glass; label edges and visible rod endpoints do not establish process features. Record input compatibility, estimated-evidence and motion-acceptance boundaries. (local)
- [docs] [chore] 本轮只保存并审核方案，验证来源、证据摘要和 Markdown/JSON；只提交 PAOS 文档与对应日志，现有未完成代码继续保留。 / This slice saves and reviews the plan, validating references, evidence summaries and Markdown/JSON; commit only PAOS documentation and associated logs, preserving pending implementation. (local)

### 预计文件 / Planned files
`docs/forge/LAB_TRANSPARENT_PERCEPTION_FEASIBILITY_20261023.md`、`docs/forge/evidence/transparent-perception-20261023.json`、`docs/forge/LAB_PERCEPTION_GRASPNET_REFACTOR_20261023.md`、本日志和 `CHANGELOG.md`。 / The feasibility review, evidence record, existing diagnosis, this log and CHANGELOG index.

### 实际修改 / Actual changes
- [docs] [docs] [新增 / Added] `docs/forge/LAB_TRANSPARENT_PERCEPTION_FEASIBILITY_20261023.md:L1-L130`：保存九组原始来源、五条路线比较、七项问题、PAOS 责任与分阶段验证；主候选为近景 RGB-D＋ReMake＋现有 GraspNet，DFNet 为对照。 / Save nine primary-source groups, five route comparisons, seven findings, PAOS ownership and staged validation; prefer near-view RGB-D + ReMake + existing GraspNet for evaluation, with DFNet as comparison. (local)
- [docs] [docs] [新增 / Added] `docs/forge/evidence/transparent-perception-20261023.json:L1-L838`：保存检索范围/来源、r2 标定、九个对象的 17 份点云摘要、标签未读状态、模型未执行状态与选型理由。 / Save search scope/sources, r2 calibration, 17 cloud summaries for nine objects, unreadable-label and unexecuted-model states, and selection rationale. (local)
- [docs] [fix] [新增入版本控制并追加 / Newly tracked and extended] `docs/forge/LAB_PERCEPTION_GRASPNET_REFACTOR_20261023.md:L1-L63`：保留此前本机诊断，L54–L63 追加透明感知复审，明确前景过滤不足、模型/私有关联接缝、功能点和默认深度裁剪问题。 / Preserve the existing local diagnosis and append transparent-perception review at L54–L63, covering inadequate foreground filtering, model/private-association seams, process features and default clipping. (local)
- [docs] [chore] 保留 v15.8.0/v15.9.0/v15.10.0 待完成记录及既有场景提交回执，更新最近五版本；保存日志不代表未提交实现已验收。 / Preserve pending v15.8.0/v15.9.0/v15.10.0 records and the previous scene receipt, updating the latest five entries; saved logs do not accept pending implementation. (local)

### 关键 Diff / Key diff (documentation only)
```diff
- 直接将透明物体分割内的深度投影后送入 GraspNet
+ 先验证/恢复透明几何，保留估计来源，再由现有 GraspNet 预测
- 仅移除桌面点，并按局部点云最高边或极值取过程功能点
+ 抓取接触区、瓶口/杯口与棒工作端分别建立证据
+ 优先验证近景 + ReMake；同输入、同 GraspNet 比较 DFNet
+ 显式适配 0.3–1.5 m 默认推理裁剪、输出分辨率和相机内参
```
以上为方案前后差异；本提交没有修改感知、候选或运动代码。 / This diff describes the plan change; no perception, candidate or motion code is changed in this commit.

### 验证 / Validation
- 逐项重新读取本机原始 `.npy`，17 份点云的数量、min/max/extent 与保存记录一致；七个瓶子的标签均未读出。七份过滤后的瓶云都被当前功能点函数返回为估计，仍未证明为真瓶口。 / Re-read the local .npy files: counts, minima, maxima and extents match all 17 summaries; all seven bottle labels remain unreadable. The current feature function returns estimates for all seven foreground bottle clouds without establishing true rims.
- `python -m json.tool docs/forge/evidence/transparent-perception-20261023.json >/dev/null`、来源编号/本地链接、UTF-8/代码围栏检查通过。 / JSON parsing, source IDs/local links and UTF-8/code-fence checks passed.
- `git diff --check` 对本次文档/日志范围通过；最近五条与月度归档全文一致。 / Scoped diff whitespace checks pass; latest-five entries match their complete archive records.
- 已核对官方 README、ReMake/DFNet 推理源码和 builder；部分 raw 网络超时后通过 GitHub contents API 完成核对。尚未下载权重、运行新模型或执行运动，本轮不重跑未改动的代码测试。 / Verified official READMEs, ReMake/DFNet inference and builders; recovered from some raw-host failures through GitHub contents API. No weights downloaded, new model run or motion executed; unchanged code tests were not rerun.

### Git 范围 / Git scope
仅 PAOS `feature/planning-loop` 的上述文档与日志；不包含待完成代码和本地模型产物，不向 LabUtopia 提交。 / Only the listed PAOS documents/logs on feature/planning-loop; pending code and local model artifacts excluded; no LabUtopia commit.

- [docs] [chore] 日志与索引修改位置 / Log and index ranges: `changelog/2026-10_part9.md:L148-L329,L367-L424`; `CHANGELOG.md:L43-L95,L97-L97,L134-L135,L137-L137,L139-L144,L146-L314`. (local)

### Git 提交回执 / Git receipt
- Review commit: `7d918abc`; Branch: `feature/planning-loop`; Push: `origin/feature/planning-loop` 已成功 / succeeded; 时间 / Time: 2026-10-23 12:00 CST.
- 本回执随同版本的文档日志提交保存；实现仍待完成。 / Persist this receipt in a same-version documentation-log commit; implementation remains pending.

## v15.10.0 (2026-10-23 11:35) - codex

### 变更摘要 / Summary [计划 / Planned]
- [sense] [fix] 在已确认原场景继续诊断真实 RGB-D → SAM2 → GraspNet：复现逐对象分割/深度错误，保存完整失败证据，修复单对象失败阻断其他对象及标签/容器语义问题。 / Continue actual RGB-D → SAM2 → GraspNet on the confirmed original scene: reproduce object-specific segmentation/depth failures, retain diagnostics, and fix per-object isolation and label/container semantics. (local)
- [policy] [refactor] 完成之前未提交的候选集合、准备/持物刷新及执行接线；模型抓取输出只能进行标定变换，禁止 USD 真值补点、规则抓取和候选覆盖。 / Complete pending candidate-set, preparation/held refresh and execution wiring; permit only calibrated transforms of model grasps, never USD-generated points, rule grasps or candidate replacement. (local)
- [eval] [chore] 按阶段验证真实模型候选、无运动准备，再尝试已授权仿真任务；分别记录契约、感知、准备与动作证据，保持失败而不伪报完成。 / Verify real predictions and no-motion preparation before authorized simulation; record contract, perception, preparation and motion evidence separately without false completion. (local)

### 责任与验证边界 / Ownership and validation boundaries
通用层拥有语义/候选/生命周期，视觉 Provider 拥有图像解析、分割/点云/预测，Isaac Adapter 拥有相机、标定与执行机制；Coordinator/Runtime 仍为取消、持有与结算唯一 owner。替换图像、模型、环境不改变调用方领域契约。以同一捕获的 observation/revision/frame/calibration 为新鲜度边界；最小替换/失败测试验证局部识别失败、多候选及不可覆盖。只向 PAOS 当前分支提交，外部场景依赖不提交。 / Generic code owns semantics/candidates/lifecycle; vision Providers own image interpretation, segmentation/clouds/prediction; Isaac owns camera/calibration/execution. Coordinator/Runtime retain cancellation, possession and settlement. Image/model/environment replacements preserve caller contracts. One capture's observation/revision/frame/calibration defines freshness; substitution/failure tests cover local perception failures, multiple candidates and immutable selection. Commit only the current PAOS branch, not the external scene dependency.

### 预计文件 / Planned files
原 v15.9.0 范围内的 Isaac Adapter、通用 perception_binding/subtask_executor/prepare 及测试；必要的 Provider 接缝；诊断与验收文档、日志。 / Existing v15.9.0 Isaac Adapter, generic binding/subtask/prepare and tests; necessary Provider seams; diagnosis, acceptance docs and logs.

- [sense] [fix] [计划] r2 逐对象回放确认：瓶体透明区深度落在桌面（z≈0.713–0.715 m），仅标签带返回瓶上深度；原 process_features 会将标签顶边误判为杯口。采用分割外邻域实测背景平面剔除，仅保留实测前景；杯口必须有视觉顶部区域内的有效深度支持，否则 process_features unavailable。原始/过滤 mask、诊断与失败保存，单对象无效不拖垮其他对象。增加原图裁剪标签读取与类别定义（不把试管作为混合烧杯），相机分辨率作为 Adapter 参数。 / Per-object r2 replay confirms transparent bottle pixels return table depth (z≈0.713–0.715 m), with only label bands on the bottle; the old process-feature fit can mistake a label top edge for a vessel rim. Remove the measured background plane from the mask neighborhood and retain observed foreground only; rim features require depth in the visual top region or remain unavailable. Persist raw/filtered masks and failures, isolate invalid objects, read labels from original-image crops and distinguish test tubes from mixing beakers; configure camera resolution in the Adapter. (local)

## v15.9.1 (2026-10-23 11:27) - codex

### 变更摘要 / Summary [完成 / Completed]
- [env] [fix] 按用户纠正，将玻璃棒入试管架的场景变更仅作为 PAOS 补丁管理；撤回误建的外部仓库提交，保留其文件与原有改动。 / Follow the user's repository correction: manage the rod-in-rack scene change only as a PAOS patch; remove mistaken external commits while retaining files and pre-existing changes. (local)
- [docs] [docs] 保存补丁应用、重建、预览与静态验证说明；本次提交只包含场景补丁、对应说明及日志，不夹带尚未验收的感知/动作重构。 / Document patch application, rebuild, preview and static verification. This commit contains only the scene patch, its instructions and logs; the ongoing perception/motion refactor remains uncommitted. (local)

### 预计文件 / Planned files
`examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch`; `examples/forge-adapters/isaacsim_lab/patches/README.md`; `changelog/2026-10_part9.md`; `CHANGELOG.md`.

### 文件变更详情 / File changes
- [新增 / Added] `examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch` L1–L226：保存原场景四个文件的精确补丁；配置玻璃棒槽位、按源轴向竖直摆放、验证架底支撑/孔板净空，包含实际 USD 与文档。 / Preserve the exact four-file scene patch: rack-slot configuration, upright source-axis placement, bottom support and plate-clearance inspection, generated USD and documentation.
- [新增 / Added] `examples/forge-adapters/isaacsim_lab/patches/README.md` L1–L62：说明 PAOS 所有权、外部工作区应用、Git LFS 文本补丁、构建和预览命令与验证范围。 / Document PAOS ownership, external-working-tree application, Git LFS text patch handling, build/preview commands and validation scope.
- [日志 / Logs] `changelog/2026-10_part9.md`：追加本版本，保留既有历史；`CHANGELOG.md`：同步已提交版本的最新五条详细记录；`changelog/2026-10_index_archive.md` L1–L23：保留原索引独有的 v13.1.13 历史记录。 / Append this version, synchronize the latest five committed detailed records and preserve the index-only v13.1.13 historical record.

### 关键代码 Diff / Key code diff
```diff
- glass_rod.position_xy: [-0.49, 0.47]
- glass_rod.lay_horizontal: true
+ glass_rod.rack_slot.center_offset_xy: [-0.01875, -0.07928]
+ glass_rod.rack_slot.support_clearance_m: 0.0002
- _place_horizontal(...)
+ _place_rod_in_rack(...)
+ _inspect_rod_storage(stage, config)
```

场景几何仅用于初始摆位与静态检查，不产生抓取候选；GraspNet 接入仍属独立未完成的重构。 / Scene geometry serves initial placement and static inspection only; it produces no grasp candidates. GraspNet integration remains separate ongoing work.

### 验证 / Validation
- `python scripts/build_tabletop_station.py build`、`inspect`：通过 / passed；2133 prim、8 个标签/瓶位、6 支试管、11 个 Franka render meshes。
- 棒底支撑间距 `0.2 mm`；上下孔板径向净空各 `8.039 mm`；无已有试管重叠。悬空、插入实体板及孔边相交反例均拒绝。 / Support gap 0.2 mm, guide clearances 8.039 mm, no tube overlap; floating, solid-plate and hole-edge counterexamples rejected.
- `python -m py_compile utils/tabletop_scene.py scripts/build_tabletop_station.py`：通过 / passed。
- 第三视角和架子近景已人工检查；输出 `/home/yanxu/LabUtopia/outputs/tabletop-rod-storage/20261023-r1/`。无抓取、物理步进或机器人控制命令。 / Third-person and rack-detail renders visually inspected; no grasp, physics step or robot controller command for this scene change.
- `git -c filter.lfs.process= -c filter.lfs.required=false apply --reverse --check <PAOS>/examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch`：已应用检查通过 / confirms the locally applied patch。

### Git 范围 / Git scope
- 仅 PAOS `feature/planning-loop`；不包含工作区中尚未验收的感知、运动或其他修改。 / Only the PAOS feature/planning-loop branch; ongoing perception/motion and unrelated working-tree changes are excluded.
- LabUtopia 误建的 `af64d0e`、`b42fe75` 已撤回，HEAD 恢复为 `61e1fba`，文件改动保留；远端拒绝了之前的推送，未更新。 / Mistaken LabUtopia commits af64d0e/b42fe75 were removed; HEAD is restored to 61e1fba and file edits retained. The rejected earlier push did not update that remote.

### Git 提交回执 / Git receipt
- Commit: `c64b03f4`; Branch: `feature/planning-loop`; Push: `origin/feature/planning-loop` 已成功 / succeeded; 时间 / Time: 2026-10-23 11:30 CST.
