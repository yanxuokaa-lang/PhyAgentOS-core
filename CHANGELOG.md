# Changelog

## Archive

- [2026-09 Part 14](changelog/2026-09_part14.md)

- [2026-09 Part 13](changelog/2026-09_part13.md)

- [2026-09 Part 12](changelog/2026-09_part12.md)

- [2026-09 Part 11](changelog/2026-09_part11.md)

- [2026-09 Part 10](changelog/2026-09_part10.md)
- [2026-09 Part 8](changelog/2026-09_part8.md)
- [2026-09 Part 9](changelog/2026-09_part9.md)
- [2026-09 Part 7](changelog/2026-09_part7.md)
- [2026-09 Part 6](changelog/2026-09_part6.md)
- [2026-09 Part 5](changelog/2026-09_part5.md)
- [2026-09 Part 4](changelog/2026-09_part4.md)

## 最近 5 条 / Latest Five Versions

## v11.6.8 (2026-09-24 19:45) - codex

- [agent] [fix] [完成] 实际恢复把跨 revision 的 retry_of 当成本图引用，错误反馈促使模型复制失败节点并耗尽 deadline。保留现有图约束和重试预算，仅在 contracts.py 与 forge_task.py 明确恢复 Query 的历史记录由前一 revision 保存，不能为满足 retry_of 复制旧节点；补充错误反馈断言。(local)
- [Agent] [Fix] [Completed] Recovery confused cross-revision history with local retry_of links and copied failed nodes until the deadline elapsed. Preserve graph validation and retry limits; clarify historical Query recovery in contracts.py and forge_task.py and test the actionable error. (local)
- Files: `PhyAgentOS/planning/contracts.py`, `PhyAgentOS/agent/tools/forge_task.py`, `tests/test_planning_task_integration.py`, `CHANGELOG.md`.

### 验证 / Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -q tests/test_planning_task_integration.py`: 27 passed; Ruff passed.
- 初次未加载 asyncio plugin 的三项异步测试未运行；显式加载后全部通过。 / Three async tests could not run without the plugin; all passed with the explicit asyncio plugin.

### 文件变更详情 / File changes

#### [修改 / Modified] `PhyAgentOS/planning/contracts.py` L229-L240

```diff
diff --git a/PhyAgentOS/planning/contracts.py b/PhyAgentOS/planning/contracts.py
index 2b26f9e..9907dcf 100644
--- a/PhyAgentOS/planning/contracts.py
+++ b/PhyAgentOS/planning/contracts.py
@@ -229,5 +229,12 @@ class PlanGraph(_Frozen):
                 raise ValueError("plan graph dependency references an unknown node")
             if node.retry_of is not None and node.retry_of not in known:
-                raise ValueError("plan graph retry_of references an unknown node")
+                raise ValueError(
+                    "plan graph retry_of references an unknown node; retry_of is a link "
+                    "within this graph, not a prior-revision history reference. Prior "
+                    "failures remain persisted in their original revision: do not copy "
+                    "failed nodes merely to represent history. For a recovery Query, "
+                    "omit cross-revision retry_of and cite its failure in reason/evidence. "
+                    "Action reconciliation and retry admission still apply."
+                )
         if self.graph_digest != plan_graph_digest(self):
             raise ValueError("plan graph digest does not match its content")
```

#### [修改 / Modified] `PhyAgentOS/agent/tools/forge_task.py` L166-L173

```diff
diff --git a/PhyAgentOS/agent/tools/forge_task.py b/PhyAgentOS/agent/tools/forge_task.py
index 66cca65..0331e98 100644
--- a/PhyAgentOS/agent/tools/forge_task.py
+++ b/PhyAgentOS/agent/tools/forge_task.py
@@ -166,5 +166,8 @@ class ForgeTaskBeginRevisionTool(Tool):
             "for coordinator-owned callers. This call only changes the planning revision and "
             "never invokes a Tool or motion. retry_of may reference only a node included in "
-            "this replacement graph; use reason and evidence refs for prior-revision history."
+            "this replacement graph; use reason and evidence refs for prior-revision history. "
+            "Do not copy failed nodes merely to preserve history. For a recovery Query, "
+            "omit prior-revision retry_of and submit only the recovery work; original "
+            "execution records remain persisted. Action retry admission is unchanged."
         )

```

#### [修改 / Modified] `tests/test_planning_task_integration.py` L697-L701, L708-L713

