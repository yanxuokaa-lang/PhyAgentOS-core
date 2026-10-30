# LabUtopia PAOS acceptance

The Agent-facing path uses semantic requests and current observation bindings:
`manipulation.execute_subtask` runs prepare, acquire, held preparation, pour/stir,
held return preparation and place inside one outer Action. The Runtime owns
invocations and possession; the adapter owns private simulator routes.
`project_pour_task()` requires an observation-derived binding and does not infer
identity from profile Prim paths. The complete-cycle endpoints described below
remain legacy controller experiments, separate from the Agent subtask path.

## Current scene and perception refactor (2026-10-23, v15.9.0)

The acceptance scene is the existing LabUtopia station opened by
`python scripts/preview_tabletop_station.py --view third-person`: eight labeled
R01–R08 flasks, a beaker, a six-tube rack and a glass rod. The rod now stands in
an empty rack hole. PAOS owns the reproducible change in
`examples/forge-adapters/isaacsim_lab/patches/labutopia-tabletop-rod-storage.patch`.
LabUtopia remains a locally modified runtime dependency; this task creates no
commits or pushes in that external repository. The two mistakenly created local
commits were removed and its branch restored to the previous `61e1fba`.

The PAOS mixture profile directly loads `config/tabletop_station.yaml` and the
station USD. The Adapter registers the authored third-person/wrist cameras and
matches the original preview script's dome lighting. The former two-bottle
fixture and setup code are removed from this integration. The original preview
command continues to show the updated rod placement.

`scene.understand` composes RGB label interpretation, SAM2 and depth localization.
Only observed point clouds feed the existing GraspNet worker. Binding preserves
multiple predictions; preparation chooses a model candidate and execution
consumes that exact pose after the declared camera/TCP conversion. No USD mesh
or private cache generates or replaces a grasp pose. USD/PhysX correspondence
is Adapter-private and used for execution identity/feedback. Runtime and
Coordinator retain possession, cancellation and settlement ownership.

Static station build/inspection and RTX views pass: rod support gap 0.2 mm,
minimum clearance 8.039 mm at both guide plates, and no overlap with the six
tubes. These checks establish placement, not dynamic stability or graspability.
The no-motion substitution/contract suite has 215 passing tests; the complete
Isaac adapter/workflow suite has 787 passes and two pre-existing release-bundle
failures (node-version assertion and archive-lock mismatch).

The original-scene probe r1 captured RGB-D but label interpretation produced no
reliable targets because the preview illumination had not been registered.
This failure is retained under `out/releases/v15.9.0/tabletop-perception-20261023-r1/`.
Lighting was corrected before probe r2. That capture is clear, but the VLM
reports unreadable labels and confuses several tubes with mixing vessels;
understanding subsequently fails before grasp prediction. The raw capture and
interpretation are retained for diagnosis. Earlier real GraspNet results on the
removed two-bottle diagnostic scene are not acceptance evidence for this station.

**Agent-directed grasp/pour/stir/return on this station is not yet accepted.**
The physical GraspNet-to-TCP contact convention, partially observed glass
geometry, held-object refresh and rack withdrawal/return still need measured
validation. Do not reuse authored `lab:grasp_contact_target_world_m`, old IK
reports or benchmark fixed-pose primitives as a fallback.

### Simulator-truth binding repair (2026-10-29)

The explicit `simulator_truth` mode now captures final composed USD world bounds
inside a same-observation `state` artifact. `scene.understand` projects those
world bounds into the calibrated camera frame for spatial envelopes and selects
actual same-capture point-cloud samples inside the world bounds. The envelope
provenance names the state artifact; point-cloud provenance remains depth and
point cloud. Missing bounds produce an entity-scoped ambiguity and no envelope.
This is an explicitly labeled simulator-ground-truth experiment, not sensor-
reconstructed geometry and not a generic PAOS contract change.

No-motion runtime probe on 2026-10-29: `out/labutopia-truth-geometry-probe-20261029/`
returned `scene.observe=available`, `scene.understand=available` for all ten
manifest labels with ten spatial envelopes, and GraspNet returned candidates.
The measured final USD bounds differ materially from stale BEAKER/GLASS_ROD
manifest coordinates. This establishes Query-level geometry/binding inputs only;
it does not qualify grasp contact, bottle mouth, beaker interior, rod working
end, preparation, or motion. The Provider therefore leaves `process_features`
unset in simulator-truth records: an AABB is sufficient for binding and grasp
candidate selection, but cannot prove a bottle mouth, beaker rim/interior, or
rod working end. `resolve()` and held refresh consequently fail closed before
execution until those landmarks are derived from final composed geometry or
validated by an independent observation. The Agent-directed mixture remains
unaccepted.

