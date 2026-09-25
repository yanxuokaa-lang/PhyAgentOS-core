---
name: pick-place-workflow
description: Execute a provider-neutral pick-and-place workflow through governed observation, grasp, preparation, acquire, and place Tools.
metadata: {"PhyAgentOS":{"always":false,"requires":{"runtime":["pick-place-workflow"]}}}
---

# Pick and Place Workflow

## Task Understanding and Multi-Object Execution

Use the user's natural-language goal, not a task-answer configuration. Activate
this Skill and create one AgentTask with the original goal, success criteria and
constraints. If the object inventory is unknown, leave the graph absent, perform
task-bound observation, capability discovery and scene understanding, then call
`forge_task_materialize_plan` with your selected semantic `nodes`. PAOS supplies
the graph identity and integrity metadata. Do not invent digests or executable
references. Preserve all discovery records in the same task.

Select entities and destinations from sensor-backed attributes and relations.
Resolve phrases such as "the left red object" against the observed scene; request
clarification or another observation when selection is ambiguous or a target is
missing. Never rewrite an entity or geometry reference to match a benchmark ID.
Calibrated named regions may be deployment data; which region serves this user's
goal is a task decision. Object count, order and goals must not come from a fixed
two-object template.

Use observed geometry for the target and relevant collision obstacles; preserve
support relations and their metric evidence. If preparation reports incomplete
observed collision coverage, obtain or bind the missing observed entities. Do not
fill gaps with simulator object poses or dimensions. Estimated envelope axes are
model coordinates, not proof of a physical object's orientation. A preparation
error reporting unavailable readiness capabilities or provider failure requires
diagnosing that evidence; regenerating candidates alone does not repair it.
If preparation reports unqualified contact geometry, inspect its rejection
summary and evidence. Refresh or improve the relevant observed geometry when
support or finger-fit evidence is insufficient. A contact-qualified candidate
still requires complete-route readiness; it is not motion authorization.

The explicitly named `robotwin-blocks-ranking-oracle` profile is a development
baseline exception: identity still comes from `scene.observe`,
`scene.understand`, and `scene.bind`, while preparation uses the bound Runtime
actor geometry and collision world. `task.goal` returns task-specification goal
facts separately from observations. Match its `execution_entity_ref` to the
mapping returned by `scene.bind` and choose the operation order yourself. Use the
opaque benchmark `destination_ref` directly in `manipulation.prepare` and
`object.place`; the Coordinator propagates the uniquely matched reference and the
Oracle Adapter resolves its Runtime-owned pose. Do not copy the benchmark 4x4
matrix into a `manipulation.target` node. Never call `task.goal` output sensor
evidence, task success, readiness, or motion approval. The Runtime must not fall
back between oracle and observed profiles.

The generic `robotwin-persistent`, `robotwin-blocks-ranking-observed`, and
`robotwin-blocks-ranking-oracle` profiles use GraspNet for pose generation.
Their route input, transform attestation, and worker source root are selected
as one GraspNet configuration closure. They do not require or pass GraspGen
environment variables.

The explicitly named `robotwin-blocks-ranking-graspgen` profile combines
observation-owned object geometry, support and collision occupancy with only
benchmark task descriptions and destinations. GraspGen generates 24 real samples
before canonicalization and filtering retains at most ten for preparation.
Use `task.goal` destinations directly; do not add `manipulation.target` nodes.
The profile retains complete-route readiness and monitored simulation Action
approval, contact/stop checks, reconciliation and cumulative video. It does not
fall back to oracle geometry or template grasps.

The graph represents your chosen obligations and dependencies. One PlanNode is one
settlement unit completed by one selected Tool. A composite intention such as
`object.relocate` is not an executable node unless the Runtime publishes one atomic
Tool that owns the complete relocation. Before materializing a graph, complete
the task-bound read-only Queries needed to establish every candidate's immutable
`input_binding_keys`. In observation-owned profiles, resolve
`manipulation.target` first when `object.place` requires an existing
`destination_ref`; a dependency cannot stand in for that reference. In the
explicit benchmark profile, use the unique `task.goal` destination propagated by
the Coordinator instead. Then materialize the current scene-bound relocation as
atomic `grasp.propose -> manipulation.prepare -> object.acquire -> object.place`
nodes (or the remaining suffix if earlier Queries already settled), followed by its
post-placement observation, understanding, and binding checkpoint. The Tools do
not need producer-specific payload agreements: use each consumer's frozen
ToolSpec, and let the Agent select its arguments from immutable node bindings,
selected discovery records, and direct-predecessor structured results.

