# LabUtopia 倾倒路线修复 / Pour Route Correction

Version: v17.8.1. Date: 2026-11-19. **路线资格修复通过，实际倾倒失败。 / Route qualification passes; actual pouring fails.** 最终代码保留路线/退出和full-pose IK重试，与E源码逐字相同；E仍transport失败、无process/hold。F手指继承尝试因更早失去接触已撤回（reverted）；首次F另为仿真前上游失败。 / Final source retains route/retreat and full-pose IK retry, bytewise matching E. E still fails in transport without process/hold. The F finger-command experiment is reverted after earlier contact loss; initial F separately stopped upstream before simulation.

## 目标与边界 / Goal and Boundary

修复由C完整失败证据暴露的倾倒几何与退出问题；机器人部署、桌面物品初始位置及碰撞、IK、对准和连续性阈值保持原值。 / Correct pour geometry and retreat issues exposed by C's complete failure evidence, retaining robot deployment, initial tabletop positions and collision, IK, alignment and continuity thresholds.

通用层保留任务语义与公共契约；横移及退路属于Isaac Adapter机制，替换Provider不需要修改AgentLoop。WorkerSession拥有scene revision，Runtime拥有取消、结算与恢复。仅fresh revision的准备与runtime反馈能证明动作；历史混合诊断不提供执行授权。 / Generic task semantics and contracts remain unchanged. Isaac Adapter owns lateral and retreat mechanisms; replacing a Provider requires no AgentLoop change. WorkerSession owns scene revisions; Runtime owns cancellation, settlement and recovery. Only fresh-revision preparation and runtime feedback establish motion evidence; mixed historical diagnostics grant no execution authority.

## 机制诊断 / Mechanism Diagnosis

证据：`out/labutopia-pour-clearance-20261119/replay-clearance.py`、同名`.json`/`.log`。输入来自C的最终acquire关节、手指开度、observed object pose、既有点云，以及同revision1的source/destination rim。source lip由生产`_task_conditioned_pour_feature`重新选择，再转换到当前observed object frame。障碍来自生产Backend/WorkerSession fresh reset。 / Inputs combine C's final acquire joints, finger openings, observed object pose and existing point cloud with same-revision1 source/destination rims. The production task-conditioned feature routine reselects the source lip in the current observed-object frame, while a production Backend/WorkerSession fresh reset supplies obstacles.

诊断共26条完整`qualify`路线，1条通过、25条拒绝，耗时162.5s。拒绝首因：payload collision4、route collision11、numerical IK6、continuity4。所有尝试期间reset实际关节及仿真时间保持不变，零操作运动命令。 / Twenty-six complete routes produce one pass and25 rejections in162.5s: four payload collisions,11 route collisions, six numerical IK failures and four continuity failures. Actual reset joints and simulation time remain unchanged throughout, with zero manipulation commands.

| 对照 / Comparison | 结果 / Result |
| --- | --- |
| `.04 / yaw0 / azimuth+π/2`，无横移 / no lateral offset | process payload/beaker碰撞 / collision |
| 同上，横移`[-.00467108245,+.02611859469,0]m`，原退出 / same offset with original retreat | process通过，exit连续IK`.624982>.5rad` / process passes, exit continuity rejects |
| 同横移，最终upright exit返回首upright ingress / same offset, final upright exit returns to first upright ingress | 完整127步通过：transport71/process15/exit41 / complete127-step pass |
| `.048 / yaw0 / azimuth+π/2`，无横移，原或同侧退出 / no offset, original or same-side retreat | fresh障碍下process payload/beaker碰撞 / collision with fresh obstacles |

唯一通过候选的横移长度26.533mm，lip/rim三维距离`.048m`，在既有预算内。方向为`-cross(axis,bottle_side)`，其中bottle_side取倾斜瓶体原点相对真实目标中心的轴正交投影。它在该候选horizontal/other基下的分量为`[-.02521218844,+.00826713698]m`，并非单一基方向。 / The sole passing offset has26.533mm length and a.048m three-dimensional lip/rim distance within the existing budget. Its direction is minus the cross product of the axis and projected bottle-side vector, with the stated horizontal/other components.