The follow-up implementation records final composed mesh vertices and boundary
edges in the same private state artifact and derives private process-affordance
candidates. Each closed circular boundary remains a distinct rim candidate;
the Provider does not infer a vessel interior from an AABB. A rod yields two
endpoint-role candidates, not a guessed working end. The current PAOS binding does not yet
carry a planner-selected process-feature reference, so these candidates do not
qualify preparation: `resolve()` and held refresh remain fail-closed. The
ordinary grasp path remains point-cloud/GraspNet based. This is Provider-level
candidate generation only, not LabUtopia mesh acceptance or motion evidence;
the no-motion Isaac probe below confirms capture traversal but leaves rim,
interior, rod-end qualification, and planning-to-preparation selection
outstanding before process actions.

### Process-feature geometry replay (2026-10-29)

The following no-motion observation used the same Isaac Adapter and LabUtopia
profile but did not create a PAOS task or invoke an Action:
`out/lab-process-geometry-no-motion-20261029-r2/`. The private final-USD state
contains R01 (1214 mesh vertices, 244 boundary edges split into 4
vertex-topology components), BEAKER (1698 vertices, 6 degenerate boundary
edges), and GLASS_ROD (66 vertices, no boundary edges). Component-preserving
capture plus a conservative highest-ring fit produces one R01 rim candidate
and one BEAKER rim candidate. The measured candidate centers are approximately
`[-0.27001, -0.56000, 0.80947] m` and `[-0.07854, 0.00000, 0.80147] m`,
respectively. These are geometry estimates from the final USD mesh, not
configured coordinates.

This does not yet qualify either pour or stir. R01's rim is not a separately
identified pouring lip/direction; BEAKER's rim does not establish its interior
volume/safe insertion region; GLASS_ROD's symmetric ends remain ambiguous.
The subsequent `manipulation.process_features` Query, AgentLoop selection,
Preparation, and Action path have not been exercised against this new capture.
No robot/object motion occurred, and no pouring/stirring claim is made.

### Final composed mesh traversal probe (2026-10-29)

The Adapter now traverses USD instance proxies when capturing final composed
mesh data. A fresh `agent_host` run without `--execute` captured and understood
the same `tabletop_third_person` observation. The state artifact contained 1214
R01 mesh vertices/244 boundary edges, 1698 BEAKER vertices/6 boundary edges,
and 66 GLASS_ROD vertices/0 boundary edges. The Provider emitted two rod-end
candidates, while R01 and BEAKER opening candidates remained unavailable because
their captured boundary topology did not establish a closed near-circular rim.
The run created no tasks, had no controller outcomes, and admitted no Action or
Session. This validates the Adapter traversal repair only; it does not qualify
pour/stir geometry or authorize motion. Artifacts are preserved in
`out/lab-geometry-no-motion-20261029-r1/`.

Reproduce the current no-motion probe from the PAOS repository:

```bash
OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
.venv/bin/python -m isaacsim_lab.perception_probe \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --workspace out/releases/v15.9.0/tabletop-perception-NEW
```

Use a new output directory for every run. Model/interpreter/checkpoint paths and
sampling settings are in `labutopia-mixture-perception.json`; the run retains
that configuration, camera artifacts, segmentation, point clouds and predictions.
The model service and GPU inference may vary between reruns; no deterministic
end-to-end claim is made.

## Historical diagnostic integration (2026-10-23, v15.8.0)

The following results describe the earlier diagnostic fixture and superseded
mesh-based grasp integration. They are retained to explain failures and do not
qualify the current station or GraspNet implementation.


The complete **no-motion Runtime integration** now passes for reagent A, reagent B
and the stirring rod, including two fresh held preparations per subtask. The
acceptance test uses the production Runtime, Tool endpoints, possession object,
SQLite assignment store and LabUtopia provider/client. It substitutes only the
simulator mechanism and the supplied observation bindings. This does not prove
LLM selection or simulator motion.

The test verifies nine internal Actions in the order
`acquire → pour → place → acquire → pour → place → acquire → stir → place`,
three outer subtask results with six Tool receipts each, refreshed observation
lineage, current held-route references, and empty possession at each successful
subtask boundary. Failed or unknown processes stop without replaying a process
or releasing the held object. Private routes stay in assignment storage and are
not returned in Agent-facing subtask receipts.

