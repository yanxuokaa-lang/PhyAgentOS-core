# Pick and Place Workflow Forge Skill

This directory is an independently installable Forge Skill source bundle for the
provider-neutral `scene.observe`, `manipulation.capabilities`, `scene.understand`,
`scene.bind`, `task.goal`, `manipulation.target`, `grasp.propose`,
`manipulation.prepare`, `object.acquire`, and `object.place`
Query/Action contracts. It is an
example integration and is not part
of the `PhyAgentOS` Python distribution.

The Skill is intentionally named `pick-place-workflow` because it describes a
complete atomic pick/place workflow. It is not a `scene-observe` Skill and does not claim
that observation alone includes grasping or manipulation.

The implementation deliberately has no simulator, robot SDK, camera driver, or
actuator dependency. `FakeGatewayTransport` is used for contract and workflow tests;
deployment adapters can replace the observation, understanding, proposal, and
preparation providers without changing the ToolSpec or PAOS Agent route.
It also does not include YOLO/Ultralytics or any other detector; a provider result
from `grasp.propose` is a contract-shaped proposal fixture, not object detection or
successful grasp execution.

The capability dependency graph is:

```text
task.goal ────────────────────────────────────────┐
scene.observe -> scene.understand -> scene.bind ──┼─ manipulation.target
                         └─ manipulation.capabilities ─┴─ grasp.propose -> manipulation.prepare -> object.acquire -> object.place
```

Each executable PlanNode corresponds to one Tool settlement. A higher-level
relocation is expanded into the atomic dependency graph unless a Runtime exposes
one genuine atomic relocation Action. Tool outputs remain reusable structured
facts; the Agent assembles each consumer input against that Tool's frozen schema.

`manipulation.capabilities` is a read-only, scene-bound discovery Query. It
materializes the adapter-owned capability snapshot used by downstream arm
assignment; it does not lease a resource, run readiness, create an invocation,
or authorize motion. Every later workflow step must preserve its opaque
`capability_snapshot_ref`. `scene.understand` and `manipulation.capabilities`
are independent ready Queries after `scene.observe`; the Agent may call them in
either order or in parallel. `grasp.propose` is the dependency join and becomes
ready only after both terminal Query results are available.

`manipulation.prepare` evaluates workspace, kinematic, and collision readiness
for proposed candidates and returns evidence-bound prepared candidates. It does
not execute commands, create an Action or Session, or authorize motion;
`motion_authorized` is always `false`. Results remain bound to the observation,
scene revision, frame, calibration, and candidate-set references, so a later
execution layer must perform its own admission checks.

Large predecessor values are selected without copying their full geometry into
the node prompt. `forge_plan_select.argument_sources` names a visible
`record_id` and exact field path; Coordinator resolves the full value and then
validates the final request against the frozen `manipulation.prepare` schema.
Browse source arrays and objects with `forge_plan_ready` pagination; use explicit
integer indexes in source `path` and optional destination `target_path` to assemble
nested consumer inputs. Match identities across arrays rather than assuming order.
Resolve required immutable bindings (including `destination_ref` for place)
through task-bound read-only Queries before materializing the executable segment.
The persistent profile gives the whole preparation Query one 330-second
deadline inside its 360-second Tool timeout.

`object.acquire` is the first physical-effect boundary. It consumes a fresh,
calibration-bound preparation reference through the standard Action admission
route and is reconciled through `/invocations`; approach, contact, close, lift,
and hold remain Gateway-internal phases. A terminal result contains only the
redacted `capability_outcome_summary_v1`, not provider or simulator payloads.

`object.place` is a separate bounded physical-effect Action. It consumes a
terminal successful acquire invocation, the same immutable candidate/preparation
lineage, the current Runtime execution scene, and an opaque `destination_ref`;
transport, descent, release, and retreat remain Gateway-internal. The provenance
URIs remain bound to the acquire preparation scene; `scene_revision` is the
current scene validated by Runtime before the held route continues. Its terminal summary adds typed
`post_release_evidence` for downstream verification, without exposing
coordinates, simulator parameters, or controller details.

