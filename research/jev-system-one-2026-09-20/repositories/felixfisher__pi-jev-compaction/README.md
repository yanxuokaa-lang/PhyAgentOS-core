# pi-jev-compaction

**Experimental** Pi Coding Agent extension. It uses TypeSafe Jev to judge old tool calls one by one, then stores an auditable, provider-neutral replay. User text and assistant prose stay verbatim.

**实验性** Pi 扩展：用 TypeSafe Jev 对旧工具调用做逐项判断，生成可审计、跨模型的精简回放。用户文本和助手正文默认逐字保留.

> New installs are **disabled** (`enabled: false`). `enabled` only gates **new** TypeSafe API requests.  
> Stored `pi-jev-compaction` details can still be replayed locally when disabled.  
> 新安装默认 **关闭**。`enabled` 只控制是否发起新的 TypeSafe 请求；已写入的 details 仍可本地重放。

Inspired by [`tamaratran/fast-jev-compaction`](https://github.com/tamaratran/fast-jev-compaction). This package is a Pi adapter with its own pairing, persistence, and replay layer; it does not copy that repository's source.

---

## English

### What it is

- A Pi package loaded with `pi -e ./` or `pi install <path>`.
- On `session_before_compact`, it pairs tool calls with results, asks Jev two Noul questions per pair, then keep / truncate / drop.
- Replay is stored in `compaction.details`. Original session JSONL history is not rewritten.
- On `context`, a matching compaction summary is replaced with `replayMessages` when the match can be proven. Otherwise it fails open.

It is **not** a prose summarizer and **not** OpenAI native compaction.

### Requirements

- Pi Coding Agent **0.85.1+**
- Node.js **>= 22.19.0** (Pi 0.85.1 uses `fs.globSync` and declares `engines.node >=22.19.0`)

### Install

```bash
pi -e ./ --no-session
# or
pi install /absolute/path/to/pi-jev-compaction
```

Set `TYPESAFE_API_KEY` in the environment. Never put the key in JSON.

### Explicit enable

1. Read this README and the privacy section.
2. Copy `2026-09-18_jev-compaction.example.json` to `~/.pi/agent/jev-compaction.json` (or `$PI_CODING_AGENT_DIR/jev-compaction.json`).
3. Set `"enabled": true`.
4. Restart Pi and check `/jev-status`.

Project override: `<cwd>/.pi/jev-compaction.json`, only when the project is trusted.

### Privacy / data flow

`enabled: false` (default) does not call TypeSafe. Matching local compaction details are still replayed.

When enabled, a Jev request sends: secret-redacted, truncated **short user/assistant text snippets**; tool names; redacted/truncated argument summaries; result lengths, error flags, and short tags. It does **not** send full toolResult bodies.

### Config

| Field | Default | Notes |
| --- | --- | --- |
| `enabled` | `false` | Must be true to send new TypeSafe requests. Local replay of stored details still runs when false. |
| `model` | `jev-latest` | TypeSafe model alias |
| `keepThreshold` | `0.5` | Clamped to `[0,1]` |
| `preserveRecentMessages` | `6` | Recent window is protected |
| `protectTools` | `["edit","write"]` | Always kept |
| `protectErrors` | `true` | Error results kept |
| `minReductionRatio` | `0.25` | Fail open if savings are too small |
| `targetReplayTokens` | `80000` | Warning above this |
| `maxReplayTokens` | `100000` | Fail open above this (`max_replay_tokens`) |
| `privacyMode` | `balanced` | `off` / `balanced` / `strict` |
| `timeoutMs` | `15000` | Per TypeSafe request |
| `maxRetries` | `2` | 429/529 only |

Invalid fields warn and are ignored. `maxReplayTokens` is raised to `targetReplayTokens` if inverted.

### Fail-open

Missing key, HTTP 401/422, timeout after retries, malformed answers, `minReductionRatio`, or `maxReplayTokens` → return `undefined` and let Pi native compaction run.

### Uninstall

Remove the package from Pi settings (`pi remove <path>` or delete the `packages`/`extensions` entry) and delete `jev-compaction.json` if you created one.

### Limits

- Experimental. Thresholds are not calibrated for every workflow.
- Do not load two custom compaction extensions in one session; hook order is undefined.
- Token budget uses a chars/4 estimate, not the provider tokenizer.
- Config directory name uses Pi's `CONFIG_DIR_NAME` (usually `.pi`) and `PI_CODING_AGENT_DIR`.
- `/jev-preview` is not in this release.

### Related work

| Project | Difference |
| --- | --- |
| `tamaratran/fast-jev-compaction` | Claude Code hook; this package is a Pi extension with session `details` replay |
| `@lll9p/pi-better-compaction` | OpenAI Responses native compaction / provider payload rewrite; this package stays provider-neutral |

---

## 中文

### 定位

用 Jev 判断旧工具调用是否仍有价值，而不是写一段摘要。精简结果仍是标准 `AgentMessage`，可供任意模型继续使用。

### 要求

- Pi Coding Agent **0.85.1+**
- Node.js **>= 22.19.0**（Pi 0.85.1 使用 `fs.globSync`，官方 engines 为 `>=22.19.0`）

### 安装

```bash
pi -e ./ --no-session
pi install /absolute/path/to/pi-jev-compaction
```

API Key 只走环境变量 `TYPESAFE_API_KEY`。

### 显式启用

1. 阅读隐私说明。
2. 将示例配置复制到 `~/.pi/agent/jev-compaction.json` 或 `$PI_CODING_AGENT_DIR/jev-compaction.json`。
3. 把 `enabled` 设为 `true`。
4. `/jev-status` 确认。

受信项目可用 `<cwd>/.pi/jev-compaction.json` 覆盖。

### 隐私与数据流

`enabled` 只控制新的 TypeSafe 请求。默认关闭时不访问 TypeSafe，但已有 `pi-jev-compaction` details 只要 marker 匹配且结构安全，仍会本地重放。

启用后，Jev 请求会发送：经过脱敏和截断的短用户/助手文本片段；工具名；脱敏/截断后的参数摘要；结果长度、错误标志和短标签。**不发送完整 toolResult 正文。**

### 失败回退

缺 Key、API 失败、答案异常、压缩收益不足、回放超过 `maxReplayTokens` 时，交给 Pi 原生 compaction。

### 卸载

从 Pi 设置中移除本包，并删除自建的 `jev-compaction.json`。

### 已知限制

实验性质；不要与其它自定义 compaction 扩展同时抢 `session_before_compact`；token 预算为字符/4 估算。

### 固定入口文件名

`package.json`、`README.md`、`LICENSE`、`tsconfig.json`、`CHANGELOG.md`、`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`.gitignore`、`.github/workflows/ci.yml`、`extensions/index.ts`、`package-lock.json` 为框架/约定固定名，不加日期前缀。其余源码与测试使用 `2026-09-18_` 前缀。

## License

MIT. See `LICENSE`.
