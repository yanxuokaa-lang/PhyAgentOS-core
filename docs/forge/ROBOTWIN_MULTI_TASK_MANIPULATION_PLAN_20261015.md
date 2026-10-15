# RoboTwin 多任务通用操作方案

日期：2026-10-15
范围：`blocks_ranking_size`、`stack_blocks_three`、`put_bottles_dustbin`
状态：设计方案，未修改运行时代码，未授权仿真或真实运动

## 1. 目标与结论

这三个任务应由一套 provider-neutral 的多对象操作流程支持，而不是为每个
任务复制一套 Agent 循环、状态机或 Gateway 路由。三者共享：

```text
scene.observe
  -> scene.understand / manipulation.capabilities
  -> grasp.propose
  -> manipulation.prepare
  -> object.acquire
  -> object.place
  -> terminal settlement
  -> fresh scene.observe / scene.bind
  -> next segment or final verification
```

任务差异只通过当前场景绑定的目标关系、依赖、后置条件和 Runtime Adapter
提供的几何解析表达：

| 任务 | 通用目标关系 | 主要新增语义 |
|---|---|---|
| `blocks_ranking_size` | `at(entity, ordered-slot)` | 从尺寸/排序事实绑定实体与槽位 |
| `stack_blocks_three` | `on(upper, lower)` | 放置顺序、支撑关系和稳定性证据 |
| `put_bottles_dustbin` | `inside(bottle, container)` | 共享容器、多轮占用和容器内状态证据 |

PAOS Core 不知道颜色、尺寸、方块、瓶子、垃圾桶、RoboTwin 坐标或
`check_success()` 的实现。Core 只处理语义义务、依赖、证据、修订和生命周期。

## 2. 现有能力与已知缺口

### 可直接复用的主干

- `AgentTaskRecord`、`PlanRevision`、`AgentTaskCoordinator` 继续拥有任务、修订、恢复和终态。
- `PhyAgentOS.planning.PlanGraph` 继续拥有语义节点依赖；Skill DAG 不拥有第二套生命周期。
- 现有 `scene.observe`、`scene.understand`、`manipulation.capabilities`、`grasp.propose`、
  `manipulation.prepare`、`object.acquire`、`object.place` Tool 链继续作为通用操作链。
- Runtime/Gateway 继续拥有 Tool 调用、并发、pending/terminal/unknown、Action admission 和停止。
- Adapter/profile 继续拥有 RoboTwin task、SAPIEN、执行几何、候选、IK、碰撞和 benchmark 查询。
- `ForgeTaskVerifier` 继续消费 PAOS 任务证据；RoboTwin `benchmark_result` 独立记录，不能替代 PAOS verdict。

### 不能直接复用的地方

1. `robotwin_blocks_ranking_adapter.py` 当前只接受 `blocks_ranking_rgb`，不能在 Core 中添加三个
   `if task_name == ...` 分支代替适配器抽象。
2. `SceneObjectBinding` 默认 `category="block"`，应改成通用实体类别或由任务输入显式提供。
3. `bind_scene_objects` 当前要求所有 `destination_ref` 唯一；三个瓶子共享垃圾桶目标时，必须允许多个义务引用同一个可多占用目标。
4. `MultiObjectAgentRunner` 当前把每项义务固定命名为 `relocate_N` 并串成固定链；它需要接受通用目标关系、依赖和刷新策略。
5. `compose_executable_pick_place_plan` 当前把所有义务投影为固定 relocation 链；仍可复用这条链，但 `place` 必须消费不透明目标关系，而不是假设目标总是独立槽位。

这些是已有语义约束与三项任务之间的真实不匹配，不需要新增哈希、全局 baseline 或额外状态库。已有 graph/policy/artifact digest 继续按现有契约使用。

## 3. 通用领域抽象

### 3.1 场景实体绑定

将当前 `SceneObjectBinding` 的含义提升为通用的 `SceneEntityBinding`。最小字段为：

