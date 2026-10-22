# Implementation Review v15.5.16: Lab Runtime Artifact Understanding Composition

Date: 2026-10-22 (Asia/Shanghai)

## Review Findings

No remaining Blocker or Major finding in this phase.

- The deployment composition now accepts either the existing complete understanding provider or the generic artifact resolver plus injected inference supported by `build_persistent_runtime`.
- A complete resolver/inference pair counts as understanding readiness for provider-neutral perception binding. An incomplete pair is rejected by the existing generic runtime builder before tool registration.
- The adapter does not select an artifact root, model, vendor SDK, or semantic policy. The deployment owns resolver construction and storage mapping.
- The Agent-facing `manipulation.execute_subtask` registration rule remains unchanged apart from recognizing the second valid understanding composition. AgentLoop and settlement code are untouched.
- No new hash, digest, frozen contract, or gate was introduced. This phase adds only the wiring and tests required to expose the existing generic composition through the production host builder.

## Architecture Review

The dependency direction is preserved:

```text
deployment-owned ArtifactResolver + inference
                    |
                    v
build_labutopia_runtime -> build_persistent_runtime
                    |
                    v
generic ArtifactResolvingSceneUnderstandingProvider
                    |
                    v
PAOS scene.understand Query validation
```

LabUtopia remains an environment execution adapter. It neither implements scene understanding nor silently derives the artifact root from `profile.lab_root`. The deployment must pass an explicit resolver whose authority mapping can point at the observation writer's storage. This keeps local filesystem, object storage, remote artifact service, and model implementation replaceable without changing PAOS contracts.

## Validation

- No-motion integration fixture writes bytes under a temporary deployment-owned root, resolves `artifact://labutopia/front.png`, and verifies the injected inference receives those exact bytes and `image/png` media type.
- The same test verifies that complete generic composition makes the subtask Tool eligible for registration.
- Incomplete resolver/inference combinations are rejected; existing provider-based composition remains covered by the adapter and workflow suites.
- `139 passed`; Ruff, compileall, and `git diff --check` pass. Pytest reports the existing unknown `asyncio_mode` option warning with plugin autoload disabled.
- No Isaac Sim, Gateway, simulator step, IK, collision query, or motion was run.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Real artifact bytes reach injected inference; no deployed recognition model or labeled-scene result was run. |
| 2. Binding and freshness | Partial | Existing PAOS Query validates observation/frame/calibration/revision fields; a live Isaac observation-to-understanding run is not verified here. |
| 3. Agent subtask granularity | Partial | No AgentLoop code changed; composition can register the subtask Tool, but no complete Agent-planned task was executed. |
| 4. IK, workspace, collision | Not verified | No simulator planner or collision checks ran. |
| 5. Grasp, hold, place state | Not verified | No action or physical/simulated state transition ran. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback was exercised. |
| 7. Subtask settlement and recovery | Partial | Existing governed executor remains in place and is reachable in composition; no multi-tool execution/recovery or single settlement was run in this phase. |

## Overall Decision

This phase passes its implementation review, but the complete LabUtopia-to-PAOS plan is not accepted. Remaining evidence must include a deployment-owned resolver backed by the actual worker observation artifact store, a real scene-understanding provider, measured grasp/preparation results, simulator IK/workspace/collision checks, acquire/process/place feedback, and one Agent settlement at the subtask boundary.
