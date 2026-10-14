# JEV Agent Loop 重构：七维修订与编码模型实施工单

日期：2026-10-14。源码核对：`c0745e58`，当前分支 `feature/planning-loop`。
状态：方案已修订；P0–P4 运行实现尚未交付。本文件面向 GPT-5.6-sol 等**接手编写代码的模型**，
不要求更换 PAOS 运行期 LLM，也不提供对任何编码模型完成质量的实测排名。

## 1. 接手入口与结论

实施以本文件的批次、接口和验收为准；职责与原始证据分别见
[总体方案](JEV_AGENT_LOOP_REFACTOR_DIAGNOSIS_20261014.md)和
[最近十次运行诊断](JEV_RECENT_RUNS_DIAGNOSIS_20261014.md)。
本文件细化这两份设计，不改变 Runtime、Coordinator、Verifier 的权威边界。

推荐分批交给编码模型：P0 → P1a → P1b → P2 → P3a → P3b → P4。
P0 可直接实施；P1/P2 按下述具体切片推进；P3a 交付关闭/影子能力，P3b 依据专项测量决定是否启用。
缺少 JEV 服务或质量数据不阻止 P0–P2 和 P3a 的固定返回测试，但不能将 P3b 标记为完成。

始终保持：程序处理精确输入、唯一确定选择和状态推进；JEV 选择有界语义选项；
运行期 LLM 负责新方法、新图、开放约束和复杂异常。编码模型不能为完成工单伪造这些运行结果。

### 1.1 七维审核及本次处置

审核标准来自 [历史七维记录](../../changelog/2026-10_part6.md)：
架构所有权、正确性、错误可观测、恢复幂等、机器人安全、扩展兼容、AgentLoop 收敛。

| 维度 | 设计判断与具体处置 | 实现验收位置 |
| --- | --- | --- |
| 架构所有权 | 一个 AgentLoop；方法内容在 Skill/planner 扩展，通用消费在 Core；JEV 无 task/执行所有权 | P2 的可选扩展接口、P3 原 selection 消费 |
| 正确性 | 补齐 consumer 映射、完整选项、可物化当前片段；候选唯一不等于参数完整 | P1a/P2、样例 S1–S6 |
| 错误可观测 | 区分服务失败、语义弃权、准入拒绝和业务不可用；明确关联与分母 | 第 5 节事件和质量表 |
| 恢复幂等 | 先对账，blocked 先于 pending selection 消费；升级不重置认知预算 | P0/P3、S7–S9 |
| 机器人安全 | 无模型补造身份/持有状态；沿用原 readiness、admission、停止和 Verifier | S4/S6/S8；Action/Session 替代另验收 |
| 扩展兼容 | 复用 projection 和 compiler；旧插件无新可选能力时走原路径；旧任务不热改契约 | P1a/P2/P3 off 回归 |
| AgentLoop 收敛 | 同一认知周期一次 JEV，LLM 升级后不回跳；有证据才推进阶段 | 第 4 节、S5/S9/S10 |

面向跨模型交接，本次审核的四项 Major 处置如下；这是方案修订，不是实现验收：

| Finding | 原缺口 | 修订位置 |
| --- | --- | --- |
| H1 Major | P1/P2 没有明确可复用接口、投影实例和片段到节点的消费链 | 第 2、3 节 |
| H2 Major | 共享 deadline 与“一次升级”的范围未落实到当前嵌套回合 | 第 4 节 |
| H3 Major | active 的质量依据、统计分母和事件关联仍不足以执行验收 | 第 5 节；缺数据保持 off/shadow |
| H4 Major | 私有运行库、本地 probe 输出和未跟踪操作说明不能随 clone 交接 | 第 6、8 节的可移交样例与执行指令 |
| H5 Minor | plain pytest 会自动加载 ROS 插件并缺少 lark | 第 7 节已核验的收集命令 |

## 2. 源码复用与禁止重复建设的边界

下表路径相对于仓库；接口是否存在以当前源码为准，新名字在下文明确标为“拟新增”。

