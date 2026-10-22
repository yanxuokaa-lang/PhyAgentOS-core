# Implementation Review v15.5.13: RGB Observation Media

Date: 2026-10-22 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Findings and disposition

No Blocker or Major findings remain for this bounded observation-media change.

- Isaac RGB artifacts are now PNG (`image/png`); depth and point-cloud artifacts remain NPY (`application/x-npy`), and calibration remains JSON.
- The writer preserves uint8 RGB pixels and converts finite floating RGB values in `[0, 1]` to uint8. Unsupported image shape/range fails explicitly instead of clipping or silently reinterpreting values.
- Pillow is declared by the Isaac adapter because the adapter owns conversion from its sensor array to image bytes.
- The Core `ArtifactResolver` contract and payload are unchanged. No model, adapter-specific understanding class, fixed object identity, or AgentLoop behavior was added.
- Compatibility note: a downstream consumer that ignored artifact `media_type` and assumed NPY for RGB must switch to media-type-aware decoding. The PAOS observation response already carries the actual media type.

## PAOS architecture, extensibility, and Developer Guide

- **Ownership:** the Isaac sensor adapter owns representation of camera sensor output; Core continues to resolve opaque artifact refs to bytes plus media type.
- **Dependency direction:** only the adapter imports Pillow. Core and workflow do not acquire Isaac or LabUtopia dependencies.
- **Replaceability:** alternate sensor adapters can emit any image media type and use the same artifact resolver/provider interfaces; this change does not bind PAOS to PNG as its public abstraction.
- **AgentLoop:** unchanged. Observation artifacts are inputs to an existing understanding Query and do not create a model turn, Tool receipt, or settlement.
- **Failure behavior:** malformed RGB shape/range raises at the writer boundary; it is not persisted or promoted to an available observation.
- **Anti-OverDefense:** range checks address lossy reinterpretation of floating camera output. No hash, frozen schema, general gate, or duplicate provenance mechanism was added.
- **Robotics safety:** no target, calibration transform, IK, collision, actuator, or execution path changed. No Isaac Sim, Gateway, or motion was run.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Partial | Live Isaac camera writer emits consumable PNG refs in no-motion API-stub tests; no live capture or semantic perception was run. |
| 2. Binding and freshness | Partial | Media type and bytes preserve the artifact reference; observation-to-understanding binding lineage is not yet wired in deployment composition. |
| 3. Agent task granularity | Partial, unchanged | No AgentLoop changes; this phase did not execute a subtask. |
| 4. IK, workspace, collision | Not verified | No kinematic or collision query ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator state transition ran. |
| 6. Process feedback | Not verified | No pour/stir feedback was captured. |
| 7. Subtask settlement/recovery | Partial, unchanged | No multi-tool LabUtopia task or live settlement/recovery was run. |

Overall plan acceptance: **not accepted**. The next implementation boundary is deployment-owned semantic provider composition consuming resolved observation artifacts, followed by provider-neutral binding tests and a second-provider replacement test. Actual simulation task acceptance remains a later, separately authorized stage.

## Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src pytest -q examples/forge-adapters/isaacsim_lab/tests`: `82 passed`.
- `ruff check` for the changed adapter source and tests: passed.
- `python -m compileall -q examples/forge-adapters/isaacsim_lab/src/isaacsim_lab`: passed.
- `git diff --check`: passed.
- Pytest reports the existing unknown `asyncio_mode` option warning with plugin autoload disabled. No Isaac Sim, Gateway, simulator step, IK, collision query, or motion ran.
