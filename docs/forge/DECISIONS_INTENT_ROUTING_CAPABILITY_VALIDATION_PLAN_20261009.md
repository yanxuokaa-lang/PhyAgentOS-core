# Decisions API：会话入口意图与路由的独立能力验证方案

日期：2026-10-09。状态：独立 runner 与 80 条合成样本已实现；Laya 三 checkpoint 和 Jev 已完成
development/evaluation，GPT-6 Luna Decisions 尚未在有效 endpoint 上执行。
诊断依据：[入口路由诊断](DECISIONS_INTENT_ROUTING_DIAGNOSIS_20261009.md)。
目标模型：用户将提供的 GPT-6 Luna Decisions API；具体 endpoint、鉴权和响应协议以实际提供信息为准。

## 1. 验证问题与结论边界

本实验回答一个问题：给定用户消息、相关短对话和固定结构的当前任务状态，Decisions API
能否正确识别用户意图，并判断应进入状态读取、任务控制、澄清回答、普通对话或 System 2。

实验只评估预测。现有 PAOS 入口、AgentLoop、Coordinator、Skill、Gateway、Runtime 和
handler 保持原状；任何 route 都只写入结果文件，不执行任务、控制、澄清、工具调用或模型
回退。实验成功只说明该模型在本数据定义下具有候选路由能力，不授权接入或替换现有链路。

初始方案不比较 GPT、Jev、Laya；v13.0.12 扩展为使用同一数据集、输入投影、标签与 scorer 的
三后端独立对比。实验仍不生成计划、抽取执行参数或测试线上节省。结果必须同时报告
准确性、简单路径覆盖、System 2 回退比例、状态利用、稳定性和 API 可用性，避免“全部送
System 2”被误读为安全且有效的路由。

## 2. 最小实验架构与所有权

```text
人工标注样本
  message + recent_turns + capability_state
        │
        ▼
standalone request builder ──► Decisions backend adapter ──► endpoint
        │                              │
        │                              └─ raw request/response/attempt metadata
        ▼
local scorer
  ├─ intent/route metrics
  ├─ compatibility/state checks（只报告，不改答案）
  └─ errors/report
```

| 组件 | 拥有的职责 | 明确不拥有 |
| --- | --- | --- |
| dataset | 原始输入、人工标签、split、family 与标注理由 | 模型输出、运行时状态 |
| request builder | 固定序列化输入和两题定义 | PAOS 会话读取、handler 执行 |
| backend adapter | HTTP/SDK 调用、响应原样保存、provider 字段归一化 | 标签解释、重写预测 |
| scorer | 标签对比、兼容性与指标计算 | API 重试、自动修复模型答案 |
| operator | 提供 endpoint/key、启动实验、审阅报告 | 用模型结果回改 evaluation 标签 |

standalone runner 不导入 `PhyAgentOS.agent`、Coordinator、Gateway、Runtime 或 PAOS 写连接。
它只读取实验目录内的样本/config，并只向配置的 Decisions endpoint 发出请求。

## 3. 输入、状态与标签契约

### 3.1 数据集字段

每条 JSONL 样本包含：

| 字段 | 内容 | 是否发送给 API |
| --- | --- | --- |
| `case_id`、`family_id`、`split` | 样本主键、语义家族、development/evaluation | 否 |
| `message` | 最新用户原话 | 是 |
| `recent_turns` | 仅保留当前指代或澄清所需的短对话 | 是 |
| `capability_state` | 固定 schema 的任务与可用能力状态 | 是 |
| `gold_intent`、`gold_route` | 人工单值标签 | 否 |
| `gold_control_operations` | pause/resume/stop 的人工标注数组，无正向控制要求时为空；混合消息也标 | 否 |
| `gold_reason`、`tags` | 标注理由与状态/否定/引用/多意图标签 | 否 |
| `annotation_status` | drafted/reviewed/adjudicated | 否 |
| `source_kind` | synthetic 或 selected_redacted_real | 否 |

`gold_*`、标注理由、split 名称和 `annotation_status` 不得进入 API input。请求构造测试必须验证
这一点；程序状态检查也不能覆盖或掩盖模型原始错误。

### 3.2 provider-neutral `capability_state`

移除逐样本自由编写的 `available_handlers`。若描述按预期答案写成“该请求应交复杂理解”，
会把标签写进输入；固定的全量候选说明本身不构成泄漏。所有 provider 使用同一事实结构：

```json
{
  "has_current_task": true,
  "task_ref": "synthetic:task:0001",
  "task_status": "paused",
  "task_goal_summary": "整理桌面物品",
  "pending_clarification": {
    "present": false,
    "question_summary": null
  },
  "capabilities": {
    "read_status": true,
    "pause": false,
    "resume": true,
    "stop": true
  }
}
```

字段不描述“应该进入哪条路径”。固定约束如下：

