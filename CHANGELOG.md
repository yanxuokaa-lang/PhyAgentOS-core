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

## v17.10.6 (2026-11-25 16:50) - codex

- [env] [exp] [进行中] 使用已提交 2dcf0aaa 的 stale 重采集修复启动独立 R05→R03 连续 AgentLoop 仿真；复制 155843 的配置仅替换运行路径，保留 4 mm/60 N、原任务与安全检查，保存阶段录像。 / [In progress] Replay the continuous R05→R03 AgentLoop task on committed 2dcf0aaa, copying 155843 configuration with run paths replaced and preserving 4 mm/60 N, task instruction and safety checks; retain annotated phase videos. (local)
- [docs] [docs] [进行中] 更新 docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md 与 CHANGELOG.md，记录启动命令、进程、终态证据和精确行号/Diff。 / [In progress] Update the continuation report and changelog index with launch command, processes, outcome evidence and precise lines/diff. (local)

### 文件变更详情 / File changes

- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L164–L220：记录两次启动、重启中断、R05成功、R03失抓恢复与二次准备，含配置一致性、证据和视频。 / Record both launches, reboot interruption, R05 success, R03 recovery and second preparation with configuration/evidence/video details.
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

- 执行代码 / Execution code: `2dcf0aaa`；分支 / Branch: `feature/planning-loop`。本轮记录待主会话审核提交。 / This run record awaits parent review and commit.

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

## v17.10.4 (2026-11-25 15:54) - codex

- [env] [fix] [完成] 将 `paos_client.py` 的 `route_search_timeout` 分类为可拒绝的候选准备结果，保留原码和消息；尝试后续已供应候选，全部失败沿用 `no_admissible_grasp` 并建议 Agent 重选候选。 / [Completed] Classify route_search_timeout as a candidate preparation rejection, preserve its original code/message, try subsequent supplied candidates and retain no_admissible_grasp with alternative-candidate recovery when all supplied candidates fail. (local)
- [eval] [exp] [完成] 在 `test_paos_integration.py` 覆盖超时后候选成功、全部超时的重规划建议及 refs、其他合同错误立即拒绝，运行现有 RecoveryDecisions 与 subtask-executor 恢复测试。 / [Completed] Cover a successful candidate after timeout, all-timeout recovery metadata and references, and immediate rejection of other contract errors; run the existing recovery-decision and subtask-executor tests. (local)
- [docs] [docs] [完成] 补全本次失败诊断、代码 Diff、行号和验证结果，同步最新五版本。搜索机制属于 Adapter，候选选择/重规划属于现有 AgentRecoveryDecisions/Coordinator；Runtime 执行所有权、时限和物理检查不变，无新增门禁。 / [Completed] Record the failure diagnosis, diff, locations and validation and update the latest-five index. Search remains Adapter-owned, selection/replanning remains Agent/Coordinator-owned and Runtime execution ownership, timeouts and physical checks remain intact. No new gate is introduced. (local)

### 文件变更详情 / File changes

- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py` L153、L182、L189–L190：仅在既有候选拒绝、可重规划和重选建议集合加入 `route_search_timeout`。 / Add route_search_timeout only to the existing candidate-rejection, replannability and alternative-candidate recommendation sets.
- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py` L941–L946、L949–L990、L993–L1040：超时后另一个候选成功保留诊断、两个候选均失败返回聚合建议和 refs、合同错误保持立即拒绝。 / Cover successful fallback with timeout diagnostics, aggregate metadata for two rejected candidates and immediate rejection of contract errors.
- [修改 / Modified] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L3、L81–L140：更新 150350 失败终态、R05 完整成功/未运动 R03 的视频标签、搜索统计、分类根因及修复验证。 / Record the failed 150350 task, completed R05/incomplete R03 video labels, search statistics, classification cause and validation.
- [修改 / Modified] `CHANGELOG.md`：最新五版本为 17.10.4、17.10.3、17.10.2、17.10.1、17.10.0，完整条目与归档一致。 / Latest-five entries are synchronized with the archive.

