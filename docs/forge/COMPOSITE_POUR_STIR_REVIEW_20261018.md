# 倾倒与搅拌复合 Action：设计自审

日期：2026-10-18（Asia/Shanghai）。对象：[修订诊断](COMPOSITE_POUR_STIR_DIAGNOSIS_20261018.md)。
依据：当前源码 `b4dac9ab` 与工作区 held-operation 原型；作者自审，非独立审核或执行验收。
方法：采用 implementation-review 的架构、配置、错误与可观测性、验证、安全、维护及文档维度；仅修订已授权的设计文档。

## 1. 发现与处置

原建议的粒度方向成立，但未充分说明接口迁移、部分效果和测量语义。本轮发现 3 项 Blocker、5 项 Major、1 项 Minor。
下表“设计已修订”指诊断已补齐明确方案；执行实现和相关测试仍待完成，不计作运行缺陷已修复。

| ID / 严重级别 | 具体问题与证据 | 设计处置 | 实施验收 |
| --- | --- | --- | --- |
| F1 / Blocker | 当前 `held_manipulation.py` L161-L169 要求已持物，L231-L240 成功仍 holding；完整 cycle 从空手开始且最终应 empty | 诊断 §3、§6：明确新 cycle 身份、前后置条件和原持物 owner 的来源扩展 | 注册发现/参数投影/旧任务兼容；cycle 后归位恢复不能伪造 acquire invocation |
| F2 / Blocker | 倾倒已完成、归位失败时重调完整 Action 会再次倾倒；旧计划自审 F9 已识别，合并后仍存在 | §6：保存 process/return 两个结果，终态 failed，之后只做合法归位恢复；unknown 先对账 | 在归位阶段注入失败；恢复不产生第二次倾倒或搅拌事件 |
| F3 / Blocker | 把所有阶段塞进一个调用却无控制/资源连续性，会在取消、场景变化或轮询停止后继续执行；通用 runtime L401-L426 的 deadline 依赖轮询推进 | §5：同一执行 owner、阶段适用性检查、设备侧执行监控；碰撞/急停后不无条件退回或松爪 | 停止轮询、取消中途、移动容器、占用归位点、反馈中断时有界停止且状态真实 |
| F4 / Major | `_measured_completion` L207-L208 分别比较最大倾角与对齐时间，可接受“对齐但未倾斜保持”或过度倾斜 | §5：同一连续窗口内联合检查瓶口区域、角度容差和持物有效性，使用反馈时间 | 直立保持后瞬时倾斜、错容器、过倾、采样中断均不能成功 |
| F5 / Major | 搅拌只看圈数/时间，未确定方向、有效半径/深度及计数口径；往返摆动可能被绝对角度累计为圈 | §4、§5：容器坐标和 cw/ccw，方向性连续轨迹，圈数/时长约束及 profile 容差 | 静止插棒、反向摆动、半径/深度偏差、漏圈和超时失败 |
| F6 / Major | 用户无称重不等于无液体；原回复易把旧无液体仿真与非夕部署混用；相关目录未找到 Flexiv 接入证据 | §1、§2、§7：过程目标明确；设备适配与测量能力按部署核实 | 不输出虚构体积/混匀结果；非夕传感/SDK/控制路径独立验收 |
| F7 / Major | 前轮笼统声称 Action 支持公共 stop；runtime L347-L351 实际只允许 Session stop_invocation | §5：Action cancel → 等待停止确认；设备急停单独处理 | Action 使用 cancel 路径；请求成功不等于物理已停止 |
| F8 / Major | 只有容器 destination_ref，没有瓶子/工具归还位置；圈数/时长与轨迹坐标含义不完整 | §4：增加 return_destination_ref；明确功能点、深度基准、参数可行性与超时范围 | 容器与归位点不混淆；“回原位”有来源且放置前仍有效 |
| F9 / Minor | “一个 Action”容易被理解为只需一次 Tool 调用、无需准备或任务验证 | §1、§3、§5：一个物理操作节点；必要 Query 与最终 Verifier 仍有独立职责 | 计划包含两次倾倒、一次搅拌及必要准备/验证，无冗余外部抓放节点 |

## 2. 审核后的责任边界

