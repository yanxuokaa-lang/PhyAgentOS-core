# Changelog
## Archive
- [2026-10 part3](changelog/2026-10_part3.md)
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.10.13 (2026-10-09 10:39) - codex

### 预期修改 / Planned Changes [完成]
- [policy] [fix] 将成功 Action 的 Runtime 持有实体从 unchanged carry-forward 中分离，Coordinator 仅在权威 `holding_state=holding`、owner、acquire invocation、entity identity 和完整场景效果证据一致时投影 `carry_state=held`；未确认持有时保持 fail-closed。(local)
- [comm] [fix] 扩展 provider-neutral scene-effects receipt 以表达当前持有实体，并让 bounded receipt 在裁剪或证据不完整时清空该投影，避免伪造 possession。(local)
- [comm] [fix] Adapter 对 `held` 与 `unchanged` 采用不同验证路径：held 使用当前 Runtime identity/pose，unchanged 继续要求旧新 Runtime pose 不变；两者均不产生 motion authorization。(local)
- [eval] [fix] 增加 Core、Runtime receipt、Adapter held/unchanged/unknown possession 的 no-motion 回归，证明抓取后的理解可保留实体且未知持有状态仍停止。(local)
- [docs] [docs] 保存本次持有实体投影缺口、PAOS ownership、AgentLoop fail-closed 边界与七维验收诊断。(local)

### Planned Changes (English)
- [policy] [fix] Separate a successful Action's Runtime-held entity from unchanged carry-forward; the Coordinator projects `carry_state=held` only when authoritative `holding_state=holding`, owner, acquire invocation, entity identity, and complete scene-effect evidence agree, remaining fail-closed when possession is unconfirmed. (local)
- [comm] [fix] Extend the provider-neutral scene-effects receipt to express the current held entity, and clear that projection when the bounded receipt is truncated or evidence is incomplete so possession cannot be fabricated. (local)
- [comm] [fix] Give the Adapter distinct validation paths for `held` and `unchanged`: held uses the current Runtime identity/pose, while unchanged keeps the old/new Runtime pose-stability check; neither path grants motion authorization. (local)
- [eval] [fix] Add no-motion regressions for Core, Runtime receipt, and Adapter held/unchanged/unknown possession, proving post-acquire understanding retains the entity while unknown possession still stops. (local)
- [docs] [docs] Preserve the held-entity projection gap diagnosis, PAOS ownership, AgentLoop fail-closed boundary, and seven-dimension acceptance record. (local)

### 具体失败场景与现有机制不足 / Failure Scenario and Gap
- `object.acquire` succeeded and advanced the action-driven scene, but the acquired entity was listed only in `changed_entity_refs`; `_coordinator_carried_entities()` intentionally consumed only `unaffected_entity_refs`, so the next `scene.understand` omitted the held object and the provider could reinterpret the gripper-occluded pixels as another entity.
- Ordinary record primary keys and action status cannot establish current possession: a changed entity may be released, lost, or uncertain. The existing Runtime snapshot already owns the necessary owner/invocation/entity facts, but the cross-layer receipt had no field to carry them. Without an explicit, evidence-bound held state, relaxing unchanged pose checks would make stale or fabricated entities eligible for binding.
- The repair therefore adds no hash or broad gate. It adds only a bounded, provider-neutral field at the existing Runtime-to-Coordinator boundary and keeps all unknown/invalid possession fail-closed; motion admission and authorization remain unchanged.

