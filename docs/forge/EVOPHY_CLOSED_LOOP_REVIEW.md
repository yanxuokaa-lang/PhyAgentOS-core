# EvoPhy Closed-Loop Review

Date: 2026-09-11. Scope: algorithm and PAOS extension lifecycle.

EvoPhy currently supports a mechanically testable, human-reviewed learning
lifecycle. It does not yet demonstrate autonomous improvement on physical tasks.
The extension consumes explicit provider/Skill projections; standard CLI
configuration alone does not supply those projections.

## Corrected Failure Paths

- Generic reflection cannot aggregate support into an extension candidate.
  Extension promotion requires independent receipts and explicit review even
  when the internal promotion helper is called directly.
- Local advice is retained in candidate-marked sections inside the existing
  managed workflow block. Subsequent local and generic revisions preserve it.
  Exclusion conditions reach both content validation and the loaded document.
- Activation records evolution candidate identities separately from Runtime
  binding candidates. Episode completion records the outcome associated with
  loaded advice; it does not claim the advice caused that outcome.
- Existing pending jobs recover extension delivery after restart using delivery
  events in the existing ledger. Projection and method failures signal retry.
- TRACE uses explicit `depends_on` edges for downstream reachability. Shared
  observation references alone no longer produce joint-cause hypotheses.
  Joint sets require dependency connectivity and shared, sufficiently confident
  owner-hypothesis evidence. They remain hypotheses, not causal proof.

## Algorithm Limits and Next Evaluation

TRACE is an earliest-observable-divergence heuristic. Dependency reachability
can indicate possible propagation, but does not distinguish a root cause from
a correlated symptom. Provider owner hypotheses still supply much of its
attribution information. Low-confidence explicit hypotheses now remain unknown
instead of falling back to an unqualified owner label.

Patch synthesis still emits four deterministic advice templates. It cannot yet
search alternative recovery strategies, show that the selected instruction
changes Agent decisions, or execute structured add/replace/remove operations on
a workflow DAG. Appending local advice avoids deleting learned transitions but
does not solve conflicting advice or patch retirement. Promotion now resolves
each support episode's primary activation, requires one shared parent document,
and compares its existing digest with the current Skill before writing. Missing
episodes, mixed parents, changed documents, and revision mismatches block the
candidate. This binds publication to the source parent; an independent evaluator
must still prove it actually ran that parent and the proposed candidate content.

The next method evaluation should separate:

1. Controlled independent failures versus propagated failures; report false
   causal links, owner accuracy, and unknown/abstention behavior.
2. Single and multiple interventions with independent oracle labels; compare
   earliest failure, random edge, dependency-aware TRACE, and oracle attribution.
3. Parent and candidate Agent runs on matched, held-out, and hazard tasks, with
   fixed model, provider, task order, reset policy, and action/model/time budget.
4. Actual selected transition behavior, task outcomes, side effects, and cost
   after a new binding. Loading advice alone is not behavioral adoption.

Real provider projections and an independent execution evaluator must be
integrated before enabling automatic promotion. The explicit
review boundary remains in place. No robot or simulator run was used for this
review; fake-facts tests verify mechanics, not measured learning effectiveness.

## Verification

```bash
PYTHONPATH=extensions/evolution:examples/forge-skills/pick-place-workflow/src \
  .venv/bin/python -m pytest -q tests/test_evophy_review_regressions.py \
  tests/test_evolution_composition.py tests/test_evolution_extension_adapter.py \
  tests/test_evolution_extension_hook.py extensions/evolution/tests \
  examples/forge-skills/pick-place-workflow/tests/test_experience_attribution.py \
  examples/forge-skills/pick-place-workflow/tests/test_experience_recovery_episode.py \
  examples/forge-skills/pick-place-workflow/tests/test_experience_capability_facts.py
```
