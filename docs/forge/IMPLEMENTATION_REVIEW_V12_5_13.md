# v12.5.13 Seven-Dimension Code Review / 七维实现审核

## Findings and disposition / 问题与处理

The three findings reproduced after v12.5.12 are fixed in the changed surfaces.
No unresolved Blocker or Major was found within this repair scope. The full
suite is **not green**: two unchanged failures reproduce at parent `b83cb88`.
These results establish local control-plane behavior, not physical acceptance.
v12.5.12 的三处复现问题已修复；本次范围内无遗留 Blocker/Major，但全量测试
仍有两项父版本既有失败，不能据此报告整套系统或机器人验收通过。

| Original finding | Fix and evidence | Disposition |
| --- | --- | --- |
| Major: a selection persisted during a model turn required another model request, and recovery could exhaust its turn budget | `planning_loop.py:717,730,775` uses the same recovery path before each turn and after model return; tests cover success, provider timeout/error and turn failure with zero/one continuation budget | Fixed |
| Major: wrapper error text outranked durable terminal/accepted records | `planning_loop.py:804` reconciles original execution records before inspecting wrapper text; real ToolRegistry tests cover success, failure, unknown, accepted Action/Session, and executor re-entry | Fixed |
| Major: standalone grasp execution aliases could not join observed geometry | `plan_proposal.py:508` reuses the current unique scene.bind correspondence; tests execute the actual geometry projection and reject ambiguous/stale mappings | Fixed |

## 1. Architecture / 架构

Pass within scope. Recovery stays in `AgentLoopNodeExecutor`; the existing
Coordinator owns selection and execution records, and the existing Registry
and Gateway retain admission and invocation execution. Alias completion stays
in the shared plan-proposal binding seam. No duplicate scheduler, state store,
hash, contract, or gate is introduced.
通过：恢复与实体规范化分别留在既有执行器和计划编译边界，不迁移物理真值所有权。

## 2. Correctness / 正确性

Pass within scope. Recovery runs immediately after the model returns, including
the last allowed turn. Only durable task/node/revision records produce results;
successful-looking wrapper text with no record remains incomplete. Standalone
grasp aliases resolve only when the current correspondence has one observed
identity; input nodes are not mutated. Complete-graph canonicalization tests
cover grasp, prepare, acquire and place.
通过：最后一轮模型返回仍可恢复；无执行记录不报成功，唯一实体映射可接入真实几何投影。

The identity repair applies to post-discovery materialization/revision
compilation. Initial task creation without task-owned discovery evidence
cannot resolve a Runtime alias; this entry point is unchanged and is not
claimed as covered by this patch.
边界：只保证拥有本任务发现证据后的物化/修订编译；初始创建尚无证据时不解析 Runtime 别名。

## 3. Recovery and Idempotency / 恢复与幂等

Pass within scope. Existing records precede pending selection. Terminal records
do not invoke the wrapper again, even if the pending-selection fixture remains
visible. Accepted Action/Session recovery reads status/result of the original
invocation; it does not repeat the POST. Unknown stays unknown. Recovery does
not spend another model-turn allowance. Timeout without any selection/record
keeps the existing bounded model retry behavior.
通过：执行记录优先；受理后只对账原 invocation；unknown 不转为成功或替代动作。

## 4. Robotics Safety / 机器人安全

Pass for control-plane changes. Pending selections still execute through
`ToolRegistry.execute` and its execution guard. A guard rejection creates no
execution and is not retried by this recovery path. Missing Registry explicitly
blocks rather than delegating governed execution to another model turn. No
freshness, calibration, workspace, collision, IK, authorization, or terminal
settlement rule was changed. Tests use local fakes and perform no robot motion.
通过：现有执行 guard 仍生效；拒绝或缺失 Registry 时明确停止，未放宽机器人门禁。

## 5. Extension Compatibility / 扩展兼容

Pass within scope. Identity mapping uses provider-neutral scene.bind fields;
arbitrary entity names are tested. Recovery is based on record/Tool semantics,
not RGB colors, benchmark profiles, or provider names. Extensions that supply a
pending selection must supply the existing governed Registry; previously
implicit model fallback is now an explicit incomplete-node error.
通过：无 RGB 专用分支；扩展若提供 pending selection，必须提供既有受治理 Registry。

## 6. Observability and Maintainability / 可观测性与可维护性

Pass within scope. One `_resume_node` helper replaces duplicated recovery paths.
Existing structured result/failure reporting remains authoritative. Missing
Registry, wrapper rejection without a record, and nonterminal execution have
explicit diagnostics. The saved diagnosis and this review distinguish local
test evidence from installed Runtime behavior. Historical reviews remain intact;
this document supersedes their all-pass claims for these three surfaces.
通过：单一恢复入口、明确错误诊断，保留历史 Review 并纠正本次相关结论。

## 7. AgentLoop Autonomy / AgentLoop 自主性

Pass within scope. Consuming a persisted selection completes an already-made
decision. It does not choose a new target, segment or replan. After settlement,
the existing Agent continuation still chooses continue/replan/finalize/stop or
clarification. The repair adds no automatic observe, post-placement refresh,
staging, or destination generation. Query success cannot prove acquisition or
placement; world-change routing remains grounded in execution facts.
通过：恢复既定选择与规划下一步分离；未加入自动观察、放置后链路或目标位置规划。

## Validation / 验证

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q tests/test_planning_loop.py tests/test_plan_proposal_bindings.py -k 'node_executor or pending_selection or standalone_grasp or complete_graph_entry'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q tests
/home/yanxu/miniconda3/envs/paos/bin/python -m ruff check PhyAgentOS/agent/planning_loop.py PhyAgentOS/agent/plan_proposal.py tests/test_planning_loop.py tests/test_plan_proposal_bindings.py
/home/yanxu/miniconda3/envs/paos/bin/python -m compileall -q PhyAgentOS/agent/planning_loop.py PhyAgentOS/agent/plan_proposal.py tests/test_planning_loop.py tests/test_plan_proposal_bindings.py
git diff --check
```

- Focused acceptance: **35 passed, 58 deselected**.
- Full core suite: **748 passed, 2 failed in 26.94s**.
- The same two failures at unchanged parent `b83cb88`: **2 failed in 2.04s**, using an isolated detached worktree and the same interpreter/plugin.
- `test_query_error_survives_live_and_persisted_settlement_and_recovery_prompt`: the SimpleNamespace fixture omits `invocation_id`; `_tool_result_from_execution` accesses that production field.
- `test_rgb_attribute_sorting_loop_replans_after_drop_and_reducer_replays`: revision-1 replay expects `('verify',)` but yields `('arrange-green',)`.
- Ruff, compileall and diff whitespace checks passed. No AgentTask, live Gateway execution, Runtime restart, installation, benchmark run, grasp or placement was performed.
- 聚焦 35 项通过；全量 748 项通过、2 项失败且父版本已复现。静态检查通过；本次未做安装或物理验收。
