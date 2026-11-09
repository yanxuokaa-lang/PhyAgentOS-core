# jev-grug-zh

> 中文候选，逐单元选择。

这是 [`mkotlikov/jev-grug`](https://github.com/mkotlikov/jev-grug) 的独立中文 fork。它保留上游的 Jev Choice tournament 实验思路，但重新设计了中文候选、拼接和重复控制，不是把英文词表逐项翻译后直接替换。

## 许可证与归属

本项目继续使用上游的 **MIT License**。上游的 [`LICENSE`](./LICENSE) 文件和原版权声明保持不变；新增中文代码、词表、界面和文档也按本 fork 的 MIT 许可发布。详细归属见 [`NOTICE.md`](./NOTICE.md)。

这只说明仓库中的软件代码许可，不代表 Jev API 的服务许可。Jev 是 TypeSafe AI 的产品，本项目不隶属于、也未获得 TypeSafe AI 背书。使用真实 API 前，应单独阅读并遵守 TypeSafe AI 当前的 API 文档、服务条款、用量限制及适用法律；不要把 API key 放进浏览器端，也不要把服务输出用于违反其条款的用途。

## 功能

- **单字模式 `char`**：每轮从常用汉字、动态主题字和中文标点中逐个选择。
- **词语模式 `word`**：以高频中文词语为主要候选，适合更快形成短句。
- **混合模式 `mixed`**：同时允许词语和单字，作为默认折中模式。
- **中文标点**：`，。！？；：、` 是独立 Choice 候选，格式化时不会被错误地加空格。
- **动态词汇**：从用户最近消息提取主题词，经 `noul` 判断后临时加入候选；数字直接保留。
- **重复控制**：最近单元暂时屏蔽，单元达到重复上限后屏蔽，并检测短周期循环；请求状态中也明确记录重复惩罚信息。
- **END 机制**：`end` 是控制选项，不会进入正文；达到模式上限仍未结束时会显示省略号。
- **无 key mock fallback**：没有配置 `TYPESAFE_API_KEY` 时使用确定性的中文 mock，便于本地检查 UI、请求格式和三种模式。

## 工作方式

每一个输出单元都经过两阶段：

```text
中文候选池
    │ 按最多 249 个候选分组
    ▼
每组 Choice tournament
    │ 每组取概率最高的少量 finalist
    ▼
final Choice → 一个中文单元或 end
    │
    └── 重复，直到 END 或达到上限
```

真实 Jev 请求使用上游当前项目采用的 HTTP 形状：

```json
{
  "state": {
    "conversation": [{ "role": "user", "text": "请解释人工智能。" }],
    "tokens_so_far": ["人工智能", "用"],
    "conversation_vocabulary": ["人工智能"],
    "generation_mode": "mixed",
    "repetition_penalty": {
      "recent_tokens": ["人工智能", "用"],
      "max_token_repeats": 2
    }
  },
  "model": "jev-latest",
  "questions": {
    "next_token": {
      "type": "choice",
      "instructions": "...",
      "criteria": { "数据": null, "end": "中文回复已经完整，应停止输出。" }
    }
  }
}
```

服务端只向 `https://api.typesafe.ai/v1/systemone` 发认证请求，浏览器只调用本项目的 `/api/chat` 路由。

## 本地运行

要求：Node.js `>=22.13.0`。

```bash
npm install
copy .env.example .env
# 可选：在 .env 中填入 TYPESAFE_API_KEY；不填则使用 mock fallback
npm run dev
```

打开终端显示的本地地址。生产构建：

```bash
npm run build
```

代码质量检查：

```bash
npm run lint
npx tsc --noEmit
```

## 目录

```text
app/
  api/chat/route.ts    server-only API route and Jev loop
  page.tsx             Chinese chat UI and mode picker
  globals.css          visual system and responsive layout
  layout.tsx           Chinese metadata and fonts
lib/
  jev.ts               Chinese request builders, modes, formatting, repetition control
  zh-vocabulary.ts     curated Chinese character/word candidates and punctuation
  mock-jev.ts          deterministic Chinese fallback
NOTICE.md              upstream attribution and service disclaimer
LICENSE                upstream MIT License, retained unchanged
```

## 上游核验记录

实现基于 2026-09-18 本地读取的上游 `mkotlikov/jev-grug`，核验提交为 `93bca7a1fe03ed0115e9ec67a11e26e21c30fd98`。上游当前仓库公开标注 MIT License，项目使用 TypeScript/React/Vinext，README 说明了 `choice`、`noul`、`jev-latest` 和 `POST /v1/systemone` 的调用方式。

这份 fork 不包含任何 API key、GitHub 凭据或私密配置。
