# Changelog
## v13.1.15 (2026-10-10 14:50) - codex

### 变更摘要 / Summary [计划]
- [policy] [fix] 仅从当前 active revision 判断 unresolved world，避免后续 revision 被历史 unknown Action 阻塞。 (local)
- [Policy] [Fix] Detect unresolved world effects only from the active revision so later revisions are not blocked by superseded unknown Actions. (local)
- [eval] [test] 覆盖当前 revision 与旧 revision 的不同生命周期行为。 (local)
- [Eval] [Test] Cover distinct lifecycle behavior for current- and superseded-revision unknown effects. (local)
- [eval] [test] 七维审查后 focused suites `257 passed`；补充 Store 事务 payload 回归，Ruff、compileall、diff check 通过。 (local)
- [Eval] [Test] After the seven-dimension review, focused suites passed (`257`); add the Store transaction payload regression, with Ruff, compileall, and diff check passing. (local)
- [policy] [fix] 七维复审补齐 late known settlement 语义，避免同一 revision 已解析的 unknown 继续阻塞恢复。 (local)
- [Policy] [Fix] Complete late-known-settlement semantics in the seven-dimension review so a resolved unknown in the same revision cannot keep recovery blocked. (local)
- [eval] [test] Focused suites `258 passed`；Ruff、compileall、diff check 通过；no-motion。 (local)
- [Eval] [Test] Focused suites passed (`258`); Ruff, compileall, and diff check passed; no-motion. (local)

详见 [2026-10 part5 v13.1.15](changelog/2026-10_part5.md)。See the detailed v13.1.15 record.

## v13.1.14 (2026-10-10 14:00) - codex

### 变更摘要 / Summary
- [policy] [fix] 修复未知世界变化恢复在多 capability `scene.observe` 上错误回退模型，并在世界未对账时保持同一 AgentTask 的 `awaiting_replan` 所有权。 (local)
- [Policy] [Fix] Fix unknown-world recovery falling back to the model for multi-capability `scene.observe`, and retain the same AgentTask in `awaiting_replan` while reconciliation is unresolved. (local)
- [eval] [test] Core recovery/planning/long-horizon/Skill suites `255 passed`；Ruff、compileall、diff check 通过；no-motion。 (local)
- [Eval] [Test] Core recovery/planning/long-horizon/Skill suites passed (`255`); Ruff, compileall, and diff check passed; no-motion. (local)

### 文件与关键 Diff / Files and key diff
- `PhyAgentOS/agent/recovery_decisions.py:L18-L67`：单一 refresh Tool 优先使用 `tool_id`，忽略其辅助 capability；多 Tool 保持 fail-closed。 / Prefer the single refresh Tool's `tool_id`, ignore auxiliary capabilities, and keep multiple Tools fail-closed.
- `PhyAgentOS/forge/task.py:L2729-L2785,L4316-L4341`：未知世界未完成对账时 `fail_replan` 保持 `awaiting_replan`，防止新任务绕过 Runtime 状态。 / Keep `awaiting_replan` when world reconciliation is unresolved so new tasks cannot bypass Runtime state.
- `tests/test_agent_foundation.py:L2424-L2490`、`tests/test_planning_loop.py:L2152-L2185`：多 capability 恢复和 unresolved world 生命周期回归。 / Add multi-capability recovery and unresolved-world lifecycle regressions.
- `docs/forge/UNKNOWN_WORLD_RECONCILIATION_DIAGNOSIS_20261010.md:L1-L75`：保存三次任务的证据链、根因与通用修复边界。 / Preserve the evidence chain, root causes, and generic fix boundaries for all three tasks.

详见 [2026-10 part5 v13.1.14](changelog/2026-10_part5.md)。See the detailed v13.1.14 record.

## v13.1.13 (2026-10-10 13:40) - codex

