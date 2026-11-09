# OpenJev 资料库

Jev / System One 的独立研究、教学书稿与 JevLab 实验代码，整理自 2026-09-19 的最终交付包。本仓库不隶属于 TypeSafe AI；Jev 和 TypeSafe 等名称归各自权利人。

## 三册套书

| 阅读顺序 | 最终版 Word | 同步源稿 | 篇幅 |
| --- | --- | --- | --- |
| 1. 使用与实践 | [Jev 使用文档](books/01_Jev_使用文档_2026-09-19_最终版.docx) | [Markdown](sources/book1/manuscript.md) | 64 页 |
| 2. 原理与研究 | [深入理解 Jev](books/02_深入理解_Jev_2026-09-19_最终版.docx) | [Markdown](sources/book2/manuscript.md) | 196 页 |
| 3. 动手实现 | [动手做一个 Jev：从 MiniJev 到开源 JevLab](books/03_动手做一个_Jev_从MiniJev到开源JevLab_2026-09-19_最终版.docx) | [Markdown](sources/book3/manuscript.md) | 182 页 |

三册合计 442 页，交付清单统计正文与表格中的净中文汉字 190,942。`sources/` 是从最终 Word 反向导出的同步稿，附有原书媒体文件；数字是交付时的快照，不代表独立学术审稿。

## 实验代码与资料

- [JevLab](code/jevlab/README.zh-CN.md)：独立的教学用 System One Runtime，包含 CLI、FastAPI、训练、评测、测试与小型 checkpoint。[英文说明](code/jevlab/README.md) / [评测与限制](code/jevlab/docs/BENCHMARKS.md)。仅 `code/jevlab/` 下的代码遵循其 [MIT License](code/jevlab/LICENSE)，不代表本仓库其他书稿也采用 MIT。
- [Jev 网络资料索引](research/Jev_网络资料索引_2026-09-19.md)：截至 2026-09-19 的官方说明、第三方评测与社区项目索引。原始来源可能更新，以原文为准。

JevLab 的合成 IID 验证集 120 条准确率为 100%，但 16 条人工改写的 OOD 样本只有 62.5%。这不是开放域性能证明，更不能等同于官方 Jev 的实现或能力。高风险动作必须交由确定性的权限、预算和人工审批等控制面决定。

本仓库由交付文件整理；书稿与研究资料未在此声明开放许可证。引用、转载或改编请先确认相应权利。
