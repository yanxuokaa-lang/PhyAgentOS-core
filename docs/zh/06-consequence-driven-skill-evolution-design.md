# EvoPhy：基于物理交互反馈的具身技能自我进化

> 状态：本地研究设计，未实现，未提交，未推送。  
> 日期：2026-09-08。  
> 范围：长程具身任务中的 Skill/workflow 演化；不改变 PAOS 现有 Runtime、Forge、Gateway、Evidence 或硬件授权边界。  
> 研究名称：EvoPhy（Embodied Skill Evolution from Physical Interaction Feedback）。
> 研究状态：方法、比较假设和实验协议已定义；实证结论有待受控实验产生。

## 1. 审查结论

该方向以 PAOS 现有 experience 模块为基础：任务级语义结果已可沉淀为 `TaskEpisode`、`FailureObservation`、`LessonCluster` 和 `SkillCandidate`，并在满足条件后投影回 Skill Markdown。该能力回答“任务是否成功、哪些经验可复用”；本研究进一步定位“哪一条工作流转移应从已结算的物理后果中学习”。

本设计关注一个更具身的问题：**一次动作即使任务最终失败或成功，它在何处首先使物理世界偏离了工作流对世界状态的预期；该偏离留下了什么可观测后果；怎样只修复相应的工作流转移，而不是重写整个 Skill。**

论文核心名称确定为 **EvoPhy: Embodied Skill Evolution from Physical Interaction Feedback**，中文为**EvoPhy：基于物理交互反馈的具身技能自我进化**。该方法把真实交互反馈投影为可验证的局部工作流修复：从已结算后果定位应学习的转移，再选择能改善后续 Skill 使用的修订。

方法由三项设计条件约束：

1. 部分可观测条件下，归因以按证据排序的假设集表示，并保留 `unknown`。
2. 视角遮挡、末端接触等并发因素以 joint cause set 表示，让多个原因保持可检验。
3. 补丁选择同时度量后果、恢复成本和执行效率，以区分真实能力改善与以冗余观测或重试换来的表面成功。

### 1.1 核心术语

| 术语 | 定义 | 在论文中的职责 |
|---|---|---|
| **PULSE (Physical Outcome Logging for Skill Evolution)** | 一条转移的预期结果、后续观测、证据覆盖与成本的最小记录 | 输入记录 |
| **TRACE (Transition Attribution from Consequence Evidence)** | 沿结果证据定位最早偏离，排序候选转移并保留 joint cause set 与 unknown | 核心算法 |
| **Local Skill Patch** | 只改变受归因转移的 expectation、observation、decision 或 recovery 关系 | 更新动作 |
| **Future Skill Use** | 已晋升 patch 在后续冻结任务中的结果、成本和干扰 | 最终效果 |
| **outcome window** | 为延迟结果收集观测，并将谓词归为 `satisfied`、`violated` 或 `unknown` 的有限时间区间 | 时间语义 |
| **joint cause set** | 可共同解释同一结果的一组转移原因；成员独立计数、生成和评估 patch | 不确定性语义 |

## 2. 研究问题与创新假设

### 2.1 现有 LLM feedback 的不足

文本 Agent 常将 reward、verifier verdict、用户反馈或最终答案正确性视为经验信号。具身长程任务的反馈不同：

- 动作后存在一个延迟显现、可传播的世界状态变化；
- 最终任务失败的位置通常晚于真正的物理偏离位置；
- “完成”不等于世界状态已结算，例如物体短暂抓住后滑落、放置后不稳定、遮挡导致后续感知失真；
- 失败可能可恢复，也可能有不可逆成本；
- 传感器只观察到部分世界，未观察到不是未发生。

因此，仅从整条轨迹文本反思并抽取 Lesson，容易把事后最后一个错误当作应修改的位置，也难以区分“应该改 Skill”、“应该补一次观测”与“证据不足、暂不学习”。

### 2.2 核心假设

本研究检验如下假设：Agent 将每条工作流转移的**预期物理结果**与执行后的**观测结果**比较，使用 TRACE 定位最早可学习偏离，并生成局部 Local Skill Patch。

该方法服务于下一次可复用决策：它输出由后续 episode 检验的局部修复假设，并以 joint cause set 表达部分观测下的归因不确定性。

## 3. 核心记录：PULSE（Physical Outcome Logging for Skill Evolution）

对于工作流中的一个转移边 `e: node_i -> node_j`，构建如下后果签名：

```text
PULSE(e) = (
  expected_effect,
  settled_observation,
  evidence_coverage,
  cost
)
```

各字段的语义如下：

| 字段 | 含义 | 与普通 trajectory log 的差异 |
|---|---|---|
| `expected_effect` | 该转移承诺改变的状态谓词或关系，以及执行前可证实的相关状态 | 从“调用了什么”转为“应造成什么” |
| `settled_observation` | 在 outcome window 内汇聚的执行返回、传感器和后继行为观测 | 将谓词结算为满足、违反或未知 |
| `evidence_coverage` | 哪些状态维度被可靠观测、哪些未覆盖 | 防止把未观测当作反证 |
| `cost` | 恢复与执行消耗的动作、时间、重规划及资源代价 | 识别以高成本换取的成功 |

`settled_observation` 是 PULSE 的关键量。每个被 Skill 依赖的状态谓词在 outcome window 结束时取 `satisfied`、`violated` 或 `unknown`。这一最小记录复用 PAOS 的语义 verdict、capability outcome、Evidence 和 NodeSettlement；`side_effects`、`reversibility` 与 `owner_hypotheses` 在有可用证据时作为扩展字段附加。

PULSE 既记录失败，也记录“语义成功但结果尚未结算或产生副作用”的 episode。这是具身反馈区别于纯答案正确性的主要切入点。

## 4. TRACE：Transition Attribution from Consequence Evidence

按执行顺序，将 episode 视作一条边链。对每条可比较的边，TRACE 从 PULSE 判断已证实的状态谓词违反与关键未知，并输出有序假设集：

```text
TRACE(episode) = [
  {
    edge, violated_or_unknown_predicate, confidence,
    evidence_coverage, owner_hypotheses, alternatives,
    downstream_consequences
  },
  ...
]
```

TRACE 依次考量出现时间、证据覆盖、与下游结果的连通性及归属可操作性，输出最值得优先修复与验证的转移和 joint cause set。

决策规则应保持简单：

- `violated` 且 evidence coverage 足够：产生 Local Skill Patch 候选；
- 仅有关键 `unknown`：形成诊断或观测建议，等待后续 evidence 结算；
- 多个并发高置信假设：保留 joint cause set，并为每个成员分别收集支持；
- infrastructure 或无关环境证据：沿用既有归因拒绝语义，不进入 Skill 候选池。

该归因语义仅决定经验是否进入持久修改候选池；运行时既有安全与停止逻辑保持原样。

## 5. 进化对象：Local Skill Patch

Local Skill Patch 的最小作用域是一条受影响的工作流转移边及其局部前后条件：

```text
Patch(edge e) =
  applicability
  + changed expectation / observation / decision / recovery relation
  + evidence required to evaluate the change
  + predicted consequence and cost effect
```

典型补丁只应属于以下四类之一：

1. **Expectation patch**：纠正该边对状态变化的错误预期。
2. **Observation patch**：在一个已知、可观测的缺口处加入或重排必要观测，而不是泛化地增加检查。
3. **Decision patch**：在满足特定状态条件时选择不同分支、参数范围或子 Skill。
4. **Recovery patch**：把已有可逆恢复的触发点前移到偏离刚被证实时。

补丁以可迁移的状态条件表达，不携带单次对象、坐标、端点、原始 tool payload 或临时错误文本。观测与恢复操作由明确的 PULSE 缺口及其成本收益证据触发。

## 6. 表示结构：链、树与稀疏图的分工

第一阶段采用执行链，候选分支使用版本树，跨任务复用稳定后再引入稀疏图：

