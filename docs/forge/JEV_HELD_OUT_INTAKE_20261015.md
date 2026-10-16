# JEV 专项留出候选入库 / Held-out Candidate Intake

## 采集前计划 / Preregistered Scope

2026-10-15 18:18 Asia/Shanghai，基础提交 c3c0bede；计划文件首次保存时间为 18:18:54，
配置保存于 18:19:16，早于下述首次采集。初写标题误填 18:20，现按实际首次保存时间校正；没有新 JEV/System-2 评分。

- 近期任务库只读检查：2026-10-15 08:20 UTC 后新增任务 0；10 月 12 日以来任务仍属于既有 RGB benchmark 家族。
- 校准家族：blocks_ranking_rgb 及相同红蓝绿方块的近重复语义选择，不通过改 seed、任务名或时间戳重新标成留出。
- 新来源计划：RoboTwin `put_bottles_dustbin`，seed 103 和 104，每场景一次同步 head/front 观测和一次本地视觉解释。
- 分组单位为瓶类工作流家族，两场景不视为两个独立工作流；拟定每场景两项目标：唯一可辨认的垃圾桶选择，以及不存在的紫色方块应升级。
- 共 2 次场景采集、最多 4 个待标注决策案例。该小批次只检验入库可行性，不是正式样本量或六类验收完成证明。
- 仅复用已提交 Adapter 导出 4059b373、既有采集器和原 profile 结构；不加载并行实验室改动。
- 禁止 play_once、Action/Session 和任何动作调用；图片只发已授权本机 Qwen，脱敏后 JEV/System-2 请求本批暂不发送。
- 若目标缺失、歧义、候选不足、采集失败，保留原记录，不替换 seed 挑成功例，不删失败分母。
- 在模型评分前记录标签和依据；若本批用于调参、修代码或修改接受策略，相关家族转为开发数据，不再算该版本留出。

## 六类覆盖与边界 / Coverage and Limits

| 原工单类别 | 当前证据与下一项 |
| --- | --- |
| 多实体 | 既有 RGB calibration 已测；瓶类为不同物体家族的待复核候选 |
| 无适用项 | 既有紫色目标 calibration 已测；本批同样预登记负例，不强行指定其他对象 |
| 跨场景 | 两个新场景是来源多样性，不等于旧场景引用/结果失效的负例；后者须通过原宿主身份检查验证 |
| 多方法 | 当前 scene.bind runner 只装载一个 ToolSpec；需真实多方法决策输入，不能给实体样例改类别标签 |
| 非法组合 | 需保留来源组合和拒绝证据；不能仅以不存在的颜色充当非法输入组合 |
| 复杂规划 | 需原图/方法边界上的升级样例；不把普通实体选择包装成复杂规划 |

## 独立复核与 provenance / Review and Provenance

用户已授权 Codex 复核。本执行者可核对原图、来源与标签，并记录自审；同作者再检查不等于独立标签复核。
正式接受条款尚需另一个未参与标签编写和调试的复核者确认。此项不能通过改 reviewer_id 满足。
服务曾返回 jev-1.13.0 和 gpt-5.6-sol；后者没有更细部署身份。返回模型别名不证明固定权重、路由或服务配置。
生产继续 off/shadow；本轮不申请或启用 motion/active，不新增 hash、数据库或门禁。

## 实际结果 / Actual Results

首轮实际运行目录：
`artifacts/evals/jev-held-out-intake/20261015-bottles/captures/seed-103/20261015T101916.708582Z-964894fb/`。

- 实际尝试 1/2 次；seed 103 返回 `observation_unavailable`，观测错误为 `sensor_unavailable`。
- `worker.log` 保留直接原因：

```text
BlocksRankingRgbTaskAdapterError: task adapter blocks_ranking_rgb does not support put_bottles_dustbin
```

- worker 在 `RoboTwinPersistentEngine.__init__` 的 `task_adapter(runtime["task_name"])` 阶段退出。
  `task_adapter` 固定构建 `BlocksRankingRgbTaskAdapter` 并校验任务名；当前仓库与导出版本同样仅支持 RGB。
- 图像 0、可用理解 0、可标注候选案例 0、JEV/System-2 请求 0、Action/Session 调用 0。
  `local_model_diagnostics.json` 为空数组；没有运行 `play_once`，没有启动任务动作。