- 本实验的 `has_current_task` 表示会话有确定的当前关联任务，包括可查询的终态任务，不表示
  该任务正在执行。未来 adapter 应从会话关联投影，不直接复制 PAOS active lifecycle 字段。
- `has_current_task=false` 时，`task_ref=null`、`task_status=none`，四项 task capability 为 false，
  pending clarification 为 false。终态任务仅可按场景提供 read_status，控制能力全部为 false。
- `pending_clarification.present=true` 时，`question_summary` 非空；本轮场景中 task status 为
  `waiting_for_user`。
- `task_ref` 只使用 `synthetic:` namespace；不引用当前 PAOS 数据库中的真实 task ID。
- `task_status` 只允许 `none/executing/paused/waiting_for_user/terminal`。
- capability 表示该场景是否具备具体能力，不表示用户是否请求它，也不提供 route 名称。
- `task_goal_summary` 只保留理解指代所需信息，不复制私有任务正文。
- state 先按场景事实编写，再标消息；同一场景中的控制请求、否定、引用与问候共享同一 state。
  不为使某条 gold 成立而按消息开关 capability；task_ref 为不含场景/route 词的普通合成编号。

状态 schema 与 route policy 作为普通版本化 JSON 配置保存，供 Luna、Laya、Jev 或后续 backend
复用；不为本实验增加 hash、冻结 contract 或发布 gate。

### 3.3 intent：七个类别

| 值 | 含义 |
| --- | --- |
| `status_query` | 查询当前任务进度、状态或结果 |
| `task_control` | 明确要求暂停、恢复或停止当前任务 |
| `clarification_answer` | 回答当前明确的待回答问题 |
| `new_task` | 提出新的执行目标或任务要求 |
| `analysis` | 请求解释、比较、诊断、讨论或计划分析 |
| `conversation` | 问候与简单对话，不请求执行任务 |
| `mixed_or_unclear` | 多个独立正向意图，或信息不足以确定意图 |

意图描述用户要求，不表示当前一定可处理。例如明确要求恢复但没有活动任务，intent 仍可为
`task_control`，route 应为 `system2`。否定、引用或解释一个操作词不自动形成控制意图。

### 3.4 route：五个语义路径

| 值 | 单值标注条件 |
| --- | --- |
| `status_read` | intent 为 status_query，且有当前任务和 read_status 能力 |
| `task_control` | intent 为 task_control，控制对象明确，且请求的具体 capability 可用 |
| `clarification_reply` | intent 为 clarification_answer，且存在当前待回答问题 |
| `conversation` | intent 为 conversation；该实验路径始终可用 |
| `system2` | 新任务、分析、多意图、歧义、缺少对象、能力不可用或其他无法直接匹配的情况 |

每条样本只有一个 `gold_route`。出现竞争路径时按以下顺序标注：

1. 明确 `/stop`、`/restart` 等现有确定性命令不进入本实验。
2. 两个独立正向要求标为 `mixed_or_unclear/system2`；否定约束不算第二个正向要求。
3. 单一 status/control/clarification 意图只有在对象和相应 capability 都满足时进入简单路径。
4. 简单问候进入 conversation；需要解释、知识分析或制定方案的对话进入 analysis/system2。
5. 仍无法单值标注的样本只留在 development；evaluation 前必须裁决或移除。

### 3.5 intent/route 兼容矩阵

两个 choice 问题仍独立读取同一输入，但 scorer 使用配置化矩阵报告矛盾：

| 预测 intent | 可兼容 route | 附加状态条件 |
| --- | --- | --- |
| `status_query` | `status_read`、`system2` | status_read 需要当前关联任务（包括可查询的 terminal task）+ read_status |
| `task_control` | `task_control`、`system2` | task_control 需要对应 operation capability |
| `clarification_answer` | `clarification_reply`、`system2` | clarification_reply 需要 pending clarification |
| `new_task` | `system2` | 无 |
| `analysis` | `system2` | 无 |
| `conversation` | `conversation` | 无 |
| `mixed_or_unclear` | `system2` | 无 |

兼容矩阵与 capability 约束分别计算。`intent=task_control, route=system2` 可以是正确组合，因为
控制对象或能力可能缺失；`route=task_control` 但对应 pause/resume/stop capability 为 false 则是
unsupported simple-route prediction。所有矛盾写入报告，原始答案不被程序改写。
对应 operations 从人工只读标注 `gold_control_operations` 获取，不从 intent/route 两题臆造。
未请求控制且数组为空时，route=task_control 计 control false positive；仅当所有控制能力均不可用
时同时计 unsupported。请求多项控制却选单一路由仍计混合意图错误；模型参数选择留给后续实验。

## 4. 样本、标注与 split

### 4.1 规模与场景覆盖

第一轮共 80 条：20 条 development 用于修正题目与类别定义，60 条 evaluation 用于独立
报告。中文为主，结论限于会话入口文字输入。

