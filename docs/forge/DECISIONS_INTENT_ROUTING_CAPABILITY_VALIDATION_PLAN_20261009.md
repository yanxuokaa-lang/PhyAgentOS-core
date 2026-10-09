# Decisions API：会话入口意图与路由的独立能力验证方案

日期：2026-10-09。状态：方案已写，样本集、runner 与付费 API 实验尚未实施。
诊断依据：[入口路由诊断](DECISIONS_INTENT_ROUTING_DIAGNOSIS_20261009.md)。
目标模型：用户将提供的 GPT-6 Luna Decisions API；具体 endpoint 与访问能力以届时提供的信息为准。

## 1. 要回答的问题

这次验证回答：给定用户消息、相关短对话和当前任务状态，Decisions API 能否正确识别
意图，并判断应进入简单处理、澄清回答、普通对话或复杂理解路径。

只评估分类与路由建议。现有 PAOS 方案不被替换，实验不注册 provider、不调用 AgentLoop、
Coordinator 控制方法、Skill activation、Gateway、Runtime 或任何真实 handler。
路由中的 `task_control` 仅是记录下来的标签。

当前阶段不比较 GPT、Jev、Laya，也不生成新计划、抽取任意参数或执行任务。
用人工标签验证 Decisions 本身，减少额外模型调用与解释成本。

## 2. 最小实验形态

```text
本地标注样本：消息 + 相关对话 + 任务状态
  → 独立请求构造器：只取输入字段
  → Decisions API：intent 和 route 两个独立 choice 问题
  → 保存原始 answers、耗时与用量
  → 本地比较人工标签，生成统计与错误清单
```

每条样本一请求；两个问题都直接依据同一输入，不依赖对方答案。
官方文档要求依赖前一答案的判断分开请求，本方案不假设请求内存在顺序推理。
暂不加 complexity score：最小实验先看直接 route 是否能把复杂问题送入 System 2。

## 3. 输入与标签

每条样本包含以下普通 JSON 字段。标签存本地，构造 API input 时不发送它们。

| 字段 | 内容 |
| --- | --- |
| `case_id`、`family_id`、`split` | 样本主键、语义家族、development/evaluation |
| `message` | 最新用户原话 |
| `recent_turns` | 仅与当前指代或澄清有关的短对话 |
| `task_state` | 有无当前任务、status、简短目标、待回答问题、暂停标志 |
| `available_handlers` | 此场景真实提供的处理能力；常规回退路径也列出 |
| `gold_intent`、`gold_route` | 人工意图与处理路径标签 |
| `gold_reason`、`tags` | 标注理由与状态/否定/引用/多意图等标签，仅供评估 |

状态用手工构造的 PAOS 场景先行验证，不访问活动任务数据库。
后续若加入真实消息，只导出用户明确选定的脱敏只读记录，并单独报告其来源与结果。
人工补写的状态标为 synthetic，不当成现场观测。

### 3.1 intent：七个类别

| 值 | 含义 |
| --- | --- |
| `status_query` | 查询当前任务进度、状态或结果 |
| `task_control` | 明确要求控制当前任务，如暂停、恢复、停止 |
| `clarification_answer` | 回答当前明确的待回答问题 |
| `new_task` | 提出新的执行目标或任务要求 |
| `analysis` | 解释、比较、诊断、讨论或计划分析 |
| `conversation` | 问候与简单对话，不请求执行任务 |
| `mixed_or_unclear` | 多个独立意图，或当前信息不足以确定意图 |

意图表示用户要求，未必表示当前能处理。例如用户明确要求恢复任务，即使没有活动任务，
也可能属于 task_control；因恢复对象缺失，route 应升级处理。

### 3.2 route：五个处理路径

| 值 | 选择条件 |
| --- | --- |
| `status_read` | 确定在查询当前任务，且状态可由已有读取能力提供 |
| `task_control` | 要求明确、当前控制对象确定，场景提供相应控制能力 |
| `clarification_reply` | 当前有待回答问题，消息确实在回答该问题 |
| `conversation` | 简单对话，不需要处理任务或复杂理解 |
| `system2` | 新目标、复杂分析、多意图、语义歧义、缺少控制对象或没有匹配处理路径 |

`system2` 是后续复杂理解/澄清入口；实验仅记录标签，不调用 GPT。
这五类是实验中的语义路径，不声明 PAOS 已有同名 handler。
`available_handlers` 用能力描述列明状态读取、暂停、恢复等具体条件；选择 task_control
仍须符合具体控制需求，不能因“有停止能力”就把暂停请求视为可直接处理。

