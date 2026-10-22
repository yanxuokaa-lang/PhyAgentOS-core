# Implementation Review v15.7.0: LabUtopia Phase RPC and Durable Routes

Date: 2026-10-22 (Asia/Shanghai)

## Findings First

### Blocker: live route qualification and phase controllers are still absent

The worker protocol now accepts standard preparation and bounded phase RPCs,
but the default LabUtopia backend deliberately returns unavailable for both
measured route qualification and phase execution. It does not yet run Lula IK,
workspace limits, collision checks, or preserve one simulator controller/task
state across acquire, held pour, and place. No internal Tool falls back to the
legacy complete-cycle controller. This phase therefore does not make the
requested live reagent-pour task executable.

### Fixed: action dispatch no longer treats a cycle as a phase

The PAOS client sends acquire, pour, and place through execute_phase.
Missing phase support raises an explicit unavailable error; it cannot dispatch
to execute_cycle. The worker checks the current session scene revision before
phase dispatch and only advances that revision when the backend reports a
world change.

### Fixed: one canonical assignment route now covers held processing

LabUtopia composition owns a durable SQLite assignment store by default under
<lab_root>/outputs/paos/assignment-artifacts.sqlite3; injected stores remain
caller-owned. Acquire, held pour, and place can resolve the same canonical
assignment reference. Stored geometry/target route remains authoritative while
the current Tool request contributes operation and lifecycle fields.

## PAOS Architecture, Extensibility, Developer Guide, and AgentLoop

- PAOS Runtime remains the owner of invocation, cancellation, Tool receipts,
  possession projection, and the single outer subtask Action.
- Worker RPCs and LabUtopia scene/controller objects remain adapter-owned.
- The standard manipulation.prepare provider consumes the measured binding
  and trusted intent; the generic SubtaskExecutor persists its typed assignment
  and route arguments. Missing backend qualification stays unavailable.
- AgentLoop still sees one subtask PlanNode; no internal model turn is added.
- The public Tool contract was not widened with USD paths or SDK objects.
- Existing cycle Tools are not used as phase fallback.

## Validation

- No-motion Runtime, subtask, persistence, LabUtopia integration/engine, and
  worker-session tests: 135 passed.
- Ruff and compileall passed; git diff --check passed.
- One known pytest warning remains because asyncio_mode is unrecognized when
  plugin autoload is disabled.
- No Isaac Sim, Gateway service, camera/model inference, IK, collision query,
  or motion was run.

## Seven-Dimension Acceptance

| Dimension | Result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Not verified | No live RGB/depth/model binding was run. |
| 2. Binding and freshness | Partial | Existing measured-binding contracts are retained; no route is qualified by the live backend. |
| 3. Agent subtask granularity | Pass for no-motion contract | Internal Runtime Tools remain inside one outer Action; no live Agent/Gateway request was run. |
| 4. IK, workspace, collision | Not verified | Default backend reports route qualification unavailable. |
| 5. Grasp, hold, place state | Not verified | No phase controller is implemented in the default backend. |
| 6. Pour process feedback | Not verified | No held-pour phase executed. |
| 7. Settlement and recovery | Partial | Generic lifecycle tests pass; the default LabUtopia backend reports preparation unavailable, so a full composed LabUtopia sequence has not completed. |

## Decision

Accept only the worker RPC boundary, no-cycle-fallback behavior, durable-store
composition, and canonical held-route lookup as implemented components. The
requested LabUtopia-wired no-motion subtask has not passed: the default backend
returns unavailable before a route can be persisted and before acquire/pour/place
can run. The complete LabUtopia subtask and live-agent pour remain unaccepted.
Next, implement session-owned route qualification and phase controllers using
measured binding data; then pass the complete LabUtopia-wired no-motion subtask
before any live camera or Isaac Sim motion attempt.
