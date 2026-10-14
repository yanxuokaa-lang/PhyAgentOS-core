# 最近十次 PAOS 运行的 JEV 替代边界与 Agent Loop 重构诊断

日期：2026-10-14（Asia/Shanghai）。源码参考：`32b6812f`，分支 `feature/planning-loop`。
状态：已保存诊断与拟议设计；运行代码、模型配置、任务状态及 Runtime 均未修改。

本报告补充并修订 [JEV 总体方案](JEV_AGENT_LOOP_REFACTOR_DIAGNOSIS_20261014.md) 的实施顺序，
重点回答“最近真实流程中哪些功能可以减少 LLM 使用，以及 JEV 必须如何完整接管这些功能”。

七维复审后的落地入口：[编码模型实施工单](JEV_IMPLEMENTATION_HANDOFF_20261014.md)。
供 GPT-5.6-sol 等模型接手实施，补齐 projection 示例、方法扩展/物化接口、共享预算、质量验收和可移交样例。
本报告保留十次运行的证据口径；具体实施细节以该工单的修订为准。

## 1. 结论

推荐采用同一个 Agent Loop 内的三层分工：**程序处理确定部分，JEV 选择现成语义选项，LLM 构造新计划与解释复杂异常。**
其中 JEV 选择下一方法，Coordinator/现有 loop 根据实际结果推进任务；模型返回阶段标签不等于阶段完成。

最近十次任务最有价值的发现是：

- 86 次已持久化节点 selection 的 Tool 候选全部只有一个；工具选择的主要余量是输入/实体/来源选择，而非多工具分类。
- 19 次 selection 已明确使用确定性 Query 路径；其余 67 次包含 52 次 Query selection 和 15 次 Action selection。
- 7 次 `scene.bind` 选参错误都缺少相同三个来源字段，应优先通过声明式装配消除，而不是让 JEV 重写 JSON。
- 17 次 continuation 反复构造观察后理解/能力/绑定、下一对象操作和恢复发现片段。常规片段应提前可执行化，JEV 才能免去规划回合。
- 4 次 unknown Action、支撑歧义、碰撞路线不可用、抓放后置条件失败属于证据或执行问题。JEV 可以选择已定义的调查方法，不能替代真实结果、感知、运动规划和对账。
- JEV 现有入口联合成功为 51/60；节点与片段选择仍是待验证能力。这十次日志用于定位替代位置，不构成 JEV 闭环成功率。

新的交付顺序是：**选择后交接 → 输入投影与提示工作集 → 常规方法片段 → JEV 节点/片段选择 → 有界恢复与复杂规划升级**。
入口意图识别可以独立推进，但不作为解决这些节点开销的前置条件。

## 2. 证据范围与统计口径

### 2.1 原始来源

- 只读任务库：`/home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3`。
- 表：`agent_tasks.record_json`、`agent_task_events`；读取使用 SQLite `mode=ro`/`-readonly`。
- 十个会话：`/home/yanxu/.PhyAgentOS/workspace/sessions/cli_rgb-benchmark-injected-20261001-{80..89}.jsonl`。
- 采样时这些是按创建时间最新的十个任务，创建时间为北京时间 2026-10-13 01:02 至 2026-10-14 13:01。
- JEV 评测：`out/jev-intent-probe/20261009T102953Z-4c8740d6/metrics.json`；完整测量边界见总体方案第 2 节。

会话记录主要覆盖入口/发现阶段，不是完整节点回合 transcript。节点分析以 selection、execution record、
settlement、continuation 和恢复事件为准；没有从 narration 推断实际执行。终端提供的 13 次模型 timing
仅属于用户贴出的片段，没有把它扩展成十个任务的总模型调用数或总 token 数。

这些任务属于同一个 RGB benchmark 工作流，且跨越代码部署：80–87 绑定 Skill 3.0.22，88–89 绑定 3.0.24。
88 与 89 之间还部署过 Core 修复。它们用于识别重复故障，不是同版本受控 A/B 实验，不能外推为所有 PAOS 任务的替代率。

### 2.2 逐任务记录

