# v11.9.4 Grasp fact and exact scene-binding review

Date: 2026-09-26. RGB acceptance remains active.

## Findings and dispositions

1. **Blocker fixed: proposal success did not unlock preparation.** Run7 completed
   a real GraspNet Query with
   `decoded=1024/canonicalized=128/deduplicated=54/retained=32`, but the result
   did not publish a trusted condition fact. The provider-neutral Runtime Query
   now publishes `condition_facts.grasp_candidates_retained` only after snapshot,
   funnel, geometry, and provenance validation. Empty, unavailable, stale,
   invalid, or provenance-invalid results publish `false`. Legacy terminal
   receipts derive the same generic fact only from Coordinator-owned status,
   monotonic funnel counts, candidate count, and artifact provenance.

2. **Blocker fixed: preparation guessed a target across scene bindings.** Run6
   retained 32 real candidates but `manipulation.prepare` failed before geometry
   screening with `benchmark target binding is absent or ambiguous`. The current
   `scene.bind` opaque `binding_ref` is now frozen into the prepare node by the
   Coordinator and injected into the Tool arguments. RoboTwin Grounding resolves
   the benchmark destination through that exact binding instead of scanning all
   same-scene bindings. Identical bind requests are idempotent; distinct entity
   sets retain distinct refs. Missing, unknown, conflicting-scene, and ambiguous
   binding provenance fail closed.

3. **Major fixed during review: provider-specific condition leaked into the
   generic replay path.** The temporary `graspnet_candidates_retained` alias
   could have allowed a non-GraspNet receipt to satisfy a provider-specific graph
   condition. The alias was removed. Runtime, ToolSpec, Skill guidance, and
   replay now use only `grasp_candidates_retained`. Deployment uses a fresh
   AgentTask, so the old Run7 graph does not need a cross-version exception.

## Seven dimensions

| Dimension | Result |
|---|---|
| Architecture integration | PASS. Runtime owns candidate availability; Coordinator owns node facts and opaque binding projection; Adapter owns destination resolution. No Agent-authored opaque ref is accepted as a substitute. |
| Recovery and idempotency | PASS. Legacy successful Query receipts can derive the generic fact without replay. Identical `scene.bind` input reuses its ref; multiple distinct bindings remain explicit and fail closed when no unique Coordinator source exists. |
| Robotics safety | PASS. Proposal and preparation remain no-motion. Collision, contact, IK, complete-route, stop, retreat, terminal-result, and unknown-outcome rules are unchanged. |
| Configuration and reproducibility | PASS. GraspNet remains `sample_count=128`, `max_candidates=32`, `orientation_diverse`; Node 0.8.3 rebuilds byte-identically with SHA-256 `0c07e9719524a05393ce6a259bf432a0275ab50676002540d725db9949acbdb5`. |
| Maintainability | PASS after review fix. One provider-neutral fact and one explicit binding argument use existing ToolSpec, planning binding, and Adapter boundaries. No hot Runtime rebind, parallel planner, new hash mechanism, or speculative retry was added. |
| Observability | PASS. Funnel, condition fact, binding ref, prepare metrics, failure owner, and zero-Action status remain persisted. Run6 evidence distinguishes binding failure from candidate quality. |
| AgentLoop autonomy | PASS in regression. The Agent selects semantic nodes and candidates; Coordinator copies the current opaque binding and builds the planning binding. Full three-block execution remains the live acceptance gate. |

## Validation

- Focused planning, Skill, and Adapter regression: `209 passed`.
- Combined Core, Adapter, and Skill regression: `1678 passed, 1 skipped`.
- Isolated scene-understanding provider suite: `9 passed`.
- Ruff, compileall, and `git diff --check`: pass.
- Node 0.8.3 deterministic double build: identical 382499-byte archives and
  SHA-256 `0c07e9719524a05393ce6a259bf432a0275ab50676002540d725db9949acbdb5`.

## Acceptance status

The implementation is ready to deploy as Skill 2.8.2 and Node 0.8.3 in a fresh
AgentTask. No RGB arrangement, terminal acquire/place receipts, retreat evidence,
final verifier, or playable video is claimed by this code review.
