# Multi-source manipulation.prepare projection diagnosis

## Incident

- Task: task_6ce47703bc1d4d70
- Revision: revision_3437b7d4c3a744d6
- Node: green_prepare_acquire
- Authoritative error: consumer_projection_invalid: projection_source and argument_sources must use the same authorized record
- Boundary: Coordinator selection/projection compilation; no Gateway call and no physical Action.

## Root cause

manipulation.prepare consumes two independently produced facts:

1. grasp.propose owns candidate_set_ref, candidate geometry, and candidate/entity association.
2. manipulation.capabilities owns the currently available arm identities and capability snapshot.

The current projection API accepts one projection_source. Its compatibility bridge accepts argument_sources only when every selector points to that same record. A grasp proposal record cannot also be the authoritative capability snapshot, so the valid request cannot be represented.

Repeated Agent attempts to write allowed_arms cannot repair the contract: the node intent is Coordinator-owned and frozen, while candidates and arm availability must remain record-derived.

## Ownership decision

- Agent: select the ready node and the ToolSpec-declared authorized source records.
- Coordinator: verify source roles, predecessor authorization, current revision, and shared scene/observation/frame/calibration facts; compile candidates and available arms into frozen Tool arguments.
- Runtime Adapter: validate candidate shape, entity association, embodiment arm membership, route readiness, workspace, IK, and collision without authorizing motion.

Candidate filtering remains mandatory and Coordinator-owned: only candidates whose entity_ref equals the node-bound entity may reach manipulation.prepare.

## Anti-OverDefense assessment

Concrete failure if the same-record check is simply removed: an Agent could join stale candidates from one scene with arm availability from another scene or an unrelated task. Git, version numbers, record primary keys, types, and ordinary schema validation do not establish shared world state.

Therefore the repair does not allow arbitrary multi-record assembly. ToolSpec must declare named source slots and their projected fields. Coordinator admission must reject undeclared records and mismatched scene revision, observation, frame, or calibration facts.

## Acceptance criteria

- A declared grasp source plus a declared same-scene capability source compiles without Agent-authored candidates or arm IDs.
- Candidate filtering is deterministic by the node-bound entity_ref.
- Cross-scene, cross-observation, cross-frame, cross-calibration, undeclared, or hidden records fail closed before Gateway execution.
- Existing single-source projection contracts remain compatible.
- No code path authorizes motion; this change ends at query argument compilation.