```diff
diff --git a/tests/test_planning_task_integration.py b/tests/test_planning_task_integration.py
index db7e8ab..295a0df 100644
--- a/tests/test_planning_task_integration.py
+++ b/tests/test_planning_task_integration.py
@@ -697,5 +697,5 @@ def test_recovery_graph_retry_of_cannot_reference_prior_revision(tmp_path):
     coordinator.store.update(task.task_id, attach_binding, event_type="test_binding")
     coordinator.request_replan(task.task_id, reason="retry")
-    with pytest.raises(ValueError, match="retry_of references an unknown node"):
+    with pytest.raises(ValueError, match="retry_of references an unknown node") as rejected:
         asyncio.run(ForgeTaskBeginRevisionTool(coordinator).execute(
             task.task_id,
@@ -708,4 +708,6 @@ def test_recovery_graph_retry_of_cannot_reference_prior_revision(tmp_path):
             ).model_dump(mode="json")],
         ))
+    assert "do not copy failed nodes" in str(rejected.value)
+    assert "Action reconciliation and retry admission still apply" in str(rejected.value)
     assert coordinator.get_task(task.task_id).replan_extension_used is False

```

### Git 提交 / Git commit

- Branch: `feature/planning-loop`; commit recorded after submission.

## v11.6.7 (2026-09-24 19:29) - codex

- [agent] [fix] [完成] 单块任务完成 grasp 后续接上下文只暴露 completed_nodes/latest_effect，遗漏无世界变化时仍有效的 discovery 引用；编译器也只检查 active_revision，丢失前一 revision 的同场景绑定。使用现有 context_from_task 的受信任 evidence 与当前 capture identity 解析同任务记录，在 continuation 提供引用摘要；不转录候选、不将旧世界证据带入新场景。(local)
- [Agent] [Fix] [Completed] Continuation after grasp hides valid discovery references and the compiler scans only the active revision. Resolve same-task current-capture records through existing trusted context and expose compact reference summaries during continuation; never copy candidates or carry stale world evidence. (local)
- Files: `PhyAgentOS/agent/plan_proposal.py`, `PhyAgentOS/agent/prompt_context.py`, corresponding tests and `CHANGELOG.md`.

### 验证 / Validation

- 166 tests passed: planning context, foundation, plan proposal bindings, prompt context, planning loop. Ruff passed. Live single-block acceptance is pending.
- 同场景跨 revision 保留引用；新 capture 和世界变化均排除旧证据，含旧 discovery refs 的回归。 / Preserve references across segments only for the current capture; exclude stale captures and world evidence, including selected old discovery refs.

### 文件变更详情 / File changes

#### [修改 / Modified] `PhyAgentOS/agent/planning_context.py` L154-L187

```diff
diff --git a/PhyAgentOS/agent/planning_context.py b/PhyAgentOS/agent/planning_context.py
index 9b50ab4..38ee77d 100644
--- a/PhyAgentOS/agent/planning_context.py
+++ b/PhyAgentOS/agent/planning_context.py
@@ -154,3 +154,34 @@ __all__ = [
     "PlanningContextUnavailableError",
     "context_from_task",
+    "current_scene_query_records",
 ]
+
+
+def current_scene_query_records(task):
+    """Return trusted Query records for the latest capture across plan segments."""
+    try:
+        context = context_from_task(task, allow_refresh=True)
+    except PlanningContextUnavailableError:
+        return ()
+    if dict(context.condition_facts).get("scene_current") is False:
+        return ()
+    trusted = set(context.evidence_refs)
+    records = tuple(getattr(task, "execution_records", ()))
+    visible = tuple(
+        record for record in records
+        if record.status == "succeeded"
+        and record.semantics == "query"
+        and trusted.intersection(record.evidence_refs)
+    )
+    observation = next((r for r in reversed(visible) if r.tool_id == "scene.observe"), None)
+    if observation is None:
+        return ()
+    keys = ("scene_revision", "observation_ref", "calibration_ref")
+    capture = response_facts(observation.response)
+    if capture.get("scene_revision") != context.scene_revision:
+        return ()
+    identity = tuple(capture.get(key) for key in keys)
+    return tuple(
+        record for record in visible
+        if tuple(response_facts(record.response).get(key) for key in keys) == identity
+    )
```

#### [修改 / Modified] `PhyAgentOS/agent/plan_proposal.py` L193-L197, L225-L239, L246-L250

