# 倾倒与搅拌复合 Action：设计自审

日期：2026-10-18（Asia/Shanghai）。对象：[修订诊断](COMPOSITE_POUR_STIR_DIAGNOSIS_20261018.md)。
依据：设计诊断基点 `b4dac9ab`；实现核对提交 `352fe271`、`c4f2a194`、`4e93476d`、`f7da28d6` 和本轮工作区修改。作者自审，非独立审核或物理执行验收。
方法：采用 implementation-review 的架构、配置、错误与可观测性、验证、安全、维护及文档维度。下表问题是实现前发现；本轮状态另列于 §4。

## 1. 发现与处置

原建议的粒度方向成立，但未充分说明接口迁移、部分效果和测量语义。设计阶段记录了 3 项 Blocker、5 项 Major、1 项 Minor。
下表保留当时的发现与验收条件；不是当前未关闭问题数量。

| ID / 严重级别 | 具体问题与证据 | 设计处置 | 实施验收 |
| --- | --- | --- | --- |
| F1 / Blocker | 旧 held Tool 要求已持物；完整 cycle 从空手开始且最终应 empty | §3、§6：独立 cycle Tool 和持物 owner 来源 | 已实现并有注册/兼容测试；cycle 来源持物拒绝旧 pour/stir |
| F2 / Blocker | 倾倒已完成、归位失败时重调完整 Action 会再次倾倒 | §6：保留过程事实，unknown 对账；已知 holding 只 place 恢复 | 已有离线回归验证，不产生第二个 cycle invocation |
| F3 / Blocker | 无阶段协议无法核实顺序、部分完成或停止状态 | §5、§8：同一 owner 内的有序阶段事实；设备监控/急停仍由具体 provider 负责 | 离线协议/取消和 unknown 路径已覆盖；真实设备侧有界停止未实现、不在本阶段 |
| F4 / Major | 分别比较最大倾角与对齐时间会产生过程假阳性 | §5：容器对准、角度、抓持和反馈在同一窗口计算 | 合成轨迹覆盖错开窗口、反馈间断和未达目标 |
| F5 / Major | 汇总圈数不能验证方向、半径/深度或容器区域 | §4、§5：容器坐标下工具尖端轨迹；单向连续圈数与时长同窗达标 | 合成轨迹覆盖反向、摆动、间断和出界 |
| F6 / Major | 用户无称重不等于无液体；原回复易把旧无液体仿真与非夕部署混用；相关目录未找到 Flexiv 接入证据 | §1、§2、§7：过程目标明确；设备适配与测量能力按部署核实 | 不输出虚构体积/混匀结果；非夕传感/SDK/控制路径独立验收 |
| F7 / Major | 前轮笼统声称 Action 支持公共 stop；runtime L347-L351 实际只允许 Session stop_invocation | §5：Action cancel → 等待停止确认；设备急停单独处理 | Action 使用 cancel 路径；请求成功不等于物理已停止 |
| F8 / Major | 只有容器 destination_ref，没有瓶子/工具归还位置；圈数/时长与轨迹坐标含义不完整 | §4：增加 return_destination_ref；明确功能点、深度基准、参数可行性与超时范围 | 容器与归位点不混淆；“回原位”有来源且放置前仍有效 |
| F9 / Minor | “一个 Action”容易被理解为只需一次 Tool 调用、无需准备或任务验证 | §1、§3、§5：一个物理操作节点；必要 Query 与最终 Verifier 仍有独立职责 | 计划包含两次倾倒、一次搅拌及必要准备/验证，无冗余外部抓放节点 |
| F10 / Major | 初次实现中搅拌反馈断点重置了连续圈数但保留连续时长；断点前时长可能与断点后圈数合并，造成非连续样本达到目标 | §5、§8：断点/无效样本同时重置圈数和时长 | 已修复；新增 synthetic counterexample 验证两段各自不足不能拼接，定向回归包含该测试 |
| F11 / Major | cycle 能力按方法存在性判断，无法区分 preparation、execution、feedback、return 是否完整；缺少 provider control-loop 验收 | §3、§7、§8：引入逐 operation 的显式 capability declaration，并用 no-motion fake engine 验证阶段顺序、失败短路和取消 | 已修复为 fail-closed 声明；真实 provider 阶段执行和传感适配仍待设备阶段 |
| F12 / Major | `process_completed`/`return_completed` 与 `artifact_refs` 绑定，缺少 ref 会抹掉已观察的部分事实 | §6、§8：artifact ref 只决定完整 evidence/整体 succeeded，不覆盖协议和反馈已经结算的事实 | 已修复；新增无 artifact ref 的 unknown partial-result 回归 |
| F13 / Major | cycle engine 可以直接返回最终 receipt，内部原子操作顺序和失败短路没有统一 provider-neutral 入口 | §5、§8：新增内部 `AtomicExecutor` 协议和 no-motion 编排器；不增加公共 Tool 或嵌套 invocation | 已修复；engine 可通过 `atomic_executor` 工厂接入，具体反馈仍待独立部署适配 |

