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

## v11.6.10 (2026-09-25 00:00) - codex

- [agent] [fix] [完成] `manipulation.prepare` 节点同时携带嵌套 intent coordination_mode 与 capability 推导的扁平 coordination_mode，导致规划选择反复被拒绝。计划编译器保留显式 intent 语义并跳过冲突的自动补全；补充跨语义来源回归测试。(local)
- [Agent] [Fix] [Completed] A preparation node carried nested intent coordination_mode together with a capability-derived flat coordination_mode, causing repeated planning-selection rejection. Preserve explicit nested intent semantics and skip conflicting derived completion; add a regression test. (local)

### 验证 / Validation

- `tests/test_plan_proposal_bindings.py tests/test_planning_context.py`: 17 passed; Ruff passed.
- Explicit nested `intent.coordination_mode=single_arm` no longer conflicts with derived flat topology mode; omitted intent mode still receives capability-derived mode.

### 文件变更详情 / File changes

#### [修改 / Modified] `PhyAgentOS/agent/plan_proposal.py` L395-L411

```diff
diff --git a/PhyAgentOS/agent/plan_proposal.py b/PhyAgentOS/agent/plan_proposal.py
index bc0c3dc..1e8f4bf 100644
--- a/PhyAgentOS/agent/plan_proposal.py
+++ b/PhyAgentOS/agent/plan_proposal.py
@@ -395,5 +395,17 @@ def _complete_persisted_runtime_bindings(
                     available_arms = capability_arm_ids.get(capability_ref, ())
                     topology = capability_topologies.get(capability_ref)
-                    if "coordination_mode" not in bindings and topology is not None:
+                    # An explicit nested intent is the model's semantic choice.
+                    # Do not add a derived flat field that would conflict during
+                    # dispatch normalization; the capability topology only fills
+                    # an omitted coordination mode.
+                    nested_intent = bindings.get("intent")
+                    explicit_nested_mode = (
+                        isinstance(nested_intent, Mapping)
+                        and isinstance(nested_intent.get("coordination_mode"), str)
+                    )
+                    if explicit_nested_mode and "coordination_mode" in bindings:
+                        if bindings["coordination_mode"] != nested_intent["coordination_mode"]:
+                            bindings.pop("coordination_mode")
+                    if "coordination_mode" not in bindings and not explicit_nested_mode and topology is not None:
                         bindings["coordination_mode"] = {
                             "single_arm": CoordinationMode.SINGLE_ARM.value,
```

#### [修改 / Modified] `tests/test_plan_proposal_bindings.py` 

```diff
```

### Git 提交 / Git commit

- Implementation commit recorded after commit; branch: `feature/planning-loop`.

## v11.6.9 (2026-09-24 19:56) - codex

- [model] [fix] [完成] 本轮真实十候选的 20 条臂路线全部 IK_FAIL；max_candidates 同时控制采样数和保留数，导致 NMS 前仅有十个样本。新增独立 sample_count 配置（默认兼容旧行为），GraspGen profile 采样 200、NMS 后保留最多 10；不合成候选、不改变位姿、不放宽路线检查。该改动用于验证候选池不足的假设，不将 IK 失败宣称为已修复。(local)
- [Model] [Fix] [Completed] All twenty arm routes from ten genuine candidates failed IK. Separate sampling count from retained count with backward-compatible defaults; sample 200 genuine GraspGen candidates and retain at most ten after existing NMS. No pose synthesis or admission relaxation; candidate-pool insufficiency remains a hypothesis until measured. (local)
- Files: grasp_proposal.py, grasp_profile.py, profiles/robotwin20/graspgen.yaml, adapter tests, release versions and Skill node lock, acceptance documentation.

### 验证 / Validation

- Grasp proposal/profile/persistent host: 22 passed; Ruff passed. Installed Skill 2.7.3 and Node 0.7.6; runtime started. Live acceptance pending.
- 上轮 / Previous: `task_f920d81e0fcf4f04`, ten candidates, 20 rejected arm routes, IK_FAIL at approach/contact; no Action. Cancelled through Coordinator before normal Runtime stop. Evidence: `/home/yanxu/robotwin20-runtime/artifacts/paos-graspgen-agent-20260924T191725/preparation-rejections/0d0d86b475024f0296d5b37500ec8f3d.json`.