| 工作 | 复用入口 | 首批修改边界 |
| --- | --- | --- |
| 节点选择后交接 | `agent/loop.py`：`_run_agent_loop`、`run_node_turn` | 独立 selection 成功交接；不将 selection 加入物理执行预算集合 |
| pending/execution 对账 | `agent/planning_loop.py`：`AgentLoopNodeExecutor.__call__`、`_resume_node` | 保留 blocked、原 invocation、晚到结果和结算顺序 |
| 确定性 Query | `agent/loop.py:persist_deterministic_query_selection`；`agent/planning_dispatch.py:prepare_frozen_query_selection` | 补投影支持，不推广为自动 Action/Session |
| 声明式参数装配 | `planning/contracts.py:ArgumentProjectionPlan` / `ArgumentProjectionSourcePlan`；`planning/projection.py:execute_argument_projection` | 优先使用已有 source_slots/source_field_map；不新写第二个字段装配器 |
| 授权来源解析 | `agent/planning_loop.py:resolve_node_argument_sources` 与原 Coordinator selection resolver | 保持 bounded view、source_scope、scene_relation；不扫描整库猜来源 |
| 精确 consumer 定义 | `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/grounding.py:BIND_TOOL_SPEC` | `scene.bind` 的映射在该 consumer planning 声明，不放到 Core 字段分支 |
| 节点提示 | `agent/context.py`、`agent/prompt_context.py` | 分离通用/节点工作集并测组成；保留适用 Skill 规则与持久化事实 |
| 当前段编译 | `agent/plan_proposal.py:compile_task_plan` | 接收已物化 `list[dict]`；不承担选择方法、实体或依赖 |
| 正常续段 | `agent/tools/forge_task.py:ForgeTaskContinuePlanTool` | 复用 `forge_task_continue_plan` 及 `begin_continuation_revision`，不冒充 replan |
| 方法扩展 | `agent/planner_plugin.py` 的可选能力模式；Skill 的 `long_horizon.py` | 新增普通可选方法能力，复用现有插件注入；不改所有旧插件必需接口 |
| 决策服务 | 拟新增 `providers/decision.py`、`providers/jev.py`、`agent/decisions.py` | typed choice 与策略分层；不把 JEV 伪装为生成 tool calls 的 chat provider |

除 examples 行外，上述代码路径以 `PhyAgentOS/` 为前缀。
已有 `DecisionTrace`、selection、Tool record 和事务继续使用；不为 JEV 新增哈希、状态库、任务循环或通用执行引擎。

## 3. 分批实施工单

### P0：成功选择后立即交接

1. 在 node scope 内，`forge_plan_select` 成功且对应当前节点的 selection 已持久化后，结束认知回合。
2. 复用当前 deferred tool-result 行为，补齐同一响应中尚未执行的后续调用；不要执行它们。
3. 由 `_resume_node` 经原 registry/wrapper 消费。保留工具使用、SkillUse、进度和经验归因。
4. selection 本身仍受认知 deadline 限制。现有 `_NODE_TURN_EXECUTION_TOOLS` 还控制执行预算，
   不把 selection 直接加入这个集合。失败/未落盘的 selection 仍进入既有纠正或拒绝流程。

验收：selection 成功后额外 LLM=0；持久化选择和实际消费各一次；失败选择可纠正；
blocked 不消费 pending selection；已有 execution 能对账；同响应后续调用只有 deferred 结果。
测试入口：`tests/test_agent_foundation.py`、`tests/test_planning_loop.py`、`tests/test_forge_tool_api.py`。

### P1a：先完成一个真实 consumer 的输入投影

首个切片是 `scene.bind` 缺失的 `observation_ref / scene_revision / calibration_ref`。
当前 `grounding.py` 声明它们必填，但没有为该 consumer 声明来源映射。
推荐给 `BIND_TOOL_SPEC.planning` 添加如下投影；这是**待实现声明示例**，不是当前已发布契约：

```yaml
argument_projection: observed_identity_for_binding_v1
argument_projection_plan:
  projection_id: observed_identity_for_binding_v1
  source_slots:
    understanding:
      tool_id: scene.understand
      source_scope: authorized
      scene_relation: current
      source_field_map:
        observation_ref: [observation_ref]
        scene_revision: [scene_revision]
        calibration_ref: [calibration_ref]
  top_level_fields: [entity_refs]
```

