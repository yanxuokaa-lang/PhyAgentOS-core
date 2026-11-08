# RoboTwin stack_blocks_three Integration Diagnosis

Date: 2026-11-06 (Asia/Shanghai)
Status: relation-target Query integration implemented; motion remains disabled.

## Finding

The task is partially integrated. `StackBlocksThreeTaskAdapter` exposes three
ordered `on` relations and a no-motion block-on-block target candidate derived
from current simulator actor poses and collision extents. Table support and
tilted-support geometry remain unavailable. The adapter explicitly sets
`motion_execution_supported = False`; `RoboTwinPersistentEngine` rejects
route/contact readiness and action preparation for this task.

The RoboTwin Runtime supports task profiles, but the repository currently has
only a `blocks_ranking_rgb` task profile. The current shell also has no
RoboTwin runtime path configuration, so a live simulation cannot be launched
or qualified from this environment yet.

The domain seam is split deliberately: the pick-place workflow now has a
provider-neutral `relation.target` Query Tool, but no relation execution
capability or qualified `relation.establish` Action settlement. Existing
`object.place` requires a destination reference and resolved scene-bound pose;
the Query only supplies a current block-on-block candidate and cannot be
treated as execution readiness or settlement.

## Concrete Failure Scenario

After `block-2` is observed above `block-1`, the Agent can select the semantic
`place_middle` obligation. No registered capability resolves the current
support geometry into a target pose for that relation. If the Agent bypasses
that gap by supplying a static `object.place` destination, the target may no
longer match the current block pose, support footprint, or observation. The
current engine's `motion_execution_supported = False` prevents this unsafe
fallback from reaching Action preparation.

The Query binds geometry evidence to the active scene revision and fresh
observation. Ordinary task IDs and tests cannot qualify motion or prove
simulation behavior; no additional hashes, frozen contracts, or speculative
gates are needed.

## PAOS Ownership

- Agent and generic planning own relation semantics, predecessor ordering,
  segment selection, and evidence requirements. AgentLoop remains the sole
  workflow driver.
- The new domain port accepts opaque entity/support references and current
  observation identity, and returns provider-neutral relation-target
  candidates plus evidence references. It contains no simulator actor names,
  filesystem paths, or SDK handles.
- The RoboTwin Provider owns scene-specific object/support geometry and
  candidate transform generation. The current implementation supports
  upright block-on-block center alignment only. Missing table geometry,
  tilted support, stale observation, or unsupported relation returns
  unavailable; it does not invent a target pose.
- Existing Action admission/`object.acquire`/`object.place` own route
  preparation, execution and bounded feedback. The Coordinator remains the
  sole task/revision/settlement owner. No second scheduler or settlement store
  is introduced.
- Motion capability remains disabled until the actual RoboTwin task profile,
  frames/calibration, relation geometry, route readiness and Action path are
  validated in no-motion tests and then in an explicitly scoped simulation.

## Implementation Order

1. [complete] Add the task-specific RoboTwin Runtime profile and keep it
   separate from deployment paths and secrets.
2. [complete] Define the provider-neutral relation-target port and its
   stale/missing-evidence behavior.
3. [partial] Wire the RoboTwin block-on-block geometry Provider through the
   existing Tool/workflow registration path with Provider substitution;
   tabletop/tilted support and execution remain unsupported.
4. Reuse existing acquisition, placement, Action admission, AgentLoop and
   Coordinator lifecycles rather than creating a relation-specific executor
   loop or state owner.
5. Add contract, substitution, geometry, freshness, failure and unknown-result
   tests. Keep motion closed until the separately provisioned RoboTwin runtime
   can produce reviewed simulation evidence.

## Acceptance Evidence

Contract tests prove domain semantics, opaque identity, freshness binding and
Provider substitution. Provider tests prove upright block-on-block geometry
projection and unavailable outcomes for unsupported support facts. Simulation
evidence is a separate acceptance layer and is not claimed by unit/integration
tests. No live RoboTwin simulation, Gateway Action, or physical robot motion
has been run for this diagnosis. `stack_blocks_three` is not executable.

## 2026-11-08 Persistent Action Provider Wiring

