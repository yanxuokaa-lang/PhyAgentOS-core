# LabUtopia/PAOS 子任务结算方案复核

日期：2026-10-20
状态：方案复核完成，代码实现尚未开始

## 1. 结论

当前 `object.pour_cycle`、`tool.stir_cycle` 和 LabUtopia adapter 可以作为控制器与反馈实验基础，但不能直接作为最终的 PAOS Agent 工作流。原方案有三个 Blocker：

1. LabUtopia 的 `task_projection.py`/`profile.py` 仍把 profile 中的 `source_path`、`destination_path` 作为目标绑定来源；Agent 没有通过 RGB/depth/segmentation 选择试剂瓶和烧杯。
2. `*_cycle` 自己执行 acquire、process、return、release、retreat，吞掉了 PAOS 已有的抓取、持有和放置边界。
3. 当前 `PlanNode`/`NodeSettlement`/`AgentLoopNodeExecutor` 的语义是一个节点对应一个 selected Tool；如果把 acquire、pour、place 分成节点，Agent 会在每个 Tool 之后重新获得控制权。

修正版原则是：

```text
一次 Agent 规划长程任务
  -> 一个子任务节点被选中
  -> SubtaskExecutor 在同一子任务内顺序调用多个 PAOS Tool
  -> 只产生一个子任务级 NodeSettlement
  -> Agent 在子任务边界继续、恢复或重规划
```

内部 Tool 仍必须留下独立的 invocation、attempt、result、feedback 和错误事实；这些事实不等于 Agent 的重新规划触发器，也不新增第二套 task/settlement store。

## 2. 与 PAOS 现有边界对齐

| 责任 | 继续使用的现有 owner | 本方案的约束 |
| --- | --- | --- |
| Task、revision、取消、恢复预算 | `AgentTaskCoordinator`、`PlanRevision`、SQLite | 不在 LabUtopia adapter 复制生命周期 |
| 规划图与依赖 | `PhyAgentOS.planning.PlanGraph` | 一个实验室子任务对应一个语义节点；工具顺序属于子任务内部执行契约 |
| Tool transport | `ForgeToolClient` -> Gateway Tool API -> ToolEndpoint -> Dora | SubtaskExecutor 只能通过既有 Tool 入口，不得直连 Isaac Sim actuator |
| 单个 Tool 事实 | `ToolExecutionRecord`、权威 Action result | 每个内部调用保留 record，但不立即生成 Agent 可见结算 |
| 子任务结算 | 现有 `NodeSettlement` 的子任务节点投影 | 每个子任务只写一个终态 settlement；`source_tool_id` 指向子任务编排入口 |
| 用户级成功 | `ForgeTaskVerifier` 与 `TaskVerificationContract` | 不能由某个 Tool 或子任务结果直接宣布整个实验成功 |
| 感知/几何/IK/碰撞 | LabUtopia adapter 与 readiness provider | 真实观测、标定、工作空间和碰撞检查必须先于运动 |

`PhyAgentOS/planning` 仍然保持纯协议库：不调用 Gateway、不写 SQLite、不持有机械臂锁、不授权运动。若需要增加 `SubtaskSpec` 类型，应放在 planning 的 provider-neutral contracts；执行和持有状态仍由 Coordinator/Runtime/adapter 按既有 owner 管理。

## 3. 修正后的对象与调用边界

### 3.1 子任务节点

长程任务图只暴露子任务节点，例如：

```text
pour_reagent_A -> pour_reagent_B -> stir_mixture
```

每个节点的 `input_bindings` 必须引用当前观测生成的 `entity_ref`、`destination_ref`、`grasp_candidate_ref`、`process_frame`、`scene_revision`、`frame_id`、`calibration_ref` 和 freshness。不能把 USD Prim 路径、固定 z 偏移或固定夹爪宽度作为 Agent 输入。

子任务节点的 frozen ToolPolicy 选择一个受治理的子任务入口（例如 `manipulation.execute_subtask`）。旧的单 Tool 节点继续兼容，因此不需要把所有 PAOS 任务一次性迁移。

### 3.2 SubtaskSpec 与 SubtaskExecutor

`SubtaskSpec` 是一个有序、有限的内部调用描述，不是第二个任务图或第二个 scheduler。每个调用声明：

- `tool_id`：`object.acquire`、`manipulation.prepare_held`、`object.pour`/`tool.stir`、`object.place`；
- `phase`：`acquire`、`prepare`、`process`、`place`；
- 参数来源：当前绑定、前一内部 Tool 的终态结果或新观测；
- 资源约束：Franka、夹爪和当前 possession 必须独占；
- 失败策略：停止、有限 no-motion 重试、或在子任务终态标记 `failed`/`outcome_unknown`。

