# 倾倒与搅拌完整操作：PAOS 架构诊断与修订方案

日期：2026-10-18（Asia/Shanghai）。设计基点：`b4dac9ab`；实现检查基点：`352fe271`、`c4f2a194`、`4e93476d`、`f7da28d6`、`b615a253`、`ba168a7f`，分支 `feature/planning-loop`。
状态：PAOS Tool/Runtime 契约、离线反馈计算器、provider 无关阶段事实协议、显式 cycle 能力声明、no-motion control-loop、provider-neutral `AtomicExecutor` 和反馈规范化适配层已实现，定向回归为 `140 passed`。复审额外修复了搅拌反馈断点只重置圈数、未同步重置连续时长，以及缺少 artifact ref 时过程事实被抹除的问题。具体设备采集、SDK/仿真/真机适配与验收不在本阶段范围。本状态不代表 cycle 可在物理设备上运行。
配套：[设计审核与验证矩阵](COMPOSITE_POUR_STIR_REVIEW_20261018.md)。

## 1. 当前需求与结论

用户要求一次“倾倒”涵盖抓取瓶子、移动、倾倒、回正、放置；搅拌采用相同的完整操作边界，包含取棒和归架。
当前没有称重测量，首版成功目标是完成指定操作过程，不包含剂量验证或混匀质量验证。无称重不代表没有液体，也不代表没有机械臂状态反馈。
非夕是用户提出的设备场景；现有实验室实现主要针对 RoboTwin/Franka。二者共享语义设计，设备控制与真机验收分别落实。

推荐一个完整操作对应一个可执行 PlanNode、一个 Action Tool 和一个 Gateway invocation。Adapter/worker 内部保留多个执行阶段。
这里的“原子”仅指一次对外结算；物理效果可能部分完成，不具备事务回滚能力。Runtime 必须报告部分完成事实。
观察、绑定、准备和最终任务验证仍可有各自 Query/节点；“一个倾倒节点”不承诺整个任务只调用一次工具。

本方案针对操作粒度替代 [2026-10-15 实施计划](LAB_POUR_STIR_IMPLEMENTATION_PLAN_20261015.md) §3/P3/P4 的外部分步链。
该旧计划的资产、几何、碰撞、功能点和过程测量要求继续有效；其“无液体仿真”属于旧场景条件，不能推定当前非夕场景也无液体。

## 2. 源码依据与现有缺口

| 依据（路径相对仓库根目录） | 已确认事实 | 对设计的约束 |
| --- | --- | --- |
| [规划设计](PLANNING_MODULE_DESIGN.md) L23-L38 | 一个节点由一个 Tool 结算；完整 Tool 可拥有复合意图 | 可合并操作粒度，不能仅靠 Skill 文字把多个 invocation 伪装成一个 |
| [PlanNode](../../PhyAgentOS/planning/contracts.py) L243-L256 | 节点表示一个语义结算义务 | Core 无需新增 pour/stir 专用节点类型 |
| [执行端口](../../PhyAgentOS/forge/capability_runtime/ports.py) L14-L34 | provider driver 提供 poll/cancel/stop；Gateway 分配 invocation/attempt | provider 拥有阶段执行；poll 不启动或重放运动 |
| [通用 Runtime](../../PhyAgentOS/forge/capability_runtime/runtime.py) L317-L426 | result 才输出终态；Action cancel 与 Session stop 分开 | Action 使用 cancel；超时和取消请求均不证明物理停止 |
| [任务协调器](../../PhyAgentOS/forge/task.py) L3626-L3665 | 相同 Action 的未知效果须先对账 | 超时不能重发整个倾倒或搅拌 |
| [现有方法](../../examples/forge-skills/pick-place-workflow/README.md) L31-L34、L64-L77 | acquire 内已有 approach/contact/close/lift 等阶段 | 多阶段封装符合已有分层方式 |

初始诊断来自当时的 held-operation 原型。其后 PAOS Tool/Runtime 契约已实现；以下旧实现摘录仅解释历史缺口，不代表当前反馈计算器行为。

