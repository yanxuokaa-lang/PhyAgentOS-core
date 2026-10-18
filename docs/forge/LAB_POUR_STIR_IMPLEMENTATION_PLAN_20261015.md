# 多试剂倾倒与手持棒搅拌：实施计划

日期：2026-10-15（Asia/Shanghai）。状态：P1 接口实现仍在工作区；根据真实资产要求重新审核 P0/P2，未完成实验室动作闭环。
资产路线更新：[真实资产来源与场景构建复审](LAB_SCENE_ASSET_REVIEW_20261015.md)。以导入真实实验室网格为准，程序化圆筒预览已被否定。
依据：[诊断](LAB_POUR_STIR_DIAGNOSIS_20261015.md)、[可行性自审与修订](LAB_POUR_STIR_FEASIBILITY_REVIEW_20261015.md)。

## 1. 目标、范围与工作假设

用户直接给出试剂与顺序，Agent 在一个任务中完成至少两瓶的选取、倾倒、归位，
随后取手持棒、搅拌并归架。首版建议无液体，不承诺定量转移或混匀效果。
用户已确认沿用 RoboTwin/Franka、无液体、开口瓶、稳定杯座、带抓握柄的手持棒，以及目标瓶受阻时先移开挡物。
用户进一步要求较多桌面物体和相机可见瓶身标签；首版数量采用可配置场景规格，不将内部 ID 当作标签识别。

首版不加入拧盖、同步双臂、接触力控、流体或化学反应。新 Tool 的建议名称为
`object.pour`、`tool.stir`，准备 Query 暂定 `manipulation.prepare_held`。
三个接口已有工作区实现，尚未接通真实 RoboTwin 实验室执行器或部署；准备 Query 复用已有路线检查责任，不引入额外全局门禁。

## 2. 架构与最小完整交付

```text
用户目标和不可变顺序约束
  -> 实验室方法 Skill / Agent 选择当前子目标与必要前置步骤
  -> 既有 PlanGraph / Coordinator
  -> Query: 观察、绑定、能力、抓取准备 / 持物操作准备
  -> Action: acquire / pour / stir / place
  -> 既有 Gateway invocation 与 Adapter/worker
  -> 过程测量、持物状态、当前场景、settlement
  -> 续段 / 对账 / 最终 Verifier
```

交付必须同时覆盖：契约与参数投影、Runtime 端点、worker 执行、部署打包、Skill 方法、
过程证据、失败恢复、旧抓放兼容和仿真验收。无第二个 Runner、任务数据库或配方执行器。

### 2.1 源码接入位置

| 现有文件或目录 | 计划修改责任 |
| --- | --- |
| `examples/forge-skills/pick-place-workflow/contracts/` 与 `src/pick_place_workflow/` | 新动作/准备契约与端点，扩展当前持物接续与 place 投影；文件最终命名在 P1 确定 |
| `PhyAgentOS/forge/capability_runtime/ports.py`、`runtime.py` | 优先复用 ActionEndpoint/ActionDriver/ActionAdmission；仅在实际调用方需要时增加通用端口 |
| `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py` | 同一 Runtime 注册新端点，实验室 profile 装配 |
| 同目录 `persistent_preparation.py`、`persistent_route_builder.py`、`prepared_routes.py` | 持物路线准备和存取；按实际复用边界抽取共用逻辑 |
| 同目录 `persistent_client.py`，`runtime/robotwin_persistent_worker.py`、`robotwin_persistent_engine.py` | 命令路由、执行、测量和取消/对账，保持一个世界 |
| `runtime/robotwin_blocks_ranking_adapter.py` 对应的任务装配入口 | 增加实验室薄任务 Adapter，复用实体/目标/结果接缝；不把实验室装成 RGB task |
| `examples/forge-skills/pick-place-workflow/skill.yaml`、profiles 与 `scripts/build_robotwin20_node.py` / `scripts/build_robotwin20_skill_bundle.py` | 按现有安装链打包新端点与选定方法，不使旧 profile 强制要求新能力 |
| 实验室方法文档与现有 planning/verification 扩展点 | 语义计划与过程评价，Core 不按试剂名或 RoboTwin task 名分支 |

这是一张工作分配表，不要求为了“通用”预先修改全部文件。
外部 RoboTwin 源码和资产的实际落点在 P0 记录；优先用现有加载入口，必要的外部改动须单独列明。

### 2.2 Skill 交付选择