Actual Isaac Sim camera rendering also passed. Two cameras each produced RGB,
depth, a 65,536-point cloud and a calibration artifact in the same Worker scene.
Calibration and point clouds now share the optical/ROS camera axes. Projecting
points onto their pixel centers gives depth-error p95 values of
`2.384185791015625e-07 m` and `0 m`. Artifacts on the acceptance host:

- `out/releases/v15.8.0/observation.json`
- `out/releases/v15.8.0/pointcloud-check.json`
- `out/releases/v15.8.0/observations/`
- `out/releases/v15.8.0/default-readiness.json`

The session now implements actual FK/IK and collision-qualified phase routes,
bounded joint control, contact/lift feedback, held processes and return. The
mixture profile places physical assets on the table once at session startup and
adds visible labels. `visual-runtime-r3/result.json` records real RGB-D selection
of REAGENT A, REAGENT B, BEAKER and STIR ROD. Geometry after association is the
simulator's rigid-body mesh; it is not reconstructed geometry.

**The complete Agent-directed mixture is not yet accepted.** Real Agent r7
created the three-node task and acquired A with a measured 0.120036 m lift, then
stopped on visual refresh. The provider now retains per-object uncertainty
without rejecting other independently resolved objects. Agent r8 stopped on
relative grip rotation before pouring.

Mechanism r30 completed A acquisition, pouring and return with the original
fingers, a 35 N gripper drive and 960 Hz physics: maximum tilt 1.327588 rad,
continuous qualified hold 1.833333 s and return error 4.25 mm. The taller B
bottle then failed. Fresh r31/r32 runs confirmed angular slip with the corrected,
coordinate-invariant grasp-anchor metric. Those failures remain unaccepted.

The supported mixture fixture now uses two independent copies of the same
97.5 mm bottle, bearing visible A/B labels. The original 164.5 mm bottle stays in
the source scene's storage area. This fixture is initialized once; execution
never teleports or attaches a bottle. Selection still requires RGB-D evidence.
The 6 mm rod rests on physical supports with 3 mm retaining rails. Its original
12 mm rails blocked vertical withdrawal during qualification in r33.

The deployed mixture profile uses its authored `/World/PhysicsScene`, 960 Hz
physics and 60 Hz control/rendering. It settles once for 2 s before observing.
Arm drive gains are explicit scene settings. Each control frame checks measured
grip and actual robot/payload collision as well as the next commanded pose.
Grip translation is measured at the grasp anchor with an 8 mm limit. Bottles
retain the full 0.08 rad rotation limit. The configured cylindrical rod permits
axial roll and applies 0.08 rad to axis tilt; full rotation remains diagnostic.
Support departure/arrival uses a vertical -2 to 8 mm band, referenced to the
measured grasp pose for lift and the original return pose for lowering. Current
rod features keep their endpoints in object coordinates across vertical poses.
For the cylindrical rod, insertion uses measured tip/axis compensation with
five-constraint IK that preserves its declared free axial rotation, and the
circle is requalified from its current grasp. The controller streams a clamped
cubic path under the configured velocity and acceleration limits, with a 0.25
turn entry reserve for the existing minimum-turn criterion. Completion still
requires measured continuous direction, radius, depth and duration. Exit uses
the configured settling interval and checks the actual tool tip and axis.
Mechanism r39 retries after a stopped transport and completes 2.240429 continuous
qualified stir turns over 20.616668 s; this does not prove a fresh horizontal-start cycle,
with 0.578 mm exit tip error and 0.001050 rad axis error. Feedback is in
`mixture-observations/phase-feedback/60d1fd25078b4dca9fbe93c9a3c3e037.json`
under `out/releases/v15.8.0/`. Rod return then succeeds with 2.748 mm position
error and final empty/on-support possession. The same scene completes standard
B acquire/pour/return: maximum tilt 1.344697 rad, continuous qualified hold
1.833333 s and return error 3.780 mm. Its pour/return feedback files are
`19d821ec00fd46e69594f063032f9c5e.json` and
`7ac4270984544e8a9580c533d1e9f3b5.json` in the same feedback directory.
Agent r9 stopped before task creation because the initially paused camera had
no rendered data. Capture now temporarily activates the rendering timeline,
samples every render and restores its prior state, without stepping physics.
The diagnostic recovers RGB-D with unchanged simulation time. Agent r10
successfully acquires A and captures post-lift RGB-D, then stops because refresh
incorrectly required the old calibration artifact URI. Refresh now accepts a
new capture's calibration while retaining consistent calibration throughout
its Query chain, source/vessel/frame identity and fresh candidate evidence.
Agent r11 passes that refresh and stops at a measured payload collision during
pouring after 0.866667 qualified seconds. Pour segments now compensate full
object pose from the measured grip without changing collision or grip limits.
The host also retains real Query receipts for reconciling the first pending
Action, before terminal scene evidence exists. Its configurable reconciliation
budget covers all three physical phases of each composite subtask.
Agent r12 completes A acquisition, pouring and return: 1.816667 s continuous
qualified hold, 1.219 mm exit lip error, 0.611 mm return error and final empty
possession. Its next B preparation rejects the original scene-0 binding before
motion. The Coordinator now supplies the persisted selection's current scene;
the Runtime refreshes that same entity/vessel before initial preparation and
updates only internal perception fields of the authorized intent. The test now
binds the complete plan once and verifies eight refreshes across nine Actions.
Agent r13 completes both reagent cycles and acquires the rod. Stirring stops
at 0.745589 continuous qualified turns on actual grip-axis drift of 0.080220 rad
against the existing 0.08 rad limit (anchor translation 0.471 mm). Its task
`task_9633be16d84b46be` remains `awaiting_replan`; stirring settles as
`outcome_unknown` and rod return is not executed. The complete Agent task
remains unaccepted pending the fresh real Agent r14 run.

