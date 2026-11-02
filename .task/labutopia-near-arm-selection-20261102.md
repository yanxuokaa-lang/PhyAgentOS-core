# Near-arm inner-corner target correction / 近机械臂内侧角目标纠正

## Diagnosis and ownership / 诊断与归属

The user clarified spatial intent: the lower-right bottle of the left region
and lower-left bottle of the right region, nearest to the robot. The previous
instruction explicitly requested R03/R04; both are in reagent zone A. Therefore
the previous Agent followed a mistaken task input, not a runtime label swap.

用户的最新空间选择优先于历史 R03/R04 指令。旧运行最终组合网格记录显示：
机械臂基座在 (-0.45, 0) m；A/R03 在 (-0.27, -0.36) m，B/R05 在
(-0.27, +0.36) m；A/R04 在 (-0.04, -0.36) m。前两者到基座的水平距离
约 0.402 m，R04 约 0.546 m。这里的中心取自最终 Model 世界包围盒，
不是 wrapper 平移，也不是抓取位姿。空间靠近不代表路线或接触一定可行。

The existing preview camera sees B on the left and A on the right. A fresh
no-motion capture must confirm the layout and label association before launch.
The previous uncertain-possession session has ended; use a new simulator,
not a retry against its displaced object or stale preparation.

Architecture review: Tier C-Safety execution review; correction belongs to the
task request. AgentLoop selects semantic Tools and opaque refs; Coordinator
owns task lifecycle/recovery; Providers own fresh identity/geometry/grasps;
Adapter owns route checks and execution. Replacing Providers requires no changes
to this caller. No new public schema, selector algorithm, gate or threshold.
No label edits, coordinate shifts or assumed graspability. Existing same-capture
and qualified-only recovery checks remain authoritative. Hephaestus-specific
workflow files are absent; use AGENTS.md, the PAOS developer manual and
MANIPULATION_DAG_DEVELOPER_GUIDE.md for actual repository ownership.

## Planned correction / 修正

Select left B/R05 then right A/R03, then GLASS_ROD in BEAKER, using the existing
native Agent host and previous process values. The task instruction carries
the verified labels; no generic runtime module receives fixed USD paths or
coordinates. Save the exact instruction, fresh observation, launch context,
final task receipt and any actual videos. A failed first subtask must not be
reported as execution of both bottles.

## Validation and results / 验证与结果

Fresh observation: `out/lab-near-arm-selection-20261102-observe-r1/`.
Captured at 2026-11-02T06:55:01.079959Z, revision suffix
`49cc517596d64d959d7ad15742f91573:0`. Final geometry and ROS-axis camera
calibration share this revision. Projection onto the actual 1600x1200 RGB image
places R05 at (432.35,653.46), R03 at (1063.63,807.74), and R04 at
(1124.47,685.95). `selected-bottles.png` marks all eight identities and the
selected two; `selection-audit.json` saves bounds-derived centers, pixels and
distances. R05/R03 are independently nearest within B/A at 0.402493/0.402492 m.
No controller motion was invoked. 51 host/semantic-task/binding tests pass.

Native run workspace: `out/lab-fullchain-truth-20261102-near-arm-r05-r03-r1/`.
Only target identity and order change; process values and safety policy stay as
in v16.7.1. Execution uses fresh evidence, not this diagnostic capture.

Reproduce from repository root (use a new workspace on every rerun):

```bash
OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
./.venv/bin/python -m isaacsim_lab.agent_host \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --workspace out/lab-fullchain-truth-20261102-near-arm-r05-r03-r1 \
  --execute \
  "$(cat .task/labutopia-near-arm-instruction.txt)"
```

Task `task_8983ebbef39b4da4`, revision `revision_3eb048c8f12047eb`, session
`cli:lab-68c0bd18324b`. Read-only inspection of the persisted graph confirms:
`pour_r05 -> entity://simulator-truth-R05`,
`pour_r03 -> entity://simulator-truth-R03`, and
`stir_glass_rod -> entity://simulator-truth-GLASS_ROD`.
Both pours retain tilt_rad=0.87/hold_s=0.6; stirring retains radius_m=0.009,
depth_m=0.04, turns=2, duration_s=4 and direction=ccw. No R04 Action is present.
This proves corrected binding and parameter propagation, not physical success.

