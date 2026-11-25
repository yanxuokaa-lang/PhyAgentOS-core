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

## v17.10.5 (2026-11-25 16:33) - codex

- [policy] [fix] [完成] 在通用 `PerceptionBindingAdapter.bind` 与 `bind_async` 中仅对 scene.observe 明确 stale 重采集，最多三次总尝试，保留 max_age_ms；available 后才启动后续理解/抓取/能力查询，仅使用新采集身份和工件。其他状态及查询异常立即按原逻辑拒绝。 / [Completed] Retry only explicitly stale scene.observe results in synchronous/asynchronous perception binding, at most three total captures with the same age limit; only the available capture supplies identity/artifacts to subsequent queries. Other statuses and query exceptions retain immediate rejection. (local)
- [eval] [exp] [完成] 扩展 `test_perception_binding.py` 覆盖同步/异步重采集、新鲜身份传递、持续 stale 上限、其他状态和异常无重试，并运行既有 refresh revision/identity 与执行器测试。 / [Completed] Cover sync/async recapture, fresh lineage, persistent stale bounds and immediate failure for other statuses/exceptions, and run existing refresh revision/identity and executor tests. (local)
- [docs] [docs] [完成] generic 层只拥有只读绑定重采集策略，Provider 拥有 capture，Runtime 拥有执行；保持未知结果安全语义、schema 和物理阈值，不新增 gate/hash/sleep。补充结果、diff、行号和日志索引。 / [Completed] The generic layer owns read-only recapture policy, providers own capture and Runtime owns execution. Preserve unknown-outcome semantics, schemas and physical thresholds without new gates, hashes or sleeps; document results, diff, lines and index. (local)

### 文件变更详情 / File changes

- [修改 / Modified] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/perception_binding.py` L29、L146–L155、L291–L297：共享三次总采集常量，同步/异步仅 stale 重采集。 / Share a three-capture bound and retry only explicit stale results in synchronous and asynchronous binding.
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py` L461–L519：14 个案例覆盖新鲜身份/工件、原时限不变、持续 stale 上限、其他状态及异常立即拒绝。 / Add 14 cases for fresh identity/artifacts, unchanged age limits, persistent stale bounds and immediate rejection of other statuses/exceptions.
- [修改 / Modified] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L126–162：补 155843 waiting_for_user、观测时间证据、只读重采集修复和验证命令。 / Record the 155843 waiting_for_user result, observation timing, recapture repair and validation command.
- [修改 / Modified] `CHANGELOG.md`：最新五版本 17.10.5、17.10.4、17.10.3、17.10.2、17.10.1 与归档全文一致。 / Synchronize the latest five complete entries with the archive.