```diff
diff --git a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py
index 384aad8e..36a54fd8 100644
--- a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py
+++ b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py
@@ -151,5 +151,5 @@ class LabUtopiaCycleProvider:
                                 "workspace_violation", "route_collision", "self_collision", "payload_collision",
                                 "payload_robot_collision", "no_admissible_grasp", "gripper_aperture_exceeded",
-                                "unsupported_capability_topology"}:
+                                "unsupported_capability_topology", "route_search_timeout"}:
                     raise PreparationProviderError(code, str(result.get("error_detail", result.get("error", code))),
                                                    failure_owner="runtime_adapter")
@@ -180,5 +180,5 @@ class LabUtopiaCycleProvider:
             requires_replan=any(
                 item.get("failure_code") in {
-                    "route_unavailable", "route_collision", "ik_discontinuity",
+                    "route_unavailable", "route_collision", "ik_discontinuity", "route_search_timeout",
                     "gripper_aperture_exceeded",
                 }
@@ -187,5 +187,6 @@ class LabUtopiaCycleProvider:
             recommended_action=(
                 "select_alternative_candidate"
-                if any(item.get("failure_code") in {"route_collision", "ik_discontinuity"} for item in rejected)
+                if any(item.get("failure_code") in {"route_collision", "ik_discontinuity", "route_search_timeout"}
+                       for item in rejected)
                 else "refresh_grasp_candidates"
                 if any(item.get("failure_code") in {"route_unavailable", "gripper_aperture_exceeded"}
diff --git a/examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py b/examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py
index e77e722c..71f44bcf 100644
--- a/examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py
+++ b/examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py
@@ -939,10 +939,14 @@ def test_preparation_tries_predicted_candidates_and_preserves_selected_pose(tmp_
     prepared.clear()
     engine.failure = 'stale_visual_observation'
-    with pytest.raises(PreparationProviderError, match='stale_visual_observation'):
+    with pytest.raises(PreparationProviderError, match='stale_visual_observation') as captured:
         provider.prepare(request)
     assert len(prepared) == 1
+    assert captured.value.failure_owner == 'runtime_adapter'
+    assert captured.value.requires_replan is False
+    assert captured.value.recommended_action == 'fix_runtime_contract'


-def test_prepare_records_rejected_candidates_on_response_and_route_arguments(tmp_path):
+@pytest.mark.parametrize("failure_code", ["route_collision", "route_search_timeout"])
+def test_prepare_records_rejected_candidates_on_response_and_route_arguments(tmp_path, failure_code):
     profile = _profile(tmp_path)
     binding = _binding(profile)
@@ -963,5 +967,6 @@ def test_prepare_records_rejected_candidates_on_response_and_route_arguments(tmp
         def prepare_manipulation(self, request):
             if request["candidate_ref"].endswith("/rejected"):
-                return {"status": "unavailable", "failure_code": "route_collision"}
+                return {"status": "unavailable", "failure_code": failure_code,
+                        "error": "candidate preparation stopped at configured bound"}
             return {"status": "available", "route_arguments": {"candidate_ref": request["candidate_ref"]}}

@@ -973,6 +978,6 @@ def test_prepare_records_rejected_candidates_on_response_and_route_arguments(tmp
     assert rejected == [{
         "candidate_ref": "candidate://observed-reagent-a/rejected",
-        "failure_code": "route_collision",
-        "error": None,
+        "failure_code": failure_code,
+        "error": "candidate preparation stopped at configured bound",
     }]
     assert result["route_arguments"]["rejected_candidates"] == rejected
@@ -989,4 +994,5 @@ def test_prepare_records_rejected_candidates_on_response_and_route_arguments(tmp
     ("route_collision", "select_alternative_candidate"),
     ("ik_discontinuity", "select_alternative_candidate"),
+    ("route_search_timeout", "select_alternative_candidate"),
     ("route_unavailable", "refresh_grasp_candidates"),
 ])
@@ -1004,4 +1010,7 @@ def test_route_rejection_is_explicitly_replannable_but_stays_no_motion(
     }

+    candidates = [candidate, {**candidate, "candidate_ref": candidate["candidate_ref"] + "-second"}]
+    attempted = []
+
     class Resolver:
         def resolve(self, observed, request):
@@ -1011,6 +1020,8 @@ def test_route_rejection_is_explicitly_replannable_but_stays_no_motion(

     class Engine:
-        def prepare_manipulation(self, _request):
-            return {"status": "unavailable", "failure_code": failure_code}
+        def prepare_manipulation(self, request):
+            attempted.append(request["candidate_ref"])
+            return {"status": "unavailable", "failure_code": failure_code,
+                    "error": "bounded search stopped before qualifying a route"}

     provider = LabUtopiaCycleProvider(Engine(), target_resolver=Resolver())
@@ -1019,10 +1030,13 @@ def test_route_rejection_is_explicitly_replannable_but_stays_no_motion(
             "perception_binding": binding,
             "process_type": "pour",
-            "candidates": [candidate],
+            "candidates": candidates,
         })

+    assert attempted == [item["candidate_ref"] for item in candidates]
+    assert captured.value.code == "no_admissible_grasp"
+    assert "bounded search stopped before qualifying a route" in str(captured.value)
     assert captured.value.requires_replan is True
     assert captured.value.recommended_action == recommended_action
-    assert captured.value.rejected_candidate_refs == (candidate["candidate_ref"],)
+    assert captured.value.rejected_candidate_refs == tuple(attempted)


```

