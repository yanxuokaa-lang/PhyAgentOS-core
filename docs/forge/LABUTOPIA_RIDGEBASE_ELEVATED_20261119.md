# Ridgebase Franka 增高部署 / Elevated Deployment

记录 / Recorded: 2026-11-20，Asia/Shanghai。版本 / Version: v17.8.4（当前候选布局；fresh初始化、路线资格与运行终态证据已补齐，v17.8.3保留为历史候选）。

既有A轮移除桌面旧臂后，24条倾倒路线仍全部失败，22条明确报告活动臂link2撞桌；B轮靠近后在lift前因瓶体旋转超限失败。历史C轮使用0.43m增高布局并最终未完成倾倒。v17.8.3曾记录底盘y=0.10m、臂基约0.82m的候选；当前v17.8.4改为单一的底盘落地、臂基约0.77m、底盘y=0.04m候选，桌面物品的初始位置与操作区域保持原坐标。

After legacy-arm removal, A still rejects all24 pour candidates, including22 explicit live-arm link2/table collisions. B fails before lift on bottle rotation. Historical C used the0.43m elevated layout and still failed to pour. Version17.8.3 recorded a candidate with chassis y=0.10m and arm root near0.82m; the current v17.8.4 candidate uses a grounded chassis, arm root near0.77m and chassis y=0.04m, while preserving tabletop item positions and operation-area coordinates.

C轮（历史0.43m布局）已失败终态：抓取返回成功并持瓶，但持瓶倾倒准备的24个候选全部拒绝，未执行pour或place。该单一布局使抓取越过B轮的lift前失败，C候选中不再出现A轮主导的link2撞桌原因；现有连续IK及腕部/载荷碰撞仍阻止倾倒，不能归因为仅距离过远。v17.8.3候选的fresh无动作检查通过，但持瓶倾倒路线资格未通过，未进入实际pour或place。

C (historical0.43m layout) terminates failed after a successful acquire and a held-pour preparation that rejects all24 candidates. Pour and place do not execute. Acquisition progresses beyond B's pre-lift failure, and C no longer reports A's dominant link2/table failure. Continuous IK and wrist/payload collisions still prevent pouring; the evidence does not isolate excessive distance as the sole cause. For v17.8.3, the fresh no-motion check passes, but held-pour route qualification rejects every candidate before pour or place.

## v17.8.3当前候选 / Current v17.8.3 Candidate

候选来自只读离线端点敏感性扫描：`arm_root=[-0.82,0.10,0.82]m` 是扫描中唯一使保存的实测姿态修正目标进入IK的部署点。该证据只支持部署方向选择，不证明连续路线、夹持接触或实际倾倒成功；fresh无动作检查已通过，但持瓶路线资格失败，按原决策边界停止继续调参并保留失败原因。

The candidate comes from a read-only offline endpoint sensitivity scan: `arm_root=[-0.82,0.10,0.82]m` is the only scanned deployment point that admits the saved measured pose-correction target to IK. This supports placement selection only; it does not establish a continuous route, grasp contact or runtime pouring. The fresh no-motion check passes, but held-pour route qualification fails; the existing decision boundary therefore stops further tuning and retains the failure evidence.

## v17.8.4当前候选与fresh终态 / Current v17.8.4 Candidate and Fresh Terminal Outcome

本轮按此前敏感性分析选择单一部署：底盘世界坐标 `[-1.105,0.04,0.01]m`，安装增量 `.48m`，fresh读回臂基 `[-0.8049764633,0.0400000103,0.7700000405]m`。无动作证据 `out/labutopia-elevated-20261120/v17.8.4-candidate/no-motion.json` 显示 `status=initialized`、`home_collision_check=passed`、`motion_commands=0`、旧Franka未激活且安装柱碰撞启用；这证明部署初态合理，不证明倾倒成功。

Following the prior sensitivity analysis, this run uses one fixed deployment: chassis `[-1.105,0.04,0.01]m`, `.48m` mount elevation increment, and fresh arm-root readback `[-0.8049764633,0.0400000103,0.7700000405]m`. The no-motion evidence at `out/labutopia-elevated-20261120/v17.8.4-candidate/no-motion.json` reports `status=initialized`, `home_collision_check=passed`, `motion_commands=0`, no active legacy Franka and enabled mount-column collision. This establishes a reasonable initial deployment, not a pouring result.

fresh路线资格证据 `out/labutopia-elevated-20261120/v17.8.4-full-run/artifacts/labutopia/readiness/a3079b268c5c4b9fab4aebbdb666279d.json` 选择居中零偏移候选：`125` 步，`kinematic=pass`、`collision=pass`、`workspace=pass`，`pour_yaw=0`、`pour_azimuth=π/2`、lip clearance `.048m`、`same_side_ingress`。资格检查通过，且不应与实际执行结果混写。

The fresh route evidence at `out/labutopia-elevated-20261120/v17.8.4-full-run/artifacts/labutopia/readiness/a3079b268c5c4b9fab4aebbdb666279d.json` selects the centered zero-offset candidate: `125` steps with `kinematic=pass`, `collision=pass` and `workspace=pass`, using `pour_yaw=0`, `pour_azimuth=π/2`, `.048m` lip clearance and `same_side_ingress`. Qualification passes and must remain separate from runtime execution.

完整运行 `out/labutopia-elevated-20261120/v17.8.4-full-run/` 的任务 `task_724bb801fcf742a5` 于2026-11-20 22:31:20至22:50:28（Asia/Shanghai）以return code1失败。R05抓取阶段成功；倾倒反馈 `artifacts/labutopia/phase-feedback/91f6b7a04aff430cbbe75d41d67ba17b.json` 共1653个样本，全部处于transport，错误为 `inverse_kinematics_failed: measured pour-pose correction is unreachable`。最大实测倾角 `0.590846rad`，`qualified_tilt_hold_s=0`、`aligned_hold_s=0`、`process_completed=false`、`transfer_verified=false`，归位未完成且机械臂仍持有R05。

