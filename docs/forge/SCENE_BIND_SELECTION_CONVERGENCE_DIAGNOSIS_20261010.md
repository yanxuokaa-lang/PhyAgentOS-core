# Scene Bind Selection Convergence Diagnosis / scene.bind 选择收敛诊断

## Scope / 范围

This review covers the generic planning-node selection boundary exposed by
`task_623ba3f50a5c4f31` and the earlier post-action bind failure. It does not
encode RGB, colors, ordering, camera names, object counts, or a provider.

本审查覆盖 `task_623ba3f50a5c4f31` 暴露的通用 planning-node selection 边界，
以及此前动作后绑定失败的差异。修复不编码 RGB、颜色、排列、相机名称、对象数量或
Provider。

## Evidence / 证据

The latest task had completed `red_checkpoint_observe` and
`red_checkpoint_understand`. The current understanding contained three
individually identified task objects and separate ambiguity references for
environment surfaces. No `scene.bind` selection, rejection, Gateway Query, or
settlement was created. The Agent spent its bounded turn reading context and
describing a possible inspection, so the Coordinator facts remained unchanged
and the AgentLoop correctly stopped with:

```text
node_turn_incomplete:red_checkpoint_bind:node_selection_no_progress
```

最近任务已经完成 `red_checkpoint_observe` 和 `red_checkpoint_understand`。当前理解记录中
三个任务对象各自有实体身份，歧义引用只涉及环境表面；没有产生 `scene.bind` selection、
rejection、Gateway Query 或 settlement。Agent 在有足够证据时继续读取并描述检查意图，
Coordinator facts 没有变化，因此 AgentLoop 按设计以
`node_turn_incomplete:red_checkpoint_bind:node_selection_no_progress` fail-closed。

The earlier post-acquire failure was different: the held object was absent from
the provider understanding and a partially occluded region was attributed to a
robot entity. That is a perception/held-object projection issue, not a bind
selection convergence issue. The two failures share a stop code but have
different owners and must not be merged into one retry rule.

此前抓取后的失败原因不同：被持有对象没有进入 Provider understanding，被夹爪遮挡区域被
识别成机器人实体。那是持有实体投影问题，不是绑定 selection 收敛问题。两次失败共享
停止代码，但所有权和恢复路径不同，不能合并成同一个重试规则。

## Root Cause / 根因

`scene.bind` validation already rejected missing, aliased, stale, or
ambiguous selected references. The gap was in the node-turn input contract:
the model saw source catalogs and a natural-language constraint, but it did
not receive a compact action-oriented projection of the current understanding's
candidate refs, ambiguity scope, and selection obligation. A valid read-only
selection therefore remained model-inferred and could consume the corrective
turn without producing a Coordinator fact.

`scene.bind` 的校验已经拒绝缺失、别名、过期或歧义引用。缺口在节点 turn 输入契约：模型能
看到 source catalog 和自然语言约束，却没有得到当前理解候选引用、歧义范围和 selection
义务的紧凑行动投影。因此合法的只读 selection 仍完全依赖模型推断，可能耗尽 corrective
turn 而没有产生 Coordinator fact。

An empty `ambiguity.entity_refs` is a global ambiguity scope in the Runtime
contract. Core previously treated it as an empty intersection and could report
no selected conflict. This review aligns prompt projection and Core preflight:
global ambiguity produces no recommended refs and rejects every non-empty
selection before Gateway invocation.

Runtime contract 中 `ambiguity.entity_refs=[]` 表示全局歧义。Core 之前只计算集合交集，
可能把它误判为没有选中冲突。本次审查统一 prompt projection 和 Core preflight：全局歧义
不推荐任何引用，并在 Gateway 调用前拒绝所有非空 selection。

## Generic Fix / 通用修复

- `NodeExecutionContext` exposes `scene_bind_selection` only for a
  `scene.bind` node and only from one successful current authorized
  `scene.understand` record, deduplicating direct-predecessor and selected
  evidence views.
- The projection contains candidate identities, unambiguous recommendations,
  ambiguity references, source record and scene identity. Missing, stale,
  failed, duplicate, or empty understanding evidence is marked unavailable.
- The node prompt tells the Agent to compare the node obligation with the
  candidates, ignore disjoint environment ambiguity, submit one governed
  `forge_plan_select` when the required task identities are present, and choose
  recovery/stop when they are absent or ambiguous. It never auto-selects.
- Core's existing `scene.bind` preflight treats empty ambiguity scope as global;
  Gateway and Runtime binding checks remain unchanged.

