# System 1 入口意图与路由对比实验报告

日期：2026-10-09
实验范围：Laya 本地模型与 Jev 远程 System One API 的离线标签判断。预测只写入实验产物，
没有接入或替换 PAOS 入口、AgentLoop、Coordinator、Runtime 或 handler。

## 摘要

计划内的 Laya/Jev 对比已经完成：三个 Laya checkpoint 和 Jev 均完成 20 条 development 与
60 条 evaluation。GPT-6 Luna Decisions 没有完成，因为当前代理对专用
`POST /v1/decisions` 返回 404；本报告不把它列入排名，也不以聊天接口替代。

在 60 条 evaluation 上，Laya English、multilingual、typed-decisions 的联合正确率分别为
0.250、0.383、0.417；Jev 在 54 条有效响应上的联合正确率为 0.944，但 6 条请求在有限重试后
仍超时，因此端到端联合成功率只有 51/60，即 0.850。结论是：Jev 值得进入 fail-to-System-2
的 shadow 验证，Laya 当前零样本配置不适合替换入口路由；两者都没有获得直接替换 PAOS 的证据。

## 1. 两种方法与 RLCD 原理

### 1.1 Laya：本地非自回归结构化决策

Laya 接收一个 `state` 和一组 typed questions，通过一次前向传播直接返回结构化答案，不逐 token
生成自然语言。本实验同时提交两道 `choice` 问题：七选一的 `intent` 和五选一的 `route`；每道题
返回选择、完整候选概率和 confidence。

本地对比了同一仓库的三个 checkpoint：

| Checkpoint | 公开定位 | 本实验角色 |
| --- | --- | --- |
| English | ModernBERT-large，421M | 英文通用模型在中文输入上的受控对照 |
| Multilingual | mmBERT-base，322M | 面向 100+ 语言，中文实验主对照 |
| Typed-decisions | ModernBERT-large，421M | 面向 typed-decision workflow 的受控对照 |

运行环境与 PAOS 隔离：`/home/yanxu/laya-system1/.venv`、Laya `0.4.1`、Torch
`2.14.1+cu130`、RTX 5060 Ti；三个 checkpoint 使用同一数据、输入投影、问题定义、标签、scorer
和 CUDA 设备，只改变 checkpoint。

### 1.2 Jev：远程 TypeSafe 结构化判断

Jev 通过 `POST /v1/systemone` 接收 `model + state + questions`。本实验请求 `jev-latest`，服务实际
返回 `jev-1.13.0`；同样使用两道 `choice` 问题并读取标签与候选概率。它是远程闭源服务，网络、
排队和服务端推理共同构成观测延迟。

Jev 与 Laya 都暴露 `choice`、`score`、`noul` 一类结构化判断原语，但不能据此断言二者内部模型
或训练过程相同。公开材料明确描述了 Laya 的 RLCD；本报告对 Jev 只陈述接口行为和本次实测，
不把 Laya 的训练细节移植到 Jev。

### 1.3 RLCD 为什么适合 System 1

RLCD 即 Reinforcement Learning for Calibrated Decisions。给定状态和问题，模型不生成解释文本，
而是直接报告候选结果的概率分布 `p_theta(y | state, question)`。其核心不是只让 top-1 标签正确，
而是让概率本身尽量诚实：当模型真实确信度是 70% 时，长期来看报告 70% 应比虚报 99% 获得更高
期望奖励。

训练机制可拆成五步：

1. 决策头为每个有限候选产生 logit，Softmax 后得到完整概率分布。
2. 训练时向 logits 加零均值高斯噪声，形成多组探索分布；给所有 logit 加同一常数不会改变
   Softmax，因此噪声会去除公共均值。
3. 用严格适当评分规则计算奖励。`log score` 强烈惩罚给真实标签过低概率；`spherical score`
   奖励概率质量集中在真实标签且保持有界；有序 `score` 问题再加入 RPS，使“差一级”优于“差三级”。
4. 使用带组均值 baseline 的 REINFORCE 更新策略。每个探索样本的 advantage 是自身奖励减去组内
   平均奖励，从而降低策略梯度方差；Laya 公开说明称其为 GRPO-style group-mean baseline。
5. 多轮数据按对话前缀切片，并用 `TD(lambda=1.0)` 将最终结果分配给早期前缀，避免早期轮次看到
   未来内容。

严格适当评分规则的重要性质是：若真实分布为 `q`，则期望得分 `E[y~q] S(p,y)` 在 `p=q` 时唯一
最大。这给“报告真实概率”提供了训练激励。但 RLCD 训练并不保证任意新领域天然校准；Laya 公开
说明仍需按问题类型和选项数做温度校准。本实验因此额外计算 ECE、Brier 和 NLL，而不是直接相信
provider 返回的 confidence。

