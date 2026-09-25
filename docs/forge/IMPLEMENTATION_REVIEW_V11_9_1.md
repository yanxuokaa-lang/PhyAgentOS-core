# v11.9.1 Planning settlement and GraspNet coverage review

Date: 2026-09-26. Acceptance remains active.

## Findings and dispositions

1. **Blocker fixed: terminal Query records were settled as failed.** The
   Coordinator persisted `tool:<record_id>` evidence, while semantic plan nodes
   declared labels such as `initial_capabilities_current`. Settlement compared
   those two namespaces as literal strings and produced
   `missing_produced_evidence`, leaving no ready node after a successful Query.
   Settlement now distinguishes semantic labels from explicitly opaque refs.
   A semantic label requires a terminal result with a Coordinator-owned opaque
   evidence ref; an explicitly opaque declaration still requires exact matching.
   Empty evidence remains fail-closed.
2. **Major addressed: the old GraspNet ingress budget was too narrow.** Run3
   decoded 1024 real poses, with the first contact-valid native pose at rank
   389. The previous profile sampled 24 and retained at most 10 for
   `manipulation.prepare`. The GraspNet profile now samples 128 and retains 32.
   This expands measured coverage without changing provider identity, NMS,
   support/contact checks, route admission, collision policy, or motion gates.

## Seven dimensions

| Dimension | Result and scope |
|---|---|
| Architecture integration | Settlement owns evidence namespace interpretation; Coordinator remains the source of `tool:` refs. Candidate budget remains in the GraspNet profile and Adapter. |
| Recovery/idempotency | No execution record or Action is replayed. A terminal Query is reconciled once; unknown and stale outcomes retain existing behavior. |
| Robotics safety | The change does not authorize motion or relax IK, collision, route, retreat, or unknown-outcome checks. Empty or non-opaque evidence cannot complete a node. |
| Configuration/reproducibility | GraspNet-only `sample_count=128`, `max_candidates=32`; GraspGen profile is unchanged. Existing artifact roots and runtime bindings remain immutable. |
| Maintainability | One small settlement helper documents the two evidence namespaces. No parallel runtime, hash, contract, or speculative gate was added. |
| Observability | Node settlements retain actual opaque refs, and failures retain `missing_produced_evidence`; tests cover semantic success, empty evidence, and exact opaque matching. |
| AgentLoop autonomy | Successful discovery Queries can unlock dependent nodes through existing `derive_ready_nodes`; the Agent still cannot submit or invent evidence refs. |

## Validation

- Focused planning settlement and DAG regressions: 42 passed.
- GraspNet Adapter regressions: 10 passed; Skill Grasp/Runtime discovery regressions: 28 passed; Skill async grasp suite: 74 passed.
- `compileall` and `git diff --check` passed. A direct pytest invocation with plugin autoload disabled reports three existing async-runner errors; the same planning integration suite passes with the repository's pytest-asyncio plugin enabled.
- Full live RGB acceptance remains required: three independent AgentTasks,
  at least one complete RGB arrangement, terminal acquire/place receipts,
  release-retreat-return evidence, fresh final observation, independent
  `ForgeTaskVerifier`, and a playable video.

## Evidence boundary

Historical GraspNet candidate counts justify expanding the search budget, not
claiming route success. Runtime planning, physical execution, and verification
must still provide their own current receipts.