- `entity_ref`：PAOS 语义实体身份；
- `benchmark_object_ref`：Adapter 对应的外部对象身份；
- `category`：`block`、`bottle`、`container` 等数据，不进入 Core 分支；
- `observation_ref`、`scene_revision`、`frame_id`、`calibration_ref`；
- 当前实体的观测几何 artifact；
- 可选 `capability_snapshot_ref` 和 `assignment_ref`；
- 一个或多个不透明 `goal_ref` / relation fact 引用。

实体身份、场景修订、frame、calibration 和 geometry provenance 必须来自同一
scene revision。缺失、歧义、过期或跨场景混用时保持 fail-closed。

### 3.2 目标关系，而不是目标位姿

公共计划只绑定目标关系和不透明引用，不绑定 RoboTwin 精确位姿：

```text
obligation_ref
subject_entity_ref
goal_ref
relation_kind       # at / on / inside，保持 provider-neutral
depends_on
required_evidence
produced_effects
resource_claims
refresh_after_world_change
```

`goal_ref` 的几何解析由 Adapter 根据当前 observation、绑定实体、标定和 profile 完成。
Agent 不生成目标 pose，不把仿真器 actor pose 当 observation evidence。

关系语义只保留可跨任务复用的最小集合。新增关系必须先证明多个任务需要，并写入
ToolSpec/Verifier 契约；不为单个 RoboTwin task 创建 Core 专用字段。

### 3.3 义务与效果

PlanNode 现有的 `dependencies`、`conditions`、`required_evidence`、`produced_evidence`、
`effects` 和 `resources` 已足以承载第一版：

- `blocks_ranking_size` 产生 `at:<entity>:<slot>`；
- `stack_blocks_three` 产生 `on:<upper>:<lower>` 和稳定支撑证据；
- `put_bottles_dustbin` 产生 `inside:<bottle>:<container>` 和容器状态证据。

这些字符串是可审计的语义事实，不是第二状态机。事实的真实性由 Runtime/sensor/simulation
证据提供，Verifier 只按声明的 `TaskVerificationContract` 聚合。

## 4. 各任务如何落到同一流程

### 4.1 `blocks_ranking_size`

Adapter 的 `task_goal_facts` 返回尺寸排序对应的 opaque slot goal。Agent/语义理解只负责
把当前实体与目标事实匹配，操作仍是普通 `object.relocate`：

```text
observe -> understand/capabilities -> grasp -> prepare -> acquire -> place(goal_ref=size-slot)
```

三个方块是否可以并行，不由 PlanGraph 单独决定。由于每次 place 都改变场景，默认使用
连续 segment；只有独立、同一场景且 Gateway 明确支持的 Query 才可并行。每次 world change
后重新 observe/bind，避免旧实体几何继续用于后续候选。

### 4.2 `stack_blocks_three`

仍复用 `object.relocate`，但目标是支撑关系而不是固定独立槽位：

```text
place(block-1, goal_ref=stack-base)
  -> fresh observe/bind
place(block-2, goal_ref=on:block-1)
  -> fresh observe/bind
place(block-3, goal_ref=on:block-2)
```

第二、三次目标几何必须由当前观测到的下层物体和支撑证据解析。不能在初始 DAG 中写入
未来方块的自然语言角色或预估 pose。每次堆叠后要求支持关系、姿态/高度容差和稳定性
证据；仅有 `object.place` terminal 不代表堆叠成功。

### 4.3 `put_bottles_dustbin`

三个瓶子的目标可共享同一个容器 goal，但每个义务的 `obligation_ref` 和 subject
必须唯一：

```text
place(bottle-1, goal_ref=inside:dustbin)
  -> fresh observe/bind/container-state
place(bottle-2, goal_ref=inside:dustbin)
  -> fresh observe/bind/container-state
place(bottle-3, goal_ref=inside:dustbin)
```