局限：历史held状态与fresh障碍不属于同一revision；fresh烧杯相对C末态约1mm不同。两个`.04`控制候选的TCP复现到约1e-10m且同样碰撞，但C最近`.048`候选原本到exit才失败，在本诊断提前被process碰撞拒绝。因此结果只支持机制选择，不宣称C全场景精确重放或正式执行合格。 / Historical held state and fresh obstacles do not share a revision; the fresh beaker differs from C's end state by about1mm. Two.04 controls reproduce TCP values to about1e-10m with matching collision outcomes, while the formerly closest.048 candidate now rejects during process rather than exit. These results support mechanism selection without claiming exact full-scene replay or execution qualification.

## 生产实现 / Production Implementation

`phase_motion.py`的pour最后upright exit使用与首upright ingress相同的位置和orientation，保留tilted上抬到原high点（横移候选在此回收横向偏移）。居中clearance/yaw/azimuth的完整搜索与既有排序保留；任何居中路线合格即不进入横移搜索。 / Final upright retreat uses the first upright ingress pose while retaining the tilted rise to the original high point (recovering lateral offset for shifted candidates). The complete centered search and existing ranking remain; any admissible centered route prevents lateral fallback.

全部居中拒绝时，计算`budget=alignment_tolerance-position_tolerance`，`r=sqrt(budget²-clearance²)`；仅有正预算且瓶体投影方向非退化时，依序尝试bottle_side与正负切向三个偏移。只平移process TCP，真实target frame及高位点保持原值。每条仍完整qualify transport/process/exit，首条fallback合格即停止；默认配置最多24条居中+36条fallback。 / After all centered rejections, the existing three-dimensional budget bounds three projected lateral directions. Only process TCP translation changes. Every candidate still qualifies the complete transport/process/exit route; the first passing fallback stops further search, with at most24 centered and36 lateral attempts under the current configuration.

route持久化`pour_lip_offset_m`世界向量与`pour_retreat_strategy="same_side_ingress"`；全部失败仍返回`pour_route_unavailable`并保存各clearance/yaw/azimuth/offset及原始detail。未新增公共字段或配置项。 / Adapter route evidence persists the world offset and retreat strategy. Exhaustion retains the existing failure code and all candidate parameters, offsets and error details; public contracts and configuration fields remain unchanged.

最小抽象泄漏检测包括prepare不改真实target、不发apply，居中合格不扩大搜索，以及exit失败仍拒绝整条候选。 / The smallest abstraction-leak checks cover immutable true targets, no apply from prepare, no fallback after centered success, and full candidate rejection on exit failure.

## 回归验证 / Regression Validation

```bash
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py examples/forge-adapters/isaacsim_lab/tests/test_ridgebase_elevated.py -q
```

结果：**202 passed**，既有`asyncio_mode`警告1项，5.22s。新增8项覆盖真实waypoint同侧退出、倾斜轴三维预算与只移process、居中优先及旧排序、全部居中失败后fallback首条通过停止、退出碰撞/连续IK拒绝60条完整候选，以及无预算/退化投影跳过。 / The original194 regressions plus eight additions pass, covering actual waypoints, tilted-axis budgeting, process-only offsets, centered preference/ranking, bounded fallback, complete-route exit rejection and degenerate cases.

首轮200通过/2失败来自新增测试误以message匹配failure code，改为检查`exc.code`后上述202项全通过。`git diff --check`通过；Ruff仅保留旧I001一项及旧E731两项，不报告全文件lint通过。 / The first run's200 passes and two failures came from matching failure codes against messages; correcting the assertions yields202 passes. Diff whitespace validation passes; three existing lint findings remain.

## 正式仿真 / Fresh Formal Simulation [failed]

D目录：`out/labutopia-pour-clearance-20261119/D-fresh`，task`task_60462336366b41f8`终态failed，时间2026-11-19T21:12:24.641851+08:00至21:32:46.593420+08:00，returncode1。 / D records the stated failed terminal task, timestamps and return code1.

28/28 probes available，acquire succeeded，反馈2139样本/113lift，lift attach位置误差峰9.314366924mm。末样grasp_valid=false、contact_load_valid=true，不将整个夹取过程描述为始终有效夹稳。 / Acquisition succeeds with2139 samples,113 lift samples and a9.314366924mm peak lift attachment-position error. Final grasp validity is false despite valid contact load, so stable-grasp validity is not generalized to all samples.

