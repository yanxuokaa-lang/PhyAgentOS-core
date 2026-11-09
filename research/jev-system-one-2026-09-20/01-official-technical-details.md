# Jev / System One：官方技术资料

资料日期：2026-09-20。官方来源以抓取时文档为准；下面把公开接口、官方技术主张、未公开实现分开记录。官网发布文章署名 Diogo Almeida，日期为 2026-09-15。[发布原文](https://typesafe.ai/blog/introducing-system-one-models-and-jev) / [本地正文](web/official-0.txt)。

## 1. 核心计算形式

```text
state（文本或可序列化结构）
  + questions（每题给 instructions、type、必要时 criteria）
  → 同一 state 上的多个独立判断
  → answers（有界值、完整选项概率、Choice/Score 的 confidence）
  → 应用代码组合、排序、路由或执行
```

System One 是产品及模型范式名称；Jev 是具体模型。官方称其采用新架构、parallel sampler 和 RLCD（Reinforcement Learning for Calibrated Decisions）。公开 AI primer 解释了校准目标，但没有给出足以独立重建原模型的网络定义、损失完整公式、训练集与训练配方。不要把社区的 CE/Brier/LoRA 实现直接认定为官方 RLCD。

来源：[官方文档：concepts/system-one](official-docs/concepts__system-one.md)、[官方文档：introduction/machine-learning-primer](official-docs/introduction__machine-learning-primer.md)。

## 2. 版本、价格和容量

| 项目 | 当前文档值 |
|---|---|
| 版本 | `jev-1.13.0` |
| 别名 | `jev-latest`、`jev-preview` 均指向上述版本 |
| 输入 | text only；字符串、JSON object、array；不直接收图片/音频/视频 |
| 收费 | 每百万输入 token USD 0.042；输出 token 免费 |
| 整请求预算 | state + 所有问题合计 64k tokens |
| 最长分支预算 | state + 最长一个问题 32k tokens |
| 限流 | 250,000 tokens/s；1,200 requests/min，官方注明动态调整 |
| Choice | 每题最多 255 个选项 |
| Score | 有序等级，至少 2、最多 10 级 |
| 定制 | 文档称不提供按客户数据 fine-tune / LoRA；通过 state、instructions、criteria 定制 |
| 语言 | 英语为主要训练语言；支持处理其他语言，但准确率不等同 |

来源：[官方文档：models](official-docs/models.md)、[官方文档：api](official-docs/api.md)。这些是抓取时服务文档，不是本次实测配额或性能。

## 3. 三种原语及精确语义

### Choice

输入是 `criteria: {选项名: 描述或 null}`，返回最高概率选项 `choice`、覆盖全部选项且和为 1 的 `probabilities`、`confidence`。

这是在给定候选集内的相对竞争。如果需要“都不合适”，应显式建模该选项或额外询问适用性；不能把候选集里第一名当作绝对适用。

### Score

输入是按顺序排列的等级描述数组。输出 `score = Σ i × p_i`，通常可落在两个等级之间；还返回 `legend`、各等级概率和 confidence。

这里的期望是**等级索引的期望**。把等级描述写成“10元、100元、1000元”并不自动把 score 变成金额期望；也不能用它精确反推某个连续数值。

### Noul

判断一个命题，返回 `noul ∈ [0,1]`，可看作“yes/true”的概率。**没有独立的 confidence 字段**。接近 0 表示强否定，不是低信心；接近 0.5 才接近二元不确定。

来源：[官方文档：primitives/choice](official-docs/primitives__choice.md)、[官方文档：primitives/score](official-docs/primitives__score.md)、[官方文档：primitives/noul](official-docs/primitives__noul.md)。

## 4. HTTP 形状

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

```json
{
  "model": "jev-1.13.0",
  "state": {"ticket": "I was charged twice. Please refund the duplicate."},
  "questions": {
    "team": {"type": "choice", "instructions": "Which team owns this ticket?",
      "criteria": {"billing": "Charges and refunds", "technical": "Software errors"}},
    "refund_requested": {"type": "noul", "instructions": "Does the customer request a refund?"},
    "urgency": {"type": "score", "instructions": "How urgent is this ticket?",
      "criteria": ["Can wait", "Respond soon", "Immediate attention"]}
  }
}
```

示例只展示合法请求形状，未发送。每个答案使用原问题 ID 返回；顶层还包含实际 `model` 与 `usage.input_tokens/output_tokens`。`GET /v1/models` 列出可用名称；文档指出可接受版本 ID 即使未显示在别名列表里。

错误包括 401（鉴权）、422（输入验证）、429（限流）、529（过载）。SDK 内有重试退避；官方 API 文档描述 `retry-after`。完整来源：[官方文档：api](official-docs/api.md)。

## 5. confidence 到底怎么算

官方说明 confidence 来自概率分布的集中程度，不能直接等同于 `p_max` 或“这一次正确的客观概率”。校准是预测集合层面的属性。

官方网页交互示例使用 `(K*p_max-1)/(K-1)` 近似演示 Choice confidence。另一个更明确的代码来源是**官方 LLM Adapter**：

- Choice：`(p_max - 1/K)/(1 - 1/K)`。
- Score：先找众数，计算概率加权的等级到众数距离，再除以均匀分布到中心的平均绝对偏差，做 `max(0, 1-ratio)`。

代码：[`src/system_one_adapter/_utils/confidence_metrics.py` L1–L32](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/typesafe-ai__system-one-adapter-python/src/system_one_adapter/_utils/confidence_metrics.py:1)。

这确认了 Adapter 的实现，**不能仅凭它断言托管 Jev 后端逐位采用完全相同公式**。社区实现还有 entropy、Gini、top-2 margin 等不同公式，详见深挖报告。

## 6. 官方开放了什么

[官方组织](https://github.com/typesafe-ai) 当前抓取到 10 个公开仓库，原始元数据在 [official-repos.json](sources/official-repos.json)。

| 仓库 | 开放内容 | 不代表什么 |
|---|---|---|
| typesafe-sdk-python | Python 同步/异步客户端、问题类型、Pydantic 响应、transport/retry | 不含模型权重或训练实现 |
| typesafe-sdk-js | TS/JS 客户端和静态类型推断 | 不含模型推理引擎 |
| system-one-adapter-python | 用其他生成式模型实现同形 typed API，供比较 | 不是 Jev 的开源模型 |
| skills | 官方 agent 使用指南/skill | 不是新增模型 |
| vllm、LLaDA 等 fork | fork 的上游基础设施/研究代码 | fork 存在不能证明 Jev 就采用其完整架构 |

本次未发现官方 Jev 权重、可直接训练 Jev 的公开完整流水线或公开参数规模证明。

## 7. SDK 与 Adapter 实现

Python 请求主路径：[`src/typesafe_sdk/_core/client/sync/client.py` L1–L233](/home/yanxu/PhyAgentOS-forge/research/jev-system-one-2026-09-20/code-snapshots/typesafe-ai__typesafe-sdk-python/src/typesafe_sdk/_core/client/sync/client.py:1)。
异步对应路径：`src/typesafe_sdk/_core/client/aio/client.py`；传输与重试在 `_core/transport.py` 和 `_core/retry.py`。

Python SDK v0.7.0（2026-09-18）从 msgspec 切换至 Pydantic，增加 `response_model`，修复 str 子类被序列化为字符列表的问题。v0.6.0 将 Score.criteria 改为有序 sequence。这些会直接影响旧版社区客户端兼容性。[版本说明](code-snapshots/typesafe-ai__typesafe-sdk-python/docs/changelog.md)。

Adapter 的流程是构造受约束响应 schema → 调用 OpenAI-compatible 或 Anthropic provider → 解析与校验 → 必要时纠正重试 → 归一化概率 → 统一 typed response。

它支持 `probabilities` 和 `discrete` 两种回答模式；前者是让生成式模型**输出**概率，不等于直接读取模型决策头。正式 OpenAI endpoint 默认走 Responses、自定义 endpoint 默认走 Chat Completions；provider 的接口选择和配置影响执行路径。这里只记录外部项目代码，不执行 provider 请求。

## 8. 已知失败模式与官方性能口径

官方 jaggedness 列出：字面理解、算术/计数、日期比较、多跳间接关系、大量无关 state、对抗内容、指令与 criteria 冲突、结构恒等式不保证、生成文本。例：分别问命题和否定命题，概率未必互补；同一问题用 Noul 与二元 Choice 也不保证一致。

[官方文档：model-jaggedness/jev-1.13](official-docs/model-jaggedness__jev-1.13.md) 给出具体反例。尤其要区分“多个问题互相隔离”与“无关 state 不影响结果”：后者官方明确指出会退化。

发布文的 70–500ms、193.6 倍速度、444.6 倍成本优势是官方测量与特定 workflow 对比。其 reference 使用更大模型的平均预测，不等于所有任务的人类 ground truth；官方也说明测试位置和短输入会影响优势。

“不能 hallucinate”在同一发布文的技术解释重点是**输出形状与候选空间受约束**，并非不会选错、不会被注入影响或不需要任务级验证。本次不把宣传口径升级成语义正确性保证。
