# Changelog

## Archive

- [2026-09 Part 6](changelog/2026-09_part6.md)
- [2026-09 Part 5](changelog/2026-09_part5.md)
- [2026-09 Part 4](changelog/2026-09_part4.md)

## 最近 5 条 / Latest Five Versions

## v8.4.0 (2026-09-09 20:00) - codex

### 变更摘要 / Change Summary

- [完成] [policy] [feat] 新增 `MultiObjectAgentRunner`，绑定可信多对象场景事实，支持显式 baseline/semantic PlanGraph，并复用 AgentLoop、Coordinator 和现有 Gateway 路径；进化模块和真实硬件不在范围内。(local)
- [Completed] [Policy] [Feat] Added `MultiObjectAgentRunner` with trusted multi-object scene binding, explicit baseline/semantic PlanGraph modes, and reuse of AgentLoop, Coordinator, and the existing Gateway path; evolution and live hardware remain out of scope. (local)

### 文件变更详情 / File Details

- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/multi_object_agent.py` L1-L206 [新增 / Added]: 实体事实绑定、PlanNode context bindings 和 AgentTask runner / scene-fact binding, PlanNode context bindings, and AgentTask runner.
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py` L43-L75, L148-L152, L224-L237 [修改 / Modified]: 接受并持久化 opaque context bindings / accept and persist opaque context bindings.
- `examples/forge-skills/pick-place-workflow/tests/test_multi_object_agent.py` L1-L91 [新增 / Added]: 多对象入口边界测试 / multi-object entry boundary tests.
- `docs/forge/MULTI_OBJECT_AGENT_LOOP_EXECUTION_PLAN_20260909.md` L1-L106 [新增 / Added]: 审核、执行和六维验收矩阵 / audit, execution, and six-dimensional acceptance matrix.

### 验证 / Validation

- Focused `10 passed`; broad `576 passed`; Ruff, compileall, and diff checks passed.
- Action/Verifier real-runtime evidence remains pending; current six-dimensional result is staged, not final physical success.

## v8.3.1 (2026-09-09 19:32) - codex

### 预期修改 / Planned Changes

- [完成] [env] [fix] 修复持久部署可接入不同 worker client 的具体错误，使准备、观测与 Action 复用同一世界连接；使用普通对象身份检查，不增加授权门禁。(local)
- [Completed] [env] [fix] Reject mismatched worker clients so preparation, observation and Actions share one world connection, using ordinary identity checks rather than new authorization gates. (local)
- [完成] [eval] [exp] 通过 ForgeToolClient 验证 seed 0 真实观测与几何感知，绿色方块 GraspGen 重放获得 24 个候选；整体 Agent/Action/Verifier 验收仍未通过。(local)
- [Completed] [eval] [exp] Validate seed-0 public observation and measured geometry; green-cube GraspGen replay returns 24 proposals. Full Agent/Action/Verifier acceptance remains incomplete. (local)

### 文件变更详情 / File Details

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py` L61-L66 [修改 / Modified]: 拒绝不同世界连接 / reject different world connections.
- `examples/forge-adapters/robotwin20/scripts/check_persistent_runtime.py` L10-L217 [修改 / Modified]: 公共 Query、几何/抓取配置、唯一目标选择与日志 / public Queries, geometry/grasp configuration, unique target selection and logs.
- `examples/forge-adapters/robotwin20/scripts/run_grasp_proposals.py` L21-L32 [修改 / Modified]: 失败产物与 worker 日志留存 / retain failure artifacts and worker logs.
- `examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py` L46-L70 [修改 / Modified]: 单连接装配及混用拒绝 / single-client assembly and mismatch rejection.
- `examples/forge-adapters/robotwin20/tests/test_persistent_public_smoke.py` L1-L55 [新增 / Added]: 新鲜捕获、不可用、目标缺失/歧义 / fresh capture, unavailable source, missing/ambiguous target.
- `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md` L268-L313 [新增 / Added]: 真实证据、完整复现命令与未完成项 / real evidence, reproduction command and remaining work.
- `CHANGELOG.md` [修改 / Modified]: 从月度日志生成最新五版本全文，补回 v8.1.1；月度历史不变 / regenerate latest five complete entries including v8.1.1, preserving monthly history.

### 关键 Diff / Key Diff

```diff
+if any(component.client is not client for component in (
+    deployment.preparation_provider, deployment.capability_provider, deployment.prepared_routes,
+)):
+    raise ValueError("persistent runtime and deployment must share one worker client")
-observation = ObservationEndpoint(SimpleNamespace(capture=lambda request: second)).invoke(...)
+observation = asyncio.run(invoke_public_query(runtime, "scene.observe", ...))
+selected_entity = select_grasp_target(understanding, args.grasp_target_category)
-result = provider.propose(request)
+try:
+    result = provider.propose(request)
+finally:
+    # persist both the result/error and worker log
```

### 验证与六维验收 / Validation and Six Dimensions

- 原始全量 / Initial full run: 984 passed, 1 skipped, 1 failed (`test_paos_import_boundary_remains_clean`, process-wide import contamination). Isolated file passed.
- 修复后广域 / Broad regression after fixes: 986 passed, 1 skipped, 1 deselected; targeted final tests: 12 passed, including isolated import-boundary coverage and new target-selection coverage.
- Command: `PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin tests examples/forge-adapters/robotwin20/tests examples/forge-skills/pick-place-workflow/tests -k 'not test_paos_import_boundary_remains_clean'`.
- 实测 / Measured: seed 0 sensor PASS; semantic model PASS; three cubes with nine measured geometry artifacts PASS; explicit green-cube replay 24 candidates. Broad grasp failed on a desktop-surface target; target selection corrected. No motion/Action/final Verifier result.
- 架构 / Architecture: PARTIAL, assembly fixed; Agent task entry and installed Skill Bundle still need integration.
- 失败路径 / Failures: PARTIAL, tested sensor/client/target failures and retained model diagnostics; live Action recovery not run.
- 权限安全 / Safety: existing route checks preserved; no motion performed or new authorization introduced.
- 配置复现 / Reproducibility: real dedicated environments and external profiles recorded; model wording and grasp sampling can vary.
- 可维护性 / Maintainability: reused providers/transport, no parallel scheduler; complete root-test import isolation remains an existing issue.
- 可观察性 / Observability: measured artifacts and worker logs available; task-level Action/Verifier receipts still absent.
- 整体验收未通过 / Overall task acceptance remains incomplete. Artifact paths and full live command are in the status document above.

### Git 提交 / Git Commit

- Commit: `96b3631`; Branch: `feature/planning-loop`; 时间 / Time: 2026-09-09 (Asia/Shanghai).

- Branch: `feature/planning-loop`; implementation commit: `c560bef`; date: 2026-09-09 (Asia/Shanghai).

## v8.3.0 (2026-09-09 19:20) - codex

### 预期修改 / Planned Changes

- [完成] [env] [feat] 增加 Robotwin20 持久 Runtime Bundle 组合根，将现有 deployment provider、CapabilityRuntime 和 HTTP transport 接到同一 ForgeToolClient 边界。(local)
- [Completed] [Env] [Feat] Add a Robotwin20 persistent Runtime Bundle composition root wiring the existing deployment providers, CapabilityRuntime, and HTTP transport to one ForgeToolClient boundary. (local)
- [完成] [eval] [test] 验证 Query/Action 注册、Action pending/terminal 生命周期及 Verifier 缺失或 unknown 结果的 fail-closed 行为。(local)
- [Completed] [Eval] [Test] Verify Query/Action registration, pending/terminal lifecycle, and fail-closed behavior for missing Verifier or unknown results. (local)

### 变更摘要 / Change Summary

- [完成] [env] [feat] 新增 `PersistentRuntimeBundle` 与 `build_persistent_runtime_bundle`，组合现有持久部署 provider、7 个 Tool endpoint 和 `CapabilityRuntimeTransport`；不 reset world、不直接启动 Action、不授予运动权限。(local)
- [Completed] [Env] [Feat] Added `PersistentRuntimeBundle` and `build_persistent_runtime_bundle` to compose existing persistent providers, seven Tool endpoints, and `CapabilityRuntimeTransport`; no world reset, direct Action start, or motion authority is introduced. (local)
- [完成] [eval] [test] 增加部署级 bundle 注册测试；既有 Runtime/Coordinator 测试验证 pending、terminal、unknown 和 Verifier fail-closed 语义。(local)
- [Completed] [Eval] [Test] Added deployment-level bundle registration coverage; existing Runtime/Coordinator tests verify pending, terminal, unknown, and Verifier fail-closed semantics. (local)

### 文件变更详情 / File Details

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py` L1-L28, L31-L80 [新增 / Added] Runtime Bundle 类型与组合入口 / Runtime Bundle type and composition entry point.
- `examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py` L35-L63 [新增 / Added] 单 transport、7 Tool 注册测试 / single-transport, seven-Tool registration test.
- `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md` L251-L265 [新增 / Added] Runtime Bundle 和 Verifier 边界状态 / Runtime Bundle and Verifier boundary status.

### 六维验收 / Six-dimensional Acceptance

- 架构集成 / Architecture: PASS, one deployment composition root reuses existing provider/runtime/transport boundaries.
- 失败路径 / Failure paths: PASS, generic Runtime preserves pending/terminal/unknown; Coordinator refuses finalization without terminal executions or Verifier.
- 权限安全 / Authority and safety: PASS, composition performs no reset or motion and leaves route admission to existing endpoint gates.
- 配置复现 / Configuration and reproducibility: PASS, deployment inputs and tool context provider are explicit; caller owns client/world lifetime.
- 可维护性 / Maintainability: PASS, no duplicate scheduler, task store, or execution protocol; focused bundle API is isolated.
- 可观察性 / Observability: PASS, Gateway identity and existing invocation/evidence records remain on the same transport.

### 验证 / Validation

- Focused: `11 passed` for deployment/runtime lifecycle tests.
- Root: `281 passed` with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests`.
- Changed-file Ruff and adapter `compileall`: passed. Full adapter-suite collection requires the RoboTwin/numpy environment and was not runnable in the PAOS interpreter.

## v8.2.0 (2026-09-09 18:56) - codex

### 预期修改 / Planned Changes

- [完成] [policy] [feat] 将 Agent 语义 relocation 子任务投影为现有 pick-place Tool DAG，保留实体/目的地绑定并复用 PlanGraph、Gateway 与任务协调器。(local)
- [Completed] [Policy] [Feat] Project Agent semantic relocation subtasks into the existing pick-place Tool DAG, preserving entity/destination bindings and reusing PlanGraph, Gateway, and task coordinator. (local)
- [完成] [eval] [test] 增加 blocks_ranking_rgb seed 0 的分解、可执行节点顺序、admission 及失败不 finalize 测试。(local)
- [Completed] [Eval] [Test] Add decomposition, executable-node ordering, admission, and failure-no-finalize tests for blocks_ranking_rgb seed 0. (local)

### 变更摘要 / Change Summary

- [完成] [policy] [feat] 新增 `compose_executable_pick_place_plan`，为每个 Agent relocation 生成 observe、capabilities、understand、grasp、prepare、acquire、place 节点，并以 verify 汇合；依赖按 place 终点连接，支持非拓扑输入顺序。(local)
- [Completed] [Policy] [Feat] Added `compose_executable_pick_place_plan` to generate observe, capabilities, understand, grasp, prepare, acquire, and place nodes per Agent relocation, joined by verify; dependencies connect through place terminals and accept non-topological input ordering. (local)
- [完成] [docs] [docs] 更新持久多物体状态，标记 F1 已解决并明确 F2-F7 仍未进入真实执行验收。(local)
- [Completed] [Docs] [Docs] Updated persistent multi-object status, marking F1 resolved and F2-F7 outside real-execution acceptance. (local)

### 文件变更详情 / File Details

- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py` L178-L246 [新增 / Added] 可执行 pick-place PlanGraph 投影及绑定传播 / executable pick-place PlanGraph projection and binding propagation.
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/__init__.py` L11-L12, L109-L110 [修改 / Modified] 导出新投影入口 / export new projection entry point.
- `examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py` L132-L183 [新增 / Added] 节点顺序、跨子任务依赖、绑定及无运动权限测试 / node order, cross-subtask dependency, bindings, and no-motion-authority tests.
- `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md` L241-L249 [新增 / Added] 产品顺序与 F1-F7 状态 / product order and F1-F7 status.

### 关键代码 Diff / Key Code Diff

```diff
 def compose_agent_plan(...):
     # existing one-node-per-semantic-obligation compatibility path
+def compose_executable_pick_place_plan(...):
+    # project each relocation onto the existing seven-tool DAG plus verify
+    node.capability = "scene.observe" ... "object.place"
+    node.input_bindings = {"entity_ref", "destination_ref"}
```

### 六维验收 / Six-dimensional Acceptance

- 架构集成 / Architecture: PASS, one projection reuses PlanGraph and existing Gateway/Coordinator boundaries; no second scheduler or task store.
- 失败路径 / Failure paths: PASS, invalid dependencies fail planning and existing admission rejects missing evidence; no success finalization logic was bypassed.
- 权限安全 / Authority and safety: PASS, projection is planning-only and admission reports `motion_authorized=False`; no provider or hardware call is made.
- 配置复现 / Configuration and reproducibility: PASS, task/revision and planner/policy digests remain explicit; seed-0 identifiers are test inputs, not hidden configuration.
- 可维护性 / Maintainability: PASS, existing semantic API remains compatible and the new projection is isolated with focused tests.
- 可观察性 / Observability: PASS, node IDs, obligation IDs, bindings, and graph digest remain available for downstream execution records.

### 验证 / Validation

- `PYTHONPATH=examples/forge-skills/pick-place-workflow/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py`: 6 passed.
- `PYTHONPATH=examples/forge-skills/pick-place-workflow/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests/test_full_workflow.py examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py`: 9 passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests`: 281 passed.
- Ruff on changed files, `compileall`, and `git diff --check`: passed. Full-repository Ruff still reports a pre-existing import-order issue in `PhyAgentOS/agent/experience/__init__.py`.

## v8.1.1 (2026-09-09 18:00) - codex

### 预期修改 / Planned Changes

- [完成] [env] [feat] 增加 PAOS 宿主侧标准 evolution composition root，统一装配 `EvolutionExtension`、`EvolutionCandidateLifecycleAdapter`、episode hook 与事件记录；缺少扩展或投影端口时保持现有核心行为并 fail-open。(local)
- [Completed] [Env] [Feat] Add a standard PAOS-host evolution composition root that wires `EvolutionExtension`, `EvolutionCandidateLifecycleAdapter`, the episode hook, and event recording; preserve core behavior and fail open when the extension or projection ports are unavailable. (local)
- [完成] [eval] [test] 覆盖成功装配、未安装扩展、事件转发和重复装配，并完成六维验收。(local)
- [Completed] [Eval] [Test] Cover successful composition, missing optional extension, event forwarding, and duplicate composition, followed by six-dimensional acceptance. (local)

### 变更摘要 / Change Summary

- [完成] [env] [feat] 新增标准宿主 composition root，复用现有 ExperienceStore、candidate lifecycle 与 episode hook；扩展事件持久化失败保持 fail-open。(local)
- [Completed] [Env] [Feat] Added the standard host composition root, reusing the existing ExperienceStore, candidate lifecycle, and episode hook; extension-event persistence failures remain fail-open. (local)
- [完成] [eval] [test] 增加幂等装配、可选扩展缺失、事件转发和既有 hook/adapter 回归测试。(local)
- [Completed] [Eval] [Test] Added idempotent composition, missing optional extension, event forwarding, and existing hook/adapter regression tests. (local)

### 影响文件 / Affected Files

- `PhyAgentOS/agent/experience/evolution_composition.py`
- `PhyAgentOS/agent/experience/__init__.py`
- `PhyAgentOS/agent/loop.py`
- `tests/test_evolution_composition.py`
- `extensions/evolution/README.md`
- `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md`

### 文件变更详情 / File Details

#### [新增 / Added] `PhyAgentOS/agent/experience/evolution_composition.py` L1-L114

**修改前 / Before:** No reusable PAOS host composition entry point existed; `AgentLoop` manually attached the adapter after constructing `ExperienceCoordinator`.

**修改后 / After:** `compose_evolution_extension` explicitly accepts an extension or registry/projection ports, wires the existing candidate adapter and event sink, returns no-op when the optional distribution is unavailable, and preserves the first extension on repeated calls.

#### [修改 / Modified] `PhyAgentOS/agent/loop.py` L122-L143

**修改前 / Before:** `AgentLoop` directly mutated `candidate_lifecycle` with an inline adapter block.

**修改后 / After:** `AgentLoop` constructs the coordinator once and delegates extension wiring to `compose_evolution_extension`.

#### [新增 / Added] `tests/test_evolution_composition.py` L1-L58

**新增内容 / Added:** Tests for idempotent wiring, absent optional package no-op, and host event persistence/forwarding.

### 六维验收 / Six-dimensional Acceptance

- 架构集成 / Architecture: PASS, one host seam reuses existing coordinator/store/lifecycle; no second scheduler or store.
- 失败路径 / Failure paths: PASS, missing package and construction/event persistence failures remain fail-open.
- 权限安全 / Authority and safety: PASS, composition grants no motion, verifier, planner, or promotion authority.
- 配置复现 / Configuration and reproducibility: PASS, provider and projection ports are explicit; no implicit physical semantics.
- 可维护性 / Maintainability: PASS, adapter wiring is centralized and idempotent; focused tests cover the public helper.
- 可观察性 / Observability: PASS, extension events are persisted through the existing store and optionally forwarded.

Acceptance scope is the host wiring seam. Formal Bundle, provider health, model geometry grounding, and real Agent multi-object execution remain open.

### 验证 / Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_evolution_composition.py tests/test_evolution_extension_hook.py tests/test_evolution_extension_adapter.py`: 14 passed.
- `cd extensions/evolution && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`: 68 passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests`: 281 passed.
- Ruff, `compileall`, and `git diff --check`: passed.

### Git 提交 / Git Commit

- Commit: `ea786fc` (implementation commit)
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-09-09 18:00 (Asia/Shanghai)

## v8.1.0 (2026-09-09 17:29) - codex

### 预期修改 / Planned Changes

- [完成] [docs] [docs] 对照设计哲学、规划/操作架构、开发和扩展指南复核接入方向，记录文档方向与实际交付边界。(local)
- [Completed] [docs] [docs] Review integration against philosophy, planning/manipulation architecture and extension guides, distinguishing direction from delivered functionality. (local)
- [完成] [env] [feat] 通用 Runtime 支持动态 context provider，发现及新调用使用同一就绪投影；持久 Skill 明确要求宿主提供就绪依据，异常不可默认 ready。(local)
- [Completed] [env] [feat] Add dynamic context providers shared by discovery and admission; persistent Skill composition requires host readiness evidence and rejects unavailable contexts. (local)
- [完成] [eval] [fix] 无执行证据的 place 成功不得生成 placed 完成证据；验证就绪状态变化、错误、旧静态接口兼容和六维验收。(local)
- [Completed] [eval] [fix] Prevent evidence-free place success from generating completion facts; test readiness transitions, failures, static compatibility and six-dimensional acceptance. (local)
- Files: generic capability runtime, persistent Skill composition, tests, status documentation and logs. Adapter deployment implementation unchanged.

### 文件变更详情 / File Details

- `PhyAgentOS/forge/capability_runtime/runtime.py`: L51, L116, L126, L137-L149, L164-L167, L192-L195, L205 [修改 / Modified] 动态发现/准入上下文 / Dynamic discovery/admission context.
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/persistent_runtime.py`: L42-L46, L50-L52, L139-L160 [修改 / Modified] 无证据成功归 unknown，显式宿主 context / Evidence-free success becomes unknown; explicit host context.
- `examples/forge-skills/pick-place-workflow/tests/test_dynamic_tool_context.py`: L1-L63 [新增 / Added] 动态状态、故障、取消及 HTTP 测试 / Dynamic state, faults, cancellation and HTTP tests.
- `examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py`: L75, L81, L93-L104 [修改 / Modified] 未就绪组合及成功证据测试 / Unready composition and success evidence tests.
- `docs/forge/MULTI_PICK_PLACE_DIRECTION_REVIEW_20260909.md`: L1-L57 [新增 / Added] 规范对照、问题和六维验收 / Normative review, findings and six-dimensional acceptance.
- `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md`: L198, L212-L230 [修改 / Modified] 参数迁移及功能状态 / Argument migration and feature status.
- `CHANGELOG.md`: Archive 新增 part6，最近五版本滚动 / Add part6 archive and roll latest five versions.

### 关键代码 Diff / Key Code Diff

```diff
-return self._registration(tool_id).context.copy()
+registration = self._registration(tool_id)
+context = registration.context.copy()
+if registration.context_provider is not None:
+    try:
+        current = registration.context_provider()
+        if not isinstance(current, Mapping) or not isinstance(current.get("ready"), bool):
+            raise ValueError("context provider must return explicit readiness")
+        context.update(current)
+    except Exception as exc:
+        context.update(ready=False, binding_error=f"context_provider_error:{type(exc).__name__}")
+return context
-if registration.context.get("ready") is not True:
+context = self.get_context(tool_id)
+if context.get("ready") is not True:
+    raise CapabilityRuntimeError(str(context.get("binding_error") or "ToolEndpoint is not ready"))
+missing_evidence = success and not refs
+if missing_evidence:
+    status, success = "unknown", False
+    outcome_known = False
-runtime.register_tool(_spec(PLACE_TOOL_SPEC), PersistentActionEndpoint("place", client, resolve_preparation))
+runtime.register_tool(_spec(spec), endpoint,
+                      context_provider=lambda tool_id=spec["tool_id"]: tool_context_provider(tool_id))
```

### 验证 / Validation

- Focused: 19 passed; workspace: 762 passed, 1 skipped; isolated staged tree: 760 passed, 1 skipped. Ruff passed.
- 六维验收通过本次功能范围；架构方向一致，发现的两个 Major 问题已修复。正式 Bundle、实际 provider 健康接线、模型几何绑定及 Agent 多物体仿真不在本次通过范围。
- Six dimensions pass for this feature; architecture direction aligns and both Major findings are fixed. Formal Bundle, actual provider health wiring, model geometry grounding and Agent multi-object simulation remain outside this acceptance.
- 复现命令见状态文档第 45 行开始的测试块；本轮未运行模型、仿真运动或硬件。静态 context 行为兼容；持久 factory 新增必需 tool_context_provider 参数。
- Reproduce with the status document's test command starting at line 45. No model, simulator motion or hardware run. Static contexts remain compatible; the persistent factory now requires tool_context_provider.

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`; implementation commit: `0a84e20`; validation date: 2026-09-09 (Asia/Shanghai).

# 历史记录 / Historical Records

## v8.0.0 (2026-09-09 17:14) - codex

### 预期修改 / Planned Changes

- [完成] [env] [feat] 选定路线后重建已有 manifest/review 的请求绑定，接入准备缓存；保持待审且不产生授权，修复 selector 更改 request ID 导致执行拒绝。(local)
- [Completed] [env] [feat] Finalize existing manifest/review request bindings after selection and connect preparation caching; retain pending review and no motion authority to fix selector request-ID drift. (local)
- [完成] [eval] [fix] 验证最终路线产物一致性、失败拒绝和未授权行为；记录剩余 Bundle 与真实 Agent 验收缺口。(local)
- [Completed] [eval] [fix] Verify final route artifact consistency, rejection paths and absent authority; record remaining Bundle and real Agent acceptance gaps. (local)
- Version: minor feature increment carries v7.10.0 to v8.0.0 under repository version limits.
- [完成] [env] [feat] 添加持久 hold_and_reconcile 路线 profile 和 adapter 部署组件工厂；修复 benchmark source 遗漏 JSONL ok/request_id 封装字段。(local)
- [Completed] [env] [feat] Add persistent hold_and_reconcile route profile and adapter deployment component factory; strip JSONL ok/request_id fields from benchmark scene facts. (local)

### 文件变更详情 / File Details

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_route_builder.py`: L5, L17-L19, L30, L89, L118, L126-L184 [修改 / Modified] 最终路线证据及 JSONL 封装 / Final route evidence and JSONL envelope.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_preparation.py`: L61-L62, L88-L89, L95 [修改 / Modified] 定稿及证据返回 / Finalization and evidence projection.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py`: L1-L59 [新增 / Added] 共享部署组件 / Shared deployment components.
- `examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-persistent.yaml`: L1-L56 [新增 / Added] 持久停止策略 / Persistent stop policy.
- `examples/forge-adapters/robotwin20/tests/test_persistent_route_builder.py`: L1-L15, L24, L134-L172 [修改 / Modified] 请求绑定和封装测试 / Request binding and envelope tests.
- `examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py`: L92-L113 [新增 / Added] 定稿成功/失败接线 / Finalization success and failure wiring.
- `examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py`: L1-L32 [新增 / Added] 共享缓存和策略测试 / Shared cache and policy tests.
- `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md`: L172-L210 [新增 / Added] 接线方法和未验收边界 / Wiring and unaccepted scope.

### 关键代码 Diff / Key Code Diff

```diff
-for key in ("holding_state", "owner", "acquire_invocation_id", "entity_ref"):
+for key in ("holding_state", "owner", "acquire_invocation_id", "entity_ref", "ok", "request_id"):
+    response.pop(key, None)
+finalize = getattr(self.route_builder, "finalize", None)
+review_ref = finalize(bundle, route) if callable(finalize) else None
+if review_ref is not None:
+    arguments["review_request_ref"] = review_ref
-"evidence": list(selected["evidence_refs"])
+"evidence": [*selected["evidence_refs"], *([review_ref] if review_ref else [])]
+manifest.update(request_id=route["request_id"],
+                route_request={"artifact_ref": route_ref, "sha256": route_sha},
+                route_geometry_digest=route_geometry_digest(route))
+review.update(request_id=route["request_id"], route_geometry_digest=route_geometry_digest(route),
+              route_request_sha256=route_sha, source_manifest_ref=manifest_ref,
+              source_manifest_sha256=manifest_sha)
-failure_recovery: reset_simulation
+failure_recovery: hold_and_reconcile
+return PersistentDeployment(preparation, capabilities, routes)
```

### 验证 / Validation

- Workspace before final two preparation tests: 753 passed, 1 skipped; isolated final staged tree: 753 passed, 1 skipped. Ruff passed.
- 六维：架构复用 adapter/Skill 接口；定稿失败不登记；权限仍待审；profile/超时外置；复用 manifest 格式；最终 review_ref 进入公开证据。无新 hash 机制，仅重算既有执行校验字段。
- Six dimensions: adapter/Skill interface reuse; no registration on finalization failure; pending authority; external profiles/timeouts; existing manifest format; final review_ref in public evidence. No new hashing mechanism; existing execution validation fields are recomputed.
- 本轮未运行真实模型或仿真运动；正式 Bundle 生命周期、完整 readiness、模型几何绑定及 Agent 多物体验收仍未交付。
- No real model or simulator motion run this checkpoint; formal Bundle lifecycle, complete readiness, model geometry grounding and Agent multi-object acceptance remain undelivered.

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`; implementation commit: `033ed0d`; validation date: 2026-09-09 (Asia/Shanghai).

## v7.10.0 (2026-09-09 16:58) - codex

### 预期修改 / Planned Changes

- [完成] [env] [feat] 接入当前现场路线构建器：调用既有 materializer，隔离每次构建目录，保留原始 artifact 引用，验证目标和现场绑定后提供 arm options。(local)
- [Completed] [env] [feat] Connect current-scene route building through the existing materializer with isolated build directories, preserved artifact references and scene/destination-bound arm options. (local)
- [完成] [env] [feat] 增加持久现场能力快照 provider，复用既有能力投影和 profile，供公开 Tool 与准备共享同一产物。(local)
- [Completed] [env] [feat] Add a persistent capability snapshot provider reusing existing profile projection and artifacts shared by public Tools and preparation. (local)
- [完成] [eval] [fix] 验证现场更新、目标错误、产物冲突和子进程失败；保留构建日志及实际验证范围。(local)
- [Completed] [eval] [fix] Verify scene updates, wrong destinations, artifact conflicts and subprocess failures; retain build logs and measured validation scope. (local)
- Files: adapter persistent route builder/capability provider, tests, integration documentation and logs.
- [完成] [eval] [fix] smoke runner 保存模型 provider 异常类型，避免公开通用错误掩盖超时/解析失败原因；不保存凭据或原始异常文本。(local)
- [Completed] [eval] [fix] Persist the model provider exception type in smoke evidence without credentials or raw exception messages. (local)

### 文件变更详情 / File Details

- [新增 / Added] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_route_builder.py` L1-L147: 当前现场构建和产物导入 / Current-scene building and artifact import.
- [新增 / Added] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_capabilities.py` L1-L39: 能力快照 provider / Capability snapshot provider.
- [新增 / Added] `examples/forge-adapters/robotwin20/tests/test_persistent_route_builder.py` L1-L128: 多候选及失败路径 / Multiple candidates and failure paths.
- [新增 / Added] `examples/forge-adapters/robotwin20/tests/test_persistent_capabilities.py` L1-L40: 公开 Tool 现场绑定及落盘 / Public Tool scene binding and persistence.
- [修改 / Modified] `examples/forge-adapters/robotwin20/scripts/check_persistent_runtime.py` L88-L101: 保存异常及 cause 类型 / Persist exception and cause classes.
- [修改 / Modified] `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md` L132-L170: 依赖、用法和验证范围 / Dependencies, usage and validation scope.

### 关键代码 Diff / Key Code Diff

```diff
+facts = validate_scene_facts(self.scene_source(deepcopy(dict(request))))
+if target is None or target["target_ref"] != request["destination_ref"]:
+    raise ValueError("requested destination is not grounded in current scene facts")
+subprocess.run(argv, check=True, timeout=self.timeout_s, stdout=log, stderr=subprocess.STDOUT)
+self._current(intent.scene_revision)
+options = enumerate_arm_candidates(intent, candidates, self.arm_profile)
+self._import_artifacts(output_roots)
+if destination.exists() and (destination.is_symlink() or destination.read_bytes() != data):
+    raise ValueError("materialized artifact conflicts with runtime evidence")
+snapshot = build_capability_snapshot(
+    self.profile, **request, profile_digest=self.profile_digest,
+    snapshot_ref=f"artifact://capabilities/{token}",
+)
-endpoint = SceneUnderstandingEndpoint(RoboTwinSceneUnderstandingProvider(inference))
+class DiagnosedProvider:
+    def understand(self, arguments):
+        try:
+            return provider.understand(arguments)
+        except Exception as exc:
+            result["understanding_provider_exception"] = type(exc).__name__
+            raise
+endpoint = SceneUnderstandingEndpoint(DiagnosedProvider())
```

### 验证 / Validation

- Focused: 7 passed; isolated staged tree: 749 passed, 1 skipped; workspace before the final envelope test: 750 passed, 1 skipped. Ruff passed.
- 六维 review：复用 adapter materializer/能力投影；测试失效现场、目标不符、冲突和进程失败；不生成执行授权；路径和超时可配置；保留命令、输入和日志。真实 materializer 与当次模型候选的组合尚未验证。
- Six-dimensional review: reuse adapter materialization/projection; test stale scenes, wrong targets, conflicts and process failures; no execution approval; configurable paths/timeouts; retained commands, inputs and logs. Current model candidates plus the real materializer remain unverified.
- 真实运行 `paos-persistent-v7100-understanding-20260909T1707`：同一仿真两次观测及公开 Observation 成功，理解返回 `understanding_provider_error`，运动 false。
- Real run `paos-persistent-v7100-understanding-20260909T1707`: two captures in one simulator and public Observation passed; understanding returned `understanding_provider_error`; motion false.
- r2 有界重试记录 `OpenAIResponsesInferenceError`，Observation available，motion false；尚不能断言底层超时。后续运行同时记录 cause 类型。
- The bounded r2 retry recorded `OpenAIResponsesInferenceError`, Observation available and motion false; the underlying timeout is not established. Subsequent runs also record the cause class.
- 已明确剩余项：selected-route manifest/review 定稿、持久 stop profile、正式 Bundle、模型实体几何绑定、完整 readiness 和真实 Agent 多物体任务。
- Remaining: selected-route manifest/review finalization, persistent stop profile, formal Bundle, model geometry grounding, complete readiness and real Agent multi-object tasks.

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`; implementation commit: `096d9ea`; validation date: 2026-09-09 (Asia/Shanghai).

## v7.9.0 (2026-09-09 16:37) - codex

### 预期修改 / Planned Changes

- [完成] [policy] [feat] 公开 manipulation.prepare 支持显式 intent、目标及能力快照绑定，返回现有 ArmAssignment 类型；旧候选准备调用保持兼容。(local)
- [Completed] [policy] [feat] Extend manipulation.prepare with explicit intent, destination and capability bindings and existing typed ArmAssignment results while preserving legacy candidate preparation. (local)
- [完成] [eval] [fix] 验证任务/候选/现场/能力/证据绑定不一致时拒绝，不能凭 Query 成功创建执行授权；同步 Tool schema 和测试。(local)
- [Completed] [eval] [fix] Reject task/candidate/scene/capability/evidence mismatches without turning Query success into motion authority; synchronize Tool schema and tests. (local)
- Files: generic preparation endpoint, Skill Tool contract, tests and logs.
- [完成] [env] [feat] 增加 adapter 准备编排：使用既有 CompleteRouteSelector 和 ArmAssignment 投影，写入 assignment 并登记准备路线；Query 准备与 Action 授权分开。(local)
- [Completed] [env] [feat] Compose existing route selection and assignment projection in the adapter, persist assignment and register prepared routes, keeping Query preparation separate from Action authorization. (local)

### 文件变更详情 / File Details

- [修改 / Modified] `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py`: L11, L37-L38, L202-L212, L246-L266, L323-L324, L394-L410, L507-L532, L540. 可选路线义务及 assignment 验证 / Optional route intent and assignment validation.
- [新增 / Added] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_preparation.py`: L1-L92. 现场准备编排 / Current-world preparation composition.
- [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/prepared_routes.py`: L24, L31-L32, L48-L49, L54-L61, L67-L68. 授权后绑定及重复准备 / Deferred approval and repeated preparation.
- [新增 / Added] `examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py`: L1-L111. 选择、持久化、授权、陈旧现场和失败路径 / Selection, persistence, approval, stale worlds and failure paths.
- [新增 / Added] `examples/forge-skills/pick-place-workflow/tests/test_prepare_assignment.py`: L1-L71. 公开契约和绑定测试 / Public contract and binding tests.
- [修改 / Modified] `examples/forge-skills/pick-place-workflow/contracts/manipulation.prepare.tool.yaml`: L1-L511. 从现有 ToolSpec 同步完整 schema / Full schema synchronized from existing ToolSpec.
- [修改 / Modified] `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md`: L96-L130. 接线方法、六维检查和剩余交付 / Wiring, six-dimensional review and remaining delivery.

### 关键代码 Diff / Key Code Diff

```diff
 class PreparationSnapshot:
+    assignments: tuple[dict[str, Any], ...] = field(default_factory=tuple)
+    destination_ref: str | None = None
+route_keys = {"intent", "destination_ref", "capability_snapshot_ref"}
+if route_keys & arguments.keys():
+    if not route_keys <= arguments.keys():
+        return _error("invalid_intent_binding", "route preparation requires intent, destination and capability snapshot")
+if assignment.readiness_evidence_ref not in candidate["evidence"]:
+    raise ValueError("assignment readiness evidence is missing from prepared candidate")
-approval_ref: str
+approval_ref: str | None
+if key in self._routes and approval_ref is None:
+    value["approval_ref"] = self._routes[key]["approval_ref"]
+if prepared["approval_ref"] is None:
+    raise ValueError("prepared geometry has no execution approval")
+bundle = self.route_builder.build(deepcopy(dict(request)))
+if bundle.get("destination_ref") != request["destination_ref"]:
+    raise ValueError("materialized route destination differs from request")
+selected = self.selector.select(intent, bundle["base_request"], bundle["options"])
+assignment = project_arm_assignment(intent, capability, selected)
+self.prepared_routes.register(arguments, route_request=route, approval_ref=None,
+                              destination_ref=request["destination_ref"])
```

- 中文：assignment 文件沿用读取器的后缀规则，带点节点 ID 不再丢失后缀。相同路线重试保留已绑定授权。未增加新 hash 或门禁。
- English: Assignment writes follow reader suffix rules, preserving dotted node IDs. Identical route retries preserve existing approval. No new hashes or gates were added.

### 验证 / Validation