优先在现有部署机制中增加实验室 profile 和独立方法内容，复用抓放代码。
P0 检查安装器实际支持的 Skill/Runtime 绑定；若尚不支持一个部署关联独立方法 Skill，
首版在同一 manifest-v2 包内组织实验室方法，并将其选择明确绑定到实验室 profile。
完成多 Skill 动态迁移不作为本场景的前置任务，不复制另一个 Runtime 或修改既有活动任务绑定。

## 3. 动作与准备接口设计

### 3.1 持物准备 Query

现有 `manipulation.prepare` 要求抓取候选集合。倾倒、搅拌及操作后的归位已有持物事实，
再提供虚构抓取候选会混淆动作来源。因此推荐单独的只读 `manipulation.prepare_held`，
复用 readiness provider、prepared route 存储与检查函数，保留旧 prepare 输入兼容。

该 Query 的最小语义输入：当前实体和持有归属的证据引用、当前场景/坐标系/标定、
操作种类（pour/stir/place）、容器或归位目标引用，以及有界参数。
输出可用性、路线准备引用、当前资源分配、适用状态、拒绝原因；不推进仿真。
具体字段名称遵循现有 ToolSpec 与投影机制，不在文档中另立大而全 schema。

### 3.2 Action 边界

| Action | 入口条件 | 终态条件 |
| --- | --- | --- |
| object.pour | 正确瓶被当前任务持有，容器几何可信，持物路线准备有效 | 瓶口/倾角/持续时间满足动作条件，瓶体回正且撤离，持物状态明确 |
| tool.stir | 正确棒被持有，杯内可用区域已确定，轨迹准备有效 | 实际棒尖达到指定轨迹覆盖/圈数或时长条件并退出，持物状态明确 |
| object.place（扩展） | 原 acquire 归属与最新持物结果一致，归位目标与新路线有效 | 使用原 release/retreat/postcondition 语义完成归位 |

功能点变换由 Adapter 根据当前抓持关系计算。棒尖目标不能直接当末端目标；
应使用工具到夹爪的变换求解末端轨迹。圆周使用固定圆心的绝对采样点或相邻点差值，
不累计圆上坐标。姿态插值、执行时步、速度与限位使用现有控制配置。

### 3.3 持物接续与来源

- 在原持物 owner 中增加“持有物操作中”的语义；保留 owner/entity/原 acquire invocation。
- 每次操作终态更新当前状态与场景；下一次准备使用当前可信状态，而非重用抓取前路线。
- `place` 保留旧 acquire→place 分支，并增加由声明的持物操作结果提供当前来源的分支。
- 两条来源有歧义时明确拒绝或由 Agent 选择合法候选；不能按任意字段同名拼接结果。
- 新方法逐段物化当前已有引用；整体顺序用依赖表达，不预造未来对象/准备证据引用。
- 调用未知或持有状态不明时，先按原 invocation 对账，不能自动重发倾倒。

## 4. 具体实施阶段

### P0：场景、版本和资产确认

输入：本计划、用户选择、当前工作区与实际安装环境。
操作：

1. 确认 RoboTwin/Franka、无液体、开口瓶、手持棒、标签语义、瓶数及清障变化。
2. 核对实际 RoboTwin/SAPIEN/规划器版本、机器人 profile、解释器和已安装 Skill；与工作区版本分别记录。
3. 按专项复审优先取得 LabUtopia 实验室 USD/贴图及必要引用，记录 CC BY-NC 4.0 资产许可；本地 RoboTwin-OD 补充经检查的干扰物。逐物体记录尺度、抓取区域、杯口/内腔/棒尖和碰撞体。
4. 决定固定杯座或自由杯；首版建议稳定杯座与可见杯沿，记录这一实验条件。
5. 核对方法文档、manifest 与 Runtime 的绑定，确定新增方法的打包方式。

输出：可实现的场景规格与资产清单；缺资产、标签不可读、没有合法杯内几何时先解决该项。
可在回答等待期间继续离线接口工作；资产加载/渲染/运动按实际授权执行，P0 不启动现场 Runtime。

### P1：契约、持物接续与 Fake Runtime

依赖：源码诊断；不依赖真实资产和运动。
操作：

1. 实现 prepare_held、pour、stir 的最小契约、端点和输入投影。
2. 扩展现有持物管理与 place 来源，保留 acquire→place 兼容路径。
3. 通过原 CapabilityRuntime 注册，接入 accepted/running/terminal、poll/cancel/stop。
4. Fake 路径覆盖 acquire→pour→place、acquire→stir→place、未知结果和失败后继续持物。
5. 给未来实施的文档和代码同步写版本日志；执行领域改动使用 anti-minimal-implementation 和 robotics-safety-implementation。