The provider-neutral `relation.establish` Action endpoint was already
implemented by the workflow Runtime, but the RoboTwin-specific
`build_persistent_runtime_bundle` did not forward its Provider and Coordinator
context-resolver arguments. A qualified Provider supplied at this deployment
boundary therefore could not become visible in the RoboTwin Runtime Tool
registry. This was an integration gap, not missing task lifecycle ownership.

The bundle now forwards both optional ports to the existing generic Runtime.
The generic Runtime remains responsible for validating that they are supplied
together and registering the endpoint. A substitution integration test checks
that the supplied Provider and resolver reach the registered endpoint without
invoking Action admission.

This only closes the Provider injection path. No concrete RoboTwin relation
execution Provider is supplied; table support geometry, route/contact
qualification, RoboTwin runtime installation, and simulation evidence remain
missing. `StackBlocksThreeTaskAdapter.motion_execution_supported` remains
false. No PAOS task, Action, simulator, or robot motion was started, and
`stack_blocks_three` remains non-executable.

## 2026-11-06 Execution Initiation Check

The requested `stack_blocks_three` task was not launched. Read-only checks found
that `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime.env`
selects `profiles/robotwin20/franka-blocks-ranking.yaml`, not the stack profile;
its configured `/home/yanxu/robotwin20-runtime/RoboTwin` runtime root does not
exist, and the configured artifact root is also absent. The `RoboTwin20` Conda
environment has SAPIEN and PyTorch, but this environment does not resolve the
`robotwin` package or Curobo. No RoboTwin, SAPIEN, or Dora simulation process is
running. Existing gateway/model processes are unrelated and were left untouched.

The software path is also intentionally incomplete for execution:
`compose_relation_goal_plan` emits `relation.establish`, but the repository has
no Action/settlement implementation for that capability; the stack Adapter
keeps `motion_execution_supported = False`, and the persistent engine refuses
route readiness and Action preparation. A `relation.target` Query is geometry
evidence, not an executable placement or completion receipt. Creating a task
record now would produce an unexecutable task, while using the configured
blocks-ranking profile would launch the wrong benchmark.

PAOS ownership and next implementation sequence:

- Agent/AgentLoop owns semantic segment selection and drives one persisted node
  at a time; Coordinator remains the sole task/revision and settlement owner.
- Add the `relation.establish` execution capability through existing Action
  admission and settlement ports. The Runtime/Adapter owns grasp selection,
  route generation, collision/support checking, gripper execution and measured
  feedback; do not put these mechanisms in generic planning or create a second
  scheduler.
- Complete current-scene support geometry for the table relation and retain
  observation, scene revision, frame and calibration provenance. Require an
  explicit unavailable result when geometry or calibration is absent.
- Only after the operator-provisioned RoboTwin root and task-specific runtime
  dependencies are present, run no-motion readiness and route checks, then a
  scoped simulation task through AgentLoop. Stop and require reconciliation
  for unknown execution/possession/contact outcomes; never blindly retry.

No source behavior was changed and no task record, Gateway Action, simulator,
or robot motion was started in this initiation check. The requested task launch
is blocked by the missing Runtime root and missing `relation.establish`
execution/settlement Provider, not by the same-task continuation lifecycle.

## 2026-11-07 Recheck and Execution Decision

The launch prerequisites were rechecked on 2026-11-07 at 17:37 Asia/Shanghai.
The configured deployment still selects
`/home/yanxu/PhyAgentOS-forge/examples/forge-adapters/robotwin20/profiles/robotwin20/franka-blocks-ranking.yaml`,
while the task-specific `stack-blocks-three.yaml` profile exists in the
repository. Both `/home/yanxu/robotwin20-runtime/RoboTwin` and the configured
`/home/yanxu/robotwin20-runtime/artifacts` root remain absent. The `RoboTwin20`
Python environment resolves `sapien` and `torch`, but not `robotwin` or
`curobo`; no RoboTwin, SAPIEN, Dora, or Isaac Sim process is running.

