# Implementation Review v15.2.0: Restarted Assignment Resolution

Date: 2026-10-21 (Asia/Shanghai)

## Findings and disposition

### Major: place resolution rejected the post-acquire scene revision

The approved route is prepared against the initial scene revision. Acquire changes
the world and PAOS projects the new current revision into the later place
request. `StoredAssignmentResolver` previously required the route's original
revision to equal the place request revision, making a valid acquire/place
sequence fail after any scene-changing acquire. The resolver now keeps strict
revision equality for acquire, verifies the stored route revision against the
assignment's original revision when available, and projects the caller's current
revision for place. The existing `PersistentActionEndpoint` remains responsible
for checking that revision against the live snapshot and possession state.

The second check is conditional only for legacy assignment fixtures that lack
`scene_revision`; production assignments with the field are strictly bound.

## PAOS architecture and extension review

- The store and resolver remain provider-neutral and know no simulator, scene
  graph, or robot SDK.
- The artifact retains its original preparation/assignment revision. Only the
  place execution projection receives the current post-acquire revision.
- Adapter/runtime admission remains the owner of live scene and held-object
  validation; the resolver does not authorize motion.
- Tool receipts remain internal to `SubtaskExecutor`; this change creates no
  Agent-facing node or intermediate settlement.
- No new hash, frozen contract, or broad gate was introduced.

## AgentLoop and Developer Guide review

No AgentLoop scheduling, Task/PlanNode, ToolSpec, or settlement reducer changed.
The integration test exercises a preparation response through SubtaskExecutor,
closes and reopens the SQLite store, then resolves acquire and place from the
persisted canonical reference. Cross-task lookup still fails closed.

## Robotics safety

All tests are no-motion. Acquire must match the original prepared revision;
place receives the post-acquire revision and is still subject to the endpoint's
live snapshot, caller ownership, and possession checks. No Isaac Sim, Gateway
Action, simulator step, or motion was run.

## Seven-dimension acceptance

1. Perception correctness: **not validated**; this stage does not add a sensor
   observation or target detector.
2. Binding and freshness: **partial**; canonical assignment, preparation,
   entity, candidate, destination, and original scene lineage are checked, but
   no live sensor freshness chain was exercised.
3. Subtask-level AgentLoop boundary: **pass for regression scope**; one subtask
   still owns its internal Tool sequence and one settlement.
4. IK, workspace, and collision: **not live-validated**; no planner or robot
   motion was invoked.
5. Execution state: **not validated**; no acquire/place Action was started.
6. Process feedback: **not validated**; no pour/stir process was run.
7. Settlement and recovery: **partial**; SQLite artifact persistence across
   store recreation and resolver ownership checks pass; live recovery and
   task-scoped production assignment generation remain open.

Overall acceptance: **incomplete**. In particular, the current LabUtopia cycle
provider is not a production perception-bound acquire/place route producer and
does not emit the complete route artifact required by this workflow. It must
not be used to claim that the durable route loop is complete.

## Validation

- Persistent Runtime and subtask executor tests: **46 passed**.
- Agent planning, multi-object Agent, LabUtopia PAOS wiring, and RoboTwin
  persistent AgentLoop tests: **35 passed**.
- Ruff and `git diff --check`: passed.
- Pytest reports the existing unknown `asyncio_mode` warning in the focused
  suite; the AgentLoop suite passes with its configured async plugin.

## Remaining blockers

- A real observation-bound preparation provider must emit the selected PAOS
  assignment and its approved route arguments.
- LabUtopia acquire, pour/stir, and place must use that same subtask execution
  path and return measured execution feedback.
- Real camera lineage, IK/workspace/collision, process outcome, and AgentLoop
  recovery evidence are still required before the seven dimensions pass.