完成条件：契约、来源和持物状态测试通过；Fake 不调用真实 worker，测试通过只代表控制流兼容。
失败分支：若现有投影不足，扩展通用声明式来源表达，不在 Core 按 pour/stir 名称补专用条件。

### P2：场景与持物路线准备

依赖：P0 资产规格、P1 契约。
操作：

1. 先对真实瓶/杯/棒/架完成 USD 到 GLB/OBJ 的单体转换，处理 OmniGlass/MDL 材质和开口碰撞；当前 Blender/bpy 尚不可用。再增加实验室薄任务 Adapter 和 task/profile，接通原 Franka 与相机，标签映射可变化。无需先完成其他三个任务的通用化迁移。
2. 把瓶口、杯口/内腔、棒尖以及抓持变换接入 Adapter；区分观测输入与评分真值。
3. 准备瓶子倾斜/保持/回正、棒插入/圆周/退出和操作后归位的整段路线。
4. 检查含 attached object、杯壁/桌面、其他物体和另一臂的碰撞模型，以及限位和可达性。
5. 实验室 profile 支持观察驱动的目标及合法 staging 区，保持原 RGB benchmark 规则。

完成条件：静态几何/路线检查发现杯口封闭、工具变换错误与不可达等样例；Query 不产生运动。
失败分支：修改资产碰撞体、抓握柄/支架、布局或路线；不得为让样例成功删除碰撞检查。
杯内几何在观测路径不可获得时，先改善资产可见性/感知；开发用真值路线单独标记，不能冒充视觉闭环。

### P3：单瓶倾倒执行闭环

依赖：P1、P2 和仿真执行授权。
操作：同一 Gateway/worker 中完成 acquire→prepare_held(pour)→pour→prepare_held(place)→place。
在动作实际执行过程中收集瓶口位置、瓶体方向、持续时间、回正/撤离和持物结果。
碰撞或取消后记录实际终态与阶段，不把中断处理自动变成一段未经准备的恢复运动。

完成条件：正常动作与归位完成；倒向错误容器、缺保持、归位失败、通信丢失等路径被准确记录。
失败分支：区分抓取失败、倾倒路线失败和放置失败；已完成倾倒后的放置重试不能重复倾倒。

### P4：手持棒搅拌执行闭环

依赖：P1、P2；可与 P3 共用持物接续实现，不能用 Fake 替代物理证据。
操作：acquire→prepare_held(stir)→stir→prepare_held(place)→place。
以实际棒尖轨迹计算杯内轨迹覆盖、有效累计转角/圈数或时长，并检查退出与归架。
指令角度或规划点数量不作为实际搅拌完成证据。

完成条件：棒可稳定抓取、插入、沿杯内无接触路径运动并退出；停在杯内不能直接判成功。
失败分支：先检查棒柄可抓性、工具变换、杯内空间与控制误差；若必须接触控制，另列范围决策。

### P5：双试剂 Skill 与整体评价

依赖：P3、P4 独立闭环可用。
操作：

1. 原请求记录顺序 A→B→搅拌，语义节点由当前观测与实际能力物化。
2. 每次世界变化后刷新相关观测/绑定；保持一个任务，在已完成结果基础上续接。
3. Runtime 过程测量进入现有执行 artifact/settlement；任务 Verifier 检查两次正确操作及先后关系。
4. 关联每个事件的任务、invocation、目标实体、接收容器、结果和模拟时间；重复 poll 不产生第二次完成事件。
5. 归位失败与倾倒完成分别表达；unknown 时只对账，不自动重放动作。

完成条件：错瓶、漏倒、换序、提前搅拌、仅插棒、旧任务证据混用都不能通过整体评价；
正确过程在归位完成后通过。用户未要求定量时，不加入虚构剂量或化学反应目标。

### P6：条件规划与仿真验收

依赖：P5；用户已确认清障作为场景要求。
采用同一任务提示的成对场景：无遮挡时直接操作；受阻时先清障再执行既定试剂顺序。
挡物须在选定抓取集合/当前规划器下实际阻挡并在移开后恢复可达；仅挡住标签或摆在前方不够。最终约 18–24 个对象的丰富布局仍须保留合法暂存区和机器人通道。
如果暂存区被占用且无合法位置，应停止并报告具体缺口；不发明目标位姿或改动试剂顺序。

