# Implementation Review v15.1.14: Reference-Addressed Assignment Resolution

Date: 2026-10-21 (Asia/Shanghai)

## Findings and disposition

The previous endpoint accepted an injected resolver callback, but the generic
Runtime had no reusable store-backed implementation. A provider could therefore
silently rebuild an assignment from current configuration while returning the
same-looking mapping. This stage adds a provider-neutral store port and resolver
that looks up the exact `assignment_ref`, validates task/entity/candidate and
preparation identity, checks placement destination and scene revision, and
returns stored `route_arguments` without rebuilding them.

The existing callback form remains supported. If the callback exposes
`resolve_for_task`, `PersistentActionEndpoint` passes the PAOS caller's task ID
to it. The resolver itself does not own storage lifecycle, create assignments,
or infer a route from semantic labels, Prim paths, or profile values.

## PAOS architecture review

- `AssignmentArtifactStore` is a provider-neutral read port. A database, file
  artifact service, or environment-owned store can implement `get(ref)`.
- `StoredAssignmentResolver` belongs beside the existing persistent Action
  endpoint because it resolves PAOS preparation artifacts at the Action
  admission boundary. It does not introduce a parallel task or receipt store.
- `PersistentActionEndpoint` still owns admission and delegates lifecycle to
  `CapabilityRuntime`; possession remains in the existing owner.
- `manipulation.prepare`/its approved route provider remains the assignment
  producer. This change deliberately does not fabricate a store writer from
  arbitrary provider output; the environment must persist the complete
  assignment plus route arguments under the canonical reference.

## Extension principles, Developer Guide, and AgentLoop

The public seam contains only the cross-provider `get(assignment_ref)`
operation. The store document preserves the provider's approved `route_arguments`
as opaque JSON-compatible execution data while the generic resolver checks
common PAOS identity. AgentLoop receives no additional node, turn, or settlement.
Unknown or mismatched artifacts fail before Action start.

No hash, new frozen contract, or additional admission gate was added. The
failure scenario is assignment reconstruction after a process restart or under
changed configuration; ordinary type checks cannot prove the loaded document
is the same artifact requested. Exact lookup by the existing PAOS artifact
primary reference, existing task ownership, and tests address that scenario.

## Robotics safety

Resolver tests are no-motion and stop before `ActionAdmission.start`. This
resolver is not a motion authorization mechanism. Calibration, IK, workspace,
collision, and controller execution remain separate providers and gates. No
Isaac Sim, Gateway Action, simulator step, or robot motion was run.

## Seven-dimension acceptance

1. Perception correctness: **not changed; partial overall**. No live sensor
observation is consumed by this storage stage.
2. Binding and freshness: **partial overall**. Assignment identity is resolved
by canonical ref; real sensor freshness/calibration provenance is not exercised.
3. Subtask-level AgentLoop boundary: **pass for Runtime contract**. This stage
adds no PlanNode or model turn and retains the one-subtask settlement boundary.
4. IK, workspace, and collision: **not live-verified**. No planner or scene
geometry was queried.
5. Execution state: **not live-verified**. Tests end before Action start.
6. Process feedback: **not live-verified**. No pour/stir process was executed.
7. Subtask settlement and recovery: **partial**. Existing settlement contract
is unchanged; resolver recreation over a shared test store and unknown/mismatch
lookups are covered. A real durable backend, OS-process restart, and held-state
reconciliation remain unverified.

## Validation

- Focused persistent Runtime, subtask executor, and LabUtopia wiring tests: **47 passed**.
- Ruff and `git diff --check`: passed.
- Pytest emitted the existing `asyncio_mode` configuration warning.
- No Isaac Sim, Gateway Action, simulator step, or motion was run.

## Remaining acceptance blockers

The overall LabUtopia plan is not accepted. The LabUtopia host still needs to
provide a durable `AssignmentArtifactStore` that stores the exact assignment and
approved route arguments emitted by task-scoped preparation, then wire the
same store to acquire/place resolution. A restart test must close and recreate
the Runtime and resolver against the actual backend. After that, real camera
providers, readiness evidence, single-pour execution, and the two-reagent/stir
long-horizon task still require evidence and seven-dimension review.
