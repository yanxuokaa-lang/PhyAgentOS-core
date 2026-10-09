# Implementation Review v13.0.5 / 七维代码审查

Scope: cross-segment Query evidence repair in `8b1e97c`, with the diagnostic
correction in `c14f2a5`. The parallel Decisions routing documentation is outside
this review. Validation uses real Coordinator persistence with fake Gateway
seams; no live task, provider, Action, simulator step, or installation is used.

## Major: compiler reachability disagreed with revision authorization / 编译与授权不一致

Locations after repair: `PhyAgentOS/agent/plan_proposal.py` L167-L169,
L328-L352, L359-L450; `PhyAgentOS/agent/tools/forge_task.py` L400-L422,
L559-L562, L673-L726.

The previous compiler considered all successful current-capture Query records
in the task. Selection exposes only the active revision's explicit discovery
evidence and direct predecessor results. Therefore a continuation could omit
`tool:grasp` or `tool:capabilities`, pass compilation, persist a new revision,
and fail selection with an unauthorized source. A completed producer exists,
but its existence does not authorize it for the submitted segment.

中文：旧编译器按全任务成功且当前观测的 Query 判断可达，selection 只暴露新段授权
的 discovery evidence 与直接前驱。续接遗漏抓取或能力来源时，计划仍能落盘，随后
选择才拒绝；这会再次消耗 AgentLoop 轮次并阻断收敛。

Reproduction before repair: the two omitted-source cases failed with
`DID NOT RAISE ValueError`; the inherited-authorization control passed. Both
failures occur before any Gateway call is possible in the fixture.

Repair: source reachability intersects successful Query records with the exact
authorization set that the entry point will persist. Continuation uses the
deduplicated union of inherited discovery refs and selected new refs. Recovery
uses replacement refs, or inherited refs when omitted. Complete PlanGraph
materialization receives its submitted refs explicitly. Default compiler and
canonicalizer calls use the active revision's discovery refs. Predecessor-only
slots still require graph-local dependencies; `authorized` retains both paths.

中文：复用已有集合和 source_scope，统一续接、恢复及完整图入口的检查。拒绝发生在
保存 revision 或领取 replan attempt 之前；不自动补引证据、不重复 Query、不重试
Action。没有新增 hash、schema、冻结 contract、baseline 或 gate。

### Recovery and complete-graph entry points / 恢复与完整图入口

The same defect was present in recovery semantic nodes and full graph
canonicalization: evidence was supplied only after compilation. These are
three manifestations of one Major finding, rather than independent defects.
Regressions verify rejected submissions leave the entire task record unchanged
and do not consume an attempt. Positive tests verify both replacement and
inherited evidence remain selectable after recovery.

## Investigated hypothesis: old capture pair / 已排除的旧观测假设

A second test supplies matching old grasp/capability records along with current
records in the same scene, using internally consistent observation and
candidate-set references. Continuation is accepted using current sources, but
selecting the old pair is rejected by the existing observation binding check.
No selection or Gateway call is saved. No additional production check is
needed. This test documents the boundary instead of adding speculative defense.

中文：两条旧来源互相一致也不能替换当前 Coordinator 观测绑定。已有规则已拒绝该
选择，本轮只补回归，不增加生产分支。

## Seven dimensions / 七个维度

| Dimension | Evidence and result |
| --- | --- |
| Architecture / 架构 | Generic Core compiler checks the same pool as Coordinator revision persistence. ToolSpec owns source scope; Runtime/Gateway keep execution ownership. |
| Correctness / 正确性 | Omitted candidate or capability refs fail before persistence; inherited/default evidence and graph-local predecessor routes remain valid. Recovery and full-graph paths share the repair. |
| Recovery and idempotency / 恢复与幂等 | Rejected submissions preserve the task record and attempt budget. Restarted Coordinator can select persisted sources; continuation retains `counts_toward_replan_budget=false`. |
| Robotics safety / 机器人安全 | Successful Query records alone can satisfy evidence sources. Strict Action predecessor contracts, motion authorization, unknown-outcome reconciliation, IK/collision checks, and stop paths remain intact. |
| Extensibility / 扩展性 | Uses existing `predecessor/evidence/authorized` semantics for any bound ToolSpec. No color, RGB, task ID, arm, camera, provider, or destination-specific production branch. |
| Observability and maintainability / 可观测性与维护性 | `projection_source_unreachable` names node/Tool/slot and points to submitted dependencies or discovery refs. Shared compiler logic avoids parallel source-authorization mechanisms. |
| AgentLoop autonomy and convergence / 自主与收敛 | Invalid source selections are corrected before an unusable revision can become active. Valid persisted facts advance without repeated Queries or new physical actions. |

No unresolved Blocker or Major remains in this reviewed change. Structural
reachability proves a source is authorized and available; entity joins,
frame/calibration, exact record selection and provider feasibility remain the
responsibility of their existing selection/Runtime boundaries.

## Validation / 验证

```bash
export PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p pytest_asyncio.plugin -q \
  tests/test_planning_source_assembly.py tests/test_planning_selection.py \
  tests/test_planning_task_integration.py tests/test_planning_loop.py \
  tests/test_agent_foundation.py \
  examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py \
  examples/forge-skills/pick-place-workflow/tests/test_prepare_assignment.py \
  examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_planning_continuation_sources.py \
  examples/forge-adapters/robotwin20/tests/test_agent_continuation_projection.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p pytest_asyncio.plugin -q \
  examples/forge-skills/pick-place-workflow/tests
.venv/bin/ruff check PhyAgentOS/agent/plan_proposal.py \
  PhyAgentOS/agent/tools/forge_task.py \
  examples/forge-skills/pick-place-workflow/tests/test_planning_continuation_sources.py
.venv/bin/python -m compileall -q PhyAgentOS/agent/plan_proposal.py \
  PhyAgentOS/agent/tools/forge_task.py \
  examples/forge-skills/pick-place-workflow/tests/test_planning_continuation_sources.py
git diff --check
```

Results: focused Core/AgentLoop/Skill/Adapter suite **405 passed in 15.62s**;
full Skill suite **415 passed in 14.27s**. Suites overlap, so do not sum them.
There are 11 additional cases, bringing this boundary file from 15 to 26 cases.
Ruff, compileall and diff checks pass. The environment's unrelated ROS plugin
requires missing `lark`; third-party autoload stays disabled, with pytest_asyncio
loaded explicitly.

Only Core implementation changed; Skill 3.0.12, Node 1.0.3 and Adapter 0.9.14
contracts/packages remain at the previous repair's versions. The old canceled
task is not resumed. No live deployment or physical success is claimed.

Related saved diagnosis: [cross-segment Query source diagnosis](../diagnostics/CROSS_SEGMENT_QUERY_SOURCE_DIAGNOSIS_20261009.md).