```text
Episode execution chain
        |
        v
First-divergence transition edge
        |
        v
Patch version tree
        |
        v
Sparse experience relation graph
```

| 结构 | 保存什么 | 为什么需要它 |
|---|---|---|
| Episode chain | 实际执行顺序、PULSE、下游结果 | “最早”在时间/转移顺序中定义 |
| Patch version tree | 一个 parent Skill/patch 的局部变体、评测和淘汰关系 | 便于回滚、对照和避免并发修改互相覆盖 |
| Sparse experience graph | “相同状态谓词”“相似后果”“可迁移的 patch”“冲突 patch”等少量关系 | 支持跨任务迁移，但不承担执行真相 |

实施顺序为链优先、树其次、图最后。首个研究原型使用边链和补丁树；当不同任务间出现重复 PULSE 模式时，再增加少量可解释的 graph relation。

## 7. 何时进化

将“调整”与“持久进化”分开：

| 时点 | 允许的行为 | 不允许的行为 |
|---|---|---|
| 执行中 | 使用当前已授权恢复、临时重规划、记录 PULSE | 持久化修改 Skill |
| Episode 结束后 | 异步提取 PULSE、TRACE 假设、结果/成本与候选 patch | 将未结算或证据不足的经验写入规则 |
| 同类转移反复出现且可比较 | 形成 patch candidate，并在匹配、留出和风险场景评测 | 用不同原因的 episode 共享支持计数 |
| 分布漂移被观察到 | 建立新的 applicability 区域或独立候选 | 覆盖旧 patch 或把漂移误写成退化 |
| 评价通过后 | 晋升局部补丁，并保留 parent/child 关系 | 用训练 episode 本身宣布泛化成功 |

“反复”不应在设计阶段先硬编码为一个神奇阈值。它至少应意味着独立 episode、可比较的状态谓词、相近的 evidence coverage，且没有更早的竞争性偏离解释。具体阈值和统计检验由后续实验设定。

## 8. 评价：证明后果改善，而非只证明任务成功

每个候选 patch 至少与 parent workflow 在相同任务分布、固定资源预算下比较，并使用匹配 episode、留出 episode 与风险 episode。建议报告以下指标：

| 维度 | 指标 |
|---|---|
| 任务结果 | task success、目标达成质量、超时率 |
| 物理后果 | transition settlement rate、side-effect rate、未结算状态比例 |
| 定位质量 | first-divergence localization accuracy 或 expert/annotated proxy、错误归因率、关键 unknown 识别率 |
| 恢复 | recovery success、recovery action/time cost、replan count |
| 效率 | 总动作数、总时间、tool/model 调用成本；同等成功下的成本增量 |
| 泛化 | 同类转移的 forward transfer、非目标任务干扰、旧能力退化 |
| 稳健性 | 部分观测、延迟观测、噪声观测和并发原因下的保守性 |

最有说服力的实验不应只放“失败 -> 成功”的案例。还应包含：

- 最终任务成功、但放置稳定性或可见性等状态未结算的案例；
- 最终失败、但更早的可观测偏离与最后报错不同的案例；
- 单一原因和并发原因各一组；
- 需要观测补丁、决策补丁、恢复补丁各一组；
- 一个 patch 在匹配任务有效、在非匹配任务不应触发的干扰测试。

主张有效时，同时展示 patch 改善的具体 PULSE 谓词、任务层收益，以及动作和时间成本。`unknown` 降低而 success 不变时，结果归入可观测性改善。

## 9. 与当前 PAOS 的后续接入边界

当前文档只定义设计，数据模型、存储和运行时接入在实现阶段处理。实现复用下列现有边界：

- `TaskEpisode`：承载一次已结算任务的去敏执行链；
- `CapabilityOutcomeFact`：提供 capability phase、owner、world-change 与 evidence availability 的有界事实；
- `FailureObservation` / `LessonCluster`：承载跨 episode 的失败模式，PULSE 作为其结构化输入；
- `SkillCandidate` 与已有 revision 投影：承载补丁树的 parent/child 关系和晋升结果；
- `NodeSettlement` 与 Planning Loop：作为长程 DAG 节点的预期/观测比较锚点，沿用现有 scheduler 和 state store。

首期为既有 episode 增加 PULSE/TRACE/patch-candidate 投影，并使 `SkillCandidate` 的支持键包含具体 transition patch identity，隔离同一 Skill/workflow 下的不同改动。

## 10. 当前待决问题

以下问题决定下一轮设计或实现的形态，不能擅自假设：

1. 第一批实验所依赖的世界状态谓词是什么，哪些可以由现有 Evidence 可靠观测，哪些永远只能标记为 `unknown`？
2. 目标 Skill 是当前 Markdown workflow，还是已有/待定义的结构化 DAG 节点与边？如果两者并存，补丁的权威表示在哪里？
3. 哪些现实/仿真任务能提供可恢复、可重复、可留出评测的后果变化，而不把 benchmark 特定脚本误当成通用 Skill？
4. `settled_observation` 的人工标注、自动 proxy 与模型判断如何分工，才能独立评估 TRACE？
5. 一个 patch 是否允许跨不同 embodiment、传感器配置或 planner 迁移；若允许，最小的 applicability 描述应包含哪些环境条件？
6. 哪些 side effect 属于 Skill 应承担的后果，哪些应明确归属给环境、感知或执行 provider，避免错误学习？

## 11. 下一步边界

在收到新的具体问题前，本文件只作为本地设计基线。不会据此修改现有 Skill、workflow、experience schema、SQLite、planner 或硬件/仿真执行路径，也不会提交或推送。

## 12. 四角度审核：论文贡献的证据要求

### 12.1 总体判断

本节审查早期宽泛的 CDSE 表述：“从长程失败经验形成局部 Skill/workflow patch”。RSI 领域已有多项工作研究跨任务经验积累、Skill patch、局部记忆修改、Harness 更新和版本选择，因此论文以结算感知的转移级信用分配界定方法问题。

更可辩护的问题应改写为：

> 在底层模型、Agent Harness、planner、执行 provider 和任务预算固定时，利用**已结算物理后果**进行带不确定性的**转移级 credit assignment**，是否比整条 trajectory 的任务级反思更准确地选择应修改的工作流位置，并产生在留出任务上更有效、成本更低的未来 Skill-use？

论文核心由以下三项组合构成：

1. 以 `intended physical effect -> observed outcome` 为单位的具身反馈记录；
2. 保留 `unknown`、证据覆盖和 joint cause 的转移级归因；
3. 在相同经验和执行预算下，对比 trajectory-level reflection 与 TRACE 生成的局部 patch。

实验分别检验归因位置、结果记录和局部 patch 的跨任务效果，区分方法增益与已有 Skill evolution 能力。

## 13. 角度一：多长程 benchmark 与 SOTA 对比的问题

### 13.1 当前方案的问题

1. **需要定义跨 benchmark 的最小观测契约。** PULSE 为每个 workflow edge 提供 `intended_effect` 和可比较的 `observed effect`。
2. **长程任务按时间尺度拆分。** 单 episode 多步骤、跨 episode 持续学习、跨任务族迁移和跨 embodiment 迁移分别报告。
3. **机器人 SOTA 与 RSI SOTA 使用不同的优化对象。** 机器人方法可能训练低层 policy，而本方法修改模型外的 Skill/workflow；论文据此在共享底层模型、训练数据和控制器的条件下进行 experience-to-update 对比。
4. **非具身 RSI benchmark 用于协议对照。** 物理结果建模在具身 benchmark 上验证。
5. **只比较 before/after 会混入顺序效应。** 随任务流推进，模型可能因任务更容易、缓存、上下文或随机性改善，而不一定是经验更新有效。
6. **跨 benchmark 复用同一结果契约。** 各环境只提供 adapter，方法使用统一的谓词、patch 类型和结果字段。

### 13.2 推荐的三层 benchmark 结构