不能通过简单删除唯一性检查来处理共享目标。应由 Adapter/目标事实声明该容器允许多实体
占用，并由每一轮当前容器状态决定是否仍可放入。若瓶子进入容器后被遮挡，必须由可信的
Runtime/sensor/simulation 结果提供 containment evidence；视觉不确定时停止或重新观察。

三次 Action 默认串行，因为它们共享容器状态并连续改变世界；两个独立 Action POST 不能
伪装成同步操作。

## 5. Adapter 与 Runtime 边界

引入 provider-neutral 的 Adapter 协议，而不是扩大 `BlocksRankingRgbTaskAdapter`：

```text
TaskAdapter
  - task_identity()
  - scene_entities(task, observation)
  - task_goal_facts(task, seed)
  - capability_facts(scene_revision)
  - resolve_goal_geometry(goal_ref, current_scene)
  - postcondition_evidence(goal_ref, current_scene)
  - benchmark_result(task)
```

其中：

- `scene_entities` 只输出当前绑定所需的实体事实；
- `task_goal_facts` 输出 benchmark 目标或明确的 observation-owned 目标，不输出动作授权；
- `resolve_goal_geometry` 只在 Adapter/Runtime 内把 opaque relation 变成当前路线输入；
- `postcondition_evidence` 负责 Adapter 能测量的关系事实，不直接改 PAOS 任务状态；
- `benchmark_result` 只供 post-run acceptance。

三项任务各自可以有薄的任务映射模块或 profile，但共享实体解析、目标引用、路线准备、
错误分类、场景修订和结果投影。PAOS Core、公共 Skill 和 Agent prompt 不导入 RoboTwin/SAPIEN。

## 6. 计划、资源和并发语义

### 6.1 分段计划

首段只物化当前场景中可绑定的一个或一组义务。完成后必须满足：

1. task-owned Action/Session 已 terminal；
2. Runtime settlement 已记录 world-change 结果；
3. 新 scene revision 已得到可信 observation；
4. 后续实体、目标和几何重新绑定；
5. Coordinator 再通过 `forge_task_continue_plan` 追加新 revision。

这保持同一个 AgentTask 身份，不创建第二个 scheduler，也不在未知物理结果上继续推进。

### 6.2 资源

- 单臂选择使用现有 `CapabilitySnapshot` 和 `ArmAssignment`；
- 需要切臂时使用显式 park/settlement 节点；
- 多对象共享容器或支撑关系通过语义依赖和当前事实表达，不让 PlanGraph 直接持有物理锁；
- 真正同步的双臂路线必须由一个 Gateway-owned atomic route bundle 提供共同时间线、碰撞范围、取消范围和证据；当前三个任务不要求开启该能力。

## 7. Agent Route Contract

实现前应在 feature card 中固定以下路由事实：

| 项目 | 归属 |
|---|---|
| 决策 owner | Agent 选择实体、义务顺序和可用目标关系；Coordinator 固化 revision |
| 上下文选择 | 只投影当前 scene revision、当前义务和明确 required evidence |
| 可调用能力 | 现有通用 Query/Action Tool；不新增 RoboTwin 专用公共 Tool |
| Runtime admission | Gateway/Runtime 校验 candidate、calibration、workspace、collision、IK、limits 和 stop policy |
| 证据 | observation、preparation、settlement、postcondition 和 benchmark evidence 分层保存 |
| 成功/失败/unknown | Tool terminal、PAOS Verifier 和 RoboTwin benchmark result 分开；unknown fail-closed |
| 恢复 | 只对可信只读事实重新投影；不重发 unknown Action/Session，不盲目重放动作 |
| 取消/停止 | 由 Runtime/Gateway/Coordinator 原有 owner 处理，继续保留 stop path |
| no-motion | 规划、适配器单测和 Fake Gateway 不授权运动；真实仿真需单独批准 |

## 8. 实施阶段

### 阶段 A：先稳定通用契约

