# Query Provider Block Recovery Diagnosis (2026-10-09)

## Scope

This diagnosis covers AgentTask `task_ba03dffaa1ac4c35`, revision
`revision_aacbc5eba12f4dd7`, and the generic PAOS recovery behavior required
when a read-only Query reaches the Gateway but its provider cannot produce a
valid semantic result. The repair is not specific to RGB ordering, colors,
blocks, cameras, `scene.understand`, or a particular model provider.

## Confirmed execution stage

The task did not fail during object motion:

1. Initial observation, understanding, capability discovery, binding, and goal
   acquisition succeeded.
2. Grasp proposal and manipulation preparation succeeded.
3. `object.acquire` and `object.place` reached successful terminal results.
4. The post-placement observation and capability refresh succeeded.
5. The post-placement understanding Query produced the only failing semantic
   result, after release and retreat had already been confirmed.

The persisted failure record is `tool_e4f6dc4b64af40ac` on node
`red_post_understand`. Its Gateway execution status is `succeeded`, while its
response contains:

```json
{
  "status": "unavailable",
  "error": {
    "code": "understanding_provider_error",
    "reason": "contract+transport",
    "failure_stage": "provider",
    "retryable": false
  },
  "provider_route": "none",
  "provider_error_class": "contract+transport"
}
```

This means the Query HTTP/Gateway path completed and was persisted, but the
provider chain produced no valid evidence. It is not an Action failure and it
does not establish an unknown physical outcome.

## Provider diagnosis and evidence boundary

The Runtime provider diagnostics show two bounded failures:

- The primary route returned an HTTP response but failed the adapter semantic
  contract (`contract`).
- The configured fallback route then failed at its transport boundary
  (`transport`).
- The adapter composed these as `contract+transport` and latched provider
  readiness unavailable.

At the incident time, Qwen lifecycle endpoints and the chat endpoint returned
HTTP 200. Therefore "Qwen process was down" is contradicted by the available
evidence. However, PAOS intentionally does not expose raw provider output or
the internal exception text through the ToolSpec result. The evidence does not
identify which exact response field violated the contract, so this diagnosis
does not invent one.

## Root cause in the PAOS control loop

Before this repair, the planning path was:

```text
Gateway Query record: transport succeeded, semantic status unavailable
  -> query_record_status() maps the record to failed
  -> AgentLoopNodeExecutor returns ToolResultEnvelope(status=failed)
  -> settle_node() creates an immutable failed NodeSettlement
  -> PlanningLoop default recovery selects stop
  -> Coordinator.fail_task() makes the entire AgentTask terminal failed
```

That policy is appropriate for a confirmed irrecoverable node failure, but it
is too strong for a read-only capability whose Runtime provider is temporarily
unavailable. Returning `blocked` after creating the failed settlement would
also be insufficient: the append-only settlement would keep the node closed
and prevent a legitimate retry after provider recovery.

## Generic recovery state machine

The repaired path is:

```text
persisted Query result
  + semantics=query
  + response.status=unavailable
  + error.failure_stage=provider
  + error.retryable=false
    -> persist query_provider_blocked event
    -> AgentTask status=waiting_for_runtime
    -> do not create a NodeSettlement
    -> do not expose the failed attempt as planning evidence
    -> read only the frozen Runtime Tool context

context still unavailable or unchanged
    -> remain waiting_for_runtime
    -> do not invoke the Query again

context changes and reports ready=true
    -> persist query_provider_released event
    -> retain the old Query record in audit history
    -> exclude that released attempt from the effective planning view
    -> return AgentTask to executing
    -> run the same semantic node through normal selection and execution

new Query succeeds and settles
    -> downstream dependencies may become ready
```

Request validation failures, retryable Query failures, Actions, Sessions, and
unknown physical outcomes do not match this predicate and retain their
existing correction, reconciliation, or replan behavior.

## PAOS ownership boundaries

- **Runtime** owns provider health, live Tool readiness, and semantic Query
  output. Tool invocation never starts or repairs a provider process.
- **Gateway** owns invocation/result transport truth.
- **Coordinator** owns the task status and append-only blocked/released events.
- **PlanningLoop** branches before settlement and preserves dependency closure.
- **AgentLoop** performs a fresh governed selection only after the Runtime
  readiness transition; it does not synthesize evidence or provider output.
- **Action admission** is unchanged. Provider recovery cannot authorize motion,
  replay an Action, or bypass binding, preparation, and terminal settlement.

## Extension principles

The implementation contains no branch for RGB, colors, arrangements, blocks,
`scene.understand`, camera identities, Qwen, GPT, or RoboTwin. New adapters gain
the same behavior when they return the same provider-neutral structured Query
facts and expose explicit boolean readiness through their Tool context.

No new hash, frozen contract, baseline, or release gate was added. Existing
task/revision/record identities and ordinary Coordinator events are sufficient:
the missing concept was a non-terminal Runtime wait, not another integrity
mechanism.

## Safety and validation boundary

The repair is control-plane only. Tests use fake Tool records and scripted
readiness contexts. They do not create or resume a live AgentTask, invoke a
Gateway Query or Action, advance a simulator, read a camera, or move hardware.
The failed historical task remains terminal; the repair governs future tasks
and future occurrences under the same generic contract.

## Supplemental code-review findings and fixes

The seven-dimension review found five additional concrete edge cases and fixed
them without changing the provider-neutral boundary:

1. A context GET is awaited before `query_provider_blocked` is persisted. If an
   operator cancels during that await, the persistence mutation now requires
   the task to remain executing and not cancellation-requested; the planning
   loop treats the resulting state race as normal terminal convergence.
2. `waiting_for_runtime` is now an explicit prompt phase. The model can inspect
   frozen Tool context or cancel the task, but cannot select, query, or start an
   Action while the host-owned readiness loop is waiting.
3. Admission context now ignores the provider-blocked semantic Query before
   collecting scene, evidence, resource, or condition facts. The failed receipt
   remains available as immutable audit history, never as planning authority.
4. When the block starts from a ready snapshot and the Runtime later reports
   unavailable before returning to the same ready snapshot, the intermediate
   transition is persisted. This prevents an equal recovered snapshot from
   waiting forever.
5. After release, the model-facing task projection now uses the same effective
   execution-record loader as planning. The failed receipt remains in durable
   audit history but is not reintroduced as a selectable planning fact.

These fixes add no RGB/object/provider branch, no hash or release gate, and no
motion path. The added regressions remain fake/no-motion tests; no live Runtime,
Gateway, simulator, camera, or physical Action was used.
