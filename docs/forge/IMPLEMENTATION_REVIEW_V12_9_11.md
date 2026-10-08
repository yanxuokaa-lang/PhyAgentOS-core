# v12.9.11 Implementation Review / 实现审核

## Scope / 范围

This review covers the generic preparation capability-lineage repair, structured failure propagation, release metadata, and no-motion regressions. It does not treat transport success as physical success and did not start an AgentTask, simulator, Gateway Action, or robot motion.

本审核覆盖通用 preparation capability 血缘修复、结构化失败传播、发布元数据与无运动回归。本审核不将 transport success 视为物理成功，也未启动 AgentTask、模拟器、Gateway Action 或机器人运动。

## Findings / 发现

### Resolved Major / 已修复 Major

The first implementation classified every `ArmPlanningError` as a non-replannable Runtime contract failure. That base class also covers candidate-budget, option-shape, and coordination failures, so the classification could have stopped valid Agent replanning. The implementation now raises and catches the narrow `ArmProfileBindingError` only; a regression proves other `ArmPlanningError` values are not reclassified.

初始实现将所有 `ArmPlanningError` 都分类为不可 replan 的 Runtime contract failure。该基类还包含候选预算、option 形状和协同失败，因此可能错误停止合法的 Agent replan。现在仅精确的 `ArmProfileBindingError` 会被抛出和捕获；回归测试证明其他 `ArmPlanningError` 不会被重分类。

No open Blocker or Major finding remains in the reviewed scope.

审核范围内无未解决的 Blocker 或 Major。

## Seven-Dimension Acceptance / 七维验收

1. **Architecture integration / 架构集成: pass.** Deployment-owned capability refs are preserved by `PersistentRouteBuilder`, contract mismatch is typed by the selector owner, Adapter composition translates it, Core preserves the public result, and AgentLoop consumes recovery facts. No parallel state machine was added.
2. **Correctness / 正确性: pass.** Parent and contact-qualification child builders now materialize route options from the same per-arm capability lineage. The real `CompleteRouteSelector` accepts rebuilt options in regression coverage.
3. **Recovery and idempotency / 恢复与幂等: pass.** The exact contract defect reports `retryable_in_revision=false` and `requires_replan=false`; AgentLoop therefore stops instead of repeatedly selecting, observing, retrying, or replanning. Planning-owned exhaustion remains separately replannable.
4. **Robotics safety / 机器人安全: pass.** The change is confined to no-motion preparation and error classification. Collision, IK, workspace, calibration, controller qualification, Action admission, stop, and reconciliation checks remain intact; all tests keep `motion_authorized=false`.
5. **Extensibility and compatibility / 扩展性与兼容性: pass.** Logic is keyed by arm IDs, deployment capability refs, provider contracts, and recovery fields. It contains no RGB, color, entity, benchmark, candidate-index, camera, or fixed-arm branch. Existing planning errors retain their behavior.
6. **Observability and maintainability / 可观测性与可维护性: pass.** Public results retain `arm_planning_contract_invalid`, owner, retry/replan flags, and recommended action; private timing metrics still record the concrete exception. The narrow subtype documents ownership without string parsing.
7. **AgentLoop autonomy and convergence / AgentLoop 自主性与收敛: pass.** The Loop decides from Coordinator-persisted structured facts. The repair does not choose a candidate, arm, next observation, next plan, or Action for the Agent; it only prevents futile automatic recovery from a Runtime contract defect.

## Verification / 验证

- Focused Adapter route, preparation, and readiness tests: `48 passed`.
- Core AgentLoop, manipulation, and recovery tests: `254 passed`.
- Full Skill suite: `379 passed`.
- Skill release/install subset: `87 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- Full Adapter suite: `821 passed, 18 failed`. The residual failures are pre-existing environment/fixture issues: unavailable `scipy`/`cv2`, a PyYAML monkeypatch fixture incompatibility, and two existing Action-contract fixture mismatches. They do not exercise the changed capability-lineage path.

## Release Boundary / 发布边界

Adapter `0.9.9`, Node `0.10.14`, and Skill `3.0.6` artifacts were built. The Node repeat build produced the same package digest. Nothing was installed, restarted, or executed against a live task in this change.

Adapter `0.9.9`、Node `0.10.14` 和 Skill `3.0.6` artifacts 已构建。Node 重复构建产生相同 package digest。本次变更未安装、未重启，也未对实时任务执行。

## Residual Risk / 剩余风险

The no-motion regression proves the previously failing profile comparison, but only a separately authorized installed-runtime run can show whether a later preparation or Action stage exposes another independent defect. Such a failure must be diagnosed from its own persisted record rather than attributed to candidate selection or this fixed lineage defect.

无运动回归已覆盖之前失败的 profile 比较，但只有单独授权的已安装 Runtime 运行才能证明后续 preparation 或 Action 阶段是否暴露其他独立缺陷。若再次失败，必须依据新的持久化记录诊断，不应归因于候选筛选或本次已修复的血缘缺陷。