| 场景家族 | Development | Evaluation | 合计 |
| --- | ---: | ---: | ---: |
| 状态查询与无活动任务 | 4 | 12 | 16 |
| 暂停/恢复/停止与否定、引用 | 4 | 12 | 16 |
| 等待澄清与同句不同状态 | 4 | 12 | 16 |
| 新目标与请求分析的区别 | 3 | 9 | 12 |
| 复杂理解、多意图和指代歧义 | 2 | 8 | 10 |
| 普通对话与未匹配请求 | 3 | 7 | 10 |
| 合计 | 20 | 60 | 80 |

每个 intent 和 route 在 evaluation 中必须有支持数；若某类样本不足，报告实际支持数，不用
总体准确率替代逐类结果。同义改写、同一句不同状态、否定/引用变体共享 `family_id`，整个
family 进入同一 split，避免近重复泄漏。

### 4.2 标注与裁决

1. 主标注者按本方案给 80 条样本写标签与理由。
2. development 可在题目修改过程中同步修订，保留修订记录。
3. evaluation 由第二名审阅者在看不到模型输出时独立复核 intent、route 和 control operation。
4. 分歧在第一次 evaluation API 调用前裁决；记录初始一致数、分歧数、裁决结果和移除样本。
5. 模型输出不得用于修改本次 evaluation 标签；发现 taxonomy 问题时，结束当前 run，并在
   新 dataset version 中修订，另备未参与修改的 evaluation 样本。

80 条是可行性样本，不证明线上可靠性。标注一致性、支持数和全部错误必须与准确率一起报告。

### 4.3 关键对照

| 消息 | 状态/上下文 | gold intent / route |
| --- | --- | --- |
| “继续” | paused，resume=true | task_control / task_control |
| “继续” | 无当前任务，也无可解释其含义的历史 | mixed_or_unclear / system2 |
| “恢复当前任务” | 无当前任务 | task_control / system2 |
| “红色那个” | 正在问“选红色还是蓝色？” | clarification_answer / clarification_reply |
| “红色那个” | 无待回答问题，指代不明 | mixed_or_unclear / system2 |
| “现在做到哪一步？” | waiting_for_user，read_status=true | status_query / status_read |
| “不要停，查一下进度” | active，read_status=true | status_query / status_read |
| “文档里的‘停止任务’是什么意思？” | 讨论文档 | analysis / system2 |
| “把这些东西分类放好” | 新执行目标 | new_task / system2 |
| “分析一下怎么分类比较合理” | 请求分析 | analysis / system2 |
| “停止任务并分析原因” | active，stop=true | mixed_or_unclear / system2 |

## 5. Backend、API 与问题定义

### 5.1 provider-neutral config

每次 run 保存以下配置：

```json
{
  "decision_backend": "openai_decisions",
  "endpoint_kind": "openai_v1_decisions",
  "endpoint_host": "api.openai.com",
  "model_requested": "gpt-6-luna",
  "response_schema_version": "observed-at-smoke",
  "dataset_version": "intent-routing-v1",
  "prompt_version": "intent-route-v1",
  "route_policy_version": "route-policy-v1",
  "timeout_seconds": 30,
  "max_transport_retries": 2
}
```

`endpoint_host` 记录主机名，不保存完整密钥、鉴权 header 或含秘密的 URL query。若用户提供
代理或兼容服务，替换 backend adapter 与 endpoint_kind，保持 dataset、标签和 scorer 不变。
adapter 保存原始响应，再归一化 answer type、choice、probabilities、confidence、refusal 与 usage；
provider 未返回的字段记为 unavailable，不能伪造 OpenAI 字段或套用同一 confidence 语义。

### 5.2 OpenAI Decisions 官方协议

按 2026-10-09 官方文档，OpenAI Decisions 使用 `POST /v1/decisions`，请求包含 `model`、
共享 `input` 和命名 `questions`；choice 返回所选值、各选项 probabilities 与 confidence，
也可能返回 refusal。独立问题可放在同一 request；依赖前题答案的判断应拆成不同 request。
本实验的 intent 和 route 都直接读取原始输入，不依赖对方答案，因此保持一请求两题。

当前官方指南的图片示例使用 inline base64，而官方 OpenAPI `createDecision` 描述也列出公开
HTTP(S) 图片 URL；两处资料存在差异。本轮只发送文本 input，不把图片 URL 能力计入实验结论；
未来若扩展图片，必须先在 development smoke 中单独验证并记录实际协议，不能从任一处文档
推断另一处行为。