| 工作区文件 | 当前语义 | 复合 Action 缺口 |
| --- | --- | --- |
| `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/held_manipulation.py` L20-L29、L161-L169 | 参数必须带原 acquire 和最近持物引用，入口要求 holding | 新复合入口应从 empty 开始，不要求调用方先抓取 |
| 同文件 L197-L210 | 倾倒比较 aligned_hold_s 与 maximum_tilt_rad；搅拌比较圈数和时长 | 缺少联合条件时间窗口与完整取放的成功表达 |
| 同文件 L230-L243 | pour/stir 成功要求 possession_state=holding | 完整操作成功应为对象已放好、末端 empty 且已撤离 |
| `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/persistent_runtime.py` L31-L99 | 持物来源围绕 acquire invocation 和最新 held invocation | 需扩展原持物 owner，不能为复合操作伪造一个公共 acquire invocation |

实现前的历史判定摘录：

```python
# held_manipulation.py 的当前过程判定（未提交原型）
if arguments["operation"] == "pour":
    return at_least("aligned_hold_s", params["hold_s"]) and at_least("maximum_tilt_rad", params["tilt_rad"])
if arguments["operation"] == "stir":
    return at_least("in_container_turns", params["turns"]) and at_least("in_container_duration_s", params["duration_s"])
# pour/stir 的成功终态仍要求 holding
expected_holding = "empty" if phase == "place" else "holding"
```

本轮在 `examples/forge-adapters`、`PhyAgentOS`、`docs/forge` 的相关源码/配置中未发现非夕设备接入证据。当前实现新增 provider-neutral 反馈适配层：部署提供原始观测、来源 frame、calibration、容器/工具坐标系、抓持状态和 sampling profile，PAOS 将其规范化后再交给反馈计算器；现有 RoboTwin engine 未因此获得真实动作实现，也不能作为非夕 SDK、控制模式或抓持反馈已接通的依据。
部署能力不再只由 `prepare_cycle`/`execute_cycle` 方法存在性推断；Runtime 要求 preparation provider 和执行 client 对同一 operation 返回包含 `preparation`、`execution`、`feedback`、`return` 的显式 capability declaration。缺少任一声明时 cycle Tool 不发布，旧 held-only Tool 不作为替代。

## 3. Tool 边界与版本处理

对用户显示“倾倒”“搅拌”。完整取放使用 `object.pour_cycle`、`tool.stir_cycle`；旧 `object.pour` / `tool.stir` 保持已持物操作语义。
现有 `object.pour` / `tool.stir` 的“已持有 → 操作 → 仍持有”含义保持明确。不得让同一个 ToolSpec 在不同调用中隐式切换两种终态。
若实施核实旧接口未发布且没有绑定任务，可在一次明确版本变更中改为完整操作名；若已有调用方，采用新 Tool ID 并迁移 Skill/profile。
首版完整 cycle 只接受已知空夹爪入口；恢复时已持物的状态通过明确的后续操作处理，避免一个入口隐式猜测从何阶段开始。

```text
AgentTask / PlanGraph：pour-cycle(A) → pour-cycle(B) → stir-cycle → 任务验证
                           │
Gateway：一个 invocation，accepted/running → 一个终态结果
                           │
Adapter/worker：抓取 → 转运 → 对齐 → 操作 → 回正/退出 → 归位释放 → 撤离
```

Agent 选择对象、容器、归位目标、顺序和过程参数；Coordinator 保存选择与执行事实；Gateway 拥有公共 invocation 生命周期。
Adapter/worker 复用原抓取、路线、夹爪和放置实现，拥有阶段转换、资源占用、物理持有事实及测量。Verifier 根据终态事实评价原任务。
内部阶段直接调用执行组件，不递归调用公共 `forge_tool_start_action` 创建子 invocation，也不新增任务调度器或状态数据库。
多阶段有界操作仍是 Action；持续开放运行、需要独立长期会话的能力才另评估 Session。

## 4. 参数设计

以下公共字段已进入 ToolSpec/静态合同。设备/器材 profile 中的反馈容差由 provider 准备结果提供，不由 Agent 伪造。

