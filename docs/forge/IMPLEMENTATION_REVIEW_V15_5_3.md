# Implementation Review v15.5.3: Session-Owned LabUtopia Task Lifecycle

Date: 2026-10-22 (Asia/Shanghai)

## Findings and disposition

- `Major` fixed: LabUtopia `BaseTask.setup_cameras()` and `BaseTask.reset()` reset the World implicitly. Added an opt-in session-owned mode that leaves World reset under the caller's ownership.
- `Major` fixed: `PickPourTask.reset()` and `StirTask.reset()` also reinitialized the robot and repositioned task objects. In session-owned mode these methods now perform only base task bookkeeping and skip those scene-changing effects.
- `Blocker` remains for the end-to-end requirement: the Isaac worker does not yet construct and retain a task/world/camera registry in the same owner. Existing engine episodes still create their own World and Tasks, so this new lifecycle seam is not yet wired to live observation/action.
- `Blocker` remains for perception: no worker camera RPC or artifact-writer IPC path was added; `scene.observe` still has no live LabUtopia camera source.

## PAOS architecture and extensibility

- The lifecycle flag is owned by the environment Task layer, where World reset and task-specific repositioning occur. No simulator concepts enter PAOS Core or the provider-neutral observation contract.
- Default constructors retain `session_owned_scene=False`, preserving existing callers. A scene owner must initialize/reset World before constructing a session-owned task and must explicitly own scene reset/revision.
- The opt-in flag is a lifecycle seam, not evidence that the worker now shares a scene. It avoids a new environment-specific perception adapter and does not change Agent-visible tools.

## Developer Guide and AgentLoop review

- Change remains within the owner of the reset side effects and does not create a second task, Runtime, or settlement store.
- No PlanNode, Agent turn, Tool receipt, or NodeSettlement behavior changed. The requirement that internal acquire/process/place calls settle once per subtask remains unaffected.
- The full worker wiring must next inject this mode during one worker-owned scene construction and route observation/action requests to those retained handles. It must also prevent perception poses from being used to teleport scene prims.

## Seven-Dimension Acceptance

1. Perception correctness: not accepted; no live camera observation or semantic detection was run.
2. Binding and freshness: not accepted; no PAOS observation artifacts or same-revision binding were produced.
3. AgentLoop subtask boundary: contract preserved; no loop changes or model turns were introduced. End-to-end execution remains unverified.
4. IK, workspace, collision: unverified; no Isaac planner or collision query ran.
5. Acquire/place state: unverified; no robot or simulation action ran.
6. Pour/stir process feedback: unverified; no controller episode ran.
7. Settlement and recovery: existing PAOS boundary unchanged; live subtask settlement and recovery remain unverified.

## Validation and safety

- `cd /home/yanxu/LabUtopia && PYTHONPATH=. pytest -q tests/test_task_scene_lifecycle.py`: 8 passed. These tests stub Isaac APIs and validate only task reset ownership.
- `python -m py_compile tasks/base_task.py tasks/pickpour_task.py tasks/stir_task.py tests/test_task_scene_lifecycle.py`: passed.
- `git diff --check` in the LabUtopia working tree reports trailing whitespace in pre-existing user edits and CRLF additions in touched files; those changes were not normalized or altered to avoid rewriting the user's worktree.
- No Isaac Sim, Gateway, simulation stepping, Action, or robot motion was started.

## Acceptance status

This lifecycle subfeature passes its no-motion contract tests. The complete plan is not accepted. The next required stage is worker-owned World/Task/camera construction shared by observation and Action, with persisted sensor artifacts and measured binding; the seven physical/perception dimensions remain open.