- `NodeExecutionContext` 仅在 `scene.bind` 节点暴露 `scene_bind_selection`，且来源必须是一个
  成功、当前、已授权的 `scene.understand` 记录；直接前驱和选定 evidence 视图会去重。
- 投影包含候选身份、无歧义推荐、歧义引用、源记录和场景身份。缺失、过期、失败、重复或
  空理解证据均标记为 unavailable。
- 节点 prompt 要求 Agent 将节点义务与候选交叉核对：无关环境歧义不阻塞，任务身份齐全且
  无歧义时提交一次受治理的 `forge_plan_select`，缺失或歧义时选择恢复/停止；绝不自动选择。
- Core 现有 `scene.bind` preflight 将空歧义范围视为全局；Gateway 和 Runtime 绑定校验未改变。

## Seven-Dimension Review / 七维审查

| Dimension / 维度 | Result / 结论 |
| --- | --- |
| Architecture / 架构 | PASS. Projection belongs to the generic planning-loop context; Coordinator still owns selection persistence and ToolSpec resolution. / 通过。投影位于通用 planning-loop context，Coordinator 仍拥有 selection 持久化和 ToolSpec 解析。 |
| Correctness / 正确性 | PASS. Only current successful understanding evidence is projected; scene identity and ambiguity are preserved; global ambiguity fails closed. / 通过。只投影当前成功 understanding，保留场景身份和歧义；全局歧义 fail-closed。 |
| Recovery and idempotency / 恢复与幂等 | PASS. No Query or Action is auto-retried, no selection is auto-created, and repeated reads still converge through the existing no-progress limit. / 通过。不自动重试 Query/Action，不自动创建 selection，重复读取仍由现有 no-progress 限制收敛。 |
| Robotics safety / 机器人安全 | PASS. `scene.bind` remains Query-only; no motion authorization, preparation, Gateway Action, or Runtime admission is changed. / 通过。`scene.bind` 仍为只读 Query，未改变运动授权、prepare、Gateway Action 或 Runtime admission。 |
| Extensibility / 扩展性 | PASS. No RGB, color, count, camera, provider, object class, or fixed Tool branch. / 通过。无 RGB、颜色、数量、相机、Provider、对象类别或固定 Tool 分支。 |
| Observability and maintainability / 可观测与可维护 | PASS. Source record, scene revision, ambiguity scope and unavailable reasons are explicit; tests cover positive, stale and absent evidence. / 通过。源记录、场景版本、歧义范围和 unavailable 原因显式可见，测试覆盖成功、过期和缺失证据。 |
| AgentLoop autonomy and convergence / AgentLoop 自主与收敛 | PASS. The Agent still chooses exact refs, but receives an actionable bounded contract instead of prose-only inference. / 通过。Agent 仍选择确切引用，但收到可执行的有界契约，不再只依赖自然语言推断。 |

## Validation Boundary / 验证边界

Validated with fake Coordinator/records only; no Runtime, AgentTask, Gateway
Query/Action, camera, simulator, or physical motion was used.

使用 fake Coordinator/records 验证；未启动 Runtime、未创建 AgentTask、未调用 Gateway
Query/Action、未读取相机、未推进 simulator，也未产生物理运动。

- `tests/test_planning_loop.py`, `tests/test_prompt_context.py`,
  `tests/test_agent_foundation.py`, `tests/test_forge_tool_api.py`,
  `tests/test_planning_dispatch.py`, and `tests/test_planning_selection.py`:
  `377 passed`.
- `tests/test_long_horizon_controller.py`,
  `tests/test_planning_effect_recovery.py`, and
  `examples/forge-skills/pick-place-workflow/tests/test_unknown_action_recovery.py`:
  `54 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- The existing selection test double now implements the Coordinator's
  `effective_planning_execution_records` read contract, so source-resolution
  regressions exercise the intended authorization path instead of failing on
  fixture drift.

- `tests/test_planning_loop.py`、`tests/test_prompt_context.py`、
  `tests/test_agent_foundation.py`、`tests/test_forge_tool_api.py`、
  `tests/test_planning_dispatch.py`、`tests/test_planning_selection.py`：
  `377 passed`。
- `tests/test_long_horizon_controller.py`、`tests/test_planning_effect_recovery.py`、
  `examples/forge-skills/pick-place-workflow/tests/test_unknown_action_recovery.py`：
  `54 passed`。
- Ruff、compileall、`git diff --check`：通过。
- selection 测试替身已实现 Coordinator 的
  `effective_planning_execution_records` 读取契约，source-resolution 回归现可验证授权路径，
  不再因 fixture drift 假失败。