```diff
diff --git a/examples/forge-skills/pick-place-workflow/src/pick_place_workflow/perception_binding.py b/examples/forge-skills/pick-place-workflow/src/pick_place_workflow/perception_binding.py
index 8c4e61b1..e2dc40ee 100644
--- a/examples/forge-skills/pick-place-workflow/src/pick_place_workflow/perception_binding.py
+++ b/examples/forge-skills/pick-place-workflow/src/pick_place_workflow/perception_binding.py
@@ -27,4 +27,6 @@ from PhyAgentOS.forge.capability_runtime import (
 from .subtask_executor import PerceptionBinding

+_OBSERVATION_CAPTURE_ATTEMPTS = 3
+

 class PerceptionBindingError(ValueError):
@@ -142,11 +144,14 @@ class PerceptionBindingAdapter:
         if not self.ready:
             raise PerceptionBindingError("perception binding providers are unavailable")
-        observation = self._query(
-            "scene.observe",
-            {
-                "sensor_refs": list(self.request.sensor_refs),
-                "max_age_ms": self.request.max_age_ms,
-            },
-        )
+        for _ in range(_OBSERVATION_CAPTURE_ATTEMPTS):
+            observation = self._query(
+                "scene.observe",
+                {
+                    "sensor_refs": list(self.request.sensor_refs),
+                    "max_age_ms": self.request.max_age_ms,
+                },
+            )
+            if observation.get("status") != "stale":
+                break
         self._require_available(observation, "scene.observe")
         identity = self._identity(observation, self.request.max_age_ms)
@@ -284,8 +289,11 @@ class PerceptionBindingAdapter:
             return results[tool_id]

-        observation = await query("scene.observe", {
-            "sensor_refs": list(self.request.sensor_refs),
-            "max_age_ms": self.request.max_age_ms,
-        })
+        for _ in range(_OBSERVATION_CAPTURE_ATTEMPTS):
+            observation = await query("scene.observe", {
+                "sensor_refs": list(self.request.sensor_refs),
+                "max_age_ms": self.request.max_age_ms,
+            })
+            if observation.get("status") != "stale":
+                break
         self._require_available(observation, "scene.observe")
         identity = self._identity(observation, self.request.max_age_ms)
diff --git a/examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py b/examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py
index b3b73253..17b3a8c7 100644
--- a/examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py
@@ -457,2 +457,63 @@ def test_adapter_is_not_ready_without_all_provider_ports():
     with pytest.raises(PerceptionBindingError, match="providers"):
         adapter.bind()
+
+
+@pytest.mark.asyncio
+@pytest.mark.parametrize("asynchronous", [False, True])
+@pytest.mark.parametrize("stale_count", [1, 2])
+async def test_binding_recaptures_stale_observation_before_using_fresh_lineage(asynchronous, stale_count):
+    chain = QueryChain(scene="fresh-scene")
+    stale = {**_chain(scene="stale-scene")[0], "status": "stale", "freshness_ms": 1235}
+    calls = []
+
+    def invoke(tool_id, arguments):
+        calls.append((tool_id, deepcopy(arguments)))
+        if tool_id == "scene.observe" and len(calls) <= stale_count:
+            return deepcopy(stale)
+        return chain(tool_id, arguments)
+
+    async def invoke_async(tool_id, arguments):
+        return invoke(tool_id, arguments)
+
+    adapter = PerceptionBindingAdapter(invoke_async if asynchronous else invoke, BindingRequest(
+        sensor_refs=("sensor://front",), source_category="reagent_a",
+        destination_category="beaker", max_age_ms=1000))
+    binding = await adapter.bind_async() if asynchronous else adapter.bind()
+    assert [tool for tool, _ in calls] == ["scene.observe"] * (stale_count + 1) + [
+        "scene.understand", "grasp.propose", "manipulation.capabilities"]
+    for _, arguments in calls[:stale_count + 1]:
+        assert arguments == {"sensor_refs": ["sensor://front"], "max_age_ms": 1000}
+    for _, arguments in calls[stale_count + 1:]:
+        assert arguments["scene_revision"] == "fresh-scene"
+        assert arguments["observation_ref"] == chain.observation["observation_ref"]
+    assert calls[stale_count + 1][1]["artifacts"] == [chain.observation["artifacts"][0]["ref"]]
+    assert binding.observation_ref == chain.observation["observation_ref"]
+    assert binding.max_age_ms == 1000
+
+
+@pytest.mark.asyncio
+@pytest.mark.parametrize("asynchronous", [False, True])
+@pytest.mark.parametrize("status,attempts", [
+    ("stale", 3), ("unavailable", 1), ("invalid", 1), ("empty", 1), ("exception", 1),
+])
+async def test_binding_capture_failure_stops_without_downstream_queries(asynchronous, status, attempts):
+    calls = []
+
+    def invoke(tool_id, arguments):
+        calls.append((tool_id, arguments))
+        if status == "exception":
+            raise RuntimeError("capture transport failed")
+        return {"status": status}
+
+    async def invoke_async(tool_id, arguments):
+        return invoke(tool_id, arguments)
+
+    adapter = PerceptionBindingAdapter(invoke_async if asynchronous else invoke, BindingRequest(
+        sensor_refs=("sensor://front",), source_category="reagent_a",
+        destination_category="beaker", max_age_ms=1000))
+    with pytest.raises(PerceptionBindingError, match="scene.observe"):
+        if asynchronous:
+            await adapter.bind_async()
+        else:
+            adapter.bind()
+    assert calls == [("scene.observe", {"sensor_refs": ["sensor://front"], "max_age_ms": 1000})] * attempts
```

### 验证 / Validation

- [eval] [exp] `PYTHONPATH=examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/scene-understanding-http/src .venv/bin/python -m pytest -q examples/forge-skills/pick-place-workflow/tests/test_perception_binding.py examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py --tb=short`：104 passed，含现有 refresh_binding revision/identity 验证。 / All 104 tests passed, including existing refresh revision/identity validation.
- [chore] [chore] 两个修改文件 Ruff、UTF-8、归档索引一致性及 `git diff --check` 通过。 / Ruff, UTF-8, archive/index consistency and diff whitespace checks passed.
- [env] [exp] 本版尚未启动仿真，验证为只读绑定与既有执行路径的无运动测试。 / This version has not started simulation; validation consists of no-motion binding and existing execution-path tests.

### Git 提交 / Git Commit

- 分支 / Branch: `feature/planning-loop`。待主会话审阅提交。 / Awaiting parent-session review and commit.
