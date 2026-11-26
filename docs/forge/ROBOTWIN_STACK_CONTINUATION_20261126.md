# RoboTwin stack continuation — 2026-11-26

状态 / Status: v18.1.0 已接通生产组合入口与无运动准备证据链。完整视觉 stack 尚未跑通：观测身份到执行身份的关系 Provider 映射、observed 支撑目标、真实路线/接触/停止和三块连续执行仍待完成。Motion remains disabled; no simulation or hardware action was started.

## 已完成与归属 / Implementation and ownership

v18.0.5 修复真实准备工厂删除 intent、丢失完整 route lineage 和错读 destination 的问题；选中的关系目标通过真实 Grounding 投影到对象与功能点，并经 `validate_scene_facts` 保留独立来源。 / v18.0.5 repaired the real preparation inputs and route lineage, and projected relation targets through Grounding with separate target provenance.

v18.1.0 的 Core 共用 `relation_manipulation_intent`，从冻结的节点语义/身份与当前 NodeContext 的成功直接前置 grasp Query 构造完整 intent；候选集必须来自持久查询，不在编译时捏造。`resolve_relation_context` 复用原 subtask 的 caller、活动 revision、执行记录、节点及输入绑定验证，再投影直接前置的完整 arguments/result；不扫描全任务的“最新结果”。已有权威持久 schema 拒绝跨 revision 记录，本轮没有新增 hash、gate 或全局 NodeContext 检查。 / Core owns trusted intent and active-plan evidence. The shared caller validation and existing authoritative store preserve revision boundaries; no latest-result scan or new hash/gate is added.

首次 `ForgePlanActivateTool` 和恢复用 `AgentLoop.activate_planning_task` 都注入动态读取 Coordinator 的 NodeContextProvider。`relation.establish` 的公开参数仍只包含关系语义、已选 relation candidate/result 与可信 intent，原始 grasp candidates、binding、capability 与内部 `coordinator_context` 不进入公开 schema。 / Both activation paths receive the live read-only context port; preparation-only fields remain private.

Adapter 的 `build_stack_relation_preparation_inputs` 从已解析的 Coordinator context 取得 scene.bind、grasp、capability、relation.target，核对实体、scene、observation、calibration、候选和坐标系，再用既有 `_artifact_path` 读取实际 JSON。artifact 的 schema/task_name/query/motion/source 必须与持久 Query 一致；pose/ref 取自持久 Query，artifact 本身没有这两个字段。 / The Adapter validates exact Query inputs/results and existing evidence JSON without inventing fields or paths.

任务、计划、证据与节点结算继续归 Coordinator，工作流归 AgentLoop；Adapter 管理几何来源与目标投影，Preparation/selector/PreparedRoutes 管理准备机制；Runtime/Gateway/worker 保持动作生命周期、取消和执行结算所有权。 / Existing owners retain task/node and Action lifecycle responsibilities; no parallel scheduler or state store is introduced.

## 可执行关系片段 / Executable relation segment

新入口 `compose_executable_relation_plan(...)` 保留原 `compose_relation_goal_plan(...)` 的语义计划行为，另编译一个显式 DAG：

```text
current observation + authorized understanding evidence
    ├─ scene.bind ── grasp.propose ────────┐
    ├─ manipulation.capabilities ─────────┤
    └─ relation.target ───────────────────┤
            scene.bind ─────────────────┤
                            relation.establish
```

调用方提供当前 observation/scene/frame/calibration、现有 understanding evidence ref、完整 semantic_intent、freshness/max_age；bind 与 grasp 通过既有 source projection 读取授权的 understanding。Action 的四个直接依赖均须实际完成并持久化，之后 dispatch 才读取 grasp 的 candidate_set。编译器不会创建已完成节点或原始抓取数组。 / The caller supplies current evidence and semantics. All four direct Queries execute before Action selection, and the candidate set is obtained only afterward.

## 显式 host 配置 / Explicit host composition

在已有有效 host profile 上增加以下配置，Runtime profile 的 task_name 必须为 `stack_blocks_three`，同时保留有效 `coordinator_workspace` 与 `binding_request`：

```yaml
stack_relation_preparation_enabled: true
simulation_action_mode: runtime_monitored
# coordinator_workspace and binding_request remain the existing configured values.
```

此开关默认 false；启用时 host 使用同一 Coordinator 装配 relation context、实际 artifact resolver 和 preparation factory。它拒绝与显式注入的 relation/subtask/perception ports 混用，也拒绝非 stack 任务。`runtime_monitored` 是现有准备 approval/任务定义装配的前提，关系 Provider 的 `motion_supported()` 仍恒为 False；注册工具不等于授权动作。 / The opt-in composes one Coordinator and the production factory; the existing action mode is required for preparation receipts, while relation motion remains explicitly unsupported.

