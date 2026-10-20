# Implementation Review v15.1.10: Subtask Intent Wiring Audit

Date: 2026-10-20 (Asia/Shanghai)

## Finding

### Blocker: persisted `manipulation_intent_v2` cannot yet be consumed by the subtask Action

The existing trusted builder is attached to `manipulation.prepare`, while
`manipulation.execute_subtask` and `SubtaskSpec` do not expose an `intent`
input. Therefore changing the Coordinator resolver to require a persisted
intent would reject the real subtask path: the Action record currently carries
the binding/spec payload, not a Coordinator-built intent. That attempted shape
was reverted before acceptance; no broken runtime contract was committed.

The correct next implementation is a coordinated contract change:

1. expose semantic intent on the subtask planning node and ToolSpec;
2. reuse the existing trusted builder to materialize the full intent into the
   persisted subtask Action arguments;
3. make the Coordinator consume and validate that persisted intent;
4. pass the same intent into task-scoped `manipulation.prepare` before
   assignment is created, then execute acquire/process/place inside one outer
   subtask settlement.

Assignment is still produced by `PerceptionBindingAdapter` before subtask
selection, so live execution remains blocked until that ordering is changed.

## Architecture Review

- **PAOS ownership:** The trusted builder must remain in PlanningDispatch;
  Coordinator owns attribution and Runtime owns invocation lifecycle. No
  second intent builder is accepted.
- **Extension principles:** The required change belongs in the provider-neutral
  ToolSpec/subtask contract. It must not add a LabUtopia-specific intent or
  perception class.
- **Developer Guide:** A missing or malformed intent must fail before any
  internal Tool. A compatibility fallback that silently reconstructs identity
  would violate evidence lineage.
- **AgentLoop:** The intent and preparation Query are subtask preconditions;
  they must not become additional Agent-facing nodes or settlements.
- **Robotics safety:** This audit performed no simulator, Gateway, or robot
  action; the existing `motion_authorized=false` boundary remains intact.

## Seven-Dimension Acceptance

1. **Perception correctness:** **partial**. Generic provider-neutral perception
   remains in place; no live camera evidence was collected.
2. **Binding and freshness:** **partial**. Existing observation/candidate
   freshness checks pass, but task-scoped assignment provenance is not closed.
3. **Agent planning granularity:** **pass for existing no-motion subtask
   sequence**. One outer Action still owns the internal receipts; the intent
   contract change is pending.
4. **IK, workspace, and collision:** **partial**. Existing preparation
   readiness remains required; no live planner/collision world was run.
5. **Execution state:** **not verified**. No acquire, possession, release, or
   retreat executed.
6. **Process feedback:** **not verified**. No live pour/stir measurements.
7. **Settlement and recovery:** **partial**. Existing subtask failure/cancel
   aggregation is covered; Coordinator-owned intent-to-assignment propagation
   and live recovery remain open.

## Validation

- Baseline Coordinator/subtask tests with the reverted compatible contract:
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src pytest -p pytest_asyncio.plugin -q tests/test_planning_task_integration.py examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py`
  -> `51 passed` before the audit-only revert; the same baseline contract was
  restored afterward.
- `.venv/bin/ruff check PhyAgentOS/forge/task.py tests/test_planning_task_integration.py`
  and `git diff --check` pass for the current worktree.
- Default pytest plugin autoload remains blocked by the host ROS
  `launch_testing` plugin importing missing `lark`.
- No Isaac Sim, Gateway Action, simulator step, or physical motion was run.