Do not freeze future `entity_ref`, `destination_ref`, Tool record IDs, or evidence
references from natural-language roles. An opaque evidence reference is legal only
after the Coordinator has persisted it; use dependencies to express future causal
ordering. After the checkpoint graph is fully settled, call
`forge_task_continue_plan` with the next segment and exact current evidence
references. This normal continuation keeps the same task identity and does not
consume failure-replan budget. A final observation/verification segment joins all
requested placements. Keep the original success criteria; do not weaken them
during recovery. Each node turn uses the task's activated Skill instructions, not
a later revision loaded silently during execution.

Before materializing a multi-object rearrangement, check whether a selected
destination is still occupied by another object that must move. A sequential
place must not overwrite an occupied destination. Break each relocation cycle
through an unoccupied staging destination whose free space, support geometry,
object fit, and later recovery path are supported by the current observation
and binding evidence. Re-observe and rebind after every staged placement. If no
such destination is evidenced, request clarification or stop; do not invent a
buffer pose. A simultaneous multi-arm swap is admissible only when the Runtime
exposes one atomic synchronized capability with inter-arm collision evidence.

Use settled results and postcondition evidence to decide whether to advance.
For failure, choose stop, replay or replan from the facts. In PAOS, replay means
recomputing the reducer from existing records, not repeating a grasp. A new
physical attempt requires a new admitted plan revision. Unknown Action effects
must be reconciled by invocation ID before any retry. Final success requires
the existing task Verifier to evaluate all requested destinations in the last
observed scene, including legitimate recovery attempts.

## Capability Workflow

### Object Binding and Explicit Targets

Use `scene.bind` for one or more selected observation entities and their matching
observation/scene/calibration references. It returns geometric correspondence,
`binding_ref`, world object geometry and the calibrated observation transform.
Identity binding does not require a placement goal or an arrangement task.

When the active Runtime publishes `task.goal`, call it as a task-bound read-only
discovery Query before materializing goal-bound nodes. It may expose exact goals
from a simulator task definition or another deployment-owned task specification;
its provenance is distinct from observation. The Agent remains responsible for
matching each goal to a bound entity and choosing order, staging, and recovery.
For the explicit benchmark profile, preserve the matched opaque
`destination_ref`; do not reproduce its numeric pose through
`manipulation.target`.

Choose task relations, reference frames, destinations, intermediate placements
and dependencies from the user goal and observed evidence. Never equate camera
left with world+x. When the user's reference frame is ambiguous, clarify it.
Use `manipulation.target` to resolve a chosen object pose: supply binding_ref,
entity_ref, frame_id, unit=m and a row-major 4x4 frame_T_object_target. Supported
frames are world and the bound observation frame. The resolver does not sort,
choose slots, preserve a height implicitly or create an execution sequence.
Derive proposed poses from returned geometry and explicit task constraints;
do not invent benchmark coordinates or opaque destination references.

The resulting destination_ref is a geometric proposal, not permission or proof
of feasibility. Pass it through manipulation.prepare and existing Action
admission. Rejected targets require Agent reconsideration, not silent changes by
the resolver. Binding validity follows the provider's declared scene model;
action-driven simulation validity does not imply stationary real-world objects.
After motion, obtain new observations and bindings before the next preparation.
The final Verifier evaluates the original user goal against final observations,
not agreement with the proposed target alone.

This Skill describes one complete provider-neutral pick-and-place workflow. It is
not a scene-observation-only Skill: `scene.observe` and `scene.understand` are the
perception steps, `grasp.propose` and `manipulation.prepare` are non-mutating
planning/readiness steps, and `object.acquire` plus `object.place` are bounded
physical-effect Actions. The Skill does not implement any provider, simulator,
camera driver, robot SDK, or task-specific success rule.

