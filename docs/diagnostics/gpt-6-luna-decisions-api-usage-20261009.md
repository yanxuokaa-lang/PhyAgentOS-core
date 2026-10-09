# GPT-6 Luna Decisions API 使用诊断

日期：2026-10-09。保存本轮 API 使用分析；信息来自当前读取的 OpenAI 官方文档。
状态：文档分析，未调用付费 API，未接入 PAOS。PAOS 接入分析见
[架构适配分析](../forge/GPT6_LUNA_DECISIONS_PAOS_FIT_ANALYSIS_20261009.md)。

## 1. 结论与定位

Decisions API 面向高频、低延迟、答案空间明确的语义判断。它接收文本、图片或两者组合，
返回条件概率、固定候选选择或有序等级评分。Agent 可以用它做请求分流、方法匹配、
证据相关性判断和已有动作之间的选择。

当前为 public beta，只支持 `gpt-6-luna`，专用端点为
`POST https://api.openai.com/v1/decisions`。它与同模型的 Responses/Chat Completions
调用拥有不同的请求、返回与计费方式。[S1]

## 2. 请求与返回

| 字段 | 含义 |
| --- | --- |
| `model` | 当前使用 `gpt-6-luna` |
| `input` | 所有问题共享的证据：文本字符串或含文本/图片的 user messages |
| `questions` | 问题类型、名称、判断标准，以及候选选项或等级 |
| `answers` | 各问题的 typed answer；建议给问题唯一 `name` 并按名称读取 |

| 类型 | 适用对象 | 主要返回 |
| --- | --- | --- |
| `predicate` | 一个条件是否成立 | `probability`：0 到 1 |
| `choice` | 无序、互斥的候选类别 | `choice`、`probabilities`、`confidence` |
| `score` | 从低到高的有序等级 | `score`、`probabilities`、`confidence` |

“固定候选”是本次请求的候选集；应用可以每次根据可用能力与当前状态动态生成。
`choice` 每题选择一个值；多个标签可以分别使用 predicate 问题表达。

相互独立的问题可放在同一请求中，共享输入。例如分别问请求类别和是否存在未明确的目标。
后一个问题依赖前一个答案时，要分步请求；不能假设同一 `questions` 数组按答案顺序执行。[S1]

## 3. Python 使用示例

官方要求 Python OpenAI SDK 至少 `3.26.0`；JavaScript 至少 `7.30.0`。[S1]
以下命令与代码是使用说明，本轮未执行安装或调用：

```bash
python -m pip install "openai>=3.26.0"
```

在服务端配置 `OPENAI_API_KEY`，然后：

```python
from openai import OpenAI

client = OpenAI()
decision = client.decisions.create(
    model="gpt-6-luna",
    input="用户：解释刚才任务为什么失败，并提出下一步建议。当前：任务已结束，日志可用。",
    questions=[
        {
            "type": "choice",
            "name": "route",
            "instructions": "选择处理路径。状态查询选 status；分析或规划选 reason；意图不明选 clarify。",
            "choices": [
                {"value": "status", "description": "直接读取已有状态或结果。"},
                {"value": "reason", "description": "解释原因、比较方案或制定计划。"},
                {"value": "clarify", "description": "需要补充关键信息。"},
            ],
        }
    ],
)

answer = next(item for item in decision.answers if item.name == "route")
if answer.type == "refusal":
    print("该问题被拒绝，使用应用定义的备用路径。")
elif answer.type == "choice":
    print(answer.choice, answer.probabilities, answer.confidence)
```

该结果只表达路径选择。应用负责读取当前状态、调用对应 handler、传递上下文及处理取消。
涉及任意工具参数生成时使用 Responses function calling；涉及自定义 JSON 对象时使用
Structured Outputs。Decisions 本身不执行工具，也不生成自由文本解释。[S1]

图片输入使用 `input_image`，与 `input_text` 放在同一个 user message 的 `content` 中：

```json
{
  "role": "user",
  "content": [
    {"type": "input_text", "text": "检查照片里的产品是否可见破损。"},
    {"type": "input_image", "image_url": "data:image/png;base64,<image bytes>"}
  ]
}
```

示例中的 `<image bytes>` 必须换成实际 base64。指南要求 inline data URL，不支持 `file_id`。
官方 OpenAPI 还描述每请求最多 128 张图片，其他 message roles、音频、文件、工具调用和
item references 不支持；关于外部 HTTP(S) 图片 URL，见第 7 节的资料差异。[S1,S2]

## 4. 概率、confidence 与 score

`predicate.probability` 是模型估计条件为真的概率。实际准确率与阈值应通过业务标注样本验证，
根据假阳性、假阴性成本选择。低概率“为真”不自动证明“为假”：证据不可见、缺失和矛盾
必须在问题设计或其他选项中表达。

`choice.probabilities` 给出选项分布；`confidence` 是另一独立字段。指南没有给出它的计算
公式，因此不能把它等同于最高选项概率，也不能自动当作经过校准的正确率。[S1]