## 2. 审核后的责任边界

| 维度 | 判断 | 落实位置 |
| --- | --- | --- |
| 架构集成 | 方向符合一个节点由一个 Tool 结算；复合 Tool 必须真实拥有全过程 | 诊断 §2、§3；planning 不调用 SDK，Gateway 保持生命周期所有权 |
| 参数和配置 | 同时定义用户参数、设备/器材参数、系统引用 | §4；实际速度、误差和力值由所选 profile 与能力验证决定 |
| 错误与可观测性 | 过程达标和整体成功分离；可知失败与未知效果分开 | §5、§6；失败阶段、当前持物、过程测量与原 invocation 可追溯 |
| 验证 | 用反例验证成功判据、取消和恢复；复审发现并修复跨采样段累计、能力声明、部分事实丢失和原子编排缺口 | 本文 §3；指定离线回归 `131 passed`，Ruff 与 diff check 通过 |
| 机器人安全 | 复合化不移动已有授权与控制边界；控制监视独立于模型轮询 | §5；阶段适用性、attached geometry、停止及释放确认 |
| 维护与兼容 | 新 ID 或明确版本迁移；复用执行组件和持物 owner | §3、§6；不增加第二 Runtime、子任务调度器或公共嵌套 invocation |
| 文档与交付 | 历史方案保留，新诊断标明操作粒度变更及引用来源 | §1、§2、§7；部署能力、打包和接口发现一并验收 |

## 3. 验证矩阵与命令

| 用例 | 期望结果 | 层级 |
| --- | --- | --- |
| 正常倾倒/搅拌阶段结算 | 一个公共 Action invocation；阶段事实和过程证据齐全后才 succeeded | 离线合成数据；不代表设备/仿真 |
| 抓取失败、只发指令无反馈 | 不推进后续阶段，不宣布过程达标 | 离线阶段协议 |
| 倾倒错开窗口、错容器、过倾或采样中断 | 有效联合保持不足，过程失败 | 离线合成轨迹 |
| 搅拌反向、摆动、半径/深度错误或采样中断 | 有效圈数不足 | 离线合成轨迹 |
| 操作达标后归位失败 | 整体 failed、过程事实保留；后续仅 place | 离线集成 |
| 取消、超时、停止轮询 | 请求/确认语义保持 unknown；物理停止能力不由离线测试证明 | PAOS Runtime 既有语义 + 离线回归 |
| 丢失启动回执、进程中断、未知持物 | 对账原 invocation；原状态未明确前不重发 | 离线控制流回归 |
| 归位点占用、容器移动、持物变化 | 后续路线失效，记录阶段和物理状态 | 几何/状态集成 + 执行验证 |
| 两次倾倒后搅拌 | Verifier 核对正确对象、容器、先后顺序、各过程与最终归位 | 任务级集成 |
| 旧 acquire→place、旧 held 操作 | 旧绑定语义保持；新 cycle 不伪造旧 acquire 来源 | 兼容回归 |

