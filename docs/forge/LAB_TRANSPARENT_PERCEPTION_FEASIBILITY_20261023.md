# 透明实验器材感知：检索结果与可行性审核

日期：2026-10-23（Asia/Shanghai）。范围：用户原有 tabletop_station 场景，RGB-D 感知、GraspNet 抓取及倾倒/搅拌功能点。结论为技术选型和修复方案；尚未运行本项目的透明几何恢复模型或完成新链路运动验收。

## 选型结论

**推荐优先验证“近景 RGB-D＋SAM2 实例分割＋ReMake 几何恢复＋现有 GraspNet”。DFNet 保留为接线和效果对照。** 在此前讨论的四条路线内，DFNet 的现有接口最直接；本次补充检索后，ReMake 的实例掩码、相对深度及多视角实验更贴近当前斜视场景，值得作为主候选。[S1–S5]

这里的“首选”指下一轮工程验证优先级。尚无本项目实测结果证明 ReMake 最准确或已经满足夹爪、杯口和玻璃棒精度。ReMake 官方实验使用作者的 PCF-Grasp；我们只接入其几何恢复部分，抓取候选继续由现有 GraspNet 产生。[S2]

| 方案 | 输入与公开资源 | 本项目主要代价/不足 | 采用顺序 |
|---|---|---|---|
| ReMake | RGB-D＋实例掩码＋从 RGB 估计的相对深度；代码、权重入口、推理脚本已公开 | 需要两个模型的权重、输入适配和独立 worker；细棒、瓶口和当前 GPU 未验证 | 主候选，先离线几何，再同一 GraspNet |
| TransCG / DFNet | RGB-D；官方给出修复深度到 GraspNet-baseline 的链路 | 官方历史记录存在深度整体偏移；输入裁剪、归一化、插值和版本差异需检查 | 第一轮对照；用于区分几何模型与接线问题 |
| ClearGrasp | RGB-D；预测法线/边界/透明区域，再优化深度；有代码和权重 | 三个预测模型与 C++ depth2depth；官方依赖较旧，CPU 优化增加部署工作 | 条件对照：前两者表面形状失败时再引入 |
| ASGrasp | 原始左右 IR＋RGB、相机标定；公开代码与权重入口 | 当前 Adapter 只有 RGB/depth/point_cloud；官方还接 GSNet，需拆出重建部分 | 获得匹配的主动双目输入后再评估 |
| Dex-NeRF | 标定多视角图像，透明感知的 NeRF 几何；原方法接 Dex-Net | 需额外视角、静态场景和重建流程；持物后场景变化需处理 | 单视角持续失败且多视角采集可行时的研究备选 |

排序依据是当前输入兼容性、目标失败模式、可用推理资源和 PAOS 接入工作量，没有人为打分或推断本机成功率。[S1–S8]

## 本地证据与审核发现

原场景入口仍为 `/home/yanxu/LabUtopia` 下 `python scripts/preview_tabletop_station.py --view third-person`。玻璃棒位于试管架空孔，场景补丁由 PAOS 管理。下列数值重新读取 r2 产物得到，机器可读记录见 [evidence/transparent-perception-20261023.json](evidence/transparent-perception-20261023.json)。原始图像/数组保留在本机 `out/releases/v15.9.0/tabletop-perception-20261023-r2/`，本次文档提交不包含这些大文件。

| 严重性 | 发现与定位 | 修复要求 |
|---|---|---|
| Blocker | 七个试剂瓶的种子连通点云都落在 z=0.712872–0.714960 m，仅约 0.5–2.0 mm 高，与桌面一致。`visual_perception.py:L195-L202` 仍将该点云交给定位。 | 先恢复/验证目标表面；非零深度和 mask 内部位置不能证明测到了玻璃。 |
| Blocker | `visual_geometry.py:L50-L65` 从最高 4 mm 点拟合圆；前景过滤后瓶云仅高 26.259–63.095 mm，回放中可能将标签上沿当瓶口。 | 去背景仅作清理；瓶口必须由独立可见边缘、局部几何及必要的补充视角支持。 |
| Blocker | `visual_geometry.py:L42-L49` 以可见点云极值取棒端；玻璃棒回放仅见 z=0.821161–0.969106 m，长度约 147.946 mm。 | 将露出抓取段与搅拌工作端分开；看不到的端点保持未确定，不能用可见上端冒充工作端。 |
| Major | `execution_identity.py:L29-L54` 再读原始深度并要求射线命中距离相差不超过 10 mm。即使前端修好了点云，该路径仍可能在桌面处关联失败。r2 总失败的具体根因尚未被该日志直接证实。 | 观测实体先独立成立；仿真私有关联单独消费同批感知证据，不再以原始错误深度覆盖恢复结果；关联失败保留给准备阶段。 |
| Major | `visual_perception.py:L181-L216` 的批处理仍可能因一个对象异常失败；`L222-L242` 将语义分数与有效深度比例相乘，也不能表征玻璃几何可信度。 | 保存逐对象失败及 worker 故障；区分对象未确定与全局服务失败；几何来源/支持区域与语义分数分开。 |
| Major | 七个可见瓶子的 label 都未读出；裁剪回放仍不可读，部分试管被解释为 mixing_vessel。 | 获取真正更近或更清晰的图像并复核类别；不能按瓶位、颜色或 USD 标签补齐试剂身份。 |
| Major | r2 是渲染器相机输入，当前未提供双 IR，未校准为某一真实深度传感器的透明物体误差模型。 | 分别报告仿真感知和真实传感器证据；相机渲染成功不能证明真实玻璃感知已通过。 |