The implementation boundary is unchanged: `relation.target` is a fresh-scene
geometry Query, not an Action. `compose_relation_goal_plan` emits the semantic
capability `relation.establish`, but no Tool/Action admission and settlement
Provider handles that capability. The stack Adapter still declares
`motion_execution_supported = False`, rejects route readiness and preparation,
and returns unavailable for table support geometry. Block-on-block geometry
alone cannot complete `stack_blocks_three`, whose first relation is block-on-
table.

The concrete unsafe failure remains: converting a Query candidate directly to
`object.place` could use an unqualified support surface, route, contact model,
or stale scene binding, and would incorrectly treat a geometric proposal as a
settled physical effect. Existing task/revision IDs and Coordinator settlement
do not establish those missing physical facts. No hash or parallel lifecycle
is needed; the necessary evidence must come from the Runtime/Adapter and the
existing Action receipt/Coordinator settlement path.

**Execution decision:** do not create a PAOS task record or invoke AgentLoop
against the current deployment. It would use the wrong benchmark profile and
cannot pass Runtime readiness or `relation.establish` Action admission. No
Gateway Action, simulation, or robot motion was started. Unknown execution,
possession, contact, or support state must remain blocked for reconciliation;
there is no automatic return-home or retry.

**Next implementation/qualification sequence:**

1. Provision the operator-owned RoboTwin source/runtime and task dependencies,
   select the stack-specific profile in an isolated deployment config, and
   provide its artifact root. Do not overwrite the blocks-ranking deployment.
2. Implement relation execution through the stable domain capability and
   existing PAOS Action admission path. Keep generic AgentLoop/Coordinator
   responsible for semantic node selection and settlement; keep target geometry,
   route generation, collision/support checks, execution feedback, and
   environment-specific references inside the RoboTwin Adapter/Provider.
3. Prove table and block support geometry against current observation, scene
   revision, frame, and calibration. Reuse acquire/place Actions and their
   receipts; unknown outcomes stop for reconciliation.
4. Run no-motion capability, route, and failure-path tests first. Only after
   those pass, run an explicitly scoped simulation through AgentLoop and
   preserve separate contract, Provider, and live-simulation evidence.

## 2026-11-07 Relation Binding Implementation

Added `bind_relation_target_candidate` at the provider-neutral relation Query
boundary. It projects an explicitly selected candidate into an
Action-facing domain binding only when the result is available, motion remains
unauthorized, and entity/relation/support/observation/scene/frame/calibration
all match the caller's current node. It preserves the opaque destination,
candidate-set identity, target transform, and geometry evidence refs. Missing,
duplicated, invalid, or stale candidates fail before an Action can consume the
binding.

This closes the Query-to-domain-binding projection gap; it does **not** add a
`relation.establish` Tool/Action provider or route readiness. The binding is
not yet consumed by `SubtaskActionEndpoint`, because the current stack adapter
cannot resolve the first `surface://table` target and the persistent engine
still refuses stack motion preparation. Do not treat the projection as a
placement route or settlement. `motion_execution_supported` remains false;
no task, Gateway Action, simulator, or robot motion was started. The next
implementation boundary is provider consumption of this domain binding plus
table geometry and route/contact qualification, using the existing Action
admission and Coordinator settlement path.

## 2026-11-08 Relation Action Contract Implementation

The remaining software integration gap was that the provider-neutral candidate
projection had no Agent-facing Action endpoint. Added an optional
`relation.establish` Tool registration to the existing `CapabilityRuntime`.
Registration requires both a Relation Execution Provider and a Coordinator
context resolver; supplying only one is rejected. The endpoint accepts only a
PAOS task caller, checks the current Coordinator node and persisted no-motion
intent, then rebuilds its Action binding from the actual `relation.target`
Query result plus the selected candidate reference. The Tool policy records
that Query result as sourced from `relation.target`.

The generic endpoint does not compute support geometry, plan a route, validate
contact, or move the robot. Those remain Provider responsibilities. Provider
admission is deferred until the Runtime supplies invocation and attempt IDs.
An invalid/missing provider admission or exception is represented as
`outcome_unknown`, never a successful relation settlement. Explicit
`unavailable` remains Provider-owned. The Coordinator continues to own task
revision and settlement; AgentLoop remains the workflow driver.