The full run under `out/labutopia-elevated-20261120/v17.8.4-full-run/` for task `task_724bb801fcf742a5` fails from 22:31:20 to 22:50:28 Asia/Shanghai with return code1. R05 acquisition succeeds; the pour feedback contains1653 samples, all in `transport`, and reports `inverse_kinematics_failed: measured pour-pose correction is unreachable`. The measured maximum tilt is `0.590846rad`; `qualified_tilt_hold_s=0`, `aligned_hold_s=0`, `process_completed=false` and `transfer_verified=false`. Return-to-place is incomplete and the robot still holds R05.

视频证据为抓取 `out/labutopia-elevated-20261120/v17.8.4-full-run/artifacts/labutopia/phase-video/ef00745a6da842439479cbbb47fcea78.mp4`（35.2秒）与失败倾倒 `out/labutopia-elevated-20261120/v17.8.4-full-run/artifacts/labutopia/phase-video/aff063945771426c8ac8d9b5f8f620ed.mp4`（27.533秒）。本轮最终结论是：**路线资格检查通过，实际倾倒失败**。现有回执没有逐候选执行态IK残差或失败目标的关节解，因此下一步诊断点应放在transport阶段的实测姿态修正、IK残差/seed连续性和失败边界；不再继续扫描底盘位置或安装高度。

The evidence videos are the acquisition clip `out/labutopia-elevated-20261120/v17.8.4-full-run/artifacts/labutopia/phase-video/ef00745a6da842439479cbbb47fcea78.mp4` (35.2s) and the failed-pour clip `out/labutopia-elevated-20261120/v17.8.4-full-run/artifacts/labutopia/phase-video/aff063945771426c8ac8d9b5f8f620ed.mp4` (27.533s). The final conclusion is: **route qualification passed; actual pouring failed**. The saved receipts do not contain per-candidate execution-time IK residuals or failed-target joint solutions, so the next diagnostic point is the transport-stage measured-pose correction, IK residual/seed continuity and failure boundary; stop scanning chassis placement or mount height.

## v17.8.4 transport姿态修正无动作诊断 / v17.8.4 Transport Pose-Correction No-Motion Diagnosis

诊断脚本 out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/diagnose-transport-correction.py 读取fresh readiness、历史1653条transport反馈和保存profile，在独立Isaac初始化中按执行步数重建实测姿态修正目标。结果为 diagnose-transport-correction.json，启动/退出日志为同目录 diagnose-transport-correction.log。反馈包含一个重复终态记录：1652条动作样本被125个路径点精确消费，剩余0；失败重建于路径点索引61（从0计），对应反馈样本1651。重建边界的TCP FK与已保存反馈完全一致，初始 tcp_from_object 误差为0。运行期间 motion_commands=0、reset关节未变、仿真时间未变；未执行碰撞检查或动作资格化。

The diagnostic reads fresh readiness, all1653 saved transport feedback records and the saved profile, then reconstructs measured-pose correction targets by execution-step accounting in a separate Isaac initialization. Results are in diagnose-transport-correction.json, with startup/shutdown output in the adjacent diagnose-transport-correction.log. One terminal record is duplicated: 1652 command samples are exactly consumed by125 route points with zero remainder. Reconstructed failure is at zero-based route point61 and feedback sample1651; saved and fresh TCP FK match exactly at that boundary, and initial tcp_from_object error is0. The diagnostic issued zero motion commands, left reset joints and simulation time unchanged, and performed no collision or execution qualification.

复现命令（输出写入独立诊断目录）：OMNI_KIT_ACCEPT_EULA=YES PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime /home/yanxu/miniconda3/envs/labutopia/bin/python out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/diagnose-transport-correction.py > out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/diagnose-transport-correction.log 2>&1

Reproduction command (writes output to the separate diagnostic directory): OMNI_KIT_ACCEPT_EULA=YES PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime /home/yanxu/miniconda3/envs/labutopia/bin/python out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/diagnose-transport-correction.py > out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/diagnose-transport-correction.log 2>&1

失败点的目标位置残差为0.000578m，低于现行0.002m容差；完整姿态角误差为0.022648rad，高于现行0.02rad。planned-point seed也失败，其邻近局部IK对照残差为0.001275m与0.051834rad；两种局部IK结果均未显示关节限位越界，current seed解的最小限位余量为0.701991rad。profile原有最大waypoint关节变化为0.5rad。

At the failing target, position residual is0.000578m, within the existing0.002m tolerance, while full-pose angular residual is0.022648rad, above the existing0.02rad tolerance. The planned-point seed also fails; its local IK comparison residual is0.001275m and0.051834rad. Neither local IK result indicates a joint-limit violation; the current-seed solution retains0.701991rad minimum limit margin. The profile's existing maximum waypoint joint delta is0.5rad.

同一transport反馈中，grasp_valid首次在样本150、37.718752s变为false；当时attachment位置误差0.192mm、旋转误差0.080425rad（超过0.08rad容差），contact_load_valid与contact_manifold_valid仍为true。此后1503/1503条样本持续grasp_valid=false，没有恢复；失败边界样本1651的attachment位置误差为1.121mm、旋转误差0.409201rad、物体原点偏移18.659mm，而接触负载与接触面标记仍为true。因而局部IK失败不是唯一未解决现象；执行中的持瓶姿态在进入该边界前已长期未满足grasp_valid，但当前证据不能判定物理打滑、目标关系变化或模拟接触模型哪一项是原因。

In the same transport feedback, grasp_valid first becomes false at sample150/time37.718752s. Attachment position error is0.192mm and rotation error is0.080425rad, above the0.08rad tolerance, while contact_load_valid and contact_manifold_valid remain true. All following1503/1503 samples remain grasp_valid=false with no recovery. At failure-boundary sample1651, attachment position error is1.121mm, rotation error is0.409201rad and object-origin offset is18.659mm, while both contact/load indicators still read true. Therefore local IK failure is not the only unresolved observation: the held pose has long failed grasp_valid before reaching this boundary. Current evidence does not distinguish physical slip, changing target relation or simulator contact-model effects.