### 变更摘要 / Summary
- [env] [chore] 按用户授权强制停止旧 Runtime，刷新 checkout editable Core，安装 Skill `3.0.15` 与 Node `1.0.5`，再启动 `robotwin-blocks-ranking-graspnet`。 (local)
- [Env] [Chore] Under user authorization, force-stop the old Runtime, refresh the checkout editable Core, install Skill `3.0.15` and Node `1.0.5`, then start `robotwin-blocks-ranking-graspnet`. (local)
- [eval] [test] Runtime/Dora running，Gateway 与 11/11 Tool contexts ready；runtime-lock SHA=`b4a6d431798a3d8bf5eb43501e733404b49c48ec6ea0c7e21b88f8debd17fd09`；任务库非终态为 0，全程无 Query/Action、相机、simulator 或物理运动。 (local)
- [Eval] [Test] Runtime/Dora running, Gateway and 11/11 Tool contexts ready; runtime-lock SHA is recorded; zero non-terminal tasks and no Query/Action, camera, simulator, or physical motion. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-skills/pick-place-workflow/skill.yaml:L1-L3,L220-L229`、`pyproject.toml:L1-L5`：Skill `3.0.14` → `3.0.15`，Node `1.0.4` → `1.0.5`。 / Bump Skill and Node versions.
- `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py:L261-L275`、`examples/forge-skills/pick-place-workflow/CHANGELOG.md:L1-L8`：同步锁版本测试与发布说明。 / Align lock-version tests and release notes.
- `changelog/2026-10_part5.md`：保存停止、安装、启动、runtime-lock、readiness、任务计数和 no-motion 证据。 / Record stop, install, start, runtime-lock, readiness, task counts, and no-motion evidence.

```diff
- Skill 3.0.14 / Node 1.0.4
+ Skill 3.0.15 / Node 1.0.5
+ Runtime running / Gateway ready / 11 of 11 Tool contexts ready
```

详见 [v13.1.13 月度日志](changelog/2026-10_part5.md)。See the [v13.1.13 detailed log](changelog/2026-10_part5.md).
- Commit: `6d35c56` on `feature/planning-loop`.

## v13.1.12 (2026-10-10 13:28) - codex

### 变更摘要 / Summary
- [sense] [fix] 将非数值、复数或截断的 observed support point cloud 统一报告为结构化 evidence failure，避免格式损坏退化为 generic provider failure。 (local)
- [Sense] [Fix] Report non-numeric, complex, or truncated observed-support point clouds as structured evidence failures instead of generic provider failures.
- [eval] [test] Adapter `114 passed`; Core recovery/planning `272 passed`; Ruff、compileall、diff check passed；no-motion。 (local)
- [Eval] [Test] Adapter `114 passed`; Core recovery/planning `272 passed`; Ruff, compileall, and diff check passed; no-motion.

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py:L948-L972`：读取时捕获 EOFError，先验证实数数值 dtype 再运行 finite 检查。 / Catch EOFError and validate real numeric dtype before finite checks.
- `examples/forge-adapters/robotwin20/tests/test_grounding.py:L1253-L1306`：覆盖字符串点云与截断读取的 evidence failure。 / Cover evidence failures for string point clouds and truncated reads.

```diff
- np.isfinite(points) on any loaded dtype; truncated read escapes as generic error
+ classify EOF and non-real numeric arrays as observed_support_unavailable
```

详见 [v13.1.12 月度日志](changelog/2026-10_part5.md)。See the [v13.1.12 detailed log](changelog/2026-10_part5.md).
- Commit: `f0697f5` on `feature/planning-loop`.

## v13.1.11 (2026-10-10 13:10) - codex

### 变更摘要 / Summary
- [policy] [fix] 按当前 revision 中同一 Query 节点的最新执行记录识别 evidence refresh，避免历史 evidence failure 污染后续错误恢复。 (local)
- [Policy] [Fix] Classify evidence refresh from the latest execution record for the same Query node in the current revision, preventing historical evidence failures from contaminating later recovery.
- [eval] [test] Core 272、Adapter 112、Skill 88 tests passed；Ruff、compileall、diff check passed；no-motion。 (local)
- [Eval] [Test] Core 272, Adapter 112, and Skill 88 tests passed; Ruff, compileall, and diff check passed; no-motion.

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/agent/recovery_decisions.py:L66-L87`：只使用最新 Query execution record 判定 evidence refresh。 / Classify evidence refresh from the latest Query execution record only.
- `tests/test_agent_foundation.py:L2566-L2591`：验证后续 provider failure 不被旧 evidence failure 覆盖。 / Verify a later provider failure is not overridden by an earlier evidence failure.

```diff
- any historical evidence-failure record triggers scene refresh
+ only the latest same-revision/node Query result can trigger scene refresh
```

详见 [v13.1.11 月度日志](changelog/2026-10_part5.md)。See the [v13.1.11 detailed log](changelog/2026-10_part5.md).
- Commit: `1c6db08` on `feature/planning-loop`.

## Archive
- [2026-10 part4](changelog/2026-10_part4.md)
- [2026-10 part5](changelog/2026-10_part5.md)
- [2026-10 part3](changelog/2026-10_part3.md)
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v13.1.10 (2026-10-10 12:42) - codex

### 变更摘要 / Summary
- [sense] [fix] 仅在当前观测 metric geometry 完全一致时合并重复 semantic support refs；真实不同或不完整的支撑证据结构化为 evidence failure。 (local)
- [Sense] [Fix] Merge duplicate semantic support refs only when current-observation metric geometry is exactly identical; classify distinct or incomplete support evidence as an evidence failure. (local)
- [policy] [fix] `manipulation.prepare` evidence failure 进入确定性 scene-refresh replacement revision，不再被 generic provider error 直接终止；不重放 Action。 (local)
- [Policy] [Fix] Route `manipulation.prepare` evidence failures into a deterministic scene-refresh replacement revision instead of terminal generic provider failure; no Action replay. (local)
- [eval] [test] Adapter/Skill/Core focused suites `112 + 88 + 271` passed；Ruff、compileall、diff check passed；全程 no-motion。 (local)
- [Eval] [Test] Adapter/Skill/Core focused suites `112 + 88 + 271` passed; Ruff, compileall, and diff check passed; validation was no-motion throughout. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py:L920-L978`：同几何 support alias 归一化及 evidence error。 / Same-geometry support alias normalization and evidence error.
- `PhyAgentOS/agent/recovery_decisions.py:L65-L81,L180-L211,L251-L294`：Query evidence failure 的 deterministic scene refresh recovery。 / Deterministic scene-refresh recovery for Query evidence failure.
- `docs/forge/PREPARATION_SUPPORT_AMBIGUITY_DIAGNOSIS_20261010.md:L1-L111`：证据、根因、七维 review 与 no-motion 边界。 / Evidence, root cause, seven-dimension review, and no-motion boundary.

