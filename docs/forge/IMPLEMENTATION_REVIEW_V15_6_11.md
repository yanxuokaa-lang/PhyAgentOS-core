# Implementation Review v15.6.11: Internal Subtask Tool Dispatch

Date: 2026-10-22 (Asia/Shanghai)

## Findings First

### Fixed: composite subtask Actions had no internal Runtime registrations

The LabUtopia composition disabled legacy acquire/place and held-operation
registration, while `RuntimeSubtaskDriver` dispatched those Tool IDs through
the Runtime. The composition now registers the required endpoints as internal
Runtime entries. They retain the existing Runtime invocation, cancellation,
and receipt lifecycle.

### Fixed: internal Tools were otherwise externally discoverable and callable

The capability Runtime now distinguishes public and internal registrations.
Gateway discovery, detail, context, Query, and Action dispatch expose public
registrations only. The subtask driver uses explicit internal Query/Action
methods. LabUtopia disables legacy cycle registrations so the Agent-facing
workflow remains the single `manipulation.execute_subtask` Action rather than
an alternative full-cycle Action.

### Fixed: a delayed Isaac camera session prevented generic Agent-route wiring

Composition previously treated `observation_ready=False` as proof that an
ObservationSource could not capture. The default worker creates its camera
session on first capture, so this conflated interface capability with current
sensor availability. Composition now requires the provider-neutral `capture`
or `query` port; each actual `scene.observe` call still validates returned
sensor data and fails unavailable when the session/camera is absent. This does
not claim live perception.

### Remaining Blocker: the engine has no phase-level manipulation backend

The Runtime registration fix does not make the current LabUtopia engine
executable as a multi-Tool task. Its backend exposes `execute_cycle` for the
whole pick/pour/place cycle and has no phase-level `prepare_manipulation`,
`acquire`, `pour`, or `place` route. Starting an internal Action against that
engine cannot provide the requested measured assignment and phase feedback.
The engine must gain a persistent, session-owned measured route and bounded
phase execution before the composite task is available.

## PAOS Architecture, Extensibility, Developer Guide, and AgentLoop

- PAOS Runtime remains the only owner of invocation, cancellation, and
  terminal lifecycle; the subtask driver composes its existing lifecycle.
- Internal Tools use the same ToolSpec and endpoint semantics. Their visibility
  is restricted at the provider-neutral Runtime/transport boundary rather than
  by a LabUtopia-specific Agent tool list.
- Environment-specific scene mapping and motion remain in the adapter/engine.
- Agent plan compilation still creates one `manipulation.execute_subtask`
  PlanNode; acquire/prepare/process/place remain internal calls and do not add
  Agent model turns.
- No hash, new public ToolSpec field, or motion-authorization shortcut was
  added. Missing phase execution remains unavailable instead of falling back
  to the legacy cycle.

## Validation

- Focused Runtime, subtask, and LabUtopia wiring tests: `40 passed`.
- Semantic task creation, PlanGraph compilation, and subtask tests: `38 passed`
  in a separate run (overlapping subtask tests are not added to the first count).
- Updated Runtime/LabUtopia focused tests after delayed-camera wiring:
  `41 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Tests verify internal endpoint lifecycle and reject Gateway discovery/detail/
  context/invocation. No Isaac Sim, Gateway service, IK, collision query, or
  motion ran.

## Seven-Dimension Acceptance

| Dimension | Result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Not verified | No live camera/model binding in this phase. |
| 2. Binding and freshness | Partial | Existing contracts remain; no live route consumes the binding. |
| 3. Agent subtask granularity | Pass for no-motion contracts; not live | PlanGraph compilation and one outer Runtime Action are covered; no live Agent/Gateway task ran. |
| 4. IK, workspace, collision | Not verified | No phase-level route qualification or planner ran. |
| 5. Grasp, hold, place state | Not verified | No engine phase Action ran. |
| 6. Pour process feedback | Not verified | No held pour Action ran. |
| 7. Settlement and recovery | Partial | Generic subtask lifecycle tests pass; LabUtopia cannot yet run the full internal sequence. |

## Decision

Accept this Runtime visibility/lifecycle and delayed-source composition
increment only. The six-item LabUtopia task remains unaccepted. Current
environment preflight found Isaac Sim and PyTorch installed in the LabUtopia
Python 3.11 environment and an RTX 5060 Ti, but the active process has no
`OMNI_KIT_ACCEPT_EULA`; more importantly, the engine still has no engine-owned
standard route qualification or session-backed phase Actions. Next work must
implement those mechanisms, then prove a complete no-motion LabUtopia subtask
before any Isaac Sim execution attempt.
