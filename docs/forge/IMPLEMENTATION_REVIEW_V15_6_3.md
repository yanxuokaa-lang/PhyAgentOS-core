# Implementation Review v15.6.3: Keep Model Vendors Outside PAOS Core

Date: 2026-10-22 (Asia/Shanghai)

## Finding and Correction

The previous phase placed an OpenAI Responses implementation in `PhyAgentOS/forge/capability_runtime`. Although endpoint, model, and credentials were configurable, the SDK, request format, and provider identity remained vendor-specific code in Core. Configuration does not make a vendor-specific implementation provider-neutral.

This phase removes that implementation and its Core exports. PAOS retains the existing `ArtifactResolvingSceneUnderstandingProvider`, `SceneUnderstandingInference` protocol, `ArtifactResolver`, and `SceneUnderstandingProvider` port. A GPT/OpenAI deployment must implement the inference protocol in its deployment/adapter package and inject it; other providers use the same composition without changing PAOS Core.

## Architecture Review

- Dependency direction is corrected: Core defines stable data contracts and composes artifact resolution with an injected inference mechanism; deployment code owns provider SDKs, API formats, credentials, retries, and model configuration.
- The generic wrapper remains unaware of models, vendors, environments, cameras, USD, and actuators.
- The PAOS `SceneUnderstandingEndpoint` still validates observation identity, freshness, scene revision, frame, calibration, claim shape, and provenance.
- AgentLoop and subtask execution/settlement are unchanged. There is no model turn between internal subtask Tools.
- No additional schema gate, hash, or new abstraction was introduced; existing generic ports and tests establish the replacement boundary.

## Validation

- Existing generic artifact-understanding tests use two distinct injected inference implementations through the same wrapper and PAOS Query endpoint.
- `tests/test_forge_artifact_understanding.py`, `tests/test_forge_artifacts.py`, and workflow `test_scene_understand.py`: `52 passed`.
- Ruff, compileall, and `git diff --check` pass.
- No live model, camera, Isaac Sim, IK, collision query, Gateway Action, or motion was run.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Vendor-neutral inference seam is tested; no live model or labeled-scene quality evidence. |
| 2. Binding and freshness | Pass (no-motion contract) | Existing PAOS endpoint tests bind claims to observation artifacts and freshness metadata; no live sensor chain. |
| 3. Agent subtask granularity | Pass (unchanged) | AgentLoop/subtask executor was not modified; no full Agent task executed. |
| 4. IK, workspace, collision | Not verified | No planner or simulator checks run. |
| 5. Grasp, hold, place state | Not verified | No action or physical state transition run. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback exercised. |
| 7. Subtask settlement and recovery | Partial | Existing boundary is unchanged; no multi-tool task or recovery was run. |

## Overall Decision

The vendor-bound Core implementation has been removed and the generic composition boundary passes review. The full LabUtopia plan remains unaccepted. The deployment still needs to supply its GPT-compatible inference implementation/configuration and run a real observation-to-understanding evaluation, followed by measured geometry/grasp preparation, IK/collision checks, acquire-process-place execution, and one terminal subtask settlement.