若实际服务与官方协议不同，先用 5 条 development smoke 记录真实 schema，再实现薄 adapter；
不得仅因 URL 或 chat 接口兼容就假定支持 Decisions。
完整请求 URL 从 `DECISIONS_API_URL` 环境变量读取并与 config 主机名对照，密钥从
`DECISIONS_API_KEY` 读取；两者不打印。默认要求 URL 使用 `https` 且路径为
`/v1/decisions`；兼容代理必须由 operator 明确选择 `endpoint_kind` 和 host，不能静默改发
到其他路径。初始 smoke 推荐使用标准 HTTP 客户端，避免项目 Python 3.11/3.12 环境误装
官方文档所列 Python 3.26.0+ SDK；若选 SDK，必须记录实际版本并确认其支持 Decisions。
SDK/HTTP 库自带 retry 关闭，由 runner 单独管理 attempts。
两题有效应答要求：intent/route 名称各恰好一次、type=choice、所选值属于各自选项。
若只有一题有效，保存该题并报告 per-question availability，基础 joint 有效口径视为无效；
refusal、缺题、重复题名、未知值和 schema failure 不自动重试。

### 5.3 两题请求示例

完整评估将同一结构稳定序列化为 input。示例中的 `capability_state` 没有 route 描述：

```json
{
  "model": "gpt-6-luna",
  "input": "{\"message\":\"现在做到哪一步了？\",\"recent_turns\":[],\"capability_state\":{\"has_current_task\":true,\"task_ref\":\"synthetic:task:0002\",\"task_status\":\"executing\",\"task_goal_summary\":\"整理物品\",\"pending_clarification\":{\"present\":false,\"question_summary\":null},\"capabilities\":{\"read_status\":true,\"pause\":true,\"resume\":false,\"stop\":true}}}",
  "questions": [
    {
      "type": "choice",
      "name": "intent",
      "instructions": "依据最新用户消息、相关短对话和任务状态识别用户意图。区分正向操作请求与否定、引用、讨论；多个独立正向意图或无法确定时选 mixed_or_unclear。",
      "choices": [
        {"value": "status_query", "description": "查询当前任务进度、状态或结果。"},
        {"value": "task_control", "description": "明确要求暂停、恢复或停止当前任务。"},
        {"value": "clarification_answer", "description": "回答当前明确的待回答问题。"},
        {"value": "new_task", "description": "提出新的执行目标或任务要求。"},
        {"value": "analysis", "description": "请求解释、比较、诊断、讨论或计划分析。"},
        {"value": "conversation", "description": "问候与简单对话，不请求执行任务。"},
        {"value": "mixed_or_unclear", "description": "多个独立正向意图或信息不足以确定意图。"}
      ]
    },
    {
      "type": "choice",
      "name": "route",
      "instructions": "根据原始消息、相关短对话和 capability_state 选择处理路径。只有对象明确且对应 capability 为 true 时选择简单状态、控制或澄清路径；新任务、分析、多意图、歧义、对象缺失或能力不可用时选择 system2。只判断，不执行操作。",
      "choices": [
        {"value": "status_read", "description": "查询当前关联任务（包括可查询的 terminal task），且 read_status 能力可用。"},
        {"value": "task_control", "description": "明确控制当前任务，且请求的具体控制能力可用。"},
        {"value": "clarification_reply", "description": "存在待回答问题，用户消息确实在回答该问题。"},
        {"value": "conversation", "description": "简单对话，不处理任务或复杂问题。"},
        {"value": "system2", "description": "新任务、分析、多意图、歧义、对象缺失或能力不可用。"}
      ]
    }
  ]
}
```

API key 只从环境变量读取，不进入样本、config、requests/responses 日志或 Git。标准 HTTP 足以
完成验证；若采用 SDK，使用官方文档要求的最低版本或更新版本，并记录实际 SDK 版本。

## 6. 分阶段执行

### A. 样本与静态校验

- 完成标注、独立复核和 evaluation 裁决。
- 校验 schema、state invariant、family split、类别支持数和 gold 字段不进入请求。
- 检查 synthetic task namespace、脱敏状态和无凭据文件。
- 保存 dataset/prompt/route-policy 的普通版本号和 runner commit。

### B. 五条 development smoke

从 development 选择覆盖五种 route 的 5 条样本，检查 endpoint、鉴权、两题命名、answer type、
choice、probabilities、confidence、refusal、usage、HTTP 状态和 provider request ID。smoke 使用的
5 条计入 development 20 条，不重复调用以凑数。
smoke 使用 phase=development，并在本地记录 smoke 标志；最终版本不变时剩余只跑 15 条。

若返回 schema 与预期不同，只修改 backend adapter；若题目或类别定义有问题，记录新
prompt_version。任何题目修订都只使用 development 结果。

### C. 完成 20 条 development

用候选最终 wording 覆盖全部 20 条 development，分析类别混淆和 confidence 分布。进入
evaluation 前记录最终 dataset/prompt/route-policy/backend config；旧 development 结果保留并
标明版本，不混入最终版本统计。

### D. 独立运行 60 条 evaluation

