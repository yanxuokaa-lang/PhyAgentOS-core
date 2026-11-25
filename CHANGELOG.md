# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

- [2026-11_part4](changelog/2026-11_part4.md)
- [2026-11_part3](changelog/2026-11_part3.md)
- [2026-11_part2](changelog/2026-11_part2.md)
- [2026-11](changelog/2026-11.md)
- [2026-10_part16](changelog/2026-10_part16.md)
- [2026-10_part15](changelog/2026-10_part15.md)
- [2026-10_part14](changelog/2026-10_part14.md)
- [2026-10_part13](changelog/2026-10_part13.md)
- [2026-10_part12](changelog/2026-10_part12.md)
- [2026-10_part11](changelog/2026-10_part11.md)
- [2026-10_part9](changelog/2026-10_part9.md)
- [2026-10_part10](changelog/2026-10_part10.md)
- [2026-10_part8](changelog/2026-10_part8.md)
- [2026-10_part7](changelog/2026-10_part7.md)
- [2026-10_part6](changelog/2026-10_part6.md)
- [2026-10_part5](changelog/2026-10_part5.md)
- [2026-10_part4](changelog/2026-10_part4.md)
- [2026-10_part3](changelog/2026-10_part3.md)
- [2026-10_part2](changelog/2026-10_part2.md)
- [2026-10_index_archive](changelog/2026-10_index_archive.md)
- [2026-10](changelog/2026-10.md)
- [2026-09_part9](changelog/2026-09_part9.md)
- [2026-09_part8](changelog/2026-09_part8.md)
- [2026-09_part7](changelog/2026-09_part7.md)
- [2026-09_part6](changelog/2026-09_part6.md)
- [2026-09_part5](changelog/2026-09_part5.md)
- [2026-09_part4](changelog/2026-09_part4.md)
- [2026-09_part3](changelog/2026-09_part3.md)
- [2026-09_part21](changelog/2026-09_part21.md)
- [2026-09_part20](changelog/2026-09_part20.md)
- [2026-09_part2](changelog/2026-09_part2.md)
- [2026-09_part19](changelog/2026-09_part19.md)
- [2026-09_part18](changelog/2026-09_part18.md)
- [2026-09_part17](changelog/2026-09_part17.md)
- [2026-09_part16](changelog/2026-09_part16.md)
- [2026-09_part15](changelog/2026-09_part15.md)
- [2026-09_part14](changelog/2026-09_part14.md)
- [2026-09_part13](changelog/2026-09_part13.md)
- [2026-09_part12](changelog/2026-09_part12.md)
- [2026-09_part11](changelog/2026-09_part11.md)
- [2026-09_part10](changelog/2026-09_part10.md)
- [2026-09](changelog/2026-09.md)

## 最近五版本 / Latest five versions

## v17.10.10 (2026-11-25 20:32) - codex

- [env] [fix] [完成] 修复Isaac Adapter执行循环的既有夹指侧走保护：将逐帧参考改为close→lift持续保存的双指最小实测开度，累计外退超过原1e-4m阈值时冻结最后目标；close与attached-follow共用局部更新逻辑，正常内收仍跟随。 / [Completed] Repair the existing Isaac Adapter finger-divergence protection by retaining per-finger minimum measured openings across close/lift. Freeze the last target after cumulative outward retreat exceeds the unchanged1e-4m threshold; share local update logic while retaining inward following. (local)
- [eval] [fix] [完成] 真实execute循环覆盖慢性close外退贯穿lift、仅lift外退、内收后累计外退与正常双指内收；复用disabled/release/contact-loss回归。验证旧实现新测试失败，再验证修复后的目标回归、Ruff与diff。 / [Completed] Exercise the real execute loop for slow close drift persisting through lift, lift-only drift, retreat after inward recession and legitimate inward following, retaining disabled/release/contact-loss regressions. Demonstrate regression failure on the old implementation, then run targeted tests, Ruff and diff checks. (local)
- [docs] [docs] [完成] 只修改phase_motion.py、相应测试与报告/日志/Latest5；不改domain port、Tool、AgentLoop或Coordinator，Runtime仍拥有取消结算恢复；无新增gate/hash/schema，不启动仿真。前轮提交e17645a3已推送。 / [Completed] Change only phase_motion.py, tests and evidence documentation; domain ports, Tools, AgentLoop and Coordinator remain unchanged, with Runtime retaining cancellation/settlement/recovery. No new gate/hash/schema and no simulation launch. Previous commit e17645a3 is pushed. (local)

### 失败场景与归属 / Failure and ownership

191713 R03 close首次双侧载荷至末close36帧双指位移[-2.439553,+2.441075]mm，最大单帧外退0.074374mm，小于既有0.1mm阈值，目标更新35次；lift119帧位移[-8.050825,+8.050924]mm，最大外退0.071133mm、更新116次。逐帧重设reference使累计侧走漏检。修复归Isaac Adapter私有机制，跨实现调用契约不变；每控制interval实测finger/contact为新鲜证据，最小回归是载荷有效的慢外退在execute中冻结目标而双指内收仍跟随。 / In191713, sub-threshold per-frame drift accumulated through close/lift while targets kept following. This is an Adapter-private mechanism repair, supported by measured per-control-interval finger/contact evidence; callers and lifecycle ownership remain unchanged.