嵌入者仍可显式注入 `build_stack_relation_execution_provider_factory(prepare_inputs=...)` 与 Coordinator 的 `resolve_relation_context`，此时不要同时打开 profile 自动装配。原零参 factory 可构造关闭运动的 Provider，但直接调用 prepare_route 会明确报 resolver 未配置。内部 `build_coordinator_ports` 现返回 perception、subtask resolver、relation resolver 三项，两个 resolver 属于同一 Coordinator。 / Explicit injection remains supported; the zero-argument factory keeps its previous explicit failure on missing preparation inputs.

## 证据边界与后续 / Evidence boundaries and next work

对象/碰撞的 `geometry_source` 与关系目标的 `target_geometry_source`/`target_evidence_refs` 独立保留。当前 relation artifact 来源为 `simulator_actor_geometry`，读取核验成功也不能称为 observed 支撑面。真实 scene.bind 使用 `frame_id=world` 和单独的 `observation_frame_id`；真实 grasp 响应使用 `frame.frame_id`，freshness/max_age 取自 Query arguments。 / Provenance and frame distinctions follow actual production payloads.

当前直通 relation Provider 的 worker 消费 execution entity ref。本轮只接受 bind 的观测 entity_ref 与其 execution_entity_ref 能和 relation Query 同一身份的组合；遇到 visual/execution 不同明确拒绝，不伪造重命名。下一阶段应在 Adapter relation Provider 利用已有 scene.bind 测量映射完成转换，保持公共语义一致。随后补 observed support Provider，再验证真实 controller route/contact/stop，最后同一 AgentTask 连续执行三块。 / The remaining identity conversion belongs in the Adapter, followed by observed support and actual execution qualification.

## 验证 / Validation

新增贯通测试通过真实 compiler、五个 ToolSpec 的 ready/selection、bind/grasp source projection、持久 Coordinator records/settlements、实际 grasp/capability/relation endpoints、relation endpoint 内部上下文、实际 JSON 读取和真实 Grounding/validator/Preparation/selector/PreparedRoutes。外部 worker snapshot、规划、碰撞/接触反馈仍由 fixture 替换；这不是完整 GPU route readiness 或物理稳定性实测。`client.start` 为 0，motion gate 在准备之前拒绝。 / The integrated path uses production boundaries with substituted external mechanisms and proves no motion was started.

失败覆盖：缺失/错误 artifact、来源缺失、query/task/motion 漂移，候选/pose/frame/实体错误、visual/execution 不同、非直接前置、多匹配、失败 Query、未结算、旧 scene/caller、intent 变更；跨 revision 由真实 store schema 拒绝。 / Failures preserve explicit evidence and ownership boundaries before target publication or preparation.

主审 18 套件共 **517 passed**；新增 context + host 定向组合 **63 passed**。Ruff 修复 4 处 import 顺序与新测试 15 处单行 if 后通过。额外 `test_planning_selection.py` 的 5 个旧 fixture 失败全部用 HEAD `planning.py` 动态载入复现相同错误，本轮不改；关联 subtask fixture 缺 `planning_selections` 也经 HEAD 复现后补初始化。 / All 517 scoped tests pass. Five additional selection-fixture failures are independently reproduced against HEAD and remain outside this change.

```bash
PYTHONPATH=examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q tests/test_planning_dispatch.py tests/test_planning_loop.py tests/test_planning_task_integration.py tests/test_planning_projection.py tests/test_planning_source_assembly.py tests/test_planning_dispatch_bootstrap.py tests/test_planning_end_to_end.py examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py examples/forge-skills/pick-place-workflow/tests/test_relation_execution.py examples/forge-skills/pick-place-workflow/tests/test_relation_target.py examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py examples/forge-adapters/robotwin20/tests/test_stack_relation_preparation.py examples/forge-adapters/robotwin20/tests/test_stack_relation_execution.py examples/forge-adapters/robotwin20/tests/test_persistent_host.py examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py examples/forge-adapters/robotwin20/tests/test_grounding.py examples/forge-adapters/robotwin20/tests/test_route_inputs.py --tb=short
.venv/bin/ruff check --select I,E701 PhyAgentOS/forge/task.py examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_inputs.py examples/forge-adapters/robotwin20/tests/test_stack_relation_context.py examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py
```