| 层级 | 候选 benchmark | 验证内容 | 适用范围 |
|---|---|---|---|
| RSI 协议对照层 | SkillFlow、SkillLearnBench、GDPevo、FinEvo-Bench、Evo-Memory/EvoMemBench | continual stream、Skill 更新、状态保留、held-out transfer、memory baseline | 非物理经验更新 |
| 符号具身层 | ALFWorld，可选 TEACh/VirtualHome | 长程行动序列、可枚举状态谓词、归因 oracle | 符号状态转移 |
| 物理交互核心层 | 当前 PAOS-RoboTwin 路径，加一个具有长程/continual protocol 的环境，如 LIBERO、CALVIN 或 BEHAVIOR/OmniGibson 中的一个 | 延迟结果、副作用、恢复成本、部分观测和跨任务 patch transfer | 具身结果 |

首篇论文保留三个代表点：

1. 一个非具身 RSI benchmark，验证方法遵守标准 continual protocol；
2. ALFWorld 作为可控 attribution/ablation 环境；
3. RoboTwin 加一个不同任务结构的物理环境，作为主要具身证据和跨 provider 扩展测试。

机器人 benchmark 提供环境、任务和执行反馈。公平的 SOTA 对比固定底层模型、Tool/Skill、planner/provider、任务顺序与预算，仅替换 experience-to-update 方法；公开机器人 policy 分数作为环境背景单列报告。

### 13.3 必须包含的基线与消融

| 对照 | 回答的问题 |
|---|---|
| Frozen Skill / no evolution | 不更新时的基础能力是多少？ |
| Full-history or long-context | 改善是否只是因为看到了更多历史？ |
| Retrieval memory | PULSE/TRACE 是否优于检索相似成功/失败经验？ |
| Trajectory-level reflection | 转移级归因是否优于整条轨迹总结？ |
| Whole-Skill rewrite / SkillFlow-style patch | Local Skill Patch 是否更少干扰旧能力？ |
| Oracle first divergence | attribution 误差距离可能上限还有多远？ |
| Random/last-failure edge | “first divergence”是否比最后错误或随机位置更有信息？ |
| No outcome window | 延迟结果记录是否真的必要？ |
| No unknown/joint-cause modeling | 不确定性建模是否减少错误更新？ |
| No efficiency constraint | 成功率是否来自额外观察和重试？ |

所有方法使用相同的基础模型、温度/seed 计划、任务流、初始 Skill、执行和模型调用预算。每个任务顺序至少需要多个随机排列，并设置 state-reset control。训练/适应阶段允许更新；held-out evaluation 阶段冻结更新。匹配任务、重组任务、非匹配任务和风险任务必须分别报告，不能只报告一个 micro-average。

### 13.4 核心指标还需要收窄

论文主指标建议只保留四组：

1. **Future-task utility**：冻结后的 held-out task success/quality；
2. **Attribution quality**：top-k transition localization、causal-set precision/recall、错误持久更新率；
3. **Consequence quality**：目标谓词 settlement、side-effect incidence、关键 unknown 残留；
4. **Evolution efficiency**：每单位成功增益所需的 episode、动作、恢复、tool/model 调用和时间。

其余 transfer、forgetting、interference 和 safety regression 作为次指标。否则指标过多会让论文缺少一个明确主结论。

## 14. 角度二：数据来源与标注闭环的问题

### 14.1 当前 PAOS 数据需要补充结果记录字段

现有 `TaskEpisode`、`CapabilityOutcomeFact`、`ToolExecutionRecord`、Evidence 和 `NodeSettlement` 能提供任务、revision、节点、执行状态、owner、world-change 与 evidence availability，但仍缺少：

- 每条转移明确依赖的状态谓词；
- 动作前后的同一谓词比较；
- 允许物理状态稳定或延迟失败显现的 outcome window；
- 预期外副作用；
- 多传感器覆盖范围与不可观测区域；
- 可用于评价 TRACE 的独立 first-divergence/joint-cause 标注；
- patch 应改哪条边的独立参考，而非由同一反思模型自问自答。

PAOS 日志需要与受控干预和独立标注结合，才能形成可靠的归因标签。

### 14.2 推荐的数据分层

| 数据层 | 来源 | 用途 | 权威边界 |
|---|---|---|---|
| Execution facts | PAOS AgentTask/PlanRevision、Tool records、Evidence、NodeSettlement、capability outcomes | 重建执行链与可见事实 | 只说明实际记录了什么 |
| Simulation oracle | benchmark 内部对象 pose、接触、约束、成功谓词和时间序列 | 生成评价标签和延迟后果 | 只用于标注/evaluator，不泄漏给 Agent |
| Controlled intervention | 固定初态与动作，仅注入一次滑落、遮挡、目标扰动、感知缺失或执行偏差 | 建立较强的 first-divergence ground truth | 干预标签不等于自然失败分布 |
| Expert annotation | 从同步视频、状态曲线和执行链标注 earliest detectable divergence 与候选因果集合 | 评价真实/复杂 episode | 至少双人标注并报告一致性；分歧保留为集合/unknown |
| Real-world pilot | 少量真实机器人长程任务的同步多视角、robot state 和 operator event | 验证 sim-only 结论是否完全失真 | 不适合作为首期大规模训练源 |

最重要的数据是**成对或成组的受控 episode**：同一任务、近似初态和同一 workflow 下，一个正常执行，另一个在某个转移引入单一干预；随后再加入少量双重干预检验 joint cause。该数据使 TRACE 的定位可被独立评价，也能测量下游结果传播。

### 14.3 数据生成协议

每个 benchmark adapter 应只提供以下标准输出：

```text
episode identity and task family
ordered transition identities
expected predicate set per transition
timestamped observable evidence
privileged evaluator state (evaluation only)
settlement decision and window
intervention identity (if controlled)
task outcome, side effects, recovery and resource cost
```

数据拆分必须同时隔离：

- episode 实例；
- 对象/布局/seed；
- task family 或规则组合；
- patch applicability 区域；
- 若主张跨 embodiment，则隔离 robot/sensor/provider。

样本规模由小型 pilot 估计的自然失败率、TRACE 标注一致性、patch effect size 与方差决定，再通过 power analysis 确定正式规模。

### 14.4 数据闭环中的四个泄漏风险

1. simulator privileged state 被写入 Skill 或 Agent context；
2. 同一 object/layout/seed 同时出现在 patch 生成与 held-out evaluation；
3. 同一模型生成 TRACE 结果、生成 patch、再充当唯一 evaluator；
4. benchmark 特有错误码或坐标被抽象成所谓通用 Skill。

训练反馈使用 provider-visible evidence；oracle state 用于离线评价。最终 semantic outcome、TRACE 标签和 patch utility 由不同来源或不同程序路径确定。

## 15. 角度三：PAOS 架构与扩展原则的问题

### 15.1 当前设计过于概念化

PULSE/TRACE 投影明确预期结果、实际结果、持久化、patch synthesis 与 promotion 的所有者，并沿用 PAOS 的 Runtime、Verifier、memory store 和 Skill writer。

另一个关键问题是权威表示不明确：当前 Skill 是 Markdown 工作流，而 `PlanGraph`/`NodeSettlement` 是结构化执行表示。没有稳定的 transition identity 和 expected-effect projection 时，所谓 local edge patch 无法跨一次 DAG 重建持续存在。

### 15.2 推荐的最小架构：六项运行功能，一个离线评测包

不建议增加一个大型“自我进化子系统”。通过 PAOS 的 extension seam 接入一个可选的 evolution
package；PAOS core 只提供 provider-neutral port、事实投影和 candidate lifecycle。

1. **Expected Effect Projection**  
   从结构化 `PlanGraph`/Skill planning extension 读取 transition identity、前置条件、预期后置谓词和允许副作用。Markdown 只能作为人类可读投影，不能靠运行时 LLM 临时猜测权威谓词。

2. **Consequence Projector**  
   在 episode 完成后，从既有 `NodeSettlement`、CapabilityOutcome 和 Evidence 引用投影 provider-neutral 的 predicate observation、coverage、settlement 和 cost。物理值与传感器语义仍由 benchmark/runtime adapter 所有。

