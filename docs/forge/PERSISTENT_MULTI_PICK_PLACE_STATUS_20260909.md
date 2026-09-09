# Persistent multi-object integration: v7.7.0 checkpoint

日期 / Date: 2026-09-09. 本文记录已实现和已验证范围，完整接入未验收。
This checkpoint records implemented and verified scope. Full integration is not accepted.

## 六维验收 / Six-dimensional acceptance

依据：`MANIPULATION_DAG_DEVELOPER_GUIDE.md`、`PLANNING_MODULE_DESIGN.md`、开发手册及前两轮接入审核。
The normative ownership remains Coordinator for tasks/revisions, Gateway for invocation identities,
adapter for physical state and route geometry, and Verifier for user-level success.

| 维度 / Dimension | 已修复 / Fixed | 剩余验收问题 / Open acceptance issue |
| --- | --- | --- |
| 架构集成 / Architecture | 通用 ActionAdmission 增加 provider driver；七个正式 Tool 注册；保持语义 DAG | Blocker: deployment factory/Runtime Bundle and current-scene preparation are not wired |
| 失败路径 / Failures | cancel 直接通知 provider；timeout 保留 unknown；失联不自动重建世界 | Blocker: physical drop/restart reconciliation and task recovery not demonstrated |
| 权限安全 / Authority | provider 持物 owner、entity、acquire ID 接续；原执行器运动检查保留 | Blocker: persistent execution profile and complete-route motion qualification not delivered |
| 配置复现 / Reproducibility | 独立解释器、唯一产物目录、模型预算和失败记录 | Model requests timed out; no real Agent multi-object experiment completed |
| 可维护性 / Maintainability | 原 phase executor 提取 generator，单次 probe 兼容；无第二任务调度器 | Current engine reuses private probe helpers; public deployment composition needs completion |
| 可观察性 / Observability | 嵌套 unknown 一致；停止错误及失败放置误差保留；未知结果不产生 placed 证据 | No final multi-goal Verifier or goal-disturbance recovery evidence |

本轮修复可按下列命令回归；整个方案仍不通过最终验收。
The repairs have focused regression coverage; the full integration remains unaccepted.

## 持久执行语义 / Persistent execution semantics

- `empty -> acquiring -> holding -> placing -> empty`; uncertain physical outcomes become `uncertain`.
- Only the task owner may place the entity held by the referenced acquisition. A second acquire is rejected while holding, moving, or uncertain.
- All engine construction, sensor queries and simulation operations run on one worker thread. Queries cannot overlap motion; scene facts and possession are projected together.
- Acquire pauses the existing validated phase generator after lift. Place continues the same attached route. Physics is paused between Actions; this is simulation behavior, not a hardware hold guarantee.
- The original preparation observation/candidate/calibration stays bound. Place separately resolves the current scene and acquisition identity. The second object requires new geometry from the post-place scene.
- A cancel acknowledgement is not physical completion. Provider results retain known/unknown effects; lost transport is latched unavailable instead of silently starting a new simulator.
- Closing destroys only the isolated simulation. It never opens a held gripper as a cleanup action.

## 真实运行证据 / Actual run evidence

External artifact root: `/home/yanxu/robotwin20-runtime/artifacts/`.

- `paos-persistent-v770-sensors-20260909`: one persistent world, two different RGB/depth captures, same scene revision, empty holding state; no motion.
- `paos-persistent-v770-understanding-20260909`: initial script passed artifact objects instead of URI strings; image input failed before inference. Fixed in the script.
- `paos-persistent-v770-understanding-r2-20260909`: image resolved; real Responses request ended in `APITimeoutError`. Failure result and worker log persisted.
- `paos-persistent-v770-understanding-r3-20260909`: 90-second timeout, no SDK retries, reasoning low, 2048 output tokens; also `APITimeoutError`. No understanding result or motion success claimed.
- `paos-persistent-v770-public-observation-20260909`: final public Observation Tool validation run; inspect its result JSON for measured outcome.

The old single-object successful probe remains single-object evidence. Fake-engine tests do not prove physics, model interpretation, or Agent task completion.

## 验证命令 / Validation commands

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin \
 tests/test_capability_runtime_driver.py tests/test_planning_module.py \
 tests/test_planning_loop.py tests/test_planning_dispatch.py tests/test_planning_end_to_end.py \
 tests/test_tui_long_horizon.py tests/test_planning_effect_recovery.py \
 tests/test_gateway_dora_no_motion_conformance.py \
 examples/forge-skills/pick-place-workflow/tests examples/forge-adapters/robotwin20/tests
```

```bash
PYTHONPATH=.:examples/forge-adapters/robotwin20/src \
/home/yanxu/miniconda3/envs/paos/bin/python \
 examples/forge-adapters/robotwin20/scripts/check_persistent_runtime.py \
 --runtime-root /home/yanxu/robotwin20-runtime/RoboTwin \
 --runtime-profile "$PWD/examples/forge-adapters/robotwin20/profiles/robotwin20/franka-blocks-ranking.yaml" \
 --artifact-root "/home/yanxu/robotwin20-runtime/artifacts/persistent-$(date +%Y%m%dT%H%M%S)" \
 --worker-python /home/yanxu/miniconda3/envs/RoboTwin20/bin/python
