# R03 native grasp coverage repair / 原生候选覆盖修复

## Decision / 重构决策

Use a local Grasp Provider mechanism extension, not an AgentLoop or public
selection-contract rewrite. Candidate selection cannot recover approaches that
the model never proposed. Existing same-capture Query -> opaque selection ->
preparation -> Action ownership remains correct. The motion workspace, approach
distance, collision limits, labels and semantic operation parameters stay intact.

采用 Provider 内部局部改造，不重构 AgentLoop。先解决候选生成方向覆盖，再由既有
工艺资格和机器人资格检查筛选；不通过修改安全下界、直接翻转抓取姿态或回退原始集合放行。

## Evidence / 已核对证据

Source: `out/lab-fullchain-truth-20261102-approach-feasibility-no-motion-r2/`.
R03 prediction: `artifacts/labutopia/grasp-predictions/06d82ec1606442dbbe6539a003e9672e.json`.
Cloud: `artifacts/labutopia/object-point-cloud/d69c342dc30c4c35aa497ab57edfd9b0.npy`.

- 1,214 captured points; world bounds approximately
  `[-0.301608,-0.391608,0.712397]` to `[-0.238393,-0.328393,0.792345]` m.
- 44 decoded proposals, 24 after NMS, below the configured 64 public budget.
  Thus this capture does not support blaming top-K truncation.
- Seven distinct approach directions among the 24, all with positive world Z
  components between 0.361839 and 0.640604. The three task-qualified proposals
  share approach Z=0.634282 and grasp Z=0.750917 m.
- At backoffs 0.12/0.18 m, pregrasp Z=0.674803/0.636746 m is below the unchanged
  workspace floor 0.7 m. This fails before IK, not at self-collision. The recorded
  24 failures do not establish that every possible grasp of this bottle fails.

## Mechanism / 修复机制

The isolated GraspNet Worker accepts up to four configured unit-quaternion
input-coordinate rotations. Let `c` be the original cloud centroid and `R` the
configured rotation. Infer on `p' = R(p-c)+c`; restore model-native predictions
with `t = R.T(t'-c)+c` and `Q = R.T Q'`. All passes share sampled point indices
and optional seed. Identity alone retains the previous inference behavior.

每个方向重新调用模型，随后逆变换回原捕获帧。没有改变物体几何、补充遮挡面或生成新相机
观测，也没有把已有不合格位姿人工旋转成新候选。总候选预算仍为原有 512 -> NMS -> 64。
失效推理不能返回前几次的部分成功，无法通过 preparation 的候选仍被拒绝。

PAOS ownership (Tier C-Safety):
- Generic/AgentLoop: task meaning, opaque selection, revisions, cancellation,
  recovery and settlement. No USD, robot joints or input-frame angles added.
- Grasp Provider/Worker: configurable model inference and frame restoration.
  GraspGen/replacement worker retains the same candidate protocol.
- Isaac Adapter: captured transforms, aperture, IK, workspace, contact/collision,
  full-route qualification and controller feedback. Probe success is not motion.
- Freshness: original observation, scene revision, camera frame, calibration and
  point-cloud evidence are retained; a replay is historical inference evidence,
  not a fresh scene or permission to execute.
- Smallest leakage tests: unchanged worker reply accepted by existing Provider;
  inverse-transform regression; partial inference failure returns no candidates;
  rejected raw references remain excluded by the existing subtask recovery tests.
- No new hash/schema/lifecycle owner or release gate. Existing numeric/frame
  validation and tests address the actual failure mode.

Authority: `AGENTS.md`, `docs/zh/03-developer-manual.md`,
`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`, and
`docs/forge/VISUAL_GEOMETRY_EVIDENCE_ARCHITECTURE.md`. Hephaestus skill reference
documents are absent in this PAOS repository; its actual PAOS ownership rules
govern this implementation, without introducing a missing-document gate.

## Paired native inference / 同捕获配对实测

Output: `out/lab-grasp-coordinate-replay-20261102-r1/`.
Seed 0; same cloud, model checkpoint, score threshold and point budget.
Identity plus 180-degree input rotations around camera-coordinate X/Y/Z.

| Result | Identity | Four input frames |
| --- | ---: | ---: |
| Native decoded | 44 | 1,058 |
| Above threshold | 44 | 1,056 |
| Worker returned | 44 | 512 |
| Provider post-NMS | 24 | 389 |
| Provider returned | 24 | 64 |
| World approach Z range | 0.362 to 0.641 | -0.968 to 0.994 |
| Existing bottle-geometry-qualified | 3 | 10 |

Among qualified ensemble proposals, examples (capture-local indices, not stable
cross-run identities) include index 17: grasp Z=0.735412, approach Z=-0.464716,
pregrasp Z=0.791177 at 0.12 m, width=0.05775 m; index 55: Z=0.734591,
approach Z=-0.376878, pregrasp Z=0.779816, width=0.03514 m. These are candidates
for the unchanged aperture/IK/collision checks, not successful grasps.

