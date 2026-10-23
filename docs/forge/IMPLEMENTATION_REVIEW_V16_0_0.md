# v16.0.0 透明几何接入审查

2026-10-23。审查范围为 PAOS 的可替换几何恢复、视觉实体、点云抓取查询和准备边界。本阶段交付查询接入；完整 Agent 混合搅拌任务尚未验收。使用 anti-minimal-implementation、robotics-safety-implementation、experiment-reproducibility 和 implementation-review。

## 已修复的问题

| 严重度 | 发现 | 修改与证据 |
|---|---|---|
| Blocker | 透明区域的有效深度可能是背景，不能直接当瓶壁 | 新增恢复 Provider/worker；无权重或 worker 故障显式失败，无原始深度假成功回退；真实 ReMake 已运行 |
| Major | scene.understand 必须依赖仿真刚体，离线图像不能独立查询 | 观测实体由视觉侧生成；执行对应移至准备/能力侧，读取恢复点云并保留原 entity_ref；离线实测不创建 Isaac engine |
| Blocker | 最高点/标签上沿可被拟合成瓶口，可见棒端被当完整工作端 | 删除这些规则；仅接受独立图像 landmark 支持的功能点拟合，隐藏端点/未验证几何不能通过准备 |
| Major | 原始深度种子连通过滤截断恢复点云 | 从恢复链及代码中移除；掩码内完整有效恢复表面进入 GraspNet，13 份点云实测可复现 |
| Major | 为满足契约把有效深度比例当几何置信度 | 删除伪置信度；标准抓取契约与 Agent 投影支持有来源的点云独立输入，原 envelope 路径保持验证 |
| Blocker | 反复查询可能覆盖候选，准备可能使用未经匹配的位姿 | 原始模型结果逐次保存、候选引用独立；准备比较完整被选候选，只作标定坐标变换；篡改与重查测试通过 |
| Major | 持有刷新只更新容器，源工具功能点沿用旧值 | 同时要求当前源/目的功能点；使用反馈表达既定持物坐标系，不重选/重标 acquisition 候选；替换测试验证历史不变 |
| Major | 多对象中的一个无效 mask 会丢失其余对象 | 逐对象失败留存；基础设施故障仍整体显式失败；不可读标签对象保留几何、标签身份保持未定 |

这些修复没有引入第二套任务状态机或额外 hash。准备侧拒绝未验证几何针对已实测的米级深度位移和被遮挡棒段：路线碰撞检查不能证明输入重建正确或补全未知物体范围。当前模型均返回 `unverified_estimate`，没有强制执行开关。

## 责任与依赖

通用层拥有语义、实体、候选、Query/Action 契约及投影；Provider 拥有分割、几何恢复、抓取模型；Isaac Adapter 拥有标定捕获和私有刚体对应。更换 ReMake/DFNet 不修改 Agent/Tool。ReMake 官方抓取执行器未接入；倾倒/搅拌仍使用 PAOS 已有的参数化准备和执行边界。

证据链为 capture → mask/解释 → 恢复元数据与点云 sidecar → 原始模型候选 → 准备 → 执行反馈。原始深度、恢复深度和未知功能点分别保存。相机光学坐标与世界坐标依据该次 calibration 转换，旧 calibration 不能被新 observation 复用。重复理解同一 capture 返回原结果，不清除候选历史。

Runtime/Coordinator 继续拥有持有、取消、恢复和结算；Provider 的进程释放只管理模型资源。仿真几何没有进入恢复或候选；准备中的射线对应只选择执行刚体。当前 `validated_observation` 语义需要后续有证据的几何测量来源，现有两个恢复模型不产生该资格；完整 process binding 因缺有效空间几何继续不可用。这是明确未完成的执行能力，不以接口测试冒充验收。

## 验证证据

- 集成：998 passed、2 failed。失败为此前已有的 node 版本断言和发布包锁一致性检查，未为了本任务修改发布锁。
- 清理后相关测试：19 passed、1 skipped；跳过的是默认不加载外部权重的 parity 测试。探针与准备阶段测试另外 31 passed。
- 实际模型数值对照：1 passed；同一原始 RGB-D/mask、同一训练权重，CPU 最大绝对差 0 m。
- 第三人称：回放 VLM/SAM2，真实 ReMake 与 GraspNet，13 点云、256 候选。
- 腕部：新 RGB-D/VLM/SAM2/ReMake/GraspNet，11 点云、192 候选。
- DFNet：官方下载配额阻止权重获取；真实 worker 启动返回缺权重失败，未伪装成模型对照结果。

命令与依赖见 `../../examples/forge-adapters/robotwin20/runtime/transparent-geometry.md`。结构化证据见 `evidence/transparent-implementation-20261023.json`，完整输出目录记录在实施文档中。Ruff 与 scoped Git whitespace 检查均通过；无新模型/依赖进入 LabUtopia 源码仓库。

## 执行验收仍缺少的证据

1. 能读出唯一试剂标签、无机器人本体遮挡的标定近景。
2. 透明瓶颈、杯口、棒径及完整棒端的几何误差测量；当前第三人称恢复位置明显不符，不能执行。
3. 由已验证观测生成空间几何与功能点，并进入标准 process binding、碰撞/可达准备。
4. 经已准备路线完成实际抓取、倾倒、搅拌和归位的反馈、取消与 Runtime 结算。

以上属于完整功能验收的 Blocker，当前记录不关闭这些问题，也不宣称 motion-ready。后续优先解决观测和几何测量；当前没有发出机械臂运动。
