# Implementation Review v12.9.1 / 实现审核 v12.9.1

## Review Scope / 审核范围

本审核复核 v12.9.0 的 Action predecessor projection，并以公开 ToolSpec、Core projection、Skill endpoint 和 Persistent Runtime 的真实所有权边界为准。验证全程 no-motion：未创建或恢复 AgentTask，未调用 Gateway Query/Action，未启动或停止 Runtime，未执行 simulator step 或物理运动。

This review re-examines the v12.9.0 Action predecessor projection at the public ToolSpec, Core projection, Skill endpoint, and Persistent Runtime ownership boundaries. Validation was entirely no-motion: no AgentTask was created or resumed, no Gateway Query or Action was invoked, no Runtime was started or stopped, and no simulator or physical step was executed.

## Findings and Fixes / 问题与修复

### Major 1 - Place consumed the acquisition input scene / Place 使用了 acquisition 输入场景

`object.place` admission correctly required an acquire predecessor whose `new_scene_revision` matched the current planning scene, but its field map compiled `scene_revision` from the predecessor's old `result.scene_revision`. A provider-neutral Adapter without the Persistent Runtime's private scene replacement could therefore receive a stale placement scene.

修复后，YAML 与 Python ToolSpec 均从 `result.new_scene_revision` 投影 place 的当前 `scene_revision`。回归断言 place 参数为 effect scene `scene-2`，并保留 effect-scene mismatch 的 selection 前拒绝。

### Major 2 - Public projection depended on private Persistent fields / 公开投影依赖 Persistent 私有字段

The place projection consumed `result.new_scene_revision` and `result.acquire_invocation_ref`, although the base acquire result schema declared neither and rejected additional properties. The old Core fixture manually supplied both, so it did not represent a legal public producer response.

修复后：

- `new_scene_revision` 是 provider-neutral acquire effect 字段；已知、成功且发生世界变化的结果必须发布它。
- `acquire_invocation_ref` 从 Gateway terminal envelope 的 `invocation_id` 投影，不再要求 provider 在业务结果中重复身份。
- Persistent Runtime 删除私有 invocation 结果扩展；缺失 acquisition effect scene 时保持 `world_change_started=true` 并降级为物理状态 `unknown`。
- Core fixture 通过公开 acquire output schema 校验，producer-to-consumer compatibility 不再依赖超 schema 数据。

### Minor 1 - Projection DSL admitted incoherent source shapes / Projection DSL 接受不一致配置

`ArgumentProjectionSourcePlan` previously accepted `scene_relation=predecessor_effect` on an evidence source and a standalone `unique_item_join_field`. Both configurations passed model validation but lacked coherent execution semantics.

现有 Pydantic validator 现在直接拒绝这两类配置。该修复位于既有 ToolSpec 加载边界，没有增加 hash、冻结 contract 或平行 gate。

## Seven-Dimension Review / 七维审核

| Dimension / 维度 | Result / 结果 | Evidence / 证据 |
|---|---|---|
| Architecture / 架构 | Pass | Effect identity belongs to the acquire public contract; invocation identity remains Gateway-owned; compilation remains in the existing projection path. |
| Correctness / 正确性 | Pass | Place receives the acquire effect scene, and the producer fixture validates against the published output schema before projection. |
| Recovery and idempotency / 恢复与幂等 | Pass | Failed, cancelled, stopped, and unknown results may omit an effect scene; known successful world changes cannot. Missing Persistent effect identity becomes explicit `unknown`, not fake success or retry. |
| Robotics safety / 机器人安全 | Pass within declared scope | No motion gate was weakened. Unknown physical outcome retains `world_change_started=true`, `outcome_known=false`; no execution was performed during review. |
| Extensibility / 扩展兼容 | Pass | Field paths use public record envelopes and provider-neutral ToolSpecs; no Adapter, color, order, object count, benchmark, camera, entity, candidate, or arm branch exists in Core. |
| Observability and maintainability / 可观测性与可维护性 | Pass | Failure code `missing_new_scene_revision`, public JSON Schema compatibility, YAML/Python parity, and Skill version `3.0.0` make the contract change explicit. |
| AgentLoop autonomy and convergence / AgentLoop 自主性与收敛 | Pass | Agent still selects the Action and authorized source record. Coordinator only validates and compiles facts; no automatic selection, execution, retry, continuation, refresh, or replan was added. `node_selection_no_progress` is unchanged. |

## Validation / 验证

- Focused Core planning/projection: `129 passed`.
- Full Core: `787 passed in 28.12s`.
- Focused Skill endpoint/Persistent paths: `130 passed`, followed by `57 passed` after the final failure-path regression.
- Full Skill: `379 passed in 8.12s`.
- Ruff, compileall, and `git diff --check`: passed.

## Acceptance / 验收

Blocker: 0. Major: 0. Minor: 0 after fixes. v12.9.1 supersedes the incorrect all-pass conclusion recorded for v12.9.0. The change is accepted for source-level merge and remains intentionally undeployed until a separate Runtime lifecycle request.

修复后 Blocker 0、Major 0、Minor 0。v12.9.1 取代 v12.9.0 中错误的全通过结论；源码可提交合并，但本次不部署，安装与 Runtime 生命周期切换留给单独请求。