3. **Divergence Attributor**  
   只读 episode chain，输出 ranked transitions、causal set、confidence 与 unknown；不修改 task verdict，不调用 Gateway，不授予动作或恢复权限。

4. **Transition Patch Candidate Adapter**  
   把 attribution 转成已有 `WorkflowPolicyCandidate`/`SkillCandidate` 能承载的局部变化，并把 candidate identity 收窄到 `parent skill + workflow + transition + patch semantics + applicability`。继续复用现有支持计数、evaluation receipt、review 和 promotion callback。

5. **Benchmark/Evaluation package（仅离线）**  
   位于 runtime core 之外，负责流式 task order、state reset、oracle label、matched/held-out/hazard evaluation 和统计输出。它不能写生产 Skill，也不能成为执行路径。

6. **Future-use observation**  
   在候选晋升后的新 binding 中记录实际后果、成本、迁移收益和非目标干扰；它只观察后续使用，不回写历史 episode，也不替代独立评测。

整体数据流应为：

```text
Runtime/benchmark provider facts
  -> existing Coordinator + Evidence + NodeSettlement
  -> existing TaskEpisode
  -> Consequence Projector
  -> Divergence Attributor
  -> existing candidate/evaluation/promotion lifecycle
  -> future Skill/workflow projection
```

### 15.3 PAOS evolution 模块的实际功能划分

这里需要区分两个层次：`evolution` 是 PAOS 中独立的宿主扩展模块，`EvoPhy` 是其中一种论文和
实验方法标识。具身后果处理实现为可选的 evolution package，通过 PAOS 暴露的 port 调用
`ExperienceCoordinator`、`SkillEvolutionManager` 和 `WorkflowPolicyCandidateManager`，而不是把
实现代码写入这些 core 类。不创建新的顶层控制器、任务调度器或事实库。

为后续接入其他 RSI/self-evolution 方法，`evolution` 只定义宿主协议和生命周期适配，不把某一篇
论文的归因算法写成唯一入口。每个方法是一个可注册的 strategy/plugin，至少声明稳定的
`method_id`、所需 projection 能力、候选输出类型和评测要求；宿主负责 episode 事件转发、候选
生命周期和 Skill binding，方法负责自己的经验更新逻辑。这样可以并列接入 `EvoPhy`、trajectory
reflection、memory-rewrite 或其他经过验证的方法，而无需修改 PAOS core 或复制事实库。

| 功能 | 放置位置 | 输入 | 输出 | 负责的问题 |
|---|---|---|---|---|
| Transition binding projection | extension package | frozen Skill binding、PlanRevision、PlanGraph/WORKFLOW_DAG port | 有稳定 identity 的 transition expectation | 当前执行边承诺改变哪些谓词 |
| Consequence settlement | extension package | core 提供的 Tool records、NodeSettlement、Evidence、CapabilityOutcomeFact | `ConsequenceRecord`：settled/unknown、coverage、cost | 动作后的物理后果何时可以结算 |
| Transition attribution | extension package | 有序 `ConsequenceRecord` 链、failure owner、下游结果 | ranked transition、multiple-cause set、诊断状态 | 哪条边值得形成学习候选 |
| Revision candidate synthesis | extension package | attribution、适用条件、现有 Skill/workflow port | scoped `SkillCandidate` 或 `WorkflowPolicyCandidate` proposal | 将归因转成局部修订 |
| Independent candidate evaluation | offline extension/evaluator | parent/candidate、matched/held-out/hazard 结果、成本 | evaluation receipt 与 `promote/hold/reject` request | 修订是否改善后续 Skill 使用 |
| Future-use observation | extension package | 新旧 candidate binding、后续 episode outcome port | forward-transfer、interference、retirement evidence | 晋升后的实际效果和反证 |

这六项功能的调用关系如下：

```text
AgentTaskCoordinator / PlanRevision
          |
          v
  transition expectation projection
          |
          v
  TaskEpisode + NodeSettlement + Evidence
          |
          v
  consequence settlement
          |
          v
  transition attribution
          |
          v
  scoped candidate synthesis
          |
          v
  existing evaluation / promotion lifecycle
          |
          v
  later episode binding and future-use observation
```

#### 功能一：Transition binding projection

该功能从结构化 `PlanGraph`、Skill planning extension 或只读 `WORKFLOW_DAG` projection 获得
transition identity、前置条件、预期后置谓词和允许副作用。它只生成 projection，不改变
`PlanRevision`，也不从 Markdown 或运行时模型文本临时猜测权威谓词。Markdown 继续作为人类可读的
Skill 投影。

Transition identity 至少绑定 `skill_name`、Skill revision、workflow key、source node、target
node 和 semantic transition key。它不绑定对象坐标、Gateway ID、provider payload 或一次任务的
临时参数。这样候选可以跨 episode 找到同一条语义转移，同时保留当前 Skill revision 的边界。

#### 功能二：Consequence settlement

该功能在 episode 完成后异步运行，不进入工具调用和动作 admission。它合并现有
`NodeSettlement`、`CapabilityOutcomeFact`、Evidence 引用和已记录的成本，将每个预期谓词结算为：

- `satisfied`：证据覆盖足够，后置条件成立；
- `violated`：证据覆盖足够，后置条件被违反；
- `unknown`：观测缺失、冲突或窗口结束仍无法判断。

结果确认窗口由 provider/profile 提供可解释的时间语义，例如抓取后的稳定保持、放置后的静止和
遮挡解除后的再次观测。物理状态解释仍由 adapter/provider 所有，experience 只消费 provider-neutral
projection。`unknown` 进入诊断和候选等待状态，不被改写成成功或失败。

当前 `ConsequenceSettler` 接收 `SettlementTarget` 与按时间排序的 `OutcomeEvidenceSample`，在 deadline、
provider settled、terminal event 或 interruption 时关闭窗口。它使用窗口结束前最后一组观测进行结算：
覆盖率不足、无证据或同一时刻状态冲突均输出 `unknown`；窗口内出现的副作用与 evidence references
保留在结算结果中，owner hypotheses 绑定最后一组观测。该实现只计算 provider-neutral observation，
不轮询传感器或调用 Tool。

#### 功能三：Transition attribution

该功能扩展现有 analyzer 的输入，而不是替换现有 Lesson 归因。它沿 episode 的 transition 顺序
比较预期与结算结果，输出：

```text
AttributionResult(
  ranked_transitions,
  multiple_cause_sets,
  unknown_predicates,
  owner_hypotheses,
  downstream_consequences
)
```

`planner`、`execution`、`perception`、`settlement` 和 `infrastructure` 等 owner 继续使用 PAOS
已有的有界分类。只有 workflow-related 且证据覆盖充分的偏离，才进入 Skill candidate；只属于
基础设施、环境或证据缺口的记录保留为诊断。这个功能不创建 retry、不调用 Gateway、不修改任务 verdict。

#### 功能四：Revision candidate synthesis

该功能将归因结果转换为已有 candidate 模型可承载的局部变化。候选必须包含：

- parent Skill/workflow revision；
- transition identity；
- changed surface：expectation、observation、decision 或 recovery；
- applicability 与 `does_not_apply_when`；
- source episode references 和归因证据摘要；
- 预期后果改善、成本影响和需要的验证条件。

候选内容沿用现有去敏与 managed-block 规则，不写入坐标、对象值、endpoint、Gateway ID、原始
工具输出或绕过 Verifier 的指令。Skill 内容的持久化仍由 `SkillEvolutionManager` 完成；planning
policy candidate 仍由 `WorkflowPolicyCandidateManager` 管理。二者只共享不透明 reference，不复制
生命周期状态。

#### 功能五：Independent candidate evaluation