Use `scene.observe` only to obtain measured observation artifacts. Before invocation,
read the ToolSpec and live context through `forge_tool_context`; use the declared
sensor reference and freshness fields. On the initial observation, omit the optional
`requested_frame`: `robot_frame_profile.observation_frame` is an abstract sensor
role, not a concrete frame identifier. If a later call must constrain the frame,
`requested_frame` must exactly equal a concrete `frame.frame_id` returned by an
earlier observation for the same sensor; never send labels such as `sensor` or
`observation`. A successful Query does not authorize planning or motion and must not
be passed directly to an Action.

The Query returns an explicit status, capture timestamp, scene revision, frame identity,
calibration reference, freshness measurement, and opaque artifact references. Treat
`unavailable`, `stale`, and `invalid` as blockers. Do not retry a stale or missing-
calibration result by weakening `max_age_ms`; obtain a new observation or operator input.

After a successful `scene.observe` result, the Agent may call
`manipulation.capabilities` or `scene.understand`; these are independent Query
nodes and may be called in either order or in parallel. For
`manipulation.capabilities`, pass the
observation reference, scene revision, and calibration reference unchanged. This
read-only Query returns the adapter-owned, scene-bound capability snapshot used to
reason about available arms and later assignment. It does not lease a resource,
run readiness, create an invocation, or authorize motion. Treat `unavailable`,
`stale`, and `invalid` as blockers, and preserve its opaque
`capability_snapshot_ref` for every downstream step.

Use `scene.understand` after a successful `scene.observe` result. It does not
depend on the capability Query. Pass the returned
`observation_ref`, scene revision, frame, calibration reference, freshness, and artifact
references unchanged. The understanding Query returns entity/relation claims and spatial
envelopes with confidence and provenance. It may also return opaque derived artifacts for
instance masks, object point clouds, and metric localization, but only when their observation,
entity, frame, calibration, source lineage, and root provenance bindings are complete. These
artifacts are Query evidence, not grasp candidates or motion authorization. Reject stale,
unavailable, ambiguous, or invalid results before any future Action.

Use `grasp.propose` only after both `scene.understand` and
`manipulation.capabilities` have returned successful terminal results. The Agent
may satisfy those two dependencies in either order or in parallel:

```text
scene.observe
  ├─ manipulation.capabilities ─┐
  └─ scene.understand ───────────┴─ grasp.propose
  -> manipulation.prepare
  -> object.acquire
  -> object.place
```

Pass the returned observation reference, scene revision, frame, calibration reference,
freshness, and target entity claims with their spatial envelopes unchanged. Never skip the
freshness, calibration, frame, or provenance checks. The proposal Query returns
provider-neutral grasp candidates with candidate identity, frame/calibration binding,
provenance, confidence, score, and bounded funnel evidence. Candidates are proposals only:
they are not IK-verified, not collision-free, and not action-admitted, and they must not be
sent directly to an Action. An `empty` result means no candidates exist for the targets; do
not fabricate or substitute default candidates and do not loosen thresholds or skip safety
checks to obtain candidates. Any further preparation must go through an independent
`manipulation.prepare` Query, and motion authorization stays with the Gateway/Runtime
admission path.

The `entity_ref` selected for a projection must be the opaque primary key copied
verbatim from the current `scene.bind`/`scene.understand` record. If the active
PlanGraph already contains a unique Coordinator-owned entity binding, omit the
selector and let PAOS project that binding. Do not rename
`entity://block-red-1` to a color-derived alias such as `entity://red-block-1`;
category and color are descriptive fields, not identity.

Use `manipulation.prepare` only after a successful `grasp.propose` result. Pass the
observation reference, scene revision, frame, calibration reference, freshness,
candidate-set reference, and complete candidate records unchanged. This Query is a
non-mutating readiness assessment with three explicit checks: `workspace`,
`kinematic`, and `collision`. Only candidates with all three checks reported as
`pass` can appear as `qualification: prepared`; rejected candidates are omitted and
an empty set is returned explicitly as `status: empty`.

For an agent-composed preparation node, include semantic fields directly in
`forge_plan_select.arguments` (or as a nested `intent` object): `goal`, non-empty
`success_criteria`, one or more exact `allowed_arms`, `coordination_mode` (`single_arm`,
`alternative_arm`, or `bimanual`), and optional `constraints`. Do not provide
task/revision/node identity, node digest, observation bindings, entity identity,
or `motion_authorized`; PAOS derives those fields from the active graph and final
Tool arguments. Flat and nested forms must not conflict with each other or with
the node declaration. Use the returned `selection.tool_arguments` unchanged for
`forge_tool_query`, together with the returned `planning_binding`.