```diff
diff --git a/PhyAgentOS/agent/plan_proposal.py b/PhyAgentOS/agent/plan_proposal.py
index c979baa..bc0c3dc 100644
--- a/PhyAgentOS/agent/plan_proposal.py
+++ b/PhyAgentOS/agent/plan_proposal.py
@@ -193,5 +193,5 @@ def _complete_persisted_runtime_bindings(
     consumers must not depend on the model copying a destination or capability
     URI into every later selection.  Only values already frozen in this graph
-    or a unique current-revision capabilities result are propagated; ambiguous or
+    or a unique current-capture capabilities result are propagated; ambiguous or
     stale values remain absent and are rejected by normal selection validation.
     """
@@ -225,10 +225,15 @@ def _complete_persisted_runtime_bindings(
                             goal_entities_by_destination.setdefault(destination, set()).add(entity)

-    # Scene-bound facts must come from the revision being compiled. Task goals
+    # Scene-bound facts may cross segments only within the current capture. Task goals
     # are task-specification facts and may outlive a scene; capabilities,
     # identity correspondence, targets, and candidates may not.
     active_revision = task.active_revision
+    scene_records = active_revision.execution_records
+    if getattr(task, "execution_records", None):
+        from PhyAgentOS.agent.planning_context import current_scene_query_records
+
+        scene_records = current_scene_query_records(task)
     latest_observation_identity: tuple[str, str, str] | None = None
-    for record in reversed(active_revision.execution_records):
+    for record in reversed(scene_records):
         if record.status != "succeeded" or record.tool_id != "scene.observe":
             continue
@@ -241,5 +246,5 @@ def _complete_persisted_runtime_bindings(
             latest_observation_identity = identity  # type: ignore[assignment]
             break
-    for record in active_revision.execution_records:
+    for record in scene_records:
         facts = response_facts(record.response)
         if record.status != "succeeded":
```

#### [修改 / Modified] `PhyAgentOS/agent/prompt_context.py` L801-L838, L861-L867

```diff
diff --git a/PhyAgentOS/agent/prompt_context.py b/PhyAgentOS/agent/prompt_context.py
index 2e94da1..0ab494a 100644
--- a/PhyAgentOS/agent/prompt_context.py
+++ b/PhyAgentOS/agent/prompt_context.py
@@ -801,6 +801,38 @@ def continuation_task_prompt_projection(task: Any | None) -> dict[str, Any] | No
     )
     effect = response_facts(getattr(latest_effect, "response", None)) if latest_effect else {}
+    from PhyAgentOS.agent.planning_context import current_scene_query_records
+
+    current_records = current_scene_query_records(task)
+    summaries = []
+    for record in current_records:
+        facts = response_facts(record.response)
+        summary = {
+            "record_id": record.record_id,
+            "tool_id": record.tool_id,
+            "evidence_refs": list(record.evidence_refs),
+            "facts": {key: facts[key] for key in (
+                "observation_ref", "scene_revision", "calibration_ref", "frame",
+                "binding_ref", "snapshot_ref", "candidate_set_ref", "preparation_ref",
+                "destination_ref", "entity_ref", "funnel",
+            ) if key in facts},
+        }
+        if record.tool_id in {"scene.bind", "scene.understand"}:
+            summary["entities"] = [
+                {key: entity[key] for key in ("entity_ref", "execution_entity_ref", "category") if key in entity}
+                for entity in facts.get("entities", ()) if isinstance(entity, dict)
+            ]
+        summaries.append(summary)
+    goals = [
+        {"record_id": record.record_id, "goals": [
+            {key: goal[key] for key in ("execution_entity_ref", "destination_ref") if key in goal}
+            for goal in response_facts(record.response).get("goals", ()) if isinstance(goal, dict)
+        ]}
+        for record in getattr(task, "execution_records", ())
+        if record.tool_id == "task.goal" and record.status == "succeeded"
+    ]
     return {
         "version": "agent_continuation_prompt_projection_v1",
+        "current_scene_queries": summaries,
+        "task_goals": goals,
         "authority": "read_only_projection_from_AgentTaskCoordinator",
         "task_id": getattr(task, "task_id", None),
@@ -829,5 +861,7 @@ def continuation_task_prompt_projection(task: Any | None) -> dict[str, Any] | No
             "Submit only the next scene-bound semantic segment or finalize. "
             "Do not repeat completed nodes, cite future node IDs, or copy prior "
-            "execution arguments, digests, assignments, candidates, or refs."
+            "execution arguments, digests, assignments or candidates. Use the current "
+            "scene query summaries and exact evidence refs for node bindings; "
+            "dependencies may only name nodes in the newly submitted segment."
         ),
         "motion_authorized": False,
```

