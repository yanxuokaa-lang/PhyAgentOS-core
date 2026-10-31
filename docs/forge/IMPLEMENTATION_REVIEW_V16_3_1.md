# v16.3.1 single-arm capability review

## Findings

- **Major resolved:** The scene contains R01 and R02, but a caller could
  confuse entity existence with two-arm execution. Isaac preparation now fails
  closed with `unsupported_capability_topology` when the request is not exactly
  the measured single-arm `franka` capability.
- **Blocker avoided:** No `left`/`right` aliases, second assignment, USD
  teleport, or actuator command was added. Existing CapabilitySnapshot and
  PlanProposal remain the discovery and validation owners.

## Ownership

The Adapter owns measured topology, arm IDs, and the zero-motion provider
diagnostic. PlanProposal/AgentLoop own semantic requirements and capability
selection. Coordinator owns revision, admission, cancellation, and settlement.
Action remains disabled until a valid no-motion preparation result exists.

## Validation

- `test_single_arm_provider_rejects_bimanual_assignment_before_motion` covers
  the explicit capability failure.
- Existing phase-pipeline, PAOS integration, subtask, and recovery suites must
  remain green.
- No Isaac runtime, reset, grasp, or Action was started.

## Remaining risk

Actual dual-arm support still requires a second configured Articulation,
measured frames/limits/workspaces, planning-resource admission, collision
validation, and execution feedback. This change intentionally does not claim
that capability.
