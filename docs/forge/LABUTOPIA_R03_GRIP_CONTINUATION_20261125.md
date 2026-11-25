# R03 夹持单变量复跑记录 / R03 grip continuation

日期：2026-11-25（Asia/Shanghai）。状态：`142657` 已失败结束；修复版 `150350` 的 R05 抓取、倾倒、归位全周期成功；R03 路线搜索超时，任务失败，R03 未运动。

## 用户目标 / Required outcome

在同一 Isaac 无液体仿真场景、同一 AgentLoop 任务内依次执行 R05 → R03。每瓶完成抓取、抬升、移到 BEAKER 上方、对准后倾倒 1.0 rad 并连续保持至少 2.0 s、扶正、原位放回、松夹与后撤。第一瓶结算后重新观察现场，再准备第二瓶。

允许执行失败。失抓后依据实测支撑、接触与持有状态恢复，安全松夹和回撤后重新观察，在原任务内重新准备并抓取，保留已完成动作。轻微位姿偏移按实际持瓶和任务反馈处理。有进展的轮次保留按瓶号、阶段和结果标注的录像。

Execute R05 then R03 in one continuing scene and one AgentLoop task. Each vessel must complete acquisition, aligned 1.0 rad pouring for at least 2.0 s, original-slot placement, release and retreat. Recover from failures using measured physical state and fresh observations within the same task, preserving settled work and annotated execution videos.

## 已有证据 / Prior evidence

| 轮次 | 观测结果 | 对本轮的含义 |
| --- | --- | --- |
| 2026-11-25 `061939` | 60 N 驱动上限；R05 完整成功，R03 抬升失抓，安全开夹前台面承重约 80% 瓶重，未满足 90% 条件。 | 当前对照轮；提高驱动上限后 R03 仍失败。 |
| 2026-11-25 `050752` | R05 完成；R03 首次失抓后松夹回撤成功，Agent 在同一任务中重新观察并第二次实际抓取，第二次抬升仍失抓。 | 同任务恢复及重抓已执行，双瓶完成尚未成立。 |
| 2026-11-22 `173044` | R03 抓取及倾倒成功，归位受阻；夹持压入量为 4 mm。oracle 同时使用 `tilt_angles_rad=[0.0]` 和不同的 `bottle_depth_fractions`。 | 历史成功运行支持验证 4 mm；候选配置也不同，因此不能据此确认压入量是失败根因。 |

历史录像与回执索引：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261124/review-videos/README.md`。

## 本轮配置 / Current experiment

- 版本记录：`v17.10.3`；执行代码 commit：`4e06f62fab886c0a4fc034bf49f49ad49c09b2b6`（Adapter `17.10.2`）。
- 新运行：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/v17.10.3-r05-r03-4mm-142657`。
- 对照运行：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261124/v17.10.2-r05-r03-agent-loop-60N-061939`。
- 新录像目录：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos`。
- 唯一物理配置差异：`labutopia-ridgebase-elevated-motion.json` 中夹持压入量从 2 mm 改为 4 mm。

```diff
-  "finger_retain_overshoot_m": 0.002,
+  "finger_retain_overshoot_m": 0.004,
```

驱动上限保持 60 N。新旧运行路径归一化后，profile、oracle、physics、manifest 内容一致；JSON、Python 语法、profile 文件引用及 USD 外部资产引用均已检查。新运行使用独立工件和任务数据库。

## 所有权与坐标 / Ownership and frames

AgentLoop 与 Coordinator 拥有语义顺序、任务修订、恢复选择、取消和结算。Isaac Adapter 拥有夹指目标生成、物理接触反馈、支撑判断、运动资格检查和执行。改动使用既有 Adapter 私有配置项，Tool 公共契约保持一致。

场景和坐标继承 `061939` 的 elevated USD、世界坐标、机器人安装位置与 TCP 标定。碰撞、工作空间、关节连续性、接触和支撑检查沿用原配置。失败和未知持有状态仍按现有停机与恢复路径处理。阶段回执、scene revision 和视频共同确定本轮执行证据；第二瓶准备使用第一瓶完成后的新观测。