多意图样本暂归 system2，用来发现单路由的表达边界。包含明确停止要求的混合消息仍单独
报告其控制意图；这一实验分类约定不作为未来在线延迟或忽略用户停止要求的依据。

## 4. 样本规模与覆盖

建议第一轮 80 条：20 条 development 用于修正题目与类别定义，60 条 evaluation 用于
独立报告。中文为主；本轮结论限于会话入口文字输入。

| 场景家族 | Development | Evaluation | 合计 |
| --- | ---: | ---: | ---: |
| 状态查询与无活动任务 | 4 | 12 | 16 |
| 暂停/恢复/停止与否定、引用 | 4 | 12 | 16 |
| 等待澄清与同句不同状态 | 4 | 12 | 16 |
| 新目标与请求分析的区别 | 3 | 9 | 12 |
| 复杂理解、多意图和指代歧义 | 2 | 8 | 10 |
| 普通对话与未匹配请求 | 3 | 7 | 10 |
| 合计 | 20 | 60 | 80 |

表按场景分组，不强求每个 intent 数量相同。每个标签在 evaluation 中应有可报告的样本；
支持数写入指标，避免只给总体准确率。

同义改写、同一句不同状态、否定/引用变体共用 family_id，整组进入同一 split。
不能把“暂停一下”放 development，再把“先暂停一下”当独立 evaluation。
development/evaluation 的区别是用途，不需要新增哈希、冻结机制或发布 gate。

### 4.1 应包含的关键对照

| 消息 | 状态/相关上下文 | 预期路径 |
| --- | --- | --- |
| “继续” | 有明确已暂停任务，提供 resume | task_control |
| “继续” | 没有当前任务，也无相关历史 | system2 |
| “红色那个” | 正在问“选红色还是蓝色目标？” | clarification_reply |
| “红色那个” | 当前无澄清问题，指代对象不明 | system2 |
| “现在做到哪一步？” | waiting_for_user，但消息没有回答待回答问题 | status_read |
| “不要停，查一下进度” | 有任务与状态读取能力 | status_read |
| “文档里的‘停止任务’是什么意思？” | 在讨论文档 | system2 |
| “把这些东西分类放好” | 新执行目标 | system2；intent=new_task |
| “分析一下怎么分类比较合理” | 请求分析 | system2；intent=analysis |

“不要停，查一下进度”的负面约束是对当前行为的限制，不按两个待执行正向操作标为 mixed。
真正的两个正向要求，如“停止任务并分析原因”，按 mixed_or_unclear/system2 单独报告。
无法一致标注的样本先在 development 澄清类别；evaluation 的争议记录单列，不能挑选
最符合模型输出的标签。

## 5. API 请求约定与连通检查

公开 OpenAI 协议为 `POST /v1/decisions`，model 为 `gpt-6-luna`，questions 为命名数组。
若用户提供代理服务，先确认完整 endpoint、鉴权方式、模型名与 questions/answers 协议；
按实际协议处理，不假设 OpenAI-compatible chat endpoint 就支持 Decisions。

建议题目 wording：

- intent：依据最新用户消息和相关上下文识别意图；区分操作请求与否定、引用、讨论。
- route：依据原始消息、当前 task_state 和 available_handlers 直接选处理路径；需要新目标
  理解、分析、缺少对象或无法明确匹配时选 system2；不要执行任何操作。

选项含义采用上面两张表，两个问题分别给完整描述。route 不引用 intent 的返回值。

以下是后续连通检查的两题请求示例；完整评估使用相同题型并逐条替换 input。

```json
{
  "model": "gpt-6-luna",
  "input": "最新用户消息：现在做到哪一步了？\n当前任务：存在，状态 executing，目标为物品分类。\n当前可用处理能力：读取当前任务状态；复杂理解；普通对话。\n待回答问题：无。",
  "questions": [
    {
      "type": "choice",
      "name": "intent",
      "instructions": "依据最新用户消息和相关上下文识别用户意图，区分操作请求与否定、引用、讨论。多个独立意图或无法确定时选 mixed_or_unclear。",
      "choices": [
        {"value": "status_query", "description": "查询当前任务进度、状态或结果。"},
        {"value": "task_control", "description": "明确要求暂停、恢复或停止当前任务等控制。"},
        {"value": "clarification_answer", "description": "回答当前明确的待回答问题。"},
        {"value": "new_task", "description": "提出新的执行目标或任务要求。"},
        {"value": "analysis", "description": "请求解释、比较、诊断、讨论或计划分析。"},
        {"value": "conversation", "description": "问候与简单对话，不请求执行任务。"},
        {"value": "mixed_or_unclear", "description": "多个独立意图或信息不足以确定意图。"}
      ]
    },
    {
      "type": "choice",
      "name": "route",
      "instructions": "根据用户消息、当前状态和可用处理能力选择处理路径。需要新目标理解、分析、缺少对象或无法明确匹配时选 system2。只判断，不执行操作。",
      "choices": [
        {"value": "status_read", "description": "查询当前任务，已有读取能力能提供状态。"},
        {"value": "task_control", "description": "明确控制当前任务，且对象和所需控制能力都可用。"},
        {"value": "clarification_reply", "description": "当前有待回答问题，用户消息在回答该问题。"},
        {"value": "conversation", "description": "简单对话，不处理任务或复杂问题。"},
        {"value": "system2", "description": "复杂理解、新任务、分析、多意图、歧义或缺少必要对象。"}
      ]
    }
  ]
}
```

