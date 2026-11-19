# LabUtopia 底盘 Franka 部署对照 / Ridgebase Franka Placement Comparison

记录时间 / Recorded: 2026-11-19，Asia/Shanghai。版本 / Version: v17.7.0。

## 当前结论 / Current Finding

移除桌面旧 Franka 后，A 轮仍在倾倒路线准备阶段失败：24 个候选全被拒，其中 22 条明确报告 `panda_link2 overlaps /World/table/surface/mesh`。移除旧臂不足以恢复倾倒。靠近桌子的 B 轮先在抓取闭合阶段因物体旋转超出既有容差而失败，尚未检验新位置的倾倒可达性。

After removing the legacy tabletop Franka, run A still fails during held pour-route preparation: all 24 candidates are rejected, with 22 explicitly reporting the live arm's link2 overlapping the tabletop. Removing the old arm is insufficient to restore pouring. At the closer base position, B fails during acquisition closure on object rotation beyond the existing tolerance, before testing held-pour reachability.

## 部署与职责 / Deployment and Ownership

- 旧场景包含 `/World/Franka`，共有 11 个碰撞体；新 USD 覆盖层将该子树 `active=false`，从渲染与物理场景排除，原资产保持原样。 / The original scene contains `/World/Franka` with 11 colliders. A USD composition layer deactivates that subtree for rendering and physics while preserving the source asset.
- A 使用底盘世界坐标 `[-1.201, 0.36, 0.01]`m；B 使用 `[-1.05, 0.18, 0.01]`m。朝桌方向前移 0.151m，并向烧杯横移 0.18m；姿态保持 `[1,0,0,0]`（wxyz）。 / A uses world base position `[-1.201, 0.36, 0.01]`m; B uses `[-1.05, 0.18, 0.01]`m. The base moves 0.151m toward the table and 0.18m toward the beaker laterally, with unchanged wxyz orientation `[1,0,0,0]`.
- 桌边 xmin≈−0.735087m，原底盘前缘≈−0.73477m，已贴桌边。新位置使底盘伸入桌下约15.1cm；底盘机身顶部约0.29m低于桌底约0.697m，但这不替代手臂及完整路线碰撞检查。 / The old chassis front is already adjacent to the table edge. The new position extends the chassis about 15.1cm under the table; chassis height alone does not establish arm or route clearance.
- 变化位于 Isaac Adapter 部署层；配置与场景可替换，调用者和公共 Tool/AgentLoop 不变。WorkerSession 仍独占场景生命周期，Runtime 继续负责取消、结算和恢复。 / Changes belong to Isaac Adapter deployment. Scene and configuration can be replaced without changing callers or public Tool/AgentLoop contracts. WorkerSession retains scene lifecycle ownership; Runtime owns cancellation, settlement and recovery.
- 两轮都重新初始化、新 scene revision、新感知及新完整 preparation；碰撞、IK、工作区、接触与姿态阈值保持。 / Both runs use fresh initialization, scene revision, perception and full preparation, retaining collision, IK, workspace, contact and pose checks.

## 同任务对照 / Same-Task Comparison

| 项目 / Item | run24f | A：仅移除 / Remove only | B：移除并靠近 / Remove and approach |
|---|---|---|---|
| 旧桌面臂 / Legacy tabletop arm | 活动 / Active | 停用 / Inactive | 停用 / Inactive |
| 底盘坐标 / Base position (m) | `[-1.201, .36, .01]` | `[-1.201, .36, .01]` | `[-1.05, .18, .01]` |
| 任务 / Task | `task_172d94df00634efc` | `task_5e60fae54b2f41ba` | `task_7b3ca51a7ec34239` |
| 状态 / Status | failed | failed | failed |
| acquire | succeeded | succeeded | failed: `grasp_object_displaced` |
| lift 采样 / Lift samples | 135 | 108 | 0 |
| attach 误差 / Attach error | 峰值约17.5mm / peak about17.5mm | 峰值9.6809mm / peak9.6809mm | 末帧7.2028mm，非峰值 / final7.2028mm, not peak |
| 倾倒 / Pour | 未执行 / Not executed | 未执行 / Not executed | 未执行 / Not executed |
| 倾倒准备 / Pour preparation | `pour_route_unavailable`，详情缺失 / detail lost | 24候选拒绝，22条link2撞桌 / 24 rejected, 22 link2/table | 未到达 / Not reached |