| 维度 | 判断 | 落实位置 |
| --- | --- | --- |
| 架构集成 | 方向符合一个节点由一个 Tool 结算；复合 Tool 必须真实拥有全过程 | 诊断 §2、§3；planning 不调用 SDK，Gateway 保持生命周期所有权 |
| 参数和配置 | 同时定义用户参数、设备/器材参数、系统引用 | §4；实际速度、误差和力值由所选 profile 与能力验证决定 |
| 错误与可观测性 | 过程达标和整体成功分离；可知失败与未知效果分开 | §5、§6；失败阶段、当前持物、过程测量与原 invocation 可追溯 |
| 验证 | 用反例验证成功判据、取消和恢复，现有单测仅为复用依据 | 本文 §3；无新增运行结果声明 |
| 机器人安全 | 复合化不移动已有授权与控制边界；控制监视独立于模型轮询 | §5；阶段适用性、attached geometry、停止及释放确认 |
| 维护与兼容 | 新 ID 或明确版本迁移；复用执行组件和持物 owner | §3、§6；不增加第二 Runtime、子任务调度器或公共嵌套 invocation |
| 文档与交付 | 历史方案保留，新诊断标明操作粒度变更及引用来源 | §1、§2、§7；部署能力、打包和接口发现一并验收 |

## 3. 验证矩阵与命令

| 用例 | 期望结果 | 层级 |
| --- | --- | --- |
| 正常倾倒/搅拌完整周期 | 一个物理 PlanNode、一个 invocation；过程和归位满足后才 succeeded | 离线集成 + 对应设备/仿真 |
| 抓取失败、只发指令无反馈 | 后续操作不执行，不能宣布过程达标 | 离线故障 + 执行测量 |
| 瞬间倾斜、错容器、过倾 | 有效联合保持不足，过程失败 | 测量单测 + 轨迹验证 |
| 静止插棒、摆动代替转圈、深度错误 | 有效圈数或轨迹条件不足 | 测量单测 + 轨迹验证 |
| 操作达标后归位失败 | 整体 failed、过程完成事实保留；后续归位不重做过程 | 离线集成 + 故障执行 |
| 取消、超时、停止轮询 | 设备执行有界；停止确认前保持未确认事实 | driver/worker 集成 + 设备控制 |
| 丢失启动回执、重启、未知持物 | 对账原 invocation；原状态未明确前不重发 | 传输/恢复集成 |
| 归位点占用、容器移动、持物变化 | 后续路线失效，记录阶段和物理状态 | 几何/状态集成 + 执行验证 |
| 两次倾倒后搅拌 | Verifier 核对正确对象、容器、先后顺序、各过程与最终归位 | 任务级集成 |
| 旧 acquire→place、旧 held 操作 | 旧绑定语义保持；新 cycle 不伪造旧 acquire 来源 | 兼容回归 |

下面是实施阶段可复用、已存在的离线测试入口。本次仅核对文件存在，未运行；它们尚不证明新 cycle 的执行能力。

```bash
cd /home/yanxu/PhyAgentOS-forge
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime \
.venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  tests/test_capability_runtime_driver.py \
  tests/test_planning_effect_recovery.py \
  examples/forge-skills/pick-place-workflow/tests/test_generic_capability_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py
```

完整 cycle、测量窗口、恢复归位的新增测试由实施阶段编写；届时补充确实存在的仿真或非夕执行命令。

本次文档验证命令：

```bash
git diff --check
git diff --stat -- CHANGELOG.md changelog/2026-10_part7.md docs/forge/COMPOSITE_POUR_STIR_DIAGNOSIS_20261018.md docs/forge/COMPOSITE_POUR_STIR_REVIEW_20261018.md
```

另检查 UTF-8、Markdown 围栏、相对链接、引用行号与测试文件存在性，确认最近五版本与归档对应条目一致。
没有执行 Action、仿真、SDK、部署或运动测试。

## 4. 结论与实施前仍需明确的事实

修订后的方案适合交用户审核。单个完整倾倒/搅拌符合 PAOS 的 Tool 结算边界；关键是完整周期的物理 owner、过程测量和部分失败恢复一起实现。
本次 9 项发现已在设计中给出处置，工程实现和实测均待实施；不能据文档修订将执行能力判定为通过。
实施时必须核实具体机器人/控制模式、工具与容器功能点、夹持和放置的可用反馈、真实参数及容差、旧 Tool 是否已部署和绑定任务。
这些事实决定设备适配与数值配置，不影响用户现在审核操作粒度和职责划分。
