# Implementation Review v13.0.2 / 七维实现审查

Reviewed scope: generic cross-segment reuse of successful read-only Query facts
for `manipulation.prepare`. No live Runtime, Query, Action, simulator step, or
hardware motion was used by this review.

## Findings and fixes / 发现与修复

### Blocker fixed: graph-local dependency and predecessor-only source formed a dead end

`manipulation.prepare.candidates` required a direct predecessor, but a normal
continuation cannot depend on a node in the completed previous PlanGraph. The
successful current-scene `grasp.propose` record was already Coordinator-owned
and explicitly selected, yet the contract rejected it before materialization.
Repeating the Query would violate AgentLoop convergence rules.

Fix: use the existing `authorized` source scope for this read-only producer /
consumer pair. Do not change graph dependency semantics or copy old nodes into
the new graph.

### Major fixed: a structural-only test would miss the real route contract

Preparation uses the installed Skill's `manipulation_intent_v2` builder and a
typed readiness assignment. A shallow projection unit test would not prove that
the continuation survives selection persistence and the real endpoint contract.

Fix: the regression runs `forge_task_continue_plan` → `forge_plan_select` →
saved `planning_binding` → `forge_tool_query` → real preparation endpoint. It
asserts one provider call, no Action path, the new revision identity in intent,
and preservation of the old execution record.

### Major fixed: broader source syntax needed negative authorization coverage

`authorized` intentionally accepts predecessor or evidence context. Without
negative regressions, a future refactor could accidentally admit old captures,
foreign task references, wrong producer Tools, failed records, mismatched
frame/calibration, or another entity's candidates.

Fix: tests cover all of those cases and verify rejection before selection or
Gateway execution. A separate case preserves strict predecessor-only behavior
for consumers that still require it, including acquire/place.

### Minor fixed: contract/version/documentation drift

Core ToolSpec, published YAML, Skill package/manifest version, version assertion,
selection design, saved diagnosis, and changelog are updated together. Node and
Adapter implementations did not change, so their versions remain unchanged.

### Major fixed: the next segment could split a strict predecessor chain again

Changing a read-only candidate source does not make Action results ordinary
discovery evidence. Acquisition and placement retain predecessor-only sources.
A model choosing one-node segments for those consumers could encounter another
structural dead end after preparation succeeds.

Fix: generic continuation prompt and Tool description explain source-aware
segment boundaries. Consumers that require strict predecessors stay with their
producers in the submitted graph. Authorized successful Queries may cross via
explicit evidence references. Declaring Action nodes cannot execute them;
existing readiness, selection, predecessor terminal checks and Gateway admission
still decide whether each node can run. The Agent retains semantic plan choice.

## Seven dimensions / 七个维度

| Dimension / 维度 | Result / 结果 |
| --- | --- |
| Architecture / 架构 | Consumer ToolSpec owns reuse policy; Coordinator owns persisted authorization and exact projection; PlanGraph stays graph-local; Runtime and Gateway remain execution owners. |
| Correctness / 正确性 | Current-scene task-bound grasp candidates and capability evidence assemble the exact frozen preparation input; entity join and typed assignment pass the real endpoint. |
| Recovery and idempotency / 恢复与幂等 | A completed Query is not repeated; continuation does not consume replan budget; failed/unknown/stale sources remain unavailable; no automatic Action retry. |
| Robotics safety / 机器人安全 | The changed Tool is a no-motion Query; `motion_authorized=false`, readiness checks, Action admission, collision/IK ownership, controller qualification, stop, and reconciliation are unchanged. |
| Extensibility / 扩展性 | No RGB, color, object count, task ID, provider, arm, camera, destination, filesystem, or benchmark runtime branch; any ToolSpec can choose predecessor/evidence/authorized explicitly. |
| Observability and maintainability / 可观测与维护 | Diagnosis records exact task/revisions/records/videos; errors distinguish argument rejection from source reachability and provider/action failures; versions/contracts remain synchronized. |
| AgentLoop autonomy and convergence / AgentLoop 自主与收敛 | Persisted successful Query facts can advance the next segment without duplicate perception; System 2 still chooses semantic nodes, while Coordinator deterministically validates exact sources. |

No outstanding Blocker or Major remains in the reviewed scope.

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
.venv/bin/ruff check PhyAgentOS/forge/capability_runtime/manipulation_prepare.py \
  examples/forge-skills/pick-place-workflow/tests/test_planning_continuation_sources.py \
  examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py
.venv/bin/python -m compileall -q PhyAgentOS/forge/capability_runtime/manipulation_prepare.py \
  examples/forge-skills/pick-place-workflow/tests/test_planning_continuation_sources.py
git diff --check
```

The repository ROS pytest entry point exposes an unrelated `launch_testing`
plugin whose environment lacks `lark`; validation disables third-party plugin
autoload and explicitly loads `pytest_asyncio.plugin`. This does not alter the
project environment or application behavior.

Final results: focused Core/AgentLoop/Skill/Adapter set `394 passed in 14.28s`;
full Skill `404 passed in 12.85s`. These suites overlap, so the counts are not
summed as unique tests. There are 15 new cross-segment boundary cases. Ruff,
compileall, and `git diff --check` passed.

Skill 3.0.12 was packaged and inspected as
`out/releases/v13.0.2/pick-place-workflow-3.0.12.tar.gz` (558302 bytes), with
`candidates.source_scope=authorized` and exactly Node 1.0.3 embedded. Packaging
reuses the existing release lock; no new checksum/gate was added. `/tmp` was
full, so packaging completed in the workspace and the artifact was moved into
the release output directory.

## Deployment boundary / 部署边界

This source change does not mutate the waiting task's frozen Skill binding and
does not install Skill 3.0.12. A later explicitly authorized deployment must
build/install the new Skill and start a new or validly resumed task under that
binding. Do not replay an Action merely to validate this contract repair.