```diff
- multiple semantic support refs raised plain ValueError and were flattened to preparation_provider_error
+ identical current metric point clouds are auditable aliases; distinct geometry returns evidence recovery fields
+ Query evidence failure creates one fresh scene-observation revision; no Action replay or motion authorization
```

详见 [v13.1.10 月度日志](changelog/2026-10_part5.md) 和 [诊断](docs/forge/PREPARATION_SUPPORT_AMBIGUITY_DIAGNOSIS_20261010.md)。
See the [v13.1.10 detailed log](changelog/2026-10_part5.md) and [diagnosis](docs/forge/PREPARATION_SUPPORT_AMBIGUITY_DIAGNOSIS_20261010.md).

## v13.1.9 (2026-10-10 12:10) - codex

### 变更摘要 / Summary
- [env] [chore] 按授权强制停止未包含当前 Core 修复的旧 Runtime，刷新 checkout editable Core，核对 Skill `3.0.14` / Node `1.0.4` runtime-lock，并用既有 profile 重启。 (local)
- [Env] [Chore] Force-stop the old Runtime without the current Core repair, refresh the checkout editable Core, verify the Skill `3.0.14` / Node `1.0.4` runtime lock, and restart with the existing profile. (local)
- [eval] [chore] Runtime、Dora、Gateway 与 11/11 Tool contexts ready；保留唯一 `awaiting_replan` 任务，未创建 AgentTask、调用 Query/Action、读取相机、推进 simulator 或产生运动。 (local)
- [Eval] [Chore] Runtime, Dora, Gateway, and all 11 Tool contexts are ready; the sole `awaiting_replan` task was preserved, with no AgentTask, Query/Action, camera, simulator, or motion activity. (local)

### 文件与关键 Diff / Files and Key Diff
- `changelog/2026-10_part5.md:L584-L615`：记录 stop/install/start 命令、Core 导入路径、runtime-lock SHA、readiness、任务状态和 no-motion 边界。 / Records commands, Core import path, runtime-lock SHA, readiness, task state, and no-motion boundary.

```diff
- Runtime process started before the current Core repair
+ old Runtime force-stopped; editable Core refreshed; Skill 3.0.14 / Node 1.0.4 lock verified
+ Runtime/Dora/Gateway running and 11/11 Tool contexts ready; awaiting_replan task preserved
```

详见 [v13.1.9 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.9 detailed log](changelog/2026-10_part5.md).
- Commit: `3832220` on `feature/planning-loop`.

## v13.1.8 (2026-10-10 11:30) - codex