后续实施时，将该 JSON 保存为独立实验的 smoke-request.json；由操作者设置完整 endpoint
和 API key，再运行以下命令。该文件与环境变量本轮尚未创建。

```bash
curl --silent --show-error --fail-with-body \
  --request POST "$DECISIONS_API_URL" \
  --header "Authorization: Bearer $DECISIONS_API_KEY" \
  --header "Content-Type: application/json" \
  --data-binary @smoke-request.json
```

API key 仅用于请求鉴权，不进入样本、config、request/response 日志或 Git。
可用标准 HTTP 调用完成验证，当前项目无需升级 openai 依赖；若采用 SDK，应满足官方
文档要求的 Python openai 3.26.0 或更新版本，并置于独立实验环境。

## 6. 分阶段执行

### A. 准备与标注

建立 80 条样本，人工先标注，记录规则与歧义。样本审阅由用户或指定审阅者进行；模型
输出不作为人工标签来源。先检查输入字段与标签隔离、家族分组和数量。

请求构造只序列化 message/recent_turns/task_state/available_handlers。
工具描述、历史消息和用户文本均为待分析数据，不能覆盖 route instructions。

### B. 连通与 development

从 development 中选 5 条做最小连通检查，再补齐剩余 15 条。
检查 named answers、choice、概率、confidence、refusal/HTTP error 和实际用量。
请求已经覆盖的 5 条无需为了凑满 20 再调用一遍。

仅在 development 修正题目、选项描述与输入表达。最后使用的 wording 记录为一个普通
prompt_version；若修订，使用新版本并明确哪些 development 结果来自旧版本。
进入 evaluation 前，该版本至少完整覆盖 20 条 development 样本。

### C. 独立 evaluation

按最终题目对 60 条 evaluation 每条调用一次，顺序调用便于测单请求耗时；使用固定样本
顺序，记录 request index。evaluation 标签只进入本地 scorer。

测试结果揭示问题后保存错误分析。本次 evaluation 不用于改提示词后继续声称独立测试；
修改后作为新实验，后续另备未用于修改的样本。

### D. 状态利用与稳定性补充

基础结果可解释后，从 evaluation 中选择预先按 family_id 指定的 10 条，将 task_state
和与它绑定的历史/待回答问题移除，比较与完整输入的答案差异；该结果是信息消融，不
直接评价模型在缺少事实时“应该猜对”原标签。重点看是否转为 system2。

另选 10 条明确/歧义样本，各额外调用 2 次，比较三次答案一致性。
这 30 次额外请求单独报告，不混入基础 60 条准确率。
如果基础表现已经显示类别不清或输入不足，先分析原因，暂不追加调用。

## 7. 记录与统计

原始预测和后处理结果分开保存。第一次有效 answers 用于基础统计；不因为预测错误
重试。refusal、timeout、HTTP failure 独立计数；可恢复 transport 重试记录每次 attempt，
其总耗时计入端到端耗时。

| 指标 | 含义 |
| --- | --- |
| intent accuracy / macro-F1 | 七类意图是否正确，逐类支持数与混淆矩阵 |
| route accuracy / macro-F1 | 五类路径是否正确；同时给有效应答条件下与全部请求口径 |
| intent+route joint accuracy | 同一样本两个结果均符合标签 |
| control false positive | 未请求控制却预测 task_control，重点列否定与引用错误 |
| clarification confusion | waiting_for_user 场景把查询/控制/新请求误作澄清回答 |
| System 2 miss / excess | 应升级却走简单路径；可简单处理却全部升级 |
| unavailable-handler selection | 标签指向当前场景不提供的具体处理能力 |
| confidence 与正确性 | 正确/错误预测的 confidence 分布和带支持数的粗分箱 |
| p50 / p95 latency、用量与费用 | 实际 endpoint 的请求耗时、usage 与当前计费 |
| API availability | 有效两题应答率、refusal/error 数量与类型 |

