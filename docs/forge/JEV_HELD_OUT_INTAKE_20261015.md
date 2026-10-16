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

## `stack_blocks_three` 预登记批次 / Preregistered `stack_blocks_three` Batch (2026-10-16)

本批次属于 P3b.1 数据入库，不是 active 验收。工作流 family 固定为
`stack_blocks_three`，场景配置为 `demo_clean`，seed 固定为 105 和 106；每个 seed 只采集一次
同步 `camera/head` 与 `camera/front` 观测。采集前已写入 `changelog/2026-10_part7.md` 的 v14.5.1
计划条目。只读 worker 仍不构造 Persistent Runtime，不注册目标/绑定/规划，不接受 Action/Session，
不调用 `play_once`。

### 标签协议 / Label Protocol

- 正例候选：三块实体在两视角中均可定位，颜色/尺寸身份无歧义，并能从图像与深度事实判定
  `on(upper, lower)` 的当前支撑关系；标签只描述应选择的实体关系，不产生抓取或放置参数。
- 负例候选：缺失一块、关系被遮挡、身份或支撑关系歧义、场景初始化失败；保留原始观测和失败
  原因，标签为 `unavailable`/`inconclusive`，不改 seed、不删除分母。
- 不合格样本：只有单视角、局部理解与几何事实冲突、或依赖任务脚本内部目标状态才能判定的案例。
  这些样本只能进入开发/诊断集，不能送入 held-out 配对。
- 六类工单映射：多实体=`on` 关系中的三实体；无适用项=不存在的支撑关系请求；跨场景=105/106
  的不同布局；多方法=同一关系的合法候选与拒答分支；非法组合=不存在的上层/下层实体组合；
  复杂规划=无法仅凭当前观测判定支撑顺序时的升级。

标签冻结前不调用 JEV 或 System-2。冻结后由未参与采集、代码修复和标签编写的复核者确认；当前
Codex 只能做来源核对，不能把同作者复核记为 independent review。模型返回别名也不等于部署
provenance；正式配对仍需记录服务端版本/路由证明。生产继续 off/shadow。

### 批次结果 / Batch Result

- seed 105：双视角、0 ms skew、8 entities、1 ambiguity；三色方块可见但仍是分散的初始化状态，
  没有当前 `on` 关系，因此不生成正例。
- seed 106：双视角、0 ms skew、6 entities、1 ambiguity；front 视角没有完整看到绿/红块，跨视角
  身份不能确认，因此不生成正例。
- 两次运行均为 `remote_model_calls=0`、`action_calls=0`、`session_calls=0`、
  `host_selection_measured=false`。该批次保留为不可判定分母，不能发送 JEV/System-2，也不改变
  acceptance policy 或 active 状态。

## `blocks_ranking_size` 预登记批次 / Preregistered `blocks_ranking_size` Batch (2026-10-16)

下一批固定 family 为 `blocks_ranking_size`，配置 `demo_clean`，seed 107 和 108；每个 seed 一次
同步 head/front 观测。正例只有在三块实体均可跨视角绑定、相对尺寸大/中/小可由 RGB 与深度一致支持
时成立；缺失、遮挡、尺寸差异不可分辨或跨视角身份冲突一律记录为 `inconclusive`，不改 seed、不
删除失败分母。模型只能报告观察到的尺寸排序，不提供抓取、放置或执行参数。

本批六类映射为：多实体=三块排序；无适用项=不存在的尺寸类别；跨场景=107/108 的不同随机布局；
多方法=合法排序与拒答分支；非法组合=重复或不存在的尺寸标签；复杂规划=仅凭观测无法确定排序
时升级。标签冻结及独立复核规则沿用上节；冻结前不调用 JEV/System-2，生产保持 off/shadow。

### `blocks_ranking_size` 结果 / Result

- seed 107 目录为 `.../20261016-size-ranking/captures/seed-107/20261016T111733.318208Z-4da7061a/`：
  head 视角可见三块，cyan 只在 head 出现，不能完成跨视角身份绑定。
- seed 108 目录为 `.../20261016-size-ranking/captures/seed-108/20261016T111906.525568Z-17d81b10/`：
  三块和尺寸差异在 head 清晰，但 front 裁掉两侧，未满足完整跨视角绑定。
- 两批均双视角、0 ms skew、0 ambiguity，且 `remote_model_calls=0`、`action_calls=0`、
  `session_calls=0`、`host_selection_measured=false`；这证明观测可用性，不证明 held-out 资格。
  107/108 被标为调参/不可判定，不能回填正式 held-out。

## `blocks_ranking_size` 宽视场批次 / Wide-view `blocks_ranking_size` Batch (2026-10-16)

为避免把前两批视场调参混入评测，新批次使用 seed 109/110 和后移抬高的 front camera：
`position=[0.0, -0.8, 1.1]`、`forward=[0.0, 1.0, -0.15]`。其余任务、标签、六类映射和
no-motion 边界不变。仅当两视角都可绑定三块、尺寸排序有 RGB/depth 一致依据且没有 ambiguity 时，
才允许生成候选；否则保留原始分母并停止模型配对。

### 宽视场实际结果 / Wide-view Results

- seed 109：传感器双视角成功，但本机 Qwen 返回不可重试 `contract_output`，`entity_count=0`，
  仅作为服务失败分母。
- seed 110：双视角、0 ms skew、5 entities、0 ambiguity；三块均可跨视角绑定，尺寸顺序唯一，
  进入待冻结候选。其排序标签暂记为 `small < medium < large`，仍需复核者在标签冻结前确认。
- 两次均为 `action_calls=0`、`session_calls=0`、`remote_model_calls=0`、
  `host_selection_measured=false`；尚未调用 JEV/System-2。

下一批 seed 111/112 复用同一宽视场配置，目标是增加独立场景候选；任何用于修复或调整标签协议的
样本都会转为开发集，不回填 held-out。

### seed 111/112 结果 / Seed 111/112 Results

- seed 111：双视角、0 ms skew、5 entities、2 ambiguity；三个方块的颜色/位置跨视角无法唯一匹配，
  排除为 `inconclusive`。
- seed 112：双视角、0 ms skew、5 entities、0 ambiguity；三块均可绑定，图像显示唯一尺寸顺序，
  进入待冻结候选。候选的暂定小到大顺序为 `entity://e3 -> entity://e1 -> entity://e2`。
- 候选 110/112 与排除 109/111 已写入 `20261016-size-ranking-wide/intake_result.json`。清单明确
  `formal_held_out=false`、`independent_review=false`、JEV/System-2 为 0；这一步只完成候选入库，
  不能进入 active 验收。

当前仍缺：至少五类额外 held-out family、正式标签冻结、未参与采集/调试的独立复核、同版本 JEV/System-2
配对测量、服务部署 provenance、宿主 selection trace、接受策略记录和操作员授权。生产继续 off/shadow。
