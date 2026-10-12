# Frozen Query Selection No-Progress Diagnosis

## Scope

This diagnosis covers a generic PAOS AgentLoop failure in which a semantic Query
node already contains complete Coordinator-frozen Tool arguments, but no planning
selection is persisted before the bounded model turns expire. It does not define
an RGB-, object-, scene-, provider-, or Skill-specific recovery rule.

The implementation and validation are no-motion. They do not restart a Runtime,
invoke a Gateway Query or Action, read a camera, advance a simulator, or authorize
motion.

## Authoritative failure

Task `task_253ac305b9ad4c8e`, revision
`revision_5b78ced22a4b4f9b`, stopped at node
`current_scene_cube_bindings` with:

```text
node_turn_incomplete:current_scene_cube_bindings:
node_selection_no_progress:
Coordinator facts did not change after a corrective planning turn
```

The PlanNode already froze all four Tool inputs:

```json
{
  "observation_ref": "observation://.../head_camera",
  "scene_revision": "...-3",
  "calibration_ref": "artifact://.../calibration",
  "entity_refs": ["entity://e1", "entity://e2", "entity://e3"]
}
```

The active revision contained zero planning selections, zero execution records,
zero node settlements, and zero selection rejections. No `scene.bind` Gateway
call occurred. The failure therefore belongs to pre-execution selection progress,
not Runtime readiness, grounding, Query provider, or physical execution.

The node context also exposed a deterministic evidence-lineage defect. The node
explicitly required the latest understanding record
`tool:tool_392197f7a589482e`, but the authorized discovery pool still contained
the earlier same-scene record `tool_a1281b35cc7848f7`. The context builder
counted both records and returned `scene_bind_selection.status=unavailable`
because it required exactly one candidate. The node prompt then correctly
prohibited a speculative selection, so both corrective turns left Coordinator
facts unchanged.

Earlier authoritative Action facts remain complete and must not be replayed. In
the same task, the prior acquire/place invocations settled successfully, and the
place result reported `release_confirmed=true`, `retreat_completed=true`,
`clear_of_target=true`, and a new scene revision. Those historical effects are
context only; current-scene observation, understanding, and binding remain the
source of current visual identity and geometry.

## Root cause

The control plane treated every planning selection as a fresh model decision,
even after the PlanGraph had already made all decisions needed for a particular
Query:

1. The node had one matching frozen ToolSpec.
2. The Tool semantics were read-only Query.
3. Every input-schema requirement was present in immutable `input_bindings`.
4. No projection record, argument source, runtime intent, or alternative Tool
   remained to be selected.
5. The model nevertheless had to call `forge_plan_select` and repeat those exact
   inputs.
6. Two turns without a selection correctly triggered the existing no-progress
   guard, but the task had no path to persist the already-made graph decision.

A second control-plane gap affected nodes that still require a semantic entity
choice: `_scene_bind_selection_context()` treated the entire authorized
discovery pool as an unordered candidate set. It did not first honor the current
PlanNode's `required_evidence`, so multiple successful understandings of the
same scene could hide the one record explicitly selected by the plan.

ToolSpec validation, PlanGraph digests, Coordinator transactions, and the
no-progress guard are all necessary, but none creates the durable planning
binding consumed by execution. A version, primary key, hash, or additional gate
would not close this lifecycle gap.

## General repair

The repair adds a narrow deterministic-selection path through existing PAOS
authorities:

```text
PlanNode frozen input_bindings
  -> AgentComposedDispatch proves zero remaining choice
  -> existing prepare_selection validation
  -> AgentTaskCoordinator.persist_planning_selection
  -> existing pending-selection resume
  -> governed Query wrapper
```

Eligibility requires all of the following:

- exactly one ToolSpec candidate for the node capability;
- semantics exactly `query`;
- a frozen input schema exists;
- the node's frozen arguments pass the complete schema after normal defaults;
- no argument projection or projection source exists;
- no trusted argument builder or runtime semantic intent exists.

If any condition fails, the method returns no proposal and the normal Agent turn
retains ownership. The ordinary admission path still validates readiness,
evidence, scene identity, semantic bindings, input schema, digests, and the
transactional absence of an execution or settlement.

For semantic binding contexts, evidence selection follows the frozen graph:

1. collect only successful authorized `scene.understand` records;
2. if the current node explicitly requires one or more of those record evidence
   references, restrict the candidate set to those explicit records;
3. require exactly one remaining record and validate its current scene and
   usable entity result;
4. when the node has no explicit understanding lineage, retain the existing
   unique-authorized-record fallback;
5. keep multiple explicitly required understandings fail-closed rather than
   selecting by timestamp, list order, category, provider, or task convention.

## Safety and extension boundary

The deterministic path cannot select or start an Action or Session. It cannot
choose among multiple Tools, select entities that were not frozen in the node,
choose a source record, compile provider output, author geometry, infer a target,
or supply manipulation intent. It also cannot weaken freshness, calibration,
workspace, collision, IK, motion authorization, Gateway admission, reconciliation,
or terminal settlement.

The rule depends only on PlanNode, ToolSpec, Query semantics, frozen schema, and
Coordinator admission. It contains no branch for RGB, color, blocks, scene.bind,
provider identity, node names, benchmark tasks, or a particular Skill.

## Recovery semantics

- An already persisted selection is always consumed first and is never selected
  again.
- A deterministic selection is persisted once through the existing idempotent
  Coordinator transaction, then consumed by the existing execution wrapper.
- Existing execution records are reconciled before either deterministic or model
  selection.
- Completed or outcome-unknown Actions are never replayed.
- Incomplete, ambiguous, projection-owned, or motion-capable nodes retain the
  existing bounded AgentLoop and fail-closed no-progress behavior.

## Validation expectations

Regression coverage must demonstrate:

1. a complete unique frozen Query compiles the same selection proposal as normal
   Coordinator admission;
2. the node executor persists and consumes it without a model turn;
3. Action, multiple-candidate, projection, and missing-field cases are ineligible;
4. the persisted selection still executes only through the governed Tool registry;
5. no test invokes a real Runtime, Gateway, camera, simulator, or actuator.
6. an explicitly required current understanding wins over same-scene historical
   understandings, while multiple explicitly required understandings remain
   unavailable.
