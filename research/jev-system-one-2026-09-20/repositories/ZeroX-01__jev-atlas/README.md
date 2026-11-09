# JEV Atlas

一个中文优先、保留原始出处的 TypeSafe JEV 社区内容索引。基于 React、TypeScript、Vite，支持静态部署。

公网地址：https://zerox-01.github.io/jev-atlas/

## 启动

```sh
npm install
npm run dev
```

打开 http://127.0.0.1:5173/ 。

```sh
npm run build
npm run preview
npm test
```

`dist/` 为静态发布产物。默认部署在域名根路径。案例详情采用 `#case/<id>`，静态服务器不需要额外的路由重写。

## 功能

- 中英文关键词、原文与作者搜索。
- 场景、视频/图文/开源、来源的组合筛选。
- 精选/时间/来源浏览量排序，网格和列表视图。
- 真实视频预览、详情播放、原文与中文参考译文、源码和出处链接。
- 精选专题、收藏、新增个人线索、导出筛选结果与个人备份、导入合并备份。
- 键盘搜索快捷键 `⌘/Ctrl K`，原生对话框与 `Esc` 返回。
- 手机适配、加载/空白/失败状态、减少动态效果偏好。

## 收录与边界

初始整理时间：2026-09-20，后续自动增量收录。

- 202 条 X 记录来自用户指定的 [QMuse 公开索引](https://render.qmuse.pub/p/muse/8079593307628562/index.html)。
- 补充 7 条公开项目或资料，来源包括 GitHub/Gist、Callstack、DEV、TypeSafe 官网。
- 初始合计 209 条公开内容，其中 203 条带视频，6 条纯图文或项目说明；17 条带可识别的源码仓库链接。后续数量由当前数据计算。
- 30 条重点记录整理了中文标题与摘要；其余保留来源提供的正文或参考译文。
- 已接入 QMuse、GitHub、DEV、Hacker News 的定时收录，**不是全网完整覆盖**。X 内容通过 QMuse 索引跟踪，尚未直接连接 X / YouTube / B 站 / 小红书搜索 API。来源删除内容时不会自动删除本站历史记录。
- 新发现的 GitHub、DEV、Hacker News 链接先标为「自动收录 · 待核验」，归入「资料与讨论」。只有包含独立的 Jev 词及 TypeSafe / AI / 模型等上下文的公开元数据才会进入；关键词判断可能漏掉相关内容或误收同名内容，不能代替人工核验或项目运行验证。
- 场景分类对重点条目采用人工标注，其余采用关键词规则，后续可继续校正。每条内容保留来源和核验说明。
- 播放与互动指标是来源快照，不是实时数据。外部视频的可访问性由原托管方决定，失效时仍可打开原帖。
- 收藏与新增记录保存在当前浏览器的 `localStorage`，不跨设备同步，不会公开提交。清理浏览器数据前应导出备份。

所有正文、视频与项目归原作者所有。本站提供索引和来源入口，生成图形没有被用作案例截图。

## 持续收录

```sh
npm run collect                         # 立即执行一次
npm run collect -- --dry-run             # 检查来源和新增数量，不写入
npm run collect -- --sources=dev,qmuse    # 只运行指定来源
npm run collect:install                  # macOS 安装/更新后台任务，并立即运行
npm run collect:status                   # 查看实际注册状态、执行结果与来源错误
npm run collect:run                      # 请求后台任务立即执行，不重复启动
npm run collect:stop                     # 卸载定时任务，保留全部数据与备份
```

当前配置为 **每 6 小时**，修改 `collector.config.json` 的 `intervalHours` 后重新执行 `npm run collect:install` 即可更改频率。最低 1 小时。配置中也可以禁用单个来源、调整检索词、请求超时和分页上限。

公网版本使用 `.github/workflows/deploy-pages.yml`：每 6 小时运行采集、提交更新后的数据、构建并发布到 GitHub Pages，不依赖这台 Mac 开机。GitHub Actions 运行时使用仓库自带的 `GITHUB_TOKEN` 提高 GitHub API 配额，不需要提交个人 token。

本地备用定时任务使用 macOS LaunchAgent，名称 `pub.jevatlas.collector`，配置位于 `~/Library/LaunchAgents/pub.jevatlas.collector.plist`。它在用户登录时启动，需要这台 Mac 开机、用户已登录且能联网。休眠期间不执行，恢复后的调度由 launchd 处理；不会主动唤醒机器。移动工程或 Node 路径后应重新安装任务。

| 来源 | 采集方式与限制 |
| --- | --- |
| QMuse / X 索引 | 读取公开页面数据块，用 TypeScript AST 解析 JSON 常量，不执行远端 JS。上游索引不更新时不会发现新的 X 帖子。 |
| GitHub | 搜索含 Jev / TypeSafe 的仓库元数据，排除 fork 与 archived。按固定更新时间窗口分页；结果多时拆分窗口并保存待补采队列，每轮最多 6 个搜索请求。不能保证 GitHub 搜索未索引、刚发生变更的内容全覆盖。 |
| DEV | 分页读取 `jev` / `typesafe` 标签文章；保留 48 小时重叠时间范围，关键词过滤。标签接口不是全文搜索。 |
| Hacker News | 通过公开 Algolia 索引搜索标题与正文，关闭模糊拼写，再匹配 Jev 和 AI 上下文；保留讨论原帖地址。 |

GitHub 无需登录即可使用公共配额。遇到 403 / 429 时记录错误，下个周期再试，不会连续重试消耗配额。需要更高配额时，可以自行在未提交的 `.env.collector` 设置 `GITHUB_TOKEN`；后台任务会读取它，token 不写入网页、数据或日志。手动执行时可用 `node --env-file=.env.collector scripts/collect.mjs`。

每次按规范化 URL 去重合并，保持已有 ID、原始视频及首次收录时间。其他社区引用已知链接时，不会覆盖已整理条目的作者或正文。`excludeUrls` 用于排除本站等循环收录目标。来源异常不会清空历史内容，也不会提前推进失败来源的时间进度。结果、分页游标与数据在同一 JSON 快照中原子提交，进程锁防止重叠运行；崩溃遗留锁会在确认原进程退出后恢复。

只保留最近 10 份变更前备份，以及最近 40 次执行摘要。文件位于：

- `.collector/backups/`：可恢复的数据快照。
- `.collector/last-run.json`：本轮结果。
- `.collector/launchd.out.log` / `launchd.err.log`：后台日志，超过 2 MB 在下次启动轮换。
- `public/data/source-cases.json` 的 `collection`：各来源状态、补采游标、更新历史。

网页每分钟（仅可见时）和恢复到前台时检查已发布数据，失败时保留已显示的内容。页底「来源更新」可查看上次检查、各来源新增数与异常。采集也同步本机 `dist/data`；GitHub Actions 会在每次采集后重新发布公网版本。

如果需要脱离这台 Mac 24 小时运行，可将完整项目放到常在线服务器，用 Node 22+ 与 cron 执行 `npm run collect`，并把站点的数据文件指向该目录。示例（路径需替换）：

```cron
17 */6 * * * cd /path/to/JEV_collect && /absolute/path/to/node scripts/collector/scheduled.mjs >> .collector/cron.log 2>&1
```

GitHub Pages 只托管静态文件；个人收藏和手动新增内容不会上传到仓库。

## 内容维护

补充来源编辑 `src/data/supplemental.json`；重点条目的中文标题、摘要、分类和排序编辑 `src/data/editorial.json`。`npm test` 检查 URL、去重、分类筛选、来源字段和备份边界。

数据文件：

| 文件 | 用途 |
| --- | --- |
| `public/data/source-cases.json` | 累积来源记录、原文、视频、链接、引用、采集状态与时间 |
| `src/data/supplemental.json` | 独立补查的公开来源与核验说明 |
| `src/data/editorial.json` | 中文整理与精选顺序 |
| `src/lib/catalog.mjs` | 数据规范化、分类、去重、组合检索、个人导入校验 |
| `collector.config.json` | 周期、来源开关、查询范围、超时和分页预算 |
| `scripts/collector/` | 来源适配、增量合并、锁、备份与定时入口 |
| `PRODUCT.md` / `DESIGN.md` | 产品范围和设计约定 |

## 参考设计

- QMuse 案例库：原帖索引、作者、视频、引用与外链。
- TypeSafe 官网：黑白文字层级、细线、点阵计算图形。
- 点阵主视觉用原生 Canvas 绘制，在不可见时跳过绘制，并尊重 reduced-motion。

图像生成服务本次返回了服务占位图，未用于页面；成品使用原生交互图形和真实视频帧。