## 验证与启动 / Validation and launch

初始回归为 **287 passed**；末端校正修复后运行同一命令，结果 **291 passed**：

```bash
PYTHONPATH=examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src \
  .venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py \
  examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py --tb=short
```

首次测试命令遗漏 `pick-place-workflow/src`，导致 105 项失败；补全 PYTHONPATH 后已通过上述回归。该失败属于测试启动环境错误。

运行启动命令（工作目录 `/home/yanxu/PhyAgentOS-forge`）：

```bash
.venv/bin/python -u out/labutopia-elevated-20261125/v17.10.3-r05-r03-4mm-142657/launch.py
```

Launcher PID 为 `889386`，输出写入本轮 `launcher.log`；Host 输出写入 `host.log`，录像处理输出写入 `watch_completed.log`。2026-11-25 14:27:00，AgentLoop 已进入任务创建模型调用。

## 执行结果 / Execution result

`142657` 的任务为 `task_1a459661e3724931`。R05 抓取成功、抬升约 58.54 mm；倾倒峰值为 1.0027256338 rad，连续对准保持 2.8333334811 s。退出阶段一次校正将瓶口轴误差从 0.3076176026 rad 降至 0.0342986536 rad，仍超过原有 0.02 rad 要求，因此以 `measured_postcondition_failed` 失败结束。瓶口位置误差为 1.113 mm。R05 未归位，R03 未执行；本轮尚不能判断 4 mm 对 R03 的效果。

- 抓取视频：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/142657_R05_抓取抬升_成功_cb72cbc1.mp4`。
- 倾倒视频：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/142657_R05_倾倒_失败_5924698a.mp4`。章节：00:00 移动至烧杯上方；00:30.517 倾倒与保持；00:41.200 扶正并离开烧杯。
- 失败回执：本轮 `artifacts/labutopia/phase-feedback/9a140b5f46dd46c69ec511e827010963.json`；任务回执：本轮 `acceptance.json`。

## 末端反馈校正修复 / Terminal correction repair

`phase_motion.py` 对已经重新资格化的倾倒退出路径，将末端校正从一次扩展至最多三次。每次先测量瓶口位置和轴误差，达到原阈值即完成；仍超限则检查当前接触、读取实测 attachment 并复用既有求解和运动循环。三次仍不达标，由原最终后置条件判失败。碰撞、连续性、取消和执行步数检查继续生效。

回执保留首次 `tip_error_before_m` / `axis_error_before_rad` 和最终 after 值，并记录 `attempt_count`。普通未重新资格化的倾倒及搅拌不进入该循环。

回归增加两次校正成功、持续漂移三次仍失败、第二次校正前失抓、第二次碰撞拒绝和取消覆盖。阶段运动与接触时序合计 **291 passed**，`git diff --check` 通过。Ruff 全文件仍有四项既有诊断，已与 HEAD 逐项对照：`phase_motion.py:1061` 的 I001；`test_phase_motion.py:3328`、`:3414` 的 E731；测试文件原 `:4059`、现 `:4100` 的 I001。修改部分无新增诊断。

契约及模拟单元测试已通过；修复后的 Isaac 倾倒退出阶段已实跑成功，双瓶任务最终失败，R03 未运动。

## 修复版实跑进展 / Repaired execution progress