The concrete RoboTwin stack Provider is still not implemented or registered.
Table support geometry, route/contact qualification, Runtime installation, and
simulation evidence remain absent. `motion_execution_supported` remains false;
this contract alone does not make `stack_blocks_three` executable and does not
authorize task launch, Gateway Action, simulation, or robot motion.

Architecture review:

- Generic domain: relation identity, selected Query candidate projection,
  current-node/freshness validation, and Action lifecycle handoff.
- Provider/Adapter: support geometry, route generation, collision/contact
  checks, motion, and physical execution feedback.
- Replaceability: a replay or RoboTwin Provider can implement the same `admit`
  port without changing the endpoint, Agent plan, or AgentLoop route.
- Evidence boundary: `relation.target` response must match current
  entity/relation/support/scene/observation/frame/calibration; Action receives
  only the selected, validated projection and its evidence refs.
- Lifecycle and recovery: Runtime owns invocation; Coordinator owns settlement;
  unknown execution remains blocked for reconciliation; no recovery scheduler
  or blind retry was added.
- Smallest leak test: a stale Query candidate must be rejected before Provider
  admission; Provider substitution and exception tests prove the seam and
  unknown-result boundary without simulator motion.

Failure scenario and mechanism rationale: if an Agent can submit a fabricated
target transform with matching object identity, task IDs and Coordinator node
binding cannot prove that the geometry came from the current observation. The
Action endpoint therefore consumes the source Query result and selected
candidate together and runs the existing lineage-aware projection before
Provider admission. No hashes, new settlement store, or extra execution gate
were added. This still does not qualify the Provider's route or prove physical
execution.

Validation covers contract, lineage mismatch, Provider substitution, explicit
unavailable propagation, and unknown Provider failure. Contract evidence is
separate from RoboTwin Provider evidence and live simulation evidence; neither
of the latter is claimed.

## 2026-11-08 Production Host Provider Injection

The previous bundle-level wiring was not reachable through the standard
`build_persistent_host` entry point: the host did not accept a relation
execution Provider or Coordinator resolver and therefore called the bundle
without either. A Provider injected only by directly constructing the bundle
would not be available to the normal host composition path.

The host now accepts the optional Provider/resolver pair, checks the Provider's
`admit` port and resolver callability before starting host resources, and
forwards both to the existing bundle. Tests cover the host-to-Runtime
registration path with the Provider enabled, default behavior with it omitted,
partial-pair rejection, and invalid Provider rejection. No Action admission is
invoked by these tests.

Ownership remains unchanged: the host composes Adapter mechanisms; the generic
workflow endpoint validates relation identity and Query lineage; the Provider
owns geometry, route/contact qualification and execution; Runtime owns Action
invocation; Coordinator owns task/revision/settlement; AgentLoop remains the
workflow driver. No second scheduler or settlement store was added.

This does not supply the concrete RoboTwin relation Provider or make
`stack_blocks_three` executable. Table support geometry, qualified routes and
contact behavior, and live RoboTwin runtime evidence remain absent. Motion is
still unqualified, so no task or simulation is started.

## 2026-11-08 Runtime Provisioning Recheck

The configured `/home/yanxu/robotwin20-runtime/RoboTwin` and artifact root do
not exist. The configured `RoboTwin20` interpreter imports `sapien` and
`torch`, but does not resolve `robotwin` or `curobo`. Creating an empty artifact
directory would satisfy only a filesystem check; it would not provide simulator
assets, task classes, observations, route planning, or execution evidence.

The official `RoboTwin-1.0` repository tree was checked through GitHub's API.
Its task configs include `blocks_stack_easy.yml` and `blocks_stack_hard.yml`,
not `stack_blocks_three`. The checked-in PAOS profile names
`stack_blocks_three`, so cloning that upstream branch and pointing the current
profile at it would still fail task resolution. Renaming the profile or
silently substituting another benchmark would change the requested task and is
not an acceptable infrastructure repair.

The current PAOS stack Adapter also has no qualified `relation.establish`
Provider. The generic Tool injection path now exists, but the stack Adapter
cannot provide table support geometry, route/contact qualification, or measured
execution/settlement feedback. These mechanisms require a task implementation
whose actor, support-surface and controller interfaces are known. The
configured runtime root is absent, so implementing against guessed RoboTwin
handles would create an untestable Provider and falsely imply execution
readiness.