R05's four qualification Queries succeed. Complete acquire preparation selects
candidate suffix 69 from current capture `b4b03a02e39e4e66af5410858ba65e82:0`.
The first two route variants fail (IK continuity, then payload/table collision);
the third qualifies in 8.731 s with 146 waypoints. Readiness artifact
`b9cf194f83614cd4881f7c3727d76c0f.json` records kinematic/collision/workspace pass
and target `/World/ReagentZones/B/R05/Model/mesh`. This is independently
consistent with the audited physical bottle. The composite Action invocation
is `invocation://manipulation-execute_subtask/6a6bc9f89814482a`.
Actual phase video starts at
`artifacts/labutopia/phase-video/44fc44626f624e69b5492f2aea87983e.mp4`.
### Terminal result / 终态

Native host exits 1. Task awaiting_replan; composite Action unknown and possession
uncertain, controller blocked with reconciliation_required:pour_r05. Four Query
records succeeded, manipulation.prepare available, object.acquire failed before
lift with grasp_not_confirmed: both fingers must contact the selected body.
Acquire invocation: `invocation://object-acquire/57bc381faac942b4`.

The foreground Agent reaches 40 iterations while motion is in flight. Its
iteration-limit response is not the physical stop or its cause; the host waits
for Runtime reconciliation and final feedback. No duplicate Action is submitted.

Feedback `phase-feedback/938b45cf75db4f09a8e983285259518f.json` isolates the event:
body displacement stays below 1.006 mm through transport, approach and insertion.
At close frame 3160 (52.685419 simulated seconds), displacement exceeds 8 mm
and reaches 26.249 mm; at frame 3161 it is 49.050 mm with zero finger impulses.
Final displacement is 393.292 mm. Both fingers briefly contact during closure
(max impulses 0.029889/0.028468 N s), but final contact is [0,0] and each finger
position is ~0.00007181 m: closure finishes without confirmed possession.

This is a closure-contact failure, not the previous R03 insertion-pushing event.
The evidence does not alone isolate contact geometry, force or friction as the
root mechanism. Do not increase tolerances, skip possession checks or retry from
this uncertain state. Next investigation belongs to Adapter dynamic closure
qualification, using the actual candidate, jaw sweep and per-substep contact.

No lift, pouring, placing, R03 motion or stirring is executed. The final TCP
position residual 119.956 mm includes the intentionally unexecuted 120 mm lift;
it is not a 120 mm tracking error. Source entity/path remain B/R05; the third
video panel is the profile's fixed R01 label camera, not target selection.

Native MP4: 3191 frames, 60 fps, 3840x960, 53.183333 s, 88,733,263 bytes;
full ffprobe frame decode succeeds. Feedback has 3192 samples, including one
trailing non-frame snapshot. Stage frame ranges are half-open:
open [0,37), transit_raise [37,166), transit_orient [166,168),
transit_cross [168,1281), staging_reorient [1281,1971), approach [1971,2839),
grasp insertion [2839,3153), close [3153,3191).

Review videos are exported under `videos/`, with exact boundaries, measured
drift, playback speed and validation in `stage-videos.json`. The source stays
unchanged. Transport/approach video is not labeled a successful grasp; the
closure review is explicitly one-quarter speed.

## Implementation review / 实现复核

- Major resolved: prior request selected two objects in the same region. Fresh
  geometry, calibrated image and persisted new Action bindings agree on the
  requested opposite inner corners. The repair is task input, not controller code.
- No public contract change; label selectors remain mechanism-independent.
  Existing tests cover ambiguity/missing labels, distinct reagents, argument
  preservation and refresh of the selected identity. No extra generic selector
  or hardcoded environment fallback is introduced.
- Residual runtime risk: shorter distance does not remove grasp/contact risks.
  Prior R03 insertion caused drift; this run keeps those checks and must stop
  on uncertain possession. Full workflow acceptance requires actual receipts.
- Review separates identity evidence (fresh image/geometry), contract evidence
  (51 tests) and native route/motion evidence (readiness/phase feedback/video).

Validation command:

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py \
  examples/forge-skills/pick-place-workflow/tests/test_semantic_task_creation.py \
  examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py
```
