# Implementation Review v15.6.0: Shared Observation Artifact Root

Date: 2026-10-22 (Asia/Shanghai)

## Review Findings

No remaining Blocker or Major finding in this phase.

- The deployment now supplies one explicit observation artifact root. The default Isaac engine passes that root to the isolated worker process; the worker's observation writer writes beneath it.
- When the deployment chooses injected inference without a custom resolver, the PAOS composition builds the existing generic `LocalFilesystemArtifactResolver` over the same explicit root and `labutopia` artifact authority.
- A caller may still inject any `ArtifactResolver`. A caller-supplied engine is responsible for writing to the configured root; the adapter does not reach into an arbitrary engine to mutate its storage configuration.
- No model, semantic policy, sensor identity, scene path, or grasp behavior was added to PAOS Core. The change is environment storage wiring only.
- No new hashes, digests, frozen contracts, or gates were introduced. An explicit root is required only for the local resolver composition because otherwise the reader cannot resolve the worker's opaque artifact refs to bytes.

## Architecture Review

Ownership and dependency flow:

```text
deployment: observation_artifact_root
       |                         |
       v                         v
default Isaac worker       generic local ArtifactResolver
       |                         |
camera ObservationSource         |
       |                         |
Filesystem writer                 |
       +------ artifact:// refs --+
                                  v
                    generic scene.understand provider
                                  v
                       PAOS Query validation
```

The generic resolver remains provider-neutral. The LabUtopia adapter only connects the environment-owned camera artifact writer to a deployment-selected store root. Model selection remains injected. AgentLoop and the one-settlement-per-subtask boundary are unchanged.

## Failure and Safety Behavior

- With no explicit root, the legacy observation writer path remains available for existing deployments; opting into local resolver/inference composition without a root fails before Runtime construction.
- The worker process receives the path only when explicitly configured. Existing deployments without it retain their current path behavior.
- Observation artifacts are still evidence inputs only. No perception output is wired directly to actuation, and `allow_live` remains false by default.
- Frame, calibration, observation, and revision validation remain owned by the existing PAOS endpoints. This phase does not relax them.

## Validation

- No-motion tests verify root propagation through the engine/backend/session/child environment chain.
- Camera stubs write RGB PNG, depth/point-cloud NPY, and calibration JSON beneath the explicit root; the generic resolver reads the returned artifact refs back with matching payloads/media types.
- Runtime composition tests verify that the same explicit root backs `scene.understand` and that incomplete or implicit local-storage composition is rejected.
- Focused Isaac adapter, persistent Runtime, and artifact provider suites: `142 passed`. Ruff, compileall, and `git diff --check` pass. Pytest reports the existing unknown `asyncio_mode` option warning with plugin autoload disabled.
- No Isaac Sim, Gateway, simulator step, IK, collision query, or motion was run.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Artifact bytes reach injected inference; no real model or labeled scene was evaluated. |
| 2. Binding and freshness | Partial | Existing PAOS observation/understanding contracts remain active; no live worker-to-inference observation was run. |
| 3. Agent subtask granularity | Partial | The generic subtask Tool can be registered; no Agent-planned task or settlement was executed. |
| 4. IK, workspace, collision | Not verified | No simulator planner or collision checks ran. |
| 5. Grasp, hold, place state | Not verified | No action or state transition ran. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback was exercised. |
| 7. Subtask settlement and recovery | Partial | Existing executor boundary is unchanged; no multi-tool task, recovery, or single settlement was run. |

## Overall Decision

This storage-wiring phase passes review, but the complete plan remains unaccepted. Remaining work includes a deployed inference provider, live observation-to-understanding evidence, measured grasp/preparation, actual IK/workspace/collision validation, acquire/process/place feedback, and an AgentLoop run that settles once after the full subtask.
