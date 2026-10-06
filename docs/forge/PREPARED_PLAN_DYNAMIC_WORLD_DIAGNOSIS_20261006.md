# Prepared Plan Dynamic-World Binding Diagnosis / Prepared Plan 动态规划世界绑定诊断

## Scope / 范围

本诊断记录 v12.8.2 在 Readiness 与 Persistent Action 之间遗漏完整动态规划世界绑定的问题。修复只使用 Adapter 已有的 provider-owned `dual_arm_state` 和 peer-arm projection，不绑定 RGB、颜色、排列、benchmark、具体实体、相机或固定机械臂。

This diagnosis records the missing dynamic planning-world binding between Readiness and Persistent Action in v12.8.2. The repair uses the Adapter's existing provider-owned `dual_arm_state` and peer-arm projection, without binding behavior to RGB, colors, arrangements, benchmarks, concrete entities, cameras, or a fixed arm.

## Failure / 失败场景

Readiness calls `prepare_planning_world()` and captures both arms before evaluating a route. The persisted prepared execution plan only retained the selected arm's `initial_qpos`. Persistent Action later captured a fresh dual-arm state, installed a fresh peer projection, and consumed the old trajectory. A peer arm moved between these stages could therefore make the old route invalid while all static route and scene references remained unchanged.

Readiness 在评估路线前捕获双臂状态并生成 peer projection，但持久化 execution plan 只保存选中臂的 `initial_qpos`。Persistent Action 随后重新捕获双臂状态、安装新的 peer projection，却直接消费旧轨迹。若非选中臂在两阶段之间移动，静态 route/scene 引用仍可能不变，但旧路线已经不再适用于当前世界。

## Ownership Rule / 所有权规则

1. Readiness owns the no-motion route solve and persists the dynamic state that made the solve admissible.
2. Persistent Action owns preflight comparison and must reject a stale dynamic world before any simulator step; it must not silently solve the route again.
3. AgentLoop receives `failure_owner=binding`, `failure_code=prepared_execution_world_state_drift`, `requires_replan=true`, and `recommended_action=refresh_declared_evidence`; it decides whether to refresh or replan.

1. Readiness 负责无运动路线求解，并持久化使该路线可准入的动态状态。
2. Persistent Action 负责执行前比较；动态世界过期时必须在任何 simulator step 前拒绝，不能静默再次求解路线。
3. AgentLoop 接收结构化漂移事实，由 Agent 自主决定刷新证据或 replan。

## Invariants / 不变量

- The binding is provider-neutral and stores the complete dual-arm state needed by the existing peer projection path.
- The comparison validates scene/frame/state identity and all arm qpos/drive targets before controller commands.
- Drift produces zero simulator steps, no changed entity claim, and no automatic arm/candidate switch or retry.
- `motion_authorized=false` remains unchanged for Readiness artifacts.

- 绑定由 Runtime/Adapter 所有，保存现有 peer projection 所需的完整双臂状态。
- 在 controller command 前验证 scene/frame/state identity 以及双臂 qpos/drive target。
- 漂移结果为零 simulator step、不声明实体变化，不自动换臂/换候选/重试。
- Readiness artifact 继续保持 `motion_authorized=false`。

## Acceptance / 验收

- A plan created from a dual-arm state loads through the real Persistent Action `_prepare` path.
- Mutating either arm's dynamic state before loading the plan returns a structured zero-motion drift failure.
- The unchanged path proves `evaluate_route_arm()` is never called during Action.
