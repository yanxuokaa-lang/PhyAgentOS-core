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