上表定位指 2026-10-23 审核时的待提交实现。当前总任务仍未验收；本轮只修订方案和保存诊断。

## 为什么不能直接照搬上游推理

**深度裁剪是一个已查明的接入失败场景。** ReMake 的 `run_utils/builder.py:L114-L122` 默认推理区间为 0.3–1.5 m；其 `configs/inference/remake.yaml` 的 inference 段未覆盖该区间。dataset 段的 0–10 m 不会自动成为 inference 参数。DFNet 的 builder 也有同样的 0.3–1.5 m 默认值。当前七个瓶子种子像素的原始深度为约 1.799–2.425 m；这些点本来就多为背景，再照抄默认配置还会被清零。[S3,S4,S6]

应显式记录原始深度单位、有效区间、归一化与裁剪比例。优先取得更近、目标占比更大的观测；保留 r2 作为失败回放，研究远距离输入时单独配置范围。扩大裁剪范围只避免丢数据，不能证明模型在该距离泛化。

**尺寸与标定必须保持一致。** r2 为 1600×1200，ReMake 示例内部为 640×480，推理函数默认输出为 1280×720。不能让默认输出配上原图内参。若恢复到原分辨率，再使用原内参；若在缩放/裁剪坐标系反投影，应同步缩放焦距并平移主点。RGB、深度、mask 要执行同一像素变换。[S3,S4]

当前棒的 VLM 框宽仅 15 像素，整图缩到 640 宽只剩 6 像素；这只是框宽，真实棒截面可能更小。提高输出插值尺寸不会增加原始证据。因此近景观测是首选路线的一部分。可评估有周围深度参照的局部裁剪，但不能直接把裁剪推理效果当作模型原训练分布内的表现。

**上游例程不是可直接托管的 PAOS worker。** ReMake 的推理函数在每次调用内加载相对深度模型，并含固定 480×640 插值；需要把模型加载放到 worker 生命周期，检查所用 checkpoint、mask 含义及尺寸。其 `elif self.model_type == 'tode' or 'dfnet'` 会错误接受其他 model_type，封装时应采用明确支持的模型分支。这些是具体适配修复，不需要新框架。[S3]

ReMake 默认相对深度路径使用 Depth Anything V2 small，另需对应权重；相对深度本身没有本项目所需的公制保证，必须经过 RGB-D 恢复链和标定后再用于几何。官方 README 的权重链接已核实存在，本次未下载或加载任何 checkpoint，链接存在不代表文件可直接加载。[S2,S4]

DFNet README 的示例与当前 `inference.py` 的构造参数/返回值存在差异；当前代码返回 `(depth_res, depth_ori)`，并含可选最近邻补洞和输入归一化。Adapter 必须按读取到的实际版本适配，补洞产生的点属于估计结果。不能把 README 示例当成已验证接口。[S5,S6]

本机 GPU 查询为 RTX 5060 Ti、16311 MiB 总显存。上游环境分别包含较旧的 PyTorch/CUDA；尚未验证本 GPU 的兼容运行时、显存占用或延迟。采用独立 worker，先跑官方样本，再回放本项目输入；复用现有 worker 生命周期顺序调度 SAM2、恢复模型、GraspNet，不新增第二套资源调度器。

## 文献证据能够支持什么