`SubtaskExecutor` 由现有 Coordinator/PlanningLoop 的执行边界驱动，内部通过既有 Forge Tool API 顺序调用，不直接导入 Isaac Sim 控制器。它维护当前 possession、scene revision、活动 invocation、内部 phase 和取消状态；世界变化后的新 scene revision 必须传给后续内部调用。

内部调用的记录约束：

- 每条 `ToolExecutionRecord` 都包含原有 task/revision/node 归属，并增加可查询的 `subtask_id` 与有序 `sequence_index`（实现阶段才修改模型）；
- 内部 Query/Action 的 `result`、反馈 artifact 和 failure code 仍不可变保存；
- `SubtaskExecutor` 不在每个内部 Tool 结束时调用 `settle_node`，也不把中间结果交给 AgentLoop；
- 最后一个内部 Tool 终结、取消确认或结果未知后，才组装一个子任务结果。

### 3.3 一次子任务结算

子任务终态复用 `NodeSettlement`，而不是建立另一张 settlement 表：

```text
NodeSettlement.node_id        = subtask node
NodeSettlement.source_tool_id = manipulation.execute_subtask
NodeSettlement.invocation_id  = outer subtask invocation
NodeSettlement.status         = completed | failed | outcome_unknown | cancelled_before_start
NodeSettlement.evidence_refs  = internal Tool receipts + before/after/process evidence
NodeSettlement.scene_revision = last trusted scene revision
```

子任务结果投影至少包含：

- `completed_tool_ids` 和对应 record/artifact 引用；
- `failed_phase`、`failure_code`、`outcome_known`；
- `possession_state`、`release_confirmed`、`retreat_completed`；
- `source_scene_revision`、`new_scene_revision`、观测 freshness；
- 倾倒或搅拌的实测过程指标；
- `recommended_action`：继续下一子任务、刷新观测、恢复、取消或要求 Agent 重规划。

这个投影是执行事实的聚合，不授予任务成功，不覆盖内部 Tool 的原始事实。

## 4. AgentLoop 行为修正

### 4.1 允许的模型回合

1. Discovery 回合：执行 `scene.observe`、`scene.understand` 等 Query，得到真实绑定并物化长程子任务图。
2. 子任务选择回合：`forge_plan_ready`/`forge_plan_select` 只选择当前子任务入口及其绑定；成功 admission 后立即结束模型回合。
3. 子任务执行：`SubtaskExecutor` 在没有 LLM 调用的情况下顺序执行内部 Tool，等待每个权威 result，并对账取消/unknown。
4. 子任务结算回合：Agent 只收到一个子任务级 settlement projection，决定继续下一子任务、刷新观测或进入受限恢复。
5. 当前场景段的全部子任务完成后，PlanningLoop 才返回 `segment_completed`；继续计划或最终验证使用既有 continuation/finalization 边界。

### 4.2 明确禁止

- 不把 `object.acquire`、`object.pour`、`object.place` 分成三个 Agent-facing PlanNode；
- 不在内部 Tool result 后再次调用 `AgentLoop.run_node_turn`；
- 不让内部 Tool 通过自然语言反馈触发 replan；
- 不让 `SubtaskExecutor` 创建 task/revision、直接写 SQLite 或绕过 Gateway；
- 不把 status snapshot 当作终态；必须等待 result payload 后再生成子任务结算；
- Action 已开始且结果未知时不自动重发倾倒/搅拌；先按 invocation 对账并在子任务边界恢复。

## 5. 实验室 Tool 组合

### 5.1 试剂 A 倾倒子任务

```text
scene binding from observation
 -> object.acquire(entity_ref=A, grasp_candidate_ref)
 -> manipulation.prepare_held(operation=pour)
 -> object.pour(destination_ref=beaker, measured process frame)
 -> manipulation.prepare_held(operation=place)
 -> object.place(return_destination_ref)
 -> one subtask settlement
```

### 5.2 试剂 B 倾倒子任务

与 A 使用相同 Tool 能力，但 `entity_ref`、几何、抓取候选和返回目标全部来自当次观测，不复制 A 的路径或位姿。

### 5.3 玻璃棒搅拌子任务

```text
scene binding from observation
 -> object.acquire(entity_ref=glass_rod, grasp_candidate_ref)
 -> manipulation.prepare_held(operation=stir)
 -> tool.stir(destination_ref=beaker, tool_tip/process frame)
 -> manipulation.prepare_held(operation=place)
 -> object.place(return_destination_ref)
 -> one subtask settlement
```

