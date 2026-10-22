# Implementation Review v15.6.4: Provider-Neutral Inference Discovery

Date: 2026-10-22 (Asia/Shanghai)

## Findings and Disposition

The previous correction removed the vendor-specific provider from PAOS Core. This phase adds only the missing deployment extension point: `SceneUnderstandingInferenceRegistry` discovers factories through `paos.scene_understanding_inference`, validates their `inference_id` and `infer(request)` contract, copies deployment configuration, and composes the selected implementation with the existing generic artifact resolver.

No model SDK, API request schema, credential lookup, environment name, USD path, camera handle, grasp logic, actuator, or process controller appears in Core. A GPT-compatible implementation, a local model, or another service can be installed as separate entry points and selected by deployment configuration.

## Architecture / Extension / AgentLoop Review

- PAOS Core owns the stable `SceneUnderstandingInferenceFactory` protocol, registry, and artifact composition.
- The deployment owns entry-point package installation, provider configuration, lifecycle, credentials, and model-specific failure mapping.
- The registry does not authorize motion or register an Action. `scene.understand` remains a Query and is still validated by the existing PAOS endpoint.
- AgentLoop and `SubtaskExecutor` are unchanged. Discovery/configuration happens before a subtask; internal acquire/process/place Tools still settle once at subtask boundary.
- Unknown IDs, duplicate IDs, invalid factories, and invalid inference objects fail before Query composition. No fake empty result is generated.

## Validation

- `tests/test_scene_understanding_inference_registry.py` uses two distinct inference factories through the same registry and generic artifact provider, plus invalid/duplicate/unknown cases.
- Combined generic artifact, registry, and workflow understanding tests: `55 passed`.
- Ruff, compileall, and `git diff --check` pass.
- No live model, camera, Isaac Sim, Gateway Action, IK, collision query, or motion was run.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Two replaceable inference implementations pass the contract; no live model or labeled-scene evaluation. |
| 2. Binding and freshness | Pass (no-motion contract) | Existing PAOS endpoint validates artifact provenance and observation binding; no live sensor chain. |
| 3. Agent subtask granularity | Pass (unchanged) | Registry is a pre-query composition utility; AgentLoop/subtask executor unchanged. |
| 4. IK, workspace, collision | Not verified | No planner or simulator checks run. |
| 5. Grasp, hold, place state | Not verified | No action or physical transition run. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback run. |
| 7. Subtask settlement and recovery | Partial | Existing boundary remains intact; no live multi-tool task or recovery was run. |

## Overall Decision

The provider discovery boundary passes review and is reusable across environments and model vendors. The complete LabUtopia plan remains unaccepted. The next deployment step is to install one concrete inference factory, connect it to the LabUtopia observation artifact root, and run a live observation-to-understanding evaluation before geometric grasp/preparation and physical execution are considered.