运行绝对路径：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/v17.10.3-r05-r03-exit-feedback-150350`。任务：`task_6559745fef2c4afc`。执行代码：`b985bf98`；沿用 `142657` 的全部物理与候选配置（4 mm、60 N）。

R05 抓取成功，倾倒阶段回执 `artifacts/labutopia/phase-feedback/6386fe150421405d9775dca466380c17.json` 判定 `succeeded`。两次末端校正将轴误差从 0.3076176026 rad 降至 0.0011673941 rad，瓶口位置误差从 0.0130169489 m 降至 0.00016727365 m；连续对准保持 2.833333 s，峰值 1.0027256 rad。原位置及轴误差阈值均已满足。

R05 归位回执 `artifacts/labutopia/phase-feedback/05bddd6a4d64406b9d9dce172de41e65.json` 已判定 `succeeded`，完成原位放回、松夹与后撤；归位位置误差 0.0009004684613 m（0.9005 mm），旋转误差 0.0064321349 rad。R05 全周期成功；R03 路线搜索超时，任务最终 failed，R03 未运动。

The repaired run completed R05 acquisition and pouring. Two feedback corrections reduced axis error to 0.0011673941 rad and tip error to 0.00016727365 m while preserving the original thresholds. R05 placement, release and retreat also succeeded, with a return position error of 0.9005 mm. R03 acquisition route search timed out; the task failed before R03 motion.

## R05 全周期合辑 / R05 complete-cycle video

绝对路径：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/150350_R05全周期成功_R03未完成_同一AgentLoop.mp4`。

合辑将同一任务 `task_6559745fef2c4afc` 的三个成功阶段按实际顺序拼接，原片保留。时长 160.250 s，保留 16 个阶段章节；标题明确标注“R05 全周期成功 / R03 未完成”。已通过 ffprobe 元数据检查及 ffmpeg 完整解码检查。

- 00:35.200：移动至烧杯上方。
- 01:05.717：倾倒与保持；峰值 1.0027256 rad，连续对准保持 2.833333 s。
- 01:16.400：扶正并离开烧杯；两次末端反馈校正成功。
- 02:06.133：扶正并移回原位。
- 02:32.100：下降到原位置。
- 02:36.700：松开夹爪；02:37.316：后撤。归位位置误差 0.9005 mm。

The 160.250 s video concatenates three successful R05 phases from the same task, preserves 16 chapters and labels R03 as incomplete. Original clips remain available. Video artifacts are stored outside the Git commit.

## 150350 终态与准备超时分类 / Final status and preparation timeout

任务 `task_6559745fef2c4afc` 最终为 `failed`，重规划次数为 0。R05 全周期成功；R03 在准备阶段出现 `route_search_timeout`，未执行运动。搜索工件 `artifacts/labutopia/acquire-search/2b8ee5f6fb724ed09272e7ea2dffadfe.json` 记录用时 600.3088 s、107 次尝试、99 次剪枝和 269 个变体。该有限搜索超时不能代表所有可能路线均不可行。

`LabUtopiaCycleProvider.prepare` 的候选拒绝分类遗漏 `route_search_timeout`，使该结果直接进入默认运行合同错误，返回不可重规划的 `fix_runtime_contract`。v17.10.4 把该码加入既有候选拒绝、可重规划和重选建议集合：原始错误码/消息留在 rejected 诊断；后续已供应候选可继续准备；全部已供应候选失败时沿用 `no_admissible_grasp`、`requires_replan=true`、`select_alternative_candidate` 和实际失败 refs。

搜索机制由 Adapter 拥有，候选选择和重规划仍由 AgentRecoveryDecisions/Coordinator 拥有，Runtime 执行所有权保持原路径。该修复不改变物理阈值或搜索时限，也不把准备结果计作运动成功。

验证命令：

```bash
PYTHONPATH=examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/scene-understanding-http/src:examples/forge-skills/pick-place-workflow/src \
  .venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py \
  tests/test_recovery_decisions.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py --tb=short
```

结果：**89 passed**。覆盖超时后后续候选成功且保留原码/消息、两个候选均拒绝时的聚合建议和 refs、其他合同错误立即拒绝，以及既有恢复决策/子任务传播。两个修改代码文件的 Ruff 检查通过；v17.10.4 仿真已停止于 waiting_for_user，归位准备报告观测“不可用或过期”。

## v17.10.4 新轮次启动 / New replay launch