```

Add `--paos-config /home/yanxu/.PhyAgentOS/config.json` for actual scene understanding.
Credentials are resolved privately; the smoke runner exposes model timeout/reasoning/token limits.

## 未交付依赖 / Remaining dependencies

1. Integrate current-scene preparation and approved route artifacts into the live Query provider. The current standalone materializer requires a fresh empty output root and defaults to reset-on-failure; it cannot be reused unchanged for held continuation.
2. Ground opaque model entity references in measured geometry, including repeated colors. The current benchmark actor map only supports three named block identities. Simulator actor facts must not be presented as model perception.
3. Add the deployment factory/profile and formal Skill Runtime Bundle, then exercise actual AgentLoop and Coordinator through live Tool APIs.
4. Implement final multi-goal Verifier evidence and run two successive objects in one world, cancellation, drop, restart, repeated identity, and disturbed-previous-goal recovery. Do not promote the checkpoint to full acceptance until these results exist.

## v7.7.1 assignment repair

The follow-up review found that persistent execution retained an assignment URI but the shared executor still selected the first feasible arm. PreparedRoutes now loads the existing typed ArmAssignment, checks source/route bindings, and passes its selected arm through task-owned admission. The worker checks the persisted assignment and enforces that arm for complete-route qualification; failure cannot silently fall back to another arm. Place must retain the acquisition assignment.

PreparedRoutes is constructed in the PAOS Python environment with `(client, artifact_root)`; the Python 3.10 simulation process does not import it. Existing assignment and per-step artifact checks are reused. No new authorization scheme is introduced.

Focused assignment/executor/endpoint tests: 62 passed. This closes the assigned-arm execution defect, not the outstanding deployment or real Agent acceptance items above.

## v7.8.0 current-scene readiness connection

`RoboTwinRouteEvaluator(..., backend=...)` now evaluates the existing world without resetting or closing it. It rejects stale request/world/source-fact revisions and checks the route's geometry against the live actors before configuring the planner. The default standalone evaluator still owns its own reset/close lifecycle.

The persistent worker exposes the adapter-private `route_readiness` query. `build_persistent_route_readiness(client)` sends it over the existing world connection and feeds its reply through the existing RouteReadinessClient validator. Outer JSONL request identity is preserved separately from the nested route identity. While holding or uncertain, new route preparation is rejected; observation and snapshots remain available.

This is the current-world evaluator connection, not the complete `manipulation.prepare` deployment factory. Contact dynamics and stop control remain unavailable in no-motion readiness results. Public preparation/assignment generation, formal Bundle and real Agent continuous multi-object execution remain outstanding.

## v8.1.1 evolution composition root

The PAOS host now exposes `compose_evolution_extension` as the standard
composition entry point. It reuses the existing `ExperienceCoordinator` store
and candidate lifecycle, accepts an explicitly selected extension or explicit
registry/projection ports, persists extension events, and is idempotent. Missing
optional extension packages or invalid construction remain fail-open. This
completes the host wiring seam only; it does not claim promotion, physical
execution, or real multi-object Agent evidence.

Focused tests cover two successive scene revisions, no backend recreation, stale rejection, held-object exclusion, unchanged readiness evidence limits and JSONL identity. No new real model or simulator-motion experiment was performed in this checkpoint.

## v7.9.0 public preparation and adapter composition

The optional `intent`, `destination_ref`, and `capability_snapshot_ref` inputs to
`manipulation.prepare` must be supplied together. Results contain existing typed
`ArmAssignment` records for exactly the prepared candidates, bound to the task,
node, source observation, capabilities, allowed arms, and readiness evidence.
Legacy preparation requests remain supported. Query success grants no motion.

`robotwin20_adapter.persistent_preparation.PersistentPreparationProvider` composes
the existing route selector and assignment projector with `PreparedRoutes`.
Inject it as `preparation_provider` and the same cache as `resolve_preparation`
into `pick_place_workflow.persistent_runtime.build_persistent_runtime`.
Its injected `route_builder.build(request)` must return `destination_ref`,
`base_request`, and the existing enumerated `options`, grounding the destination
in calibrated geometry. Selection uses complete readiness evidence. The adapter
checks the live empty scene before and after selection, persists the assignment,
and registers geometry without approval. `PreparedRoutes.bind_approval` attaches
an externally issued execution approval; the execution worker still validates it.
Repreparing identical geometry preserves an existing approval. Changed selection
under the same assignment reference requires a new task revision/node reference.

Six-dimensional review: architecture keeps selection in the adapter and task
ownership in PAOS; failure paths reject changed scenes, holdings, destinations,
and unbound assignments; authority remains separate from Query; configuration
uses injected dependencies and the existing profiles; maintainability reuses
selection/projection and artifact naming; observability retains readiness refs
and persisted assignments. Tests are composition evidence, not physical proof.

Still required for deployment: a current-scene route builder (the standalone
materializer currently requires an empty artifact root), capability provider and
formal Bundle factory, model entity-to-measured-geometry grounding, and real
Agent continuous multi-object execution plus final goal verification. The
no-motion evaluator cannot claim contact/stop dynamics readiness. No new model
or simulator-motion run was performed for this checkpoint.

## v7.10.0 current-scene route builder and capabilities

`PersistentRouteBuilder` runs the existing `materialize_complete_route.py` CLI
for each proposed candidate using the supplied interpreter, static profile and
controller qualification arguments. Dynamic scene facts, proposal bundle and
output directory are owned by the builder. Each build keeps its inputs, command
and subprocess logs under `preparation-builds/route-*`. Current scene and empty
holding state are checked before/after materialization. Requested destinations
must match the selected entity's scene-fact target, and generated routes must
retain candidate, scene, calibration and destination bindings.

Artifact import preserves original references and compares existing bytes before
publishing; conflicting data is rejected rather than replacing runtime evidence.
Multiple candidates reuse equivalent shared calibration/controller artifacts.
`BenchmarkSceneSource(client)` explicitly reads simulator benchmark facts and
requires `allow_benchmark_scene_facts=true`; it does not implement model entity
grounding. Deployments may supply another measured scene source.

`PersistentCapabilityProvider` projects the configured arm profile into a typed
scene-bound snapshot, persists it under `artifact://capabilities/`, reuses it for
identical requests and rejects obsolete scene revisions. Pass the existing
deployment profile digest explicitly. Inject this provider and the route builder
into the preparation/runtime composition described above. The materializer
arguments use its existing CLI option names without leading `--`; its command
is `[python_executable, materializer_script]`, with a finite timeout in seconds.

