# Implementation Review v15.5.15: Persistent Runtime Provider Composition

Date: 2026-10-22 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Findings and disposition

No Blocker or Major findings remain for the runtime composition change. A Major blocker remains for full plan acceptance: the deployment still has to supply a real inference implementation and resolver configured for the artifact store shared with the observation worker.

- `build_persistent_runtime` now supports two explicit forms: the existing complete `understanding_provider`, or `understanding_artifact_resolver` plus `understanding_inference`. It rejects missing and mixed composition inputs.
- Runtime tests invoke the registered `scene.understand` Query through the composed provider and verify resolved image bytes/media type arrive at inference and a valid claim is projected by the PAOS endpoint.
- Existing provider-based callers remain source-compatible; no LabUtopia-specific class, model config, artifact path, or sensor name entered the reusable workflow package.
- The resolver and inference remain caller-owned dependencies. This runtime seam does not invent deployment configuration or claim a live model is installed.

## PAOS architecture, extensibility, Developer Guide, and AgentLoop

- **Ownership:** the workflow runtime owns endpoint composition; resolver owns storage access; inference owns semantic claims; the PAOS endpoint validates claims and provenance.
- **Dependency direction:** the generic workflow composes only the generic provider port. It does not import an adapter or environment.
- **Replaceability:** existing complete providers continue to work; a different resolver or inference can be substituted without changing ToolSpec or the AgentLoop.
- **AgentLoop:** unchanged. `scene.understand` remains one Query within the existing task flow; composition adds no Agent/model turn, PlanNode, or settlement.
- **Failure behavior:** incomplete or mixed configuration fails at runtime construction; unavailable artifacts/inference continue to fail through the provider and PAOS endpoint path.
- **Anti-OverDefense:** composition has only explicit missing/mutually-exclusive input validation; no extra hash, registry, version lock, or generic gate was added.
- **Robotics safety:** this is runtime Query wiring only. No sensor capture, target transform, IK, collision, Action, simulator, Gateway, or motion was run.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Partial | Runtime carries resolved artifact bytes to injected inference; only fixtures were used, not a live model/camera. |
| 2. Binding and freshness | Partial | PAOS Query freshness/provenance validation remains active; a deployment has not connected the real shared artifact store through to measured binding. |
| 3. Agent task granularity | Partial | Runtime composition does not alter AgentLoop; no full multi-tool semantic subtask was executed. |
| 4. IK, workspace, collision | Not verified | No kinematic or collision query ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator state transition ran. |
| 6. Process feedback | Not verified | No pour/stir feedback was captured. |
| 7. Subtask settlement/recovery | Partial | Existing subtask executor is unchanged; no live multi-tool settlement/recovery was run. |

Overall plan acceptance: **not accepted**. Next: configure a real inference implementation and shared resolver in a deployment entrypoint, then validate real observation-to-binding, candidate/preparation, and task-level settlement before any separately authorized simulation execution.

## Validation

- Focused provider/runtime tests: `54 passed`.
- Full pick-place workflow + artifact tests: `596 passed, 2 failed`. The two failures are Robotwin release assertions: a workspace node version differs from the fixture's expected `1.0.15`, and the source-build digest differs from the manifest lock. The worktree already contains unrelated modified/untracked Robotwin files; they were not changed or staged in this phase.
- Ruff, compileall, and `git diff --check`: passed.
- No Isaac Sim, Gateway, simulator step, IK, collision query, or motion ran.
