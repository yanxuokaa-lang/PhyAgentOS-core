# LabUtopia R03/R04 small-vessel full-chain execution diagnosis

## Runtime identity

- Workspace: `out/lab-fullchain-truth-20261101-r03-r04-small-vessel-execute-r1/`
- Session: `cli:lab-d099bf7187df`
- Task: `task_b4d730ffb7f043b7`
- Scene revision: `labutopia-tabletop-rod-rack-v1:b50bb095e683479c8779e3410b50bdfb:0`
- Observation: `observation://labutopia-tabletop-rod-rack-v1:b50bb095e683479c8779e3410b50bdfb:0/tabletop_third_person`
- Host: `simulated_motion_enabled=true`; exit code `1`; task status `failed`.

## Scene evidence

The fresh simulator-truth state confirms the regenerated scene, rather than the
old large-flask scene, was observed:

- R03 world dimensions: `0.077091 x 0.077092 x 0.097497 m`; prim
  `/World/ReagentZones/A/R03/Model`.
- R04 world dimensions: `0.093248 x 0.092821 x 0.165041 m`; prim
  `/World/ReagentZones/A/R04/Model`.
- The observation contains a `1600 x 1200` depth frame, a `1,854,436 x 3`
  scene point cloud, final-composed observed geometry and object point clouds.
- Artifact kinds contain simulator-truth, depth, point clouds, state,
  observed-geometry and GraspNet predictions. No ReMake/DFNet/SAM2 worker,
  recovered-depth or transparent-mask artifact was created.

## Prompt-owned parameters

- `pour_r03`: `tilt_rad=0.87`, `hold_s=0.6`.
- `pour_r04`: `tilt_rad=0.87`, `hold_s=0.6`.
- `stir_glass_rod`: `radius_m=0.009`, `depth_m=0.04`, `turns=2`,
  `duration_s=4`, `direction=ccw`.

The PlanGraph retained these values in the semantic subtasks. No action code,
task definition, Provider or grasp coordinate was changed for this run.

## Preparation result

R03 process-feature Query/Preparation produced the selected `pour_lip` and
BEAKER `opening`. Task-affordance Query/Preparation returned 19 ordered,
same-capture qualified grasp references. `manipulation.execute_subtask` passed
only those references to Isaac preparation; no raw GraspNet candidate recovered
outside the qualified set.

All 19 references were rejected before the first controller command:

- `13` `gripper_aperture_exceeded`; requested widths range above the composed
  Franka `0.080000 m` limit, including the selected `0.100000 m` candidate.
- `4` `route_collision`; representative conflicts are `panda_link6` or a finger
  against `/World/table/surface/mesh`, and `panda_hand` against the target
  BEAKER on an alternative clearance route.
- `1` `self_collision`; Franka link1/link2 overlaps link6 on transit/approach.
- `1` `inverse_kinematics_failed`; alternative clearance routes then encounter
  self-collision.

The smaller R03 geometry increased the task-qualified set from the prior eight
candidates to nineteen, but vessel size was not the sole blocker. Six candidates
fit the aperture and still fail embodiment route feasibility.

## Safety and lifecycle result

- `controller_outcomes=[]`
- `world_change_started=false`
- `outcome_known=true`
- `possession_state=empty`
- R03 did not complete acquire or pour. R04, stirring and all return actions did
  not start.
- AgentLoop cancelled the task after the known R03 preparation failure, exactly
  as required by the user instruction.

## Architecture assessment

- AgentLoop correctly owns semantic order, prompt parameters, opaque selection,
  cancellation and settlement; it does not inspect USD paths, widths or collision
  geometry.
- Task-Affordance owns grasp/process compatibility and the same-capture qualified
  reference set.
- Isaac Adapter owns final-world geometry, aperture, IK, self/environment/payload
  collision, route clearance and execution authority.
- No bypass, hard-coded grasp, threshold relaxation, hash, new gate or shadow
  scheduler was added.

## Next blocker

Do not keep shrinking the flask or retuning task-affordance thresholds. The next
no-motion investigation belongs to Isaac route preparation: inspect the six
aperture-valid candidates against the measured initial joint/TCP state, table
collision geometry, BEAKER clearance and approach orientation. Any change must
remain Adapter/configuration-owned and preserve the existing failure gates.

## LabUtopia v0.2.9 all-small-vessel rerun

### Runtime identity

