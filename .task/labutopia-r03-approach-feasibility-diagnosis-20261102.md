# R03 short-approach qualification diagnosis / 短接近资格诊断

## Scope and evidence / 范围与证据

Continue v16.5.0 using the existing LabUtopia scene, explicitly configured
`simulator_truth` perception and model-native GraspNet proposals. This change
qualifies candidates before Agent selection; it does not claim successful
acquisition, pouring, stirring, liquid transfer or real-hardware readiness.

延续已有场景和仿真真值实验。用户提示词提供工艺参数；候选资格检查不授予动作权限。

- Historical full-route run: `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/`.
  Three candidates produced 288 rejected routes: 140 IK discontinuities,
  49 unavailable IK solutions, 21 self-collisions and 78 environment collisions.
  Early stage failures do not establish that the later final approach is viable.
- Probe r2: `out/lab-fullchain-truth-20261101-approach-feasibility-no-motion-r2/`.
  No task was created; `scene.observe unavailable` is an observation-path failure,
  not evidence about candidate geometry or manipulation feasibility.
- Probe r3: `out/lab-fullchain-truth-20261101-approach-feasibility-no-motion-r3/`.
  Task `task_60ecd419ecb64b03`, session `cli:lab-adcd9b63d389`,
  scene `labutopia-tabletop-rod-rack-v1:461b3c2c107a47a9b08832e6b66e02bd:0`.
  Capture calibration `artifact://labutopia/calibration/1a936c6bf65e46f3a3d70ef0b32590b5.json`;
  prediction artifact `artifact://labutopia/grasp-predictions/e0c7826fbf0244bfbfdc9327457e3138.json`.
  Same-capture task-qualified refs 15/16/23 each fail eight short approaches
  (four axial orientations x two distinct approach distances), all at workspace
  checking before IK. No controller action or downstream R04/stir execution.

## Measured geometry / 实测几何

Transform native candidates through the captured camera transform and calibrated
`provider_from_tcp`; do not use the wrapper translation or replace coordinates
with scene configuration XY. Lengths are metres in world coordinates.

| Candidate | World grasp position | Pre-grasp z at 0.12 m | Pre-grasp z at 0.18 m |
| --- | --- | --- | --- |
| 15 | [-0.270001, -0.340537, 0.750917] | 0.674803 | 0.636746 |
| 16 | [-0.262553, -0.342018, 0.750917] | 0.674803 | 0.636746 |
| 23 | [-0.266204, -0.340914, 0.750917] | 0.674803 | 0.636746 |

The three world approach vectors are approximately
`[0.403409, -0.659505, 0.634282]`. Both the probe and full preparation compute
`pregrasp = grasp - normalize(approach) * distance`.
Existing workspace minimum z is `0.700 m`; both backoffs violate it. Rotation
about the bottle's vertical axis cannot fix the vertical component.

因此该拒绝是真实的当前接近段不合格。抓取点本身在 workspace 内；该诊断不证明瓶子太大、
所有抓法不可行或变换错误。旧完整路线更早停在 staging/IK，并未证明后续接近段可行。

## Ownership and implementation / 所有权与实现

- AgentLoop/Coordinator: task order, caller parameters, opaque selections,
  lifecycle, cancellation, recovery and settlement through existing Tools.
- Task-Affordance Provider: same-capture geometric qualification followed by an
  injected read-only approach feasibility mechanism. The existing public
  candidate/preparation contract remains provider-neutral.
- Isaac Adapter: observation correspondence, world transforms, robot state,
  axial equivalents, pre-grasp IK, short-route continuity, workspace and collision
  checks in the existing WorkerSession. Full Action preparation still checks
  the entire route from measured joints; a probe receipt is not a reusable
  execution route or permission to start the controller.
- Evidence: capture identity + grasp reference + variant diagnostics remain
  Adapter-private. Worker revision rejection keeps its identity and reason;
  Provider failures/missing receipts cannot become available candidates.
- No new hash, schema or release gate. Concrete corrections address lost capture
  identity, conflated provider/geometry failures, and insufficient workspace
  diagnostics; ordinary stored fields and tests are sufficient.

## Follow-up decision / 后续决策

Finish the same-capture query/preparation implementation and validate no motion.
If no candidate passes, preserve that result. Next inspect point-cloud coverage
and GraspNet approach-direction diversity, then consider configuration-driven
shorter approach distances only with gripper/table clearance and full-route
qualification. Do not lower the workspace floor, flip candidate axes, inject
task-specific grasps or silently substitute a raw rejected grasp.

The required outcome here is correct filtering and traceable failure evidence.
The full pour/pour/stir capability remains unproven until complete preparation
and subsequent authorized simulator execution succeed.

## Validation on 2026-11-02 / 本轮验证

- Full Isaac Adapter and subtask-executor regression: `370 passed`.
- The real short-route qualifier is tested with replacement FK/IK mechanisms;
  recorded R03 pre-grasp coordinates match full preparation construction.
- `r1` workspace `out/lab-fullchain-truth-20261102-approach-feasibility-no-motion-r1/`
  contains observation/state/understanding artifacts but has no `acceptance.json`
  after the interactive interruption. Do not infer task completion or final
  feasibility from this incomplete run.
- `r2` uses the same formal entry point and unchanged no-motion instruction:

```bash
lab_probe_instruction=$(jq -r .instruction out/lab-fullchain-truth-20261101-approach-feasibility-no-motion-r3/acceptance.json)
OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src \
./.venv/bin/python -m isaacsim_lab.agent_host \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --workspace out/lab-fullchain-truth-20261102-approach-feasibility-no-motion-r2 \
  --execution-timeout-s 1800 "$lab_probe_instruction"
```

The quoted instruction requests R03 and R04 pour parameters
`tilt_rad=0.87, hold_s=0.60`, followed by GLASS_ROD stirring with
`radius_m=0.009, depth_m=0.04, turns=2.0, duration_s=4.0, direction=ccw`.
The command omits `--execute` and the instruction explicitly disables motion.
These are scenario inputs, not hard-coded motion or grasp implementations.

### r2 final receipt / r2 终态回执

- Session `cli:lab-5fe426934fb3`; task `task_51ae038c97d246fd`;
  revision `revision_81419cec0f164d95`; terminal status `cancelled`.
- Capture scene `labutopia-tabletop-rod-rack-v1:7d8b3acba40f4756af091de8635a4c6c:0`;
  calibration `artifact://labutopia/calibration/acc21842b09c4546967a330ba89d87bd.json`.
- R03 process-feature Query and preparation returned available. Task-affordance
  Query evaluated refs `06d82ec1606442dbbe6539a003e9672e-15/-16/-23`, rejected
  all 24 approach variants at workspace checking and returned unavailable.
  This reproduces the r3 numeric coordinates above with fresh simulator evidence.
- Three private `grasp-approach-feasibility` receipts:
  `400999221db64131a99918de7e1a3f5b.json`,
  `d0670d95f5064206be57d6c6cd46caa8.json`,
  `d547b1fea3904b209f31490b7e15e67d.json`.
  Every receipt contains eight evaluated variants, full same-capture identity,
  `motion_authorized=false` and `world_change_started=false`.
- Host exited with code 1 for the cancelled task and wrote `acceptance.json`:
  `simulated_motion_enabled=false`, `controller_outcomes=[]`. No Action started;
  R04 and GLASS_ROD did not execute. The code path was exercised successfully;
  the requested manipulation task did not succeed.
- A valid final grasp direction and safe complete route are still needed.
  This delivery adds correct early exclusion and diagnosis, not a feasibility
  claim for the rejected candidates.