用户指令逐字相同，实际倾倒任务参数为1.0rad、保持2.0秒；A/B 继续沿用现行物理、控制、感知与 oracle 配置。A 相对 run24f 的唯一部署变量为移除旧臂；A→B 的部署变量为底盘位置。失败详情透传是诊断修改，不改变候选选择。

The instruction is identical, with task parameters of 1.0rad and a 2.0s hold. A/B retain the existing physics, control, perception and oracle configuration. A changes only legacy-arm removal relative to run24f at the deployment level; B then changes base position. Failure-detail forwarding changes diagnostics without changing candidate selection.

## A 轮证据 / Run A Evidence

目录 / Workspace: `out/labutopia-placement-20261119-1847/A-remove-only/`。

- `metadata.json`：2026-11-19 18:49:16 开始，19:02:37 结束，`returncode=1`，任务已失败；此返回码不记作成功。 / Metadata records start and finish times and return code1; the task failed and this is not counted as success.
- 28/28 approach probes available；acquire succeeded。阶段反馈 `artifacts/labutopia/phase-feedback/50b86ddbee92461aaffdb57cc101399d.json` 记录总1791采样、108个lift采样，attach误差峰值 `0.009680901646895916m`。 / All 28 approach probes are available and acquire succeeds; phase feedback records 1791 total samples, including 108 lift samples, and the stated peak attach error.
- 视频 / Video: `artifacts/labutopia/phase-video/752e43f86efa4f94bf9b96a28c4fb223.mp4`，29.816667秒 / seconds。
- 24条倾倒候选详情完整保存于 `placement-summary.json` 与 `acceptance.json`；22条明确为 `panda_link2 overlaps /World/table/surface/mesh`。余下2条只报告 `transport`：`clearance=0.04/0.048, yaw=-π/2, azimuth=0`，未细分原因。源码存在只写stage的关节限位失败形式，但现有证据不足以将这2条确诊为关节限位。 / Full candidate details are retained in the summary and acceptance files. Twenty-two report link2/table collisions; two report only the transport stage. A stage-only joint-limit failure form exists in the code, but the saved evidence does not establish that cause for these two candidates.
- 终态仍持有瓶子，pour/place均未执行。 / The terminal state still holds the bottle; pour and place do not execute.
- 实际抓取候选后缀 `-0`，轴向分支π，切向偏移 `+0.06m`；run24f 为轴向π/2、切向 `−0.06m`。两轮并非相同运动学轨迹或逐位重放。 / The effective candidate suffix is `-0`, with axial branchπ and tangent offset `+0.06m`; run24f used axial branchπ/2 and tangent offset `−0.06m`. These runs are not identical kinematic trajectories or bitwise replays.

## B 轮与无动作检查 / Run B and No-Motion Check

B 目录 / Workspace: `out/labutopia-placement-20261119-1847/B-remove-and-near/`。任务 `task_7b3ca51a7ec34239` 已失败终态，2026-11-19 19:03:58开始，19:16:12结束，`returncode=1`。新 scene revision `labutopia-tabletop-rod-rack-v1:3b3910c4a9344528848b5cdd8653575a:0`。

Run B reaches a failed terminal outcome between the stated start and finish times, with return code1 and the stated fresh scene revision.

