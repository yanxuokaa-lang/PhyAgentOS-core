# Ridgebase Franka 增高部署 / Elevated Deployment

记录 / Recorded: 2026-11-20，Asia/Shanghai。版本 / Version: v17.8.3（当前候选布局；fresh初始化与运行证据已补齐，C轮仍为历史v17.8.0布局）。

既有A轮移除桌面旧臂后，24条倾倒路线仍全部失败，22条明确报告活动臂link2撞桌；B轮靠近后在lift前因瓶体旋转超限失败。历史C轮使用0.43m增高布局并最终未完成倾倒。本版本只记录由离线端点敏感性扫描选出的单一候选：底盘落地、臂基增高到约0.82m、底盘y移至0.10m；桌面物品的初始位置与操作区域保持原坐标。

After legacy-arm removal, A still rejects all24 pour candidates, including22 explicit live-arm link2/table collisions. B fails before lift on bottle rotation. Historical C used the0.43m elevated layout and still failed to pour. This version records one candidate selected by offline endpoint sensitivity: grounded chassis, arm root near0.82m, and chassis y=0.10m, while preserving tabletop item positions and operation-area coordinates.

C轮（历史0.43m布局）已失败终态：抓取返回成功并持瓶，但持瓶倾倒准备的24个候选全部拒绝，未执行pour或place。该单一布局使抓取越过B轮的lift前失败，C候选中不再出现A轮主导的link2撞桌原因；现有连续IK及腕部/载荷碰撞仍阻止倾倒，不能归因为仅距离过远。v17.8.3候选的fresh无动作检查通过，但持瓶倾倒路线资格未通过，未进入实际pour或place。

C (historical0.43m layout) terminates failed after a successful acquire and a held-pour preparation that rejects all24 candidates. Pour and place do not execute. Acquisition progresses beyond B's pre-lift failure, and C no longer reports A's dominant link2/table failure. Continuous IK and wrist/payload collisions still prevent pouring; the evidence does not isolate excessive distance as the sole cause. For v17.8.3, the fresh no-motion check passes, but held-pour route qualification rejects every candidate before pour or place.

## v17.8.3当前候选 / Current v17.8.3 Candidate

候选来自只读离线端点敏感性扫描：`arm_root=[-0.82,0.10,0.82]m` 是扫描中唯一使保存的实测姿态修正目标进入IK的部署点。该证据只支持部署方向选择，不证明连续路线、夹持接触或实际倾倒成功；fresh无动作检查已通过，但持瓶路线资格失败，按原决策边界停止继续调参并保留失败原因。

The candidate comes from a read-only offline endpoint sensitivity scan: `arm_root=[-0.82,0.10,0.82]m` is the only scanned deployment point that admits the saved measured pose-correction target to IK. This supports placement selection only; it does not establish a continuous route, grasp contact or runtime pouring. The fresh no-motion check passes, but held-pour route qualification fails; the existing decision boundary therefore stops further tuning and retains the failure evidence.

## 单一布局 / Fixed Layout

| 项目 / Item | 历史C布局 / Historical C | v17.8.3当前候选 / Current candidate |
|---|---|---|
| 底盘世界坐标 / Chassis world position | [-1.12,.18,.01]m | [-1.12,.10,.01]m |
| 名义臂基世界坐标 / Nominal arm-root world position | [-.82,.18,.72]m | [-.82,.10,.82]m |
| 手臂尺寸 / Arm scale | 1 | 1 |
| 安装柱 / Elevation column | 0.12×0.12×0.43m | 0.12×0.12×0.53m |
| 柱质量、COM / Mount mass, local COM | 6kg; [.3,0,.215]m | 6kg; [.3,0,.265]m |
| 柱主惯量 / Mount diagonal inertia | [.09965,.09965,.0144]kg·m² | [.14765,.14765,.0144]kg·m² |

当前候选的桌面AABB仍为z=[.6973860684,.7123860691]m；名义臂基高出桌面107.614mm。柱名义世界AABB为x[-.88,-.76]、y[.04,.16]、z[.29,.82]m，与桌子xmin=-.7350872574m相隔24.913mm。R05与烧杯的当前目标距离不沿用历史C数值，须由fresh初始化和路线证据重新记录。

