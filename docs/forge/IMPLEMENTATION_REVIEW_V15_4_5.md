# Implementation Review v15.4.5: Async Semantic Query Binding

Date: 2026-10-21 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Findings and disposition

### Fixed Blocker: synchronous binding could not call the production Gateway client

`ForgeToolClient.invoke_query` is asynchronous, but the semantic plan builder
introduced in v15.4.3 called the synchronous `PerceptionBindingAdapter.bind`.
An async function object would be treated as a Query result and rejected as a
non-object, so the no-motion synchronous fixtures did not prove compatibility
with the Agent's Gateway path. Added `bind_async`,
`bind_subtask_from_semantics_async`, and `AsyncQuerySemanticPlanBuilder`; the
AgentTask tool already awaits an awaitable plan builder before Coordinator
persistence. The existing synchronous binding API remains unchanged.

The async adapter executes observation, understanding, grasp proposal, and
capability queries sequentially, then runs the same binding validation and
measurement projection as the synchronous API. It does not invoke preparation
or Action endpoints.

## Architecture review

- PAOS boundary: Gateway/Query transport remains injected; workflow owns the
  semantic binding composition; Coordinator remains the only task persistence
  authority.
- Extensibility: async transport is a port behavior, not a simulator-specific
  implementation. Sync providers remain supported by the sync API.
- Developer Guide: integration is covered by an awaitable Query fixture,
  including failure before persistence.
- AgentLoop: `ForgeTaskCreateTool.execute` awaits async builders, so no detached
  task or extra model turn is introduced.
- Cancellation/errors: `asyncio.CancelledError` is not swallowed by the
  adapter's `except Exception` handling on supported Python versions; Query
  failures are converted to a stage-specific binding error.
- Anti-OverDefense: no hash or new gate was added.

## Seven-dimension acceptance

1. Perception correctness: **partial**. The asynchronous Query contract is
   exercised with provider fixtures; live camera output is not inspected.
2. Binding and freshness: **passed for no-motion**. Async results go through
   the same observation identity, freshness, semantic uniqueness, candidate,
   frame, calibration and scene revision validation as sync results.
3. Subtask AgentLoop boundary: **passed for no-motion**. The async builder
   returns one `manipulation.execute_subtask` node per requested subtask and
   is awaited inside one `forge_task_create` invocation.
4. IK, workspace, collision: **not verified live**. No robot planner or
   collision runtime was invoked.
5. Real execution state: **not verified**. No Action, simulator step, or
   physical IO was invoked.
6. Pour/stir feedback: **not verified**. No process telemetry was generated.
7. Settlement and recovery: **partial**. Existing single-subtask settlement
   tests remain green; live AgentLoop recovery is not exercised here.

## Validation

- Focused semantic/perception/subtask/runtime/AgentTask/planning-loop suite:
  `247 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No Isaac Sim, Gateway Action, simulator step, robot motion, or hardware IO
  was run. The Query tests are local fixtures, not a live Gateway acceptance.

## Remaining work

The async builder still requires production injection into the runtime that
constructs `AgentLoop`, using the actual `ForgeToolClient` and caller/session
identity. The repository CLI currently does not provide such a builder. After
that wiring, validate a no-motion task creation through a live Query runtime;
then separately authorize Isaac Sim tests for IK/collision, acquire/place,
pour/stir feedback, and task-boundary recovery.