- 28/28 approach probes available，但acquire返回 `grasp_object_displaced: object moved before a qualified lift`。反馈共1248条（包含异常结束重复record），lift/grasp_valid/contact_load_valid均为0；倾倒准备、pour、place均未到达，`returned_to_safe_pose=false`、`observation_ready=false`。 / All 28 approach probes are available, but acquire fails on pre-lift displacement. The 1248 feedback records include a repeated exception-ending record; there are zero lift, grasp-valid or bilateral-load-valid samples. Pour preparation, pour and place are never reached, and safe-pose return and observation readiness are false.
- 反馈 / Feedback: `artifacts/labutopia/phase-feedback/b152d2bf3e3943bd8b40376f173538bb.json`。视频 / Video: `artifacts/labutopia/phase-video/a49242a7d8c74e58ac62bd1275c1ba33.mp4`，20.783333秒、1247帧、3840×960 / 20.783333 seconds, 1247 frames, 3840×960。
- 用保存的 `original_return_pose`、`tcp_from_object` 和末帧 `object_pose` 调用生产 `grasp_anchor_drift` / `grasp_pose_errors` 重算：抓取锚点漂移 `0.007132053241597708m ≤ 0.008m`；物体相对初始的完整旋转 `0.08129748240811713rad > 0.08rad`。R05不在 `axial_grip_paths`，没有轴对称豁免。B保存的motion/physics/perception配置与执行后仓库版本逐字节一致。 / Production helper recomputation from the saved original pose, TCP/object transform and final object pose puts anchor drift inside the position tolerance but full object rotation beyond the existing angular tolerance. R05 has no axial-symmetry exemption. Saved motion, physics and perception configurations match the repository versions after execution byte for byte.
- 上述pre-lift旋转不是末帧 `attachment_rotation_error_rad=0.08183650103083709`；两者参考关系不同。末帧左右接触冲量为 `[0, 0.010030197765445337]N·s`，双侧负载无效，不能据28/28探针通过声称已夹稳或可倾倒。 / The pre-lift object rotation differs from the final attachment rotation error because they use different references. Final left/right impulses are `[0, 0.010030197765445337]N·s`, so bilateral load is invalid; available probes do not establish a qualified grip or successful pour.
- B实际候选后缀 `-0`、轴向π、切向+0.06m，与A同一分支；底盘位置改变了IK和实际接触实现。摘要见 `placement-summary.json`，不从该抓取失败推断新位置的倾倒可达或不可达。 / B uses the same candidate suffix, axial branch and tangent as A, while changed base placement changes IK and physical contact. The saved summary documents acquisition failure without establishing whether pouring from the new position is reachable.

A/B视频右侧的固定标签检查视角沿用profile默认 `label_inspection_prim_path`，显示R01；这不代表操作目标为R01。assignment和phase-feedback明确记录R05。本轮保留该既有视角，未修改摄像头配置。

The fixed label-inspection pane on the right of the A/B videos retains the profile's R01 default view. It does not identify the manipulated target: assignments and phase feedback explicitly name R05. Camera configuration is unchanged in this task.

此前真实 Isaac 无动作初始化证据 `out/labutopia-placement-20261119-1847/no-motion.json` 读回底盘 `[-1.0499999523, 0.1800000072, 0.0099999998]`m、臂基 `[-0.7540267110, 0.1806367636, 0.2899999917]`m，旧臂inactive、活动旧臂碰撞体为空、home碰撞检查passed。scene revision为 `labutopia-tabletop-rod-rack-v1:45be9393627949ea9432e094d45fce83:0`。这是frame和home的Provider证据，不能证明完整倾倒或执行。

The actual no-motion initialization reads the stated base and arm-base positions, excludes the legacy arm and its colliders, and passes the home collision check. This is frame and home Provider evidence for the stated revision, not proof of a complete pour route or execution.

## 复现 / Reproduction

以下命令在仓库根目录运行；每次使用新的workspace，保留历史运行。 / Run from the repository root with a new workspace each time, preserving prior runs.

```bash
export OMNI_KIT_ACCEPT_EULA=YES
export PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime
.venv/bin/python -m isaacsim_lab.agent_host \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-ridgebase.json \
  --workspace out/labutopia-placement-rerun-B-NEW \
  --execute '请按可见标签选择 REAGENT E（R05 试剂瓶），将其中的试剂一次性倒入 BEAKER，倾倒时保持瓶口对准 BEAKER 瓶口，完成后将试剂瓶放回原位。倾倒参数由你决定：倾倒角度请在 0.8-1.2 rad 内选择，保持时间 2.0 秒，不要向用户反问，直接执行到任务终态。'
```

A复现使用其已保存的profile和相同指令，换新workspace： / For A, use its saved profile and the same instruction with another new workspace:

```bash
.venv/bin/python -m isaacsim_lab.agent_host \
  --profile out/labutopia-placement-20261119-1847/A-remove-only/profile.json \
  --workspace out/labutopia-placement-rerun-A-NEW \
  --execute '请按可见标签选择 REAGENT E（R05 试剂瓶），将其中的试剂一次性倒入 BEAKER，倾倒时保持瓶口对准 BEAKER 瓶口，完成后将试剂瓶放回原位。倾倒参数由你决定：倾倒角度请在 0.8-1.2 rad 内选择，保持时间 2.0 秒，不要向用户反问，直接执行到任务终态。'
```

这些命令仅执行 Isaac 无液体仿真。观测/准备先于Action，执行继续使用现有fail-closed停止路径；无真实硬件授权或执行。

These commands execute fluid-free Isaac simulation. Observation and preparation precede actions, existing fail-closed stop paths remain active, and no physical hardware is authorized or used.