| 参数 | 倾倒 cycle | 搅拌 cycle | 来源 |
| --- | --- | --- | --- |
| `entity_ref` | 源瓶 | 搅拌棒 | 当前对象绑定 |
| `destination_ref` | 接收容器 | 被搅拌容器 | 当前容器几何绑定 |
| `return_destination_ref` | 瓶子放置位置 | 棒架/归还位置 | 调用方明确选择或 Skill 的“回原位”规则解析 |
| `parameters.tilt_rad` / `hold_s` | 相对直立轴的目标倾角 / 有效连续保持秒数 | 不适用 | 用户或已选工艺参数 |
| `parameters.radius_m` / `depth_m` | 不适用 | 棒尖轨迹半径 / 沿容器内轴从杯口平面向下的深度 | 用户或已选工艺参数 |
| `parameters.turns` / `duration_s` | 不适用 | 圈数 / 有效搅拌阶段目标时长 | 一起定义节奏，匀速段平均频率为 turns/duration_s |
| `parameters.direction` | 不适用 | 以容器 +Z 轴指向杯外、从杯口上方观察定义 cw/ccw | 显式选择或已展示默认值 |

共同系统输入沿用当前 observation/scene/frame/calibration/capability 和有效 preparation/assignment 引用；由既有准备与参数投影提供，用户不手写这些引用。
`return_destination_ref` 与容器目标是两个独立位置。选择“回原位”时，准备阶段从原始有效绑定记录解析归位目标，放置前复核该位置仍可用。
工具到末端变换、瓶口/棒尖功能点、容器内部区域、倾倒轴/方向、瓶口偏置、夹爪设置、速度/力限制、容差和撤离位由设备/器材 profile 明确提供。
同一器材有多种工艺时由可见的 profile 选择；所选参数在执行记录中可查，Core 不硬编码一组非夕数字。
超时通过现有 Action timeout 传递，覆盖准备、取物、操作和归位的预算；不是 hold_s 或 duration_s 的别名。
圈数和时长若需要超出已配置速度/加速度能力，准备返回不可行；执行层不能静默改变圈数或拉长时长来宣布达标。

## 5. 准备、控制与完成判定

先复用只读准备组件检查整条操作链及归位路径；准备可以作为显式 Query 保留。将来若内置在 Action 中，也必须先完成所需检查再允许首次运动。
完整 cycle 不能直接使用“已持物才允许”的 prepare_held 契约。需要从空手状态准备完整路线，再在抓持关系确定、场景变化时复核相关后续路段。
一个 invocation 在全过程保有原执行 owner 与设备资源；每次阶段变化使用当前夹持关系、attached geometry 与相关观测，不凭旧 scene_revision 沿用失效路线。
持物时的必要观测由同一 worker 内部安全读取；现有外部 Query 在 operating 时可能拒绝，不能假定现成公共 Query 可在运动中调用。
若容器移动、归位点被占用或抓持变化超出已准备范围，则停止推进并报告实际状态，由上层决定新目标或清障。

`cycle_protocol.py` 从 process 阶段时间窗内的带时间戳样本计算倾倒有效保持时间：正确目标容器对准、倾角目标容差、抓持有效和反馈有效必须同时成立；仅当相邻样本间隔不超过 profile 的 `max_sample_gap_s` 才累计。
`maximum_tilt_rad >= tilt_rad` 与某段对齐时间分别达标不足以证明这一条件。例如直立对齐 3 秒再瞬间倾斜，不等于倾斜保持 3 秒；过度倾斜也不应被当成更好。
按单调时间和实际反馈采样计算，过程有效时间取满足全部联合条件的最长连续窗口；对准时间、最大倾角或多个不连续区间累计值不能替代。倾角、轴、位置容差在 profile 中定义，回正和撤离单独验证。

搅拌以 process 时间窗内实测棒尖在容器坐标系中的 x/y/depth 轨迹计算。profile 定义容器内半径和深度边界；有效采样同时满足目标半径/深度容差、容器边界、夹持有效和反馈有效。
按请求方向展开角度；圈数与有效时长必须在同一连续、单向有效轨迹段内达标。反向运动、采样中断、无效样本及出界会同时重置该连续段的圈数与时长，不能将往返摆动的绝对角度累计成圈，也不能将断点两侧的不同片段拼接达标。
不在容器内、只插棒静止、漏圈、离开有效区、反馈缺失和超时都不能用规划点数或指令时长替代实际完成。
棒尖位置来自实测末端状态与已确认抓持变换；若只能确认末端运动，无法确认工具仍被夹持，结果应明确这一证据缺口。