### 验证 / Validation

- [eval] [exp] `PYTHONPATH=examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/scene-understanding-http/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py tests/test_recovery_decisions.py examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py --tb=short`：89 passed。 / All 89 PAOS integration, recovery-decision and subtask-executor tests passed.
- [chore] [chore] `.venv/bin/ruff check examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py` 与 `git diff --check` 均通过。 / Ruff on both edited code files and diff whitespace checks passed.
- [env] [exp] 本版验证为无运动的 Provider 与恢复传播测试；v17.10.4 仿真已于 15:58:43 启动，实跑以 waiting_for_user 停止，R05 倾倒后归位观测被报告为不可用或过期，双瓶尚未完成。 / This version has no-motion provider and recovery-propagation evidence; the v17.10.4 replay started at 15:58:43 and execution evidence remains pending; the two-vessel goal remains incomplete.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit: `69f2724f`，分支 / Branch: `feature/planning-loop`；已推送 / Pushed。

- [env] [exp] [完成本轮] 以已推送提交 `69f2724f` 启动新的 R05 → R03 同任务复跑，沿用 `150350` 全部物理、候选和任务指令，仅验证候选准备搜索超时分类修复；新运行使用独立任务数据库、工件和会话。 / [Replay finished] Start a fresh R05 then R03 task on pushed commit 69f2724f with all 150350 physics, candidate settings and task instructions preserved, testing only the candidate preparation timeout classification repair. Use independent task state, artifacts and sessions.

- [env] [exp] 新运行 `/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/v17.10.4-r05-r03-route-recovery-155843` 于 2026-11-25 15:58:43 +08:00 启动；Launcher/Host/录像观察器 PID 分别为 `1006855`/`1006858`/`1006859`。命令 `.venv/bin/python -u out/labutopia-elevated-20261125/v17.10.4-r05-r03-route-recovery-155843/launch.py`；15:58:46 已进入任务创建模型调用。配置和用户指令与 `150350` 归一化路径后完全一致，生产代码 diff 为空。 / Replay 155843 launched at 15:58:43 +08:00 with launcher/host/observer PIDs 1006855/1006858/1006859 and entered task-creation model inference at 15:58:46. Configuration and instruction match 150350 after path normalization, and the production diff is empty. The replay stopped waiting_for_user after an unavailable-or-stale placement-refresh observation report.

- [env] [exp] `155843` 的 `task_321b838973ed4938` 以 `waiting_for_user` 停止：R05 抓取和倾倒成功，归位刷新报告观测“不可用或过期”，使 driver 返回 outcome_unknown，R03 未执行。观测 calibration `b02c15ef9e8e4062a415ff79fe3d8e41.json` 至 state `97103928097a4fe697204820a17d503e.json` 的工件写入间隔约 1.235 s，超过 max_age_ms=1000；后续恢复观测 freshness=540 ms 为 available。原始首次响应未保存，mtime 与后续成功支持瞬时过期解释，未确证首次 status=stale。 / Task task_321b838973ed4938 stopped waiting_for_user after successful R05 acquisition and pouring. An unavailable-or-stale placement refresh report produced outcome_unknown and R03 did not execute. The calibration-to-state artifact interval was about 1.235 s against max_age_ms=1000; a later recovery observation was available at 540 ms freshness. The original response was not retained; these timings support transient staleness without establishing its original status.

## v17.10.3 (2026-11-25 14:25) - codex

