# Implementation Review v15.5.12: Provider-Neutral Artifact Resolution

Date: 2026-10-23 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Findings and disposition

No Blocker or Major findings remain for the bounded Core resolver implementation.

- `ArtifactResolver` is a provider-neutral read port. `LocalFilesystemArtifactResolver` is one storage implementation configured by an authority-to-root map; it has no Isaac, LabUtopia, or RoboTwin dependencies.
- Consumers receive only bytes and media type. Filesystem paths stay inside the resolver implementation.
- Unknown authorities, malformed URIs, encoded traversal, query/fragment variants, missing files, empty files, unsupported media types, and symlinks escaping the configured root resolve as unavailable (`None`).
- Core tests exercise image, NPY, and JSON payloads. An Isaac observation-writer test confirms that its emitted `artifact://labutopia/...` refs resolve to the same persisted bytes and media types.
- The specific failure scenario justifying path confinement is a ref escaping a configured artifact root and causing a local consumer to read an unrelated file. Root containment is required; content hashes are not required for this read contract and were not added.

## Architecture and Developer Guide review

- **PAOS ownership:** the Forge Core owns the generic resolver contract and path-independent payload type. A deployment composition owns the mapping from artifact authorities to storage roots. Sensor providers continue to own capture and writing.
- **Dependency direction:** Core does not import adapters or simulator APIs. Storage-specific behavior sits behind the Core protocol.
- **Extensibility:** callers can inject a different implementation (remote object store, database-backed store, or test fixture) without changing observation/understanding schemas or AgentLoop.
- **Lifecycle and AgentLoop:** no task, invocation, receipt, settlement, or AgentLoop state changed. Artifact resolution is provider IO within an existing understanding call and does not add model turns or settlements.
- **Failure semantics:** unresolved refs remain unavailable; the resolver does not synthesize data or promote a missing artifact to success.
- **Anti-OverDefense:** path containment is tied to caller-controlled artifact refs and a concrete local-file escape scenario. No digest, schema freeze, or general gate was introduced.
- **Robotics safety:** this is a no-motion data-access change. No camera SDK, Isaac Sim, Gateway, IK, collision check, or robot motion was run.

## Review findings still blocking the overall plan

1. **Major, overall plan:** no LabUtopia deployment composition injects this resolver into a semantic-understanding provider. The resolver is reusable and tested, but `scene.understand` still has no LabUtopia runtime path to consume these camera artifacts.
2. **Major, overall plan:** RGB is currently persisted as NPY (`application/x-npy`), while existing model vision providers consume image media. A later provider integration must either support NPY explicitly or the observation writer must produce a standard image artifact without losing the measured source.
3. **Major, overall plan:** the worker-local artifact root is not yet exposed to a PAOS Agent host through a deployment-owned resolver configuration or remote artifact service.

These are not defects in the provider-neutral resolver itself; they prevent claiming that the LabUtopia observation-to-understanding path is complete.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Partial | Existing worker camera artifacts resolve by URI in tests; no live camera capture or semantic perception was run. |
| 2. Binding and freshness | Partial | Resolver preserves exact stored bytes/media type and does not rewrite evidence refs. Full observation-to-binding lineage remains incomplete. |
| 3. Agent task granularity | Partial, unchanged | No AgentLoop changes; no LabUtopia semantic subtask was run. |
| 4. IK, workspace, collision | Not verified | No kinematic or collision query ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator state transition ran. |
| 6. Process feedback | Not verified | No pour/stir feedback was captured. |
| 7. Subtask settlement/recovery | Partial, unchanged | No multi-tool LabUtopia task or live settlement/recovery was run. |

Overall plan acceptance: **not accepted**.

## Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src pytest -q tests/test_forge_artifacts.py examples/forge-adapters/isaacsim_lab/tests`: `92 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- Pytest reports the existing unknown `asyncio_mode` option warning with plugin autoload disabled. No Isaac Sim, Gateway, simulation step, IK, collision query, or motion ran.
