# 多试剂倾倒与手持棒搅拌：场景升级诊断

日期：2026-10-15（Asia/Shanghai）。源码参考：`cd96c8bf`，分支 `feature/planning-loop`。
状态：需求与源码诊断；新能力尚未实现，本次未运行仿真或硬件。
后续入口：[实施计划](LAB_POUR_STIR_IMPLEMENTATION_PLAN_20261015.md)、[可行性自审](LAB_POUR_STIR_FEASIBILITY_REVIEW_20261015.md)。

## 1. 结论

推荐复用现有观察、对象绑定、抓取、放置与任务生命周期，增加倾倒和搅拌两项有界 Action，
并补齐持物操作准备、操作后归位、过程证据和实验室任务方法。
新增 Tool 名称暂定为 `object.pour`、`tool.stir`；名称不是已经发布的接口。

主要工作量在“抓住之后继续操作”的执行与验证链，而非提示词或两个 Tool YAML。
已有公共准备接口围绕抓取候选，放置接口直接投影抓取结果，持物管理器只接入 acquire/place。
因此，倾倒/搅拌结束后的当前持物状态、场景修订和归位路线必须一起接通。

## 2. 需求来源与确认状态

| 项目 | 状态 | 依据与解释 |
| --- | --- | --- |
| 实验室台面、多个带标签瓶、接收容器、器材 | 已确认 | 用户场景描述与提供的 Gemini 对话 |
| 每项任务至少操作两种试剂 | 已确认 | 聊天截图要求“至少两种试剂的操作” |
| 任务直接给出试剂和顺序 | 已确认 | 用户明确选择；Agent 不自行改写配方顺序 |
| 手持棒搅拌 | 已确认 | 用户明确选择；不采用磁力搅拌器主路线 |
| 可以无液体，只体现动作 | 已允许；首版建议采用 | 截图明确“可以不用液体，只要动作” |
| 沿用 RoboTwin/Franka | 推荐实现前提，待任务配置确认 | 用户最后一条复述了该问题，没有单独明确回答 |
| 目标瓶受阻，先移开挡物 | 推荐主要规划变化，待场景确认 | 上轮建议；不当作已经确认的验收要求 |
| 四瓶、A/B/C/D 标签、开口瓶、固定烧杯、棒架 | 首版建议 | 数量、标签语言、瓶盖和杯子固定方式尚未确定 |
| 瓶身标签表示试剂还是产物 | 待明确 | 首版建议表示瓶内试剂身份；不要求化学推理 |
| 双臂同步、拧盖、定量液体、化学反应 | 不在首版建议范围 | 现有用户要求未包含这些能力 |

明确顺序后的规划目标是按约束完成现场操作：识别、可达性判断、清障、临时放置、结果核对与恢复。
布局随机化只能证明部分泛化；至少一种条件变化应实际改变计划中的前置步骤，才能展示状态驱动规划。

## 3. 当前源码证据

下表行号对应上述源码参考；后续实现以符号与文件为定位依据。

