# Implementation Review v15.6.6: Vendor-Neutral HTTP Inference Adapter

Date: 2026-10-22 (Asia/Shanghai)

## Findings and Disposition

This phase adds an optional deployment package, `paos-scene-understanding-http`,
that registers `HttpJsonInferenceFactory` through the existing
`paos.scene_understanding_inference` entry-point group. The adapter transports
PAOS Query fields and resolved observation artifacts to a deployment-configured
HTTP/JSON service. It does not select a model vendor, interpret a simulator
scene, own credentials beyond reading a deployment-selected token variable, or
authorize execution.

Binary artifact bytes are encoded as `data_base64`; provenance and observation
fields remain ordinary JSON fields. HTTP status, transport, and JSON-shape
errors propagate. The adapter never converts a failed request into an empty
scene or a successful Query.

## PAOS Architecture, Extension, Developer Guide, and AgentLoop

- Core owns the factory protocol, registry, artifact resolver, and Query validation.
- The deployment package owns HTTP transport, endpoint/timeout/header settings,
  and the server-side model contract.
- The adapter has no Isaac Sim, LabUtopia, USD, robot, OpenAI, GPT, or actuator import.
- `scene.understand` remains a Query. AgentLoop and SubtaskExecutor are unchanged;
  no model turn or settlement is introduced between acquire/process/place.
- Configuration errors and unavailable credentials fail before inference creation;
  transport and response errors remain visible to the Query caller.

## Validation

- Adapter, registry, and artifact-understanding no-motion tests: `19 passed`.
- Ruff, compileall, and `git diff --check` pass.
- Package metadata test verifies the installable `http_json` entry point.
- No live HTTP service, model, camera, Isaac Sim, Gateway Action, IK, collision
  query, or motion was run.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Adapter preserves a replaceable inference boundary; no real model/labeled-scene accuracy evidence. |
| 2. Binding and freshness | Pass (contract) | Existing PAOS endpoint validates provenance/revision/frame/freshness; no live sensor chain. |
| 3. Agent subtask granularity | Pass (unchanged) | Adapter is a Query provider; AgentLoop and subtask settlement are untouched. |
| 4. IK, workspace, collision | Not verified | No planner or simulator checks ran. |
| 5. Grasp, hold, place state | Not verified | No action or physical transition ran. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback ran. |
| 7. Subtask settlement and recovery | Partial | Existing boundary remains; no live multi-tool task/recovery ran. |

## Overall Decision

The deployment extension point is now installable and vendor-neutral. This
does not complete the LabUtopia experiment: the service endpoint must still be
deployed and evaluated on captured camera artifacts before measured bindings,
grasp preparation, IK/collision, and real pour/stir execution can be accepted.
