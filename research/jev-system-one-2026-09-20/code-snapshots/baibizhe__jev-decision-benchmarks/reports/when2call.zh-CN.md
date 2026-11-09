# JEV 在 When2Call 上的评测与公开模型对照

日期：2026-09-19。实际模型：`typesafe/jev-1.13-20260917`。3,652 个请求全部有效，零重试。

## 1. 主结果与计分

普通准确率为 **2733/3652 = 74.84%**，固定四类 Macro F1 为 **56.55**，工具幻觉率为 **197/258 = 76.36%**。

JEV 同时看到原始四个答案候选，通过 Choice 选择一个；官方 MCQ 分别计算候选续写似然。双方使用相同 3,652 题及类别计分，但推理协议不同。这是有适配差异的任务对照，不能据此宣称严格同协议领先。

Macro F1 对 direct、tool_call、request_for_info、cannot_answer 四类等权平均。direct 没有正样本且零分母计零，因此满分上限为 75（0–100 标度）。工具幻觉率分母仅为 `tools=[]` 且 gold 为 cannot_answer 的题目；分子为其中预测 tool_call 的数量。

## 2. 官方 MCQ 全部模型

| 模型 / 模式 | 普通准确率 ↑ | Macro F1 ↑ | 工具幻觉率 ↓ |
|---|---:|---:|---:|
| **JEV 1.13 (Choice)** | **74.84%** | **56.55** | 76.36% |
| Llama 3.2 1B Instruct | — | 21.70 | 43.00% |
| Llama 3.2 3B Instruct | — | 17.90 | 52.00% |
| Llama 3.1 8B Instruct | — | 16.60 | 67.00% |
| Llama 3.1 70B Instruct | — | 37.80 | 57.00% |
| Qwen 2.5 0.5B Instruct | — | 32.00 | 20.00% |
| Qwen 2.5 1.5B Instruct | — | 29.90 | 23.00% |
| Qwen 2.5 3B Instruct | — | 29.80 | 23.00% |
| Qwen 2.5 7B Instruct | 49.01% | 32.00 | 21.00% |
| Qwen 2.5 14B Instruct | — | 36.20 | 21.00% |
| Qwen 2.5 32B Instruct | — | 32.90 | 17.00% |
| Qwen 2.5 72B Instruct | 50.82% | 32.80 | 23.00% |
| xLAM 1B FC-R | — | 25.60 | 40.00% |
| xLAM 7B FC-R | 42.72% | 31.50 | 24.00% |
| xLAM 8x7B R | — | 32.90 | 13.00% |
| xLAM 8x22B R | — | 34.30 | 9.00% |
| MNM 4B SFT (baseline) | — | 29.70 | 16.00% |
| MNM 4B dataset-SFT | — | 48.10 | 4.30% |
| MNM 4B dataset-RPO | — | 51.00 | 1.90% |
| MNM 8B SFT (baseline) | 48.38% | 31.90 | 19.00% |
| MNM 8B dataset-SFT | 66.13% | 49.40 | 7.00% |
| **MNM 8B dataset-RPO** | 69.09% | 52.40 | **1.20%** |

加粗仅表示本列数值最优及对应模型名。MNM 为 Mistral-NeMo-Minitron；dataset-SFT/RPO 表示使用 When2Call 训练。JEV 是否见过公开测试数据未知。

