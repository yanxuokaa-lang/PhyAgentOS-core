# Implementation Review v15.5.7: Worker-Owned Isaac Scene Resources

Date: 2026-10-22 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Scope and disposition

This increment moves the worker's World, USD stage, and robot into the worker-owned session for the pour/stir paths. Observation initializes these resources once; later pour/stir Actions resolve the same objects. Episode Task wrappers remain per-call because they contain target paths, frame counters, and return-pose state. A Task switch therefore creates a new wrapper without resetting the shared World or initializing the robot a second time.

The implementation is adapter-owned and does not change PAOS Core, AgentLoop, Tool receipts, or NodeSettlement. It does not provide camera registration, measured perception, durable observation artifacts, or live-task evidence. Rotation tasks are explicitly unsupported in this shared worker-scene path until their Task lifecycle supports an owned World.

## Architecture and Developer Guide review

- **PAOS ownership:** worker/session owns simulator resources; the task and Agent settlement owners are unchanged. No parallel PAOS task, receipt, or settlement state was introduced.
- **Dependency direction and extensibility:** Isaac/LabUtopia types stay in the adapter. The session boundary stores resource values without importing task classes into worker context. Another backend can keep its own resource factory behind the same worker lifecycle.
- **Domain and lifecycle ownership:** World/stage/robot are stable across calls; Task remains episode-scoped because its target and progress fields are mutable. This avoids cross-subtask target leakage while retaining a single simulator scene owner.
- **Developer Guide:** production episode entry points use the same resource helper as observation; failures in scene-path compatibility or missing live providers remain explicit. No success is inferred from resource existence.
- **AgentLoop:** no PlanNode or AgentLoop code changed. This resource reuse adds no Agent turn or tool-level settlement, but does not itself prove acquire/process/place are executed as one settled subtask.
- **Anti-OverDefense:** no hash, frozen contract, baseline, or global gate was added. The scene-path equality check is required because reusing World/robot against another USD scene would bind handles to the wrong stage; regular object identity and tests are insufficient to prevent that cross-scene mix.
- **Robotics safety:** no Isaac Sim process, simulation step, IK, collision query, or motion was run. Missing camera provider still returns unavailable. Session worker rotation fails before motion with `unsupported` and `world_change_started=false`.

## Code review findings

1. **Blocker for overall plan:** no production camera-backed `observation_source` or durable artifact writer is registered. Observation initializes scene resources but still returns unavailable without a source; it does not produce measured bindings or a scene revision.
2. **Major remaining integration gap:** OpenCloseTask does not support session-owned World lifecycle. This worker path reports rotation unsupported rather than creating a second World. A compatible Task lifecycle contract is required before handle/cap rotation can use this shared scene.
3. **Unverified runtime behavior:** fake tests establish resource identity and initialization counts, not Isaac API/runtime compatibility. Task camera handles are still created by episode Task constructors and have not been exercised against the persistent World.

No additional code defect was found within the no-motion resource-cache behavior. Findings 1-3 keep the full LabUtopia workflow unaccepted.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Not accepted | Observation now resolves/initializes the session scene, but no live camera-backed provider is registered. |
| 2. Binding and freshness | Not accepted | No measured entity/destination binding, calibration lineage, or live scene revision is produced here. |
| 3. Agent task granularity | Partial, unchanged | Worker RPCs add no Agent turn; full acquire/process/place execution and one terminal NodeSettlement are not exercised. |
| 4. IK, workspace, collision | Not verified | No live planning, IK, workspace, or collision check ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator task or physical state transition ran. |
| 6. Process feedback | Not verified | No real pour/stir feedback was captured. |
| 7. Subtask settlement/recovery | Partial, unchanged | Existing AgentLoop boundary is untouched; live receipts, failure recovery, and settlement are not connected to this scene owner. |

Overall plan acceptance: **not accepted**. Remaining work includes live camera/provider and artifact wiring, measured binding/revision lineage, compatible rotation Task lifecycle if required, real IK/collision and acquire/place checks, pour/stir process evidence, and one subtask-level settlement/recovery result.

## Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src pytest -q examples/forge-adapters/isaacsim_lab/tests`: `73 passed`.
- Ruff, `python -m compileall -q examples/forge-adapters/isaacsim_lab/src/isaacsim_lab`, and `git diff --check` passed.
- Pytest emitted the known local warning that `asyncio_mode` is unknown with plugin autoload disabled.
- No Isaac Sim, Gateway, simulation step, IK, collision query, or motion ran.