候选生成与候选晋升分离。`ExperienceCoordinator` 可以创建 pending candidate job，但 promotion
继续走现有 candidate lifecycle 和 review/promotion callback。评测至少拆成 matched、held-out 和
hazard/non-target 三类，固定 parent/candidate 的任务流、provider、预算和 patch 生效时机，并记录
任务结果、物理后果、成本、错误更新和干扰。

`SkillCandidate` 的支持键需要包含具体 transition revision 和 applicability，而不仅是 Skill 名称、
workflow key 或 owner。这样不同修订不会共享错误支持计数。promotion 以后，新 revision 只影响后续
新 episode 的 Skill binding；既有 episode 的 binding 和 verdict 保持不可变。

#### 功能六：Future-use observation

当前 PAOS 能记录 candidate promoted，但还需要把“晋升后实际使用”作为可观测闭环。每个后续 episode
在创建时记录 parent/candidate binding，完成时回填：

- 同类 transition 的后果变化；
- later-task success 与 criterion quality；
- 动作、时间、重规划和模型调用成本；
- 非目标 workflow 的触发率与旧能力退化；
- counterexample、retirement 或重新打开 candidate 的证据。

该功能只汇总已有执行事实，不修改历史任务，不把单次成功直接转成 promotion，也不把 candidate
被加载误记为 candidate 生效。

### 15.4 进化时机与状态机

PAOS 的现有任务生命周期与 EvoPhy 学习生命周期保持分离。建议在 experience 层增加以下候选状态，
映射到已有 `pending/blocked/promoted/retired` 事件，而不引入新的任务状态：

```text
observed
  -> settled
  -> attributed
  -> candidate_pending
  -> evaluated
       ├─ promote -> active for new bindings
       ├─ hold    -> collect more comparable episodes
       └─ reject  -> diagnostic / superseded
```

触发规则：

1. `observed`：每个已终结 episode 都可记录后果事实；不产生持久 Skill 变化。
2. `settled`：结果确认窗口完成后，才允许对相关谓词进行比较；`unknown` 保持待诊断。
3. `attributed`：形成 ranked transition 和 owner scope；只有 workflow-related 证据进入 candidate 支持。
4. `candidate_pending`：同一 transition、相近 applicability 和可比较 coverage 的独立 episode 汇聚后，
   生成候选；单次 episode 只提供 evidence，不直接晋升。
5. `evaluated`：独立 matched/held-out/hazard 结果决定 `promote`、`hold` 或 `reject`。
6. `active for new bindings`：新 revision 只在后续 Skill activation 和 AgentTask binding 中生效；
   通过后续 episode 的实际表现继续收集 forward-transfer、interference 和 counterexample。

执行中允许临时恢复和重规划；持久进化在 episode 后异步进行。该分离保持 AgentTask、PlanRevision、
Gateway invocation 和 Skill binding 的不可变事实，同时让进化失败继续沿用 fail-open 语义。

### 15.5 PAOS 设计原则下的新增边界

| 设计原则 | 对 evolution 模块的具体要求 |
|---|---|
| 单一事实源 | AgentTask/PlanRevision/SQLite 保存任务和执行事实；experience 不另建物理状态库 |
| provider-neutral | 核心只消费 transition expectation 与 consequence projection；传感器、位姿、接触和稳定性由 adapter/profile 提供 |
| 执行与学习分离 | evolution 不创建 Tool invocation、不持有 Session、不重试 Action、不授权 motion |
| 事实不可变 | 历史 binding、verdict、evidence 和 invocation 不因候选修订而改写 |
| fail-open | 反思、结算投影、候选生成或写入失败记录事件并保留原任务结果 |
| 最小扩展 | 在 `ExperienceCoordinator` 现有异步 job 与 candidate lifecycle 上增加 projection/attribution/evaluation seam |
| 可观察性 | 每次 settlement、attribution、candidate、evaluation、promotion 和 future-use 都产生有界事件 |
| 可回滚 | Skill Runtime 使用已有 managed block、原子替换、reload validation 和 rollback |
| 安全权威不迁移 | Verifier、Gateway、Runtime、operator policy 和 adapter readiness 继续拥有最终判断 |

以下组件不属于本次 PAOS evolution 扩展：第二个 scheduler、第二个 SQLite/store、独立 planner、
独立 verifier、物理 world model、provider-specific Agent Tool、自动修改 `AGENTS.md`/`EMBODIED.md`、
以及把 `unknown` 变成新的普通执行 gate。

### 15.6 与现有代码的最小接入面

| 现有代码边界 | 接入动作 |
|---|---|
| `ExperienceCoordinator` | 暴露 episode/event/candidate ports；可选地装载 extension，不实现具身逻辑 |
| `AgentTaskOutcomeSource` / `ForgeTaskOutcomeSource` | 保持 episode outcome provider；通过只读 port 提供 transition/consequence projection 所需字段 |
| `TaskEpisode` / `LineageOutcome` | 保留执行顺序、revision、invocation 和 evidence lineage；不复制 provider 原始 payload |
| `CapabilityOutcomeFact` / `NodeSettlement` | 提供 capability phase、owner、world-change、settlement 和 evidence availability |
| `ExperienceAnalyzer` | 保持 generic analyzer port；具身 attribution 由 extension 实现并提交结构化 proposal |
| `SkillEvolutionManager` | 继续拥有 Skill revision 持久化、脱敏、managed block、原子替换和 rollback |
| `WorkflowPolicyCandidateManager` | 继续拥有结构化 workflow candidate 与既有 promotion callback |
| `SkillActivationManager` | 在新 task binding 中加载已晋升 revision，记录 parent/candidate lineage |
| offline evaluation package | 作为独立 extension/CLI 生成 matched/held-out/hazard 任务流和统计，不进入 core import path |

首期实现优先增加 projection 和 candidate identity；候选树、跨任务 sparse graph 和自动 retirement
均在产生真实分支数据后再评估，避免把数据组织结构误当成新的执行控制面。

### 15.6.1 独立 package 与 PAOS host seam

具身进化实现采用 monorepo 内的独立 distribution：

```text
extensions/evolution/
├── pyproject.toml         # independent dependencies and build metadata
├── README.md              # development and deployment boundary
├── evolution/
│   ├── api.py             # host ports and EvolutionMethod protocol
│   ├── plugin.py          # extension entry point and lifecycle
│   ├── registry.py        # method_id -> strategy factory; no scheduler/store
│   ├── projection.py      # transition and consequence projections
│   ├── settlement.py      # delayed outcome confirmation
│   ├── pulse.py           # PULSE physical-outcome records
│   ├── trace.py           # TRACE transition attribution
│   ├── revision.py        # local revision proposal
│   ├── evaluation.py      # offline candidate evaluation
│   ├── experiment.py      # reproducible evaluation artifacts
│   ├── observation.py     # promoted-version future-use observation
│   └── methods/
│       ├── evophy/         # current consequence-feedback method implementation
│       └── <method_id>/     # future RSI/self-evolution method, isolated by strategy
└── tests/                 # extension-owned fake-facts and method tests
```

宿主模块统一使用 `evolution` 命名，不把论文名称 `EvoPhy` 提升为宿主 namespace。当前论文实现
放在 `evolution.methods.evophy`，未来方法放在同级的 `evolution.methods.<method_id>`；不建立
任何方法对 PAOS core 的反向依赖。根 `pyproject.toml` 不发布 `evolution`；该目录使用自己的
`pyproject.toml`、依赖解析、测试入口、构建产物和本地 `.venv`。这使扩展能够脱离 PAOS Core
完成开发、fake-facts 验证和 wheel 构建，同时保持 core 与 extension 的单向协议依赖：

```text
PAOS core  --public ports/projections-->  evolution extension
     ^                                      |
     |                                      v
     +---- existing candidate/activation lifecycle
```

PAOS core 只需要一个薄的 host seam：在 episode 完成、candidate 生命周期变化和 Skill activation
绑定时发布结构化事件或调用可选 extension callback。该 seam 不解析物理结果、不运行归因算法、不
创建新任务状态。没有安装 extension 时，现有 generic evolution 行为保持不变。

