# Jev X Tags

用 [TypeSafe Jev](https://typesafe.ai)（System One）给 X/Twitter **账号**打标签，再按你选择的标签 **批量拉黑账号**。

Tag X/Twitter **accounts** with TypeSafe Jev (name / bio / comments), then **batch-block users** whose tag is in your auto-block set.

这是一个 **Chromium Manifest V3** 扩展，基于 [WXT](https://wxt.dev) + TypeScript + React。

> **行为变更：** 旧版用 CSS 隐藏帖子。那是错的。现在的动作是平台级拉黑账号，不是藏 DOM。

## 功能 Features

- 在 `https://x.com` / `https://twitter.com` 观察时间线帖子，以及打开的个人主页
- 从 DOM 读取作者 **显示名、handle、简介（如有）、最近可见评论/帖子文本**，送给 Jev
- 帖子进入视口后再打标（IntersectionObserver + debounce）；后台 service worker 串行调用 Jev
- `primary_tag.choice` 作为账号标签；你勾选的 **auto-block tags** 决定是否入队拉黑
- `should_hide_candidate`（noul）只作为 UI 建议，**不单独拉黑**
- 按 handle 缓存到 `chrome.storage.local`，带 TTL
- 匹配标签的账号进入拉黑队列（pending → blocked / failed），弹窗/选项页显示进度
- 用 **当前已登录的 X 会话**（`ct0` CSRF + 同源 `POST /i/api/1.1/blocks/create.json`）执行拉黑；失败则回退点击原生 Block 菜单
- 拉黑失败 **fail-open**：账号保持可见，记下错误，不假装成功
- 本地保存已拉黑 handle 以及是否确认成功，避免重复刷拉黑请求
- 待拉黑时可淡化帖子，但目标始终是账号拉黑，不再 `display:none` 藏帖
- API key 只存在扩展存储里，仓库不包含密钥

## 安装与开发 Install

需要 Node 20+ 和 [pnpm](https://pnpm.io)。

```bash
pnpm install
pnpm dev
```

`pnpm dev` 会编译到 `.output/chrome-mv3`。在 Chrome / Edge / Brave：

1. 打开 `chrome://extensions`
2. 打开 **开发者模式 Developer mode**
3. **加载已解压的扩展 Load unpacked**，选仓库里的 `.output/chrome-mv3`
4. 点工具栏图标，粘贴 TypeSafe API key（[console.typesafe.ai](https://console.typesafe.ai)），保存
5. 按需编辑标签词表、勾选要 **自动拉黑** 的标签（默认：`spam` / `promo` / `crypto`）
6. 打开 x.com 并滚动。作者旁会出现标签；匹配账号会入队，由当前登录会话执行平台拉黑
7. 需要一次性处理缓存里所有匹配账号时，点 **立即拉黑所有匹配账号**（须打开 x.com 才能真正发出请求）

生产构建：

```bash
pnpm build
```

产物同样在 `.output/chrome-mv3`。

## 选项页 Options

- **API Key**：Bearer token，仅本地存储
- **Auto-block tags**：与作者标签求交则 **拉黑该账号**
- **Tag list**：每项的 description 会作为 Jev Choice `criteria`；`other` 在请求里固定为 `null`
- **拉黑队列**：pending / blocked / failed；已确认的 handle 不会重试
- **TTL**：默认 168 小时
- **清空打标缓存**：丢掉 handle → tag 缓存和日志（**保留**已确认拉黑记录）
- **立即拉黑所有匹配账号**：扫描缓存中标签命中的账号并入队（含失败重试）
- **日志**：最近打标结果、缓存命中、入队/拉黑结果、错误

完整选项页：右键扩展图标 → 选项，或弹窗里的「打开完整选项」。

## 架构 Architecture

```
内容脚本 Content script (x.com)
  MutationObserver + IntersectionObserver
        │  chrome.runtime.sendMessage({ type: "TAG_ACCOUNT" })
        ▼
后台 Service worker
  读 chrome.storage.local 缓存
  未命中则 POST https://api.typesafe.ai/v1/systemone
  标签命中 auto-block → 写入拉黑队列（不重复已确认 handle）
        │
        ▼
内容脚本用当前 X 会话 POST /i/api/1.1/blocks/create.json
  成功 → confirmed
  失败 → 保持可见 + 记录错误（可再试 UI 菜单）
```

Jev 请求体（字段固定）：

```json
{
  "model": "jev-latest",
  "state": { "handle": "", "displayName": "", "bio": "", "recentText": "" },
  "questions": {
    "primary_tag": {
      "type": "choice",
      "instructions": "Pick the best tag for this X/Twitter account based on the state (display name, handle, bio, and recent comments/posts).",
      "criteria": { "spam": "...", "other": null }
    },
    "should_hide_candidate": {
      "type": "noul",
      "instructions": "Is this account the kind the user would typically want blocked (spam, ragebait, crypto promo, etc.)?",
      "criteria": { "true": "...", "false": "..." }
    }
  }
}
```

### 拉黑怎么做 How blocking works

X 网页端拉黑走的是 **已登录 viewer 会话**，不是官方开放 API。我们核对了现有 MV3 / userscript 的常见写法后，采用：

1. **主路径（更稳）：** 同源 `POST https://x.com/i/api/1.1/blocks/create.json`，body 为 `user_id` 或 `screen_name`，请求头带 `ct0` CSRF 与 X 网页客户端公开 bearer（x.com 前端 JS 里的同一个公开 token，不是用户密钥）。
2. **不硬编码 GraphQL `BlockUser` queryId：** 该 id 随 bundle 轮换，容易过期。
3. **失败回退：** 点击帖子/主页溢出菜单里的 Block，再确认。仍失败则记 `failed`，账号保持可见。

权限：`storage`；host：`x.com`、`twitter.com`、`api.typesafe.ai`。

## 测试 Tests

```bash
pnpm test
pnpm compile
pnpm build
```

单测覆盖：DOM 抽取（含 user id / 主页 bio / 评论拼接）、Jev 请求/响应、缓存 TTL、按标签入队、拉黑请求构造与 fail-open 判定、设置里 `hideTags → blockTags` 迁移。没有连真实 TypeSafe 或 X 账号的 e2e。

## 预览选项 UI Preview

不装扩展也能看选项页：

```bash
pnpm preview
```

打开 http://127.0.0.1:43173 （内存状态，不会写入扩展存储）。

## 安全 Secrets

- 不要把 key 写进代码、README 或 git
- 密钥只通过弹窗/选项页写入 `chrome.storage.local`
- 内容脚本拿不到 TypeSafe key；只有 service worker 带 `Authorization` 调 Jev
- X 拉黑发生在内容脚本里，复用你已经登录的 x.com cookie