#### [修改 / Modified] `tests/test_planning_context.py` L210-L265

```diff
diff --git a/tests/test_planning_context.py b/tests/test_planning_context.py
index 28d2f87..0085f69 100644
--- a/tests/test_planning_context.py
+++ b/tests/test_planning_context.py
@@ -210,2 +210,56 @@ def test_context_does_not_restore_unselected_historical_discovery_evidence() ->
     assert "tool:selected" in context.evidence_refs
     assert "tool:historical" not in context.evidence_refs
+
+
+def test_continuation_keeps_same_capture_records_and_excludes_stale_captures():
+    from PhyAgentOS.agent.planning_context import current_scene_query_records
+    from PhyAgentOS.agent.prompt_context import continuation_task_prompt_projection
+
+    def query(name, tool, capture):
+        return _record(name, tool_id=tool, arguments={}, response={"data": {
+            "scene_revision": "scene", "observation_ref": "observation://same-scene",
+            "calibration_ref": f"artifact://{capture}/calibration",
+            "entities": [{"entity_ref": "entity://red", "category": "red cube", "world_T_object": [12345]}],
+        }})
+
+    observation = query("observe", "scene.observe", "first")
+    binding = query("bind", "scene.bind", "first")
+    task = _task(observation, binding)
+    # Queries remain available even though the active continuation has no records.
+    task.active_revision.execution_records = ()
+    assert current_scene_query_records(task) == (observation, binding)
+    projection = continuation_task_prompt_projection(task)
+    assert projection["current_scene_queries"][1]["entities"] == [{"entity_ref": "entity://red", "category": "red cube"}]
+    assert "12345" not in str(projection)
+    newer = query("observe-new", "scene.observe", "second")
+    task.execution_records += (newer,)
+    assert current_scene_query_records(task) == (newer,)
+    effect = _record("action", tool_id="object.place", arguments={}, response={"data": {"world_change_started": True}})
+    effect.semantics = "action"
+    task.execution_records += (effect,)
+    task.active_revision.discovery_evidence_refs = newer.evidence_refs
+    assert current_scene_query_records(task) == ()
+    effect.response["data"]["new_scene_revision"] = "scene-after-place"
+    assert current_scene_query_records(task) == ()
+
+
+def test_compiler_resolves_entity_from_previous_segment_current_capture():
+    from PhyAgentOS.agent.plan_proposal import _complete_persisted_runtime_bindings
+    from PhyAgentOS.planning import PlanNode
+
+    identity = {"scene_revision": "scene", "observation_ref": "observation://current",
+                "calibration_ref": "artifact://current/calibration"}
+    observation = _record("observe", tool_id="scene.observe", arguments={}, response={"data": identity})
+    binding = _record("bind", tool_id="scene.bind", arguments={}, response={"data": {
+        **identity, "entities": [{"entity_ref": "entity://observed-red",
+                                 "execution_entity_ref": "entity://block-red-1"}],
+    }})
+    observation.node_id = "observe"
+    binding.node_id = "bind"
+    task = _task(observation, binding)
+    task.revisions = (SimpleNamespace(execution_records=task.execution_records),)
+    task.active_revision.execution_records = ()
+    prepare = PlanNode(node_id="prepare", obligation_id="prepare", capability="manipulation.prepare",
+                       input_bindings={"execution_entity_ref": "entity://block-red-1"})
+    completed = _complete_persisted_runtime_bindings(task, (prepare,))
+    assert completed[0].input_bindings["entity_ref"] == "entity://observed-red"
```

### Git 提交 / Git commit

- Implementation commit: `2e9dd6f`; branch: `feature/planning-loop`; pushed. / 实现已提交并推送，动作验收仍在进行。

## v11.6.6 (2026-09-24 18:08) - codex

### 实际修改 / Completed changes

