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

### 下一步决策 / Next Decision

建议保留当前机座坐标、高度、桌面初始布局及所有容差，不再据此失败继续调布局。下一步优先只读追查：为何transport样本150起attachment旋转误差超限，尽管接触与负载标记仍有效却持续到失败边界；Lula候选解暂留为备选证据。请裁决先做持瓶关系漂移诊断（推荐），还是直接进行Lula候选的完整无动作路线/碰撞资格验证。任一路径都须保留现有连续性、限位、工作区和碰撞规则；本次诊断不授权机器人执行。

Recommended: retain the current chassis coordinates, mount height, tabletop initial layout and all tolerances; this failure does not support another placement adjustment. First investigate, read-only, why attachment rotation exceeds tolerance from transport sample150 while contact/load flags remain valid and stays invalid through the failure boundary; keep the Lula candidate as secondary evidence. Decide whether to diagnose held-object relation drift first (recommended) or immediately qualify the Lula candidate across the complete no-motion route and collision checks. Either path retains existing continuity, joint-limit, workspace and collision rules. This diagnostic does not authorize robot execution.

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