F1 和幻觉率来自[固定官方 README](https://github.com/NVIDIA/When2Call/blob/ecc8d42388e91ab37e7e737d48e16e8ecea3d1dc/README.md#mcq-1)；普通准确率来自[论文 Table 14–19](https://aclanthology.org/2025.naacl-long.174.pdf#page=18) 的混淆矩阵复算，均通过总数 3,652、类别支持数及已发表 F1 一致性检查。Acc-Norm 不纳入结果。

论文 Table 13 标为 Llama 3.1 70B，但矩阵总数为 3,649、复算 F1 为 17.58，与公布的 37.8 不符。因此该模型普通准确率留空；缺失值不以 Acc-Norm 或其他模型分数填补。

### 普通准确率的独立复算

| 模型 | 正确数 / 总数 | 普通准确率 |
|---|---:|---:|
| Qwen 2.5 7B Instruct | 1790 / 3652 | 49.01% |
| Qwen 2.5 72B Instruct | 1856 / 3652 | 50.82% |
| xLAM 7B FC-R | 1560 / 3652 | 42.72% |
| MNM 8B SFT (baseline) | 1767 / 3652 | 48.38% |
| MNM 8B dataset-SFT | 2415 / 3652 | 66.13% |
| MNM 8B dataset-RPO | 2523 / 3652 | 69.09% |

详见[矩阵与复算记录](../data/when2call/derived_checks.json)。

## 3. 混淆矩阵

行是真实类别，列是预测类别。

| 真实 / 预测 | direct | tool_call | request_for_info | cannot_answer |
|---|---:|---:|---:|---:|
| direct | 0 | 0 | 0 | 0 |
| tool_call | 8 | 1186 | 95 | 6 |
| request_for_info | 11 | 228 | 817 | 6 |
| cannot_answer | 77 | 312 | 176 | 730 |

## 工具幻觉的真实例子与分母解释

以下是本次已保存结果中的真实案例。按 UUID 排序，取满足 `tools=[]`、正确类别为 `cannot_answer`、JEV 预测为 `tool_call` 的第一题，不根据概率或故事性挑选。

| 项目 | 内容 |
|---|---|
| 题目 UUID | `0089914c-3735-490a-aa4c-b782fea825d4` |
| 数据来源 / 原始题号 | BFCL v2 Live Simple / `live_simple_235-124-0` |
| 用户原话 | `Play the song 'Friends' by Marshmello` |
| 中文意思 | 播放 Marshmello 的《Friends》 |
| 实际可用工具 | **无，`tools=[]`** |
| JEV 实际返回 | `choice="c1"`，对应 `tool_call` |
| 官方正确类别 | `cannot_answer`，对应 `c3` |

JEV 选中的原始候选内容如下，仅为便于阅读添加缩进：

```json
{
  "name": "play_spotify_song",
  "arguments": {
    "query": "track:Friends artist:Marshmello"
  }
}
```

官方正确候选原文是：

> I'm sorry, I'm currently unable to play music. I'm designed to assist with information and tasks, but I don't have the capability to play songs.

中文意思：抱歉，我目前无法播放音乐。我可以协助处理信息和任务，但没有播放歌曲的能力。

**为什么算幻觉？** 题目没有给它音乐播放工具，它却选择了调用 `play_spotify_song`。这个调用在当前环境里不可用，因此计入一次工具幻觉。歌曲和歌手都来自用户问题，出错的是对工具是否可用的判断。

这里的调用 JSON 是数据集预先提供的候选；JEV 的实际返回是选择编号 `c1`，没有实际执行歌曲播放。这个例子证明它选中了不可用工具的调用答案，不能据此声称它在自由生成中凭空编造了函数名，或成功调用过 Spotify。API 返回的该候选概率为 0.52，只作原始记录，不等同于经过校准的正确概率。

原始数据另有 `orig_tools` 字段保留删减前的工具，但实际评测使用的 `tools` 字段为空。已核对实际请求：上下文保留官方通用工具调用说明，没有注入 `play_spotify_song` 的工具定义；该名字只出现在调用候选中。候选文本中出现一个工具名，不代表系统提供了该工具。

**这题如何计分？** 工具幻觉率的分母增加 1、分子增加 1；整体准确率的总题数增加 1、正确数增加 0。总计 258 道无工具且正确类别为 cannot_answer 的题中，197 道发生了这种选择，所以工具幻觉率为 **197/258 = 76.36%**。

整体准确率看全部 3,652 题，分母不同。把结果拆开如下：

| 范围 | 总题数 | 答对题数 | 普通准确率 |
|---|---:|---:|---:|
| 无工具子集 | 258 | 16 | 6.20% |
| 其余题目 | 3,394 | 2,717 | 80.05% |
| 全量 | 3,652 | 2,733 | 74.84% |

无工具子集仅占全量的 7.06%。JEV 在这一小部分题上表现很差，其他题的较高正确率仍能使整体准确率达到 74.84%。高总体准确率与高工具幻觉率可以同时存在。这个案例说明了实际错误行为；模型为何作出该选择仍需控制变量实验验证，不能仅从候选或概率推断内部原因。

核查材料：[单题证据 JSON](../data/when2call/hallucination_case.json) 包含原始题目、实际请求与响应、选择映射、原归档行号和哈希；[逐题计分 CSV](../data/when2call/per_example.csv) 可复算上述分子、分母。这里引用已有记录。

## 4. 官方 Judge：单独参考

这条路线在 300 题子集上自由生成回答，再由 GPT-4-Turbo-04-09 判别，样本规模、输出形式和评分过程均不同。此表保留论文公布的 F1，不把它重命名为本实验固定四类 Macro F1，也不将 JEV Choice 成绩放入该表。

| 模型 | 论文 Acc ↑ | 论文 F1 ↑ | 工具幻觉率 ↓ | 论文表 |
|---|---:|---:|---:|---:|
| GPT-4o | 61.30% | 61.30 | 26.00% | 4 |
| GPT-4o-Mini | 54.20% | 52.90 | 41.00% | 4 |
| GPT-4-Turbo-04-09 | 64.30% | 64.60 | 22.00% | 4 |
| MNM 4B baseline | — | 27.90 | — | 5 |
| MNM 4B SFT | — | 48.60 | — | 5 |
| MNM 4B RPO | — | 64.30 | — | 5 |
| MNM 8B baseline | — | 34.80 | — | 5 |
| MNM 8B SFT | — | 57.10 | — | 5 |
| MNM 8B RPO | — | 66.10 | — | 5 |

来源：[论文 Table 4、5](https://aclanthology.org/2025.naacl-long.174.pdf#page=7)。

## 5. 来源与复查

[统计 JSON](../data/when2call/summary.json) · [逐题计分](../data/when2call/per_example.csv) · [MCQ CSV](../data/when2call/comparison.csv) · [Judge CSV](../data/when2call/judge.csv) · [来源哈希](../data/manifest.json)

先前检索到的第三方新模型资料存在未公开数值、仅 15 题示例、格式回退或改变三类计分等问题，没有作为同口径主表成绩。基线均为已发表数字，未重测其他模型。

在仓库根目录运行 `python3 scripts/build_tables.py --check` 可离线复算准确率、四类 F1、幻觉率及六个论文矩阵，并核验案例选择和原始候选映射。
