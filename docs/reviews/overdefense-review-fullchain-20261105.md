# Full-chain over-defense code review (planning → simulation integration → execution)

Date: 2026-11-05. Method: three parallel read-only reviews with call-chain
verification, spot-checked by the owner's reviewer; criteria from AGENTS.md
principles #7/#10/#11. Carve-outs respected throughout: physical fail-closed
safety (collision/IK/motion/possession), evidence freshness/staleness
discipline, and genuine trust-boundary validation are NOT over-defense.

40 findings: 37 CONFIRMED, 3 PLAUSIBLE. Full detail in the review session
transcripts; one-line index below, grouped by the five observed GPT-defense
signatures.

## Signature A — same invariant re-checked 3-4x in one synchronous chain

| Layer | Site | Redundancy |
|---|---|---|
| planning | planning_dispatch.py:588-609 (+loop.py:545,721) | callers prove node/policy/capability, prepare re-derives 3rd time, each pass full context scan + graph re-toposort |
| planning | planning_dispatch.py:840-846 | input_binding_keys equality re-checked after trusted builder sets them and admission re-checks |
| planning | planning_dispatch.py:152,1167 + planning_loop.py:2057,2469 | isinstance(AdmissionContext) ×4 on a constructor that cannot return another type |
| planning | planning_loop.py:851-869 | winning source record validated per-candidate then re-validated inside projector (N+1 dict rebuilds) |
| sim | engine.py:454-457, 1207, 1243 | parameters normalized + target validated at prepare, re-run at engine execute, again in worker (keep worker pass; delete parent re-run) |
| sim | engine.py:472-475 | cycle_capability() twice back-to-back (each = fs stats + importlib) |
| sim | engine.py:383...+646 (6 sites) | EULA env gate evaluated twice per chain in one process |
| sim | paos_client.py:232-234 | prepare_held route-preservation equality can FALSE-POSITIVE on tuple/list JSON round-trip — harmful, not just redundant |
| exec | subtask_executor.py:977→478→persistent_runtime.py:487 | assignment artifact structurally validated 3x in one chain |
| exec | persistent_runtime.py:577-595 + paos_client endpoint 414-421 | identity fields checked in resolver twice then endpoint third time |
| exec | subtask_executor.py:1034-1043 (+held 435, paos_client 233) | echo checks stacked 3 layers on one in-process chain |
| exec | subtask_executor.py:334-353, 836 | pydantic model re-validates what field validators/equality just established |

## Signature B — per-turn redundant full passes (runtime cost)

| Layer | Site | Cost |
|---|---|---|
| planning | planning_loop.py:1341-1389 | THREE byte-identical if/else resume blocks (spot-checked) — up to 3 redundant full reconciles per node turn before the model runs |
| planning | planning_loop.py:1510-1602 | _resume_node loads task 3x per happy-path resume; ×6 with above |
| planning | plan_proposal.py:169-492 | _task_goal_destinations ×3 + current_scene_query_records ×2 per compile (each = full record scan) |
| planning | planning_dispatch.py:268-463 | admission predicate recomputed ~10x per policy per node in describe(); one computed dict block dead (shadowed key) |
| exec | held_manipulation.py:902-930, 711-758 | admit+start double full preparation resolution; 4× validate_begin per action |
| exec | phase_motion.py:749-753, 2013-2062 | contact sensor captured twice per rendered frame in the hot control loop |

## Signature C — deepcopy sandwiches

paos_client.py:52,88,91 + engine.py:432 (triple copy of one prepared artifact);
paos_client.py:124-141 (per-candidate double copy incl. calibration arrays) +
engine.py:498 + JSON wire (copies anyway); client 387-400 → engine 559 →
backend 715 (execution path ×3); planning_dispatch.py:113+375 (schemas ×2);
held_manipulation.py:422,439 + project_result 842/657; subtask_executor.py:771
(schema rebuilt per call — hoist/lru_cache); paos_client.py:364.

## Signature D — dead/unreachable code

- planning_loop.py:2496-2543 triple-nested except keeps only type names (drops causes); planning_loop.py:1770-1798 conflates Coordinator bugs into "Gateway read failed" on durable records
- subtask_executor.py:615-619 broad except drops str(exc) from receipts
- sim engine.py 8 sites + paos_client 5 sites: fabricated invalid_*_result fallbacks for non-Mapping returns that cannot occur (worker wire enforces)
- sim engine/paos_client ~15 sites: getattr/callable probes against own constructed components → "not_supported" fallbacks
- paos_client.py:35-275: SHADOW preparation store (_prepared + equality gate) provably unreachable — StoredAssignmentResolver always wins (build 506-524)
- subtask_executor.py:545-640: sync SubtaskExecutor production-dead (tests only; spot-checked), _arguments duplicates _runtime_arguments verbatim; :1104 reads nonexistent field; :748 dead reassignment
- planning_dispatch.py:569-622: deterministic fast-path swallows non-retryable rejections → burns an LLM turn to re-receive them
- cycle_protocol.py:119-133 vs 163/216/281: gap condition encoded twice

