# Preparation Capability Lineage Diagnosis / Preparation 能力血缘诊断

## Scope / 范围

This diagnosis compares the recent persisted AgentTask records and preparation timing artifacts. It does not infer motion from transport success and does not replay a Query or Action.

本诊断对比近期持久化 AgentTask 与 preparation timing artifacts，不从 transport success 推断运动结果，也不重放 Query 或 Action。

## Observed Event Chains / 已观察事件链

- `task_13315d0d962a45f5`: `grasp.propose` succeeded and `manipulation.prepare` returned business status `unavailable`. The private timing record reports `ValueError: materialized artifact conflicts with runtime evidence`. This was the immutable artifact identity problem addressed by v12.9.8.
- `task_b2f30f6918d14eb6`: `grasp.propose` again succeeded and `manipulation.prepare` returned `unavailable`, but its timing record reports `ArmPlanningError: route option arm profile binding is invalid`. All 32 proposals were materialized; contact qualification accepted candidates 14 and 25 through 31. The failure occurred before route readiness evaluated an option.
- Earlier tasks `task_e90cab6880fa4f86`, `task_e3949a368fad4e3d`, and `task_802c0dc7a58b4434` completed preparation and stopped later at `object.acquire`. They are not instances of the current preparation failure.
- Both recent preparation failures remained no-motion: `action_count=0`, `simulator_steps=0`, and `motion_authorized=false`.

## Root Cause / 根因

The deployment binds the parent `PersistentRouteBuilder.arm_profile` to qualification-owned per-arm capability references. Contact qualification then rematerializes every qualified candidate through a child `PersistentRouteBuilder`. The child was constructed without those bindings, so it reloaded the deployment file's legacy capability references.

部署将父级 `PersistentRouteBuilder.arm_profile` 绑定到 qualification-owned 的逐臂 capability refs。Contact qualification 随后通过子 `PersistentRouteBuilder` 重新物化每个合格候选，但子 builder 未继承这些绑定，因此重新加载 deployment 文件中的 legacy refs。

The child-generated `option.arm_profiles` therefore differed from the parent `CompleteRouteSelector.profile`. The selector correctly failed closed at its contract comparison with `route option arm profile binding is invalid`. This is a provider composition lineage defect, not a grasp-ranking, color, object-order, target, camera, collision-world, or Agent selection defect.

因此，子级生成的 `option.arm_profiles` 与父级 `CompleteRouteSelector.profile` 不一致。Selector 在 contract 比较处以 `route option arm profile binding is invalid` 正确失败关闭。这是 provider composition 的血缘缺陷，不是抓取排序、颜色、对象顺序、目标、相机、碰撞世界或 Agent 选择缺陷。

## Why The Outer Error Was Misleading / 外层错误为何误导

`PersistentPreparationProvider` recorded the concrete exception in its private timing artifact, but did not translate the exact arm-profile binding mismatch into `PreparationProviderError`. `ManipulationPreparationEndpoint` consequently used its final unexpected-exception branch and returned generic `preparation_provider_error`. The AgentLoop received valid fail-closed facts but lost the concrete error code and could only stop with `fix_runtime_contract`.

`PersistentPreparationProvider` 在私有 timing artifact 中记录了具体异常，但未将这一精确的 arm-profile binding mismatch 转换为 `PreparationProviderError`。因此 `ManipulationPreparationEndpoint` 进入最终 unexpected-exception 分支，只返回通用 `preparation_provider_error`。AgentLoop 虽然保持失败关闭，却丢失具体错误码，只能以 `fix_runtime_contract` 停止。

## PAOS-Aligned Resolution / 符合 PAOS 的解决方案

1. The route-builder owner carries the same per-arm capability reference mapping into every child rematerialization. Producer and consumer profiles therefore share one deployment-owned lineage.
2. The Adapter translates only `ArmProfileBindingError` into `arm_planning_contract_invalid` with `failure_owner=runtime_adapter`, `retryable_in_revision=false`, `requires_replan=false`, and `recommended_action=fix_runtime_contract`. Other arm-planning failures retain their existing ownership and recovery semantics.
3. Core continues to project those structured fields unchanged. AgentLoop stops deterministically for this runtime contract failure. It does not parse prose, automatically observe, switch a candidate or arm, retry, replan, or dispatch an Action.
4. Planning-owned exhaustion remains separate: declared provider results such as `no_admissible_route` or `no_qualified_contacts` retain `failure_owner=planning` and `requires_replan=true`, leaving the next plan to the Agent and Coordinator.

## Genericity and Safety / 通用性与安全性

The resolution is keyed only by provider contracts, arm capability references, and structured recovery fields. It contains no RGB, color, ordering, benchmark ID, entity ID, candidate index, camera name, or fixed-arm branch. Collision, IK, workspace, calibration, qualification, Action admission, stop, and reconciliation checks remain unchanged.

该修复仅依据 provider contract、逐臂 capability refs 与结构化恢复字段，不包含 RGB、颜色、顺序、benchmark ID、entity ID、候选索引、相机名或固定机械臂分支。碰撞、IK、workspace、calibration、qualification、Action admission、stop 与 reconciliation 检查均保持不变。