**Decision:** preserve `motion_execution_supported = False`; do not create an
empty Runtime/artifact root, switch to `blocks_stack_easy`, create a PAOS task,
or invoke an Action. To continue without changing task semantics, provide the
intended `stack_blocks_three` task source/config and its supported RoboTwin
revision (or explicitly authorize adapting the task to official
`blocks_stack_easy`). Once that source is fixed, provision its external assets
and dependencies, then implement table/block support geometry and relation
execution inside the RoboTwin Adapter Provider; validate no-motion contracts,
route/contact behavior and failure/unknown outcomes before any simulation
execution. Coordinator and AgentLoop lifecycle ownership remains unchanged.

No repository source behavior was changed in this recheck. The official task
inventory and local environment facts are diagnostic evidence only; they are
not RoboTwin runtime, Provider, or simulation qualification evidence.

## 2026-11-08 Corrected Runtime and Table Geometry Findings

Correction: the preceding section's statement that the RoboTwin Runtime root
is absent was incorrect. A usable checkout is present at
`/home/data/yanxu_migrated/RoboTwin` (`main`, revision `3095469`), and it
contains both `envs/stack_blocks_three.py` and
`env_cfg/task_config/demo_clean.yml`. The deployment file pointed at an
obsolete path and selected the unrelated `blocks_ranking_rgb` profile; this
was a configuration defect, not a missing task source.

The deployment now selects the existing checkout and a dedicated
`stack-blocks-three.yaml` profile. Its artifact root is the isolated
`/home/data/yanxu_migrated/robotwin-stack-blocks-three/artifacts`; the prior
benchmark artifact tree is untouched. The profile loads successfully and
resolves `stack_blocks_three`, `demo_clean`, the dual Franka embodiment, and
the two configured camera references.

The stack Adapter now resolves the table support candidate from the current
SAPIEN table actor's collision shapes, requires exactly one broad horizontal
tabletop shape, and derives the object's support height from its current
collision extents. Placement XY comes from the task's declared
`block1_target_pose`. Missing, malformed, ambiguous, or tilted support
geometry returns `unavailable`; this Query does not qualify a route or
authorize Action execution. Tests cover table and block support geometry,
stale-observation rejection, and missing table geometry.

No-motion preflight evidence on 2026-11-08: Runtime root, Python, task source,
task config, Torch CUDA kernel, SAPIEN renderer, and Vulkan passed. Preflight
still fails because `assets/background_texture`, `assets/embodiments`, and
`assets/objects` are empty, the Franka embodiment config is absent, `curobo`
is not installed, and importing the task fails on
`assets/objects/objaverse/list.json`. At check time `/home/data` had only
6.0 GB free, less than the approximately 14.9 GB official asset archive; no
download or installer was started. The root filesystem had 735 MB free and
was not used for provisioning.

The concrete RoboTwin `relation.establish` execution Provider remains
unimplemented and unqualified. The current relation Query supplies target
geometry only; it does not supply a qualified stack grasp/contact route. The
benchmark's synchronous `pick_and_place_block` helper is not wired as a
Provider because it advances the simulator outside the Gateway-owned,
pollable/stoppable Action driver and does not provide PAOS route/contact
qualification evidence. `motion_execution_supported` therefore remains
false and no task, Action, simulator, or motion was started.

Architecture ownership remains: task/revision/settlement in Coordinator,
workflow driving in AgentLoop, geometry and any future route/execution
mechanism in the RoboTwin Adapter Provider, and invocation state in the
existing CapabilityRuntime. No lifecycle or settlement store was added.

## 2026-11-08 Runtime Smoke and SAPIEN Entity API Correction

The earlier statement above that the artifact root is
`/home/data/yanxu_migrated/robotwin-stack-blocks-three/artifacts` was
incorrect. The active deployment uses the isolated writable root
`/home/yanxu/robotwin20-runtime/stack-blocks-three/artifacts`; it is outside
both the Runtime checkout and the PAOS repository. The external
`runtime.env` selects the existing `/home/data/yanxu_migrated/RoboTwin`
checkout and the checked-in `stack-blocks-three.yaml` profile.