同一条已授权、当前场景、业务结果可用的 understanding record 提供三个精确值；
现有 resolver 可读取该 record 的 response 或原 arguments，不要求 producer 添加 consumer 专用对象。
`entity_refs` 是节点已有固定选择或 JEV/LLM 的语义选择，不能将所有可见实体默认视为目标。
在投影前，保留现有当前理解缺失/歧义检查；完整 schema 校验和准入仍在原入口进行。

确定性扩展按顺序做：当前唯一 Query → 完整固定语义输入 → 每个声明 slot 恰有一个合法来源 →
原投影/校验/selection 持久化。零来源保留缺口，多来源或语义未确定退出快路径；不按最新时间或列表第一项猜测。
来源资格的判断复用原 resolver；host 不能以字段同名、Tool ready 或 record 外层 succeeded 代替业务有效性。

先验证单 slot；多 slot 可复用现有类型，但每个 slot 都必须唯一且组合合法才能零模型。
trusted argument builder 保持原路径，未专项验证前不一并纳入快路径。
旧任务继续使用已绑定的 ToolSpec；新映射只影响正常新绑定，不能热改历史 selection/契约。

验收：S1–S4；唯一完整 Query 的 JEV=0、LLM=0；七个历史缺字段事件对应形状都正确装配；
source_scope/predecessor/current-scene 反例仍被拒绝。
补跑 `tests/test_planning_dispatch.py`、`tests/test_multi_source_projection.py`、
`tests/test_planning_selection.py`、`tests/test_planning_context.py` 及 Skill grounding tests。

### P1b：缩小工作集，保持必要事实

分别记录 bootstrap/system、Skill、节点事实、工具 schema、历史各部分的 token 估算及总量。
从重复注入处消重；沿用一份权威 Skill 指令，不用自由摘要替换必要规则。
节点仅带当前义务、合法候选与来源、相关成功/失败/unknown、原目标和完成效果。
续段额外保留未完成目标、已完成效果和证据缺口；复杂规划才使用更宽的上下文。

验收以同一 fixture 的原/新请求比较：输入减少，所列必要事实均存在；S6 的旧实体与 S10 的历史失败不能被裁掉。
既有失败事实进入 prompt 不等于保证模型理解正确，两项分别测量。

### P2：让常规方法选项直接携带可编译节点

`compile_task_plan(task, nodes, ...)` 当前要求完整节点列表；它不是片段 ID 解释器。
本批选择以下具体实现方式，不引入模板语言或另一套 scheduler：

- 在 `agent/planner_plugin.py` 增加拟议可选能力 `MethodFragmentPlugin`，采用现有 optional recovery capability 的模式。
  拟议方法 `propose_method_options(*, request: PlanningRequest)` 返回普通内存选项序列；
  旧 `PlannerPlugin` 的 compose/replan 必需接口不变，旧插件不具备该能力时使用原 LLM continuation。
- 每个选项携带 `method_id`、描述/适用义务、已物化 `nodes`、精确 `evidence_refs`、`reason`。
  这些是宿主可消费字段，不是新的持久化合同；复用 `PlanNode` 验证节点。
- Skill/planner 扩展根据已有可信 request 生成方法内容；Core 只做通用选择、当前身份复核、原 compiler/continuation 消费。
  沿用现有显式插件注入/注册，不让 Core import 某个 RGB Skill，也不新增通用插件发现平台。
- 在 `AgentLoop.run_segment_continuation_turn` 发起原 LLM 回合之前调用这个可选能力；
  以当前可信事实构建 `PlanningRequest`，选项被接受后直接交原续段 wrapper，缺能力/无适用项才走原 LLM。
- 仅在当前事实足以物化该段时生成选项。空选项转原 LLM 或明确缺口；多选项由 P3 的 JEV 选择。
  唯一选项也须确认适用义务、事实完整及确定性前提，不仅检查列表长度。

首个只读方法选项的分段例子：