fresh readiness`artifacts/labutopia/readiness/5e739d478ae84170bae9ba88ccf8b99a.json`选中居中`.048/yaw0/azimuth+π/2`、world offset`[0,0,0]`、same_side_ingress，完整125步（transport71/process14/exit40）通过。revision=`labutopia-tabletop-rod-rack-v1:a6f7f35ca07c4a2ca05755a06c73c99c:1`。本次实际选择不是混合诊断中唯一通过的横移候选；准备阶段只需同侧退路即可获准。 / Fresh readiness admits the centered zero-offset same-side125-step route in the stated revision. The actual selected route differs from the sole lateral pass in the mixed-history diagnostic.

pour反馈`phase-feedback/73990b0b189f4330a31a143903605cde.json`：1651样本均为transport，failure=`inverse_kinematics_failed`，detail=`measured pour-pose correction is unreachable`。process0、合格tilt hold0s、最大实测tilt`.5951736459333297rad`；未执行place。双边contact load与manifold均1651/1651有效，但grasp_valid仅229/1651；末态attach位置误差10.352944586mm、旋转`.3821746528rad`。这些事实不支持倾倒成功或已完成物料转移。 / Pour fails during transport with the stated correction-IK error before any process or qualified hold. Bilateral contact remains valid throughout but grasp-transform validity holds for only229 of1651 samples; the stated final attachment errors remain explicit. No pouring, placement or transfer success is claimed.

pour视频`phase-video/487f1976e3e94be5bfb786cf47b6b022.mp4`，主会话ffprobe核实27.5s/1650帧/3840×960；反馈比视频多一个终态重复record，1651样本不等于1651执行帧。 / The primary verifies27.5s,1650 frames and3840×960 resolution; feedback includes one extra terminal record rather than an additional commanded frame.

后续仅做`diagnose-pour-correction.py`无动作诊断：按保存point边界重建原full-pose求解，比较少量seed、primary Lula和tip+axis残差，保持完整pose语义优先，正式改法待主会话裁决。 / Follow-up diagnosis reconstructs the original full-pose solve at saved boundaries and compares a few seeds, primary Lula and tip/axis residuals without motion. Full-pose semantics remain the priority; the primary decides any implementation change.

输入比较：station相对C仅workspace路径变化，motion配置逐字节一致；elevated USD仅删除旧EOF空行，rstrip后相同。部署与桌面初始布局保持原值。 / Compared with C, station differs only in workspace path, motion configuration is bytewise identical and the elevated USD differs only by deletion of an EOF blank line; deployment and initial tabletop layout are retained.

## 运行期IK无动作诊断 / Runtime IK No-Motion Diagnosis

脚本`out/labutopia-pour-clearance-20261119/diagnose-pour-correction.py`及同名JSON/log，使用生产Backend fresh初始化的真实FK/limits，逐点重现原full-pose correction和smooth_joint_segment长度，再从D已保存边界sample读取实际joints/object_pose更新relation。终态多一次record已扣除，不重放任何机器人动作。 / The diagnostic uses production fresh FK/limits and reconstructs each original full-pose correction and segment length from saved measured boundary states, excluding the extra terminal record and commanding no motion.

重建结果：point index61（第62点，transport）首次full local invalid；之前61点累计1650执行帧，恰好覆盖全部1650非重复反馈，剩余0。初始relation差0，所有边界saved TCP与FK位置差0。故记录为`exact_saved_boundary_accounting`；它表示保存边界及帧数精确匹配，不表示物理轨迹重演或新场景执行授权。 / Reconstruction finds the first rejection at zero-based point61 in transport, with all1650 saved command samples exactly accounted for and zero initial-relation/FK-position discrepancies. This establishes saved-boundary accounting, not replayed physical motion or fresh execution admission.

