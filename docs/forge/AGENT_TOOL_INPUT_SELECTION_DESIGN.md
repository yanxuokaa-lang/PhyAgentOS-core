# Agent Tool Input Selection Design

## Goal

Allow a Tool producer to return reusable provider-neutral structured facts and
allow a later AgentLoop node to select and assemble the subset required by a
consumer ToolSpec. A producer does not emit a consumer-specific transport
object, and a PlanNode does not duplicate a complete predecessor response.

## Ownership

| Concern | Owner |
| --- | --- |
| Structured terminal result and evidence provenance | Producer Tool and Runtime/Adapter |
| Required final argument shape | Consumer ToolSpec `input_schema` |
| Semantic identity and graph dependency | PlanNode |
| Durable Tool records, evidence, revisions, and DecisionTrace | AgentTaskCoordinator |
| Selection and assembly from the bounded input view | AgentLoop node turn |
| Structural validation before invocation | AgentComposedDispatch |
| Execution and motion admission | Gateway and existing readiness/safety providers |

## Data Flow

```text
producer Tool terminal result
  -> Coordinator ToolExecutionRecord + evidence refs
  -> NodeContextProvider bounded input view
       - exact direct-predecessor results
       - exact discovery Query arguments and terminal results named by node.required_evidence
  -> Agent selects fields and assembles consumer arguments
  -> AgentComposedDispatch validates frozen consumer input_schema
  -> Coordinator persists DecisionTrace and resumable selection
  -> existing Forge wrapper and Gateway admission
```

The Agent may select, filter, wrap, and combine values already present in the
bounded input view or immutable node bindings. It may not create sensor facts,
metric geometry, calibration, freshness, execution state, or motion authority.
Runtime-specific semantic validation remains owned by the consumer endpoint.

## Contract Rules

1. `BoundToolSpec` freezes the provider-neutral `input_schema` observed when the
   task binds the Tool. Legacy records without a frozen schema remain readable.
2. `input_binding_keys` continue to describe immutable semantic PlanNode
   bindings. They are not expanded to every transport argument.
3. `forge_plan_ready` exposes the consumer's required top-level arguments as a
   diagnostic projection. It does not synthesize values or make a node ready.
4. `forge_plan_select` accepts exact final arguments chosen by the Agent and
   validates them against the frozen schema before persisting a DecisionTrace.
5. A root node can receive exact discovery Query arguments and terminal results only when its
   `required_evidence` names evidence persisted by Coordinator and selected into
   the active revision's `discovery_evidence_refs`.
6. A successor receives exact results only from direct predecessor executions.
7. Schema rejection creates no Tool record, Gateway invocation, Action,
   Session, simulator step, or motion authorization.
8. Recovery-provider failure preserves the original node failure and enters the
   existing bounded `awaiting_replan` state; it never retries a Tool automatically.

## Extension Rule

New benchmark tasks add or replace ToolSpecs and Adapter outputs. PAOS Core does
not add drawer, bin, shelf, hook, obstacle, tabletop, color, or fixed-object
branches. A consumer declares its final input schema; any producer may supply
compatible structured facts through the bounded evidence or predecessor view.

If a future consumer needs a deterministic transformation that cannot be
expressed as Agent selection plus its normal endpoint validation, add a
consumer-owned trusted argument builder through the existing planning extension
seam. Do not hard-code a producer Tool ID into Core.

## Failure Semantics

- Missing required argument: `tool_input_schema_invalid` before Gateway.
- Wrong type, enum, bounds, pattern, array/object shape, or unknown property:
  `tool_input_schema_invalid` before Gateway.
- Required evidence absent: existing DAG readiness rejection.
- Stale scene or calibration: existing planning/Gateway admission rejection.
- Consumer semantic rejection: terminal Query failure owned by the Runtime.
- Recovery provider unavailable or invalid: existing bounded
  `awaiting_replan`, preserving the original settlement failure.

## Acceptance

1. An incomplete `grasp.propose` payload is rejected before a Tool record.
2. A root grasp node sees the exact selected discovery understanding result.
3. A successor still sees only direct-predecessor results.
4. A valid Agent-assembled grasp payload passes selection without producer ID
   coupling.
5. Recovery-provider failure does not become `runner_error`.
6. No-motion tests prove zero Action/Session/Gateway motion effects.
7. Existing ToolSpec, legacy binding, continuation, settlement, and replay
   behavior remain compatible.
