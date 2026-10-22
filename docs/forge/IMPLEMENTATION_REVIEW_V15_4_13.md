# Implementation Review v15.4.13: Standard CLI Builder Host Wiring

Date: 2026-10-22 (Asia/Shanghai)

## Findings and disposition

- No Blocker or Major finding in this no-motion host-composition regression.
- `tests/test_cli_semantic_builder_host.py` replaces Runtime/catalog/coordinator dependencies with typed identity-checking fakes, then calls the real `_make_forge_components` function.
- With `forge.semantic_plan_builder="fixture"`, Registry discovery occurs, the builder receives the exact `DynamicForgeToolClient` instance used as Coordinator client, and the returned builder is passed through the component tuple.
- With the setting unset, discovery and builder creation are not called and the returned builder remains `None`, preserving the optional extension behavior.
- The test invokes no Agent conversation, Runtime Query/Action, Gateway, simulator, or motion.

## PAOS architecture and extensibility review

- CLI host assembly owns dependency composition; Core Registry owns generic entry-point discovery; the workflow extension owns semantic builder creation; Coordinator owns task persistence. No ownership duplication was added.
- Substitutable fakes verify the host depends on the established interfaces and object identity, not environment names or Prim paths.
- No hashes, new authorization gates, or duplicate stores were added. The test covers the concrete failure mode of a builder receiving a different query client than the Coordinator-managed client.

## Developer Guide and AgentLoop review

- The configured builder is created once during host assembly and injected into AgentLoop through the existing component tuple. The unset path remains backward-compatible.
- The existing AgentLoop ToolRegistry regression still proves the downstream `forge_task_create` call and one `manipulation.execute_subtask` Agent-facing node.
- This change does not launch the Agent command or a model turn; it proves composition only, not LLM selection or runtime lifecycle.

## Seven-dimension acceptance

1. Perception correctness: partial. The builder receives the host query port, but fixtures—not live sensors—supply observations.
2. Binding and freshness: no-motion pass for existing binding/stale tests; live timestamps/calibration are not measured.
3. AgentLoop subtask boundary: no-motion pass via existing ToolRegistry integration; one subtask remains one Agent-facing node.
4. IK, workspace, collision: not verified; no robot planner or collision checker was invoked.
5. Physical execution state: not verified; no gripper/object state was observed.
6. Process feedback: not verified; no pour/stir execution or process measurements were collected.
7. Settlement and recovery: partial; host/task creation and prior executor tests pass, but live recovery and terminal settlement are not demonstrated.

## Validation and safety

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src pytest -q tests/test_cli_semantic_builder_host.py examples/forge-skills/pick-place-workflow/tests/test_semantic_task_creation.py tests/test_agent_task_tool.py tests/test_agent_foundation.py`: `182 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- One local pytest warning remains because plugin autoload is disabled while `asyncio_mode` is configured.
- No Agent dialogue, Gateway, Runtime Query/Action, Isaac Sim, simulator step, robot motion, or hardware IO was started.

## Remaining acceptance blockers

The standard host now has no-motion evidence that the configured builder and query client are composed consistently. Full acceptance still requires a live installed Runtime/Agent task lifecycle, sensor-backed bindings, IK/workspace/collision, physical acquire/place feedback, measured pour/stir feedback, and one terminal settlement/recovery boundary per subtask.