以相同失败边界目标和当前关节为seed，现有Lula full-pose solver返回一组限位内候选：位置误差0.000158m、角误差0.001542rad、关节变化0.080606rad、最小限位余量0.674910rad，均满足对应现行数值限制。邻近目标的对照也出现局部求解器失败而Lula求解器成功。此结果支持“当前局部IK求解未收敛到合格姿态”的诊断，不证明全路径可达：新解尚未验证连续插值、桌面/支柱/烧杯/瓶体碰撞、实时夹持稳定性或执行后反馈。

For the same failure-boundary target and current joint seed, the existing Lula full-pose solver returns an in-limit candidate with0.000158m position error,0.001542rad angular error,0.080606rad joint change and0.674910rad minimum joint-limit margin; each is within its corresponding existing numeric limit. Neighbor comparisons also show cases where local IK fails while Lula succeeds. This supports a diagnosis that the current local IK solve fails to converge to a qualified pose. It does not prove full-route reachability: the candidate has not been checked for continuous interpolation, table/mount/beaker/bottle collisions, live grasp stability or post-execution feedback.

### 持瓶关系漂移复核 / Held-object Relation Drift Review

对采集与倾倒两个已保存phase-feedback逐样本复核。acquire阶段结束于35.202s，status为succeeded；lift的117条记录中，77条grasp_valid=false，但117/117条contact_load_valid与contact_manifold_valid均为true。末帧TCP抓取锚点偏移9.131mm，超过现行8mm抓取位置值；旋转误差为0.012789rad。源码中的采集终态以双侧接触和抬升距离判定carried/lifted，因此phase成功不等于整个lift期间的固定TCP-object关系都满足grasp_valid。

The saved acquisition and pour feedback were reviewed sample by sample. Acquisition ends at35.202s with status=succeeded. During lift,77/117 records have grasp_valid=false, while contact_load_valid and contact_manifold_valid remain true in117/117. The terminal TCP grasp-anchor displacement is9.131mm, above the existing8mm grasp-position value; rotation error is0.012789rad. Source semantics determine final carried/lifted from bilateral contact and lift distance, so a successful phase does not establish that the fixed TCP/object relation remained within grasp_valid throughout lift.

Pour feedback uses a freshly measured starting relation: at sample0 its rotation error is0.000628rad and anchor displacement is0.097mm. The relation then rotates while task tilt remains near vertical: at sample150/time37.718752s the relation rotation error is0.080425rad, crossing the existing0.08rad threshold, while anchor displacement is0.192mm and task tilt is0.011209rad. At sample1000 the relation rotation error reaches0.365396rad while task tilt is0.016542rad. At failure-boundary sample1651, relation rotation error is0.409201rad and anchor displacement is1.121mm; the bottle-origin offset is18.659mm. Thus the large bottle-origin offset is not an18.659mm translation at the grasp anchor: the measured object rotates about/near a substantially steadier grasp region. The first threshold crossing occurs before the intended pour tilt.

倾倒phase中的夹爪实测开度总和保持约35.49–35.89mm，目标总和约35.49mm；末帧左右指目标偏差约0.066mm和0.002mm。两侧接触冲量均保持非零，1653/1653条记录的接触标记都为true。源码里的contact_load_valid要求当前control interval中两个传感器各自都有非零接触冲量，并有新鲜双侧接触面；它不检查抗滑摩擦裕量或夹持力矩。grasp_valid还要求TCP抓取锚点位置误差不超过8mm且旋转误差不超过0.08rad，所以样本150起false由旋转项越界解释，非接触丢失。

During the pour phase, the measured total finger opening stays around35.49–35.89mm against a target total of about35.49mm; at the final sample the left/right finger-target deviations are about0.066mm and0.002mm. Both sides retain nonzero contact impulse, and all1653 records keep both contact flags true. In source, contact_load_valid requires nonzero contact impulse from each sensor within the current control interval and fresh bilateral manifolds; it does not check anti-slip friction margin or grasp torque. grasp_valid additionally requires TCP grasp-anchor position error at or below8mm and rotation error at or below0.08rad, so the sample150 transition to false is explained by the rotation threshold, not loss of contact.

结论限于已记录的仿真状态：瓶体相对TCP出现明显转动/接触内位移，而指节开度和双侧接触仍持续；现有回执不能区分接触几何、摩擦/力矩不足、物理模型效应或观测位姿映射误差。attached阶段的中止条件检查双侧接触是否消失，不以grasp_valid为中止条件；因此该漂移可在反馈持续报告grasp_valid=false时继续累积，并改变后续实测姿态修正目标。它解释了为什么单看接触标记会漏掉关系变化，但不能单独证明具体物理根因，也不支持放宽阈值或把Lula单点解视为路线/夹持合格。

Conclusion is limited to the recorded simulation state: the bottle rotates/moves within the TCP grasp relation while finger opening and bilateral contact persist. The saved evidence cannot distinguish contact geometry, insufficient friction/torque, physics-model effects or observed-pose mapping error. The attached-stage stop condition checks for loss of bilateral contact rather than grasp_valid; the drift can therefore accumulate while feedback reports grasp_valid=false and alter subsequent measured-pose correction targets. This explains why contact flags alone miss relation change, but does not establish a specific physical root cause, justify loosening thresholds or qualify the single Lula solution as a safe route or stable grasp.

复现命令（仅读取已保存JSON，不启动Isaac）：python3 -m py_compile out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/analyze-held-object-relation-drift.py && python3 out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/analyze-held-object-relation-drift.py；逐样本结果写入同目录analyze-held-object-relation-drift.json。

Reproduction command (reads saved JSON only; does not start Isaac): python3 -m py_compile out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/analyze-held-object-relation-drift.py && python3 out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/analyze-held-object-relation-drift.py; per-sample results are written to analyze-held-object-relation-drift.json in the same directory.

### Lula失败边界路线后缀资格复核 / Lula Failure-Boundary Route-Suffix Qualification