### Git 提交 / Git Commit

- 上轮诊断结果 / Previous diagnostic evidence: `e17645a3`（已推送 / pushed）；分支 / Branch: `feature/planning-loop`。主会话代码审阅无 Blocker/Major，待其统一提交；本执行代理不 commit/push。 / Parent code review found no Blocker/Major; parent commit is pending, and the execution agent will not commit or push.

### 文件变更详情 / File changes

- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2777、L2788–L2802、L3027–L3037、L3078–L3085：执行局部的 minimum reference 与共享 follow helper，close/attached 两入口共同锁定累计外退；既有 1e-4 m 阈值不变，正常内收更新 minimum，跨 lift 保留参考。 / An execute-local minimum reference and shared follow helper latch cumulative outward retreat in both close and attached motion. The existing threshold remains unchanged; inward motion updates the minimum and lift retains it.
- [新增 / Added] `examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py` L385–L448：3 种慢性外退轨迹 × 任一夹指，共 6 个真实 execute 回归；双侧载荷保持有效，每帧外退 0.07 mm，验证越限前正常更新与越限后直到 lift 结束保持最后目标。 / Six real execute regressions cover three slow-retreat trajectories on either finger, preserving bilateral load and asserting normal updates before crossing and a frozen target through lift afterward.
- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L314–L326：历史失效证据、离线检测重算、Adapter 归属、旧实现失败和新实现回归、Ruff 既有问题及尚无新实跑证据。 / Historical failure evidence, offline detector recalculation, Adapter ownership, old/new regression results, the pre-existing Ruff finding and the absence of new live evidence.

**修改前 / Before:**

```python
# Close compared only with the immediately preceding held sample.
if (follow_hold and contact_established and last_follow_fingers is not None
        and np.any(measured_fingers > last_follow_fingers + 1e-4)):
    follow_diverged = True
# Following updates then replaced that reference every interval.
last_follow_fingers = measured_fingers
# Attached following updated its target without an outward-retreat check.
```

**修改后 / After:**

```python
def follow_measured_fingers(measured_fingers):
    nonlocal finger_target, follow_diverged, minimum_follow_fingers
    if follow_diverged:
        return
    if (minimum_follow_fingers is not None
            and np.any(measured_fingers > minimum_follow_fingers + 1e-4)):
        follow_diverged = True
        return
    minimum_follow_fingers = (measured_fingers.copy() if minimum_follow_fingers is None
                              else np.minimum(minimum_follow_fingers, measured_fingers))
    retain_overshoot = float(self.config.get("finger_retain_overshoot_m", 0.0))
    finger_target = np.maximum(measured_fingers - retain_overshoot, 0.0)
# Close and attached-follow both call this execute-local helper.
```

### 验证与证据边界 / Validation and evidence boundary

- [eval] [fix] 修改生产代码之前，`test_contact_timing.py -k freezes_cumulative_outward_drift --tb=short` 的 6 个新例全部失败（6 failed, 26 deselected, 1.22 s），失败均为累计越限后的 target 未冻结，最大偏离预期 0.49 mm；无需临时恢复生产文件。 / Before production edits, all six new cases failed because targets continued following after cumulative crossing, with a maximum 0.49 mm difference from the expected frozen value; no temporary source restoration was needed. (local)
- [eval] [fix] `PYTHONPATH=examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py --tb=short`：297 passed in 10.00 s；含快速侧走、正常双指内收、disabled、release、contact-loss、取消及已有恢复回归。 / The combined motion/contact suite passed all 297 tests, including fast divergence, normal inward following, disabled follow, release, contact loss, cancellation and existing recovery. (local)
- [chore] [chore] `.venv/bin/ruff check examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py`、`git diff --check` 通过。生产文件完整 Ruff 未全绿：仅 L1061–L1065 既有 I001 import formatting，已在 `git show HEAD:examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py | .venv/bin/ruff check --stdin-filename examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py -` 复现相同告警，未顺带修改。 / Test-file Ruff and whitespace checks passed. Full production-file Ruff retains the same pre-existing I001 finding reproduced from HEAD; no unrelated formatting edit was made. (local)
- [eval] [exp] 主会话对 191713 保存轨迹只读重算：R05 首双侧载荷后第 1 帧（0.01667 s）外退 0.145977 mm，旧 guard 已检出；R03 第 2 帧累计外退 0.143545 mm、每帧小于 0.1 mm，minimum reference 可检出。仅为历史检测重算，不是新物理结果。 / Parent read-only recalculation of the saved trajectory shows the old guard detecting R05's first outward step, while the minimum reference detects R03's accumulated second step. This is historical detector evidence, not a new physical result. (local)
- [docs] [docs] 主会话审阅 helper 和 6 个回归，无 Blocker/Major；本轮没有启动 Isaac 或硬件、未变物理配置，也未证明居中抓持或倾倒成功。实际运动结果需提交后另行验证；执行代理完成文档后暂停写入。 / Parent review found no Blocker/Major. This work launched no Isaac or hardware execution and changed no physics configuration; centered gripping and pouring success still require later live validation. The execution agent pauses edits after documentation completion. (local)

