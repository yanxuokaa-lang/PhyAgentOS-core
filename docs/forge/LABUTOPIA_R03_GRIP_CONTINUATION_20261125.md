# R03 夹持单变量复跑记录 / R03 grip continuation

日期：2026-11-25（Asia/Shanghai）。状态：`142657` 已失败结束；末端校正修复已通过回归，修复版仿真复跑待执行。

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

契约及模拟单元测试已通过；修复后的 Isaac 物理执行结果待复跑，双瓶任务尚未完成。
