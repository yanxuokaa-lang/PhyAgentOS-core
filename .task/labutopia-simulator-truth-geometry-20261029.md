# Current Task: LabUtopia simulator-truth spatial geometry

- Task ID: `labutopia-simulator-truth-geometry-20261029`
- Goal: derive simulator-truth spatial envelopes and visible point clouds from final composed USD geometry through the existing PAOS observation and understanding path; keep AgentLoop and public PAOS contracts unchanged.
- Tier: `C-Safety`
- Risk dimensions: `architecture-sensitive`, `cross-module-contract-sensitive`, `runtime-sensor-sensitive`, `safety-sensitive`, `test-sensitive`, `bug/debugging`
- Owner layer: Isaac Lab Adapter observation capture and simulator-truth perception Provider.
- Public-interface impact: none; reuse observation artifact kind `state` and existing `scene.understand` envelope fields.
- AgentLoop impact: none; task planning, binding policy, lifecycle, cancellation and settlement remain PAOS-owned and unchanged.
- Evidence source: final composed USD world bounds captured in the same paused scene revision, plus same-capture RGB-D artifacts.
- Stop conditions: missing/invalid prim, empty/non-finite bounds, scene/capture mismatch, missing state artifact, or insufficient visible points; no guessed bounds and no automatic motion fallback.
- Validation: provider and endpoint tests, observation-source state artifact tests, Adapter/AgentLoop contract regression, Ruff, compileall and diff check. Runtime acceptance only after implementation tests; any live run must stop before motion if binding/preparation is not qualified.
- Existing `.task/current.md` is preserved because it records a separate planning task and explicitly forbids provider changes; this task-specific document records the newer user-authorized scope.

## Architecture Review

- Generic domain layer: unchanged; consumes the existing entity, provenance, frame and spatial-envelope semantics.
- Provider/Adapter: Isaac Adapter captures final USD world bounds as a simulator-state artifact; simulator-truth Provider associates that state with labels and same-capture visible point-cloud samples.
- Replacement: other perception Providers and non-Isaac observation sources remain unaffected; standard visual mode does not request simulator state.
- Evidence freshness: state and camera artifacts are emitted by one observation request and carry the same frame and scene revision.
- Lifecycle owner: existing AgentTaskCoordinator/Runtime; no new task, scheduler or settlement state.
- Smallest leak test: assert the public understanding endpoint accepts the truth envelope while no USD prim path appears in public claims and a non-truth provider remains unchanged.

## Review Addendum (before follow-up edits)

- Concrete unsafe case: the final-USD AABB and point cloud can be current while the manifest's `origin_world`, `tip_world`, `axis_world`, and `size_m` remain stale. `LabVisualPerception.resolve()` accepts the `simulator_ground_truth` qualification and converts those fields into object, tool, and process frames, allowing incorrect preparation despite correct binding geometry.
- Existing `resolve()` checks do not close this case because they validate presence and a broad geometry qualification, not provenance/freshness of process landmarks. A focused regression must prove simulator-truth spatial evidence cannot be mistaken for process-feature evidence.
- Planned correction: keep current AABB-derived envelope and visible-point-cloud Query evidence, but set simulator-truth process features unavailable until derived from final composed geometry; verify preparation rejects the missing feature evidence before execution. No motion or AgentLoop/public contract changes.

## Failure Scenario and Rationale

The concrete failure is that `simulator_truth` identifies entities but emits no spatial envelopes, so PAOS correctly rejects selected entities before preparation. Ordinary tests had asserted the empty list rather than detecting that the production truth Provider could not satisfy the existing binding contract. Git history and versions cannot prevent this functional omission; a focused endpoint regression is sufficient. No hashes, frozen contracts or new gates are added.
