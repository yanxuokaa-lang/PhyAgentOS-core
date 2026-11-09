# 收集范围与方法

## 查询与发现

使用 GitHub 公共 repository search API，查询包括：

- `jev typesafe created:<2026-09-19`
- `jev typesafe created:>=2026-09-19`
- `"typesafe.ai"`
- `"system one" "typesafe"`
- `topic:jev`
- `"openjev"`
- `"jev" fork:only`

按 full_name 去重；保留各查询分页与 GitHub total_count/incomplete_results。created 日期切分用于降低单查询 1000 项上限影响。宽泛 fork 查询包含无关仓库，不能用来计算“二次开发项目总数”。

先从 yibie/awesome-jev、AbdelStark/awesome-typesafe、cobanov/awesome-jev 的外链找到入口，再读取官方 docs 与重点源码。精选表只作为发现线索。

## 实际覆盖与缺口

初轮遇到匿名 GitHub search 403 限流。后续补取了新建时间段的第 4–6 页，以及 typesafe.ai 的第 1–4 页；`system one typesafe` 在补取第 4 页再次限流，topic:jev 也未成功。宽泛 fork 查询在第 10 页前停止，且全量超过 GitHub 单查询 1000 项可取上限。

最终候选元数据包括补取新增的仓库；大规模 README 下载在补取前完成，因此并非每个最终候选都有本地 README。每个获取失败的 HTTP 响应原样保留，可在来源索引查状态。未执行登录态全站 code search，未获取私人/删除仓库，也未穷尽所有 PR 评论、issue 评论、分支和历史提交。

抓取跨几分钟，total_count 与 pushed_at 可能变动；由分页移动导致的漏项/重复风险不靠去重完全消除。这个包是广泛发现加重点源码研究，不是某一瞬间的全站数据库。

## 源码快照

通过 GitHub codeload 下载重点仓库默认分支 main/master 的 zip，按相对路径保存选定文本。未执行其中代码。跳过权重、图片/视频、二进制、大于 1.5 MB 的单文件、node_modules、dist、vendor、lock 文件和未选定后缀。多数 JSONL 原始数据未保存；需要重跑时应取原仓库完整环境和数据。

快照来源为 branch URL，记录了抓取时间；后续取到的 recent commit 列表用于开发时间线，不伪称 archive 已按某个 SHA 严格固定。原许可证文件随可取源码保存；本包不改写上游许可证。

## 证据层级

1. 官方服务文档 / 官方 SDK 和 Adapter 源码。
2. 本轮读取的独立项目具体函数与控制流，链接本地行号。
3. 仓库已发布但本轮未复跑的结果。
4. README 自述、精选列表、未深入检查的检索候选。
5. 黑盒架构推断：用来指导实验，不充当私有架构的确证。

## 文件检查

收尾检查只检查本包自己的索引可解析、源文件存在、Markdown 本地链接与行号有效、UTF-8 可读；没有执行外部项目测试、训练、GPU 推理、付费 API、网页动作或机器人控制。检查结果见 validation-summary.json。

没有修改项目日志或执行任何 Git 写入操作。原工作区已有改动保留。
