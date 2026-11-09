# Jev 吃豆人环境

一个自带经典吃豆人规则的决策环境，专门为 TypeSafe 的 **Jev**（System One 极速决策模型）设计，同时也可以当普通强化学习环境用。

Jev 不生成文字，只回答结构化问题（Choice / Score / Noul），延迟 70～500ms。所以这个环境每一步都会：

1. 把局面整理成结构化 `state`：分数、命数、幽灵位置和状态、ASCII 地图，以及**每个可走方向的预计算特征**（离豆子几步、离危险幽灵几步、离受惊幽灵几步等）；
2. 把“往哪走”包装成一道 `Choice` 题，选项就是当前能走的方向；
3. 把 Jev 的选择作为动作执行。

| 规则基线（回合制，通关） | 模拟 Jev（实时模式，约 300ms 延迟） |
|---|---|
| ![greedy](demo_greedy_turn.gif) | ![mockjev](demo_mockjev_realtime.gif) |

## 安装

```bash
pip install -r requirements.txt           # numpy, pillow
pip install typesafe-sdk                   # 拿到 Jev 资格后再装
```

## 快速开始

```bash
# 规则基线（回合制）
python run.py --agent greedy --episodes 10

# 离线模拟 Jev（模拟 70~500ms 延迟），实时模式，录 GIF
python run.py --agent mockjev --mode realtime --tick-ms 150 --gif demo.gif --gif-every 2

# 真 Jev（方式一：TypeSafe 官方，需要排队拿资格）
set TYPESAFE_API_KEY=你的key               # PowerShell: $env:TYPESAFE_API_KEY="你的key"
python run.py --agent jev --mode turn --episodes 3
python run.py --agent jev --mode realtime --tick-ms 200

# 真 Jev（方式二：OpenRouter，不用排队，充值即用，只依赖标准库）
set OPENROUTER_API_KEY=你的key
python run.py --agent jev-openrouter --mode realtime --tick-ms 200
```

OpenRouter 方式调用 `POST https://openrouter.ai/api/alpha/decisions`，模型为 `~typesafe/jev-latest`，
会自动使用系统代理并复用长连接。在当前网络下（经 127.0.0.1:7890 代理）实测单次往返约 120ms（不含模型推理时间）。

常用参数：`--ghosts 0~4` 调幽灵数量、`--lives`、`--max-ticks`、`--no-map`（不发 ASCII 地图，减少输入）、`--json result.json` 保存结果。

## 两种模式

| 模式 | 规则 | 考察什么 |
|---|---|---|
| `turn` 回合制 | 环境等模型想好再走一步 | 决策质量 |
| `realtime` 实时 | 环境按 `--tick-ms` 固定节拍前进，模型在后台不停决策；想慢了就错过若干 tick，吃豆人沿用上一个指令 | 又快又准 |

实时模式的结果会多出 `stale_ticks_mean`：决策生效时局面已经过去了多少个 tick。

## 接入 Jev 的代码位置

`jev_pacman/agents/jev.py`

- `JevAgent.from_typesafe()`：用 `typesafe_sdk.TypeSafeClient` 和 `Choice`
- `JevAgent._ask()`：唯一直接调用 SDK 的地方，调用方式是
  `client.system_one(state=..., questions={"move": Choice(instructions=..., criteria={...})})`，
  读取 `response.answers["move"].choice / .probabilities / .confidence`
- 提示语在 `INSTRUCTIONS`，每个选项的描述由 `describe_move()` 生成

以上调用方式来自 Jev 的公开示例。如果正式版 SDK 的字段名不同，只需要改 `_ask()`。
API 报错时不会中断游戏，会沿当前方向继续走，并在结果里记录 `api_errors` / `last_error`。

## 作为强化学习环境使用

```python
from jev_pacman import PacmanEnv, PacmanConfig

env = PacmanEnv(PacmanConfig(obs_type="planes"))   # state | grid | planes | text
obs, info = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step("LEFT")   # 或下标 0~4: NOOP UP DOWN LEFT RIGHT
```

- `planes`：`(7, 31, 28)` 的 float32，通道为墙 / 豆子 / 能量豆 / 吃豆人 / 危险幽灵 / 受惊幽灵 / 眼睛
- 奖励：得分增量；死亡 -200，通关 +500（可在 `PacmanConfig` 中调整）
- 难度：`ghost_speed`（默认 0.9，调到 1.0 更难）、`frightened_ticks`、`schedule`

## 自定义智能体

任何实现了 `act(state) -> "UP"|"DOWN"|"LEFT"|"RIGHT"` 的对象都能直接用 `run_turn_based` / `run_realtime` 跑。

## 规则说明

标准 28×31 迷宫，244 颗豆子（含 4 颗能量豆），左右隧道互通。四只幽灵沿用原版的追踪逻辑（Blinky 直追、Pinky 堵前方、Inky 夹击、Clyde 近了就跑），有分散/追击交替和受惊模式。连吃幽灵依次得 200 / 400 / 800 / 1600 分。为了简化，只有一关，没有水果。