| 证据 | 当前行为 | 升级影响 |
| --- | --- | --- |
| [Skill](../../examples/forge-skills/pick-place-workflow/SKILL.md) L79-L123、L169-L174 | 原子抓放节点、逐段刷新、统一任务验证 | 复用任务主干，增加方法与动作依赖 |
| [manifest](../../examples/forge-skills/pick-place-workflow/skill.yaml) L1-L18 | 工作区版本 3.0.25，required_tools 包含观察、目标解析、抓放 | 工作区版本不等于现场安装版本；新能力需发布到实际部署包 |
| [prepare 契约](../../examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml) L1-L54 | Query 必须消费 candidate_set/candidates；描述针对抓取候选 | 不能把旧 preparation_ref 直接用作持物倾倒/搅拌许可 |
| [place 契约](../../examples/forge-skills/pick-place-workflow/contracts/object.place.tool.yaml) L10-L41 | 从前驱 object.acquire 投影场景、抓取和准备引用 | 新动作插入后须增加当前持物结果来源并更新准备路线 |
| [PersistentPossession](../../examples/forge-skills/pick-place-workflow/src/pick_place_workflow/persistent_runtime.py) L31-L85 | begin 仅支持 acquire/place，依 owner/entity/acquisition 关联持物 | 新动作必须保留原抓取归属、更新当前结果，未知时对账 |
| [计划生成器](../../examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py) L193-L245 | 每个子任务展开固定抓放顺序，父依赖和最终验证指向 .place | 实验室任务不能直接套该函数表达倾倒/搅拌 |
| [执行端口](../../PhyAgentOS/forge/capability_runtime/ports.py) L16-L35、L61-L66 | 通用 ActionDriver/ActionAdmission 可复用；ManipulationExecutor 仅 acquire/place | 在同一 Gateway 生命周期注册新端点，按实际调用者扩展端口 |
| [通用 Runtime](../../PhyAgentOS/forge/capability_runtime/runtime.py) L110-L138 | 通用 Tool 注册与发现 | 无需新增实验室专用任务调度器或执行协议 |
| [部署组合](../../examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py) | 共享 worker/world，注册抓放及 grounding 端点 | 增加 profile、端点与包内容，保持同一 Runtime |
| [任务 Adapter](../../examples/forge-adapters/robotwin20/runtime/robotwin_blocks_ranking_adapter.py) L33-L37 | validate_task_name 拒绝与本 Adapter 不同的任务名 | 实验室需要薄任务 Adapter 与装配入口，不能仅替换场景名 |
| [Skill 目标规则](../../examples/forge-skills/pick-place-workflow/SKILL.md) L107-L115 | benchmark 模式禁止自主 staging/target | 清障应使用实验室支持的目标模式，不放宽旧 RGB 模式 |

搜索范围为 `examples/` 与 `PhyAgentOS/` 中 YAML Tool 声明，本次未找到倾倒/搅拌能力声明。
以上是工作区接口诊断，不包含现场 Gateway 能力发现或安装版本核验。

## 4. Skill、Tool 与 Runtime 的落点

| 层 | 本次职责 |
| --- | --- |
| 实验室方法 Skill | 读取用户给定的试剂顺序，选择当前对象、清障方法和续接方式 |
| PlanGraph / Coordinator | 保存一个任务的依赖、计划修订、执行记录和结果；保持原顺序约束 |
| 准备 Query | 根据当前持物、容器、工具和现场生成并检查有界路线；不推进模拟 |
| pour / stir Action | 启动已准备动作，沿现有 invocation poll/cancel/stop 路径返回结果 |
| RoboTwin Adapter / worker | 坐标、碰撞、轨迹、控制、功能点和实测结果；公共契约不含 SAPIEN 类型 |
| 既有 Verifier | 依据有来源的动作过程证据和最后状态检查整体任务 |

[Runtime/Skill 迁移文档](RUNTIME_BINDING_SKILL_USE_DESIGN.md)明确其多 Skill/按需 Tool 绑定属于迁移方向，
不能当作当前全部可用能力。首版沿现有 manifest-v2 安装链交付，验证方法文档与同一部署包的绑定。
将完整 Runtime/Skill 解耦迁移列为实验室任务前置条件会无谓扩大范围。

## 5. 推荐动作边界

### 倾倒

已知持有正确瓶子 → 接近接收容器 → 瓶口对齐 → 倾斜保持 → 回正 → 撤离。
成功后仍持瓶，由后续 place 归位。一次 Tool 调用拥有上述动作段的执行、取消和结果。
瓶口对齐和倾角阈值由资产、容器和 profile 标定，保持时间按秒定义，再按模拟时步实现。
倾倒前路线应保证指定终态可达；中断时不自动盲目执行“回正/归位”，先使用实际状态判断恢复。

### 搅拌