### 变更摘要 / Summary
- [policy] [fix] 为通用 `scene.bind` planning node 投影当前成功 understanding 的候选实体、歧义范围和 selection 行动契约；不自动选择、不放宽 binding 或 motion gate。 (local)
- [Policy] [Fix] Project current successful understanding candidates, ambiguity scope, and selection action contract into generic `scene.bind` planning nodes; do not auto-select or relax binding or motion gates. (local)
- [policy] [fix] 将空 `ambiguity.entity_refs` 按全局歧义处理，Core 在 Gateway 前拒绝非空 selection；修复 selection 测试替身的现有 Coordinator record-reader 接口。 (local)
- [Policy] [Fix] Treat empty `ambiguity.entity_refs` as global ambiguity, reject non-empty selections before Gateway, and align the selection test double with the existing Coordinator record-reader interface. (local)
- [eval] [test] 新增当前/过期/缺失理解证据及全局歧义 no-motion 回归；377 个 Core/Tool/selection 测试与 54 个 recovery 测试通过。 (local)
- [Eval] [Test] Add current/stale/absent understanding and global-ambiguity no-motion regressions; 377 Core/Tool/selection tests and 54 recovery tests pass. (local)

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/agent/planning_loop.py:L115-L131,L294-L430,L510-L539,L1340-L1348`：新增 bounded `scene_bind_selection` projection，并把行动指引加入 node prompt。 / Add bounded projection and actionable node guidance.
- `PhyAgentOS/agent/prompt_context.py:L410-L460`：统一全局 ambiguity 的推荐与 scope。 / Align global ambiguity recommendations and scope.
- `PhyAgentOS/agent/tools/forge_tool_api.py:L985-L1030`：`scene.bind` preflight 拒绝全局歧义下的非空选择。 / Reject non-empty selections under global ambiguity.
- `tests/test_planning_loop.py:L343-L469`、`tests/test_agent_foundation.py:L2816-L2876`、`tests/test_prompt_context.py:L607-L628`：新增候选投影、过期/缺失证据与空范围歧义回归。 / Add projection, stale/absent evidence, and empty-scope ambiguity regressions.
- `tests/test_planning_selection.py:L103-L110`：测试 Coordinator 提供现有 `effective_planning_execution_records` 接口。 / Align the test Coordinator with the existing record-reader interface.
- `docs/forge/SCENE_BIND_SELECTION_CONVERGENCE_DIAGNOSIS_20261010.md:L1-L136`：保存证据、七维审查与 no-motion 边界。 / Preserve evidence, seven-dimension review, and no-motion boundary.

```diff
- node prompt exposed catalogs and prose-only scene.bind constraints
+ node prompt exposes current authorized candidates, ambiguity scope, and one governed selection action
- empty ambiguity scope was treated as an empty intersection
+ empty ambiguity scope yields no recommendations and rejects non-empty selection before Gateway
```

详见 [v13.1.8 月度日志](changelog/2026-10_part5.md) 和 [诊断](docs/forge/SCENE_BIND_SELECTION_CONVERGENCE_DIAGNOSIS_20261010.md)。
See the [v13.1.8 detailed log](changelog/2026-10_part5.md) and [diagnosis](docs/forge/SCENE_BIND_SELECTION_CONVERGENCE_DIAGNOSIS_20261010.md).
- Commit: `4893664` on `feature/planning-loop` (implementation, review, and tests).

## v13.1.7 (2026-10-10 10:30) - codex

### 变更摘要 / Summary
- [comm] [fix] 将包含 task/revision/node/frame-scoped preparation URI 的 RobotWin persistent-host Node 从 `1.0.3` 发布为 `1.0.4`，Skill 从 `3.0.13` 发布为 `3.0.14`；manifest lock 更新为 Node SHA `e884cbe5bcf208d00a25674b49cd170d46f2efb5e4ab8bcd05de692b407daa20`。 (local)
- [Comm] [Fix] Publish the RobotWin persistent-host Node containing task/revision/node/frame-scoped preparation URIs as `1.0.4`, bump the Skill from `3.0.13` to `3.0.14`, and update the manifest lock to Node SHA `e884cbe5bcf208d00a25674b49cd170d46f2efb5e4ab8bcd05de692b407daa20`. (local)
- [eval] [test] 新增从当前 Adapter/Workflow 源码重建 Node 并校验 manifest lock 的发布回归；本次 release/contract/preparation/action 与 persistent-host/deployment focused suites 共 `238 passed`。 (local)
- [Eval] [Test] Add a release regression that rebuilds the Node from current Adapter/Workflow sources and checks the manifest lock; the release/contract/preparation/action and persistent-host/deployment focused suites pass with `238 passed`. (local)
- [env] [chore] 按授权强停旧 Runtime，安装 Skill `3.0.14` 与 Node `1.0.4`，用原 profile 环境启动；Runtime/Dora/Gateway running/ready，11/11 Tool contexts ready。 (local)
- [Env] [Chore] Under authorization, force-stop the old Runtime, install Skill `3.0.14` and Node `1.0.4`, and start with the existing profile environment; Runtime/Dora/Gateway are running/ready with 11/11 Tool contexts ready. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-skills/pick-place-workflow/skill.yaml:L1-L4,L219-L229`: Skill `3.0.13` -> `3.0.14`; Node `1.0.3` -> `1.0.4` and lock SHA updated.
- `examples/forge-skills/pick-place-workflow/pyproject.toml:L1-L3`: package version `3.0.13` -> `3.0.14`.
- `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py:L261-L274`: assert Skill/package/Node lock alignment.
- `examples/forge-skills/pick-place-workflow/tests/test_release_bundle.py:L21-L27,L73-L87`: rebuild current Node source and compare its SHA/artifact ID to the manifest lock.
- `examples/forge-skills/pick-place-workflow/CHANGELOG.md:L3-L9`: record Node/Skill release boundary.
- `docs/forge/PREPARATION_NODE_DEPLOYMENT_DIAGNOSIS_20261010.md:L1-L66`: preserve three-task evidence, ownership analysis, and live deployment result.