保存实际 Agent 计划/修订与动作视频，核对变化由观测驱动，而非由 task_id/seed 给定脚本。
首轮建议覆盖 3 个布局 × 2 个标签位置映射 × 2 个遮挡条件，共 12 个正常验收回合；
另列取消、丢失持物、结果未知等故障用例。该规模用于工程覆盖，不宣称统计成功率已充分估计。
逐回合报告成功/失败、失败阶段、错误对象操作、约束违反及有效步骤数，不仅展示最佳视频。

### P7：部署与回归交付

依赖：P1-P6 对应范围完成；部署时沿用原项目操作授权和发布规则。
构建现有 node/Skill 包，核对 ToolSpec、Python 端点、profiles 和方法内容一致，在隔离安装位置检查导入与发现。
保留旧 RGB profile 的 required_tools、目标限制和抓放行为；新 profile 才暴露完整实验室能力。
有未终态任务时不覆盖其执行包或契约；按现有取消/对账与版本安装流程切换。
回滚使用上一已验证部署包，并处理在途动作；不能将文件回滚等同于物理状态复原。

## 5. 验证命令与证据

### 当前已有的离线回归入口

以下命令供实施阶段运行，本次文档任务未执行测试。解释器为当前仓库 `.venv/bin/python`，
实施时先核对其依赖；缺依赖时按项目环境安装，不直接切换到未核实的系统 Python。

```bash
cd /home/yanxu/PhyAgentOS-forge
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts \
.venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  tests/test_capability_runtime_driver.py \
  tests/test_tool_spec_projection.py \
  tests/test_planning_effect_recovery.py \
  examples/forge-skills/pick-place-workflow/tests/test_generic_capability_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_task_verification_context.py
```

### 拟新增的离线测试入口

下列文件在 P1-P5 创建，当前不存在；不能把命令列出视为验证通过。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime \
.venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  examples/forge-skills/pick-place-workflow/tests/test_held_manipulation.py \
  examples/forge-skills/pick-place-workflow/tests/test_pour_stir_contracts.py \
  examples/forge-skills/pick-place-workflow/tests/test_lab_workflow_verification.py \
  examples/forge-adapters/robotwin20/tests/test_lab_route_geometry.py
