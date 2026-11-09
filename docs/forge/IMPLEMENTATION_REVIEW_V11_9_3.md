# v11.9.3 Grounding bind idempotency review

Date: 2026-09-26. Acceptance remains active.

## Finding

**Blocker fixed: repeated AgentLoop assembly made an equivalent binding
ambiguous.** Run6 created two bindings for the same scene identity and the same
red/green/blue entity set. Benchmark target resolution correctly rejected the
duplicate set as ambiguous, but the duplicate was produced by a retry of the
same `scene.bind` obligation rather than by conflicting scene evidence. The
Grounding owner now reuses the existing current binding for an identical
identity and entity set. A different entity set or scene revision still creates
a new binding and remains independently checked.

## Seven dimensions

| Dimension | Result and scope |
|---|---|
| Architecture integration | Idempotency lives in the adapter-owned Grounding boundary; Coordinator and evidence ownership are unchanged. |
| Recovery/idempotency | Same-input retries return the same binding ref. Existing binding pose/current-scene checks still run; no task store is edited and no Action is replayed. |
| Robotics safety | Reuse is allowed only for the current idle identity. It does not authorize motion, change route geometry, or bypass target binding. |
| Configuration/reproducibility | No profile or provider change. The fix applies to repeated `scene.bind` calls in any current profile. |
| Maintainability | Small local lookup with a focused regression; no new hash, service, or global cache. |
| Observability | Returned `binding_ref` and evidence remain the original Coordinator-owned values, making retry provenance explicit. |
| AgentLoop autonomy | Repeated assembly no longer manufactures equivalent state that blocks the next node; distinct selections remain explicit. |

## Validation

- Grounding adapter regression: 56 passed.
- Previous settlement/planning and GraspNet/Skill suites remain passing.
- Live Run6 stopped before Action; preparation failure was `benchmark target binding is absent or ambiguous`, with `action_count=0` and `motion_authorized=false`.
- A new deployment and independent AgentTask are required before acceptance can claim RGB completion.