独立开发环境不等于独立运行进程。同进程部署时，将 extension wheel 安装到 PAOS host 环境，
再由 composition root 注入 `EvolutionExtension`。当具体方法出现无法共存的依赖、需要崩溃隔离，
或长期占用 GPU/CPU 时，再通过该 host seam 增加 worker transport，使扩展运行在自己的解释器和
`.venv` 中。当前 PULSE/TRACE 是轻量、无设备依赖的纯 Python 逻辑，独立进程不会改善其正确性，
也没有具体失败证据支持引入 IPC。

extension 通过以下 port 读取和提交信息：

| Port | 方向 | 内容 | 所有者 |
|---|---|---|---|
| `EpisodeReaderPort` | core → extension | 去敏 TaskEpisode、PlanRevision、Tool lineage、Evidence refs | PAOS core |
| `TransitionProjectionPort` | core/Skill → extension | transition identity、前置条件、预期后置谓词 | PAOS planning/Skill projection |
| `OutcomeProjectionPort` | adapter → extension | provider-visible physical outcome、coverage、cost、window metadata | provider adapter |
| `CandidateLifecyclePort` | extension → core | revision proposal | PAOS experience/evolution |
| `EvaluationLifecyclePort` | extension → core | evaluation receipt、selection decision | PAOS experience/evolution |
| `SkillBindingPort` | core → extension | parent/candidate binding 和后续使用结果 | PAOS Skill Runtime/experience |
| `EventSinkPort` | extension → core | settlement、attribution、candidate、evaluation 事件 | PAOS event/persistence |

extension 不直接导入 Gateway、Dora、Action endpoint、planner runtime、Verifier 或机器人 SDK。provider
adapter 可以读取自己的观测和仿真状态，但只向 extension 输出 provider-neutral projection；privileged
state 仅进入离线 evaluator。

#### 15.6.1.1 方法注册与兼容性边界

方法注册表只解决“哪个方法接收哪些事件、产生哪类候选”的发现问题，不承载调度、事实存储或
promotion 权限。建议的最小协议为：

```python
class EvolutionMethod(Protocol):
    method_id: str
    required_projections: frozenset[str]

    def process(self, episode: EpisodeProjection) -> Sequence[CandidateProposal]: ...
    def on_candidate_evaluated(self, receipt: EvaluationReceipt) -> None: ...
```

`EvoPhy` 可以实现该协议并额外使用 settlement、attribution 和 future-use ports；只做文本记忆
重写的方法可以声明不需要 physical outcome projection。registry 返回 method instance 和能力声明，
host 在能力不满足时跳过该方法并记录普通 extension 事件，不改变任务结果。多个方法可以在同一
episode 上并行生成候选，但每个候选必须携带 `method_id`，其支持计数、评测 receipt、promotion
请求和后续使用结果彼此隔离，防止不同论文方法共享错误的证据。

这一层不要求现在实现所有方法。首期只实现 `evolution.methods.evophy`，并用一个极薄的 registry/协议为
未来方法留出接入点；新增方法只需实现协议、声明所需 projection、提供离线 evaluator adapter，
无需改动 `ExperienceCoordinator`、Skill store 或 Runtime。

### 15.6.2 Core 只需增加的最小接口

当前接入面按运行责任分为五项：

1. PAOS Core 定义 typed `EpisodeClosedHook`，在 episode 已持久化后调用 `on_episode_closed`；
2. extension 的 `EpisodeProjectionPort` 把 Core episode 与 provider/Skill projection 合成为不可变输入；
3. `candidate_sink` 和 `event_sink` 由 composition root 注入，把 proposal 与事件交回现有生命周期；
4. offline evaluator 调用 `on_candidate_evaluated`，Future-use observer 按 `method_id + candidate_id` 记录后续结果；
5. 部署层安装并注入 extension wheel；未注入时 callback 为 no-op，扩展失败保持原任务结果。

Skill binding 与 candidate promotion 继续由现有 PAOS lifecycle 驱动。需要在候选晋升后自动采集
future-use 时，composition root 将现有 binding/outcome 事件适配到 `FutureUseObserver`；这不要求 Core
理解 PULSE、TRACE 或 EvoPhy。

这些接口属于 PAOS 的扩展协议，不包含具身规则、物理谓词、归因权重或 benchmark 代码。所有业务实现
留在 `evolution` package；现有 `ExperienceCoordinator` 只负责事件转发和生命周期协调。

### 15.7 PAOS 所有权边界

| 责任 | 所有者 | 方法可修改范围 |
|---|---|---|
| 物理/仿真世界事实、传感器语义 | Runtime/benchmark adapter | 否，只能消费投影 |
| AgentTask、revision、node settlement | Coordinator/现有 store | 否，不建第二 store |
| 执行 admission、lease、cancel、motion | Forge/Gateway/provider | 否 |
| 最终语义成功与安全规则 | Verifier/operator policy | 否 |
| 经验 projection、attribution、candidate | `evolution` extension（由所选 method 实现） | 是，但只产生非权威候选 |
| Skill/workflow promotion | 现有 review/promotion boundary | 是，沿用已有流程 |

`unknown` 参与自动学习与晋升语义；任务执行继续沿用已有的不可逆、跨系统、安全和正式发布边界。方法复用既有版本、存储与调度能力。

### 15.8 仍需解决的四个接入与证据缺口

1. extension wheel 的标准 CLI/gateway composition root 仍需由宿主显式选择 projection ports 后装载；默认不自动猜测 provider 的物理语义；
2. `EvolutionCandidateLifecycleAdapter` 已将带有 Skill scope 的 proposal 映射到普通 `SkillCandidate`；decision surface 仍只在宿主显式提供 policy digest resolver 时映射到 `WorkflowPolicyCandidate`，不会猜测规划 policy 的物理语义；
3. EvoPhy Skill candidate 现在需要独立支持、完整 matched/held-out/hazard receipt，以及与当前 receipt 集绑定的 extension `promote` decision。评测 runner 分别通过 `on_candidate_evaluated(...)` 和 `on_candidate_selected(...)` 回写这两类事实，之后由具名宿主 reviewer 显式调用现有 Skill writer。它不是自动 production promotion；workflow policy 仍走独立的 review/promotion callback；
4. 需要一条完整的多成功 episode -> candidate -> evaluation -> promotion -> 后续任务实际使用新 Skill 的端到端证据。

这些是实验可信度问题，不只是工程完善项。若未解决，论文无法确认性能变化来自哪个实际生效的版本。

代码复核后的实现边界如下：`EpisodeProjection` 现在拒绝未声明的 predicate，EvoPhy 不会从无
evidence reference 的 violation 生成候选，owner hypothesis 需要达到配置的最低置信度，TRACE
默认保留 earliest-observable 顺序并可显式切换到 score-primary 排序。`CandidateLifecyclePort`
把候选提交交还宿主；它不替代 PAOS 的 SkillCandidate/WorkflowPolicyCandidate adapter，也不
自动授予 promotion 权限。verification-off episode 在 extension 入口被跳过，重复评测 receipt
保持 hold，Future Skill Use 没有 held-out pair 时不报告 forward-transfer gain。

## 16. 角度四：RSI 相关工作能支持什么，不能支持什么

### 16.1 检索边界

2026-09-08 进行了一个只取元数据的 OpenAlex/Crossref 小规模快照，并交叉查看用户给出的 Awesome RSI curated map。检索得到 46 个去重候选；11 个 provider-query 组合完成，Crossref 的一个 benchmark 查询为 partial。因此下面是**相关工作快照，不是穷尽综述或新颖性证明**。Awesome RSI 可用于发现和分类，论文中的技术主张仍应回到原论文核验。

### 16.2 能作为背景与对照的工作