表中 Q/A 为 execution record 数，S/D 为已持久化 selection 数/明确确定性 selection 数，C 为 continuation 事件数。
事件范围定位原始记录；“停点”优先使用自动推进结束时的事件，不用数小时后的操作员停止时间估算模型耗时。

| 会话 | task_id | Q/A | S/D | C | 原始事件范围 | 主要停点 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 80 | `task_d6c7a8189f824060` | 19/4 | 18/3 | 3 | 12067–12498 | green_place 后置条件失败；后续准备 `no_qualified_contacts`，恢复选择 stop |
| 81 | `task_dfff5bc448ef495b` | 16/2 | 13/3 | 2 | 12499–12701 | 准备报告支撑歧义；刷新后绑定无进展，随后操作员停止 |
| 82 | `task_485c371aea724fcf` | 11/1 | 7/2 | 1 | 12702–12817 | acquire unknown；绑定要求持有状态对账，随后操作员停止 |
| 83 | `task_a0d36a0097884109` | 7/0 | 2/0 | 0 | 12818–12842 | `no_admissible_route`，退让段起始状态碰撞，恢复选择 stop |
| 84 | `task_4807de31b86a4a91` | 11/1 | 7/2 | 2 | 12843–12959 | acquire unknown；绑定要求持有状态对账，随后操作员停止 |
| 85 | `task_50cabc9e3734470e` | 7/0 | 2/0 | 0 | 12960–12984 | 相同路线错误；恢复模型未返回唯一决策，异常路径返回 stop |
| 86 | `task_feedfde84cec4022` | 11/1 | 7/2 | 2 | 12985–13115 | 3 次 pre-Tool provider_timeout；acquire unknown；绑定对账阻塞后操作员停止 |
| 87 | `task_2d374f88b79d4ae9` | 11/1 | 7/2 | 2 | 13116–13242 | acquire unknown；绑定要求持有状态对账，随后操作员停止 |
| 88 | `task_8fed40f6212c4b19` | 17/4 | 16/3 | 3 | 13243–13634 | green_place 后置条件失败；支撑面绑定无进展，随后操作员停止 |
| 89 | `task_5d583f3090304eaf` | 11/1 | 7/2 | 2 | 13635–13748 | acquire 已知失败；当前理解未确认红块，waiting_for_user |
| 合计 | 10 个独立 task_id | 121/15 | 86/19 | 17 | — | 136 条 execution records |

读取时 80–88 状态为 failed，89 为 waiting_for_user。81、82、84、86、87、88 末尾存在
`task_cancel_requested`；不能把这六次的最终 failed 都解释为自动 Agent 推理主动终止。

121 条 Query record 的外层 status 均为 succeeded，但其中 8 条业务 payload 为 unavailable，
由 settlement/恢复流程识别失败：4 次准备不可用、4 次绑定不可用。15 条 Action record 为
8 succeeded、3 failed、4 unknown。统计业务质量必须同时读取 payload 和 settlement，不能只数 HTTP/record 成功。

### 2.3 节点选择分布与交接间隔

| Tool | selection 数 | 明确确定性数 | 优先移出 LLM 的内容 |
| --- | ---: | ---: | --- |
| `grasp.propose` | 14 | 0 | 已绑定实体与合法理解来源的选择、consumer projection |
| `manipulation.prepare` | 14 | 0 | candidates/capabilities 来源槽、精确引用装配 |
| `object.acquire` | 10 | 0 | 消费准备结果和已持久化选择；不由模型重建执行参数 |
| `object.place` | 5 | 0 | 消费抓取终态与已注入目标；动态语义仍服从原准入 |
| `scene.observe` | 11 | 11 | 继续使用已有零模型路径 |
| `manipulation.capabilities` | 11 | 8 | 其余来源已唯一时也由程序装配 |
| `scene.understand` | 11 | 0 | 完整双视角/场景/标定投影，携带已有对账假设 |
| `scene.bind` | 10 | 0 | 程序装配共同来源字段；剩余实体集合选择由 JEV/LLM 处理 |

全部 86 次 selection 都对应本 revision 的实际执行 record。按 selection.created_at 至该节点首条
record.created_at 计算：

| 路径标记 | 样本数 | 中位间隔 | 最小–最大 | 间隔合计 |
| --- | ---: | ---: | ---: | ---: |
| reason 明确为确定性 Query | 19 | 0.782 s | 0.701–0.874 s | 14.891 s |
| 其余 selection | 67 | 13.020 s | 7.282–100.165 s | 1111.412 s |

这测量的是交接间隔，包含宿主处理、模型回合或等待；不是纯推理时间，也不是已实现的可节省时长。
67 是值得继续拆分的选择次数，不能直接写成“JEV 可替代 67 次”或“78% 的工作”。

十份外层会话还记录了 95 次 `forge_tool_context`，其中九次任务各 10 次、83 为 5 次；
每次都有五个初始 Query。可减少的是为读取已有契约再启动认知回合；实时 readiness 检查仍保留。

## 3. 跨任务问题、责任层与方案审核

### M1（Major）：同一种精确字段遗漏重复出现，首先应修输入消费链

80、81、82、84、86、87、88 均出现 `tool_input_schema_invalid`，缺少
`calibration_ref`、`observation_ref`、`scene_revision`。对应事件：
`12261, 12665, 12810, 12952, 13108, 13235, 13435`。

这是 `agent_arguments` 的可纠正失败，未授权执行。相同字段存在于当前授权来源中时，应由 consumer
声明字段映射，程序读取原值；来源不唯一才需要认知选择。不能按字段同名任意跨 record 复制。
JEV 选择实体/来源 ID，原 Coordinator 完成精确装配和校验，避免快模型重复制造相同错误。

当前 `prepare_frozen_query_selection`（`PhyAgentOS/agent/planning_dispatch.py:436`）明确排除了
projection、projection plan 和 trusted builder；扩大零模型覆盖必须先证明来源/语义选择唯一，
通过既有 selection admission，而不是删除该限制后直接执行所有 Query。

### M2（Major）：成功 selection 后仍需要直接交还宿主

`AgentLoop.run_node_turn`（`agent/loop.py:1857`）只将执行工具列入交接集合；
`AgentLoopNodeExecutor._resume_node`（`agent/planning_loop.py:1235`）已经能消费 pending selection。
应把成功且确已持久化的 selection 作为独立交接条件，立即返回原 executor。

不能把 selection 简单塞入执行工具集合：`loop.py:1274` 同时用该集合区分决策与执行预算。
同响应后续工具按既有 deferred handoff 语义处理；失败 selection 保留原纠正机会。
当前 blocked admission 必须先于消费 pending selection，已有 execution record 仍能对账。

### M3（Major）：常规续段可复用，但完整消费接口需要提前落地

17 次 continuation 中多次出现相同结构：恢复观察后理解/能力，再绑定；80、81、88 还出现下一个对象的
grasp/prepare/acquire/place/checkpoint。84、86、87、89 将理解/能力与绑定分成两个续段。
其中确有动态实体边界，不能为了少一段而预绑定尚未观察到的实体。

Skill 现有 `WORKFLOW_DAG`（`examples/forge-skills/pick-place-workflow/src/pick_place_workflow/long_horizon.py:138`）
提供通用依赖骨架，但该声明本身并未覆盖本次全部 binding、goal 与恢复义务。
需要补充少量 Method Fragment，使宿主能从真实结果物化下一段。JEV 选中片段后仍请求 LLM 写图，属于辅助而非替代。

应保留：正常 continuation 与失败 replan 分开；前者在现有条件满足时追加，不消耗恢复重规划预算；
同图的 predecessor 来源关系和跨段授权来源规则照旧。Core 不认识红、绿、蓝或 benchmark 专用步骤。

### M4（Major）：恢复必须把事实缺口与可用方法一同输入，不能只做标签分类

- 82、84、86、87：acquire 的 `SimulationProbeError` 伴随 outcome_known=false；之后绑定返回
  `grounding_unavailable`，明确要求 `runtime_possession_reconciliation`。
- 81：准备返回 `observed_support_unavailable`；88：支撑面绑定无进展。
- 89：理解请求已经携带受影响实体假设，响应仍为 `affected_execution_entity_unresolved`。
  新场景 `entity://e1` 是机器人，不能继承旧场景同名红块身份。

程序先识别必须对账/补证的事实，保留原 invocation 与恢复所有权。若已有合法调查方法，JEV 可以匹配；
若要构造新调查策略、解释新异常或权衡多个目标，LLM 介入。找不到可取得事实的能力时，应准确报告缺口。
JEV/LLM 都不能将 unknown 判成成功、重放原动作或凭置信度补齐观测。

“可调用”与“能解决当前缺口”需要分开。绑定其他已识别实体可以服务其他义务，但不能因此把当前红块身份
对账标记为完成。执行成功、证据充分、任务完成分别由原 owner 判定。

现有 Core v13.4.10/v13.4.11 已处理固定实体缺失/歧义的模型前 blocked 和 selection 消费顺序；
81/88 的历史无进展不能直接宣称当前仍未修复。后续接入应复用并回归这些路径。

### M5（Major）：恢复 provider 失败不能误算为有效语义选择

86 有三组 `agent_provider_blocked/released`（事件 13008/13009、13100/13103、13104/13107），
均声明发生在 Tool 执行前；它们和 Action unknown 是两个不同失败层。
85 的事件 12983 是 `recovery unavailable: ValueError: recovery model returned no unique decision`，
随后事件 12984 结束自动推进。当前 `recovery_decisions.py:285` 将此异常转换为 stop。

接入 JEV 时 `unavailable` 必须先升级给原 LLM 路径，不得把服务无答案当成 STOP。
原 LLM 同样失败时，保留现有安全停止语义并单独记录 provider 原因；若要改成可恢复等待，需单独设计
原 Coordinator 的恢复归属和生命周期，不能在 JEV adapter 内创建新任务状态或无限重试。
输出 choice 合法不代表故障可自动修复；不能把 stop/replay/replan 三选一当成天然简单任务。

### M6（Major）：提示投影和证据完整性应与模型替代一起验收

`ContextBuilder.build_system_prompt`（`agent/context.py:50`）加载通用 bootstrap、memory、Skills；
节点投影（`agent/prompt_context.py:1608`）又携带当前 Skill 和任务事实。
应测量并分离 system、Skill、事实、工具 schema 和历史的 token 占比，消除重复而保留必需约束。

80 的恢复理由称未提供 green_place 权威终态，而任务库确有失败的 `tool_27c9b9178c5843f1`。
这是恢复叙述与任务事实不一致的证据；尚未取得当次完整 provider 请求，不能直接断定字段在何处丢失。
验收应确保相关跨 revision 的已知失败、unknown 与成功效果均可被工作集正确引用，不能只保留成功效果。
JEV 也必须消费同源事实，不能另从聊天摘要拼一个可能丢失失败证据的世界状态。

## 4. JEV 究竟可以替代哪些功能

“适合替代”指设计适配且需专项验证；“程序”列是必须先消除的模型工作。

| 功能 | 程序先承担 | JEV 的具体产物 | 何时需要 LLM | 本批证据/优先级 |
| --- | --- | --- | --- | --- |
| 意图及消息与澄清关系 | 显式命令、task 关联、原状态读取 | 意图/控制语义/问题关系选项 | 混合要求、目标变化、复杂澄清 | 入口另有 60 条评测；十任务都为新任务，不能证明全入口能力 |
| Skill/方法匹配 | 原目录、版本、runtime 适用性筛选 | 已有 Skill/方法引用 | 新方法组合、约束冲突 | 当前方法被用户指定；泛化匹配另测，非本轮首要收益 |
| Tool 实现选择 | 当前节点合法 Tool 集合；唯一适用且完整则直接处理 | Tool option ID | 实现语义不明、需新增能力 | 86/86 单候选，没有真实多 Tool 比较样本 |
| 实体与来源选择 | 绑定传播、当前场景/授权范围过滤、完整选项解析 | entity/source/参数档位的合法组合 ID | 多跳关系、指代冲突、开放约束 | 52 个非确定性标记 Query selection 内的主要候选空间 |
| 精确参数装配 | consumer projection、已有值读取和 schema 校验 | 只选择来源或语义选择器，不生成精确载荷 | 无声明可表达的开放参数需规划/扩展 | 7 次相同字段遗漏，优先由程序修复 |
| 常规阶段选择 | 依赖/结果归约、可物化片段、停止条件 | 已定义 Method Fragment ID | 新图、新调查方法、跨对象顺序 | 17 次续段；必须选完即可进入原 compiler |
| 已知失败分类与方法匹配 | 结构化故障、unknown 对账、明确不可恢复分支 | 已有恢复/调查方法 ID，或 escalate | 接触/碰撞根因、未知异常、复合恢复 | 11 次 recovery decision 含确定性与模型分支，不能全部替换 |
| 状态说明 | 读取真实 task/节点/结果，以模板报告进度 | 可选的简短语义归类 | 需要解释因果、比较策略 | 不应为“已选择，现在执行”再请求模型 |
| Lesson/上下文排序 | scope/version 过滤及必需事实保留 | 可选经验的相关性排序 | 冲突解决、新经验归因/修订 | 本批没有性能证据，放在后续独立交付 |