完整成功需要同时满足：正确对象被取得、过程目标完成、瓶体回正或棒尖退出、对象放到指定归位位置并稳定受支撑、释放确认、空夹爪撤离、最终状态可知。
普通动作后处理只执行已经准备且当前仍适用的路线。急停、碰撞或状态未知时，不执行无条件回正、拔棒、放置或松爪。
Action 取消使用已有 cancel；公共 stop_invocation 当前只接受 Session。设备急停属于设备安全路径，不能包装成“cancel 已接受就已急停”。
控制执行与安全监视必须独立于 Agent 的轮询频率；现有超时在读取时推进，不能单独充当设备侧实时超时保护。

## 6. 结果、失败与恢复

结果沿现有 status、outcome_known、world_change_started、possession_state、failure_code、evidence_refs 等字段表达。增加 `process_completed`、`return_completed`、`failed_phase`、`phase_facts`、`completed_phases` 及重算 measurements，不另造终态系统。
对该 cycle 定义 `operation_completed` 为整个取放周期完成，避免与旧 held-operation 的过程完成含义混用。
过程计量字段适用于本次请求；液体转移量和混匀质量标记为未测量，不能填零或用请求值回填测量值。

| 情况 | 结算与恢复 |
| --- | --- |
| 全流程及归位成功 | succeeded；process_completed=true、return_completed=true；最终 empty、对象已稳定放置 |
| 倾倒/搅拌完成，归位失败但状态可知 | failed；保留 process_completed=true、return_completed=false 和阶段事实；cycle 持物来源只允许 place 恢复，禁止旧 held-only pour/stir |
| 部分圈数/保持时间后失败 | failed 且报告有效已完成部分；不自动补足，需依据工艺目标决定后续 |
| 启动回执丢失或执行效果不可知 | unknown；按原 invocation 对账，无法确认时保留 unknown，不重发 cycle |
| 取消 | 请求后等待执行侧停止确认，报告已发生效果和持物状态；不能为了归位而继续整条循环 |
| 进程重启 | 已持久化阶段记录只说明过去；核对设备当前状态后才允许新的动作 |

归位失败后的默认恢复是“保留已完成过程 → 对账/观察 → 单独准备并执行归位”，通常复用 place 能力。
place 接受同一 owner 下经当前 cycle invocation/held invocation/scene revision 对齐的持物来源；cycle 来源与旧 acquire 来源保持区分，不伪造 acquire ID。
不伪造 acquire ID，不从调用方传入 start_phase 跳过检查。恢复会产生新的合法执行记录，原 cycle 失败历史不改写成成功。
任务 Verifier 可以验证原 cycle 的过程事实和后续恢复归位共同满足原目标；不能只看最后一次调用成功就忽略错瓶、错序或漏过程。
跨进程恢复若已有日志无法关联具体阶段，首版停留 unknown 并检查现场；先验证现有记录能力再决定是否扩展字段，不预加第二套持久化。

## 7. 实施状态与可验收结果

1. [完成] `object.pour_cycle`、`tool.stir_cycle` 与 `manipulation.prepare_cycle` 沿既有 PAOS Tool/Runtime 注册；准备 provider 和执行 client 均对同一 operation 显式声明 `cycle_capability(operation)` 的 preparation、execution、feedback、return 能力才发布对应 cycle 工具，旧 held-only 工具不冒充完整操作。
2. [完成] provider 无关 `CyclePhaseProtocol` 接收有序、带单调时间戳的阶段事件，并结算 acquire、transport、process、reorient_exit、stow、release、retreat 的可观察事实、失败阶段和未知状态。
3. [完成] 从合成倾倒/搅拌反馈轨迹验证联合连续窗口、方向性圈数、容器区域、采样中断和部分失败；新增反例保证采样断点前后的圈数与时长不能拼接。无称重结果仅表示 `motion_goal_reached`，液量与混匀质量明确未测量。
4. [完成] 已知过程完成但归位失败保留阶段事实并只允许 place；缺阶段、丢失反馈、启动回执丢失或无法确认的阶段结果保持 unknown，不重放 cycle。
5. [完成；no-motion] provider 读取显式 cycle capability declaration；fake engine control-loop 覆盖七阶段顺序、失败短路和取消后的 unknown。过程/归位事实不再因缺失 artifact ref 被抹除，但完整 succeeded 仍要求完整 evidence。
6. [完成；provider-neutral executor] provider 支持通过 `atomic_executor` 工厂提供 acquire、transport、process、reorient_exit、stow、release、retreat 七个内部原子操作；executor 只产生阶段事实，不创建嵌套 PAOS invocation。no-motion executor 验证顺序、失败短路和取消 unknown。
7. [完成；provider-neutral 反馈适配] 新增 `feedback_adapter`，将 provider 原始观测规范化为倾倒/搅拌计算器样本；校验单调时间、frame、calibration、容器/工具坐标系、抓持状态、过程字段和采样 profile。具体部署仍需提供实际采集、器材几何和 profile 数值；这不是非夕 SDK 接入。按当前范围不运行仿真或机械臂，也不据离线测试声称物理执行成功。