| 工作 | 可支持的背景命题 | 对当前创新的威胁/边界 |
|---|---|---|
| StuLife / Experience-driven Lifelong Learning, arXiv:2508.19005 | Agent 可从连续交互、长期记忆和 recurring patterns 形成 Skill | “从交互经验学习 Skill”不是新颖性 |
| Evo-Memory, arXiv:2511.20857 | 需要用连续 task stream 评价 test-time memory evolution | 支持 streaming protocol，不覆盖 PULSE |
| EvoMemBench, arXiv:2605.18421 | memory 应区分 in/cross episode 与 knowledge/execution content；long-context 是强基线 | TRACE 与 full-history/retrieval baseline 比较 |
| SkillLearnBench, arXiv:2604.20087 | Skill 学习应同时评价 Skill 质量、trajectory 和 task outcome；外部反馈与多轮更新重要 | 多级指标与 iterative Skill generation 已存在 |
| SkillFlow, arXiv:2604.17308 | 可从 trajectory 与 verification feedback 对 Skill 增删改，并在连续 task family 中评价 | “trajectory -> Skill patch”和链式更新均非新颖性 |
| Recuris, arXiv:2608.24876 | 长程任务中可聚合跨任务失败并局部修改相关 Skill memory | 对旧表述威胁最大；“重复失败 -> 局部 Skill 修改”不能再作为核心贡献 |
| Evo-Harness, arXiv:2608.15071 | Solver 可总结 candidate experience，Evolver 决定 add/merge/revise/discard | candidate experience 的双角色过滤也不是新颖性 |
| SkillSmith, arXiv:2606.01314 | Skill 与 Tool 可协同演化，且需要考虑 Skill 之间的协作/干扰与历史失败模式 | 方法范围聚焦 workflow transition，Tool 与经验图演化作为相邻问题 |
| Darwin Gödel Machine, arXiv:2505.22954 | tree/archive 能保留多个候选版本并用 benchmark 实证选择 | patch tree 是实现选择，不是独立创新 |
| GDPevo, arXiv:2608.03764 | rule recombination 可区分经验复用和答案记忆，并构造 held-out combination | 支持 compositional held-out protocol，不支持物理因果主张 |
| FinEvo-Bench, arXiv:2608.06144 | interleaved continual stream、不同任务顺序和 state-reset control 可测 retained experience 增益 | 在线积累协议已有成熟对照思路 |
| HarnessDev, arXiv:2609.01437 | 固定模型权重后仍应评价可运行 harness 的能力与 token efficiency，并使用 hidden downstream tasks | 支持 capability + efficiency 评价，不证明局部 patch 优越 |

Proteus 是可参考的开源系统，而非上述论文证据链的替代品。它支持“声明可修改表面、fresh context、验证后激活、保存版本”的工程思想，但不能单独支撑学术新颖性。

### 16.3 RSI 文献支持的边界与待检验命题

现有非具身 RSI 工作为 continual protocol、经验更新基线和版本化候选选择提供背景。具身论文以以下待检验命题建立自己的证据链：

- 物理后果比任务 verdict 更适合指导具身 Skill 更新；
- 最早可观测偏离比最后失败点更有 causal utility；
- outcome window 能识别延迟滑落、放置不稳等具身结果；
- 带 `unknown` 和 concurrent causal set 的 attribution 会减少错误 Skill 更新；
- transition patch 在相同成功率下具有更低恢复/执行成本；
- PULSE 能跨不同物理 provider 保持同一语义。

这些命题通过受控干预、独立标注与冻结后的 future Skill use 评估。

## 17. 论文贡献陈述与建议名称

**EvoPhy: Embodied Skill Evolution from Physical Interaction Feedback** 将研究问题收敛为物理交互反馈如何改变未来 Skill 使用：

中文：**面向具身 Skill 自我进化的物理交互反馈学习**。

论文贡献由四个可检验部分构成：

1. 一个将预期物理效果、延迟结算、部分可观测性和副作用统一到 workflow transition 的有界表征；
2. 一个输出 ranked edge、joint cause set 与 `unknown` 的 TRACE 方法；
3. 一个固定模型、Harness 与执行 provider 后，比较 trajectory-level 和 transition-level experience update 的跨 benchmark 协议；
4. 一个复用 TaskEpisode、NodeSettlement 与既有 candidate lifecycle 的 PAOS 接入方案。

贡献范围聚焦结算感知的转移级信用分配及其在固定执行条件下的 future Skill use；memory、补丁版本拓扑和 PAOS lifecycle 是支撑该方法的实现结构。

## 18. 实施定界决策

进入 schema 或运行时设计前，先确定以下三项：

1. 核心物理 benchmark 选择哪两个，以及它们是否都能在不泄漏 privileged state 的前提下投影同一组 predicate/settlement 语义；
2. 第一批可控干预的 failure family 是什么，能否构造单一原因、并发原因和 delayed consequence；
3. 论文究竟主打 attribution accuracy，还是主打 future Skill utility。建议以前者为机制主指标、以后者为最终效果指标。

## 19. 论文方法章节

### 19.1 方法叙事

方法章节围绕一个因果链组织：PULSE 是结果记录，TRACE 是归因算法，Local Skill Patch 是更新动作，版本树和 candidate store 承载候选的历史与选择。

方法章节必须只保留一个主因果链：

```text
settled physical consequence
  -> uncertain transition credit assignment
  -> local patch proposal
  -> independent patch selection
  -> future Skill-use
```

TRACE 是方法核心；PULSE 与 Local Skill Patch 明确其输入和输出，版本树、异步反思与 PAOS promotion 在实现章节说明其承载职责。

### 19.2 可计算定义

论文以以下对象和计算规则定义方法：

1. **Transition state**：对第 `i` 条边定义 `x_i=(P_i^pre, A_i, P_i^post, U_i, C_i)`，其中 `P` 是谓词集合，`A` 是已执行的语义动作，`U` 是观测未知集合，`C` 是成本向量。
2. **Settlement window**：定义将后置谓词从 `pending` 结算为 `satisfied`、`violated` 或 `unknown` 的观测区间与终止条件。
3. **Attribution score**：给出边的排序函数，至少说明时间优先、证据覆盖、下游传播和 owner 可操作性如何组合；若权重由模型学习，必须在训练/验证集之外固定。
4. **Concurrent-cause set**：定义共同解释一个后果的多个边，并规定成员的独立支持计数、patch 生成和评测规则。
5. **Patch operator**：规定 expectation、observation、decision 与 recovery 四类 patch 的可修改字段和 authority 边界。
6. **Selection objective**：定义 patch utility，例如
   `U = heldout_gain - λ1*action_cost - λ2*time_cost - λ3*side_effect_rate - λ4*interference`，其中 λ 在适应前由协议固定。

这些定义使 PULSE、TRACE 与 patch utility 分别对应可复核的观测、归因和选择过程。

### 19.3 按可证伪职责组织方法模块

方法章节采用四个职责明确的模块：

| 模块 | 输入 | 输出 | 可证伪问题 |
|---|---|---|---|
| Outcome Logger | provider-visible execution facts 与预期结果 | PULSE/predicate settlement | 是否正确保留 delayed/unknown/side-effect 信息？ |
| TRACE Attributor | 有序 PULSE 链 | ranked edge/joint cause set | 是否比 last-error/trajectory reflection 更接近独立标签？ |
| Local Patch Synthesizer | attribution + applicability + cost | patch candidate | 是否只修改相关边且不泄漏实例细节？ |
| Patch Selector | candidate、匹配/留出/风险结果 | promote/hold/reject | 是否在收益、成本和干扰之间做可复现选择？ |

前三个模块位于 `evolution` extension。Patch Selector 使用独立的 matched、held-out 与 hazard 评测作出 `promote`、`hold` 或 `reject` 决定，从而将 patch synthesis 与 patch selection 分离。

### 19.4 论文应明确三个时间尺度

方法描述若不区分时间尺度，会导致“在线学习”与“离线评测”混淆：

1. **Execution time**：只产生临时恢复和事实记录，不写持久 Skill；
2. **Episode time**：计算 PULSE/TRACE 并生成 candidate；
3. **Evaluation time**：在独立 matched/held-out/hazard 集合上选择 promote/hold/reject，之后的新 episode 才可使用 promoted patch。

