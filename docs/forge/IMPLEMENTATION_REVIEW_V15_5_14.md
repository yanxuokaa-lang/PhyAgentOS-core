# Implementation Review v15.5.14: Artifact-Resolving Understanding Provider

Date: 2026-10-22 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Findings and disposition

No Blocker or Major findings remain for the generic Core composition mechanism. One Major blocker remains for the overall LabUtopia plan: a deployment host still needs to compose a real inference provider and a resolver configured for the observation artifact store.

- `ArtifactResolvingSceneUnderstandingProvider` implements the existing provider port and composes an injected `ArtifactResolver` with an injected inference callable/object.
- Top-level observation refs and per-view artifact descriptors are resolved, deduplicated by ref, and passed to inference as bytes plus the resolver's actual media type. View-declared media type disagreement and missing payloads fail before inference.
- The wrapper does not perform detection, assign metric geometry, map identities to simulator objects, or authorize motion. Returned claims flow through the existing `SceneUnderstandingEndpoint`, which remains responsible for PAOS schema and provenance validation.
- Two distinct inference implementations use the same wrapper in tests. The Core module has no simulator, model vendor, adapter, or environment dependency.
- No production Agent host currently constructs this wrapper with a real model and the artifact root shared with the camera worker. This remains the next wiring step; fixture inference is not perception evidence.

## PAOS architecture, extensibility, and Developer Guide

- **Ownership:** Core owns the generic bytes/media composition; the artifact store owns storage lookup; inference owns semantic claims; the existing endpoint owns claim normalization and validation.
- **Dependency direction:** Core depends only on the existing resolver port and a narrow inference protocol. No environment-specific code is imported.
- **Replaceability:** replacing both resolver and inference does not change ToolSpec, Query input, endpoint, AgentLoop, or task planning. Tests swap inference while retaining the same wrapper.
- **Lifecycle and AgentLoop:** the wrapper is synchronous provider work inside the existing `scene.understand` Query. It adds no task node, Tool invocation, settlement, or model turn.
- **Evidence:** artifact refs and returned provenance remain unchanged and are checked by the existing endpoint. Unavailable artifact payloads or mismatched declared media types do not reach inference.
- **Anti-OverDefense:** no hashes, frozen contracts, generic gate, or parallel state store were added. The only rejection covers a concrete wrong-payload/missing-payload inference failure.
- **Robotics safety:** this is no-motion Query composition; no actuator or simulator execution path changed.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Partial | Artifact bytes are delivered to two injected inference fixtures and one PAOS Query test; no real model or live camera inference was run. |
| 2. Binding and freshness | Partial | Existing Query freshness validation and endpoint provenance validation remain in force; production observation-to-binding composition is not wired. |
| 3. Agent task granularity | Partial, unchanged | No AgentLoop behavior changed; no semantic manipulation subtask was run. |
| 4. IK, workspace, collision | Not verified | No kinematic or collision query ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator state transition ran. |
| 6. Process feedback | Not verified | No pour/stir feedback was captured. |
| 7. Subtask settlement/recovery | Partial, unchanged | No multi-tool LabUtopia task or live settlement/recovery was run. |

Overall plan acceptance: **not accepted**. The next stage is deployment-owned composition of a real inference implementation and resolver rooted at the camera worker's artifact store, followed by a real observation/understanding/binding test and a second-provider substitution test. Simulation task acceptance remains separate.

## Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src pytest -q -p pytest_asyncio.plugin tests/test_forge_artifact_understanding.py tests/test_forge_artifacts.py examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py`: `52 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- No Isaac Sim, Gateway, simulator step, IK, collision query, or motion ran.