Fresh mechanism r41 completes horizontal acquisition, first-attempt stirring
and return: 2.240281 qualified turns, 0.799 mm exit tip error and 0.278 mm
return error, ending empty/on-support with release and retreat confirmed.
Continuous transport reduces grip-axis drift; contact evidence spans physics
substeps within each current control interval while requiring fresh selected-body
contact pairs at the end and positive per-finger impulse within that interval.
Missing pairs, unloaded intervals, stale/wrong-body readings or sampling errors
still stop execution. The complete Agent task is being checked separately.
No liquid transfer, volume,
chemical compatibility or mixing quality is measured.

### Run the actual Agent

The host uses the existing PAOS model configuration and an independent Isaac
worker interpreter configured by `worker_python_path`. The acceptance host needs
LabUtopia assets, Isaac Sim, a working RGB-capable model and the configured camera.
Paths in the supplied mixture profile describe this host and must be adjusted
when installing elsewhere.

```bash
OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src \
.venv/bin/python -m isaacsim_lab.agent_host \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --workspace out/labutopia-mixture-agent --execute \
  --execution-timeout-s 1800 \
  '请按可见标签选择 REAGENT A 和 REAGENT B，依次倒入 BEAKER，再用 STIR ROD 搅拌，并将试剂瓶和玻璃棒归位。'
```

Omit `--execute` for a host that refuses simulated motion. The Agent writes
`acceptance.json`, session Tool records and observation/phase artifacts beneath
its workspace, including the long-horizon controller's final outcome. The host
joins that controller before closing its worker. Exit code 0 requires a completed task. A failed or unknown phase
must retain its evidence and stop subsequent processing.

### Reproduce the integration checks

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src \
.venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_pipeline.py \
  examples/forge-adapters/isaacsim_lab/tests/test_engine.py \
  examples/forge-adapters/isaacsim_lab/tests/test_observation.py
```

After accepting the Isaac Sim EULA in the deployment, capture actual cameras
using its Python environment (the path below is the acceptance host's install):

```bash
OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src \
/home/yanxu/miniconda3/envs/labutopia/bin/python -m isaacsim_lab.cli \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-pour-cycle.json \
  --observe --sensor-ref sensor://camera_1 --sensor-ref sensor://camera_2 \
  --artifact-root out/releases/v15.8.0/observations
```

This renders camera frames without issuing robot commands. It returns exit code
2 if capture is unavailable. `LabUtopiaCycleClient` still defaults to
`allow_live=False`; the configured worker must also expose a ready, qualified motion backend.

### Physical acceptance criteria

The same Agent task must settle all three subtasks. Each bottle must have
measured grasp/lift, aligned continuous tilt/hold and return/release/retreat.
The rod must have measured grasp, insertion, circular tip motion, withdrawal and
return. Final possession must be empty. The task must retain fresh observation,
calibration, assignment and execution evidence for every phase.

## Legacy cycle evidence

The following records describe the earlier complete-cycle controller interface.
They do not establish success for the new three-subtask Agent path.

## Acceptance layers

1. **Discovery**: the runtime lists `object.pour_cycle` and, for a profile that
   explicitly enables stir, `tool.stir_cycle`. Unsupported controllers remain
   absent or return `unsupported`.
2. **Planning and preflight**: the Agent supplies semantic labels and PAOS
   evidence. Preparation returns `motion_authorized=false`, binds the current
   scene revision/frame/calibration, and creates one preparation/assignment
   record. The caller task id is checked before execution.
3. **Single public Action**: one `object.pour_cycle` or `tool.stir_cycle`
   invocation owns all seven internal phases. The adapter never creates nested
   Agent invocations and the PAOS possession object remains the only lifecycle
   state owner.
4. **Measured settlement**: success requires observed acquire, transport,
   process, reorient/exit, stow, release, and retreat events, valid feedback,
   the requested process goal, changed scene revision, artifact evidence, and
   an empty possession on support. A request parameter is not completion proof.
5. **Failure closure**: stale frame/calibration, wrong task ownership,
   unsupported operation/parameter, missing feedback, or a failed transport /
   process phase cannot produce `succeeded`. Live exceptions settle as
   `unknown` with the world-change state preserved for reconciliation.

For `stir_cycle`, the entity reference (`/World/glass_rod`) and the control /
feedback prim (`/World/glass_rod/Cylinder`) are separate profile fields. The
feedback samples use the control prim, and process completion additionally
requires measured container alignment, radius progress, the configured hold
duration, and at least 90% of the configured stir turns. The controller then
executes the existing LabUtopia place/release/retreat path; PAOS settles
`stow`, `release`, and `retreat` only from the post-release support observation.

## Dry-run versus live

`LabUtopiaCycleClient` defaults to `allow_live=False`. In this mode its
capability declaration is dry-run only and `start()` refuses motion. A live
Isaac Sim run must explicitly construct the client with `allow_live=True`, use
the LabUtopia profile, accept the Isaac Sim EULA, and run the worker in the
Isaac Sim Python environment. The no-motion tests use a fake engine only to
verify PAOS lifecycle wiring; they are not evidence that the real Franka task
has succeeded.

## Verification

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src \
pytest -q examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py
```

The controlled RTX 5060 Ti + Isaac Sim 5.1 pour run remains the accepted live
success.  A repaired stir worker run produced measured feedback and a video,
but PAOS correctly rejected the process because the real tip path did not meet
the requested geometry:

- result JSON: `/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.json`;
- video: `/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.mp4`;
- 1,404 feedback observations and 1,403 video frames;
- acquire and transport completed; process was `failed/stir_observation_not_qualified`;
- measured process tip radius was about `0.0033-0.1003 m` against the requested
  `0.009 +/- 0.002 m`, so reorient/stow/release/retreat remain unknown.

This is an evidence-bounded live failure, not a successful stir claim.  The
remaining fix belongs in LabUtopia's controller end-effector reference/IK
target, after which the same PAOS profile must be rerun.

## v16.0.0 透明几何接入验收（2026-10-23）

当前验收仅通过 Provider/查询接入，动作与完整 Agent 任务未通过。原始场景仍为 `python scripts/preview_tabletop_station.py --view third-person` 对应场景；本轮未修改或提交 LabUtopia。

第三人称保存观测经过真实 ReMake/GraspNet，产生 13 个点云、256 个候选；新腕部 RGB-D/VLM/SAM2/ReMake/GraspNet 产生 11 个点云、192 个候选。标签均未形成可用唯一选择，腕部视角被机械臂本体遮挡，第三人称恢复有明显位置偏移。模型输出保持未验证，未进入机械臂运动。

集成测试 998 通过，2 项此前已有的 node 版本/发布锁检查仍失败；新增外部权重对照 1 通过，最大数值差 0 m；清理后相关验证 19 通过、1 项外部权重测试默认跳过，探针/准备阶段测试另有 31 通过。普通测试和模型候选数不替代真实动作反馈。

详见 `LAB_TRANSPARENT_PERCEPTION_IMPLEMENTATION_20261023.md`、`IMPLEMENTATION_REVIEW_V16_0_0.md` 及 `evidence/transparent-implementation-20261023.json`。历史机制验证只保留为历史证据，不能作为当前透明感知链的执行通过记录。

## v16.1.1 原场景 Agent 验收（2026-10-24）

本轮使用既有 mixture profile，启用 `--execute`，要求读取 R01/R02 标签、依次倾倒、搅拌并归位。任务参数显式给定：两次倾倒均 `tilt_rad=0.87`、`hold_s=0.6`；搅拌 `radius_m=0.009`、`depth_m=0.04`、`turns=2`、`duration_s=4`、`direction=ccw`。这些值属于本次实验指令，未成为产品默认工艺。

首轮模型从可读原图漏掉 R01。更新通用读取指引后，同图三次独立推理均读出编号；第二轮重新启动场景采集，Agent 再次读出 `R01 / LAB REAGENT / 蒸馏水 / Distilled water / H2O / Simulation reagent`。本轮没有修改标签材质或位置。保存的 R01 恢复点云经真实 GraspNet 返回 32 个候选，仅作离线诊断。

前两轮联合采集返回 `capture_skew_exceeded`。修复先读多路缓冲再写盘，并用 Isaac 渲染帧证据区分同帧数据导出耗时与真实采样差；不同帧、换帧与无效帧信息继续拒绝，没有帧 API 的相机保留独立时间。没有扩大既有 50 ms 偏差或 1000 ms 新鲜度要求。

参数化验证直接调用真实轨迹生成器，再根据 TCP/物体挂载还原瓶口或棒尖，改变倾角、停留、半径、深度、圈数、时长和方向并验证结果。最终相机、引擎、视觉理解、Host、动作轨迹和编排六文件 **175 passed**；Ruff 通过。测试没有运行物理仿真动作。

执行验收继续要求 R02 唯一视觉身份、完整瓶口/杯口/棒端观测与独立几何精度证据。`resolve` 和 `refresh_process` 要求 `validated_observation`，当前 ReMake worker 输出 `unverified_estimate`；不能改名绕过这项缺失。前两轮均无 manipulation task 或 controller outcome，没有抓取、倾倒、搅拌、归位的执行反馈。

第三轮 23:46:55–23:57:46 的记录在 `out/releases/v16.1.1/agent-fullchain-20261024-2350-r3/`。联合观测恢复为 `available`、freshness 539 ms，近景完整读出 R01，ReMake 全景/近景推理为 0.394/0.102 s。摘要投影未保存原始采样时间和完整 views，不能以 Agent 填写的 `capture_skew_ms=0` 作为独立同步测量。R01 身份点与 mask 错配、瓶口裁切、R02 未读清、杯口点越界、棒端未定仍阻止执行。最终 `tasks=[]`、`controller_outcomes=[]`、退出码 1：全链路未通过，没有实际工艺动作反馈。

离线重查第二轮 R01 候选可运行以下命令。指定新的输出路径以保留已有结果；该查询不创建当前仿真准备或动作。

```bash
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src \
.venv/bin/python out/releases/v16.1.1/query_recorded_grasp.py \
  --run out/releases/v16.1.1/agent-fullchain-20261024-2330-r2 \
  --label R01 --output /tmp/paos-r01-grasp-repeat.json
```

复现最终无运动回归：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src \
.venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_pipeline.py \
  examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py \
  examples/forge-adapters/isaacsim_lab/tests/test_observation.py \
  examples/forge-adapters/isaacsim_lab/tests/test_engine.py \
  examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py
```

按本次实际指令启动新一轮授权仿真（输出目录使用新名称）：

```bash
OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src \
.venv/bin/python -m isaacsim_lab.agent_host \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --config /home/yanxu/.PhyAgentOS/config-rgb-no-evolution-long.json \
  --workspace out/labutopia-remake-next-run --execute --execution-timeout-s 1800 \
  "$(jq -r .instruction out/releases/v16.1.1/agent-fullchain-20261024-2330-r2/acceptance.json)"
```

原始输入、中间结果、失败和模型候选保存在 `out/releases/v16.1.1/`，诊断与报告分别见 `../diagnostics/transparent-model-comparison-20261023.md`、`../reports/transparent-model-selection-report-20261024.md`。后续顺序为：补齐观测和几何测量 → 单物体抓取归位 → 单次倾倒 → 单次搅拌 → 两次倾倒与搅拌组合任务。每阶段以当前观测、准备、执行反馈和 Runtime 结算验收。