```diff
- Skill 3.0.13 -> Node 1.0.3 (old immutable artifact)
+ Skill 3.0.14 -> Node 1.0.4 (rebuilt from current Adapter source)
- source-only release check
+ rebuild-and-lock SHA regression plus 238 focused no-motion tests
```

详见 [v13.1.7 月度日志](changelog/2026-10_part5.md)和[诊断](docs/forge/PREPARATION_NODE_DEPLOYMENT_DIAGNOSIS_20261010.md)。
See the [v13.1.7 detailed log](changelog/2026-10_part5.md) and [diagnosis](docs/forge/PREPARATION_NODE_DEPLOYMENT_DIAGNOSIS_20261010.md).
- Commit: `06e3cd9` on `feature/planning-loop` (implementation and release artifacts).

## v13.1.6 (2026-10-10 00:45) - codex

### 变更摘要 / Summary
- [env] [chore] 在授权下强制停止旧 Runtime，刷新 checkout Core，将已安装 Skill 从不一致的 `3.0.12` 发布为 `3.0.13`，并启动 `robotwin-blocks-ranking-graspnet` 新 Runtime。 (local)
- [Env] [Chore] Under authorization, force-stop the old Runtime, refresh the checkout Core, publish the inconsistent installed Skill from `3.0.12` to `3.0.13`, and start the new `robotwin-blocks-ranking-graspnet` Runtime. (local)
- [eval] [test] 新 bundle SHA-256=`529c265a2ec5d2f264e460a4e7ab822973eba8d16c65f056719c9c21ce5dfb33`；Runtime/Dora/Gateway running/ready，11/11 Tool contexts ready；无 AgentTask、Query/Action、simulator 或物理运动。 (local)
- [Eval] [Test] New bundle SHA-256 is recorded; Runtime/Dora/Gateway are running/ready with 11/11 Tool contexts ready; no AgentTask, Query/Action, simulator, or physical motion was used. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-skills/pick-place-workflow/skill.yaml:L1-L4` and `pyproject.toml:L1-L5`: `3.0.12` → `3.0.13`.
- `examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py:L270`: bundle/package version assertion updated.
- `changelog/2026-10_part5.md`: exact stop/install/start commands, bundle path/SHA, readiness, task-store and no-motion boundaries.

```diff
- installed pick-place-workflow 3.0.12 did not contain the reviewed Action contract
+ installed pick-place-workflow 3.0.13 contains the reviewed frame-lineage fix
- Runtime old process
+ Runtime 3.0.13 profile running; Gateway /tools ready; 11/11 contexts ready
```

详见 [v13.1.6 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.6 detailed log](changelog/2026-10_part5.md).
- Commit: `3751c18` on `feature/planning-loop`.

## v13.1.5 (2026-10-10 00:30) - codex

### 变更摘要 / Summary
- [policy] [fix] 七维 Code Review 修复 `object.acquire`/`object.place` 只校验 preparation scene、未校验 terminal frame 的 lineage 缺口；同一 scene 下跨观察帧 URI 现在 fail-closed。 (local)
- [Policy] [Fix] The seven-dimension review fixed the lineage gap where `object.acquire`/`object.place` checked only the preparation scene and not its terminal frame; cross-frame URIs in one scene now fail closed. (local)
- [eval] [test] 增加跨帧拒绝回归；目标 Core/Skill/Adapter suite `134 passed`，Ruff、compileall、`git diff --check` 通过。 (local)
- [Eval] [Test] Add cross-frame rejection regressions; the targeted Core/Skill/Adapter suite has `134 passed`, with Ruff, compileall, and `git diff --check` passing. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py:L38-L43,L420-L428`
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_place.py:L9-L14,L440-L447`
- `examples/forge-skills/pick-place-workflow/tests/test_object_acquire.py:L242` and `test_object_place.py:L166-L170`

```diff
- preparation_ref scene matched, frame component was not checked
+ preparation_ref scene and terminal frame both match the observation lineage
```

详见 [v13.1.5 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.5 detailed log](changelog/2026-10_part5.md).
- Implementation commit: `e1526e9`; log/index commit: `bbcc941` on `feature/planning-loop`.

## v13.1.4 (2026-10-10 00:00) - codex

### 变更摘要 / Summary
- [comm] [fix] Core/RobotWin 生成 task/revision/node-scoped preparation identity，解决跨任务 route geometry collision；Action route 保持 source scene 校验。 (local)
- [Comm] [Fix] Core/RobotWin now generate task/revision/node-scoped preparation identities to prevent cross-task route-geometry collisions while Action routes retain source-scene validation. (local)
- [eval] [test] 增加同输入幂等、跨任务隔离、scoped URI 与 `node_selection_no_progress` no-motion 回归；无 Runtime、AgentTask 或物理运动。 (local)
- [Eval] [Test] Add idempotency, cross-task isolation, scoped-URI, and `node_selection_no_progress` no-motion regressions; no Runtime, AgentTask, or physical motion was used. (local)

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/forge/capability_runtime/manipulation_prepare.py:L32-L56,L545-L562`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_preparation.py:L246-L249`
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py` and `object_place.py` preparation binding checks

