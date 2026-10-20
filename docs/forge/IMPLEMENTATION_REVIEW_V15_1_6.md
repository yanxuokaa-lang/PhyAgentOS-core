# Implementation Review v15.1.6: Observation Ownership Seam

## Findings and disposition

- **Major fixed:** the LabUtopia Runtime composition implicitly used the cycle
  Action client as the observation source. `LabUtopiaCycleClient` owns
  `start/poll/cancel/stop` and does not provide a sensor contract, so a complete
  generic perception chain could be advertised while `scene.observe` had no
  valid source. `build_persistent_runtime()` now accepts an explicit generic
  `observation_source`; `build_labutopia_runtime()` forwards it unchanged.
- **Compatibility preserved:** the standard source contract is
  `capture(request)`. A small PAOS-side compatibility adapter also accepts an
  existing host `query("observe", request)` port during migration. No new
  environment-specific perception class or ToolSpec was added.
- **No Blocker for this no-motion stage:** missing observation methods fail at
  the Query boundary with an explicit error; no fake observation or motion
  authorization is produced.
- **Unrelated regression evidence:** the complete workflow test run reported
  `586 passed, 2 failed`. One test still expects Node `1.0.15` while the Skill
  manifest declares `1.0.16`; the package-lock test builds from the current
  dirty/untracked RoboTwin workspace and obtains a digest different from the
  manifest. Neither failure is in changed files and no release metadata or
  user workspace content was modified.

## PAOS architecture review

- `PersistentObservationSource` is a thin provider-port adapter. It does not
  own Runtime state, scene revision, settlement, or action lifecycle.
- `PersistentActionEndpoint` and `LabUtopiaCycleClient` remain action owners;
  ObservationEndpoint remains the public observation-contract owner; the
  environment supplies the source implementation.
- `PerceptionBindingAdapter`, `SubtaskExecutor`, `CapabilityRuntime`, and
  `NodeSettlement` are unchanged. One subtask remains one Agent-facing node and
  one settlement.

## Extension-principle review

- Any environment can inject a camera/depth provider implementing `capture()`;
  the generic workflow and ToolSpec do not name LabUtopia, Isaac Sim, MuJoCo,
  or a scene node.
- The legacy `query("observe")` path is an adapter compatibility path, not a
  second public semantic contract. It can be removed after host migration.
- Action and observation providers can now be replaced independently, which
  prevents an execution backend from becoming an accidental perception owner.

## Developer-guide and AgentLoop review

- The Agent still sees `scene.observe` through the normal Runtime Query route;
  the source seam is below Tool discovery and does not create an extra Agent
  turn.
- `manipulation.execute_subtask` registration remains conditional on a ready
  provider-neutral binding adapter. The change does not expose internal
  acquire/prepare/process/place nodes.
- Provider errors remain Query failures and do not become successful bindings.

## Robotics-safety review

- No Isaac Sim process, Gateway call, simulator step, actuator, or live route
  ran in this stage.
- Observation still must pass the existing frame, calibration, freshness,
  artifact, and scene-revision validation before downstream binding.
- The new seam only supplies input evidence; it cannot set `motion_authorized`
  and does not bypass preparation, admission, collision, or stop handling.

## Seven-dimension acceptance

| Dimension | Result | Evidence / remaining gap |
|---|---|---|
| 1. Perception source | Pass for ownership/wiring contract | Explicit source is used by `scene.observe`; live LabUtopia RGB-D capture remains unverified. |
| 2. Binding/frame/calibration/freshness | Pass for Runtime boundary | ObservationEndpoint retains all existing identity and freshness checks; downstream live binding remains unverified. |
| 3. Agent subtask granularity | Pass | No plan or AgentLoop node shape changed; focused Runtime/subtask tests pass. |
| 4. IK/workspace/collision | Partial | Preparation remains provider-owned and no-motion; no live planner/collision execution ran. |
| 5. Acquire/hold/release/place feedback | Partial | Action client remains separate and no physical-effect action ran. |
| 6. Pour/stir process feedback | Partial | No process action ran; previous measured-cycle evidence remains separate. |
| 7. Settlement/unknown/cancel/recovery | Pass for ownership regression | Runtime lifecycle and subtask settlement owners are unchanged; failure-path tests pass. |

## Verification

```text
29 passed: persistent Runtime and LabUtopia wiring tests
586 passed, 2 failed: complete workflow/LabUtopia directories
ruff check: passed
compileall: passed
git diff --check: passed after log formatting correction
Isaac Sim/Gateway/motion: not run
```

The two full-suite failures remain recorded as unrelated release-lock drift and
are not suppressed or converted into success.
