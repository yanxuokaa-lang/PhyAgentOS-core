# Implementation Review v15.6.2: Deployment-Configured GPT Scene Understanding

Date: 2026-10-22 (Asia/Shanghai)

## Review Findings

One integration finding was corrected in this phase: the PAOS understanding endpoint reads `provider_error_class` and `provider_error_code` from provider exceptions. The initial provider exposed only `code`, which would have dropped the failure classification. The exception now supplies the PAOS fields, and RGB inference rejects metric spatial claims rather than allowing a language model to fabricate geometry.

## Architecture Review

- The provider is in `PhyAgentOS/forge/capability_runtime`, behind the existing `SceneUnderstandingProvider` and `ArtifactResolver` interfaces.
- Deployment owns `api_base`, GPT model name, credential environment variable, timeout, and resolver. There is no LabUtopia-specific model class or configuration dependency in PAOS Core.
- The provider consumes image artifacts only. GPT contributes visible semantic entities/relations; metric geometry, localization, grasp candidates, readiness, IK, collision checks, and motion remain separate capabilities.
- The existing `SceneUnderstandingEndpoint` remains responsible for validating entity IDs, source-artifact provenance, relation consistency, observation freshness, scene revision, frame, and calibration.
- AgentLoop and the subtask execution/settlement boundary are unchanged. Scene understanding remains a Query prerequisite; it does not cause a model turn between internal manipulation Tools.

## Developer Guide and Extension Review

This is a reusable provider implementation, not a new environment adapter. A deployment may select a GPT-compatible Responses endpoint or replace this provider with another `SceneUnderstandingProvider`; PAOS ToolSpec, task model, and AgentLoop do not change. Model/provider replacement is configuration or composition work. No environment names, USD/Prim fields, object IDs, or actuator APIs enter the generic provider.

No new hashes, frozen contracts, or global gates were added. Configuration is validated where the endpoint/client is constructed; request failures remain Query failures and do not authorize execution.

## Failure Behavior

- Missing API credentials, artifact bytes, image inputs, invalid JSON, and endpoint errors become bounded provider failures; no empty-entity success is synthesized.
- The provider makes one request (`max_retries=0`) so AgentLoop/Coordinator own retry and recovery policy.
- Metric envelopes from RGB inference are rejected. Depth/calibration-derived geometry must come from a separate measured provider and retain source provenance.
- `store=false` is set on the Responses request; the client is closed after each call.

## Validation

- No-motion tests cover artifact-to-image request construction, structured output through the PAOS endpoint, invalid output, missing credential, and metric-claim rejection.
- Focused tests: `24 passed`; Ruff, compileall, and `git diff --check` pass.
- The current environment has no configured GPT API credential and common local inference ports are closed. No live GPT request or live camera observation was run. This phase does not prove model accuracy on LabUtopia labels.
- No Isaac Sim, Gateway Action, simulator step, IK, collision query, or motion was run.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | GPT image-query adapter contract tested; no live API or labeled-scene evaluation. |
| 2. Binding and freshness | Partial | Existing PAOS endpoint validates bindings; no live sensor-to-GPT chain. |
| 3. Agent subtask granularity | Pass (unchanged) | Provider is a Query; AgentLoop/subtask executor is untouched. No full Agent task executed. |
| 4. IK, workspace, collision | Not verified | No planner or simulator checks run. |
| 5. Grasp, hold, place state | Not verified | No action or physical state transition run. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback exercised. |
| 7. Subtask settlement and recovery | Partial | Existing boundary is unchanged; no multi-tool live execution or recovery settlement. |

## Overall Decision

The generic GPT API provider phase passes its code review and no-motion contract tests. The complete LabUtopia plan remains unaccepted. Next, deployment composition must supply the selected GPT API settings and a real shared artifact resolver, then a live camera observation must be evaluated for readable labels and correct entity binding. Real geometric understanding/grasp candidates, preparation, IK/collision, acquire/process/place execution, and one terminal settlement for the full subtask remain outstanding.
