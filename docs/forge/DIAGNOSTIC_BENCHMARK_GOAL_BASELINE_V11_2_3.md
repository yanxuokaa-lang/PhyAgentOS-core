# Current Task Diagnostics and Benchmark-Goal Baseline

Date: 2026-09-21 (Asia/Shanghai)

Task under diagnosis: `task_f8a3e17443e041da`

Active revision: `revision_d06b871cc98d41ee`

This document records the current diagnosis before implementation. It does not
change the active task, resume it, retry a physical Action, or change the
observation-owned route profile.

## Scope and Evidence

The task completed a fresh observation, capability queries, scene understanding,
entity binding, and three target queries. The staging target query succeeded and
returned:

- `destination_ref`: `destination://targets/f73bf1f3653c4d7b9bd4673d112b795b`
- `observation_ref`: `observation://ec943451aeee4ee4b9e03d168caa47f9-1/head_camera`
- calibration from the current `...000002` capture
- `motion_authorized=false`

The task then completed `grasp.propose` for the blue staging move. It never
created a `manipulation.prepare` execution record. The durable event sequence
ended with two selection rejections and:

```text
planning_node_blocked:prepare_blue_staging:
node_turn_incomplete:prepare_blue_staging:
selection rejected without execution: missing_runtime_arguments
```

The active `prepare_blue_staging` node contained only:

```text
goal, success_criteria, allowed_arms, coordination_mode, constraints
```

It did not contain the Runtime-owned references required by the trusted
`manipulation_intent_v2` builder:

```text
entity_ref, destination_ref, capability_snapshot_ref
```

The previous revision persisted two successful capability snapshots for the
same observed scene, one for each capture/calibration generation. The current
binding propagation helper only forwards a capability snapshot when exactly one
candidate reference is found.

## Four Diagnoses

### 1. Model selection is configuration-driven

The active config explicitly sets:

```json
{
  "model": "gpt-5.6-terra",
  "provider": "custom",
  "requestTimeoutS": 300,
  "turnTimeoutS": 3600
}
```

AgentLoop passes the configured model to every model request. There is no
Coordinator fallback from another model in this path. Terra increases latency,
especially with large discovery context, but it is not the source of the
missing Runtime references and it is not evidence that preparation filtering
timed out.

### 2. Coordinator validation is correct; graph binding is incomplete

The Coordinator correctly rejects preparation without:

```text
destination_ref
capability_snapshot_ref
```

These are opaque Runtime facts and must not be invented from prose, benchmark
defaults, stale records, or model-generated geometry. The defect is earlier:
`manipulation.prepare` has an empty `planning_policy.input_binding_keys` list,
so graph compilation treats the node as bindable before the trusted argument
builder checks its additional Runtime requirements.

The current `_complete_persisted_runtime_bindings` helper can propagate a
destination only when it finds one in a node binding for the same entity, and a
capability snapshot only when exactly one successful capability reference exists.
The staging node had no entity binding and the task had multiple capability
snapshots, so neither reference reached the node.

This is a graph-materialization and Coordinator-owned binding propagation issue,
not a reason to weaken frozen ToolSpec validation.

### 3. AgentLoop repeats a deterministic binding failure

Selection errors such as source-path mistakes are reasonably repairable within a
node turn. Missing Coordinator-owned Runtime references are different: the
current graph has no authorized source from which the model can derive them.

The selection tool currently returns `missing_runtime_arguments` with
`requires_replan=false` and a generic retry recommendation. The node prompt then
asks the model to correct the selection, so the model rereads context and tries
again. The outer node continuation limit is bounded, but one node turn can still
consume many model iterations. This converts a deterministic graph defect into
long latency and, when the provider eventually stops, an apparent provider
timeout.

The loop also records a blocked node without making the task terminal or
`awaiting_replan`; the task can therefore remain visibly `executing` while the
runner has stopped.

### 4. The current task did not use benchmark target regions

The successful staging target was created by the current `manipulation.target`
query from the observed binding and current scene evidence. It is not the
RoboTwin benchmark target region. The early rejections were caused by:

1. a semantic graph node that declared a future place without an available
   `destination_ref`;
2. an invalid/nonexistent evidence or staging placeholder reference;
3. one malformed `node_digest` in a planning binding.

After the target query was retried with a valid binding, it succeeded. Therefore
the observation-owned target was not rejected because it differed from a
benchmark target. The desired development baseline is a separate, explicit
benchmark-goal profile that invokes the existing `task.goal` Runtime Query and
uses its `geometry_source=benchmark_task_definition` facts. It must not silently
change observation-owned mode.

## Architectural Decision for the Next Implementation

The first end-to-end baseline will use the existing Runtime-owned `task.goal`
contract to inject RoboTwin benchmark destinations. The Agent will still choose
entity order, grasp candidates, and execution sequencing, but it will not invent
or optimize destination poses in this profile. The later observation-owned
profile will restore Agent-selected `manipulation.target` planning.

The implementation must preserve these boundaries:

- Runtime/Adapter owns benchmark goal facts and their provenance.
- Coordinator owns opaque destination and capability references.
- Agent chooses semantic nodes and order, but never fabricates Runtime facts.
- `manipulation.prepare` remains fail-closed and motion-free until admitted.
- Observation-owned mode must reject benchmark facts rather than silently
  accepting them.
- Benchmark goal facts are not a task-success verdict and do not authorize
  motion; final success remains Verifier-owned.

Before a new run, graph materialization must either propagate the exact goal and
capability references into the current segment or reject the segment before
exposing a ready node. The AgentLoop must stop or request a governed replan on a
deterministic missing-binding error instead of asking the model to guess.

## Deferred Work

This diagnostic-only change does not yet:

- add the benchmark-goal profile to the running installation;
- change `manipulation.prepare` policy keys;
- change AgentLoop retry semantics;
- alter route geometry, collision checks, or motion authorization;
- resume or cancel `task_f8a3e17443e041da`;
- claim a successful Action, cumulative video, or seven-dimension runtime
  acceptance.

## English Summary

The current run used Terra because the config explicitly selected it. The
Coordinator rejection was correct: `prepare_blue_staging` lacked the
Runtime-owned destination and capability references. The graph compiler exposed
the node too early, and AgentLoop treated the deterministic missing-binding
condition as a model-repair problem, causing repeated confirmations and apparent
timeouts. The staging destination that did succeed came from the current
observation, not RoboTwin benchmark goals. The next baseline will explicitly
consume the existing Runtime `task.goal` benchmark facts, while keeping that
mode separate from the later Agent-owned target-planning mode.
