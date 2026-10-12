# Scene Understanding Provider Failure Diagnosis - 2026-10-12

## Scope

This record covers the latest `task_e37a4626b085484f` failure and the earlier
provider, grounding, preparation, and unknown-Action incidents. It is a
provider-neutral PAOS diagnosis; it does not add RGB, color, object, target, or
benchmark-specific behavior.

## Authoritative latest evidence

- `after_red_observe` and `after_red_capabilities` succeeded after the red
  placement.
- Qwen primary reported an error at `2026-10-11T03:12:50Z`.
- GPT fallback reported `available` at `2026-10-11T03:13:30Z`, with the
  diagnostic class describing the Qwen primary failure.
- The persistent host then logged
  `single-view perception failed: stage=proposal error_type=ProcessWorkerError`.
- The persisted Query response was `status=unavailable`,
  `understanding_provider_error`, `failure_stage=provider`,
  `retryable=false`, `provider_route=gpt-6.1-sol-high`,
  `provider_error_class=transport`.
- Core correctly recorded `readiness=ready` and `recovery_mode=replan` for this
  task. No Action was replayed and no new motion was authorized.

## Causal chain

```text
Qwen semantic provider failure
  -> GPT fallback semantic result available
  -> primary-view metric enrichment begins
  -> LocateAnything proposal worker lifecycle/transport failure
  -> SingleViewPerceptionInference raises ProcessWorkerError
  -> generic endpoint projects failure_stage=provider
  -> persisted record loses the failing stage and recovery owner
```

The final failure is therefore an Adapter observability and contract-projection
defect. It is not evidence that GPT fallback failed, and it is distinct from:

- unknown physical Action effects, which require Runtime-owned world
  reconciliation and fail-closed grounding;
- preparation geometry ambiguity, which is a planning/provider geometry result;
- an unavailable semantic provider chain, which may enter the existing bounded
  provider-block lifecycle.

## PAOS ownership and repair

- Runtime/worker owns process lifecycle, return code, bounded stderr metadata,
  and whether a metric stage can produce evidence.
- The RobotWin Adapter owns mapping those facts to provider-neutral stage and
  retryability fields. It must not expose arbitrary exception text or authorize
  motion.
- Core owns response validation, persisted Query settlement, and the predicate
  that distinguishes a semantic provider block (`failure_stage=provider`,
  `retryable=false`) from a recoverable enrichment failure.
- AgentLoop owns the handoff: provider-blocked semantic failures wait for the
  governed readiness/replan lifecycle; metric enrichment failures return to the
  ordinary bounded recovery/replan path. No Action is replayed automatically.

## Safety and convergence

The repair remains Query-only. Missing metric evidence continues to block
scene binding and all downstream motion. `motion_authorized=false`, calibration,
workspace, collision, IK, admission, Action terminal settlement, and Runtime
possession truth are unchanged. A worker restart or retry is not performed by a
scene Query invocation; it is an operator/Runtime lifecycle responsibility.

## Verification boundary

The regression suite uses fake semantic and worker providers only. It verifies
stage/error projection and AgentLoop classification without starting Runtime,
reading cameras, advancing simulation, or executing physical Actions.
