# Preparation Failure Recovery Contract Diagnosis

## Scope

This diagnosis records the AgentLoop recovery semantics exposed by the same
`task_5f6efbc4e2d94061` preparation failure. It separates Runtime-provider faults
from scene-evidence refresh and semantic replanning.

## Observed Recovery Facts

The failed `manipulation.prepare` result persisted:

```text
status: unavailable
failure_owner: runtime_provider
error.code: route_materialization_invalid
invocation_id: null
world_change_started: false
```

The Agent recovery decision was `stop` and correctly reasoned that a Runtime
configuration/identity failure cannot be repaired by re-observing, regenerating
grasp candidates, replaying execution, or replacing the semantic PlanGraph.

No Action was started, so no effect reconciliation or physical retry was needed.

## Contract Contradiction

`PreparationProviderError` currently defaults to:

```text
failure_owner=runtime_provider
retryable_in_revision=false
requires_replan=true
recommended_action=replan_from_provider_result
```

Those defaults describe two incompatible ownership decisions. A provider-owned,
non-retryable static configuration fault is outside the Agent's semantic plan and
cannot be corrected by a replacement graph. The Agent happened to stop because it
interpreted the detailed record correctly, but the durable result still invites a
future model or recovery policy to replan.

## Recovery Taxonomy

Recovery must be selected from structured durable facts, not parsed from prose.

| Failure class | Owner | Same revision | Replan | Recommended action |
|---|---|---:|---:|---|
| transient provider timeout with unchanged valid inputs | runtime_provider | yes | no | retry_provider_query |
| stale or incomplete declared observation lineage | evidence | no | yes | refresh_declared_evidence |
| candidate-specific geometry rejection | planning evidence | continue other candidates | no | inspect_candidate_results |
| exhausted valid candidates | agent planning | no | yes | revise_semantic_plan |
| static profile/schema/materializer configuration | runtime_provider | no | no | fix_runtime_contract |
| unknown Action effect | runtime/action | no | no | reconcile_invocation |

The classification must be based on generic error categories/codes emitted at the
provider boundary. It must not inspect colors, benchmark layouts, node names,
camera names, or natural-language error text.

## Architecture-Aligned Repair

1. Keep `PreparationProviderError` as the Core public diagnostic carrier. Its
   defaults must be internally consistent for a generic Runtime-provider fault:

   ```text
   retryable_in_revision=false
   requires_replan=false
   recommended_action=fix_runtime_contract
   ```

2. Call sites that own recoverable evidence or timeouts must continue to set their
   explicit semantics. Evidence lineage failures remain
   `refresh_declared_evidence`; bounded transient timeout handling remains an
   explicit provider retry policy.
3. `PersistentRouteBuilder` must classify static materializer/profile/schema
   failures explicitly at the Adapter boundary. Candidate rejection continues to
   the next candidate; it must not become a provider fault.
4. AgentLoop remains autonomous: it receives the structured failure and decides
   stop/retry/replan. Coordinator and Runtime do not automatically observe,
   reselect, replan, or execute a Tool.
5. A stopped task is resumed only through a governed recovery after the Runtime
   contract is repaired and evidence freshness is reassessed. Historical candidates
   are not silently reused.

## Why This Is Not Task-Specific

The repair concerns ownership and recoverability of any Query provider failure.
It applies to any Adapter, profile, sensor set, provider, and semantic task. The
external benchmark goal remains Coordinator-owned, but it is unrelated to this
failure and must not be regenerated or replaced.

## Acceptance Criteria

- Static profile/schema/materializer faults persist
  `failure_owner=runtime_provider`, `retryable_in_revision=false`,
  `requires_replan=false`, and `recommended_action=fix_runtime_contract`.
- Evidence-lineage and freshness failures preserve their explicit refresh semantics.
- Transient retry semantics never simultaneously require a replacement graph.
- Candidate-specific rejection still allows the existing bounded candidate loop.
- AgentLoop performs no automatic observation, selection, replan, Query, or Action.
- Tests remain no-motion and confirm no invocation or world change is produced.