### 文件变更详情 / File changes

#### [修改 / Modified] `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md` L20-L24

```diff
diff --git a/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md b/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md
index e63bf2a..4c91605 100644
--- a/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md
+++ b/docs/forge/GRASPGEN_RGB_ACCEPTANCE.md
@@ -20,5 +20,5 @@ Run three independent tasks with current observations and fresh task identities.
 ## Ownership and remaining simulation scope

-The grasp provider is selected from the adapter grasp profile independently of route geometry. The supplied graspgen profile names GraspGen and retains at most ten candidates. Benchmark destination_ref may still originate from task.goal. Existing oracle route/collision geometry and simulation Action admission remain explicitly simulator-owned; they are not sensor evidence and do not generate grasp poses. This stage is simulation execution, not hardware acceptance.
+The grasp provider is selected from the adapter grasp profile independently of route geometry. The supplied graspgen profile names GraspGen and samples 200 real candidates and retains at most ten after existing score/NMS filtering. Sampling and retained counts are configured separately; shortages are reported without padding. Benchmark destination_ref may still originate from task.goal. Existing oracle route/collision geometry and simulation Action admission remain explicitly simulator-owned; they are not sensor evidence and do not generate grasp poses. This stage is simulation execution, not hardware acceptance.

 PAOS remains gpt-5.6-sol/high. Preserve architecture, extension boundaries, developer guidance, Coordinator ownership and AgentLoop recovery. The existing external goal has an unfinished objective and the goal tool cannot edit its text; this document records the user's supplemental acceptance requirements without falsely completing that goal.
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml` L3-L7

```diff
diff --git a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml
index 7f87f33..2bef046 100644
--- a/examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml
+++ b/examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml
@@ -3,4 +3,5 @@ artifact_root: ${ROBOTWIN20_ARTIFACT_ROOT}
 provider_id: graspgen
 max_candidates: 10
+sample_count: 200
 score_threshold: 0.02
 apply_nms: true
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/pyproject.toml` L1-L5

```diff
diff --git a/examples/forge-adapters/robotwin20/pyproject.toml b/examples/forge-adapters/robotwin20/pyproject.toml
index 7fe1e3e..9bcff31 100644
--- a/examples/forge-adapters/robotwin20/pyproject.toml
+++ b/examples/forge-adapters/robotwin20/pyproject.toml
@@ -1,5 +1,5 @@
 [project]
 name = "paos-robotwin20-adapter"
-version = "0.7.5"
+version = "0.7.6"
 description = "PAOS EnvironmentAdapter seam for RoboTwin20 sensor-backed observations."
 requires-python = ">=3.10"
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py` L76-L80

```diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py
index 14d0839..6a6230e 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py
@@ -76,4 +76,5 @@ def build_grasp_provider(
             artifact_store=FilesystemPointCloudArtifactResolver(artifact_root),
             max_candidates=profile["max_candidates"],
+            sample_count=profile.get("sample_count"),
             score_threshold=profile["score_threshold"],
             apply_nms=profile["apply_nms"],
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py` L79-L83, L97-L104, L123-L127, L245-L249

```diff
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py
index 4c32d4c..5175861 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py
@@ -79,4 +79,5 @@ class GraspProposalProvider:
         artifact_store: PointCloudArtifactResolver,
         max_candidates: int = 24,
+        sample_count: int | None = None,
         score_threshold: float = 0.0,
         apply_nms: bool = True,
@@ -96,4 +97,8 @@ class GraspProposalProvider:
         if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or not 1 <= max_candidates <= 512:
             raise ValueError("max_candidates must be between 1 and 512")
+        if sample_count is None:
+            sample_count = max_candidates
+        if isinstance(sample_count, bool) or not isinstance(sample_count, int) or not max_candidates <= sample_count <= 512:
+            raise ValueError("sample_count must be between max_candidates and 512")
         if not _unit_interval(score_threshold):
             raise ValueError("score_threshold must be between 0 and 1")
@@ -118,4 +123,5 @@ class GraspProposalProvider:
         self.artifact_store = artifact_store
         self.max_candidates = max_candidates
+        self.sample_count = sample_count
         self.score_threshold = float(score_threshold)
         self.apply_nms = apply_nms
@@ -239,5 +245,5 @@ class GraspProposalProvider:
                 "point_units": "m",
                 "point_cloud_path": str(points_path),
-                "max_candidates": self.max_candidates,
+                "max_candidates": self.sample_count,
                 "score_threshold": self.score_threshold,
                 "apply_nms": False,
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py` L201-L226

