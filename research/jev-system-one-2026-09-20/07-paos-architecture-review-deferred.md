# PAOS 接入 Jev 的架构审核与暂缓实施决定

日期：2026-09-20。

状态：审核资料已保存，未实施。用户决定先完成自身方法验证，再回到本项工程加速工作。本记录不构成实施、部署或机器人执行授权。

## 1. 工作定位与用户决定

当前问题：PAOS 在执行已有 SOP 时，中间节点仍反复调用生成式 LLM，包含工具选择、已知参数传递和流程衔接，产生额外等待。

目标：确定步骤由程序完成；有限语义选择由 Jev 完成；新任务分解、开放式参数构造和复杂异常重规划由生成式 LLM 完成。真正消除中间 LLM 往返，而不是在每次 LLM 调用前再增加 Jev。

本项属于工程加速，不是当前方法验证的前置条件。当前不接入 Jev、不修改 Agent Loop、不开展 API 推理评测或机器人实验。待方法验证完成、用户重新启动此项工作后，再确认范围并实施。后续性能比较应明确是否启用本优化，避免将工程加速与方法效果混为一谈。

按用户要求，保存本审核不更新项目日志，不执行 Git 暂存、提交或推送。

## 2. 审核结论

方向合理，符合 PAOS 的 Agent 决策、Core 管理事实、Runtime 执行的责任划分。Agent 的决策责任不要求每次都由生成式 LLM 产生文本。

推荐在现有 Agent Loop 的节点决策入口提供规则、Jev、LLM 三种路径，汇合到既有 selection、DecisionTrace、wrapper、Gateway 和结算流程。不得引入第二套 SOP Runner、任务状态或执行入口。

| 提案 | 审核判断 | 约束 |
| --- | --- | --- |
| 确定工具和参数来源后直接执行 | 合理，需要节点路径改造 | 保留调用意图、绑定、校验和执行记录 |
| Jev 从合法候选中选择工具、实体或方法 | 合理 | 先过滤能力、语义、证据和权限；只返回候选标识 |
| Jev 选择已有计划模板 | 有条件合理 | 绑定当前证据，经过计划编译和 Coordinator 接纳 |
| 新增独立 SOP 调度器 | 不合理 | 复用 PlanningLoopAdapter 与节点执行器 |
| Jev 直接跳过节点或修改 DAG | 不合理 | 改变图必须走 continuation 或 recovery 等既有路径 |
| Jev 将推测写成 conditions 事实 | 不合理 | conditions 只读取可信的精确事实 |
| Jev 取代物理资格、执行结果或任务成功判定 | 不合理 | readiness、Tool result、Verifier 保持各自权威 |

## 3. 对此前方案的修正

### 3.1 复用 WorkflowPolicy，不新建通用 SOP 配置体系

已有 WorkflowPolicy 包含工具选择、参数绑定、适用条件和验证检查点等描述，但规则字段并不等于已具备通用执行解释器。应针对现有 Skill 的稳定步骤补齐明确的决策适配与参数构造，不立即建设新的 DSL、编译器和状态机。

消费者特有的参数变换由消费者拥有的参数构造器承担；Core 不硬编码生产者 Tool ID、对象名称、机器人型号或坐标。

### 3.2 区分节点内选择与计划变化

- 当前节点内选择兼容工具、实体及参数来源，可以进入现有 selection。
- 增加观察、改变依赖、替换步骤属于计划变化，需要合法的新计划提案。
- 可以用 Jev 选择已有模板、程序实例化计划，从而不调用生成式 LLM；但不能省略计划编译与接纳。
- 动态场景中仍需动作后观察、重新绑定、追加下一段，不能复用旧坐标或提前冻结未来实体。

### 3.3 快速路径必须保留原节点回合的责任

即使不调用 run_node_turn 中的生成式回路，也必须保留当前 task/revision/node 身份、实际 SkillUse、DecisionTrace、调用前持久化意图、终态结果结算及恢复行为。

已有执行事实优先于模型输出。Action/Session 不因 Jev 或 LLM 超时被重新提交；unknown 通过原 invocation 对账。未消费 receipt 可以通过既有入口继续消费，但仍需检查当前 revision 与执行记录。

### 3.4 Jev 调用放在 Agent 决策适配层

纯 planning 模块不调用网络、不写 SQLite、不调用 Gateway。若采用受管理的插件形式，私有依赖归插件环境；插件只交换 provider-neutral 规划投影和提案。

不把 Jev 全局替换为 chat/tool-calling provider：它适合有界选择，不具备开放式生成和多模态感知的等价能力。

## 4. 建议接入结构

```text
现有 PlanningLoopAdapter
  → 现有节点执行器
      → 规则可确定：程序选择与参数装配
      → 有限语义选择：Jev 返回候选 ID
      → 开放式规划或构造：LLM
  → 既有 selection + DecisionTrace
  → 既有 wrapper → Gateway → Runtime
  → 权威执行结果 → Coordinator 结算
```

节点所需输出和方法覆盖范围可以直接决定分流，不必每次额外调用 Jev 判断是否需要 LLM。独立问题可以批量询问；存在工具与参数依赖时，不能将各自独立预测任意组合。

## 5. 候选加速位置与优先级