## v17.10.9 (2026-11-25 20:12) - codex

- [env] [exp] [完成] 创建独立本地R03静态倾倒路线诊断：使用191713抬升末态、历史assignment/点云及scene:4 rim特征，按现有qualify检查最多32条方位组合，量化历史观测与新初始化场景差异。初始化后不step、不写关节/物体、不执行动作；历史两指位置仅用于纯计算碰撞几何。 / [Completed] Create an independent static R03 pouring-route diagnostic using the191713 terminal lift sample, historical assignment/clouds and scene:4 rim features. Retain existing qualify checks for at most32 orientation variants and quantify historical/fresh-scene differences. After initialization, do not step, set joints/objects or execute; saved finger positions supply calculation-only collision geometry. (local)
- [docs] [docs] [完成] 先完成本地脚本交主会话审阅，再运行诊断；保存每条进度/中间JSON、前后真实state/time及限制说明，更新报告和Latest5；不产生readiness/admission，不改生产代码，不启动新任务。 / [Completed] Submit the local script for parent review before running it, then retain per-variant progress/intermediate JSON, before/after real state/time and limitations. Update report and Latest5 without readiness/admission, production edits or a new task. (local)

### Git 提交 / Git Commit

- 上轮终态证据 / Previous terminal evidence: `5d2d1017`（已推送 / pushed）；分支 / Branch: `feature/planning-loop`。本轮待主会话审阅，执行代理不提交/推送。 / This work awaits parent review; the execution agent will not commit or push.

### 文件变更详情 / File changes

- [新增 / Added] 本地 `out/labutopia-elevated-20261125/v17.10.9-r03-pour-diagnostic-201540/diagnose_r03_pour.py` L1–L301；历史取数L24–L53、候选组L56–L66、仅计算的SavedFingerReadback L69–L82、绑定点云与目标变换L149–L180、虚拟夹指几何L182–L193、有界qualify L236–L272、实际state/time回读L279–L287。 / Local diagnostic script: historical inputs, candidate groups, calculation-only finger readback, payload/target transforms, bounded qualification and real-state readbacks.
- [新增 / Added] 同目录 `diagnostic-config.json` L1–L10：历史run/commit/assignment/feedback路径、clearance0.048/0.04与tilt1rad/hold2s。 / Historical sources and parameters remain explicit in the local configuration.
- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L294–L302：静态诊断范围、近似、审阅及启动。 / Diagnostic scope, approximation, review and launch.

```python
# Calculation inputs only; never written to robot or scene.
relation = np.linalg.inv(saved_tcp) @ saved_observed_body
source_lip = _task_conditioned_pour_feature(source_rim, destination_rim)
model.finger_boxes = historical_finger_boxes  # Original geometry with saved-position readback.
qualified = model.qualify(points, source, relation, 'pour', supported_pose,
                          initial_joints=saved_q, initial_pose=saved_tcp, progress=progress)
```

### 验证与进度 / Validation and progress

- [eval] [exp] [完成] 脚本python语法编译、Ruff通过；主会话审阅通过后20:19:01以PID507170启动，无新AgentLoop任务。 / [Completed] Python syntax compilation and Ruff passed; parent review authorized the20:19:01 launch (PID507170), without a new AgentLoop task. (local)
- [eval] [exp] [完成] 20:21:21已完成32条、0可行，真实关节/time前后一致；不新增生产机制或放宽约束。 / [Completed] At20:21:21 all32 candidates completed without a feasible route; real joints/time were unchanged, with no production mechanism or relaxed constraint. (local)

### 实测结果 / Measured result

- [eval] [exp] [完成] 32条/139.538秒：6 robot collisions、6 payload collisions、10 IK失败、10 continuity失败；无可行路线，达到预算后停止。FK(savedq)与savedtcp位置/旋转误差均0，真实关节/time前后一致（0.0020833334419876337s），历史finger几何参与7632次检查。 / [Completed]32 candidates in139.538s produced6 robot collisions,6 payload collisions,10 IK failures and10 continuity failures, then stopped at the budget. Saved FK/TCP errors were zero; real joints/time stayed unchanged, and historical-finger geometry participated in7632 checks. (local)
- [eval] [exp] [完成] 捕获rim中心与末帧observed origin差范数0.047650mm；新鲜BEAKER比历史物理姿态高0.967681mm。此为静态近似，未找到45度对角补充可行路线，不证明全方位不可行。 / [Completed] Captured-rim center differed from terminal observed origin by0.047650mm; fresh BEAKER geometry was0.967681mm higher than the historical physical pose. This approximate static sample found no feasible diagonal extension and does not prove universal infeasibility. (local)
- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L304–L312：分组失败统计、近似误差、无运动证据与结论边界。 / Grouped failures, approximation metrics, no-motion evidence and bounded conclusion.

