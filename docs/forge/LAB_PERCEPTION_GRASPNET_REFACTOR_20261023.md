# 实验室感知与 GraspNet 接入诊断及重构方案

日期：2026-10-23。状态：实施中，完整 Agent 仿真验收尚未通过。

## 用户目标与既有方案

在用户已设置的带不同可见标签的锥形瓶场景中，以相机 RGB-D 和感知模型识别目标、产生目标点云，通过 GraspNet 预测抓取位姿，再执行倾倒、搅拌与归位。倾倒角度、保持时间、圆周/圈数等过程可以参数化规则生成；抓取点与方向不能从场景网格、Prim 位姿或固定高度规则生成。

2026-10-15 实施计划 L127–134 要求区分观测与真值；2026-10-20 子任务复审 L148–165 要求 scene.observe → scene.understand → grasp.propose → readiness。此前方案的感知主线有效，但应明确 GraspNet 部署、实例分割来自模型而非仿真标注，并加入真实 Provider 贯通验收。

允许参考 LabUtopia benchmark 的倾倒、搅拌轨迹逻辑，将其改造成 PAOS 参数化持物工具。不能沿用固定目标、固定抓取和自带抓放生命周期；不直接包装 benchmark 原子作为新工作流。复用其场景、相机、机器人及物理环境。

## 已确认问题

1. Blocker：agent_host 将 LabVisualPerception 同时注入 understanding/grasp/target；grasp.propose 未调用已有 GraspNet worker。
2. Blocker：PerceptionBinding 仅传 spatial_envelope，遗漏 geometry_artifacts，并强制一个候选。真实 GraspNet Provider 复现报 grasp target has no bound geometry artifact，推理未被调用；该缺口源自 2026-10-20 的 c35062e46。
3. Blocker：visual_geometry 遍历 USD 网格/刚体姿态并生成抓取点（瓶高 90%、棒中心和规则朝向）。这些输出进入视觉几何；违背观测证据边界。
4. Major：target resolver 忽略被选候选，从私有记录重建目标；竖棒公开向下接近与执行侧向接近相差 90°。
5. Major：替身测试只覆盖一个规则候选，没有接入真实点云/模型 Provider，无法证明可替换性。

当前 r14 的 A/B 抓取倾倒归位完成；搅拌连续合格 0.7681616956 圈不足请求 2 圈，任务 failed，未归棒。独立棒周期成功不等于完整 Agent 验收；已有视频均非 GraspNet 抓取证据。

## 修复责任与顺序

1. 保留现有相机、坐标标定、场景新鲜度、Runtime/Coordinator/持有/结算修复。删除新接入中的规则抓取及隐式回退实现和依赖这些行为的测试。
2. 复用已有视觉定位/分割 Provider、深度投影和 GraspNet worker；环境配置和 artifact 解析留在 Adapter。公开 Tool 保持领域语义。
3. 绑定完整观测点云引用并传递候选集合，由准备层评估多个候选。模型输出的坐标约定通过明确的夹爪变换适配，不能覆盖为规则姿态。
4. 准备和执行只消费被选候选、观测几何和功能点；仿真物体身份/当前状态只能在 Adapter 私有映射和物理诊断中使用，不补全被遮挡几何。
5. 过程路径使用实测/已标定功能点和有界参数，保留原 IK、工作空间、碰撞、速度、夹持和停止控制。缺观测、无候选或无合法路径时显式失败，不调用 benchmark fallback。
6. 先测试 Provider 替换、无点云、多候选、坐标变换、过期与失败关闭；再用真实场景 RGB-D 运行分割和 GraspNet，保存输入与预测可视化；最后完成 Agent 双倾倒和搅拌归位。

## 验收证据

必须能追溯 RGB/depth/calibration → 模型分割 → 目标点云 → GraspNet 原始候选 → 被选候选及准备检查 → 实际命令与反馈 → 单子任务结算。运行记录保留代码版本、模型/权重/配置、随机性、输出目录和失败阶段。

感知契约测试、真实模型推理、实际仿真动作分开报告；只有最后一项成功才能关闭完整 Agent 验收。


## 场景归属修正（2026-10-23）

用户指定的场景入口是 LabUtopia `python scripts/preview_tabletop_station.py --view third-person`，实际资产为 `tabletop_station.usda`，包含 R01–R08、烧杯、试管架/六支试管和玻璃棒。此前两瓶 A/B 场景用错，相关推理/动作记录仅为诊断证据，不算此场景验收。

玻璃棒已放入试管架靠操作区空孔。场景变更在 PAOS 的 `examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch` 管理，外部 LabUtopia 只作为本地运行依赖。误建的两个外部提交已撤回，远端未更新；以后本任务只向 PAOS 当前分支提交。

