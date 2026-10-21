# Implementation Review v15.1.12: Task-Scoped Preparation

Date: 2026-10-21 (Asia/Shanghai)

## Scope and outcome

This stage moves manipulation preparation out of the generic perception binding
chain and into the selected PAOS subtask. `PerceptionBindingAdapter` now
composes observation, scene understanding, grasp proposal, and capability
Queries only. The `manipulation.execute_subtask` Runtime driver invokes the
no-motion `manipulation.prepare` Query with the Coordinator-resolved trusted
intent, validates the returned evidence and task assignment, then carries the
prepared references into the existing acquire/place Tools.

This directly addresses the earlier `LabUtopiaPerceptionAdapter` concern:
there is no LabUtopia-specific perception adapter in the implementation.
LabUtopia consumes the same `PerceptionBindingAdapter`; environment-specific
camera and execution behavior remains behind the provider/adapter ports.

## PAOS architecture review

- The PlanNode and Coordinator remain owners of semantic intent and task,
  revision, and node identity.
- The generic perception adapter owns only Query choreography and evidence
  binding. It has no simulator imports, Prim paths, or preparation provider.
- The Runtime subtask Action owns the internal sequence and records each Tool
  receipt, while AgentLoop sees one Action and one terminal NodeSettlement.
- Synchronous and Runtime subtask drivers both project the latest successful
  held-preparation arguments into placement, so a post-acquire scene revision
  is not silently replaced by the initial preparation context.
- `manipulation.prepare` produces the task-scoped assignment. PAOS Action
  contracts intentionally carry its `assignment_ref` as the artifact primary
  key; `PersistentActionEndpoint` resolves that reference and rejects a
  different task or assignment reference before invoking acquire/place.
- The environment resolver is responsible for resolving the canonical
  assignment artifact by that reference. A synthetic fixture cannot establish
  that a live LabUtopia resolver persists and retrieves the same artifact.

## Extension principles

The stable contract contains semantic references, measured geometry,
observation lineage, candidates, and capability evidence. Providers may differ
in sensor technology, category vocabulary, frame IDs, and storage references;
the adapter remains unchanged. A second independent provider fixture exercises
that replacement boundary. Environment mechanisms remain below the provider
ports; the generic layer does not branch on simulator or device identity.

No new hash, frozen baseline, or extra gate was added. Existing provenance,
assignment-reference, and Runtime caller checks address concrete mismatched or
stale-evidence failure cases using PAOS primary references and ordinary tests.

## Developer Guide and AgentLoop review

The path is:

`scene.observe -> scene.understand -> grasp.propose -> capabilities -> PlanNode selection -> manipulation.prepare -> acquire -> held preparation/process -> held preparation/place -> one NodeSettlement`

Preparation now happens after subtask selection and before the first motion
Action. Missing or mismatched preparation evidence fails within the subtask;
it does not cause an Agent turn between internal Tools. Runtime retains
individual invocation/attempt receipts for diagnosis and recovery. The outer
subtask settlement is the only Agent-facing completion boundary.

The current Runtime checks assignment task identity and the exact
`assignment_ref` returned by preparation. The live environment must make its
resolver lookup that authoritative reference; it must not reconstruct a
different assignment from object names or profile defaults.

## Seven-dimension acceptance

1. Perception correctness: **partial**. The generic Query flow and provider
   substitution are tested; no live camera observations were consumed.
2. Binding and freshness: **partial**. Observation, scene, frame, calibration,
   candidate, and capability lineage are checked in contract tests; physical
   sensor timing and calibration were not exercised.
3. Subtask-level AgentLoop boundary: **pass for Runtime contract**. Tests cover
   one outer Action, multiple internal Tool receipts, and one aggregate
   settlement without intermediate model turns.
4. IK, workspace, and collision: **contract-only**. The preparation Query
   requires qualified candidate checks, but no real planner or simulator
   preparation was run in this stage.
5. Execution state: **not live-verified**. Acquire/place and possession
   lifecycle were exercised with no-motion endpoints only.
6. Process feedback: **not live-verified**. No pour/stir controller feedback,
   trajectory, or task success measurement was collected.
7. Subtask settlement and recovery: **partial**. Success, known failure,
   unknown outcome, cancellation, stale binding, and Coordinator identity are
   covered by contract tests; real environment restart/reconciliation and
   assignment artifact persistence remain unverified.

## Validation

- Focused provider-neutral perception, planning, subtask Runtime, persistent
  action, and LabUtopia integration tests: **96 passed**.
- Broader workflow/planning/LabUtopia suite: **658 passed, 2 failed** on the
  existing RoboTwin node-version (`1.0.15` expected, `1.0.16` manifest) and
  immutable bundle SHA lock mismatch. These failures are outside this change.
- Ruff, `compileall`, and `git diff --check`: passed.
- No Isaac Sim, Gateway Action, simulator step, or robot motion was run.

## Remaining acceptance work

The full solution is **not accepted**. Remaining work is to wire and verify a
real observation provider, persist and resolve the exact task assignment
artifact through the environment acquire/place resolver, and verify the
post-acquire/post-process scene-revision transitions against the production
Action schemas. The current test endpoints are intentionally no-motion and do
not establish that an assignment prepared against the initial scene remains a
valid placement assignment after world-changing internal Actions. Then run one
complete reagent-pour subtask in Isaac Sim with observed execution feedback,
followed by the longer two-reagent-and-stir task. The same seven dimensions must
be reviewed again against those artifacts. No LabUtopia-specific perception
adapter should be introduced to complete that wiring.