```diff
- preparation://{scene_revision}/{frame_id}
+ preparation://{scene_revision}/{task_id}/{revision_id}/{node_id}/{frame_id}
```

详见 [v13.1.4 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.4 detailed log](changelog/2026-10_part5.md).

## v13.1.3 (2026-10-09 23:00) - codex

### 变更摘要 / Summary
- [env] [chore] 在用户授权下停止旧 Runtime，完成当前 checkout 的 editable Core 安装，复核 `pick-place-workflow 3.0.12` payload，并使用既有 operator-owned profile environment 启动新的 `robotwin-blocks-ranking-graspnet` Runtime。 (local)
- [Env] [Chore] Under user authorization, stop the old Runtime, install the checkout Core in editable mode, verify the `pick-place-workflow 3.0.12` payload, and start the new `robotwin-blocks-ranking-graspnet` Runtime with the existing operator-owned profile environment. (local)
- [eval] [test] 启动后只做状态验收：Runtime/Dora/Gateway 与 11/11 Tool context ready；任务库无非终态任务，未创建 AgentTask、调用 Query/Action、读取相机或推进物理运动。 (local)
- [Eval] [Test] Post-start validation only checked Runtime/Dora/Gateway and 11/11 Tool contexts ready; the task store has no non-terminal tasks, and no AgentTask, Query/Action, camera read, or physical motion was performed. (local)
- Git commit: `55478bc` on `feature/planning-loop`; detailed deployment record is in `changelog/2026-10_part5.md`.

### 文件与关键 Diff / Files and Key Diff
| 对象 / Object | 位置 / Location | 结果 / Result |
| --- | --- | --- |
| PAOS Core | `PhyAgentOS/` | editable import from current checkout |
| Skill | `pick-place-workflow 3.0.12` | local installer returned `already ready` |
| Runtime | `pick-place-workflow:robotwin-blocks-ranking-graspnet` | running; Dora running; Gateway ready |
| Task store | `/home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3` | non-terminal tasks = 0 |
| Detailed log | `changelog/2026-10_part5.md` | v13.1.3 deployment, exact runtime state, and no-motion boundary |

```diff
- Runtime stopped; Dora down; Gateway unavailable
+ Runtime running; Dora flow running; Gateway /tools ready; 11/11 Tool contexts ready
  Core editable-installed; Skill 3.0.12 unchanged; no live task or motion during validation
```

详见 [v13.1.3 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.3 detailed log](changelog/2026-10_part5.md).

## v13.1.1 (2026-10-09 21:20) - codex

### 变更摘要 / Summary
- [env] [chore] 使用既有 operator-owned profile environment 启动新安装的 `pick-place-workflow 3.0.12`，恢复 `robotwin-blocks-ranking-graspnet` Runtime、Dora flow 与 Gateway readiness。 (local)
- [Env] [Chore] Start the newly installed `pick-place-workflow 3.0.12` with the existing operator-owned profile environment, restoring `robotwin-blocks-ranking-graspnet` Runtime, Dora flow, and Gateway readiness. (local)
- [env] [chore] readiness 验收覆盖 11 个 required Tool context，未创建 AgentTask、调用 Query/Action、推进 simulator 或产生物理运动；无 env-file 的首次启动被 PAOS preflight 安全拒绝。 (local)
- [Env] [Chore] Readiness validation covered all 11 required Tool contexts without creating an AgentTask, invoking Query/Action, advancing the simulator, or producing physical motion; the first start without an env-file was safely rejected by PAOS preflight. (local)