The builder is tested with a controlled materializer, not yet with current model
grasp output. Its static route profile must use `hold_and_reconcile` for persistent
execution; the standalone reset profile is not execution-compatible. Selection
also changes the request identity; selected-route source manifest/review
materialization must be finalized before execution approval. This remains an
open execution integration requirement, not permission to reuse old approvals.

Real smoke `paos-persistent-v7100-understanding-20260909T1707` produced two captures
from one world and an available public Observation Tool result. Scene understanding
returned `understanding_provider_error`; motion remained false. The smoke runner
now records the underlying provider exception class without raw exception text.
Formal Bundle, selected-route finalization, model geometry grounding, complete
readiness evidence and real Agent multi-object task verification remain open.

## v8.0.0 selected route finalization and deployment components

The persistent builder now finalizes the selected request after the selector
adds its option ID. It writes the final route, source manifest and pending review
under `artifact://selected-routes/<request-id>/`, preserving the original
materializer outputs. Existing artifact digests are recomputed for those changed
records, and source manifest bytes must match the original review. The preparation
provider registers the review reference and exposes it as preparation evidence.
Finalization failure prevents assignment/cache publication. No approval is issued.

`profiles/robotwin20/route-inputs-persistent.yaml` retains the existing GraspGen
geometry settings and uses `hold_and_reconcile`. The standalone reset profile
remains available for independent probes. `build_persistent_deployment` requires
the persistent stop policy and constructs the builder, selector, capability
provider and shared cache with one caller-owned client. Compose the Skill with:

```python
deployment = build_persistent_deployment(
    client=client, artifact_root=artifact_root, scene_source=scene_source,
    materializer_command=materializer_command,
    materializer_arguments=materializer_arguments,
    arm_profile_digest=arm_profile_digest,
)
runtime = build_persistent_runtime(
    client=client, understanding_provider=understanding_provider,
    grasp_provider=grasp_provider, **deployment.runtime_arguments(),
    tool_context_provider=tool_context_provider,
)
```

The default readiness evaluator uses the live persistent world and retains
unavailable contact/stop evidence. A complete-evidence evaluator can be injected
through the existing interface. The factory does not create another task loop,
grant motion authority or own client shutdown. Benchmark scene projection now
also removes JSONL `ok`/`request_id` envelope fields.

This closes selected-request artifact identity and provider composition only.
Formal Skill Bundle lifecycle/registration, complete readiness, model entity
grounding and real Agent continuous multi-object verification remain unaccepted.
No additional model or simulator-motion run was performed in this checkpoint.

## v8.1.0 direction review and live Tool contexts

The [direction review](MULTI_PICK_PLACE_DIRECTION_REVIEW_20260909.md) confirms
ownership and extension direction against the normative guides. It distinguishes
component delivery from formal Bundle/Agent acceptance and records two corrected
implementation findings.

`CapabilityRuntime.register_tool(..., context_provider=...)` supports live endpoint
context. Discovery and new Query/Action admission use the same projection; missing
explicit readiness or provider exceptions return ready=false. Existing invocation
poll/cancel/stop remain available. Static registrations retain their prior behavior.
`build_persistent_runtime` now requires `tool_context_provider(tool_id)` from its
host. This must report endpoint dependency/connection health without inference or
motion, independently from holding state and per-request route/approval admission.

A provider success without execution artifact refs projects to unknown with
`missing_execution_evidence`, preserves world-change facts, and emits no `placed:`
completion. No additional simulation or model run was performed in this checkpoint.