按固定 case 顺序，每条一个逻辑 request，两个问题同请求。evaluation 标签仅由本地 scorer
读取。运行后生成 metrics、全部错误与标注一致性报告；不能修改 prompt 后继续把同一 60 条
称为独立 evaluation。

### E. 选做状态消融与重复稳定性

- 预先按 family 指定 10 条 evaluation，移除 capability_state 与绑定的 recent turns，比较完整
  与消融输入。消融阶段使用缺少状态的输入变体，不填 false 冒充“无任务”，不参与基础 schema/
  capability 评分；问题指令明确“状态未知时不能确认任务简单路径”。消融不要求匹配原 gold，
  重点观察是否转向 system2。
- 预先选择 10 条明确/歧义样本，各额外调用 2 次，与基础调用组成三次预测，计算 route/intent
  不一致率和概率变化。
- 10 次消融和 20 次重复独立报告，不并入基础 60 条准确率。

## 7. 恢复、重试与幂等

一个样本在一个 phase 中只有一个逻辑预测：

| 字段 | 作用 |
| --- | --- |
| `run_id` | 唯一输出目录对应的实验运行 |
| `case_id` | 数据集样本身份 |
| `logical_request_id` | run + phase + case + repeat_index 的稳定请求身份；基础 repeat_index=0 |
| `attempt_index` | 从 0 开始的 transport 尝试序号 |

重试规则：

- 只对连接错误、timeout、HTTP 408/429/5xx 重试，最多额外 2 次，并遵守 `Retry-After`。
- HTTP 4xx（408/429 除外）、schema error、refusal 和有效但错误的预测不重试。
- timeout 可能意味着服务端已完成，但 API 调用无 PAOS 副作用；后续 attempt 仍属于同一个
  `logical_request_id`，不能作为第二个基础预测。
- 按 attempt_index 选择第一个完整且 schema-valid 的两题响应用于基础统计；所有 attempt 原样
  保留，总耗时计入端到端 latency。
- 进程恢复时，若同一 run/config/case 已有选中的有效响应则跳过；已耗尽重试的 terminal failure
  也不自动重跑。补测失败样本使用新的 supplemental run，不混入原基础指标。
- 预测错误永远不触发重试。旧输出目录不覆盖。

稳定 ID、普通版本号和完成状态已足以恢复实验；不新增 hash、冻结 baseline 或额外 gate。
一个 run 目录中的 config/题目/数据版本和精确输入不得被 resume 改写；版本改变使用新 run。
先写 request/attempt-start，再调用；收到响应先原子保存原始响应，再生成预测。崩溃后已有原始
响应则离线解析；只有 start 没有 response 时记 interrupted/unknown，并消耗一个 attempt，不猜成功。

## 8. 指标与收敛解释

### 8.1 主要指标

| 指标 | 含义 |
| --- | --- |
| intent accuracy / macro-F1 | 七类意图准确率、逐类支持数与混淆矩阵 |
| route accuracy / macro-F1 | 五类 route；分别报告全部逻辑请求与有效应答口径 |
| intent+route joint accuracy | 两个预测同时命中单值 gold |
| incompatible pair rate | 预测 intent/route 不符合兼容矩阵的比例 |
| unsupported simple-route rate | 预测简单路径但 capability_state 不支持的比例 |
| control false positive | 未请求控制却预测 task_control，重点列否定/引用 |
| clarification confusion | waiting_for_user 时把查询、控制或新请求误作 clarification_reply |
| System 2 miss / excess | 应升级却走简单路径；可简单处理却升级 |
| simple-path coverage / correctness | gold_route 非 system2 的样本中，预测也为非 system2 的比例；另报告这些简单预测的准确率 |
| System 2 route rate | 全部样本中 route=system2 的比例 |
| repeated-call instability | 同一输入三次 intent/route 不一致的样本比例 |
| state-ablation transition | 完整状态与消融状态的 route 转移矩阵 |
| probability quality | intent/route 分别报告 probability coverage、10-bin ECE、未缩放 multiclass Brier 与 NLL；评估校准表现，不等同于完成下游温度校准 |
| latency/usage/cost | p50/p95 端到端耗时、provider usage 与实际账单口径 |
| API availability | 两题有效应答率、refusal 与 transport/schema error |

`unsupported simple-route` 检查模型预测，不检查 gold 标签。例如 message 要求 resume、
`capabilities.resume=false`，模型仍预测 task_control 时计错；gold 应为 system2。
所有指标给分子/分母。单题 accuracy 的全量分母为该 split 全部逻辑样本，无效题计未命中；
条件 accuracy/macro-F1 仅用该题有效答案，joint 条件口径要求两题有效。all-request macro-F1
将缺失/refusal 作为真实类的 false negative，另报无效数，不伪造一个有效 route。
control false positive 同时报告 intent 与 route 两种口径，分母为无正向控制请求的样本；
System 2 miss 分母为 gold=system2，excess 分母为 gold!=system2。兼容性分母为两题均有效的
样本；unsupported 分母为有效简单路径预测。latency 报告有效请求与全量终态请求两种口径。
概率指标仅使用候选集完整、数值有限非负且总和为正的有效响应；先归一化 provider 四舍五入
误差。ECE 以最大候选概率及其 argmax 正确性计算，NLL 对零概率使用 `1e-12` 数值截断；每项均
报告 probability coverage，transport failure 不进入条件概率指标。

