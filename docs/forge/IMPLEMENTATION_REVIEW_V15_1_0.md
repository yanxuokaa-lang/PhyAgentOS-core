# Implementation Review v15.1.0: PAOS Laboratory Subtasks

## Scope

This review covers the first implementation stage of the LabUtopia/PAOS
subtask design. It is a no-motion planning and orchestration change. It does
not claim live Isaac Sim execution, camera perception, IK qualification, or
physical feedback.

## PAOS architecture review

- Existing `PlanGraph`, `PlanNode`, `NodeSettlement`, and Tool receipt concepts
  remain the owners of task state. No second scheduler or settlement store was
  introduced.
- `compose_subtask_plan()` exposes one `manipulation.execute_subtask` node per
  semantic subtask. `verify` joins those nodes rather than individual Tools.
- `SubtaskExecutor` is below the AgentLoop model boundary. Its receipts are
  internal evidence and do not create additional Agent turns.
- The public Tool contract is provider-neutral and contains no USD Prim path or
  simulator actuator access.

## Extension and developer-guide review

- Existing pick/place projection remains available for compatibility.
- The new contract uses injected `SubtaskInvoker`; the executor does not import
  or call Isaac Sim.
- The operation sequence is constrained to the governed acquire/prepare/process/
  prepare/place flow. A custom sequence cannot silently bypass the possession
  boundary.
- Input binding includes measured geometry, grasp candidate provenance, frame,
  calibration, scene revision, and freshness. A stale binding is rejected.

## AgentLoop review

The implementation changes planning shape, not the existing AgentLoop reducer.
The plan graph has one executable node per subtask, so intermediate Tool receipts
cannot become Agent-facing nodes. Runtime Action lifecycle integration is
intentionally not claimed until a driver can poll existing Runtime invocations
without blocking or bypassing cancellation/unknown semantics.

## Seven-dimension acceptance

| Dimension | Result | Evidence / gap |
|---|---|---|
| Perception source | Partial | Structured observation-bound binding; no live camera provider yet |
| Binding/frame/calibration/freshness | Pass for contract | Pydantic validation and stale rejection; no live scene join yet |
| Agent subtask granularity | Pass | One execute-subtask node plus verify join |
| IK/workspace/collision | Not evaluated | No motion in this stage |
| Acquire/hold/release/place feedback | Partial | State propagation and short-circuit tests; no Runtime-backed feedback |
| Pour/stir process feedback | Partial | Receipts preserve responses; no measured process execution |
| Settlement/unknown/cancel/recovery | Pass for no-motion | One NodeSettlement; unknown and cancel stop the sequence |

## Verification

```text
12 passed: planning + subtask executor tests
76 passed: persistent runtime, multi-object agent, composite manipulation regressions
ruff check: passed
compileall: passed
git diff --check: passed
```

## Next gate

Before live Isaac Sim acceptance, implement a Runtime-backed subtask Action
driver that invokes existing Tool endpoints through their normal start/poll/
cancel lifecycle, then add a perception adapter that supplies the complete
acquire/place provenance fields from the observation/understanding/grasp chain.