已知持有棒 → 对齐杯口 → 插入 → 完成指定圈数/时长的轨迹 → 提起退出。
成功后仍持棒，由 place 归架。棒尖轨迹需要由夹持变换换算到机械臂末端。
首版采用杯内无接触轨迹；壁面接触控制另行研究，不作为现有位置控制能力。

两项动作都必须绑定当前抓持归属和现场，不允许取得新 preparation 后默默沿用旧路线。
动作进行中、失败后以及进程重启后的持物状态继续由 Runtime 拥有。

## 6. 资产与感知缺口

- 同形瓶不同标签可减少形状捷径；位置和标签映射应能变化。真实标签识别必须来自图像。
- 环境 target_id 可以供专家或评分使用；直接传给 Agent 不能证明视觉选瓶。
- 透明烧杯和细棒可能无法提供当前观察几何所需的点云与支撑事实。
  首版建议可见杯沿/不透明或磨砂接收容器、可抓握的加粗棒柄和稳定棒架；具体尺寸需测量。
- 烧杯碰撞体必须保留开口与内腔；渲染网格是空心不代表碰撞体可插入。
- 功能点包含瓶口、杯口、杯内区域与棒尖，均须说明局部坐标、单位和当前观测位姿来源。
  仿真 actor pose 仅供执行对应或独立评分；不能填补 observation-owned 路径缺失的几何。
- 开口瓶、固定或自由烧杯、归位区和清障暂存区需要在场景规格中明确。
  若采用固定杯座，应如实报告固定夹具，而非宣称完成自由容器稳定操作。

## 7. 过程验证与恢复

最终评价至少消费：目标瓶身份、接收容器身份、每次倾倒的动作测量与顺序、搅拌轨迹测量、
操作后持有状态和要求的归位状态。复用现有 invocation、artifact、settlement 与任务证据，
不另建配方状态库。语义事实的名称和字段在实现阶段按现有证据消费者确定。

| 情况 | 必须保留的事实与行为 |
| --- | --- |
| A 成功、B 尚未开始 | A 的成功过程保留；续接 B，不能从头重倒 A |
| B 执行中超时、结果未知 | 根据原 invocation 对账；不能把超时当未执行并重试 |
| 倾倒完成但归位失败 | 倾倒与归位分别记录，恢复放置，不重做倾倒 |
| 持物丢失 | 更新 Runtime 持物事实，重新观察；不能继续执行持物路线 |
| 搅拌中断 | 记录已执行轨迹与棒尖位置，明确继续或重新准备，不凭最终插入位置判成功 |
| 用户取消 | 停止请求与停止确认分别记录，不把请求提交当作实际停止 |

无液体评价只能证明代理动作条件。禁止报告体积精度、混匀率或化学产率。

## 8. Gemini 示例审查

用户粘贴的 Gemini 内容是构想来源，外部平台任务数量和资产库存本次未独立核实。
其中代码存在以下可直接从文本确认的缺口：

1. 只有一个 target_id，未覆盖至少两种试剂的顺序任务。
2. 使用环境给出的 target_bottle，未实现相机标签识别。
3. 倾倒段未显式构造倾斜和保持，归位注释后仅抬升。
4. beaker_inner_center 被计算但未用于移动；把圆上坐标逐个作为增量不等于围绕指定圆心运动。
5. 最终棒尖位置不能证明倾倒和完整搅拌；补充单瓶布尔值仍未表达多试剂过程。
6. create_actor/place_actor 等参数、动态凹碰撞体支持和资产可用性需要按实际版本确认。

## 9. 可行性判断

架构上可通过现有扩展点接入；无液体、顺序操作的首版具有合理可行性。
真实仿真完成率尚未测量，最大风险依次是细棒抓取及杯内几何、持物操作后的路线接续、
标签与目标绑定，以及旧抓放部署对新方法的支持。
实施顺序应先打通单操作和持物接续，再组合双试剂，最后加入受阻条件；详见配套计划。
