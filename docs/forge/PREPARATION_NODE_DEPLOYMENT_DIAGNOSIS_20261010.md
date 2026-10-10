# Preparation Node Deployment Diagnosis (2026-10-10)

## Summary

The scoped preparation-reference fix was present in the checkout but not in the
RobotWin persistent-host executable used by the running Runtime. The installed
`pick-place-workflow 3.0.13` lock still selected
`robotwin20_persistent_host-1.0.3-linux-x86_64` with SHA-256
`7108b7e10dff24cbc49451abf1b446aec1bb84e2c958f47b36aef22aa8b94776`.
Updating Core/Skill source and restarting the same Node version could not deploy
the Adapter change because Forge runs the immutable artifact named by the
Runtime lock.

## Evidence From the Three Tasks

| Task | Last node | Authoritative result | Interpretation |
| --- | --- | --- | --- |
| `task_01931f149c3d43cd` | `red_prepare` | `status=unavailable`, `error.code=preparation_provider_error`, `failure_owner=runtime_adapter`; public error message is generic | Preparation failed before acquire. The task record alone does not preserve its lower-level cause. |
| `task_a117690aaa954152` | `red_prepare` | Same public error; Runtime preparation metrics report `ValueError: preparation reference already identifies different geometry` | Confirms a route-identity collision; no acquire Action was started. |
| `task_4ddbbc5295b94336` | `red_acquire` | `red_prepare` succeeded; acquire execution persisted as `unknown` without `invocation_id` or `attempt_id`, then CLI stop made the task terminal | Distinct Action reconciliation problem. The persisted evidence cannot prove whether Gateway rejected before admission or the response/identity was lost after submission. Do not retry it blindly. |

All three tasks used task-bound discovery and the same persisted Runtime snapshot.
Their failures are downstream of successful observation, understanding,
capabilities, binding, and `task.goal`; `motion_authorized=false` on read-only
Queries is not the cause.

The task-scoped URI is visible in the third task's durable `red_acquire`
selection, for example:

```text
preparation://<scene>/task_4ddbbc5295b94336/revision_7414106dff4e4d72/red_prepare/head_camera
```

This shows Coordinator projection emitted the scoped identity. It does not prove
the old Adapter consumed it successfully or identify the later Action unknown.

## PAOS Ownership and Repair

- Core owns generic preparation identity construction and Coordinator projection.
- The RobotWin Adapter owns route registration and resolution; it reuses the Core
  identity helper and owns the persistent route geometry registry.
- Forge Node artifacts are immutable. The Skill manifest's node artifact ID and
  SHA determine the executable loaded by the Runtime; a Skill version bump alone
  does not replace that executable.
- Gateway/Runtime continue to own Action admission, invocation identity,
  settlement, and unknown-effect truth. This fix does not relax those boundaries.
- AgentLoop continues through normal selection, Query settlement, Action
  admission, and reconciliation. A new preparation URI never authorizes motion.

The release repair publishes Node `1.0.4`, updates the Skill lock to that
artifact, and builds a new Skill bundle. Existing artifact SHA validation is
retained; no additional hash scheme or deployment gate is introduced.

## Validation Boundary

Release tests rebuild the executable archive from the current Adapter and
Workflow source and compare it to the manifest lock. Provider/Adapter tests
exercise task-scoped URI generation, same-intent idempotency, cross-task
isolation, and downstream Action reference validation without Gateway Actions.

The authorized stop/install/start sequence was completed after the no-motion
build checks. The active Runtime now reports Skill `3.0.14`, Node
`robotwin20_persistent_host-1.0.4-linux-x86_64`, Dora running, Gateway ready,
and all 11 required Tool contexts ready. Its embedded adapter path is a fresh
temporary payload extracted from the `1.0.4` Node. No AgentTask, live
Query/Action, camera read, simulator step, or physical motion was performed for
deployment verification.
