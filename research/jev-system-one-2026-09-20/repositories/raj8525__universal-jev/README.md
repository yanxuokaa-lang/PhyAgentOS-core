# universal-jev

Universal TypeSafe Jev Runtime Plugin, MCP Server & Autonomous Browser Engine for Coding Agents (Codex, Pi, DSH, OpenCode, Antigravity).

---

## Core Capabilities

1. **Jev-Verified Receipt Extraction (95%+ Token Savings)**:
   - Evaluates lengthy terminal outputs (builds, tests, linters, game engine logs) using TypeSafe Jev System 1.
   - Dehydrates passing logs into high-confidence verified receipts (`[Jev Verified Receipt ✓]`) with 100% transparency to LLMs.
   - Isolates failure/error traces (`[Jev Diagnostic Warning ⚠️]`) while pruning routine output.
   - **Triple Safety Barrier**:
     - **Unified Diff & Patch Immunity**: Git diffs (`diff --git`, `@@ ... @@`) and patch outputs are strictly protected from pruning.
     - **Exit-Code Fast-Path**: Non-zero process exit codes immediately bypass LLM probabilistic guessing with 0ms latency and 100% deterministic diagnostic failure.
     - **Smart Anchor Sampling & Middle Error Isolation**: Automatically scans un-sampled intermediate log regions for errors (`traceback`, `script error`, `exception`), ensuring intermediate crashes (e.g. Godot/Blender/Cargo runs) are never concealed by normal trailing logs.

2. **Universal 2-Tier Browser Engine (`jev-ultrafast` × `browser-use`)**:
   - **Tier 1 (`jev-ultrafast`)**: Sub-second indexed DOM decisions via TypeSafe Jev System 1 (zero vision LLM overhead).
   - **Tier 2 (`browser-use` Fallback)**: Automatically falls back to full multimodal semantic snapshots and visual reasoning when encountering CAPTCHAs, complex canvas, or blocked states.
   - **Zero User Disruption**: Always creates a fresh, isolated Ego Lite TaskSpace, leaving your personal tabs untouched.
   - **Instant Cleanup**: Space is guaranteed to be closed and destroyed immediately upon task completion in a `finally` block.

3. **Verbatim Context Compaction & Auto Image Dehydration**:
   - Compresses bloated conversation history while preserving user instructions 100% verbatim.
   - Automatically dehydrates images after 3 model turns, liberating up to 90% vision token budget.

4. **Fast Decision Primitives**:
   - Millisecond multi-choice classification (`Choice`), boolean hypothesis probability (`Noul`), rubric evaluation (`Score`), and security guardrails (`Guard`).

---

## Installation (初次安装)

Requires Node.js 20+.

```bash
git clone https://github.com/raj8525/universal-jev.git ~/.agents/plugins/universal-jev
cd ~/.agents/plugins/universal-jev
./install.sh
```

Set your API key (Official TypeSafe API or OpenRouter fallback):

```bash
# Official TypeSafe System 1 Endpoint (Recommended)
export TYPESAFE_API_KEY="apikey_..."

# Or OpenRouter Fallback:
export OPENROUTER_API_KEY="sk-or-v1-..."
```

---

## Update & Upgrade (平滑更新)

对于已经安装过的用户，更新过程**100% 平滑、幂等且无损**：

### 方式 1：一键自动更新（推荐）

直接进入项目目录重新运行安装脚本：

```bash
cd ~/.agents/plugins/universal-jev && ./install.sh
```

**为什么推荐直接运行 `./install.sh`？**
- **自动拉取**：脚本会自动检查并执行 `git pull --ff-only` 同步 GitHub 上的最新提交。
- **配置幂等**：脚本内置各 Agent 配置检测（OpenCode, Codex, Antigravity, Pi），**绝不重复添加、不覆盖已有配置**。
- **符号软链接**：全局命令（`~/.local/bin/jev`、`universal-jev-mcp` 等）是指向仓库源码的软链接，更新后立即指向最新代码。
- **自动刷新 Schema**：自动同步 Antigravity 最新的 MCP 工具定义（如 `exitCode` 参数）。

### 方式 2：极简 Git Pull

```bash
cd ~/.agents/plugins/universal-jev && git pull
```

由于 `~/.local/bin/` 下的指令均为软链接，执行 `git pull` 后代码立即更新生效。

### 🔄 各 Agent 生效与重启说明

| Agent 客户端 | 生效方式 | 是否需要重启应用 |
| :--- | :--- | :--- |
| **Codex (GPT-6)** | 每次运行命令独立调用 In-Flight Hook (`codex-hook.js`) | **无需重启！** 下一次在终端执行命令即自动应用最新补丁。 |
| **Antigravity / Gemini** | 通过 MCP Server 连接 | **无需重启 IDE**，新建会话（New Chat）或重连 MCP 即可生效。 |
| **OpenCode / Claude Code** | 通过 MCP Server 连接 | 新建会话（New Session）或重启一次命令行即可。 |
| **Pi Coding Agent** | TypeScript 扩展插件加载 | 重启 Pi 客户端或执行 `/reload` 即可。 |

---

## Usage (使用指南)

### 1. CLI 命令行工具

```bash
# 1. 检查 API 连通性与模型延迟
jev status

# 2. 自主 2-Tier 浏览器任务 (jev-ultrafast -> browser-use 自动降级)
jev browse https://example.com "Verify page title and confirm done"
# 或直接通过专用 CLI:
ego-browse https://www.google.com/travel/flights "Find one-way flights from Zurich to London on Sep 20"

# 3. 布尔真值置信度验证 (Noul)
jev noul "Is this an emergency?" --state "Database CPU 100%"

# 4. 多选项分类 (Choice)
jev choice "Department" --criteria "infra:Server down,billing:Payment issue" --state "Service timeout"

# 5. 标尺评分 (Score)
jev score "Severity" --criteria "low,medium,high" --state "SyntaxError in script"

# 6. 命令安全风控检查 (Guard)
jev guard "rm -rf /"

# 7. 查看 Token 节省数据遥测
jev stats

# 8. 会话历史无损脱水
jev compact transcript.json --out compacted.json
```

### 2. MCP Server 与 Hook 自动集成

运行 `./install.sh` 后，已为各大 Agent 自动注册如下能力：
- **Codex (GPT-6)**：通过 `universal-jev-codex-hook` 拦截工具输出，长日志毫秒级收据化。
- **Pi Agent**：通过 `pi-extension.ts` 实现工具结果脱水与 >=3 轮图片上下文自动瘦身。
- **Antigravity / OpenCode / Claude Code**：通过 `universal-jev-mcp` 暴露核心工具：
  - `jev_receipt`：终端与工具长日志脱水为验证收据（支持 `exitCode` 短路）。
  - `jev_compact`：对话历史上下文无损压缩。
  - `jev_decide_choice`：快速多选项分类。
  - `jev_decide_noul`：布尔假说真值概率评估 ($0.0 \sim 1.0$)。
  - `jev_decide_score`：有序评分标尺。
  - `jev_guard`：高危命令与死循环熔断防护。
  - `jev_status`：服务连通性与延迟探针。

---

## Development & Testing (测试与验证)

```bash
# 运行全量端到端测试 (原语、压缩、MCP Stdio 协议、收据)
npm test

# 运行收据脱水引擎专项测试 (涵盖 Diff 免疫、退出码短路、中间盲区采样等 7 大场景)
node ./test/test-receipt.js
```

---

## License

MIT