`object.pour` 与 `tool.stir` 是可复用的持物 Tool，不绑定某个瓶子、玻璃棒规格或单一任务。`object.pour_cycle`、`tool.stir_cycle` 只能作为兼容/回放入口，不能作为新 Agent 规划的默认入口；兼容入口也必须标记其固定场景限制。

## 6. 感知与执行绑定

公开绑定链必须是：

```text
Isaac RGB/depth/segmentation
 -> scene.observe
 -> scene.understand (标签/类别/几何/位姿)
 -> grasp.propose
 -> readiness (IK/关节限位/工作空间/碰撞)
 -> SubtaskExecutor
```

绑定结果必须携带：

`entity_ref`、`semantic_label`、`category`、`measured_pose`、`measured_geometry`、`grasp_candidate_ref`、`destination_ref`、`destination_pose`、`process_frame`、`observation_ref`、`scene_revision`、`frame_id`、`calibration_ref`、`freshness_ms`、`confidence` 和 `provenance`。

LabUtopia adapter 可以在内部把已验证的 opaque `entity_ref` 映射到当前场景 Prim，以便调用 Isaac Sim API；该映射不能由 Agent 提供，也不能从 profile 的固定 `source_path` 推导出目标身份。USD actor/prim 真值、内部 pose 和 segmentation 只用于最终对照验收，不得替代观测输入。

## 7. 七维验收矩阵

| 维度 | 通过标准 | 失败证据 |
| --- | --- | --- |
| 1. 感知来源 | Agent 选择的是当前 RGB/depth/segmentation 绑定的标签和类别 | 目标直接来自 profile/Prim 名称 |
| 2. 绑定一致性 | entity/destination、pose、frame、calibration、scene revision、freshness 同源且未过期 | 混用旧观测或跨场景几何 |
| 3. Agent 粒度 | 每个子任务内部至少完成 acquire + process + place，Agent 只在子任务终态收到一次 settlement | 每个 Tool 后出现模型回合或 NodeSettlement |
| 4. 规划与安全 | grasp candidate 经过 Lula/RMPFlow、关节限位、工作空间和碰撞/attached-object 检查 | 仅 IK 成功就授权运动，或固定 offset 绕过检查 |
| 5. 真实持有/放置 | 夹爪闭合、抬升、连续持有、释放、支撑面和撤离均由观测/执行反馈确认 | 只看控制器返回值或归位标记 |
| 6. 过程反馈 | pour 使用实测瓶口对准/倾角/连续窗口；stir 使用实测棒尖轨迹/半径/深度/圈数/碰撞 | 只用请求参数或规划点数量判定完成 |
| 7. 结算与恢复 | 一个子任务一个 NodeSettlement；失败/unknown/取消保留内部 receipts，下一步只在子任务边界决定 | 内部 Tool 失败被伪造成成功或自动重放世界改变动作 |

## 8. 实施顺序与验证

1. **契约层**：增加子任务执行单元和内部调用归属字段；保留 legacy 单 Tool 节点和旧 cycle replay。先测 no-motion，不启动 Isaac Sim。
2. **工作流层**：让 `object.acquire`、`manipulation.prepare_held`、`object.pour`/`tool.stir`、`object.place` 由一个 `SubtaskExecutor` 顺序驱动；测试一个子任务只产生一个 `NodeSettlement`。
3. **感知层**：替换 `task_projection.py` 的 profile 目标绑定为 observation-derived binding；加入过期、错标签、错容器和场景版本变化测试。
4. **LabUtopia 执行层**：只消费 measured pose/geometry/grasp/process frame；Prim 映射保持 adapter 私有；dry-run 先验证，之后才做单子任务 live run。
5. **长程验收**：依次执行 A 倾倒、B 倾倒、玻璃棒搅拌；每个子任务一次 settlement，最后由任务 Verifier 进行顺序和实验目标验收。

首轮离线验证建议：

```bash
cd /home/yanxu/PhyAgentOS-forge
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src \
  .venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  examples/forge-skills/pick-place-workflow/tests/test_held_manipulation.py \
  examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_long_horizon.py
```

新增实现必须补充：

- `test_subtask_single_settlement.py`：三个内部 Tool 只产生一个子任务 settlement；
- `test_subtask_failure_boundary.py`：process 失败后不自动重复 process，保留持有和放置事实；
- `test_perception_binding_not_prim.py`：没有观测绑定或 freshness/scene 不一致时 fail closed；
- `test_agentloop_no_tool_replan.py`：内部 Tool 完成之间没有第二个模型回合；
- LabUtopia adapter 的 no-motion、dry-run 和单子任务 Isaac Sim 证据。

本次复核未启动 Isaac Sim、未调用 Gateway、未执行运动；上述命令和新增测试是实施阶段验收入口，不代表本轮已通过。