来源：用户指定的[知乎说明](https://zhuanlan.zhihu.com/p/2085760548034167437)，以及本地留存的
Laya 官方 README：`research/jev-system-one-2026-09-20/repositories/Hengle__laya/README.md`。

## 2. 数据集、标签与示例

### 2.1 数据规模

数据文件为 `research/decision-api-intent-probe/samples.jsonl`，共 80 条人工裁定的中文合成记录：

| Split | 记录数 | 结构 | 用途 |
| --- | ---: | --- | --- |
| Development | 20 | 20 个独立设计样例 | 连通、schema、prompt 和错误检查 |
| Evaluation | 60 | 20 个语义家族，每家族 3 个措辞/标点变体 | prompt 冻结后的独立评分 |

这里的“60 条”是 60 次模型判定，但不是 60 个完全独立的真实用户场景。evaluation 的家族结构会
放大一致性错误，且全量数据均为合成中文，因此结果不能外推为真实 PAOS 流量表现。

输入由三部分组成：最新用户消息、相关短对话、当前任务与可用 capability。输出 gold 包含：

- 七类 intent：`status_query`、`task_control`、`clarification_answer`、`new_task`、`analysis`、
  `conversation`、`mixed_or_unclear`。
- 五类 route：`status_read`、`task_control`、`clarification_reply`、`conversation`、`system2`。

development 覆盖全部七类 intent 和五类 route。evaluation 聚焦入口高风险边界，包含 24 条
`status_query`、24 条 `task_control`、6 条 `clarification_answer`、6 条 `analysis`；对应 route 为
18 条 `status_read`、18 条 `task_control`、6 条 `clarification_reply`、18 条 `system2`。

### 2.2 代表性样例

| 用户消息与关键状态 | Gold intent | Gold route | 判断理由 |
| --- | --- | --- | --- |
| “现在做到哪一步了？”；当前任务可读 | `status_query` | `status_read` | 简单状态读取能力可用 |
| “现在有任务吗？”；无当前任务 | `status_query` | `system2` | 缺少可绑定的任务对象 |
| “暂停一下。”；任务执行中且 pause 可用 | `task_control` | `task_control` | 对象和控制能力都明确 |
| “恢复当前任务。”；无任务且 resume 不可用 | `task_control` | `system2` | 有控制意图，但不能走简单执行路径 |
| “红色那个。”；正在等待“红色还是蓝色” | `clarification_answer` | `clarification_reply` | 回答现存澄清问题 |
| “文档里的‘停止任务’是什么意思？” | `analysis` | `system2` | 引用控制词请求解释，不是停止命令 |
| “不要停，查一下进度。”；当前任务可读 | `status_query` | `status_read` | 否定 stop，正向请求状态 |
| “停止任务并分析失败原因。” | `mixed_or_unclear` | `system2` | 同时包含控制和分析两个正向意图 |

这些样例刻意要求模型同时理解文字和 capability state。仅看关键词会把“不要停”或文档引用误判
为控制命令；仅看文字也无法区分“继续”在有暂停任务和无任务时应走的不同路径。

## 3. 结果对比

### 3.1 标签判断与可用性

| Backend | 有效/总数 | Coverage | Intent acc. | Route acc. | Joint acc. | 端到端联合成功 | 成功尝试平均延迟 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Laya English | 60/60 | 1.000 | 0.700 | 0.333 | 0.250 | 0.250 | 0.055 s |
| Laya multilingual | 60/60 | 1.000 | 0.750 | 0.483 | 0.383 | 0.383 | 0.034 s |
| Laya typed-decisions | 60/60 | 1.000 | 0.650 | 0.450 | 0.417 | 0.417 | 0.061 s |
| Jev `jev-1.13.0` | 54/60 | 0.900 | 1.000 | 0.944 | 0.944 | 0.850 | 1.351 s |

<small>Coverage：同时返回合法 intent 和 route 的样本数 / 总请求数。</small><br>
<small>Intent accuracy：在有效响应中，意图标签正确的比例。</small><br>
<small>Route accuracy：在有效响应中，处理路径标签正确的比例。</small><br>
<small>Joint accuracy：在有效响应中，intent 与 route 同时正确的比例。</small><br>
<small>端到端联合成功：同时正确的样本数 / 全部 60 条；传输失败按未成功计。</small><br>
<small>成功尝试平均延迟：只统计最终返回 HTTP 200/本地合法结果的单次尝试，不含模型冷加载；Jev 不含此前失败重试和重试间隔，因此不是完整用户等待时间。</small>

Jev 的 60 个逻辑请求共发生 77 次 HTTP 尝试，其中 23 次 transport failure、17 次为重试；6 个
逻辑请求用尽重试仍失败。有效响应中的 3 个 route 错误全部是 `system2 -> conversation`，属于把
本应升级复杂理解的边界请求降级为普通对话。其 0.944 joint accuracy 的分母是 54，不能写成
“60 条中成功 94.4%”。Jev evaluation 用量为 48,253 input tokens、7,144 output tokens。

Laya 三个 checkpoint 的所有请求都返回合法结构，但 route accuracy 均低于 0.50。English 倾向
`clarification_reply/task_control`，multilingual 大量把 `system2` 和控制请求压到 `status_read`，
typed-decisions 也在 `status_read/clarification_reply/task_control` 间混淆。Multilingual 的 intent
和 route 单项准确率最高，typed-decisions 的 joint 最高；不存在一个在所有指标上占优的 Laya
checkpoint。

### 3.2 概率质量

所有概率指标只在返回合法完整概率分布的有效响应上计算。provider 返回概率有四舍五入误差，
scorer 在候选键和值通过检查后重新归一化；NLL 对真实标签零概率使用 `1e-12` 数值截断。

| Backend | 问题 | 概率样本 | ECE-10 | Multiclass Brier | NLL |
| --- | --- | ---: | ---: | ---: | ---: |
| Laya English | intent | 60 | 0.250 | 0.421 | 0.946 |
| Laya English | route | 60 | 0.213 | 0.770 | 1.533 |
| Laya multilingual | intent | 60 | 0.100 | 0.407 | 0.975 |
| Laya multilingual | route | 60 | 0.274 | 0.843 | 1.951 |
| Laya typed-decisions | intent | 60 | 0.364 | 0.582 | 1.258 |
| Laya typed-decisions | route | 60 | 0.210 | 0.756 | 1.506 |
| Jev `jev-1.13.0` | intent | 54 | 0.047 | 0.021 | 0.055 |
| Jev `jev-1.13.0` | route | 54 | 0.104 | 0.084 | 0.186 |

<small>ECE-10：把最大预测概率分成 10 个等宽区间，累计各区间“平均置信度与实际正确率”的加权差；越低越好。本实验样本很少，ECE 对分箱敏感，只能作方向性比较。</small><br>
<small>Multiclass Brier：每条样本对全部类别计算预测概率与 one-hot 真值的平方误差之和，再取平均；本报告未按类别数缩放，范围 0–2，越低越好。</small><br>
<small>NLL：真实标签预测概率的平均负自然对数；越低越好，对把真实标签赋为接近零概率的过度自信错误惩罚很重。</small><br>
<small>概率样本：通过完整候选集、有限非负数值和正概率和检查的有效响应数；Laya 为 60/60，Jev 为 54/54，但 Jev 仍有 6 个逻辑请求没有概率输出。</small>

Jev 在有效响应上的三个概率指标均明显更低，说明它不仅 top-1 标签更准，概率排序也更接近本
数据的 gold。但该结论受两个限制：第一，只有 54 条有效样本且类别不均衡；第二，Jev 的 6 条
传输失败完全不进入概率评分。因此概率质量不能替代 coverage，也不能证明真实流量上的全局校准。

Laya 的概率结果揭示了 accuracy 看不到的问题。例如 multilingual 的 intent ECE 最低，但 route
NLL 最高；这表示 checkpoint 在部分错误 route 上给了较高概率。若继续 Laya，必须用新的校准集
按问题类型/选项数拟合温度，再使用未参与调参的新 evaluation 重测，不能在本次 evaluation 上
校准后继续把它称为独立测试集。

## 4. 结论与 PAOS 适用边界

1. **Jev 是更强的下一阶段候选。** 在有效响应上，它的标签与概率质量显著领先，适合进入只记录
   预测的 shadow validation；任何超时、非法响应或低把握结果都必须回到 System 2，不能执行简单
   路由。
2. **Jev 尚不能直接替换。** 0.90 coverage、`system2 -> conversation` 错误和远程网络依赖都触及
   入口路由的关键边界。下一轮必须用真实匿名流量、并发、完整逻辑请求延迟和故障回退验证。
3. **Laya 当前配置不进入替换讨论。** 它证明了本地、低延迟、结构化概率输出可行，但 zero-shot
   route accuracy 只有 0.333–0.483。后续价值在领域微调和独立校准，而不是直接接入。
4. **本实验没有验证 System 2 本身。** 它只判断是否应把请求交给状态读取、控制、澄清、对话或
   System 2；复杂规划、工具调用、执行安全和 AgentLoop 仍由现有 PAOS 负责。
5. **GPT-6 Luna 仍是缺失项。** 获得真正支持 `/v1/decisions` 的 endpoint 后，应复用同一 80 条
   数据和 scorer 补跑；在此之前不存在 Laya/Jev/Luna 三方完整排名。

## 5. 可复查产物

- 数据：`research/decision-api-intent-probe/samples.jsonl`
- Scorer：`decision_intent_probe.py`、`laya_intent_probe.py`、`jev_intent_probe.py`
- Laya evaluation：
  `out/laya-intent-probe/{english/20261009T110226Z-8a1d7dee,multilingual/20261009T110235Z-72267c19,typed-decisions/20261009T110243Z-10158043}/`
- Jev evaluation：`out/jev-intent-probe/20261009T102953Z-4c8740d6/`

每个 run 保存 config、environment、requests、responses、predictions、metrics 与 report；Jev 另存
attempts/errors。重新执行 `score` 只读取已有 artifacts，不调用网络，也不覆盖原始响应。