```diff
- diagnostic_status = pending
+ diagnostic_status = completed_static_diagnostic_only
+ candidates = 32; feasible = 0
+ failure_counts = {robot_collision: 6, payload_collision: 6, IK: 10, continuity: 10}
+ actual_joints_unchanged = true; simulation_time_unchanged = true
+ execution_authorized = false; readiness_or_admission = false
```

## v17.10.8 (2026-11-25 19:16) - codex

- [env] [exp] [完成] 在独立本地运行中对照夹指驱动力：复制173255启动配置，仅新增joint2 max_force_n=60、max_velocity_m_s=0.2，保留joint1 60/0.02、4mm、场景/候选/阈值和R05→R03指令。先初始化只读原60/1200及新60/60的USD/runtime DOF驱动，确认初始化后state/time不变，再启动完整仿真；不改默认配置/生产运动代码。 / [Completed] In an independent local replay, add only finger-joint2 force60N with existing velocity0.2m/s; preserve joint1 60N/0.02m/s,4mm,scene/candidates/thresholds and R05→R03 instruction. Read USD/runtime drives after initialization without subsequent state/time changes before executing simulation; default configurations and production motion code remain unchanged. (local)
- [docs] [docs] [完成] 更新报告、只读readback及录像索引；检验驱动不对称假设，不预先认定根因。前轮预算接线修复提交efb217c9。 / [Completed] Document readbacks and videos to test the asymmetric-drive hypothesis without assuming causality. Previous budget-wiring commit: efb217c9. (local)

### 文件变更与证据 / File changes and evidence

- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L248–L262：驱动力假设、独立只读诊断、初始化读数及实际启动。 / Document force hypothesis, independent read-only initialization and launch.
- [新增 / Added] 本地运行 `out/labutopia-elevated-20261125/v17.10.8-r05-r03-symmetric-force-191713/`：launch.py L1–L57、diagnose_drives.py L1–L58及physics配置；运行产物留本地。 / Local launcher, read-only diagnostic and comparison physics, retained outside Git.

```diff
 drives = [joint1(max_force_n=60.0, max_velocity_m_s=0.02)]
+drives += [joint2(max_force_n=60.0, max_velocity_m_s=0.2)]
- readback_joint2_max_force_n = 1200.0
+ readback_joint2_max_force_n = 60.0
```

### 验证 / Validation

- [env] [exp] [完成] 原/新两次初始化后USD/runtime DOF与gains比较：仅joint2力上限1200→60，速度/gains不变；两次读取前后关节/time相同，无初始化后运动指令。首次get_gains接口错误已更正为controller只读调用。 / [Completed] Both initialization readbacks confirm only joint2 force changes1200→60; velocities/gains and post-initialization state/time remain unchanged with no commands. Corrected the first diagnostic API mismatch to controller readback. (local)
- [env] [exp] [完成] 19:22:58启动完整新任务，20:04:00以R03持瓶倾倒准备不可用终止failed，未达成双瓶目标。 / [Completed] The fresh task ran from19:22:58 to20:04:00 and ended failed at R03 held-object preparation; the dual-bottle goal is incomplete. (local)

### Git 提交 / Git Commit

- 执行代码 / Execution code: `efb217c9`（已推送 / pushed）；分支 / Branch: `feature/planning-loop`。启动证据提交 / Launch evidence commit: `378e200a`（2026-11-25 19:26:17 +08:00，已推送 / pushed）；本终态证据待主会话审阅提交。 / Final evidence awaits parent review and commit.

- [env] [exp] R05三阶段成功，倾倒连续保持2.816667s，归位误差0.202405mm。双侧首次有效载荷至闭合末的推移方向反转但仍侧移，117/117 lift有效；R03待执行。报告新增L264–L270。 / R05 completed all three phases with2.816667s aligned hold and0.202405mm return error. Bilateral-load-to-close-end displacement reversed but persisted, and117/117 lift samples were valid; R03 remains pending. Report lines264–270. (local)

- [docs] [docs] R05同任务完整合辑118.800秒、16章节，ffprobe及完整解码通过；报告L272新增视频与R03执行中进展。旧R03闭合统计同样明确为双侧有效载荷首样本起算（报告L250）。 / The118.800-second R05 same-task compilation has16 chapters and passed probing/full decoding; reportL272 records the video and active R03 execution. Prior R03 close statistics explicitly use the first bilateral-valid-load sample (reportL250). (local)