已推送实现提交 `69f2724f60b3acc6e85da7ab9945b6f215879ce8`。新运行绝对路径：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/v17.10.4-r05-r03-route-recovery-155843`。全部物理/候选配置和任务指令沿用 `150350`（仅路径改至新目录）；本次代码差异为候选准备超时分类修复。新目录使用独立工件、任务数据库和会话。

启动命令（仓库根目录）：

```bash
.venv/bin/python -u out/labutopia-elevated-20261125/v17.10.4-r05-r03-route-recovery-155843/launch.py
```

2026-11-25 15:58:43 +08:00 启动，Launcher PID `1006855`、Host PID `1006858`、录像观察器 PID `1006859`。15:58:46，AgentLoop 进入任务创建模型调用，session `cli:lab-f0def334d3f4`。录像继续保存到本日 `review-videos`；启动时生产代码 diff 为空。本轮后续停在 waiting_for_user，双瓶未完成。

Replay 155843 started on pushed commit 69f2724f, preserving the previous run's physics, candidates and user instruction. The launcher, host and video observer are running; the run subsequently stopped waiting_for_user.

## 155843 观测过期结果 / Stale observation result

`task_321b838973ed4938` 最终停在 `waiting_for_user`。R05 抓取回执 `604115c42d2247cd82f8488449df46dc.json` 和倾倒回执 `2dab419aa55848059e6a070f02598453.json` 均成功；倾倒两次校正及测量指标与 `150350` 相同。归位准备 refresh_binding 报告观测“不可用或过期”，driver 返回 outcome_unknown，R03 未执行。原始 scene.observe 响应未保存在本轮日志，无法从该消息区分 unavailable 与 stale。

归位观测 calibration `b02c15ef9e8e4062a415ff79fe3d8e41.json` 的写入时间为 16:25:46.326，state `97103928097a4fe697204820a17d503e.json` 为 16:25:47.561，工件写入间隔约 1.235 s，超过 max_age_ms=1000；mtime 仅为间接时序证据。恢复阶段重新观测 `8bd0668bae35481291d7ca9eac499dd3.json` / `8566a86969884c2faf233896e7d04b47.json` 的 freshness 为 540 ms，状态 available。这支持瞬时过期解释，尚不能确认首次原始响应就是 stale。

## v17.10.5 只读重采集修复 / Read-only recapture repair

检查现有绑定实现后，scene.observe 没有 stale 重试路径。同步 `bind` 和异步 `bind_async` 现在仅对明确 `status=stale` 的返回重新采集，最多三次总尝试，继续使用 max_age_ms=1000。仅 available 的新采集身份和工件进入 understand/grasp/capabilities；三次仍 stale 按原可用性检查拒绝，unavailable/invalid/empty 和查询异常立即停止。异步缓存仅保留最后的成功采集结果。

该策略属于通用只读感知绑定编排；Provider 仍拥有采集，Runtime 仍拥有执行与未知结果处理。物理阈值、工具 schema、driver outcome_unknown 语义保持不变。

验证：perception binding、subtask executor 和 Isaac PAOS integration 共 **104 passed**，包含 14 个新增同步/异步重采集案例，以及现有 refresh_binding 的 expected revision 和身份一致性测试。代码与测试 Ruff 通过。尚未启动 v17.10.5 仿真。

```bash
PYTHONPATH=examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/scene-understanding-http/src \
  .venv/bin/python -m pytest -q \
  examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py \
  examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py --tb=short
```

## v17.10.6 连续复跑 / Continuous replay

2026-11-25 16:51:11 +08:00，使用已提交 `2dcf0aaa0c670c991d495cc05d8fd1734a5abc30`（v17.10.5 观测重采集修复）启动新轮次。运行目录：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/v17.10.6-r05-r03-stale-recapture-165053`。Launcher PID `1064556`、Host PID `1064557`、录像观察器 PID `1064558`；16:51:14 进入任务创建，session `cli:lab-23e4b67abf89`。启动不代表任务完成。

复制 `155843` 的 13 个启动配置/脚本，仅替换运行目录；JSON/Python 语法、实际文件依赖和指令一致性检查通过。源/目标 `/World/...` 是 USD prim，未将其视为磁盘文件。物理、候选、世界坐标、TCP 标定和停止/恢复路径均继承 `155843`（4 mm 夹持压入量、60 N 上限）。新运行使用独立数据库和工件，视频由既有观察器标注到同日 `review-videos`。未重复运行此前通过的 104 项测试，本轮验证是实际 Isaac 无液体仿真。

