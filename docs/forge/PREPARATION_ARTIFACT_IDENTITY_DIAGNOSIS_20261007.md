# Preparation Artifact Identity Diagnosis

Date: 2026-10-07 (Asia/Shanghai)

## Scope

This diagnosis covers the generic evidence-identity failure observed in
`task_13315d0d962a45f5`. It does not depend on object color, ordering, a
benchmark destination, camera name, entity ID, candidate index, or arm choice.

## Authoritative Event Chain

- Discovery, binding, goal retrieval, and `grasp.propose` completed.
- `red_grasp` produced 32 candidates for the frozen entity.
- Coordinator persisted the `red_prepare` selection and invoked
  `manipulation.prepare`.
- All 32 candidate route materializers completed successfully.
- Preparation then failed before contact qualification, route readiness,
  Action admission, or any simulator step.
- The persisted preparation metrics record
  `ValueError: materialized artifact conflicts with runtime evidence`,
  `action_count=0`, and `simulator_steps=0`.

The deployed route profile is `planner_world_only`; observed occupancy and
unknown-space qualification were not active in this failure.

## Root Cause

The long-lived Runtime artifact root already contained motion-capability files
under `artifact://robotwin/franka-bounded-q4/...` from an older controller
deployment. The current approved controller qualification produced different
capability payloads, including a new controller source identity, planner
version, and runtime Python version, but reused those same artifact refs.

`PersistentRouteBuilder._import_artifacts()` correctly refused to overwrite an
immutable ref with different bytes. Deleting the old evidence would destroy
traceability; accepting the overwrite would allow old routes to resolve to new
content. Neither is valid.

## Ownership Correction

- The static arm-planning profile owns arm topology, frames, supported modes,
  and logical planning configuration.
- A controller-qualification package owns the concrete capability and
  validation evidence refs for one qualified provider identity.
- Route materialization consumes those qualification-owned refs.
- The scene-bound capability snapshot projects the same current refs.
- The Runtime artifact store keeps immutable artifacts and rejects ref/content
  conflicts.

Future qualification packages must allocate capability refs inside their own
qualification namespace. This is an existing formal motion-admission boundary,
not a new task-level gate.

## AgentLoop Boundary

This is a provider contract failure. It is not recoverable by repeating the
current node, changing candidate or arm, observing again, or replanning the
semantic task. The proper result is a structured non-retryable Runtime-owned
failure with `recommended_action=fix_runtime_contract`. No Action may be
automatically dispatched.