- [env] [exp] [完成] 单变量运行 `142657` 将夹持压入量 2 → 4 mm，驱动保持 60 N；R05 抓取成功，倾倒保持 2.833 s、峰值 1.003 rad，退出轴误差 0.0343 rad 超过原 0.02 rad 要求而失败，R03 未执行。录像已分阶段标注保存。 / [Completed] Run 142657 changed only retain overshoot from 2 to 4 mm with the 60 N drive retained. R05 acquisition succeeded and pouring held 2.833 s at 1.003 rad, but exit axis error 0.0343 rad exceeded the existing 0.02 rad criterion; R03 did not execute. Annotated phase videos were retained. (local)
- [env] [fix] [完成] 一次末端校正已将轴误差 0.3076 降至 0.0343 rad；将重新资格化倾倒退出路径的末端反馈校正扩展至最多三次，每次重测位置/轴误差，复用当前接触、实测 attachment、碰撞、连续性、取消和步数限制，保留原最终阈值。 / [Completed] One terminal correction reduced axis error from 0.3076 to 0.0343 rad. Requalified pour exits now allow at most three feedback corrections, remeasuring endpoint errors and preserving fresh contact, measured attachment, collision, continuity, cancellation, execution bounds and original endpoint criteria. (local)
- [docs] [docs] [完成] 记录配置差异、历史证据、实际失败结果、测试和视频章节，并滚动最新五版本；修复版 Isaac 已通过 R05 倾倒阶段，R05 归位亦已成功，R03 路线搜索超时，任务失败。 / [Completed] Record configuration differences, prior evidence, the actual failure, tests and video chapters, and roll the latest-five index. The repaired Isaac replay passed the R05 pour phase; R05 placement also succeeded, while R03 route search timed out and the task failed. (local)

### 文件变更详情 / File changes

- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2847–L2875：一次末端校正改为最多三次，首次误差保留，回执增加 `attempt_count`。 / Replace one terminal correction with at most three, preserving initial errors and recording attempt count.
- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L3909–L4096：覆盖一次/两次收敛、三次不收敛、第二次校正前失抓、碰撞及取消；后者均只发出原停机保持，不发新运动。 / Cover one/two-step convergence, three-step nonconvergence, lost grip, collision and cancellation before a second correction, allowing only the existing stop hold after rejection.
- [新增 / Added] `docs/forge/LABUTOPIA_R03_GRIP_CONTINUATION_20261125.md` L1–81：双语需求、证据边界、单变量配置、运行/验证命令、失败测量和修复状态。 / Record requirements, evidence limits, experiment configuration, launch/validation commands, failure measurements and repair status.
- [新增 / Added] `out/labutopia-elevated-20261125/v17.10.3-r05-r03-4mm-142657/labutopia-ridgebase-elevated-motion.json` L78：运行配置 `finger_retain_overshoot_m` 为 0.004；独立运行目录保存 profile、工件、回执和视频，未复用旧任务数据库。 / The isolated run uses 0.004 m retain overshoot and stores its own profile, artifacts, receipts and videos without reusing a prior task database.
- [修改 / Modified] `CHANGELOG.md` 最近五版本同步完整归档条目。 / Synchronize the latest-five section with complete archive entries.

```diff
-  "finger_retain_overshoot_m": 0.002,
+  "finger_retain_overshoot_m": 0.004,
```