Replay 165053 started on committed 2dcf0aaa with unchanged physics, candidates, coordinate/calibration assumptions, stop/recovery behavior and R05→R03 instruction. Thirteen launcher/configuration files differ only in run-directory references; syntax, filesystem dependencies and instruction checks passed. Separate task/artifact stores and the existing annotated-video observer are active. The previous 104 passing tests are not repeated; actual simulation provides the new evidence. Outcome remains pending.

```bash
.venv/bin/python -u out/labutopia-elevated-20261125/v17.10.6-r05-r03-stale-recapture-165053/launch.py
```

## 165053 主机重启中断与 173255 复跑 / Reboot interruption and replay

165053 的任务 `task_fb7fbc55bef24d9d` 最后已落盘阶段回执为 R05 acquire `succeeded`（`phase-feedback/a529e3ea9c8849aeaae7fcd351a90069.json`）；未生成 acceptance.json，未获得倾倒终态。主机于 2026-11-25 17:25:38 重启，原场景和进程消失。该轮记录为主机重启导致执行中断，不能判为动作失败或双瓶完成。旧启动日志的 memory pressure 提示不能单独确立重启原因；已保留原始工件与视频。

17:32:55 +08:00 使用相同提交 `2dcf0aaa` 和原 4 mm/60 N 配置启动全新完整任务，目录 `/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/v17.10.6-r05-r03-post-reboot-173255`；Launcher `15236`、Host `15237`、录像观察器 `15238`，session `cli:lab-aaabb2d12eff`。13 个启动配置/脚本归一化路径后与 165053 一致；未复制旧数据库、工件或持瓶状态。启动前可用 RAM 20 GiB、空闲 swap 13 GiB、工作盘 58 GiB、GPU 空闲约 10.8 GiB；现有推理服务保持运行。该轮状态待实际回执。

Run 165053 was interrupted by a host reboot, with only R05 acquisition confirmed successful and no final acceptance or pouring receipt. No action failure is inferred. Replay 173255 starts a fresh scene and complete task on the same commit, physics and instruction, preserving old evidence and leaving the existing inference service running. Resource availability was checked because the prior interruption had memory-pressure messages; its cause remains unconfirmed.

```bash
.venv/bin/python -u out/labutopia-elevated-20261125/v17.10.6-r05-r03-post-reboot-173255/launch.py
```

## 173255 R05 全周期结果 / R05 complete cycle

同一任务 `task_8f67e002d7364db8` 的 R05 抓取、倾倒、归位松夹后撤三个回执均 `succeeded`。抓取回执 `75c8a6c0ca094575bc039c0686fd10a6.json`，垂直抬升约58.54 mm；倾倒回执 `151d0885612c43e0b9ab706c3b871432.json`，峰值1.0027256 rad、连续对准保持2.833333 s、瓶口位置误差0.1673 mm、轴误差0.0011674 rad；归位回执 `3e72675907cc4aa3be3104bffe83b841.json`，原位误差0.9005 mm、旋转误差0.006432 rad。原安全阈值和4 mm/60 N保持不变。无液体仿真只证明运动目标，液体转移未测量。

R05合辑绝对路径：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/173255_R05全周期成功_R03待完成_同一AgentLoop.mp4`。160.250秒，来自同一任务的三个阶段，保留16个章节；ffprobe检查与ffmpeg完整解码通过。R03尚待完成，合辑不代表双瓶任务成功。

All three R05 phase receipts succeeded in the same task. Continuous aligned hold reached 2.833333 seconds and original-slot return error was 0.9005 mm. The 160.250-second video retains 16 phase chapters and passed full decoding. This liquid-free simulation proves motion targets only; R03 remains pending.

## 173255 R03 候选搜索进展 / Candidate-search progress

同一任务在 R05 结算并重新观察后进入 R03，scene revision 为 `labutopia-tabletop-rod-rack-v1:5a88bc08455c4b4c9067f34f83fb9ec1:3`。首个候选 `candidate://simulator-truth-R03/b6160a8d743c4295bb6e06b44e7717f6-8` 搜索600.928秒后以 `route_search_timeout` 拒绝：128次尝试、122次剪枝、269个变体；回执 `acquire-search/a811aeefe5d3445b9cddf52034f84964.json`，`world_change_started=false`。

