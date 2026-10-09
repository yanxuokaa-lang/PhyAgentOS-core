# Implementation Review v13.0.9 / 七维实现复审

## Findings / 问题

### Major: a non-refreshing Query could pass unknown-world recovery / Major：不刷新场景的 Query 也能通过恢复门禁

`_validate_unknown_recovery_graph()` required a new Query ancestor, but Query
semantics also cover reads such as capabilities and task goals. Such a node
does not establish the current scene after an Action with unknown physical
effects. Runtime admission remains authoritative, but the AgentLoop contract
did not itself require refreshed scene evidence and could advance stale context
to a later gate.

**Fixed:** classify recovery queries through bound `ToolSpecPolicy` metadata;
only `semantics="query"` with `refreshes_scene=true` counts. Each new Action
must have such a new Query in its dependency ancestry. Conflicting metadata for
one capability fails closed. This uses existing metadata and adds no task,
tool-name, object, camera, or benchmark branch.

### Minor: no-motion result diagnosis could mask reported motion / Minor：no-motion 错误诊断会被次级字段掩盖

Acquire/place validated the complete provider result before checking
`world_change_started`. A no-motion provider that reported motion but omitted
another success field returned the secondary schema error instead of the
safety-specific motion rejection. Both endpoints now check the explicit
`true` motion fact immediately after snapshot type validation. The no-motion
placement fixture also claimed success without the required release evidence;
it now returns a contract-valid known failure instead of fabricating physical
postconditions.

## Seven Dimensions / 七个维度

1. **Architecture:** the rule remains in the generic PlanningLoop and derives
   recovery semantics from Coordinator-owned bound ToolSpecs.
2. **Correctness:** a Query is sufficient only when its ToolSpec declares
   `refreshes_scene=true`; absent or contradictory metadata cannot satisfy the
   recovery gate.
3. **Recovery and idempotency:** the original invocation remains immutable;
   the existing append-only revision and replan budget are unchanged.
4. **Robotics safety:** each new physical Action depends on a newly introduced
   scene-refresh Query. No-motion acquire/place endpoints prioritize an
   explicit motion report. Runtime/Gateway admission still decides whether a
   later Action is allowed.
5. **Extensibility and compatibility:** the rule is capability/ToolSpec
   metadata-driven. Existing ToolSpecs default `refreshes_scene` to false;
   recovery fails closed until a genuine scene-refresh Tool declares it.
6. **Observability and maintainability:** failure messages distinguish absent
   scene-refresh Query from an Action not gated by one; no-motion errors retain
   their cause-specific code. Regression tests cover absent, unrelated, valid,
   and ambiguous metadata and both Action endpoints.
7. **AgentLoop autonomy and convergence:** a valid Runtime replan can proceed
   through fresh scene evidence; malformed recovery plans stop before a new
   revision starts, while Coordinator still owns revision and retry budgets.

## Validation / 验证

The new no-motion cases cover: a refreshing Query gating an Action, a
non-refreshing Query being rejected, a refreshing Query unrelated to an Action
being rejected, and conflicting `refreshes_scene` metadata being rejected.
The reproducible focused Runtime/AgentLoop/Skill/Adapter command is:

```bash
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p pytest_asyncio.plugin \
  examples/forge-skills/pick-place-workflow/tests/test_unknown_action_recovery.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_host.py \
  examples/forge-adapters/robotwin20/tests/test_grounding.py \
  examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_object_acquire.py \
  examples/forge-skills/pick-place-workflow/tests/test_object_place.py \
  examples/forge-adapters/robotwin20/tests/test_action_readiness_gate.py -q
```

Result: `195 passed in 2.16s`. Ruff, compileall, and `git diff --check` pass.
This includes the two Adapter readiness tests that failed before the review
fixes. No live Runtime, Gateway, simulator, or physical Action was invoked.