独立Isaac诊断从保存的sample1651实测关节、TCP姿态和固定TCP-object关系开始，检查零基waypoint61至124共64个后缀点。R05点云、sidecar和标定均对应readiness/route保存的scene revision `labutopia-tabletop-rod-rack-v1:da14ce1a64164cdda77fddb7cb74f728:1`；诊断场景为同一profile的独立初始化，revision为`labutopia-tabletop-rod-rack-v1:ff6157a897f0438bb0eb10491cb67fbd:0`。脚本在本地隔离artifact store中绑定原始点云，使用生产`world_from_camera`和保存的`observed_model_pose`/`body_from_observed`关系。1214个有限点经现有`observed_point_boxes`生成9个载荷碰撞盒；该生产函数只包络观测表面，不重建隐藏网格。

The independent Isaac diagnostic starts from the saved sample 1651 joints, TCP pose and fixed TCP/object relation. It prepares a 64-waypoint suffix from zero-based waypoint 61 through 124. The R05 point cloud, sidecar and calibration share the readiness/route scene revision `labutopia-tabletop-rod-rack-v1:da14ce1a64164cdda77fddb7cb74f728:1`; the diagnostic initializes a separate scene from the same profile at revision `labutopia-tabletop-rod-rack-v1:ff6157a897f0438bb0eb10491cb67fbd:0`. It binds the source cloud in a local isolated artifact store using production `world_from_camera` and the saved `observed_model_pose`/`body_from_observed` relation. The existing `observed_point_boxes` function converts 1,214 finite points into 9 payload collision boxes that bound observed surfaces without reconstructing hidden mesh.

资格检查在进入首个`process`目标（零基waypoint71）的插值过程中以`payload_collision`拒绝：载荷盒与`/World/OperationArea/TargetBeaker/Model/mesh`重叠。报告的碰撞盒中心为`[-0.1328163,-0.0076964,0.8335190]m`，半尺寸为`[0.0353995,0.0353997,0.0073625]m`（包含现行3mm margin）。截至拒绝共进行9992次overlap查询，local-IK fallback为0；64个后缀点没有全部完成，`qualified_waypoint_count`未产生。因此，现有证据是生产观测表面载荷盒与烧杯碰撞查询重叠，不能单独判定完整路线已检查完毕或真实瓶体与烧杯已发生物理穿透。

Qualification rejects during interpolation toward the first `process` target, zero-based waypoint 71, with `payload_collision`: a payload box overlaps `/World/OperationArea/TargetBeaker/Model/mesh`. The reported box center is `[-0.1328163,-0.0076964,0.8335190]m`, with half-extents `[0.0353995,0.0353997,0.0073625]m`, including the existing 3 mm margin. The run performs 9,992 overlap queries and makes 0 local-IK fallback calls before rejection. The 64-waypoint suffix was not fully checked and `qualified_waypoint_count` remains unset. The evidence records an overlap between the production observed-surface payload boxes and the beaker collision query; it does not establish a completed route check or physical bottle/beaker interpenetration.

诊断期间`simulation_steps=0`、`motion_commands=0`，初始化关节与仿真时间保持不变；底盘/安装布局、生产源码和全部阈值未改。复现命令：

During diagnosis, `simulation_steps=0` and `motion_commands=0`; initialized joints and simulation time remain unchanged. Chassis/mount placement, production source and all thresholds remain unchanged. Reproduce with:

```bash
python3 -m py_compile out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/qualify-lula-route-suffix.py
OMNI_KIT_ACCEPT_EULA=YES PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime /home/yanxu/miniconda3/envs/labutopia/bin/python out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/qualify-lula-route-suffix.py > out/labutopia-elevated-20261120/v17.8.4-transport-diagnostic-20261121/qualify-lula-route-suffix.log 2>&1
```

### 下一步决策 / Next Decision

保留当前机座坐标、高度、桌面布局和全部阈值。静态复核已确认waypoint71命中的box0为最低观测表面层，并解释了其局部半尺寸与烧杯世界AABB不可直接逐轴比较；定向盒世界Z投影最大可达约50.60mm，高于失败中心至烧杯mesh上缘的30.73mm间隔。因此这两份证据不构成几何矛盾，但没有失败瞬间的盒姿态及cook后凸分解数据，仍不能判断实际接触或保守碰撞近似。下一步建议只读检查cook后凸分解与失败盒姿态；澄清并重新通过fresh资格检查前不执行机械臂动作。持瓶关系漂移仍是独立未决问题。

Retain the current chassis position, mount height, tabletop layout and all thresholds. Static review confirms waypoint71 hit box0 is the lowest observed-surface slab and explains why its local half-extents cannot be compared axis by axis with the beaker world AABB; its oriented world-Z projection can reach about50.60mm, above the30.73mm gap from the reported center to the beaker mesh top. These records therefore do not contradict each other, but the missing hit-time box orientation and cooked convex decomposition leave actual contact versus conservative collision approximation unresolved. Next, read-only inspect the cooked convex decomposition and failure-box pose; keep arm motion disabled until clarified and a fresh qualification passes. Held-object relation drift remains a separate unresolved issue.

### 静态几何与OBB复核 / Static Geometry and OBB Review

使用与route相同的R05点云、标定和`observed_model_pose`，按生产`world_from_camera`及`observed_point_boxes`重算：1214个点的局部范围为`[-0.0358518,-0.0308453,-0.0067502]`至`[0.0289472,0.0339542,0.1088665]m`，生成9个沿局部Z分层的观测表面盒。waypoint71失败盒对应最低层（box0）；其局部中心约`[-0.003452,0.001554,-0.002388]m`，含既有3mm margin的半尺寸为`[0.0353995,0.0353997,0.0073625]m`。这些盒是填充长方体包络，不是瓶体网格或中空实体重建。

The same R05 cloud, calibration and route `observed_model_pose` were transformed with production `world_from_camera` and `observed_point_boxes`: 1,214 points span local bounds `[-0.0358518,-0.0308453,-0.0067502]` to `[0.0289472,0.0339542,0.1088665]m`, forming 9 observed-surface boxes sliced along local Z. The waypoint71 failure box is the lowest slab (box0), with local center about `[-0.003452,0.001554,-0.002388]m` and half-extents `[0.0353995,0.0353997,0.0073625]m` including the existing 3 mm margin. These are filled cuboid bounds, not a bottle mesh or reconstruction of its hollow interior.

