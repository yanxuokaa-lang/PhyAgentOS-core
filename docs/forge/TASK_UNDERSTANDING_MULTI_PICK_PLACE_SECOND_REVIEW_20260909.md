# 多次抓放接入方案：第二轮架构审核

日期：2026-09-09。审核对象：[上一轮诊断及方案](TASK_UNDERSTANDING_MULTI_PICK_PLACE_INTEGRATION_REVIEW_20260909.md)。

用户条件：再次按 PAOS 原则审核，没有问题才进入实现；全部功能完成后按六个维度进行代码 review。

审核结果：**不通过实施准入条件**。上一轮已识别实现缺口，本轮进一步发现方案自身缺少关键执行语义，且“展开节点组”的表述可能改变 PAOS 的动态规划原则。本轮只保存审核结果，未进入执行代码修改，未运行仿真、硬件或模型推理。最终六维代码 review 尚未具备执行前提。

## 1. 规范依据

- [Planning Module Design](PLANNING_MODULE_DESIGN.md)：PlanNode 表达语义义务，同一节点可以选择不同 Tool sequence；固定七 Tool 流程只是一种 baseline policy。规则是固定合法性条件，而不是固定调用顺序。
- [Manipulation Developer Guide](MANIPULATION_DAG_DEVELOPER_GUIDE.md)：Coordinator 是 task/revision 唯一权威；Gateway 管执行和并发；Runtime/adapter 管物理事实；Verifier 管用户级成功。ResourceClaim 和 ArmAssignment 不是资源 lease。
- [集成开发指南第 1-3 节](../user_development_guide/README.md)：Action 为有界物理效果，Session 为显式有所有权的有状态能力；cancel accepted 不是 stopped；失去执行事实时返回 unknown。
- [开发手册第 12-13 节](../zh/03-developer-manual.md)：独立 provider 环境、通用 ToolSpec、正式 Runtime Bundle 和 Tool contexts；Agent 始终走 Tool API。
- 用户 Anti-OverDefense：不因草稿风险增加新哈希、schema 层或门禁；已有安全、授权和完整性约束保留。本次“未通过”是用户要求的方案审核结果，不是新增运行时 gate。

## 2. 新发现及修订要求

### R1 [Blocker] 不能把语义 DAG 强制改成逐 Tool 队列

上一轮 F1 建议将搬运展开为能力节点组，但没有明确这只是可选 Skill policy，也没有保留同一语义节点动态选择不同 Tool sequence 的实现路线。

证据：`PhyAgentOS/planning/contracts.py:50` 的 PlanNode 定义为 semantic obligation；规范文档 Purpose 明确允许每个 semantic node 选择不同 Tool sequence。实际 `AgentComposedDispatch` 按 capability 匹配可用 Tool，而 `AgentLoopNodeExecutor` 仅依据本轮调用记录的终态聚合，尚不能仅凭一个成功 Query 判定搬运义务已完成。

具体失败：为了让当前执行器工作，将所有任务强制展开为七 Tool 顺序，会限制 Agent 按场景选择观察、候选、恢复路径，也会把可演化的 WorkflowPolicy 固化到 core。

修订要求：保留语义 DAG；明确 WorkflowPolicy 如何提供当前义务允许的 Tool candidates，以及基于哪些实际效果和证据完成义务。展开节点组可作为显式选择的 baseline，不能成为所有 planner 的强制规则。若复用现有 ToolSpecPolicy 无法表达同一义务的动态调用资格，应先给出有界的协议调整及兼容方案，不能给任意 Tool 随意贴 relocate capability。

### R2 [Blocker] 抓取与放置间的持物占用和退出语义未定义

上一轮提出持续 Runtime，并说不一定需要 Session，这个判断本身成立，但不足以定义对外执行行为。

具体失败：acquire 已 succeeded，物体仍在夹爪中；Agent 暂停、place 长时间不来、另一个请求想使用同一机械臂、Runtime shutdown 或进程崩溃。此时仅有 Action 终态和保持关节目标，无法回答谁占用资源、哪个请求有权接续、何时允许下一次抓取。

证据：`PhyAgentOS/forge/capability_runtime/runtime.py:194` 统计的是同一 tool_id 的活动 invocation；acquire terminal 后不再计入。现有 acquire/place 输入虽有 assignment/acquire invocation 引用，但持物状态的抢占、暂停、失联和清理策略尚未在方案中落定。

修订要求：由执行侧定义持物事实与资源占用，至少明确 empty、acquiring、holding、placing、uncertain 各状态下允许的命令，以及 owner、接续引用、cancel/shutdown 行为。这些是 Runtime 物理状态，不是新的 AgentTask 状态库。需要对外暴露独立生命周期时再采用已有 Session 模型；仅内部持物也必须由 Runtime 保证安全接续。不得通过 PAOS 跨 Tool lease 解决，不得默认超时张开夹爪。

### R3 [Blocker] 场景更新与 acquire/place 接续绑定存在未决冲突

上一轮要求场景变化后更新版本，又沿用 Skill 中 place 继承 acquire 的 observation、scene、candidate、preparation 引用。两个要求不能简单合并成“place 一律使用最新 scene”。

具体失败：acquire 从 S0 执行到 S1。place 如果仍按 S0 校验当前几何，会使用旧障碍；如果把请求全替换成 S1，则会破坏原候选、准备与 acquire invocation 的证据关联。后续 observation 如果只是原 scene 的新 capture，也不能自动代表之前准备仍有效。