- 写 feature card，锁定 ToolSpec、目标关系、证据、failure/unknown 语义；
- 将实体绑定从 block-specific 语义改为通用实体；
- 将 destination 唯一性改为 subject/obligation 唯一性，并显式表达目标的占用策略；
- 保持历史 `blocks_ranking_rgb` 记录兼容，不新增任务名分支。

### 阶段 B：重构 Adapter 工厂

- 用通用 `TaskAdapter` 协议替换单一 RGB Adapter 入口；
- 为 size、stack、dustbin 提供薄任务映射和 profile；
- 将目标几何、容器/支撑解析和 benchmark checker 留在 adapter/runtime；
- PAOS Core 仍只接收 provider-neutral facts。

### 阶段 C：复用计划编译与续段

- 保留现有七 Tool 操作链；
- 为义务增加 goal relation、effects、refresh-after-world-change 和 postcondition evidence；
- 对 stack 和 dustbin 使用逐段续接；
- 不把未来场景实体写成一个静态计划中的自然语言占位符。

### 阶段 D：验证与部署

顺序为：

```text
pure contract tests
  -> Fake Gateway conformance
  -> generic capability runtime tests
  -> adapter/profile tests
  -> no-motion route/readiness tests
  -> separately approved simulation acceptance
```

每个任务至少保存：任务/profile、seed、scene revision、observation/calibration、候选和路线
证据、每段 settlement、postcondition evidence、PAOS verifier verdict、RoboTwin benchmark
result、视频或失败产物。普通单元测试不能替代真实仿真验收。

## 9. 必须保持的非目标

- 不在 PAOS Core 中导入 RoboTwin、SAPIEN 或 vendor SDK。
- 不在 Skill 名称或公共 ToolSpec 中写入任务名、颜色、对象类别或仿真器字段。
- 不创建第二个调度器、状态库、执行协议或任务专用 verifier。
- 不把 benchmark `check_success()` 当作 PAOS 任务成功。
- 不从视觉猜测、颜色、目标或模型文本推断 possession/inside/on 事实。
- 不放宽 workspace、collision、IK、joint limits、calibration、scene binding、Action admission 或 `motion_authorized`。
- 不把两个独立 Action POST 当成同步双臂操作。
- 不为本方案新增 speculative hash、baseline 或全局 gate；复用现有 graph/policy/artifact digest 契约。

## 10. 主要验收矩阵

| 维度 | `blocks_ranking_size` | `stack_blocks_three` | `put_bottles_dustbin` |
|---|---|---|---|
| 实体绑定 | 三个方块唯一、同 scene | 三个方块唯一、支撑对象随 revision 更新 | 三个瓶子唯一，容器可被多义务引用 |
| 目标事实 | 尺寸排序槽位 | base/upper 支撑关系 | 容器 containment 关系 |
| 操作链 | 复用 relocate | 复用 relocate + 逐段刷新 | 复用 relocate + 容器状态刷新 |
| 失败重点 | 目标匹配/路线不可行 | 支撑不稳定/目标过期 | 容器满、遮挡、inside 未确认 |
| 最终验证 | 所有排序关系满足 | 完整 on 链满足 | 三个 inside 关系满足 |
| 运动边界 | 默认 no-motion，单独批准仿真 | 默认 no-motion，单独批准仿真 | 默认 no-motion，单独批准仿真 |

## 11. 参考实现位置

- PAOS 所有权与计划规则：`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`
- 功能引用卡与 RoboTwin 接入顺序：`docs/forge/FEATURE_REFERENCE_CARDS.md`
- 当前通用操作计划入口：`examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py`
- 当前多对象绑定入口：`examples/forge-skills/pick-place-workflow/src/pick_place_workflow/multi_object_agent.py`
- 当前 RoboTwin task adapter：`examples/forge-adapters/robotwin20/runtime/robotwin_blocks_ranking_adapter.py`
- 当前 persistent Runtime：`examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py`
