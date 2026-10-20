# Implementation Review v15.1.5: Provider Substitution Evidence

## Findings and disposition

- **Major fixed:** the generic perception binding had only one concrete test
  provider. A second independent provider now implements the existing PAOS Query
  port (`invoke_query`) and preparation port (`prepare_binding`) with different
  semantic categories, references, frame, calibration, and scene revision.
  The same `PerceptionBindingAdapter` produces a valid binding without a
  production-code or ToolSpec change.
- **No Blocker for this no-motion stage:** the test uses measured contract-shaped
  facts and explicitly keeps `motion_authorized=false`; it does not claim camera
  detection, IK, collision, or simulator execution.
- **Unrelated regression evidence:** the complete workflow test run reported
  `583 passed, 2 failed`. The failures are the pre-existing release manifest
  version/SHA mismatch (`test_grasp_propose.py` and `test_release_bundle.py`)
  associated with the user's separate RoboTwin workspace changes. They are not
  in the changed files and were not modified here.

## PAOS architecture review

- `PerceptionBindingAdapter` remains the generic choreography owner. Providers
  remain responsible for observation, understanding, proposal, capability
  discovery, and preparation mechanisms.
- No second Runtime, Coordinator, persistence store, revision owner, or
  Agent-facing PlanNode was introduced.
- The existing `PerceptionBinding`, `SubtaskExecutor`, `NodeSettlement`, and
  `CapabilityRuntime` ownership boundaries are unchanged.

## Extension-principle review

- The new fixture is intentionally not a LabUtopia subclass or copy. It uses a
  different provider object interface and semantic vocabulary (`sample_vial`,
  `mixing_vessel`) while consuming the same PAOS ToolSpec projection.
- Replacing the provider changes only provider construction and the semantic
  `BindingRequest`; the generic adapter, ToolSpec, AgentLoop route, and subtask
  contract remain unchanged.
- This proves one substitution boundary in no-motion tests. A live second
  environment remains future evidence, not an implied result.

## Developer-guide and AgentLoop review

- The test exercises Query composition only and does not bypass the documented
  `scene.observe -> scene.understand -> grasp.propose -> capabilities` order.
- The output remains an opaque `PerceptionBinding` consumed by the existing
  single-subtask PlanNode. No internal Tool becomes an Agent turn.
- The fixture cannot authorize motion; preparation is an evidence-producing
  provider boundary and returns `status=prepared` with `motion_authorized` absent.

## Robotics-safety review

- No actuator, camera driver, simulator process, Gateway, or live route was run.
- Frame, calibration, observation, scene revision, candidate, and preparation
  references are all checked by the existing adapter before the binding is
  emitted.
- The validation is contract/no-motion evidence only. It does not qualify IK,
  workspace, collision, gripper, or physical process behavior.

## Seven-dimension acceptance

| Dimension | Result | Evidence / remaining gap |
|---|---|---|
| 1. Perception source | Pass for provider substitution contract | Independent Query provider fixture produces observation and semantic entities; live RGB-D remains unverified. |
| 2. Binding/frame/calibration/freshness | Pass | Alternate scene, frame, calibration, freshness, candidate, and preparation lineage pass the same checks. |
| 3. Agent subtask granularity | Pass | No plan or AgentLoop code changed; existing one-subtask/one-settlement path remains covered by the focused suite. |
| 4. IK/workspace/collision | Partial | Preparation is injected and lineage-checked; no real planner or collision execution ran. |
| 5. Acquire/hold/release/place feedback | Partial | No physical-effect Tool ran; existing Runtime tests remain the source of contract evidence. |
| 6. Pour/stir process feedback | Partial | No process action ran; this stage only validates reusable binding inputs. |
| 7. Settlement/unknown/cancel/recovery | Pass for regression boundary | Existing subtask executor tests pass; this change adds no lifecycle owner or recovery path. |

## Verification

```text
7 passed: provider-neutral perception binding tests
28 passed: perception, Agent planning, subtask executor, and LabUtopia wiring subset
583 passed, 2 failed: complete pick-place/LabUtopia test directories
ruff check: passed for changed test file
git diff --check: pending final commit validation
Isaac Sim/Gateway/motion: not run
```

The two full-suite failures are recorded as unrelated workspace release-lock
drift, not suppressed or converted into success.