The `robotwin-persistent` and `robotwin-blocks-ranking-observed` profiles use
observation-owned route geometry and GraspNet by default. Their provider,
route-transform attestation, and source-root inputs are passed together through
the deployment profile. The explicit `robotwin-blocks-ranking-graspgen` profile
keeps the GraspGen worker and GraspGen-only route adaptation isolated in its own
dataflow. `robotwin-blocks-ranking-oracle` keeps observation-owned semantic identity but
uses bound actor geometry and task-definition goals for the `blocks_ranking_rgb`
development baseline. No profile automatically falls back to another.

All persistent profiles enable adapter-owned task video. All
`object.acquire` and `object.place` Actions with the same PAOS task owner are
aggregated into cumulative head-camera and observer-camera MP4 artifacts. Each
Action result carries the latest task-video manifest and both cumulative views;
the final successful `object.place` therefore points to the complete multi-step
execution, while the provider-neutral Tool schemas continue to expose only
opaque evidence references. Recording observes existing simulator steps and
does not grant motion authority or add control commands.

Long-horizon orchestration remains an AgentTask concern. The bundle exposes a
replayable reducer for the atomic pick-and-place dependency graph; it stores only
step status and opaque references, delegates all execution to the existing
ForgeToolClient/AgentTask path, and uses append-only revisions for recovery. It
does not add a Gateway route, Session, cross-Tool lease, or motion authorization.

Multi-object rearrangement uses scene-bound segments rather than one static graph
containing future object roles. Each revision freezes only references available in
the current observation and ends at a fresh observation/understanding/binding
checkpoint. After every node in that graph is completed,
`forge_task_continue_plan` appends the next segment under the same task without
consuming failure-replan budget. `forge_task_begin_revision` remains reserved for
`awaiting_replan` failure recovery.

For Agent-composed long-horizon tasks, use `pick_place_workflow.agent_planning`.
The Agent supplies semantic subtasks (for example one `relocate-*` node per
entity), and `compose_agent_plan` compiles them into a PAOS `PlanGraph` with a
final verification join. `DynamicToolPlanner` exposes all frozen ToolSpec
candidates matching a node capability and delegates admission to
`PhyAgentOS.planning`; it never invokes the selected Tool. This is the
`agent_composed` mode. The existing `LongHorizonWorkflow` remains the explicit
`baseline` mode for deterministic replay and backward compatibility.

AgentLoop integration uses `forge_plan_activate` to bind the current persisted
PlanGraph and `forge_plan_ready` to inspect ready nodes. A registry guard then
performs pure admission before task-bound Forge Query/Action/Session creation;
execution and cancellation still go through the existing Coordinator/Gateway.
Ready diagnostics distinguish dependency readiness from Tool/node binding
readiness and list runtime arguments required at selection. Rejections are
persisted as redacted task events with stable code, owner, missing fields, and
same-revision retry or replan guidance.

The Agent may change subtask order, independent-arm assignments, optional
Queries, and Tool choice through a new plan/revision. It may not change adapter
workspace/limits/transforms, readiness, collision/stop rules, Gateway authority,
or Verifier criteria. A successful episode becomes an evolution candidate only
through the PAOS experience review and independent evaluation path.

## Validation

```bash
PYTHONPATH=src:/home/yanxu/PhyAgentOS-forge \
  python -m pytest -q tests
```

The tests use PAOS's real `ForgeToolClient` with an `httpx.MockTransport` and therefore
exercise discovery, readiness/context, ToolSpec binding, and Query invocation through
the documented Gateway routes. No test enables or performs motion.

### Observed RGB acceptance with GraspNet

Use robotwin-blocks-ranking-graspnet for benchmark-injected task goals and
monitored simulation Actions with observed geometry. The provider takes segmented
RGB-D object point clouds; GraspNet decodes its native output, selects the best
24 scored candidates, and the adapter applies NMS and retains at most 10 for
manipulation.prepare. No GraspGen backoff or contact offset is used.
Select graspnet.yaml and persistent-materializer.yaml together via the
existing deployment environment. Rebuild and install Node 0.7.13 and Skill 2.7.10
before running this profile; install readiness does not prove task success.