- Workspace: 744 passed, 1 skipped; isolated staged tree: 742 passed, 1 skipped; focused preparation/cache tests: 14 passed. Ruff passed.
- 六维检查覆盖架构、失败路径、权限安全、配置复现、可维护性和可观测性；范围为接口组合，未声称物理执行成功。
- Six-dimensional review covers architecture, failure paths, authority/safety, configuration/reproducibility, maintainability and observability; this is interface composition, not physical execution evidence.
- 当前现场路线构建器、正式 Bundle、模型实体几何绑定和真实 Agent 多物体验收仍待完成。
- Current-scene route builder, formal Bundle, model entity grounding and real Agent multi-object acceptance remain outstanding.

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`; implementation commit: `60f2e9c`; validation date: 2026-09-09 (Asia/Shanghai).

## v7.8.0 (2026-09-09 16:25) - codex

### 预期修改 / Planned Changes

- [完成] [env] [feat] 将现有完整路线 evaluator 接入持久 backend，当前场景准入和产物绑定保留；禁止持物期间重建规划世界，避免覆盖已附着几何。(local)
- [Completed] [env] [feat] Connect the existing complete-route evaluator to the persistent backend with current-scene/artifact bindings; reject replanning-world queries while holding to preserve attached geometry. (local)
- [完成] [eval] [fix] 验证连续场景评估不 reset/close、旧场景拒绝、持物期间查询隔离；记录真实验证范围和未完成接线。(local)
- [Completed] [eval] [fix] Test successive scene evaluation without reset/close, stale rejection and holding-query isolation; record measured scope and remaining integration. (local)
- Files: route planner, persistent engine/provider, adapter tests, integration status and logs.

### 文件变更详情 / File Details

- `docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md`: L86-L95.
- `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py`: L74-L82.
- `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_worker.py`: L52-L52.
- `examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py`: L249-L249, L254-L254, L276-L279, L285-L287, L297-L298, L300-L307, L329-L330.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_client.py`: L62-L78.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py`: L46-L47.
- `examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py`: L42-L43.
- `examples/forge-adapters/robotwin20/tests/test_persistent_route_evaluator.py`: L1-L99.

### 代码 Diff / Code Diff

```diff
diff --git a/docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md b/docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md
index 8051a51..7f9e840 100644
--- a/docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md
+++ b/docs/forge/PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md
@@ -85,0 +86,10 @@ Focused assignment/executor/endpoint tests: 62 passed. This closes the assigned-
+
+## v7.8.0 current-scene readiness connection
+
+`RoboTwinRouteEvaluator(..., backend=...)` now evaluates the existing world without resetting or closing it. It rejects stale request/world/source-fact revisions and checks the route's geometry against the live actors before configuring the planner. The default standalone evaluator still owns its own reset/close lifecycle.
+
+The persistent worker exposes the adapter-private `route_readiness` query. `build_persistent_route_readiness(client)` sends it over the existing world connection and feeds its reply through the existing RouteReadinessClient validator. Outer JSONL request identity is preserved separately from the nested route identity. While holding or uncertain, new route preparation is rejected; observation and snapshots remain available.
+
+This is the current-world evaluator connection, not the complete `manipulation.prepare` deployment factory. Contact dynamics and stop control remain unavailable in no-motion readiness results. Public preparation/assignment generation, formal Bundle and real Agent continuous multi-object execution remain outstanding.
+
+Focused tests cover two successive scene revisions, no backend recreation, stale rejection, held-object exclusion, unchanged readiness evidence limits and JSONL identity. No new real model or simulator-motion experiment was performed in this checkpoint.
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py b/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
index 8a8cb5f..132cb22 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py
@@ -73,0 +74,9 @@ class RoboTwinPersistentEngine:
+        if operation == "route_readiness":
+            from robotwin_route_planner import RoboTwinRouteEvaluator
+            from robotwin_route_readiness_worker import _handle_factory
+
+            evaluator = RoboTwinRouteEvaluator(
+                Path(self.profile["runtime_root"]), Path(self.profile["runtime_profile"]),
+                self.root, backend=self.backend,
+            )
+            return dict(_handle_factory(self.root, "persistent-route-readiness", evaluator)(arguments))
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_worker.py b/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_worker.py
index 52a8505..af07d9e 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_worker.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_persistent_worker.py
@@ -52 +52 @@ def main() -> int:
-                emit({"request_id": request["request_id"], "ok": True, **result})
+                emit({**result, "request_id": request["request_id"], "ok": True})
diff --git a/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py b/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py
index 04e2fd4..cebd166 100644
--- a/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py
+++ b/examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py
@@ -249 +249 @@ class RoboTwinRouteEvaluator:
-    def __init__(self, runtime_root, runtime_profile, artifact_root, *, diagnose_failure=False):
+    def __init__(self, runtime_root, runtime_profile, artifact_root, *, diagnose_failure=False, backend=None):
@@ -253,0 +254 @@ class RoboTwinRouteEvaluator:
+        self.backend = backend
@@ -275 +276,4 @@ class RoboTwinRouteEvaluator:
-        if request["scene_revision"] != f"{profile['task_name']}-{profile['seed']}-1":
+        owned = self.backend is None
+        expected_scene = (f"{profile['task_name']}-{profile['seed']}-1" if owned
+                          else self.backend.snapshot()["scene_revision"])
+        if request["scene_revision"] != expected_scene:
@@ -281 +285,3 @@ class RoboTwinRouteEvaluator:
-        backend = RoboTwinSensorBackend(
+        if world["scene_revision"] != expected_scene or scene["scene_revision"] != expected_scene:
+            raise SimulationProbeError("route collision world or source facts are stale")
+        backend = self.backend if not owned else RoboTwinSensorBackend(
@@ -291 +297,2 @@ class RoboTwinRouteEvaluator:
-            backend.reset(seed=profile["seed"])
+            if owned:
+                backend.reset(seed=profile["seed"])
@@ -292,0 +300,8 @@ class RoboTwinRouteEvaluator:
+            if not owned:
+                from robotwin_simulation_probe_worker import (
+                    _validate_route_input_artifacts,
+                    _validate_runtime_route_input_binding,
+                )
+                for candidate in request["candidates"]:
+                    inputs = _validate_route_input_artifacts(self.artifact_root, request, candidate)
+                    _validate_runtime_route_input_binding(task, candidate, inputs)
@@ -314 +329,2 @@ class RoboTwinRouteEvaluator:
-            backend.close()
+            if owned:
+                backend.close()
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_client.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_client.py
index 31db745..fb8064f 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_client.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_client.py
@@ -61,0 +62,17 @@ class PersistentActionDriver:
+
+
+class PersistentRouteReadinessTransport:
+    """Use the existing readiness validator over the live world connection."""
+
+    def __init__(self, client: PersistentWorkerClient) -> None:
+        self.client = client
+
+    def request(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
+        response = self.client.query("route_readiness", payload)
+        return {**response, "request_id": payload["request_id"]}
+
+
+def build_persistent_route_readiness(client: PersistentWorkerClient):
+    from .route_readiness import RouteReadinessClient
+
+    return RouteReadinessClient(PersistentRouteReadinessTransport(client), worker_id="persistent-route-readiness")
diff --git a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py
index 04d62c8..5dfe629 100644
--- a/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py
+++ b/examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py
@@ -45,0 +46,2 @@ class PersistentManipulationProvider:
+            if operation == "route_readiness" and self._state != "empty":
+                raise ManipulationStateError("new route preparation requires an empty provider")
diff --git a/examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py b/examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py
index 977f4da..2d7d015 100644
--- a/examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py
+++ b/examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py
@@ -41,0 +42,2 @@ def test_two_objects_share_world_and_require_owned_acquire_continuation():
+            with pytest.raises(ManipulationStateError, match="empty provider"):
+                provider.query("route_readiness", {})
diff --git a/examples/forge-adapters/robotwin20/tests/test_persistent_route_evaluator.py b/examples/forge-adapters/robotwin20/tests/test_persistent_route_evaluator.py
new file mode 100644
index 0000000..a1cc01c
--- /dev/null
+++ b/examples/forge-adapters/robotwin20/tests/test_persistent_route_evaluator.py
@@ -0,0 +1,99 @@
+import hashlib
+import json
+from types import SimpleNamespace
+
+import pytest
+import robotwin_route_planner as planner
+import robotwin_simulation_probe_worker as probe
+
+
+def test_current_route_evaluation_reuses_world_and_rejects_stale_inputs(tmp_path, monkeypatch):
+    import robotwin_backend
+    backend = SimpleNamespace(_task=SimpleNamespace(block=object()), revision="scene-2")
+    backend.snapshot = lambda: {"scene_revision": backend.revision}
+    monkeypatch.setattr(robotwin_backend, "load_runtime_profile", lambda path: {"task_name": "blocks", "seed": 0})
+    monkeypatch.setattr(robotwin_backend, "RoboTwinSensorBackend", lambda *args: pytest.fail("must not create a world"))
+    checked = []
+    monkeypatch.setattr(probe, "_validate_route_input_artifacts", lambda root, request, candidate: candidate)
+    monkeypatch.setattr(probe, "_validate_runtime_route_input_binding", lambda task, candidate, inputs: checked.append(candidate["entity_ref"]))
+    monkeypatch.setattr(planner, "prepare_planning_world", lambda task, world: {"scene_revision": world["scene_revision"]})
+    monkeypatch.setattr(planner, "evaluate_route", lambda *args, **kwargs: {"status": "pass"})
+
+    def artifact(name, value):
+        data = json.dumps(value).encode()
+        path = tmp_path / "scene" / (name + ".json")
+        path.parent.mkdir(exist_ok=True)
+        path.write_bytes(data)
+        return "artifact://scene/" + name, hashlib.sha256(data).hexdigest()
+
+    evaluator = planner.RoboTwinRouteEvaluator(tmp_path, tmp_path / "profile.yaml", tmp_path, backend=backend)
+    for revision in ("scene-2", "scene-3"):
+        backend.revision = revision
+        scene_ref, scene_digest = artifact(revision + "-facts", {
+            "scene_revision": revision, "objects": [{"entity_ref": "entity://block", "actor_name": "block"}],
+        })
+        world_ref, world_digest = artifact(revision + "-world", {
+            "scene_revision": revision, "source_scene_facts_ref": scene_ref, "source_scene_facts_sha256": scene_digest,
+        })
+        request = {"scene_revision": revision, "collision_world": {"artifact_ref": world_ref, "sha256": world_digest},
+                   "candidates": [{"candidate_ref": "candidate://block/0", "entity_ref": "entity://block"}]}
+        result = evaluator(request)
+        assert result["simulator_steps"] == 0
+        assert result["motion_authorized"] is False
+        assert result["world"]["scene_revision"] == revision
+        with pytest.raises(planner.SimulationProbeError, match="scene revision"):
+            evaluator({**request, "scene_revision": "old-scene"})
+    assert checked == ["entity://block", "entity://block"]
+
+
+def test_readiness_client_validates_live_world_evidence(tmp_path):
+    from robotwin_route_readiness_worker import _handle_factory
+    from robotwin20_adapter.persistent_client import build_persistent_route_readiness
+    from test_route_readiness import _request
+
+    request = _request(tmp_path)
+    handle = _handle_factory(tmp_path, "persistent-route-readiness", lambda request: {
+        "candidates": {c["candidate_ref"]: {"status": "pass"} for c in request["candidates"]},
+        "world": {}, "simulator_steps": 0,
+    })
+
+    class Client:
+        def query(self, operation, arguments):
+            assert operation == "route_readiness"
+            return {**handle(arguments), "request_id": "transport-id"}
+
+    response = build_persistent_route_readiness(Client()).evaluate(request)
+    assert response["request_id"] == request["request_id"]
+    assert response["provider_available"] is True
+    assert response["status"] == "fail"
+    assert response["route_evidence"][0]["checks"]["complete_transport_descent_retreat"] == "pass"
+    assert response["route_evidence"][0]["checks"]["contact_dynamics"] == "unavailable"
+
+
+def test_worker_preserves_transport_identity_for_nested_query(monkeypatch, tmp_path):
+    import io
+    import sys
+    import robotwin_persistent_worker as worker
+
+    profile = tmp_path / "profile.json"
+    profile.write_text("{}")
+    closed = []
+
+    class Provider:
+        def __init__(self, factory):
+            pass
+
+        def query(self, operation, arguments):
+            return {"request_id": "route-id", "status": "fail"}
+
+        def close(self):
+            closed.append(True)
+
+    output = io.StringIO()
+    monkeypatch.setattr(worker, "PersistentManipulationProvider", Provider)
+    monkeypatch.setattr(sys, "argv", ["worker", "--profile", str(profile)])
+    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"command": "query", "operation": "route_readiness", "request_id": "transport-id"}) + "\n"))
+    monkeypatch.setattr(sys, "stdout", output)
+    assert worker.main() == 0
+    assert json.loads(output.getvalue().splitlines()[1])["request_id"] == "transport-id"
+    assert closed
```

### 验证 / Validation

- Focused: 11 passed; workspace: 731 passed, 1 skipped; isolated staged tree: 729 passed, 1 skipped. Ruff and diff checks passed.
- 测试中两个现场连续评估且不 reset/close，旧现场拒绝；本轮未运行真实模型或仿真运动。完整准备、Bundle 和 Agent 连续多物体验收仍待完成。
- Tests evaluate two successive scenes without reset/close and reject stale input. No new real-model or simulator-motion run; full preparation, Bundle and continuous Agent multi-object acceptance remain outstanding.

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`; implementation commit: `182e345`; validation: 2026-09-09 (Asia/Shanghai).

## 既有历史记录 / Earlier Records

## v7.5.5 (2026-09-09 14:34) - codex

### 预期修改 / Planned Changes

- [完成] [docs] [docs] 保存上一轮模块接入诊断，分析单次抓放子任务如何组成多次抓放，并依据 PAOS 架构和开发者指南审核接入方案，记录问题、修正方案和后续验收条件。(local)
- [Completed] [docs] [docs] Preserve the previous integration diagnosis, analyze composition of repeated pick/place subtasks, and audit the proposal against PAOS architecture and developer guidance with findings, corrections and future acceptance criteria. (local)
- 影响 / Files: `docs/forge/TASK_UNDERSTANDING_MULTI_PICK_PLACE_INTEGRATION_REVIEW_20260909.md`, this monthly log, CHANGELOG.md.
- 范围 / Scope: documentation and source analysis only; no execution-code changes, simulator, hardware, model inference or Gateway calls. Existing unrelated edits are preserved.

### 审核结果 / Review Results

- [docs] [docs] 原职责划分通过；执行完整性未通过。记录 F1-F5 五项阻断问题（节点粒度、目标绑定、连续现场、真实 Action 生命周期、场景/证据更新）及 F6-F7 两项 Major（动态目标/验证、部署/恢复结算）。(local)
- [docs] [docs] Ownership direction passes; execution completeness does not. Record five blockers (node granularity, target binding, continuous world, real Action lifecycle, scene/evidence updates) and two major findings (dynamic targets/verification, deployment/recovery settlement). (local)
- [docs] [docs] 修订为一个 AgentTask 内的多个搬运义务，每个义务展开已有能力节点组，逐次观测与验证，再最终结算；失败经现有 revision/反证/对账恢复，保留历史。(local)
- [docs] [docs] Revise the proposal to multiple relocation obligations within one AgentTask, expanded into existing capability nodes with per-object observation/verification and final settlement; preserve history through existing revision, counterevidence and reconciliation paths. (local)
- [docs] [docs] 本轮只修订方案，不修复源码问题，不运行测试或仿真。文档中的 64 passed/1 failed 为上一轮检查结果；v7.5.4 是先前实测证据。(local)
- [docs] [docs] This turn revises the design only: no source fixes, tests or simulation. The documented 64 passed/1 failed belongs to the prior inspection; v7.5.4 is prior measured evidence. (local)

### 文件变更详情 / File Details

- [新增 / Added] `docs/forge/TASK_UNDERSTANDING_MULTI_PICK_PLACE_INTEGRATION_REVIEW_20260909.md` L1-L200：L7-L42 保存证据和原诊断，L44-L127 架构依据及七项审查，L129-L194 多次组合、恢复与实施验收，L196-L200 结论 / evidence and prior diagnosis, architecture and seven findings, composition/recovery/acceptance, conclusion.
- [新增 / Added] `changelog/2026-09_part5.md` L138-L182：本版本双语计划与结果 / bilingual plan and results.
- [修改 / Modified] `CHANGELOG.md` L10-L54：同步完整版本记录；Earlier Records 分隔线前移至 v7.5.0 / mirror full version entry and move Earlier Records separator before v7.5.0.

### 关键文档 Diff / Key Documentation Diff

```diff
-上一轮诊断只存在对话中 / prior diagnosis only in conversation
+保存到 TASK_UNDERSTANDING_MULTI_PICK_PLACE_INTEGRATION_REVIEW_20260909.md
-按模块接线即可推广到多次抓放 / assume wiring alone extends to repeated manipulation
+一个任务，多义务，已有能力节点组，目标绑定，持续现场，逐次更新证据和验证
+One task, multiple obligations, existing capability nodes, bound targets,
+continuous runtime, refreshed evidence and per-obligation verification.
+F1-F7 remain implementation findings; no production changes this turn.
```

### 验证 / Validation

- `git diff --check` 通过；UTF-8 文本检查、5 个本地文档链接目标、7 个发现条目检查通过。
- `git diff --check`, UTF-8 text inspection, five local link targets and seven finding entries pass. No runtime/test commands executed.

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`; commit only the diagnosis and its logs.
- Diagnosis commit: `dfc51f2`; 时间 / Time: 2026-09-09 14:40 (Asia/Shanghai).

## v7.5.4 (2026-09-09 14:21) - codex

### 预期操作 / Planned Operations

- [完成] [eval] [exp] 按用户“再次运行一次仿真”执行修复后的一次独立 RoboTwin probe，沿用成功路线、场景和候选，新建绑定当前 worker 的授权与输出包；保存视频、阶段步数、到位误差及最终结果。(local)
- [Completed] [eval] [exp] Run one independent RoboTwin probe following the user's explicit rerun request, reusing the successful route, scene and candidate in a new package bound to the current worker; preserve videos, phase steps, arrival errors and outcome. (local)
- 影响 / Files: this log, CHANGELOG.md, external simulation artifacts. No hardware or Gateway invocation; preserve collision, stop and reset checks.

### 实际结果 / Results

- [eval] [exp] 单次运行 available，world_change_completed=true，reconciliation_required=false；右臂 1361 steps，相比 v7.5.2 的 1778 减少 417（23.45%）。未放宽任何参数或重复试跑。(local)
- [eval] [exp] One run returns available/completed with no reconciliation required: right arm 1361 steps versus 1778 in v7.5.2, a reduction of 417 (23.45%). No parameter relaxation or repeated attempts. (local)
- [eval] [exp] close/release 轨迹各 0 steps，夹爪各 20 steps；transport 跳过 lift 重复首点。close/transport/release 到位位置误差分别 0.003326079896 / 0.003822250210 / 0.004228611383 m，姿态误差 0.007453857039 / 0.004559152033 / 0.007200542569 rad，均直接通过，额外等待 0 steps。(local)
- [eval] [exp] Close/release each execute zero trajectory steps and 20 gripper steps; transport skips the duplicate lift endpoint. Close/transport/release arrival position errors are 0.003326079896 / 0.003822250210 / 0.004228611383 m and orientation errors 0.007453857039 / 0.004559152033 / 0.007200542569 rad; all pass with zero additional wait. (local)
- [eval] [exp] 抓取和落地接触通过；现有 attached robot/environment 检查 unexpected=0。最终位置误差 0.004567554930 m，姿态误差 0.043359644876 rad，夹爪张开，满足原有落点容差。(local)
- [eval] [exp] Grasp and support contact pass; existing attached robot/environment checks report zero unexpected contacts. Final position error 0.004567554930 m and orientation error 0.043359644876 rad satisfy original placement tolerances, with gripper open. (local)
- [eval] [exp] 双视频各 320x240、340 frames、13.60 s；ffprobe 和 observer 五帧接触表验证通过。步数差并非严格 430，因为其他规划段也有变化；单次结果不建立成功率。(local)
- [eval] [exp] Both videos are 320x240, 340 frames, 13.60 s; ffprobe and a five-frame observer contact sheet pass inspection. The reduction is not exactly 430 because other planned segment lengths also changed; one run does not establish a success rate. (local)

| Phase | Trajectory steps | Arrival steps | Gripper steps |
|---|---:|---:|---:|
| approach | 278 | 0 | 20 |
| contact | 199 | 0 | 20 |
| close | 0 | 0 | 20 |
| lift | 192 | 0 | 20 |
| transport | 77 | 0 | 20 |
| descent | 263 | 0 | 20 |
| release | 0 | 0 | 20 |
| retreat | 192 | 0 | 20 |

### 证据与复现 / Evidence and Reproduction

- Output root: `/home/yanxu/robotwin20-runtime/artifacts/paos-probe-v7.5.4-20260909T062313Z`.
- `probe/result.json`, `probe/approval.json`, `probe/run.log`, `probe/run_provenance.py`, `probe/observer-contact-sheet.png`.
- `simulation-probe/franka-green-release-gap-v751/block-green-1-0/`: trajectory, contact-dynamics, observed-outcome, stop-control, before/after snapshots, head/observer videos.
- Scene: blocks_ranking_rgb, seed 0, candidate `candidate://block-green-1/0`; original 5 mm elevated release route, current worker commit `090885e`, RoboTwin20 Python 3.10. Invocation uses `run_approved_simulation_probe.py`; exact arguments and environment are preserved in `probe/run_provenance.py`.
- 本次运行仅更新新包中 manifest 的 worker 绑定和 review 的 worker/profile/manifest 绑定，通过既有 approve 工具物化用户本轮授权；原包未覆盖。无硬件、Gateway 或 PAOS 任务结算。
- Only new-package worker/profile/manifest bindings were updated and the existing approval tool materialized this turn's user authorization; original package preserved. No hardware, Gateway or PAOS task finalization.

### 文件变更详情 / File Details

- [新增 / Added] `changelog/2026-09_part5.md` L80-L136：双语运行记录、精确结果和命令来源 / bilingual run record, measured results and command provenance.
- [修改 / Modified] `CHANGELOG.md` L10-L66：同步本版本完整记录 / mirror complete version record; move Earlier Records separator before v7.4.2 to preserve latest five.
- 外部 `probe/run_provenance.py` L1-L63 记录新包物化及执行命令，其他输出为 JSON/视频机器证据；本轮未改生产代码。
- External `probe/run_provenance.py` L1-L63 preserves package materialization and invocation; other outputs are machine JSON/video evidence. No production code changes.

```diff
-latest recorded run: v7.5.2, 1778 steps
+v7.5.4: 1361 steps, close/release trajectory_steps=0
+arrival checks: arrived; additional arrival_steps=0
+position error: 0.004567554930 m; orientation error: 0.043359644876 rad
```

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`; only this log and CHANGELOG.md are committed.
- Simulation record commit: `fd62ff4`; 时间 / Time: 2026-09-09 14:27 (Asia/Shanghai).

## v7.5.3 (2026-09-09 14:11) - codex

### 预期修改 / Planned Changes

- [完成] [policy] [fix] 修复 RoboTwin close/release 重复轨迹及 lift/transport 重复边界，夹爪保持固定轨迹终点；保留阶段和安全检查。(local)
- [Completed] [policy] [fix] Remove duplicate close/release trajectories and the lift/transport boundary motion; hold the fixed trajectory endpoint during gripper commands and preserve phase evidence and safety checks. (local)
- [完成] [eval] [fix] 增加可配置有界到位等待及回归测试；不调用硬件。(local)
- [Completed] [eval] [fix] Add configurable bounded arrival waiting and regression coverage; no hardware invocation. (local)
- 具体失败场景：移除重复规划后，跟踪滞后可能使夹爪提前动作；静态类型及普通测试无法测得运行时位置。因此在夹爪动作前及重复边界处测量姿态，有限步保持原目标，超限失败；复用现有逐步执行检查，不新增 hash、baseline 或发布门禁。
- Failure scenario: after removing replanning, tracking lag can trigger gripper action before arrival. Types and ordinary tests cannot measure runtime pose. Measure arrival before gripper-only phases and skipped boundaries, hold the existing target for bounded steps, and fail on exhaustion using existing step checks; no new hashes, baselines or release gates.

### 影响文件 / Planned Files

- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py`
- `examples/forge-adapters/robotwin20/profiles/robotwin20/simulation-probe.yaml`
- `examples/forge-adapters/robotwin20/tests/test_simulation_probe.py`
- `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md`
- `CHANGELOG.md`, `changelog/2026-09_part5.md`

### 完成结果 / Results

- [eval] [fix] 八阶段保留，close/release 的机械臂轨迹为零；transport 仅去除与 lift 完整姿态相同的首点。夹爪保持最后已验证关节目标。(local)
- [eval] [fix] Preserve eight phases, execute zero arm trajectory in close/release, skip only a transport start matching the full lift endpoint, and hold the last validated joint target. (local)
- [eval] [test] 专项 54 passed；当前工作区适配器 384 passed, 1 skipped；独立提交导出 382 passed, 1 skipped（两项差异来自其他未提交测试）；Ruff、compileall 和 diff check 通过。测试使用 fake planner/scene IO；未运行新 SAPIEN 仿真或硬件。(local)
- [eval] [test] Focused: 54 passed; workspace: 384 passed, 1 skipped; isolated commit export: 382 passed, 1 skipped (two additional unstaged tests in workspace); Ruff, compileall and diff check pass. Tests use fake planner/scene IO; no new SAPIEN or hardware run. (local)
- 到位默认 0.005 m / 0.05 rad / 125 steps 为可配置初始值，尚未通过新动态试验测量；v7.5.2 的成功不代表此版本动态验证。
- Arrival defaults of 0.005 m / 0.05 rad / 125 steps are configurable initial values, pending dynamic measurement; v7.5.2 success does not validate this executor.

### 文件变更详情 / File Details

