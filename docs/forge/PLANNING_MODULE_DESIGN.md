# PAOS Planning Module Design

## Status

This document is the implementation baseline for `PhyAgentOS/planning`. It is
an approved design boundary, not a second task runtime.

## Purpose

The module represents an Agent-composed semantic subtask DAG and evaluates
whether a proposed Tool call is structurally and evidentially admissible. It
does not execute Tools, own a task lifecycle, persist facts, acquire locks, or
authorize motion.

The task-level shape is:

```text
relocate(red)  ─────┐
relocate(blue) ─────┼──> verify
```

Each semantic node may select a different Tool sequence. The old fixed
`observe -> capabilities -> understand -> propose -> prepare -> acquire ->
place` sequence remains a Skill baseline policy only; it is not the only legal
plan.

## Ownership boundary

| Boundary | Owner | Rule |
| --- | --- | --- |
| PlanGraph and Tool-call protocol | `PhyAgentOS/planning` | Immutable Pydantic contracts and pure validation only |
| Task, revision, execution facts | `forge/task.py` and SQLite | The only lifecycle authority |
| Tool transport and invocation | `forge/tool_client.py` / Gateway | The only execution plane |
| Robot capability and readiness | adapter/provider | Physical facts; fail closed |
| Semantic success | Verifier | Task-level verdict authority |
| Policy candidates and promotion | `agent/experience` / Skill Runtime | Review and independent evaluation required |

The planning module must not import Gateway clients, SQLite stores, adapter
providers, or Skill Runtime state.

## Robot/controller capability boundary

`CapabilitySnapshot` and `ArmCapability` are the sole PAOS capability
projection. Robot-specific motion limits are not a second core model: each
arm may carry an opaque `motion_capabilities_ref` to an adapter-owned,
immutable provider artifact. The artifact records per-joint limits,
controller/simulator identity, units, timing, provenance, and whether a limit is
actually enforced by the controller. Planning consumes this projection for
admission and arm assignment; it never imports an SDK or changes a limit.

The RoboTwin20 Franka path is simulation-only. Its local requirements include
SAPIEN, MPlib, and CuRobo but no `libfranka`/`frankx`; the simulation loads
`panda.urdf` and drives SAPIEN articulation targets. No global numeric speed
threshold is defined by PAOS. An adapter must bind provider-owned limits and
their provenance before planning or execution. A hard bound may be advertised
only after a controller-specific qualification artifact proves enforcement and
binds the controller identity/version. Diagnostic measurements remain evidence
only and cannot authorize motion. See `REAL_SPEED_LIMITS_ARCHITECTURE.md` for
the normative route.

