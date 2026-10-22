# Implementation Review v15.4.7: Semantic Builder Host Assembly

Date: 2026-10-22 (Asia/Shanghai)

## Findings and disposition

- Blocker resolved: the standard `agent` and `gateway` CLI hosts now pass the configured semantic builder into `AgentLoop`; the builder is created from the active `DynamicForgeToolClient` through an opt-in entry point, not a Core import of a workflow/environment package.
- Blocker resolved: `forge.semantic_plan_builder` is optional. When unset, existing task creation behavior is unchanged and the semantic-subtask schema remains unavailable. A configured but missing or invalid extension fails host startup rather than silently creating an unbound task.
- Major resolved: the production workflow factory uses the asynchronous Query builder. It reads the four current Query ToolSpecs before binding, verifies tool identity, Query semantics, endpoint, and operation against the provider-neutral PAOS query contract, then records a policy snapshot digest from those ToolSpecs. Query observations still supply the actual measured binding.
- No motion was authorized or run. The test Query providers are fixtures and are not evidence of camera perception or physical execution.

## Architecture review

- PAOS Core owns extension discovery, selection configuration, and host dependency injection. It defines only the factory protocol and does not import workflow, simulator, USD, or camera implementation modules.
- The workflow extension owns semantic request interpretation and Query choreography. Providers own observation, understanding, grasp candidates, and capabilities. The Coordinator remains the task persistence owner.
- The builder completes all Query binding before `ForgeTaskCreateTool` persists the task. Internal acquire/process/place Tools remain inside one `manipulation.execute_subtask` PlanNode and do not introduce an Agent turn between tools.
- Plan digest fields are provenance/integrity metadata required by `PlanGraph`; they do not authorize motion. Runtime admission, task binding, and Action safety remain authoritative.

## Developer Guide and AgentLoop review

- Extension discovery follows the existing `PlannerPluginRegistry` entry-point pattern and is opt-in through configuration.
- CLI host assembly passes the same active dynamic Forge client used by task-bound Query execution; switching the managed Runtime remains visible through the proxy.
- The builder must implement `build(task_description, semantic_subtasks)` and can be synchronous or asynchronous at the Tool interface; the installed workflow factory selects the asynchronous implementation.
- Query binding failure occurs before Coordinator persistence. Tool-level receipts and the single subtask-level settlement boundary are unchanged.

## Seven-dimension acceptance

1. Perception correctness: partial. Query ordering and semantic selector binding pass provider fixtures; real camera evidence is not available.
2. Binding and freshness: no-motion pass for the tested Query contracts, lineage, and stale rejection; no live sensor freshness measurement.
3. AgentLoop subtask boundary: no-motion pass. One manipulation subtask remains one Agent-facing PlanNode; internal Tools are not exposed as separate planning nodes.
4. IK, workspace, collision: not verified. No Lula/RMPFlow or collision execution was run.
5. Physical execution state: not verified. No acquire/place, gripper hold, release, or support confirmation was run.
6. Process feedback: not verified. No measured pour angle/alignment window or stir tip trajectory/depth/revolutions was collected.
7. Settlement and recovery: partial. Task creation and executor regressions pass; live AgentLoop recovery after simulator/runtime failure is not verified.

## Validation

- Focused task, registry, AgentLoop, perception-binding, subtask-executor tests: `206 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- One pytest warning remains: local pytest does not recognize `asyncio_mode`; the focused tests pass without plugin autoload and explicitly exercise async code with `asyncio.run`.
- No Isaac Sim, Gateway Action, simulator step, robot motion, or hardware IO was started.

## Remaining acceptance blockers

This stage closes the standard-host injection gap only. The complete solution is not accepted until a real installed Forge Runtime provides live sensor observations and the full task is run with verified IK/workspace/collision, acquire/place state, process feedback, and one settlement/recovery boundary per subtask.