```diff
diff --git a/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py b/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
index 0b36798..4af5923 100644
--- a/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
+++ b/examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py
@@ -201,2 +201,26 @@ def test_invalid_worker_grasp_geometry_is_rejected(tmp_path):
     with pytest.raises(GraspProposalAdapterError, match="geometry is invalid"):
         provider.propose(REQUEST)
+
+
+def test_sample_pool_is_filtered_before_retained_limit(tmp_path):
+    class PoolWorker(Worker):
+        def request(self, payload):
+            self.requests.append(payload)
+            candidates = []
+            for i in range(20):
+                pose = np.eye(4)
+                pose[0, 3] = i * 0.01
+                candidates.append({"matrix": pose.tolist(), "score": (i + 1) / 20})
+            return {"request_id": payload["request_id"], "status": "available",
+                    "candidates": candidates,
+                    "funnel": {"decoded": 20, "canonicalized": 20, "deduplicated": 20, "retained": 20}}
+
+    worker = PoolWorker()
+    provider = GraspGenProposalProvider(worker, artifact_store=_store(tmp_path),
+                                        sample_count=200, max_candidates=10)
+    data = provider.propose(REQUEST)
+    assert worker.requests[0]["max_candidates"] == 200
+    assert data["funnel"] == {"decoded": 20, "canonicalized": 20, "deduplicated": 20, "retained": 10}
+    assert len(data["candidates"]) == 10
+    assert data["candidates"][0]["score"] == 1.0
+    assert data["candidates"][-1]["score"] == 0.55
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/pyproject.toml` L1-L5

```diff
diff --git a/examples/forge-skills/pick-place-workflow/pyproject.toml b/examples/forge-skills/pick-place-workflow/pyproject.toml
index bbd7351..8bf7da9 100644
--- a/examples/forge-skills/pick-place-workflow/pyproject.toml
+++ b/examples/forge-skills/pick-place-workflow/pyproject.toml
@@ -1,5 +1,5 @@
 [project]
 name = "paos-pick-place-workflow"
-version = "2.7.2"
+version = "2.7.3"
 description = "Provider-neutral Forge capability contracts and no-motion conformance fixtures."
 requires-python = ">=3.11"
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/skill.yaml` L1-L5, L150-L158

```diff
diff --git a/examples/forge-skills/pick-place-workflow/skill.yaml b/examples/forge-skills/pick-place-workflow/skill.yaml
index 92a61a8..93efda1 100644
--- a/examples/forge-skills/pick-place-workflow/skill.yaml
+++ b/examples/forge-skills/pick-place-workflow/skill.yaml
@@ -1,5 +1,5 @@
 manifest_version: 2
 name: pick-place-workflow
-version: "2.7.2"
+version: "2.7.3"
 description: Provider-neutral perception, preparation, acquisition, placement, and long-horizon workflow contracts.
 skill_document: SKILL.md
@@ -150,9 +150,9 @@ artifacts:
   nodes:
     robotwin20_persistent_host:
-      artifact_id: robotwin20_persistent_host-0.7.5-linux-x86_64
-      version: "0.7.5"
+      artifact_id: robotwin20_persistent_host-0.7.6-linux-x86_64
+      version: "0.7.6"
       platform: linux
       arch: x86_64
       artifact_type: executable_tar_gz
       entrypoint: robotwin20_persistent_host
-      sha256: d051b41b7fc98cf8ea9d9266a42fc5029db0abafb575bbda5d6259bb48d1a418
+      sha256: f8c69ac006f5b7519869e5164839de572a81ac12d8e7a4e333319167ab93de0e
```

### Git 提交 / Git commit

- Branch: `feature/planning-loop`; commit recorded after submission.

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

- Implementation: `52ecb4b`; branch: `feature/planning-loop`; pushed. / 已提交并推送。

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