The dedicated preflight passed all checks on 2026-11-08, including the real
asset families (11,000 background files, 229 embodiment files, 9,368 object
files), Franka configs, RoboTwin imports, Torch 2.9.1+cu128 CUDA execution on
RTX 5060 Ti capability 12.0, CuRobo modules, SAPIEN renderer and Vulkan.
CuRobo's local CUDA extension was rebuilt for `compute_120/sm_120`. A no-motion
`demo_clean` seed-0 `setup_demo` plus RGB/depth/state capture completed and
wrote typed artifacts under the isolated artifact root; it did not call
`play_once`, a robot action, or a simulation motion step. SAPIEN emitted OIDN
CUDA-device warnings, but capture completed with `sensor_available=true`.

The first real table relation Query returned `unavailable`. The concrete
failure was an Adapter/SAPIEN API mismatch: RoboTwin `create_table()` returns a
SAPIEN `Entity` whose collision components are obtained from
`get_components()`, while the Adapter only looked for `table.actor.components`.
The Adapter now reads `get_components()` on SAPIEN Entities and retains the
legacy wrapper fallback. Regression fixtures follow the actual Entity API.
The rerun returned one candidate using `current_table_collision_shape`, with
table top `z=0.7400000 m` and block-center target `z=0.7650010 m` for the live
scene revision `stack_blocks_three-0-1`.

This fixes current-scene support geometry, not relation execution. There is
still no qualified stack `relation.establish` Provider: the benchmark's
`pick_and_place_block()` synchronously advances a full trajectory and cannot
be stopped between control ticks through the Gateway Action driver. Wrapping
it in a background future would allow motion to continue after cancellation or
an unknown Action result. In addition, no stack-specific route/contact
qualification and runtime-monitored approval evidence exists. Ordinary
contract tests cannot establish simulator-thread stop behavior or physical
contact outcomes; enabling motion without those would permit post-cancellation
motion or report a relation without measured support. Keep
`motion_execution_supported = False`; no PAOS task or Action was admitted.

Architecture remains unchanged: Coordinator owns task/revision/settlement,
AgentLoop drives the workflow, CapabilityRuntime owns Action invocation, and
the RoboTwin Adapter owns environment geometry and any future qualified
execution mechanism. The remaining implementation must provide a simulator-
thread-affine bounded control-tick driver, stack-specific route/contact
qualification, explicit stop behavior, and measured placement feedback before
motion can be enabled.

## 2026-11-08 Provider Implementation Recheck

The configured RoboTwin checkout and isolated artifact root both exist:
`/home/data/yanxu_migrated/RoboTwin` and
`/home/yanxu/robotwin20-runtime/stack-blocks-three/artifacts`. The artifact
directory currently contains no qualification outputs. The configured
controller qualification `qualification.json`, `plan.json`, `evidence.json`,
and `validation.json` are absent. This is not a missing-directory defect.

Correction to the implementation handoff: PAOS relation Action plumbing is
already present. `RelationEstablishActionEndpoint` binds the request to the
Coordinator node and defers start until Gateway invocation/attempt IDs exist;
`build_persistent_runtime_bundle` registers the injected provider; and
`build_persistent_host` accepts the provider and matching context resolver.
Do not add another endpoint or lifecycle store. The unresolved work is the
concrete RoboTwin stack execution mechanism and its route/contact qualification,
not generic PAOS wiring.

The stack Adapter still reports `motion_execution_supported = False`. Keep
that state until a provider can produce a current-scene qualified single-block
route, execute it through the existing per-control-step controller stop path,
and return measured placement/support evidence. The task's `play_once()` and
`pick_and_place_block()` remain out of scope because they execute all three
placements as benchmark-owned synchronous behavior rather than one
Coordinator-settled relation Action. No task or motion Action was started in
this recheck.