### 文件与关键 Diff / Files and Key Diff
| 对象 / Object | 位置 / Location | 结果 / Result |
| --- | --- | --- |
| Runtime environment | `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env` | 复用既有 operator-owned 配置，不记录 secret / Reused operator-owned configuration without recording secrets |
| Runtime | `pick-place-workflow:robotwin-blocks-ranking-graspnet` | `running`；Dora `running`；Gateway `ready` / Running; Dora running; Gateway ready |
| Tools | Gateway `/tools` | 11/11 required contexts ready / 11/11 required contexts ready |
| 任务库 / Task store | `/home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3` | 非终态任务=`0` / non-terminal tasks=`0` |
| 日志 / Log | `changelog/2026-10_part5.md` L3-L45 | 双语启动、预检失败分支和无运动验收 / Bilingual startup, preflight-failure branch, and no-motion validation |

```diff
- Runtime stopped; Gateway unavailable; Agent sees no ready Forge Skill runtime
+ Runtime running; Gateway ready; all 11 required Tool contexts ready
  no AgentTask, live Query/Action, simulator advancement, or physical motion during readiness check
```

详见 [v13.1.1 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.1 detailed log](changelog/2026-10_part5.md).

## v13.1.0 (2026-10-09 21:04) - codex

### 变更摘要 / Summary
- [env] [chore] 按明确授权强制停止旧 `pick-place-workflow` Runtime，并刷新当前仓库的 editable `PhyAgentOS-ai 1.0.2` Core，使 unknown-world scene-refresh bootstrap 修复由 `paos` CLI 加载。 (local)
- [Env] [Chore] Force-stop the old `pick-place-workflow` Runtime under explicit authorization and refresh the checkout's editable `PhyAgentOS-ai 1.0.2` Core so the `paos` CLI loads the unknown-world scene-refresh bootstrap repair. (local)
- [env] [chore] 核对已安装 Skill 仍为已验证的 `3.0.12` payload；部署后保持 Runtime stopped、Dora down、Gateway unavailable，未执行 live Query/Action 或推进 simulator。 (local)
- [Env] [Chore] Confirm that the installed Skill remains the verified `3.0.12` payload; keep the Runtime stopped, Dora down, and Gateway unavailable after deployment, with no live Query/Action or simulator advancement. (local)

### 文件与关键 Diff / Files and Key Diff

| 对象 / Object | 位置 / Location | 结果 / Result |
| --- | --- | --- |
| PAOS Core | `PhyAgentOS/agent/recovery_decisions.py` L11-L62, L219-L250 | editable install 从当前 checkout 导入恢复逻辑 / Editable install imports the recovery logic from this checkout |
| Skill | `pick-place-workflow 3.0.12` | installer 返回 `already ready`；payload 未变 / Installer returned `already ready`; payload unchanged |
| Runtime | `robotwin-blocks-ranking-graspnet` | stopped；Dora down；Gateway unavailable；非终态任务 0 / Stopped; Dora down; Gateway unavailable; zero non-terminal tasks |
| 日志 / Log | `changelog/2026-10_part5.md` L3-L58 | 完整双语部署记录 / Complete bilingual deployment record |

```diff
- old Runtime running against the previous process lifetime
+ old Runtime force-stopped; editable Core refreshed from the repaired checkout
  Skill payload remains verified version 3.0.12
  no Runtime restart, live Action, simulator advancement, or physical motion
```

详见 [v13.1.0 月度日志](changelog/2026-10_part5.md)。
See the [v13.1.0 detailed log](changelog/2026-10_part5.md).

## v13.0.15 (2026-10-09 19:22) - codex

### 变更摘要 / Summary
- [docs] [docs] 新增 Laya/Jev System 1 入口意图与路由正式对比报告，覆盖 RLCD 原理、80 条数据与样例、分类/可用性/概率指标、失败分析和 PAOS 适用边界。(local)
- [docs] [docs] Add the formal Laya/Jev System 1 intent-routing report covering RLCD principles, the 80-case dataset and examples, classification/availability/probability metrics, failure analysis, and PAOS applicability boundaries. (local)
- [eval] [feat] 为 Decisions、Laya 和 Jev scorer 增加共享的 10-bin ECE、multiclass Brier、NLL 与 probability coverage，并用已有原始响应重算全部 development/evaluation 结果。(local)
- [eval] [feat] Add shared 10-bin ECE, multiclass Brier, NLL, and probability coverage to the Decisions, Laya, and Jev scorers, then rescore every development/evaluation run from preserved raw responses. (local)

