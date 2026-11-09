# Jev 导航站 (jev-nav)

基于 Jev 判断模型的应用案例导航站：预渲染的静态站点（`index.html`，由 `data/cases.json` 生成）加上一组只读 JSON API。

线上地址：<https://jev-nav.jevai.workers.dev>

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `public/index.html` | 预渲染站点，由 `build_site.js` 生成，可直接打开 |
| `public/data/cases.json` | 88 个案例 + 分类数据（站点唯一数据源） |
| `public/data/sources.json` | 资料出处 |
| `build_site.js` | 由 `data/cases.json` 重新生成 `index.html` |
| `server.py` | 本地开发后端：静态文件 + `/api/*` 接口（默认端口 8137） |
| `worker.js` | Cloudflare Worker 入口：托管静态资源 + 实现同一套 `/api/*` |
| `wrangler.jsonc` | Cloudflare Workers 部署配置 |

## 本地运行

```bash
node build_site.js          # 需要时重新生成 index.html
python server.py 8137       # http://localhost:8137
```

Windows 上也可以直接双击 `start-server.bat`。

## API

| 接口 | 说明 |
| --- | --- |
| `GET /api/cases` | 全部案例，支持 `?cat=`、`?q=`、`?hot=1` |
| `GET /api/categories` | 分类及每类案例数 |
| `GET /api/stats` | 总数 / 分类数 / 热门数 / 每类计数 |
| `GET /api/sources` | 资料来源 |
| `GET /api/health` | 健康检查 |

本地由 `server.py` 提供，线上由 `worker.js`（Cloudflare Workers）提供。

## 部署到 Cloudflare

推送到 `main` 分支即触发 Cloudflare Workers Builds：`npm run build` 重新生成站点，`npx wrangler deploy` 发布 Worker。

手动部署：

```bash
npm install
npx wrangler deploy
```
