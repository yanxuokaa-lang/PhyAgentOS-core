# v12.9.0 Implementation Review / 实现审核

## Findings / 审核发现

- Blocker: 0.
- Major: 0.
- Minor: 0.

The review found no acceptance-blocking issue after adding the effect-scene mismatch regression. The original `node_selection_no_progress` result remains a correct bounded-loop outcome; this change fixes the missing ToolSpec recipe that caused the Agent to reach that guard without producing a selection.

补充 effect-scene 不匹配回归后，未发现阻塞验收的问题。原有 `node_selection_no_progress` 仍是正确的有界收敛结果；本次修复的是导致 Agent 在没有 selection 的情况下触发该保护的 ToolSpec 配方缺口。

## Seven-Dimension Review / 七维审核

### 1. Architecture / 架构

Pass. Generic projection syntax and execution remain in `PhyAgentOS/planning`; source authorization and scene-lineage checks remain in the planning Coordinator boundary; Action-specific mappings live in the Skill ToolSpecs. No parallel Action argument compiler or secondary state machine was added.

通过。通用投影语法与执行位于 `PhyAgentOS/planning`，来源授权与场景血缘校验位于 planning Coordinator 边界，Action 字段映射位于 Skill ToolSpec；没有新增平行 Action 参数编译器或第二状态机。

### 2. Correctness / 正确性

Pass. `object.acquire` requires exactly one preparation assignment matching the Coordinator-owned `entity_ref`. `object.place` requires the acquisition result entity to match and its `new_scene_revision` to equal the current scene. Zero matches, duplicates, missing fields, wrong Tools, wrong scopes, stale scenes, and effect-scene mismatches fail before selection persistence.

通过。`object.acquire` 要求 preparation assignment 与 Coordinator-owned `entity_ref` 唯一匹配；`object.place` 要求 acquisition result 实体一致，且 `new_scene_revision` 等于当前场景。零匹配、多匹配、缺字段、错误 Tool/scope、旧场景及 effect-scene 不一致都在 selection 持久化前失败。

### 3. Recovery and Idempotency / 恢复与幂等

Pass. The existing durable progress fingerprint, one corrective turn, and `node_selection_no_progress` stop remain unchanged. Projection creates no invocation and performs no retry, Action replay, automatic continuation, or replan. A persisted selection continues through the existing resume and reconciliation path.

通过。既有持久化 progress fingerprint、一次纠正回合及 `node_selection_no_progress` 停止语义保持不变。投影不创建 invocation，也不重试、重放 Action、自动续接或 replan；已持久化 selection 仍由现有恢复与 reconciliation 路径处理。

### 4. Robotics Safety / 机器人安全

Pass for the changed boundary. The implementation only compiles selection arguments. Motion authorization, Action admission, freshness, frame/calibration validation, route/collision/IK/workspace checks, stop, reconciliation, and settlement are unchanged. Tests create no live task and issue no Gateway Query or Action.

变更边界内通过。实现只编译 selection 参数；运动授权、Action admission、freshness、frame/calibration、路线/碰撞/IK/workspace、stop、reconciliation 与 settlement 均未改变。测试不创建真实任务，也不调用 Gateway Query/Action。

### 5. Extensibility / 扩展兼容

Pass. Behavior is driven by ToolSpec producer identity, source scope, scene relation, join field, collection path, and output paths. Core contains no color, RGB order, benchmark ID, entity number, candidate number, camera, provider, or arm branch.

通过。行为完全由 ToolSpec 的 producer identity、source scope、scene relation、join field、collection path 与输出路径驱动；Core 不包含颜色、RGB 顺序、benchmark ID、实体/候选编号、相机、provider 或机械臂分支。

### 6. Observability and Maintainability / 可观测性与可维护性

Pass. `forge_plan_ready` exposes non-default `scene_relation`; projection failures report the source slot and violated Tool/scope/scene/join rule. The Skill YAML and Python ToolSpec definitions remain synchronized, and Skill version `2.10.15` records the contract change.

通过。`forge_plan_ready` 暴露非默认 `scene_relation`；投影错误指出 source slot 及违反的 Tool/scope/scene/join 规则。Skill YAML 与 Python ToolSpec 保持同步，Skill `2.10.15` 记录该契约变更。

### 7. AgentLoop Autonomy and Convergence / AgentLoop 自主性与收敛

Pass. The Agent still decides whether and when to select the Action and explicitly names one authorized producer record. The Coordinator only compiles declared facts and either persists one selection or one structured rejection. Core does not choose candidates, destinations, arms, continuation, or recovery actions.

通过。Agent 仍决定是否及何时选择 Action，并显式指定一条授权 producer record；Coordinator 只编译声明事实，并持久化一个 selection 或一个结构化 rejection。Core 不选择候选、目标、机械臂、续接或恢复动作。

## Validation / 验证

- Focused planning and projection regression: `118 passed`.
- Full Core suite with external plugin autoload disabled and `pytest_asyncio` explicitly loaded: `785 passed`.
- Full `pick-place-workflow` Skill suite: `375 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- No AgentTask, Gateway Query/Action, simulator step, Runtime restart, or physical motion was performed.

## Remaining Risk / 剩余风险

This is a no-motion contract proof. A deployment and live benchmark rerun are separate operations and are not claimed by this review. Runtime installation must occur only after proving no active invocation, Session, task binding, unresolved world change, or non-terminal AgentTask.

本审核是 no-motion 契约证明，不包含部署或真实 benchmark 重跑。安装 Runtime 前仍必须证明不存在活动 invocation、Session、task binding、未决 world change 或非终态 AgentTask。