| 当前事实 | 扩展物化的当前段 | 该段完成后的处理 |
| --- | --- | --- |
| 已有当前 observation，缺 understanding/capabilities | 只生成缺少的理解/能力 Query 节点，输入来自该 observation 的明确声明映射 | 结算并重新读取结果，再考虑绑定选项 |
| 已有可用 understanding，目标实体集合已确定且无歧义 | 生成当前 `scene.bind` 节点；P1a 装配身份字段 | 绑定实际返回后决定是否满足当前义务 |
| understanding 没有确认必需实体 | 不生成该目标的绑定或动作节点 | 保留 gap，匹配已有调查方法或升级/澄清 |

理解/能力 consumer 若尚无声明映射，先依 P1a 的同一通用机制补齐实际需要的字段再纳入该方法。
不能为了合并段而提前填未来 observation/entity/evidence 引用。每个当前段以真实 refs 编译，
后续动态身份留给下一 continuation。一个 segment 内保留需要的 predecessor 关系；
跨段来源用现有授权 evidence，不能引用旧段节点作新段 dependency。

消费链：方法扩展生成完整选项 → 程序/JEV 选 ID → 宿主复核当前 task/revision/scene →
经原 registry 调用 `forge_task_continue_plan(nodes, evidence_refs, reason)` → 原 compiler/Coordinator → 原节点循环。
不要在这一链里再调用 LLM 写图，也不要绕过 wrapper 直接写 revision。

验收：固定方法选择后 LLM 写图=0；编译不接受未来绑定；部分完成不误建下一段；Query unavailable 不清除 gap；
正常续段不消耗 replan 预算。使用 `tests/test_planning_task_integration.py`、
`tests/test_plan_proposal_bindings.py`、`tests/test_planning_context.py` 和 Skill long-horizon tests。

### P3a / P3b：服务接入与 active 启用分开交付

P3a 新增可选 typed DecisionProvider/JEV adapter 和 Agent 策略。首版仅使用已测的 choice 题型；
传候选 ID/描述和最小必要事实，返回 selected/escalate/unavailable；服务不写 task、selection 或执行结果。
复用配置风格和 HTTP 客户端；现有 LLM registry 若要求 chat 接口，不能为了复用把 decision 塞进去。
配置需覆盖各决策点 mode=off/shadow/active、endpoint/model、timeout_cap_s、fallback_reserve_s、
经专项测量形成的 acceptance policy。值与凭据在配置/操作员环境，不硬编码到 loop 或 Skill。

首个 JEV 切片：已物化 Query 节点中，从多个**完整合法输入组合**选择一个。
多个来源若事实意义不可区分或相互矛盾，直接升级，不能以 JEV 强选消除数据歧义。
片段选择在 P2 消费链通过后加入；Action/Session 的语义选择不随只读点开关一起启用。

P3a 以固定 provider/Fake Gateway 完成接受、弃权、超时、取消、过期结果和关闭回归。
shadow 不参与 task 写入，超时/失败不阻塞主回合；其后台任务必须受现有生命周期取消和清理。
P3b 才进行第 5 节专项测量和配置 active；没有测量结果时保持 off/shadow，并把 P3b 列为未完成。

### P4：已有恢复方法匹配，新策略交 LLM

以“当前未完成义务 + 结构化失败 + 证据缺口 + 可用调查能力”构造恢复方法选项，
不直接把 stop/replay/replan 三标签当成已验证简单分类。
先覆盖已定义的只读调查。unknown/持有对账仍归原执行 owner；新根因、新方法、新图调用原 LLM。
JEV unavailable/escalate 先升级；原 LLM 失败仍遵守该调用点既有语义：
节点 provider wait 与 recovery 的异常 stop 分别记录，不由 adapter 新增 task 状态。

验收：S5/S6/S8–S10，恢复方法实际减少对应 gap 才能推进；关掉决策点仍能对账已接受的选择/执行。
若原能力无法取得缺失事实，报告缺口，不承诺“换模型即可完成”。

## 4. 共享 deadline、升级范围与生命周期

现状：`run_node_turn` 传入完整 `turn_timeout_s`，`_run_agent_loop` 内部再执行
`monotonic() + decision_timeout_s`。`AgentLoopNodeExecutor.__call__` 还可能再次调用节点回合。
若在前面加 JEV 却保留这些计时入口，会得到 JEV 等待加一份新的完整 LLM 预算。

