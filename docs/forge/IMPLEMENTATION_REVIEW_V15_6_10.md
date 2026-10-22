# Implementation Review v15.6.10: Standard Preparation Binding Wiring

Date: 2026-10-22 (Asia/Shanghai)

## Findings First

### Major fixed: measured binding stopped at the legacy cycle provider

The standard `manipulation.prepare` Query now accepts a provider-neutral
`perception_binding` and `process_type`. The endpoint checks reference identity,
freshness, finite JSON values, and request/binding consistency before invoking a
provider. The public schema contains semantic and measured fields only; it does
not contain simulator paths, SDK handles, or model-vendor fields.

### Major fixed: LabUtopia standard preparation had no resolver seam

`LabUtopiaCycleProvider.prepare()` now consumes the same binding used by the
subtask, calls the injected target resolver, and forwards the resulting
adapter-private target to an engine-owned `prepare_manipulation` port. The
provider returns only the engine's readiness, assignment, and route evidence;
it does not fabricate assignment or route data when the engine lacks that port.

### Remaining Blocker: live LabUtopia engine does not yet publish typed assignments

The standard provider is wired and fail-closed, but the current LabUtopia engine
implementation exposes `prepare_cycle`, not a complete `prepare_manipulation`
route qualification that returns a typed `ArmAssignment` and route arguments.
Consequently a real subtask cannot yet reach `object.acquire`/`object.place`
through the durable assignment store. This is an explicit unavailable result,
not a fake success.

## Architecture Review

- PAOS Core owns the binding contract, freshness/identity validation, Tool
  lifecycle, receipts, assignment-store persistence, and one subtask settlement.
- The LabUtopia adapter owns opaque-reference resolution, scene-node mapping,
  coordinate conversion, IK/collision qualification, and controller route data.
- `SubtaskExecutor` and `RuntimeSubtaskDriver` remain the only internal sequence
  owners; `acquire -> held preparation -> pour/stir -> held preparation -> place`
  still produces one Agent-facing settlement.
- No model-vendor, simulator path, or environment-specific class is added to
  PAOS Core contracts. No new hash or broad gate was introduced.
- A missing engine preparation port or missing typed assignment fails closed;
  the provider never turns an unavailable route into `available`.

## Validation

- Standard preparation, assignment, subtask, persistent-runtime, and LabUtopia
  no-motion suites: `77 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No Isaac Sim, Gateway Action, IK, collision query, hardware IO, or motion ran.

## Seven-Dimension Acceptance

| Dimension | Result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Standard prepare receives the same measured binding; live camera/model recognition is not proven. |
| 2. Binding and freshness | Pass for this boundary | Identity, provenance, freshness, and finite-value checks are enforced before provider invocation. |
| 3. Agent subtask granularity | Pass for generic route; Partial for LabUtopia | Existing executor/runtime tests retain one outer invocation and settlement; LabUtopia typed route publication remains unavailable. |
| 4. IK, workspace, collision | Not verified | No live engine route qualification or simulator planner ran. |
| 5. Grasp, hold, place state | Not verified | No acquire/place Action or physical state transition ran. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback ran. |
| 7. Subtask settlement and recovery | Partial | Generic receipts, assignment persistence, and durable route lookup pass; no LabUtopia multi-tool execution was possible without typed assignments. |

## Decision

This phase is accepted as a provider-neutral standard-preparation wiring
increment. The complete laboratory task remains unaccepted. The next required
implementation is an engine/provider route qualification that consumes the
resolved target and trusted intent, returns one typed assignment plus route
arguments, and then proves one no-motion subtask result over the full sequence
before live Isaac execution is considered.