原Action随后自动准备另一个已供应候选 `candidate://simulator-truth-R03/b6160a8d743c4295bb6e06b44e7717f6-12`，由 `acquire-search/c5eef3d3387d497daa898dd0bfec7519.json` 和 fallback `d0c6f4458f864c158c41eaf725272eb2.json` 证明。这是不同候选的准备搜索，尚未发生R03运动，也不是重新执行已完成R05。原 `--execution-timeout-s=3600` 保持不变，其语义为每个 composite subtask 的 Coordinator Action reconciliation 预算，不是从 Host 启动开始计时。

R03 candidate -8 timed out after 600.928 seconds without world changes; the same Action proceeded to supplied candidate -12. This confirms candidate rejection fallback rather than a repeated identical candidate or a restarted task. R03 motion and overall completion remain unproven.

## 173255 R03 首抓失败与安全恢复 / First acquisition and safe recovery

候选-12的第136个路线尝试得到available（`acquire-search/068b7f81d6264a3ca107da7535c8a928.json`），随后真实执行抓取。阶段回执 `phase-feedback/5da98a9cf4d24fa0819b387895053087.json` 为 `failed/physical_grasp_lost`，失败说明为双侧接触载荷在附着运动中丢失；同时 `returned_to_safe_pose=true`、`observation_ready=true`，恢复终点 `qualified_route_start`。原Agent在同一任务重新观察并继续准备，未重做已完成R05。

最后lift样本的双侧接触冲量为 `[0.004484,0] N·s`，contact_load_valid和grasp_valid为false，contact_manifold_valid仍true；瓶体垂直位移仅0.153 mm，attachment误差8.105 mm。原地测量后支撑力0.93923 N、瓶重0.981 N（约95.7%），随后安全开夹并沿合格来路回撤。恢复完成时无接触载荷或manifold，瓶体原位误差回执为3.316 mm。

标注视频：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/173255_R03_抓取抬升_失抓后恢复成功_6783ffaa.mp4`。58.600秒抬升、58.967秒失抓测量、59.567秒开夹、62.433秒沿来路回撤。恢复成功不等于R03任务完成，重抓结果仍待实跑。

Candidate -12 found a route, but acquisition lost bilateral load during lift. The Adapter safely opened the gripper and retreated along the qualified route, returning explicit observation-ready evidence. The original Agent continues with fresh observations while preserving completed R05 work. R03 remains incomplete.

## 173255 二次准备与中间结论 / Second preparation and interim result

18:43:22，原Agent再次选择R03 execute_subtask；新搜索 `acquire-search/b803576328014a20899b7b8b312f3d96.json` 使用 scene revision `:4` 和候选 `candidate://simulator-truth-R03/09ae35cde54945c2ae78591c4298b233-8`。与首抓失败的旧候选 `b6160a8d743c4295bb6e06b44e7717f6-12` 对比，grasp-predictions中同一固定相机坐标下的拟议抓取中心相差5.190 mm，接近方向相差0.3403°。因此证据支持重新感知后的不同候选引用/抓取中心，尚不能称为显著不同方向的抓法；最终路线可能使用额外轴对称旋转，当前仅比较候选提案。

