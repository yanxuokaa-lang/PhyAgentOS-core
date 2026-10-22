# Implementation Review v15.5.2: Reusable Isaac Worker Process

Date: 2026-10-22 (Asia/Shanghai)

## Findings

- `Blocker` remains for the complete task: the worker now owns one long-lived `SimulationApp` process, but each Action still enters the existing episode builder, which creates a `World` and loads the task scene. There is no registered live camera source in that owner. Process reuse therefore does not yet prove that Query and Action share one live scene revision or initialized camera handles.
- The worker has an explicit `observe` RPC, but the current environment backend returns `unavailable/session_camera_registry_unavailable`. PAOS composition checks readiness and does not advertise the worker as a perception source while that remains false.
- Worker startup, request serialization, cancellation, response correlation, and close are owned by the adapter session client. No PAOS Core lifecycle, Agent-visible node, settlement store, or generic workflow code was added.

## PAOS Architecture and Extensibility

- `IsaacWorkerSession` belongs in the environment Adapter because it owns the Isaac child process and translates stable `execute_cycle`/`observe` request methods into local IPC. PAOS Runtime remains the caller and closes the worker through the existing client lifecycle.
- The IPC contract uses request IDs and JSON domain payloads; it does not expose Isaac SDK handles, USD objects, or worker paths to PAOS. A replacement worker process can be substituted without changing the PAOS client protocol.
- Requests are serialized by one session lock and served in order by one worker owner. No second scheduler or settlement state was introduced.
- Observation absence remains unavailable. The test backend is transport evidence only, not proof of camera acquisition or scene lineage.

## Developer Guide and Implementation Review

- Dependency direction remains PAOS client -> adapter session -> Isaac worker/backend. Core has no environment import.
- The concrete failure addressed is cross-process scene/sensor ownership caused by one new `SimulationApp` per Action. Ordinary tests cannot keep a camera handle alive across those child-process lifetimes; the worker now remains alive until its owner closes it.
- Cancellation is request-scoped: the host writes a marker observed by the worker's cancellation event. Timeouts or protocol failures discard the process and report an unknown Action result rather than success.
- `LabUtopiaCycleClient.capture` returns no observation for unavailable worker results, matching the existing ObservationSource contract. Composition also checks `observation_ready` before binding the provider-neutral perception adapter.
- The required second backend substitution test is represented by the injectable process factory and fake session server; live Isaac API compatibility still requires the installed Isaac runtime.

## AgentLoop Review

- No PlanNode, Agent turn, Tool settlement, or SubtaskExecutor boundary changes. The existing rule remains: internal Tool receipts may be retained, while Agent settlement belongs at the subtask boundary.
- The worker serializes environment requests only; it does not call an Agent, Coordinator, or Runtime Tool directly.
- The client lifecycle waits for pending Action work to finish before closing the engine, then requests worker shutdown and `SimulationApp.close()` through the worker's `finally` path.

## Seven-Dimension Acceptance

1. Perception correctness: not accepted. No live camera registry or semantic perception ran; observation is explicitly unavailable.
2. Binding and freshness: not accepted. No Query artifact was produced and no shared scene revision was demonstrated.
3. AgentLoop subtask boundary: contract preserved. This change adds no model turn or tool-level settlement; end-to-end subtask execution remains unverified.
4. IK, workspace, collision: unverified. No Isaac planner or collision query ran.
5. Acquire/place physical state: unverified. No simulation Action or gripper feedback ran.
6. Pour/stir process feedback: unverified. No process trajectory ran.
7. Subtask settlement and recovery: partial contract evidence. Cancellation propagates to the active worker request and uncertain outcomes stay unknown; live recovery/reconciliation and one final subtask settlement were not run.

## Validation and Safety

- Complete Isaac adapter test directory: `67 passed`.
- Ruff, `compileall`, and `git diff --check` passed. Pytest emitted one existing warning because plugin autoload is disabled and `asyncio_mode` is not recognized.
- Tests used a fake backend and local Unix socket. No Isaac Sim, Gateway, simulator step, Action, robot motion, or hardware IO was started.

## Acceptance Status

This worker-process milestone is accepted as a reusable IPC/lifecycle adapter, but the full plan is not accepted. The next blocker is to keep one actual stage/World alive, register real Isaac cameras in that same owner, and make both observation and action consume that same scene authority and revision. Only then can the seven dimensions proceed to live no-motion observation checks and later explicitly authorized simulation execution.