补丁基于本机原场景配置/构建代码，包含实际 USD 的棒位变更；不复制 benchmark 动作。原场景已应用此补丁，无需重复应用。其他安装可在对应 LabUtopia 工作区使用 `git -c filter.lfs.process= -c filter.lfs.required=false apply --check <PAOS>/examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch` 检查可应用性，再用相同配置的 `git apply` 应用（USD 为 LFS 文件，补丁操作针对已下载的文本内容）；已经应用的场景可用 `git -c filter.lfs.process= -c filter.lfs.required=false apply --reverse --check` 检查。此操作不创建外部 Git 提交。

静态 build/inspect 和 RTX 预览通过，棒底支撑间距 0.2 mm，两层孔板净空各 8.039 mm。悬空、插入实体板及孔边相交反例均被拒绝。源场景的规则抓取/旧 IK 报告不会进入 PAOS 感知链；新位置的物理稳定性、模型抓取和动作尚需验证。


原场景 r2 已获得清晰 RGB-D，但 VLM 报标签不可读（label=null），并将数支试管列为 mixing_vessel；后续理解 Provider 返回失败，未形成候选/动作。证据在 `out/releases/v15.9.0/tabletop-perception-20261023-r2/`。接下来需要定位具体分割/深度失败，并通过实际近景观测解决标签与容器语义歧义；不能用源配置的标签、物体路径或抓取标记补齐。

当前按用户仓库纠正，先单独提交已验证的场景补丁和说明；感知/动作重构保持工作区未提交，完整 Agent 验收未关闭。

## 透明物体专项复审（2026-10-23，v15.10.1）

检索结果、上游代码核对、方案排序与分阶段验收已保存到 [透明感知可行性审核](LAB_TRANSPARENT_PERCEPTION_FEASIBILITY_20261023.md)，本机回放数值见 [证据摘要](evidence/transparent-perception-20261023.json)。本节修正前述直接深度投影方案及 v15.10.0 的前景过滤计划；历史失败记录保留。

1. 原场景七个瓶子的种子连通点云位于桌面高度；去除背景后仅剩局部前景，不能作为完整玻璃表面。必须加入透明几何恢复和支持区域检查，不能把背景剔除当作恢复。
2. 优先验证近景 RGB-D＋SAM2＋ReMake 几何恢复＋现有 GraspNet；DFNet 作为第一轮对照。ReMake 的官方抓取端为 PCF-Grasp，我们只复用其几何机制。ClearGrasp 为条件对照，ASGrasp 等待匹配的原始 IR/RGB 输入，多视角重建为后续分支。
3. 两个 RGB-D 模型的 builder 默认将推理深度限制为 0.3–1.5 m；当前瓶子种子深度约 1.799–2.425 m，直接套默认值会清零。推理范围、单位、归一化、尺寸与内参必须按实际版本适配。增大范围不等于解决距离泛化；近景采集同时用于标签辨识与细棒可见性。
4. 删除“点云最高边就是瓶口”“可见棒端就是工作端”的推断依赖；分别验证抓取接触区、瓶口/杯口、棒工作端。模型输出标注为估计，未观测部分保持未确定，不能伪造置信度。
5. 私有执行关联仍读取原始深度，需与几何恢复接线同时改造；关联只服务仿真执行，不决定感知几何或标签。单对象失败不应抹掉其他可用观测，worker 故障仍明确报告。
6. 首先在同批输入上完成恢复模型与 GraspNet 对照、候选/功能点准备，再进行原场景 Agent 任务。USD 只供离线误差评估，不能补入在线点云。当前模型尚未安装/运行，本次结论是验证优先级，不是模型或运动验收。

## 可执行方案与新增依赖诊断（2026-10-23，v15.10.2）

详细实施顺序、责任层、文件范围、命令、产物和失败分叉已保存到 [透明器材感知接入方案](LAB_TRANSPARENT_PERCEPTION_IMPLEMENTATION_20261023.md)。当前主线确定为近景 RGB-D＋SAM2＋ReMake 几何恢复＋现有 GraspNet；DFNet 保持同输入对照。

本轮新增 Major 发现：`LabVisualPerception.resolve()` 在抓取前同时要求源/目标过程功能点，`refresh_process()` 目前仅更新目标容器。不能假定当前已经支持“先抓起来，再补看棒尖”；也不能以空功能点绕过准备。第一版在 acquire 前取得任务所需功能点，并修复持有后源工具/容器证据刷新，沿用已选候选和持有收据。

玻璃棒工作端如果被架子完全遮挡，优先补充标定视角；仍不可见时，需要同一根棒在安全可完整观察状态下的相机几何记录，再用当前可见部分定位。记录不从 USD 获取，每次抓取仍由 GraspNet 根据当前感知预测。没有完整记录且安全采集路径不成立时，搅拌子任务保持未准备；恢复模型不能代替缺失的观测条件。

下一实施切片为先修复感知/执行身份依赖和错误功能点推断，接入独立几何恢复 Provider 的无运动路径；完成输入、几何与准备验收后再继续原场景动作。本次保存方案，不代表上述实现已经完成。