论文结果标注 patch 的生效时间点。适应 evidence 与冻结评测 episode 使用不重叠的样本集合。

### 19.5 方法主张的 claim ledger

在正式写作前建议冻结如下主张状态：

| 主张 | 类型 | 当前状态 | 允许写法 |
|---|---|---|---|
| PAOS 可记录任务级 episode 和 Skill candidate | capability/architecture | supported by code/docs | “系统提供……” |
| PULSE 能表达延迟结算、unknown 和副作用 | mechanistic | implemented, evaluation pending | “实现支持……”，不写识别准确率 |
| TRACE 能输出 ranked transition、joint cause set 与 unknown | mechanistic | implemented, evaluation pending | “实现计算……”，不写归因优于基线 |
| TRACE 比 trajectory-level reflection 更准 | comparative/mechanistic | planned | 以独立标注和消融报告结果 |
| Local Skill Patch 区分四类修改表面并隔离候选 identity | mechanistic | implemented, evaluation pending | “实现生成结构化候选……”，不写改善效果 |
| Patch Selector 计算前后收益、成本、副作用与干扰 | mechanistic | implemented, evaluation pending | “实现按固定权重计算……”，不写策略有效性 |
| 局部 patch 改善 held-out future Skill use | comparative/generalization | planned | 以冻结测试与重复 trial 报告结果 |
| PULSE 跨 provider 复用 | generalization | planned | 以两个独立 provider 的统一协议报告结果 |
| 方法减少错误持久更新 | safety | planned | 以 hazard、执行边界和独立安全 evidence 报告结果 |

当前代码已实现 projection、PULSE、TRACE、结构化 patch、独立选择与 Future Skill Use 差值计算，并由 fake-facts 测试验证机械行为。fake-facts 不构成归因准确率、跨 provider 泛化、future-task utility 或安全收益证据；结果章节只在受控实验产生独立 artifact 后报告这些比较结论。

## 20. 对比与消融实验角度的再次审核

### 20.1 匹配信息与预算的机制消融

机制消融在相同信息量与预算下比较 PULSE、TRACE 和 patch generation 的作用。每个变体匹配：

- 相同的 provider-visible observation；
- 相同的模型调用次数和最大 token；
- 相同的任务顺序、初始 Skill 和 reset；
- 相同的 patch 生效时机；
- 相同的 evaluator 与 promotion 规则。

不使用 outcome window 或 joint cause set 的变体保留等 token 占位输入，从而将信息量与机制贡献分开估计。

### 20.2 推荐一个 2×2 核心因子设计

主实验可以用两个正交因素建立最小可解释矩阵：

| 因素 | 水平 0 | 水平 1 |
|---|---|---|
| Credit assignment | trajectory-level / last-error | transition-level TRACE |
| Outcome state | terminal verdict only | PULSE with outcome window + unknown |

四个 cell 为：

1. terminal + trajectory（最接近传统 reflection baseline）；
2. terminal + transition（检验仅改变 attribution 是否有效）；
3. PULSE + trajectory（检验仅增加结果记录是否有效）；
4. PULSE + TRACE（完整方法）。

这个设计比“完整方法 vs 一个 baseline”更能回答：增益来自后果表征、信用分配，还是两者的交互。需要报告 interaction effect，而不只是四个独立均值。

### 20.3 必须加入的机制消融

| 消融 | 预期检验 |
|---|---|
| no outcome window | 延迟结果是否需要结算过程 |
| force top-1 instead of causal set | 并发原因建模是否减少误修复 |
| treat unknown as violated | 未观测是否导致错误持久更新 |
| last failure edge | first divergence 的时间定位是否有增益 |
| random edge | 不是任意边修改都能获得收益 |
| no side-effect field | 暂时成功但留下后果债务是否被遗漏 |
| no cost term | 成功率提升是否靠额外动作/时间换来 |
| whole-Skill rewrite | 局部 patch 是否减少 interference/forgetting |
| no applicability boundary | patch 是否在非匹配任务误触发 |
| oracle attribution | 方法距离可达到的上限还有多远 |

并发原因和 unknown 不能只做文字案例。至少要有受控单干预、双干预和观测缺失三类 episode，并将其分别计入 causal-set precision/recall、错误 patch 率和 hold/reject 率。

### 20.4 按同一更新预算组织 SOTA 对比

SOTA 对比固定基础模型、Harness、provider、任务流与更新预算，并报告以下三种表：

1. **Protocol table**：各方法是否支持跨 episode memory、Skill update、held-out freeze、state reset、cost accounting；
2. **Mechanism table**：同一基础模型/Harness 下，四个 2×2 cell 和各消融的 attribution/consequence 指标；
3. **Outcome table**：与代表性 RSI baseline 在相同任务流、调用预算和测试冻结条件下的 future-task utility。

每个结果报告多 seed 或多任务顺序的均值、置信区间、有效 episode 数以及失败、中断和排除原因。

### 20.5 错误更新分析

错误更新矩阵将真实偏离 owner 与方法修改 owner 对齐，直接衡量 Skill evolution 的归因质量：

```text
真实偏离 owner  ×  方法修改 owner
planner           -> planner / wrong-skill / reject
execution         -> execution / wrong-skill / reject
perception        -> perception / wrong-skill / reject
environment       -> environment / wrong-skill / reject
```

核心报告量包括 `wrong-skill update rate`、`unnecessary-patch rate`、`rejected-when-learnable rate`，以及错误 patch 在后续任务造成的 side-effect 增量。该矩阵与 task success、成本和 future Skill use 共同构成更新质量判断。

### 20.6 结果叙事顺序

结果章节按机制到结果的顺序展开：

1. TRACE 在受控干预上的定位质量；
2. PULSE 对 delayed/unknown/side-effect 的识别质量；
3. patch 在 matched task 上的后果改善与成本；
4. held-out future Skill-use 和跨任务 transfer；
5. hazard/non-target 任务上的错误更新和干扰；
6. 真实机器人小规模复核及其与仿真结果的差异。

该顺序将定位与后果表征证据连接到后续 Skill 使用结果。

## 21. 论文实现优先级

1. 以“TRACE 降低 transition attribution error，并在固定成本下改善 Future Skill Use”作为核心机制假设。
2. 采用 PULSE 最小四元组 `expected_effect, settled_observation, evidence_coverage, cost`；将 `side_effects`、`reversibility` 和 `owner_hypotheses` 作为证据充分时的扩展字段。
3. 将 TRACE 输出固定为 ranked edge、joint cause set 与 `unknown`，并用结构化字段取代自由文本 explanation。
4. 将 patch synthesis 与 patch selection 分离：前者生成候选，后者由独立 matched、held-out 与 hazard 评测决定。
5. 首篇论文以两个 provider 的共享 predicate/settlement 语义检验可复用性；跨 embodiment 的物理规律迁移进入后续研究阶段。
6. 先完成 2×2 因子、oracle 上限和错误更新矩阵，再根据实测的候选分支需求引入 patch version tree 或 sparse graph。

## 22. 当前论文级结论

- **方法核心**：TRACE 是算法性贡献；PULSE 与 Local Skill Patch 分别定义输入与输出，memory、版本树和 PAOS lifecycle 提供实现承载。
- **实验设计**：固定模型、Harness 与 provider，使用 2×2 因子、oracle、错误更新矩阵、matched/held-out/hazard 和成本核算评估方法。
- **证据状态**：方法的机械能力已实现并通过 fake-facts 测试；全部比较效果仍处于 `evaluation pending`，在独立标注、冻结评测和两个 provider 的 artifact 产生后报告。
- **最小可发表单元**：一个可计算的 TRACE、一个局部 Patch Selector，以及至少两个 provider 上的受控干预和跨任务留出评测。独立 TRACE 标签决定论文主张是信用分配方法，还是结果记录与经验更新框架。
