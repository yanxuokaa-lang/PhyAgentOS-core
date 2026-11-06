# AgentLoop Continuation and Recovery Diagnosis / AgentLoop 续段与恢复诊断

Date: 2026-11-06 (Asia/Shanghai)

## Conclusion / 结论

The prior v17.2.0 follow-up incorrectly stated that Coordinator/AgentLoop lacked
same-parent continuation. That lifecycle already exists: `LongHorizonTaskController`
calls the AgentLoop continuation turn after a fully settled segment, and
`AgentTaskCoordinator.begin_continuation_revision` appends a non-recovery
revision under the same `task_id`. The actual gap was evidence freshness at that
append boundary, not a missing scheduler or lifecycle entry point.

此前 v17.2.0 的后续记录误称 Coordinator/AgentLoop 缺少同父任务续段。该生命周期已存在：
`LongHorizonTaskController` 在一个 segment 全部结算后调用 AgentLoop continuation turn，
`AgentTaskCoordinator.begin_continuation_revision` 随后在同一 `task_id` 下追加不消耗失败重规划额度的 revision。真实缺口在续段追加处的 evidence freshness，而不是缺少 scheduler 或生命周期入口。

## Existing Lifecycle / 已有生命周期

- Successful continuation: `PlanningLoopAdapter` returns `segment_completed`; the outer
  controller invokes `AgentLoop.run_segment_continuation_turn`; the Agent chooses a next
  segment, finalization, replan, cancellation, or clarification through the bounded task
  Tool surface. Coordinator verifies settlement and terminal Action/Session state before
  appending a revision. Continuation keeps the parent task and does not spend replan budget.
- Known failure recovery: a Provider/Adapter may report a safe recovery outcome only when
  its own evidence proves the configured recovery postconditions. AgentLoop then permits a
  fresh-query replan on the new scene. Robot pose, contact, support, and return trajectory
  remain Adapter-owned.
- Unknown physical outcome: stays reconciliation-blocked. Generic AgentLoop must not
  command an unconditional return-home, retry, or continuation.

- 成功续段：`PlanningLoopAdapter` 返回 `segment_completed`；外层 controller 调用
  `AgentLoop.run_segment_continuation_turn`；Agent 通过受限 task Tool surface 选择下一段、
  finalize、replan、取消或澄清。Coordinator 在追加 revision 前校验 settlement 和
  Action/Session 终态。续段保持父 task 不变，也不消耗失败重规划额度。
- 已知失败恢复：Provider/Adapter 只能在自身证据证明配置恢复后置条件成立时报告安全恢复；
  随后 AgentLoop 才允许基于新 scene 的 fresh-query replan。机器人位姿、接触、支撑和回位轨迹由 Adapter 持有。
- 未知物理结果：保持 reconciliation 阻断。通用 AgentLoop 不得无条件回起点、重试或继续。

## Concrete Failure / 具体失败场景

After a successful world-changing Action and a fresh observation, the completed
revision could still contain old-scene Query references in
`discovery_evidence_refs`. `context_from_task` exposes the active revision's
explicitly selected refs, and `ForgeTaskContinuePlanTool` previously compiled
the next graph with the union of those refs and current evidence. A next node
could therefore require a known old-scene Query ref and have its revision
persisted. Later `NodeContextProvider` would reject the stale source, leaving a
valid-looking active revision that cannot execute. The existing pre-submit
stale check applied only when a node itself was a scene-refresh Query, not when a
downstream consumer required stale Query evidence.

World-changing Action 成功并完成 fresh observation 后，已结算 revision 的
`discovery_evidence_refs` 仍可能包含旧 scene Query 引用。`context_from_task` 会暴露 active
revision 显式选择的引用，旧版 `ForgeTaskContinuePlanTool` 又用这些引用与当前 evidence 的并集编译新图。
因此新节点可能要求一个已知属于旧 scene 的 Query ref，并使 revision 先被持久化；之后
`NodeContextProvider` 才拒绝 stale source，留下不能执行的 active revision。原提交前检查只处理
节点本身是 scene-refresh Query 的情况，没有覆盖下游 consumer 对旧 Query evidence 的依赖。