- TransCG 官方明确描述“深度恢复→按内参生成点云→GraspNet-baseline”。它支持这条接口路线；不能证明现有标签瓶、细棒或功能点精度合格。[S5]
- DFNet 官方 2022-10-10 更新记录仍提到约 2 cm 偏移，2022-10-14 又更新了正确 checkpoint。这是历史版本注意事项，不能将它改写为所有当前输出固定偏移 2 cm；更不能为本场景无依据地统一减去 2 cm。[S5]
- ReMake 的 2025 arXiv 版本 Table II 报告斜视平均抓取率为 73.47%，同表 DFNet 为 10.20%；平视分别为 71.43% 和 2.04%。每视角 7 类、每类 7 次，是作者系统的小规模对比；用于提高验证优先级，不能转成 PAOS 的成功率。官方 README 当前另列 2026 RA-L 发表信息。[S1,S2]
- ClearGrasp 通过法线、透明区域、遮挡边界和全局优化恢复深度；它有不同的几何约束，适合作为条件对照，但不是自动更好的选择。[S7]
- ASGrasp 面向原始主动双目输入，官方入口依赖 GSNet；把一张深度图复制为左右图不满足输入条件。Dex-NeRF 的原始抓取端是 Dex-Net；多视角方案仍需独立验证与现有 GraspNet 的接线。[S8,S9]

## PAOS 责任与证据链

```text
同批相机观测（RGB、深度、内外参、观测引用）
  → 实例/标签解释、透明区域与深度质量诊断
  → 可替换的几何恢复 Provider（先 ReMake，对照 DFNet）
  → 带观测/估计来源和支持区域的公制几何
  → GraspNet 原始候选
  → 准备：被选候选、接触几何、可达性、碰撞、功能点
  → 执行反馈 → Runtime/Coordinator 结算
```

| 责任 | 所属层与可替换边界 |
|---|---|
| 试剂身份、目标语义、能力发现 | Agent/通用领域层；不暴露 ReMake、DFNet 或场景 Prim |
| 恢复深度/局部几何及模型状态 | scene.understand 背后的 Provider 接缝；用现有 artifact/source_refs 承载输出 |
| 内外参、单位、像素变换、渲染/设备采集 | 相机 Adapter；替换仿真或真实相机保持调用方语义 |
| 抓取位姿预测 | 现有 GraspNet Provider；允许明确标定变换，不允许私有位姿替换 |
| 过程功能点、准备资格 | 对应感知/准备能力；抓取接触区、瓶口/杯口、棒工作端分别有证据 |
| 持有、取消、执行状态、恢复、结算 | 既有 Runtime/Coordinator 与执行 Adapter；不另建状态机 |

几何 artifact 在 Provider 元数据中区分传感器值、模型估计和未支持区域，并绑定原始观测、实例 mask、模型/配置版本与像素变换。传感器值也可能错误，来源不能代替质量判断。无需把某个网络的张量字段加入公共 Tool 契约，也不自行伪造校准置信度。

仿真真值只供离线误差测量；不能修补在线点云、生成候选或决定可见标签。私有执行身份关联可以使用环境机制对应物体，但不能成为感知成功的证据或回流几何。关联存在歧义时准备不能执行。

新鲜度沿用 observation/revision/frame/calibration。多视角融合要证实物体未发生未建模移动；持物后旧姿态不可直接复用。模型恢复单视角可见表面不等于获得整个封闭物体，payload 与功能点准备须处理未观测部分。

## 推荐执行顺序与验收

1. **先改善观测并保留失败输入。** 第三视角用于全局选择；利用已有腕部相机或额外标定观察位取得标签、瓶颈、杯口和棒段近景。相机需要机械臂移动时仍经过现有路线准备与停止控制。输出清晰标签或明确未确定、实例 mask、同批标定，不靠放大旧图猜字。
2. **完成输入适配与独立恢复实验。** 先检查官方样本加载，再用相同观测比较原始深度、前景过滤、ReMake、DFNet。记录实际权重来源、配置、输入裁剪比例、处理时间、峰值显存和失败阶段。前景过滤是诊断对照，不作为恢复方法。
3. **分别测几何。** 在相同图像 mask/区域内报告深度误差分布、背景残留、覆盖率；分别测瓶颈接触区、瓶口/杯口中心与轴、棒径和工作端。USD 真值由独立离线评估器读取，推理进程只收到相机产物。不能用全图平均误差掩盖细棒或杯口错误。
4. **保持同一个 GraspNet 验证候选。** 固定模型、采样设置和已记录随机性，仅替换上游几何；保存候选与接触可视化。验证候选未被改写，并记录准备拒绝原因。单独确认 TCP/GraspNet 接触点约定；抓取通过仍不等于倾倒或搅拌功能点通过。
5. **通过准备后执行原场景任务。** 先做单对象抓取/归位，再由 Agent 按实际可读标签选择试剂，执行双倾倒和搅拌。沿用原有速度、碰撞、工作空间、取消及持物检查；记录失败，不用 benchmark 动作回退。

