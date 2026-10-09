# Implementation Review v12.10.13 / 七维验收

## Findings and disposition / 发现与修复

- **Major fixed — missing held identity**: successful acquisition effects exposed
  only changed/unchanged entities. Added a separate Runtime-owned held receipt,
  matched against settled possession, and Coordinator-owned held projection.
- **Major fixed — observation-local ID collision**: the provider reused a task
  entity ID for a robot. Preserve the visual claim under a remapped observation
  ID; keep its metric geometry, relations, and ambiguities on that ID.
- **Major fixed — wrong geometric invariant**: unchanged pose equality rejected
  legitimate held motion. Held binding now checks current possession and
  transports the prior visual model by the actor's rigid displacement; unchanged
  pose stability is still required.
- **Major fixed — selection/execution mismatch**: injecting carry-forward only
  at invocation changed arguments after binding. Inject before selection
  persistence, compare at execution, and verify through real Coordinator SQLite
  persistence and execution validation.
- **Major fixed — stale success resurrection**: searching past a later unknown
  Action could reuse older carry evidence. The latest Action must have a known
  successful business result and a matching scene effect.
- **Minor fixed — stale release fixture**: the Skill suite asserted version
  3.0.9 although current manifest/package are 3.0.10. Updated the fixture.

已修复持有身份缺失、视觉 ID 冲突、错误位姿不变量、选参后改参、跨未知动作复用旧证据，
以及既有版本测试夹具过期。没有通过关闭安全检查或重试动作来消除错误。

## Seven dimensions / 七个维度

| Dimension / 维度 | Acceptance / 验收证据 |
| --- | --- |
| Architecture / 架构 | Runtime owns possession; Coordinator projects task evidence; visual provider receives observations only; Adapter owns execution correspondence. |
| Correctness / 正确性 | Held works when unchanged is empty; local ID collisions preserve all visual references; translation/rotation preserve visual geometry and offsets. |
| Recovery and idempotency / 恢复与幂等 | Latest unknown Action blocks old evidence; cached bind rechecks possession; selection retains exact arguments; no Action retry. |
| Robotics safety / 机器人安全 | Missing or inconsistent possession rejects binding; unchanged pose drift still rejects; no new motion authorization or collision exemption. |
| Extensibility / 扩展兼容 | Optional held fields extend the provider-neutral contract; old unchanged inputs remain valid; no RGB/task/arm/count branches. |
| Observability and maintainability / 可观测与维护 | Saved authoritative snapshot and video paths; explicit held/remap reconciliation and held-projection rejection stage. |
| AgentLoop autonomy and convergence / 自主与收敛 | No automatic observe/bind/replan/Action; Agent chooses from complete evidence; existing no-progress and unknown reconciliation remain. |

## Reproducible validation / 可复现验证

Run from the repository root with:

```bash
export PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src
.venv/bin/python -m pytest -q tests/test_forge_tool_api.py tests/test_planning_selection.py tests/test_planning_source_assembly.py tests/test_planning_task_integration.py tests/test_planning_loop.py tests/test_agent_foundation.py examples/forge-adapters/robotwin20/tests/test_grounding.py examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py examples/forge-adapters/robotwin20/tests/test_persistent_agent_loop.py examples/forge-adapters/robotwin20/tests/test_persistent_route_builder.py
.venv/bin/python -m pytest -q examples/forge-adapters/robotwin20/tests/test_scene_understand_provider.py
.venv/bin/python -m pytest -q examples/forge-skills/pick-place-workflow/tests
git diff --check
```

The provider import-boundary suite must run in its own process: its existing
assertion checks the entire `sys.modules`, so collecting Core Agent tests in the
same process introduces their legitimate OpenAI SDK imports. The isolated
provider suite passed; no import-boundary production rule was weakened.

所有回归为 no-motion：测试仅使用临时任务库、fake worker/provider 和合成矩阵。
没有操作现场任务、调用 live Gateway Query/Action、推进 simulator、安装或重启 Runtime。

## Limits / 边界

Final results / 最终结果: Core/AgentLoop and Adapter focused `434 passed in
11.30s`; full Skill suite `387 passed in 9.33s`; isolated provider boundary
`12 passed in 0.33s`. Total: 833 passed. Ruff, compileall, and diff checks passed.
No outstanding Blocker or Major finding remains within the reviewed scope.

The original receipt lacks held evidence and remains unchanged. The fix does
not reconstruct current possession from old success status or from video
existence. Source tests cannot establish current-world holding or complete
task success; live acceptance requires the rebuilt deployment and a separately
authorized run. See the diagnosis and snapshot for exact original facts.