For the current candidate, the tabletop remains at z=[.6973860684,.7123860691]m, leaving the nominal arm root107.614mm above its top. The column's nominal world bounds are x[-.88,-.76], y[.04,.16], z[.29,.82]m, with24.913mm horizontal clearance from the table edge. Current R05 and beaker target distances are not reused from historical C and must be recorded from fresh initialization and route evidence.

`labutopia-ridgebase-elevated.usda`引用原`ridgeback_franka.usd`的`panda_mobile`，不改外部原资产。当前候选将全部12个臂/手/手指/endeffector刚体平移z+.53m，安装节点原位，安装关节localPos0改为[.3,0,.53]；其余关节局部框架及底盘变换保留。stage明确以米为单位、Z朝上。

The wrapper references the original robot without editing it, raises all12 arm/hand/finger/end-effector bodies by.53m, retains the mounting body's pose and updates the mounting joint's localPos0. Other joint frames and chassis transforms remain intact; stage units are meters with Z up.

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

# 复现使用新目录；本次C已执行完毕 / Reproduce in a fresh directory; C is complete:
.venv/bin/python out/labutopia-elevated-20261119/run-elevated.py \
  --workspace out/labutopia-elevated-20261119/C-elevated-NEW

# 只抽取本次已落盘结果，不运行仿真 / Extract the persisted C result without simulation:
.venv/bin/python out/labutopia-elevated-20261119/summarize-run.py \
  --workspace out/labutopia-elevated-20261119/C-elevated
```

当前代码与配置回归测试206 passed：真实`_collisions`用stub PhysX覆盖link2、finger、payload撞柱拒绝及link0连接豁免；USD组合验证全部刚体平移、关节锚、底盘、柱碰撞/质量/惯量/单位，配置验证除mount路径外完全相等。未安装pxr或原外部资产时仅跳过USD集成测试，纯配置测试仍执行。桌面布局逐字比较记录于`deployment-diff-evidence.json`。

The current code and configuration regression command passes206 tests, exercising actual collision logic and no-motion USD composition. USD integrations skip when pxr/source assets are unavailable; pure configuration checks still run. Exact unchanged tabletop/layout evidence is saved separately in `deployment-diff-evidence.json`.

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

`summarize-run.py`已由主会话用于本轮C，`placement-summary.json`记录已落盘任务/receipt/反馈状态、完整失败detail、24候选、抓取参数与视频路径。缺某phase反馈只标缺证据，脚本本身不据缺失猜执行；本报告的未执行结论结合完整任务receipts与反馈。当前实现提交见[月档v17.8.3 Git实现提交收据](../../changelog/2026-11_part3.md)；push尚待执行，未预写结果。

The primary has used the summarizer on C's persisted artifacts. The summary preserves task/receipt/feedback status, full failures,24 candidates, grasp parameters and video paths. Missing phase feedback remains explicitly missing evidence; this report's execution conclusion additionally uses complete task receipts. The current implementation commit is recorded in the [v17.8.3 archive receipt](../../changelog/2026-11_part3.md); the push remains unperformed and no result is asserted.

C相对B恢复成功抓取，且24个倾倒候选不再出现A的link2撞桌主导失败；倾倒仍因连续IK及腕部/载荷碰撞被拒。离线独立端点分析没有覆盖这些连续路径约束。遵照用户限制，本轮只采用上述一个计算布局，桌面初始位置不动，安全阈值保留；不再逐次试高度或放宽阈值。当前结论是部署与抓取证据改善、倾倒任务失败，不能承诺靠近或增高即可倾倒。

C restores acquisition beyond B's failure and removes A's dominant link2/table failure from the observed pour-candidate set. Continuous IK and wrist/payload collisions still reject pouring, demonstrating the limits of independent-endpoint analysis. This run uses the single computed layout, preserves initial tabletop positions and existing thresholds, and does not continue successive height or threshold trials. Improved deployment/acquisition evidence does not establish successful pouring or isolate distance as the remedy.