### 8.2 全部回退的诊断对照

以 gold=system2 支持数/60 计算“全部送 system2”会得到的 route accuracy，同时其 simple-path
coverage 必为 0。这是针对全量回退掩盖能力不足的普通算术对照，不建立冻结 baseline 或新增
门禁，也不增加 API 请求。

一个模型即使没有 System 2 miss，只要 simple-path coverage 接近 0 或 System 2 excess 很高，就
不能支持“可替换入口简单判断”的结论。兼容率高也不能替代逐类正确率。

### 8.3 结论等级

本轮不设生产上线阈值。报告按证据分为：

1. `invalid_or_inconclusive`：标注/split 泄漏、有效应答不足或 schema 无法稳定解析。
2. `capability_not_supported`：关键类别、状态对照或简单路径覆盖明显失败。
3. `promising_for_next_validation`：各关键类别有有效证据，状态对照和简单路径覆盖成立，且
   没有明显控制误判或不支持能力选择。

第三类也只允许设计下一轮 shadow/integration proposal，不授权改变 PAOS 路由。

## 9. 可观测性、结果文件与复查

实现目录为 `research/decision-api-intent-probe/`；每次输出到唯一目录
`out/decision-api-intent-probe/<timestamp>-<run_id>/`。当前已生成 80 条合成样本和本地 dry-run
输出；真实 API 输出需在提供 `DECISIONS_API_KEY` 后产生。

```text
samples.jsonl          样本、人工标签、family/split、标注状态
state-schema.json      capability_state schema 与 invariant
questions.json         两题定义和选项
route-policy.json      单值标注规则、兼容矩阵、状态约束
config.json            backend/model/endpoint host/版本/timeout/retry
environment.json       Python、SDK、runner commit、操作系统时间信息
requests.jsonl         logical_request_id、精确 input、case/order；无鉴权
attempts.jsonl         每次 transport attempt 的开始/结束、HTTP/error/latency
responses.jsonl        原始 provider 响应；无密钥
predictions.jsonl      归一化 intent/route/probabilities/confidence/refusal
metrics.json           指标、支持数、混淆矩阵、统计口径
errors.md              全部错误、人工理由与错误分类
report.md              能力结论、成本、限制与下一步
```

每次 attempt 至少记录：wall-clock start/end、monotonic duration、HTTP status、provider request
ID（若返回）、requested/reported model、answer type/name、raw probabilities、confidence、refusal、
usage、attempt count、exception category 和 endpoint host。错误分类区分：

- `annotation_disagreement`
- `state_insufficient_or_invalid`
- `intent_error`
- `route_error`
- `incompatible_pair`
- `unsupported_simple_route`
- `refusal`
- `transport_or_http_failure`
- `response_schema_failure`

environment 记录 Python/SDK 版本、runner commit、dataset/prompt/route-policy/backend schema 版本。
模型没有暴露 seed、checkpoint、usage 或 provider request ID 时记为 unavailable，不添加接口不支持
的参数。主要漂移来源是 beta API、服务端模型更新、provider adapter、网络和重复调用差异。

## 10. 实验安全与数据边界

- synthetic-first：基础 80 条全部可用 synthetic 场景完成，不访问活动任务数据库。
- 真实样本需用户明确选择、人工脱敏并标记 `selected_redacted_real`；凭据、个人信息、私有任务
  正文和真实 task ID 不进入数据或输出。
- runner 没有 PAOS database URL、workspace、Coordinator/Runtime/Gateway client 或 write-capable
  connector；实验配置只允许一个 Decisions endpoint host。
- route 结果不映射 handler，runner 中不存在 status/pause/resume/stop/clarification/AgentLoop 调用。
- input 中的用户文本、recent turns 和 tool-like 字符串均作为待分类数据，不能覆盖 questions。
- 失败时只记录 API/实验错误，不创建任务、恢复任务、暂停/停止任务或写 PAOS 状态。

这些是实验实现边界，不是新增生产运行时 gate。现有安全、权限、数据完整性和发布控制保持原状。

## 11. AgentLoop 自主性与未来集成原则

若能力结果值得进入下一轮，集成设计仍须满足：

1. 显式命令继续由现有确定性入口处理，不经过概率路由。
2. 每个入站 user turn 最多产生一次 Decisions 入口建议；除非外部状态发生可证明变化，否则
   不在同一回合反复调用 router。
