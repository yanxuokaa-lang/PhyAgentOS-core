# Implementation Review: v16.9.1

## Findings

1. **Major, unresolved — R03 acquisition ends with uncertain possession.**
   The fresh Action passes complete readiness and starts actual motion, but
   stops in lift with `physical_grasp_lost`. Because world change started and
   possession is uncertain, R04 and stirring correctly remain blocked. This
   version must not be accepted as completing the requested workflow.
2. **Fixed — configured support prim did not cover its PhysX descendant.**
   `/World/table` now matches `/World/table/surface/mesh` only inside the
   existing support-contact window. The prior exact equality caused a known
   zero-motion `payload_collision` during initial lift preparation.
3. **Fixed — prefix collision is explicitly excluded.** `/World/tableware/...`
   does not match `/World/table`, and the table descendant remains an obstacle
   outside the support window.

## Architecture

- The change stays in Isaac Adapter collision-path interpretation.
- AgentLoop retains semantic ordering, opaque selection and lifecycle ownership.
- The Provider candidate set and preparation evidence chain are unchanged.
- No public Tool field, USD path, collision margin, IK tolerance or recovery
  policy is added to the generic layer.
- Failure remains fail-closed: uncertain possession stops later subtasks.

## Evidence grades

- **Contract evidence:** 467 Adapter/executor tests pass, 2 native USD tests
  skip; Ruff, compileall and whitespace checks pass.
- **Provider evidence:** the same-capture R03 candidate set and process features
  are preserved through task-affordance preparation.
- **Preparation evidence:** candidate 57 passes full readiness after the support
  path repair.
- **Live execution evidence:** the controller reaches close and lift and writes
  a 19.93-second phase video. Acquire fails with unknown outcome; no pour,
  return, R04 or stir execution evidence exists.

## Acceptance

Accept the support-path repair, not the full workflow. The next change must use
the measured phase feedback to separate persistent contact loss from a single
zero-load interval after an already-qualified grip, while preserving bilateral
initial-load confirmation, transform tolerances and fail-closed settlement.