### 文件与关键 Diff / Files and Key Diff
`research/decision-api-intent-probe/{decision,jev,laya}_intent_probe.py`, probability-metric tests,
`docs/forge/SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md`, and the existing
result summary.

```diff
+ shared probability-distribution validation and normalization
+ intent/route ECE-10, multiclass Brier, NLL, and probability coverage
+ formal report with RLCD, dataset examples, metrics, failures, and replacement boundary
- do not count Jev timeouts inside valid-response probability metrics
```

详见 [v13.0.15 月度日志](changelog/2026-10_part4.md)和[正式实验报告](docs/forge/SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md)。
See the [v13.0.15 detailed log](changelog/2026-10_part4.md) and [formal experiment report](docs/forge/SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md).

## v13.0.14 (2026-10-09 18:36) - codex

### 变更摘要 / Summary
- [policy] [fix] 对 Runtime 明确声明的未知世界变化，使用冻结 ToolSpec 中唯一可空绑定的 `refreshes_scene` Query capability 建立场景刷新 bootstrap revision；不 replay 原 Action，不推断实体位姿或持有状态。 (local)
- [Policy] [Fix] For an explicit Runtime-declared unknown world change, bootstrap a scene-refresh revision from the one bindable `refreshes_scene` Query capability in frozen ToolSpecs; never replay the original Action or infer entity pose or possession. (local)
- [eval] [test] 增加 no-motion Core/Skill-loop 回归与七维审查，修复随机/固定恢复节点 ID 的幂等性与 settlement 继承风险。 (local)
- [Eval] [Test] Add no-motion Core/Skill-loop regressions and a seven-dimension review, fixing idempotency and settlement-inheritance risks from random or fixed recovery node IDs. (local)
- [docs] [docs] 保存 `task_f6fcda0556d14245` 的 910-step lift failure、Runtime recovery facts、视频 manifest、失败链、PAOS ownership 与通用修复边界。 (local)
- [Docs] [Docs] Preserve the 910-step lift failure, Runtime recovery facts, video manifest, failure chain, PAOS ownership, and generic repair boundary for `task_f6fcda0556d14245`. (local)

### 文件与关键 Diff / Files and Key Diff

| 文件 / File | 行号 / Lines | 摘要 / Summary |
| --- | --- | --- |
| `PhyAgentOS/agent/recovery_decisions.py` | L11-L62, L219-L250 | 唯一 refresh capability 发现、Query-only replan、确定性冲突安全节点 ID / Unique refresh capability discovery, Query-only replan, deterministic collision-safe node ID |
| `tests/test_agent_foundation.py` | L28-L32, L2339-L2544 | bootstrap、歧义、旧绑定、identity 回归 / Bootstrap, ambiguity, stale-binding, and identity regressions |
| `examples/forge-skills/pick-place-workflow/tests/test_unknown_action_recovery.py` | L12-L24, L61-L155, L307-L364 | 完整 PlanningLoop 新 revision 无运动回归 / Full PlanningLoop replacement-revision no-motion regression |
| `docs/forge/UNKNOWN_ACTION_REFRESH_BOOTSTRAP_DIAGNOSIS_20261009.md` | L1-L161 | 诊断、架构边界与七维审查 / Diagnosis, architecture boundary, and seven-dimension review |
| `changelog/2026-10_part5.md` | v13.0.14 | 完整双语记录 / Complete bilingual record |

```diff
- unknown world-changing Action -> model must return complete replacement graph
+ unknown world-changing Action -> unique ToolSpec refresh Query bootstrap revision
+ same source revision -> stable node identity
+ source-node collision -> first free deterministic suffix
+ ambiguous or stale-bound refresh capability -> existing fail-closed model path
```

### 验证 / Validation
- Recovery-focused Core/AgentLoop/Skill suites: `263 passed in 13.64s`.
- Ruff、compileall、`git diff --check` 通过；没有 live AgentTask、Gateway、simulator 或物理运动。 / Ruff, compileall, and `git diff --check` pass; no live AgentTask, Gateway, simulator, or physical motion was run.

详见 [v13.0.14 月度日志](changelog/2026-10_part5.md)和[诊断](docs/forge/UNKNOWN_ACTION_REFRESH_BOOTSTRAP_DIAGNOSIS_20261009.md)。
See the [v13.0.14 detailed log](changelog/2026-10_part5.md) and [diagnosis](docs/forge/UNKNOWN_ACTION_REFRESH_BOOTSTRAP_DIAGNOSIS_20261009.md).
