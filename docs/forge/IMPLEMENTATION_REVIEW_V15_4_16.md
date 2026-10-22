# Implementation Review v15.4.16: Isaac Camera Observation Source

Date: 2026-10-22 (Asia/Shanghai)

## Findings and disposition

- No Blocker or Major remains in the bounded sensor-source implementation.
- PAOS Core already owns the provider-neutral `ObservationSource.capture(request)` contract and `scene.observe` validation. The adapter now supplies `IsaacCameraObservationSource`, which resolves registered camera handles by opaque `sensor_ref`, reads configured RGB/depth/point-cloud modalities, and asks the host for the live frame, calibration reference, and scene revision.
- Sensor artifacts are written through an injected `ObservationArtifactWriter`. The source requires the writer to return both the stored artifact reference and its actual media type; it does not label raw arrays as PNG or manufacture calibration/scene metadata.
- `build_labutopia_runtime(observation_source=...)` already injects this source into the PAOS observation endpoint. Runtime integration now exercises that path using a fake Isaac camera; this proves adapter wiring and contract behavior only.

## PAOS architecture and extensibility review

- Core remains free of Isaac Sim, USD, LabUtopia, camera-driver, and storage dependencies.
- The Isaac adapter contains only camera API translation. Sensor lookup, live metadata, and artifact persistence are injected ports, so another Isaac task can reuse the source without a task-specific perception class.
- Semantic understanding, label recognition, grasp proposal, capability discovery, and preparation remain separate providers. The source does not read Prim paths, actor state, or profile labels to claim perception.
- Existing Runtime and AgentLoop ownership is unchanged: Query receipts stay Runtime-owned and internal manipulation calls remain inside one SubtaskExecutor boundary. No new Agent turn is introduced.
- No hashes, parallel observation registry, or extra authorization gates were added. The unavailable result on incomplete live evidence is required by the existing observation contract.

## Implementation review findings

- `Major` resolved: inferred media type could have misrepresented raw camera arrays as PNG. The source now requires the artifact writer's actual `media_type`.
- `Major` resolved: required calibration/frame/revision could otherwise be filled from a static profile. The source now requires all three from the injected host metadata resolver and returns unavailable if any are absent.
- Remaining integration gap: the current LabUtopia cycle worker creates and closes `SimulationApp` per episode and does not expose its task camera handles to the PAOS host. This implementation is reusable once a live host registers handles; it does not yet create or keep that live camera session.

## AgentLoop review

- Agent-facing observation remains `scene.observe`; the camera registry and metadata resolver are adapter-private.
- No planning, Tool visibility, Coordinator, subtask, settlement, or recovery behavior changed.
- Query invocation is no-motion. Missing sensor or live evidence returns unavailable; an absent artifact-writer port prevents source construction. Neither condition can enable an Action.

## Seven-dimension acceptance

1. Perception correctness: partial. Real Isaac camera reads are implemented behind the adapter, but this stage uses fake cameras and has not verified label recognition or a live sensor.
2. Binding and freshness: no-motion contract pass. The real Runtime observation endpoint validates frame, calibration reference, scene revision, timestamp, artifacts, and freshness; live metadata provenance remains unverified.
3. AgentLoop subtask boundary: unchanged and covered by prior subtask tests; this change adds no Agent turn. No full live AgentLoop session was run.
4. IK, workspace, collision: unverified; no planner or collision checker ran.
5. Physical acquire/place state: unverified; no Action or gripper feedback ran.
6. Pour/stir process feedback: unverified; no process trajectory was executed.
7. Settlement and recovery: unchanged but not live-verified; no persistent live subtask was run.

## Validation and safety

- Isaac observation source, PAOS Runtime integration, and engine tests: `48 passed`.
- Ruff passed. Tests are no-motion; camera fixtures are not evidence of a live Isaac sensor, calibrated geometry, semantic perception, IK, or physics.
- No Isaac Sim, Gateway Action, simulator step, robot motion, or hardware IO was started.

## Remaining acceptance blockers

The complete plan remains unaccepted. Next, provide a host-owned camera session that exposes initialized Isaac camera handles and authoritative calibration/frame/scene-revision metadata to PAOS before task creation. Then add real understanding and grasp providers, and continue through no-motion subtask checks before any separately authorized simulator run.