静态组合读取的目标烧杯mesh有1698个点、3408个面，碰撞启用且`physics:approximation=convexDecomposition`；世界包围盒为`[-0.112462,-0.030133,0.712386]`至`[-0.047538,0.030133,0.802787]m`。mesh缩放为`[0.0004,0.0005,0.0004]`，保存的PhysX日志还出现该prim的`ScaleOrientation is not supported for rigid bodies`警告；这提示 cooked collider 需要单独核对，但本身不能证明碰撞体错误。

The composed target-beaker mesh has 1,698 points and 3,408 faces, with collision enabled and `physics:approximation=convexDecomposition`; its world bounds are `[-0.112462,-0.030133,0.712386]` to `[-0.047538,0.030133,0.802787]m`. The mesh scale is `[0.0004,0.0005,0.0004]`, and the saved PhysX log warns `ScaleOrientation is not supported for rigid bodies` on this prim. This motivates separate inspection of the cooked collider but does not establish that the collider is wrong.

失败记录中的半尺寸是定向盒局部半尺寸，不能直接与世界Z轴包围盒上界比较。该盒局部半尺寸向量的长度（任何方向投影半径的上界）约为50.60mm；失败中心z=`0.833519m`比烧杯mesh世界Z上界`0.802787m`高30.73mm。因此某些盒姿态会与mesh上缘高度相交，但失败JSON未保存命中瞬间的完整盒旋转，不能从现有文件重建精确世界AABB或独立复算该次PhysX overlap。

The reported half-extents belong to an oriented box and cannot be compared directly with the beaker's world-Z AABB. The norm of this box's local half-extent vector, an upper bound on its projected half-radius in any direction, is about50.60mm; its reported center z=`0.833519m` is30.73mm above the beaker mesh world-Z upper bound at`0.802787m`. Some orientations can therefore intersect the mesh's upper-bound height, but the failure JSON omits the full box rotation at the hit, preventing reconstruction of its exact world AABB or independent replay of the PhysX overlap.

结论仍限于生产观测表面长方体的overlap查询与烧杯碰撞mesh相交。盒体填充、杯体凹形几何及`convexDecomposition`都可能令保守资格查询比真实瓶体表面更宽；现有证据仍不能区分真实瓶身/杯沿接触与包络或cook近似导致的拒绝，也不证明发生物理穿透。独立的持瓶关系漂移结论不变。scene根USDA未声明`metersPerUnit`/`upAxis`，其subLayer `tabletop_station.usda`声明1m/Z-up；直接`Usd.Stage.Open`根层时得到USD fallback `.01m`/Y-up，而诊断初始化传入`World(stage_units_in_meters=1.0)`。保存结果未记录运行时合成up-axis，因此这个静态fallback差异不是已证实的运行时坐标错误或碰撞根因。下一步若继续，应只读检查命中时实际cooked凸分解与定向盒姿态，再决定是否调整process路线或几何输入；保持布局、阈值和运动代码不变。

The conclusion remains limited to an overlap query between production observed-surface cuboids and the beaker collision mesh. Filled boxes, the vessel's concavity and `convexDecomposition` can make conservative qualification broader than the actual bottle surface. Existing evidence cannot distinguish physical bottle/rim contact from rejection caused by the envelope or cooked approximation, and does not prove physical interpenetration. The separate held-object relation-drift finding is unchanged. The scene root USDA does not author `metersPerUnit`/`upAxis`, while its `tabletop_station.usda` sublayer authors 1 m/Z-up; directly opening the root with `Usd.Stage.Open` returns USD fallback `.01m`/Y-up, whereas diagnostic initialization passes `World(stage_units_in_meters=1.0)`. The saved result does not record the runtime composed up-axis, so the static fallback difference is not an established runtime frame error or collision cause. If work continues, inspect the actual cooked convex decomposition and oriented-box pose at the hit without motion, then decide whether process-route or geometry inputs need changes; retain placement, thresholds and motion code.

## 单一布局 / Fixed Layout

| 项目 / Item | 历史C布局 / Historical C | v17.8.3候选 / Candidate | v17.8.4候选 / Candidate |
|---|---|---|---|
| 底盘世界坐标 / Chassis world position | [-1.12,.18,.01]m | [-1.12,.10,.01]m | [-1.105,.04,.01]m |
| 名义臂基世界坐标 / Nominal arm-root world position | [-.82,.18,.72]m | [-.82,.10,.82]m | [-.805,.04,.77]m |
| 手臂尺寸 / Arm scale | 1 | 1 | 1 |
| 安装柱 / Elevation column | 0.12×0.12×0.43m | 0.12×0.12×0.53m | 0.12×0.12×0.48m |
| 柱质量、COM / Mount mass, local COM | 6kg; [.3,0,.215]m | 6kg; [.3,0,.265]m | 6kg; [.3,0,.24]m |
| 柱主惯量 / Mount diagonal inertia | [.09965,.09965,.0144]kg·m² | [.14765,.14765,.0144]kg·m² | [.1224,.1224,.0144]kg·m² |

v17.8.4候选的桌面AABB仍为z=[.6973860684,.7123860691]m；fresh读回臂基高出桌面约57.614mm。柱世界AABB为x[-.8649764,-.7449764]、y[-.02,.10]、z[.29,.77]m，与桌子xmin=-.7350872574m保持约9.889mm水平间隔。R05与烧杯的当前目标距离不沿用历史C数值，已由fresh路线证据重新绑定。

For v17.8.4, the tabletop remains at z=[.6973860684,.7123860691]m and the fresh arm-root readback is about57.614mm above its top. The column bounds are x[-.8649764,-.7449764], y[-.02,.10], z[.29,.77]m, leaving about9.889mm horizontal clearance to table xmin=-.7350872574m. Current R05 and beaker target distances are rebound from fresh route evidence rather than reused from historical C.

`labutopia-ridgebase-elevated.usda`引用原`ridgeback_franka.usd`的`panda_mobile`，不改外部原资产。v17.8.4候选将全部12个臂/手/手指/endeffector刚体平移z+.48m，安装节点原位，安装关节localPos0改为[.3,0,.48]；其余关节局部框架及底盘变换保留。stage明确以米为单位、Z朝上。

