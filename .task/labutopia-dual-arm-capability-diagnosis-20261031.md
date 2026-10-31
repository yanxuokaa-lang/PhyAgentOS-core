# LabUtopia dual-arm capability diagnosis (2026-10-31)

## Finding

R01 and R02 are both created in the simulator scene manifest. They resolve to
`/World/ReagentZones/A/R01/Model` and `/World/ReagentZones/A/R02/Model`.
That scene fact does not establish that two manipulators exist or that both
objects can be grasped simultaneously.

The current Isaac Adapter capability snapshot is measured as `topology=single_arm`
with one arm id, `franka`, one Franka articulation, and one parallel-finger
gripper. The prior R12 run selected R01 only, reached no-motion preparation,
and stopped on `no_admissible_grasp / route_collision`; R02 never entered a
grasp path. There was no left/right dual-arm grasp.

## PAOS implementation boundary

Capability discovery remains Adapter-owned and is projected through the existing
`CapabilitySnapshot`; PlanProposal validates arm IDs against that snapshot.
AgentLoop may express a bimanual semantic requirement, but it must not invent
`left`/`right` aliases or reinterpret one `franka` resource as two resources.

The Isaac preparation boundary now rejects any request whose coordination mode
is not `single_arm` or whose allowed arms are not exactly `("franka",)` with a
known, zero-motion `unsupported_capability_topology` result. No assignment or
actuator command is emitted.

## Required work before real dual-arm execution

1. Add a second configured Articulation and gripper to the LabUtopia scene.
2. Measure and publish two distinct arm IDs, frames, limits, workspaces and
   capability references in one snapshot.
3. Extend planning/resource admission for two independent or coordinated
   resources, with explicit collision and workspace evidence.
4. Add no-motion dual-arm preparation and feedback tests before enabling Action.

Until those facts exist, the correct result is an explicit capability block or
two sequential single-arm subtasks, not a simulated left/right grasp claim.