```diff
diff --git a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py
index 80f2d807..9a4ea6ab 100644
--- a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py
+++ b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py
@@ -2845,11 +2845,10 @@ class IsaacPhaseMotion:
             place_pose_checked = False
             pour_exit_requalified = False
-            terminal_exit_checked = False
+            terminal_exit_attempts = 0
             while True:
                 point = next(points, None)
                 if point is None:
-                    if not pour_exit_requalified or terminal_exit_checked or last_stage != "exit":
+                    if not pour_exit_requalified or last_stage != "exit":
                         break
-                    terminal_exit_checked = True
                     planned = np.asarray(route["steps"][-1]["joints"])
                     tool = route["target"]["tool_frame"]
@@ -2859,6 +2858,10 @@ class IsaacPhaseMotion:
                     if tip_error <= self.config["position_tolerance_m"] and axis_error <= .02:
                         break
-                    terminal_exit_correction = {"tip_error_before_m": tip_error,
-                                                "axis_error_before_rad": axis_error}
+                    if terminal_exit_attempts >= 3:
+                        break
+                    if terminal_exit_correction is None:
+                        terminal_exit_correction = {"tip_error_before_m": tip_error,
+                                                    "axis_error_before_rad": axis_error,
+                                                    "attempt_count": 0}
                     if not contacts():
                         raise PhaseMotionError("physical_grasp_lost",
@@ -2867,4 +2870,6 @@ class IsaacPhaseMotion:
                     relation = np.linalg.inv(self.tcp(start)) @ observed
                     goal = self._pour_corrected_joints(start, planned, expected, relation, tool, "exit")
+                    terminal_exit_attempts += 1
+                    terminal_exit_correction["attempt_count"] = terminal_exit_attempts
                     point = {"stage": "exit", "joints": goal, "hold_s": 0.,
                              "allow_contact": False, "attached": True}
diff --git a/examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py b/examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py
index 9415dfa8..911bacee 100644
--- a/examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py
+++ b/examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py
@@ -3910,9 +3910,30 @@ def test_pour_tip_axis_fallback_uses_measured_grip_and_checks_joint_delta(
     "passes", "qualification_collision", "live_collision", "grasp_lost",
     "terminal_corrected", "terminal_collision", "terminal_still_drifted",
+    "terminal_twice_corrected", "terminal_second_collision", "terminal_second_grasp_lost",
+    "terminal_second_cancelled",
 ])
 def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypatch, outcome):
-    from isaacsim_lab.phase_motion import local_tool_inverse_kinematics
+    from isaacsim_lab.phase_motion import (
+        GripContactWindow,
+        local_tool_inverse_kinematics,
+        tool_feature_errors,
+    )

     model, arguments, commands, artifacts = _pour_correction_execution_fixture(monkeypatch)
+    cancel = Event()
+    second_check = []
+    original_contact_valid = GripContactWindow.valid
+
+    def measure_features(*args):
+        errors = tool_feature_errors(*args)
+        if len(terminal_checks) == 1 and errors[1] > .02:
+            second_check.append((len(commands), model.joints().copy()))
+            if outcome == "terminal_second_cancelled":
+                cancel.set()
+        return errors
+
+    monkeypatch.setattr("isaacsim_lab.phase_motion.tool_feature_errors", measure_features)
+    monkeypatch.setattr(GripContactWindow, "valid", lambda window: (
+        False if outcome == "terminal_second_grasp_lost" and second_check else original_contact_valid(window)))
     route = arguments["phase_route"]
     transport = dict(route["steps"][0], stage="transport")
@@ -3930,5 +3951,7 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
     terminal_waypoint = None
     terminal_drift = pose_matrix([.003, 0., 0.], Rotation.from_euler("y", .15).as_quat()) @ relation
-    further_drift = pose_matrix([.006, 0., 0.], Rotation.from_euler("y", .19).as_quat()) @ relation
+    def further_drift(attempt):
+        return pose_matrix([.003 + .003 * attempt, 0., 0.],
+                           Rotation.from_euler("y", .15 + .04 * attempt).as_quat()) @ relation
     body_pose = model.body_pose

@@ -3936,6 +3959,8 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
         if terminal_waypoint is not None and np.allclose(model.joints(), terminal_waypoint, atol=1e-9):
             return model.tcp() @ terminal_drift
+        if terminal_checks and (outcome == "terminal_twice_corrected" or outcome.startswith("terminal_second")):
+            return model.tcp() @ further_drift(1)
         if outcome == "terminal_still_drifted" and terminal_checks:
-            return model.tcp() @ further_drift
+            return model.tcp() @ further_drift(len(terminal_checks))
         if terminal_checks:
             return model.tcp() @ terminal_drift
@@ -3984,6 +4009,9 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
     def correct(start, planned, target, measured, tool, stage):
         if terminal_waypoint is not None:
-            assert start == pytest.approx(terminal_waypoint)
-            assert measured == pytest.approx(terminal_drift)
+            if not terminal_checks:
+                assert start == pytest.approx(terminal_waypoint)
+                assert measured == pytest.approx(terminal_drift)
+            else:
+                assert measured == pytest.approx(further_drift(len(terminal_checks)))
             assert target == pytest.approx(model.tcp(original_steps[-1]["joints"]) @ nominal)
             terminal_checks.append(len(commands))
@@ -3994,5 +4022,6 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
         if not outcome.startswith("terminal_"):
             assert measured == pytest.approx(relation)
-        if outcome == "terminal_collision" and terminal_checks:
+        if ((outcome == "terminal_collision" and terminal_checks)
+                or (outcome == "terminal_second_collision" and len(terminal_checks) == 2)):
             raise PhaseMotionError("payload_collision", "terminal correction hits receiver")
         if ((qualifying and outcome == "qualification_collision")
@@ -4005,5 +4034,5 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
     monkeypatch.setattr("isaacsim_lab.phase_motion.local_inverse_kinematics", distant_full_pose)
     monkeypatch.setattr("isaacsim_lab.phase_motion.local_tool_inverse_kinematics", tool_solver)
-    result = model.execute(arguments, Event())
+    result = model.execute(arguments, cancel)

     assert route["steps"] == original_steps
@@ -4025,4 +4054,5 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
     if outcome.startswith("terminal_"):
         correction = feedback["terminal_exit_correction"]
+        assert correction["attempt_count"] == len(terminal_checks)
         assert correction["axis_error_before_rad"] == pytest.approx(.15)
         assert correction["tip_error_before_m"] > 0.
@@ -4031,12 +4061,12 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
     else:
         assert "terminal_exit_correction" not in feedback
-    if outcome in {"passes", "terminal_corrected"}:
+    if outcome in {"passes", "terminal_corrected", "terminal_twice_corrected"}:
         assert readiness["qualification"] == "passed"
         assert result["operation_completed"] is True
         assert result["measurements"]["final_tool_tip_error_m"] <= .002
         assert result["measurements"]["final_tool_axis_error_rad"] <= .02
-        assert len(terminal_checks) == int(outcome == "terminal_corrected")
+        assert len(terminal_checks) == {"passes": 0, "terminal_corrected": 1, "terminal_twice_corrected": 2}[outcome]
     elif outcome in {"terminal_collision", "terminal_still_drifted"}:
-        assert len(terminal_checks) == 1
+        assert len(terminal_checks) == (3 if outcome == "terminal_still_drifted" else 1)
         assert result["operation_completed"] is False
         assert result["possession_state"] == "holding"
@@ -4048,4 +4078,15 @@ def test_pour_requalifies_remaining_exit_after_discontinuous_solutions(monkeypat
             assert result["failure_code"] == "measured_postcondition_failed"
             assert result["measurements"]["final_tool_axis_error_rad"] > .02
+    elif outcome.startswith("terminal_second"):
+        assert result["operation_completed"] is False
+        assert result["failure_code"] == {
+            "terminal_second_collision": "payload_collision",
+            "terminal_second_grasp_lost": "physical_grasp_lost",
+            "terminal_second_cancelled": "cancelled",
+        }[outcome]
+        assert len(terminal_checks) == (1 if outcome == "terminal_second_grasp_lost" else 2)
+        command_count, stopped_joints = second_check[0]
+        assert len(commands) == command_count + 1  # Existing stop hold; no new motion.
+        assert commands[-1][:7] == pytest.approx(stopped_joints)
     else:
         assert readiness["qualification"] == ("rejected" if outcome == "qualification_collision" else "passed")
```

### 验证 / Validation

- [env] [exp] `PYTHONPATH=examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest -q examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py examples/forge-adapters/isaacsim_lab/tests/test_contact_timing.py --tb=short`：291 passed；原末端校正专项 11 passed。 / The combined phase-motion/contact suite passed 291 tests; the terminal exit cases passed all 11 variants.
- [chore] [chore] 首次遗漏 workflow 的 PYTHONPATH 导致 105 项失败，补路径后初始 287 项通过；修复后新增 4 项，共 291 项通过。 / The initial command omitted the workflow PYTHONPATH and failed 105 tests; correcting the path passed the original 287, and the repair adds four passing cases.
- [chore] [chore] `git diff --check` 通过；Ruff 与 HEAD 一致存在四项既有诊断：源码 L1061 I001，测试 L3328/L3414 E731、L4100 I001（HEAD L4059）。修改未增加诊断。 / Diff whitespace validation passes. Ruff retains four HEAD-identical findings: source L1061 I001, test L3328/L3414 E731 and L4100 I001 (HEAD L4059); no new findings were introduced.
- [env] [exp] `142657` 实跑失败已落盘；修复版 `150350` 已通过 R05 倾倒退出阶段，本轮最终失败，R03 未运动。 / The failed 142657 execution is recorded; repaired run 150350 passed the R05 pour exit phase, while the task ultimately failed before R03 motion.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit: `b985bf98`，分支 / Branch: `feature/planning-loop`；已推送 / Pushed。首次实验执行代码 / First experiment code: `4e06f62f`。