几何容差应由实际夹爪接触余量、瓶口/杯口净空、棒径和过程要求确定，不能从论文全局误差或模型分数直接指定一个“可执行”阈值。容差未确定或所需区域无证据时保持未准备，不宣称完整验收。

**失败分叉：** 官方样本都失败则先修依赖/权重/接口；样本通过而本场景失败则查单位、裁剪、像素标定、可见尺度和渲染分布；ReMake 与 DFNet 都失败则补充视角，并视法线/边缘质量引入 ClearGrasp；确有主动双目原始数据时才比较 ASGrasp。细棒或隐藏工作端仍不确定时，单独改进观测，不能通过规则抓取掩盖。

最小替换测试需证明 ReMake/DFNet 输出经同一 artifact 接缝进入同一 GraspNet；最小失败测试包括原始桌面深度、标签带假瓶口、遮挡棒端、深度全被裁剪、尺寸与内参不匹配、单对象失败、旧观测及候选被覆盖。它们针对上述实际失败，不新增 hash、冻结契约或重复门禁。

现有无运动集成检查命令如下；后续新增 Provider 测试应并入对应集合。当前这些测试不含未安装模型的实际推理，不能代替第 2–5 步。

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  .venv/bin/pytest -q \
  examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_pipeline.py \
  examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py
```

本轮实际验证只读取既有数组、核对上游源码/论文、校验保存的文档与 JSON。没有下载模型、训练、相机移动或运动执行。

## 检索记录与来源

检索日期为 2026-10-23。先复核此前四条路线，再检索 transparent object depth completion / RGB-D / pretrained / 2025–2026，补充 ReMake。纳入条件为与当前感知输入/抓取目标有关且可核查的论文、作者项目页和官方代码；未按引用数、网页热度或年份排序。这是工程选型的定向检索，不声称覆盖全部工作。搜索结果中仅有题名/摘要、尚未核对推理实现的条目不进入推荐排序。

GitHub raw 读取部分超时，已通过 GitHub contents API 核对对应源码；arXiv HTML 首次读取成功，后续重读超时。保存的是来源、摘述与审核证据，没有复制论文全文，也没有验证下载链接内的权重文件。

- **S1** ReMake 论文，arXiv:2508.02507v1（2025-08-04），方法与 Table II：<https://arxiv.org/html/2508.02507v1>。
- **S2** ReMake 官方仓库 README，环境、checkpoint 入口、PCF-Grasp 关系、推理脚本及 2026 发表信息：<https://github.com/ChengYaofeng/ReMake>；作者页：<https://chengyaofeng.github.io/ReMake.github.io/>。
- **S3** ReMake 推理与 builder：<https://github.com/ChengYaofeng/ReMake/blob/main/run_utils/inferencer.py>；<https://github.com/ChengYaofeng/ReMake/blob/main/run_utils/builder.py>。
- **S4** ReMake 推理配置与相对深度加载：<https://github.com/ChengYaofeng/ReMake/blob/main/configs/inference/remake.yaml>；<https://github.com/ChengYaofeng/ReMake/blob/main/relat_depth_models/load_reldepth_model.py>。
- **S5** TransCG / DFNet 官方仓库与 GraspNet 接线：<https://github.com/Galaxies99/TransCG>；<https://github.com/Galaxies99/TransCG/blob/main/assets/docs/grasping.md>；数据/项目页：<https://graspnet.net/transcg>。
- **S6** DFNet 实际推理与 builder：<https://github.com/Galaxies99/TransCG/blob/main/inference.py>；<https://github.com/Galaxies99/TransCG/blob/main/utils/builder.py>。
- **S7** ClearGrasp 官方仓库，方法、权重入口、依赖与 depth2depth：<https://github.com/Shreeyak/cleargrasp>。
- **S8** ASGrasp 作者页与官方仓库，原始 IR/RGB 输入和 GSNet 入口：<https://pku-epic.github.io/ASGrasp/>；<https://github.com/jun7-shi/ASGrasp>。
- **S9** Dex-NeRF，PMLR 164（2022），多视角/透明深度与 Dex-Net：<https://proceedings.mlr.press/v164/ichnowski22a.html>。