3. route 是 proposal。它不能创建/绑定任务、回答澄清、pause/resume/stop、选择 Runtime、
   调用 Tool、提交 PlanGraph 或 finalize。
   包含正向停止要求的混合消息须保留停止语义；mixed/system2 的实验约定不授权在线延迟或忽略
   用户停止，未来需单独设计现有用户中断入口的优先处理。
4. System 2 接收原始 user message、relevant turns 和 capability_state；不能只收到 route 标签。
5. Decision → System 2 后不返回 Decision，避免 Decision↔System 2 递归；System 2 的现有
   AgentLoop 收敛、等待用户、取消和失败语义保持权威。
6. waiting_for_user 的现有行为本轮只被样本测量，不被实验改变。
7. confidence 只能参与后续 shadow 阶段的升级策略研究，不能绕过现有 owner 或扩大 tools。

## 12. 请求量、费用与失败分叉

基础逻辑请求为 20 development + 60 evaluation = 80；每个请求包含两题，共 160 个 answers
目标。最初 5 条 smoke 计入 development。选做 10 条消融与 20 次重复后，共 110 个逻辑请求。
题目修订、supplemental run 和 transport attempts 另计，报告逻辑请求数与实际 HTTP 次数。

按 2026-10-09 OpenAI 官方文档，`/v1/decisions` 的 GPT-6 Luna 只计输入 tokens，公开基准价
为每 100 万 input tokens 0.10 美元，区域处理和长上下文可能有额外倍率。方案只保存公式：

```text
estimated_cost = billed_input_tokens / 1_000_000 * effective_provider_rate
```

最终报告使用实际 endpoint 的 usage、provider rate 和账单；代理服务不套用 OpenAI 价格。

| 发现 | 下一步 |
| --- | --- |
| 401/403 | 核对密钥与 Decisions 权限；不计为分类能力错误 |
| 404/不识别 questions | 确认 endpoint_kind；停止套用 chat 协议 |
| 408/429/5xx/timeout | 按 transport policy 重试并保存 attempts |
| schema 与官方不同 | 保存原始响应，实现/修正薄 adapter，再重跑 development |
| 同一句不同状态仍同路由 | 检查 state 是否进入 input，再判断状态利用不足 |
| 否定/引用频繁误作控制 | 归为 control false positive，不靠规则静默修正 |
| 全部送 system2 | 报告 simple-path coverage 和全部回退的算术对照，不判定有替换价值 |
| intent 正确但 route 错 | 检查 capability/state 关系，归为 route error |
| intent/route 互相矛盾 | 归为 incompatible_pair，保留两个原始答案 |
| evaluation 标签争议 | 结束当前 run；修订新 dataset version，不按模型答案回写 |

## 13. runner CLI 契约

runner 已实现；提供以下可复查命令：

```bash
python -m decision_intent_probe validate \
  --config research/decision-api-intent-probe/config.json

python -m decision_intent_probe run \
  --config research/decision-api-intent-probe/config.json \
  --phase development --smoke

python -m decision_intent_probe run \
  --config research/decision-api-intent-probe/config.json \
  --phase evaluation

python -m decision_intent_probe score \
  --run-dir out/decision-api-intent-probe/<timestamp>-<run_id>

python -m decision_intent_probe compare \
  --left out/decision-api-intent-probe/<run-a> \
  --right out/decision-api-intent-probe/<run-b>
```

`validate` 只做 schema、split、标签隔离和安全边界检查；`run` 才调用 endpoint；`score` 与
`compare` 不访问网络。`--smoke` 选择前 5 条 development；同一 run 使用 `--resume` 完成剩余
development。smoke、development、evaluation 和 supplemental run 使用不同 phase/
run 记录（smoke 计入 development）；run 支持 `--resume <run-dir>`，只按原配置续跑未终态
请求，不覆盖旧输出。相同数据版本允许按 case ID 比较；数据版本不同只对公共 case ID 给配对
结果，并单列支持数与配置变化。

## 14. 本轮交付

本轮已实现独立样本、runner 和配置；完成 Laya 三 checkpoint 的 5 条 smoke、20 条 development
与 60 条 evaluation，并完成 Jev 20 条 development 与 60 条 evaluation。GPT-6 Luna Decisions
仍未调用。实验没有改变当前 PAOS 入口路由；能力报告通过人工审核后，才决定是否设计 shadow
验证。