- [env] [exp] [完成] 使用实现提交 `b985bf98` 在新独立运行中复跑 R05 → R03，沿用 `142657` 全部物理与候选配置（4 mm、60 N），仅验证已提交的最多三次末端反馈校正；继续保存本日标注录像。 / [Completed] Replay R05 then R03 in a fresh run with implementation commit b985bf98, preserving all 142657 physics and candidate settings (4 mm, 60 N) and testing only the committed terminal feedback correction. Continue saving annotated videos in today's review directory.

- [env] [exp] [完成] 修复版运行绝对路径 `/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/v17.10.3-r05-r03-exit-feedback-150350`，任务 `task_6559745fef2c4afc`。R05 抓取及倾倒成功；倾倒回执 `6386fe150421405d9775dca466380c17.json` 记录两次校正：轴误差 0.3076176026 → 0.0011673941 rad，瓶口位置误差 0.0130169489 → 0.00016727365 m；连续保持 2.833333 s，峰值 1.0027256 rad。R05 归位已成功，回执 `05bddd6a4d64406b9d9dce172de41e65.json` 记录归位误差 0.9005 mm，视频 `7204d5768cbc4d44be2c8529195379d9.mp4` 已完成；R03 路线搜索超时，本轮失败，R03 未运动。 / [Completed] Task task_6559745fef2c4afc in repaired run 150350 completed R05 acquisition and pouring. The pour receipt records two corrections reducing axis error from 0.3076176026 to 0.0011673941 rad and tip error from 0.0130169489 to 0.00016727365 m, with a 2.833333 s aligned hold at a peak 1.0027256 rad. R05 placement succeeded with a 0.9005 mm return error and a completed video. R03 route search timed out; the task failed before R03 motion.

- [env] [exp] 已将 `150350` 同一任务的 R05 抓取、倾倒、归位三段成功录像按顺序合成 `/home/yanxu/PhyAgentOS-forge/out/labutopia-elevated-20261125/review-videos/150350_R05全周期成功_R03未完成_同一AgentLoop.mp4`，时长 160.250 s、16 个章节，保留原片。ffprobe 检查及 ffmpeg 完整解码通过；合辑和原片不加入 Git。R03 未运动，本轮任务失败。 / Concatenated the three successful R05 phases from the same task into the named 160.250 s video with 16 chapters, retaining original clips. ffprobe inspection and full ffmpeg decoding passed. Videos remain outside Git; R03 did not move and the task failed.

- [env] [exp] `150350` 最终任务 `task_6559745fef2c4afc` 为 failed，R05 全周期成功，R03 未运动；搜索工件 `acquire-search/2b8ee5f6fb724ed09272e7ea2dffadfe.json` 记录 600.3088 s、107 次尝试、99 次剪枝、269 个变体，错误 `route_search_timeout`，重规划次数 0。 / Run 150350 ended failed after a complete R05 cycle and before R03 motion. Its acquisition-search artifact records 600.3088 s, 107 attempts, 99 pruned attempts and 269 variants with route_search_timeout and zero replans.

## v17.10.2 (2026-11-25 04:06) - codex

- [env] [fix] Isaac 回放 `031330` 的 R03 在失抓后原位开夹首帧未通过承重复核。局部复现显示，开夹初段台面和单侧指爪分担荷载，期间瓶体高度变化约 0.094 mm。仅在夹爪固定、瓶体距原支撑高度不超过 0.5 mm 且单侧仍有有效载荷时，允许按 75% 瓶重确认继续开夹。开始开夹与开夹后回撤前仍要求至少 90% 实测承重。 / R03 stopped on the first recovery opening frame in Isaac replay `031330`. Isolated simulation replay showed shared support during partial opening with about 0.094 mm vertical bottle travel. Fixed-arm opening accepts 75% of vessel weight only within 0.5 mm of the original seated height with measured unilateral finger load. Admission and retreat still require measured support of at least 90% of vessel weight.
- [env] [fix] 把有效但不足的实测力保存在阶段回执中，便于区分承重不足与反馈缺失。 / Retain valid subthreshold force samples to distinguish low force from missing feedback.

