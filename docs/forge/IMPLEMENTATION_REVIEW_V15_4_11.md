# Implementation Review v15.4.11: Installed Workflow Extension Discovery

Date: 2026-10-22 (Asia/Shanghai)

## Findings and disposition

- No Blocker or Major finding in this bounded integration-test change.
- The prior test parsed `pyproject.toml` only. The new regression builds a wheel, installs it into a pytest-owned temporary target, then launches a subprocess that uses PAOS `SemanticPlanBuilderRegistry.discover()` and `create()` to load the installed workflow factory.
- Wheel build or installation failures fail the regression. If the build backend is not installed, `pytest.importorskip("hatchling")` marks this packaging test skipped rather than passing it.
- The smoke test injects an inert object as the Query invoker and only checks builder construction. It does not call Query, Action, or any simulator API.

## PAOS architecture and extensibility review

- Core retains ownership of entry-point discovery and the factory protocol. The workflow remains a separately packaged extension; no workflow/environment import was added to Core.
- The test changes packaging and installation location while using the same Core Registry API. The builder is created from the installed package without changing the task-creation API or AgentLoop.
- This test validates extension packaging/discovery, not provider replacement behavior; provider replacement remains covered by the existing two-fixture semantic-builder test.
- No hashes, new runtime gates, or duplicate state stores were introduced. The test uses ordinary package metadata and subprocess behavior as evidence.

## Developer Guide and AgentLoop review

- The installed extension factory implements the existing `paos.semantic_plan_builders` contract and produces a builder with the expected `build` method.
- The previous v15.4.10 regression continues to cover the AgentLoop ToolRegistry to `forge_task_create` to Coordinator path and verifies one Agent-facing `manipulation.execute_subtask` node.
- This stage does not test Core wheel installation, CLI process startup, live LLM tool selection, or Gateway session lifecycle. Those remain separate acceptance work.

## Seven-dimension acceptance

1. Perception correctness: partial. Installed factory loading and fixture-based semantic binding are covered; no live sensor observation is present.
2. Binding and freshness: no-motion pass for existing fixture lineage/staleness tests; no sensor timestamp or calibration measurement was made.
3. AgentLoop subtask boundary: no-motion pass from the existing ToolRegistry regression; one manipulation subtask remains one Agent-facing node.
4. IK, workspace, collision: not verified. No planner or collision checker was run.
5. Physical execution state: not verified. No gripper or object state was observed.
6. Process feedback: not verified. No pour or stir was performed or measured.
7. Settlement and recovery: partial. Task creation and prior no-motion executor tests pass; live runtime recovery and terminal settlement are not demonstrated by this phase.

## Validation and safety

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src pytest -q examples/forge-skills/pick-place-workflow/tests/test_semantic_task_creation.py tests/test_agent_task_tool.py tests/test_agent_foundation.py`: `180 passed`.
- Isolated wheel build/install/Registry discovery test: `1 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- Pytest emits one local warning because plugin autoload is disabled while `asyncio_mode` remains configured.
- No Gateway, Isaac Sim, simulator step, Runtime Action, robot motion, or hardware IO was started.

## Remaining acceptance blockers

The extension wheel is proven discoverable against Core source code, but a clean combined PAOS+workflow installation and standard CLI startup have not been exercised. The complete plan still requires live sensor binding, verified IK/workspace/collision, physical acquire/place feedback, measured pour/stir evidence, and one subtask-level terminal settlement/recovery per subtask.
