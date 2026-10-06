# Prepare/Action Route-Plan Consistency Diagnosis / Prepare/Action 路线计划一致性诊断

## Scope / 范围

本诊断记录 `manipulation.prepare` 已通过、`object.acquire` 在零 simulator step 前再次规划失败的问题。目标是明确 PAOS 控制面、Readiness、Runtime Adapter 与 AgentLoop 的责任边界；不把问题绑定到颜色、排列、benchmark task ID、固定实体、固定相机或固定机械臂。

This diagnosis records the case where `manipulation.prepare` passed but `object.acquire` replanned and failed before any simulator step. It defines ownership across the PAOS control plane, readiness, Runtime Adapter, and AgentLoop without binding the fix to colors, arrangements, benchmark IDs, entities, cameras, or a fixed arm.

## Evidence / 证据

- Task: `task_e90cab6880fa4f86`; revision: `revision_6d305cee948c44c3`.
- Entity/candidate: `entity://e1` / `candidate://e1/27`.
- `manipulation.prepare`: `status=available`; selected assignment arm `left`; kinematic, collision, and workspace checks `pass`.
- Readiness artifact: `artifact://simulation-route-readiness/8adc445f2d113843fa8d2039e76265edcf4f927ea9715566139b551d380036f0`; left arm `pass`, right arm approach `IK_FAIL`; route digest `d9452c4752ee0e666453d4afe54f16ca27a77d79b0b72c63ba4ac2e7d45a5a2c`.
- `object.acquire`: invocation `invocation://object-acquire/73e8d37c5e704ee1`, attempt `attempt://object-acquire/c0140cb59a31493b`; failure `SimulationProbeError: no arm can plan complete candidate route`.
- Action artifact: `simulator_steps=0`, `phases=[]`, `world_change_started=false`, `outcome_known=true`, `failure_owner=execution`; no grasp, lift, placement, or scene revision was produced.

## Concrete Failure and Mechanism Gap / 具体失败与机制缺口

`RouteReadinessEvaluationAdapter` and `evaluate_route_arm()` establish that a route is statically usable and the assignment stores only route/arm/readiness references. During Action, `execute_candidate_phases()` calls `evaluate_route_arm()` again. The second numerical planning call can disagree with the first even when all input digests match. Current code then raises one generic error at `robotwin_simulation_probe_worker.py` where the per-arm attempts are held only in transient `execution_state`.

`RouteReadinessEvaluationAdapter` 与 `evaluate_route_arm()` 证明路线静态可用，assignment 只保存 route/arm/readiness 引用。Action 阶段 `execute_candidate_phases()` 再次调用 `evaluate_route_arm()`；即使所有输入 digest 一致，第二次数值规划也可能与第一次不同。当前代码随后在 `robotwin_simulation_probe_worker.py` 抛出一个通用错误，逐臂 attempts 只存在于临时 `execution_state`。

## PAOS Ownership Rule / PAOS 所有权规则

1. Readiness owns route planning and emits a persistent execution-plan artifact containing selected arm, route digest, scene/world bindings, initial joint state, and every phase/waypoint trajectory needed by the Action boundary.
2. Action owns only preflight binding validation, stop handling, controller execution, and terminal evidence. It consumes the prepared plan and must not silently solve the same complete route again.
3. If scene, world, assignment, initial joint state, controller profile, or plan artifact binding diverges, Runtime returns a structured preflight divergence with zero-motion evidence. It does not switch arms, candidates, or retry.
4. AgentLoop owns whether to stop, refresh evidence, or propose a replan from the structured result. Core does not infer recovery from an exception string.

1. Readiness 负责路线规划并产生持久化 execution-plan artifact，包含选定机械臂、route digest、scene/world 绑定、初始关节状态及 Action 所需的每阶段/每 waypoint 轨迹。
2. Action 只负责执行前绑定校验、停止控制器、执行控制命令和终态证据；消费 prepared plan，不再静默求解同一完整路线。
3. scene、world、assignment、初始关节、controller profile 或 plan artifact 发生漂移时，Runtime 返回结构化 preflight divergence，零动作 fail-closed；不自动换臂、换候选或重试。
4. AgentLoop 根据结构化结果决定停止、刷新证据或提出 replan；Core 不从异常字符串推断恢复。

## Required Invariants / 必须保持的约束

- `motion_authorized` remains false for preparation and static readiness; Action authorization remains an independent runtime gate.
- No simulator step or controller command occurs before plan, scene, world, assignment, and start-state validation.
- A zero-step failure has `changed_entity_refs=[]`, `new_scene_revision=null`, and `carry_forward_authorized=false`.
- Existing complete-route collision, IK, joint-limit, workspace, frame, calibration, freshness, stop, reconciliation, and settlement gates remain active.
- Legacy readiness artifacts without an execution plan are rejected explicitly as an input-contract failure; they are not silently re-planned.

## Acceptance / 验收

- Regression 1: readiness produces a plan; Action consumes it without a second complete-route solve.
- Regression 2: mutate initial joint state or world/route binding before Action; receive structured divergence with `simulator_steps=0` and no entity-change claim.
- Regression 3: force a route execution failure after plan consumption; terminal evidence contains selected arm, failed phase, underlying reason, and arm attempts.
- Regression 4: arbitrary route/entity fixture passes without RGB or task-specific branches.
