# LabUtopia R03 Authorized Execution Diagnosis

## Scope

- Workspace: `out/lab-fullchain-truth-20261101-staged-symmetry-execute-r1/`
- Agent session: `cli:lab-dc8cd9539e91`
- Task: `task_093815df65154b03`
- Action invocation: `invocation://manipulation-execute_subtask/118c1f7ccfea474e`
- Scene revision: `labutopia-tabletop-rod-rack-v1:03b288762548416e890d5da8b38e9584:0`
- Authorization: Isaac/LabUtopia simulation only, with `--execute`; no physical robot or hardware IO.

## Requested Semantic Parameters

- R03 -> BEAKER pour: `tilt_rad=0.87`, `hold_s=0.60`
- R04 -> BEAKER pour: `tilt_rad=0.87`, `hold_s=0.60`
- GLASS_ROD stir: `radius_m=0.009`, `depth_m=0.04`, `turns=2.0`, `duration_s=4.0`, `direction=ccw`

The persisted PlanGraph contains these values exactly. They originated in the user instruction and were not introduced by the Isaac Adapter, the launch profile, or a hard-coded grasp pose.

## Result

- R03 process-feature Query and preparation completed.
- R03 task-affordance Query and preparation completed.
- `manipulation.execute_subtask` accepted the same-capture qualified refs `15`, `23`, and `16` and ran Adapter preparation.
- All 72 route variants failed before the first controller command: 3 candidates x 3 clearances x 2 transport orientations x 4 geometry-supported axial angles.
- The action returned `failed` with `outcome_known=true`, `world_change_started=false`, unchanged scene revision, empty possession, and no controller outcome.
- AgentLoop stopped R04 and GLASS_ROD after the known R03 failure. It did not retry from the raw GraspNet candidate set.

## Route Failure Distribution

| Candidate | IK discontinuity | IK unavailable | Self-collision | Environment collision | Total |
|---|---:|---:|---:|---:|---:|
| `15` | 7 | 5 | 3 | 9 | 24 |
| `23` | 8 | 7 | 5 | 4 | 24 |
| `16` | 7 | 4 | 4 | 9 | 24 |
| **Total** | **22** | **16** | **12** | **22** | **72** |

The failures are localized to `staging_reorient` and `approach`:

- `staging_reorient`: full-pose IK has no solution, returns a discontinuous branch beyond the configured `0.5 rad` waypoint limit, or produces genuine robot self-collision such as `panda_link5`/`panda_hand` or `panda_link1`/`panda_link5` overlap.
- `approach`: the validated checked configuration overlaps the table surface, and candidate `16` also has approaches where `panda_link7` overlaps the adjacent R04 mesh.

This is not an AgentLoop parameter or candidate-lineage failure. The action used only the task-affordance-qualified opaque references from the same capture. The remaining blocker is Adapter-owned staging/approach feasibility and local scene clearance.

## PAOS Ownership Review

- AgentLoop/Coordinator correctly own semantic ordering, exact prompt parameters, opaque selection, failure settlement, and stopping downstream nodes.
- Grasp and process Providers correctly own candidate evidence; no USD path, joint state, or robot-specific collision representation crosses the public domain contract.
- Isaac Adapter correctly owns final-world transforms, route variants, full-pose IK, continuity, self/environment collision, payload checks, and controller start.
- Evidence lineage remains one chain from simulator-truth observation through task-affordance preparation to the failed Action receipt. No stale capture or raw-candidate recovery was observed.
- The smallest abstraction-leak check passed operationally: after task-affordance selected three refs, Action preparation traversed those three refs only.

## Video and Evidence

- The failed Action returned no `artifact_refs` or `evidence_refs`, so there is no action-execution MP4 and no motion may be claimed.
- Four 1600x1200 simulator RGB frames were preserved in the workspace.
- A five-second 1600x1200, 30 fps static preview was generated from the run's real RGB frame at `artifacts/labutopia/no-motion-video/r03-preparation-failed-observation.mp4`.
- The preview is visibly labelled `NO MOTION`, `Controller not started`, and `world_change_started=false`; it is diagnostic observation evidence, not Action evidence.

## Recommended Next Change

Keep all current safety and evidence gates. In the Isaac Adapter, add bounded, configuration-driven staging pose and final approach-direction alternatives, then qualify every alternative with the unchanged continuous IK, joint limits, workspace, self/environment collision, payload, and same-capture checks. Run no-motion preparation first and only repeat `--execute` after at least one complete R03 route passes.
