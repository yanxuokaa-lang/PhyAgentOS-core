# Implementation Review v15.5.9: Worker Camera Observation Wiring

Date: 2026-10-22 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Scope

The persistent Isaac worker now constructs camera handles from the loaded deployment camera configuration, registers them in its session context, and composes `IsaacCameraObservationSource` with the v15.5.8 filesystem artifact writer. Observation reads RGB, depth, point cloud, intrinsics, and camera world pose through those handles. Missing camera configuration leaves the source unregistered. The public PAOS ObservationEndpoint and Core contracts are unchanged.

## Architecture and Developer Guide review

- **PAOS ownership:** Core ObservationEndpoint validates and projects results; the worker owns Isaac camera handles and the adapter owns the mapping to sensor refs, frame IDs, calibration, and persisted artifacts.
- **Dependency direction:** Isaac SDK objects remain inside the adapter. The generic runtime receives only the existing `ObservationSource` contract and artifact refs.
- **Substitutability:** the observation source and artifact writer remain injectable ports; the camera composition is environment-specific. Stub tests exercise the composition without importing or initializing Isaac Sim.
- **Lifecycle:** camera handles are registered under the existing worker session owner and are discarded with that owner. No task, invocation, receipt, settlement, or AgentLoop state was duplicated.
- **AgentLoop:** no AgentLoop code changed. Existing `observation_ready=False` remains, so this change does not make `manipulation.execute_subtask` newly visible or add a model turn.
- **Evidence and safety:** a missing sensor/config/API result remains unavailable. No SimulationApp, physics step, IK, collision query, or movement was run. The source still reports the configured profile scene revision, not a dynamic scene-state revision; it must not authorize preparation or execution.
- **Anti-OverDefense:** no new hash or broad gate was added. Duplicate sensor names are rejected because they would make `sensor://name` resolve ambiguously.

## Review findings

1. **Blocker for overall plan:** the camera metadata provider still uses `profile.scene_revision`; prepare/execute also require that static value. The observation, binding, preparation, and action lineage is not yet tied to a live worker revision. `observation_ready` deliberately remains false.
2. **Blocker for Agent integration:** although the worker now returns real sensor artifacts when explicitly observed, the PAOS perception-to-subtask chain is not enabled end-to-end. Semantic understanding, measured binding, candidate generation, preparation, and a single subtask settlement still need one common live revision.
3. **Major, runtime unverified:** LabUtopia episode Tasks also create Camera wrappers for their task observations. This phase did not run Isaac 5.1 to establish whether the additional session-owned handles sharing those prims cause duplicate render resources or API lifecycle conflicts.
4. **Major artifact integration gap:** `artifact://labutopia/...` refs map to files under `lab_root/outputs/paos-observation-artifacts`, but no Gateway artifact serving/resolver endpoint is connected.

These findings keep the overall implementation unaccepted. This phase only proves provider wiring against stubs, not live Isaac API compatibility or perception correctness.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Partial | Configured camera handles feed RGB/depth/point-cloud artifacts through the worker-owned source in stub tests; no live Isaac capture was run. |
| 2. Binding and freshness | Not accepted | Static profile revision remains; no shared live evidence chain through preparation/assignment/action. |
| 3. Agent task granularity | Partial, unchanged | No AgentLoop changes; worker capture adds no Agent turn, but a full subtask has not run. |
| 4. IK, workspace, collision | Not verified | No planning or safety query ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator state transition ran. |
| 6. Process feedback | Not verified | No pour/stir feedback was captured. |
| 7. Subtask settlement/recovery | Partial, unchanged | Existing settlement path is untouched; no live task receipt or recovery ran. |

Overall plan acceptance: **not accepted**.

## Validation

- `ruff check examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py examples/forge-adapters/isaacsim_lab/tests/test_engine.py`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src pytest -q examples/forge-adapters/isaacsim_lab/tests`: `78 passed`.
- `python -m compileall -q examples/forge-adapters/isaacsim_lab/src/isaacsim_lab`: passed.
- Pytest reported the existing unknown `asyncio_mode` option warning with plugin autoload disabled. No Isaac Sim, Gateway, simulation step, IK, collision query, or motion ran.