JEV 不承担：物理运动控制、碰撞/IK/路线规划、视觉定位、校准、真实持有状态确认、
执行结果归约、动作重放许可、最终任务判定。LLM 也不替代这些权威机制；它可以提出调查和新计划。

83/85 的 `no_admissible_route` 与 80 的 `no_qualified_contacts` 需要规划/执行侧诊断。
改变 Agent 决策 provider 不能自动生成合格路线。89 的初始理解 record 生命周期约 68.389 s，准备约 72.728 s，
也不能全部算作 Agent 认知调用可消除的时间。

## 5. 符合 PAOS 哲学的目标架构

### 5.1 一个闭环，三个认知入口

```text
消息 / Tool 终态 / 用户中断
  → 原 AgentLoop / LongHorizon 读取 Coordinator 事实
  → 已有执行先对账；当前不合法选择停止消费
  → 确定性输入与下一节点：原程序处理
  → 有界语义选项：JEV 选择；不接受则一次升级
  → 新方法、新图或复杂异常：LLM 规划
  → 原 selection / continuation / replan 接口
  → 原 admission → registry/wrapper → Gateway/Runtime
  → 真实结果与 settlement → 重新读取事实
  → 下一节点 / 调查 / 等待 / 原 Verifier
```

程序不是第二个 planner。它执行已声明的方法、事实投影与既有生命周期；新目标与新约束仍可让 LLM
重新规划。JEV/LLM 是同一个 Agent 使用的认知能力，不各自持有 task、revision 或执行队列。

### 5.2 所有权与扩展位置

| 内容 | 归属/接入位置 | 必须保持的边界 |
| --- | --- | --- |
| task/revision/selection/执行记录/结算事实 | 现有 Coordinator/SQLite | 不新增 JEV 状态库；模型无直接写入权 |
| 必要工作集与选项适用性 | Agent 的原 prompt/context/decision 接入 | 同源事实；候选合法性不由 JEV 自证 |
| 精确字段投影 | consumer ToolSpec planning 扩展 + 原 Coordinator resolver | producer 不输出消费者专用载荷；Core 不硬编码业务字段 |
| 常规 Method Fragment | Skill 的方法声明 + 现有 compiler | 普通声明与测试，不新增脚本执行引擎或业务分支 |
| typed decision provider | 拟议 `providers/decision.py`、`providers/jev.py` | 只做有限选择；无 Gateway/SQLite 依赖，不伪造 chat tool calls |
| 选择消费与升级策略 | 拟议 `agent/decisions.py` + 原 loop | 无第二个循环；共用既有 deadline/取消/恢复边界 |
| Action/Session 执行 | 原 Gateway/Runtime | readiness、动作准入、终态、停止与对账不转移给模型 |
| 原始目标成功 | 原 Verifier | FINALIZE 只是请求终验；局部工具成功不是任务成功 |

依据：[框架介绍](../zh/01-framework-introduction.md)、[Planning 设计](PLANNING_MODULE_DESIGN.md)、
[输入选择设计](AGENT_TOOL_INPUT_SELECTION_DESIGN.md)、[Runtime/Skill ADR](../adr/0001-runtime-ownership-and-skill-use.md)、
[扩展指南](../user_development_guide/README.md)、[领域术语](../../CONTEXT.md)。

### 5.3 节点选项和片段怎样消费

