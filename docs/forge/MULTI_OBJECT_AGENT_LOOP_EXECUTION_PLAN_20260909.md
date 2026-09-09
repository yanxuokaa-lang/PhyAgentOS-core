# 多对象完整 Agent Loop 执行方案

日期：2026-09-09 20:15（Asia/Shanghai）  
范围：Agent 接收任务 -> 任务分解 -> PlanGraph -> Tool/Gateway 执行 -> 多对象连续 acquire/place -> 最终 Verifier。  
明确不接入：进化模块、真实硬件、第二套 scheduler、第二套 task store、跨 Tool lease。

## 1. 审核结论

总体方向符合 PAOS 的控制面/执行面分离原则，但原方案不能直接作为最终实现。必须先关闭以下问题：

1. 固定的 `observe -> capabilities -> understand -> grasp -> prepare -> acquire -> place` 只能是 pick-place Skill 的 baseline policy；Agent-composed 计划必须保留语义义务和动态 Tool candidate 选择能力。
2. 场景实体必须绑定当前可信事实：`entity_ref`、benchmark object identity、destination、observation、scene revision、frame、calibration、geometry/capability/assignment evidence。
3. acquire/place 必须区分原始候选依据和当前执行现场。场景变化后，Runtime/provider 重新判断 place 准入；不把新 scene revision 伪装成旧候选的延续。
4. `accepted` 不等于 Action 完成；`unknown`、cancel requested、停止未确认和失败后的已知世界变化必须保留，不能投影成无效果成功或 `cancelled_before_start`。
5. 持物、资源占用、owner、接续和退出由 Runtime/provider 负责。AgentTask 只记录事实，不创建跨 Tool lease。
6. 一个对象完成不能 finalise 多对象任务；最终 Verifier 必须检查所有目标及已完成目标是否保持。

## 2. 所有权和执行边界

| 责任 | 唯一权威 | 本阶段约束 |
|---|---|---|
| 语义义务、依赖、Tool candidate | `PhyAgentOS.planning` / Skill policy | 纯校验，不调用 Gateway |
| 任务、Revision、Execution、Evidence | `AgentTaskCoordinator` + SQLite | 不在 runner 中复制状态 |
| Query/Action/Session 生命周期 | Forge Gateway + `ForgeToolClient` | Agent 只调用 wrapper |
| 场景、几何、路线、持物和资源事实 | adapter/provider/Runtime | 缺失或未知时 fail-closed |
| 用户级成功 | `ForgeTaskVerifier` | 只由 `finalize_task()` 产生最终 verdict |
| Agent 编排 | `AgentLoop` + `PlanningLoopAdapter` | 不直连 provider 或 simulator |

物理路径必须保持：

```text
AgentLoop -> Forge Tool wrapper -> ForgeToolClient -> Gateway -> ToolEndpoint -> Runtime/provider -> simulator
```

## 3. 分阶段执行

### 阶段 A：场景事实和任务分解

- 完成一次可信 `scene.observe` / `scene.understand`。
- 只选择唯一、可执行的方块实体；排除桌面、容器表面和没有 benchmark identity 的模型实体。
- 每个实体生成一个 relocation obligation，并绑定目的地不透明引用；不得把颜色、数量或布局写死在 core planner。
- 将 observation、scene revision、frame、calibration、geometry artifact 和来源 evidence 作为输入事实保存。

### 阶段 B：PlanGraph

- 默认采用 Agent-composed semantic graph。
- 现有七节点展开只能通过显式 Skill baseline policy 使用。
- 每个对象使用独立 obligation；依赖关系只表达语义先后，不表达资源租约。
- 所有对象连接到一个 `verify` 节点。

### 阶段 C：逐节点 Agent 执行

- 使用 `AgentLoop.build_long_horizon_controller()` 和 `PlanningLoopAdapter`。
- 每个 Tool 调用必须带完整 planning binding，并由 `AgentComposedDispatch` 进行 admission。
- Query 必须 terminal 后才可作为证据；Action 必须经过 start -> status/result -> `observe_action`。
- `accepted`、pending、timeout、unknown、cancel requested 都不能完成节点。
- acquire 成功后保留 Runtime 的 holding/resource owner 事实；place 使用当前 scene revision 重新准入。
- 每次 world-changing Action 后获取新的 scene revision，后续对象不得复用失效现场证据。

### 阶段 D：最终验证

- 所有 relocation obligations 的 place 节点都 terminal succeeded 后才允许进入 verify。
- `AgentTaskCoordinator.finalize_task()` 聚合全部 execution/evidence 并调用 Verifier。
- Verifier 必须检查每个对象的最终位置、未破坏先前目标以及 evidence 属于当前 task/revision。
- 任一对象失败、unknown、取消或证据不足，任务不得报告 success。

## 4. 必须覆盖的失败路径

- 第二对象使用第一对象 place 后的新 scene revision。
- 目标实体缺失、重复 identity、重复目的地或桌面被误选。
- acquire 返回 unknown；禁止重发相同 Action，必须先对账。
- place 失败但已产生世界变化；保留变化事实并要求 fresh observation/replan。
- cancellation accepted 但停止未确认；任务保持 cancelling/unknown，不报告成功。
- Verifier rejection；任务失败或进入既有 recovery/replan 状态。
- 只完成一个对象时调用 finalize；必须被 Coordinator 拒绝或得到非成功结果。

## 5. 验收入口和证据

最小可复现测试入口：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src \
python -m pytest -q examples/forge-skills/pick-place-workflow/tests/test_multi_object_agent.py
```

广域回归沿用仓库既有 PAOS/Skill 测试命令；真实 RoboTwin 仅在独立环境和 dry-run/no-motion 配置下执行。不得把 FakeGateway、模型感知或 Action accepted 作为真实机器人成功证据。

## 6. 六维验收矩阵

| 维度 | 通过条件 | 必须保留的证据 |
|---|---|---|
| 架构集成 | 一个 AgentTask、一个 Coordinator、一个 Gateway 路径；无第二 scheduler/store | PlanRevision、Tool records、controller result |
| 失败路径 | unknown/失败/取消/Verifier rejection 不被误判成功；世界变化不丢失 | execution status、failure code、scene revisions、recovery result |
| 权限与安全 | 无直连 provider；frame/calibration/workspace/route readiness 缺失即阻断；motion authority 不由 planner 产生 | Tool admission、Runtime context、`motion_authorized=false`、dry-run 记录 |
| 配置与复现 | 实体/目的地/scene/profile 来源显式；测试可在隔离环境重跑 | profile、observation/evidence refs、命令和环境记录 |
| 可维护性 | 复用现有 Coordinator/PlanningLoop/Tool API；baseline 与 dynamic policy 分离 | 模块边界、无重复生命周期实现、focused tests |
| 可观察性 | 每个对象、节点、Action、scene revision、Verifier verdict 可追踪 | task events、execution records、artifact/evidence refs、最终 verdict |

六维验收必须在阶段 A-D 全部完成后执行；本文件之前的设计审核记录不等于最终验收。