- [修改 / Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py` L25, L100-L167, L1060-L1062, L1082, L1095, L1144-L1145, L1155-L1180, L1218-L1219, L1256-L1259, L1262, L1401, L1628, L1744, L1913-L1915, L1917-L1919, L1961：阶段分流、完整姿态去重、固定保持、到位检查、失败记录及 CLI 参数 / phase dispatch, full-pose deduplication, fixed holds, bounded arrival, failure evidence and CLI.
- [修改 / Modified] `examples/forge-adapters/robotwin20/tests/test_simulation_probe.py` L917, L968, L987, L1593-L1763：固定保持及真实执行循环 fake IO 回归 / fixed holds and production execution-loop fake IO regressions.
- [修改 / Modified] `examples/forge-adapters/robotwin20/profiles/robotwin20/simulation-probe.yaml` L41-L46：显式到位参数 / explicit arrival parameters.
- [新增 / Added] `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md` L228-L263：执行语义、配置及未实测边界 / execution semantics, configuration and dynamic validation limits.
- [新增 / Added] `changelog/2026-09_part5.md` L1-L78：本版本完整双语归档 / complete bilingual version archive.
- [修改 / Modified] `CHANGELOG.md` L5, L10-L85, L600-L601：新增 Part 5 链接，保留当前最新五版本完整记录并分隔已有历史记录 / add Part 5 link, retain complete latest five records and separate existing history.

### 关键代码 Diff / Key Code Diff

```diff
-entity = task.robot.left_entity if arm == "left" else task.robot.right_entity
-current_position = [float(item) for item in entity.get_qpos()[:7]]
-controller.command(current_position, [0.0] * len(current_position))
+hold_position = execution_state["_arm_hold_targets"][arm]
+controller.command(hold_position, [0.0] * len(hold_position))
```

```diff
+execution_state.setdefault("_arm_hold_targets", {})[arm] = np.asarray(
+    positions[-1], dtype=np.float64
+).tolist()
-for route_waypoint, waypoint in zip(phase["waypoints"], world_waypoints):
+for index, (route_waypoint, waypoint) in enumerate(zip(phase["waypoints"], world_waypoints)):
+    if gripper_only or duplicate_boundary:
+        arrival_checks.append(_wait_for_arrival(...))
+        skipped_waypoints.append(...)
+        continue
     result = fn(waypoint)
```

- 上述循环 Diff 为关键片段；完整代码对 close/release 只执行一次到位检查，并校验它们与前一移动阶段一致。
- The loop diff is abbreviated; full code checks arrival once for each gripper-only phase and validates the preceding motion endpoint.

### 验证命令 / Validation

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
/home/yanxu/miniconda3/envs/paos/bin/ruff check examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py examples/forge-adapters/robotwin20/tests/test_simulation_probe.py
git diff --check
```

### Git 提交 / Git Commit

- Branch: `feature/planning-loop`.
- 仅提交本次文件；已有其他未提交修改保留 / commit only this task's files and preserve existing unrelated edits.
- Implementation commit: `090885e`; 时间 / Time: 2026-09-09 14:20 (Asia/Shanghai).

## v7.5.2 (2026-09-09 13:51) - codex

### 实测追加修复 / Measured Follow-Up

- 首轮 1776 steps 完成释放与退让动作后，接触判定失败；记录出现同一 link 自身接触及静止方块随机被标成机器人 link。`_contact_state` 只保存临时 Python wrapper 的 id，wrapper 被回收后 id 可复用。改为保存 wrapper 强引用与名称，避免误归因，保留所有碰撞判定并补回归后用新包重跑。
- First run reached 1776 steps and completed release/retreat motion, but contact evaluation failed. Trace identities included self-identical links and stationary blocks misidentified as robot links. Retain strong wrapper references with names in `_contact_state` to prevent Python id reuse; keep collision policy, add regression and rerun a new package.
- Files: `runtime/robotwin_simulation_probe_worker.py`, `tests/test_simulation_probe.py` under the RoboTwin adapter.

### 预期操作 / Planned Operations

- [完成] [eval] [exp] 根据用户在 5 mm 上方释放完整无动作路线通过后的“jixu”指令，执行该具体路线的独立 simulation-only probe；物化新 approval，保存 head/observer 视频、接触、停止、reset 和落点结果，不使用硬件或 Gateway。(local)
- [Completed] [eval] [exp] Following the user's continuation after the concrete 5 mm elevated-release route passed no-motion planning, run its independent simulation-only probe with a new approval; preserve head/observer video, contacts, stop/reset and placement evidence. No hardware or Gateway. (local)
- 影响 / Files: this monthly log, CHANGELOG.md, external `paos-release-gap-v7.5.1-20260909T053746Z/probe/` and `simulation-probe/` artifacts. Existing route and collision policy unchanged.

### 结果 / Results

- [eval] [exp] 新包 `/home/yanxu/robotwin20-runtime/artifacts/paos-probe-v7.5.2-20260909T055546Z`：status=available，world_change_completed=true，reconciliation_required=false；右臂 1778 steps，抓取及落地支撑接触通过，既有 attached robot/environment 判定下 unexpected=0。(local)
- [eval] [exp] Corrected package returns available/completed with no reconciliation needed: right arm 1778 steps, observed grasp and support contact, zero unexpected contacts under the existing attached robot/environment checks. (local)
- [eval] [exp] 最终位置误差 0.006262958274 m，姿态误差 0.013672666572 rad，夹爪张开；满足当前 0.04 m / 0.35 rad 容差。head/observer 视频各 444 帧、320x240、17.76 s。仅独立仿真，不授予硬件权限、不创建 Gateway invocation 或 PAOS 任务成功。(local)
- [eval] [exp] Position error 0.006262958274 m and orientation error 0.013672666572 rad meet configured tolerances; gripper open. Both videos contain 444 frames at 320x240, 17.76 seconds. Independent simulation only; no hardware authority, Gateway invocation or PAOS task finalization. (local)
- [eval] [test] 专项 38 passed；工作区 368 passed, 1 skipped；独立暂存内容 366 passed, 1 skipped；Ruff、compileall、diff check、视频元数据及抽帧验证通过。(local)
- [eval] [test] Focused 38 pass; working tree 368 pass/1 skip; isolated staged content 366 pass/1 skip. Ruff, compileall, diff check, video metadata and frame extraction pass. (local)

### 文件详情 / File Details

- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py` L449-L479：保存强引用 / retain strong references.
- `examples/forge-adapters/robotwin20/tests/test_simulation_probe.py` L1514-L1543：临时 wrapper 生命周期及真实碰撞标记回归 / transient-wrapper lifetime and real contact regression.
- `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md` L206-L227：独立仿真范围与结果 / independent simulation scope and result.

```diff
-link_identity[id(link)] = qualified
+link_identity[id(link)] = (link, qualified)
-qualified = link_identity.get(id(candidate))
+binding = link_identity.get(id(candidate))
+if binding is not None and binding[0] is candidate:
+    return binding[1]
```

### 验证命令 / Validation

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
```

### Git 提交 / Git Commit

- Commit: `e5e65f8`; Branch: `feature/planning-loop`; 时间 / Time: 2026-09-09 13:59 (Asia/Shanghai).

## v7.5.1 (2026-09-09 13:29) - codex

### 用户确认的范围更新 / User-Authorized Scope Update

- [完成] [policy] [feat] 用户允许在目标上方释放，新增显式 5 mm release_clearance_m；最终落点目标不变，释放 TCP 按支撑法向抬高，保留附着/桌面/双臂碰撞检查并重新无动作验证完整路线。(local)
- [Completed] [policy] [feat] User authorized releasing above the destination. Add explicit 5 mm release_clearance_m, keep the final placement goal, offset release TCP along the support normal, retain attached/table/dual-arm collision checks and rerun full no-motion qualification. (local)
- Additional files: route_generation.py, route_readiness.py, route-inputs.yaml, route generation/readiness tests.
- 实测追加修复 / Measured follow-up fix: 5 mm 路线已通过下降和释放，但退让因 OBB cache 无 released-object slot 被拒绝；在原有 world 安装时为已实现的释放物体障碍预留一个槽位，不删除任何碰撞对象。Reserve one OBB slot during world setup for the existing released-object obstacle after the measured retreat cache-capacity failure.

### 预期修改 / Planned Changes

- [完成] [eval] [fix] 在独立 provider 无动作诊断中对比失败下降段的 attached/robot-only 结果，记录目标物体及机械臂 sphere 的桌面距离；保持生产碰撞检查和原始路线不变。(local)
- [Completed] [eval] [fix] Compare attached and robot-only planning for the rejected descent in an isolated provider diagnostic and measure object/robot sphere table distances; preserve production collision checks and the original route. (local)
- [完成] [docs] [docs] 根据实际证据记录根因及后续修复边界，补充测试、行号、Diff 和提交信息；无 scene.step、Gateway 或硬件操作。(local)
- [Completed] [docs] [docs] Record the measured cause and repair boundary with tests, line ranges, diffs and commits; no scene stepping, Gateway or hardware operation. (local)

### 影响文件 / Planned Files

- RoboTwin runtime diagnostic module, route evaluator diagnostic hook, focused tests, contact postprocessing documentation, monthly log and index.

### 实际结果 / Results

- [eval] [fix] 已定位 attached sphere/table 约 -1.0000615 mm 重叠；robot-only 对照成功但不参与准入。用户允许目标上方释放后，显式 5 mm 间隙通过最终下降；预留 released-object OBB 槽位后右臂完整八阶段、10 waypoint segment 全部通过。(local)
- [eval] [fix] Diagnosed about -1.0000615 mm attached sphere/table overlap; robot-only success remains diagnostic. User-authorized 5 mm elevated release clears final descent; reserving the released-object OBB slot completes all eight right-arm phases and 10 segments. (local)
- [eval] [test] 工作区 367 passed, 1 skipped；独立暂存内容 365 passed, 1 skipped；Ruff、compileall 和 diff check 通过。未提交草稿造成两项差异。(local)
- [eval] [test] Working tree 367 passed, 1 skipped; isolated staged tree 365 passed, 1 skipped; Ruff, compileall and diff check pass. Two extra tests belong to unstaged drafts. (local)
- Evidence: `/home/yanxu/robotwin20-runtime/artifacts/paos-release-gap-v7.5.1-20260909T053746Z/no-motion-route-cache-fixed.json`; left fails approach, right complete-route pass, simulator_steps=0, motion_authorized=false. Landing dynamics and final accuracy remain unmeasured.
- 桌面、红蓝方块和 peer-arm projection 保留；抓取 16 mm backoff 不变；最终物体目标不变；只抬高释放 TCP，退让障碍覆盖释放至落地的包络。
- Table, red/blue blocks and peer projection remain; 16 mm grasp backoff and final object goal are unchanged. Only release TCP is elevated; retreat includes the release-to-settled object envelope.

### 文件详情 / File Details

- `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md` L154-L205 [修改 / Added or modified]

```diff
+
+## Final descent diagnosis (v7.5.1)
+
+The one-shot route worker accepts `--diagnose-failure` with `--request` and
```

- `examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs.yaml` L36-L36 [修改 / Added or modified]

```diff
+  release_clearance_m: 0.005
```

- `examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py` L379-L380 [修改 / Added or modified]

```diff
-        required_capacity = len(world.cuboid)
+        # Retreat replaces the attachment with one released-object obstacle.
+        required_capacity = len(world.cuboid) + 1
```

- `examples/forge-adapters/robotwin20/runtime/robotwin_descent_diagnostic.py` L1-L101 [修改 / Added or modified]

```diff
+"""Explicit no-motion ablation of a rejected attached segment.
+
+The robot-only result is diagnostic evidence and can never replace the
+production attached-route result. The full table/blocks/peer world stays loaded.
```

- `examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py` L5-L5, L96-L113, L115-L121, L146-L146, L149-L150, L187-L194, L201-L201, L218-L223, L226-L234, L249-L249, L253-L253, L303-L303 [修改 / Added or modified]

```diff
+from copy import deepcopy
+def released_object_envelope(candidate):
+    """Conservative box covering release-to-settled translation for retreat."""
+    import numpy as np
```

- `examples/forge-adapters/robotwin20/runtime/robotwin_route_readiness_worker.py` L117-L117, L124-L126 [修改 / Added or modified]

```diff
+    parser.add_argument("--diagnose-failure", action="store_true")
-        evaluator = RoboTwinRouteEvaluator(args.runtime_root.resolve(), args.runtime_profile.resolve(), args.artifact_root.resolve())
+        evaluator = RoboTwinRouteEvaluator(args.runtime_root.resolve(), args.runtime_profile.resolve(), args.artifact_root.resolve(), diagnose_failure=args.diagnose_failure)
+    if args.diagnose_failure and not (args.request and args.output):
```

- `examples/forge-adapters/robotwin20/scripts/materialize_complete_route.py` L181-L181 [修改 / Added or modified]

```diff
-    if not isinstance(route_policy, Mapping) or set(route_policy) != {
+    if not isinstance(route_policy, Mapping) or set(route_policy) - {"release_clearance_m"} != {
```

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_generation.py` L173-L173, L182-L186, L307-L308, L349-L349 [修改 / Added or modified]

```diff
-    if not isinstance(value, Mapping) or set(value) != required:
+    if not isinstance(value, Mapping) or set(value) - {"release_clearance_m"} != required:
+    if "release_clearance_m" in value:
+        clearance = _finite(value["release_clearance_m"], "release_clearance_m")
```

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_readiness.py` L359-L359, L372-L378 [修改 / Added or modified]

```diff
-        if not isinstance(placement, Mapping) or set(placement) != {
+        if not isinstance(placement, Mapping) or set(placement) - {"release_clearance_m"} != {
-        if not _pose_matches_matrix(release_pose, _multiply(_pose_matrix(target_pose), transform)):
+        release_clearance = placement.get("release_clearance_m", 0.0)
```

- `examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py` L200-L200, L203-L206 [修改 / Added or modified]

```diff
-    assert all(item[1:] == (3, 3) for item in rebuilt)
+    assert all(item[1:] == (3, 4) for item in rebuilt)
-        assert planner.motion_gen.collision_cache["obb"] == 3
+        assert planner.motion_gen.collision_cache["obb"] == 4
```

- `examples/forge-adapters/robotwin20/tests/test_descent_diagnostic.py` L1-L53 [修改 / Added or modified]

```diff
+from types import SimpleNamespace
+
+import numpy as np
+import pytest
```

- `examples/forge-adapters/robotwin20/tests/test_route_generation.py` L62-L87 [修改 / Added or modified]

```diff
+def test_release_clearance_preserves_final_goal_and_grasp():
+    inputs = _inputs()
+    nominal = generate_route_request(*inputs)
+    inputs[-1]["release_clearance_m"] = .005
```

- `examples/forge-adapters/robotwin20/tests/test_route_planner.py` L121-L152 [修改 / Added or modified]

```diff
+
+
+def test_diagnostic_success_never_promotes_rejected_route(route, monkeypatch):
+    task, request, candidate, entity, events, starts = route
```

### 验证 / Validation

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
```

### Git 提交 / Git Commit

- Commit: `376c097`; Branch: `feature/planning-loop`; 时间 / Time: 2026-09-09 13:42 (Asia/Shanghai).

## v7.5.0 (2026-09-09 12:43) - codex

### 预期修改 / Planned Changes

- [完成] [policy] [feat] 按开发者手册第 12/13 节和 manipulation ownership matrix，将完整碰撞世界、无动作路线评估与抓取资格评估接入现有 RoboTwin adapter/runtime；Core、Skill、Gateway 生命周期保持原有所有权。(local)
- [Completed] [policy] [feat] Integrate complete collision-world preparation, no-motion route evaluation and grasp qualification in the existing RoboTwin adapter/runtime following developer manual sections 12/13 and the manipulation ownership matrix. Preserve Core, Skill and Gateway lifecycle ownership. (local)
- [完成] [model] [fix] 修正旋转物体的包含判定，补充指间几何约束和有限 backoff 候选的实际 Curobo 评估；保留原始 GraspGen depth、实测桌面、方块、peer-arm 投影。(local)
- [Completed] [model] [fix] Correct rotated-object containment and add finger geometry constraints and actual Curobo evaluation of finite backoffs; retain original GraspGen depth, measured table, blocks and peer-arm projection. (local)
- [完成] [eval] [test] 增加失败路径回归并运行独立 no-motion 测量；记录每个候选/机械臂/阶段的结果，不将几何可行性当作动态接触、任务成功或运动授权。(local)
- [Completed] [eval] [test] Add failure regressions and independent no-motion measurements with candidate/arm/phase results. Geometry feasibility does not establish contact dynamics, task success or motion authority. (local)

### 架构审核 / Architecture Review

- `docs/zh/03-developer-manual.md` L197-L229、`docs/user_development_guide/README.md` L24-L47、`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md` L8-L18：通过上述 ownership 修正后实施。仿真内部物体几何仅作仿真资格对照。
- Approved within those documented ownership boundaries; simulator object geometry remains simulation qualification reference data.
- 具体失败：mesh-only qualified 会选中 planner 拒绝的抓取；原始姿态检查与实际执行目标不一致；只测 contact 不能判断完整 attached route。现有 route-readiness 边界足以承载修复，不新增 hash、gate、状态库或执行协议。
- Concrete failures: mesh-only qualification selects planner-rejected grasps; raw-pose checks differ from execution targets; contact-only checks do not establish attached-route feasibility. Reuse existing route-readiness checks without new hashes, gates, stores or execution protocols.

### 预期影响文件 / Planned Files

- `examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py`
- `examples/forge-adapters/robotwin20/runtime/robotwin_route_readiness_worker.py`
- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py`
- `examples/forge-adapters/robotwin20/runtime/robotwin_grasp_contact_geometry_worker.py`
- RoboTwin provider shared geometry/planning helpers, qualification CLI, grasp postprocessing, profiles and focused tests.
- `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md`, `CHANGELOG.md`, this monthly archive.
### 实际修改与验证 / Changes and Validation

- [完成] [policy] [feat] 完成 provider-owned 完整世界与路线评估；原始 GraspGen depth 和 Core/Skill/Gateway 权限不变。(local)
- [Completed] [policy] [feat] Implemented provider-owned complete-world and route evaluation; original GraspGen depth and Core/Skill/Gateway authority are unchanged. (local)
- [完成] [eval] [test] 工作区 356 passed, 1 skipped；独立暂存内容 354 passed, 1 skipped；Ruff、compileall、git diff --check 通过。差异来自未纳入提交的现有草稿测试。
- [Completed] [eval] [test] Working tree: 356 passed, 1 skipped; isolated staged content: 354 passed, 1 skipped. Ruff, compileall and diff check pass. Existing unstaged draft tests explain the count difference.
- [完成] [eval] [exp] 右臂 16/16.25/16.45 mm 接触资格通过，sphere 净空 0.050918/0.300401/0.500095 mm；左臂八个候选全部失败。16 mm 完整路线复测：left approach waypoint 0 失败；right descent waypoint 1 失败；simulator_steps=0，motion_authorized=false。
- [Completed] [eval] [exp] Right 16/16.25/16.45 mm contact variants qualify with the listed sphere clearances; all eight left variants fail. Full 16 mm route repeat rejects left approach waypoint 0 and right descent waypoint 1, with zero steps and no motion authorization.
- Evidence: `/home/yanxu/robotwin20-runtime/artifacts/paos-contact-v7.5.0-20260909T1305Z/`; final package `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v7.5.0-16mm-20260909T0508Z/`. Earlier directory timestamp labels were manually chosen; they are output identifiers, not measured capture timestamps. Scene seed 0, original saved GraspGen proposal, RoboTwin20 Python 3.10, Torch 2.9.1+cu128. Curobo randomness remains.

### 文件变更详情 / File Changes

#### [修改 / Added or Modified] `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md` L18-L20, L43-L47, L80-L153

关键 Diff / Key Diff:

```diff
-keeps the contact center inside the object. It never calls Curobo/SAPIEN,
+keeps the contact center inside the oriented object. Live qualification also
+requires a conservative Panda finger-envelope fit and Curobo contact evidence.
+The pure module never calls Curobo/SAPIEN,
-- Pinch validity is checked against the measured object center and half extents.
+- Contact containment uses the inverse object rotation and measured half extents.
+  Live qualification checks that the object fits the open-finger aperture, the
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs.yaml` L25-L25

关键 Diff / Key Diff:

```diff
-  contact_backoff_candidates_m: [0.0, 0.005, 0.010, 0.015, 0.020]
+  contact_backoff_candidates_m: [0.0, 0.005, 0.010, 0.015, 0.016, 0.01625, 0.01645, 0.020]
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/profiles/robotwin20/route-readiness-live.yaml` L1-L22

关键 Diff / Key Diff:

```diff
+schema_version: paos-robotwin20-route-readiness/v1
+worker_id: robotwin20-route-readiness/v1
+artifact_root: ${ROBOTWIN20_SIMULATION_ARTIFACT_ROOT}
+worker:
+  python: ${ROBOTWIN20_ROUTE_WORKER_PYTHON}
+  script: ${PAOS_ROBOTWIN20_ADAPTER_ROOT}/runtime/robotwin_route_readiness_worker.py
+  cwd: ${ROBOTWIN20_RUNTIME_ROOT}
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py` L5-L5, L12-L13, L23-L106, L315-L334

关键 Diff / Key Diff:

```diff
+import math
+    DualArmStateError,
+    build_peer_arm_sphere_projection,
+def bind_scene_table(task: Any) -> None:
+    """Bind the measured support box to both provider planners without stepping."""
+    table = getattr(task, "table", None)
+    table_pose = table.get_pose() if table is not None and callable(getattr(table, "get_pose", None)) else None
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_grasp_contact_geometry_worker.py` L12-L12, L38-L38, L43-L78

关键 Diff / Key Diff:

```diff
-from robotwin_simulation_probe_worker import _collision_vertices, _table_top_z
+from robotwin_planning_geometry import _collision_vertices, _table_top_z
-        arms: dict[str, Any] = {}
-        for arm, attribute in (("left", "left_entity"), ("right", "right_entity")):
-            entity = getattr(task.robot, attribute, None)
-            if entity is None:
-                raise GraspContactGeometryError(f"{arm} robot entity is unavailable")
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_planning_geometry.py` L1-L361

关键 Diff / Key Diff:

```diff
+"""Shared RoboTwin planner geometry checks; no controller or scene stepping."""
+
+from __future__ import annotations
+
+import math
+from typing import Any, Mapping
+
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py` L1-L265

关键 Diff / Key Diff:

```diff
+"""Provider-owned no-motion evaluation of execution grasps and full routes."""
+
+from __future__ import annotations
+
+from typing import Any, Mapping
+
+from robotwin_curobo_world_port import (
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_route_readiness_worker.py` L3-L5, L14-L15, L36-L36, L49-L56, L61-L65, L69-L69, L72-L79, L91-L91, L95-L95, L97-L97, L100-L100, 删除旧 L80-L80, L113-L116, L118-L136

关键 Diff / Key Diff:

```diff
-The worker validates the complete route/evidence contract and records an
-explicit unavailable result until a real planner, attached-object collision
-checker, contact probe, stop controller, and semantic verifier are injected.
+The worker records planner and attached-object geometry evidence when a
+RoboTwin evaluator is configured. Contact dynamics and stop control remain
+unavailable here; user-level verification belongs to the PAOS Verifier.
+import sys
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py` L34-L64, 删除旧 L48-L49, 删除旧 L71-L72, 删除旧 L285-L321, 删除旧 L325-L345, L315-L317, 删除旧 L496-L513, 删除旧 L667-L684, 删除旧 L687-L691, 删除旧 L693-L713, 删除旧 L715-L723, 删除旧 L726-L728, 删除旧 L730-L761, 删除旧 L764-L778, 删除旧 L781-L784, 删除旧 L786-L790, L606-L606, 删除旧 L1087-L1096, 删除旧 L1162-L1206, L1056-L1061, L1098-L1107, L1135-L1135, L1140-L1144, L1659-L1659, 删除旧 L1980-L1981

关键 Diff / Key Diff:

```diff
-from robotwin_curobo_world_port import CuroboWorldPortError, apply_collision_world
+from robotwin_curobo_world_port import (
+    CuroboWorldPortError,
+    add_released_object,
+    apply_collision_world,
+    bind_scene_table,
+    capture_peer_projection,
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/scripts/qualify_grasp_contact.py` L9-L9, L17-L17, L39-L45, L90-L90, L105-L105, L108-L146, L152-L152, L156-L170, L178-L178, L184-L184, L186-L188, L190-L192, L197-L225, L234-L243, L246-L247, L258-L263

关键 Diff / Key Diff:

```diff
+from copy import deepcopy
+    _rotation_quaternion,
-def _candidate(value: Mapping[str, Any]) -> Mapping[str, Any]:
+def _candidate(value: Mapping[str, Any], candidate_ref: str | None = None) -> Mapping[str, Any]:
+    if candidate_ref is not None:
+        candidates = value.get("candidates", [value.get("candidate", value)])
+        candidate = next((item for item in candidates if item.get("candidate_ref") == candidate_ref), None)
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_postprocessing.py` L14-L14, L180-L211, L223-L226, L251-L251, L264-L275, L278-L278, L284-L293, L300-L308, L318-L318, L349-L351, L394-L397

关键 Diff / Key Diff:

```diff
+from itertools import product
-def _object_contains(point: Sequence[float], center: Sequence[float], half_extents: Sequence[float]) -> bool:
-    return all(abs(float(a) - float(b)) <= float(extent) + 1e-9 for a, b, extent in zip(point, center, half_extents))
+def _object_contains(point: Sequence[float], center: Sequence[float], half_extents: Sequence[float], rotation: Sequence[Sequence[float]]) -> bool:
+    local = _rotate(list(zip(*rotation)), [a - b for a, b in zip(point, center)])
+    return all(abs(value) <= extent + 1e-9 for value, extent in zip(local, half_extents))
+
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_readiness.py` L543-L547, L549-L549, L581-L584

关键 Diff / Key Diff:

```diff
-        if response.get("status") != "unavailable" or response.get("provider_available") is not False:
+        status = response.get("status")
+        if not (
+            (status == "unavailable" and response.get("provider_available") is False)
+            or (status == "fail" and response.get("provider_available") is True)
+        ):
-                "route readiness worker must remain unavailable until capabilities exist"
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py` L89-L106

关键 Diff / Key Diff:

```diff
+def test_released_target_becomes_obstacle_without_dropping_existing_world():
+    from robotwin_curobo_world_port import add_released_object
+    planner = FakePlanner()
+    previous = add_released_object(planner, {"position_m": [.1, .2, .8], "orientation_xyzw": [0, 0, 0, 1]}, [.02] * 3)
+    for model, world in previous:
+        assert [item.name for item in model.world_model.cuboid] == ["table", "released_target"]
+        assert [item.name for item in world.cuboid] == ["table"]
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/tests/test_grasp_postprocessing.py` L15-L36, L88-L132

关键 Diff / Key Diff:

```diff
+def test_rotated_object_containment_uses_object_frame():
+    from robotwin20_adapter.grasp_postprocessing import _object_contains
+    rotation = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
+    assert _object_contains([0, .08, 0], [0, 0, 0], [.1, .02, .02], rotation)
+    assert not _object_contains([.08, 0, 0], [0, 0, 0], [.1, .02, .02], rotation)
+
+
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/tests/test_qualify_grasp_contact.py` L72-L129

关键 Diff / Key Diff:

```diff
+def test_cli_rejects_mesh_only_variant_when_curobo_evidence_fails(tmp_path):
+    files = _inputs(tmp_path)
+    curobo = _write(
+        tmp_path / "curobo.json",
+        {
+            "schema_version": "paos-robotwin20-curobo-contact-qualification/v1",
+            "candidate_ref": "candidate://block-green-1/0",
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/tests/test_route_planner.py` L1-L120

关键 Diff / Key Diff:

```diff
+from copy import deepcopy
+from types import SimpleNamespace
+
+import numpy as np
+import pytest
+import robotwin_route_planner as module
+
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/tests/test_route_readiness.py` L209-L245

关键 Diff / Key Diff:

```diff
+def test_live_geometry_evidence_cannot_authorize_dynamic_readiness(tmp_path):
+    from robotwin_route_readiness_worker import _handle_factory
+
+    from robotwin20_adapter.route_readiness import RouteReadinessClient
+
+    request = _request(tmp_path)
+    def evaluate(request):
```

#### [修改 / Added or Modified] `examples/forge-adapters/robotwin20/tests/test_simulation_probe.py` L34-L34, L118-L131

关键 Diff / Key Diff:

```diff
+    _validate_support_departure_results,
+def test_support_departure_allows_only_a_leading_world_contact_prefix():
+    world_contact = SimpleNamespace(value="Start state is colliding with world")
+    _validate_support_departure_results(
+        [(False, world_contact), (False, world_contact), (True, None), (True, None)]
+    )
+
```

### 验证命令 / Validation Commands

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
```

### Git 提交 / Git Commit

- Commit: `b15d053`; Branch: `feature/planning-loop`; 时间 / Time: 2026-09-09 13:08 (Asia/Shanghai).

## v7.4.2 (2026-09-09 13:20) - codex

### 预期修改 / Planned Changes

- [计划] [policy] [fix] 在 RoboTwin provider-owned grasp/contact qualification 中增加 Curobo robot collision-sphere 与实测桌面投影的 no-motion 净空检查；保留现有 SAPIEN mesh 净空和 pinch containment 判定，不放宽 collision policy。
- [Planned] [Policy] [Fix] Add a no-motion clearance check between Curobo robot collision spheres and the measured table projection to RoboTwin provider-owned grasp/contact qualification; retain SAPIEN mesh clearance and pinch containment checks without relaxing collision policy.
- [计划] [eval] [test] 增加 sphere/table 分离、目标姿态碰撞、双臂 frame 变换和未提供 Curobo model 的回归测试；失败时返回明确 qualification reason，不进入 route materialization。
- [Planned] [Eval] [Test] Add regressions for sphere/table separation, colliding target poses, dual-arm frame transforms, and unavailable Curobo models; return an explicit qualification reason and prevent route materialization on failure.

### 预期影响文件 / Planned Files

- `changelog/2026-09_part4.md`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_postprocessing.py`
- `examples/forge-adapters/robotwin20/runtime/robotwin_grasp_contact_geometry_worker.py`
- `examples/forge-adapters/robotwin20/tests/`
- `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md`

## v7.4.1 (2026-09-09 11:30) - codex

### 预期修改 / Planned Changes

- [计划] [eval] [exp] 物化用户批准的 v7.4.0 simulation-only approval，并运行绑定该 route、candidate、source manifest 和 worker 的完整 RoboTwin 双视角 probe；保存 head-camera 与 observer-camera 视频证据。
- [Planned] [Eval] [Exp] Materialize the user-approved v7.4.0 simulation-only approval and run the complete RoboTwin dual-view probe bound to this route, candidate, source manifest, and worker; persist head-camera and observer-camera video evidence.
- [计划] [safety] [test] 仅允许 attached/lift/transport/descent/release/retreat/semantic probe；不接入 Gateway、Dora、Action 或硬件，失败时保留 failure evidence、接触记录、stop/reset 和视频结果。
- [Planned] [Safety] [Test] Permit only the attached/lift/transport/descent/release/retreat/semantic probe; do not connect Gateway, Dora, Action, or hardware, and preserve failure evidence, contact records, stop/reset, and video results on failure.

### 预期影响文件 / Planned Files

- `changelog/2026-09_part4.md`
- `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v7.4.0-graspgen-contact-backoff-20260909T1100Z/probe/approval.json`
- `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v7.4.0-graspgen-contact-backoff-20260909T1100Z/probe/`

### 实际结果 / Actual Results

- [完成] [eval] [exp] 已物化并校验用户批准的 approval artifact：`/home/yanxu/robotwin20-runtime/artifacts/paos-route-v7.4.0-graspgen-contact-backoff-20260909T1100Z/probe/approval.json`；route digest `7f9055c2090c64ee88f42e00657e3c7800173c7e5c2c53ec5bd303921083935a`、source manifest digest `8fb85da145f034a4a3283bbfa43bdd4378499d78443b15ce8d882b911b8bffeb`、worker digest `6534f093bb4fb76f747a9532646be056520ef69c91c9a61b8a096797d3e092cc` 均匹配。/ [Completed] Materialized and validated the approved approval artifact; route, source-manifest, and worker digests matched the submitted approval.
- [完成] [eval] [test] 使用外置 artifact root `/home/yanxu/robotwin20-probe-v7.4.0-graspgen-contact-backoff-20260909T1100Z-run3/` 运行独立 RoboTwin worker；worker 在 `.../RoboTwin` runtime 中成功加载 provider、初始化场景并开始碰撞世界 preflight。/ [Completed] Ran the independent RoboTwin worker with an external artifact root; the provider loaded, initialized the scene, and began collision-world preflight in the `.../RoboTwin` runtime.
- [完成] [eval] [test] probe 返回 `unavailable`，原因是 `no arm can plan candidate route`：left/right 两臂均在首段 planner route segment 失败；`simulator_steps=0`、`contact_trace=[]`、`video_evidence=null`，因此没有任何动作执行或视频帧可供人工验收。/ [Completed] The probe returned `unavailable` because no arm could plan the candidate route; both arms failed on the first planner segment, with zero simulator steps, no contacts, and no video evidence.
- [完成] [safety] [test] 失败证据已保存：`simulation-probe/.../failure.json`、`before-snapshot.json`、`after-failure-snapshot.json`；`controller_stop_status=stopped`、`simulation_reset_status=completed`、`reconciliation_required=false`。未调用 Gateway、Dora、Action 或硬件。/ [Completed] Failure evidence was persisted with stopped controller and completed simulation reset; Gateway, Dora, Action, and hardware were not used.

### 六维验收 / Six-Dimension Acceptance

1. 架构集成：通过（边界）。执行仍在独立 RoboTwin provider worker，PAOS planning、Gateway 和任务生命周期未被接管；功能结果本身未通过。/ Passed (boundary). Execution remained in the independent RoboTwin provider worker; PAOS planning, Gateway, and task lifecycle were not taken over. The functional result did not pass.
2. 失败路径：通过。启动路径、provider unavailable、双臂 planner 失败、reset 和 failure evidence 均被明确收敛；失败未被解释为成功。/ Passed. Startup, provider availability, dual-arm planner failure, reset, and failure evidence were explicitly reconciled without treating failure as success.
3. 权威与安全边界：通过。仅使用 simulation-only approval；`scene.step()` 未发生，未接入生产动作执行面。/ Passed. Only the simulation-only approval was used; no `scene.step()` occurred and no production execution plane was connected.
4. 配置与复现：通过。首次路径错误和 runtime-root 配置错误均被识别；最终 run 使用固定 route/source/worker/profile 绑定及独立输出目录。/ Passed. The initial profile-path and runtime-root configuration errors were identified; the final run used fixed route/source/worker/profile bindings and an isolated output directory.
5. 可维护性：部分通过。probe 的证据和复位行为可复现，但 planner 首段失败细节目前只在 arm-attempt 摘要中记录，尚不足以判断具体碰撞几何或 IK 原因。/ Partially passed. Probe evidence and reset behavior are reproducible, but the first-segment planner failure is only summarized at arm-attempt level and does not yet identify the exact collision or IK cause.
6. 防止过度防御编程：通过。未新增代码、哈希、baseline 或 gate；仅修正了运行时目录边界并保存现有 worker 的失败证据。/ Passed. No code, hash, baseline, or gate was added; only the runtime directory boundary was corrected for execution and existing worker failure evidence was preserved.

### 验证与 Git 状态 / Verification and Git Status

- `validate_route_request()` 与前序聚焦测试已通过（`65 passed`）；本轮独立 probe 的最终结果为 `unavailable`，不能宣称双臂 route 可执行。
- 首次执行因 profile 相对路径被拒绝，第二次因 artifact root 位于 runtime root 内被拒绝；第三次修正为外置 artifact root 与 `.../RoboTwin` runtime 后进入真实 provider preflight。
- 本轮只修改本日志；未修改实现代码。工作区包含其他已有用户改动，未对其进行提交或推送。

### Git 提交 / Git Commit

- Commit: `cd73356`；Branch: `feature/planning-loop`；已推送。/ Commit: `cd73356`; Branch: `feature/planning-loop`; pushed.

## Historical Index (Preserved)


## [v7.4.1] - 2026-09-09

Ran the approved isolated RoboTwin dual-view probe for the v7.4.0 GraspGen
route. Provider initialization and collision-world preflight completed, but
both arms failed the first route-planning segment; the result is explicitly
`unavailable` with zero simulator steps and no video frames. Failure snapshots,
reset evidence, and arm-attempt records were preserved. No Gateway, Dora,
Action, or hardware was used.

运行 v7.4.0 GraspGen 路线的已批准隔离 RoboTwin 双视角 probe。provider 初始化与
碰撞世界 preflight 完成，但左右臂均未通过首段路线规划；结果明确为
`unavailable`，仿真步数为 0 且没有视频帧。失败快照、复位证据和双臂尝试记录已保留。
未调用 Gateway、Dora、Action 或硬件。

Files: `changelog/2026-09_part4.md:L3-L38`.
Validation: focused RoboTwin tests `65 passed`; simulation probe result is
`unavailable` and is not treated as route success.

## [v7.3.11] - 2026-09-09

Completed the local self-evolution lifecycle closure: evaluator receipts and
selection requests now return through the extension boundary, a named host
reviewer promotes only evidence-current Skill candidates, and Future-use
metrics recompute only for newly complete parent/candidate pairs. Extension
tests pass `68`; full PAOS tests pass `258`. No commit or push.

完成本地自我进化生命周期闭环：评测 receipt 与 selection request 通过 extension
边界回写；具名宿主 reviewer 只晋升证据仍为当前的 Skill candidate；Future-use
指标仅在新增完整 parent/candidate pair 时重算。扩展测试 `68` 通过，PAOS 全量测试
`258` 通过。不会提交或推送。

## [v7.3.10] - 2026-09-09

Fixed duplicate Future-use comparisons by recording completion in the existing
evolution event ledger. Extension tests pass `66`; full PAOS tests pass `254`.
No commit or push.

修复 Future-use 配对完成后的重复比较，使用现有 evolution event ledger 记录完成状态。
扩展测试 `66` 通过，PAOS 全量测试 `254` 通过。不会提交或推送。

## [v7.3.4] - 2026-09-08

Added a provider-neutral `SettledOutcomeProjectionPort` that routes host
targets and evidence through `ConsequenceSettler` before EvoPhy processing.
Extension tests pass `61`; full PAOS tests pass `253`. No commit or push.

新增 provider-neutral 的 `SettledOutcomeProjectionPort`，在 EvoPhy 处理前将宿主提供的
targets 与 evidence 统一交给 `ConsequenceSettler`。扩展测试 `61` 通过，PAOS 全量测试
`253` 通过。不会提交或推送。

## [v7.3.3] - 2026-09-08

Connected the optional evolution extension to the existing PAOS candidate
lifecycle and evolution-job replay path through a host adapter. Added optional
provenance storage and fail-closed delivery handling; no commit or push.

通过宿主适配器将可选 evolution 扩展接入现有 PAOS candidate 生命周期与 evolution-job
重放路径，增加 provenance 保存和失败闭环处理；不会提交或推送。

All notable changes to PhyAgentOS are documented here. Categories follow Keep a Changelog.

## [v7.3.0] - 2026-09-08

Added RoboTwin provider-owned GraspGen contact-depth post-processing. The new
no-motion geometry worker extracts real Panda hand/finger vertices and table
support geometry; finite ingress-backoff variants are qualified for support
clearance and pinch containment before route materialization. Original
GraspGen depth and PAOS authority boundaries remain unchanged. Focused tests
pass `10`; full RoboTwin adapter suite passes `323 passed, 1 skipped`; no
simulator motion, Gateway, Dora, Action, benchmark motion, or hardware ran.

新增 RoboTwin provider-owned GraspGen 抓取接触后处理。新的无运动 geometry worker
读取真实 Panda hand/finger 顶点和桌面支撑几何，在 route 物化前按有限 ingress backoff
候选同时验证支撑面净空与 pinch 包络。原始 GraspGen depth 与 PAOS 权威边界保持不变。
专项测试 `9 passed`，RoboTwin adapter 全量 `323 passed, 1 skipped`；未运行仿真动作、
Gateway、Dora、Action、benchmark motion 或硬件。

Files: `docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md:L1-L67`,
`examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_postprocessing.py:L1-L201`,
`examples/forge-adapters/robotwin20/runtime/robotwin_grasp_contact_geometry_worker.py:L1-L98`,
`examples/forge-adapters/robotwin20/scripts/materialize_complete_route.py:L653-L674,L692-L699,L820-L827`,
and the two focused test files.

Implementation commit: `f7eea46`; branch: `feature/planning-loop`.

## [v7.3.1] - 2026-09-08

Code-review fixes for the independent `evolution` extension: transition
predicates are bound to declared expectations, evidence-free and low-confidence
attributions cannot create EvoPhy candidates, TRACE exposes explicit
score-primary ordering while retaining earliest-first default behavior, and
EvoPhy can emit all four bounded patch surfaces. Candidate lifecycle submission
is now an explicit host port; verification-off episodes are skipped and
forward-transfer is reported only when held-out pairs exist.

针对独立 `evolution` 扩展完成代码审查修复：transition predicate 必须绑定到已声明的
expectation；无 evidence 和低置信度归因不会生成 EvoPhy 候选；TRACE 保留默认最早偏离
顺序并支持显式 score-primary 排序；EvoPhy 可生成四类受限 patch。候选生命周期提交改为
显式宿主 port；verification-off episode 会跳过；只有存在 held-out pair 时才报告
forward-transfer。

Files: `extensions/evolution/evolution/api.py:L158-L184,L267-L312`,
`trace.py:L12-L174`, `settlement.py:L21-L226`,
`methods/evophy/method.py:L21-L83`, `plugin.py:L25-L151`,
`evaluation.py:L49-L75`, `observation.py:L27-L145`,
`PhyAgentOS/agent/experience/contracts.py:L139-L206`,
`source.py:L237-L267`, `coordinator.py:L205-L235`, and extension tests.

Validation: extension `60 passed`; full PAOS `250 passed`; Ruff,
compileall, wheel build, and `git diff --check` passed. Six-dimension review
passes failure behavior, authority/safety, reproducibility, maintainability,
and observability. Architecture integration is partial: standard CLI/gateway
composition still requires an explicit host projection and lifecycle adapter;
no complete production self-evolution claim is made. No Gateway, Dora,
simulation step, Action, or hardware execution ran.

## [v7.2.6] - 2026-09-08

Fixed the Textual Tasks / DAG projection diagnostics. An empty dashboard now
identifies the exact session and explains that a persisted `AgentTask +
PlanGraph` is required; DAG node states render as plain `status=<state>` text
so `pending` is not consumed by Rich/Textual markup. The existing
AgentTaskCoordinator ownership, session filtering, Skill binding requirements,
and no-motion boundaries are unchanged.

修复 Textual Tasks / DAG 投影诊断。空面板现在显示精确 session，并说明必须先持久化
`AgentTask + PlanGraph`；DAG 节点状态改为纯文本 `status=<state>`，避免 `pending`
被 Rich/Textual markup 吞掉。AgentTaskCoordinator 所有权、session 过滤、Skill binding
要求以及无运动边界均保持不变。

Files: `PhyAgentOS/cli/textual_app.py:L240-L250,L267-L273`,
`tests/test_textual_app.py:L128-L207`.

Key diff / 关键代码 Diff:

```python
# Before
self.query_one("#tasks", static_type).update("No AgentTask")
lines.append(f"  [{node['status']}] {node['node_id']} ...")

# After
self.query_one("#tasks", static_type).update(
    f"No AgentTask for session {normalized_session_key}\n"
    "Submit a task that materializes an AgentTask + PlanGraph."
)
lines.append(f"  status={node['status']} node={node['node_id']} ...")
```

Validation: Textual/planning regression `44 passed, 1 warning`; Ruff,
compileall, and `git diff --check` passed. No Gateway, Dora, simulator,
Action, or hardware execution ran.

## [v7.2.5] - 2026-09-08

Added provider-neutral consequence settlement to the independent `evolution`
extension. Timestamped physical evidence now remains pending while its outcome
window is open and settles on deadline, provider confirmation, terminal event,
or interruption. The latest observation group determines predicate state;
missing, low-coverage, and same-time conflicting evidence settles as `unknown`.
Side effects, reversibility, owner hypotheses, evidence references, and window
close reason remain available to PULSE, TRACE, and EvoPhy candidate generation.

为独立 `evolution` 扩展增加 provider-neutral consequence settlement。带时间戳的
物理证据在 outcome window 开放时保持 pending，并在 deadline、provider 确认、
terminal event 或 interruption 时结算。最后一组观测决定谓词状态；无证据、低覆盖和
同时间冲突结算为 `unknown`。side effects、reversibility、owner hypotheses、
evidence references 与窗口关闭原因继续传递给 PULSE、TRACE 和 EvoPhy 候选生成。

Files: `extensions/evolution/evolution/api.py:L25-L155,L293-L314`,
`settlement.py:L21-L212`, `evolution/__init__.py:L1-L58`,
`tests/test_consequence_settlement.py:L1-L250`,
`extensions/evolution/README.md:L38-L72`, and the local design document
`docs/zh/06-consequence-driven-skill-evolution-design.md:L455-L472`.

Key diff / 关键代码 Diff:

```python
# Before: episode close converted every pending record directly to unknown.
settled = settle_pending(records)

# After: timestamped provider evidence is settled against explicit windows.
observations = ConsequenceSettler(policy=policy).settle(
    targets=targets,
    samples=evidence_samples,
    at_ms=settlement_time_ms,
    close_reason=close_reason,
)
```

Six-dimension acceptance passed for architecture integration, failure behavior,
authority and safety, configuration and reproducibility, maintainability, and
observability/Anti-OverDefense. Review found no Blocker or Major findings.
Validation: independent extension `48 passed`; PAOS seam `6 passed`; full PAOS
regression `248 passed`; Ruff, compileall, locked environment sync, extension
sdist/wheel build, isolated wheel import, root wheel build/exclusion, and
`git diff --check` passed. All tests used fake facts without Gateway, Dora,
simulation step, Action, or hardware motion. Benchmark accuracy, cross-provider
generalization, and future-task utility remain evaluation-pending claims.

## [v7.2.4] - 2026-09-08

Completed the independently packaged `evolution` extension around the existing
PAOS episode hook. Provider-neutral projection composition now feeds explicit
outcome windows, evidence coverage, owner hypotheses, reversibility, and costs
into PULSE and TRACE; EvoPhy emits one-surface Local Skill Patch candidates.
Matched, held-out, and hazard receipts drive a fixed-weight selection policy,
paired Future Skill Use comparisons, and non-overwriting evaluation artifacts.

完成基于 PAOS 既有 episode hook 的独立 `evolution` 扩展包。provider-neutral
projection 将 outcome window、证据覆盖、owner hypotheses、reversibility 与成本
送入 PULSE 和 TRACE；EvoPhy 输出单一修改表面的 Local Skill Patch 候选。
matched、held-out 与 hazard receipts 驱动固定权重选择、成对 Future Skill Use
比较以及不覆盖历史结果的评测 artifacts。

Files: `extensions/evolution/evolution/api.py:L1-L267`,
`projection.py:L1-L106`, `plugin.py:L1-L136`, `pulse.py:L1-L74`,
`trace.py:L1-L160`, `revision.py:L1-L107`, `evaluation.py:L1-L156`,
`observation.py:L1-L145`, `experiment.py:L1-L144`,
`tests/test_evolution_extension.py:L1-L937`,
`tests/test_evolution_extension_hook.py:L1-L133`, and the local design/README.

Key diff / 关键代码 Diff:

```python
# Before: evolution stopped at a generic episode/candidate loop.
projection = project_episode(episode)
proposal = method.process(projection)

# After: episode facts flow through explicit method and evaluation stages.
projection = composed_projection.project(episode)
proposals = evophy.process(projection)
decision = CandidateEvaluator(policy=policy).decide(
    proposals[0], receipts=matched_heldout_hazard_receipts
)
```

Validation: independent Python 3.11 extension suite `38 passed`; PAOS seam
suite `6 passed`; full PAOS regression `247 passed`; Ruff, compileall, locked
environment sync, extension/root wheel builds, fresh-wheel import, root-wheel
exclusion, and `git diff --check` passed. Fake facts establish mechanical and
integration behavior only; comparative benchmark claims remain evaluation
pending. No Gateway, Dora, simulator step, Action, or hardware motion ran.

## [v7.2.3] - 2026-09-08

Bounded provider attempts and complete Agent turn execution with configurable
`requestTimeoutS` and `turnTimeoutS`. AgentLoop now emits turn-correlated
queued/running/completed/timeout/failed/cancelled lifecycle events, and the
Textual presentation renders them instead of leaving a permanent `thinking`
marker. A timed-out turn releases the existing serialization lock so the next
queued turn can run; no second scheduler or store was introduced.

通过可配置的 `requestTimeoutS` 与 `turnTimeoutS` 限制 provider 单次请求和完整
Agent turn。AgentLoop 发布关联 turn_id 的 queued/running/completed/timeout/failed/
cancelled 生命周期事件，Textual 展示这些状态，不再永久停留在 `thinking`。超时后会
释放既有串行锁，使后续排队 turn 能继续执行；没有新增第二套 scheduler 或 store。

Files: `PhyAgentOS/providers/base.py:L59-L69,L219-L272`,
`PhyAgentOS/providers/litellm_provider.py:L243-L249`,
`PhyAgentOS/config/schema.py:L232-L251`,
`PhyAgentOS/agent/loop.py:L627-L713,L893-L964`,
`PhyAgentOS/cli/textual_app.py:L159-L280`, CLI wiring, and focused tests.

Key diff / 关键代码 Diff:

```python
# Before: an unbounded model request could hold the turn forever.
response = await self._process_message(msg)

# After: the same AgentLoop owns a bounded turn and publishes timeout state.
response = await asyncio.wait_for(
    self._process_message(msg), timeout=self.turn_timeout_s
)
```

Validation: focused timeout/Textual suite `11 passed`; planning/TUI regression
`64 passed`; Ruff, compileall, and `git diff --check` passed. No Gateway, Dora,
simulation, Action, or hardware execution was started.

## [v7.2.0] - 2026-09-08

Added the optional Textual task-monitoring presentation layer. `paos agent
--ui textual` renders conversation, progress, persisted Coordinator events,
task/revision/DAG settlements, and clarification state while reusing the
existing AgentLoop, MessageBus, LongHorizonTaskController, and
AgentTaskCoordinator. It adds no scheduler, store, PlanRevision, Gateway, or
motion authority; `prompt_toolkit` remains the default. Validation: Textual
0.89.1 installed, focused no-motion suite `41 passed, 1 warning`, Ruff,
compileall, and `git diff --check` passed.

新增可选 Textual 任务监控 presentation layer。`paos agent --ui textual` 复用既有
AgentLoop、MessageBus、LongHorizonTaskController 和 AgentTaskCoordinator，展示对话、
进度、持久化 Coordinator 事件、任务/revision/DAG settlement 与 clarification；不新增
scheduler、store、PlanRevision、Gateway 或运动权限，默认 `prompt_toolkit` 保持兼容。
验证：Textual 0.89.1 安装成功，无运动专项 `41 passed, 1 warning`，Ruff、compileall 和
`git diff --check` 通过。

Files: `PhyAgentOS/cli/textual_app.py`, `PhyAgentOS/cli/commands.py`,
`tests/test_textual_app.py`, `pyproject.toml`, and Forge planning docs.

Key diff / 关键代码 Diff:

```python
# Before: prompt_toolkit presentation started directly after controller wiring.
agent_loop.set_long_horizon_controller(long_horizon_controller)

# After: Textual receives the same runtime objects through an optional branch.
if ui == "textual":
    run_textual_app(
        agent_loop=agent_loop,
        bus=bus,
        controller=long_horizon_controller,
        coordinator=forge_task_coordinator,
        session_key=session_id,
    )
```

File details: `PhyAgentOS/cli/textual_app.py:L1-L332` added the presentation
adapter; `PhyAgentOS/cli/commands.py:L900-L1003` added the optional entry;
`tests/test_textual_app.py:L1-L192` added projection, headless UI, delegation,
and shutdown coverage.

Implementation commit: `be13b77`; branch: `feature/planning-loop`.

## [v6.10.9] - 2026-09-08

Added the control-only long-horizon task surface: `paos task status|pause|resume`
and interactive `/task ...` commands reuse `LongHorizonTaskController` and the
existing Coordinator transaction store. No second scheduler, store, LiteLLM
loop, Gateway path, or motion authority was added. No-motion planning/controller
regression passes `47 passed`.

新增长程任务 control-only 入口：`paos task status|pause|resume` 及交互式
`/task ...` 命令复用 `LongHorizonTaskController` 与现有 Coordinator 事务存储，
没有新增 scheduler、store、LiteLLM loop、Gateway 路径或运动权限。无运动规划/控制器
回归通过 `47 passed`。

Files: `PhyAgentOS/agent/long_horizon.py`, `PhyAgentOS/cli/commands.py`,
`tests/test_long_horizon_controller.py`, and Forge planning docs.

Note: current Typer 0.9/Click 8.2 help rendering has a pre-existing
`Parameter.make_metavar(ctx)` compatibility error; task control logic itself is
covered directly and does not depend on help rendering.

## [v6.10.10] - 2026-09-08

Clarified that production Planner/Skill plugins run in their own managed
runtime environment and exchange only provider-neutral planning projections;
the `paos.planners` entry point remains an explicit in-process development seam.
Validated in the `paos` environment: planning/controller no-motion focus
`47 passed`, CLI task help renders, and unknown task control exits with code 1.

明确生产 Planner/Skill 插件必须运行在自身 managed runtime 环境，只跨边界交换
provider-neutral planning projection；`paos.planners` entry point 仅作为显式的
PAOS 内开发 seam。在 `paos` 环境验证：规划/控制器无运动专项 `47 passed`，CLI
task help 正常显示，未知任务控制以退出码 1 fail-closed。

Files: `docs/forge/PLANNING_MODULE_DESIGN.md`,
`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`.

## [v6.10.6] - 2026-09-08

Reviewed and implemented a PAOS-compliant long-horizon outer loop: `LongHorizonTaskController` drives the existing `PlanningLoopAdapter` with per-call checkpoints, while pause requests are persisted on `AgentTaskRecord` through Coordinator transactions. Documented TUI/prompt_toolkit boundaries, stateless LiteLLM semantics, and Textual as a future presentation layer.

按 PAOS 原则审核并实现长程任务 outer loop：`LongHorizonTaskController` 通过 per-call checkpoint 驱动现有 `PlanningLoopAdapter`，pause 请求由 Coordinator 事务持久化到 `AgentTaskRecord`。同步记录 TUI/prompt_toolkit 边界、LiteLLM 无状态语义和 Textual 后续展示层原则。

Files: `PhyAgentOS/agent/long_horizon.py`, `PhyAgentOS/agent/planning_loop.py`, `PhyAgentOS/agent/__init__.py`, `PhyAgentOS/forge/task.py`, `tests/test_long_horizon_controller.py`, `docs/forge/PLANNING_MODULE_DESIGN.md`, `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`.

Validation: `45 passed, 1 warning`; Ruff, compileall, and `git diff --check` passed; no Gateway, Dora, simulator, or hardware motion.

## [v6.10.2] - 2026-09-07

Replan settlement carry-over now compares complete `PlanNode` identities and rejects changed-node preservation; node execution results are checked against task/revision/node context; admission no longer reserves a fixed `verify` node name. Added no-motion regressions for all three cases.

跨 revision 复用 settlement 前比较完整 `PlanNode` 身份并拒绝内容变化；节点执行结果校验 task/revision/node 绑定；admission 不再占用固定 `verify` 节点名。新增三类 no-motion 回归测试。

Files: `PhyAgentOS/forge/task.py:L1075-L1099`, `PhyAgentOS/agent/planning_loop.py:L341-L348`, `PhyAgentOS/agent/planning_dispatch.py:L165-L174`, `tests/test_planning_loop.py:L238-L329`, `changelog/2026-09_part3.md:L3-L74`.

Validation: focused planning suite `41 passed, 1 warning`; Ruff, compileall, and `git diff --check` passed; no Gateway, Dora, simulator, or hardware motion.

## [v6.10.0] - 2026-09-07

Implemented the PAOS planning-loop feature as an independent orchestration extension. The existing AgentTask/PlanRevision now persist NodeSettlements and replan metadata, discovery can expand a DAG under the same task, and `PlanningLoopAdapter` drives ready nodes with direct-predecessor context, reducer replay, and Agent-selected counterevidence recovery. `PlannerPlugin` provides an opt-in entry-point seam without a second scheduler, store, or execution path. Pure RGB attribute-sorting fake execution passed the focused contract suite; no Gateway, Dora, simulator, or hardware motion was run.

以独立编排扩展实现 PAOS planning loop：现有 AgentTask/PlanRevision 持久化 NodeSettlement 与 replan 元数据，同一任务支持 discovery 后 DAG 扩展；`PlanningLoopAdapter` 支持 ready node 推进、直接前驱上下文、reducer replay 与 Agent 选择的反证恢复；`PlannerPlugin` 提供 opt-in entry-point 插件边界，不新增 scheduler、store 或执行协议。RGB 属性排序纯 fake execution 专项通过，未运行 Gateway、Dora、仿真器或硬件动作。

Files: `PhyAgentOS/agent/planning_loop.py`, `PhyAgentOS/agent/planner_plugin.py`, `PhyAgentOS/forge/task.py`, `PhyAgentOS/agent/loop.py`, `PhyAgentOS/agent/tools/forge_task.py`, `tests/test_planning_loop.py`, `docs/forge/PLANNING_MODULE_DESIGN.md`.

Validation: `38 passed`; Ruff, compileall, and `git diff --check` passed; no-motion only.

## [v6.8.15] - 2026-09-07

Completed the RGB attribute-sorting scenario analysis with the progressive-planning gaps that the initial design did not cover. Unknown block inventory now requires a discovery checkpoint followed by DAG expansion in a new PlanRevision under the same AgentTask. The design also distinguishes direct Action failure from post-success counterevidence such as a later-observed dropped block, and records that preserve/invalidate/fresh-evidence semantics must be applied across revisions before predecessor context can be reused.

补全 RGB 属性排序场景的 progressive planning 缺口：未知方块库存必须先经过 discovery checkpoint，再在同一 AgentTask 的新 PlanRevision 中扩展 DAG；同时区分 Action 直接失败与成功后被后续观察发现脱落的反证，并明确跨 revision 复用前驱上下文之前必须实际应用 preserve/invalidate/fresh-evidence 语义。

Files: `docs/forge/PLANNING_MODULE_DESIGN.md:L263-L306,L418-L426`, `changelog/2026-09_part3.md:L3-L38`.

Validation: `git diff --check` passed; documentation-only analysis, with no Gateway, Dora, Action, simulation motion, or hardware execution.

## [v6.8.13] - 2026-09-07

Recorded the PAOS-compatible generic attribute-sorting scenario and execution-loop extension in `docs/forge/PLANNING_MODULE_DESIGN.md:L233-L387`. The RGB block example is treated as a validation case: block count, colors, and locations are discovered by observation evidence rather than hard-coded. The design reuses AgentLoop, AgentComposedDispatch, AgentTaskCoordinator, PlanRevision, Forge Tools, Evidence, and Verifier; it defines direct-predecessor context injection, NodeSettlement persistence, reducer replay versus Action/Session rerun, Agent-selected ReplanDelta recovery, and a planner/plugin boundary without a second scheduler, store, DAG, or execution protocol.

记录 PAOS 兼容的通用属性排序场景和执行 loop 扩展，详见 `docs/forge/PLANNING_MODULE_DESIGN.md:L233-L387`。RGB 方块仅作为验证场景，方块数量、颜色和位置由 observation evidence 发现，不写死在规划器中。设计复用 AgentLoop、AgentComposedDispatch、AgentTaskCoordinator、PlanRevision、Forge Tools、Evidence 和 Verifier；定义直接前驱上下文注入、NodeSettlement 持久化、reducer replay 与 Action/Session rerun 的区别、Agent 选择的 ReplanDelta 恢复路径以及 planner/plugin 边界，不引入第二套 scheduler、store、DAG 或执行协议。

Files: `docs/forge/PLANNING_MODULE_DESIGN.md:L233-L387`, `changelog/2026-09_part3.md:L3-L51`.

Validation: planning-focused tests `20 passed`; `git diff --check` passed; no code, Gateway, Dora, Action, simulation motion, or hardware was executed or changed.

## [v6.8.11] - 2026-09-07

Replaced the failed SAPIEN single-box peer-arm extraction with a provider-owned Curobo collision-sphere projection. The held peer arm is evaluated at its captured qpos, transformed through the shared world frame, and loaded into each selected-arm planner as conservative enclosing OBBs because the vendored collision checker does not install `WorldConfig.sphere`. Real no-motion validation loaded 61 peer obstacles plus table and two blocks into each planner.

用 provider-owned Curobo collision-sphere 投影替代失败的 SAPIEN 单 box 机械臂投影。未选中臂按捕获的 hold qpos 求碰撞球，经共享 world frame 转换，并因 vendored collision checker 不会装载 `WorldConfig.sphere` 而以保守包围 OBB 加载到每个选中臂 planner。真实 no-motion 验证确认每侧加载 61 个 peer 障碍以及 table 和两个方块。

Files: `dual_arm_state.py:L17,L197-L287`, `robotwin_simulation_probe_worker.py:L240-L289`, `robotwin_curobo_world_port.py:L9-L13,L121-L156,L166-L211`, tests, and `DUAL_ARM_PLANNING_EXECUTION_PLAN.md:L222-L234`.

Validation: focused `51 passed`; full relevant suite `776 passed, 1 skipped`; real Curobo no-motion load `64 active OBB per arm`, Ruff, compileall, and `git diff --check` passed. New route package `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v6.8.11-20260907T2200Z/` remains pending human review with route digest `f66bd11a5d1f941ed9c93facd6476e1eee07163ec1df6a2d377a7c3cbb3379c0`, source-manifest digest `542ea4aac6cfbed491e9f8fdf70eff9a06873c69c7cd9d6632776fdad23d8f7e`, and worker digest `c47601e14f3b632481babdbf8eb22e4c1cd3445aaea46ed9d88bd92a7603df96`. No simulation step, Gateway, Dora, Action, or hardware motion ran in v6.8.11.

## [v6.8.10] - 2026-09-07

Ran the human-approved v6.8.9 simulation-only probe once. It failed closed during scene initialization with `peer arm collision geometry is unavailable`, before any simulator/control step. Evidence showed that SAPIEN Franka links expose mesh/convex geometry while the old provider projection required a single box; candidate, speed, TCP, route geometry, and OBB cache were not implicated.

执行了一次经人工批准的 v6.8.9 simulation-only probe。它在任何 simulator/control step 前，于 scene initialization 因 `peer arm collision geometry is unavailable` fail-closed。证据表明 SAPIEN Franka link 提供 mesh/convex geometry，而旧 provider projection 强制要求单 box；问题与 candidate、速度、TCP、route geometry 或 OBB cache 无关。

Artifacts: `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v6.8.9-20260907T2015Z/probe/result.json` and the bound failure/snapshot records. No Gateway, Dora, Action, or hardware path was used.

## [v6.8.9] - 2026-09-07

Materialized and independently validated a fresh no-motion `blocks_ranking_rgb` sequential dual-arm route package. It binds the latest simulation-probe worker, both-arm MotionCapability documents, controller qualification, and a complete non-target collision world. The package remains pending exact human simulation-only approval; no simulator step, Gateway, Dora, Action, or hardware motion ran.

重新物化并独立校验了新的 no-motion `blocks_ranking_rgb` 顺序双臂 route package。它绑定最新 simulation-probe worker、双臂 MotionCapability、controller qualification 和完整非目标物体碰撞世界。package 仍等待精确人工 simulation-only 审批；未执行 simulator step、Gateway、Dora、Action 或硬件动作。

Artifact root: `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v6.8.9-20260907T2015Z/`; route digest `ba6153412ef675b4a1b7cd750f7ea02316cd10ad989873ccf1ef0c596aa09923`; source-manifest digest `b707f0836d973fb57c3e362e4488d6e93e85bf5d8a3f5c6b8e4c7cb1284815dc`; worker sha256 `7c7b1bfb6ba2c93419c5a34bec7165415e151bfc81aa65c2fba8fa5271de6d5d`.

Validation: route-request and collision-world validators passed; focused dual-arm/collision/qualification/probe suite `49 passed`; `git diff --check` passed.

## [v6.8.8] - 2026-09-07

Documented the cross-benchmark reuse boundary for single-arm Franka providers. PAOS Core, planning, Skill, capability, and lifecycle contracts are reusable; RoboTwin runtime, route readiness, probe, and collision-world code still require explicit single-arm topology branches.

记录跨 benchmark 单臂 Franka provider 的代码复用边界。PAOS Core、planning、Skill、capability 和生命周期协议可复用；RoboTwin runtime、route readiness、probe 与 collision-world 仍需显式单臂 topology 分支。

Files: `docs/forge/DUAL_ARM_PLANNING_EXECUTION_PLAN.md:L420-L458`.

Validation: documentation-only change; `git diff --check` passed and no simulation or motion was run.

## [v6.8.7] - 2026-09-07

Clarified that the current RoboTwin integration supports sequential dual-arm execution only: one arm is driven at a time and the peer arm is held/parked and projected as a static obstacle. Simultaneous synchronized bimanual motion is not implemented.

明确当前 RoboTwin 集成仅支持顺序双臂执行：一次只驱动一只机械臂，另一只机械臂保持/停放并作为静态障碍投影。同时同步双臂运动尚未实现。

Files: `docs/forge/DUAL_ARM_PLANNING_EXECUTION_PLAN.md:L61-L63`.

Validation: documentation-only change; `git diff --check` passed and no simulation or motion was run.

## [v6.8.6] - 2026-09-07

Implemented provider-owned dual-arm planning state, qualified arm/link contact identity, held-arm drift checks, and peer-arm static collision projection for sequential RoboTwin planning. Curobo remains behind the adapter port; synchronized atomic dual-arm execution is still not claimed.

实现 provider-owned 双臂规划状态、qualified arm/link 接触归因、未选中臂漂移检查和顺序 RoboTwin 规划的另一臂静态碰撞投影。Curobo 仍封装在 adapter port 后；本轮不宣称同步原子双臂执行。

Files: `examples/forge-adapters/robotwin20/src/robotwin20_adapter/dual_arm_state.py:L1-L200`, `examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py:L82-L238`, `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py:L426-L500,L853-L910,L1692-L1740`.

Validation: RoboTwin adapter `289 passed, 1 skipped`; focused dual-arm/route/probe `40 passed`; Ruff, compileall, and `git diff --check` passed. New simulation motion was not run; prior approval is invalid after worker changes.

## [v6.8.5] - 2026-09-07

Clarified that true dual-arm planning is not the concatenation of two independent Curobo plans. The design now distinguishes static other-arm projection, sequential bimanual execution, and synchronized atomic bimanual execution, with geometry, trajectory, and execution-layer collision checks. The current RoboTwin path remains limited to sequential execution with explicit hold/park semantics.

明确真正的双臂联合规划不是两个独立 Curobo 结果的拼接。设计现在区分另一只机械臂静态投影、顺序双臂执行和同步原子双臂执行，并定义几何层、轨迹层和执行层防碰撞检查。当前 RoboTwin 路径仍限制为带显式 hold/park 语义的顺序执行。

Files: `docs/forge/DUAL_ARM_PLANNING_EXECUTION_PLAN.md:L61-L121`, `changelog/2026-09_part3.md:L3-L20`.

Validation: `git diff --check` passed; no runtime code or simulation motion was changed or executed.

## [v6.8.4] - 2026-09-07

Recorded the PAOS-compatible dual-arm planning protocol and corrected the earlier overclaim that an ambiguous `panda_leftfinger ↔ table` contact proved an unselected-left-arm collision. The document defines reset/stabilization state, qualified contact identity, provider-owned inter-arm projection, route admission, semantic verification, and replanning.

记录 PAOS 兼容的双臂规划协议，并纠正此前将无法区分机械臂的 `panda_leftfinger ↔ table` 接触直接归因于未选中左臂的问题。文档定义 reset/stabilization 状态、qualified contact identity、provider-owned 跨臂投影、路线准入、语义验收和重规划。

Files: `docs/forge/DUAL_ARM_PLANNING_EXECUTION_PLAN.md:L1-L58,L123-L286`, `changelog/2026-09_part3.md:L17-L31`.

Validation: documentation review and `git diff --check` passed; no runtime or motion changes were made.

## [v6.8.3] - 2026-09-07

Materialized the exact human-approved simulation-only probe package and ran one independent RoboTwin20 probe. The provider executed 1174 simulator steps but returned `unavailable` at retreat because the unselected left arm contacted the table; failure evidence, contact trace, and stop/reset records were persisted. This is a real route-safety failure, not a candidate or speed-tuning success, and no Gateway, Dora, Action, or hardware path was used.

物化了与人工批准精确绑定的 simulation-only probe package，并运行一次独立 RoboTwin20 probe。provider 实际执行 1174 个 simulator steps，但在 retreat 阶段因未选中的左臂接触 table 返回 `unavailable`；失败 evidence、接触轨迹和 stop/reset 记录均已保存。这是路线安全失败，不是更换候选或调速成功；未调用 Gateway、Dora、Action 或 hardware。

Artifacts: approval `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v6.8.2-20260907T1515Z/route/probe/approval.json` (sha256 `a1529ddd1286863f2be390a8ccf192931515df7aefcf3a3654a997b0c00e5fdf`); failure `artifact://simulation-probe/franka-blocks-green0-collision-v682-20260907/block-green-1-0/failure`.

Validation: approval materialization passed; probe returned expected exit code 2 with `status=unavailable`; focused route/probe suite `52 passed`. Six-dimension review recorded in `changelog/2026-09_part3.md`; architecture and maintainability remain partial until an explicit park/back-to-origin subtask or equivalent unselected-arm state is admitted.

## [v6.8.2] - 2026-09-07

Materialized and independently validated a fresh route-request/v7 package for the provider collision-world probe. The package binds a complete table+red+blue world, real GraspGen candidate-0, dual-Franka capabilities, and q4 qualification; it remains pending exact human simulation-only approval and no simulation step was run.

为 provider collision-world probe 物化并独立校验了新的 route-request/v7 package。package 绑定完整 table+red+blue 世界、真实 GraspGen candidate-0、双 Franka capability 和 q4 qualification；当前仍等待精确人工 simulation-only 审核，未执行任何仿真 step。

Artifact root: `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v6.8.2-20260907T1515Z/route/`; route digest `ada0e733dbbe2e59145ef00c89bb33f3841bf379ab15dee94cb3ef31551455d1`; source-manifest digest `96f1e24087f76f8ced9cf1ab68c4fba4704f659683274882a5a7e513b85fc308`.

Validation: route and collision-world validators passed; `motion_authorized=false`; no scene.step, benchmark, Gateway, Dora, Action, or hardware ran.

## [v6.8.1] - 2026-09-07

Integrated the provider-owned RoboTwin/Curobo collision world and fixed the concrete OBB cache-capacity failure. The runtime now updates both arms when capacity is available or rebuilds warmed MotionGen instances from the existing RoboTwin profile when it is not; the swap is no-motion and fail-closed. Collision-world capacity is derived from obstacle count rather than a fixed constant.

接入 provider-owned RoboTwin/Curobo 碰撞世界并修复已复现的 OBB cache 容量问题。runtime 在容量足够时更新双臂，容量不足时按现有 RoboTwin profile 重建并 warmup MotionGen，切换过程无动作且 fail-closed；碰撞世界容量由障碍数量推导，不再使用固定常量。

Files: `examples/forge-adapters/robotwin20/src/robotwin20_adapter/collision_world.py`, `examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py`, `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py`, route v7 files, and collision-world tests.

Validation: full module suite `759 passed, 1 skipped`; real RoboTwin20/Curobo no-motion probe loaded table+red+blue for dual Franka and rebuilt both arms with capacity 3; Ruff, compileall, and `git diff --check` passed. Six-dimension review passed, including Anti-OverDefense. No Gateway, Dora, Action, hardware, or benchmark motion was run.

## [v6.7.4] - 2026-09-07

Reviewed the diagnosis that observed entities were missing from the RoboTwin/Curobo planning world. Five-dimension review found no blocker after clarifying unknown-space coverage, phase-scoped target exclusion, synchronized dual-MotionGen updates, and Coordinator-owned replanning. Recorded the provider-owned `SceneCollisionWorld` contract and fail-closed gates; no runtime motion or execution surface was changed.

复核已观测实体未进入 RoboTwin/Curobo 规划碰撞世界的诊断。五维审核在补充未知空间覆盖、阶段化目标排除、双 MotionGen 同步更新和 Coordinator 负责重规划后未发现阻塞项。已记录 provider-owned `SceneCollisionWorld` 协议及 fail-closed 门禁；未修改运行时动作或执行面。

Files: `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L1373-L1431`, `docs/forge/ROBOTWIN_ADAPTER_REFACTOR_DIAGNOSIS.md:L574-L649`, `docs/forge/PLANNING_MODULE_DESIGN.md:L211-L224`.

Validation: `git diff --check` passed; read-only document consistency checks passed. No `scene.step`, benchmark, Gateway, Dora, Action, or hardware was run.

## [v6.7.1] - 2026-09-07

Materialized a fresh immutable RoboTwin/Franka simulation-only route package from the v6.7 sources. The package binds q4 controller qualification, both-arm MotionCapability artifacts, runtime, GraspGen provenance, placement/geometry artifacts, and current worker/controller source digests. No simulation step, benchmark, Gateway, Dora, Action, or hardware motion was executed; the package remains pending fresh human approval.

使用 v6.7 当前源码生成新的不可覆盖 RoboTwin/Franka simulation-only route package，绑定 q4 controller qualification、双臂 MotionCapability、runtime、GraspGen provenance、放置/几何 artifact 及当前 worker/controller source digest。未执行仿真 step、benchmark、Gateway、Dora、Action 或硬件动作；package 仍等待新的人工审批。

Artifacts: `/home/yanxu/robotwin20-runtime/artifacts/paos-route-v6.7.1-20260907T0020Z/`; route digest `5dc2abfb6b23c322f12816c86e1762d36dde5da47dfd17b996e7eb112a6a0808`; source-manifest digest `73aed005d1e07c3a11ba50785ee29cb0bb356217bae6c99b55d087f8abcedd2e`.

Validation: no-motion digest check passed; focused route/approval/probe `64 passed`; full `750 passed, 1 skipped`; `git diff --check` passed. Fresh `I_REVIEWED_AND_APPROVE_SIMULATION_ONLY` is still required before any probe.

## [v6.7.0] - 2026-09-07

Bound the RoboTwin simulation probe to the exact provider controller qualified by the immutable MotionCapability artifacts. Every trajectory step now settles through the bounded controller, controller source/version digests are rechecked before execution, and stale approvals, source drift, input drift, invalid commands, and recovery failures remain fail-closed. This change does not authorize benchmark, Gateway, Dora, Action, or hardware motion.

将 RoboTwin simulation probe 绑定到 MotionCapability artifact 资格化的精确 provider controller。每个轨迹 step 都经过 bounded controller 结算，并在执行前重新校验 controller 源码/版本摘要；旧审批、源码漂移、输入漂移、非法命令和恢复失败均保持 fail-closed。本变更不授权 benchmark、Gateway、Dora、Action 或硬件动作。

Validation: focused `67 passed`; full `750 passed, 1 skipped`; Ruff, compileall, and `git diff --check` passed. Existing route artifacts remain diagnostic-only until fresh materialization and human simulation-only approval.

## [v6.1.0] - 2026-09-06

Implemented the first, no-motion milestone of RoboTwin/SAPIEN controller qualification. The provider-owned adapter now separates a qualification plan, source manifest, human review request, no-motion validation, scoped approval, execution evidence, independent validation, and final qualification. Cross-artifact identity/digest checks and atomic staging publication prevent partial or drifted packages. Qualification approval is scoped only to isolated qualification motion; benchmark, hardware, and PAOS motion remain unauthorized.

实现 RoboTwin/SAPIEN controller qualification 的第一阶段无动作闭环。adapter 现在分离 qualification plan、source manifest、人工审核请求、无动作验证、隔离审批、执行证据、独立验证和最终资格记录；跨 artifact identity/digest 校验与 staging 原子发布防止半包和漂移。qualification approval 仅适用于隔离资格测试，benchmark、硬件和 PAOS 动作仍未授权。

### 文件变更详情 / Detailed changes

- 新增 `examples/forge-adapters/robotwin20/src/robotwin20_adapter/controller_qualification.py`：严格定义五类 qualification contract、测试矩阵、证据范围、双臂 capability binding 和跨 artifact validator。
- Added `examples/forge-adapters/robotwin20/src/robotwin20_adapter/controller_qualification.py`: strict qualification contracts, test matrix, evidence scope, dual-arm capability bindings, and cross-artifact validation.
- 新增 `examples/forge-adapters/robotwin20/scripts/materialize_controller_qualification_plan.py`、`verify_controller_qualification_plan.py`、`validate_controller_qualification.py`、`approve_controller_qualification_plan.py`：生成、独立校验和人工审批隔离 qualification 包；不加载场景、不调用 `scene.step()`。
- Added `materialize_controller_qualification_plan.py`, `verify_controller_qualification_plan.py`, `validate_controller_qualification.py`, and `approve_controller_qualification_plan.py`: materialize, independently verify, validate, and human-approve an isolated qualification package without loading a scene or calling `scene.step()`.
- 新增 `examples/forge-adapters/robotwin20/tests/test_controller_qualification.py`：覆盖 schema、完整测试矩阵、digest/identity drift、权限隔离、错误审批和 CLI 路径。
- Added `examples/forge-adapters/robotwin20/tests/test_controller_qualification.py`: covered schemas, complete test matrix, digest/identity drift, authority isolation, invalid approval, and CLI paths.
- 新增 `docs/forge/ROBOTWIN_CONTROLLER_QUALIFICATION_EXECUTION_PLAN.md`：记录大步门禁、PAOS 所有权、实际 artifact 和五维验收结论。
- Added `docs/forge/ROBOTWIN_CONTROLLER_QUALIFICATION_EXECUTION_PLAN.md`: documented milestone gates, PAOS ownership, real artifacts, and five-dimension acceptance.

### 五维验收 / Five-Dimension Review

- 架构集成：通过；qualification 留在 RoboTwin adapter，不创建第二套 PAOS lifecycle/store/execution plane。
- Architecture integration: pass; qualification remains in the RoboTwin adapter without a second PAOS lifecycle, store, or execution plane.
- 失败路径：通过；缺失/重复矩阵、digest mismatch、identity drift、错误审批短语和不完整绑定均 fail-closed。
- Failure paths: pass; incomplete/duplicate matrices, digest mismatch, identity drift, wrong approval phrase, and incomplete bindings fail closed.
- 权威边界：通过；隔离 qualification motion 与 benchmark/hardware/PAOS motion 明确分离。
- Authority boundaries: pass; isolated qualification motion is explicitly separated from benchmark, hardware, and PAOS motion.
- 配置与 provenance：通过；双臂 capability、validation、manifest、plan 和 review request 交叉绑定，无硬编码速度事实。
- Configuration and provenance: pass; dual-arm capability, validation, manifest, plan, and review request are cross-bound with no hard-coded speed facts.
- 可维护性：通过；contract、materializer、verifier、approval CLI 和测试分层，便于替换 provider。
- Maintainability: pass; contracts, materializer, verifier, approval CLI, and tests are layered for provider replacement.

### 验证 / Validation

- Focused qualification suite: `10 passed`。
- Combined core/Skill/adapter regression: `728 passed, 1 skipped`。
- Ruff、compileall、`git diff --check`：通过。
- Real no-motion package: `/home/yanxu/robotwin20-runtime/artifacts/paos-controller-qualification-plan-20260906T1630Z/`。
- No-motion validation digest: `2d977c2ec9ae179fa7ad9ae37b82367e2ddf84b9d3daded96ea2841f69af497e`。
- 未启动 qualification motion、benchmark、Gateway、Dora、Action 或硬件。
- No qualification motion, benchmark, Gateway, Dora, Action, or hardware was started.

### Git 提交 / Git Commit

- Commit: `17bef6f`
- Branch: `feature/long-horizon-workflow`

## [v6.0.0] - 2026-09-06

Implemented the RoboTwin provider-owned `MotionCapability` v2 artifact and bound both Franka arms into route-request/v5. The artifact is derived from the selected RoboTwin checkout and runtime interpreter, records per-joint URDF limits, CuRobo derivatives, timing, identity, source digests, and explicit enforcement semantics. Independent validation proves source/planner agreement only; it does not create controller qualification or motion authority.

实现 RoboTwin provider-owned `MotionCapability` v2，并将 Franka 左右臂绑定到 route-request/v5。artifact 从选定 RoboTwin checkout 和 runtime interpreter 导出逐关节 URDF 限制、CuRobo 导数限制、时间语义、provider identity、source digest 和执行语义。独立验证只证明来源/planner 一致性，不生成 controller qualification 或动作权威。

### 文件变更详情 / Detailed changes

- 新增 `examples/forge-adapters/robotwin20/src/robotwin20_adapter/motion_capabilities.py`：实现 provider source extraction、canonical digest、runtime identity、joint-order/timing/drive semantics 校验及 no-motion validation record。
- Added `examples/forge-adapters/robotwin20/src/robotwin20_adapter/motion_capabilities.py`: provider-source extraction, canonical digesting, runtime identity, joint-order/timing/drive-semantics validation, and a no-motion validation record.
- 新增 `examples/forge-adapters/robotwin20/scripts/materialize_motion_capability.py`、`verify_motion_capability.py`：提供可复现的两阶段 artifact 物化与独立重验证 CLI。
- Added `examples/forge-adapters/robotwin20/scripts/materialize_motion_capability.py` and `verify_motion_capability.py`: reproducible two-stage materialization and independent revalidation CLIs.
- 修改 `PhyAgentOS/forge/manipulation.py`、`arm_candidates.py`、`manipulation-planning.yaml`：将 arm capability opaque reference 命名为 `motion_capabilities_ref`，不新增 PAOS Core 速度事实源。
- Modified `PhyAgentOS/forge/manipulation.py`, `arm_candidates.py`, and `manipulation-planning.yaml`: renamed the arm capability opaque reference to `motion_capabilities_ref` without adding a PAOS Core speed fact source.
- 修改 `route_readiness.py`、`route_generation.py`、`materialize_complete_route.py`、`robotwin_simulation_probe_worker.py`：route-request/v5 和 source-manifest/v3 绑定左右 capability/validation digest；worker 在 world change 前拒绝缺少独立 controller qualification 的路线。
- Modified `route_readiness.py`, `route_generation.py`, `materialize_complete_route.py`, and `robotwin_simulation_probe_worker.py`: route-request/v5 and source-manifest/v3 bind both capability/validation digests; the worker rejects before world change when independent controller qualification is absent.
- 删除旧的 `controller_capabilities.py` 及其测试，避免形成与 MotionCapability 并行的第二份速度配置/事实源；同步 PAOS 诊断、规划、开发者和 adapter 文档。
- Removed the legacy `controller_capabilities.py` and its tests to avoid a parallel speed configuration/fact source; synchronized PAOS diagnosis, planning, developer, and adapter documentation.

### 五维验收 / Five-Dimension Review

- 架构集成：通过；artifact 属于 RoboTwin adapter，Planning 只消费 opaque reference，Gateway/Action/SQLite 生命周期未改变。
- Architecture integration: pass; the artifact belongs to the RoboTwin adapter, Planning consumes only an opaque reference, and Gateway/Action/SQLite lifecycle is unchanged.
- 失败路径：通过；来源篡改、joint order/timing 歧义、digest 漂移、错误本体和缺少资格均 fail-closed。
- Failure paths: pass; source tampering, joint-order/timing ambiguity, digest drift, wrong embodiment, and missing qualification fail closed.
- 权威边界：通过；当前 SAPIEN 结论是 `planner_constrained`，Cartesian/effort enforcement unknown，validation 和 artifact 都固定 `motion_authorized=false`。
- Authority boundaries: pass; current SAPIEN results are `planner_constrained`, Cartesian/effort enforcement is unknown, and both validation and capability artifacts fix `motion_authorized=false`.
- 配置与 provenance：通过；两臂 artifact/validation digest、RoboTwin git revision、runtime versions 和 source paths 均绑定；旧 approval 不复用。
- Configuration and provenance: pass; both arm artifact/validation digests, RoboTwin git revision, runtime versions, and source paths are bound; old approvals are not reused.
- 可维护性：通过；解析、验证、物化、route gate 分层，未来硬件 controller 只能通过独立 provider qualification 接入。
- Maintainability: pass; extraction, validation, materialization, and route gating are layered, and future hardware controllers require independent provider qualification.

### 验证 / Validation

- Adapter/core/Skill combined regression: `718 passed, 1 skipped`。
- Ruff、compileall、`git diff --check`：通过。
- Real RoboTwin Franka source validation (no scene/no motion): left/right both `validated_planner_constraints`; planner/simulator default timestep `0.004 s`; controller period `null`。
- New route package (no motion): route schema `paos-robotwin20-route-request/v5`, manifest `v3`, route digest `bf52b56e3d258789cb58f7cfc2fa7b7ec382771dedf3665a0762f0aba017ecae`, source manifest digest `5d62573d7d70649020ff6bcb8421b572d6d5a080c42787ff909942a23d45888a`。
- Simulation worker gate: `controller-enforced motion capability qualification is unavailable`; rejected before world change, `motion_authorized=false`。
- 未启动 Gateway、Dora、Action、真实仿真动作或硬件；未生成新的 motion approval。
- No Gateway, Dora, Action, real simulation motion, or hardware was started; no motion approval was generated.

### Git 提交 / Git Commit

- Commit: `992d0de`
- Branch: `feature/long-horizon-workflow`

## [v5.10.3] - 2026-09-06

回写 v5.10.2 速度限制架构变更的 Git 提交信息。Recorded the v5.10.2 real speed-limit architecture commit metadata.

- Commit: `891dfea`
- Branch: `feature/long-horizon-workflow`

## [v5.10.2] - 2026-09-06

撤销 RoboTwin 抓取放置 route 中所有无 provider 来源的硬编码速度行为：route v4、route-input profile v3 和 joint-limit policy v2 不再携带统一 `0.20 m/s`、`1.0 rad/s`、execution scale 或自制 retiming；删除伪 speed-controller 层。当前 simulation probe 在缺少 provider-owned motion capability 时于 world change 前 fail-closed，末端速度只作为诊断 evidence。新增真实速度限制架构文档。

Removed every provider-unbacked hard-coded speed behavior from the RoboTwin pick-place route: route v4, route-input profile v3, and joint-limit policy v2 no longer carry global `0.20 m/s`, `1.0 rad/s`, execution scaling, or custom retiming, and the pseudo speed-controller layer was deleted. The simulation probe now fails closed before world change while provider-owned motion capability is absent; end-effector speed remains diagnostic evidence only. Added the real speed-limit architecture document.

### 文件变更详情 / Detailed changes

- `route_readiness.py:L25-L84`、`route_generation.py:L31-L56,L143-L148`、`grasp_adaptation.py:L201-L208,L309-L333`、`route_inputs.py:L16-L20,L205-L216,L312-L316`：删除 pose 速度字段并升级严格 schema。
- `route-inputs.yaml:L1-L52`、`materialize_complete_route.py:L82-L112,L308-L323,L352-L362`：删除无来源速度配置、scale、controller 伪绑定与 retiming。
- `robotwin_simulation_probe_worker.py:L422-L482,L598-L645,L745-L822`：删除补偿和 threshold gate；缺 provider capability 时 pre-motion fail-closed，保留 finite diagnostic measurement。
- 删除 `runtime/trajectory_controller.py:L1-L179` 与 `tests/test_trajectory_controller.py:L1-L126`。
- 新增 `docs/forge/REAL_SPEED_LIMITS_ARCHITECTURE.md:L1-L301`，同步 planning/developer/adapter 文档与回归测试。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置/provenance 和可维护性通过；未启动仿真动作、Gateway、Dora、Action 或硬件。Architecture integration, failure paths, authority boundaries, configuration/provenance, and maintainability pass; no simulation motion, Gateway, Dora, Action, or hardware was started.

### 验证 / Validation

`717 passed, 1 skipped`; Ruff、compileall、`git diff --check` passed。

### Git 提交 / Git Commit

- Commit: `891dfea`
- Branch: `feature/long-horizon-workflow`

## [v5.10.0] - 2026-09-06

复用既有 `CapabilitySnapshot/ArmCapability`，为左右臂增加 adapter-owned controller capability artifact 引用，并新增严格的 RoboTwin controller capability 文档模型。RoboTwin Franka 仿真使用 SAPIEN/URDF 与 CuRobo/MPlib，未接入 Franka SDK；当前 `0.20 m/s` 明确为 measured diagnostic threshold，不是 PAOS 或 Franka 全局硬限制。

Reused the existing `CapabilitySnapshot/ArmCapability` contracts with adapter-owned controller-capability artifact references for both arms, and added a strict RoboTwin controller-capability document model. RoboTwin Franka simulation uses SAPIEN/URDF with CuRobo/MPlib and does not use the Franka SDK; the current `0.20 m/s` value is explicitly a measured diagnostic threshold, not a PAOS or Franka global hard limit.

### 文件变更详情 / Detailed changes

- `PhyAgentOS/forge/manipulation.py:L90-L121`：增加可选、严格校验的 `controller_capabilities_ref`。
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/arm_candidates.py:L98-L167`、`profiles/robotwin20/manipulation-planning.yaml:L6-L25`：绑定每个 arm 的 controller capability artifact。
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/controller_capabilities.py:L1-L147`：新增来源、执行语义、qualification 和 digest 校验。
- `docs/forge/PLANNING_MODULE_DESIGN.md:L27-L55`、`MANIPULATION_DAG_DEVELOPER_GUIDE.md:L101-L123`、两份诊断/审查文档：记录 RoboTwin/Franka SDK 证据及 PAOS 分层。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置/provenance 和可维护性通过；未启动 Gateway、Dora、仿真动作或硬件。Architecture integration, failure paths, authority boundaries, configuration/provenance, and maintainability pass; no Gateway, Dora, simulation motion, or hardware was started.

### 验证 / Validation

`734 passed, 1 skipped`; Ruff、compileall、`git diff --check` passed。

## [v5.9.2] - 2026-09-06

为 adapter-local speed controller 增加独立 `ControllerQualification` 资格协议。`hard_bounded` 必须绑定已批准、独立、限速匹配且有 artifact provenance 的资格证据；缺失、待审核、超限或 identity 漂移均 fail-closed。当前 RoboTwin/SAPIEN drive-target backend 仍不具备 hard-limit 资格。

Added an independent `ControllerQualification` contract for the adapter-local speed controller. `hard_bounded` now requires approved, independent, limit-matching qualification evidence with artifact provenance; missing, pending, over-limit, or identity-drifted evidence fails closed. The current RoboTwin/SAPIEN drive-target backend remains unqualified for hard limits.

### 文件变更详情 / Detailed changes

- `examples/forge-adapters/robotwin20/runtime/trajectory_controller.py:L18-L151`：新增 qualification contract 并强制 hard-mode 校验。
- `examples/forge-adapters/robotwin20/tests/test_trajectory_controller.py:L13-L73`：覆盖资格缺失、批准、漂移和 pending review。
- `changelog/2026-09_part3.md`、两份 PAOS 诊断/实现审查文档：记录 qualification 门禁和五维审查。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置/provenance 和可维护性均通过；当前 backend 仍不可进入 hard-bounded simulation probe。Architecture integration, failure paths, authority boundaries, configuration/provenance, and maintainability pass; the current backend remains ineligible for a hard-bounded simulation probe.

### 验证 / Validation

`40 passed` focused; combined regression `725 passed, 1 skipped`; Ruff、compileall、`git diff --check` passed.

## [v5.9.0] - 2026-09-06

在 RoboTwin adapter 内新增 provider-local `SpeedBoundedExecutionController` seam，明确区分 `hard_bounded` 与 `diagnostic_measured_guard`。当前 SAPIEN drive-target backend 在 world change 前拒绝 hard mode；diagnostic mode 仅记录实测 Cartesian 速度并在超限时 fail-closed。Planning、Skill、Gateway、Experience 未承载仿真器实现。

Added a provider-local `SpeedBoundedExecutionController` seam in the RoboTwin adapter, explicitly distinguishing `hard_bounded` from `diagnostic_measured_guard`. The current SAPIEN drive-target backend rejects hard mode before world change; diagnostic mode only records measured Cartesian speed and fails closed on violations. Planning, Skill, Gateway, and Experience carry no simulator implementation.

### 文件变更详情 / Detailed changes

- `examples/forge-adapters/robotwin20/runtime/trajectory_controller.py:L1-L125`：controller capability、模式、预检、policy binding 和 violation contract。
- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py:L29-L39,L546-L635,L782-L824,L1018-L1032`：接入 measured-speed controller seam 并记录 controller provenance。
- `examples/forge-adapters/robotwin20/tests/test_trajectory_controller.py:L1-L87`、`test_simulation_probe.py:L389-L417`：覆盖 hard-mode 拒绝、速度、输入、policy 漂移和 evidence 失败路径。
- `examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs.yaml:L47-L57`、`scripts/materialize_complete_route.py:L105-L118`：绑定 execution controller profile。
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L1176-L1192`、`docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L1173-L1189`：记录五维审查与 qualification gate。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置和可维护性均通过；当前后端仍不具备 hard Cartesian 限速资格，不得进入新的完整 route probe。Architecture integration, failure paths, authority boundaries, configuration, and maintainability pass; the current backend remains unqualified for hard Cartesian limiting, so no new complete-route probe is authorized.

### 验证 / Validation

`38 passed` focused; combined regression `723 passed, 1 skipped`; Ruff、compileall、`git diff --check` passed.

## [v5.8.0] - 2026-09-06

根据 v7-v10 仿真证据撤回不能证明 Cartesian 速度受控的 position-subdivision 执行调参；`execution_velocity_scale` 恢复为 `0.25` advisory 值，measured-speed `0.20 m/s` fail-closed 门禁和 uniform retiming 保持不变。同步 profile、materializer、simulation worker 与回归测试；保留历史负证据，未生成新 route 或启动新的 probe/Gateway/Dora/Action/硬件。

Based on v7-v10 simulation evidence, removed position-subdivision execution tuning that cannot prove bounded Cartesian speed; restored `execution_velocity_scale` to the `0.25` advisory value while retaining the measured-speed `0.20 m/s` fail-closed gate and uniform retiming. Synchronized the profile, materializer, simulation worker, and regression tests; historical negative evidence is preserved, with no new route or probe/Gateway/Dora/Action/hardware started.

### 文件变更详情 / Detailed changes

- `examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs.yaml:L47-L49`：移除 subdivision，恢复 scale `0.25` 并标记 advisory。
- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py:L546-L633,L750-L811,L939-L950`：删除 subdivision 校验/插值/乘法预算，恢复单一 planner sample 执行。
- `examples/forge-adapters/robotwin20/scripts/materialize_complete_route.py:L105-L112`、`examples/forge-adapters/robotwin20/tests/test_simulation_probe.py:L220-L469`：同步 schema 与测试，移除无证据调参分支。
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L1157-L1173`、`docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L1158-L1174`：记录根因、回滚范围和后续门禁。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置和可维护性均通过；该回滚不授予任何生产动作权限。Architecture integration, failure paths, authority boundaries, configuration, and maintainability pass; the rollback grants no production motion authority.

### 验证 / Validation

`31 passed`; combined regression `716 passed, 1 skipped`; Ruff、compileall、`git diff --check` passed.

## [v5.7.10] - 2026-09-06

回写 v5.7.9 simulation probe evidence 修复提交哈希 `f4222d1`；实现与安全边界不变。

Recorded commit hash `f4222d1` for the v5.7.9 simulation-probe evidence fix; implementation and safety boundaries are unchanged.

### Git 提交 / Git Commit

- Commit: `f4222d1`
- Branch: `feature/long-horizon-workflow`

## [v5.7.9] - 2026-09-06

修正 independent simulation probe 的已执行步数 evidence 低报：`scene.step()` 后立即计入 `simulator_steps`，并新增命令级 execution velocity scale、线速度违规和 failure artifact 回归。全量组合回归 `716 passed, 1 skipped`；Ruff、compileall、`git diff --check` 通过。v7 route 仍等待新的 simulation-only approval，未启动 probe、Gateway、Dora、Action 或硬件。

Corrected under-counted executed-step evidence in the independent simulation probe by incrementing `simulator_steps` immediately after `scene.step()`, and added command-level execution-velocity-scale, linear-speed-violation, and failure-artifact regressions. Full combined regression: `716 passed, 1 skipped`; Ruff, compileall, and `git diff --check` pass. The v7 route still awaits fresh simulation-only approval; no probe, Gateway, Dora, Action, or hardware was started.

### 文件变更详情 / Detailed changes

- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py:L779-L799`：修正 failure step 计数，保持 `0.20 m/s` gate 不变。
- `examples/forge-adapters/robotwin20/tests/test_simulation_probe.py:L263-L297,L357-L468,L470-L535`：覆盖非法 scale、命令缩放、违规字段和 artifact 持久化。
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L1047-L1051`、`docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L1063-L1066`：记录证据计数边界。

### 五维验收 / Five-Dimension Review

架构集成、失败路径、权威边界、配置和可维护性均通过；该修复仅限 adapter-owned simulation probe evidence，不授予生产动作权威。

Architecture integration, failure paths, authority boundaries, configuration, and maintainability pass; the fix is limited to adapter-owned simulation-probe evidence and grants no production motion authority.

### Git 提交 / Git Commit

- Commit: `f4222d1`
- Branch: `feature/long-horizon-workflow`

## [v5.7.7] - 2026-09-05

回写 v5.7.6 simulation-only probe 记录的提交哈希 `d5aa0de`；无实现、证据或安全边界变化。

Recorded commit hash `d5aa0de` for the v5.7.6 simulation-only probe; no implementation, evidence, or safety-boundary changes.

### Git 提交 / Git Commit

- Commit: pending
- Branch: `feature/long-horizon-workflow`

## [v5.7.6] - 2026-09-05

针对 reviewer `yanxu` 批准的 v3 route package，完成一次独立 simulation-only probe。审批与 route/source-manifest digest 严格绑定；RoboTwin20 Python 3.10 worker 在 contact 阶段因超过 profile 的 `0.2 m/s` simulator waypoint linear-speed limit 返回 `unavailable`，保存 before/after snapshot、contact trace、failure artifact 和 reset 状态。该负结果未被解释为 readiness 或任务成功，Gateway/Dora/Action/硬件仍未启用。

Ran one independent simulation-only probe for reviewer-approved v3 route package with strict route/source-manifest digest binding. The RoboTwin20 Python 3.10 worker returned `unavailable` in the contact phase because the trajectory exceeded the profile `0.2 m/s` simulator waypoint linear-speed limit, preserving before/after snapshots, contact trace, failure artifact, and reset status. The negative result is not readiness or task success; Gateway, Dora, Action, and hardware remain disabled.

### 文件变更详情 / Detailed changes

- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L980-L1026`：修正规划模块历史状态并记录 v3 probe 的审批、失败证据和下一门禁。
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L984-L1045`：新增 simulation-only probe 的审批边界、负结果和五维审查。
- `/home/yanxu/robotwin20-sim-probe-20260905T230500Z/`：保存审批、probe response、before/after snapshot、contact trace 和 failure artifact。

### 五维验收 / Five-Dimension Review

探针边界的架构集成、失败路径、权威边界、配置/provenance 和可维护性均通过；但完整路线、attached-object collision、真实 lift、接触动力学和语义放置仍未证明，必须生成新 route 并重新审批。

Architecture integration, failure paths, authority boundaries, configuration/provenance, and maintainability pass for the probe boundary. Complete route, attached-object collision, physical lift, contact dynamics, and semantic placement remain unproven; a new route and approval are required.

### Git 提交 / Git Commit

- Commit: pending
- Branch: `feature/long-horizon-workflow`

## [v5.7.3] - 2026-09-05

修正规划模块历史验收章节的状态漂移，并新增 no-motion 全链路接入验收：PlanGraph 持久化、AgentLoop dispatch、动态 Tool admission、失败结算、重规划以及 Experience replay/审核/promotion 均得到验证。组合回归 `709 passed, 1 skipped`；未调用 Gateway、Dora 或硬件。

Corrected stale planning-module historical status and added a no-motion end-to-end integration acceptance covering PlanGraph persistence, AgentLoop dispatch, dynamic Tool admission, failed settlement, replanning, and Experience replay/review/promotion. Combined regression: `709 passed, 1 skipped`; no Gateway, Dora, or hardware was called.

### 文件变更详情 / Detailed changes

- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L958-L986`：将历史 32.5 节的过时待办改为已完成状态，保留真实 readiness/simulation evidence 为当前门禁。
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L966-L968`：增加历史状态说明和当前下一步边界。
- `tests/test_planning_end_to_end.py:L1-L246`：新增 no-motion 规划集成验收，覆盖 Coordinator、dispatch、admission、settlement、replan 和 Experience promotion。

### 五维验收 / Five-Dimension Review

架构集成、失败路径、权威边界、配置 provenance、可维护性均通过；测试使用独立 no-motion 夹具，不构成真实运动或 readiness 证据。

Architecture integration, failure paths, authority boundaries, configuration/provenance, and maintainability all pass; the test uses an isolated no-motion fixture and is not evidence of real motion or readiness.

### Git 提交 / Git Commit

- Commit: `f244751`
- Branch: `feature/long-horizon-workflow`

## [v5.7.1] - 2026-09-05

规划模块最终收口审查通过：未发现 Blocker/Major；全量组合回归 `708 passed, 1 skipped`，核心/Skill/adapter 回归 `205 passed`，Ruff、compileall、`git diff --check` 通过。真实 Gateway/Dora/Action、仿真运动和 benchmark evidence 仍按 PAOS 门禁后置。

The final planning-module closeout review passed with no Blocker/Major findings. Full combined regression: `708 passed, 1 skipped`; core/Skill/adapter regression: `205 passed`; Ruff, compileall, and `git diff --check` passed. Real Gateway/Dora/Action, simulation motion, and benchmark evidence remain deferred behind PAOS gates.

### Git 提交 / Git Commit

- Commit: `aadc833`
- Branch: `feature/long-horizon-workflow`

## [v5.7.0] - 2026-09-05

规划模块已完成 AgentLoop 的只读 `agent_composed` dispatch bridge 与 Experience 的 review-gated workflow-policy candidate ledger。`forge_plan_activate` 只接受可信 `AdmissionContext` provider，`forge_plan_ready` 暴露 ready semantic nodes；Registry guard 在现有 Forge Query/Action/Session wrapper 前执行 fail-closed admission。候选按 base/proposed policy digest 聚合，必须有独立 replay receipt、不同 episode 支持和人工审核，promotion 还必须由 Skill Runtime callback 返回 `artifact://` receipt。组合回归 `707 passed, 1 skipped`，未启动 Gateway、Dora、Action、仿真动作或硬件。

The planning module now has a read-only `agent_composed` dispatch bridge in AgentLoop and a review-gated workflow-policy candidate ledger in Experience. `forge_plan_activate` accepts only a trusted `AdmissionContext` provider and `forge_plan_ready` exposes ready semantic nodes; the registry guard performs fail-closed admission before existing Forge Query/Action/Session wrappers. Candidates aggregate by base/proposed policy digests and require independent replay receipts, distinct episode support, and human review; promotion additionally requires a Skill Runtime callback returning an `artifact://` receipt. Combined regression: `707 passed, 1 skipped`; no Gateway, Dora, Action, simulation motion, or hardware was started.

### 文件变更详情 / Detailed changes

- `PhyAgentOS/agent/planning_dispatch.py:L1-L244`、`PhyAgentOS/agent/tools/planning.py:L1-L112`：新增只读 AgentLoop dispatch 与可信上下文激活工具。
- `PhyAgentOS/agent/loop.py:L145-L208,L260-L314`、`PhyAgentOS/agent/tools/registry.py:L17-L79`：接入可选 admission guard，不接管 Tool 执行。
- `PhyAgentOS/planning/contracts.py:L327-L383`、`PhyAgentOS/agent/experience/{policy_candidates.py,store.py,coordinator.py}`：新增候选/replay 协议、SQLite ledger、审核与 callback-gated promotion。
- `tests/test_planning_dispatch.py:L1-L170`、`tests/test_workflow_policy_candidates.py:L1-L75`：覆盖 dispatch 和演化门禁。

### Git 提交 / Git Commit

- Commit: `aadc833`
- Branch: `feature/long-horizon-workflow`

## [v5.6.0] - 2026-09-05

规划模块已接入 PAOS 任务生命周期边界：`AgentTaskCoordinator` 接收并持久化具体 `PlanGraph` 的 artifact/ref 与 digest；Query、Action、Session 可携带完整规划归因；`ReplanDelta` 通过 coordinator 生成新 revision；DecisionTrace 以脱敏引用进入 Experience outcome。planning 专项 15 passed，组合 core/Skill 回归 457 passed，RoboTwin adapter 233 passed, 1 skipped。未启动 Gateway、Dora、Action、仿真动作或硬件。

The planning module is now connected to PAOS lifecycle boundaries: `AgentTaskCoordinator` accepts and persists concrete `PlanGraph` artifact/ref and digests; Query, Action, and Session calls can carry complete planning attribution; `ReplanDelta` is adapted into a new revision through the coordinator; DecisionTrace enters the Experience outcome as a redacted reference. Focused planning suite: 15 passed; combined core/Skill regression: 457 passed; RoboTwin adapter: 233 passed, 1 skipped. No Gateway, Dora, Action, simulation motion, or hardware was started.

Remaining by design: real Gateway/Dora/Action motion and benchmark evidence; these are outside the pure planning/Experience integration and remain separately gated.

### Git 提交 / Git Commit

- Commit: `619c1b2`
- Branch: `feature/long-horizon-workflow`

## [v5.5.5] - 2026-09-05

抓取放置 Skill 增加 `baseline` / `agent_composed` 双模式。旧 `LongHorizonWorkflow` 保留为确定性 replay projection；新 bridge 接收 Agent 语义子任务，编译为带 `verify` join 的 PAOS PlanGraph，并按 capability 暴露多个 Tool 候选，通过 planning admission 校验证据、scene、资源和 ToolSpec digest。未执行 Tool、未写 SQLite、未创建 revision、未授权动作。Skill 回归 `270 passed`。

The pick-place Skill now exposes `baseline` / `agent_composed` modes. The existing `LongHorizonWorkflow` remains the deterministic replay projection; the new bridge accepts Agent semantic subtasks, compiles a PAOS PlanGraph with a `verify` join, exposes multiple Tool candidates by capability, and delegates evidence, scene, resource, and ToolSpec-digest checks to planning admission. It executes no Tool, writes no SQLite, creates no revision, and grants no motion authority. Skill regression: `270 passed`.

### 文件变更详情 / Detailed changes

- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py:L1-L216`：新增语义子任务编译、双模式切换、动态 Tool 候选与 admission bridge。
- `examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py:L1-L126`：覆盖多实体并行 DAG、verify join、失败路径、Tool 替代和 mode switch。
- `examples/forge-skills/pick-place-workflow/README.md:L43-L89`、`SKILL.md:L128-L143`、`docs/forge/PLANNING_MODULE_DESIGN.md:L104-L124`：同步动态规划和演化边界。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置、可维护性均通过；旧 reducer 仍为 baseline，Gateway/SQLite/adapter/readiness/Verifier 权威未迁移。未启动 Gateway、Dora、Action、仿真动作或硬件。

Architecture integration, failure paths, authority boundaries, configuration, and maintainability all pass; the legacy reducer remains the baseline and Gateway/SQLite/adapter/readiness/Verifier ownership is unchanged. No Gateway, Dora, Action, simulation motion, or hardware was started.

### Git 提交 / Git Commit

- Commit: `f6d1b7d`
- Branch: `feature/long-horizon-workflow`

## [v5.5.4] - 2026-09-05

新增 PAOS 纯规划模块 `PhyAgentOS/planning`，引入任务级语义 PlanGraph、动态 Tool admission、节点结算、传递重规划、DecisionTrace 和 review-gated WorkflowPolicyCandidate；不接管 Gateway、SQLite、动作执行或物理真值。PlanRevision/ToolExecutionRecord 增加可选但全量校验的 DAG/node binding。设计基准见 `docs/forge/PLANNING_MODULE_DESIGN.md`，开发者指南同步说明 Skill WorkflowDag 仅为 baseline projection。

Added the pure PAOS planning module `PhyAgentOS/planning` with semantic task PlanGraph, dynamic Tool admission, node settlement, transitive replanning, DecisionTrace, and review-gated WorkflowPolicyCandidate; it owns no Gateway, SQLite, motion execution, or physical truth. PlanRevision/ToolExecutionRecord now support optional but all-or-nothing DAG/node bindings. See `docs/forge/PLANNING_MODULE_DESIGN.md`; the developer guide now treats Skill WorkflowDag as a baseline projection only.

### 文件变更详情 / Detailed changes

- `PhyAgentOS/planning/{contracts,dag,admission,settlement,replan,trace,policy}.py:L1-L316`：纯协议和计算，覆盖 digest、依赖/cycle、ready set、evidence/scene/resource/capability/precondition admission、unknown/stale/cancelled settlement、replan delta、trace 和 policy 校验。
- `PhyAgentOS/forge/task.py:L83-L197`：PlanRevision 与 ToolExecutionRecord 绑定 artifact graph/node/obligation/trace digest；SQLite 仍为生命周期事实源。
- `docs/forge/PLANNING_MODULE_DESIGN.md:L1-L118`、`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md:L10-L216`：记录所有权、失败语义、演化边界和迁移阶段。
- `tests/test_planning_module.py:L1-L267`：逐项纯函数、失败路径、生命周期绑定和纯模块边界回归。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置、可维护性均通过；未启动 Gateway、Dora、Action、仿真动作或硬件。规划模块只产生结构准入结果，永不产生 motion authority。

Architecture integration, failure paths, authority boundaries, configuration, and maintainability all pass; no Gateway, Dora, Action, simulation motion, or hardware was started. The planning module produces structural admission results only and never grants motion authority.

### 验证 / Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_planning_module.py` → `8 passed`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -q tests` → `180 passed`
- `python -m ruff check PhyAgentOS/planning PhyAgentOS/forge/task.py PhyAgentOS/forge/__init__.py tests/test_planning_module.py`、`compileall`、`git diff --check` → 通过。

### Git 提交 / Git Commit

- Commit: `f95c53d`
- Branch: `feature/long-horizon-workflow`

## [v5.5.2] - 2026-09-06

完成双臂能力 Query 的 canonical DAG 接入复验：固定七节点
`observe → capabilities → understand → propose → prepare → acquire → place`，所有后续步骤
强制复用同一个 capability snapshot；同步升级 DAG/reducer、Skill manifest 与 Python 包版本，并
修正文档和旧 Runtime fixture。组合回归 `670 passed, 1 skipped`；未启动 Gateway、Dora、Action、
仿真运动或硬件。

Completed the acceptance re-review for the dual-arm capability Query canonical-DAG integration: the
seven-node order `observe → capabilities → understand → propose → prepare → acquire → place` is fixed,
all downstream steps must reuse one capability snapshot, protocol/Skill/package versions are bumped, and
documentation plus old-Runtime fixtures are synchronized. Combined regression: `670 passed, 1 skipped`;
no Gateway, Dora, Action, simulation motion, or hardware was started.

### 文件变更详情 / Detailed changes

- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/long_horizon.py:L15-L17,L173-L236,L560-L585`：新增 canonical `capabilities` 节点、传播并校验 `capability_snapshot_ref`，升级 DAG/reducer 版本。
- `examples/forge-skills/pick-place-workflow/tests/test_long_horizon.py:L25-L311`：更新七节点顺序、terminal response、恢复和绑定漂移回归。
- `examples/forge-skills/pick-place-workflow/skill.yaml:L1-L16`、`pyproject.toml:L1-L6`、`tests/test_binding_freeze.py:L58-L103`、`tests/test_runtime_install_discovery.py:L34-L100`、`tests/test_task_binding_activation.py:L68-L154`、`tests/test_grasp_propose.py:L261-L265`、`tests/test_runtime_controller.py:L73-L76`：统一 Skill `0.10.0` 并验证旧 Runtime fail-closed。
- `examples/forge-skills/pick-place-workflow/README.md:L3-L58`、`SKILL.md:L26-L50,L113-L120`、`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md:L47-L58`、`docs/user_development_guide/README.md:L25-L30`、`README_en.md:L25-L31`：同步七 Tool 顺序和无动作边界。
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L902-L933`、`docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L939-L959`、`examples/forge-skills/pick-place-workflow/CHANGELOG.md:L3-L22`：记录五维验收和剩余 readiness/atomic route 门禁。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置、可维护性均通过；atomic bimanual executor、真实 readiness/人工审批、完整 transport/descent/release/retreat 与语义闭环仍未实现。

Architecture integration, failure paths, authority boundaries, configuration, and maintainability all pass; an atomic bimanual executor, real readiness/human approval, complete transport/descent/release/retreat, and the semantic loop remain unimplemented.

### 验证 / Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src python -m pytest -p pytest_asyncio.plugin -q tests examples/forge-skills/pick-place-workflow/tests examples/forge-adapters/robotwin20/tests` → `670 passed, 1 skipped`
- `python -m ruff check ...`、`python -m compileall -q ...`、`git diff --check` → 通过。
- 未启动 Gateway、Dora、Action、仿真运动或硬件；`motion_authorized=false` 边界保持不变。

## [v5.5.1] - 2026-09-05

完成 PAOS 双臂扩展协议收口：`object.acquire/place` 现在强制绑定 capability snapshot 与 arm assignment；新增只读 `manipulation.capabilities` Query、Skill manifest/contract/Fake Gateway 接入和严格失败关闭。组合回归 `669 passed, 1 skipped`；未启动任何动作、仿真运动或硬件。

Completed the PAOS dual-arm extension contract closeout: `object.acquire/place` now require capability-snapshot and arm-assignment bindings; the read-only `manipulation.capabilities` Query is integrated with the Skill manifest, contract, and Fake Gateway with strict fail-closed behavior. Combined regression: `669 passed, 1 skipped`; no action, simulation motion, or hardware was started.

### 文件变更详情 / Detailed changes

- `PhyAgentOS/forge/manipulation.py:L29-L380`：新增冻结的资源需求、能力快照、assignment、协调组和 digest。
- `PhyAgentOS/forge/capability_runtime/manipulation_capabilities.py:L23-L105`：新增 provider-neutral capability Query。
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/long_horizon.py:L191-L225,L440-L473,L552-L610`：DAG action binding 强制 capability/assignment refs。
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py:L95-L225,L300-L425`、`object_place.py:L40-L270,L340-L501`：同步 Action schema/校验。
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/fake_gateway.py:L14-L24,L285-L430`、`contracts/manipulation.capabilities.tool.yaml`、`skill.yaml`：完成 discovery/query wiring。
- `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`、`docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`、`changelog/2026-09_part3.md`：更新架构边界和五维审查。

### 五维审查 / Five-Dimension Review

架构集成、失败路径、权威边界、配置、可维护性均通过；atomic bimanual executor、真实 readiness/approval 与完整语义闭环仍未实现。

Architecture integration, failure paths, authority boundaries, configuration, and maintainability all pass; an atomic bimanual executor, real readiness/approval, and the complete semantic loop remain unimplemented.

### 验证 / Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src python -m pytest -p pytest_asyncio.plugin -q tests examples/forge-skills/pick-place-workflow/tests examples/forge-adapters/robotwin20/tests` → `669 passed, 1 skipped`
- Ruff、compileall、`git diff --check`：通过。

### Git 提交 / Git Commit

- Commit: `c60f58c`
- Branch: `feature/long-horizon-workflow`

## [v5.4.4] - 2026-09-05

完成 RoboTwin/Curobo 250 Hz 轨迹语义修复：route profile 现在显式声明并绑定 uniform time-dilation retiming，保持 1.0 rad/s PAOS 策略、不修改 Franka URDF 限幅，并保留 endpoint/dtype/速度证据。PAOS 环境安装 NumPy 2.5.2；adapter `228 passed, 1 skipped`，根仓库 `168 passed`。新的 v6 package 仍为 `pending_human_review`、`motion_authorized=false`；右臂八阶段 no-motion planner 通过，左臂不可用，未运行仿真动作、Gateway、Dora 或硬件。

Completed the RoboTwin/Curobo 250 Hz trajectory-semantics repair: the route profile now explicitly declares and binds uniform time-dilation retiming, preserving the 1.0 rad/s PAOS policy without changing Franka URDF limits, with endpoint/dtype/speed evidence retained. NumPy 2.5.2 is installed in the PAOS environment; adapter `228 passed, 1 skipped`, root `168 passed`. The new v6 package remains `pending_human_review` and `motion_authorized=false`; all eight right-arm no-motion planner phases pass while the left arm is unavailable, and no simulation motion, Gateway, Dora, or hardware was run.

### 文件变更详情 / Detailed changes

- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py:L422-L535,L542-L603,L829-L891`：增加 profile-owned retiming、dtype/endpoint/速度校验，并把 retiming evidence 写入 trajectory。
- `examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs.yaml:L40-L51`：声明 250 Hz、0.95 safety margin、20,000 sample 上限。
- `examples/forge-adapters/robotwin20/tests/test_simulation_probe.py:L11-L340`：增加 retiming 单位、端点、速度、dtype、预算和失败路径测试。
- `examples/forge-adapters/robotwin20/README.md:L441-L451`、`docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L881-L904`、`changelog/2026-09_part3.md:L186-L235`：更新 v6 evidence、五维审查和 readiness 门禁。

### 关键 Diff / Key Diff

```text
Before: Curobo samples above the profile-owned 1.0 rad/s policy were rejected, with no route passing continuous preflight.
After:  bounded profile-owned resampling at RoboTwin's 250 Hz cadence preserves endpoints and verifies retimed speed; v6 right-arm eight-phase planner preflight passes without simulator steps.
```

### 验证 / Validation

- `/home/yanxu/miniconda3/envs/paos/bin/python -m pytest ...` → adapter `228 passed, 1 skipped`; root `168 passed`; focused `62 passed`。
- `ruff`、`compileall`、`git diff --check` 通过。
- v6 preflight：`status=available`、右臂全阶段通过、左臂 `unavailable`、`robot_control_steps=0`、`simulator_steps=0`。
- 仍需 fresh human approval；未启动 simulation probe、Gateway、Dora、Action 或硬件。

### Git 提交 / Git Commit

- Commit: pending
- Branch: `feature/long-horizon-workflow`

## [v5.4.3] - 2026-09-05

完成 GraspGen depth 到 RoboTwin planner-frame 的 PAOS adapter 修复。`provider_T_contact_center`
先重建 canonical contact center，再由 Franka profile 派生 `robot_target_pose`；route、probe 和
approval 改用 `object_T_robot_target`，旧的混合 TCP 契约 fail-closed。新的 v3 package 保持
`pending_human_review` 与 `motion_authorized=false`。

Completed the PAOS adapter repair for GraspGen depth and the RoboTwin planner frame. The adapter first
reconstructs the canonical contact center with `provider_T_contact_center`, then derives `robot_target_pose`
from the Franka profile; route, probe, and approval now use `object_T_robot_target`, while mixed legacy TCP
contracts fail closed. The new v3 package remains `pending_human_review` with `motion_authorized=false`.

### 文件变更详情 / Detailed changes

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_adaptation.py:L193-L340`：分离 provider depth、canonical contact、RoboTwin standard target 和 planner round-trip。
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_generation.py:L194-L359`、`route_readiness.py:L241-L352`、`route_inputs.py:L1-L390`：升级 v3 route 与对象变换契约。
- `examples/forge-adapters/robotwin20/runtime/robotwin_simulation_probe_worker.py:L37-L270,L477-L730`、`scripts/approve_simulation_probe.py:L15-L145`：同步 v3 approval/artifact digest 绑定。
- `examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs.yaml`、`graspgen-tool-transform.json`、`README.md`：声明 profile 与使用边界。
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L900-L934`、`changelog/2026-09_part3.md:L125-L205`：记录诊断、证据和人工审批门禁。
- `tests/test_grasp_adaptation.py`、`test_route_inputs.py`、`test_route_generation.py`、`test_route_readiness.py`、`test_simulation_probe.py`、`test_approve_simulation_probe.py`：增加 frame round-trip、旧契约拒绝和 digest 绑定回归。

### 验证 / Validation

- 专项 `69 passed`；完整 adapter（正确加载 pick-place 与 pytest-asyncio，排除 NumPy provider collection）`212 passed, 2 skipped`。
- `ruff`、`compileall`、`git diff --check` 通过；RoboTwin20 Python 3.10 no-motion preflight 仅产生 preliminary evidence，`prepared_candidates=[]`、`collision=unavailable`、零 simulator step。
- 未启动 Gateway、Dora、Action、硬件或 simulation probe；v4 approval 不可复用，当前等待新的人工审批。

### Git 提交 / Git Commit

- Commit: pending
- Branch: `feature/long-horizon-workflow`

## [v5.2.1] - 2026-09-05

回写 v5.2.0 PAOS-first 操作规划重构实现提交 `514e044`。实现、十一项 Major 修复、五维验收、测试结果与
后续真实 readiness 门禁均未改变；`.codegraph/`、`.cursor/` 保持未跟踪且未提交。

Recorded v5.2.0 PAOS-first manipulation-planning implementation commit `514e044`. The implementation,
eleven Major fixes, five-dimension acceptance, test results, and subsequent real-readiness gate are unchanged;
`.codegraph/` and `.cursor/` remain untracked and uncommitted.

### 文件变更详情 / Detailed changes

- `changelog/2026-09_part2.md:L2996-L3037` 与 `changelog/2026-09_part3.md:L62-L101`：回写 v5.2.0
  implementation commit `514e044`、校正最终实现行号，并新增 v5.2.1 双语维护记录。
- `changelog/2026-09_part2.md:L2996-L3037` and `changelog/2026-09_part3.md:L62-L101`: record v5.2.0
  implementation commit `514e044`, correct final implementation line ranges, and add the bilingual v5.2.1 record.
- `CHANGELOG.md:L5-L60,L143-L147`：新增本条完整记录、回写 v5.2.0 commit，并滚动 Archive 边界；不修改运行代码。
- `CHANGELOG.md:L5-L60,L143-L147`: adds this complete record, records the v5.2.0 commit, and rolls the Archive boundary
  without changing runtime code.

### 关键 Diff / Key Diff

```text
Before: v5.2.0 implementation and validation were recorded with Commit: pending.
After:  implementation commit 514e044 and the pushed branch are explicitly recorded; code and evidence are unchanged.
```

### 验证 / Validation

- `514e044` 已推送到 `origin/feature/long-horizon-workflow`；`git diff --check` 和 UTF-8 日志显示检查通过。
- 本维护提交只包含日志；`.codegraph/`、`.cursor/` 未暂存。

### Git 提交 / Git Commit

- Implementation commit: `514e044`
- Branch: `feature/long-horizon-workflow`

## [v5.2.0] - 2026-09-05

完成 PAOS-first 操作规划收口与第二轮五维代码审查。Skill reducer 现在以 immutable DAG readiness 驱动；replan hint 绑定 node digest；RoboTwin route-readiness 明确适配到独立 route-evaluation contract，并拒绝 release TCP 变换或 phase gripper 语义不一致。PAOS task/revision/SQLite/Verifier/Gateway 权威边界和 no-motion 门禁保持不变。

Closed the PAOS-first manipulation-planning refactor and the second five-dimension code review. The Skill reducer is now driven by immutable DAG readiness; replan hints bind node digests; RoboTwin route-readiness explicitly adapts to the independent route-evaluation contract and rejects inconsistent release-TCP transforms or phase gripper semantics. PAOS task/revision/SQLite/Verifier/Gateway authority and no-motion gates remain unchanged.

### 文件变更详情 / Detailed changes

- `PhyAgentOS/forge/manipulation.py:L1-L314`：移除重叠生命周期并增加带 `node_digest` 的自校验 `ReplanSignal`。
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/long_horizon.py:L1-L639`：DAG-ready reducer、immutable references 和恢复状态校验。
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_readiness.py:L95-L591`：route semantic validation、完整 candidate evidence validation 与 `RouteReadinessEvaluationAdapter`。
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/arm_candidates.py:L1-L583`、`route_generation.py:L1-L335`、`perception_profile.py:L27-L184`：adapter/profile ownership、路线选择和 strict YAML。
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L843-L886`、`docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L829-L842`、`changelog/2026-09_part2.md:L2947-L3037`：记录十一个 Major 修复、五维验收和后续门禁。

### 验证 / Validation

- 组合 core/adapter/Skill（排除缺少 NumPy 的 GraspGen collection）→ `616 passed, 2 skipped`；core/adapter `355 passed, 2 skipped`；Skill `261 passed`；根仓库 `168 passed`；route generation/readiness/selection 专项 `36 passed`；开发者指南完整 DAG/route/evidence 专项 `69 passed`。
- `ruff check`、`compileall`、`git diff --check` → 通过。
- 未启动 Gateway、Dora、Action、硬件或仿真运动；真实 readiness、人工批准和抓取放置闭环仍未完成。
- Implementation commit: `514e044` on `feature/long-horizon-workflow`。

## [v5.1.0] - 2026-09-05 (withdrawn)

路线生成草案在实现审查中发现 PAOS 权威边界、frame/transform 语义和配置归属问题，未进入完成、提交或动作接入；未提交草案由 v5.2.0 PAOS-first 重构替代。

The route-generation draft was withdrawn after review found PAOS authority-boundary, frame/transform-semantics, and configuration-ownership issues. It was not completed, committed, or wired to motion; the uncommitted draft was superseded by the v5.2.0 PAOS-first refactor.

### 文件变更详情 / Detailed changes

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_generation.py`：草案保留为后续 adapter 语义参考，未作为独立完成版本发布。
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`、`docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`：记录撤销原因和边界。

### 验证 / Validation

- 未创建 motion wiring、Gateway/Dora invocation 或 readiness approval；该版本不作为完成实现计入。

## [v5.0.0] - 2026-09-05

新增 provider-neutral 语义 Manipulation DAG、双臂候选枚举、完整路线选择和失败重规划契约。公共层只
保存语义依赖、资源/证据绑定、不可变摘要和 no-motion 重规划信号；RoboTwin adapter 保存本体 profile、
候选×手臂展开和完整路线 evaluator/selector。现有 AgentTaskRecord、PlanRevision、SQLite、Runtime、
Evidence、Verifier、Gateway、Dora 和 Action 权威边界未改变，Hephaestus 仅作为设计参考。

Added provider-neutral semantic Manipulation DAG, dual-arm candidate enumeration, complete-route selection,
and failure-replanning contracts. The public layer stores semantic dependencies, resource/evidence bindings,
immutable digests, and no-motion replan signals; the RoboTwin adapter owns embodiment profiles, candidate×arm
expansion, and complete-route evaluation/selection. Existing AgentTaskRecord, PlanRevision, SQLite, Runtime,
Evidence, Verifier, Gateway, Dora, and Action authority boundaries are unchanged; Hephaestus is design reference only.

### 文件变更详情 / Detailed changes

- `PhyAgentOS/forge/manipulation.py`：新增严格 Pydantic DAG/Intent/RouteFailure/Replan contracts；所有运动授权固定为 `false`。
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/arm_candidates.py`：新增 profile-owned candidate×arm enumeration、完整路线 selector、独立 evaluator/selection schema 和 fail-closed validation。
- `examples/forge-adapters/robotwin20/profiles/robotwin20/manipulation-planning.yaml`：新增 Franka dual-independent profile 与确定性评分策略。
- `docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`、`docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`、`docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`：记录 PAOS 扩展边界、Hephaestus clean-room 参考、开发规则和五维审查。
- `tests/test_manipulation.py`、`examples/forge-adapters/robotwin20/tests/test_arm_candidates.py`：覆盖 DAG、绑定、拓扑、重规划预算、候选枚举、确定性选择和篡改失败。

### 验证 / Validation

- 专项契约：`16 passed`。
- PAOS/RoboTwin adapter 组合套件：`338 passed, 2 skipped`（跳过缺少 NumPy 的 GraspGen provider collection）。
- 根仓库套件：`171 passed`。
- `ruff`、`compileall`、`git diff --check`：通过。
- 未启动 Gateway、Dora、Action、硬件或 simulation motion；真实 readiness 仍受上一阶段 `not_approved_for_readiness_or_motion_wiring` 门禁约束。
- Git commit: `d09cca5` on `feature/long-horizon-workflow`.

## [v4.12.2] - 2026-09-05

回写 v4.12.1 独立 RoboTwin simulation-probe 实现提交 `f88778a`。实现、真实负证据、五维验收结论与
后续执行门禁均未改变；`.codegraph/`、`.cursor/` 仍为未跟踪的用户目录，未纳入提交。

Recorded the v4.12.1 independent RoboTwin simulation-probe implementation commit `f88778a`. The
implementation, real negative evidence, five-dimension acceptance conclusions, and next execution gate are
unchanged; the user-owned `.codegraph/` and `.cursor/` directories remain untracked and uncommitted.

### 文件变更详情 / Detailed changes

- `changelog/2026-09_part2.md:L310-L403`：新增 v4.12.2 双语维护记录，并将 v4.12.1 的
  `Commit: pending` 更新为 `f88778a`。
- `changelog/2026-09_part2.md:L310-L403`: adds the bilingual v4.12.2 maintenance record and replaces the
  v4.12.1 `Commit: pending` marker with `f88778a`.
- `CHANGELOG.md:L5-L95`：同步根日志最近记录及 v4.12.1 implementation commit；未修改运行代码。
- `CHANGELOG.md:L5-L95`: synchronizes the root recent entry and v4.12.1 implementation commit without
  changing runtime code.

### 关键 Diff / Key Diff

```text
Before: v4.12.1 implementation and validation were recorded with Commit: pending.
After:  implementation commit f88778a and pushed branch are explicitly recorded; code and evidence are unchanged.
```

### 验证 / Validation

- `f88778a` 同时为本地 `HEAD` 和 `origin/feature/long-horizon-workflow`；日志 UTF-8 显示正常。
- `git diff --check` 通过；仅两份日志进入定向提交，未跟踪用户目录未暂存。

### Git 提交 / Git Commit

- Implementation commit: `f88778a`
- Branch: `feature/long-horizon-workflow`

## Archive

- [2026-09 part 4](changelog/2026-09_part4.md)
- [2026-09 part 3](changelog/2026-09_part3.md)
- [2026-09 part 2](changelog/2026-09_part2.md)
- [2026-09](changelog/2026-09.md)

## [v4.12.1] - 2026-09-05

收紧独立 RoboTwin simulation probe 的真实性门禁：为 block actor 分配唯一身份，首步前保存 before
snapshot，校验实际 backend revision，并要求目标实体在 lift 阶段真实升高至少 1 cm。修复 client 将
“世界曾变化”错误等同于“仍需 reconciliation”的协议问题，以及启动时双 reset 导致的 revision 漂移。

最终复审进一步实体化并执行 joint/stop policy，将 calibration 与 policy 内容摘要绑定进 approval，校验
runtime limit 的有限有序性和规划/观测速度，并将 worker 固定为 single-use；planning/finalization 失败
统一保存不可变诊断并进入 reset 恢复。scene reset 现在也被如实计为仿真世界变化。

Tightened the independent RoboTwin simulation probe's truthfulness gates: assign unique block identities,
persist the before snapshot before the first step, verify the actual backend revision, and require the target
entity to rise by at least 1 cm during lift. Fixed the client protocol conflating prior world change with pending
reconciliation and removed the startup double-reset revision drift.

The final review also materializes and enforces joint/stop policies, binds calibration and policy digests into the
approval, validates finite ordered runtime limits and planned/observed speeds, makes the worker single-use, and
routes planning/finalization failures through immutable diagnostics and reset recovery. Scene reset is now
truthfully counted as a simulation-world change.

### 文件变更详情 / Detailed changes

- `robotwin_simulation_probe_worker.py:L110-L173,L295-L397,L514-L1225`：绑定审批输入摘要，执行实体化
  policy、runtime/速度/真实 lift 门禁，并统一 finalization/failure/reset；worker 固定 single-use。
- `robotwin_simulation_probe_worker.py:L110-L173,L295-L397,L514-L1225`: binds approved input digests,
  enforces materialized policies plus runtime/speed/real-lift gates, unifies finalization/failure/reset, and makes
  the worker single-use.
- `simulation_probe.py:L41-L108` 与 `test_simulation_probe.py:L1-L656`：收紧 client failure/reconciliation
  contract，并覆盖摘要篡改、limits、失败恢复与 revision 生命周期。
- `simulation_probe.py:L41-L108` and `test_simulation_probe.py:L1-L656`: tighten the client
  failure/reconciliation contract and cover digest tampering, limits, recovery, and revision lifecycle.
- `PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L737-L763`、`STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L773-L804`
  与 adapter README `L395-L428`：记录最终真实负证据、五维验收和下一门禁。
- The diagnosis `L737-L763`, implementation review `L773-L804`, and adapter README `L395-L428` record the
  final real negative evidence, five-dimension acceptance, and next gate.

### 关键 Diff / Key Diff

```text
Before: approval bound policy references but not their bytes; final evidence failures could escape recovery;
        scene reset could be reported as no world change.
After:  approval binds calibration/joint/stop SHA-256; all post-reset failures persist diagnostics and reset;
        scene reset is a world change, while negative evidence never becomes readiness.
```

### Validation

- Latest real run: `paos-simulation-probe-20260905T020000p0800-policy-v6` returned `unavailable` before a robot
  step because the left arm failed planning and the right arm exceeded the approved `1.0 rad/s` limit; the scene
  reset was recorded as world change, recovery reset completed, and readiness/motion wiring was not approved.
- Focused simulation-probe conformance: `21 passed`; adapter subset: `158 passed, 2 skipped`; repository:
  `164 passed`; ruff, compileall, and diff-check passed.
- Gateway, Dora, Action executor, and hardware remain disconnected. Commit: `f88778a` on
  `feature/long-horizon-workflow`.

## [v4.11.0] - 2026-09-04

新增独立 route-evidence verifier：消费外部授权 simulation probe 产物，校验附着 geometry、planner route、六项 readiness scope、before/after snapshot、semantic verdict、producer identity 和 SHA-256；verifier 与 worker 始终保持 no-motion，不启动 RoboTwin、Dora、Gateway 或硬件。

Added an independent route-evidence verifier that consumes artifacts from an authorized external simulation probe and validates attached geometry, planner route, six readiness scopes, before/after snapshots, semantic verdict, producer identity, and SHA-256. The verifier and worker remain no-motion and never start RoboTwin, Dora, Gateway, or hardware.

### Detailed changes

- Added `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_evidence.py`, `runtime/robotwin_route_evidence_worker.py`, `profiles/robotwin20/route-evidence.yaml`, and `tests/test_route_evidence.py`.
- Added strict producer/probe execution binding so external world change is explicit and cannot be confused with verifier no-motion.
- Updated PAOS diagnosis, implementation review, and adapter README with the five-dimension acceptance and remaining motion gate.

### Validation

- Verifier focus: `10 passed`; combined route/readiness/action focus: `80 passed`; repository: `164 passed`.
- Ruff, compileall, and `git diff --check` passed. No RoboTwin `play_once`, Dora, Gateway motion, or hardware was started.
- Commit: `3d72b98` on `feature/long-horizon-workflow`.

## [v4.10.0] - 2026-09-05

新增 simulation route-readiness contract、profile-owned bounded JSONL worker 和外部配置。请求绑定附着物体 geometry/digest、八阶段路线、waypoint frame/速度限幅、workspace 与 stop policy；当前 worker 对真实 planner、附着碰撞、接触动力学、stop controller 和语义验收明确返回 unavailable，保持 no-motion。

Added the simulation route-readiness contract, profile-owned bounded JSONL worker, and external configuration. Requests bind attached-object geometry/digests, eight route phases, waypoint frames/speed limits, workspace, and stop policy; the current worker explicitly returns unavailable for the real planner, attached collision, contact dynamics, stop controller, and semantic verification while remaining no-motion.

### Detailed changes

- Added `examples/forge-adapters/robotwin20/src/robotwin20_adapter/route_readiness.py:L1-L344`, `runtime/robotwin_route_readiness_worker.py:L1-L99`, `profiles/robotwin20/route-readiness.yaml:L1-L18`, and `tests/test_route_readiness.py:L1-L166`.
- Exported route readiness APIs from `robotwin20_adapter/__init__.py:L67-L78,L185-L193`.
- Updated architecture diagnosis, implementation review, adapter README, and monthly changelog.

### Validation

- Route readiness: `9 passed`; combined readiness/action/Gateway focus: `81 passed`; repository: `164 passed`.
- Ruff, compileall, and `git diff --check` passed. No RoboTwin `play_once`, Dora, Gateway motion executor, or hardware was started.
- Git commit: `ada59b5` on `feature/long-horizon-workflow`.

## [v4.9.0] - 2026-09-05

新增独立的 simulation-motion authorization profile/schema。`simulation_authorization.py` 严格绑定 runtime/evidence manifest digest、任务/场景/Franka 本体身份、四类 readiness scope、审批记录、停止策略和 before/after semantic snapshot；默认配置为 disabled/no-motion，不启动任何 worker 或动作。

Added an isolated simulation-motion authorization profile/schema. `simulation_authorization.py` binds runtime/evidence-manifest digests, task/scene/Franka identity, four readiness scopes, approval records, stop policy, and before/after semantic snapshots; the checked-in profile is disabled/no-motion and starts no worker or action.

### Detailed changes

- Added `examples/forge-adapters/robotwin20/src/robotwin20_adapter/simulation_authorization.py:L1-L443`, `profiles/robotwin20/simulation-motion.yaml:L1-L47`, and `tests/test_simulation_authorization.py:L1-L238`.
- Exported the schema/profile loader from `robotwin20_adapter/__init__.py:L55-L64,L143-L149`.
- Updated architecture diagnosis, five-dimension review, adapter README, and `changelog/2026-09_part2.md`.

### Validation

- Simulation profile conformance: `10 passed`; readiness/action/Gateway focused suite: `81 passed`; repository: `164 passed`.
- Ruff, compileall, and `git diff --check` passed. No RoboTwin `play_once`, Dora, Gateway motion executor, or hardware was started.
- Git commit: `0447dab` on `feature/long-horizon-workflow`.

## [v4.8.0] - 2026-09-05

将 Action 生命周期改为 invocation-first：先创建 invocation/attempt，再启动 deferred provider；保留失败、取消、超时和 unknown 语义。

Changed the Action lifecycle to invocation-first: allocate invocation/attempt before starting deferred providers while preserving failure, cancel, timeout, and unknown semantics.

### Detailed changes

- Updated `PhyAgentOS/forge/capability_runtime/ports.py:L17-L23`, `runtime.py:L204-L270`, and pick-place endpoints/gateway at `object_acquire.py:L51-L60,L410-L488`, `object_place.py:L56-L65,L487-L565`, `fake_gateway.py:L272-L307,L494-L795`.
- Added provider identity/start-failure/deferred cancel-stop conformance and documented the five-dimension review.

### Validation

- Focused Action/Gateway tests: `58 passed`; repository: `164 passed`; pick-place suite: `256 passed`.
- No simulation motion, Dora, or hardware execution was enabled.

## [v4.7.14] - 2026-09-05

记录仿真 motion executor 的前置阻断，修订顺序为 invocation-first、独立 simulation authorization、完整 readiness、before/after snapshot 与语义验收后再运动。

Recorded simulation motion-executor blockers and revised the order to invocation-first, isolated simulation authorization, complete readiness, before/after snapshots, and semantic verification before motion.

### Detailed changes

- Updated `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L585-L630` and `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L606-L628`.
- Verified no-motion Action/Gateway `52 passed` and repository `161 passed`; no RoboTwin motion stepping.

## [v4.7.10] - 2026-09-05

回写 v4.7.9 Action readiness gate 实现提交哈希 `83c74ff`；未修改运行逻辑，用户目录 `.codegraph/` 与 `.cursor/` 未纳入提交。

Recorded the v4.7.9 Action readiness-gate implementation commit hash `83c74ff`; runtime logic was unchanged, and user directories `.codegraph/` and `.cursor/` were excluded from the commit.

### Detailed changes

- Updated `changelog/2026-09_part2.md` with the completed maintenance record and exact implementation commit.
- Kept user-owned `.codegraph/` and `.cursor/` directories out of the change.

### Validation

- Verified the working tree contains only the intended changelog/index edits plus pre-existing untracked user directories.
- Git commit: `e6883f8` on `feature/long-horizon-workflow`.

## [v4.7.9] - 2026-09-05

接入已人工审核 readiness evidence 的 Action admission no-motion gate。`object.acquire`/
`object.place` 在创建 Gateway invocation 前校验 manifest/review/evidence SHA-256、同一
scene/candidate-set/frame/calibration、candidate/entity、worker/embodiment identity、三项
readiness checks 和 `motion_authorized=false`；Fake Gateway action context 显式返回 no-motion，
并拒绝 provider 报告的 `world_change_started=true`。manifest/review/artifact 路径由
`profiles/robotwin20/action-readiness.yaml` 和环境变量注入。

Added a no-motion Action-admission gate backed by manually reviewed readiness evidence. Before
allocating a Gateway invocation, `object.acquire`/`object.place` validate manifest/review/evidence
SHA-256, scene/candidate-set/frame/calibration, candidate/entity, worker/embodiment identity, all
readiness checks, and `motion_authorized=false`. Fake Gateway Action contexts explicitly expose
no-motion and reject providers reporting `world_change_started=true`. Manifest/review/artifact
paths are injected through `profiles/robotwin20/action-readiness.yaml` and environment variables.

### Detailed changes

- Added `examples/forge-adapters/robotwin20/src/robotwin20_adapter/action_readiness.py:L1-L274` and `profiles/robotwin20/action-readiness.yaml:L1-L4`.
- Added `examples/forge-adapters/robotwin20/tests/test_action_readiness_gate.py:L1-L273`.
- Updated Skill Action endpoints and Fake Gateway at `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py:L51-L60,L410-L488`, `object_place.py:L56-L65,L487-L565`, and `fake_gateway.py:L261-L297,L375-L410`.
- Updated architecture diagnosis, five-dimension review, and adapter README.

### Validation

- Focused Action/Gateway/readiness conformance: `52 passed`.
- Ruff and `git diff --check` passed; real Franka manifest gate loaded all `50` evidence candidates.
- No RoboTwin `play_once`, Dora, Action stepping, or hardware motion was invoked.

## [v4.7.6] - 2026-09-04

完成 Franka `blocks_ranking_rgb` 的独立 readiness worker 证据闭环，并将 live worker 接入 adapter 的 bounded JSONL profile seam。相同 `blocks_ranking_rgb-0-1/head_camera` 上生成 12 个 geometry/point-cloud derived artifacts，GraspGen funnel 为 `72→72→71→71`，Curobo no-motion worker 为 `50/71` prepared；50 个 evidence ref 唯一且全部绑定 request、candidate-set、observation、scene、frame、calibration、worker 和 profile digest。

Completed the independent readiness-worker evidence loop for Franka `blocks_ranking_rgb` and wired the live worker through the adapter's bounded JSONL profile seam. On the same `blocks_ranking_rgb-0-1/head_camera`, 12 geometry/point-cloud derived artifacts were verified, GraspGen produced funnel `72→72→71→71`, and the Curobo no-motion worker prepared `50/71`; all 50 evidence refs are unique and bound to request, candidate-set, observation, scene, frame, calibration, worker, and profile digest.

### Detailed changes

- Added `runtime/robotwin_readiness_worker.py` live schema, strict freshness/provenance/pose checks, and per-evidence no-motion bindings.
- Added `profiles/robotwin20/readiness-live.yaml`, `ReadinessLiveClient`, and `build_live_readiness_evaluator`; added schema/motion-drift tests.
- Updated architecture diagnosis, implementation review, and adapter README. Manual review authorizes only the next no-motion Action/Gateway review; no Action, Dora, attached-object transport, or hardware motion is authorized.

### Validation

- Adapter readiness/backend tests: `50 passed`; repository with explicit async plugin: `161 passed`.
- External live profile → worker → PAOS `manipulation.prepare`: `available`, `50 prepared`, all checks `pass`, `motion_authorized=false`.
- Ruff, compileall, and `git diff --check` passed. Evidence manifest: `b0cd2298b84bbc4be0470fb66da4b543928836dd026433ae7e0861cb691fec79`.

## [v4.7.4] - 2026-09-04

完成 Franka `blocks_ranking_rgb` readiness 输入审计：capture 缺少同一 scene revision 的 geometry/candidate，现有 GraspGen 结果不可跨场景复用，因此安全记录 `unavailable`，未启动 IK/碰撞或动作链路。

Completed the Franka `blocks_ranking_rgb` readiness-input audit: the capture lacks same-revision geometry/candidates and the existing GraspGen result cannot be reused across scenes, so the gate safely records `unavailable` without starting IK/collision or motion paths.

详细记录见 [FRANKA_READINESS_INPUT_AUDIT_20260904](docs/forge/FRANKA_READINESS_INPUT_AUDIT_20260904.md)。

## [v4.7.5] - 2026-09-04

回写 v4.7.4 Franka readiness 输入审计提交哈希 `ee2144e`；实现和执行顺序不变。

Recorded the v4.7.4 Franka readiness-input audit commit hash `ee2144e`; implementation and execution order are unchanged.

## [v4.7.1] - 2026-09-04

回写 v4.7.0 本体 profile 与 readiness identity 实现提交哈希 `30bf3ed`；没有修改实现行为。

Recorded the v4.7.0 embodiment-profile and readiness-identity implementation commit hash `30bf3ed`; implementation behavior is unchanged.

## [v4.7.2] - 2026-09-04

readiness profile 现在校验绑定的 runtime profile 文件及 SHA-256，防止 benchmark/本体配置漂移后复用旧 evidence。

The readiness profile now verifies its bound runtime-profile file and SHA-256, preventing stale evidence reuse after benchmark or embodiment drift.

## [v4.7.0] - 2026-09-04

完成 RoboTwin adapter 的可替换 embodiment profile 与 readiness 身份绑定。
Franka `blocks_ranking_rgb`（`[franka-panda, franka-panda, 0.8]`）已通过实际
no-motion preflight/scene capture；未接入 Action、Gateway、Dora 或硬件运动。

Completed replaceable RoboTwin embodiment profiles and readiness identity
bindings. Franka `blocks_ranking_rgb` (`[franka-panda, franka-panda, 0.8]`)
passed real no-motion preflight/scene capture; Action, Gateway, Dora, and
hardware motion remain disconnected.

### Detailed changes

- Backend/preflight now validate native dual-arm versus two-single-arm topology and load `franka-blocks-ranking.yaml`.
- Readiness fixture, evidence manifest, worker response, and immutable replay artifact now require matching robot/gripper/topology/planner/profile-digest bindings.
- Updated architecture diagnosis, execution order, and adapter replacement guidance.

### Validation

- Adapter conformance: `71 passed, 1 skipped`; focused backend/preflight/readiness: `37 passed`; repository: `161 passed` with `pytest_asyncio`.
- RoboTwin20 Franka pair preflight: `ready=true`; no-motion capture produced RGB/depth/state/calibration.
- Ruff, compileall, and `git diff --check` passed.

## [v4.5.4] - 2026-09-05

回写 v4.5.3 GraspGen 验收日志维护提交哈希 `36d940d`，并完成 v4.5.4 索引提交 `0cfcd56`；没有修改实现、测试或执行顺序。

Recorded the v4.5.3 GraspGen acceptance-log maintenance commit hash `36d940d` and completed the v4.5.4 index commit `0cfcd56`; implementation, tests, and execution order are unchanged.

## [v4.5.1] - 2026-09-05

回写 v4.5.0 provider no-motion 真实链路验收提交哈希 `9a2af2e`；没有修改实现、测试或执行顺序。

Recorded the v4.5.0 provider no-motion live-chain acceptance commit hash `9a2af2e`; implementation, tests, and execution order are unchanged.

## [v4.5.2] - 2026-09-05

修复 GraspGen worker 的 JSONL stdout conformance，并通过真实 `entity://red-rectangular-block-1` 点云完成 no-motion `grasp.propose`，返回 24 个 provider-neutral candidates；未进入 readiness、Action 或运动。

Fixed GraspGen worker JSONL stdout conformance and completed a no-motion `grasp.propose` on the real `entity://red-rectangular-block-1` point cloud, returning 24 provider-neutral candidates; readiness, Action, and motion remain gated.

### Validation

- Adapter: `104 passed`; repository: `161 passed`; pick-place: `256 passed`; Ruff and compileall passed.
- Evidence manifest: `a7627a6d8583bf4da502dfe1deaf8c3ec1e978f8f274ede545446614f43ae336`.

## [v4.5.3] - 2026-09-05

回写 v4.5.2 GraspGen live provider seam 实现提交哈希 `aff62a5`；没有修改实现、测试或执行顺序。

Recorded the v4.5.2 GraspGen live provider seam implementation commit hash `aff62a5`; implementation, tests, and execution order are unchanged.

## [v4.5.0] - 2026-09-05

完成已接入 provider 的真实 RoboTwin no-motion 链路验收，并修复 runtime stdout 可审计性；按架构集成、失败路径、权威边界、配置、可维护性五维复审无 Blocker/Major。当前仍未进入 Action/Gateway、Dora 或机器人运动。

Completed the live RoboTwin no-motion chain review for currently integrated providers and fixed runtime stdout auditability; the five-dimension review found no Blocker/Major. Action/Gateway, Dora, and robot motion remain deferred.

### Detailed changes

- `examples/forge-adapters/robotwin20/runtime/robotwin_backend.py:L18,L384-L412`: redirect simulator/runtime stdout noise to stderr and emit one machine-readable JSON document on stdout.
- `examples/forge-adapters/robotwin20/tests/test_robotwin_backend_contract.py:L79-L118`: add stdout/stderr contract coverage.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L462-L483`, `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L509-L522`, `examples/forge-adapters/robotwin20/README.md:L227-L236`: record the run, intermediate perception artifacts, unavailable providers, motion flags, and final manifest digest.

### Validation

- Isolated adapter tests with explicit async plugin and dependency paths: `103 passed`; repository: `161 passed`; pick-place with required path and async plugin: `256 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Run manifest: `/home/yanxu/robotwin20-runtime/artifacts/paos-real-chain-20260905T0020Z/run_manifest.json`, SHA-256 `da7a81bd2efccbf70312428a3adeef10babe2d465734f63f7c90444297389b46`; all motion flags are `false`.
- GraspGen (`GRASPGEN_PYTHON`) and readiness (`READINESS_FIXTURE`) are unavailable; no `object.acquire`/`object.place` was attempted.

## [v4.4.0] - 2026-09-04

固化独立 readiness worker 的 no-motion projection 为 adapter-local、不可变 canonical replay artifact；保持人工审核门禁，不进入真实 Action/Gateway wiring。

Persisted independently validated readiness worker no-motion projections as immutable adapter-local canonical replay artifacts; retained the manual-review gate and did not enter real Action/Gateway wiring.

### Validation

- Readiness/replay/process: `25 passed`; repository: `161 passed`; dependency-free adapter subset: `16 passed`; pick-place: `256 passed`.
- Ruff, compileall, and `git diff --check` passed. Artifact is not a PAOS EvidenceBundle or motion authorization.

## [v4.4.1] - 2026-09-04

回写 v4.4.0 readiness replay artifact 实现提交哈希 `a2f972a`；没有修改实现、测试或执行顺序。

Recorded the v4.4.0 readiness replay artifact implementation commit hash `a2f972a`; implementation, tests, and execution order were unchanged.

## [v4.3.4] - 2026-09-04

回写 v4.3.3 readiness calibration identity 修复提交哈希 `20c6ad6`；没有修改实现、测试或执行顺序。

Recorded the v4.3.3 readiness calibration-identity fix commit hash `20c6ad6`; implementation, tests, and execution order were unchanged.

## [v4.3.3] - 2026-09-04

修复 readiness replay 中 calibration identity 未完整绑定的问题；fixture、request、manifest 现在三方一致校验。

Fixed incomplete calibration identity binding in readiness replay; fixture, request, and manifest now require three-way consistency.

### Validation

- Readiness/replay/process: `34 passed`; dependency-free adapter subset: `44 passed`.
- Ruff, compileall, and `git diff --check` passed.

## [v4.3.2] - 2026-09-04

回写 v4.3.1 日志维护提交哈希 `8833784`；没有修改实现、测试或执行顺序。

Recorded the v4.3.1 changelog-maintenance commit hash `8833784`; implementation, tests, and execution order were unchanged.

## [v4.3.1] - 2026-09-04

回写 v4.3.0 readiness evidence manifest 实现提交哈希 `23364de`；没有修改实现、测试或执行顺序。

Recorded the v4.3.0 readiness evidence-manifest implementation commit hash `23364de`; implementation, tests, and execution order were unchanged.

## [v4.3.0] - 2026-09-04

完成 readiness replay evidence manifest 的 no-motion 绑定校验，并按架构集成、失败路径、权威边界、配置、可维护性五个维度复审通过。

Implemented no-motion binding validation for the readiness replay evidence manifest and passed review across architecture integration, failure paths, authority boundaries, configuration, and maintainability.

### Detailed changes

- `examples/forge-adapters/robotwin20/runtime/readiness_replay_worker.py`: strict hash-pinned evidence manifest validation for candidate-set, calibration, source, and timezone-aware capture timestamps.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/readiness_profile.py`: external manifest path, permission, digest, and duplicate-argument gates.
- `examples/forge-adapters/robotwin20/tests/test_readiness_replay.py`, `profiles/robotwin20/readiness-replay.yaml`: manifest conformance and profile configuration.

### Validation

- Readiness/replay/process tests: `34 passed`; dependency-free adapter subset: `44 passed`; repository: `161 passed`; pick-place: `256 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No real IK, collision engine, Action, Gateway, Dora, hardware, or motion path was started.

## [v4.2.1] - 2026-09-04

回写 v4.2.0 readiness replay 实现提交哈希 `103db24`；没有修改实现、测试或执行顺序。

Recorded the v4.2.0 readiness replay implementation commit hash `103db24`; implementation, tests, and execution order were unchanged.

## [v4.2.0] - 2026-09-04

完成 readiness evidence replay worker/profile 的 no-motion conformance，并按五个维度复审通过；保持 PAOS projection 和动作权限边界不变。

Implemented no-motion conformance for the readiness evidence replay worker/profile and passed the five-dimension review; PAOS projection and motion-authority boundaries remain unchanged.

### Detailed changes

- `examples/forge-adapters/robotwin20/runtime/readiness_replay_worker.py`: hash-pinned fixture replay with complete case identity matching and no-motion output.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/readiness_profile.py`: fixture digest/path/permission gates and worker identity validation through the existing JSONL process boundary.
- Existing `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py` mapping normalization remains the final PAOS owner.
- `examples/forge-adapters/robotwin20/tests/test_readiness_replay.py`, `profiles/robotwin20/readiness-replay.yaml`: replay and profile conformance coverage.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/readiness.py`: expose explicit readiness adapter teardown for process-backed evaluators.

### Validation

- Replay/readiness/process tests: `28 passed`; dependency-free adapter subset: `38 passed`; repository: `161 passed`; pick-place: `256 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Replay is protocol evidence only; no real IK, collision engine, Action, Gateway, Dora, hardware, or motion path was started.
- Full RoboTwin20 adapter collection remains environment-limited by optional `numpy` and missing pick-place source-path injection; this does not invalidate the dependency-free conformance subset.

## [v4.1.0] - 2026-09-04

完成 RoboTwin20 独立 `ReadinessEvaluator` conformance，并按五个维度复审通过；保持 provider-neutral、dry-run/no-motion。Hephaestus 仅作 clean-room 语义参考，未接入运行时代码。

Implemented the independent RoboTwin20 `ReadinessEvaluator` conformance and passed the five-dimension review; kept provider-neutral, dry-run/no-motion behavior. Hephaestus was used only as a clean-room semantic reference, with no runtime code integrated.

### Detailed changes

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/readiness.py`: strict request/result binding, evidence validation, evaluator isolation, and fail-closed adapter boundary.
- `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py`: strict normalization of adapter mappings while preserving PAOS ownership of projection and `motion_authorized=false`.
- `examples/forge-adapters/robotwin20/tests/test_readiness.py`: readiness and PAOS integration conformance coverage.
- `examples/forge-adapters/robotwin20/README.md`, `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`: updated implementation order and reference boundary.

### Validation

- Readiness tests: `14 passed`; dependency-free adapter subset: `30 passed`; repository: `161 passed`; pick-place: `256 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No real IK/collision engine, Action, Gateway, Dora, hardware, or motion path was started.

## [v4.1.1] - 2026-09-04

回写 v4.1.0 实现提交哈希；没有修改实现、测试或执行顺序。

Recorded the v4.1.0 implementation commit hash; implementation, tests, and execution order are unchanged.

- Commit: `4b6ab2b`
- Branch: `feature/long-horizon-workflow`

## [v4.1.2] - 2026-09-04

修正 readiness conformance 日志索引中的提交哈希说明；没有修改实现、测试或执行顺序。

Corrected the readiness conformance changelog index's commit-hash note; implementation, tests, and execution order are unchanged.

- Correct maintenance commit for v4.1.1: `68bacaf`
- Branch: `feature/long-horizon-workflow`

## [v4.0.0] - 2026-09-04

完成 `manipulation.prepare` candidate consumer 的协议加固，并按架构集成、失败路径、权威边界、配置、可维护性五个维度复审通过；保持 Query/no-motion。Hephaestus 仅作为 clean-room 行为参考，未接入其运行时代码。

Hardened the `manipulation.prepare` candidate consumer and passed review across architecture integration, failure paths, authority boundaries, configuration, and maintainability; kept Query/no-motion. Hephaestus was used only as a clean-room behavioral reference, with no runtime code integrated.

### Detailed changes

- `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py`: strict observation/candidate-set identity, duplicate prepared-candidate rejection, provider request isolation, and fail-closed readiness projection.
- `examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py`: revision/frame drift, provider mutation, and duplicate-candidate regression coverage.
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`: implementation status, five-dimension review, execution order, and Hephaestus reference boundary.

### Validation

- Manipulation-prepare tests: `60 passed`; repository tests: `161 passed`; pick-place tests: `256 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No real IK, collision engine, Gateway, Dora, Action executor, hardware, or motion path was started.

## [v4.0.1] - 2026-09-04

回写 v4.0.0 实现提交哈希；没有修改实现、测试或执行顺序。

Recorded the v4.0.0 implementation commit hash; implementation, tests, and execution order are unchanged.

- Commit: `385eb7a`
- Branch: `feature/long-horizon-workflow`

## [v3.10.8] - 2026-09-04

加固 `scene.understand` 对 `scene.observe` identity 与 artifact lineage 的消费边界，并按架构集成、失败路径、权威边界、配置、可维护性五个维度复审通过；保持 Query/no-motion。

Hardened `scene.understand` consumption of `scene.observe` identity and artifact lineage, passing review across architecture integration, failure paths, authority boundaries, configuration, and maintainability; kept Query/no-motion.

### Detailed changes

- `PhyAgentOS/forge/capability_runtime/understanding.py`: strict observation identity, unique artifact/provenance binding, frame consistency, and provider-request isolation.
- `examples/forge-skills/pick-place-workflow/tests/test_scene_understand.py`: binding, provenance, frame-drift, and mutation regression coverage.
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`: stage status and five-dimension review.

### Validation

- Scene-understand tests: `21 passed`; repository tests: `161 passed`; pick-place tests: `250 passed`.
- RoboTwin provider tests: `7 passed, 1 skipped`; Ruff, compileall, and `git diff --check` passed.
- Real model, Gateway/Dora, Action executor, and hardware remain deferred.
- Commit: `2ba3a21` on `feature/long-horizon-workflow`.

## [v3.11.0] - 2026-09-04

加固 `grasp.propose` 对 `scene.understand` geometry artifact 的消费，并按五个维度复审通过；保持 Query/no-motion。

Hardened `grasp.propose` consumption of `scene.understand` geometry artifacts and passed the five-dimension review; kept Query/no-motion.

### Detailed changes

- `PhyAgentOS/forge/capability_runtime/grasp_proposal.py`: strict identity/provenance validation and isolated provider request.
- `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py`: binding, provenance, and mutation regressions.
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`: stage status and review.

### Validation

- Grasp proposal tests: `61 passed`; repository: `161 passed`; pick-place: `253 passed`.
- Adapter GraspGen live tests remain blocked by missing optional `numpy`; no live checkpoint claim.
- Commit: `88267b4` on `feature/long-horizon-workflow`.

## [v3.10.2] - 2026-09-04

完成 EnvironmentAdapter/provider-neutral `scene.observe` 核心 seam，并按架构集成、失败路径、权威边界、配置、可维护性五个维度复审通过；保持 no-motion，不连接真实机器人、Dora 或硬件。

Completed the EnvironmentAdapter/provider-neutral `scene.observe` core seam and passed review across architecture integration, failure paths, authority boundaries, configuration, and maintainability; kept no-motion with no real robot, Dora, or hardware connected.

### Detailed changes

- `PhyAgentOS/forge/capability_runtime/observation.py`: explicit provider-neutral ToolSpec, strict observation projection, injected clock, and fail-closed provider/sensor errors.
- `PhyAgentOS/forge/capability_runtime/__init__.py`, `examples/forge-adapters/robotwin20/src/robotwin20_adapter/adapter.py`: core export and sanitized adapter boundary.
- `tests/test_environment_adapter_observation.py`: observation contract, failure, and explicit registration coverage.
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`, `docs/forge/ROBOTWIN_ADAPTER_REFACTOR_DIAGNOSIS.md`: stage status and five-dimension review.

### Validation

- Repository tests: `161 passed`; observation seam: `10 passed`; RoboTwin dependency-free subset: `16 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Full RoboTwin runtime, real Gateway/Dora, geometry consumer, Action executor, and hardware remain deferred.
- Commit: `c46a35a` on `feature/long-horizon-workflow`.
- Follow-up adapter failure-path fix: `69c00d7` on `feature/long-horizon-workflow`.

## [v3.10.0] - 2026-09-04

完成 provider-neutral 抓取放置协议级证据闭环，并按架构集成、失败路径、权威边界、配置、可维护性五个维度复审通过；不连接真实 Action executor、Dora、机器人或硬件。

Completed the provider-neutral protocol-level pick-and-place evidence closure and passed review across architecture integration, failure paths, authority boundaries, configuration, and maintainability; no real Action executor, Dora, robot, or hardware connected.

### Detailed changes

- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/long_horizon.py:L24-L27,L78-L89,L194-L231,L301-L316`: terminal-response ref extraction, strict acquire identity equality, destination schema, and post-release evidence gate.
- `examples/forge-skills/pick-place-workflow/tests/test_long_horizon.py:L59-L70,L123-L145`: binding-drift, evidence-missing, and terminal-response replay coverage.
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`: stage status and five-dimension review.

### Validation

- Repository tests: `151 passed`; pick-place tests: `245 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Real physical execution and autonomous-evolution promotion remain deferred.
- Commit: `a847cd7` on `feature/long-horizon-workflow`.

## [v3.9.0] - 2026-09-04

完成 Gateway/Dora provider-neutral 无动作 wiring，并按架构集成、失败路径、权威边界、配置、可维护性五个维度完成审查；不连接真实 Dora、Gateway、Action 或硬件。

Completed provider-neutral no-motion Gateway/Dora wiring and reviewed it across architecture integration, failure paths, authority boundaries, configuration, and maintainability; no real Dora, Gateway, Actions, or hardware connected.

### Detailed changes

- `PhyAgentOS/forge/capability_runtime/http_transport.py:L1-L95`: reusable HTTP Gateway transport over `CapabilityRuntime`.
- `PhyAgentOS/forge/capability_runtime/runtime.py:L57-L70,L180-L223,L260-L313`: deadline/unknown and cancel/stop terminal reconciliation; Session timeout rejection.
- `tests/test_gateway_dora_no_motion_conformance.py:L1-L117`: discovery, identity, lifecycle, malformed JSON, cancellation, timeout, and no-POST conformance.
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`: five-dimension acceptance and execution-order clarification.

### Validation

- Repository tests: `150 passed`; pick-place tests: `243 passed`; conformance subset: `11 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Real Dora/Gateway, Action executor, hardware motion, pick-place closure, and autonomous-evolution promotion remain deferred.
- Commit: `dd1ee70` on `feature/long-horizon-workflow`.
- Follow-up log commit: `83185bc`.

## [v3.8.3] - 2026-09-04

完成完整 `gpt-5.6-sol/high` held-out + hazard 真实模型语义评估并关闭 Verification 质量门禁；保留一个 replan/inconclusive 残余质量风险，不连接 Gateway、Dora、Action 或硬件。

Completed the full `gpt-5.6-sol/high` held-out + hazard real-model semantic evaluation and closed the Verification quality gate; retained one replan/inconclusive residual quality risk, with no Gateway, Dora, Action, or hardware connected.

### Detailed changes

- `artifacts/evals/verification/20260904T034715.434600Z-42a21625/run_manifest.json`: full 7-case run bound to commit `2722d78d1f21d43f12c0213811376ee8f8bf57a8`, exact custom provider binding, and redacted file credential source.
- `artifacts/evals/verification/20260904T034715.434600Z-42a21625/metrics.json`: `quality_gate_eligible=true`, `quality_gate_passed=true`, contract/criterion/recovery-context `1.0`, false-positive rate `0`, overall verdict accuracy `0.8571428571428571`.
- `docs/forge/VERIFICATION_MODEL_EVALUATION.md`, `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md`: recorded per-case review, residual replan error, and the next Gateway/Dora no-motion integration stage.

### Validation

- All 7 held-out/hazard cases completed; no credential or Bearer leakage found in artifacts.
- The held-out `replan_required` case was returned as `inconclusive` (`held_out` accuracy `0.75`), above the configured overall `0.8` threshold but retained as follow-up risk.
- Verification gate closure does not authorize physical execution, pick-place closure, or autonomous-evolution promotion.
- Commit: `bccdd6f` on `feature/long-horizon-workflow`.

## [v3.8.2] - 2026-09-04

回写 v3.8.1 实现提交 `9c1b955`，不修改实现或评估行为。

Recorded v3.8.1 implementation commit `9c1b955`; implementation and evaluation behavior were unchanged.

- Commit: `2722d78` on `feature/long-horizon-workflow`.

## [v3.8.1] - 2026-09-04

将独立 key 文件能力接入 `paos agent` 主配置，修正评估文档与日志中的当前状态，并验证 Agent 配置链路。

Wired the independent key-file capability into the `paos agent` main configuration, corrected the evaluation documentation and changelog state, and verified the Agent configuration path.

### Detailed changes

- `PhyAgentOS/config/credentials.py:L1-L48`: strict owner-only, non-symlink API-key-file reader.
- `PhyAgentOS/config/schema.py:L394-L417,L547-L612`, `PhyAgentOS/config/loader.py:L43-L52`, `PhyAgentOS/cli/commands.py:L285-L337,L1650-L1657`: `apiKeyFile` schema, config-path-relative resolution, runtime provider wiring, and status detection.
- `tests/test_config_api_key_file.py:L1-L52`: success, relative-path, dual-source, symlink, and permission regression tests.
- `README.md:L196-L200`, `docs/zh/04-forge-configuration-reference.md:L70-L76`, `docs/forge/VERIFICATION_MODEL_EVALUATION.md:L42-L101`: configuration and execution-order documentation.

### Validation

- `paos status`: `Custom: ✓`.
- No-tool `paos agent` connectivity check completed successfully with `gpt-5.6-sol/high`.
- Repository tests: `147 passed`; Ruff, compileall, and `git diff --check` passed.
- The LiteLLM SOCKS cost-map warning is non-fatal; no Gateway, Dora, Action, hardware, or motion path was started.
- Commit: `9c1b955` on `feature/long-horizon-workflow`.

## [v3.8.0] - 2026-09-04

接入 Verification 真实模型评估的独立 API key 文件，并完成 `gpt-5.6-sol/high` 单 case 连通性验证；同时保持完整 held-out + hazard 门禁、Gateway/Dora 和抓取放置闭环后置。

Added an independent API-key-file credential source for Verification real-model evaluation and completed a `gpt-5.6-sol/high` single-case connectivity check; full held-out + hazard gating, Gateway/Dora, and pick-place closure remain deferred.

### Detailed changes

- `PhyAgentOS/verification/evaluation.py:L6-L18,L137-L190,L254-L329,L514-L548`: strict file credential loading, redaction, and provider binding.
- `PhyAgentOS/verification/service.py:L64-L68`: explicit recovery-context field guidance in the production prompt.
- `evals/verification/evaluation_config_sol_high_v1.json:L1-L25`, `evals/verification/provider.sol_high.example.json:L1-L13`: versioned `custom`/`gpt-5.6-sol` `/v1` configuration with `allow_custom_provider=true` binding.
- `tests/test_verification_model_evaluation.py:L21-L22,L196-L207,L300-L413`, `tests/test_verifier_semantic_conformance.py:L10,L43-L49`: credential, prompt, and strict-schema regression coverage.
- `docs/forge/VERIFICATION_MODEL_EVALUATION.md:L42-L101`, `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L272-L285`: operating instructions and evidence boundaries.

### Validation

- `gpt-5.6-sol/high --max-cases 1`: completed with contract/verdict/criterion/recovery-context `1.0`; gate eligibility remains `false`.
- Full repository regression after the follow-up configuration wiring: `147 passed`; Ruff, compileall, and `git diff --check` passed.
- No Gateway, Dora, Action, hardware, or motion path was started.

## [v3.7.2] - 2026-09-04

回写 v3.7.1 审计维护提交；没有修改实现、评估配置、运行证据或执行顺序。

Recorded the v3.7.1 audit-maintenance commit; implementation, evaluation configuration, run evidence, and execution order are unchanged.

- Commit: `d88fd3a`
- Branch: `feature/long-horizon-workflow`

## [v3.7.1] - 2026-09-04

维护 v3.7.0 审计记录：回写实现提交，并把真实模型 blocker 更新为提交后的终态 preflight 产物；没有修改评估行为、阈值或执行顺序。

Maintained the v3.7.0 audit record by recording the implementation commit and updating the real-model blocker to the terminal post-commit preflight artifact; evaluation behavior, thresholds, and execution order are unchanged.

- Implementation commit: `8775073`
- Post-commit blocked run: `artifacts/evals/verification/20260903T163926.458050Z-db095983/`
- The manifest binds the run to full commit `8775073eccb26791a5ffd0215794c49fd46f3f82`; no model request or quality score was produced.

## [v3.7.0] - 2026-09-03

建立可复现的 Verification Service 真实模型语义质量评估基础设施，并在代码审查后关闭跨层依赖、非终态错误、fixture 身份冒充和部分 case 误过完整门禁的问题。真实模型凭据当前不可用，因此质量门禁保持 blocked；未连接 Gateway、Dora、Action 或硬件。

Established reproducible real-model semantic-quality evaluation infrastructure for Verification Service, then closed reverse-layer dependencies, non-terminal errors, fixture identity masquerading, and partial-case gate bypasses during code review. Real-model credentials remain unavailable, so the quality gate is blocked; no Gateway, Dora, Action, or hardware was connected.

### Detailed changes

- `PhyAgentOS/verification/evaluation.py:L1-L675`: adds strict dataset/config/provider schemas, immutable provider gate binding, unique UTC run directories, provenance/digests, production subprocess execution, fsynced per-attempt records, metrics, threshold decisions, and terminal blocked/error artifacts.
- `PhyAgentOS/verification/validation.py:L1-L34`, `PhyAgentOS/agent/session_verifier.py:L29-L32,L178-L192`: moves criteria/evidence-reference authority validation into the Verification layer while preserving the Agent-facing error contract.
- `PhyAgentOS/verification/request_builder.py:L35-L52,L389`: shares the production verification prompt envelope with the evaluator.
- `scripts/evaluate_verification_model.py:L1-L37`, `evals/verification/semantic_verifier_v1.json:L1-L299`, `evals/verification/evaluation_config_v1.json:L1-L23`, `evals/verification/provider.openai_codex.example.json:L1-L11`: adds the CLI, 10-case development/held-out/hazard corpus, thresholds, and credential-safe provider example.
- `tests/test_verification_model_evaluation.py:L1-L449`: covers strict loading, production subprocess fixture replay, credential blockers, terminal startup errors, provider identity binding, and partial-case ineligibility.
- `docs/forge/VERIFICATION_MODEL_EVALUATION.md:L1-L75`, `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L214-L250`, `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L315-L320`: records the quality/evaluation boundary and preserves the approved execution order.

### Key diff

```text
Before: fixture smoke and partial runs could self-declare real_model eligibility; evaluation reused an Agent-private validator; startup failure could leave a running manifest.
After:  a versioned non-custom provider identity and full case set are mandatory; validation is owned by Verification; every blocked/error path writes terminal fail-closed artifacts.
```

### Validation

- Verification/evaluation focused suite: `57 passed`.
- Repository suite: `136 passed`.
- Pick-place workflow and RoboTwin adapter suites: `310 passed` using the existing PAOS packages plus system NumPy; the unmodified PAOS environment alone currently lacks NumPy.
- Ruff, compileall, `git diff --check`, reverse-dependency scan, and credential/artifact review passed.
- Real-model preflight remains blocked by unavailable Codex OAuth credentials; fixture metrics are explicitly not quality-gate evidence.

Git commit: `8775073` on `feature/long-horizon-workflow`.

## [v3.6.0] - 2026-09-03

完成真实 `VerificationServiceProcess` provider-spec 子进程门禁：父进程启动正式子进程，独立 OpenAI-compatible HTTP stub 验证配置传递、私有 readiness、鉴权请求、结构化 verdict、provider 失败、超时和 stop 清理；未连接外部模型、Gateway、Watchdog、Action 或硬件。

Completed the production `VerificationServiceProcess` provider-spec subprocess gate: the parent starts the formal child process, and an independent OpenAI-compatible HTTP stub verifies config transfer, private readiness, authenticated requests, structured verdicts, provider failure, timeout, and stop cleanup; no external model, Gateway, Watchdog, Action, or hardware was connected.

### Detailed changes

- `PhyAgentOS/verification/service.py:L28,L282-L314,L405-L418`: added a stable service identifier and token-protected `/readyz` readiness probe with strict JSON/service identity checks; retained `/healthz` as liveness.
- `tests/test_verification_service_process.py:L1-L230`: covers formal subprocess startup, provider-spec propagation, external HTTP provider stub, failure/timeout mapping, readiness authentication, and process cleanup.
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L161-L212`: records implementation review, validation evidence, and remaining gates.

### Validation

- Repository tests: `127 passed`.
- Pick-place example tests: `241 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Real-model semantic quality, Gateway/Dora wiring, and pick-place closure remain pending.

Git commit: `cfef665` on `feature/long-horizon-workflow`.

## [v3.6.1] - 2026-09-03

维护 v3.6.0 实现提交日志，记录 provider-spec 子进程门禁提交 hash。

Maintained the v3.6.0 implementation log and recorded the provider-spec subprocess gate commit hash.

Git commit: `cfef665` on `feature/long-horizon-workflow`.

## [v3.5.2] - 2026-09-03

维护提交日志：回写 v3.5.0/v3.5.1 的实现提交 hash，并核对当前分支。

Commit-log maintenance: recorded the implementation commit hash for v3.5.0/v3.5.1 and verified the current branch.

- Implementation commit: `e4cdac5`
- Branch: `feature/long-horizon-workflow`

## [v3.5.1] - 2026-09-03

完成第三轮五维代码审查并修复 Store、状态协议和 Verification HTTP 边界；未启动真实 provider、外部模型、Gateway、Action 或硬件。

Completed the third five-dimension code review and fixed Store, state-protocol, and Verification HTTP boundaries; no real provider, external model, Gateway, Action, or hardware was started.

Git commit: `e4cdac5` on `feature/long-horizon-workflow`.

### Detailed changes

- `PhyAgentOS/forge/task.py:L83-L125,L182-L262,L381-L411,L417-L463,L571-L586`：finite execution/event payload、完整聚合关系校验、create/update pre-commit validation、`task_id`/`created_at`/origin identity immutability。
- `PhyAgentOS/state_io/protocol.py:L31-L55,L140-L155`：JSON/YAML duplicate-key rejection。
- `PhyAgentOS/verification/service.py:L33-L51,L197-L239,L341-L351,L372-L421`：strict JSON decoding and strict parent constructor types。
- `tests/test_state_file_authority_boundaries.py`、`tests/test_state_file_adapter.py`、`tests/test_verification_service_replay.py`、`tests/test_verification_service_config.py`：真实边界回归覆盖。
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L117-L176`：第三轮 review 记录。

### Validation

- Repository tests: `123 passed`.
- Pick-place example tests: `241 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Provider-spec production subprocess, real-model semantic quality, and pick-place closure remain pending.

## [v3.5.0] - 2026-09-03

完成状态文件适配、Evidence、Verifier 与 Verification Service 的边界修复，并完成第二轮代码审查；未启动真实 provider 子进程、外部模型、Gateway、Watchdog、Action 或硬件。

Completed boundary fixes for state-file adapters, Evidence, Verifier, and Verification Service, followed by a second code review; no real provider subprocess, external model, Gateway, Watchdog, Action, or hardware was started.

### Detailed changes

- `PhyAgentOS/forge/task.py:L45-L56,L190-L244,L286-L361,L393-L445,L1193-L1240`：AgentTask approval binding、SQLite origin migration/backfill/index、immutable origin、full aggregate revalidation、terminal retention wiring。
- `PhyAgentOS/state_io/adapters.py:L275-L322,L390-L405,L429-L510,L548-L632`：strict TARGETS/SESSIONS schema、bounded promotion、dedup exception handling。
- `PhyAgentOS/forge/evidence.py:L31-L115,L118-L152,L165-L244,L301-L350,L570-L583`：v2 manifest、writer-owned path、pre-write immutability、strict robot-state JSON、stable bundle identity。
- `PhyAgentOS/verification/request_builder.py:L27-L32,L198-L227,L253-L318`：AgentTask Bundle binding, same-bundle evidence ownership, strict structured JSON and unique paths。
- `PhyAgentOS/verification/service.py:L56-L206,L345-L418`、`PhyAgentOS/config/schema.py:L341-L361`：shared provider/service schema and stable HTTP errors。
- `PhyAgentOS/state_io/__init__.py`：移除无生产 owner 的 generic SKILLRUNTIME/LESSONS renderer 公共导出。
- `tests/test_state_file_authority_boundaries.py:L1-L476`：真实 Store/writer/request/context/retention 边界审查覆盖。
- `docs/forge/STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md:L1-L176`：完整审查发现、修复记录和三轮五维复审结论。

### Key diff

```text
Before: origin migration was incomplete; malformed evidence/provider failures could cross owner boundaries; generic renderers looked production-ready.
After:  origins migrate and remain immutable; evidence/provider requests fail closed; only owned projections are represented as implemented.
```

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -q tests` → `105 passed`.
- Pick-place example suite → `241 passed`.
- Unguarded pytest is blocked before collection by the system ROS `launch_testing` plugin missing `lark`; validation isolates plugins and explicitly loads `pytest_asyncio.plugin`.
- Ruff, compileall, and `git diff --check` passed.
- Provider-spec production subprocess, real-model semantic quality, and pick-place closure remain pending.

## [v3.4.6] - 2026-09-03

增加 Verification Service HTTP replay/failure conformance：验证授权 token、请求 envelope、重复 replay、
deterministic provider verdict、invalid-response normalization 和 provider failure。测试仅使用进程内
provider，不启动生产验证子进程或连接外部模型。

Added Verification Service HTTP replay/failure conformance for authorization tokens, request envelopes, repeated
replay, deterministic provider verdicts, invalid-response normalization, and provider failures. Tests use only an
in-process provider and do not start the production verification subprocess or connect to external models.

### Detailed changes

- `tests/test_verification_service_replay.py:L1-L117` adds HTTP handler/engine replay and failure tests.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L285-L296` records service-level conformance and remaining provider-spec/real-model gates.
- `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L60-L63` records Verification Service HTTP conformance coverage.

### Key diff

```text
Before: verifier checks were tested locally, but the HTTP service boundary had no deterministic replay matrix.
After:  the real handler + VerificationEngine path validates auth, request schema, normalization, replay, and failure propagation without external side effects.
```

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `58 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No production Verification Service, external model, Gateway, Watchdog, Action, or motion authorization was used.

## [v3.4.5] - 2026-09-03

增加 ForgeTaskVerifier 本地 verdict contract conformance：success/replan 不变量、criteria 精确绑定、
unknown evidence、malformed response 和 no-service 边界。该轮不启动 Verification Service，不调用模型或 Gateway。

Added local ForgeTaskVerifier verdict contract conformance for success/replan invariants, exact criterion binding,
unknown evidence, malformed responses, and the no-service boundary. This iteration does not start the Verification
Service or call a model or Gateway.

### Detailed changes

- `tests/test_verifier_semantic_conformance.py:L1-L126` adds deterministic verifier acceptance/rejection tests.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L280-L290` distinguishes local verdict contract checks from provider-backed semantic quality.
- `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L59-L62` records local verifier conformance coverage.

### Key diff

```text
Before: verifier boundary tests covered projection-as-evidence rejection, but not the full verdict contract matrix.
After:  deterministic fixtures validate criteria/evidence/recovery invariants and malformed responses without starting a service.
```

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `54 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No Verification Service, model, Gateway, Watchdog, Action, or motion authorization was used.

## [v3.4.4] - 2026-09-03

校正执行顺序文档：明确 `SKILLRUNTIME.md`/`LESSONS.md` 是可选 projection，记录受限 promotion 先于
后续 replay conformance 的历史顺序，并确认抓取放置和自主进化尚未启动。未修改运行时代码。

Corrected execution-order documentation: `SKILLRUNTIME.md`/`LESSONS.md` are optional projections, the historical
ordering of bounded promotion before later replay conformance is recorded, and pick-place plus autonomous evolution
remain unstarted. No runtime code was changed.

### Detailed changes

- `docs/forge/ROBOTWIN_ADAPTER_REFACTOR_DIAGNOSIS.md:L400-L420` aligns required versus optional file adapters and records the bounded-promotion ordering review.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L275-L283` distinguishes request-level Evidence conformance from remaining semantic/live replay work.

### Validation

- Documentation-only change; `git diff --check` passed.
- No Gateway, Watchdog, Action, AgentTask, or motion authorization was used.

## [v3.4.3] - 2026-09-03

增加 Evidence request-level conformance：不可变 Evidence Bundle 在跨工作区 replay 时重新校验
capture window、必需 kind/source、association、retention、digest/size、媒体类型和结构化 JSON。
该轮不修改 Verifier 语义权威逻辑，也不把 `ENVIRONMENT.md` 变成 Evidence。

Added Evidence request-level conformance: immutable Evidence Bundles are revalidated across workspace replay
for capture windows, required kind/source, association, retention, digest/size, media type, and structured JSON.
This iteration does not change Verifier semantic authority or turn `ENVIRONMENT.md` into Evidence.

### Detailed changes

- `tests/test_evidence_semantic_replay_conformance.py:L1-L184` adds immutable bundle replay and fail-closed request validation tests.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L280-L287` records request-level Evidence conformance and its remaining limits.
- `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L59-L61` records Evidence request conformance coverage.

### Key diff

```text
Before: Evidence boundary had basic projection rejection but no dedicated replay matrix for request consumption.
After:  immutable bundle replay validates identity, window, policy, retention, digest/size, media, and structured data;
        LLM semantic verdict and live Gateway replay remain explicitly out of scope.
```

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `48 passed`.
- `PYTHONPATH=examples/forge-skills/pick-place-workflow/src python -m pytest -q examples/forge-skills/pick-place-workflow/tests` → `241 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No real Gateway, Watchdog, Action, or motion authorization was used.

## [v3.4.2] - 2026-09-03

增加状态文件适配的 replay/failure conformance：跨工作区回放保持确定性，未知字段在触及 Store/Gateway
前 fail-closed，Store 编译失败不留下生命周期残留，projection drift 保留原内容，TARGETS/SESSIONS
继续保持 `motion_authorized=false`。`SKILLRUNTIME.md` 与 `LESSONS.md` producer 仍明确为可选 projection。

Added state-file adapter replay/failure conformance: cross-workspace replay remains deterministic, unknown fields
fail closed before Store/Gateway access, Store compilation failures leave no lifecycle residue, projection drift
preserves the prior content, and TARGETS/SESSIONS retain `motion_authorized=false`. `SKILLRUNTIME.md` and
`LESSONS.md` producers remain explicitly optional projections.

### Detailed changes

- `tests/test_state_file_replay_conformance.py:L1-L215` adds replay, Fake Store failure, Gateway no-call sentinel, drift-preservation, and no-motion tests.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L280-L288` separates required Phase-B boundary conformance from optional Markdown projections.

### Key diff

```text
Before: replay/failure coverage was distributed across adapter tests without an explicit cross-workspace boundary.
After: dedicated conformance tests assert deterministic replay, no partial lifecycle state, drift preservation,
       and no-motion behavior while keeping Markdown non-authoritative.
```

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `43 passed`.
- `PYTHONPATH=examples/forge-skills/pick-place-workflow/src python -m pytest -q examples/forge-skills/pick-place-workflow/tests` → `241 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No real Gateway, Watchdog, Action, or motion authorization was used.

## [v3.4.1] - 2026-09-03

增加 Verifier/Evidence boundary conformance：`ENVIRONMENT.md` projection 不能被解析为 Evidence Bundle，
verifier verdict 不能以 projection URI 冒充 evidence reference。未修改 Verifier 的事实源或语义判定逻辑。

Added Verifier/Evidence boundary conformance proving that an `ENVIRONMENT.md` projection cannot be parsed as an
Evidence Bundle and a verifier verdict cannot use a projection URI as an evidence reference. No verifier fact
source or semantic decision logic was changed.

### Detailed changes

- `tests/test_verifier_evidence_boundary.py:L1-L59` adds projection-as-evidence rejection and unknown projection-reference verdict tests.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L271-L283` records the completed boundary conformance and remaining full semantic/replay work.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `38 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No Gateway, Watchdog, Action, AgentTask, or motion authorization was produced.

## [v3.4.0] - 2026-09-03

增加 `ForgeEvidenceWriter` 到 `EnvironmentProjectionProducer` 的受限关联。writer 校验自身生成的
before/after manifest、phase 和路径，生成稳定 opaque `evidence://` reference，并拒绝同一 phase 的
不同内容覆盖；producer 可自动注入 phase/reference 并拒绝不匹配值。Evidence/Verifier 仍是权威，未增加
Gateway、Watchdog、Action、AgentTask 或运动路径。

Added a bounded association from `ForgeEvidenceWriter` to `EnvironmentProjectionProducer`. The writer validates
its before/after manifests, phase, and path, derives a stable opaque `evidence://` reference, and rejects content
replacement within a phase. The producer injects phase/reference or rejects mismatches. Evidence/Verifier remain
authoritative; no Gateway, Watchdog, Action, AgentTask, or motion path was added.

### Detailed changes

- `PhyAgentOS/forge/evidence.py:L27-L143` adds writer-owned snapshot identity validation, stable evidence URI derivation, and same-phase immutability checks.
- `PhyAgentOS/forge/environment_projection.py:L30-L237` adds `publish_from_evidence_writer()` and the minimal `EvidenceSnapshotStore` seam.
- `PhyAgentOS/forge/__init__.py:L3-L33` exports the evidence association protocol.
- `tests/test_environment_projection_producer.py:L1-L194` covers manifest association, stable URI, overwrite rejection, phase/reference mismatch, and non-writer paths.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L265-L278` and `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L27-L71` record the completed association and remaining Phase-B work.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `36 passed`.
- `PYTHONPATH=examples/forge-skills/pick-place-workflow/src python -m pytest -q examples/forge-skills/pick-place-workflow/tests` → `241 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Full RoboTwin collection remains environment-limited by missing `numpy`/package path; no motion or live verifier run.

## [v3.3.0] - 2026-09-03

增加受限 `EnvironmentProjectionProducer`：从已捕获的 `ObservationSnapshot` 和显式 provenance 生成严格
`ENVIRONMENT.md` projection；before/after 快照必须绑定 `evidence://` URI，可选地与
`EnvironmentAdapter.snapshot()` 的 scene revision 一致性校验。producer 只做原子 projection 写入，
不调用 Gateway、Watchdog、Action，不创建 AgentTask，也不替代 Evidence/Verifier 事实源。

Added a bounded `EnvironmentProjectionProducer` that renders a strict `ENVIRONMENT.md` projection from an
already captured `ObservationSnapshot` and explicit provenance. Before/after snapshots must use an `evidence://`
URI and can be revision-bound to `EnvironmentAdapter.snapshot()`. The producer only performs atomic projection
writes; it does not call Gateway, Watchdog, or Action, create AgentTasks, or replace Evidence/Verifier authority.

### Detailed changes

- `PhyAgentOS/forge/environment_projection.py:L1-L180` adds the producer input contract, adapter revision binding, evidence URI gate, and no-side-effect projection path.
- `PhyAgentOS/forge/__init__.py:L3-L31` exports the producer API.
- `PhyAgentOS/state_io/adapters.py:L553-L601` forwards optional `expected_sha256` to the atomic projection writer.
- `tests/test_environment_projection_producer.py:L1-L144` covers before/after success, idempotency, drift, invalid/empty input, evidence URI, adapter revision, and no-capture boundaries.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L256-L273` and `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L27-L71` record the producer boundary and remaining Phase-B work.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `33 passed`.
- Ruff, compileall, and `git diff --check` passed.
- No live pick-place provider, Gateway invocation, AgentTask, Evidence verdict, or motion authorization was produced.

## [v3.2.0] - 2026-09-03

完成 `ENVIRONMENT.md` 的严格 projection 适配：增加 snapshot/provenance schema、revision 一致性校验，
将 SceneGraph 查询从宽松 loader 切换为严格 parser，并同步模板。缺失、旧版或损坏文件现在返回 bounded
error；Evidence snapshot 仍是唯一语义事实源，未接入动作、Watchdog、Gateway 或硬件。

Completed strict `ENVIRONMENT.md` projection adaptation with snapshot/provenance schema and revision consistency
checks, switched SceneGraph queries from the permissive loader to the strict parser, and aligned the template.
Missing, legacy, or damaged files now return a bounded error. Evidence snapshots remain the sole semantic authority;
no Action, Watchdog, Gateway, or hardware path was added.

### Detailed changes

- `PhyAgentOS/state_io/adapters.py:L88-L148,L330-L344,L563-L574` adds the strict environment schema, parser, and renderer validation.
- `PhyAgentOS/agent/tools/scene_graph.py:L11-L63` consumes only valid environment projections and rejects malformed input.
- `PhyAgentOS/templates/ENVIRONMENT.md:L1-L34` aligns the template with `paos.state-file.v1`.
- `tests/test_state_file_adapter.py:L264-L335,L406-L414` covers provenance, revision, legacy, and fail-closed behavior.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests` → `26 passed`.
- `ruff check ...`, `python -m compileall ...`, and `git diff --check` passed.

## [v3.1.1] - 2026-09-03

完成最近三个 `TARGETS.md` candidate 功能的代码审查与测试。修复 `profile_id` 可包含路径分隔符的问题，
并补充审批 decision/时间戳、非法 profile、baseline 差异批准、输入文件不变和 no-motion 测试。

Completed code review and testing for the three recent `TARGETS.md` candidate features. Fixed path-like
`profile_id` identities and added coverage for approval decision/timestamp, invalid profiles, explicit baseline
differences, input immutability, and no-motion behavior.

### Detailed changes

- `PhyAgentOS/state_io/adapters.py:L180-L190` now rejects path-unsafe `profile_id` values.
- `tests/test_state_file_adapter.py:L82-L180` adds the review and failure-path tests; 18 focused tests pass.
- `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L50-L56` and `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L246-L255` record the review result and remaining Minor risk.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_state_file_adapter.py` → `18 passed`.
- `ruff check ...`, `python -m compileall ...`, and `git diff --check` passed.

## [v3.1.0] - 2026-09-03

新增 `TARGETS.md` 的已验证 Capability Profile candidate：候选必须通过严格 shadow validation，并由
`TargetProfileApproval` 同时绑定源文件 digest 与 baseline digest。candidate 仅用于比较和回放，固定
`motion_authorized=false`，不写 Runtime/Profile 权威配置，不改变 Action admission 或运动限幅。

Added a validated Capability Profile candidate for `TARGETS.md`: candidates must pass strict shadow validation
and carry a `TargetProfileApproval` bound to both source and baseline digests. Candidates are limited to comparison
and replay, always expose `motion_authorized=false`, and cannot write Runtime/Profile authorities or alter Action
admission or motion limits.

### Detailed changes

- `PhyAgentOS/state_io/adapters.py:L24-L145,L253-L300` adds `TargetProfileApproval`, `TargetProfileCandidate`, and `promote_targets_candidate()`.
- `PhyAgentOS/state_io/__init__.py:L3-L42` exports the bounded candidate API.
- `tests/test_state_file_adapter.py:L61-L130` covers approved candidates, baseline drift, and no-motion behavior.
- `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L24-L47` and `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L240-L247` document the non-admission boundary.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_state_file_adapter.py` → `15 passed`.
- `ruff check ...`, `python -m compileall ...`, and `git diff --check` passed.

## [v3.0.0] - 2026-09-03

在人工确认边界内提升 `SESSIONS.md` 输入：新增 digest 绑定审批凭据、单会话幂等编译器，并通过
`AgentTaskCoordinator.create_task()` 写入既有 AgentTask SQLite 事实源；新增 `parent_task_id` 与
`retry_limit` 声明式字段。编译前检查全局非终态任务，重复编译复用既有记录；不直接写 SQLite、不调度
Watchdog、不调用 Gateway、不授权运动。

Promoted `SESSIONS.md` within an explicit human-approval boundary: added digest-bound approval credentials,
single-session idempotent compilation, and writes through the existing `AgentTaskCoordinator.create_task()`
to the AgentTask SQLite authority. Added declarative `parent_task_id` and `retry_limit` fields. Compilation
checks the global non-terminal slot and reuses repeated source/session records; it does not write SQLite directly,
dispatch Watchdog, call Gateway, or authorize motion.

### Detailed changes

- `PhyAgentOS/state_io/adapters.py:L43-L372` adds approval validation, one-session compiler, stable origin identity, parent/active-task checks, and no-motion result semantics.
- `PhyAgentOS/forge/task.py:L153-L181,L300-L315,L420-L527` persists optional parent/retry metadata and adds origin-key lookup used for idempotency.
- `PhyAgentOS/state_io/__init__.py:L3-L39` exports the bounded promotion API.
- `tests/test_state_file_adapter.py:L207-L322` covers approval digest binding, idempotent reuse, active-task and multi-session conflicts, unknown parents, and no-motion.
- `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L6-L58` and `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L228-L244` record the promotion boundary and remaining non-goals.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_state_file_adapter.py` → `13 passed`.
- `ruff check PhyAgentOS/state_io PhyAgentOS/forge/task.py tests/test_state_file_adapter.py` passed.
- `python -m compileall -q PhyAgentOS/state_io PhyAgentOS/forge/task.py tests/test_state_file_adapter.py` and `git diff --check` passed.
- Existing pick-place task tests remain un-runnable in this environment because `pick_place_workflow` is not on `PYTHONPATH`; this is reported separately and is not treated as a pass.

## [v2.9.0] - 2026-09-03

新增 PAOS 状态文件架构诊断文档，汇总 `TARGETS.md`、`SKILLRUNTIME.md`、`SESSIONS.md`、
`ENVIRONMENT.md`、`LESSONS.md` 与现有 AgentTask、Gateway、Evidence、Runtime 和 Experience
权威边界的对应关系；明确 Markdown 不是事务性中间状态的唯一事实源，并提出“先冻结最小上层契约，
再继续抓取放置证据闭环，最后实现文件输入/投影适配”的审核方向。

Added the PAOS state-file architecture diagnosis documenting how `TARGETS.md`, `SKILLRUNTIME.md`,
`SESSIONS.md`, `ENVIRONMENT.md`, and `LESSONS.md` map to the existing AgentTask, Gateway, Evidence,
Runtime, and Experience authorities. It clarifies that Markdown is not the sole source of transactional
intermediate state and proposes “freeze the minimal upper-layer contract, continue the pick-place evidence
closure, then add file input/projection adapters” for review.

### Detailed changes

- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L1-L240` adds the bilingual-domain diagnosis, authority table, Markdown input/projection protocol, pick-place impact analysis, autonomous-evolution boundaries, and six review gates.
- `docs/forge/ROBOTWIN_ADAPTER_REFACTOR_DIAGNOSIS.md:L390-L411` records the state-file protocol decision and preserves the provider-neutral pick-place implementation order.
- `docs/README.md:L29,L63` adds Chinese and English index links to the diagnosis.
- `changelog/2026-09_part2.md:L1-L61` records the detailed bilingual change, actual line ranges, key diffs, and validation in the split monthly archive.

### Validation

- `git diff --check` passed.
- Markdown headings, cross-document links, line references, and bilingual changelog entries were inspected.
- No source code, runtime behavior, or execution contract was changed by this documentation decision.

## [v2.9.1] - 2026-09-03

审核并确认“先做受限文件适配、后做抓取放置闭环”符合 PAOS 扩展原则。执行顺序调整为：冻结最小上层与文件契约，
实现只读 projection、`TARGETS.md` shadow validation、`SESSIONS.md` dry-run 及回放验证，人工确认后再提升输入边界，
最后推进抓取放置和受控自主进化。适配层不得拥有 Watchdog、AgentTask 生命周期、Gateway 或 Action admission，
也不得建立 Markdown queue Runtime。

Reviewed and confirmed that “restricted file adapters before the pick-place closure” conforms to PAOS extension principles.
The execution order now freezes the minimal upper-layer and file contracts, implements read-only projections,
`TARGETS.md` shadow validation, `SESSIONS.md` dry-runs, and replay validation, promotes inputs only after human approval,
and then advances pick-place and guarded evolution. Adapters do not own Watchdog, AgentTask lifecycle, Gateway, or Action
admission, and no Markdown queue Runtime is introduced.

### Detailed changes

- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L162-L208,L249-L257` records the review conclusion and revised five-stage order.
- `docs/forge/ROBOTWIN_ADAPTER_REFACTOR_DIAGNOSIS.md:L398-L414` synchronizes the RoboTwin execution order and explicitly approves restricted file adapters first.
- `changelog/2026-09_part2.md:L55-L103` records the bilingual plan, actual changes, validation, and commit references.

### Validation

- `git diff --check` passed.
- PAOS extension principles were checked against ownership, provider-neutral boundary, no-second-protocol, projection authority, and no-motion requirements.
- No source code, runtime behavior, hardware IO, or motion authorization changed.

## [v2.10.0] - 2026-09-03

新增 PAOS State File Adapter 第一阶段实现：严格解析 `paos.state-file.v1` Markdown 结构化区块，提供原子 projection 写入、canonical digest drift 检查、`TARGETS.md` capability shadow validation、`SESSIONS.md` 确定性 dry-run 预览，并通过功能引用卡固定其非执行边界。该适配器不写入 AgentTask 生命周期、不调度 Watchdog、不调用 Gateway，也不授权运动。

Added the phase-one PAOS State File Adapter: strict `paos.state-file.v1` Markdown block parsing, atomic projection writes, canonical-digest drift checks, `TARGETS.md` capability shadow validation, and deterministic `SESSIONS.md` dry-run previews. The feature card fixes its non-execution boundary: it does not write AgentTask lifecycle state, schedule Watchdog work, call Gateway, or authorize motion.

### Detailed changes

- `PhyAgentOS/state_io/protocol.py:L1-L224` adds the strict envelope parser, opaque-reference metadata validation, canonical digest, atomic projection writer, and explicit drift error.
- `PhyAgentOS/state_io/adapters.py:L1-L214` adds target shadow validation, deterministic session previews, and projection entry points for Runtime, Environment, and Lessons.
- `PhyAgentOS/state_io/__init__.py:L1-L35` exports the bounded adapter API without adding a Gateway or Runtime route.
- `tests/test_state_file_adapter.py:L1-L198` covers valid/invalid envelopes, limits, drift, projection mode, deterministic dry-run, duplicate/unsafe identities, and no-motion flags.
- `docs/forge/STATE_FILE_ADAPTER_FEATURE_CARD.md:L1-L61` records the normative references, ownership, failure semantics, acceptance gates, and non-goals.
- `docs/forge/PAOS_STATE_FILE_ARCHITECTURE_DIAGNOSIS.md:L162-L228` records the phase-one implementation status and next promotion gate; `docs/README.md:L30,L65` indexes the feature card.

### Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_state_file_adapter.py` → `9 passed`.
- `ruff check PhyAgentOS/state_io tests/test_state_file_adapter.py` passed.
- `python -m compileall -q PhyAgentOS/state_io tests/test_state_file_adapter.py` passed.
- `git diff --check` passed.
- No hardware, simulator, Gateway, Watchdog, AgentTask store, or motion path was invoked.

## [v2.8.17] - 2026-09-03

Implemented the provider-neutral grasp proposal extension: `grasp.propose`
targets may carry observation/revision/frame/calibration-bound geometry
artifacts, while the independent adapter resolves point clouds and invokes an
isolated GraspGen-compatible JSONL worker. Candidate matrices are validated,
converted to normalized pose/approach evidence, filtered with deterministic
SE(3) NMS, and returned with a reconciled funnel; no IK, collision admission,
or motion authorization is added.

实现 provider-neutral 抓取候选扩展：`grasp.propose` target 可携带绑定
observation/revision/frame/calibration 的几何资产；独立 adapter 解析点云并调用隔离的
GraspGen-compatible JSONL worker，校验候选矩阵、转换为归一化位姿/approach 证据，执行确定性
SE(3) NMS 并返回闭合 funnel；没有增加 IK、碰撞准入或运动授权。

### Detailed changes

- `PhyAgentOS/forge/capability_runtime/grasp_proposal.py:L34-L678` adds neutral geometry-artifact binding, mapping normalization, unit quaternion/approach validation, and strict fail-closed projection.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_proposal.py:L1-L383` adds point-cloud resolution, isolated worker request/response mapping, candidate canonicalization, NMS, provenance, and cleanup handling.
- `examples/forge-adapters/robotwin20/runtime/graspgen_worker.py:L1-L129` and `runtime/worker_protocol.py:L12-L72` add the isolated worker entrypoint and versioned JSONL lifecycle.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grasp_profile.py:L1-L75` and `profiles/robotwin20/graspgen.yaml:L1-L29` keep interpreter, checkpoint, and filtering settings outside PAOS.
- `examples/forge-skills/pick-place-workflow/contracts/grasp.propose.tool.yaml:L1-L110` mirrors the public ToolSpec; tests cover mapping normalization, artifact binding, NMS, malformed worker data, and cleanup failure.

### Validation

- Generic PAOS grasp conformance: `57 passed`.
- Isolated adapter grasp/provider/profile tests: `7 passed`.
- Ruff, compileall, and `git diff --check` passed.
- Live GraspGen inference was not claimed: no verified local checkpoint/source environment was found; the worker reports unavailable until an external profile supplies them.
- `.codegraph/` and `.cursor/` remain untracked and are not staged.

## [v2.8.16] - 2026-09-03

Implemented the clean-room, adapter-side single-view perception composition:
semantic entity binding to LocateAnything proposals, bounded proposal-worker
shutdown, SAM2 box segmentation in its separate environment, deterministic
RGB-D localization, transactional derived artifacts, and projection through
the existing provider-neutral `scene.understand` Gateway contract. PAOS and
RoboTwin20 remain free of model-environment dependencies, and every result is
Query evidence with `motion_authorized=false`.

实现 clean-room、adapter-side 单视角感知 composition：语义实体绑定
LocateAnything proposal，关闭 proposal worker 后再在独立环境运行 SAM2 box
segmentation，然后确定性生成 RGB-D 定位和事务式派生资产，最终通过既有
provider-neutral `scene.understand` Gateway 契约投影。PAOS 和 RoboTwin20 不引入模型
环境依赖，所有结果仍是 `motion_authorized=false` 的 Query 证据。

### Detailed changes

- `PhyAgentOS/forge/capability_runtime/understanding.py:L461-L601` binds every derived artifact to the current request's observation, revision, frame, and calibration.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/single_view_perception.py:L1-L707` composes proposal, segmentation, localization, artifact materialization, rollback, and ambiguity handling.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/process_worker.py:L1-L212` and `perception_profile.py:L1-L153` add bounded JSONL process lifecycle and profile-only environment wiring.
- `examples/forge-adapters/robotwin20/runtime/locateanything_worker.py:L1-L242`, `sam2_worker.py:L1-L186`, and `worker_protocol.py:L1-L60` are adapter-owned entrypoints for the two existing isolated model environments.
- `examples/forge-adapters/robotwin20/profiles/robotwin20/perception.yaml:L1-L56` externalizes interpreters, model revision, checkpoint, CUDA device, caches, artifact roots, and timeouts.
- Adapter/workflow tests cover worker protocol failures, request binding, proposal ambiguity, mask/depth/calibration validation, artifact traversal and rollback, and the no-motion Gateway route.

### Validation

- PAOS/workflow/adapter suite: `281 passed, 2 skipped`; model-side tests skip because PAOS intentionally has no NumPy/Pillow.
- Isolated adapter numerical/worker suite: `27 passed`.
- Real no-motion composition on an existing RoboTwin RGB-D capture returned one LocateAnything proposal, an aligned SAM2 mask, 788 camera-frame points, all three derived artifacts, and `motion_authorized=false`; both worker processes exited.
- Ruff, compileall, and `git diff --check` passed. A system-Python whole-suite attempt was not accepted because that interpreter lacks PAOS `loguru` and asyncio test dependencies.
- `.codegraph/` and `.cursor/` remain untracked and are not staged.

## [v2.8.15] - 2026-09-03

Extended the provider-neutral `scene.understand` Query with auditable derived
perception artifacts for instance masks, object point clouds, and metric
localization. Every artifact is bound to the observation, scene revision,
entity, frame, calibration, source lineage, and root provenance; no Action or
motion authorization was added. The independent RoboTwin adapter forwards only
plain mappings and remains free of PAOS, simulator, Torch, and model imports.

扩展 provider-neutral `scene.understand` Query，增加可审计的实例 mask、目标点云和度量定位
派生资产。每个资产绑定 observation、scene revision、entity、frame、calibration、source
lineage 和 root provenance；没有增加 Action 或运动授权。独立 RoboTwin adapter 只转发普通
mapping，仍不依赖 PAOS、仿真器、Torch 或模型导入。

### Validation

- `268 passed` for the workflow and RoboTwin adapter suites.
- Ruff, compileall, ToolSpec YAML equality, and `git diff --check` passed.
- `.codegraph/` and `.cursor/` remain untracked and were not staged.

## [v2.8.14] - 2026-09-03

整理两条 provider-neutral 感知接入方案：单视角
`LocateAnything → SAM2 → RGB-D localization`，以及多视角
`MultiViewObservationSet → cross-view segmentation/identity/geometry fusion`。
明确多视角不是 RoboTwin Skill 或模型 Tool；融合实体几何可供
`scene.understand` / `grasp.propose`，Global SceneGeometry 仅作为独立可选输出，
所有结果仍须经过 PAOS provenance、frame/calibration 和 fail-closed 门禁。

Consolidated two provider-neutral perception paths: single-view
`LocateAnything → SAM2 → RGB-D localization`, and multi-view
`MultiViewObservationSet → cross-view segmentation/identity/geometry fusion`.
Clarified that multi-view is neither a RoboTwin Skill nor a model Tool; fused
entity geometry may feed `scene.understand` / `grasp.propose`, while Global
SceneGeometry remains a separate optional output under PAOS provenance,
frame/calibration, and fail-closed gates.

### Validation

- `git diff --check` passed.
- Execution document audit confirms no direct Agent-to-model/Dora/SDK path and no implicit camera motion.
- `.codegraph/` and `.cursor/` remain untracked and were not staged.

## [v2.8.13] - 2026-09-03

Fixed the GPT Responses strict JSON schema by declaring `spatial_envelopes.unit`
as a typed string const. Added recursive regression checks because the fake
Responses client does not validate request schemas. Updated the RoboTwin
adapter diagnosis and README to keep recognition, segmentation, metric
localization, grasp-pose proposal, readiness, and execution in their PAOS
use-case boundaries; the current GPT provider remains RGB semantic-only.

修正 GPT Responses strict JSON schema，为 `spatial_envelopes.unit` 补充
`type: string`，并增加递归回归校验，避免 Fake client 遗漏真实 API 的请求阶段错误。
同步更新 RoboTwin adapter 诊断与 README，明确识别、分割、度量定位、抓取位姿、准入和执行的
PAOS 用例归属；当前 GPT provider 仍只负责 RGB 语义理解。

### Validation

- `261 passed` for the adapter/workflow suites.
- Ruff, compileall, and `git diff --check` passed.
- `.codegraph/` and `.cursor/` remain untracked and were not staged.

## [v2.8.12] - 2026-09-03

Added an adapter-side `FilesystemArtifactResolver` for external RoboTwin
observation artifacts. It safely maps opaque RGB artifact references to files
under an explicitly external absolute root, rejects traversal/non-image refs,
and enables the GPT scene-understanding provider to consume real runtime
captures without exposing paths or assets to PAOS.

为外部 RoboTwin observation artifact 增加 adapter 侧 `FilesystemArtifactResolver`。它只在显式外部绝对根目录
下安全解析 opaque RGB artifact 引用，拒绝路径穿越和非图像 refs，使 GPT 场景理解 provider 能消费真实 runtime
capture，同时不向 PAOS 暴露本地路径或资产。

### Validation

- `260 passed in 2.62s` for the adapter/workflow suites.
- Ruff, compileall, and `git diff --check` passed.
- Complete `ForgeToolClient -> Fake Gateway -> generic endpoint -> RoboTwin provider -> GPT client` route is covered by a fake Responses client test.
- No live API call was attempted because `HEPHAESTUS_RELAY_API_KEY` remains absent; no real model result is claimed.
- `.codegraph/` and `.cursor/` remain untracked and were not staged.

## [v2.8.10] - 2026-09-02

Removed the duplicate provider-neutral `RoboTwinUnderstandingSnapshot` from
the adapter. The compatibility name now aliases PAOS's
`UnderstandingSnapshot`, so the adapter only translates inference inputs and
outputs while PAOS remains the sole owner of the public scene-understanding
snapshot contract.

移除 adapter 中重复的 provider-neutral `RoboTwinUnderstandingSnapshot`。兼容名称现在指向 PAOS 的
`UnderstandingSnapshot`，adapter 只负责 inference 输入/输出转换，PAOS 继续作为 scene-understand snapshot
公共契约的唯一所有者。

### Validation

- `251 passed` for the adapter/workflow suites.
- Ruff, compileall, and `git diff --check` passed.
- Provider-specific output remains fail-closed and the ForgeToolClient/Fake Gateway path is unchanged.

## [v2.8.9] - 2026-09-02

Moved the provider-neutral `manipulation.prepare` Query implementation into
the PAOS-owned generic capability runtime. The runtime owns candidate binding,
preparation identity, workspace/kinematic/collision check validation, evidence
projection, stale/empty/unavailable/invalid states, and the fixed
`motion_authorized: false` boundary. The Skill module is now a compatibility
export only; no robot, simulator, or model dependency was added.

将 provider-neutral `manipulation.prepare` Query 实现迁移到 PAOS 自有 generic capability runtime。运行时统一
持有候选绑定、preparation identity、workspace/kinematic/collision 检查校验、证据投影、
stale/empty/unavailable/invalid 状态以及固定的 `motion_authorized: false` 边界。Skill 模块仅保留兼容导出，
未加入机器人、仿真器或模型依赖。

### Validation

- `250 passed` for the adapter/workflow suites.
- Ruff, compileall, and `git diff --check` passed.
- `manipulation.prepare` remains read-only; no Action/Session/motion route is created.

## [v2.8.8] - 2026-09-02

Moved the provider-neutral `grasp.propose` Query implementation into the
PAOS-owned generic capability runtime. The runtime now owns the strict
ToolSpec, observation/frame/calibration binding, candidate and candidate-set
identity, funnel reconciliation, provenance validation, stale/empty/
unavailable/invalid states, and fail-closed provider error projection. The
Skill module is now a compatibility export only, and preparation imports the
shared candidate validator directly from PAOS. No YOLO, GraspGen, RoboTwin,
SAPIEN, Torch, Dora, or Hephaestus dependency was added.

将 provider-neutral `grasp.propose` Query 实现迁移到 PAOS 自有 generic capability runtime。运行时统一持有
严格 ToolSpec、observation/frame/calibration 绑定、候选与候选集身份、funnel 对账、provenance 校验、
stale/empty/unavailable/invalid 状态以及 provider 异常的 fail-closed 投影；Skill 模块仅保留兼容导出，
准备能力直接导入 PAOS 的候选校验器。未加入 YOLO、GraspGen、RoboTwin、SAPIEN、Torch、Dora 或 Hephaestus
依赖。

### Validation

- `249 passed` for the adapter/workflow suites.
- Ruff, compileall, and `git diff --check` passed.
- `grasp.propose` remains Query-only; no Action/Session/motion route is created.

## [v2.8.7] - 2026-09-02

Moved the provider-neutral `scene.understand` contract into the PAOS-owned
generic capability runtime. ToolSpec validation, observation/artifact binding,
scene-graph snapshot validation, stale rejection, provider error projection,
and Query result projection now live under
`PhyAgentOS.forge.capability_runtime.understanding`. The Skill module is only a
compatibility export; no Hephaestus, RoboTwin, SAPIEN, Torch, YOLO, Dora, or
motion dependency was added.

将 provider-neutral `scene.understand` 契约迁移到 PAOS 自有的 generic capability runtime。ToolSpec 校验、
observation/artifact 绑定、场景图 snapshot 校验、stale 拒绝、provider 错误投影和 Query 结果投影均由
`PhyAgentOS.forge.capability_runtime.understanding` 持有；Skill 模块仅保留兼容导出。未加入 Hephaestus、
RoboTwin、SAPIEN、Torch、YOLO、Dora 或运动依赖。

### Validation

- `248 passed in 2.64s` for adapter/workflow tests.
- Ruff, compileall, and `git diff --check` passed.
- Existing Skill imports remain compatible while resolving to the PAOS-owned implementation.

## [v2.8.6] - 2026-09-02

Added the independent RoboTwin adapter seam for the existing provider-neutral
`scene.understand` Query. `RoboTwinSceneUnderstandingProvider` accepts an
injected inference service, forwards only `scene.observe` identity/artifact
references, and rejects provider-specific fields. The generic endpoint now
projects provider failures as explicit `understanding_provider_error` results.
No detector/VLM/YOLO or simulator truth is included.

按 v1.0 扩展原则，在现有 provider-neutral `scene.understand` Query 后增加独立 RoboTwin adapter seam。
`RoboTwinSceneUnderstandingProvider` 只转发 `scene.observe` 身份与 artifact 引用，拒绝 provider 专有字段；
通用 endpoint 将 provider 异常投影为明确的 `understanding_provider_error` 结果。不包含检测器、VLM、YOLO
或仿真真值。

### Validation

- `248 passed in 2.65s` for adapter/workflow tests.
- Ruff, compileall, and `git diff --check` passed.
- No Action/Session/motion route or simulator/model import was added.

## [v2.8.5] - 2026-09-02

Unified Fake Gateway and RoboTwin `scene.observe` results behind the existing
`ForgeToolClient.invoke_query_tool` path. Added a runtime-only
`RoboTwinObservationProvider` that projects camera/depth/state captures into
provider-neutral observation identity, frame, calibration, freshness, and typed
artifact references. The adapter accepts either the external runtime capture
seam or the injected `RoboTwin20Adapter` seam; PAOS remains free of RoboTwin,
SAPIEN, Torch, and model imports. Relaxed the Fake Gateway artifact-reference
validator to accept capture subpaths, and added equality/integration tests.

通过既有 `ForgeToolClient.invoke_query_tool` 路径统一 Fake Gateway 与 RoboTwin 的 `scene.observe` 结果。
新增 runtime-only `RoboTwinObservationProvider`，将 camera/depth/state capture 投影为 provider-neutral 的
observation identity、frame、calibration、freshness 与 typed artifact refs；支持外部 runtime capture seam
和注入式 `RoboTwin20Adapter` seam。PAOS 仍不包含 RoboTwin、SAPIEN、Torch 或模型导入；Fake Gateway
artifact ref 校验支持 capture 子路径，并新增一致性集成测试。

### Validation

- `244 passed in 2.53s` for adapter/workflow tests.
- Ruff, compileall, and `git diff --check` passed.
- External RoboTwin20 `--format scene_observe` smoke returned the expected observation reference and RGB/depth/state artifacts; OIDN CUDA warnings remain a known runtime risk.
- `.codegraph/` and `.cursor/` remain untracked and were not staged.

## [v2.8.4] - 2026-09-02

Fixed the external RoboTwin runtime working-directory boundary in
`examples/forge-adapters/robotwin20/runtime/robotwin_backend.py:L88-L101,L119-L120,L179-L184,L208-L209,L223-L224`.
Official imports, `setup_demo`, `get_obs`, and `close_env` now run under the
runtime checkout and restore the caller's cwd. This removes the real smoke
failure caused by RoboTwin's relative `assets/objects/objaverse/list.json`
lookup when launched from the PAOS root. Added the regression test at
`tests/test_robotwin_backend_contract.py:L55-L65`.

修复独立 RoboTwin runtime 的工作目录边界：官方导入、场景初始化、观测读取和关闭均在外部 runtime checkout
上下文中执行并恢复调用方 cwd，消除从 PAOS 根目录启动时的相对资产路径错误。新增 cwd 回归测试；不改变
PAOS 依赖、ToolSpec 或动作权限。

## [v2.8.3] - 2026-09-02

Added the runtime-only `RoboTwinSensorBackend` at
`examples/forge-adapters/robotwin20/runtime/robotwin_backend.py:L1-L338` and
 contract tests at `tests/test_robotwin_backend_contract.py:L1-L77`. The backend
uses the official task's rendered RGB/depth and joint/end-effector state,
persists calibration and typed external artifacts, and injects through the
provider-neutral `RoboTwin20Adapter`. It rejects simulator truth channels and
never calls action/evaluator APIs. A real `beat_block_hammer/demo_clean` seed-0
capture produced 240x320 RGB/depth artifacts; SAPIEN OIDN CUDA warnings remain a
known runtime risk.

新增 runtime-only `RoboTwinSensorBackend`，通过 provider-neutral `RoboTwin20Adapter` 暴露真实 RGB/depth/state
artifact 与 calibration；不导出 actor/segmentation truth，不调用动作或 evaluator。真实 seed-0 capture 已验证，
但 OIDN CUDA warning 仍是运行时风险。

## [v2.8.2] - 2026-09-02

Added the standard-library fail-closed preflight at
`examples/forge-adapters/robotwin20/src/robotwin20_adapter/preflight.py:L1-L284`,
its tests at `tests/test_preflight.py:L1-L75`, and the `robotwin20-preflight`
entry point in `pyproject.toml:L1-L13`. The user-provided external RoboTwin20
environment passed all 16 checks (`ready=true`), including assets, CUDA
`sm_120`, SAPIEN, Vulkan, and task import, without modifying PAOS dependencies.

新增只使用标准库的 fail-closed preflight 与测试及 console entry point。用户提供的隔离 RoboTwin20 环境 16 项
检查全部通过（`ready=true`），包含官方 assets、CUDA `sm_120`、SAPIEN、Vulkan 与 task import；PAOS 依赖未被污染。

## [v2.8.1] - 2026-09-02

Verified the isolated `RoboTwin20` conda environment and checked out the official RoboTwin 2.0 source with
its pinned `XPolicyLab` submodule under `/home/yanxu/robotwin20-runtime/RoboTwin`. Confirmed the official asset
source is the Hugging Face dataset `TianxingChen/RoboTwin2.0`; only `embodiments.zip` was downloaded and verified.
The large `background_texture.zip` and `objects.zip` archives remain for the user to download. No PAOS dependency,
wheel content, ToolSpec, Hephaestus source, or tracked simulator asset was changed.

已核对隔离 `RoboTwin20` conda 环境，并将官方 RoboTwin 2.0 源码及固定的 `XPolicyLab` 子模块 checkout 到
`/home/yanxu/robotwin20-runtime/RoboTwin`。确认官方资产来源为 Hugging Face 数据集
`TianxingChen/RoboTwin2.0`；本次仅下载并校验 `embodiments.zip`，大型 `background_texture.zip` 与
`objects.zip` 留待用户自行下载。未修改 PAOS 依赖、wheel 内容、ToolSpec、Hephaestus 源码或已跟踪仿真资产。

### Validation

- `RoboTwin20` Python `3.10.21`; SAPIEN/Torch/TorchVision/OpenCV/Gymnasium/Open3D present.
- `embodiments.zip`: `219859313` bytes, SHA-256 `6b87d7d55e106d8ff25917e0538eb1e177fc549280e8a742a8cec3cb9f953fc6`.
- Official sizes: `background_texture.zip` `10970687027` bytes; `objects.zip` `3737778549` bytes.
- `.codegraph/` and `.cursor/` remain untracked and were not staged.

## [v2.8.0] - 2026-09-02

Implemented the first RoboTwin 2.0 adapter slice: an environment-owned lifecycle seam and sensor-only observation
source that can be connected to camera/depth/state outputs without importing RoboTwin into PAOS.

### Changed

- Added an independently packaged `robotwin20` adapter with explicit backend and sensor artifact protocols.
- Requires RGB/depth/state artifacts, frame, calibration, timestamp, and scene revision; rejects missing or
  simulator-ground-truth-only observations.
- Added no-motion tests; no YOLO, SAPIEN, robot SDK, Dora, or actuator dependencies were added to PAOS.

## [v2.7.0] - 2026-09-02

Implemented the simulator-free generic capability runtime foundation for the next integration phase.

### Changed

- Added reusable ToolEndpoint registration, discovery/context, Query dispatch, and bounded Action lifecycle
  primitives under `PhyAgentOS.forge`, with provider ports defined independently of RoboTwin, SAPIEN, YOLO,
  robot SDKs, and hardware.
- Added no-motion conformance tests and documented that this phase does not implement perception models or
  physical execution.

## [v2.6.3] - 2026-09-02

Corrected the documented extension order so the independent generic capability runtime is implemented before
any RoboTwin adapter work.

### Changed

- Added the simulator-free generic ToolEndpoint/provider-port phase to the bilingual user development guides.
- RoboTwin remains a profile-selected EnvironmentAdapter and simulation ground truth remains comparison-only.

## [v2.6.2] - 2026-09-02

Renamed the six-Tool workflow Skill to `pick-place-workflow` and corrected the RoboTwin perception boundary.

### Changed

- The Skill name now describes the complete observe → understand → propose → prepare → acquire → place workflow;
  the six stable Tool IDs are unchanged.
- PAOS v1.0 still requires an independent generic capability runtime. RoboTwin actor/entity truth, segmentation,
  object metadata, internal poses, and `check_success()` are simulation comparison/acceptance facts only; real
  deployment must use sensor artifacts and replaceable perception providers.
- Renamed `examples/forge-skills/scene-observe/` to `examples/forge-skills/pick-place-workflow/` and synchronized
  package imports, tests, manifest, and runtime discovery fixtures.

### Validation

- `220 passed`; `ruff check`; `compileall`; and `git diff --check` passed.
- No Dora, real Gateway server, RoboTwin, hardware, or motion route was started.

## [v2.6.1] - 2026-09-02

Saved and reviewed the RoboTwin adapter refactor diagnosis, separating reusable capability runtime semantics
from environment-specific adapters.

### Added

- Added `docs/forge/ROBOTWIN_ADAPTER_REFACTOR_DIAGNOSIS.md` with ownership boundaries, six-Tool migration seams,
  clean-room reimplementation rules, profile strategy, and acceptance gates.

### Changed

- Added diagnosis links to the Forge contract and documentation index.

### Security

- Documentation-only change; no Hephaestus, PAOS runtime, Gateway implementation, simulator, hardware, or motion path changed.

## [v2.6.0] - 2026-09-02

Clarified the v1.0 PAOS boundary for simulator integration and corrected the RoboTwin execution order.

### Changed

- Skills expose provider-neutral ToolSpecs and workflow guidance; RoboTwin 2.0 remains an independent
  Gateway/ToolEndpoint/Dora/simulator runtime.
- Documented that RoboTwin task, SAPIEN, embodiment, and benchmark configuration belongs in the adapter/profile,
  while a Skill Bundle freezes only runtime wiring and locked artifacts.

### Security

- Documentation-only change; no PAOS runtime, Gateway implementation, simulator, hardware, or motion path changed.

## [v2.5.3] - 2026-09-02

Added a reusable v1.0 feature-reference-card method for planning and reviewing PAOS extensions.

### Added

- Added `docs/forge/FEATURE_REFERENCE_CARDS.md`, linking normative documentation, selected extension points, ownership, failure semantics, implementation modules, tests, and PR traceability.

### Security

- Documentation-only change; no Gateway, Runtime, simulator, hardware, or motion path changed.

## [v2.5.1] - 2026-09-02

Backfilled the v2.5.0 verification-context commit and root index record.

### Changed

- Recorded commit `d6f6a74` and synchronized the bilingual monthly log with the root index.

### Security

- Documentation-only change; no runtime, Gateway, simulator, hardware, or motion path changed.

## [v2.5.0] - 2026-09-02

Added bound AgentTask verification-context integration coverage.

### Added

- Added an integration test that routes bound Query and bounded Action execution facts through
  `VerificationRequestBuilder` into the generic verifier context.
- Verified frozen binding/revision/invocation identity, execution-fact-only capability projections,
  opaque capability artifact references, and the absence of motion authorization in verifier input.

### Security

- The test uses only the Fake Gateway no-motion path and starts no Dora, simulator, hardware, or
  motion route.

## [v2.4.0] - 2026-09-02

Added ExperienceCoordinator recovery-episode integration coverage.

### Added

- Added tests confirming one recovered AgentTask becomes one processed TaskEpisode with preserved
  `replan_required → success` lineage delivered to the analyzer.
- Added assertions that capability facts alone do not create Skill candidates or Lesson clusters.

### Security

- Recovery episode tests execute no real Action, Session, Dora, hardware, or motion route.

## [v2.3.0] - 2026-09-02

Added generic AgentTask verification and recovery coverage.

### Added

- Added deterministic verifier tests for `replan_required`, append-only PlanRevision recovery, and
  final success on the same AgentTask.
- Verified recovered TaskEpisode lineage preserves both the replan-required and successful
  revisions.

### Security

- Recovery tests execute only Fake Gateway Queries and do not create motion, Session, or Dora
  execution.

## [v2.2.0] - 2026-09-02

Added governed execution record coverage after immutable Skill binding.

### Added

- Added a bound Query and bounded Action integration test through `AgentTaskCoordinator` and the
  standard Forge Tool API.
- Verified binding ID, revision ID, ToolSpec digest, invocation/attempt references, and capability
  outcome summary on persisted records.

### Security

- Execution remains on the Fake Gateway no-motion path; no real robot or simulator is invoked.

## [v2.1.0] - 2026-09-02

Added activation-to-AgentTask immutable binding integration coverage for the scene-observe Skill.

### Added

- Added tests connecting `SkillActivationManager`, `ForgeSkillBindingResolver`, and
  `AgentTaskCoordinator` through one primary Skill activation and frozen binding.
- Added fail-closed coverage for Runtime identity drift before governed Query access.

### Security

- The integration performs no Action, Session, Dora, hardware, or motion execution.

## [v2.0.0] - 2026-09-02

Added immutable Forge Skill binding coverage for the provider-neutral scene-observe Bundle.

### Added

- Added preview/freeze tests for manifest, SKILL document, Runtime identity, and all required
  ToolSpec hashes.
- Added fail-closed validation tests for Runtime replacement and ToolSpec tampering after binding.

### Security

- Binding tests execute no Action or Session and do not start Dora, hardware, or motion routes.

## [v1.9.0] - 2026-09-02

Added Runtime controller switch and rollback protection coverage.

### Added

- Added tests that block Skill Runtime switching while an AgentTask is non-terminal.
- Added rollback coverage for failed target startup and atomic active-registry replacement after a
  healthy target check.

### Security

- Tests use fake catalog/manager state only and start no Dora, Gateway, simulator, hardware, or
  motion route.

## [v1.8.0] - 2026-09-02

Added HTTP health-contract coverage for the RuntimeManager's Gateway and required Tool context
checks.

### Added

- Added a localhost-only HTTP fixture exercising real `RuntimeManager.status()` `/tools` and
  required `/context` reads.
- Added fail-closed verification that a missing or unavailable Tool context persists Runtime state
  as `failed` and prevents active-runtime publication.

### Security

- The test starts no Dora flow, hardware process, simulator, or motion route.

## [v1.7.0] - 2026-09-02

Added manifest-v2 Bundle installation and healthy Runtime discovery coverage for the
provider-neutral scene-observe Skill.

### Added

- Added isolated archive install/reload tests through `SkillInstaller` and `SkillCatalog`.
- Added fail-closed discovery tests for a single running runtime with all Tool contexts ready and
  for non-ready runtime states.

### Changed

- Marked the no-binary fake profile as `artifacts.resolver: local`; registry resolution remains
  reserved for Bundles with explicit Node locks.

## [v1.6.0] - 2026-09-02

Added a full no-motion AgentTask workflow integration fixture for the provider-neutral
scene-observe Bundle.

### Added

- Added an end-to-end test using `AgentTaskCoordinator -> ForgeToolClient -> FakeGatewayTransport`
  across observe, understand, propose, prepare, acquire, and place.
- Verified one task/revision, terminal Query/Action records, capability outcome projection, and
  synchronous `ExperienceCoordinator` `TaskEpisode` persistence.
- Covered non-terminal finalization rejection, unknown-action resend blocking, and cancellation
  reconciliation without introducing a second execution protocol or RoboTwin dependency.

## [v1.5.0] - 2026-09-02

Skill candidate support is now partitioned by bounded capability failure-owner scope. Successful
episodes with different scopes create independent candidates and cannot share promotion counts.

### Changed

- Added `capability_failure_owners` to `SkillCandidate`.
- Included owner scope in candidate identity and support matching while preserving legacy empty-scope
  compatibility and existing promotion thresholds.

## [v1.4.0] - 2026-09-02

Active Lesson counterexamples now require an exact capability failure-owner scope match. Mismatched
or scoped/legacy-missing scopes are recorded diagnostically and cannot retire or weaken a Lesson.

### Changed

- Added bounded owner-scope persistence to `ScopedLesson` and exact-scope counterexample checks.
- Preserved legacy behavior when both Lesson and episode have empty owner scopes.

## [v1.3.0] - 2026-09-02

Lesson activation now validates cross-episode capability failure-owner scope. Same-owner
observations may aggregate, while different-owner or scoped/legacy mixtures remain blocked before
synthesis and activation.

### Changed

- Added bounded owner-scope validation to LessonCluster synthesis and direct activation paths.
- Added idempotent `lesson_cluster_attribution_blocked` diagnostics without changing task verdicts,
  Tool API behavior, or Skill promotion thresholds.

## [v1.2.0] - 2026-09-02

Lesson clusters now retain a bounded capability failure-owner scope. Cross-episode observations
with different explicit root-cause owners cannot merge into one reusable Lesson pattern.

### Changed

- Added owner-scope persistence to `FailureObservation` and `LessonCluster`.
- Cluster matching rejects mismatched non-empty capability owner scopes while preserving the
  existing Skill/workflow scope and unique root-task support rules.

## [v0.9.0] - 2026-09-02

Capability outcome facts now flow from verified AgentTask execution records into the experience
and Skill-evolution input without changing task verdict authority or Forge execution boundaries.

### Added

- Added versioned `CapabilityOutcomeFact` and bounded `CapabilityOutcomeErrorFact` records to
  `TaskOutcomeEnvelope`.
- Added AgentTask outcome-source projection with provider-private Tool ID filtering and tests for
  redaction, unknown/failed states, malformed summaries, and diagnostic errors.

### Changed

- Experience analysis now receives only provider-neutral phase/status/owner/world-change/evidence
  facts. Artifact URIs and failure codes remain excluded, and facts/errors cannot authorize
  verdicts, learnability, or Skill/Lesson promotion.

## [v0.8.0] - 2026-09-02

Added a generic verification-layer projection for versioned Forge capability outcomes. The
projection exposes execution facts to AgentTask verification without creating a second execution
protocol or authorizing task success.

### Added

- Added `PhyAgentOS.verification.outcome_projection` for terminal Action summaries, including
  bounded validation of status, capability phase, failure ownership, evidence availability,
  opaque artifact references, metric names, and post-release evidence.
- Added AgentTask verifier-context fields for capability outcome projections and bounded projection
  errors while preserving the existing evidence allowlist and verdict flow.
- Added 14 projection tests covering valid outcomes, malformed summaries, unknown/failure paths,
  post-release evidence, missing summaries, and request-builder integration.

### Changed

- Documented the `execution_fact_only` authority boundary and fixed
  `task_success_authorized=false`; only `TaskVerificationContract` and the generic verifier may
  produce a user-level task verdict.

### Security

- Gateway artifact references remain opaque and are never promoted into `valid_evidence_refs`.
- Projection performs no Gateway calls, motion admission, retry, or PlanRevision mutation.

## [v1.0.0] - 2026-08-30

Initial stable release of PhyAgentOS.

### Security

- Upgraded `@whiskeysockets/baileys` to `7.0.0-rc14` to address
  `CVE-2026-48063` / `GHSA-qvv5-jq5g-4cgg`, and locked the Bridge dependency graph.

## [v0.2.3] - 2026-08-27

PhyAgentOS can run independently distributed Forge Skills through a task-scoped, immutable
Skill/Runtime/ToolSpec binding while keeping Gateway as the execution authority.

### Added

- Added first-class Query, Action, and Session Tool API lifecycles, including Session ownership,
  status/result reconciliation, and owned stop behavior.
- Added activation-time binding previews and task-time frozen bindings containing exact Skill
  version, manifest and workflow hashes, Runtime/Gateway identity, ToolSpec hashes, and Node locks.
- Added crash recovery that reconciles persisted invocation IDs using reads only, plus
  version-scoped Forge experience and Lessons.
- Added deterministic Skill bundle packaging and exact single-executable Node archive locks.
- Added the optional Bundle startup hook
  `bash <bundle>/start.sh <skill-name> <skill-version>` and supplies `PAOS_SKILL_NAME` and
  `PAOS_SKILL_VERSION` to rendered dataflows and Dora process environments.

### Changed

- Forge Gateway selection now comes only from one explicitly started, healthy installed Skill
  Runtime; static `forge.enabled`, `forge.baseUrl`, and `forge.apiVersion` selectors are rejected.
- Runtime state uses schema v2 so Runtime/Gateway identities, Session references, task bindings,
  and force-stop audit records are mandatory and stable across restarts.
- Action admission persists a PAOS-generated caller ID and intent before the remote request.
  Timeouts and unknown results cannot trigger an automatic POST retry.
- Runtime stop and switching account for active invocations, Sessions, and task bindings; forced
  stop records an audit event.
- Resource Registry Skill lookup uses the name endpoint. `paos skill install --version` validates
  the downloaded manifest as a client-side constraint before Node resolution and installation
  commit; schema-v3 static indexes retain version selection.
- Runtime environment identity now covers the selected dataflow path and profile file digests, so
  configuration edits and dataflow-path changes rematerialize the environment.
- Expanded the bilingual integration guide with Bundle packaging, local validation, immutable
  Node/Bundle publication order, and Registry acceptance guidance.

### Fixed

- Forge Node downloads accept Registry responses that omit duplicate digest and size fields. The
  verified Skill lock remains the digest authority, while the direct-download endpoint supplies
  the content length before the archive is downloaded and checked.
- Documented the Dora CLI v0.4.1 and `dora-message` v0.7.0 Forge Skill compatibility baseline,
  version-pinned installation methods, PATH and lifecycle checks, and RuntimeManager's automatic
  local Dora service startup.
- Startup-hook failures, missing Bash, and execution errors now persist a `failed` lifecycle state
  and diagnostic log before Dora can start, rather than leaving stale or unstarted state.
- Start, stop, install/update commit, and removal now use a non-blocking cross-process lock per
  Skill, preventing overlapping lifecycle mutations while allowing automatic release on process
  exit.

### Removed

- Removed the concrete Forge Skill, simulation profile, and remote bundle-fetch helper from the
  PhyAgentOS distribution. Forge Skills and their nodes, models, and assets are installed
  independently when required.

### Security

- Skill and Node downloads require exact size and SHA-256 metadata, archive extraction remains
  bounded and link-safe, and mutations require task ownership plus live binding revalidation.
- Unknown remote effects retain Runtime safety guards until explicit operator resolution.

## [v0.2.2] - 2026-08-21

PhyAgentOS now uses one Forge Query/Action Tool API execution plane while retaining Agent verification, experience, evolution, and the existing general-purpose tool platform.

### Added

- Added the AgentTask lifecycle tools `forge_task_create`, `forge_task_get`, `forge_task_begin_revision`, `forge_task_finalize`, and `forge_task_cancel` with one global non-terminal task, immutable PlanRevisions, bound Query records, Action invocation references, evidence, and aggregate verification.
- Added the Forge Tool API tools `forge_tool_context`, `forge_tool_query`, `forge_tool_start_action`, `forge_tool_action_status`, `forge_tool_action_result`, and `forge_tool_cancel_action` for bound and unbound Query/Action calls.
- Added the manifest-v2 Skill Runtime, catalog, archive validation, transactional installation, persistent runtime state, Resource Registry support, and `paos skill` / `paos forge-node` lifecycle commands.
- Added the built-in `move-arm-by-ee` v0.2 Skill with a MuJoCo profile, relative-pose Query, motion Action, gripper Action, ToolSpecs, and independently locked Forge nodes.
- Added backward-compatible AgentTask, PlanRevision, ToolInvocation, and attempt references to task experience and evolution records.

### Changed

- Robot execution now follows `AgentTask-bound or unbound call → ForgeToolClient → Gateway /tools → ToolInvocation → ToolEndpoint → Dora/robot`; operation `max_concurrency` remains the execution concurrency authority.
- Task verification now aggregates all calls bound to one AgentTask. A recovery verdict appends a bounded PlanRevision to the same task and continues through the existing verification and evolution policies.
- Skill discovery now combines workspace, installed, and built-in Skills. A healthy active Runtime contributes availability and its manifest `gateway_url` takes precedence over `forge.baseUrl`.
- `ForgeConfig` now represents `forge-tool-api.v1`; Resource Registry configuration is available through `resourceRegistry.url` or `PAOS_RESOURCE_REGISTRY_URL` and never triggers an implicit unconfigured download.
- Existing Agent tools, dynamic MCP tools, verification contracts, experience storage, evolution storage, and Skill activation remain available with their existing contracts.

### Removed

- Removed the PAOS Forge Session execution path and the seven Session-specific Agent tools: `forge_execute_task`, `forge_get_session`, `forge_cancel_session`, `forge_get_context`, `forge_reset`, `verify_forge_session`, and `create_replanned_forge_session`.
- Removed the built-in `pipergo2-demo`; `move-arm-by-ee` is the maintained robot Skill example.

### Fixed

- Cancellation acceptance, local timeout, and `unknown` invocation outcomes no longer imply that physical execution stopped and do not trigger blind retries.
- Skill and node installation now verifies SHA-256 metadata, blocks path traversal and unsafe links, validates locked node digests, and rolls back incomplete replacements.

### Security

- Runtime artifacts require verified size and digest metadata before installation; archive extraction is bounded and atomic, and no Registry download occurs without explicit configuration.

## [v0.2.1] - 2026-08-14

PhyAgentOS can turn verified Forge task outcomes into scoped, auditable workflow experience and supply activated Skill Lessons to verification as bounded, non-authoritative advice without changing the Forge execution path.

### Added

- Added explicit `activate_skill(name, role)` activation with one primary Skill, optional supporting Skills, applicable scoped Lessons, and task-to-Skill attribution.
- Added versioned task-outcome, episode, assessment, Skill candidate, failure observation, Lesson cluster, abstraction-validation, and scoped-Lesson contracts.
- Added a crash-safe SQLite WAL experience ledger, asynchronous reflection jobs, structured evolution events, Skill revision history, and generated per-Skill Lesson projections.
- Added guarded Skill creation/update after independent semantic-success support, including managed workflow blocks, workspace overrides for built-in Skills, reload validation, atomic writes, and rollback.
- Added workflow-related failure eligibility, normalized observation clustering, independent root-lineage support, Lesson synthesis, and abstraction validation.

### Changed

- Skill summaries now direct the Agent to activate a matching workflow before tool execution when evolution is enabled; direct `SKILL.md` reads are not treated as activation.
- Learned Lessons are loaded dynamically with the activated Skill. The root `LESSONS.md` remains available as legacy/human-authored material but is no longer injected globally while evolution is enabled.
- Forge verification uses the active scoped Lessons frozen with the root task's explicit Skill activations. Evolution mode never reads root `LESSONS.md` for automatic verification or review, and tasks without an activated Skill receive no learned Lesson context.
- Verifier prompts treat Lessons as untrusted, non-authoritative workflow advice that cannot establish criterion status, replace execution evidence, or appear as evidence references.
- Failures caused by unsatisfiable tasks, verifier/evidence limits, infrastructure, user constraints, or uncertain attribution remain diagnostic-only.
- Built-in Skills remain immutable; promoted revisions are written as workspace overrides and only the PAOS-managed workflow block is replaced on later updates.

### Security

- Experience records redact endpoint-, credential-, path-, executable-ID-, and action-assignment-shaped data and persist only workflow structure, input field names, opaque evidence references, and immutable record references.
- Lesson and Skill policies reject task-specific answers, fixed coordinates/values, credentials, endpoints, Gateway IDs, Action Manifest copies, prompt injection, and instructions that bypass Forge or verification.
