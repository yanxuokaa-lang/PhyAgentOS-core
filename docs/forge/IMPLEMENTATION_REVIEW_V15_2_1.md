# Implementation Review v15.2.1: Provider-Owned Route Arguments

Date: 2026-10-21 (Asia/Shanghai)

## Findings and disposition

The RoboTwin persistent preparation provider already builds a complete route,
selects one route/arm assignment, verifies that its geometry matches the
assignment, rechecks the world revision, and optionally issues a route-bound
execution approval. It previously registered this exact execution bundle only
in the adapter's in-memory `PreparedRoutes` cache and omitted it from the PAOS
preparation response. Consequently, the PAOS subtask persistence hook could not
store the route that preparation had actually selected.

`PreparedRoutes.register` now returns a defensive copy of the same provider-owned
bundle it registered, and `PersistentPreparationProvider.prepare` publishes it
as `route_arguments`. This is opaque adapter data to PAOS: the generic store
does not parse route requests, pick an arm, or grant approval. No route is
authorized when the adapter has no execution approval; existing `PreparedRoutes`
continues to reject execution in that case.

## PAOS architecture, extension, and Developer Guide review

- The new value is produced at the owner of route generation and approval, not
  reconstructed in PAOS or from Agent labels/profile fields.
- The shared preparation output remains a provider-neutral mapping; adapter
  details stay inside `route_arguments`.
- No Agent-facing tool, PlanNode, Runtime lifecycle, settlement state, or
  AgentLoop turn boundary changed.
- This response enables persistence but does not wire a store or a production
  subtask entry point into the RoboTwin host.

## AgentLoop and integration blocker

RoboTwin's current persistent Runtime composition registers the ordinary
perception/preparation/acquire/place Tools but does not register
`manipulation.execute_subtask` with a provider-neutral perception binding and
Coordinator context resolver. Therefore, the new provider output is testable
through the real preparation provider contract but is not yet consumed by the
one-settlement subtask loop in production composition. A separate adapter-owned
route resolver also performs live snapshot, approval, and current acquisition
checks; it must remain in the chain when durable artifacts are wired.

This stage deliberately does not bypass those checks or label a fixture as the
production closed loop. The next implementation must compose the generic
perception binding/subtask endpoint, persist the exact provider output into a
configured durable store, and preserve adapter-owned execution validation on
acquire/place.

## Robotics safety

Tests exercise preparation only and start no Action. The route remains bound to
the observation scene revision, candidate, assignment and destination; approval
remains a separate adapter artifact. No Isaac Sim, Gateway Action, simulator
step, or robot motion was run.

## Seven-dimension acceptance

1. Perception correctness: **not validated here**; no camera observation or
   target identification is executed by these preparation fixtures.
2. Binding and freshness: **partial**; the provider validates route/assignment
   scene and candidate identity, but this stage does not exercise live sensor
   freshness through the subtask entry.
3. Subtask-level AgentLoop boundary: **not production-integrated**; current
   RoboTwin composition still lacks the subtask endpoint/context wiring.
4. IK, workspace, and collision: **provider-preparation tests only**; no live
   planner/controller or robot motion proof is claimed.
5. Execution state: **not validated**; no Action was started.
6. Process feedback: **not applicable to this route-output stage**; no pour or
   stir operation was run.
7. Settlement and recovery: **not production-integrated**; store persistence,
   restart resolution, and recovery through the one-subtask AgentLoop remain
   open.

Overall plan acceptance: **incomplete**.

## Validation

- Persistent preparation, deployment composition, and generic preparation
  contract tests: **102 passed**.
- Ruff and `git diff --check`: passed.
- No Isaac Sim, Gateway Action, simulator step, or motion was run.
