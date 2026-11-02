# Cooked finger envelope repair / 夹指碰撞包络修复

## Diagnosis / 诊断

The fresh v16.6.1 capture in
`out/lab-fullchain-truth-20261102-reset-sync-no-motion-r1/` rejects four
aperture candidates and all 48 approaches: workspace 20, environment 20,
self-overlap 4, IK unavailable 4. Reset FK/USD synchronization is repaired,
but the unchanged distribution shows that it did not solve grasp feasibility.
环境/自碰撞回执是模型重叠证据，不是实测撞击；IK 失败也不是不可达证明。

Historical candidate 17 has table top Z=0.712386069 m, checked TCP
Z=0.780287021 m, authored full-opening mesh minimum Z=0.728555958 m,
and unpadded box minimum Z=0.717026071 m. The padded box rejects while
the mesh has 16.17 mm clearance at this intermediate sample. Final TCP
Z=0.735411521 m is lower; final clearance must be checked independently.
不能把中间位置的净空外推为终态/完整路线可行。

## Architecture decisions / 架构决策

- Generic layer: task parameters, opaque candidate selection, same-capture
  lineage; no USD path, gripper geometry, IK seed or physical success inference.
- Adapter: read actual PhysX cooked convex components, transform into finger
  body coordinates, conservatively bound each convex slice including edge/plane
  intersections, sweep each bound over prismatic limits, retain existing padding.
- Replacement: the existing collision-query/kinematics mechanisms and public
  preparation contracts remain unchanged. Unit tests substitute cooking and
  query mechanisms; public failures continue to use existing opaque receipts.
- Freshness: geometry belongs to the current worker scene/articulation; historic
  replay retains its original capture separately and never authorizes motion.
- Lifecycle, cancellation, settlement and qualified-only recovery remain owned
  by Runtime/Coordinator/AgentLoop. No alternate scheduler or recovery path.
- Minimal leak/failure test: failed cooking must not qualify clear; convex
  slicing must cover edges/interiors and full travel, with identical margins;
  collision errors still propagate before any robot command.

## Plan / 计划

1. Reproduce box overfill and verify conservative convex slice coverage in
   pure geometry tests. Obtain cooked data with the installed PhysX cooking API,
   not render-mesh vertices. Invalid/unavailable cooked mesh evidence rejects.
2. Wire into the existing Adapter finger geometry seam and diagnostics. Keep
   sphere, self-collision, workspace, aperture, source-contact policy and full
   route validation. Do not add IK branches before the geometry rerun identifies
   a remaining need. No new public contracts, hashes or gates.
3. Run affected regressions and native historical-sample no-motion validation;
   distinguish contract, Provider and live execution evidence. Run a fresh
   qualification only after the new representation is verified.
4. Record exact changes/results and push only task-owned files on the current
   branch. Other dirty files and runtime artifacts stay untouched.

This is safety-sensitive Adapter work. The Hephaestus-only authority documents
are not present; PAOS AGENTS.md, the developer manual, manipulation DAG guide
and visual geometry evidence architecture are the applicable authorities.
本轮使用无动作验证；不宣称倒液/搅拌完成。

## Implemented and measured / 实施与实测结果

- `finger_collision.py` copies all cooked components in the synchronous callback
  and bounds solid slices including crossing edges. `finger_geometry` transforms
  them from collider to body coordinates using the composed stage. Existing
  joint transforms, full travel, measured-width tolerance and padding are reused.
- Native replay `out/lab-cooked-finger-geometry-20261102-r1/geometry.json`:
  eight components per finger, 53/56 boxes; all five old intermediate failures
  clear, joints/time unchanged. This proves removal of the early box overfill.
- 434 affected regression tests pass, including 13 new geometry/failure tests;
  Ruff, compileall and whitespace checks pass. Commands are in
  `docs/forge/IMPLEMENTATION_REVIEW_V16_6_2.md`.

### Fresh formal no-motion run / 正式新捕获无动作运行

Workspace: `out/lab-fullchain-truth-20261102-cooked-finger-no-motion-r1/`.
Session: `cli:lab-3c4728b402d2`; task: `task_9c72fe6c84e94594`;
revision: `revision_3b1df384b60c41f4`.
Scene: `labutopia-tabletop-rod-rack-v1:8004def4d5f0416bb2e01bee45d4864b:0`.
Calibration: `artifact://labutopia/calibration/80750d0520574f578e0d832774b91f5c.json`.

Ten candidates remain geometry-qualified. Four exceed aperture; six generate
48 approaches, still rejected as workspace 20, environment 20, self-overlap 4,
IK unavailable 4. **The distribution alone hides the repaired failure location.**

- Candidate 17: five old finger/table rejections become later **hand-sphere/table**
  rejections. First checked TCP Z moves from 0.780287021 to 0.777972762 m,
  advancing 2.314 mm downward, still 42.561 mm above the target TCP. Sphere
  center Z=0.738710899 m, padded radius=0.027 m, lower bound=0.711710899 m,
  overlapping the table bound by 0.675 mm. This is still a model overlap, not
  measured hand contact; the actual cooked palm has not been tested here.
- Candidate 55: two refined finger/table rejections occur at TCP Z about
  0.742054/0.742087 m. Padded slice minimum Z is 0.711146/0.711150 m,
  about 1.24 mm below the table bound. This no longer uses the old whole-finger
  box; whether remaining slice overfill or actual geometry dominates is unproven.
- Other pairs remain: link5/table 3, link6/table 4, hand/R01 2,
  link6/R02 1, link7/R02 1, link5/BEAKER 2, link1/link5 3, link1/link6 1.

Task terminal is `cancelled`, host exit 1. All three execution records are Queries;
transport success of `grasp_task_affordances` does not change its unavailable
payload. `simulated_motion_enabled=false`, `controller_outcomes=[]`; no Action,
R04 manipulation or stirring started.

### Remaining boundary / 剩余边界

本轮已修复并验证整夹指包络的提前误拒绝；尚未修复或证明整条抓取路径可行。
下一步应先对实际 cooked 手掌与最终候选姿态做几何复核，再区分刚体碰撞表示、
候选夹持姿态与 IK 分支问题。保留安全裕量；不能从单一 IK 解失败推断目标不可达，
也不能为得到成功结果直接缩小球半径、修改候选坐标或重构 AgentLoop。

The remaining rigid-link/IK findings are a separate evidence-driven repair;
this change does not manufacture a successful candidate or authorize motion.