```

部署打包兼容检查使用现有 `examples/forge-skills/pick-place-workflow/tests/test_release_bundle.py`。
Isaac Sim runner 已实现为 `isaacsim_lab` 的 PAOS 父进程与 worker 子进程；P3 当前已有可复现的单回合命令，
但尚未达到正常倾倒完成条件。P6 验收运行前仍需固定 profile、解释器、输出目录和逐回合证据，不得把 worker 启动或场景加载当作成功。

### 验收数据记录

每回合记录任务原文、对象/顺序、代码与资产版本、profile、seed、标签/布局映射、相机设置、
模拟时步、动作阈值、真实结果与视频路径。阈值在资产标定后写入 profile，验收失败时不逐回合改阈值。
效果由实际轨迹与终态支持，不能以准备成功或模型文本替代。普通 Git/版本/现有记录足以管理这些材料。

## 6. Agent Route Contract 与控制边界

| 项目 | 归属和要求 |
| --- | --- |
| 决策 owner | Agent 选择当前对象与清障方法，严格保持用户试剂顺序；Coordinator 保存 revision |
| 上下文 | 当前观测、已绑定对象、实际执行结果、剩余义务；不泄露环境正确目标 ID |
| 可调用能力 | 当前 profile 实际发布的 Query/Action；未部署能力不得被计划执行 |
| Runtime admission | 现有状态、标定、workspace、IK、碰撞、限位和停止路径，新增持物路线按同一职责检查 |
| 证据 | 已有 invocation/attempt/artifact/settlement，过程测量和最终状态分别保存 |
| 结果 | success/failed/unknown 明确区分；准备可行与执行完成分离 |
| 中断与恢复 | 原 invocation 对账，明确持物后再准备恢复路线；已倒试剂不重复操作 |
| Skill 与执行包 | 沿现有版本和任务绑定，方法选择不授予动作权限 |
| 仿真/硬件 | 本次文档不授权执行；后续仿真按用户授权范围推进，硬件不在首版范围 |

本计划不新加 hash、冻结 baseline、全局 gate 或第二状态库。持物、碰撞和动作结果检查对应真实执行边界：
旧状态可能导致掉物、碰撞或重复倾倒，Git、类型和单元测试无法替代运行时物理事实；沿用已有 owner 实现。

## 7. 排期与完成判据

不按“两个 Tool”承诺固定工期。P0 完成资产与部署确认后，分别估算接续/契约、资产与路线、
执行与测量、Skill 与验收四项工作量；P3/P4 的物理试验结果决定是否需要调整夹持资产或布局。
计划的关键路径是 P0/P1→P2→P3/P4→P5→P6/P7。

交付完成要求实际部署能够执行目标任务，正反例有证据，旧抓放兼容，失败与取消可解释。
离线测试、Fake Runtime 和单段成功分别报告，不替代完整双试剂仿真结果。

## 8. v14.12.2 Isaac Sim / LabUtopia 接入状态

已确认 `/home/yanxu/LabUtopia` 的 `labutopia` 环境包含 Isaac Sim 5.1，且 `lab_001.usd`、Franka、`conical_bottle03` 与 `beaker2` 可作为本次任务的默认绑定。新增 `examples/forge-adapters/isaacsim_lab` 作为薄 Adapter：

- `LabUtopiaProfile` 将既有 PAOS observation/preparation 输入投影到 `entity://conical_bottle03`、`destination://beaker2` 和 cycle 参数；scene USD、配置、frame、calibration 均由 profile 提供。
- `IsaacSimLabEngine` 只在 active Python 能发现 `isaacsim` 且 `OMNI_KIT_ACCEPT_EULA` 已明确设置时声明完整 cycle 能力；普通 PAOS Python 不会导入 Isaac 模块。
- `LabUtopiaBackend` 在 Isaac Sim 内复用 LabUtopia 的 pick/pour 控制器，再执行归位、释放和撤离；返回原始反馈观测与七阶段事件，交由现有 PAOS feedback adapter / cycle projector 结算。倾倒对准点是源瓶口按当前姿态投影的点，而不是瓶体中心；provider 还尝试用该偏移补偿控制器目标。最终 `succeeded` 仍要求七个阶段全部完成且反馈计算器观测到同一连续倾倒保持窗口。
- 预览命令只证明 Kit 和场景可加载，不证明运动或任务成功；完整任务必须使用 `labutopia` Python、显式 profile，并保留逐样本反馈、阶段事件和最终状态。

当前可先查看 PAOS 将接收的输入：

```bash
cd /home/yanxu/PhyAgentOS-forge
PYTHONPATH=examples/forge-adapters/isaacsim_lab/src \
python -m isaacsim_lab.cli \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-pour-cycle.json
```

实际单回合使用下列 `labutopia` worker 命令执行；没有 Isaac 运行时或反馈证据时必须保持 `unavailable`/`unknown`，不得由 PAOS preparation 结果推断倾倒成功：

```bash
OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=/home/yanxu/PhyAgentOS-forge/examples/forge-adapters/isaacsim_lab/src \
/home/yanxu/miniconda3/envs/labutopia/bin/python - <<'PY'
import json
from pathlib import Path
from threading import Event
from isaacsim_lab.engine import IsaacSimLabEngine
from isaacsim_lab.profile import LabUtopiaProfile
profile = LabUtopiaProfile.from_json(Path('/home/yanxu/PhyAgentOS-forge/examples/forge-adapters/isaacsim_lab/configs/labutopia-pour-cycle.json'))
result = IsaacSimLabEngine(profile).execute_cycle('pour_cycle', profile.paos_input(), Event())
print(json.dumps({key: result.get(key) for key in ('status', 'outcome_known', 'phase_events')}, ensure_ascii=False))
PY
```

2026-10-18 的真实单回合已启动 Isaac Sim 并返回可观测失败：`acquire`、`transport`、`stow`、`release`、`retreat` 完成，`process` 失败 `continuous_pour_window_not_observed`，因此最终为 `failed/outcome_known=true`。瓶口观测与 provider 目标补偿接入后，最新回合共有 1039 个反馈样本，抓持、对准、目标倾角和采样连续性共同满足的窗口仍为 0；抓持且对准时最大倾角为 `0.259 rad`。这证明结算边界和失败保留有效，不证明物理倾倒成功。下一步应针对 LabUtopia 控制器的旋转路线、瓶口轴/尺寸标定和烧杯口目标定义做专门验收，不能放宽 PAOS 保持窗口定义。
