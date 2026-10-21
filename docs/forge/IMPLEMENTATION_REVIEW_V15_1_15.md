# Implementation Review v15.1.15: Durable Assignment Artifact Store

Date: 2026-10-21 (Asia/Shanghai)

## Scope

This stage adds a provider-neutral SQLite implementation for the existing
`AssignmentArtifactStore` port and allows preparation responses to carry
provider-owned approved `route_arguments`. The subtask boundary persists the
complete assignment artifact after a trusted-intent preparation; acquire/place
resolve through the same canonical reference when the store is injected.

No perception provider, Isaac Sim controller, AgentLoop settlement rule, or
motion path was changed. The store does not derive or interpret routes.

## Architecture Review

- PAOS owns the provider-neutral store protocol, serialization, the subtask
  persistence point, and canonical-reference resolver.
- Preparation providers own the route data they approved. Readiness-only
  providers remain valid and do not fabricate route arguments.
- Adapters may inject the store; environment-specific path/SDK interpretation
  remains outside the generic Skill and PAOS store.
- Internal Tool receipts remain internal to one `manipulation.execute_subtask`
  invocation. AgentLoop settlement remains at the subtask boundary.
- Duplicate `assignment_ref` writes are idempotent only for identical content;
  conflicting content is rejected. This protects a concrete case where a
  retry or concurrent producer reuses a canonical reference for another route.

## Findings

### Blocker: production route producer is not yet connected

`ManipulationPreparationEndpoint` now transports optional `route_arguments`,
and the executor persists them only when a complete trusted assignment is
present. Existing production providers do not yet return these route
arguments, and LabUtopia composition does not yet provide a production route
artifact producer. Consequently, the SQLite mechanism and no-motion contract
are implemented, but the actual LabUtopia prepare -> durable write -> acquire /
place read flow is not yet proven. Missing route data fails closed; it is not
reconstructed from a profile, object name, or USD Prim.

### Major: process-restart proof is limited to the store/resolver boundary

Tests close and reopen a real SQLite file and resolve its contents through a
new resolver instance. A full Runtime process restart with real provider
artifacts is not yet exercised.

## Seven-Dimension Acceptance

1. Perception correctness: not validated in this stage; prior real sensor
   evidence remains outstanding.
2. Binding and freshness: existing subtask provenance checks remain in force;
   durable route artifact lineage is contract-tested but lacks a production
   provider payload.
3. Agent granularity: passed at no-motion Runtime-contract level; one outer
   subtask lifecycle retains all internal receipts and one settlement.
4. IK, workspace, and collision: only existing no-motion preparation checks
   are exercised; no live IK/collision proof was run.
5. Execution state: not validated; no acquire/place motion was run.
6. Process feedback: not validated; no pour/stir process was run.
7. Settlement and recovery: store write failures/missing artifacts stop the
   subtask before later tools; live AgentLoop recovery remains unvalidated.

Overall acceptance: **incomplete**. This stage closes the durable storage
mechanism but does not satisfy the user's whole-plan completion criterion.

## Validation

- Focused preparation/store/subtask tests: `47 passed`.
- LabUtopia integration wiring: `7 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No Isaac Sim, Gateway Action, simulator step, or motion was run.

## Next Required Work

Connect a real preparation provider that produces a complete PAOS assignment
and approved route arguments, inject a file-backed store into the Runtime,
verify acquire and place resolve that same artifact after Runtime recreation,
then continue with real observation, motion-safety, process-feedback, and
AgentLoop subtask settlement acceptance.
