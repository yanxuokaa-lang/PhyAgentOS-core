# Implementation Review v16.9.7

## Findings

### Major - fixed: transport failure still allowed blank-worker recreation

`LabUtopiaBackend` originally cleared the failed session but its next
prepare/qualify/execute call could immediately create another worker without a
fresh observation. The new worker could not recover the old revision, but this
still violated the required reset/observation recovery boundary.

Resolution: the Backend now records an Adapter-private
`_session_recovery_requires_observation` state when the matching session is
invalidated. Motion preparation/probing/execution return
`fresh_observation_required` without creating a worker. A successful transport
round trip through a new `observe` call establishes the next session and clears
the state.

### Blocker

None.

### Remaining Major

None.

## Architecture and safety acceptance

- Public AgentLoop, Coordinator and Tool contracts are unchanged.
- Search budget, transport validity and recovery remain inside the Isaac
  Adapter boundary.
- Provider-level unavailability does not destroy a healthy scene; transport
  failure cannot masquerade as a recoverable old scene.
- Preparation timeout is zero-motion and known. Execute transport loss remains
  unknown and conservatively assumes world change may have started.
- No motion feasibility or collision criterion was weakened.

## Evidence

- Focused tests: 222 passed.
- Full Adapter/executor tests: 488 passed, 2 skipped.
- Ruff, compileall, JSON parsing and whitespace checks pass.
- Fresh no-motion run stops before R05 Action with zero Action records.
- Independent native reset probe records zero commands and open finger joints.
