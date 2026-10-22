# Implementation Review v15.6.5: Registry-Backed Runtime Composition

Date: 2026-10-22 (Asia/Shanghai)

## Findings and Disposition

The registry from v15.6.4 was not yet usable through the normal persistent-runtime composition. This phase adds a provider-neutral selection path to `build_persistent_runtime`: a host may pass an artifact resolver, an inference registry, an inference ID, and optional deployment configuration. The runtime composes the selected inference with the existing artifact-resolving provider before registering `scene.understand`.

LabUtopia only forwards those generic composition values. It does not import a model vendor, define a lab-specific perception adapter, interpret model configuration, or use a scene path as inference input. Its local resolver is created only when a complete direct inference or registry selection is present and an explicit observation artifact root was supplied.

## PAOS Architecture, Extension, Developer Guide, and AgentLoop

- Domain ownership remains in PAOS: `scene.understand` Query semantics and validation remain in `SceneUnderstandingEndpoint`.
- Inference mechanisms and configuration remain deployment-owned and enter through `SceneUnderstandingInferenceRegistry`.
- The workflow package composes the provider; it does not add an Agent-facing Tool or change task/settlement ownership.
- The LabUtopia adapter forwards the resolver, registry, ID, and configuration without branching on provider IDs.
- No AgentLoop code changed. Observation and understanding remain pre-subtask Queries; acquire/process/place are still governed by the existing single subtask settlement boundary.
- Incomplete or mixed composition forms fail before Tool registration. Missing local artifact root fails before the resolver is created.
- No extra hash, model-vendor gate, or environment-specific contract was introduced.

## Validation

- Persistent-runtime, LabUtopia integration, and inference-registry suites: `55 passed`.
- Ruff, compileall, and `git diff --check` pass.
- The no-motion test confirms the selected factory receives deployment configuration, inference receives resolved image bytes, and the existing PAOS Query returns the normalized result.
- No live model, real camera, Isaac Sim process, Gateway Action, IK, collision query, or motion was run.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Registry-selected providers are replaceable; fixtures do not establish labeled-scene accuracy. |
| 2. Binding and freshness | Pass (no-motion contract) | Existing Query endpoint still validates provenance/revision/frame/freshness; no live sensor chain. |
| 3. Agent subtask granularity | Pass (unchanged) | Runtime only adds Query composition; AgentLoop and subtask settlement are unchanged. |
| 4. IK, workspace, collision | Not verified | No planner/simulator checks ran. |
| 5. Grasp, hold, place state | Not verified | No action or physical transition ran. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured process feedback ran. |
| 7. Subtask settlement and recovery | Partial | Existing boundary remains unchanged; no live multi-tool task/recovery ran. |

## Overall Decision

The generic runtime can now compose a deployment-selected inference without model-vendor or environment-specific code in PAOS Core, the workflow runtime, or LabUtopia wiring. This is a contract/wiring milestone, not acceptance of the complete LabUtopia task. The next phase must provide one installable deployment-owned inference factory through the entry-point group, then validate it against captured labeled observations before geometric grasp/preparation or motion work.
