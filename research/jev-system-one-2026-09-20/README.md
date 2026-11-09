# Jev / TypeSafe System One GitHub 资料包

收集时间：2026-09-20（Asia/Shanghai）。按本次要求只保存研究资料，不写项目 CHANGELOG/月度日志，不 git add/commit/push。

## 先读这几份

1. **[源码级实现深挖](02-implementation-deep-dive.md)**：16 个项目的执行链、函数、概率公式、训练/校准、forward 次数、接口差异与实际边界。不是项目简介汇编。
2. **[官方技术细节](01-official-technical-details.md)**：API、三种原语、模型容量、定价、SDK/Adapter、RLCD 已公开与未公开部分。
3. **[后续开发时间线](04-development-timeline.md)**：重点个人项目与官方 SDK 的具体提交记录及变化方向。
4. **[架构推断与评测](06-architecture-evidence-and-evaluation.md)**：黑盒架构研究、独立 benchmark 入口与比较口径。
5. **[核心代码摘录](05-source-excerpts.md)**：原样代码、函数名、行号；完整文本源在 code-snapshots。
6. **[GitHub 项目目录](03-repository-catalog.md)**：[完整 CSV](repositories.csv)、[相关候选 CSV](relevant-repositories.csv)，便于后续筛选。

## 本轮保存规模

| 类型 | 数量 |
|---|---:|
| GitHub 去重检索候选 | 2263 |
| 官方组织/精选链接/相关文本匹配候选 | 1246 |
| 成功保存的候选仓库 README | 1785 |
| 官方文档页面 | 109 |
| 重点仓库文本源码快照 | 33 个仓库，4585 个文件 |
| 源码级分析 | 16 个项目 |
| GitHub commits/releases/issues 响应 | 21 份 |

候选数量包括 fork 与未核实命中；**不是已确认的独立实现数量，也不是 GitHub 全站穷尽结果**。较相关子集通过链接/文本自动筛选，只有深挖报告的具体入口经过本轮源码阅读。GitHub 结果持续变化且有匿名限流，范围和缺口见 [收集方法](collection-method.md)。

## 最值得保留的具体发现

- 官方开放 SDK/Adapter，但本轮未找到 Jev 权重或完整训练实现。
- kev 真正训练 pointer readout；LitJev 是两次 forward；openjev-sglang 请求单 token 的 logprob。它们不能统称同一种“开源 Jev”。
- confidence 公式跨项目不同；API 相似不保证阈值可直接复用。
- jeff 默认 Score 与返回概率的加权平均不一致；Von 新后端按 question 逐个 forward。报告有代码出处。
- 应用侧已有可研究的具体循环：浏览器 operation/target fan-out、输出逐块保留、GEPA 问法改进、仿真无人机异步战术层。

## 原始资料位置

- `official-docs/`：官方 Markdown 文档；`sources/official-llms.txt` 是获取索引。
- `code-snapshots/owner__repo/`：选定文本源，保留原路径和许可证文件；不是完整 clone。
- `repositories/owner__repo/README.md`：广泛候选的 README；成功/失败以 sources-index.json 为准。
- `search/`、`search-summary.json`、`search-recovery.json`：查询及分页原始响应。
- `github-activity/`：提交、release 和 issue 的原始 JSON。
- `web/`：官方发布文章、manifesto、eval 页面和社区架构文章的 HTML/正文。
- `sources-index.json`、`code-snapshots-index.json`、`github-activity-index.json`：来源 URL、保存位置与抓取状态。

性能、准确率和校准数字保留为原作者报告。本次未进行模型或应用复跑。
