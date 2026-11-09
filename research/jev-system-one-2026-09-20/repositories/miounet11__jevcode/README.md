# JevCode

**Jev 技术解决方案与最佳实践** — [www.jevcode.ai](https://www.jevcode.ai)

[![Astro](https://img.shields.io/badge/Astro-5-FF5D01?logo=astro&logoColor=white)](https://astro.build)
[![i18n](https://img.shields.io/badge/i18n-8%20languages-2dd4bf)](#多语言)

![JevCode 首页主图](./public/img/hero/pareto.webp)

Jev 是 TypeSafe 的 System One 决策模型：你给它**状态 + 类型化问题**，它返回**可直接进代码的决策**（带置信度），不是聊天文案。

| 原语 | 做什么 | 典型用途 |
| :--- | :--- | :--- |
| **Choice** | 从互斥选项里选一个 | 意图路由、工单分派、动作选择 |
| **Score** | 按量纲打分 | 相关性排序、质量评估、风险分级 |
| **Noul** | 是/否概率 | 校验、断言核查、Agent 护栏 |

> 本站是 **实践与文档聚合**（8 语言），官方模型与 API 仍以 [TypeSafe](https://typesafe.ai/) / [docs.typesafe.ai](https://docs.typesafe.ai/) 为准。

## 快速入口

- 中文站：https://www.jevcode.ai/zh/
- English：https://www.jevcode.ai/en/
- 认识 Jev：https://www.jevcode.ai/zh/introduction/
- 5 分钟上手：https://www.jevcode.ai/zh/quickstart/
- 问题原语：https://www.jevcode.ai/zh/primitives/
- 架构模式：https://www.jevcode.ai/zh/patterns/
- 社区生态：https://www.jevcode.ai/zh/ecosystem/

## 配图一览

文档站配有原创示意图（全部同时提供 WebP 与 PNG 回退）：

| 图 | 用途 |
| :--- | :--- |
| `public/img/hero/pareto.webp` | 首页主图：成本 / 质量权衡 |
| `public/img/docs/architecture.webp` | 架构总览 |
| `public/img/docs/primitives.webp` | 三种问题原语 |
| `public/img/docs/intent-routing.webp` | 意图路由 |
| `public/img/docs/confidence.webp` | 置信度分流 |
| `public/img/docs/composite-scoring.webp` | 组合评分 |
| `public/img/docs/fan-out.webp` | 扇出并行 |
| `public/img/docs/state.webp` | 状态分层 |
| `public/img/docs/sdk.webp` | SDK 语言绑定 |
| `public/img/og.png` | 社交预览图（1200×630） |

## 多语言

站点提供 8 种语言的界面与文档；某篇文档在目标语言缺失时，会自动回退到默认语言并在页面顶部提示。

| 语言 | 入口 | 语言 | 入口 |
| :--- | :--- | :--- | :--- |
| 简体中文 | [`/zh/`](https://www.jevcode.ai/zh/) | English | [`/en/`](https://www.jevcode.ai/en/) |
| 日本語 | [`/ja/`](https://www.jevcode.ai/ja/) | 한국어 | [`/ko/`](https://www.jevcode.ai/ko/) |
| Deutsch | [`/de/`](https://www.jevcode.ai/de/) | Français | [`/fr/`](https://www.jevcode.ai/fr/) |
| Español | [`/es/`](https://www.jevcode.ai/es/) | Português | [`/pt/`](https://www.jevcode.ai/pt/) |

> 中文与英文为人工撰写；其余语言由本地模型翻译，frontmatter 带 `translatedFrom: zh` 标记，
> 仅经结构与构建校验，**未经人工逐篇校对**。欢迎通过 PR 修正术语与措辞；
> 存在歧义时以中文 / 英文原文及官方文档为准。

## 自动化发布管线（Jev 做守门人）

本站的特色：**发布什么、何时发布、是否合格，由 Jev 判断**。整个循环对其他「判断模型 + 静态站」项目可直接参考：

```
每日 09:30（cron）
  │
  ├─ 1. 抓取        scripts/fetch-ecosystem.mjs
  │     GitHub API 刷新 12 个跟踪仓库的 stars/forks/archived
  │
  ├─ 2. 批量累积     小于 +10% 的变化攒着不发，避免琐碎发布
  │     （任一仓库相对增量 ≥ +10% 才触发，批次状态在 pending.json）
  │
  ├─ 3. Jev 门 ①    值得发布吗？（noul）→ 发到哪里？（choice）
  │
  ├─ 4. 机械验证     astro build + astro check + 全量内链检查（16,522 链接）
  │
  ├─ 5. Jev 门 ②    release 合格吗？（noul）→ 风险几分？（score 0-3）
  │
  ├─ 6. 发布         commit → push → 原子软链部署（秒级回滚）
  │
  └─ 7. 留痕         .research/pipeline-logs/*.jsonl 审计日志
                      失败写 ALERT-*.txt，按设计跳过写 SKIPPED-*.txt
```

### 设计原则（踩过的坑）

1. **判断与生成分离**：Jev 只做门控（该不该/哪里/几时/风险），不生成内容——
   这是判断模型的正确定位。已归档的 13 次调用共 13,565 input tokens
   （输出 token 免费），按 $42/Btok 计约 **$0.0006**；单次响应 2–5 秒。
2. **cron PATH 陷阱**：macOS cron 的 PATH 不含 `/opt/homebrew/bin`，必须在
   脚本内显式 export 或 crontab 行内联，否则 node/npm/gh 全找不到。
3. **运行时产物必须脱离 git 跟踪**：管线自己写日志/状态会把工作区弄脏，
   触发「脏区保护」后**永久跳过**——自锁死循环。光写 gitignore 不够，
   已跟踪过的文件要 `git rm --cached` 才真正脱离。
4. **退出码要取真值**：`if ! cmd; then code=$?` 取到的是取反后的值（恒 0）。
5. **告警分两级**：真失败（ALERT）与按设计跳过（SKIPPED）分开留痕，
   否则日常跳过会淹没真故障。
6. **机械门输出别用管道截断**：`npm run check | tail -3` 恰好切掉
   `- 0 errors` 行导致永远误判失败——捕获全量再正则。
7. **非发布路径要还原抓取写入**：fetch 每次写回已跟踪的 ecosystem.ts，
   累积/HOLD/无变化等路径必须 `git checkout --` 还原，Jev 门异常
   （如 402 余额耗尽）同样要还原，否则下一轮脏区跳过。

### 文件索引

| 文件 | 职责 |
| :--- | :--- |
| [`scripts/pipeline.mjs`](./scripts/pipeline.mjs) | 主流程：抓取→累积→双 Jev 门→验证→部署 |
| [`scripts/pipeline-cron.sh`](./scripts/pipeline-cron.sh) | cron 包装：PATH 修复、前置检查、脏区保护、ALERT/SKIPPED |
| [`scripts/fetch-ecosystem.mjs`](./scripts/fetch-ecosystem.mjs) | GitHub 抓取 + 写回 ecosystem.ts（含限流退避） |
| [`scripts/run-jev.mjs`](./scripts/run-jev.mjs) | Jev API 通用调用器（读 JSON 请求→输出响应） |
| [`scripts/i18n-gaps.mjs`](./scripts/i18n-gaps.mjs) | 翻译缺口检查（清单/JSON/骨架，CI 卡点） |
| [`scripts/test-search.mjs`](./scripts/test-search.mjs) | pagefind 索引搜索回归测试 |
| [`.research/jev-requests/`](./.research/jev-requests/) | Jev 决策的请求/响应存档（12 轮决策 + 4 组 playground 预录） |
| [`.research/jev-notes.md`](./.research/jev-notes.md) | 决策笔记：每轮问题、判定、执行结果 |

## 内容结构

```
src/content/docs/<lang>/
├── introduction.md          # 认识 Jev
├── quickstart.md            # 5 分钟上手
├── concepts/                # 状态、置信度、System One
├── primitives/              # choice / score / noul
├── patterns/                # 意图路由、置信度路由、组合评分、扇出
├── sdk/                     # Python / JavaScript / Agent Skill
└── cases/                   # 生态与案例地图
```

## 本地开发

```bash
npm install
npm run dev      # http://localhost:4321
npm run build    # 产出到 dist/
```

Node 20+ 推荐。部署脚本见 [`deploy/`](./deploy/)。

## 仓库结构

```
src/content/docs/{zh,en,ja,ko,de,fr,es,pt}/  # 文档正文
src/i18n/ui.ts        # 界面文案与语言表
src/data/site.ts      # 侧边栏分组、首页卡片
src/data/images.ts    # 配图清单与页面映射
src/pages/            # Astro 路由（含 language fallback）
deploy/               # nginx / 发布 / 回滚
```

## 和官方的关系

- 官方产品：TypeSafe / Jev API
- 本仓库：中文优先的解决方案站 + 模式 / 案例整理，方便工程落地
- 不替代官方 docs；有冲突以官方为准

## License

文档与站点代码以本仓库为准；TypeSafe / Jev 商标与模型归原厂所有。