The wrapper references the original robot without editing it, raises all12 arm/hand/finger/end-effector bodies by.48m for v17.8.4, retains the mounting body's pose and updates the mounting joint's localPos0. Other joint frames and chassis transforms remain intact; stage units are meters with Z up.

## 离线计算 / Offline Calculation

证据 / Evidence: `out/labutopia-elevated-20261119/offline-placement-analysis.py/.json/.log`。

- 生产URDF与Lula spheres；七关节有界least-squares，12个初始种子，随机种子20261119。A轮真实TCP/joints首中末帧FK对照最大位置误差24.0067µm、角度约5.16e-8rad。 / Production URDF and Lula spheres, bounded seven-joint least-squares with12 starting seeds and RNG seed20261119. FK matches historical first/middle/final TCP observations within24.0067µm and about5.16e-8rad.
- 八个抓取对称分支，五个抓取与6cm抬升端点数值可达。24个倾倒候选中四个全部端点数值可达，两个的各端点均找到桌/柱余量≥现有3mm的分支：yaw=-π/2、azimuth=0、lip clearance=.04/.048m。所选端点分支最小桌/柱余量57.6135mm，最小关节限位余量.1807476rad。 / Five of eight grasp variants reach both grasp and6cm-lift endpoints numerically. Four of24 pour candidates reach every endpoint; two have endpoint branches with at least the existing3mm table/column margin, at yaw=-π/2, azimuth0 and clearance.04/.048m. Minimum selected-branch clearance is57.6135mm and joint-limit margin.1807476rad.
- 主会话起初要求的第二clearance=.078m超出现行profile的.05-.002=.048m限制，分析已纠正并重算；运行时阈值未变。 / The caller's initially requested.078m clearance exceeds the existing.048m allowance; the analysis specification was corrected and recomputed without changing runtime thresholds.

只计算独立端点，未证明连续路径、自碰撞、载荷、其他桌面物体或夹取接触合格；使用历史feature与实测attachment仅作部署敏感性输入。数值不收敛也不等于几何不可达。v17.8.3已fresh reset并重新观测/绑定/准备，完整持瓶路线资格检查拒绝了全部60个倾倒候选；离线端点可达不等于连续路径合格。

Independent endpoint IK omits path interpolation, self collision, payload, other tabletop items and grasp contact. Historical feature and attachment inputs support placement sensitivity only; numerical nonconvergence does not prove impossibility. The v17.8.3 run uses a fresh reset, observation, binding and preparation; complete held-pour qualification rejects all60 candidates. Reachable independent endpoints do not establish a qualified continuous path.

## 所有权与碰撞 / Ownership and Collision

通用domain、公共Tool/AgentLoop不变；部署资产和PhysX碰撞查询属于Isaac Adapter，机制可通过profile替换。WorkerSession拥有场景及reset/revision，Runtime继续拥有取消、结算与恢复；旧revision的preparation不能用于本次执行。

Generic domain semantics and public Tool/AgentLoop contracts remain unchanged. Deployment assets and PhysX queries belong to the Isaac Adapter and can be replaced through the profile. WorkerSession owns scene/reset/revision; Runtime owns cancellation, settlement and recovery. Previous-revision preparation cannot authorize this execution.

既有代码忽略整个robot子树，会同时隐藏新柱。现在仅让`mount_collision_paths`中明确列出的内部碰撞体参与sphere、finger、payload检查，保留link0安装连接的既有exact-path豁免；其他碰撞/工作区/速度/接触/容差原值保留。motion配置相对于oracle仅多一个柱路径。

The previous robot-subtree exemption would hide the new column. Explicit internal mount colliders now participate in sphere, finger and payload checks, preserving the existing exact-path link0 connection exemption. The motion config differs from oracle only by the added column path; existing safety parameters apply.

## 验证与复现 / Validation and Reproduction

```bash
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py \
  examples/forge-adapters/isaacsim_lab/tests/test_ridgebase_elevated.py -q

.venv/bin/python out/labutopia-elevated-20261119/offline-placement-analysis.py

OMNI_KIT_ACCEPT_EULA=YES /home/yanxu/miniconda3/envs/labutopia/bin/python \
  out/labutopia-elevated-20261119/no-motion-check.py

# 历史v17.8.3候选复现命令；不代表当前v17.8.4结果 / Historical v17.8.3 candidate reproduction; does not represent the current v17.8.4 result:
.venv/bin/python out/labutopia-elevated-20261119/run-elevated.py \
  --workspace out/labutopia-elevated-20261119/C-elevated-NEW

# 只抽取历史v17.8.3已落盘结果，不运行仿真 / Extract the persisted historical v17.8.3 result without simulation:
.venv/bin/python out/labutopia-elevated-20261119/summarize-run.py \
  --workspace out/labutopia-elevated-20261119/C-elevated
```

当前v17.8.4代码与配置回归测试206 passed：真实`_collisions`用stub PhysX覆盖link2、finger、payload撞柱拒绝及link0连接豁免；USD组合验证全部刚体平移、关节锚、底盘、柱碰撞/质量/惯量/单位，配置验证除mount路径外完全相等。未安装pxr或原外部资产时仅跳过USD集成测试，纯配置测试仍执行。桌面布局逐字比较记录于`deployment-diff-evidence.json`。

The current v17.8.4 code and configuration regression command passes206 tests, exercising actual collision logic and no-motion USD composition. USD integrations skip when pxr/source assets are unavailable; pure configuration checks still run. Exact unchanged tabletop/layout evidence is saved separately in `deployment-diff-evidence.json`.

Launcher创建新workspace并保存profile、各配置及USD覆盖层、指令、Git差异、commit/branch、命令、起止时间和returncode。完整任务参数沿用原R05→BEAKER倾倒并放回；实际求解/接触仿真没有显式seed，不声称确定性。数据集/训练checkpoint不适用。外部资产源及已有快照在metadata记录。仿真停止仍使用原fail-closed路径；此任务没有真实硬件执行。

The launcher preserves fresh workspace inputs, Git/config provenance, command and terminal metadata. The task retains R05-to-beaker pouring and return, with no explicit seed for planning/contact simulation and no determinism claim. Dataset/checkpoint fields are inapplicable. Existing fail-closed simulation stop behavior applies; no physical hardware executes.

