# R03 collision geometry and reset-state repair / 碰撞几何与复位状态修复

## Evidence and corrected diagnosis / 证据与诊断纠正

The v16.6.0 run `out/lab-fullchain-truth-20261102-native-coordinate-no-motion-r2/`
ended before motion. Ten R03 geometry-qualified candidates included four aperture
rejections. Six others generated 48 approaches: workspace 20, environment overlap
20, self-overlap 4 and unavailable IK 4. These are model decisions, not observed
physical impacts. Increasing candidate budget or rewriting AgentLoop does not
explain these findings.

候选 17 的回执 `ce11776449c344e299f7b6af02cdfed8.json` 保存了五个
夹指/桌面拒绝的实际检查关节角。通过真实 Isaac 会话按这些角度计算 FK、
最终 USD 夹指几何及碰撞包络，未设置这些假设关节角到机械臂，未执行控制器。
初次结果在 `out/lab-collision-geometry-20261102-r1/geometry.json`。

- Table surface world Z maximum: `0.712386069 m`.
- First failed sample TCP Z: `0.780287021 m`.
- Authored finger mesh swept over both joint limits: minimum Z `0.728555958 m`;
  mesh/table separation is about `16.17 mm` at this sample.
- Existing full-travel finger AABB minimum Z before margin: `0.717026071 m`.
  The configured 3 mm margin is applied in each box axis; its world-Z projection
  reaches the table. This explains a conservative model rejection. It does not
  establish contact or prove the remaining approach/final grasp is safe.
- All five saved finger/table samples show this distinction. AABB corner space
  is not occupied mesh; margins and closure travel must still be retained.

另一项独立且可复现的错误是初始状态不同步：`_refresh_initial_robot_state`
先 `world.step()` 推进动力学，再把关节读数重置回配置姿态，只做 render。
CPU articulation 的 USD 变换没有同步回新 qpos。真实比较发现 hand 平移相差
`0.006561186 m`，link7 相差 `0.006677454 m`。这超过当前 2 mm 位置容差；
腕部相机挂在 hand 下，不能把这个不同步状态当成一致的观测/规划起点。

## Ownership / 架构与实现边界

- Generic domain/AgentLoop: semantic operations, instruction parameters, opaque
  candidate selection and same-capture references. No USD paths or joint seeds.
- Isaac Adapter: initial/reset state synchronization, FK, collision mechanisms,
  private diagnostic geometry and complete-route qualification.
- Provider substitution: existing Tool/provider contracts stay unchanged;
  replacing the simulator/IK implementation changes only the Adapter mechanism.
- Evidence boundary: historical joint replay explicitly retains original capture
  identity and a separate current scene revision. It cannot authorize execution.
  Any subsequent Agent run must capture and bind new observation evidence.
- Lifecycle/cancellation/recovery/settlement remain with the existing
  Runtime/Coordinator/AgentLoop owners. Diagnostics start no tasks or Actions.
- Smallest abstraction-leak test: collision failure retains geometry in a private
  artifact and exposes only its existing reference; a replacement backend must
  still reject before motion. No new public schema, hash, baseline or gate.

## Implemented repair / 实施内容

1. Replace dynamics stepping during initial-pose refresh with explicit kinematic
   update and PhysX-to-USD publication, followed by rendering. Reuse the same
   helper at initial creation and after reset; preserve timeline state on error.
2. Retain checked joints/TCP, collider primitive, world geometry, margin and
   obstacle/link pair in private collision diagnostics. Preserve them through
   route error wrapping and task-affordance no-motion receipts. Explicitly label
   them `collision_model_overlap`, never measured contact.
3. Add a repeatable Adapter-local receipt inspector. It reads actual composed
   finger colliders and world obstacles, checks FK versus USD at reset, evaluates
   recorded joint poses numerically and checks no joint/time changes afterward.
4. Keep the existing finger envelope, margins, workspace, aperture, IK continuity,
   qualified-only recovery and full-route validation. Mesh separation at one
   intermediate sample is insufficient evidence to remove a collision check.

The initial reset defect has a direct repair. Replacing collision primitives or
adding alternative IK seeds is a separate decision requiring fresh results after
the state repair. No scene object is resized/repositioned in this change.

## Validation / 验证

Initial tests first reproduced seven failures from the old dynamics-step path.
The engine suite then passed 66 tests after the repair. The complete affected
suite passed **421 tests**, including geometry-receipt tests with substituted
query mechanisms and the existing qualified-only Action recovery suite. Ruff,
compileall and whitespace checks passed. Unit tests alone are not motion proof.

Native post-repair `out/lab-collision-geometry-20261102-r3/geometry.json` confirms:
hand FK/USD error `1.9680e-7 m`; maximum link error `2.0074e-7 m`, versus the
original hand error `6.5612e-3 m`. Joint positions and physics time remain
unchanged during all five historical joint-geometry checks. The joint samples
still trigger the conservative finger/table model rejection; the repair does
not bypass it or establish grasp success. Intermediate r2 stalled during startup
and was explicitly terminated with no result; r3 completed successfully.

A new formal Agent no-motion run uses
`out/lab-fullchain-truth-20261102-reset-sync-no-motion-r1/`, the same profile,
instruction and process parameters as the preceding run, without `--execute`.
Its result must be recorded separately from historical replay.

### Formal fresh-capture outcome / 正式新捕获结果

- Session `cli:lab-3019a1d6c656`, task `task_ebea061a2ed841e3`, revision
  `revision_a274694de4f847f9`; host exits 1, task terminal `cancelled`.
- Scene `labutopia-tabletop-rod-rack-v1:da1a3f2ae9fc46b9a7d9027e4ac16d92:0`,
  calibration `artifact://labutopia/calibration/7a9942cc43164d0ab7a4302d711d3a92.json`.
- R03 process-feature Query/preparation succeed. The task-affordance Query still
  returns unavailable: four candidates exceed aperture; six candidates generate
  48 failed approaches (workspace 20, environment 20, self-collision 4, IK 4).
- All 24 environment/self-collision attempts now contain private structured
  geometry diagnostics. The same failure distribution after state repair proves
  that the initial-state defect was real but was not the sole/main explanation
  of these final-approach rejections. Do not claim the collision blocker fixed.
- `simulated_motion_enabled=false`, `controller_outcomes=[]`; no Action or
  acquisition/pour/stir controller is started. R04 and GLASS_ROD do not execute.

下一步决策应依据现在完整记录的碰撞形状，区分终态真正不可行与保守包络提前拒绝。
若收紧夹指碰撞表示，必须证明它覆盖实际 cooked collider 及整个开合行程，保持既有
安全裕量；若仅是手臂 IK 分支问题，再评估有界替代种子。不能用网格顶点局部净空
直接跳过碰撞，也不能把这次已修好的状态同步问题当成所有碰撞的根因。

```bash
OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/labutopia/bin/python \
  examples/forge-adapters/isaacsim_lab/scripts/inspect_collision_receipt.py \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --receipt out/lab-fullchain-truth-20261102-native-coordinate-no-motion-r2/artifacts/labutopia/grasp-approach-feasibility/ce11776449c344e299f7b6af02cdfed8.json \
  --output out/lab-collision-geometry-NEW
```

The inspector never exempts source contact in its diagnostic overlap replay;
that replay is not a replacement for original stage-specific qualification.
Attempts without stored checked joints remain explicitly unreplayed.

Affected regression command (from repository root):

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_profile.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py
```