下列命令运行本轮离线协议、合成轨迹及已有恢复回归。所有新轨迹都明确标注为 synthetic measurement records，不是仿真或机器人执行结果。

```bash
cd /home/yanxu/PhyAgentOS-forge
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime \
.venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  tests/test_capability_runtime_driver.py \
  tests/test_planning_effect_recovery.py \
  examples/forge-skills/pick-place-workflow/tests/test_cycle_protocol.py \
  examples/forge-skills/pick-place-workflow/tests/test_composite_manipulation.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py \
  examples/forge-adapters/robotwin20/tests/test_held_provider.py \
  examples/forge-skills/pick-place-workflow/tests/test_generic_capability_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py
```

`execute_cycle` provider/engine 的设备侧动作仍需未来独立适配和授权验收；本阶段不提供仿真或设备运行命令。

本次文档验证命令：

```bash
git diff --check
git diff --stat -- CHANGELOG.md changelog/2026-10_part7.md docs/forge/COMPOSITE_POUR_STIR_DIAGNOSIS_20261018.md docs/forge/COMPOSITE_POUR_STIR_REVIEW_20261018.md
```

另检查 UTF-8、Markdown 围栏、相对链接、引用行号与测试文件存在性，确认最近五版本与归档对应条目一致。
没有执行 PAOS Action、仿真、SDK、部署或运动测试；测试只证明离线算法、协议和 Runtime 控制流。

## 4. 当前实现状态

- `CyclePhaseProtocol` 要求 acquire → transport → process → reorient_exit → stow → release → retreat 顺序、单调阶段时间和对应可观察事实；缺阶段、错序、缺事实、丢测量或 unknown 事件不能结算成功。process 阶段执行结束与工艺目标达标分开表达。no-motion fake engine 和 `AtomicExecutor` 编排器还验证了失败阶段后不推进后续阶段、取消后保持 unknown。
- 倾倒保持从 process 阶段内样本联合计算；搅拌从容器坐标下棒尖轨迹计算，并要求方向性圈数和有效时长在同一连续段达到。汇总指标/请求值不作为测量证据。
- cycle 能力须由准备 provider 和执行 client 对同一 operation 通过 `cycle_capability(operation)` 显式声明 preparation、execution、feedback、return；Runtime 未发现完整声明时不发布 cycle Tool，旧 held Tool 不会被命名或描述成完整 cycle。`supports_cycle` 仅保留为 provider 内部兼容查询，不再是 Runtime 的唯一发现依据。
- cycle 来源持物拒绝旧 held-only pour/stir，仅允许 place；回执 unknown 时保留 unknown 并要求现有 invocation 对账。原子操作只存在于 provider 内部，不产生公共子 invocation。
- 诊断所列合成记录是手写的 synthetic measurement records。它们没有设备/仿真来源，不测量液量或混匀质量。`dry_run=true` 只表示可以做无运动控制流验收，不表示有物理运动授权。

尚未实现具体部署的反馈采集、实时安全监控和物理执行；这部分需要独立设备/传感适配方案，非夕 SDK 不在本阶段范围。当前 `AtomicExecutor` 和 no-motion executor 只证明 provider 能按原子操作产生阶段事件，不能证明具体设备已经执行这些阶段。

## 5. 结论与后续设备适配范围

复审发现的 F10 跨采样段时长/圈数拼接问题、F11 能力声明缺口、F12 部分事实丢失问题和 F13 原子编排缺口均已修复并有回归覆盖。当前离线/no-motion 验收未遗留 Blocker/Major；实现满足公共 invocation、内部原子编排、过程反馈计算、阶段事实、部分失败和 fail-closed 能力发现边界，但不含具体设备反馈和物理执行器，因此仍无法证明夹持反馈、坐标标定、运动安全或动作结果。
后续若接设备，须单独核实具体机器人/控制模式、工具与容器功能点、夹持/放置反馈、profile 数值与停止能力；这属于独立设备适配与验收，不应从本轮测试外推。