## 历史C轮初始化及运行状态 / Historical C Initialization and Run Status

以下`no-motion.json`是历史C轮0.43m布局的fresh读回：revision `labutopia-tabletop-rod-rack-v1:2faca503a5de4b20bc3e3a4ea8b08e03:0`，actual armroot=[-.8199764490,.1800000221,.7199999690]m；柱世界AABB=[[-.8799765223,.1200000209,.2899999881],[-.7599765188,.2400000244,.7199999952]]m。柱碰撞启用；旧臂inactive、活动旧臂碰撞体为空、home_collision_check=passed、读回期间关节不变、manipulation commands=0。v17.8.3候选的fresh读回见下方独立证据。

The following no-motion evidence is a fresh readback of the historical C0.43m layout: it confirms the stated arm root and column bounds, enabled column collision, no active legacy arm/colliders, a passed home collision check and unchanged joints during readback, with zero manipulation commands. The v17.8.3 candidate has a separate fresh readback below. Finger opening and existing world-joint frame differences are not reported as zero.

主会话核对外部原robot USD、tabletop scene USDA、tabletop_station.yaml与A/B既有external-scene-snapshot逐字节相等；当前station的layout之后全部文本与HEAD逐字一致，motion JSON移除mount_collision_paths后与oracle逐值相等。主会话review已修复临时文件测试依赖与USD单位问题，当前无其余Major。上述历史C的首次no-motion因script路径未加入repo root而在Backend导入前停止，修正后retry完成；首轮日志保留，不记作通过。当前v17.8.3代码/配置回归为206 passed，fresh候选的初始检查和持瓶资格结果见下方。

The primary confirms bytewise equality of external robot, scene and station assets against the earlier A/B snapshot, exact unchanged station layout text and complete equality of motion values after excluding mount_collision_paths. Review resolved the temporary-file test dependency and USD unit issues, with no other outstanding Major finding. Initial import-path/test-harness failures are retained and corrected; the current code/configuration regression rerun passes206 tests, while the fresh initialization and held-pour qualification outcomes are recorded below.

## Fresh v17.8.3初始化与路线资格 / Fresh v17.8.3 Initialization and Route Qualification

无动作证据 `out/labutopia-elevated-20261120/no-motion.json`：生产 Backend fresh 初始化 `status=initialized`，`home_collision_check=passed`，`old_franka_active=false`，`active_legacy_colliders=[]`，`joints_unchanged_during_checks=true`，`motion_commands=0`。实测底盘世界坐标为 `[-1.1200000048,0.1000000015,0.0099999998]m`，臂基为 `[-0.8199764490,0.1000000164,0.8199999928]m`；安装柱世界AABB为 `[[-0.8799765223,0.0400000152,0.2900000358],[-0.7599765188,0.1600000187,0.8200000072]]m`，柱碰撞启用。该证据证明部署初态和home检查通过，不证明完整倾倒路线。

Fresh no-motion evidence in `out/labutopia-elevated-20261120/no-motion.json` shows production Backend initialization with `status=initialized`, `home_collision_check=passed`, `old_franka_active=false`, no active legacy colliders, unchanged joints during checks, and zero manipulation commands. The measured chassis is `[-1.1200000048,0.1000000015,0.0099999998]m`, the arm root is `[-0.8199764490,0.1000000164,0.8199999928]m`, and the enabled column bounds are `[[-0.8799765223,0.0400000152,0.2900000358],[-0.7599765188,0.1600000187,0.8200000072]]m`. This proves deployment initialization and the home check, not a complete pour route.

运行证据来自 `out/labutopia-elevated-20261120/v17.8.3-full-run/`：任务 `task_1ec4c496cb464524` 于2026-11-20 17:23:02至17:54:30（Asia/Shanghai）以return code1失败。`object.acquire`成功并进入`possession_state=holding`；随后`manipulation.prepare_held=unavailable`，错误为`pour_route_unavailable`。60条候选全部拒绝；下表只统计每条候选的首个报告原因，完整detail仍保存在`acceptance.json`与`placement-summary.json`。

The runtime evidence is under `out/labutopia-elevated-20261120/v17.8.3-full-run/`: task `task_1ec4c496cb464524` fails from 17:23:02 to 17:54:30 Asia/Shanghai with return code1. `object.acquire` succeeds and reaches `possession_state=holding`; `manipulation.prepare_held` then returns unavailable with `pour_route_unavailable`. All60 candidates are rejected. The table counts each candidate's first reported reason; complete details remain in `acceptance.json` and `placement-summary.json`.

| 各候选首个报告拒绝原因 / First reported rejection per candidate | 数量 / Count |
|---|---:|
| transport阶段无解 / No solution in transport | 25 |
| transport阶段IK连续性/关节跳变超限 / Transport IK continuity or joint-delta rejection | 15 |
| process阶段 `panda_hand` 碰撞 TargetBeaker / Process `panda_hand`–TargetBeaker collision | 9 |
| process阶段 `panda_link6` 碰撞桌面 / Process `panda_link6`–table collision | 5 |
| process阶段 payload 碰撞 TargetBeaker / Process payload–TargetBeaker collision | 5 |
| process阶段 finger 碰撞 TargetBeaker / Process finger–TargetBeaker collision | 1 |
| 总计 / Total | 60 |

没有`pour`或`place`阶段反馈；任务在held路线准备阶段终止，因此本轮没有进入实际倾倒，不能把视频中的抓取/持瓶片段解释为倾倒成功。视频为 `out/labutopia-elevated-20261120/v17.8.3-full-run/artifacts/labutopia/phase-video/7dd524eaa9f14e91ab4dc5080d16dbf2.mp4`，`ffprobe`为32.066667秒、1924帧、3840×960、41629502 bytes。

No `pour` or `place` phase feedback exists. The task stops during held-route preparation, so this run does not enter actual pouring and the acquisition/holding footage is not evidence of pour success. The video is `out/labutopia-elevated-20261120/v17.8.3-full-run/artifacts/labutopia/phase-video/7dd524eaa9f14e91ab4dc5080d16dbf2.mp4`; `ffprobe` reports 32.066667 seconds, 1924 frames, 3840×960 and41629502 bytes.