### 文件变更详情 / File changes

- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L2546–L2567、L2637–L2639、L2661–L2692。区分承重读数新鲜度与重量比例，新增固定臂位开夹的坐落判断，在回撤前校验开夹空夹与独立支撑。 / Separate read freshness from load qualification, check the seated pose during fixed-arm opening, and verify an open clear gripper and independent support before retreat.
- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L2617–L2718。验证开夹时的分担荷载、低载、离座、清空后承重不足及回撤前复核失败。 / Exercise shared load, weak support, unseated geometry, low support after finger clearance, and a failed final recheck.

```diff
diff --git a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py
index 3abc51fc..80f2d807 100644
--- a/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py
+++ b/examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py
@@ -2545,0 +2546,3 @@ class IsaacPhaseMotion:
+        def seated_on_support(pose):
+            return in_support_band(pose) and abs(pose[2, 3] - original[2, 3]) <= .0005
+
@@ -2558,2 +2561 @@ class IsaacPhaseMotion:
-                    or not contact_window.start < evidence["timestamp_s"] <= float(self.world.current_time)
-                    or evidence["upward_force_n"] < .9 * evidence["weight_n"]):
+                    or not contact_window.start < evidence["timestamp_s"] <= float(self.world.current_time)):
@@ -2562,0 +2565,3 @@ class IsaacPhaseMotion:
+        def support_bears_weight(evidence, minimum_fraction=.9):
+            return evidence is not None and evidence["upward_force_n"] >= minimum_fraction * evidence["weight_n"]
+
@@ -2632 +2637,2 @@ class IsaacPhaseMotion:
-                if settle_steps and evidence is not None and contact_window.has_unilateral_load():
+                if (settle_steps and seated_on_support(physical_body) and support_bears_weight(evidence)
+                        and contact_window.has_unilateral_load()):
@@ -2655 +2661,4 @@ class IsaacPhaseMotion:
-                if (held or not supported or not in_support_band(physical_body) or evidence is None
+                unloaded = safe_to_open(physical_body)
+                # During partial release the seated bottle can share load with one finger.
+                shared_support = not unloaded and contact_window.has_unilateral_load()
+                if (held or not supported or not seated_on_support(physical_body)
@@ -2657 +2666,2 @@ class IsaacPhaseMotion:
-                        or not (safe_to_open(physical_body) or contact_window.has_unilateral_load())):
+                        or not (unloaded or shared_support)
+                        or not support_bears_weight(evidence, .75 if shared_support else .9)):
@@ -2663,2 +2673,3 @@ class IsaacPhaseMotion:
-        def verify_empty(stage):
-            held, physical_body = record(stage)
+        def verify_empty(stage, *, require_support_load=False):
+            evidence = read_support() if require_support_load else None
+            held, physical_body = record(stage, support_evidence=evidence)
@@ -2669 +2680,6 @@ class IsaacPhaseMotion:
-                    or not contact_window.current_unloaded(require_clear=True)):
+                    or not contact_window.current_unloaded(require_clear=True)
+                    or (require_support_load and not (
+                        seated_on_support(physical_body)
+                        and contact_window.has_current_feedback(after=contact_window.start)
+                        and support_bears_weight(evidence)
+                    ))):
@@ -2676 +2692 @@ class IsaacPhaseMotion:
-        verify_empty("recovery_open_check")
+        verify_empty("recovery_open_check", require_support_load=require_supported_opening)
```

### 验证 / Validation

- [env] [exp] `PYTHONPATH=examples/forge-adapters/isaacsim_lab/src .venv/bin/python -m pytest -q examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` 通过 261 项。 / All 261 phase motion tests passed.
- [env] [exp] 独立 Isaac 5.1 局部复现采用 `031330` 的关节序列与每控制步 16 个物理子步。前 20 帧台面实测最低 0.757 N，瓶重 0.981 N，开夹后的最后八帧平均承重 0.979–0.984 N。 / The isolated Isaac 5.1 replay used the `031330` joint samples and 16 physics substeps per control interval. The first 20 opening frames had a minimum measured support of 0.757 N for a 0.981 N vessel. Over the last eight frames, control-interval mean support was 0.979–0.984 N.

### Git 提交 / Git Commit

- 实现提交 / Implementation commit `80cee4e0`，`feature/planning-loop`，2026-11-25 04:09:52 +0800。