恢复合辑：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/173255_R05完成_R03失抓后恢复成功_同一AgentLoop.mp4`（277.333秒，完整解码通过）。当前中间结论：R05完整成功；R03首抓失败后安全恢复；原Agent正在二次准备，双瓶任务仍进行中、尚未完成。

At 18:43:22 the same Agent selected the second R03 Action with fresh scene revision :4 and candidate 09ae…-8. Proposed center and approach differ from the failed candidate by 5.190 mm and 0.3403 degrees in the fixed camera frame, so this does not establish a substantially different approach direction. The 277.333-second recovery compilation passed full decoding. R05 succeeded, first R03 acquisition safely recovered, and second preparation remains in progress.

## 173255 最终结果 / Final result

2026-11-25 19:07:56 +08:00，`acceptance.json` 确认同一任务 `task_8f67e002d7364db8` 最终 `failed`。R05全周期成功；R03两次真实抓取均在抬升时 `physical_grasp_lost`，两次均完成安全开夹与合格来路回撤，原任务内的首次恢复→重新感知→二次准备→二次实际抓取已经发生，但R03倾倒/归位未完成。

第二次失败回执为 `phase-feedback/d61b588684fe4cf0932130118527b5d4.json`；最后lift样本双侧冲量 `[0.002127,0] N·s`，接触载荷及manifold均无效，瓶体垂直位移0.0365 mm、attachment误差6.415 mm。原地测量末支撑0.98858 N，恢复完成后 `returned_to_safe_pose=true`、`observation_ready=true`，原位误差3.743 mm。

第二次安全恢复后，控制器请求再次replan并返回 `runner_error:AgentTaskError:replan budget exhausted (2)`；最终记录11个revision、2次replan。启动metadata/临时配置指定 `maxReplansPerEpisode=4`，而运行Coordinator实际上限为2（错误栈直接显示）。该差异需后续定位配置传递，不能靠metadata声称已有4次预算；本轮没有改动生产代码或扩大预算。

最终合辑绝对路径：`/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/173255_R05完成_R03两次失抓均恢复_任务失败_同一AgentLoop.mp4`。381.050秒、30章节，ffmpeg完整解码通过；全部片段来自同一任务，标明任务失败。2:40.250进入R03首抓，4:37.333进入第二次重抓。现有证据证明恢复和重抓链路，不能证明双瓶完成，也不能证明4 mm/60 N已经解决R03持瓶稳定性。

At 19:07:56 the acceptance record marked the task failed. R05 completed; both R03 lift attempts lost bilateral load and safely recovered. The original Agent reobserved and physically retried, but R03 pouring/placement remained incomplete. Recovery after the second attempt exhausted the actual Coordinator replan limit of2 despite launch configuration requesting4; this discrepancy requires diagnosis. The 381.050-second, 30-chapter same-task video passed full decoding and explicitly labels failure.

## v17.10.7 预算传递修复 / Replan budget wiring repair

最终仿真证据已提交 `d1ce17b7`。预算差异根因位于Isaac Host组合层：run_instruction读取了verification配置，却未将max_replans_per_episode传入compose_host；compose_host构造Coordinator时也未传max_replans，导致其默认值2生效。

compose_host现在接受max_replans（默认2），直接传给AgentTaskCoordinator；run_instruction从现有config.agents.verification.max_replans_per_episode传入该值，显式0保持0。Coordinator继续拥有预算、生命周期、取消、结算与恢复；Provider/Adapter、坐标/TCP标定和运动安全边界均未修改。此修复只使配置值生效，不能解决R03物理失抓。

无运动测试从临时JSON配置经真实load_config、run_instruction、compose_host构造真实Coordinator，替换外部LLM/感知和消息执行，验证省略预算=2、自定义4、显式0；既有直接compose_host测试验证默认2。Host定向回归15项通过，两文件Ruff与git diff --check通过；未启动新仿真或硬件执行。

```bash
PYTHONPATH=examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/scene-understanding-http/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/isaacsim_lab/tests/test_agent_host.py --tb=short
```

The Isaac Host omitted both links from the existing verification configuration to Coordinator.max_replans. The repair forwards the configured value while preserving default2 and explicit0. Coordinator retains lifecycle and budget ownership; physical grasp stability is unchanged. Real configuration-loading and composition tests passed (15 tests), with external model/perception calls stubbed and no motion enabled.