Failure consequence: stale semantic work is accepted as a new revision, then rejected
at node execution; recovery may consume replan budget or require operator intervention.
This is why normal successful-path tests and the existing unknown-outcome stop tests
did not expose the append-boundary gap.

失败后果：旧 scene 语义工作先被接受为新 revision，随后在节点执行前被拒绝；恢复可能消耗重规划额度或要求人工介入。
因此，只覆盖正常续段和 unknown-stop 的现有测试无法发现 append 边界缺口。

## Ownership and Design / 所有权与设计

- Generic domain / Coordinator: owns task/revision lifecycle, current scene identity
  projected from persisted Tool facts, and filtering/rejection of known stale Query refs
  during atomic revision append.
- AgentLoop / planning: chooses the semantic next segment and uses current trusted
  context; it does not select physical recovery poses or execute the segment itself.
- Provider / Adapter: owns scene capture, physical recovery, motion details and evidence
  that proves safe return. No Provider-specific field is added to the shared planning
  contract.
- Evidence lineage: explicitly known older-scene Query refs are excluded; a plan node
  that requires one is rejected before append. Historical Action evidence remains
  available as history, and evidence with no scene identity is not falsely labeled stale;
  it remains subject to existing source and execution validation.
- Lifecycle: Coordinator remains the only revision owner. No parallel scheduler, retry
  loop, new gate, hash, or motion authorization is introduced.

- 通用域 / Coordinator：拥有 task/revision 生命周期、从持久化 Tool facts 投影当前 scene 身份，
  并在原子追加 revision 时过滤或拒绝已知 stale Query refs。
- AgentLoop / planning：选择语义上的下一段并使用当前可信 context，不选择物理恢复位姿，也不自行执行 segment。
- Provider / Adapter：拥有 scene capture、物理恢复、运动细节和安全回位证明；共享规划合同不增加 Provider 专用字段。
- Evidence lineage：明确属于旧 scene 的 Query refs 不会进入新段；节点要求它时在 append 前拒绝。
  历史 Action evidence 作为历史事实保留；缺少 scene identity 的 evidence 不被臆断为 stale，仍受现有来源和执行校验约束。
- 生命周期：Coordinator 仍是唯一 revision owner。不增加平行 scheduler、重试循环、新 gate、hash 或运动授权。

## Validation / 验证

- `examples/forge-skills/pick-place-workflow/tests/test_planning_continuation_sources.py`:
  stale Query evidence rejection before revision append; old Query filtering while retaining
  historical Action evidence and scene-unknown Query references; same-scene inherited source
  compatibility (`28 passed`). No Gateway execution or motion.
- `tests/test_long_horizon_controller.py` and `tests/test_recovery_decisions.py`:
  successful continuation, bounded known-failure recovery decisions and unknown-outcome
  blocking (`34 passed`). Combined with the continuation-source file: `62 passed`.
- `tests/test_planning_task_integration.py`: `72 passed, 1 failed` in the combined run. The
  remaining failure is the separate `resolve_subtask_context` fixture, whose `SimpleNamespace`
  lacks `planning_selections`; it fails before the changed continuation methods.
- Ruff, `compileall` for the changed Python modules, and `git diff --check` pass.
- Contract evidence is test-only. No live Isaac/RoboTwin Provider recovery, simulator
  execution, or physical motion is claimed by this change.

- `examples/forge-skills/pick-place-workflow/tests/test_planning_continuation_sources.py`：
  覆盖 revision append 前拒绝 stale Query evidence、过滤旧 Query 同时保留历史 Action evidence 与
  scene-unknown Query refs，以及 same-scene inherited source 兼容性（28 passed）；不执行 Gateway 或运动。
- `tests/test_long_horizon_controller.py` 与 `tests/test_recovery_decisions.py`：成功续段、受限已知失败恢复决策和 unknown 结果阻断 34 passed；与续段来源测试合计 62 passed。
- `tests/test_planning_task_integration.py` 合并运行 72 passed、1 failed。唯一失败是独立的 `resolve_subtask_context` fixture 缺少 `planning_selections`，发生在本次改动的续段方法之前。
- 修改模块 Ruff、`compileall` 和 `git diff --check` 通过。
- 本变更提供的是 contract/test evidence，不宣称完成 live Isaac/RoboTwin Provider 恢复、仿真执行或真实运动验证。