实现前不添加 hash、冻结契约、baseline 或额外门禁；复用已有版本、类型、invocation 和现有运动边界检查。
新增字段和阶段事实对应具体故障：归位失败重倒、过程假阳性、取消后继续运动。没有这些故障依据的机制不纳入本方案。
当前验证命令和范围见配套审核。离线 fixture 明确为 synthetic measurement records，不是仿真或机器人执行记录。

## 8. Provider 反馈协议

cycle engine 的终态 receipt 携带 `phase_events`、规范化后的 `feedback_samples` 与 `evaluation_profile`；若 provider 仍提供原始 `feedback_observations`，同时携带 `feedback_source_profile`，PAOS 在投影阶段调用 `feedback_adapter` 再计算。每个阶段事件含阶段名、`completed`/`failed`/`unknown` 状态、单调时钟 `started_at_s`/`completed_at_s` 和可观察 facts；成功阶段必须满足协议规定的事实前置条件。阶段严格有序，缺失阶段或无效时间线不能结算为成功。
反馈样本的 `timestamp_s` 使用同一单调时钟，倾倒样本含容器对准误差、倾角、抓持和反馈有效性；搅拌样本含容器坐标系下棒尖位置、抓持和反馈有效性。profile 提供采样最大间隔、单采样角度变化上界及与器材/容器相符的几何容差，以避免稀疏采样造成转向混叠。process 阶段 `completed` 表示该阶段的执行观察已结束；是否达到工艺运动目标另由计算出的 qualification 事实判断。任一采样间隔超限、样本无效或轨迹离开目标区域时，搅拌的连续圈数和连续时长都从新片段重新计算。
PAOS 重算过程目标，不信任 provider 的汇总圈数/倾倒时间或 `process_completed` 布尔值。部署只有在准备 provider 和执行 client 都对相同 operation 显式声明完整 `cycle_capability(operation)` 时才发现 cycle Tool；RoboTwin provider 只在 engine 提供完整声明、准备和执行入口时声明支持。协议不含运动命令、SDK 类型或设备身份。

本轮将上述发现收敛为 `cycle_capability(operation)` 声明：声明必须逐 operation 给出 preparation、execution、feedback 和 return 能力，`dry_run` 仅表示可进行无运动控制流验证，不等于已授权物理动作。provider 若没有声明或声明不完整则 fail closed。反馈适配层的结构性错误（时间回退、frame/calibration 漂移、坐标或抓持证据缺失）会使整条原始流 invalid 并保持 cycle unknown；provider 明确报告的 `feedback_valid=false` 只是一个不合格采样，不会被改成成功。阶段 control-loop 仍由具体 provider/engine 实现；当前 fake engine 只用于验证阶段事件顺序、失败短路和取消语义。

过程测量、阶段事实和完整证据分开结算。有效反馈可以保留 `process_completed`/`return_completed` 部分事实；`artifact_refs` 缺失时整体结果不能升级为完整 `succeeded`，但不得因此把已经观察到的过程事实改写为未完成。

`AtomicExecutor` 是 provider 内部的原子操作协议，不是新的 PAOS Tool。它按 cycle invocation 接收 owner、invocation 和 cancel 上下文，并为七个阶段返回带时间和 facts 的事件。engine 可以继续实现完整 `execute_cycle`，也可以通过 `atomic_executor` 工厂把原子方法交给 provider-neutral 编排器；两种路径都必须由 PAOS 重算反馈并结算最终状态。`NoMotionAtomicExecutor` 只用于控制流测试，不能产生物理成功证据。