- [env] [exp] R03 acquire成功：119/119 lift双侧载荷有效、116/119 grasp_valid，末attachment8.133123mm、上升60.114342mm；不改变阈值，后续倾倒/归位仍进行。报告L274–L280记录回执和首双侧有效close统计。 / R03 acquisition succeeded with119/119 bilateral-load-valid and116/119 grasp-valid lift samples, final8.133123mm attachment error and60.114342mm rise. Thresholds are unchanged; pouring/placement remain active. ReportL274–L280 records the receipt and bilateral-valid-close comparison. (local)

```diff
- R03 = awaiting acquisition result
+ R03 acquire = succeeded; lift bilateral contact load 119/119
+ lift grasp_valid = 116/119; final attachment error = 8.133123 mm
+ R03 pour/place = pending; same task continues
```

### 终态证据 / Terminal evidence

- [env] [exp] [完成] 20:04:00同一任务failed，R05全周期成功、R03 acquire成功；prepare_held返回pour_route_unavailable，failed_phase=prepare、possession_state=holding、requires_replan=false，6 revisions/0 replans。未执行R03倾倒/归位，无安全恢复回执。 / [Completed] The same task ended failed at20:04:00 after full R05 success and successful R03 acquisition; held preparation returned pour_route_unavailable with holding possession, no replan request,6 revisions and0 replans. R03 pouring/placement did not execute and no safe-recovery receipt exists. (local)
- [docs] [docs] [完成] 最终合辑178.433333秒、25章节通过ffprobe与完整解码，1:58.800进入R03，末章节标注后续准备失败；60行原始诊断另存运行目录r03-pour-route-unavailable.txt。 / [Completed] The178.433333-second,25-chapter final compilation passed probing and full decoding; R03 begins at1:58.800 and the last chapter labels subsequent preparation failure. The run directory retains all60 raw diagnostic lines. (local)

- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L282–L292：终态、持瓶准备失败边界、视频与对照证据范围。 / Terminal result, held-preparation failure boundary, video and comparison limits.

```diff
- overall = running; R03 pour/place pending
+ overall = failed; R05 complete; R03 acquire succeeded
+ failed_tool = manipulation.prepare_held; error = pour_route_unavailable
+ possession = holding; requires_replan = false; replans = 0
+ R03 pour/place/safe-recovery receipts = absent
+ final_video = 178.433333 s; 25 chapters; full decode passed
```

- [eval] [exp] 本轮验证为真实Isaac仿真、顺序只读drive实测及终态视频/回执，不重复运行已通过Host单测；未改生产代码或默认physics。 / Validation consists of actual Isaac execution, sequential read-only drive measurements and terminal video/receipts; already-passed Host tests were not repeated. Production code and default physics remain unchanged. (local)

## v17.10.7 (2026-11-25 19:13) - codex

- [env] [fix] [完成] 修复Isaac agent_host预算接线：compose_host新增默认2的max_replans并传入Coordinator，run_instruction传递现有verification.max_replans_per_episode，保留显式0。 / [Completed] Wire the existing verification replan budget through run_instruction and compose_host to Coordinator, retaining default2 and explicit0. (local)
- [eval] [fix] [完成] 使用无运动测试验证默认2、自定义4、显式0及真实配置读取路径；stub外部LLM/感知，不启动仿真。 / [Completed] Test default2, custom4, explicit0 and real configuration loading without motion, stubbing external model/perception. (local)
- [docs] [docs] [完成] 更新报告、精确行号/Diff和最近五条；前轮最终证据提交为d1ce17b7。预算及生命周期由Coordinator拥有，Provider和物理参数不变，不新增schema/gate。 / [Completed] Update report, lines/diff and latest five entries; previous final evidence commit is d1ce17b7. Coordinator retains budget/lifecycle ownership; provider and physical settings remain unchanged without new schemas or gates. (local)

### 所有权与验证边界 / Ownership and validation boundaries

- Host只将已有配置接入Coordinator；预算与生命周期、取消、结算、恢复归Coordinator，Provider不变且可替换，不新增契约。使用当前加载配置为新任务构建Coordinator，不改变旧任务证据。最小失败测试是配置4却得到2；无运动配置集成测试揭示该接线遗漏。 / Host only forwards existing configuration; Coordinator owns budget/lifecycle/cancellation/settlement/recovery, providers remain replaceable and contracts unchanged. Current configuration initializes new task composition without altering historical evidence. The minimal regression is configured4 becoming2, exposed by no-motion configuration integration tests.

### 文件变更详情 / File changes

- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py` L134、L150、L217：增加默认2参数并接通配置→Host→Coordinator。 / Add the default2 parameter and wire configuration through Host to Coordinator.
- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py` L5、L144、L201–L238：默认值断言及真实配置加载的2/4/0无运动测试。 / Add default assertion and real configuration-loading no-motion cases for2/4/0.
- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L234–L246：记录根因、所有权、测试及前轮提交d1ce17b7。 / Record root cause, ownership, validation and prior final-evidence commit d1ce17b7.
- [修改 / Modified] `CHANGELOG.md`：最近五条为17.10.7至17.10.3，与月档全文一致。 / Latest five entries17.10.7 through17.10.3 match their archive records.