## Signature E — shadow policies / duplicated state (principle 7)

- planning_dispatch.py:174,782 + planning_loop.py:2094: ready-set override triplicated WITH DRIFT (loop copy missing refreshes_scene check — admits more nodes) → centralize in derive_ready_nodes
- paos_client.py:38-43 vs 339-354: duplicate capability projections
- engine.py:2514-2518: scene-switch guard against same immutable profile (always equal)

## PLAUSIBLE (needs one design decision each)

1. engine.py:377-421 parent-side isaac importability gate duplicates worker's own failure mode (parent env ≠ worker interpreter) — risk: medium
2. held_manipulation.py:465-466 "possession changed during cycle preparation" unreachable without concurrent driver polling
3. planning_loop.py:334-357 historical settlements merged twice (loader-seam dependent)

## Explicitly kept (reviewed, justified)

All collision/IK/motion/possession fail-closed checks; scene_revision/staleness
gates; schema validation at model-output→tool-arg boundary; idempotency/digest
checks on model-supplied bindings; PersistentPossession as authoritative store
(executor context is a documented projection); prepare failure-code allowlist
(keeps unknown failures explicit); _EpisodeVideoRecorder best-effort write.

## Recommended cleanup order

1. **Tier 1 (mechanical, low risk, ~25 findings)**: dead branches, fabricated
   fallbacks, duplicate deepcopies, dead sync executor, schema hoisting.
2. **Tier 2 (performance, low risk, ~8)**: identical if/else collapses, single
   task-load per resume, admission-predicate memoization per node, sensor
   capture-once-per-frame, admit/start single resolution.
3. **Tier 3 (design decisions, ~5)**: shadow store deletion, ready-set
   centralization (behavior-affecting), normalization single point,
   parent-isaac gate, narrowed excepts with cause retention.

Each tier ships with the full regression suite (506+ tests) green and a
changelog entry per the maintenance rules.

## Cleanup outcome (v17.1.0, same day)

Applied: engine copy reductions (6 sites) + capability-once; paos_client
JSON-roundtrip held-route check (false-positive fix), dead poll branch, bool
guard, capture copy; held/cycle admit→start single resolution; held/projector
deepcopy trims; unreachable possession-changed check deleted; cycle-protocol
gap-condition dedup; subtask-executor sequence/possession/persist/evidence-refs
dedup + failure code carries type name; persistent endpoint ownership-only;
planning triple identical if/else collapse; stale-scene predicate centralized
in dispatch (helper `stale_scene_ready_nodes`).

Overturned by test evidence (reverted — the review's redundancy claim was wrong):
- shadow preparation store: it IS the working path for store-less compositions
  (tests + legacy deployments); only unreachable WITH an assignment store.
- execute-side parameter normalization: direct-call tests depend on it.
- prepare() per-candidate deepcopy hoist: downstream mutates nested values;
  shared shallow copy bleeds across candidates.
- _resume_node single records load: the post-reconcile re-read observes
  records reconciliation itself surfaces.
- held-route identity-only comparison: parameter preservation is a tested
  contract; fixed instead by JSON-round-trip normalization of the expected side.

Kept as legitimate (not over-defense): engine/provider capability probes and
fabricated-result fallbacks (live injected-backend/FakeEngine test seams),
backend EULA guards (zero-cost, protect direct calls), parent-side Isaac gate
(capability dedup applied).

Deferred (documented follow-ups): describe() admission-predicate memoization,
deterministic fast-path rejection propagation, plan_proposal single-pass
computation, isinstance dedup, binding-keys dedup, frozen-schema copy dedup,
settlement double-merge, phase_motion sensor single-capture-per-frame, full
sync-executor deletion, planning-loop policies seam for the stale-scene
prefilter.

Validation: the focused affected-module suite completed with 410 passed and six
failures; the full Core + Isaac Adapter + pick-place suite completed with 2226
passed, 2 skipped and 16 failures. Every failing node was rerun in an isolated
HEAD worktree and failed there unchanged, so this cleanup adds no new failing
test. Ruff, compileall and targeted `git diff --check` pass on all cleanup files.