证据：`pick_place_workflow/SKILL.md` 要求继承 acquire 绑定；`robotwin_backend.py:373` 只在 reset 处产生新 scene identity；`NodeContextProvider.build()` 对不同 scene_revision 的前驱直接拒绝。

修订要求：区分原始动作/候选依据和当前执行现场；由 Runtime 对继承的 acquire 事实以及 place 当前准入分别验证。设计应逐字段说明哪些引用保持不变、哪些由 provider 重新解析/测量、何时需要重新准备和新 PlanRevision。不能删除 scene 校验，也不能把原 scene 名重命名后宣称新证据有效。

### R4 [Blocker] 失败和取消的物理效果在当前投影中丢失

证据：

- `PhyAgentOS/agent/planning_loop.py:225-227` 对所有非 succeeded 结果强制设置 world_changed=False，并清空 new_scene_revisions。
- `PhyAgentOS/planning/settlement.py:17-18` 把所有 cancelled 结果映射为 cancelled_before_start。
- `CapabilityRuntime._advance()` 将 cancel_requested 直接变为 cancelled；当前路径没有底层停止事实确认。

具体失败：机器人已抓起或掉落物体后失败/取消，下游可能得到“没有改变世界”或“启动前取消”，从而复用旧证据或把后续重试当成无副作用。

修订要求：动作状态、是否开始产生效果、效果是否已知、是否确认停止应保持各自含义。保留失败后的已知变化和证据；unknown 不能归为未执行；只有明确 before-start 证据才能产生 cancelled_before_start。接口字段优先复用既有 capability_outcome_summary 和执行记录，必要的类型调整须说明兼容投影。

这是接入必须处理的源码缺陷；本轮按“先审核通过”的条件记录，未修代码。

### R5 [Major] 可信上下文更新不能简单累计历史集合

证据：`PhyAgentOS/agent/planning_context.py:33-52` 累积所有 execution_records 的 evidence 和 resources_in_use，以最后遇到的 scene 字符串作为当前场景。

具体失败：旧记录声明机械臂占用，新记录声明资源已空闲，但集合 union 无法移除旧占用；旧 evidence 也可能继续满足新节点的 required_evidence。记录枚举顺序不应成为现场权威，尤其存在失败、恢复和跨 revision 记录时。

修订要求：明确当前 snapshot 与历史事件的投影规则，按已持久化可信终态/事件更新当前资源及证据适用范围。物理占用权威仍在 Runtime，planning 只消费投影；完整历史留在现有记录中，当前可用集合不是历史全集。

### R6 [Major] 全功能验收需要从自动通过测试改为具体任务证据

上一轮 P3/P4 列出“两物体连续仿真”和“N 物体恢复”，但缺少明确区分假执行、benchmark 配置事实、传感器感知事实、语言任务绑定以及最终 Verifier 的验收矩阵。

修订要求：每条验收注明入口、输入来源、预期物理事实、任务状态和证据文件。最少包含自然语言触发同一 AgentTask 的两次搬运；第二次使用第一次之后现场；重复颜色的身份绑定；抓取后掉落；取消后确认停止；进程重启后对账；后续操作破坏前目标后的恢复。只运行独立 probe 或 scripted Tool 顺序不能宣称 Agent 全链路通过。

此外，验证模式错误应依据真实类型修复：`VerificationMode` 为 off/audit/enforce/recovery，experience 未提交改动使用 off/report/enforce。这是两个模式域被错误等同，不能把 recovery 简单映射成 enforce 后丢失语义。

## 3. 六维设计检查结果

以下是设计检查，不是用户要求的“全部实现后代码 review”。

| 维度 | 结论 | 依据 |
| --- | --- | --- |
| 架构集成 | 部分通过 | 唯一 task/Gateway 权威正确；R1 动态语义和 R2 执行侧持物归属须细化 |
| 失败路径 | 不通过 | R4 丢失效果事实、取消误归类；重试前状态核对未闭合 |
| 权限与安全 | 不通过 | R2 持物期间资源冲突及停止确认；R3 当前现场准入未定义 |
| 配置与复现 | 部分通过 | 独立环境和 profile 方向正确；R6 验收输入及证据矩阵需明确 |
| 可维护性 | 部分通过 | 复用现有记录；需避免固定 core 流程及 R5 历史/当前状态混用 |
| 可观察性 | 不通过 | 失败后世界变化和 before-start/after-start 取消不能被正确追踪 |

## 4. 进入实现前的具体交付

1. 修订动态义务到 Tool selection/settlement 的规则，明确 baseline 与 agent_composed 兼容。
2. 确定 Runtime 持物状态转换、资源占用、owner 接续和安全退出；列出各状态可调用的操作。
3. 逐字段定义 acquire/place 的原始依据与当前现场的继承/更新规则，并与 scene/revision 恢复一致。
4. 给出成功、失败、取消、失联四类执行事实到 ToolResultEnvelope/NodeSettlement 的映射。
5. 明确 current context 的事件投影规则，以及 P0-P4 每项验收的入口、输入和可检查证据。

这些交付均属于现有方案的修订，不要求用户新增一套架构，也不引入新的安全门禁。全部设计阻断关闭后，才能按用户条件开始接入实现，完成既定范围并进行六维代码 review。

## 5. 本轮完成情况

完成了规范复核、源码证据定位和本审核文档。原诊断文档保持历史原样。未修改生产代码，未执行新的测试、仿真或硬件操作；未把实现待办标记为完成。