API 依据：[OpenAI Decisions 官方文档](https://developers.openai.com/api/docs/guides/decisions)。

## 15. Laya 本地、Jev 远程与 Decisions 远程对比扩展

### 15.1 固定项与唯一变量

三路实验固定 `intent-routing-v1` 的 80 条样本、`build_input` 投影、七类 intent、五类 route、
gold 标签和离线 scorer。每条样本都同时回答 intent 与 route，route 只作为预测标签保存。唯一
主要变量是 backend 及其原生协议，不把一个 provider 的 confidence 语义强行映射成另一个。

| Backend | 部署与接口 | 本轮调用形态 | 可直接比较 | 单独报告 |
|---|---|---|---|---|
| Laya English | 本地 CUDA，root checkpoint | Python `agent.predict(state, questions)` | hard-label accuracy、延迟 | 中文跨语言压力测试 |
| Laya multilingual | 本地 CUDA，`multilingual/` | 同上 | hard-label accuracy、延迟 | 本地冷加载、显存、校准 |
| Laya typed-decisions | 本地 CUDA，`typed-decisions/` | 同上 | hard-label accuracy、延迟 | 域迁移与 checkpoint 专门化 |
| Jev | 远程 `POST /v1/systemone` | `state` + questions 对象 | hard-label accuracy、HTTP 延迟 | Jev probabilities/confidence、用量 |
| GPT-6 Luna Decisions | 远程 `POST /v1/decisions` | `input` + questions 数组 | hard-label accuracy、HTTP 延迟 | Decisions probabilities/confidence、用量 |

三路不得通过自动降级到 Chat Completions、Responses 或另一个模型来制造成功。Jev 与 Decisions
使用各自独立 adapter；endpoint/key 不进入数据集、仓库 config 或输出 artifact。

### 15.2 Laya 隔离与三个 checkpoint

Laya Python 包源码发布于 PyPI/GitHub，模型权重由 `convaiinnovations/laya` Hugging Face bundle
提供。本地运行使用 `/home/yanxu/laya-system1/.venv`，缓存固定为
`/home/yanxu/laya-system1/huggingface`，不复用 PAOS `.venv`。三个 checkpoint 必须分别核验：

1. root `english`；
2. `multilingual/`；
3. `typed-decisions/`。

每个 checkpoint 保存实际 revision、Laya/Torch 版本、Python executable、device、load time、逐例
latency、原始 answers 与概率。中文主实验优先解释 multilingual；English 与 typed-decisions 是
受控对照，不能因同仓库或同接口就声称语言适配相同。

### 15.3 Jev 远程协议

Jev 请求使用 `model=jev-latest`、序列化后的 provider-neutral state，以及以问题名为 key 的
choice questions；每题的有限候选写入 `criteria`。响应要求 `answers.intent.choice` 与
`answers.route.choice` 均属于请求候选集。服务返回的实际模型版本（例如 `jev-1.13.0`）、概率、
confidence、usage 和 HTTP latency 原样保存。401/403、schema failure 与分类错误分开统计。

### 15.4 执行顺序和判断门槛

1. 三个 Laya checkpoint 各跑 5 条 development smoke；检查合法输出、加载时间和明显塌缩。
2. Jev 跑同五条 smoke；仅在 endpoint/schema 通过后运行剩余 development。
3. GPT-6 Luna Decisions 仅在有效 `/v1/decisions` endpoint 可用后运行；已知
   `api.shuaiapi.com/v1/decisions` 返回 404，不作协议降级。
4. development 完成并冻结 prompt 后才运行 60 条 evaluation；任何后端单独失败，不阻止保存
   其他后端真实结果，也不以缺失值补齐排名。

这轮结论只回答“结构化 System 1 模型对入口 intent/route 是否有离线判别能力”。即便某一路
优于当前基线，也只能进入后续 shadow 设计，不能直接替换 PAOS 入口、AgentLoop、Coordinator、
Runtime 或 handler。

### 15.5 实测结果

| Backend / checkpoint | Phase | Cases | Coverage | Intent | Route | Joint | Mean successful latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Laya English | evaluation | 60 | 1.00 | 0.70 | 0.333 | 0.25 | 0.055 s |
| Laya multilingual | evaluation | 60 | 1.00 | 0.75 | 0.483 | 0.383 | 0.034 s |
| Laya typed-decisions | evaluation | 60 | 1.00 | 0.65 | 0.45 | 0.417 | 0.061 s |
| Jev `jev-1.13.0` | evaluation | 60 | 0.90 | 1.00 | 0.944 | 0.944 | 1.351 s |
| GPT-6 Luna Decisions | evaluation | 0 | unavailable | unavailable | unavailable | unavailable | unavailable |

Laya 三路均完成同一 20 条 development 和同一 60 条 evaluation，配置未在 checkpoint 之间变化。
Multilingual 的 intent/route 单项最高，typed-decisions 的 joint 最高；三者 route 均低于 0.50。
Jev accuracy 只以 54 条有效响应为分母，另有 6 条在有限重试后 network timeout，因此 0.944
不是端到端成功率。完整 run ID、混淆矩阵与结论见
[实验结果](SYSTEM1_INTENT_ROUTING_EXPERIMENT_RESULTS_20261009.md)。