## 复现元数据与局限 / Metadata and Limits

每轮目录保存 `profile.json`、`station.yaml`、`instruction.txt`、`metadata.json`、`implementation.diff` 和运动/物理/感知/manifest/场景覆盖层副本。基础Git提交 `090df094bf1df7404a33309cf90a8863ba417b23`，分支 `feature/planning-loop`；实现差异和配置副本保存本轮未提交状态。profile仍引用仓库内配置路径，复现前应确认与保存副本一致或显式指向保存副本。

Each run retains profile, station, instruction, metadata, implementation diff and configuration copies. The base Git revision and branch identify the starting code; the diff and copies preserve the uncommitted implementation. Profiles still reference repository configuration paths, so reproduction should check these against the saved copies or explicitly point to the copies.

外部LabUtopia资产基于提交 `2224bb815fedeff91f82021ec661761682f99310`，源scene/config在本轮前已有本地修改。实际 `tabletop_station.usda`、`tabletop_station.yaml`、`ridgeback_franka.usd`、`tracked-assets.diff` 及 `metadata.json` 已保存在 `out/labutopia-placement-20261119-1847/external-scene-snapshot/`；本轮没有修改这些外部源资产，A/B metadata指向该证据。

External LabUtopia assets start from the stated commit with pre-existing local scene/config edits. The external-scene snapshot retains the actual scene, station configuration, robot asset, tracked diff and metadata; this task does not modify the external sources. A/B metadata points to that snapshot.

现行runner没有暴露显式seed，本轮未配置种子，不声称确定性。数据集/训练checkpoint不适用：使用authored LabUtopia场景和simulator-truth oracle。Agent规划、求解分支、接触仿真与环境差异仍可能影响重跑。

The existing runner exposes no explicit seed and none was configured; determinism is not claimed. Dataset and training-checkpoint fields are inapplicable to the authored LabUtopia scene and simulator-truth oracle. Agent planning, solver branches, contact simulation and environment drift can affect reruns.

## 因果与验收 / Causality and Acceptance

- 旧臂确实存在并参与场景碰撞，其移除伴随可用抓取路线选择变化；这说明旧部署含多余碰撞障碍，但不足以证明run24f全由它导致。 / The legacy arm existed as a collision obstacle, and its removal accompanies changed available grasp-route selection; this does not prove it caused the entire run24f failure.
- A明确证明移除旧臂仍不能倾倒，当前22条候选证据指向活动臂link2与桌面碰撞；2条transport-only原因保留未知。 / A establishes that removal alone does not restore pouring, with 22 saved candidates naming the active arm's link2/table collision; two stage-only causes remain unresolved.
- B在新位置先于lift抓取失败，因此没有回答新位置能否倾倒；不能把结果归结为只因距离。A与run24f抓取路线不同，A/B同分支但IK和接触实现改变，需连同候选、路线和物理反馈解释。 / B fails acquisition before lift, so it does not answer new-placement pour reachability or isolate distance as the sole cause. A differs from run24f in route, and A/B share a branch while IK and contact change.
- 契约证据：PAOS集成28 passed，Ruff和diff检查通过。Provider证据：原资产保留旧臂、新场景停用旧臂、真实初始化及home检查通过。仿真执行证据：A抓取成功、倾倒未开始且任务失败；B在lift前因物体旋转超容差失败，未进入倾倒准备。 / Contract evidence: 28 PAOS integration tests and lint/diff checks pass. Provider evidence: source preservation, composed-arm exclusion and actual initialization/home checks. Simulation evidence: A acquires successfully but fails before pouring; B fails on object rotation before lift and never reaches pour preparation.
- 主会话实现复核当前无Blocker/Major发现，所有已识别架构问题均已解决；两轮任务失败如实保留，不作为倾倒成功。 / The primary implementation review currently has no Blocker/Major findings and no unresolved identified architecture issue; both failed task outcomes remain explicit and do not establish successful pouring.

下一步建议先检查新位置抓取时双指对称接触和瓶体旋转，再针对桌面与低臂基高度做无动作路线测量；不盲目继续前移，不放松阈值。本轮完成用户指定的两处部署改动及对照后停止调参。

Recommended follow-up is to inspect bilateral contact symmetry and bottle rotation at the new position, then measure routes against the tabletop and low arm-base height without motion. Further forward shifts or relaxed tolerances are not supported by this comparison. This task stops after the two requested deployment changes and their comparison.