```diff
diff --git a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py
index ddb77d30..5e2e23c8 100644
--- a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py
+++ b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py
@@ -131,7 +131,7 @@ Report only measured no-liquid manipulation, never transferred volume or chemica

 def compose_host(*, profile, workspace, provider, inference, model, sensor_ref, execute=False,
                  execution_timeout_s=1800, max_agent_provider_retries=2,
-                 agent_provider_retry_delay_s=1.0):
+                 agent_provider_retry_delay_s=1.0, max_replans=2):
     workspace = Path(workspace).expanduser().resolve()
     workspace.mkdir(parents=True, exist_ok=True)
     artifact_root = workspace / "artifacts" / "labutopia"
@@ -147,6 +147,7 @@ def compose_host(*, profile, workspace, provider, inference, model, sensor_ref,
         workspace=workspace, config=ForgeConfig(execution_timeout_s=execution_timeout_s), client=None,
         max_agent_provider_retries=max_agent_provider_retries,
         agent_provider_retry_delay_s=agent_provider_retry_delay_s,
+        max_replans=max_replans,
     )
     assignments = SQLiteAssignmentArtifactStore(workspace / "assignment-artifacts.sqlite3")
     bundle = build_labutopia_runtime(
@@ -213,6 +214,7 @@ async def run_instruction(*, profile, workspace, config_path, instruction, senso
         sensor_ref=sensor_ref, execute=execute, execution_timeout_s=execution_timeout_s,
         max_agent_provider_retries=config.agents.verification.max_agent_provider_retries,
         agent_provider_retry_delay_s=config.agents.verification.agent_provider_retry_delay_s,
+        max_replans=config.agents.verification.max_replans_per_episode,
     )
     session_key = f"cli:lab-{uuid4().hex[:12]}"
     # Deployment guidance belongs to the system context, separate from the instruction.
diff --git a/examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py b/examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py
index 7d3f5776..efa3a343 100644
--- a/examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py
+++ b/examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py
@@ -2,7 +2,7 @@ import asyncio
 import json
 from dataclasses import replace
 from types import SimpleNamespace
-from unittest.mock import Mock
+from unittest.mock import AsyncMock, Mock

 import pytest

@@ -141,6 +141,7 @@ def test_host_enrolls_real_subtask_contract_and_rejects_other_actions(tmp_path,
             agent_provider_retry_delay_s=3.5)
         try:
             assert coordinator.config.execution_timeout_s == 1800
+            assert coordinator.max_replans == 2
             assert coordinator.max_agent_provider_retries == 5
             assert coordinator.agent_provider_retry_delay_s == 3.5
             adapter = loop.long_horizon_controller.adapter
@@ -195,3 +196,43 @@ def test_host_enrolls_real_subtask_contract_and_rejects_other_actions(tmp_path,
             bundle.client.close()
             assignments.close()
     asyncio.run(run(tmp_path))
+
+
+@pytest.mark.parametrize('budget', [None, 4, 0], ids=['default', 'four', 'disabled'])
+def test_run_instruction_applies_loaded_replan_budget(tmp_path, monkeypatch, budget):
+    from isaacsim_lab import agent_host
+
+    verification = {} if budget is None else {'maxReplansPerEpisode': budget}
+    config = tmp_path / 'config.json'
+    config.write_text(json.dumps({
+        'agents': {'defaults': {'model': 'openai/test-model'}, 'verification': verification},
+        'providers': {'openai': {'apiKey': 'test-only-key'}},
+    }))
+    for name in ('camera.yaml', 'scene.usd', 'robot.usd'):
+        (tmp_path / name).write_text('test fixture; never loaded by a simulator')
+    profile = LabUtopiaProfile.from_mapping({
+        'lab_root': str(tmp_path), 'config_path': 'camera.yaml',
+        'scene_usd_path': 'scene.usd', 'robot_usd_path': 'robot.usd',
+        'source_path': '/World/source', 'destination_path': '/World/destination',
+    }, base_dir=tmp_path)
+    provider = Mock(generation=SimpleNamespace(max_tokens=2048), _client=None)
+    monkeypatch.setattr('PhyAgentOS.cli.commands._make_provider', lambda *a, **k: provider)
+    monkeypatch.setattr('openai.OpenAI', lambda **kwargs: Mock(close=kwargs['http_client'].close))
+    monkeypatch.setattr(agent_host, 'build_visual_providers', lambda *args: (Mock(), Mock()))
+    monkeypatch.setattr(agent_host.AgentLoop, 'process_direct', AsyncMock(return_value='no motion'))
+    monkeypatch.setattr(agent_host.AgentLoop, 'wait_for_long_horizon_tasks', AsyncMock(return_value=[]))
+    composed = []
+
+    def capture_host(**kwargs):
+        result = compose_host(**kwargs)
+        composed.append(result[1])
+        return result
+
+    monkeypatch.setattr(agent_host, 'compose_host', capture_host)
+    report = asyncio.run(agent_host.run_instruction(
+        profile=profile, workspace=tmp_path, config_path=config,
+        instruction='Read-only configuration check', sensor_ref='sensor://front',
+    ))
+    assert composed[0].max_replans == (2 if budget is None else budget)
+    assert report['simulated_motion_enabled'] is False
+    assert report['tasks'] == []
```