节点选项由宿主构造，保留原 task/revision/node/scene 关联、合法 Tool、语义选择器和授权来源引用。
Tool 与参数相互依赖时，选项代表完整可解析组合，或先选 Tool 后生成其输入选项；候选爆炸时直接交 LLM。
不要求模型输出坐标、标定、长引用载荷或整个 consumer JSON。

片段只增加实际需要的表达：方法身份、所解决义务、所需事实、原子节点依赖、输入来源关系和退出条件。
复用现有 PlanNode/ToolSpec 类型。动作后的新实体晚绑定；原 `source_scope` 和 predecessor 约束继续成立。
多条方法均可行且涉及语义匹配时交 JEV，只有一条且条件充分时程序直接处理。

当缺口是 runtime possession 时，视觉绑定本身不能清除该义务；当缺口是当前视觉身份时，
方法必须能取得相关新证据或明确进入澄清。工具执行成功但缺口未减少时，重新读取真实结果并升级/等待，
不把相同观察上的相同方法无限重跑。使用既有预算和记录判断进展，不新增 hash 或额外状态账本。

### 5.4 失败、暂停、重启和状态变化

- 有 invocation/record：先由原 owner 对账，再考虑认知调用；unknown 不被模型改成已知。
- 有 pending selection：先遵守当前 blocked admission，再由原 executor 消费，不再分类同一选择。
- JEV 返回 selected：校验当前选项身份与原 admission；成功后无额外 LLM 回合。
- JEV 返回 escalate/unavailable：本轮升级一次；确定性 blocked 不因升级改变为执行许可。
- 返回期间 revision/scene/取消状态变化：复用原检查拒绝旧选择，重新读取事实。
- 显式停止、取消和持久化恢复不等待 JEV；取消认知请求不代表物理动作已停止。
- LLM/provider 失败按调用位置原语义收敛；节点 `waiting_for_agent_provider` 与恢复异常 stop 分别测试。
- 关闭某个决策点只回退尚未发生的认知选择；已接受 selection/在途 invocation 继续由原 owner 处理。

## 6. 可执行的分阶段实施方案

| 批次 | 工作与文件接入点 | 前置条件 | 完成条件 |
| --- | --- | --- | --- |
| P0：选择完成直接交接 | `agent/loop.py`、`agent/planning_loop.py`；独立 selection handoff，复用执行记录与 SkillUse 归因 | 当前 resume/admission 回归通过 | 成功 selection 后模型请求 0；只消费一次；失败 selection 可纠正；blocked 不消费 |
| P1：输入与工作集 | `planning_dispatch.py`、`prompt_context.py`、`context.py`、consumer ToolSpec；声明式来源映射、参数装配、提示组成统计 | 先处理本批反复缺失的三个来源字段，查清合法来源范围 | 七个历史错误样例正确装配；来源歧义不默认取第一条；确定只读节点 0 模型；必要失败事实完整 |
| P2：常规片段 | Skill workflow + 原 compiler/continuation 接口；先实现观察后发现、当前绑定、已定义检查点片段 | P1 已能完整消费输入；动态身份在结果取得后绑定 | 选定已有片段后不再请求 LLM 写图；节点逐个结算；正常续段不冒充恢复 |
| P3：JEV 选择 | 拟议 decision provider/adapter/Agent 策略，配置 off/shadow/active；接入实体/来源/片段选择 | 有完整选项、有各决策点独立数据；P0/P2 消费链已成立 | 接受路径 1 JEV、0 LLM；弃权/超时只升级一次且保留预算；同源事实、合法候选、当前版本检查 |
| P4：局部恢复与复杂规划 | 原 recovery/continuation + Skill 调查方法；常规方法匹配由 JEV，未知根因/新图由 LLM | 分故障类型确认能力可用，区别服务失败和语义 STOP | 不重放 unknown/completed Action；无适用候选时升级；缺口未解决不宣称完成；provider 失败可归因 |

