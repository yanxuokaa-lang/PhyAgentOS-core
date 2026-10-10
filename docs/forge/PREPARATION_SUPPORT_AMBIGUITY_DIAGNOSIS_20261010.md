# Preparation Support Ambiguity Diagnosis (2026-10-10)

## Scope

This diagnosis covers the failed `green_prepare` node in AgentTask
`task_041adca140584fcb`, revision `revision_e54c022a27174aa0`. The repair is
provider-neutral: it changes observed support geometry resolution and the
Agent recovery transition for explicitly re-plannable Query evidence failures.
It does not add RGB, color, object-class, task-name, Tool-ID, or provider-specific
branches.

## Evidence

The Coordinator decision trace
`artifacts/planning-traces/task_041adca140584fcb/revision_e54c022a27174aa0/green_prepare/e34815756b7b43df.json`
shows that `manipulation.prepare` was selected with the frozen entity
`entity://e2`, current scene `1d2608e7ac4948b7830bdf56d7b083d4-3`, the current
binding, 32 candidates, a same-scene capability snapshot, and the destination
injected into the node by `task.goal`. This rules out an Agent-authored target,
missing selection, or stale candidate/target projection as the recorded cause.

The Runtime metric
`/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/preparation-metrics/564a28947e524fa1a4a3c5d361e7a150.json`
records:

- Provider failure after `0.034044569940306246` seconds: `ValueError: observed support surface is ambiguous`.
- `candidate_count=32`, `action_count=0`, `simulator_steps=0`, `motion_authorized=false`.
- The error occurred while resolving support geometry, before a route could be selected or any Action admitted.

The scene-understanding evidence for that post-placement observation represented
one visible support geometry through multiple semantic entities (`e4`, `e5`,
`e6`), each with a full-frame mask and identical metric localization bounds and
point counts. The semantic `on` relations therefore yielded multiple refs even
though their metric geometry described the same observed surface. In other
cases, multiple refs can genuinely refer to distinct surfaces; those remain
ambiguous and must not be merged.

## Root Cause

`Grounding._observed_support()` assumed that one semantic `on` target must map
to exactly one support entity. Multiple refs raised ordinary `ValueError`.
`PersistentPreparationProvider.prepare()` preserves declared
`PreparationProviderError` diagnostics, but does not reinterpret arbitrary
geometry exceptions. The Core `ManipulationPreparationEndpoint` then
intentionally redacted an unclassified exception as generic
`preparation_provider_error`, `failure_owner=runtime_adapter`,
`requires_replan=false`, and `recommended_action=fix_runtime_contract`.

The generic exception redaction is appropriate for unknown adapter defects, but
the support resolver had enough domain evidence to classify this case as an
evidence ambiguity. Losing that ownership prevented the Agent recovery loop
from distinguishing refreshable scene evidence from a code/configuration fault.

## Repair

1. Resolve every semantic support ref against exactly one current, same-scene,
   same-calibration, same-frame metric point cloud.
2. Treat refs as aliases only when the loaded metric point arrays are exactly
   equal. Keep every source artifact ref in `source_refs`; choose the canonical
   evidence ref by sorted semantic ref order for deterministic output.
3. Reject missing, stale, invalid, or distinct metric geometries with
   `PreparationProviderError(code="observed_support_unavailable",
   failure_owner="evidence", requires_replan=true,
   recommended_action="refresh_declared_evidence")`.
4. When the failed execution is a Query whose structured result explicitly has
   this evidence owner/replan/recommended-action tuple, AgentRecoveryDecisions
   selects a deterministic replacement revision with one ToolSpec-owned scene
   refresh Query. The failed preparation is not retried automatically, and no
   Action is proposed in that bootstrap revision.
5. After refresh, the normal Agent loop and Coordinator use the newly persisted
   observation/understanding/selection evidence to decide what can continue.
   No evidence token is invented, and the failed Query's old evidence is not
   treated as a new observation.

The refresh Query remains a normal selected Tool invocation under Coordinator
and Runtime readiness/admission. Existing Action authorization, Gateway
admission, candidate binding, and terminal settlement checks are unchanged.

## Seven-Dimension Review

- **Architecture:** support deduplication stays in the observation-owning
  RobotWin Grounding adapter; generic Query recovery stays in Core
  `AgentRecoveryDecisions`. No parallel recovery loop or provider API was added.
- **Correctness:** only exact metric-array equality permits semantic alias
  collapse. Distinct geometry, incomplete cloud sets, or lineage mismatch are
  explicit evidence failures.
- **Recovery and idempotency:** the replacement starts with one deterministic
  scene-refresh node ID derived from the source revision; it does not replay
  `manipulation.prepare` or any Action. Existing node-collision handling remains
  in force.
- **Robotics safety:** preparation remains Query-only and returns
  `motion_authorized=false`; tests exercise no Gateway Action, simulator step,
  camera, or robot motion.
- **Extension compatibility:** no RGB/color/task/provider/Tool-specific branch
  was introduced. Other Queries opt into the same recovery path only by
  returning the existing explicit evidence-recovery fields.
- **Observability and maintainability:** the public error retains the scene,
  frame, calibration, preparation, and candidate-set lineage; low-level file
  errors are not exposed. Alias source artifact refs remain auditable.
- **AgentLoop autonomy:** explicitly refreshable Query evidence failure routes
  through the persisted recovery lifecycle. If no uniquely declared
  scene-refresh Query is available, the existing model-proposed path remains
  fail-closed; no Tool or Action is guessed.

## Validation Boundary

Unit and contract tests use temporary evidence files and in-memory coordinator
fixtures only. No live AgentTask, Runtime Query/Action, camera, simulator, or
physical motion is run by these tests. A future live retry requires normal
operator task creation and Runtime readiness; this repair does not resume the
failed task automatically.
