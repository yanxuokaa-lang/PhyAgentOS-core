# Jev 直觉服务

用 [AI SDK 的 `experimental_evaluate`](https://ai-sdk.dev/docs/ai-sdk-core/evaluation) 调用 `typesafe-ai/jev`，替换行为树和状态机里的**判断层**。Jev 不写台词、不生成代码。你给它局面和一组事先声明的问题，它并行返回选项、分数和是非概率。

游戏仍然负责移动、动画和寻路。那些是行为树里会跑很多帧的 Action。这个服务取代的是条件节点和选择器。

## 对照

| 行为树 | 这里 |
| --- | --- |
| Selector | 一次 `choice`。选项必须是游戏真能执行的战术 |
| Condition | `boolean`。灰区标成 `uncertain`，不当成是或否 |
| Utility | `score`。描述的是情境，不是「低/中/高」 |
| Sequence | 不交给模型。模型只选一个战术，游戏自己播 |
| Abort | `interrupt` 为真时，允许一次切换 |
| Blackboard | 请求里的 `scene` / `agent` / `nearby` |
| Running | 留在游戏里。下一拍把 `tactic` 和 `targetId` 原样传回来 |

Jev 的每个问题互相独立，后一个问题看不见前一个的答案。所以环境和角色都只问**一个**决定性的 choice。威胁分、敌意、时机是仪表，不参与投票，否则「逃跑」和「冲上去」会同时成立。

置信度不够时保持上一拍的战术，避免 NPC 每拍抖一次。明确选了 `hold` 会展开成正在执行的战术。`interrupt` 不能推翻这个 `hold`。

## 启动

```powershell
npm install
npm test
npm run demo
npm start
```

服务只听 `127.0.0.1:8787`。不要暴露到公网，否则任何人都能花掉 Gateway 的额度。Key 放在 `.env` 的 `AI_GATEWAY_API_KEY`，不要提交。

Go、Rust、C# 和 C++ 走同一份 JSON 合约，但不依赖 TypeScript SDK。它们直接 `POST https://ai-gateway.vercel.sh/v4/ai/evaluation-model`，带上 `ai-model-id`、`ai-evaluation-model-specification-version: 4` 和 `ai-gateway-protocol-version: 0.0.1`。迟滞、打断和目标绑定与 TypeScript 版相同。

五门语言可以同时跑，默认端口错开。共享的 `.env` 里如果写了 `PORT=8787`，其他语言不会读它，避免撞上 TypeScript 服务。它们只从 `.env` 读取 `AI_GATEWAY_API_KEY`、`JEV_MODEL`、`JEV_TIMEOUT_MS`、`JEV_MAX_RETRIES`。

```powershell
cd go
go test
go run .
```

Go 听 `127.0.0.1:8788`。`GET /health` 的 `language` 是 `go`。

```powershell
cd rust
cargo test
cargo run
```

Rust 听 `127.0.0.1:8789`。`GET /health` 的 `language` 是 `rust`。

```powershell
cd csharp
dotnet test Jev.Tests/Jev.Tests.csproj
dotnet run --project Jev.csproj
```

C# 听 `127.0.0.1:8790`。`GET /health` 的 `language` 是 `csharp`。

```powershell
cd cpp
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Debug --target jev-tests
.\build\Debug\jev-tests.exe
cmake --build build --config Debug --target jev
.\build\Debug\jev.exe
```

C++ 用 MSVC 编译，HTTPS 走 Windows 自带的 WinHTTP。听 `127.0.0.1:8791`。`GET /health` 的 `language` 是 `cpp`。

如果调用返回 403，且原文提到 credit card：key 已经被 Gateway 认出来了，是账号还没绑信用卡。到 Vercel 的 AI 页面加上卡、解锁免费额度后，同样的请求就会打到 Jev。

模型默认 `typesafe-ai/jev`。字符串模型 id 走 Vercel AI Gateway，所以用的是 Gateway key，不是 TypeSafe 自己的 key。

## 接口

`POST /v1/impulse` 一个角色。`POST /v1/world` 环境拍子。`POST /v1/tick` 同一局面下的环境和最多 16 个角色，默认 4 路并发。

`GET /health` 只报告模型名，不报告 key。

角色预置：`guard`、`civilian`、`predator`、`companion`、`ambient`。自定义角色必须自己传 `tactics`。选项 id 用英文，描述可以写中文，但要写情境，不要写「比较危险」。

环境预置拍子：`hold_atmosphere`、`tighten_patrol`、`fog_stalk`、`ambush_now`、`release`、`seal_escape`。游戏把拍子映射到天气、刷怪和关门。不要把这三件事拆成三个 choice。

血量用 0 到 1。`health <= 0` 不再调用模型，直接返回 `incapacitated`。距离由游戏算好再传。不同阵营不会自动变成敌人，敌意是判断，不是几何。

建议角色 2–4Hz，环境 0.5–1Hz。不要放进 60 帧的 Update。输入大约每百万 token 0.042 美元，输出不另计。

## 游戏循环

```text
每拍：
  收集黑板（位置、血量、看得见谁、上一拍战术）
  POST /v1/tick
  disposition=incapacitated → 播死亡
  否则按 tactic + targetId 继续或切换本地动作
  下一拍把 tactic、targetId、secondsOnTactic 传回来
```

`because` 说明这次为什么换或为什么没换：`confident`、`interrupt`、`hysteresis`、`still-fitting`。调 `policy.switchConfidence`（默认 0.72）和 `policy.interruptAt`（默认 0.75）即可，不用改模型。

示例请求在 `examples/impulse.json`。

```powershell
curl.exe -s http://127.0.0.1:8787/v1/impulse -H "content-type: application/json" --data-binary "@examples/impulse.json"
```

`npm run demo` 跑一座黄昏礼拜堂：守卫、平民、狼，外加环境拍子。玩家走位是脚本，战术由上一拍的返回喂回去。