80 条主要验证可行性，60 条 evaluation 的总体统计不能证明线上可靠性。
报告实际分子/分母和全部错误，避免用稀疏分箱声称已经完成概率校准。

confidence 与 options probabilities 分开记录。OpenAI 官方文档没有给出可直接复制的
通用校准保证；Jev/Laya 的字段含义与阈值也不能照搬。
可在 development 选择一个升级阈值，在 evaluation 额外报告覆盖率/覆盖部分准确率；
没有足够 development 证据时只报告分布，不强行设置阈值。
阈值处理的分数另列，不能掩盖原始路由错误。

本轮没有正式上线验收门槛。供人工评估的重点是：能否区分关键类别、是否利用状态、
是否发生明显控制误判，以及 system2 回退是否吞掉几乎所有简单请求。

## 8. 结果文件与可复查性

后续实现建议使用独立目录 `research/decision-api-intent-probe/`，只新增实验文件；
每次输出到唯一时间目录 `out/decision-api-intent-probe/<timestamp>/`。
本轮只写方案，这些目录中的 runner、数据与报告尚未创建。

```text
samples.jsonl       全部样本、人工标签、family_id 与 split
questions.json     两题完整定义和选项描述
config.json        实际 endpoint、model、prompt/dataset 版本、split IDs、调用设置
requests.jsonl     精确输入、请求序号、case_id；不含鉴权 header
responses.jsonl    原始 answers/usage、attempt 状态和耗时；不含密钥
predictions.jsonl  提取的 intent/route、分布与 confidence
metrics.json       指标、支持数、混淆矩阵与统计口径
errors.md          错误样本、人工理由与错误类型
report.md          能力结论、费用、局限与后续选择
```

config 记录源码 commit、实验文件版本、数据来源、模型实际标识、HTTP/SDK 版本、日期、
调用顺序、超时与重试设置；若进行了随机分组，记录 seed，否则注明按 family_id 人工分组。
模型没有暴露 seed 或 checkpoint 时注明 unavailable，不给接口添加未支持参数。

复查使用同一版本 samples/questions 和相同 case IDs，对比预测与错误清单。
API beta、服务端模型更新、网络延迟及重复调用差异是主要漂移来源；旧输出不覆盖。

## 9. 请求量、费用与失败分叉

无题目修订时，基础为 20 development + 60 evaluation = 80 请求，正式两题合计 160 个
问题；最初 5 条连通检查计入 development 的 20 条。
选做消融 10 请求与重复 20 请求后，共 110 请求。
development 修订、最终版本重测和 transport 重试另计，报告实际请求量。

OpenAI 公共价格为 $0.10 / 1M 输入 tokens。若实际每请求计费约 1,000 tokens，80 请求
估算为 $0.008，110 请求约 $0.011；这是按 token 假设估算，实际费用读 usage 与账单，
代理服务及区域/长上下文额外费用按提供方计费。

| 发现 | 下一步 |
| --- | --- |
| 401/403 | 核对密钥与 Decisions 权限；不把访问失败记成分类能力差 |
| 404/不识别 questions | 核对是否真正支持 Decisions endpoint，停止套用 chat 协议 |
| 429/timeout | 记录失败与重试；降低调用频率，区分网络与模型质量 |
| 同意图不同状态全部同路由 | 检查状态是否实际进入 input、题目是否明确引用状态 |
| 否定/引用频繁误作控制 | 查看原始消息与选项描述，归为控制语义识别不足 |
| 全部送 system2 | 检查简单路径条件是否清楚；报告低简单路径覆盖率 |
| intent 正确但 route 错 | 检查 available_handlers 与状态关系，归为路由而非意图错误 |
| 人工标签本身存在争议 | 保留争议，修正下一版分类规则，勿按模型答案重写测试标签 |

## 10. 本轮与后续交付

本轮保存诊断与这份方案，未调用 API、生成完整样本集或编写 runner。
用户提供 endpoint/访问方式后，可按上述步骤另行实现独立实验，先给出 Decisions 本身
的能力报告，再决定是否值得讨论与 PAOS 集成。当前系统无需为实验变更。

API 依据：[Decisions 官方文档](https://developers.openai.com/api/docs/guides/decisions)。