Evidence sources: `RoboTwin/scripts/requirements.txt`,
`assets/embodiments/franka-panda/config.yml`,
`assets/embodiments/franka-panda/curobo.yml`, and RoboTwin
`envs/robot/robot.py:set_arm_joints`; the upstream
[libfranka Robot API](https://raw.githubusercontent.com/frankaemika/libfranka/main/include/franka/robot.h)
documents explicit rate-limiting controls and joint-velocity-limit queries.

## Protocols

- `PlanGraph` / `PlanNode`: current task's semantic DAG, bound to a task and
  revision digest. Nodes describe obligations, capabilities, dependencies,
  evidence, resource claims, and retry lineage.
- `ToolSpecPolicy`: planning projection of a ToolSpec. It declares
  preconditions, required/produced evidence, expected effects, resources,
  scene-write behavior, failure classes, and idempotency. It is not a second
  provider configuration source.
- `ToolCallEnvelope`: Agent proposal with task/revision/node identity,
  ToolSpec digest, input-binding digest, scene revision, and idempotency key.
- `ToolResultEnvelope`: execution result projection. `unknown`, `failed`, and
  `cancelled` are distinct; a result never grants motion authority.
- `NodeSettlement`: normalized node fact (`completed`, `failed`, `outcome_unknown`,
  `blocked_by_dependency`, `stale`, or `cancelled_before_start`).
- `ReplanDelta`: preserve/cancel/invalidate/retry instructions and fresh
  evidence requirements. The coordinator, not this module, creates a new
  `PlanRevision`.
- `DecisionTrace`: redacted, attributable record of candidate Tools, selected
  Tool, policy/context digests, and result/evidence references.
- `WorkflowPolicy`: reusable partial-order and Tool-selection policy. It is
  separate from a concrete `PlanGraph`; one successful episode never rewrites a
  policy automatically.

`PlanRevision` stores an immutable `artifact://` graph reference plus graph,
planner-decision, and policy-snapshot digests;
`ToolExecutionRecord` stores node/obligation/input-binding/decision-trace
references when a Tool call is attached to a semantic node. These are optional
for legacy records but become an all-or-nothing binding once any planning field
is supplied. SQLite continues to persist the aggregate; this module only
validates the shape.

## Dynamic Tool admission

The Agent may choose any Tool present in the frozen binding. Admission is
constrained by the ToolSpec projection and current context:

1. The node exists and is ready in the DAG.
2. The proposed Tool matches the node capability and bound ToolSpec digest.
3. Required evidence is present and references the current scene revision.
4. Resource claims do not conflict with currently held resources.
5. Action/session semantics remain subject to Gateway admission; planning only
   returns a decision.

Thus the rule is **not a fixed order, but fixed legality conditions**.

## Evolution boundary

Experience may propose changes to Tool order, optional queries, re-observation,
candidate ranking, arm preference, retry/replan strategy, and semantic
parameter binding. It may not change workspace, joint limits, collision/stop
policy, transforms, readiness, Gateway authority, or Verifier safety rules.

Only a complete attributable AgentTask episode with independent semantic
verification can produce a `WorkflowPolicyCandidate`; replay/matched evaluation
and review are required before Skill promotion.

## Failure semantics

Missing evidence, stale scene, dependency failure, resource conflict, unknown
Tool, and cycle are explicit rejection paths. Timeout/transport uncertainty is
represented as `outcome_unknown`, never as success. Replanning preserves task
identity while the PAOS coordinator owns the new revision and retry budget.

## Migration stages

1. Keep the existing Skill workflow as a deterministic baseline policy.
2. Generate an Agent-composed no-motion semantic DAG for multi-object tasks.
3. Select Tools dynamically through admission checks.
4. Record DecisionTrace and derive reviewed policy candidates.
5. Promote only reviewed, independently evaluated Skill policy versions.

The pick-place Skill exposes these modes explicitly: `baseline` uses the legacy
fixed Tool projection for compatibility/replay; `agent_composed` compiles
Agent-provided semantic subtasks into `PlanGraph` and uses dynamic Tool
candidate admission. The Skill bridge is an adapter over the planning library,
not a second planner runtime.

## Review gates

Every change to this module is reviewed across architecture integration,
failure paths, authority boundaries, configuration/provenance, and
maintainability. Tests must prove the module is pure: no Gateway calls, no
SQLite writes, no locks, and no `motion_authorized=True` output.

## Implementation status (2026-09-05)

The coordinator integration now accepts a concrete `PlanGraph` plus an immutable
`artifact://` reference at task creation and at a new revision. It persists the
graph, planner-decision, and policy-snapshot digests in the authoritative
`PlanRevision`. Planning-driven Query/Action/Session calls may provide one
complete `PlanningExecutionBinding`; the coordinator persists its node,
obligation, input-binding, and redacted DecisionTrace reference in the
`ToolExecutionRecord`. A partial binding is rejected, while calls without a
planning binding remain compatible with legacy tasks. `ReplanDelta` is adapted
through `begin_revision_from_delta`; the planning module still does not mutate
the store or create revisions itself. Redacted decision-trace references are
also carried into the experience outcome projection.

Live ToolSpecs now have an explicit `planning` extension projection through
`project_tool_spec()`. The extension is versioned and strict; missing metadata
does not get guessed from a tool name, endpoint, or implementation, so legacy
ToolSpecs remain executable but unavailable to `agent_composed` admission.
Bound Skill metadata carries the immutable projection when present and
revalidates it on the next binding check. AgentLoop production dispatch is
provided by a read-only `AgentComposedDispatch` bridge, and Experience stores
planning policy candidates plus independent replay receipts with explicit
human-review and callback-gated promotion. No Action/Gateway/Dora motion wiring
is introduced here.

## ToolSpec projection review (2026-09-05)

The live binding path now projects only an explicit versioned `planning`
extension through `project_tool_spec()`. The projection preserves the live
ToolSpec digest and strict planning fields; it never infers a capability from a
provider endpoint or implementation name. Legacy ToolSpecs without the
extension remain valid for ordinary execution but are unavailable to
`agent_composed` admission. If an extension is present but malformed, binding
fails closed, and a previously bound projection is revalidated on the next
ToolSpec check. This closes the configuration/provenance gap without creating a
second Tool registry or execution path.

## AgentLoop dispatch and policy-candidate status (2026-09-05)

`PhyAgentOS.agent.planning_dispatch.AgentComposedDispatch` is the AgentLoop
bridge for an active task. `forge_plan_activate` builds it from the persisted
`PlanRevision.plan_graph`, frozen Skill binding, and an injected trusted
`AdmissionContext` provider. Agent-supplied evidence, settlements, scene
revisions, and condition facts are not accepted. `forge_plan_ready` exposes only
the current ready semantic nodes and their explicit ToolSpec projections. A
registry execution guard checks task-bound Query/Action/Session creation calls
before the existing Forge wrappers run. Missing providers/projections, stale
identities, incomplete planning bindings, and unready nodes return a
structured fail-closed error; status/result/cancel reconciliation remains under
Coordinator ownership.

Experience now stores `WorkflowPolicyCandidate` and immutable independent
`WorkflowPolicyReplayReceipt` records in `experience.sqlite3`. Candidates are
deduplicated by base/proposed policy digests, require support from distinct
episodes and passing independent replay receipts before human approval, and
cannot be promoted without an explicit Skill Runtime callback returning an
`artifact://` receipt. No candidate transition mutates an active AgentTask.

## Collision-world admission boundary (2026-09-07)

`SceneCollisionWorld` is an adapter-owned evidence dependency of
`manipulation.prepare`; it is not a planning Tool, Skill step, or Curobo handle exposed to the
Agent. The planning module may validate its reference, digest, scene/world revision, coverage,
and phase-scoped target exclusion, then return an admission or stale/invalidation result. It
must not build a Curobo `WorldConfig`, call `MotionGen.update_world()`, execute `scene.step()`,
or create a `PlanRevision`.

When a world revision changes, `AgentLoop`/`AgentTaskCoordinator`—not this library—creates the
next revision and rebinds a fresh collision-world artifact. The adapter must update both
`motion_gen` and `motion_gen_batch` from the same world digest. Partial/unknown perception
coverage, missing geometry/provenance, cache-capacity overflow, or update failure remains
fail-closed and cannot be converted into a ready or motion-authorized result.

The RoboTwin provider handles Curobo's fixed OBB cache explicitly. It uses
`MotionGen.update_world()` when both arm planners have capacity for the complete world. If
capacity is insufficient, the runtime port rebuilds warmed `MotionGen` and batch instances from
the existing RoboTwin robot profile and complete `WorldConfig`, then swaps both arm references
only after all replacements succeed. This is provider behavior, not planning-module logic; no
`scene.step()` or motion authorization occurs during rebuild.

## Generic attribute-sorting scenario and execution-loop extension (2026-09-07)

### Scenario fit

The user request "arrange blocks by RGB/color" is a valid instance of a
generic attribute-sorting task, not a request for an RGB-specific workflow.
The request intentionally omits the number of blocks, the set of observed
colors, and their initial locations. Those values must be discovered from the
live observation Skill and represented as evidence; they must not be placed in
the planner, a Skill prompt, or a fixed DAG template.

The intended flow is therefore:

```text
natural-language goal
  -> Agent selects an observation/understanding Skill
  -> live scene observation and scene-graph evidence
  -> Agent decomposes the discovered entities and ordering obligations
  -> generic PlanGraph (one semantic obligation per entity/group)
  -> node-scoped Agent execution through existing Forge Tools
  -> NodeSettlement and evidence update
  -> next ready node, or bounded replay/replan after a failure
```

The decomposition may produce nodes such as `sort-group/<opaque-id>` or
`arrange/<opaque-id>`, but these are planner outputs, not PAOS-owned RGB
semantics. A final verification node joins the discovered obligations. The
graph must remain valid when the scene contains a different number of blocks,
additional colors, duplicate colors, or an empty/partially observed set.

The unknown inventory creates a progressive-planning requirement. The current
task API can create a task with a final graph or with no graph, while
`AgentComposedDispatch` requires a concrete graph and `begin_revision()` is
normally entered after `awaiting_replan`. A production flow therefore needs a
same-`AgentTask` discovery checkpoint: observe and validate the scene first,
then let the planner propose an expanded graph in a new `PlanRevision`, while
preserving the observation evidence. This is a revision/expansion transition,
not a second task and not a fixed RGB graph.

The requested order must be explicit in the task goal or verification
contract. If "RGB" supplies the comparator (for example red, then green, then
blue), the planner can bind discovered entities to that comparator. If the
ordering rule or target layout is ambiguous, the Agent must ask or produce an
unknown verification outcome; it must not infer a layout from a color name.

### Failure cases exposed by the scenario

An object can be dropped during an Action in two observably different ways:

- the Action returns `failed` or `outcome_unknown`; the active node can be
  settled directly and its descendants invalidated;
- the Action returns success, but a later observation/verification supplies
  counterevidence that the object is no longer in the required place. In this
  case the later evidence must mark the affected obligation stale/failed and
  trigger a new revision; the system must not rewrite the historical success.

The second case requires a generic postcondition/observation checkpoint and
an evidence-to-obligation attribution. It cannot be implemented as an
RGB-specific "dropped block" branch. The new revision should preserve only
nodes whose evidence remains valid, invalidate the affected obligation and its
descendants, and carry the counterevidence into the Agent's replan context.

The current `begin_revision_from_delta()` validates task/revision identity and
accepts a replacement graph, but does not itself materialize
`preserve_node_ids`, `invalidate_node_ids`, or `fresh_evidence_requirements`.
The loop adapter must apply those fields when constructing the replacement
revision and when selecting predecessor context; otherwise a replay could
reuse evidence from an invalidated branch.

Each world-changing node may advance the scene revision. Before the next node,
the trusted context provider must refresh the scene/evidence view and reject
stale predecessor facts. A re-observation node or a planner-selected
fresh-evidence requirement is preferable to silently continuing from the
initial scene graph.

### Minimal loop that reuses PAOS authorities

The missing connection is a thin `PlanningLoopAdapter`, not another runtime.
It consumes the persisted `PlanRevision.plan_graph`, calls the existing
`AgentComposedDispatch` for ready-node and Tool admission, and invokes one
node-scoped turn of the existing `AgentLoop`. The loop writes execution facts
through `AgentTaskCoordinator`; it does not write a parallel state file or
invoke a Gateway directly.

For each selected ready node:

1. Build a bounded node prompt from the node declaration and the direct
   predecessor's persisted settlement/evidence summary.
2. Run the normal AgentLoop Tool-call loop with the planning guard enabled.
3. Convert terminal `ToolExecutionRecord` facts to `ToolResultEnvelope`, then
   call the pure `settle_node()` function.
4. Persist the resulting `NodeSettlement` in the active `PlanRevision` and
   refresh the trusted `AdmissionContext`.
5. Call `derive_ready_nodes()` and continue until the graph is complete or a
   non-success settlement requires recovery.

`NodeSettlement` should become a field of the existing `PlanRevision` rather
than a second store. Deriving settlement only from Tool records is acceptable
for an initial experiment, but is ambiguous when one semantic node selects
multiple Tools or has an unknown outcome; durable node settlement is required
for reliable replay and recovery.

### Minimum predecessor-context injection

The first implementation only needs direct-predecessor context. A
`NodeContextProvider` outside the pure planning package can project:

- current `task_id`, `revision_id`, and `node_id`;
- the current node's capability, dependencies, and required evidence;
- each direct predecessor's terminal status;
- opaque `evidence_refs`/`output_refs`, source Tool ID, and failure code;
- preserved constraints from the latest replan decision.

The projection is inserted into the node-scoped Agent turn as data, not as a
new authority. Raw provider payloads, unverified coordinates, controller
parameters, and arbitrary workspace text are excluded. A predecessor result
can therefore tell the current Agent "acquisition completed and produced
evidence X" or "the prior attempt is unknown; re-observe before acting",
without allowing the Agent to assert that the scene is current.

This reuses `ToolExecutionRecord`, `NodeSettlement`, `AgentTaskStore.events()`,
the existing evidence references, and advisory Experience lessons. It does not
require a second memory database or a second prompt protocol.

### Failure, replay, and replan semantics

The physical-drop example is represented as a normal node outcome, not as an
RGB-specific exception:

```text
node action result
  -> failed / outcome_unknown / stale
  -> settle_node()
  -> build_replan_delta()
  -> Agent proposes a replacement graph or bounded retry
  -> coordinator appends a new PlanRevision
  -> adapter resumes from the new revision
```

The Agent may choose the recovery strategy from the failure feedback, but it
cannot mutate the active graph or mark a node successful by assertion.
`ReplanDelta` remains the bounded description of preserved nodes, invalidated
descendants, retry lineage, and fresh evidence requirements;
`AgentTaskCoordinator` remains the owner that accepts a new revision and
enforces the retry budget/deadline.

Replay must be split into two operations:

- **Reducer replay:** replay stored Tool results and settlements without any
  Gateway call. This is safe for diagnosing the DAG and rebuilding ready sets.
- **Execution rerun:** execute a node again. Query reruns may create another
  execution record; Action/Session reruns require a new revision, fresh
  admission, and explicit `retry_of` lineage so a physical side effect is not
  silently duplicated.

The recovery policy is selected by the Agent/Planner Plugin from the failure
feedback. PAOS supplies the facts and gates; it does not hard-code a rule such
as "always retry the dropped block".

An installable planner may implement the optional `RecoveryPlannerPlugin`
protocol and return `stop`, `replay`, or `replan` from `select_recovery()`.
Plugins that only implement the original `PlannerPlugin` remain compatible and
retain bounded replan behavior. When no planner is installed, the composition
root supplies neither a fake proposer nor a recovery policy, so failure stops
cleanly instead of manufacturing a `None` proposal.

The adapter exposes three explicit recovery decisions after a non-completed
settlement: `stop`, `replay`, and `replan`. `stop` leaves the failed node and
its descendants unexecuted. `replay` invokes only the pure reducer over
persisted Tool results and `NodeSettlement` records; it neither calls the node
executor nor creates a revision. `replan` is the execution-recovery path: it
must create a new `PlanRevision` through `AgentTaskCoordinator`, persist
`retry_parent_node_id`, and pass through normal admission before any replacement
node can execute. A missing policy retains compatibility by choosing `replan`
only when a replan proposer is installed; otherwise it stops.

If a failed or outcome-unknown result reports `world_changed` and a
`new_scene_revision`, `replan` is blocked until the trusted admission context
projects exactly that revision. The refreshed revision is then supplied to the
Planner while the node's original input bindings remain provenance. No later
object may observe, plan, or act using the prior scene. An unknown invocation
is reconciled through its existing invocation identity; reducer replay or a
new POST is not a substitute for Gateway reconciliation. If recovery pauses
with `scene_refresh_required:*`, a later adapter run reloads the failed
`NodeSettlement` from the active revision and re-enters recovery after the
trusted context refreshes; this checkpoint does not require a second recovery
store. Selecting execution `replan` for an `outcome_unknown` settlement returns
`reconciliation_required:*` before the proposer is called.
The recovery-only context projection retains stale predecessor settlements as
labelled historical provenance so the Planner can invalidate or replace them;
the normal node-execution projection continues to reject the same stale facts.
After process restart, the adapter reconstructs an outstanding refresh from the
active revision's latest world-changing settlement, so the next object cannot
advance merely because the in-memory refresh marker was lost.

### Planner/plugin boundary

The decomposer, node-selection policy, node-context projection, and recovery
policy belong in an installable planner/Skill plugin. The plugin may call
`compose_agent_plan()` and return a `PlanGraph`, but it does not own task state,
Tool transport, Evidence, Verifier semantics, Runtime admission, or motion
authority. PAOS core exposes only the provider-neutral planning contracts and
the existing coordinator/AgentLoop seams. In-process entry-point loading is
for development in the PAOS interpreter; a managed production plugin runs
its code and private dependencies in the plugin/Skill-owned environment (for
example, a separately installed runtime Node) and exchanges only these
provider-neutral projections across the process boundary.

This preserves the current baseline workflow and allows an attribute-sorting
planner to coexist with other planners. The present repository already has
Skill Runtime installation and ToolSpec planning projections; the remaining
extension is a formal planner-plugin interface/discovery seam, not a second
planner runtime embedded in `PhyAgentOS/planning`.

### Six-dimension acceptance for this extension

| Dimension | Acceptance condition for the attribute-sorting loop |
| --- | --- |
| Architecture integration | Reuse AgentLoop, AgentComposedDispatch, AgentTaskCoordinator, PlanRevision, Forge Tool API, Evidence, and Verifier; no second scheduler/store/execution path |
| Failure paths | Tests cover incomplete observation, empty/duplicate attributes, dependency blocking, failed/unknown/stale/cancelled nodes, dropped-object feedback, replay, replan timeout, and retry-budget exhaustion |
| Authority boundaries | Planning and plugins remain no-motion; Coordinator owns task/revision state; Gateway owns execution; adapters own physical facts; Verifier owns semantic success |
| Configuration/provenance | Discovered entities and prior-node context carry task/revision/node/evidence provenance and reuse existing graph, ToolSpec, and trace identities; Agent-supplied facts are not trusted context |
| Maintainability | One orchestration adapter, one node-context projection, and one plugin interface; existing baseline reducer and Tool wrappers remain usable |
| Anti-OverDefense | Add checks only for observed hazards such as stale predecessor context and duplicate Action side effects; do not add RGB-specific schemas, fixed block counts, speculative hashes, or duplicate gates |

### Completion status and next implementation slice

The previously missing loop slice is implemented in the feature branch below.
Planner-specific decomposition remains an extension responsibility: a plugin
receives a task-conditioned `PlanningRequest` containing the task description,
verification contract, optional trusted evidence/observations, and available
capabilities. The Agent chooses whether to call observation or scene-understanding
Tools first; PAOS does not impose that phase. The adapter and coordinator
enforce the common lifecycle. Action/Session reruns still require the existing
Gateway reconciliation and fresh admission; this feature does not silently
replay physical side effects.

## Implementation result (2026-09-07)

The first complete no-motion slice is now implemented outside the pure planning
package. `PhyAgentOS.agent.planning_loop` provides a `PlanningLoopAdapter`,
`NodeContextProvider`, durable settlement writes through `AgentTaskCoordinator`,
ready-node progression, reducer replay, postcondition counterevidence recovery,
Agent-selected replacement-graph application, and `AgentLoopNodeExecutor` for
turning node-scoped Tool records into normalized results. `AgentLoop.run_node_turn()`
is the node-scoped entry point; it uses the existing tool registry and planning
admission guard. `PhyAgentOS.agent.planner_plugin` provides an explicit
`PlannerPlugin` protocol and opt-in `paos.planners` entry-point registry.

An Agent-selected graph is materialized through
`AgentTaskCoordinator.materialize_plan_revision()` (with the discovery-named
compatibility alias `expand_discovery_revision()`) under the same task identity.
`NodeSettlement` is persisted in `PlanRevision`;
replan metadata and preserved settlements are carried into the replacement
revision with a new revision identity. The adapter never calls Gateway, writes
SQLite directly, or authorizes motion. Action/Session physical reruns remain
subject to the existing coordinator unknown-state and admission rules.

The RGB attribute-sorting scenario is covered by pure fake-execution tests with
discovered entities, a sequential semantic DAG, direct predecessor context,
post-action dropped-object counterevidence, bounded replan, and reducer replay.
No Gateway, Dora, simulator step, or hardware action is part of this validation.

## Long-horizon task outer loop review and implementation (2026-09-08)

The continuous-autonomy extension was reviewed against PAOS ownership,
provider-neutrality, extension, and developer-guide principles. The approved
shape is a task-state-driven outer controller over the existing
`PlanningLoopAdapter`; it is not a LiteLLM conversation loop and not a second
runtime scheduler.

```text
TUI / chat channel
  -> LongHorizonTaskController
  -> PlanningLoopAdapter (one persisted planning run)
  -> AgentLoop node turn
  -> existing Forge Tool/Gateway execution
  -> Coordinator execution facts, Evidence, NodeSettlement
  -> task/revision checkpoint
```

LiteLLM remains stateless: it receives the complete `messages` array for one
model call and returns one response. Ordinary chat continuity is provided by
the existing `SessionManager`/`Session` JSONL history and
`ContextBuilder.build_messages()`. Long-horizon continuity is provided by the
persisted `AgentTask`/`PlanRevision` aggregate, not by provider-side session
state.

The TUI remains an interaction surface. The current slice can inspect, start,
pause, resume, stop/cancel, and reducer-replay a task through the same
controller boundary. Materialized tasks created by a user turn are started in
the AgentLoop's background task set, so the prompt remains available for
control or clarification input. The TUI must not write SQLite, call Gateway
directly, create revisions, or infer success from natural-language output.
`prompt_toolkit` remains the default input surface. The optional Textual
presentation layer is enabled with `pip install -e '.[tui]'` and
`paos agent --ui textual`; it renders conversation, progress, Coordinator
events, task/revision/DAG state, and clarification prompts while receiving the
same AgentLoop, MessageBus, LongHorizonTaskController, and Coordinator
objects. It does not add a scheduler, store, execution adapter, or motion
authority. Its task commands are `/task status|start|pause|resume|stop|replay
TASK_ID`. Missing Textual is reported as an explicit install error.

Execution admission in the TUI is backed by
`AgentTaskPlanningContextProvider`. It projects the latest scene revision,
evidence references, and node settlements from persisted Tool records and the
active `PlanRevision`. If no observation/understanding Tool has produced a
scene revision yet, the runner returns `blocked` with an explicit missing-fact
reason; it never invents a placeholder scene identity. Natural-language task
creation can therefore let the Agent choose whether observation is needed,
while execution still uses the existing evidence authority.

The first implementation slice is `PhyAgentOS.agent.long_horizon`:
`LongHorizonTaskController` wraps the existing adapter with a per-task lock,
checkpoint pause/resume, terminal-task short-circuit, and
`awaiting_replan` propagation. `PlanningLoopAdapter.run()` accepts a
per-invocation checkpoint callback, so controller state is not stored in a
mutable global scheduler. A pause takes effect between semantic nodes; it
does not claim that an in-flight Gateway Action was stopped. Pause requests are
stored as `AgentTaskRecord.pause_requested` through Coordinator transactions,
so a restarted TUI can observe the pause without a second pause database.

The outer loop has four explicit outcomes: terminal task status, blocked or
awaiting-replan state, a user pause checkpoint, or continued node execution.
Stop/cancel is reconciled through `AgentTaskCoordinator.cancel_task()` and does
not claim an in-flight Action stopped. Structured clarification events are
persisted as `waiting_for_user` by the existing task Tool and rendered by the
dashboard; ordinary model text still must not mutate task state.

The shipped control surface is `paos task status|pause|resume|stop|replay TASK_ID`.
An interactive `paos agent` session accepts `/task status|pause|resume|start|stop|replay
TASK_ID`. In the same process, `start`/`resume` wake the existing background
controller; status/pause/stop/replay remain Coordinator/controller operations.
No command constructs a second execution adapter, invokes LiteLLM directly,
calls Gateway directly, or claims that an in-flight Action stopped.

### Six-dimension review

| Dimension | Result |
| --- | --- |
| Architecture integration | Pass: controller delegates to existing Coordinator, PlanningLoopAdapter, AgentLoop, Forge wrappers, Evidence, and Verifier; no second scheduler/store/execution plane. |
| Failure paths | Pass for this slice: pause, terminal, awaiting-replan, blocked, node failure/unknown/stale and existing replan budget remain explicit; in-flight Action cancellation remains Coordinator/Gateway-owned. |
| Authority boundaries | Pass: TUI/controller orchestrate; Coordinator owns task/revision facts; Gateway owns transport; LiteLLM only performs one model request; planning remains no-motion. |
| Configuration/provenance | Pass: task/revision/node/evidence context remains loaded from the existing aggregate and trusted admission provider; no provider-side hidden conversation identity is introduced. |
| Maintainability | Pass: one outer controller and a per-call checkpoint seam; no mutation of shared adapter state and no duplicate lifecycle implementation. |
| Anti-OverDefense | Pass: pause is checkpointed rather than pretending to cancel physical work; no extra hashes, stores, or UI-specific task contracts were added. |

Validation is no-motion only. The controller tests cover pause/resume,
terminal short-circuit, and awaiting-replan propagation; the combined planning
suite passes. This does not prove Gateway, simulator, or hardware execution.

## Multi-turn Agent/TUI gap diagnosis and extension plan (2026-09-08)

The previous TUI waited for one complete Agent turn before reading the next
input. That gave a stable `thinking -> reply` interaction, but it prevented a
long-horizon AgentTask from remaining active while the user issued control or
clarification input. The current background mode removes that wait, but the
presentation layer is still missing several pieces required for a complete
multi-turn experience.

The remaining gaps are:

1. Inbound and outbound messages do not share a durable turn correlation. A
   normal reply, progress hint, task completion, and runner failure can all
   arrive through the same queue without an explicit turn/task/node relation.
2. The TUI prints a one-shot thinking marker but has no queued, running,
   completed, or failed lifecycle for each turn. The user cannot tell whether
   a later input is queued behind the existing per-process AgentLoop lock.
3. Clarification is still plain text. There is no structured
   `waiting_for_user` state bound to task, revision, and node, and no explicit
   resume transition after the user answers.
4. `PlanningLoopAdapter` accepts a `replan_proposer`, but the CLI-created
   controller does not yet select a `PlannerPlugin` and bind its pure
   `propose_replan` callback. Failure can therefore be surfaced without
   autonomous plugin-selected replacement planning.
5. Rich output is not portable to hosts that expose ANSI escapes literally.
   The TUI needs a presentation renderer that can choose Rich for a real TTY
   and plain text for embedded or non-ANSI hosts.

The first implementation slice now carries `turn_id` and `event_type` in the
existing inbound/outbound metadata, emits a structured clarification event,
and persists clarification state through `AgentTaskCoordinator`. A user reply
to the same session resolves the waiting task before the normal Agent turn and
the existing outer controller can resume it. Hosts may inject one
`PlannerPlugin` into `AgentLoop`; its pure `propose_replan` method is then
passed to the existing `PlanningLoopAdapter` without moving plugin code into
PAOS Core.

The implementation boundary is a thin Agent/TUI presentation adapter. It may
add correlation metadata and render state, but it must not become a task
store, scheduler, Gateway client, or lifecycle authority. AgentTask state
continues to be owned by `AgentTaskCoordinator`; DAG execution remains in
`PlanningLoopAdapter`; provider-side conversation state remains absent; and a
planner plugin remains a pure graph/replan proposer.

The recommended implementation order is:

```text
correlated bus events
  -> per-session turn queue/state
  -> structured clarification event
  -> planner plugin replan callback
  -> TUI renderer (ANSI/plain)
```

`prompt_toolkit` remains the near-term input surface because it already
provides editing, history, paste handling, and async prompts. A future
Textual view may replace only this presentation adapter and render the same
events and Coordinator snapshots; it must not introduce another AgentTask or
execution implementation. Rich Live, questionary, and InquirerPy do not
provide the required combined async input, event routing, and task-state view.