P0/P1 有独立收益，不依赖 JEV 服务。P2 是阶段替代的实际前置条件，不再推迟到所有入口功能完成之后。
为便于编码模型分批交付，P1 拆为 P1a（consumer 投影）与 P1b（工作集），P3 拆为 P3a（关闭/影子接入）
与 P3b（专项数据验收后启用）；禁止把服务连通或固定返回测试通过当成 active 质量证明。
P3 先覆盖只读节点和只读片段；Action/Session 的认知替代另做完整 no-motion 验收，不能因唯一候选自动放行。
经验排序和入口扩展可独立交付，但不阻塞这条主线。

实施时复用现有 provider registry/configuration、HTTP 客户端、selection、编译和记录设施。
新增模型改 provider，新增方法改 Skill，新增证据能力改 ToolSpec/adapter。没有证据要求新增进程、数据库或插件平台。

## 7. 验收、观测与失败分叉

### 7.1 先用固定返回与 Fake Gateway 验证消费链

| 验收样例 | 必须断言 |
| --- | --- |
| 7 次同类 scene.bind 缺字段 | consumer 完整参数来自同一合法映射；传感器/身份值不重新生成 |
| 唯一完整 Query / 唯一有投影 Query | 满足确定性前提时 JEV=0、LLM=0；来源不唯一退出该路径 |
| JEV 合法完整选择 | JEV=1、LLM=0；selection 和实际消费各一次，经验归因/进度保留 |
| 成功 selection 后模型响应中还有调用 | 原 handoff 正确补齐 deferred 结果，不重复执行 |
| 空候选、遗漏实体、互不适配的 Tool/source、跨场景同名实体 | 弃权/原 blocked；不能选择任意剩余项凑成调用 |
| 已有可物化片段 | 无额外 LLM 写图；所有节点仍通过原 compiler/admission/settlement |
| Query record succeeded + payload unavailable | 保留业务失败；不误推进到 Action |
| unknown Action 后的绑定 | 保留 possession reconciliation 义务；不以理解/绑定成功替代 Runtime 对账 |
| 理解成功但红块 unresolved | 保留 gap，选择合法调查方法或升级/等待；不沿用旧 e1 |
| 85 类无唯一恢复决策 | provider 失败与语义 STOP 分开统计；JEV 无答案先升级，原 LLM 失败按原语义处理 |
| 请求期间 revision 改变、取消、重启 | 拒绝旧答案；先对账；已有 selection 不重复分类，blocked 不恢复消费 |
| 80 类跨 revision 失败引用 | 相关历史失败终态可见，模型不能把已失败 place 说成没有执行记录 |

候选生成器和 JEV 分别验收：先证明正确选项或正确升级出口在候选中，再评价 JEV 是否选对。
候选遗漏不能算作模型选择失败后靠更高置信度解决。模板正确性、分类正确性、执行效果分别统计。

### 7.2 再测实际收益

记录各决策点的：确定性覆盖、JEV 接受覆盖、误接受、必要升级召回、升级原因、LLM 调用数、
selection-to-execution 间隔、每个有效节点耗时、任务主动运行时间、provider 等待、工具耗时、
用户等待时间、无进展回合、任务业务结果及实际 provider 版本。

置信策略和在线超时从专项校准数据确定，不照搬入口概率或离线 30 s/重试配置；
首版每个决策点至多一次有界 JEV 尝试，为原 LLM 回退保留时间。接受失败时按决策点关闭，不中断既有 execution owner。

十次同工作流样本用于历史回归；新增多实体、多方法、无适用项和跨对象约束样例，按 family 划分校准/测试，
避免近重复运行同时用于调参和宣称泛化。先离线/无运动验证；真实任务配对测量另行明确授权与部署版本。

失败分叉：

1. 字段/来源解析失败：修 ToolSpec 映射或选项构造，不反复问模型复制字段。
2. 选项中没有正确方法：补充 Skill 方法或能力，或直接交 LLM；不是降低接受条件。
3. JEV 选择质量不足：保持该决策点关闭，增加专项数据；其他已验证点可独立启用。
4. JEV 延迟/服务失败：按预算升级并计算含失败等待的端到端耗时，不能只统计成功请求均值。
5. Runtime 无合格路线、unknown 或观测缺口：进入原对账/调查/修复，分别测量；不能归入 JEV 提速成功。

