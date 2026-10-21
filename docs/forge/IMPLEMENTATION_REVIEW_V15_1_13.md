# Implementation Review v15.1.13: Production Tool Schema Closure

Date: 2026-10-21 (Asia/Shanghai)

## Findings and disposition

No production-code Blocker was found in this stage's tested Runtime projection. The prior acceptance gap was that internal subtask Action inputs were exercised with reduced test-only ToolSpecs, so passing tests did not prove compatibility with the public acquire/place/held-preparation schemas. The regression now registers the production ToolSpecs and runs one complete no-motion subtask through preparation, acquire, held preparation, process, second held preparation, and place.

The exercised provenance sequence is:

```text
initial observation / scene-1
  -> initial manipulation.prepare assignment
  -> object.acquire (scene-1) -> scene-2
  -> refresh binding and held preparation (scene-2)
  -> process (scene-2) -> scene-3
  -> refresh binding and held preparation (scene-3)
  -> object.place using the latest preparation and assignment -> scene-4
```

The regression asserts that acquire uses the initial preparation's canonical
assignment reference, and place uses the second held preparation's assignment
reference and scene revision. A separate Runtime endpoint regression confirms
that acquire/place reject a resolver response whose assignment reference does
not equal the public canonical `assignment_ref`.

## PAOS architecture review

- `CapabilityRuntime` remains the lifecycle owner for each internal Action; this change adds tests only and does not introduce another Runtime or settlement state machine.
- `RuntimeSubtaskDriver` retains internal Tool receipts and exposes one terminal `manipulation.execute_subtask` result. No Agent turn is introduced between acquire, process, and place.
- Production ToolSpecs, not duplicated test schemas, define the Action input boundaries exercised by the new end-to-end fixture.
- Assignment references remain PAOS artifact primary references. The generic Runtime verifies exact reference and task ownership; it does not claim that a LabUtopia host has durable artifact storage unless its injected resolver demonstrates that behavior.

## Extension principles, Developer Guide, and AgentLoop

The tested path is environment-neutral: it uses provider contracts and PAOS ToolSpecs without a LabUtopia-specific perception class. The production schema is the stable boundary; test endpoints provide only no-motion observations/results. AgentLoop sees one selected semantic PlanNode and one terminal settlement, while internal invocation/attempt records remain diagnostic evidence owned by Runtime.

No hash, new contract freeze, or extra admission gate was added. The concrete gap was inadequate test coverage of existing published schemas; ordinary schema validation and focused Runtime tests address it.

## Robotics safety

All test endpoints are no-motion. The test does not authorize execution or prove planner, workspace, collision, grasp, pour, stir, or release behavior. Frame and calibration values remain attached to the measured binding and are checked by existing preparation contracts. No Isaac Sim, Gateway Action, simulator step, or robot motion was started.

## Seven-dimension acceptance

1. Perception correctness: **partial**. Provider-neutral binding remains in place, but no real RGB/depth/segmentation observation was consumed.
2. Binding and freshness: **partial**. Production Action inputs and scene revisions are exercised; live sensor timestamps, calibration, and observation refresh are not verified.
3. Subtask-level AgentLoop boundary: **pass for Runtime contract**. One outer Action contains six internal Tool receipts and produces one terminal result with no intermediate Agent turn.
4. IK, workspace, and collision: **contract-only**. Production prepare schema is exercised with prepared-candidate fixture evidence; no live IK, collision engine, or workspace check was executed.
5. Execution state: **contract-only**. Acquire/place arguments and possession results are fixture-backed; no simulated object was moved or physically reconciled.
6. Process feedback: **not verified live**. No controller trajectory or measured pour/stir feedback was collected.
7. Subtask settlement and recovery: **partial**. Scene transitions, assignment reference mismatch, unknown/cancel paths, and one outer settlement have no-motion coverage; durable assignment lookup and process-restart reconciliation remain unverified.

## Validation

- Focused subtask, persistent Runtime, and LabUtopia wiring suite: **45 passed**.
- Ruff on changed Python files: passed.
- `git diff --check`: passed.
- Pytest emitted the existing `asyncio_mode` configuration warning.
- Isaac Sim/Gateway/live motion: not run.

## Remaining acceptance blockers

The overall solution is not accepted. Next implementation/evidence stages are:

1. Supply a real observation source and understanding/grasp providers that return measured geometry, candidates, frame/calibration, freshness, and scene revision from sensor evidence.
2. Supply a durable environment resolver that loads the exact assignment artifact by `assignment_ref` for acquire and the latest held-preparation assignment for place; test persistence across Runtime restart without reconstructing assignment from object names/profile data.
3. Run no-motion readiness with the deployed production providers and verify their provenance and actual planner/collision/workspace results.
4. Execute one reagent pour subtask in Isaac Sim and collect timestamped observations, measured process feedback, release/retreat evidence, and exactly one subtask settlement.
5. Execute the two-reagent-then-stir long-horizon task and verify one settlement per semantic subtask plus one final task verification.

These are evidence-bearing environment/runtime tasks, not grounds to introduce an
environment-specific perception adapter or to label fixture tests as live
acceptance.
