# Implementation Review v15.1.11: Persisted Subtask Intent

Date: 2026-10-20 (Asia/Shanghai)

## Scope

This stage closes the trusted-intent contract for the Agent-facing
`manipulation.execute_subtask` Action. The semantic intent belongs to the
PlanNode; `AgentComposedDispatch` uses the existing
`manipulation_intent_v2` builder to bind task/revision/node identity and
perception evidence; the selected Action arguments persist that exact intent;
Coordinator admission reads and compares the persisted record against the
active PlanNode. No second intent builder or environment-specific intent model
was introduced.

## PAOS Architecture Review

- PlanningDispatch owns trusted argument construction and schema admission.
- PlanGraph owns the stable semantic intent and nested perception binding.
- AgentTaskCoordinator owns the persisted execution record and validates its
  task/revision/node lineage.
- Runtime owns the Action invocation lifecycle; `SubtaskActionEndpoint` only
  validates context and starts the existing Runtime-backed driver.
- Internal acquire/prepare/process/place Tool receipts remain inside one outer
  Action and do not create Agent-facing PlanNodes or NodeSettlements.

## Extension Principles

The subtask contract uses domain-level entity, observation, frame, calibration,
candidate, and semantic-intent fields. The trusted builder obtains identity
from the active PAOS graph and binding, not an environment profile or scene
node name. Provider replacement remains outside this change; the existing
assignment preparation is still performed before subtask selection and is an
open sequencing blocker.

## Developer Guide and AgentLoop Review

Missing or malformed semantic intent, missing perception binding, altered
trusted intent, stale task revision, or mismatched persisted intent is rejected
before the internal Runtime sequence starts. The selected subtask remains one
Action invocation and one outer settlement. Internal Tool receipts remain
available for diagnostics and recovery without asking the Agent to replan after
each Tool.

## Seven-Dimension Acceptance

1. Perception correctness: **partial**. The contract accepts observation-bound
   provider output; no camera/provider execution was performed in this stage.
2. Binding and freshness: **partial**. Intent binds entity, observation,
   revision, frame, calibration, and candidate set; pre-subtask assignment
   timing remains unresolved.
3. Subtask-level planning: **pass for contract**. One subtask maps to one
   `manipulation.execute_subtask` PlanNode and one Action settlement; internal
   receipts do not open AgentLoop turns.
4. IK, workspace, and collision: **not live-verified**. The existing
   preparation contract requires these checks, but no provider or simulator
   was run here.
5. Execution state: **contract-only**. Runtime driver receipts and possession
   projection are tested with no-motion fixtures; no Isaac Sim execution was
   performed.
6. Process feedback: **not live-verified**. Pour/stir measurement quality is
   unchanged and no new physical feedback evidence is claimed.
7. Settlement and recovery: **partial**. Persisted Action intent and outer
   settlement identity are validated; task-scoped preparation/assignment and
   full failure recovery remain open.

## Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src pytest -p pytest_asyncio.plugin -q tests/test_planning_dispatch.py examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py tests/test_planning_task_integration.py`: **83 passed**.
- Ruff, compileall, and `git diff --check`: **passed**.
- No Isaac Sim, Gateway Action, simulator step, or robot motion was run.

## Remaining Blocker

`PerceptionBindingAdapter.bind()` still runs `manipulation.prepare` and receives
`assignment_ref` before the Agent selects the subtask PlanNode. The next stage
must make the candidate and capability evidence available to the selected
subtask, run preparation under the persisted subtask intent, and pass the
resulting assignment through acquire/place while preserving a single outer
settlement. This stage does not claim the complete LabUtopia workflow is
accepted.