实现后的已有回归入口如下；新增决策/片段测试随对应功能交付，本次文档工作未运行这些代码测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p pytest_asyncio.plugin tests/test_agent_foundation.py tests/test_planning_loop.py tests/test_forge_tool_api.py
.venv/bin/python -m ruff check PhyAgentOS tests
```

## 8. 可复查的只读查询

以下 SQL 按会话固定样本，不使用“最新十条”随运行漂移。时间间隔是同 revision/node 的 selection 至首条 record，
没有混入操作员停止后的等待。原始数据库和会话留在运行工作区，本提交只保存分析，不复制整库或图像。

```bash
sqlite3 -readonly -header -column /home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3 <<'SQL'
WITH sample AS (
  SELECT task_id, origin_session_key, record_json FROM agent_tasks
  WHERE origin_session_key IN (
    'cli:rgb-benchmark-injected-20261001-80', 'cli:rgb-benchmark-injected-20261001-81',
    'cli:rgb-benchmark-injected-20261001-82', 'cli:rgb-benchmark-injected-20261001-83',
    'cli:rgb-benchmark-injected-20261001-84', 'cli:rgb-benchmark-injected-20261001-85',
    'cli:rgb-benchmark-injected-20261001-86', 'cli:rgb-benchmark-injected-20261001-87',
    'cli:rgb-benchmark-injected-20261001-88', 'cli:rgb-benchmark-injected-20261001-89'
  )
), revisions AS (
  SELECT task_id, origin_session_key, r.value AS rev
  FROM sample, json_each(record_json, '$.revisions') r
), selections AS (
  SELECT task_id, origin_session_key, rev, s.value AS sel,
    CASE WHEN json_extract(s.value, '$.decision_reason') LIKE 'execute the unique read-only Tool%'
      THEN 1 ELSE 0 END AS deterministic
  FROM revisions, json_each(rev, '$.planning_selections') s
)
SELECT json_extract(sel, '$.selected_tool_id') AS tool,
  count(*) AS selections, sum(deterministic) AS deterministic,
  sum(json_array_length(sel, '$.candidate_tool_ids') = 1) AS singleton,
  round(sum((julianday((
    SELECT min(json_extract(x.value, '$.created_at'))
    FROM json_each(rev, '$.execution_records') x
    WHERE json_extract(x.value, '$.node_id') = json_extract(sel, '$.node_id')
  )) - julianday(json_extract(sel, '$.created_at'))) * 86400), 3) AS handoff_seconds
FROM selections GROUP BY tool ORDER BY tool;

SELECT event_id, task_id, event_type,
  json_extract(payload_json, '$.error.code') AS code,
  json_extract(payload_json, '$.error.missing_fields') AS missing_fields
FROM agent_task_events
WHERE event_id IN (12261,12665,12810,12952,13108,13235,13435)
ORDER BY event_id;
SQL
```

SQLite julianday 毫秒舍入可能使合计与原 ISO 微秒解析有几毫秒差异；第 2.3 节用微秒解析后汇总并四舍五入。
19/67 两组中位数取排序后的中间值；复查时应使用各 task 的相同 revision/node，不按节点名跨任务连接。

## 9. 审核处置与边界

六项 Major 在本次设计中分别落实为 M1→P1、M2→P0、M3→P2/P3、M4→P2/P4、M5→P3/P4、M6→P1。
这表示设计有具体处置和验收，不表示运行实现已修复或 JEV 已经接管。

没有新增 hash、冻结协议、第二套任务存储或全局 gate。唯一新增认知能力以普通接口/配置表达；
现有身份、事务、schema、准入和普通测试处理来源一致性、状态变化与执行消费。
此次文档修改不部署能力、不修改安全条件，也不触发任何 Query/Action、相机读取或仿真推进。

需要保留给 LLM 的不是“剩余所有步骤”，而是需要新方法、新图、开放约束和复杂解释的决策。
凡是已有事实与方法足够明确的部分，应通过程序或完整可消费的 JEV 选项完成闭环。

同日七维交接复审在实施工单中处置 H1–H5：四项实施交接 Major 与 pytest 命令 Minor。
它们与本报告 M1–M6 的历史流程诊断分别编号。设计修订不代表运行实现完成；
P3b 仍需实际 JEV 专项数据与配对测量，其他编码模型可以从 P0 独立开始。
