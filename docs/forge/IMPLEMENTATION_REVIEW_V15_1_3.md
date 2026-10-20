# Implementation Review v15.1.3: Provider-Neutral Perception Binding

## Findings and disposition

- **Major fixed:** the first design boundary would have required a
  `LabUtopiaPerceptionAdapter` per environment. `PerceptionBindingAdapter` now
  owns only PAOS Query choreography and semantic selection; providers own
  sensor capture, understanding, grasp proposal, and preparation.
- **Major fixed:** preparation results could have been paired with a fresh
  observation without checking their observation, scene, frame, or calibration
  lineage. The adapter now rejects that result before a binding is emitted.
- **No Blocker remaining for this no-motion stage:** no USD path, Prim name,
  actuator command, or simulator ground truth enters the generic adapter.

## PAOS architecture review

- Existing `CapabilityRuntime`, Query ToolSpecs, `PerceptionBinding`,
  `SubtaskActionEndpoint`, receipts, and `NodeSettlement` remain the owners of
  lifecycle and settlement state.
- `register_subtask_tool()` is a small composition seam. It registers one
  Agent-facing subtask boundary after Runtime construction; internal Tools stay
  below AgentLoop.
- `PerceptionBindingAdapter` is in the provider-neutral workflow package. The
  LabUtopia adapter only wires it after the complete provider chain is present.

## Extension-principle review

- New environments provide the same PAOS Query and preparation ports and do not
  subclass or copy a LabUtopia implementation.
- Semantic categories/selectors and an optional destination reference factory
  are task inputs. Environment paths are not accepted by the public binding.
- The adapter does not add a second registry, scheduler, persistence store, or
  motion authorization mechanism.

## Developer-guide and AgentLoop review

- Tool discovery exposes `manipulation.execute_subtask` only when the host
  injects a ready generic perception adapter. Otherwise the Runtime remains
  query/action compatible without advertising an ungrounded subtask action.
- One subtask still maps to one Agent-facing PlanNode and one outer Runtime
  invocation. The four Query calls and preparation provider run before the
  binding is consumed; internal acquire/process/place receipts do not create
  Agent turns.
- Semantic ambiguity, unavailable Query results, stale provenance, and stale
  preparation fail closed and leave motion authorization false.

## Robotics-safety review

- Observation, understanding, grasp proposal, preparation, admission, and
  execution remain separate stages.
- The adapter requires a concrete frame, calibration reference, freshness
  bound, same scene revision, candidate set, and provider-owned preparation
  references before producing a binding.
- `orientation_xyzw: null` in the envelope-derived measured pose explicitly
  means the envelope did not measure object orientation; the executable grasp
  orientation must come from the grasp candidate, not a fabricated default.
- This stage is no-motion. No Isaac Sim process, Gateway call, or physical
  actuator was run.

## Seven-dimension acceptance

| Dimension | Result | Evidence / remaining gap |
|---|---|---|
| 1. Perception source | Pass for provider-neutral contract | Binding is composed from PAOS Query outputs; live LabUtopia RGB-D provider still needs a separate runtime run. |
| 2. Binding/frame/calibration/freshness | Pass | Query and preparation provenance are checked; stale and mixed-scene results fail closed. |
| 3. Agent subtask granularity | Pass | Existing single-PlanNode/subtask settlement path is unchanged; wiring adds no Agent-facing intermediate nodes. |
| 4. IK/workspace/collision | Partial | The adapter consumes provider-owned preparation evidence; no live Lula/IK or collision execution was run. |
| 5. Acquire/hold/release/place feedback | Partial | Runtime receipts remain the source of truth; no LabUtopia subtask execution was run in this stage. |
| 6. Pour/stir process feedback | Partial | Process feedback remains below the subtask boundary; no live pour/stir measurement was produced here. |
| 7. Settlement/unknown/cancel/recovery | Pass | Existing Runtime subtask driver and one outer settlement remain active; refresh uses the new adapter and rejects stale candidate lineage. |

## Verification

```text
6 passed: provider-neutral perception binding tests
45 passed: LabUtopia integration, engine/profile, and related PAOS regressions
20 passed: multi-object AgentLoop regression with pytest-asyncio enabled
ruff check: passed
python -m compileall: passed
git diff --check: passed
```

The first multi-object command intentionally disabled pytest plugin discovery
and reported unsupported async tests; it was rerun with the repository's
pytest-asyncio configuration and passed. No motion was authorized or executed.