实施约定：先按原路径对账；确实需要新认知时，由 node executor 建立本次认知周期的绝对 deadline。
显式传入 JEV 策略、`run_node_turn`、`_run_agent_loop`；旧调用者省略参数时保持旧默认行为。
同一周期内的上下文构造、JEV、LLM、选择纠正共享剩余时间，Tool 执行仍使用原执行预算。

```text
remaining = decision_deadline - monotonic()
jev_wait = min(timeout_cap_s, max(0, remaining - fallback_reserve_s))
jev_wait <= 0  -> 不尝试 JEV，进入尚有预算的原 LLM 路径
JEV 失败/弃权 -> LLM 使用相同 deadline，不重置为 turn_timeout_s
剩余预算耗尽 -> 原 turn_timeout / provider-failure 生命周期
```

一次尝试范围：同一节点认知周期内 JEV 至多一次；进入 LLM 后的纠正/timeout 重入不再调用 JEV。
新节点或确有新的已结算事实需要新决策时才开启新周期；不把“读了状态”当作新事实。
用宿主调用局部状态表达 attempted/escalated，不新建持久化请求账本。
重启先恢复原 selection/execution；只有没有可消费结果且原生命周期允许时，才启动新认知周期。
取消沿原控制路径传播，不能吞掉 CancelledError 后再启动 LLM；返回旧 revision/scene 的答案拒绝消费。

验收用假时钟/可控异步 provider：JEV+LLM 不能超过原周期预算；升级后重复节点纠正不再请求 JEV；
取消不生成 selection；预算耗尽前已持久化选择仍按原恢复机制对账，不转成动作重放。
续段/恢复接入时分别在 `run_segment_continuation_turn` / `AgentRecoveryDecisions.select_recovery` 的宿主
决策入口建立同样的共享预算，并单测各自取消与失败路径；不能只改节点计时却宣称三条路径都已覆盖。
这些是处理已发现的嵌套计时问题，不新增全局 deadline 系统或 gate。

## 5. active 所需证据、观测与接受标准

固定 provider 只能验证控制流；JEV 51/60 入口结果不能验证节点选择。
先用下列确定验收，再以独立专项数据选择语义阈值，阈值不得由编码模型凭经验填写。

| 检查 | 接受条件 | 不满足时 |
| --- | --- | --- |
| 控制流与反例 | 第 6 节所有普通回归通过；accepted=1 JEV/0 LLM；无额外消费/重放 | 修实现，保持 off |
| 候选生成 | 标注可替代样例中正确完整选项存在；无适用项保留升级出口，单独报告遗漏 | 修方法/输入，不降低模型接受条件 |
| 数据隔离 | 同工作流近重复样本不跨校准与留出集；至少覆盖多实体、多方法、无适用项、跨场景、非法组合和需复杂规划 | 补样例，不用十次近重复任务声称泛化 |
| 首个只读点语义正确性 | 留出验收中已接受错误数为 0，标注必须升级的样例全部升级；报告实际分母及置信区间 | 该点留在 shadow；零观测错误不声称总体风险为零 |
| 实际替代 | 至少存在真实正确接受样例，且接受后实际免去 LLM，不是全量弃权取得零错误 | 不宣布替代完成 |
| 时延收益 | 同输入/同版本配对，含失败与升级等待的决策总耗时均值下降且 p95 不恶化；另报工具/用户等待 | 优化工作集或超时策略；保持 shadow |
| 质量范围 | 只读点专项通过只启用该点；Action/Session、恢复分别验收 | 不扩大适用范围 |

上述是首个只读点的上线判定标准，不是新增统一 gate；用已有配置和普通验收报告执行。
样本量与各类分布在采集前记录；报告不足以判断时继续 shadow，不用少量无错误样本推导泛化保证。
数据集、标注、模型实际版本、接受策略和完整失败请求统计随评测产物保存；当前不承诺提速倍数。