- [model] [fix] [完成] `persistent_host.py` 不再按 `route_geometry_source=oracle` 选择 `PersistentOracleGraspProvider`；所有 profile 均通过独立 `graspgen.yaml` 构建 GraspGen Provider。`graspgen.yaml` 的真实候选上限设为 10，禁止模板回退。(local)
- [Model] [Fix] [Completed] `persistent_host.py` no longer selects `PersistentOracleGraspProvider` from `route_geometry_source=oracle`; every profile builds the GraspGen provider from the independent `graspgen.yaml`. The real-candidate cap is 10 and template fallback is forbidden. (local)
- [policy] [fix] [完成] `materialize_complete_route.py` 接受当前 runtime profile 已有的 `max_observation_age_ms` 字段并校验为正整数；此前该字段使真实十候选 prepare 在 materializer 前错误返回 `route_materialization_invalid`。(local)
- [Policy] [Fix] [Completed] `materialize_complete_route.py` accepts and validates the existing positive `max_observation_age_ms` runtime field; previously this field caused the real ten-candidate preparation to fail before materialization with `route_materialization_invalid`. (local)
- [tests] [feat] [完成] persistent host、backend contract、GraspGen proposal/profile tests: `37 passed`;真实首次 GraspGen 任务确认实时点云存在，首个失败为错误 `GRASPGEN_SOURCE_ROOT`，修正后十个真实候选已进入 preparation，随后暴露并修复 runtime identity schema mismatch。(local)
- [Tests] [Feat] [Completed] Persistent-host, backend-contract, and GraspGen proposal/profile tests: `37 passed`; the first live GraspGen task confirmed the current point cloud, initially failed only because `GRASPGEN_SOURCE_ROOT` was wrong, then passed ten real candidates into preparation and exposed/fixed the runtime-identity schema mismatch. (local)

### 精确变更 / Exact files and diff

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py:L28,L546-L593` 删除 Oracle grasp Provider 分支，统一从 grasp profile 构建 GraspGen。
- `examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml:L3-L6` 增加 `provider_id: graspgen`，`max_candidates: 24` → `10`。
- `examples/forge-adapters/robotwin20/scripts/materialize_complete_route.py:L219-L244` 将 `max_observation_age_ms` 纳入严格 identity 字段并校验正整数。
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py:L239-L303` observed/oracle 两路线均断言 GraspGen Provider 与十候选配置。
- `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md:L1-L29` 记录实时感知→点云→GraspGen→十候选→prepare→Action→三轮验收。

**关键 Diff / Key diff:**
```diff
- if route_geometry_source == "oracle":
-     grasp = PersistentOracleGraspProvider(...)
- else:
-     grasp = build_grasp_provider(...)
+ grasp = build_grasp_provider(load_grasp_profile(grasp_profile), environ=variables)
+ max_candidates: 10
+ expected runtime identity fields += max_observation_age_ms
```

### Git 提交 / Git commit

- Implementation commit: `332b683`; branch: `feature/planning-loop`; pushed. Live acceptance remains pending.


### 变更计划 / Planned changes

- [model] [fix] [计划] 按用户明确要求，persistent host 抓取 Provider 始终由独立 grasp profile 构建，移除 route_geometry_source=oracle 隐式选择模板的耦合；GraspGen profile 保留十个真实候选进入 preparation，无模板 fallback。(local)
- [Model] [Fix] [Planned] Build the persistent grasp provider from its independent grasp profile; remove implicit template selection by oracle route geometry and retain ten real GraspGen candidates for preparation without template fallback. (local)
- [eval] [docs] [计划] 记录补充目标：先实时感知、分割与对象点云、GraspGen、十候选 preparation、单次 acquire/place 与 retreat 验收，再启动三轮 RGB 排列，至少一轮完整成功且有视频及 Verifier。已有 goal 工具不支持修改未完成目标正文，本文记录用户的新增约束。(local)
- [Eval] [Docs] [Planned] Record the amended objective: validate live perception, segmented object clouds, GraspGen, ten-candidate preparation and one acquire/place with retreat before three independent RGB trials with at least one full success, video and verifier. The goal API cannot edit the existing unfinished objective. (local)

### 预期文件 / Expected files

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py`
- `examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml`
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py`
- `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md`
- `CHANGELOG.md`

现有 profile、Provider 接口和准备检查足以处理该问题，不新增 hash、gate 或 Action 重试。 / Existing profiles, provider interfaces and preparation checks suffice; no new hash, gate or Action retry.

### 追加修复计划 / Additional planned fix

