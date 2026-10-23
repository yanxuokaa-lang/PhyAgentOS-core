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

## v15.9.0 (2026-10-23 10:16) - codex

### 变更摘要 / Summary [计划 / Planned]
- [docs] [docs] 保存感知/GraspNet 接入偏离诊断与修复方案；v15.8.0 r14 整体失败（两次倾倒完成，搅拌连续合格 0.7681617 圈不足 2 圈，未归棒），不得作为模型抓取验收。 / Save the perception/GraspNet integration diagnosis and repair plan. v15.8.0 r14 failed overall: both pours completed, stirring reached only 0.7681617 qualified turns out of two and rod return did not run; it is not model-grasp acceptance. (local)
- [sense] [refactor] 删除 Isaac 接入中的网格规则抓取与候选覆盖路径，复用分割/观测点云/GraspNet worker 和标准 Query，保留预测候选到准备与执行的来源。 / Remove mesh-rule grasp generation and candidate replacement from the Isaac integration; reuse segmentation, observed point clouds, GraspNet workers and standard Queries, preserving predicted candidates into preparation and execution. (local)
- [policy] [fix] 修复 PerceptionBinding 的点云证据遗漏和单候选限制，准备阶段评估候选，维持原任务/实体/观测版本/持有与结算归属。 / Repair omitted point-cloud evidence and the single-candidate restriction in PerceptionBinding; evaluate candidates in preparation while retaining task/entity/observation/possession/settlement ownership. (local)
- [env] [refactor] LabUtopia 仅提供现有场景、相机、机器人与物理环境；新工作流不调用其固定抓取/倾倒/搅拌 benchmark 原子。保留限位、碰撞、取消及实测反馈。 / Use LabUtopia only for scene, cameras, robot and physics; the new workflow does not call its fixed benchmark grasp/pour/stir primitives. Retain limits, collision checks, cancellation and measured feedback. (local)
- [eval] [chore] 先完成真实 Provider 接口与失败测试，再执行当前场景的无运动模型推理，保存点云、模型配置、候选及来源证据；检查后运行授权范围内的仿真验证。 / Test real Provider interfaces and failures first, then run no-motion model inference on the current scene and retain point clouds, model configuration, candidates and provenance before authorized simulation validation. (local)

### 预计文件 / Planned files
- docs/forge/LAB_PERCEPTION_GRASPNET_REFACTOR_20261023.md; docs/forge/labutopia-paos-acceptance.md; Isaac visual_perception/visual_geometry/agent_host/phase_motion/engine/profile and tests; workflow perception_binding/subtask_executor and tests; existing provider wiring where required; CHANGELOG.md and this archive.

### 架构边界 / Architecture boundaries
- 通用层拥有语义绑定、候选集合、准备/执行生命周期；Provider 拥有分割、点云与模型预测；Isaac Adapter 拥有坐标转换、机器人执行和私有实体映射。 / Generic code owns semantic binding, candidate sets and preparation/execution lifecycle; Providers own segmentation, clouds and prediction; Isaac owns frame conversion, robot execution and private identity mapping.
- 同一 observation/scene/frame/calibration 贯穿 mask/cloud/candidate/preparation；Coordinator/Runtime 继续拥有取消、结算与恢复，不新增平行调度。 / One observation/scene/frame/calibration links mask/cloud/candidate/preparation; Coordinator/Runtime retain cancellation, settlement and recovery without parallel scheduling.
- 替换测试使用真实 GraspNet Provider 接口和多个候选，确保准备/执行不读取网格来重新制造抓取目标；仿真真值只用于私有身份/物理诊断，不作为感知几何。 / Substitution tests exercise the real GraspNet Provider interface and multiple candidates; preparation/execution must not recreate grasps from meshes. Simulator truth is private identity/physics diagnostics, not perceived geometry.

- [docs] [docs] 用户补充：允许参考 benchmark 的倾倒/搅拌轨迹逻辑，但必须重构成 PAOS 参数化工具，不沿用其固定目标和整套抓放生命周期；抓取仍来自 GraspNet。 / User clarification: benchmark pour/stir trajectory logic may inform PAOS parameterized Tools, but fixed targets and embedded grasp/place lifecycles must not carry over; grasps still come from GraspNet. (local)

- [policy] [fix] [计划] 同步 preparation 与 subtask 的候选集合 schema，并保留 Provider 基础设施错误、候选不合格和陈旧观测的区别；新增无运动感知探针保存真实模型证据。 / Synchronize preparation/subtask candidate-list schemas, distinguish infrastructure failures, rejected candidates and stale observations, and add a no-motion probe that persists actual model evidence. (local)

- [sense] [fix] [计划] 新鲜相机 r1 的 SAM2 轮廓中少量背景深度使棒点云延伸到 0.457 m；按被识别表面像素的三维邻接连通域保留观测点，1 cm 连通阈值后棒长约 0.250 m。该过滤只使用 mask、depth 和标定，不读取场景形状；加入回归与配置。 / Fresh r1 SAM2 silhouettes contain sparse background depth, stretching the rod cloud to 0.457 m. Retain the 3D connected depth component seeded by the observed surface pixel; a 1 cm edge threshold yields about 0.250 m. This uses only mask/depth/calibration, with regression coverage and configuration. (local)

- [env] [fix] [计划] 2026-10-23 10:59 用户确认现有场景入口为 LabUtopia `scripts/preview_tabletop_station.py --view third-person`（tabletop_station.usda，R01–R08）；纠正此前双瓶诊断场景误用。按用户追加要求先将原场景玻璃棒放入试管架空孔；独立源场景变更记录为 LabUtopia v0.2.7，随后 PAOS profile 使用该场景。 / User confirms the existing tabletop_station.usda (R01–R08) as the scene source. Correct the earlier two-bottle diagnostic-scene selection; first place the original rod in an empty rack hole per user steering, recorded as LabUtopia v0.2.7, then bind the PAOS profile to that scene. (local)

- [chore] [fix] [计划] 用户纠正仓库归属：撤回误建在 LabUtopia 的本地 af64d0e/b42fe75（远端拒绝，未推送），保留场景文件；本任务只在 PAOS 当前分支保存、提交和推送场景集成及诊断。外部依赖仓库不再提交。 / User corrects repository ownership: remove the mistaken local LabUtopia commits af64d0e/b42fe75 (remote rejected; not pushed), retaining scene files. Save, commit and push this task only in the current PAOS branch; do not commit the external dependency repository. (local)

- [env] [fix] [计划] PAOS 保存外部原场景的配置/构建/USD/文档补丁；部署直接加载 tabletop_station 配置与相机，移除新接入中误造双瓶夹具的 setup 路径。新增原场景配置投影测试，然后执行当前场景的真实感知探针。 / Keep the original-scene config/builder/USD/docs patch in PAOS; load tabletop_station config and cameras directly, removing the mistaken two-bottle fixture setup path. Add station-configuration projection coverage and run real perception on the corrected scene. (local)

- [sense] [fix] [计划] 原场景 r1 capture 可用但 RGB 几乎全黑；preview_tabletop_station.py 在运行时添加 PreviewDomeLight，USD 本体不包含该照明。PAOS Adapter 同步该预览照明（1200、RGB 0.88/0.93/1），不改变器材或抓取，重跑观测。215 项接口测试已通过。 / Original-scene r1 captures RGB-D but RGB is nearly black: preview_tabletop_station.py adds PreviewDomeLight at runtime, absent from the USD asset. Match that preview lighting in the Adapter (1200, RGB 0.88/0.93/1) without changing objects or grasps, then recapture. 215 interface tests pass. (local)
