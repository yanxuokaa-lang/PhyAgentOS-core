# jev-decision-layer

把决策模型包成**业务决策工具**：调用方只说"要做什么判断"，不说"用哪个模型"。

[![CI](https://github.com/Wany-i/jev-decision-layer/actions/workflows/ci.yml/badge.svg)](https://github.com/Wany-i/jev-decision-layer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#不需要什么)

> ⚠️ **非官方项目。** 第三方封装，与 TypeSafe AI 无任何隶属关系。

---

## 背景：这个项目接的是什么

| 项 | 值 |
|---|---|
| **调用平台** | **OpenRouter** —— 走它的 decisions 端点，不是通用的 `chat/completions` |
| **端点** | `POST https://openrouter.ai/api/alpha/decisions`（注意**没有 `/v1`**，加了会 404） |
| **模型代号** | **`typesafe/jev-1.13`**（别名 `jev-latest`；实测回答版本 `typesafe/jev-1.13-20260917`；厂商标识 `TypeSafe`） |
| **模型类型** | "System One" **决策模型**：输入 `state` + 声明式 `questions`，输出类型化答案 + 概率 + 置信度，**不生成文本** |
| **输出形态** | `answers` 内按问题类型分三种：`choice`（选项 + 概率 + 置信度）/ `score`（分数 + 概率 + 置信度）/ `noul`（是-否概率，**无置信度字段**） |
| **计费** | 按输入 token 计，$0.042 / 百万 token，**输出免费** |
| **上下文** | 64k / 请求；其中 `state` + 单条最长问题 ≤ **32k**（硬上限） |

**为什么需要这一层**：该模型不能按常规"接模型"的方式使用 —— 用 `chat/completions` 协议调它**会直接 400**
（实测原文：`typesafe/jev-1.13 is a decisions model and cannot be used with the chat/completions endpoint`）。
所以"在模型下拉框里选它"这件事本身不成立，必须有一层把它包成可用的工具。

### 脱敏说明

- **不含任何密钥**：key 只在运行时从环境变量 `OPENROUTER_API_KEY` 读取，不写盘、不进日志、不进报错
- **不含真实业务数据**：`examples/` 与 `registry/` 中的数据均为构造的示例值
- **不含个人路径、账号标识、客户可识别信息**

---

## 这个项目解决什么问题

决策模型和聊天模型是两种东西：

| | 聊天模型 | 决策模型 |
|---|---|---|
| 输入 | 消息 | `state`（素材）+ `questions`（声明式问题） |
| 输出 | 文本 | 类型化答案（选择 / 分数 / 是-否概率）+ 置信度 |
| 用途 | 写、聊、推理 | 分流、打标、门禁、评分、路由 |

直接暴露原生接口有三个问题：① 调用方得懂它一堆坑；② 模型成了硬依赖，换模型要改所有调用点；
③ 没人会在调用点做置信度门控。**这一层解决这三件事。**

---

## 装载后你会得到什么

| 你得到 | 具体是什么 |
|---|---|
| **一个函数** | `decide(决策名, 业务字段)` → `结论 + 置信度 + 门控`。业务代码里只写这一句 |
| **三个能直接用的决策** | 见下表。也可以只当模板，照抄改成自己的 |
| **一套加决策的机制** | 在 `registry/` 加一个 JSON 就是新决策，**不用改代码** |
| **两种现成装载形态** | 命令行、MCP 工具（接进 Agent 即用） |
| **Agent 里多两个工具** | `list_decisions`（问有哪些决策、要哪些字段）与 `decide`（做判断） |
| **28 项离线测试** | 不需要 API key、不联网，改完代码立刻能验 |
| **一批调研文档（可选）** | 为什么这么设计、阈值从哪来、这个模型哪些事不能干 —— 见 [`docs/`](docs/) |

**三个自带决策**（既是可直接用的，也是写自己决策的模板）：

| 决策名 | 判断什么 | 特点 |
|---|---|---|
| `ad_keyword_action` | 广告关键词下一步动作（加价 / 降价 / 暂停 / 保持 / 否定） | 中文，按动作分别定阈值 |
| `browser_step` | 浏览器/桌面自动化的风险闸门（下一步该不该自动做） | 中文，演示硬约束怎么写 |
| `support_triage` | 客服消息分流（类目 + 是否要退款） | 英文（底层模型英文准确率最高） |

### 明确没给你的

避免预期错位，这几件它**不做**：

- **不接业务系统** —— 它不会去连广告后台、不会点浏览器、不会读数据库。输入是你给的字段，输出是判断
- **不做算术** —— 比例、差值、计数要你在代码里算好再传
- **不管结果落地** —— 存证、审计、审批、回滚都在你的代码里
- **不能聊天** —— 它不生成文本，当不了对话模型

---

## 使用方式

**不需要安装**：复制目录即可（纯标准库，无第三方依赖）。只需要 **Python 3.10+** 与一个 API key。

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."     # PowerShell: $env:OPENROUTER_API_KEY = "sk-or-v1-..."
```

按场景选一种（或组合）：

### A. 当库用（Python）

```python
from decision import decide

# 注意：需要计算的值先自己算好 —— 这个模型不做算术、计数也不可靠
r = decide("ad_keyword_action", {
    "目标ACOS": 0.30, "关键词": "car phone holder magnetic", "匹配方式": "widened",
    "曝光": 1840, "点击": 11, "花费": 6.85, "销售额": 0.0, "订单": 0,
    "运行天数": 9, "当前出价": 0.62, "实测ACOS": "无成交",   # ← 代码算好的
})

if r["gate"] == "auto":
    apply(r["outcome"])      # 可以按结论自动执行
else:
    queue_for_review(r)      # 必须转人工
```

### B. 当命令行用

```bash
python decision.py list                                   # 有哪些决策
python decision.py show ad_keyword_action                  # 某个决策要哪些字段
python decision.py decide ad_keyword_action \
  --context examples/context_ad_keyword.json               # 做一次判断
```

### C. 接进 Agent（MCP）—— 装完 Agent 就多了两个工具

```json
{
  "mcpServers": {
    "decision-layer": {
      "command": "python",
      "args": ["/absolute/path/to/jev-decision-layer/mcp_server.py"],
      "env": { "OPENROUTER_API_KEY": "sk-or-v1-..." }
    }
  }
}
```

不需要 MCP 客户端也能自测：`python mcp_server.py --selftest`

装好之后，Agent 侧的使用方式是：**先问有哪些决策，再带着字段去调**。
工具名刻意**不带底层模型名** —— Agent 看到的是"业务决策"，不是"某个模型"。

---

## 一次决策：你要给什么，你会收到什么

**你要给的** —— 决策名 + 该决策声明的字段（其余字段会被自动裁掉，不算错）。
需要算术的值**必须先算好**：模型不做算术，计数也不可靠。

**你会收到的**：

| 字段 | 含义 |
|---|---|
| `outcome` | 结论（选中的选项 / 分数 / 是-否概率） |
| `confidence` | 模型对这个结论的把握 |
| **`gate`** | **`auto`** = 可以按结论自动执行；**`review`** = 必须转人工 |
| `signals` | 其它问题的答案（不参与结论，供你的代码或注册表硬约束参考） |
| `trimmed` | 被裁掉的字段名，可核对 |
| `elapsed_ms` / `usage` | 耗时与本次 token 费用 |
| `guard_hits` | 命中硬约束时才有，说明是哪条规则拦下的 |

**`gate` 是结果的一部分，不是可选项。** 设计上它可能因为两件事变成 `review`：

1. **置信度不够** —— 每个动作有各自的阈值（"保持"错了只是少赚，"暂停投放"错了直接丢流量）
2. **命中注册表里的硬约束** —— 例如"下一步动作不可逆概率高"，哪怕结论再自信也拦下

原始概率分布需显式 `debug=True` 才返回 —— 默认不给，因为置信度很容易被误用。

---

## 加你自己的决策：只写 JSON，不改代码

在 `registry/` 放一个文件即可：

```json
{
  "name": "ticket_priority",
  "description": "工单优先级排序",
  "primary": "优先级",
  "state_fields": ["标题", "正文", "客户等级"],
  "default_threshold": 0.7,
  "thresholds": { "高": 0.85, "中": 0.7, "低": 0.5 },
  "guards": [
    { "signal": "涉及金额", "op": ">", "value": 0.6, "then": "review",
      "why": "涉及金额的判断一律人工复核" }
  ],
  "questions": {
    "优先级": {
      "type": "choice",
      "instructions": "这条工单应该排在哪一档",
      "criteria": { "高": "影响可用性", "中": "影响体验", "低": "咨询类", "other": "都不合适" }
    },
    "涉及金额": { "type": "noul", "instructions": "这条工单涉及退款或赔付" }
  }
}
```

**三种问题原语**（就这三种）：

| type | 问什么 | `criteria` 形状 | 返回 |
|---|---|---|---|
| `choice` | 从你声明的选项里选一个 | **对象** `{key: 说明}` | 选项 + 概率分布 + 置信度 |
| `score` | 在有序标尺上打分 | **数组**（顺序 = 刻度） | 分数（可落两档之间）+ 概率 + 置信度 |
| `noul` | 一个是/否命题 | 可省略 | "是"的概率 0–1（**没有**置信度字段） |

**一定要带 `other` 选项**，否则模型只能在你给的选项里挑个最不坏的。
自查清单与"什么会被拒"见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 用之前要知道的几条

**别交给它做的事**：

| 别交 | 为什么 |
|---|---|
| 算术、计数、百分比、差值 | 官方明说"不是计算器"，且**计数不可靠、误差随规模增长** |
| 日期先后与天数 | 日期被当文本读，不当有序量 |
| 生成文本、写文案 | 不生成文本 |
| 开放式推理、多跳、复合判断 | 间接层级越多越不准；要求**一句话一个判断** |
| 看截图、看图 | 仅文本输入，页面状态必须你自己文本化 |
| 拿 `score` 插值还原具体数值 | 官方称其 score 层级"数值校准很弱" |
| 把 `noul` 和 `choice` 的数互相换算 | 同题两者可差 20 倍以上 |

**三条使用提醒**：

- **阈值必须在你自己的数据上标定。** 实测同一判断、不同 `state` 形状，置信度可偏 ±0.33 ——
  换 `state` 结构要重标。默认阈值是起点，不是结论。
- **中文可用但不是最优。** 底层模型官方写明英文准确率最高，CJK 等其它语言
  "handled but not equally well"，要求"在你的数据上自测"。
- **32k 是硬上限，不是推荐值。** 上下文共 64k / 请求，其中 `state` + 单条最长问题 ≤ 32k。
  实际给多少，取决于那几条数据是否真在支撑这次判断。

**`state` 是数据不是指令** —— 底层模型不把 `state` 当敌意内容处理，见 [SECURITY.md](SECURITY.md)。

---

## 不需要什么

- **不需要装任何依赖** —— 仅 Python 标准库（3.10+）
- **不需要 GPU**、不需要本地模型
- **不需要 API key 也能跑测试** —— `python -m unittest discover -s tests` 完全不联网
- 不需要数据库、不需要常驻服务

---

## 项目结构

```
decision.py                 核心层：唯一入口 decide()，装载注册表 / 裁剪 / 门控 / 硬约束
mcp_server.py               MCP 壳（工具：list_decisions、decide）
registry/                   决策注册表（一份 JSON = 一个决策）
  ├── ad_keyword_action.json    广告关键词下一步动作（中文）
  ├── browser_step.json         浏览器/桌面自动化的风险闸门（中文，演示 guards）
  └── support_triage.json       客服分流（英文）
examples/
  ├── quickstart.py             三个可直接跑的场景
  └── context_ad_keyword.json   示例输入
tests/test_offline.py       离线单元测试（28 项，不需要 key）
docs/                       调研文档与实现说明（15 份，索引见 docs/README.md）
  ├── README.md                         文档索引与来源声明
  ├── 实现说明-一次决策的内部链路.md          给改造者：调用链、真实报文、改造指南
  ├── Jev模型使用调研.md                   接口契约与实测数据
  ├── Jev决策场景清单.md                   它能干什么、不能干什么
  ├── Jev广告关键词决策-状态设计与实测.md      一个场景的完整设计（含 40 次对照实验）
  ├── Jev接入指南-IDE浏览器与运行环境.md      怎么接进 IDE 与浏览器自动化
  ├── Jev外网用法调研.md                   调用通道、官方宣称与独立实测
  └── 调研原始/                            六路调研产物 + 独立复核报告（8 份）
```

---

## 贡献与反馈

**Issue 与 PR 均接受。**

- **新增一个决策** → 直接提 PR：在 `registry/` 加一个 JSON 即可，不用改代码
- 提交前读 [CONTRIBUTING.md](CONTRIBUTING.md)（含自查清单与"什么会被拒"）
- Bug / 新功能 → 用对应的 issue 模板
- **安全漏洞或密钥泄露 → 不要开公开 issue**，走 [SECURITY.md](SECURITY.md) 的私密渠道
- 参与即视为同意 [行为准则](CODE_OF_CONDUCT.md)

---

## 基于什么

| 项 | 说明 |
|---|---|
| 调用平台 | OpenRouter（decisions 端点） |
| 模型代号 | `typesafe/jev-1.13`，厂商标识 `TypeSafe` |
| 本项目 | 独立的第三方封装层，**不是** TypeSafe 官方项目，也**未**获得其背书 |
| 运行时 | Python 3.10+，仅标准库 |
| 许可 | MIT |

对底层模型的接口事实、实测数据与局限，见 `registry/*.json` 的 `notes` 字段与本文档各节。

## 调研文档与实现说明

- **想改这个项目** → [`docs/实现说明-一次决策的内部链路.md`](docs/实现说明-一次决策的内部链路.md)：
  八步调用链、真实请求/响应快照、字段映射、改造指南
- **想知道为什么这么设计、阈值从哪来、哪些事不该交给它** → [`docs/`](docs/)

来源声明与完整索引见 [`docs/README.md`](docs/README.md)。

---

## 依赖与许可

- 仅 Python 标准库（3.10+），**无第三方依赖**
- MIT License，见 [LICENSE](LICENSE)
- 变更记录见 [CHANGELOG.md](CHANGELOG.md)