### 验证 / Validation

- [eval] [fix] 上述报告命令：15 passed；两个代码文件Ruff、git diff --check通过；无仿真/硬件运动。 / The documented command passed15 tests; both files passed Ruff and diff whitespace checks; no simulation or hardware motion.

### Git 提交 / Git Commit

- 前轮最终证据 / Previous final evidence: `d1ce17b7`；分支 / Branch: `feature/planning-loop`。本修复待主会话审阅提交。 / This repair awaits parent review and commit.

## v17.10.6 (2026-11-25 16:50) - codex

- [env] [exp] [完成] 使用已提交 2dcf0aaa 的 stale 重采集修复启动独立 R05→R03 连续 AgentLoop 仿真；复制 155843 的配置仅替换运行路径，保留 4 mm/60 N、原任务与安全检查，保存阶段录像。 / [Completed] Replay the continuous R05→R03 AgentLoop task on committed 2dcf0aaa, copying 155843 configuration with run paths replaced and preserving 4 mm/60 N, task instruction and safety checks; retain annotated phase videos. (local)
- [docs] [docs] [完成] 更新 docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md 与 CHANGELOG.md，记录启动命令、进程、终态证据和精确行号/Diff。 / [Completed] Update the continuation report and changelog index with launch command, processes, outcome evidence and precise lines/diff. (local)

### 文件变更详情 / File changes

- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L164–L232：记录两次启动、重启中断、R05成功、R03失抓恢复与二次准备，含配置一致性、证据和视频。 / Record both launches, reboot interruption, R05 success, R03 recovery and second preparation with configuration/evidence/video details.
- [新增 / Added] `out/labutopia-elevated-20261125/v17.10.6-r05-r03-stale-recapture-165053/launch.py` L1–L57 及同目录配置：沿用 155843 启动器，运行产物保留本地。 / Reuse the 155843 launcher and configurations; retain run artifacts locally.

```diff
- run = out/labutopia-elevated-20261125/v17.10.4-r05-r03-route-recovery-155843
+ run = out/labutopia-elevated-20261125/v17.10.6-r05-r03-stale-recapture-165053
- git_commit = 69f2724f60b3acc6e85da7ab9945b6f215879ce8
+ git_commit = 2dcf0aaa0c670c991d495cc05d8fd1734a5abc30
```

### 验证 / Validation

- [eval] [exp] 13 个配置/脚本归一化路径后与 155843 一致；JSON/Python 语法及文件依赖通过，AgentLoop 于 16:51:14 进入 task_creation，终态待实际回执。 / All 13 files match 155843 after path normalization; JSON/Python syntax and file dependencies passed, AgentLoop entered task_creation at 16:51:14, final outcome awaits receipts.

### Git 提交 / Git Commit

- 执行代码 / Execution code: `2dcf0aaa`；分支 / Branch: `feature/planning-loop`。中间证据提交 / Interim evidence commit: `4ca78c5d`，2026-11-25 18:48:31 +08:00，已推送；运行仍进行中，后续回执统一补记。 / Pushed at 18:48:31 +08:00; execution continues and later receipts will be recorded together.

### 主机重启中断与复跑计划 / Host restart and replay plan

- [env] [exp] [完成] 165053 未生成 acceptance.json，最后已完成回执为 R05 acquire succeeded；主机于 2026-11-25 17:25:38 重新启动，原仿真场景及进程已消失，不能复用旧 holding 状态。旧启动日志出现 memory pressure，但尚未确认重启根因；此结果记录为执行中断，不判定动作失败。保留旧工件，以相同代码、原任务和 4 mm/60 N 参数创建独立新场景完整复跑。 / [Completed] Run 165053 has no acceptance.json; the last completed receipt is R05 acquire succeeded. The host rebooted at 17:25:38, losing the simulation and processes, so prior holding state cannot be reused. Memory-pressure messages do not establish the reboot cause. Record an interrupted execution rather than action failure; preserve artifacts and replay the full task in a new scene with unchanged code and 4 mm/60 N settings. (local)
- [env] [exp] 启动前资源实测：可用 RAM 20 GiB、swap 余量13 GiB、工作盘余量58 GiB、RTX5060Ti 16311 MiB中已用5502 MiB。 / Pre-launch resources: 20 GiB available RAM, 13 GiB free swap, 58 GiB free disk, GPU 5502/16311 MiB used. (local)