| 场景 | 推荐方式 | 接入边界 | 优先级 |
| --- | --- | --- | --- |
| 唯一工具、固定字段映射、receipt 消费 | 程序 | 原 selection/执行链路 | 第一阶段 |
| 当前节点多个合法工具或方法 | Jev Choice | 先做确定性兼容过滤 | 第一阶段 |
| 用户指代与已有场景实体匹配 | Jev Choice | 只选已有 ID；度量与空间关系来自感知或程序 | 高 |
| 常见异常恢复分类 | 规则 + Jev | 事实来自 Runtime；复杂新计划交 LLM | 高 |
| 场景段后的继续、澄清或请求验证 | Jev + 已有方法 | 新段仍编译；成功由 Verifier 判定 | 后续重点 |
| 观察方式选择 | Jev | 只选已声明能力；移动相机仍走运动执行链路 | 中 |
| 合格方案中的语义偏好 | Jev | 不代替 readiness、资源管理和完整路线资格 | 中 |
| 操作员话语的有限意图路由 | Jev | 明确停止入口不等待语义模型 | 中 |
| Skill/Lesson 适用性筛选 | Jev 或现有规则 | 候选少时避免额外网络开销 | 后续 |

恢复决策的现有接口 select_recovery 只选择 stop/replay/replan，propose_replan 单独生成计划，适合作为接入位置。replay 是基于持久化事实重算，不是重复物理动作。

重复分拣等任务可在新观察后选择下一个目标，再实例化已有方法的下一段。遮挡关系变化、交换环、中转位置等新结构问题交给 LLM；不能提前假定所有后续步骤都由固定模板覆盖。

## 6. 机械臂低延迟边界

Jev 适合缩短语义反应时间，例如操作意图解释、方法选择、下一次观察选择和事后恢复分类。

伺服、轨迹跟踪、接触检测、滑落即时响应、力控、碰撞停止和急停留在本地 Runtime/控制器。Jev 不能提供硬实时期限，也不能代替感知检测或安全条件。

- 从已合格的方案中按用户偏好选择：可考虑 Jev。
- 控制器检测滑落后立即调整夹持：本地控制器职责。
- 根据已报告的滑落结果选择重抓或观察：可考虑 Jev。
- 明确停止按钮或控制事件：直接进入现有停止路径。

官方 70–500 ms 是特定条件下的测量，不是 PAOS 实测或延迟上界。Jev 为文本模型。confidence 不能视为单次正确性保证，不能照搬社区阈值。

## 7. 与当前日志证据的关系

v10.9.0 记录约 44,856-token 的节点上下文问题，并已实施精简。合成 fixture 的 49,717→1,456 字符说明上下文压缩有效，但不是当前真实任务 token 数或时延。本提案进一步减少生成式调用次数。

v10.10.2 相关回放中，构建约 7.906571 秒、资格检查约 9.873165 秒属于工具计算时间，不能算作 Jev 可直接消除的等待。候选全部被几何资格检查拒绝的问题也不会因接入 Jev 自动修复。

## 8. 方法验证完成后的恢复工作顺序

1. 重新读取届时的架构与代码，确认节点、SkillUse、continuation 和 Runtime 绑定实现是否变化；不要将本快照当作最新实现。
2. 选择一条常用 SOP，用当前记录统计每节点的生成式调用、决策等待和工具时间。
3. 先消除确定步骤的 LLM 往返，复用原执行和结算路径。
4. 再接入少量 Jev 有限选择，无法覆盖时进入原 LLM 路径。
5. 使用已保存记录进行不执行工具的决策比较，再按单独授权范围开展模拟验证。
6. 正常节点验证完成后，再扩展场景段 continuation 与重复任务。

验收关注：实际生成式调用减少量、决策等待 p50/p95、工具/实体/恢复选择错误率、LLM 回退比例，以及重启和超时后是否重复执行。不能仅以模型间答案一致率或 Jev 单次 API 速度作为成功依据。

当前不承诺具体加速倍数。只有真正省掉后续 LLM 调用，且节省时间超过新增 Jev 请求与回退成本，才形成端到端收益。

## 9. 审核依据

以下为本次阅读的设计与源码位置，后续以届时实现为准：

- [PAOS 开发者手册](../../docs/zh/03-developer-manual.md)：开发不变量、节点回合、执行事实、continuation 与 recovery。
- [集成开发指南](../../docs/user_development_guide/README.md)：能力接入与 Skill 工作流边界。
- [规划模块设计](../../docs/forge/PLANNING_MODULE_DESIGN.md)：纯 planning、WorkflowPolicy、conditions、图与执行的责任。
- [机械臂规划开发指南](../../docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md)：单一 orchestration adapter、插件边界、物理资格与分段执行。
- [Agent 输入选择设计](../../docs/forge/AGENT_TOOL_INPUT_SELECTION_DESIGN.md)：Bounded Input View、来源引用、消费者参数构造扩展。
- [Runtime 与 Skill 迁移方向](../../docs/forge/RUNTIME_BINDING_SKILL_USE_DESIGN.md)：方法与执行归属分离；文档明确部分内容未实现。
- [速度与控制权架构](../../docs/forge/REAL_SPEED_LIMITS_ARCHITECTURE.md)：provider/controller 权威。
- [Agent Loop](../../PhyAgentOS/agent/loop.py)：run_node_turn。
- [节点执行与编排](../../PhyAgentOS/agent/planning_loop.py)：AgentLoopNodeExecutor、PlanningLoopAdapter。
- [恢复决策](../../PhyAgentOS/agent/recovery_decisions.py)：select_recovery、propose_replan。
- [规划契约](../../PhyAgentOS/planning/contracts.py)：WorkflowPolicy。
- [v10.9.0 实现审查](../../docs/forge/IMPLEMENTATION_REVIEW_V10_9_0.md)：上下文优化与测量边界。
- [近期日志](../../changelog/2026-09_part12.md)：工具计算时间与尚在计划中的工作。
- [Jev 官方技术资料](01-official-technical-details.md)：输入输出、confidence、延迟及局限。
- [Jev 社区实现细节](02-implementation-deep-dive.md)：有限选择、批量问题与相关实现参考。

