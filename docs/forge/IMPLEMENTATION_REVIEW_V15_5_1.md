# Implementation Review v15.5.1: Live Isaac Camera Calibration Metadata

Date: 2026-10-22 (Asia/Shanghai)

## Findings and disposition

- `Major` resolved: the observation source could receive a profile/static calibration reference unrelated to the active sensor. The new provider reads intrinsics, world pose, and resolution from the registered live camera and persists those values before returning its calibration reference.
- Camera API failures or invalid calibration return unavailable. Artifact-writer failures are not swallowed, so storage errors remain visible to the Query caller.
- `Blocker` remains: the provider can only access camera handles in the process that owns the live Isaac session. The current LabUtopia action worker starts and closes `SimulationApp` per episode and does not expose those handles to the PAOS host. This change does not create a persistent RPC session or prove that observation and action share one scene revision.

## PAOS architecture and extensibility review

- PAOS Core still owns the provider-neutral observation contract and Query receipt; no Isaac dependency was added to Core.
- The sensor adapter owns Isaac API translation. Camera registry, frame/revision resolution, and artifact persistence remain host-injected boundaries; no LabUtopia task name, Prim path, or profile is read by the provider.
- The normalized calibration artifact contains sensor reference, frame, scene revision, resolution, intrinsics, and world pose. The host remains authoritative for frame identity and scene revision.
- No new Agent-visible Tool, PlanNode, settlement, or duplicate lifecycle state was added. AgentLoop continues to call scene observation as subtask pre-binding; internal action Tools remain settled once by the existing SubtaskExecutor.
- This fits the Developer Guide's provider/adapter extension boundary. It does not yet satisfy the full task requirement because the required live provider cannot be constructed from the current PAOS host process.

## Implementation review

- Isaac Sim 5.1 installed source confirms the used Camera API methods: `get_intrinsics_matrix(device=...)`, `get_world_pose(camera_axes=...)`, and `get_resolution()`.
- No SDK imports execute in the unit-test process. The provider consumes an injected camera registry and writer, and its test fixtures match the inspected API signatures.
- Calibration persistence is performed on each metadata resolution so a changed camera pose/resolution creates a new measured artifact. This is deliberately not cached because the current host has no authoritative invalidation event for camera movement or lens changes.
- The remaining integration is process/session ownership, not another perception adapter: the environment must expose its initialized camera handles through a session boundary usable by both scene Query and Action.

## AgentLoop review

- `scene.observe` remains the Agent-facing Query and still runs before a selected subtask; this provider does not introduce model turns or tool-level settlements.
- Missing camera, frame, scene revision, or valid calibration remains unavailable and therefore cannot create a measured binding.
- Writer errors propagate as infrastructure failures rather than being misreported as sensor unavailability.

## Seven-dimension acceptance

1. Perception correctness: partial. Real Isaac calibration API mapping is implemented, but no live camera or semantic label/grasp provider was run.
2. Binding and freshness: partial. Calibration data and live host frame/revision are linked in the artifact; same-session scene lineage and live freshness remain unverified.
3. AgentLoop subtask boundary: contract pass; no AgentLoop behavior changed and no tool-level settlement was introduced.
4. IK, workspace, collision: unverified; no planner or collision checker ran.
5. Acquire/place physical state: unverified; no action, gripper, or placement feedback ran.
6. Pour/stir process feedback: unverified; no process trajectory ran.
7. Subtask settlement and recovery: no-motion contract unchanged; live task settlement/recovery remains unverified.

## Validation and safety

- Focused observation, PAOS integration, and engine tests: `54 passed`; Ruff and `git diff --check` passed.
- One existing local pytest warning remains: with plugin autoload disabled, pytest does not recognize `asyncio_mode`.
- No Isaac Sim, Gateway, Action, simulator step, robot motion, or hardware IO was started.

## Acceptance status

The complete plan is not accepted. The next required stage is a persistent environment-session boundary that owns initialized camera handles and serves both observation Query and action execution against one scene authority. It must be implemented where the Isaac session is actually created, without adding a LabUtopia-specific perception class to PAOS Core or the generic workflow package.