- seed 104 记为 `not_attempted_shared_adapter_blocker`，不是第二次采集失败，也不是成功样例。
  更换 seed 不能改变 Adapter 支持范围，因此停止重复尝试。
- 不把 `observation_unavailable` 当作独立语义留出案例；没有足够事实构造本次预登记决策。
  不删除失败目录，不更换工作流名伪装适配成功，不解除原任务类型检查。

## 继续所需范围 / Required Next Scope

推荐：单独批准实现多任务的只读观测适配，使新工作流能沿原 worker/ObservationEndpoint 输出真实观测。
保持动作能力未接入/不可达，不默认扩展抓取、绑定、规划、执行或成功验收。这是 Adapter 能力扩展，
不是修改评测标签或配置即可完成，且需避开工作区并行实验室 Runtime 改动。

备选：提供其他工作流已有的真实、完整、未参与调试的决策时刻快照及来源记录，直接用隔离宿主验收，
不扩展 Runtime。但它们仍需合格候选、分组隔离、六类覆盖、独立复核及模型部署 provenance。

在选择前不自动实现新的多任务 Runtime。当前 intake 交付的是可追溯的能力边界与失败记录，
不是新增有效 held-out 数据，P3b 仍未完成。

## 复现与只读验证 / Reproduction and Read-only Verification

以下命令是已经执行过的首次采集；在 Adapter 支持范围改变前不建议重复运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" \
  /home/yanxu/miniconda3/envs/paos/bin/python scripts/capture_jev_observation.py \
  --config artifacts/evals/jev-held-out-intake/20261015-bottles/capture-103.json
```

只读核对失败与零模型调用（无需启动 Runtime）：

```bash
jq '{status, action_calls, session_calls, remote_model_calls}' \
  artifacts/evals/jev-held-out-intake/20261015-bottles/captures/seed-103/20261015T101916.708582Z-964894fb/summary.json
jq 'length' \
  artifacts/evals/jev-held-out-intake/20261015-bottles/captures/seed-103/20261015T101916.708582Z-964894fb/local_model_diagnostics.json
```

七维结论：所有权和原任务类型检查保留；未伪造候选或成功；失败日志可追踪；未重试/复用旧场景；
no-motion 和图片本地边界不变；没有生产代码或配置变更；共一次失败尝试，第二次因同一已知原因未发起。

## 只读观测适配复验 / Read-only Observation Adapter Recheck (2026-10-16)

为处理上述已确认的 Adapter 支持范围阻塞，新增了独立只读 worker。它只加载
`RoboTwinSensorBackend`，执行官方任务的 `reset` 和同步 `capture_sensor_set`，不构造
`RoboTwinPersistentEngine`，不注册任务目标/绑定/规划，不接受 `start`/`poll`/`cancel`，也不调用
`play_once`、Action 或 Session。请求预算通过配置外置为 120 秒，以覆盖首次 RoboTwin 渲染的进程请求时间。

两次新的现场观测均成功，但仍不是可评分的 held-out：

- seed 103：
  `artifacts/evals/jev-held-out-intake/20261016-bottles-readonly/captures/seed-103/20261016T104929.254450Z-e7fe8dcc/`，
  `put_bottles_dustbin-103-1`，双视角、5 个实体、0 ambiguity、本地理解约 10.8 秒。
- seed 104：
  `artifacts/evals/jev-held-out-intake/20261016-bottles-readonly/captures/seed-104/20261016T105009.167217Z-fac2ac0b/`，
  `put_bottles_dustbin-104-1`，双视角、4 个实体、0 ambiguity、本地理解约 8.0 秒。
- 两个观测都只看到三个瓶子、白桌和背景；没有可确认的垃圾桶。因此预登记的“唯一垃圾桶选择”
  没有合格候选，不能改写为选择某个瓶子或把缺失目标标成成功；不存在的紫色目标也只能保留为
  待独立标签确认的升级候选。两次 `remote_model_calls=0`、`action_calls=0`、`session_calls=0`，
  `host_selection_measured=false`。
- 先前 `blocks_ranking_rgb` Adapter 失败目录仍保留；新 worker 的修复样本不计入正式 held-out，
  也没有触发 JEV/System-2 配对或修改接受策略。

本轮因此证明了“其他 RoboTwin 工作流可产生真实只读观测”的能力边界，但没有增加有效质量样本。
正式 P3b 仍需要预登记一个实际包含可判定目标和负例的工作流/场景，并在标签冻结后做完整配对、
独立复核和部署 provenance 确认。