`allowed_arms` must copy the `arm_id` strings from the same-scene
`manipulation.capabilities` snapshot verbatim. For an `alternative_arm` node,
PAOS may already bind all available IDs from that snapshot; in that case use the
node binding and do not repeat the field. They are opaque Runtime resource
identifiers, not natural-language labels: for this profile the values are `left`
and `right`; do not rewrite them as `left_arm`/`right_arm` or invent aliases.

Preparation evidence is not an IK guarantee, collision guarantee for a future
trajectory, or execution admission. Treat `stale`, `unavailable`, and `invalid` as
blockers. Never call `invoke_action` or start a Session with this Query, and never
interpret `motion_authorized: false` as permission to bypass the Gateway/Runtime
admission path.

Use `object.acquire` only after `manipulation.prepare` returned a selected prepared
candidate and the current Tool context is ready. Create one AgentTask binding and
pass the observation, scene, frame, calibration, candidate-set, preparation,
candidate, and entity references unchanged. Start it through
`forge_tool_start_action`, then reconcile the returned `invocation_id` with the
standard status/result routes. Admission is not completion; pending, cancellation
acceptance, timeout, and `unknown` do not prove a physical stop and must not be
blindly retried.

The bounded Action owns its internal approach/contact/close/lift/hold phases. Use
the terminal `capability_outcome_summary_v1` for phase attribution only after the
Gateway result is terminal. It is execution evidence, not a replacement for
`AgentTask finalize` or the generic verification contract.

Use `object.place` only after `object.acquire` is terminal with `status: succeeded`.
Pass the acquire observation, frame, calibration, candidate-set, preparation,
candidate, and entity references unchanged, plus the acquire invocation reference
and an opaque `destination_ref`. The `scene_revision` field names the current
Runtime execution scene after acquire; the provenance URIs remain bound to the
scene in which the route was prepared. A destination reference
does not expose coordinates, simulator fields, or controller parameters; its
meaning is resolved by the Gateway profile. Transport, descent, release, and
retreat are internal bounded phases. Reconcile the place invocation through the
standard status/result/cancel routes and treat cancellation acceptance and
`unknown` as physically uncertain.

The terminal place summary includes `post_release_evidence`, which reports only
typed artifact references and their availability. This evidence is required for
verification of the released object's destination state; a successful Action is
not by itself a user-level task verdict. Do not retry release blindly or infer
placement from an unverified acquire result.

For a long-horizon pick-and-place task, keep one AgentTask and one PAOS-owned
append-only PlanRevision across the complete sequence. The Skill exposes a
read-only semantic DAG projection (`WORKFLOW_DAG`) for dependencies and ready
nodes; it does not create revisions, hold resource leases, or execute Tools:

```text
observe -> {capabilities, understand} -> propose -> prepare -> acquire -> place
```

The workflow reducer is a replayable projection over existing Tool records. It
accepts only terminal Tool results and opaque references, rejects skipped steps or
cross-scene bindings, and exposes the next declared Tool without invoking a
Gateway. `failed`, `cancelled`, and `unknown` stop automatic progression. Reconcile
an unknown invocation by its existing ID; for a recoverable failure ask the PAOS
task coordinator to append a new PlanRevision, then rebind this projection to
that revision. Never create a second execution protocol or infer task success
from a single Action summary.

For a task whose objects must be decomposed or assigned dynamically, the Agent
may select `planning_mode=agent_composed` and submit semantic subtasks to
`compose_agent_plan`. The resulting PlanGraph describes obligations and
dependencies, not a hard-coded Tool sequence. For each ready node,
`DynamicToolPlanner.candidate_tools` returns all frozen Tool candidates matching
the node capability; the Agent chooses one and `DynamicToolPlanner.admit`
performs PAOS evidence, scene, capability, resource, and ToolSpec checks before
the caller invokes the normal AgentTask/ForgeToolClient path. This bridge does
not execute Tools, create revisions, hold leases, or authorize motion. The
`baseline` reducer remains available for deterministic replay.