因此有证据启用本实验的四次推理配置；没有证据要求缩短接近距离。GPU 冷启动影响耗时，
这里不比较两次运行速度。固定 seed 不保证不同 GPU/依赖版本位级一致。

## Validation commands / 验证命令

```bash
PYTHONPATH= /home/yanxu/miniconda3/envs/graspnet/bin/python \
  examples/forge-adapters/robotwin20/scripts/compare_grasp_input_frames.py \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-perception.json \
  --prediction out/lab-fullchain-truth-20261102-approach-feasibility-no-motion-r2/artifacts/labutopia/grasp-predictions/06d82ec1606442dbbe6539a003e9672e.json \
  --artifact-root out/lab-fullchain-truth-20261102-approach-feasibility-no-motion-r2/artifacts/labutopia \
  --output out/lab-grasp-coordinate-replay-NEW \
  --seed 0 --input-rotation-xyzw 0 0 0 1 --input-rotation-xyzw 1 0 0 0 \
  --input-rotation-xyzw 0 1 0 0 --input-rotation-xyzw 0 0 1 0

PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  ./.venv/bin/python -m pytest -q examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_profile.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py
```

## Integration outcome / 集成结果

- Full affected regression: **410 passed**; focused worker: **19 passed**.
  Ruff, compileall and diff whitespace checks passed. Tests include substitution
  through the unchanged proposal-provider protocol and existing qualified-only
  Action recovery; no controller is exercised by these tests.
- Formal r1: `out/lab-fullchain-truth-20261102-native-coordinate-no-motion-r1/`,
  session `cli:lab-99ebda8ffe51`. `acceptance.json` records `tasks=[]`,
  `controller_outcomes=[]`, `simulated_motion_enabled=false`. Initial binding
  failed `scene.observe is unavailable or stale` against max_age_ms=1000.
  No grasp query/preparation ran; this is not a negative grasp result.
- Unchanged r2: `out/lab-fullchain-truth-20261102-native-coordinate-no-motion-r2/`,
  session `cli:lab-2063ffedd5eb`, task `task_053053cf3a0b4804`, revision
  `revision_e4383c96834e44ec`. Task cancelled after R03 process-feature Query and
  preparation passed, but grasp-task-affordance returned unavailable.
- Fresh R03 inference reproduces decoded=1058, worker returned=512,
  post-NMS=389, public=64. Ten pass the existing bottle-geometry check.
  Four fail gripper aperture before approach enumeration. The remaining six
  produce 48 approach attempts: 20 workspace, 20 environment collisions,
  four self-collisions, four unavailable IK. Zero approach candidates pass.
- Environment collision breakdown: finger/table=7, link6/table=4,
  link5/table=3, hand/R01=2, link6/R02=1, link7/R02=1, link5/BEAKER=2.
  Self-collision examples are link1/link5 and link1/link6. These are the existing
  Adapter collision-model results; they are not physical contact measurements.
- Capture scene: `labutopia-tabletop-rod-rack-v1:2fcce54c68e140d9ab15afe19f46e9dd:0`;
  calibration: `artifact://labutopia/calibration/c24f19fdd67442bd92ddf18844fcbd8f.json`.
  Ten private receipts live in the r2 `artifacts/labutopia/grasp-approach-feasibility/`
  directory. Representative candidate 17 receipt:
  `ce11776449c344e299f7b6af02cdfed8.json`; candidate 55:
  `7616c6ba05e04802b10a53605684c721.json`.

## Remaining blocker and next decision / 剩余阻塞及后续决策

Direction coverage is repaired and demonstrably wired into the fresh workflow.
The current selected grasps are still infeasible under the present embodiment
and scene. This does not justify bypassing qualification, enabling the controller
or claiming that the complete acquisition/pour/stir task is repaired.

下一步应以失败回执中的 checked joints/TCP 和具体碰撞对做无动作几何复核：
1. 将当前 Franka 手掌/夹指实体与 tabletop/邻瓶/烧杯在同一世界帧可视化，核对
   provider-to-TCP 变换、碰撞形状与真实网格的对应关系，区分模型保守性和真实干涉。
2. 若碰撞确实存在，针对当前已观测瓶身可夹持区域与真实夹爪实体净空联合评价；
   不仅用 TCP 高度或模型预测 width 判断可抓。不能直接放宽瓶口/支撑端阈值放行。
3. 对仅因某个 IK 分支碰撞的候选，在 Adapter 既有准备边界评估有界替代关节种子；
   每个种子仍需限位、FK、连续性、碰撞及从当前状态出发的完整路线验证。
4. 若所有合法候选仍不可达，明确返回 Agent 重新观测/重规划；若必须移动瓶子或改布局，
   作为独立场景变更记录，并产生新的 scene revision/观测，不能沿用本次候选证据。

None of these follow-ups requires moving USD paths, robot limits or joint seeds
into AgentLoop. Current public selection/ref freshness boundaries should remain.
