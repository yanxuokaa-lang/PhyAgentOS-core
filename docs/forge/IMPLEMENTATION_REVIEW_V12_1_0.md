# v12.1.0 Settlement Reconciliation and Place Postcondition Review

Date: 2026-09-29. Scope is source-level and Fake Gateway/no-motion only; no live Runtime, simulator, or hardware execution was performed.

## Findings and dispositions

1. **Blocker fixed: late terminal results could not resolve an audited unknown.** `AgentTaskCoordinator` now preserves the original `outcome_unknown` settlement, appends `node_settlement_resolved`, and exposes an effective reducer. Resolution requires the same task, revision, node, and invocation plus a known terminal `succeeded|failed` result. No arbitrary status mutation or second state store was added.

2. **Major fixed: unknown invocations were skipped and recovery could remain blocked.** `reconcile_nonterminal()` now GETs persisted unknown invocations, never POSTs them, and routes reads through the frozen task Gateway binding. A known terminal result resumes `executing` and wakes the existing LongHorizon controller through its callback seam.

3. **Major fixed: place success was under-specified.** `object.place` now rejects success unless release confirmation, retreat completion, target clearance, observation readiness, a new scene revision, and complete post-release evidence are present. Exact return-to-start pose is not a PAOS core condition.

4. **Major fixed: continuation could advance from stale settlement projections.** PlanningLoop, NodeContextProvider, continuation, finalization, replay, and LongHorizon replay use the Coordinator effective reducer. Continuation guidance requires fresh observe -> understand -> capabilities -> bind before the next segment.

## Seven dimensions

| Dimension | Result |
|---|---|
| Architecture integration | PASS. Coordinator remains the sole task/revision/event authority; Agent tools remain wrappers; no parallel scheduler, watchdog, Gateway, or state store. |
| Recovery and idempotency | PASS. Unknown reads are GET-only and identity-bound; resolution is append-only and idempotent; no Action replay is introduced. |
| Robotics safety | PASS. Place remains Gateway-admitted and provider-neutral; no motion code changed. Missing release/retreat/clearance/observation evidence fails closed. |
| Configuration and reproducibility | PASS. No new runtime path, profile, device, or hardware setting was hard-coded. Validation uses Fake Gateway/no-motion fixtures. |
| Maintainability | PASS. Effective settlement is a thin Coordinator reducer; frozen Gateway binding is reused for reads; continuation uses the existing controller and PlanningLoop seams. |
| Observability | PASS. Original unknown audit facts remain queryable; resolution events carry task/revision/node/invocation and from/to status; place exposes typed evidence fields. |
| AgentLoop autonomy | PASS. Model cannot decide completion from video; Coordinator determines terminal facts, then the independent continuation turn performs fresh scene reads before planning the next object. |

## Validation

- Focused Core/Skill regression: `83 passed`.
- Targeted unknown resolution regression: `1 passed`.
- `ruff check`, `python -m compileall -q`, and `git diff --check`: passed.
- No live Runtime, simulator, or hardware motion was run.

## Residual risk

Real deployment still needs a fresh AgentTask and a provider result that supplies the typed place postconditions. Existing historical records retain their original facts and require a later known result for effective resolution.