本轮决策：fresh部署初态与home碰撞检查通过，抓取成功，但完整持瓶倾倒路线资格失败，实际倾倒未执行。按既有决策边界停止继续调整高度、位置或阈值；不把离线端点可达、无动作检查或抓取成功升级为倾倒成功证据。

Decision: fresh deployment initialization and the home collision check pass, acquisition succeeds, but complete held-pour route qualification fails and actual pouring is not executed. Under the existing decision boundary, stop further height, placement or threshold tuning; endpoint reachability, no-motion checks and acquisition success do not establish pouring success.

## C轮完整终态 / C Terminal Outcome

目录 / Workspace: `out/labutopia-elevated-20261119/C-elevated/`。任务 / Task: `task_535f6c998fb04d52`，状态 / Status: **failed**。metadata记录2026-11-19 20:12:24.275076至20:28:19.962926（Asia/Shanghai），returncode=1；不是倾倒成功。

Metadata records the stated start/finish times and return code1. The task fails after acquisition; pouring is not completed.

- 28/28 approach probes available；`object.acquire=succeeded`，`possession_state=holding`，new revision=`labutopia-tabletop-rod-rack-v1:087c1ba6869a4d73825e4096ee6ddefd:1`。候选`candidate://simulator-truth-R05/af325f880663461697740f87b1dca780-0`，轴向π、approach=.18m、staging backoff=.08m、tangent=+.06m、transit clearance=.04m。 / All28 probes are available and acquisition succeeds with holding possession and the stated new revision, candidate and route parameters.
- 反馈`artifacts/labutopia/phase-feedback/1cb8383e4ab8467db70bcf71d3f1bddc.json`含2139样本，113个lift，其中42个lift样本grasp_valid；全部阶段合计79个grasp_valid、150个contact_load_valid。lift attachment位置误差峰值=.009314366924203562m（9.314366924mm）。 / The feedback contains2139 samples, including113 lift samples with42 grasp-valid lift samples; across all stages,79 are grasp-valid and150 contact-load-valid. Peak lift attachment position error is9.314366924mm.
- 末样`grasp_valid=false`、`contact_load_valid=true`、`contact_manifold_valid=true`，左右接触冲量[.03290384557027437,.02986502507701516]N·s。acquire成功是生产阶段结果，不代表每个样本均稳定有效。 / The final sample has invalid grasp qualification despite valid bilateral load/manifold and the stated impulses. A successful acquire result does not establish validity of every sample.
- `manipulation.prepare_held=unavailable`、`pour_route_unavailable`；24个候选全部拒绝。完整逐候选detail保存在`acceptance.json`与抽取后的`placement-summary.json`，以下只分类各候选报告的首个拒绝原因，不代表该候选仅有一个问题；12条数值未找到解不等于数学不可达。 / Held preparation rejects every candidate, retaining full raw details in acceptance and the extracted summary. Counts classify each candidate's first reported rejection, without excluding additional problems; failure to find a numerical solution in12 cases does not prove mathematical unreachability.

| 各候选首个报告拒绝原因 / First reported rejection per candidate | 数量 / Count |
|---|---:|
| transport阶段无解 / No solution in transport | 12 |
| IK连续解失败 / Continuous IK failure | 5 |
| panda_hand碰撞TargetBeaker / Hand–TargetBeaker collision | 4 |
| panda_link6碰撞桌面 / Link6–table collision | 2 |
| payload碰撞TargetBeaker / Payload–TargetBeaker collision | 1 |
| 总计 / Total | 24 |

没有执行pour或place，终态仍holding。视频仅包含acquire阶段；倾倒资格化失败后无倾倒运动。视频为`out/labutopia-elevated-20261119/C-elevated/artifacts/labutopia/phase-video/7e063e88c039442db11750ea220ea68b.mp4`；主会话ffprobe确认35.616667秒、2137帧、3840×960、46641276bytes，并抽帧目视确认增高部署。

Pour and place do not execute, and possession remains holding. The video covers acquisition only; failed pour qualification produces no pouring motion. The stated video is independently checked with ffprobe at35.616667 seconds,2137 frames,3840×960 and46641276bytes; extracted-frame inspection confirms the elevated deployment.

`summarize-run.py`已由主会话用于本轮C，`placement-summary.json`记录已落盘任务/receipt/反馈状态、完整失败detail、24候选、抓取参数与视频路径。缺某phase反馈只标缺证据，脚本本身不据缺失猜执行；本报告的未执行结论结合完整任务receipts与反馈。当前实现提交见[月档v17.8.3 Git实现提交收据](../../changelog/2026-11_part3.md)；本分支push已成功并由远端指针核验。

The primary has used the summarizer on C's persisted artifacts. The summary preserves task/receipt/feedback status, full failures,24 candidates, grasp parameters and video paths. Missing phase feedback remains explicitly missing evidence; this report's execution conclusion additionally uses complete task receipts. The current implementation commit is recorded in the [v17.8.3 archive receipt](../../changelog/2026-11_part3.md); the branch push succeeded and the remote ref was verified.

C相对B恢复成功抓取，且24个倾倒候选不再出现A的link2撞桌主导失败；倾倒仍因连续IK及腕部/载荷碰撞被拒。离线独立端点分析没有覆盖这些连续路径约束。遵照用户限制，本轮只采用上述一个计算布局，桌面初始位置不动，安全阈值保留；不再逐次试高度或放宽阈值。当前结论是部署与抓取证据改善、倾倒任务失败，不能承诺靠近或增高即可倾倒。

C restores acquisition beyond B's failure and removes A's dominant link2/table failure from the observed pour-candidate set. Continuous IK and wrist/payload collisions still reject pouring, demonstrating the limits of independent-endpoint analysis. This run uses the single computed layout, preserves initial tabletop positions and existing thresholds, and does not continue successive height or threshold trials. Improved deployment/acquisition evidence does not establish successful pouring or isolate distance as the remedy.
