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