在原 Agent 日志记录每个决策的 task/revision/node（续段用已有段关联）、decision_point、mode、
provider/实际 model version、candidate_count、selected candidate ID、outcome、reason、elapsed_ms、remaining_ms。
outcome 至少区分 selected、abstained、unavailable、stale、admission_rejected。
选定后以原 selection/decision_trace_ref 关联 execution record；服务失败且未产生 selection 的日志不伪造 trace。
不新增持久化 DecisionTrace schema 来存服务遥测，不记录凭据或整个来源载荷。

分别统计：候选覆盖、raw 选择正确率、策略接受率、错误接受数/接受数、必须升级召回、
接受后实际免去 LLM 的比例；超时和无效答案留在总请求分母。
record succeeded 与业务 payload unavailable 分开；操作员等待/停止不算模型推理时间或自主失败。

## 6. 可移交样例：不依赖私有运行库才能开始

原十次日志位于本机 workspace；probe 结果在未跟踪的 `out/`，本地 `AGENTS.md` 也未被 Git 跟踪。
干净 clone 可读取本文件和已跟踪源码/测试，无需复制 live SQLite、完整会话或凭据。
以下区分“真实证据摘录”和“根据故障形状构造的合成 fixture”。合成数据仅用于控制流测试。

### 6.1 已复核的真实事件摘录

七条事件均为 `planning_selection_rejected`，code=`tool_input_schema_invalid`，
missing_fields=`["calibration_ref", "observation_ref", "scene_revision"]`：

| event_id | task_id |
| --- | --- |
| 12261 | task_d6c7a8189f824060 |
| 12665 | task_dfff5bc448ef495b |
| 12810 | task_485c371aea724fcf |
| 12952 | task_4807de31b86a4a91 |
| 13108 | task_feedfde84cec4022 |
| 13235 | task_2d374f88b79d4ae9 |
| 13435 | task_8fed40f6212c4b19 |

摘录保留来源定位，但不伪装成七份完整可重放的 task 快照。实施者据此把同一错误形状参数化为回归，
再在具备原库的环境核对历史回放；没有原库时只报告合成 fixture 结果。

### 6.2 可直接转成单元测试的投影样例

下面所有 fixture 引用都是合成测试值，不是 live Tool 参数：

```json
{
  "record_id": "fixture_understanding_current",
  "arguments": {
    "observation_ref": "observation://fixture/current",
    "scene_revision": "fixture_scene_current",
    "calibration_ref": "calibration://fixture/current"
  },
  "response": {
    "data": {
      "status": "available",
      "entities": [{"entity_ref": "entity://fixture_target"}]
    }
  },
  "literals": {"entity_refs": ["entity://fixture_target"]},
  "source_record_ids": {"understanding": "fixture_understanding_current"},
  "expected_arguments": {
    "observation_ref": "observation://fixture/current",
    "scene_revision": "fixture_scene_current",
    "calibration_ref": "calibration://fixture/current",
    "entity_refs": ["entity://fixture_target"]
  }
}
```

将 P1a 的 plan 交给现有 `execute_argument_projection`，records 映射值为 `(arguments, response)`，
输出应严格等于 expected_arguments。该纯函数验证不替代授权、当前场景和实体资格检查；
后者用现有 Coordinator/NodeContext fixture 通过真实 selection 消费链验证。

| Case | fixture 变化/已有回归参照 | 必须断言 |
| --- | --- | --- |
| S1 唯一完整来源 | 上面的当前来源；节点实体已固定 | 三个字段来自同条记录；确定性路径 JEV=0/LLM=0 |
| S2 多来源 | 增加第二条合法、但语义来源尚未确定的 record | 不默认取第一条；需要明确语义选择或升级 |
| S3 缺字段 | 删除 record 两侧的 calibration_ref | 无完整 selection，不请求模型编造值 |
| S4 跨场景同名实体 | 旧场景目标 e1；新场景 e1 是其他对象 | 不继承旧身份；当前缺失/歧义按原 admission 拒绝 |
| S5 业务不可用 | 外层 record succeeded，payload status=unavailable | 不清除缺口，不推进依赖事实的节点 |
| S6 当前身份未确认 | 理解没有必需实体，但有其他实体 | 可调查/升级；不能将其他实体绑定成功等同于目标已对账 |
| S7 selection 交接 | 成功落盘后，同响应再请求执行；另测落盘失败 | 后续调用 deferred；成功只消费一次；失败不假交接 |
| S8 已有执行/blocked | unknown/completed Action；以及 blocked 下 pending selection | 对账原 invocation；无重放；blocked 不新执行 |
| S9 JEV 升级/取消/过期 | timeout、invalid response、取消、返回期间 revision 改变、LLM 也失败 | 同周期 JEV≤1；共享 deadline；旧答案不消费；按原失败语义收敛 |
| S10 方法无进展/历史失败 | 相同证据方法重入；跨 revision 已有 failed record | 不无限重跑；失败终态保持可见；原义务仍未完成 |

