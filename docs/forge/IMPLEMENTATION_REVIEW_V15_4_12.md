# Implementation Review v15.4.12: Combined Core and Workflow Installation

Date: 2026-10-22 (Asia/Shanghai)

## Findings and disposition

- No Blocker or Major finding in this packaging/host smoke-test change.
- The regression builds both PAOS Core and pick-place workflow wheels, installs both into one pytest-managed temporary target, and starts a subprocess with that target as its only `PYTHONPATH` and a temporary cwd outside the repository.
- The subprocess checks that `PhyAgentOS` and `pick_place_workflow` resolve from the installed target, discovers and instantiates the configured factory through `SemanticPlanBuilderRegistry`, then invokes the standard Typer app's `--help` command.
- Wheel build/install failures and CLI/import failures fail the test. If `hatchling` is absent, the test explicitly skips instead of reporting success.
- No Agent dialogue, Runtime Query, Action, Gateway, simulator, or motion is invoked. CLI help validates import/command registration only, not a configured Agent or Gateway startup.

## PAOS architecture and extensibility review

- PAOS Core owns generic entry-point discovery and host composition; the workflow package owns semantic binding. The test confirms both packages coexist in an isolated install without adding environment-specific imports to Core.
- The extension boundary is replaceable at package installation/entry-point discovery; existing provider fixture replacement tests continue to verify semantic provider substitution without changes to the Core API.
- The test uses ordinary wheel metadata and imports. No hashes, new runtime authorization gates, or duplicate state stores were introduced.

## Developer Guide and AgentLoop review

- The standard CLI application imports and renders help from the combined installation. Registry discovery returns the installed workflow builder and its `build` method.
- The prior v15.4.10 regression covers AgentLoop ToolRegistry -> `forge_task_create` -> Coordinator and confirms one Agent-facing `manipulation.execute_subtask` node.
- This phase does not launch the Agent command, prove LLM selection, load managed Runtime capabilities, or exercise a Gateway session. No AgentLoop production behavior changed.

## Seven-dimension acceptance

1. Perception correctness: partial. Fixture-backed binding remains; no live camera/depth/segmentation evidence.
2. Binding and freshness: no-motion pass for fixture lineage/stale rejection; no live calibration or observation freshness measurement.
3. AgentLoop subtask boundary: no-motion pass from the registered Tool regression; one manipulation subtask remains one Agent-facing node.
4. IK, workspace, collision: not verified; no planner or collision checker was run.
5. Physical execution state: not verified; no acquire/place or gripper feedback was collected.
6. Process feedback: not verified; no pour/stir action or measured process signal was collected.
7. Settlement and recovery: partial; creation and existing executor tests pass, but live terminal settlement and recovery are not demonstrated.

## Validation and safety

- Focused semantic task creation, Forge task, and AgentLoop regressions: `180 passed`.
- Combined Core/workflow wheel build, isolated installation, installed module-origin checks, Registry discovery, and CLI help smoke: `1 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- One local pytest warning remains because plugin autoload is disabled while `asyncio_mode` is configured.
- No Agent dialogue, Gateway, Runtime Query/Action, Isaac Sim, simulator step, robot motion, or hardware IO was started.

## Remaining acceptance blockers

Full acceptance still requires real sensor-backed bindings, a configured Runtime/Agent task lifecycle, verified IK/workspace/collision, observed acquire/place state, measured pour/stir feedback, and exactly one terminal settlement/recovery decision per subtask. The combined wheel and CLI-help smoke closes packaging/import discovery only.
