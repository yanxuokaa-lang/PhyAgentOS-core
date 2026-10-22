# Implementation Review v15.5.8: Durable Isaac Observation Artifacts

Date: 2026-10-22 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Scope

This increment adds an adapter-owned filesystem writer for Isaac camera arrays and calibration mappings. It atomically persists values and returns opaque `artifact://` references with the actual serialization media type. It does not register cameras in the persistent worker or advertise observation readiness.

## Architecture and Developer Guide review

- **PAOS ownership:** the provider-neutral ObservationEndpoint still owns validation and public result semantics. The writer is an injected adapter port implementation; no Core or AgentLoop ownership changed.
- **Extensibility:** the writer accepts a root and URI namespace rather than embedding a scene path. Other environments can supply their own `ObservationArtifactWriter` implementation.
- **Domain boundary:** camera arrays and calibration mappings remain adapter-side values; PAOS receives only artifact refs and media types.
- **Lifecycle:** this adds no task, receipt, or settlement state. It does not add an Agent turn or change subtask settlement granularity.
- **Failure semantics:** invalid capture metadata, unsupported kinds, empty arrays, serialization errors, and file errors raise to the existing ObservationEndpoint boundary, which reports the observation unavailable. No artifact ref is returned before atomic persistence succeeds.
- **Anti-OverDefense:** no new digest/hash, schema freeze, or global gate was added. UUID names avoid file collisions; atomic replacement prevents consumers from seeing partially written artifacts.
- **Robotics safety:** no camera SDK, SimulationApp, simulation step, IK, collision query, or motion was run. This increment cannot enable motion.

## Review findings

1. **Blocker for end-to-end perception:** `FilesystemObservationArtifactWriter` is not yet composed into the persistent Isaac worker, and no worker-owned camera registry is registered. The production engine remains `observation_ready=False`.
2. **Blocker for binding consistency:** scene revision is still checked against the static profile value in prepare/execute. A live session revision and its propagation through observation, preparation, assignment, and action are still required.
3. **Major artifact integration gap:** refs are persisted under the configured root but no PAOS artifact-serving/resolution endpoint is wired for consumers. The returned ref is traceable, but this increment does not establish remote retrieval.

No Blocker or Major is hidden by this phase review; they prevent overall plan acceptance but do not invalidate the isolated writer contract.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Partial | Camera observation source can persist artifacts through an injected writer; worker camera registration and live Isaac capture remain absent. |
| 2. Binding and freshness | Not accepted | No live revision propagation or perception binding is produced by this change. |
| 3. Agent task granularity | Partial, unchanged | Writer adds no Agent turn; full acquire/process/place subtask settlement is not exercised. |
| 4. IK, workspace, collision | Not verified | No planning or safety query ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator state transition ran. |
| 6. Process feedback | Not verified | No pour/stir evidence was captured. |
| 7. Subtask settlement/recovery | Partial, unchanged | Existing settlement path is untouched; no live task receipt or recovery ran. |

Overall plan acceptance: **not accepted**.

## Validation

- `ruff check examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/observation.py examples/forge-adapters/isaacsim_lab/tests/test_observation.py examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/__init__.py`: passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src pytest -q examples/forge-adapters/isaacsim_lab/tests`: `76 passed`.
- Pytest reported the existing `asyncio_mode` unknown-option warning when plugin autoload is disabled.
- No Isaac Sim, Gateway, simulator step, IK, collision query, or motion ran.
