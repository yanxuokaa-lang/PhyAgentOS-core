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

Focused tests cover two successive scene revisions, no backend recreation, stale rejection, held-object exclusion, unchanged readiness evidence limits and JSONL identity. No new real model or simulator-motion experiment was performed in this checkpoint.