### 影响文件 / Expected Files
- `PhyAgentOS/agent/tools/forge_tool_api.py`
- `PhyAgentOS/forge/capability_runtime/understanding.py`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py`
- `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py`
- `tests/test_forge_tool_api.py`
- `examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py`
- `examples/forge-adapters/robotwin20/tests/test_grounding.py`
- `docs/forge/HELD_ENTITY_PROJECTION_DIAGNOSIS_20261009.md`

### 计划补充 / Additional Plan
- [policy] [fix] 在 selection 持久化前注入 Coordinator carry-forward，避免执行时参数与 planning binding 不一致；隔离新视觉 ID 与旧任务 ID 的冲突，保留视觉证据。(local)
- [policy] [fix] Inject Coordinator carry-forward before persisting selection to keep execution arguments consistent with the planning binding; isolate fresh visual IDs that collide with task identities while retaining visual evidence. (local)
- [docs] [docs] 本次正确版本为 v12.10.13；原暂存计划 v12.10.8 重号已更正，超过 1500 行的 part2 不再追加。(local)
- [docs] [docs] This change is v12.10.13; corrected the duplicate draft v12.10.8 and rolled the oversized part2 forward to part3. (local)
- [eval] [fix] 修正 Skill 版本回归仍断言已卸载的 3.0.9 的既有 fixture，使其与当前 3.0.10 manifest/package 一致；provider import-boundary 回归使用独立进程执行，避免 Core Agent 测试加载 OpenAI SDK 后污染 `sys.modules`。(local)
- [eval] [fix] Correct the existing stale Skill version fixture from 3.0.9 to the current 3.0.10 manifest/package; run provider import-boundary tests in an isolated process so Core Agent tests importing the OpenAI SDK do not contaminate `sys.modules`. (local)


### 实际修改 / Completed Changes

- [policy] [fix] 分离 held 与 unchanged，修复五项 Major；Runtime → Coordinator → understanding → Grounding 使用一致持有事实，不包含 RGB 专用分支。(local)
- [policy] [fix] Separate held from unchanged and resolve five Major findings; Runtime → Coordinator → understanding → Grounding uses consistent possession facts with no RGB-specific branch. (local)

### 文件变更详情 / File Changes

| 文件 / File | 精确行号 / Exact Lines | 修改 / Change |
| --- | --- | --- |
| `PhyAgentOS/agent/tools/forge_tool_api.py` | L390-L390, L395-L398, L833-L833, L843-L843, L845-L845, L847-L850, L858-L859, L862-L863, L867-L867, L871-L871, L877-L893, L924-L924, L932-L941 | 投影最新权威 held/unchanged 证据，保留已选参数并拒绝过期投影 / Project latest authoritative held/unchanged facts and preserve selected arguments. |
| `PhyAgentOS/agent/tools/planning.py` | L447-L459 | 选参持久化前注入 Coordinator 投影 / Inject Coordinator facts before persisting selection. |
| `PhyAgentOS/forge/capability_runtime/understanding.py` | L229-L239, L540-L540, L543-L545, L563-L576, L907-L923, L987-L998, L1001-L1005, L1017-L1017, L1024-L1025, L1032-L1034 | 扩展 held schema、验证 possession、隔离视觉 ID 并保留原视觉证据 / Extend held schema, validate possession, and isolate conflicting visual IDs. |
| `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py` | L703-L709 | 成功 acquire artifact 写入 held_entity / Persist held_entity in a known successful acquisition artifact. |
| `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py` | L188-L194, L283-L283, L354-L354, L358-L362, L380-L380, L436-L456 | 核对当前 possession 并刚体搬运旧视觉模型，保留 unchanged 漂移检查 / Verify current possession and transport the visual model while retaining unchanged drift checks. |
| `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py` | L321-L329 | 仅发布与 settled possession 一致的 held receipt / Publish held receipts only when settled possession agrees. |
| `examples/forge-adapters/robotwin20/tests/test_grounding.py` | L226-L284 | 覆盖 held 平移、旋转、cached mismatch 与 unchanged drift / Cover held translation, rotation, cached mismatch, and unchanged drift. |
| `examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py` | L94-L115, L180-L181, L191-L191, L421-L454 | 覆盖 engine artifact、receipt 裁剪和 possession 对账 / Cover engine artifacts, receipt truncation, and possession agreement. |
| `examples/forge-skills/pick-place-workflow/contracts/scene.understand.tool.yaml` | L148-L165 | 同步静态 ToolSpec 可选 held 字段 / Synchronize optional held fields in the static ToolSpec. |
| `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py` | L270-L270 | 修正旧版本测试夹具 / Correct the stale release fixture. |
| `examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py` | L246-L295 | 覆盖视觉 ID 冲突和未确认持有拒绝 / Cover visual ID conflicts and unconfirmed possession rejection. |
| `tests/test_forge_tool_api.py` | L591-L591, L796-L1034 | 覆盖 held 来源验证、未知 Action、exact binding 和真实 SQLite selection/Query / Cover held sources, unknown Actions, exact bindings, and real SQLite selection/Query execution. |
| `docs/forge/HELD_ENTITY_PROJECTION_DIAGNOSIS_20261009.md` | L1-L119 | 新增双语根因、阶段、视频与修复边界 / Add bilingual diagnosis, stage, videos, and repair boundaries. |
| `docs/forge/HELD_ENTITY_DIAGNOSTIC_SNAPSHOT_20261009.json` | L1-L132 | 只读诊断快照，未修改现场记录 / Read-only diagnostic snapshot; live records untouched. |
| `docs/forge/IMPLEMENTATION_REVIEW_V12_10_13.md` | L1-L71 | 七维审查、发现处置和验证命令 / Seven-dimension review, disposition, and validation commands. |

### 关键代码 Diff / Key Code Diff

#### [修改 / Modified] `PhyAgentOS/agent/tools/forge_tool_api.py` L390-L390, L395-L398, L833-L833, L843-L843, L845-L845, L847-L850, L858-L859, L862-L863, L867-L867, L871-L871, L877-L893, L924-L924, L932-L941

```diff
--- a/PhyAgentOS/agent/tools/forge_tool_api.py
+++ b/PhyAgentOS/agent/tools/forge_tool_api.py
@@ -391 +390,0 @@ class ForgeToolQueryTool(Tool):
-                    resolved_arguments.pop("carried_entities", None)
@@ -396 +395,4 @@ class ForgeToolQueryTool(Tool):
-                    if carried:
+                    if resolved_binding is not None:
+                        if resolved_arguments.get("carried_entities", []) != carried:
+                            raise AgentTaskError("Coordinator carry-forward changed after selection; select current evidence again")
+                    elif carried:
@@ -831 +833 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-    """Project Runtime-proven unchanged entities into one fresh understanding Query.
+    """Project Runtime-proven unchanged and held identities into fresh understanding.
@@ -840,0 +843 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
+    action = None
@@ -842 +845 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-        if record.semantics != "action" or record.status != "succeeded":
+        if record.semantics != "action":
@@ -843,0 +847,4 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
+        # Never resurrect an older successful effect across a newer unknown
+        # Action, even if it did not report a new scene revision.
+        if record.status != "succeeded":
+            return []
@@ -851 +858,2 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-            and candidate.get("carry_forward_authorized") is True
+            and facts.get("status") == "succeeded"
+            and facts.get("outcome_known") is True
@@ -854 +862,2 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-            break
+            action = record
+        break
@@ -858 +867 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-    unaffected = effect.get("unaffected_entity_refs")
+    unaffected = effect.get("unaffected_entity_refs", []) if effect.get("carry_forward_authorized") is True else []
@@ -862 +871 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-        or not isinstance(unaffected, list) or not unaffected
+        or not isinstance(unaffected, list)
@@ -867,0 +877,17 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
+    held = effect.get("held_entity")
+    held_ref = None
+    changed = effect.get("changed_entity_refs")
+    if isinstance(held, dict) and action is not None:
+        facts = response_facts(action.response)
+        entity_ref = held.get("entity_ref")
+        if (facts.get("status") == "succeeded" and facts.get("outcome_known") is True
+                and held.get("holding_state") == "holding"
+                and held.get("owner") == f"paos:{getattr(task, 'task_id', '')}"
+                and held.get("acquire_invocation_id") == getattr(action, "invocation_id", None)
+                and isinstance(held.get("acquire_invocation_id"), str)
+                and entity_ref == action.arguments.get("entity_ref")
+                and isinstance(entity_ref, str)
+                and isinstance(changed, list) and entity_ref in changed):
+            held_ref = entity_ref
+    if not unaffected and held_ref is None:
+        return []
@@ -898 +924 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-    for entity_ref in unaffected:
+    for entity_ref in dict.fromkeys([*unaffected, *([held_ref] if held_ref else [])]):
@@ -906,9 +932,10 @@ def _coordinator_carried_entities(task: Any, scene_revision: Any) -> list[dict[s
-        carried.append(
-            {
-                "entity": dict(claim),
-                "source_scene_revision": source_scene,
-                "source_binding_ref": binding_ref,
-                "execution_entity_ref": execution_ref,
-                "effect_evidence_refs": list(effect_refs),
-            }
-        )
+        item = {
+            "entity": dict(claim),
+            "source_scene_revision": source_scene,
+            "source_binding_ref": binding_ref,
+            "execution_entity_ref": execution_ref,
+            "effect_evidence_refs": list(effect_refs),
+        }
+        if entity_ref == held_ref:
+            item.update(carry_state="held", possession=dict(held))
+        carried.append(item)
```

#### [修改 / Modified] `PhyAgentOS/agent/tools/planning.py` L447-L459

```diff
--- a/PhyAgentOS/agent/tools/planning.py
+++ b/PhyAgentOS/agent/tools/planning.py
@@ -446,0 +447,13 @@ class ForgePlanSelectTool(Tool):
+            if tool_id == "scene.understand":
+                from PhyAgentOS.agent.tools.forge_tool_api import _coordinator_carried_entities
+
+                if "carried_entities" in final_arguments:
+                    raise PlanningDispatchError(
+                        "carried_entities is Coordinator-owned and cannot be supplied by the Agent",
+                        code="invalid_selection_arguments",
+                    )
+                carried = _coordinator_carried_entities(
+                    self.coordinator.get_task(task_id), final_arguments.get("scene_revision")
+                )
+                if carried:
+                    final_arguments = {**final_arguments, "carried_entities": carried}
```

#### [修改 / Modified] `PhyAgentOS/forge/capability_runtime/understanding.py` L229-L239, L540-L540, L543-L545, L563-L576, L907-L923, L987-L998, L1001-L1005, L1017-L1017, L1024-L1025, L1032-L1034

```diff
--- a/PhyAgentOS/forge/capability_runtime/understanding.py
+++ b/PhyAgentOS/forge/capability_runtime/understanding.py
@@ -228,0 +229,11 @@ TOOL_SPEC: dict[str, Any] = {
+                        "carry_state": {"enum": ["unchanged", "held"]},
+                        "possession": {
+                            "type": "object", "additionalProperties": False,
+                            "required": ["holding_state", "entity_ref", "owner", "acquire_invocation_id"],
+                            "properties": {
+                                "holding_state": {"const": "holding"},
+                                "entity_ref": {"type": "string", "pattern": _ENTITY_REF.pattern},
+                                "owner": {"type": "string", "minLength": 1},
+                                "acquire_invocation_id": {"type": "string", "minLength": 1},
+                            },
+                        },
@@ -529 +540 @@ def validate_arguments(arguments: Any) -> dict[str, Any] | None:
-        if not isinstance(item, dict) or set(item) != {
+        required = {
@@ -532 +543,3 @@ def validate_arguments(arguments: Any) -> dict[str, Any] | None:
-        }:
+        }
+        if (not isinstance(item, dict) or not required <= set(item)
+                or set(item) - required - {"carry_state", "possession"}):
@@ -549,0 +563,14 @@ def validate_arguments(arguments: Any) -> dict[str, Any] | None:
+        carry_state = item.get("carry_state", "unchanged")
+        possession = item.get("possession")
+        if carry_state not in {"unchanged", "held"}:
+            return _error("invalid_carry_forward", "carry state is invalid", observation_ref=observation_ref)
+        if carry_state == "held":
+            if (not isinstance(possession, dict)
+                    or set(possession) != {"holding_state", "entity_ref", "owner", "acquire_invocation_id"}
+                    or possession.get("holding_state") != "holding"
+                    or possession.get("entity_ref") != entity_ref
+                    or any(not isinstance(possession.get(key), str) or not possession[key]
+                           for key in ("owner", "acquire_invocation_id"))):
+                return _error("invalid_carry_forward", "held possession is invalid", observation_ref=observation_ref)
+        elif possession is not None:
+            return _error("invalid_carry_forward", "unchanged entity cannot claim possession", observation_ref=observation_ref)
@@ -879,0 +907,17 @@ def _metric_alias_ambiguities(
+def _remap_visual_identity(value: Any, aliases: dict[str, str]) -> Any:
+    """Keep fresh observation-local IDs distinct from Runtime-proven task IDs."""
+    if isinstance(value, list):
+        return [_remap_visual_identity(item, aliases) for item in value]
+    if isinstance(value, dict):
+        result = {}
+        for key, item in value.items():
+            if key in {"entity_ref", "subject_ref", "object_ref"} and isinstance(item, str):
+                result[key] = aliases.get(item, item)
+            elif key == "entity_refs" and isinstance(item, list):
+                result[key] = [aliases.get(ref, ref) for ref in item]
+            else:
+                result[key] = _remap_visual_identity(item, aliases)
+        return result
+    return deepcopy(value)
+
+
@@ -943 +987,12 @@ class SceneUnderstandingEndpoint:
-        entities = [dict(item) for item in normalized.entities]
+        reserved = {item["entity"]["entity_ref"] for item in carried_entities if item.get("carry_state") == "held"}
+        used = reserved | {item["entity_ref"] for item in normalized.entities}
+        aliases = {}
+        for ref in sorted(reserved & {item["entity_ref"] for item in normalized.entities}):
+            index = 1
+            alias = f"entity://observed-{ref.removeprefix('entity://')}-{index}"
+            while alias in used:
+                index += 1
+                alias = f"entity://observed-{ref.removeprefix('entity://')}-{index}"
+            aliases[ref] = alias
+            used.add(alias)
+        entities = [_remap_visual_identity(item, aliases) for item in normalized.entities]
@@ -946 +1001,5 @@ class SceneUnderstandingEndpoint:
-        reconciliations = [dict(item) for item in normalized.reconciliations]
+        reconciliations = [_remap_visual_identity(item, aliases) for item in normalized.reconciliations]
+        reconciliations.extend({
+            "code": "observation_local_identity_remapped", "entity_refs": [alias],
+            "source_entity_ref": ref, "observation_ref": observation_ref,
+        } for ref, alias in aliases.items())
@@ -958 +1017 @@ class SceneUnderstandingEndpoint:
-                    "code": "runtime_proven_entity_unchanged",
+                    "code": "runtime_proven_entity_held" if item.get("carry_state") == "held" else "runtime_proven_entity_unchanged",
@@ -965,2 +1024,2 @@ class SceneUnderstandingEndpoint:
-        ambiguities = [dict(item) for item in normalized.ambiguities]
-        ambiguities.extend(_metric_alias_ambiguities(normalized))
+        ambiguities = [_remap_visual_identity(item, aliases) for item in normalized.ambiguities]
+        ambiguities.extend(_remap_visual_identity(_metric_alias_ambiguities(normalized), aliases))
@@ -973,3 +1032,3 @@ class SceneUnderstandingEndpoint:
-            "relations": [dict(item) for item in normalized.relations],
-            "spatial_envelopes": [dict(item) for item in normalized.spatial_envelopes],
-            "derived_artifacts": [dict(item) for item in normalized.derived_artifacts],
+            "relations": [_remap_visual_identity(item, aliases) for item in normalized.relations],
+            "spatial_envelopes": [_remap_visual_identity(item, aliases) for item in normalized.spatial_envelopes],
+            "derived_artifacts": [_remap_visual_identity(item, aliases) for item in normalized.derived_artifacts],
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py` L703-L709

```diff
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
@@ -702,0 +703,7 @@ class RoboTwinPersistentEngine:
+        if (phase == "acquire" and result.get("status") == "succeeded"
+                and result.get("outcome_known") is True
+                and result["scene_effects"]["effect_scope_complete"] is True):
+            result["scene_effects"]["held_entity"] = {
+                "holding_state": "holding", "entity_ref": arguments["entity_ref"],
+                "owner": owner, "acquire_invocation_id": invocation_id,
+            }
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py` L188-L194, L283-L283, L354-L354, L358-L362, L380-L380, L436-L456

```diff
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py
@@ -188 +188,7 @@ class Grounding:
-                self._current(request)
+                state = self._current(request)
+                carried = {
+                    item["entity"]["entity_ref"]: item
+                    for item in understanding.get("carried_forward", [])
+                    if item.get("carry_state") == "held" and item["entity"]["entity_ref"] in selected
+                }
+                self._carried_objects(carried, binding["scene_facts"], state)
@@ -277 +283 @@ class Grounding:
-        self._current(request)
+        current_state = self._current(request)
@@ -348 +354 @@ class Grounding:
-        objects.update(self._carried_objects(selected_carried, facts))
+        objects.update(self._carried_objects(selected_carried, facts, current_state))
@@ -352 +358,5 @@ class Grounding:
-        self._current(request)
+        current_state = self._current(request)
+        self._carried_objects(
+            {ref: item for ref, item in selected_carried.items() if item.get("carry_state") == "held"},
+            facts, current_state,
+        )
@@ -370 +380 @@ class Grounding:
-    def _carried_objects(self, carried_by_ref, current_facts):
+    def _carried_objects(self, carried_by_ref, current_facts, current_state=None):
@@ -425,0 +436,21 @@ class Grounding:
+            carry_state = carried.get("carry_state", "unchanged")
+            if carry_state == "held":
+                possession = carried.get("possession")
+                if (not isinstance(possession, Mapping) or not isinstance(current_state, Mapping)
+                        or possession.get("entity_ref") != entity_ref
+                        or possession.get("holding_state") != "holding"
+                        or not possession.get("owner") or not possession.get("acquire_invocation_id")
+                        or any(current_state.get(key) != possession.get(key)
+                               for key in ("holding_state", "owner", "entity_ref", "acquire_invocation_id"))):
+                    self._reject("held entity possession no longer matches Runtime", stage="held_projection", entity_ref=entity_ref)
+                # Transport the existing observation-derived model with the
+                # physical object's rigid displacement. Never substitute actor
+                # dimensions or pretend this is a fresh visual measurement.
+                delta = current_pose @ np.linalg.inv(source_pose)
+                model = deepcopy(dict(source_model))
+                for key in ("world_T_object", "world_T_functional_point"):
+                    model[key] = (delta @ rigid_transform(model[key])).reshape(-1).tolist()
+                projected[entity_ref] = model
+                continue
+            if carry_state != "unchanged":
+                self._reject("carried entity state is invalid", stage="carry_forward", entity_ref=entity_ref)
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py` L321-L329

```diff
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py
@@ -320,0 +321,9 @@ class PersistentManipulationProvider:
+            effects = result.get("scene_effects")
+            if isinstance(effects, dict) and "held_entity" in effects:
+                # A historical engine receipt alone does not prove possession.
+                # Publish it only when the provider's settled ownership agrees.
+                held = effects["held_entity"]
+                if (self._state != "holding" or result.get("outcome_known") is not True
+                        or status != "succeeded" or not isinstance(held, dict)
+                        or held != self.snapshot()):
+                    effects.pop("held_entity")
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_grounding.py` L226-L284

```diff
--- a/examples/forge-adapters/robotwin20/tests/test_grounding.py
+++ b/examples/forge-adapters/robotwin20/tests/test_grounding.py
@@ -225,0 +226,59 @@ def test_holding_scene_binding_rejects_carried_entity_pose_drift(tmp_path):
+def setup_held_scene(tmp_path):
+    grounding, request = setup_carried_scene(tmp_path, move_selected=True)
+    understanding = next(value for value in grounding.understandings.values() if value["scene_revision"] == "s2")
+    held = understanding["carried_forward"][0]
+    held.update(carry_state="held", possession={
+        "holding_state": "holding", "entity_ref": "entity://seen", "owner": "paos:task-1",
+        "acquire_invocation_id": "invocation://acquire/1",
+    })
+    original_query = grounding.client.query
+    grounding.client.query = lambda operation, arguments: {
+        **original_query(operation, arguments), **held["possession"],
+    }
+    return grounding, request, held
+
+
+... additional held/unknown/persistence regression cases as listed above
```

#### [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py` L94-L115, L180-L181, L191-L191, L421-L454

```diff
--- a/examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py
+++ b/examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py
@@ -93,0 +94,22 @@ def test_cancelled_motion_retains_uncertain_possession_without_release():
+@pytest.mark.parametrize("mismatch", [False, True])
+def test_provider_publishes_held_receipt_only_with_matching_settled_possession(mismatch):
+    class HeldEngine(Engine):
+        def execute(self, phase, arguments, cancel, *, owner, invocation_id):
+            return {
+                **super().execute(phase, arguments, cancel, owner=owner, invocation_id=invocation_id),
+                "scene_effects": {"held_entity": {
+                    "holding_state": "holding", "entity_ref": arguments["entity_ref"],
+                    "owner": "other" if mismatch else owner,
+                    "acquire_invocation_id": invocation_id,
+                }},
+            }
+    provider = PersistentManipulationProvider(HeldEngine)
+    try:
+        provider.start("acquire", "invocation://acquire/1", "paos:task-1", {"entity_ref": "entity://container"})
+... additional held/unknown/persistence regression cases as listed above
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/scene.understand.tool.yaml` L148-L165

```diff
--- a/examples/forge-skills/pick-place-workflow/contracts/scene.understand.tool.yaml
+++ b/examples/forge-skills/pick-place-workflow/contracts/scene.understand.tool.yaml
@@ -147,0 +148,18 @@ input_schema:
+          carry_state:
+            enum: [unchanged, held]
+          possession:
+            type: object
+            additionalProperties: false
+            required: [holding_state, entity_ref, owner, acquire_invocation_id]
+            properties:
+              holding_state:
+                const: holding
+              entity_ref:
+                type: string
+                pattern: ^entity://[^/]+$
+              owner:
+                type: string
+                minLength: 1
+              acquire_invocation_id:
+                type: string
+                minLength: 1
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py` L270-L270

```diff
--- a/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
@@ -270 +270 @@ def test_bundle_and_package_versions_match_the_feature_revision():
-    assert bundle_manifest["version"] == "3.0.9"
+    assert bundle_manifest["version"] == "3.0.10"
```

#### [修改 / Modified] `examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py` L246-L295

```diff
--- a/examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py
+++ b/examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py
@@ -245,0 +246,50 @@ def test_runtime_proven_unchanged_entity_is_merged_without_reaching_visual_provi
+def held_projection():
+    return {
+        "entity": {"entity_ref": "entity://bottle-1", "category": "held container",
+                   "confidence": 0.92, "provenance": ["artifact://old/rgb"]},
+        "source_scene_revision": "old", "source_binding_ref": "artifact://bindings/old",
+        "execution_entity_ref": "entity://runtime-container",
+        "effect_evidence_refs": ["artifact://action/acquire"], "carry_state": "held",
+        "possession": {"holding_state": "holding", "entity_ref": "entity://bottle-1",
+                       "owner": "paos:task-1", "acquire_invocation_id": "invocation://acquire/1"},
+    }
+
+
+def test_held_projection_preserves_conflicting_visual_identity_and_geometry():
+    snapshot = understanding_snapshot(
+        entities=({**understanding_snapshot().entities[0], "category": "robot"},),
+... additional held/unknown/persistence regression cases as listed above
```

#### [修改 / Modified] `tests/test_forge_tool_api.py` L591-L591, L796-L1034

```diff
--- a/tests/test_forge_tool_api.py
+++ b/tests/test_forge_tool_api.py
@@ -591 +591 @@ def _carry_task(*, effect_overrides=None, include_effect=True):
-    action_result = {"status": "succeeded"}
+    action_result = {"status": "succeeded", "outcome_known": True}
@@ -795,0 +796,239 @@ def test_coordinator_does_not_carry_entities_without_complete_runtime_evidence(t
+
+
+def _held_task():
+    task = _carry_task(effect_overrides={
+        "unaffected_entity_refs": [], "carry_forward_authorized": False,
+        "held_entity": {
+            "holding_state": "holding", "entity_ref": "entity://held",
+            "owner": "paos:task-1", "acquire_invocation_id": "invocation://acquire/1",
+        },
+    })
+    task.task_id = "task-1"
+    task.execution_records[0].response["data"]["entities"][0]["entity_ref"] = "entity://held"
+... additional held/unknown/persistence regression cases as listed above
```

### 七维验收与验证 / Seven-Dimension Acceptance and Validation

- [eval] [fix] Core/AgentLoop + Adapter focused：`434 passed in 11.30s`；Skill 全量：`387 passed in 9.33s`；独立 provider boundary：`12 passed in 0.33s`；合计 833 项全部通过。(local)
- [eval] [fix] Core/AgentLoop + Adapter focused: `434 passed in 11.30s`; full Skill: `387 passed in 9.33s`; isolated provider boundary: `12 passed in 0.33s`; 833 tests passed in total. (local)
- [eval] [fix] Ruff、compileall、`git diff --check` 通过；七维审查五项 Major 已修复，无未解决 Blocker/Major；完整命令见审查文档。(local)
- [eval] [fix] Ruff, compileall, and `git diff --check` passed; five Major findings resolved with no outstanding Blocker/Major; exact commands are in the review. (local)
- [eval] [fix] 初次混合测试 `444 passed, 1 failed` 的唯一失败是既有全进程 sys.modules 边界测试；独立进程 12/12 通过。初次 Skill suite 的旧 3.0.9 断言已修正，最终全量通过。(local)
- [eval] [fix] The initial mixed process had `444 passed, 1 failed` from the existing whole-process sys.modules assertion; isolated provider tests passed 12/12. Corrected the initial stale 3.0.9 Skill assertion and the final full suite passed. (local)
- [env] [chore] 仅在临时测试库和 fake/no-motion seam 验证；未创建/恢复现场任务、调用 live Gateway Query/Action、推进 simulator/物理运动或安装/重启 Runtime。旧 receipt 不补造 held evidence；下一次部署需一起重建 Node 和 Skill contract。(local)
- [env] [chore] Validation used temporary test stores and fake/no-motion seams only; no live task creation/resumption, Gateway Query/Action, simulator/physical movement, or Runtime installation/restart. Old receipts receive no fabricated held evidence; the next deployment must rebuild Node and Skill contracts together. (local)

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`
- Commit: `859d1b8`（实现、诊断与七维审查 / implementation, diagnosis, and seven-dimension review）

## v12.10.12 (2026-10-09 00:35) - codex

### 预期修改 / Planned Changes [完成]
- [env] [chore] 用户授权后停止旧 `pick-place-workflow` Runtime；先确认 AgentTask 均为终态，再核验 invocation/session/task-binding ownership，旧 host/worker 退出后才安装新产物。(local)
- [env] [release] 将 Core editable 安装更新到当前已推送分支；从当前 Adapter/Core source 构建 Node `1.0.2`，更新 Skill 锁与版本至 `3.0.10`，构建并验证本地 Skill bundle 后原子安装。(local)
- [eval] [test] 启动同一 `robotwin-blocks-ranking-graspnet` profile，验证新 Skill/Node 锁、Gateway、Dora flow、所有 Tool readiness 与零活动任务/ownership；不恢复旧任务、不调用 Query/Action、不推进 simulator 或物理运动。(local)

### Planned Changes (English)
- [env] [chore] Under the user's authorization, stop the old `pick-place-workflow` Runtime; confirm all AgentTasks are terminal, inspect invocation/session/task-binding ownership, and install only after the old host/worker exit. (local)
- [env] [release] Refresh the Core editable installation from the current pushed branch; build Node `1.0.2` from current Adapter/Core sources, update the Skill lock/version to `3.0.10`, build and verify the local Skill bundle, then install atomically. (local)
- [eval] [test] Start the same `robotwin-blocks-ranking-graspnet` profile and verify the new Skill/Node lock, Gateway, Dora flow, all Tool readiness, and zero active task/ownership; do not resume old tasks, invoke Query/Action, or advance simulator/physical motion. (local)

### 实际修改 / Completed Changes
- [env] [chore] `paos skill stop pick-place-workflow --force` 在用户授权后完成；旧 Dora flow、host/worker 和 Runtime binding 已退出后才安装新产物。当前任务库仅有 1 个历史 `cancelled` 任务，非终态任务为 0。(local)
- [env] [chore] `.venv/bin/python -m pip install -e .` 完成当前 Core editable 安装；未改变 AgentTask、Gateway 或 Action 状态。(local)
- [env] [release] `examples/forge-adapters/robotwin20/pyproject.toml:L1-L6` Adapter `0.9.12` → `0.9.13`；`examples/forge-skills/pick-place-workflow/pyproject.toml:L1-L6` Skill `3.0.9` → `3.0.10`。(local)
- [env] [release] `examples/forge-skills/pick-place-workflow/skill.yaml:L1-L8,L220-L231` 锁定 Skill `3.0.10`、Node `1.0.2` 及 Node SHA-256 `e2361540634d9a9d950864caffa4a26cbdc05835daa12a1073373f84ad25e9e2`；Node archive `robotwin20_persistent_host-1.0.2-linux-x86_64.tar.gz` 为 `414538` bytes。(local)
- [env] [release] 本地 Skill bundle `pick-place-workflow-3.0.10.tar.gz` 已构建并安装，SHA-256 为 `e2d1c54c21bc49d1800675eb8e1f6861edce9530fbc3bb3a329120fdd557f360`；`paos forge-node verify pick-place-workflow robotwin20_persistent_host` 通过。(local)
- [eval] [test] 同一 `robotwin-blocks-ranking-graspnet` profile 已启动新 flow；日志确认 spawner 使用 `robotwin20_persistent_host-1.0.2`，`paos skill status` 显示 running、Gateway `/tools` ready、11/11 Tool context ready。启动前日志中的旧 SIGKILL/semantic failure 属于被 force-stop 的旧 flow；新 flow 在 `00:45:18` 完成 spawning，当前 worker 仍存活。(local)
- [eval] [test] 全程只做 lifecycle、editable install、bundle/node verify、SQLite 状态检查和 health/readiness 读取；未创建或恢复 AgentTask，未调用 Gateway Query/Action，未推进 simulator 或物理运动。(local)

### Completed Changes (English)
- [env] [chore] With user authorization, `paos skill stop pick-place-workflow --force` completed before installation; the old Dora flow, host/worker, and Runtime binding exited first. The task store contains only one historical `cancelled` task and zero non-terminal tasks. (local)
- [env] [chore] Refreshed the current Core editable installation with `.venv/bin/python -m pip install -e .`; no AgentTask, Gateway, or Action state was changed. (local)
- [env] [release] Bumped the Adapter from `0.9.12` to `0.9.13` and the Skill from `3.0.9` to `3.0.10` in the listed project files. (local)
- [env] [release] Locked Skill `3.0.10`, Node `1.0.2`, and Node SHA-256 `e2361540634d9a9d950864caffa4a26cbdc05835daa12a1073373f84ad25e9e2`; the Node archive is `414538` bytes. (local)
- [env] [release] Built and installed the local `pick-place-workflow-3.0.10.tar.gz` bundle with SHA-256 `e2d1c54c21bc49d1800675eb8e1f6861edce9530fbc3bb3a329120fdd557f360`; `paos forge-node verify pick-place-workflow robotwin20_persistent_host` passed. (local)
- [eval] [test] Restarted the same `robotwin-blocks-ranking-graspnet` profile; logs confirm the spawner uses `robotwin20_persistent_host-1.0.2`, while status reports running, Gateway `/tools` ready, and all 11/11 Tool contexts ready. The earlier SIGKILL/semantic failure belongs to the force-stopped flow; the new flow spawned at `00:45:18` and its worker remains alive. (local)
- [eval] [test] Validation was limited to lifecycle, editable install, bundle/node verification, SQLite status, and health/readiness reads; no AgentTask was created or resumed, no Gateway Query/Action was invoked, and no simulator or physical motion advanced. (local)

### 关键 Diff / Key Diff
```diff
-version = "0.9.12"
+version = "0.9.13"
-version = "3.0.9"
+version = "3.0.10"
-artifact_id: robotwin20_persistent_host-1.0.1-linux-x86_64
+artifact_id: robotwin20_persistent_host-1.0.2-linux-x86_64
```

### Git 提交 / Git Commit
- Commit: `db2e148`（部署记录 / deployment record）
- Branch: `feature/planning-loop`; 时间 / Time: 2026-10-09 Asia/Shanghai

## v12.10.11 (2026-10-09 00:10) - codex

### 预期修改 / Planned Changes [完成]
- [comm] [fix] 保留 Qwen/vLLM transport、timeout 与 authentication 分类穿过异常包装，使 PAOS `scene.understand` 的结构化 `error.reason` 不再退化为 `provider_failure`；不改变 fallback、ToolSpec 或 AgentLoop 的授权边界。(local)
- [comm] [fix] 将 Core provider diagnostics 的 route 校验从固定模型名白名单改为有界 provider-neutral token，保留任意合法配置 route 的可观测性，同时拒绝异常文本和超长值。(local)
- [comm] [fix] 为 persistent Adapter diagnostic sink 增加同一有界 token 约束，避免配置化 provider route 造成无界日志记录；失败场景是任意配置 route 或 provider 注入值跨 JSONL/Tool 边界膨胀，现有类型检查不足以限制长度。(local)
- [eval] [test] 增加 endpoint transport reason、动态 fallback route、恶意/超长 diagnostic token 与异常包装分类回归；全部使用 fake provider/no-motion，不创建任务、不调用真实 Gateway、不推进 simulator 或物理运动。(local)
- [docs] [docs] 新增七维 Code Review，记录 Blocker/Major/Minor、修复行号、扩展性和 PAOS ownership；不加入 RGB、颜色、排列、相机、对象数量或固定机械臂分支。(local)

### Planned Changes (English)
- [comm] [fix] Preserve Qwen/vLLM transport, timeout, and authentication classes through exception wrapping so the PAOS `scene.understand` structured `error.reason` does not degrade to `provider_failure`; keep fallback, ToolSpec, and AgentLoop authority unchanged. (local)
- [comm] [fix] Replace the Core provider-diagnostics route allowlist of fixed model names with a bounded provider-neutral token, preserving observability for any valid configured route while rejecting exception text and oversized values. (local)
- [comm] [fix] Apply the same bounded token constraint before persistent Adapter diagnostic events are written, preventing a configured provider route from producing unbounded JSONL records; the concrete failure is an arbitrary configured/injected route expanding across the JSONL/Tool seam, which type checks alone do not limit. (local)
- [eval] [test] Add regressions for endpoint transport reasons, dynamic fallback routes, malicious/oversized diagnostic tokens, and wrapped-exception classification; use only fake providers/no-motion with no task, real Gateway, simulator, or physical motion. (local)
- [docs] [docs] Add the seven-dimension Code Review with Blocker/Major/Minor findings, fix line references, extensibility, and PAOS ownership; add no RGB, color, arrangement, camera, object-count, or fixed-arm branch. (local)

### 实际修改 / Completed Changes
- [comm] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_scene_understanding.py:L27-L87,L128-L144,L265-L286`：异常包装携带有界 `provider_error_class` 与 `retryable`，并在 transport/timeout 前识别 authentication。(local)
- [comm] [fix] `PhyAgentOS/forge/capability_runtime/understanding.py:L24-L27,L379-L429`：Core route 改为有界 provider-neutral token；错误类别使用稳定词汇组合校验，非法声明 fail-closed。(local)
- [comm] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_lifecycle.py:L15-L20,L281-L299`、`persistent_host.py:L63-L65,L136-L170`：lifecycle、readiness 和 JSONL sink 统一拒绝超长、空白或非结构化 diagnostic token。(local)
- [eval] [test] 新增动态 fallback route、transport/timeout/authentication 分类、异常包装、非法 token 和 JSONL sink 回归；Adapter `80 passed`，Core focused `118 passed`。(local)
- [docs] [docs] 新增 `docs/forge/IMPLEMENTATION_REVIEW_V12_10_11.md`，记录三项 Major 的发现与修复、七维验收、精确行号和残余风险。(local)

### Completed Changes (English)
- [comm] [fix] `qwen3_vl_vllm_scene_understanding.py:L27-L87,L128-L144,L265-L286`: preserve bounded `provider_error_class` and `retryable` through exception wrapping, and classify authentication before transport/timeout. (local)
- [comm] [fix] `understanding.py:L24-L27,L379-L429`: replace the fixed Core route allowlist with bounded provider-neutral tokens and validate composed error classes against the stable vocabulary; invalid declarations fail closed. (local)
- [comm] [fix] `qwen3_vl_vllm_lifecycle.py:L15-L20,L281-L299` and `persistent_host.py:L63-L65,L136-L170`: reject oversized, whitespace-containing, or unstructured diagnostic tokens at lifecycle, readiness, and JSONL seams. (local)
- [eval] [test] Add dynamic fallback-route, transport/timeout/authentication, wrapped-exception, invalid-token, and JSONL-sink regressions; Adapter `80 passed`, Core focused `118 passed`. (local)
- [docs] [docs] Add `docs/forge/IMPLEMENTATION_REVIEW_V12_10_11.md` with the three Major findings, seven-dimension acceptance, exact line references, and residual risks. (local)

### 关键 Diff / Key Diff
```diff
-raise Qwen3VLVLLMInferenceError("qwen vLLM scene understanding request failed") from exc
+raise Qwen3VLVLLMInferenceError(
+    "qwen vLLM scene understanding request failed",
+    provider_error_class=error_class,
+    retryable=error_class in {"timeout", "transport"},
+ ) from exc
```
```diff
-item in {"qwen3-vl-4b-vllm", "gpt-6.1-sol-high", ...}
+_DIAGNOSTIC_TOKEN.fullmatch(item) and _valid_provider_error_class(item)
```

### 验证 / Validation
- [eval] [test] `80 passed`（Adapter Provider/lifecycle/fallback/endpoint/host）；`118 passed`（Core planning/tool/runtime focused）；Ruff、compileall、`git diff --check` 通过。全程未创建或恢复任务、未调用 Gateway Query/Action、未推进 simulator 或物理运动，Runtime 未重启。(local)
- [eval] [test] `80 passed` (Adapter provider/lifecycle/fallback/endpoint/host) and `118 passed` (Core planning/tool/runtime focused); Ruff, compileall, and `git diff --check` passed. No task was created or resumed, no Gateway Query/Action was invoked, no simulator or physical motion advanced, and Runtime was not restarted. (local)
- [eval] [test] Adapter 全量 collection `844 passed, 18 failed`；失败为当前解释器缺少 `scipy/cv2/PyYAML` 及既有 Action/video/backend fixture，不在本次 Provider diagnostics 改动路径；无 changed-path failure。(local)
- [eval] [test] Full Adapter collection reported `844 passed, 18 failed`; failures were missing `scipy/cv2/PyYAML` in the current interpreter and existing Action/video/backend fixtures outside the Provider diagnostics path; no changed-path failure. (local)

### Git 提交 / Git Commit
- Commit: `1e3d4a8`（实现与七维审查 / implementation and seven-dimension review）
- Branch: `feature/planning-loop`; 时间 / Time: 2026-10-09 Asia/Shanghai

## v12.10.10 (2026-10-08 23:20) - codex

### 预期修改 / Planned Changes [计划]
- [comm] [fix] 修复 Qwen/VLLM 场景理解生命周期包装层丢失 `diagnostic_summary`，导致真实 Provider 错误被投影为 `provider_error_class=none`；保持 PAOS ToolSpec 的 bounded diagnostics，不泄露异常文本或模型输出。(local)
- [comm] [fix] 修复配置 fallback 仅捕获 lifecycle/contract 子类、遗漏基础 `Qwen3VLVLLMInferenceError` 的通用边界；将已确认的 transport、timeout、contract 与 provider failure 分类在 Adapter 内保持可恢复/不可恢复语义。(local)
- [eval] [test] 增加生命周期诊断透传、Qwen 基础异常分类和 fallback 路由回归；所有验证使用 fake provider/no-motion，不创建任务、不调用真实 Gateway、不推进 simulator 或物理动作。(local)
- [docs] [docs] 保存本次 `after_red_understand` provider failure 诊断，记录执行阶段、HTTP 200 但 Provider 投影失败的证据、视频路径、PAOS ownership 和 AgentLoop fail-closed 边界；不加入 RGB、颜色、排列、相机或固定 Tool 分支。(local)

### Planned Changes (English)
- [comm] [fix] Preserve `diagnostic_summary` through the Qwen/vLLM lifecycle wrapper so a real Provider failure is not projected as `provider_error_class=none`; retain bounded PAOS diagnostics without exposing exception text or model output. (local)
- [comm] [fix] Cover the generic `Qwen3VLVLLMInferenceError` in the configured fallback boundary instead of catching only lifecycle/contract subclasses; preserve transport, timeout, contract, and provider-failure recovery semantics at the Adapter boundary. (local)
- [eval] [test] Add regressions for lifecycle diagnostic passthrough, Qwen base-error classification, and fallback routing; all validation is fake/no-motion with no task, real Gateway, simulator, or physical motion. (local)
- [docs] [docs] Save the `after_red_understand` Provider-failure diagnosis with execution phase, HTTP-200/provider-projection evidence, video paths, PAOS ownership, and AgentLoop fail-closed boundaries; add no RGB, color, arrangement, camera, or fixed-Tool branch. (local)

### 实际修改 / Completed Changes
- [comm] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_scene_understanding.py:L66-L75,L111-L124,L206-L262,L332-L455`：将模型输出、JSON、响应字段、provenance 和语义投影错误归类为 bounded `contract`，保留 timeout/transport/provider failure 分类，并在 Qwen 诊断摘要中保留实际错误类别。(local)
- [comm] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_lifecycle.py:L278-L293`：生命周期包装层透传 `provider_route` 与 `provider_error_class`，仅允许有界字段通过，不暴露异常文本。(local)
- [comm] [fix] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py:L53-L58,L654-L666`：fallback profile 捕获基础 `Qwen3VLVLLMInferenceError`，使通用 Provider 失败按既有 fallback policy 处理。(local)
- [eval] [test] `test_qwen3_vl_vllm_lifecycle.py`、`test_qwen3_vl_vllm_scene_understanding.py`、`test_scene_understanding_fallback.py` 增加诊断透传、合同失败分类、基础异常 fallback 和 no-motion 回归；Adapter focused suite `74 passed`。(local)
- [docs] [docs] 新增 `docs/forge/SCENE_UNDERSTANDING_PROVIDER_FAILURE_DIAGNOSIS_20261008.md:L1-L81`，保存任务阶段、证据、根因、PAOS ownership、AgentLoop 停止边界与残余风险。(local)

### Completed Changes (English)
- [comm] [fix] `qwen3_vl_vllm_scene_understanding.py:L66-L75,L111-L124,L206-L262,L332-L455`: classify model output, JSON, response-field, provenance, and semantic projection failures as bounded `contract` errors while preserving timeout/transport/provider-failure categories and exposing the actual bounded class in diagnostics. (local)
- [comm] [fix] `qwen3_vl_vllm_lifecycle.py:L278-L293`: forward only `provider_route` and `provider_error_class` across the lifecycle wrapper; exception text never crosses the seam. (local)
- [comm] [fix] `persistent_host.py:L53-L58,L654-L666`: include the base `Qwen3VLVLLMInferenceError` in the configured fallback boundary. (local)
- [eval] [test] Add diagnostics passthrough, contract classification, generic-error fallback, and no-motion regressions; the focused Adapter suite passes `74`. (local)
- [docs] [docs] Add `SCENE_UNDERSTANDING_PROVIDER_FAILURE_DIAGNOSIS_20261008.md:L1-L81` with phase, evidence, root cause, PAOS ownership, AgentLoop stop boundary, and residual risk. (local)

### 验证 / Validation
- [eval] [test] `74 passed`（Qwen lifecycle/provider/fallback/scene endpoint/persistent host changed path）；compileall、Ruff、`git diff --check` 通过。全程未创建或恢复任务、未调用真实 Gateway Query/Action、未推进 simulator 或物理运动。(local)
- [eval] [test] `74 passed` on the changed Adapter path; compileall, Ruff, and `git diff --check` passed. No task was created or resumed, no real Gateway Query/Action was invoked, and no simulator or physical motion advanced. (local)

### Git 提交 / Git Commit
- Commit: `66a9d07`（implementation / 实现）; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.9 (2026-10-08 21:00) - codex

### 预期修改 / Planned Changes [完成]
- [env] [chore] 在用户明确授权下停止旧的 `pick-place-workflow` Runtime，确认不存在活动任务或未对账 Action 后，安装当前分支的 Core/Adapter/Skill 产物并重启既有 profile。(local)
- [eval] [test] 仅执行 no-motion 生命周期健康检查：Runtime/Dora、Gateway、Tool contexts、运行时所有权及持久化任务状态；不创建任务、不调用 Query/Action、不推进模拟器。(local)

### Planned Changes (English)
- [env] [chore] Under explicit user authorization, stop the old `pick-place-workflow` Runtime, confirm no active task or unreconciled Action, install the current branch Core/Adapter/Skill artifacts, and restart the existing profile. (local)
- [eval] [test] Run only no-motion lifecycle health checks for Runtime/Dora, Gateway, Tool contexts, runtime ownership, and persisted task state; create no task, invoke no Query/Action, and advance no simulator. (local)

### 实际执行 / Completed Execution
- [env] [chore] 用户明确授权后执行 `paos skill stop pick-place-workflow --force`；旧 Runtime 进入 `stopped`，Dora flow down，Gateway unavailable，进程树无 persistent host/worker；停止前任务库仅有 1 个 `cancelled` 任务，非终态任务为 0。 (local)
- [env] [chore] After explicit user authorization, ran `paos skill stop pick-place-workflow --force`; the old Runtime became `stopped`, the Dora flow went down, Gateway became unavailable, and no persistent host/worker remained; before stopping, the task database contained only one `cancelled` task and zero non-terminal tasks. (local)
- [env] [chore] `.venv/bin/python -m pip install -e .` 成功；`PhyAgentOS` import 指向当前工作树 `/home/yanxu/PhyAgentOS-forge/PhyAgentOS/__init__.py`，CLI 为 `PhyAgentOS v1.0.2`。使用当前已验证的 Skill `3.0.9` bundle 和 Node `1.0.1`，通过 `paos skill install --local --yes` 保持原子安装状态。 (local)
- [env] [chore] `.venv/bin/python -m pip install -e .` succeeded; `PhyAgentOS` imports from the current worktree `/home/yanxu/PhyAgentOS-forge/PhyAgentOS/__init__.py` and the CLI reports `PhyAgentOS v1.0.2`. The current verified Skill `3.0.9` bundle and Node `1.0.1` were retained through `paos skill install --local --yes`. (local)
- [env] [chore] 使用原 operator env `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env` 启动 profile `robotwin-blocks-ranking-graspnet`。 (local)
- [env] [chore] Started profile `robotwin-blocks-ranking-graspnet` with the existing operator env `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env`. (local)

### 文件变更详情 / File Change Details
- [修改 / Modified] `changelog/2026-10_part2.md:L3-L35`：补全停止旧实例、editable 安装、Skill/Node 安装、重启和 no-motion 验收记录；本次无 Core、Adapter、ToolSpec、Skill source 或 Node source 修改。 (local)
- [modified] `changelog/2026-10_part2.md:L3-L35`: complete the stop, editable-install, Skill/Node installation, restart, and no-motion acceptance record; no Core, Adapter, ToolSpec, Skill source, or Node source was modified in this deployment. (local)

### 验证 / Validation
- [eval] [test] 新 Runtime `runtime_4cb91725948c4f16` running；Dora flow running；Gateway `/tools` `ok=true` 且返回 11 个 Tool；`paos skill status` 显示 11/11 Tool contexts ready；实际 spawn 为 `robotwin20_persistent_host-1.0.1-linux-x86_64`。 (local)
- [eval] [test] New Runtime `runtime_4cb91725948c4f16` is running; the Dora flow is running; Gateway `/tools` returns `ok=true` with 11 Tools; `paos skill status` reports all 11/11 Tool contexts ready; the actual spawn is `robotwin20_persistent_host-1.0.1-linux-x86_64`. (local)
- [eval] [test] Node lock SHA-256 `947c2815fe1f9fbb18b4c5794112259f792612e9963314c01df2f49d81ecbc63` 通过 `paos forge-node verify`；`active_invocations=[]`、`active_sessions=[]`、`active_task_bindings=[]`；任务库非终态数量为 0。 (local)
- [eval] [test] Node lock SHA-256 `947c2815fe1f9fbb18b4c5794112259f792612e9963314c01df2f49d81ecbc63` passed `paos forge-node verify`; `active_invocations=[]`, `active_sessions=[]`, and `active_task_bindings=[]`; persisted non-terminal task count is 0. (local)
- [eval] [test] 全程仅执行 lifecycle、editable install、bundle install、Node verify 与只读 status/inspect/logs/Gateway GET；未创建或恢复任务，未调用 Query/Action，未推进 simulator 或物理运动。 (local)
- [eval] [test] Only lifecycle, editable installation, bundle installation, Node verification, and read-only status/inspect/logs/Gateway GET were run; no task was created or resumed, no Query/Action was invoked, and no simulator or physical motion advanced. (local)

### Git 提交 / Git Commit
- Commit: `42b706b`（部署记录 / deployment record）; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai
