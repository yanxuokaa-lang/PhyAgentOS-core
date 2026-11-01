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
