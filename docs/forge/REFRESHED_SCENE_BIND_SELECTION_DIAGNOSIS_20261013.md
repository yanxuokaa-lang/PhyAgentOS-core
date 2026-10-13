# Refreshed-scene binding selection diagnosis (2026-10-13)

## Scope

This record covers a generic AgentLoop convergence failure after a read-only
evidence refresh. It is not tied to a color, object layout, benchmark, or
workflow node name. No Runtime Query/Action, task resume, simulator step, or
physical motion was performed while producing or validating this repair.

## Evidence-bounded failure

The preparation Query reported ambiguous support/collision geometry and asked
for declared evidence refresh. The refresh, scene understanding, and
capability Query completed on a new observation lineage. The subsequent
`scene.bind` Tool was never called: no planning selection and no execution
record were persisted for that node. The AgentLoop therefore stopped with
`node_selection_no_progress`, after a corrective model turn produced no new
Coordinator fact.

This is distinct from a Gateway binding failure. The existing ambiguity gate
was correctly fail-closed; the model lacked a structured distinction between
task identities that must be selected and environment geometry that should
remain evidence for preparation. The recovery plan could mention support or
collision entities in its obligation text, which made the ambiguity appear to
block the binding selection itself.

## Architecture decision

`scene.understand` owns the complete observed world description, including
task entities, support relations, collision geometry, and ambiguity facts.
`scene.bind` owns only the current observation-to-execution identity mapping
for entities relevant to the node. `manipulation.prepare` consumes the
understanding evidence for support/collision validation and remains
fail-closed when that evidence is ambiguous.

The Coordinator continues to project the current understanding's bounded
`candidate_entity_refs`, `ambiguous_entity_refs`, and
`recommended_unambiguous_entity_refs` without selecting. It does not classify
entities by provider-specific category text. The Agent must match the node's
task identities against those candidates; support/collision entities remain
understanding evidence unless the node's structured input bindings explicitly
make one a task identity.

The Agent must still submit `forge_plan_select`. No automatic selection,
entity substitution, binding reuse across observation lineage, or Action
authorization was added. The existing Coordinator ambiguity, freshness,
calibration, projection, Gateway admission, and motion gates remain owners of
their respective checks.

## Validation

- Focused no-motion suite: `267 passed in 10.05s`.
- Full no-motion suite: `905 passed in 32.54s`.
- `git diff --check`, `compileall`, and scoped Ruff passed.

These tests use local fixtures only. They do not prove live scene content,
provider availability, or physical placement success.
