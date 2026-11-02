# Qualified grasps to Action: diagnosis and simulation rerun

## Diagnosis / 诊断

Previous workspace: `out/lab-fullchain-truth-20261102-region-no-motion-r3/`.
Task: `task_a87e6bb320964db7`; final state `awaiting_replan`.
The four R03 process/affordance Query nodes completed and seven independent
combinations qualified. These receipts cover task/process compatibility and
short-approach feasibility, not the complete acquire/pour/return route.

上轮 acceptance.json 的原始指令明确写明“保持 no-motion only，禁止 Action 或控制器调用”；
`simulated_motion_enabled=false`。下一节点 `pour_r03` 是 Action，最终调度失败为
`node_selection_no_progress`，没有创建任何 Action 记录。已有合格候选不改变执行授权。
早期 `agent_response` 先于后台长期规划结果，不作为最终阶段证据。

The launcher and instruction deliberately disabled execution. The ready Action
was never selected/executed, so this is not an observed full-route collision or
a new GraspNet failure. The old shared guidance also told both modes to execute
ready nodes; deployment guidance now explicitly distinguishes their handoffs.

## Architecture / 架构审查

- Tier C-Safety: authorized simulator execution and evidence interpretation.
- Generic layer: AgentLoop selects Tool/opaque references; Coordinator owns
  lifecycle, recovery, cancellation and settlement. No changes to either.
- Adapter/deployment: explicit execution mode, simulator observations, route
  preparation, controllers and existing per-phase recording.
- Replacement: caller continues using the same Tool and predecessor receipts;
  no USD paths, joint parameters or camera handles enter generic interfaces.
- Evidence: a fresh workspace/capture; only current qualified same-set grasps.
  No reuse of the prior seven candidates as fresh executable evidence.
- Smallest leak test: default CLI remains read-only; explicit --execute reaches
  composition unchanged; mode guidance preserves qualified-only references and
  complete-route checks. Existing executor/adapter tests exercise actual checks.
- No new hash, schema, gate, second scheduler or simulated success receipt.

## Run plan / 执行计划

1. Test entry guidance/CLI and existing qualified-only preparation/phase video.
2. Launch native Agent with --execute and a new instruction authorizing only
   Isaac simulation: R03 then R04 to BEAKER, tilt_rad=0.87 and hold_s=0.60;
   GLASS_ROD stirring radius_m=0.009, depth_m=0.04, turns=2.0,
   duration_s=4.0, direction=ccw. Values remain user instruction parameters.
3. Keep full-route workspace, IK, continuity, collision, payload and possession
   checks. Record failures; do not bypass preparation to produce a video.
4. Existing phase recorder captures actual rendered controller steps, including
   failed attempts, without extra physics ticks. Qualification-only stages have
   no motion video; do not fabricate one from still frames or planned routes.
5. Inspect final persisted node outcomes and decode actual MP4s; retain run
   receipts/video paths and distinguish tested, prepared, executed, completed.

## Results / 结果

Fresh run: `out/lab-fullchain-truth-20261102-qualified-execute-r1/`.
Task `task_1d0ea7cd9e184b04`, session `cli:lab-c3b0f0020bea`, revision
`revision_cfd6235f73dc44d6`. Simulator execution is explicitly enabled.
At 13:46:47 CST the R03 task-affordance Query completed: 108 approach receipts,
41 aperture rejections, 60 unavailable approaches and seven available independent
combinations. This reproduces the previous qualification result with fresh evidence.
完整路线与实际动作尚在本轮后续验证中，不能由上述七个候选推定成功。

Validation so far: 418 adapter/executor tests pass (including 153 targeted tests),
Ruff and diff whitespace checks pass. Results do not constitute motion proof.

### r1 terminal result / r1 终态

At 13:47:43 the Agent selected and invoked the R03 composite Action using the
seven qualified predecessor references; the previous handoff blockage is resolved.
Its first `manipulation.prepare` then timed out after 900 seconds with
`IsaacWorkerSessionError: Isaac worker request timed out`. Checks remained
unknown; completed_tool_ids=[], world_change_started=false, possession=empty.
Task awaiting_replan, host exit 1, no movement or phase video. The outer Agent
turn also exceeded its 1200-second budget; this is not a measured collision.

### r2 repair / r2 修复