S4/S6/S8/S10 的真实故障依据见十次诊断；不把合成 fixture 数当成 JEV 质量测试样本数。
实现时把以上样例写入对应 tests，补实际 Coordinator、registry、selection 数断言，不能只测 adapter 返回值。

## 7. 验证命令及当前验证结果

本次复审在当前环境复现 plain pytest 自动加载 ROS `launch_testing`，报
`ModuleNotFoundError: No module named 'lark'`。显式插件命令成功收集 **330 项**；尚未执行这些用例。
无需为普通 Core 测试安装 ROS 依赖。接手者先收集，再在实现后运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest --collect-only -q -p pytest_asyncio.plugin -p no:cacheprovider tests/test_agent_foundation.py tests/test_planning_loop.py tests/test_forge_tool_api.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p pytest_asyncio.plugin tests/test_agent_foundation.py tests/test_planning_loop.py tests/test_forge_tool_api.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p pytest_asyncio.plugin tests/test_planning_dispatch.py tests/test_multi_source_projection.py tests/test_planning_selection.py tests/test_planning_context.py tests/test_planning_task_integration.py tests/test_plan_proposal_bindings.py
git diff --check
```

新增 decision/provider/fragment 测试随对应批次加入；对修改文件运行仓库 Ruff。
Skill 独立包的测试使用其文档规定环境，不能因 Core pytest 通过就宣称 Skill 发布或 Runtime 已验证。
无 `.venv` 时按仓库开发文档准备环境；不得触发 onboarding、Runtime 启停或 live task 来代替 fixture。

## 8. 可直接交给另一个编码模型的指令

> 在当前工作分支落地本文件指定的一批，默认从 P0 开始；不是一次性完成 P0–P4，也不是更换 PAOS 的运行期 LLM。
> 先读取仓库操作规范、两份关联诊断及本批源码；对照第 2 节复用现有 owner/API。
> 本批提交必须包含真实消费链实现和可执行测试，不能只新增 adapter、伪造工具响应或把 JEV 选项交回 LLM 写图。
> 遵守现有 source_scope、revision/scene、blocked、selection、invocation、settlement 与 Verifier 语义。
> 缺少事实/服务/专项质量数据时完成可离线验证的范围，明确留下哪个批次未完成；不要猜阈值或默认 active。
> 不部署、不恢复任务、不调用现场 Query/Action、相机或运动；需要这些验证时单独请求授权。
> 每批报告修改入口、七维判断、测试实际结果、调用次数断言、剩余问题及下一批前置条件。

供干净 clone 接手时一并转交的仓库流程：修改前先追加当月双语计划日志；完成后补行号/关键 Diff，
同步 CHANGELOG 最近五版；只暂存本批文件，保留既有未跟踪/无关变更；按当前分支提交推送。
用户明确要求不提交/不推送时遵从其要求。新增代码按仓库 Skill Usage Policy 使用相关实现/测试技能。

## 9. 交付状态与下一步

本次交付的是已修订方案与可复用样例。共享预算、片段能力与 DecisionProvider 均仍是待实现工作，
不能从本文推断 JEV 节点准确率或闭环速度已经提升。
推荐下一条实施请求：**“按此工单实施 P0，并完成对应七维 review 和 no-motion 回归。”**
P0 验收通过后推进 P1a；每批有独立收益，不把 JEV 服务可用性变成整个改造的阻塞条件。