- [env] [exp] [进行中] 17:32:55 已启动独立 173255 轮，Launcher15236/Host15237/观察器15238；13 个配置/脚本仅替换路径，执行代码仍为2dcf0aaa。 / [In progress] Started independent replay 173255 at 17:32:55, with launcher15236/host15237/observer15238; thirteen files differ only in paths and execution code remains 2dcf0aaa. (local)
- [docs] [docs] 报告新增 L176–L186，区分重启中断与动作失败并记录新运行命令；新增运行目录 `v17.10.6-r05-r03-post-reboot-173255` 的启动器 L1–L57，未复用旧场景状态。 / Append report lines176–186 to distinguish reboot interruption from action failure and document replay; the new run reuses launcher lines1–57 without old scene state. (local)

```diff
- active_run = v17.10.6-r05-r03-stale-recapture-165053
+ interrupted_run = v17.10.6-r05-r03-stale-recapture-165053
+ active_run = v17.10.6-r05-r03-post-reboot-173255
```

- [env] [exp] [完成] 173255 R05全周期实跑成功，倾倒1.0027256rad连续保持2.833333s，归位误差0.9005mm；R03待完成。 / [Completed] R05 completed its full cycle in 173255 with 1.0027256rad tilt, 2.833333s aligned hold and 0.9005mm return error; R03 remains pending. (local)
- [docs] [docs] 报告新增L188–L194及本地视频索引：保存同任务R05合辑160.250秒/16章节，ffmpeg完整解码通过。 / Append report lines188–194 and local video index for a 160.250-second, 16-chapter same-task R05 video; full ffmpeg decoding passed. (local)

- [env] [exp] R03候选-8搜索600.928秒超时后，原Action继续候选-12准备；尚无R03运动。报告新增L196–L202，每个 composite subtask 的 Coordinator Action reconciliation 预算保持3600秒。 / After R03 candidate -8 timed out at 600.928 seconds, the same Action continued preparation of candidate -12; no R03 motion yet. Append report lines196–202 and retain the 3600-second Coordinator Action reconciliation budget per composite subtask. (local)

- [env] [exp] R03候选-12获得路线，实抓抬升发生physical_grasp_lost，安全松夹回撤成功；原Agent同任务重新观察继续准备，R03未完成。报告新增L204–L212，记录接触载荷/支撑和视频章节。 / Candidate -12 found a route but lost grasp during lift; safe release and retreat succeeded, and the same Agent task resumes fresh preparation. R03 remains incomplete; report lines204–212 record contact/support evidence and video chapters. (local)

### 中间验收 / Interim acceptance

- [docs] [docs] [完成] 报告L214–L220补二次候选与首抓提案差异（5.190 mm/0.3403°），明确R03仍在准备，双瓶未完成；恢复合辑277.333秒完整解码通过。 / [Completed] Report lines214–220 compare the second candidate with the first proposal (5.190 mm/0.3403 degrees), retain incomplete dual-bottle status, and record the fully decoded 277.333-second recovery compilation. (local)
- [chore] [chore] 本轮无生产代码变更；执行配置/指令按原设置复制，已有104测试未重复。实际运行证据与日志均UTF-8可读，git diff --check通过；当前仅提交中间记录，运行继续。 / No production code changed; settings/instruction were copied unchanged and prior104 tests were not repeated. Live simulation evidence and UTF-8 records are readable, diff whitespace checks passed; this is an interim record while execution continues. (local)

```diff
- latest_evidence = v17.10.5 unit tests; simulation not started
+ R05 = acquire/pour/place succeeded in task_8f67e002d7364db8
+ R03_first = physical_grasp_lost; returned_to_safe_pose=true; observation_ready=true
+ R03_second = fresh scene revision :4; candidate 09ae...-8; preparation in progress
+ overall = in progress, dual-bottle completion not established
```

### 最终验收 / Final acceptance

- [env] [exp] [完成] 19:07:56 acceptance确认任务failed：R05完整成功，R03两次physical_grasp_lost且均安全恢复；第二次恢复后Coordinator实际replan上限2耗尽。启动配置4与实际2的差异待定位，双瓶目标未完成。 / [Completed] Acceptance at19:07:56 records failure: R05 succeeded, both R03 attempts lost grasp and safely recovered, then actual Coordinator replan limit2 was exhausted. Requested4 versus effective2 remains to diagnose; the dual-bottle goal is incomplete. (local)
- [docs] [docs] 报告新增L222–L232；最终381.050秒/30章节合辑完整解码通过，标注任务失败并保留两次恢复。 / Append report lines222–232; the final381.050-second,30-chapter video passed full decoding and labels task failure with both recoveries. (local)

```diff
- R03_second = preparation in progress
- overall = in progress
+ R03_second = physical_grasp_lost; safe recovery succeeded
+ overall = failed; replan budget exhausted (2)
+ evidence = same-task R05 success and two R03 recoveries; dual-bottle goal incomplete
```