score 使用从 0 开始的等级索引，返回概率加权均值：

```text
等级 0/1/2 的概率为 0.1/0.7/0.2
score = 0×0.1 + 1×0.7 + 2×0.2 = 1.1
```

“全部集中在中等级”和“最低/最高等级各一半”可以有相同均值。因此需要采取离散动作时，
使用 choice 或同时分析分布；不要仅凭 score 判断某个唯一等级。score 的索引也不等于
实际损失或物理量；若成本不等距，应由应用按自己的损失函数计算。

## 5. 适用范围

| 功能 | 使用建议 |
| --- | --- |
| 工单分类、模型路由、请求意图 | choice；保留 other/reason/clarify 等符合业务的选项 |
| 从当前可用 Skill/Tool 中选择 | choice；候选来自应用的真实能力目录 |
| 多标签检查、证据是否相关 | 每个独立条件用 predicate |
| 严重程度、候选相关性等级 | score；保持各等级标准清晰 |
| 图片可见属性/破损判断 | predicate/choice；区分不可见与明确否定 |
| UI/媒体/语音动作选择 | choice；应用执行前再次检查当前状态 |
| 完整 PlanGraph、工具参数、自由文本说明 | 保留 Responses / function calling / Structured Outputs |
| 精确权限、资源状态、引用关系、IK/碰撞 | 保留程序与拥有事实的专用系统 |

官方提供 GPT-Live client delegation 示例：Live 负责语音交互，应用把转写和当前状态交给
Decisions 选动作；复杂请求转 reasoning model；应用执行并向 Live 报告实际结果。
这是组合式分工，语音音频不是 Decisions 直接输入。[S3]

## 6. 价格、速度与验证

官方目前公布约比 Responses API 快 10 倍；没有在已读指南中给出本项目的绝对延迟或端到端
加速保证。若模型调用只占任务小部分，整体收益会低于该倍数。

Decisions 使用 GPT-6 Luna 的输入价格为每百万 tokens 0.10 美元；无缓存读、缓存写或输出
token 费用。区域处理 premium 与长上下文输入 multiplier 仍适用。同模型其他端点遵循
其各自计费。[S1]

例如每次完整请求 1,000 输入 tokens，一百万次基础输入费用约 100 美元。问题标准、候选
描述与图片同样属于输入成本；共享 input 的实际收益用返回 usage 测量。

首次验证选择一个具体分类任务，用正常、歧义、缺证与类别外样本对比现有处理路径，测量：

- 分类质量、误路由和拒绝处理；
- p50/p95 完整请求延迟；
- 输入 tokens、费用、备用模型使用率；
- 取消或状态变化后是否仍错误消费旧答案。

本轮没有 API 计费、账户可用性、绝对延迟或业务精度实测结果。

## 7. 官方资料差异与明确边界

本轮官方指南和 API reference 搜索内容要求 base64 inline 图片，明确排除外部 URL；
官方 OpenAPI `createDecision` description 同时写有 publicly accessible HTTP(S) URL
支持。两个来源存在直接冲突。初次接入选择共同支持的 base64；URL 能力留待官方修订或
单独实测确认，不能把它写成当前已验证能力。

GPT-6 Luna 模型页描述一般模型上下文、推理 effort、工具与 endpoint 支持；Decisions 使用
专用协议，不能直接继承全部参数。已读指南未确定 Decisions 的最大 question/choice 数量、
专用上下文上限、streaming 或 Batch 支持。本轮不填猜测值。[S1,S2,S4]

## 8. 官方来源

- [S1 Decisions guide](https://developers.openai.com/api/docs/guides/decisions)：协议、示例、三类问题、概率解释、价格与 beta 状态。
- [S2 Create a decision reference](https://developers.openai.com/api/reference/resources/decisions/methods/create)：通过官方 OpenAPI 工具取得 `/v1/decisions` operation；Markdown fetch 返回 404，未取得完整 component schemas。
- [S3 Connect voice to Decisions](https://developers.openai.com/api/docs/guides/decisions-voice)：应用状态、取消、动作选择和复杂请求路由。
- [S4 GPT-6 Luna model](https://developers.openai.com/api/docs/models/gpt-6-luna)：一般模型能力；与 Decisions 专用参数区分。

## English summary

Decisions is a dedicated public-beta endpoint for GPT-6 Luna. It evaluates shared text/image input
with predicate, choice, and score questions. Use it for bounded semantic classification, selection,
and ranking; use Responses for generated plans, arbitrary structured fields, explanations, and tool
arguments. Probability and confidence require application-specific validation. Current published
pricing is $0.10 per million input tokens, without cache or output charges, subject to applicable
regional and long-context input premiums. Official sources disagree about hosted image URLs;
inline base64 is the shared documented path. This record contains documentation analysis, not a
paid API test or a PAOS implementation.