Acquire enumerated all 3 clearances × 2 transport orientations × 4 corridors ×
4 symmetries before selecting minimum joint travel, even after a route passed.
The old run did not save per-variant progress, so it cannot prove whether a route
had passed before timeout. Add explicit Adapter-private selection policy:
minimum_joint_travel remains the default; the mixture deployment selects
first_feasible, which returns only after every check in a complete route passes.
No deadline is increased and no collision/IK or possession check is removed.

Persist private `acquire-search/` evidence at search, route and waypoint-stage
boundaries, with elapsed time, failure code, captured candidate/scene identity,
and no-motion markers. These diagnostics are not a parallel task state machine
or motion authorization. An unfinished trace is not a passing route.

424 Adapter/executor regressions pass, including different selection outcomes
for default min-travel and first-feasible policies, invalid policy rejection,
failed-candidate skipping and existing full-route/collision/video checks.
Ruff and git diff --check pass.

Rerun: `out/lab-fullchain-truth-20261102-qualified-execute-r2/`, same r1
instruction and --execute, fresh capture. Final result is recorded below.

### r2 observed progress / r2 实测进展

Task `task_bb8c12ae87744d91`, session `cli:lab-ac37effc8a52`.
The first complete acquire route qualifies in 8.182 seconds with 144 commanded
waypoints; readiness artifact `e26f274f46e646ea97e018b5d777d8df.json`.
The fresh Agent selected candidate suffix 367, whereas r1 selected suffix 420.
Thus the two native timings are not a controlled same-candidate speed comparison.
The first-feasible early exit and unchanged checks are separately covered by tests.

Actual simulator execution starts and writes
`artifacts/labutopia/phase-video/8eae14287ad647d393068f3039352fb0.mp4`.
This intermediate observation did not claim decodability or atomic grasp
completion. Final feedback and video validation are recorded below.

### r2 terminal result and videos / r2 终态与录像

Final task is awaiting_replan; composite Action outcome_unknown and controller
outcome blocked with reconciliation_required:pour_r03. Four Query records
succeeded; manipulation.prepare is available. object.acquire starts real
simulator motion and stops before lift with grasp_transform_mismatch.
R04, pouring, returning and stirring were not executed. No automatic retry is
permitted from the uncertain possession state.

原始视频已正常封装并完整解码：3153 帧，60 fps，3840×960，52.55 秒，90,699,502 bytes。
H.264 审阅副本保留真实运动和时间顺序：
- `videos/r03-motion-through-approach.mp4`: frames [0,2810), about 46.83 s;
  open/transport/reorientation/approach segments, not a successful grasp.
- `videos/r03-acquire-stopped-before-lift.mp4`: complete 52.55 s source attempt,
  including insertion, close and the pre-lift stop.
- `stage-videos.json`: exact source frame ranges, phase outcomes and measurements.
- `videos/pre-lift-stop.png`: reviewed final-insertion image.

### Current physical blocker / 当前物理阻塞

The object stays stationary through approach. During grasp insertion, fingers
are still fully open (approximately 0.04 m each), but one finger contacts the
selected body. At frame 3023 (simulation timestamp 50.4021 s), displacement
exceeds 8 mm and contact impulse is [0.003588,0] N·s. The body moves 26.785 mm
by insertion end; closure increases displacement to 33.487 mm. Both fingers
then have contact impulses [0.069665,0.069906] N·s, but the measured attachment
differs from the prepared relation by 34.220 mm and 0.197260 rad, exceeding the
existing 8 mm / 0.08 rad checks. Therefore the pre-lift rejection is supported
by dynamic evidence, not merely a guessed collision or absent contact.

The final TCP-position residual 119.94 mm is measured against the unexecuted
120 mm lift goal, so it must not be reported as that much controller tracking
error. The third video panel is the fixed R01 label-inspection camera; readiness
and Action actually bind `/World/ReagentZones/A/R03/Model/mesh`. It is not
evidence that the Agent selected R01.

Next work belongs to Adapter contact/approach qualification: discriminate the
intended fingertip contact from single-sided pushing while the gripper is open.
If contact-driven centering is allowed, qualify stability and reprepare the
remaining motion from the measured grip relation before lifting. Do not enlarge
the mismatch thresholds, relabel uncertain possession as held, or continue
pouring with the old relation. This is a new contact-execution blocker; the
selection/handoff and successful complete-route preparation are demonstrated.

Final validation: 425 Adapter/executor regressions pass; Ruff and whitespace
checks pass. Native evidence demonstrates movement and a safety stop, not a
successful grasp/pour/stir workflow.