| 失败点求解 / Solve at failure point | valid | 位置误差 / Position error | 完整旋转误差 / Full rotation error | 相对当前关节最大delta / Max delta from current |
| --- | --- | --- | --- | --- |
| full local，当前seed / current seed | false | .795374mm | .0238165rad | .0460364rad |
| full local，名义point seed / nominal point seed | true | 5.04e-10m | 1.41e-8rad | .110876rad |
| full local，上一名义point seed / previous nominal seed | true | 1.57e-12m | 4.23e-11rad | .0846107rad |
| full primary Lula，当前warm start | true | .0982303mm | .000962118rad | .0803714rad |
| tip+axis local，当前seed / current seed | true | .555481mm TCP；tip2.47e-12m | .0408325rad | .0672011rad |

原阈值位置2mm、完整旋转.02rad、continuity.5rad保持。前三条有效full候选均在limits内，最小关节限位余量分别.741763/.736337/.723502rad。失败点前后各2点仅比较同一失败边界relation下的名义目标，未虚构未来physical relation；nominal-seeded full和primary Lula五个比较点均成功。 / Existing2mm position,.02rad full-rotation and.5rad continuity limits remain. All three valid full-pose comparisons satisfy joint limits with the stated margins. Five neighboring targets share the saved failure-boundary relation rather than fabricated future physical state; nominal-seeded full solves and primary Lula succeed across these comparisons.

证据支持当前local seed遇到数值分支失败，不支持目标full pose必然不可达。tip+axis虽能满足其残差，但该点完整旋转误差超原.02rad，因此不能据此替换完整姿态语义；task-conditioned rim offset也不是中心轴点。未检查这些替代解的完整碰撞轨迹，不授予执行资格。reset实际关节和simulation time保持不变，motion commands0；生产改法仍由主会话裁决。 / Evidence supports a local numerical-branch failure rather than full-pose impossibility. The tip/axis comparator exceeds the original full-rotation tolerance and does not justify relaxing semantics, especially for an off-axis task-conditioned lip. Alternative collision paths remain unqualified, reset joints/time stay unchanged and production decisions remain with the primary.

## Full-pose单次重试 / Single Full-Pose Retry [E failed]

主会话根据诊断裁决：仅当pour当前seed local IK无效，使用当前point原planned joints对完全相同target TCP重试同一full-pose local solver。有效且相对start最大joint delta不超原.5rad才采用；有效但超限返回`ik_discontinuity`，含stage/delta/max；无效保留原`inverse_kinematics_failed`。不加入Lula、tip+axis或额外搜索，不改变姿态语义、frame、容差及逐命令碰撞检查。 / The primary approves one retry of the identical full-pose target using the current point's planned joints, only after current-seed failure. Valid solutions must remain within the existing.5rad continuity bound; branch jumps are rejected explicitly and no-solution errors remain unchanged. No Lula, tip/axis or wider search is added.

必要边界：改变初值可能得到远关节分支，preparation约束的是原抓持关系，不能约束实测抓持修正的新解。因此只在这个fallback动作边界复用现有连续性阈值；不新增公共配置、契约或机制。 / A new seed may find a distant branch for a measured-attachment correction that original preparation cannot constrain, so this fallback reuses the existing continuity bound at its motion boundary without extending public contracts or configuration.

同一测试命令最新结果：**206 passed**（202+4执行回归），5.68s，既有asyncio_mode警告1项。新增测试实际调用full local solver，核实同target/原planned seed及最终body完整姿态、tip、axis误差；两seed失败、远跳均零动作；fallback路径碰撞在首次apply前拒绝。Ruff仍仅3项既有问题。 / The same command now passes206 tests, including four execution regressions covering the identical full-pose target and final residuals, zero-motion solver exhaustion/branch rejection and collision rejection before the first apply. The three existing lint findings remain.

主会话review本次10行修复及4执行回归无Blocker/Major，已启动fresh E：`out/labutopia-pour-clearance-20261119/E-fresh`，基于HEAD`91b910840e56a15e0a73d4dea72ad2ca5a54deaa`加保存的`implementation.diff`。E已failed，详见下节；D保持已记录失败，206项测试并未证明运行期倾倒已完成。 / Primary review finds no Blocker/Major and launches E with recorded HEAD plus implementation.diff. E subsequently fails as detailed below; D remains failed and206 passing tests do not establish runtime pouring completion.

## E终态与指令交接证据 / E Outcome and Command Handoff Evidence

