# AgentLoop Diagnosis: Canonical Entity Projection

## Scope

This record captures the repeated failure in task `task_5dbef31d4241497e` without
depending on a task name, object color, benchmark profile, or provider.

## Evidence

- Discovery completed with `scene.observe`, `scene.understand`,
  `manipulation.capabilities`, `scene.bind`, and `task.goal`.
- The only planning/execution record was a successful `grasp.propose` query.
- `world_change_started=false`; no `object.acquire`, `object.place`, Gateway
  Action, invocation, or physical motion occurred.
- `scene.bind` returned an observed identity such as `entity://e1` and an
  execution identity such as `entity://block-red-1`.
- A later `manipulation.prepare` projection joined the producer collection with
  the execution alias, while the producer collection was keyed by the observed
  identity. The exact join therefore failed with:
  `projection source collection has no entity_ref matching selected entity`.

## Root Cause

The Coordinator had a correspondence map, but the canonicalization helper was
not enforced at every plan materialization entry. Semantic-node materialization
could repair some consumers; a complete `plan_graph` or persisted continuation
could still carry a model-authored alias into the projection join. The projection
layer then correctly performed an exact match on a non-canonical key.

## Required Invariant

For every scene-bound manipulation segment, the Coordinator must resolve one
canonical observed entity before selection:

`observed_entity_ref <-> execution_entity_ref <-> binding_ref <-> scene_revision`

The observed entity is the projection join key. The execution entity is only the
Runtime-facing identity. A one-to-one correspondence may be normalized; zero or
multiple correspondences must return a structured planning error before Gateway
admission. No color, category, string suffix, or benchmark-specific rule may
infer the mapping.

## Non-goals

This diagnosis does not relax freshness, calibration, workspace, collision, IK,
motion authorization, Gateway admission, terminal settlement, or unknown-result
reconciliation. It also does not add a new hash or baseline mechanism.