Ownership remains: Coordinator owns task/revision/node settlement; AgentLoop
owns workflow progression; CapabilityRuntime/Gateway owns Action invocation
and cancellation; the RoboTwin Adapter owns scene geometry, route preparation,
controller interaction and environment measurements. Provider substitution
must leave the first three owners and public relation Tool contract unchanged.

## 2026-11-08 Relation Provider Boundary Correction

The earlier statement that RoboTwin lacked the `relation.establish` Runtime
injection path was incorrect. `build_persistent_runtime_bundle` already accepts
`relation_execution_provider` and `resolve_relation_context`, forwards both to
the existing pick-place Runtime, and the host validates that the pair is
provided together. The registered endpoint binds task/revision/node/intent and
fresh relation-target evidence before it calls `provider.admit(...)`.

Reusable implementations are present but do not by themselves implement one
stack relation Action:

- `PersistentRelationTargetProvider` returns current-scene support geometry;
  it is Query evidence, not an execution route.
- `PersistentPreparationProvider` consumes a manipulation intent, grasp
  candidates, capability snapshot and complete route request, then emits an
  assignment and prepared route. Those inputs are not present in the public
  `relation.establish` request, which carries only the selected relation-target
  candidate and trusted intent.
- `PersistentManipulationProvider` and `RoboTwinPersistentEngine.execute`
  implement a bounded acquire/place lifecycle. They do not expose a one-call
  stack-relation operation that consumes a relation candidate and settles a
  complete pick/transport/release/retreat route.
- `RoboTwinPersistentEngine` rejects route readiness, contact qualification
  and action preparation while `StackBlocksThreeTaskAdapter` declares
  `motion_execution_supported = False`.

The concrete missing mechanism is therefore the Adapter-side composition from
one Coordinator-bound relation candidate to a current-scene grasp/assignment,
qualified full route, runtime-monitored approval, bounded controller execution
and measured support settlement. This cannot be filled by forwarding the
existing provider injection arguments or by wrapping `play_once()`; the latter
owns benchmark behavior for all three placements and is not interruptible at
the PAOS relation Action boundary.

The dedicated runtime's `artifacts` tree was checked for controller
`qualification.json`, `plan.json`, `evidence.json` and `validation.json`; none
were present. No provider code or motion authorization was added in this
recheck. `motion_execution_supported` remains false, and no task, Action or
simulator motion was started. Next implementation must expose a
provider-private input/composition path for fresh grasp and route preparation,
then prove per-control-step stop and placement/support measurements with the
actual configured RoboTwin controller before enabling the stack Action.

## 2026-11-08 Stack Relation Provider Implementation

Added `StackRelationExecutionProvider` as the concrete RoboTwin Adapter
composition for one `relation.establish` invocation. It consumes one current
relation binding and an Adapter-private `prepare_route` result, checks task/entity,
candidate, destination, approval reference and scene identity, then starts the
existing persistent worker's `acquire` phase. Only a known acquire success with
confirmed holding and a new scene revision advances the same invocation to
`place`. Success requires finite non-negative placement errors, a scene revision
different from acquire, at least one artifact evidence reference, confirmed
release, completed retreat, clear target and empty possession. A narrow
transition lock serializes cancellation against the
acquire-to-place handoff, so cancellation either prevents place or reaches the
place driver. Worker polling failure, cancellation while acquiring, uncertain
place start, or incomplete placement evidence remains unknown and is not
settled as success.

The host can construct the Provider through its existing factory injection
using the same persistent client and deployment; no new Runtime endpoint,
Coordinator state, scheduler or AgentLoop route was added. Tests exercise the
factory with the host-owned worker client and substitute no-motion Provider
drivers for phase execution.

This implements the single-relation Provider composition, but does not close
the task execution gate. No stack-specific `prepare_route` factory is wired,
and the isolated artifact root has no controller qualification evidence. The
stack Adapter continues to report `motion_execution_supported = False`; no
task, Action, simulation startup or robot/simulator motion was initiated.
Acceptance evidence is contract/provider-only: 82 focused tests pass, but these
do not establish real RoboTwin route/contact/stop behavior. The next required
work is task-specific grasp/route preparation and a simulator-thread-affine
control-tick driver, followed by no-motion route validation and explicitly
authorized simulation qualification before enabling motion.
