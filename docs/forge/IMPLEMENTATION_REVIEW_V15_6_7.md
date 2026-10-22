# Implementation Review v15.6.7: Observation-to-HTTP No-Motion Evidence Chain

Date: 2026-10-22 (Asia/Shanghai)

## Findings and Disposition

No Blocker or Major finding remains in this bounded test change. The test now
exercises the real module boundaries used by the deployment path:

```text
IsaacCameraObservationSource
  -> ObservationEndpoint
  -> FilesystemObservationArtifactWriter
  -> LocalFilesystemArtifactResolver
  -> HttpJsonInferenceFactory / local TCP HTTP service
  -> SceneUnderstandingEndpoint
```

The test uses a synthetic one-pixel camera and a process-local HTTP server. It
is therefore evidence that artifact bytes, media type, observation identity,
frame, calibration reference, scene revision, and response provenance survive
the provider-neutral transport boundary. It is not evidence of a live Isaac
sensor, model accuracy, calibrated geometry, or physical execution.

## PAOS Architecture and Ownership

- `ObservationEndpoint` owns the public observation contract and freshness
  projection; the test does not call the camera source as a substitute for it.
- `FilesystemObservationArtifactWriter` and `LocalFilesystemArtifactResolver`
  own persistence and opaque artifact resolution; HTTP receives bytes, not
  local filesystem paths.
- The deployment package owns HTTP transport and configuration. Core owns the
  inference registry and `scene.understand` validation.
- The local server returns an entity whose provenance references the submitted
  observation artifact. `SceneUnderstandingEndpoint` remains the authority that
  accepts or rejects that response.
- AgentLoop, SubtaskExecutor, acquire/process/place ordering, and settlement
  ownership are unchanged. No model turn or Action is introduced.

## Extensibility and Developer Guide Review

The test uses the generic `ObservationSource`, artifact writer/resolver, and
inference factory protocols. No vendor, environment name, USD path, model name,
or actuator dependency was added to Core. A second inference implementation
can replace `HttpJsonInferenceFactory` without changing the test's PAOS Query
shape; the local HTTP server is only a transport fixture.

Failure behavior remains fail-closed in the exercised path: missing artifacts,
invalid observation bindings, stale input, HTTP transport errors, and invalid
response shapes are handled by existing provider/endpoint contracts. This
change adds no hash, baseline, or speculative gate.

## AgentLoop Review

`scene.understand` remains a Query. The test invokes it once after observation
capture and does not create a plan node, Runtime Action, subtask settlement, or
re-planning turn. The existing rule remains intact: multiple internal tools may
execute inside one governed subtask, while Agent settlement occurs only at the
subtask boundary.

## Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/scene-understanding-http/src:examples/forge-adapters/isaacsim_lab/src pytest -q examples/forge-adapters/scene-understanding-http/tests`: `11 passed`.
- `ruff check examples/forge-adapters/scene-understanding-http`: passed.
- `python -m compileall -q examples/forge-adapters/scene-understanding-http/src examples/forge-adapters/scene-understanding-http/tests examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/observation.py`: passed.
- `git diff --check`: passed.
- The test starts only a loopback TCP fixture and uses synthetic RGB data. No
  Isaac Sim, Gateway Action, simulator step, IK, collision query, robot, or
  hardware IO was started.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Sensor-to-inference transport and provenance are exercised; no live model or labeled-scene accuracy evidence. |
| 2. Binding and freshness | Pass (no-motion contract) | `ObservationEndpoint` and `SceneUnderstandingEndpoint` carry matching observation ref, scene revision, frame, calibration, freshness, artifact media type, and provenance. |
| 3. Agent subtask granularity | Pass (unchanged) | Query-only test; no AgentLoop turn or settlement boundary changed. |
| 4. IK, workspace, collision | Not verified | No planner or simulator execution ran. |
| 5. Grasp, hold, place state | Not verified | No Action or physical transition ran. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback ran. |
| 7. Subtask settlement and recovery | Partial | Existing governed boundary is preserved; no live multi-tool recovery or process restart was exercised. |

## Overall Decision

This phase is accepted as a provider-neutral, no-motion transport and evidence
lineage regression. It does not complete the LabUtopia/PAOS experiment. Live
camera session wiring, real inference evaluation, measured grasp preparation,
IK/workspace/collision checks, acquire/place execution, pour/stir feedback, and
subtask recovery remain required before the complete plan can be accepted.
