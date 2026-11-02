# Palm and final-approach follow-up / 手掌与最终接近后续修复

## Evidence / 当前证据

v16.6.2 fixes whole-finger envelope overfill with actual cooked convex solids.
The fresh task `task_9c72fe6c84e94594` still has no feasible approach. Candidate
17 now fails later at hand-sphere/table; candidate 55 reaches lower finger/table
checks. These are collision-model decisions, not measured impacts.

Candidate 17 first rejected TCP Z=0.777972762 m, grasp target Z=0.735411452 m.
Hand-sphere center Z=0.738710899 m, padded radius=0.027 m, bottom=0.711710899 m.
The table top is Z=0.712386069 m: padded overlap is 0.675 mm, while the
unpadded 0.024 m sphere itself is about 2.325 mm above the table. This alone
cannot establish whether the actual cooked palm is clear, within margin or in
contact. The remaining 42.56 mm of descent also cannot be declared safe.

Source receipt:
`out/lab-fullchain-truth-20261102-cooked-finger-no-motion-r1/artifacts/labutopia/grasp-approach-feasibility/5c0e6cc776c04688830565cd0dd03fcd.json`.

## Ownership and plan / 职责与计划

- Generic domain/AgentLoop continues to own semantic operations, opaque
  selections, cancellation/recovery and settlement; no USD or joint parameters.
- Isaac Adapter owns composed collision geometry, FK/IK, motion qualification,
  private evidence and execution feedback. Mechanisms may be replaced behind
  existing preparation/query ports; no new public contract or lifecycle owner.
- First extend the no-motion inspector to read the reported rigid link's
  actual cooked components at recorded joints. No articulation writes or steps.
- Use those results to choose representation repair versus planning/IK search.
  Do not shrink spheres, reduce margin or exempt support to force success.
- Smallest leak test: substituted collision/cooking mechanism rejects missing
  evidence without commands; geometry remains private behind the same receipt.
- Preserve current-capture observation/revision/calibration in new qualification;
  historical replay remains diagnostic with a separate current scene identity.

Native measurement target: `out/lab-palm-cooked-geometry-20261102-r1/`.
Native measurement has completed with unchanged joints/time. At candidate 17's
five hand/table samples the actual cooked hand minimum Z is below the table
height by 0.574, 1.341, 1.330, 1.333 and 1.334 mm. This refutes the assumption
that reducing the hand sphere is the proper fix. Changing an IK branch cannot
change rigid gripper geometry for a fixed TCP pose.

The 64 proposed poses also contain higher grasps, but process qualification
rejects many near the opening. For example, candidate 24 is at Z=0.76768 m,
while the current opening exclusion uses twice the measured rim radius
(0.0287465 m). This does not prove candidate 24 is graspable or preserves the
pouring lip. Relaxing that rule without a geometric opening-clearance check
would introduce a separate policy/safety defect and is not part of this repair.

## Revised implementation / 基于实测的修复

Add an Adapter-private **final gripper pose preflight** before pre-grasp IK:
evaluate actual cooked palm and full-travel finger bounds at each exact
geometry-equivalent candidate pose with the original margin/contact rules.
Impossible final geometry must be reported as `final_grasp` evidence instead
of repeatedly exploring pre-grasp branches and reporting whichever earlier
collision happened first. A clear preflight still must pass all existing IK,
self-collision, approach and full-route qualification.

Share current-stage cooked-body extraction with the existing finger mechanism;
keep it private. Do not invent checked joints for a pose-only test. Preserve
the exact candidate TCP in private diagnostics. Tests must show final obstruction
stops before IK/commands, source contact is the only intentional exemption, a
clear endpoint cannot bypass later failures, and Provider errors remain explicit.

## Implemented result / 实现结果

Isaac Adapter now shares `cooked_body_boxes` between palm and fingers. It checks
the final hand pose derived from the candidate TCP before pregrasp IK, once per
axial orientation, reusing the outcome for both approach distances. Cooked
geometry failure stays unavailable. All prior downstream checks remain active.
Public probe errors contain failure codes/counts and the opaque evidence receipt;
the private artifact retains simulator paths, full poses and query geometry.

Review exposed an empty-source replay bug: `path.startswith(source + "/")`
matched every absolute path when source was empty. Four new regression cases
failed first, then passed after requiring a nonempty source for that exemption.
This changes diagnostic replay; formal binding already supplies a nonempty
source. No-source replay now tests all external objects, including the source.

## Fresh run / 新捕获实测

- Workspace: `out/lab-fullchain-truth-20261102-final-gripper-no-motion-r1/`.
- Session: `cli:lab-ca9ce2f70682`; task: `task_4972b9d477f048d2`.
- Revision: `revision_d41e73623a814c98`.
- Scene: `labutopia-tabletop-rod-rack-v1:e8deb99e6ba4497885dda271553640b7:0`.
- Calibration: `artifact://labutopia/calibration/4a562a0dbd1043a9b5a1b7396ede7e86.json`.
- R03 process-feature Query and preparation are available; task-affordance
  Query returns unavailable. AgentLoop cancels the task; host exits 1.
- `simulated_motion_enabled=false`; `controller_outcomes=[]`. No grasp/pour/stir
  execution is claimed; R04 and GLASS_ROD do not reach execution.

| Candidate index in this capture | Rejection | Coverage |
| --- | --- | --- |
| 4, 16, 44, 57 | Required opening exceeds measured 0.08 m limit | Four candidates |
| 10, 17, 23, 27, 52, 55 | `final_grasp`, cooked-palm padded bounds/table | Six candidates × four axial orientations |

The 24 unique final-pose checks block both approach distances, producing 48
attempt records; these are not 48 independent endpoint measurements. No IK is
needed for those rejected endpoints. The result identifies the earlier binding
constraint, rather than proving that old workspace/self/IK limitations vanished.
Query transport success does not turn its unavailable payload into success.

450 affected tests pass. Ruff, compileall and whitespace validation pass.
Native pose-only replay `out/lab-final-gripper-geometry-20261102-r1/geometry.json`
reproduces all eight recorded candidate-17 endpoint rejections with no source
exemption. It reports zero joint samples, eight final-pose samples, zero
unreplayed attempts, unchanged joints/physics time and zero controller commands;
process exit is 0. Maximum initial FK/USD translation disagreement is 2.01e-7 m.
The original/current scene identities remain distinct. This diagnostic does not
reuse historical evidence as current preparation authority. Kit reports material
and GPU-particle errors; no liquid/particle simulation is validated by this run.

## Remaining work / 后续真正的阻塞

当前受检集合没有同时满足工艺约束、夹爪开口与终态净空的候选。继续增加接近距离或
IK seed 不会改变固定 TCP 下的刚性手掌几何。不得由此断言所有候选、所有抓取区域或
整个场景都无解，也不得以此放松碰撞球、裕量、瓶口保护或完整路线检查。

The next candidate-generation change belongs to the Grasp/Task-Affordance
Provider seam: measure coverage of opening-safe gripping regions and actual
gripper clearance using current observed geometry, then propose new candidates
with new opaque references and unchanged lineage checks. If the existing opening
exclusion is shown to over-reject usable neck/body regions, replace it only with
an evidenced geometric lip-clearance mechanism and substitution/failure tests.
Do not translate accepted candidates or restore Provider-rejected raw candidates
inside Action recovery. Compare old/new eligible sets before full-route
preparation; only a completely prepared route may proceed to authorized motion.