When running through AgentLoop, activate a persisted agent-composed revision
with `forge_plan_activate`, then call `forge_plan_ready` before selecting a
Forge Tool. For each ready node, call `forge_plan_select` with the node, frozen
candidate Tool, exact semantic Tool arguments, and a short decision reason.
PAOS returns the complete Coordinator-owned `planning_binding` and
`selection.tool_arguments`; pass both unchanged to the task-bound Query or
Action wrapper. Never calculate node/input digests, add Coordinator-owned
intent identity, or invent a decision-trace reference. The selection tool is
control-plane only and does not invoke a Gateway, authorize motion, or replace
Coordinator/Gateway execution and reconciliation.

Once `forge_plan_select` succeeds, that node has one durable unconsumed
selection. Execute the returned receipt; do not select a second Tool for the
same node. A different implementation choice requires a governed replacement
revision before any execution fact exists, or normal recovery after failure.

For `manipulation.prepare`, use prompt-visible literals for small fields and
`forge_plan_select.argument_sources` for large Producer values such as the
complete candidate array. A source names the visible predecessor/evidence
`record_id` and exact source path; PAOS resolves the complete value
and validates the resulting arguments against the frozen consumer schema before
persisting the selection.
For arrays or nested objects, browse the authorized record using
`forge_plan_ready(node_id, source_record_id, source_path, offset, limit)` and
follow `next_offset` until the needed item is visible. Paths contain field
strings and integer array indexes, not dotted strings or JSONPath expressions.
Associate entities, envelopes and artifact records by their visible identity;
do not assume parallel arrays share an order. Each source can set `target_path`
such as `["targets", 0, "category"]` to copy one exact source value into a nested
consumer field. Build only the fields required/allowed by that consumer's schema;
an entire producer entity or envelope can contain extra metadata. Without
`target_path`, the source map key remains a literal top-level parameter name.
When the receipt sets `use_selected_arguments=true`, invoke its execution Tool
with `arguments={}`, that flag, and the exact `planning_binding`; PAOS loads the
persisted complete parameters without another model payload round trip.
Do not copy summarized geometry into literal arguments or select an unrelated
record. A `missing_runtime_arguments` rejection is retryable
in the same revision after adding the listed fields. A
`node_tool_binding_incompatible` rejection means the immutable graph itself is
not bindable; replace the segment through the governed revision path instead of
retrying the same selection.

The persistent Runtime freezes a 360-second default timeout for
`manipulation.prepare`, matching its worker request boundary so the Query does
not fall back to the generic 10-second Forge HTTP default. Its shipped profile
uses one 330-second internal deadline across materialization, readiness, and
finalization. A timeout is a no-motion `preparation_timeout`; it does not
authorize motion or retry a provider failure. The legacy `robotwin-persistent`
profile and `robotwin-blocks-ranking-observed` use observation-owned route
geometry. `robotwin-blocks-ranking-oracle` uses bound actor geometry for the
`blocks_ranking_rgb` development baseline. These are explicit profiles, never an
automatic recovery choice. All three return an adapter-owned cumulative task-video manifest and both
camera MP4 references as opaque Action evidence; never treat their contents as
Tool arguments or motion authority.

When submitting semantic nodes, use exact task-bound
`paos_record.evidence_refs` for evidence already available at the graph root.
Do not put labels such as `latest_observation`, `metric_geometry`, or
`entity_binding` in `required_evidence` unless a Tool actually returned that
exact opaque reference. The optional `evidence_refs` argument only selects from
the task-bound references already persisted by Coordinator; it cannot create or
rename evidence. Use `dependencies` for ordering and keep prose in the
obligation or `input_bindings`. A `conditions` key is legal only when the same
key is already true in trusted Coordinator `condition_facts`, or when a prior
Tool node will persist it before the dependent node is evaluated. Read
`forge_plan_ready.node_diagnostics` to distinguish missing dependencies,
evidence, conditions, and Tool candidates; never bypass an empty ready set.

Before any execution or settlement is attached to a newly materialized graph,
one corrected semantic graph may be resubmitted and will become a new
append-only revision. Once execution facts exist, use failure replan only for
failed or unknown execution. For successful dynamic-scene progress, complete
the current checkpoint graph and call `forge_task_continue_plan`; discovery
correction and failure replan are not normal forward-progression mechanisms.