- [agent] [fix] [计划] 当前真实 GraspGen 查询已成功并持久化十个候选，但后续节点把前驱 effects 重复写成未登记的 condition facts，AgentLoop 因 trusted condition_facts 为空而无 ready 节点。保留 dependencies 作为节点顺序与 settlement 门槛，编译时拒绝没有已登记事实来源、却重复直接前驱 effects 的 conditions，由 Agent 修正；不把 effects 提升为物理事实、不新增 Action 重试。(local)
- [Agent] [Fix] [Planned] The live GraspGen query succeeded and persisted ten candidates, but dependent nodes duplicated predecessor effects as unregistered condition facts, leaving AgentLoop with no ready node because trusted condition_facts is empty. Keep dependencies as ordering and settlement gates, and reject conditions duplicating direct predecessor effects without registered facts and let the Agent correct the plan; do not promote effects to physical facts or retry Actions. (local)

### 追加验证 / Additional validation

- [agent] [fix] [完成] 不删除 conditions、不提升 effects；提前拒绝不受事实支持的 effects-as-conditions，公开工具说明明确 dependencies 表示前驱完成。Agent foundation + plan bindings: 72 passed。
- [Agent] [Fix] [Completed] Preserve conditions and never promote effects; reject unsupported effects-as-conditions with actionable guidance. Agent foundation + plan bindings: 72 passed.
- [eval] [fix] [完成] 当前 runtime observation profile 回归及 materializer diagnostics: 6 passed。控制器部署参数现已按同一 package 修正 qualification/plan/evidence/validation 与左右能力文件；离线无运动 materialization 成功，不等同 readiness 或动作成功。
- [Eval] [Fix] [Completed] Runtime profile and materializer diagnostics: 6 passed. Correct qualification/plan/evidence/validation and arm capability paths from one package; offline no-motion materialization passed, not readiness or Action acceptance.
- 单块正式任务 / Single-block task: `task_cde71cc5ec254b5b`, log `/tmp/graspgen-single-v1166.log`; acceptance pending.

### 最终工作树行号 / Current worktree line ranges

- `PhyAgentOS/agent/plan_proposal.py`: L127-L145
- `PhyAgentOS/agent/tools/forge_task.py`: L243-L245
- `examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml`: L3-L4
- `examples/forge-adapters/robotwin20/pyproject.toml`: L3-L3
- `examples/forge-adapters/robotwin20/scripts/materialize_complete_route.py`: L231-L231, L245-L246
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py`: L27-L27, L544-L544, L569-L573
- `examples/forge-adapters/robotwin20/tests/test_materializer_diagnostics.py`: L72-L86
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py`: L232-L233, L235-L235, L259-L260, L264-L264, L296-L297
- `examples/forge-skills/pick-place-workflow/pyproject.toml`: L3-L3
- `examples/forge-skills/pick-place-workflow/skill.yaml`: L3-L3, L152-L153, L158-L158
- `tests/test_agent_foundation.py`: L1465-L1477
- `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md`: L1-L24

## v11.6.5 (2026-09-24 17:10) - codex

### 变更记录 / Changes [完成]

- [agent] [fix] 真实任务 `task_f0d1c32d75fc494a` 在计划物化拒绝后以“将修正”文字结束，图仍为空。AgentLoop 在本回合尝试物化、任务仍处于 discovery 时允许一次文字后 continuation，要求通过正式工具修正或明确请求澄清；不重复已有 Tool。(local)
- [Agent] [Fix] Task `task_f0d1c32d75fc494a` ended with a promised correction after rejected materialization while its graph remained empty. Allow one continuation after prose when this turn attempted materialization and the task remains in discovery; use normal tools to correct or request clarification without replaying Tools. (local)

### 文件与 Diff / Files and diff

- `PhyAgentOS/agent/loop.py:L731,L1113-L1141`：`prose -> return` → `rejected materialization + discovery -> one model continuation`。仅使用现有模型与 Coordinator 工具；不重发 Tool。
- `tests/test_agent_foundation.py:L384-L420`：验证修正物化成功和重复文字的有界终止。 / Verify successful corrected materialization and bounded termination on repeated prose.
- Validation: Agent foundation, PlanningLoop, prompt context, turn timeout and provider timing suites: `160 passed`; Ruff and `git diff --check`: passed.
- RGB 三块验收尚未完成。 / Live RGB acceptance remains incomplete.
