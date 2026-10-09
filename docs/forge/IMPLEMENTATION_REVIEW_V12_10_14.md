# Implementation Review v12.10.14 / 七维复审

Reviewed implementation: `859d1b8` (v12.10.13); log commit: `df1f54e`.
本轮复审上一版 held-entity 身份连续性修改，并直接修复以下两项 Major。

## Findings and disposition / 发现与修复

### Major fixed: visual alias can drop an unchanged identity

Location: `PhyAgentOS/forge/capability_runtime/understanding.py:L988-L989`.

The alias allocator reserved only held IDs and observed IDs. If the generated
`entity://observed-bottle-1-1` was already an unchanged carried identity, the
merge later treated that carried entity as present and silently discarded it.
This can replace a task object with a visual robot claim.

修复：分配视觉别名前保留全部 Coordinator carried ID 和当前视觉 ID；
沿用现有确定性别名机制，不增加 schema、hash 或 gate。

Two regression cases failed on the old implementation (entity count lost one),
then passed after the fix. They cover consecutive carried/observed collisions,
entity uniqueness, relations, envelopes, derived artifacts, ambiguities, and
preservation of the original provider snapshot.

### Major fixed: source understanding and binding can refer to different observations

Location: `PhyAgentOS/agent/tools/forge_tool_api.py:L844-L845,L897-L915`.

The helper independently selected the latest understanding and latest binding
with the same scene revision. Re-observation may reuse local IDs; re-understanding
after a binding may change claims even for the same observation. The resulting
projection could attach a new category to an older physical execution identity.

修复：仅从最新 Action 之前选取 available binding，再读取该 binding 之前、
observation/scene/calibration 全部一致的 available understanding；Action 已声明
lineage 时也必须一致。缺失或不匹配时使用既有空投影行为，保持 fail-closed。

Eight initial regression cases failed on the old implementation and passed after
the repair. Additional cases cover Action lineage, unavailable source results,
missing observation identity, and a post-Action binding attempting to replace
the original source. Both held and unchanged paths are covered.
The existing real SQLite selection-to-execution test also passed.

## Seven dimensions / 七个维度

| Dimension / 维度 | Acceptance / 验收 |
| --- | --- |
| Architecture / 架构 | Runtime owns possession; Coordinator pairs persisted task evidence; understanding owns deterministic visual ID remapping; Adapter owns correspondence and geometry. |
| Correctness / 正确性 | All carried IDs are reserved; source records share observation/scene/calibration and causal ordering; synthetic failures reproduce both findings. |
| Recovery and idempotency / 恢复与幂等 | Latest unknown Action still blocks carry; selected arguments stay unchanged; cached held binding still verifies possession; no Action retry. |
| Robotics safety / 机器人安全 | Possession mismatch and unchanged pose drift remain rejected; rigid world transforms remain metre-based; motion_authorized=false and existing collision/admission/stop controls remain. |
| Extensibility / 扩展兼容 | Uses existing identity fields and alias allocation; no RGB, task ID, object count, camera, arm, provider, or filesystem-path branch; legacy unchanged payloads remain valid. |
| Observability and maintainability / 可观测与维护 | Existing identity-remap reconciliation retains original visual provenance; this report preserves reproductions, diff, source locations and exact validation commands. |
| AgentLoop autonomy and convergence / 自主与收敛 | Coordinator supplies facts without selecting next nodes; existing no-progress/reconciliation stops remain; no automatic observe/bind/replan/Action added. |

No outstanding Blocker or Major remains within the reviewed scope.
本轮两项 Major 已修复；未发现额外未解决 Blocker/Major。

## Validation / 验证

From repository root:

```bash
export PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src
.venv/bin/python -m pytest -q tests/test_forge_tool_api.py tests/test_planning_selection.py tests/test_planning_source_assembly.py tests/test_planning_task_integration.py tests/test_planning_loop.py tests/test_agent_foundation.py examples/forge-adapters/robotwin20/tests/test_grounding.py examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py examples/forge-adapters/robotwin20/tests/test_persistent_agent_loop.py examples/forge-adapters/robotwin20/tests/test_persistent_route_builder.py
.venv/bin/python -m pytest -q examples/forge-skills/pick-place-workflow/tests
.venv/bin/python -m pytest -q examples/forge-adapters/robotwin20/tests/test_scene_understand_provider.py
.venv/bin/ruff check PhyAgentOS/agent/tools/forge_tool_api.py PhyAgentOS/forge/capability_runtime/understanding.py tests/test_forge_tool_api.py examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py
.venv/bin/python -m compileall -q PhyAgentOS/agent/tools/forge_tool_api.py PhyAgentOS/forge/capability_runtime/understanding.py
git diff --check
```

Final results: Core/AgentLoop + Adapter `448 passed in 11.89s`; full Skill
`389 passed in 9.39s`; isolated provider `12 passed in 0.32s`.
Total: 849 passed, including 16 new cases. Ruff and compileall passed.
Provider import-boundary tests ran separately, as documented in v12.10.13.

## Limits and deployment / 边界与部署

All verification used temporary test stores, fake providers/workers, and
synthetic transforms. No live task, Gateway Query/Action, simulator step,
installation, Runtime restart, or hardware motion was performed.
本轮为源码复审修复，不代表现场完整任务已成功。Node/Skill 产物仍需在部署时
一同重建，旧 receipt 不补造 held evidence，未知动作不得为验证而重发。
Historical diagnosis and video references remain in
[HELD_ENTITY_PROJECTION_DIAGNOSIS_20261009.md](HELD_ENTITY_PROJECTION_DIAGNOSIS_20261009.md).