E task`task_46b67f1aaa20470c`于2026-11-19T21:43:16.559192+08:00至22:05:21.927886+08:00运行，failed/returncode1；acquire反馈`ab87d968d4e54cbeb14b520b4b2ec604.json`仍succeeded2139样本。pour反馈`aa03d16ad38040c29238017b432b9bf0.json`仍`inverse_kinematics_failed: measured pour-pose correction is unreachable`，2062样本均transport，process0/hold0，最大tilt`.8227368211517622rad`，末attach位置10.141432925mm/旋转`.5132515595rad`。 / E records the stated failed task and times after successful acquisition, with2062 transport samples, no process/hold and the same correction-IK failure. The stated terminal attachment errors remain explicit.

相对D1651样本/最大tilt.59517，E前沿延长到2062样本/.82274rad，但仍未进入process，不能把数值fallback写成已解决倾倒。视频`phase-video/e456e5e8e26d45e4b0a7000eeab5c252.mp4`由主会话ffprobe核实34.35s/2061帧/3840×960/45003107bytes。 / E advances farther than D but still reaches no process stage, so numerical fallback has not resolved pouring. The primary verifies the stated complete video metadata, including the extra terminal feedback record.

D/E相同的交接证据：acquire末指令`[.01592840626835823,.015569766983389854]m`，末实测`[.019920673221349716,.015569900162518024]m`；旧代码pour首指令变成后者，左指目标向外改变3.992267mm，抹掉原已施加servo压紧目标。指令交接bug由代码与反馈直接支持；fresh F已正确继承指令但仍失败，不能将交接修复描述为已解决夹持或倾倒。 / Both runs show acquire's applied command differing from measured opening; old pour initialization substitutes that measurement, opening the left commanded target by3.992267mm. Code/feedback establish the handoff bug; fresh F preserves the command but still fails, so the correction does not establish successful grasp or pouring.

## 手指目标连续性尝试 / Finger Target Continuity Experiment [F failed; reverted]

以下为F尝试的历史实现，已在最终代码中撤回。 / The following describes the historical F experiment, reverted from final source.

该尝试的非acquire初始化读取现有SDK`get_articulation_controller().get_applied_action().joint_positions[finger_indices]`的dense上一指令，保留实际已施加目标；不另加servo状态、overshoot、hold_follow、力或阈值。SDK本地源码`articulation_controller.py` L231-L248确认返回dense joint_positions且不带indices。acquire初始及release目标仍为.04m。 / Non-acquire initialization retains the controller's previous dense applied finger command, with no new servo state, force, overshoot, follow or threshold. Local SDK source confirms the dense return; acquire/release opening remains.04m.

缺action/positions、finger索引不可取或非有限时，以`PhaseMotionPreconditionError(held_finger_target_unavailable)`在world.play/apply前拒绝。测量开度不是servo目标，不能用它静默替代未知命令；这是现有held动作边界的必要前置条件。 / Missing, unindexable or nonfinite applied finger targets reject before play/apply at the existing held-action boundary, because measured opening cannot silently substitute for an unknown servo command.

F尝试时同命令 **212 passed**（206+6），5.58s，既有warning1项；真实acquire→pour fixture建立指令/测量不等，pour首及carry保持上一目标，release仍.04；缺失/短数组/NaN/Inf零动作。Ruff仍3项旧问题，git diff --check通过。F当时的212项回归通过，但fresh运行failed；该patch及6项专用回归/fixture改动现已撤回，212不作为最终测试结果。 / The same regression command passes212 tests, including six new handoff, release and no-motion rejection cases. Fresh F fails as detailed below; its patch and six dedicated regressions/fixture changes are now reverted, so212 is not the final regression result.

首次F：`out/labutopia-pour-clearance-20261119/F-fresh`于2026-11-19 22:10:33至22:11:10（Asia/Shanghai）退出returncode1；host.log为`LLM upstream response stream interrupted`，tasks=[]，无phase反馈、无新动作，未进入仿真。它是上游启动失败，不能记为motion失败。 / Initial F exits with the stated upstream LLM stream interruption, empty tasks and no phase feedback/new motion before simulation; it is not a motion failure.

主会话使用相同源代码及配置重试：`out/labutopia-pour-clearance-20261119/F-retry-fresh`，真实终态failed，详见下节；源码/测试继续固定，仅维护文档。 / The primary retries identical source/configuration in F-retry-fresh; its actual outcome is failed as detailed below, while source/tests stay fixed.

F运行前，主会话对三处修复及新增18项回归的代码review未见Blocker/Major：变更均在Isaac Adapter；source/target原语义及全部阈值保留；full-pose fallback目标不变，复用原连续性边界并保留逐命令碰撞；手指指令由现有controller持有，无shadow状态。F retry与E的七个输入文件在strip并归一workspace后完全一致，profile归一后也相等。这些是运行前边界与输入可比性证据；F真实失败随后推翻手指patch验收，该patch已撤回。 / Before F runtime, code review finds no Blocker/Major across the three fixes and18 new regressions: changes stay in the Isaac Adapter, source/target semantics and thresholds remain, full-pose fallback preserves its target, continuity bound and command-level collision checks, and the existing controller owns finger commands without shadow state. Seven F-retry/E input files match after stripping and workspace normalization; normalized profiles also match. These pre-runtime review and input-comparison records do not establish acceptance: F subsequently overturns acceptance of the finger patch, which is reverted.

## F-retry终态与后续诊断 / F-Retry Outcome and Next Diagnosis [failed]

F-retry task`task_26d6248c2657456e`于2026-11-19T22:11:23.962067+08:00至22:28:53.830262+08:00运行，failed/returncode1。acquire反馈`a643a6c9cb8b4765b24304c6fca59065.json` succeeded/2139样本、113lift；末finger target与measurement逐项等于E，末attach位置9.314366924mm/旋转.01352641545rad，grasp_valid=false/contact_load=true，不称全程夹稳。 / F-retry records the stated failed task, timestamps and return code after successful2139-sample acquisition with113 lift samples. Final finger commands/measurements match E elementwise; the stated attachment error and false grasp-valid/true contact-load flags remain explicit without claiming continuously stable grasp.

fresh readiness`readiness/fb3f00aef189438ca9a918eca0f725a8.json`在revision后缀`bd21cd9e8fb64cf38dd07e23d421372e:1`选中居中`.048/yaw0/azimuth+π/2`、zero offset、125步same-side ingress路线。pour首finger target已正确继承acquire末指令`[.01592840626835823,.015569766983389854]m`，没有替换成实测开度。 / Fresh readiness admits the centered zero-offset125-step same-side route in the stated revision. Pour's first finger target correctly retains acquire's final applied command rather than the measured opening.

pour反馈`phase-feedback/7a5700228fe34c4e807959b1f682b4e2.json`为`physical_grasp_lost: bilateral contact lost during attached motion`：411样本均transport，process0/hold0，最大tilt.07209758523rad，attach位置/旋转峰.02303421763m/.1794298536rad。视频`phase-video/85585f0c9c1f4c96ac8edfc8c9d56b13.mp4`经主会话ffprobe核实6.833333s/410帧/3840×960/8855228bytes；反馈额外终态record1。 / Pour fails with bilateral-contact loss after411 transport-only samples, before process or hold, with the stated maximum tilt and attachment-error peaks. The primary verifies the stated complete410-frame video; feedback includes one extra terminal record.

F已证明目标指令交接按改法生效，但比E更早失去双边接触，尚不能认定手指继承修复解决了夹持或倾倒。下一步由主会话只读比较E/F相同时间段joints、手指目标/实测、接触几何及已有视频；后续主会话已裁决撤回F专用patch，保留路线/IK；force/config保持，不新增完整仿真。 / F establishes that command inheritance takes effect, yet loses bilateral contact earlier than E; it does not establish successful grasp or pouring. The primary will compare matching E/F time windows using saved joints, commanded/measured fingers, contact geometry and existing videos without motion. The primary subsequently reverts the F-only patch and retains route/IK fixes, with unchanged force/configuration and no additional full simulation.

## 无动作夹持几何诊断 / No-Motion Grip Geometry Diagnostic

`diagnose-grip-geometry.py`使用F-retry profile和生产Backend/WorkerSession fresh reset，只读保存DOF及USD Drive/PhysX属性、authored opinions、world transforms、finger_geometry与oracle approach；R05唯一body为`/World/ReagentZones/B/R05/Model/mesh`。按生产`cooked_body_boxes`及USD local-to-world转换保存1 collider的32完整convex、907 world顶点，不以rings替代几何。 / The diagnostic uses F-retry configuration and a production fresh reset to save DOF and USD drive/PhysX opinions, transforms, finger geometry and oracle approach. It resolves the stated unique R05 body and retains all32 complete cooked convexes with907 world vertices using the production USD conversion.

运行exit0，202.2089667378459s，py_compile通过；reset time始末均.0020833334419876337s，joints逐值不变，motion_commands0，无apply/set/step、物体修改或IK求解，app关闭。保存历史F125个原step的只读FK、limits/dt/config；fresh revision不同，不能授权历史F执行。首次缺少既有EULA环境变量的启动在Kit前退出；补齐既有环境后完成本次诊断。 / The completed diagnostic exits0 in202.21s and compiles, with identical reset time/joints and zero motion commands, object changes or IK solves; the app closes. It also saves read-only FK for all125 historical F steps plus limits/dt/config, without granting execution authority across revisions. An initial launch stopped before Kit because the existing EULA environment variable was missing; the configured-environment run completes.

两指实际stiffness均1e7、damping均1e5；joint1 maxForce20N由session layer覆盖原`ridgeback_franka.usd`的1200N，joint2仍asset1200N，DOF maxEffort同为20/1200。robot子树未发现mimic/tendon schema、属性或关系；这不等于已证明不存在机械耦合，也不能单凭force cap不对称宣称滑脱根因。 / Both drives read stiffness1e7 and damping1e5. The session layer overrides finger joint1's asset1200N maxForce to20N; joint2 retains asset1200N, matching runtime DOF effort limits. No mimic/tendon schema, attribute or relationship is found in the robot subtree. This does not rule out mechanical coupling or establish asymmetric force limits as the slip cause.

原始`diagnose-grip-geometry.json`保留；1.195GB主要来自生产返回的5,081,094个body-frame slab boxes。轻量`diagnose-grip-geometry-summary.json`为4,393,907bytes，仍保留全部32凸体/907 world顶点、drive/FK，另列每凸体径向/高度范围。以R05轴及显式诊断范围radius≤.1m、span[-.02,.20]m筛选，32/32均在范围内，excluded0；最大半径34.375804mm，span约[-.000890,116.202456]mm，本次转换后未发现foreign凸体。 / The raw file is retained; its size is dominated by5,081,094 production body-frame slabs. The4,393,907-byte summary preserves all convex/world, drive and FK data with per-convex ranges. An explicit diagnostic near-axis subset retains all32 convexes and excludes none, with the stated maximum radius/span; no foreign convex is identified after this conversion.

## 最终收敛与验收范围 / Final Scope and Acceptance

主会话撤回F手指继承patch、6项专用测试及仅服务该patch的fixture；最终source及tests均与E的`implementation.diff`从原blob重建结果逐字相同。因此最终真实运行证据是E：路线资格通过，但2062样本均transport、process0/hold0，仍measured pour-pose correction IK失败。F是已撤回尝试的失败证据，不能替代E或被写成已解决夹持。 / The primary reverts the F patch, six dedicated tests and their fixture changes. Final source and tests exactly match reconstruction from E's saved diff/base blobs, making E the applicable runtime evidence: route qualification passes but transport correction IK still fails before any process or hold. F remains failed evidence for a reverted experiment.

主会话最终review接受本轮路线/退出及full-pose单次重试代码：搜索预算、完整qualify、full target、原连续性和逐命令碰撞保留。相同回归命令最终 **206 passed**、5.65s、既有asyncio warning1项，git diff --check通过。验收范围为路线代码及回归；实际倾倒未通过，force/config/初始布局未改，停止新增完整仿真，提交/推送由主会话执行。 / Final primary review accepts route/retreat and single full-pose retry with unchanged search budget, complete qualification, target, continuity and command collision checks. The same regression command passes206 tests in5.65s with one existing warning, and whitespace validation passes. Code/regression acceptance does not establish successful pouring; force/configuration/initial layout remain unchanged, no additional full simulation follows and the primary owns commit/push.