- Workspace: `out/lab-fullchain-truth-20261101-all-small-vessel-execute-r3/`
- Session: `cli:lab-3a7197f13915`
- Task: `task_135e08bbdf8e429b`
- Scene revision: `labutopia-tabletop-rod-rack-v1:0e65f1fb903d4ef88a533d530cec59c1:0`
- Observation: `observation://labutopia-tabletop-rod-rack-v1:0e65f1fb903d4ef88a533d530cec59c1:0/tabletop_third_person`
- Host: `simulated_motion_enabled=true`; exit code `1`; task status `failed`.

The preceding `r1` interactive attempt and `r2` background-launch attempt did
not create a task or start Isaac motion. The independent `r3` Host is the only
runtime attempt used as execution evidence for this section.

### Final-composed scene truth

The state artifact reports `source=final_composed_usd_world_geometry` and the
following world-space bounds:

- R03: `63.215 x 63.215 x 79.948 mm`; prim `/World/ReagentZones/A/R03/Model`.
- R04: `65.474 x 65.046 x 115.680 mm`; prim `/World/ReagentZones/A/R04/Model`.
- BEAKER: `64.924 x 60.266 x 90.400 mm`; prim
  `/World/OperationArea/TargetBeaker/Model`.
- GLASS_ROD: `6.000 x 6.001 x 250.000 mm`; prim
  `/World/OperationArea/GlassRod/Model`.

Three simulator-truth captures each contain a `1200 x 1600` float depth frame
and a `1,854,436 x 3` float scene point cloud. The same observation identity
provided object point clouds for R03 (`1214 x 3`), R04 (`1214 x 3`), BEAKER
(`1698 x 3`) and GLASS_ROD (`66 x 3`). Artifact kinds include simulator-truth,
depth, point clouds, state, observed geometry and GraspNet predictions. No
ReMake, DFNet, SAM2, recovered-depth, transparent-mask or recovery-worker
artifact exists.

### Prompt and evidence lineage

- `pour_r03`: `tilt_rad=0.87`, `hold_s=0.60`.
- `pour_r04`: `tilt_rad=0.87`, `hold_s=0.60`.
- `stir_glass_rod`: `radius_m=0.009`, `depth_m=0.04`, `turns=2.0`,
  `duration_s=4.0`, `direction=ccw`.
- Process-feature Query/Preparation selected R03 `pour_lip` and BEAKER
  `opening` from `process-feature-set://21193f0cdbc7448fafb03171beb5b52c`.
- Task-Affordance Query returned exactly three combinations backed by grasp
  candidates `15`, `16` and `23` in
  `grasp-affordance-set://3e1119f5aefa43cd97bf723b63be1043`.
- Task-Affordance Preparation returned the ordered opaque list `15, 16, 23`.
  `manipulation.prepare` rejected exactly the same three references; no raw
  GraspNet candidate re-entered Action preparation.

### Adapter preparation result

No candidate reached the first controller command:

- Candidate `15`: `self_collision` at 0.04/0.08 m transit clearance
  (`panda_link2` overlaps `panda_link6`/`panda_link5`); 0.12 m has no IK
  solution.
- Candidate `16`: 0.04/0.12 m have no IK solution; 0.08 m reports
  `route_collision` because a finger overlaps `/World/table/surface/mesh`.
- Candidate `23`: 0.04 m reports `self_collision` (`panda_link2` overlaps
  `panda_link6`); 0.08/0.12 m have no IK solution.

This is a known zero-motion preparation failure owned by the Isaac Adapter:

- `controller_outcomes=[]`
- `completed_tool_ids=[]`
- `world_change_started=false`
- `outcome_known=true`
- `possession_state=empty`
- R03 acquire/pour/place did not start; R04, GLASS_ROD stirring and all return
  actions did not start.

### Architecture and next blocker

The run preserves PAOS ownership: AgentLoop owns semantic order, prompt
parameters, opaque selection, cancellation and settlement; task-affordance owns
process/grasp qualification; the Isaac Adapter owns final geometry, frame,
aperture, IK, collision and route feasibility. No hard-coded grasp, USD path,
threshold relaxation, automatic retry, shadow scheduler, new contract or hash
gate was added.

The all-small-vessel scene removes gripper-aperture rejection from the final
qualified set, but it does not make the transit route admissible. The next fix
must remain in Isaac Adapter/configuration preparation: reproduce candidates
`15/16/23` in a no-motion route probe, record the initial joints/TCP and each
`transit_cross` waypoint, then determine whether the failure is caused by the
initial arm posture, table collision geometry, cross-table route shape or grasp
approach orientation. Do not shrink the vessels again and do not weaken IK or
collision gates.
