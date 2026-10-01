# Change Log

## v2.10.5 (2026-10-01)

- 中文：保留本地 Qwen vLLM 作为 RobotWin 场景理解主路径，并将 provider fallback 统一切换为 `gpt-6.1-sol`、`reasoning_effort=high`；PAOS Agent 默认模型同步切换为 `gpt-6.1-sol/high`，不把凭据写入 Skill 或日志。
- English: Keep local Qwen vLLM as the primary RobotWin scene-understanding route and switch the provider fallback to `gpt-6.1-sol` with `reasoning_effort=high`; switch the PAOS Agent default to `gpt-6.1-sol/high` without writing credentials into the Skill or logs.

## v2.10.4 (2026-10-01)

- 中文：明确只读 Query 的 `motion_authorized=false` 是非运动证据而非授权失败；发现 Query 全部成功后必须继续计划物化，不得请求 clarification、取消任务或等待外部运动授权。
- English: Clarify that `motion_authorized=false` from a read-only Query is non-motion evidence, not an authorization failure; after discovery Queries succeed, continue to plan materialization and do not request clarification, cancel the task, or wait for external motion authorization.

## v2.10.3 (2026-10-01)

- 中文：将 benchmark `task.goal` 设为唯一放置目标来源；Agent 必须省略 `destination_ref`，不得创建 target/staging 或替代目标，由 Coordinator 在计划物化时注入并校验。
- English: Make benchmark `task.goal` the sole placement-goal source; Agents must omit `destination_ref` and may not create target/staging or replacement goals, while Coordinator injects and validates destinations during plan materialization.

## v2.10.2 (2026-09-30)

- 中文：发布 Coordinator 具名多来源 projection 支持，使 `manipulation.prepare` 从 `grasp.propose` 获取当前实体候选、从同场景 `manipulation.capabilities` 获取可用机械臂；Agent 只选择授权记录，不再组装候选或 arm 参数。
- English: Publish Coordinator named multi-source projection support so `manipulation.prepare` consumes current-entity candidates from `grasp.propose` and available arms from same-scene `manipulation.capabilities`; the Agent selects authorized records without assembling candidate or arm arguments.
- 中文：继续锁定已验证的 Node `0.10.1`（SHA-256 `5b61b5630109d676c6a29376016b50a6e135fddeab24477274b9216dd6985140`）；不改变 Runtime 感知、运动、碰撞、IK 或授权逻辑。
- English: Retain the verified Node `0.10.1` lock (SHA-256 `5b61b5630109d676c6a29376016b50a6e135fddeab24477274b9216dd6985140`) without changing Runtime perception, motion, collision, IK, or authorization logic.

## v2.10.1 (2026-09-30)

- 中文：在 GraspNet worker/provider 边界将非负 native score 上界饱和到 provider-neutral `[0,1]`，保留 `native_score` 诊断和原始排序；负分过滤、非有限值 fail-closed，IK、碰撞与动作授权不变。
- English: Saturate non-negative GraspNet native scores to the provider-neutral `[0,1]` range at the worker/provider boundary while retaining `native_score` diagnostics and native ordering; filter negative scores, fail closed on non-finite values, and leave IK, collision, and Action authorization unchanged.
- 中文：benchmark profile 将 `task.goal` 作为放置目标外部注入边界；自主 target/staging 不再作为可规划能力，Grounding 和 Coordinator 均拒绝或覆盖替代目标。`observation_owned` profile 保持自主目标规划兼容。
- English: Make `task.goal` the external placement-goal injection boundary for benchmark profiles; autonomous target/staging are no longer plannable, and Grounding/Coordinator reject or override replacement goals. Preserve autonomous planning for `observation_owned` profiles.
- 中文：发布 Node `0.10.1`，SHA-256 为 `5b61b5630109d676c6a29376016b50a6e135fddeab24477274b9216dd6985140`。
- English: Publish Node `0.10.1` with SHA-256 `5b61b5630109d676c6a29376016b50a6e135fddeab24477274b9216dd6985140`.

## v2.9.0 (2026-09-29)

- 中文：完成感知 worker 生命周期所有权：请求结束继续使用 CPU hibernate 复用，PersistentHost 终止时则显式 shutdown LocateAnything 与 SAM2 子进程；即使一个资源关闭失败，也继续关闭其余资源并最终 fail-closed。
- English: Complete perception-worker lifecycle ownership: retain CPU hibernation reuse after requests, but explicitly shut down LocateAnything and SAM2 child processes when PersistentHost terminates; continue closing remaining resources after one failure and then fail closed.
- 中文：发布 Node `0.8.15`，SHA-256 为 `5fa1d5afdb9aca2d4162a2e5464e9eeee44a9ac6e6e4f3291c0fa7ddee65420e`；依据项目版本规则，Skill patch 从 `2.8.15` 进位到 `2.9.0`。
- English: Publish Node `0.8.15` with SHA-256 `5fa1d5afdb9aca2d4162a2e5464e9eeee44a9ac6e6e4f3291c0fa7ddee65420e`; advance the Skill from `2.8.15` to `2.9.0` under the repository's patch-carry rule.

## v2.8.15 (2026-09-29)

- 中文：将隔离感知 worker 的 startup、wake、request、sleep 与 shutdown 耗时接入持久 Runtime 的专用 INFO logger；仅提升该 logger 的可见性，不提高全局日志噪声。
- English: Route isolated-perception worker startup, wake, request, sleep, and shutdown timings through a dedicated persistent-Runtime INFO logger without increasing global log verbosity.
- 中文：发布 Node `0.8.14`，SHA-256 为 `2ea8bfe46561ce6caca4b27193ebf82db7cabe580a9cdd60e7bd3cf97de840ea`；`2.8.14/0.8.13` 保持不可变。
- English: Publish Node `0.8.14` with SHA-256 `2ea8bfe46561ce6caca4b27193ebf82db7cabe580a9cdd60e7bd3cf97de840ea`; retain `2.8.14/0.8.13` as immutable artifacts.

## v2.8.14 (2026-09-29)

- 中文：为 LocateAnything 与 SAM2 增加显式 GPU sleep/wake 协议；请求阶段结束后模型迁移到 CPU 并释放 CUDA cache，下一次请求复用同一 worker 进程和已读取的 checkpoint，避免重复 Python/模块/checkpoint 冷启动。
- English: Add explicit GPU sleep/wake lifecycle support for LocateAnything and SAM2; move models to CPU and release the CUDA cache after each stage, then reuse the same worker process and already-loaded checkpoint on the next request instead of repeating Python/module/checkpoint cold start.
- 中文：该行为由 perception profile 的 `hibernate_on_release` 显式启用，默认 worker 语义保持不变；sleep/wake 失败会终止 worker 并 fail-closed，Qwen、proposal 与 segmentation 继续串行占用 GPU。
- English: Enable the behavior explicitly through perception-profile `hibernate_on_release` while preserving default worker semantics; sleep/wake failures terminate the worker and fail closed, and Qwen, proposal, and segmentation retain serial GPU ownership.
- 中文：发布 Node `0.8.13`，SHA-256 为 `5304500c3da536fb1c1e42ae2829c2e65d736de8441645014b52370d755423e8`。
- English: Publish Node `0.8.13` with SHA-256 `5304500c3da536fb1c1e42ae2829c2e65d736de8441645014b52370d755423e8`.

## v2.8.13 (2026-09-29)

- 中文：将多视角语义关系限定为最多 8 条最高置信、非冗余、非传递关系，并在生成 schema、模型提示和 Adapter 投影三层一致执行；全部可见实体仍保持开放世界枚举。
- English: Bound multi-view semantic relations to at most 8 highest-confidence, non-redundant, non-transitive relations and enforce the rule consistently in the generation schema, model prompt, and Adapter projection while retaining open-world enumeration of all visible entities.
- 中文：真实双图 A/B 请求从 1536-token 截断恢复为 826-token 完整 JSON，识别红、蓝、绿方块及支撑面；发布 Node `0.8.12`，SHA-256 为 `eff451481315dea34ff54a17aac24eb7dbb602fe385096ed0d8974e3ea3d2989`。
- English: The live two-image A/B request moved from 1536-token truncation to complete 826-token JSON recognizing red, blue, and green cubes plus the support surface; publish Node `0.8.12` with SHA-256 `eff451481315dea34ff54a17aac24eb7dbb602fe385096ed0d8974e3ea3d2989`.

## v2.8.12 (2026-09-29)

- 中文：将持久 Qwen 场景理解的输出预算从 768 提升到 1536；真实双图请求的 prompt 为 397 tokens，总预算仍低于 2048 context，避免实体与关系 JSON 在 768 tokens 处截断。
- English: Raise the persistent Qwen scene-understanding output budget from 768 to 1536; the live two-image prompt used 397 tokens, keeping the total below the 2048 context while preventing entity/relation JSON truncation at 768 tokens.
- 中文：Provider 显式识别 `finish_reason=length` 并报告输出预算截断；发布 Node `0.8.11`，SHA-256 为 `652d8b96e5cd1ce32a22fabf62fde36624e232c0c5af1c52d09a1fccbe61c3c1`。
- English: Make the Provider explicitly report `finish_reason=length` as output-budget truncation; publish Node `0.8.11` with SHA-256 `652d8b96e5cd1ce32a22fabf62fde36624e232c0c5af1c52d09a1fccbe61c3c1`.

## v2.8.11 (2026-09-29)

- 中文：修复本地 Qwen vLLM 的结构化输出兼容性：生成侧 JSON Schema 不再使用 xgrammar 不支持的 `uniqueItems`，Adapter 投影层继续严格拒绝重复 `source_view_indexes`。
- English: Fix local Qwen vLLM structured-output compatibility by removing xgrammar-unsupported `uniqueItems` from the generation schema while retaining strict duplicate `source_view_indexes` rejection in the Adapter projection layer.
- 中文：发布包含该兼容修复的 Node `0.8.10`，SHA-256 为 `28d7c59c742933b6c1ea900bc697178572266711c30808ff046e30f186b3bcb2`；旧 `2.8.10`/`0.8.9` artifact 保持不可变。
- English: Publish Node `0.8.10` with the compatibility fix, SHA-256 `28d7c59c742933b6c1ea900bc697178572266711c30808ff046e30f186b3bcb2`; prior `2.8.10`/`0.8.9` artifacts remain immutable.

## v2.8.10 (2026-09-29)

- 中文：新增 runtime-profile-owned `additional_static_cameras` 扩展点，在不修改第三方 RoboTwin checkout 的情况下为 embodiment 实例化额外的渲染 RGB-D 相机；配置身份、向量有限性和原生名称冲突均 fail-closed。
- English: Add the runtime-profile-owned `additional_static_cameras` extension to instantiate extra rendered RGB-D cameras without modifying the third-party RoboTwin checkout; configuration identity, finite vectors, and native-name collisions fail closed.
- 中文：为通用 Franka 双臂 profile 启用原生 `front_camera`，使 `camera/head + camera/front` 同步观察在真实 Runtime 中可用；发布 Node `0.8.9`，SHA-256 为 `5fff258c5ef99eabbdc0909b55178399586ea5d350e115cbcc655c52fb662e9f`。
- English: Enable native `front_camera` in the general dual-Franka profile so synchronized `camera/head + camera/front` observations are available in the live Runtime; publish Node `0.8.9` with SHA-256 `5fff258c5ef99eabbdc0909b55178399586ea5d350e115cbcc655c52fb662e9f`.

## v2.8.9 (2026-09-29)

- 中文：发布通用同步多视角场景观测与多图 Qwen/OpenAI 语义理解；metric RGB-D 仍仅由 primary view 生成，secondary-only 实体不伪造三维几何。
- English: Release general synchronized multi-view scene observation and multi-image Qwen/OpenAI semantic understanding; metric RGB-D remains primary-view-only and secondary-only entities do not receive fabricated 3D geometry.
- 中文：发布 Runtime terminal `scene_effects`、Coordinator 所有的未变化实体 carry-forward，以及持物状态下只读 grounding/preparation/route；所有 identity、pose、calibration、freshness 与未知 effect 继续 fail-closed。
- English: Release Runtime terminal `scene_effects`, Coordinator-owned unchanged-entity carry-forward, and read-only grounding/preparation/route while holding; identity, pose, calibration, freshness, and unknown-effect checks remain fail-closed.
- 中文：锁定 RobotWin20 Node `0.8.8`，artifact SHA-256 为 `16912f2fdbe66fa6227df337650eca750dfab4714d58c5f206c53f90fa887053`；旧 `2.8.8`/`0.8.7` 包保持不可变。
- English: Lock RobotWin20 Node `0.8.8` with artifact SHA-256 `16912f2fdbe66fa6227df337650eca750dfab4714d58c5f206c53f90fa887053`; prior `2.8.8`/`0.8.7` packages remain immutable.

## v2.8.8 (2026-09-29)

- 中文：将 RobotWin 场景理解切换为纯本地 Qwen vLLM provider，移除 shuaiapi fallback 及 Dora 环境中的主模型 secret；PAOS 主 Agent provider 保持独立。
- English: Move RobotWin scene understanding to a local-Qwen-only vLLM provider, remove the shuaiapi fallback and main-model secret from Dora, and keep the PAOS main-Agent provider independent.

## v2.8.7 (2026-09-29)

- 中文：发布 Qwen vLLM 场景理解恢复语义与 RobotWin20 Node 0.8.6；保持 provider 进程由 operator 管理，服务未就绪时复用未变化观测、停止无效重试并维持 motion_authorized=false。
- English: Release Qwen vLLM scene-understanding recovery semantics with RobotWin20 Node 0.8.6; keep provider lifecycle operator-owned, reuse unchanged observations while unavailable, suppress ineffective retries, and preserve motion_authorized=false.

## v2.8.6 (2026-09-29) - codex

- [sense] [fix] Align observed-depth support lineage validation with `scene.observe`: validate observation/revision/calibration/frame on the enclosing observation and consume its sole depth artifact; publish Node 0.8.5.
- [Sense] [Fix] 让观测深度支撑面 lineage 校验符合 `scene.observe`：在外层 observation 校验 observation/revision/calibration/frame 身份并消费其中唯一 depth artifact；发布 Node 0.8.5。
- [eval] [fix] Add a regression using the public artifact shape (`ref/kind/media_type`) and retain fail-closed coverage for stale observation identity.
- [Eval] [Fix] 增加使用公开 artifact 形状（`ref/kind/media_type`）的回归，并保留过期 observation 身份的 fail-closed 覆盖。

## v2.8.5 (2026-09-29) - codex

- [sense] [fix] Publish Node 0.8.4 with the observed-depth support fallback already implemented in Grounding; this prevents an observation-owned route from silently omitting `support_surface` when no semantic `on` relation is available.
- [Sense] [Fix] 发布包含 Grounding 既有观测深度支撑面 fallback 的 Node 0.8.4，避免缺少语义 `on` 关系时 observation-owned route 静默遗漏 `support_surface`。
- [eval] [exp] Local no-motion and full RGB AgentLoop acceptance remains in progress; package release alone is not task acceptance.
- [Eval] [Exp] 本地 no-motion 与 RGB AgentLoop 全链路验收仍在进行中；仅发布包不构成任务验收通过。

## v2.7.12 (2026-09-25) - codex

- [model] [fix] Correct GraspNet X-forward to canonical Z-forward mapping and native RoboTwin fingertip-depth conversion; publish Node 0.7.15.
- [model] [fix] 修复 GraspNet X-forward 到 canonical Z-forward 旋转及 RoboTwin 实际指尖深度转换；发布 Node 0.7.15。


## v2.7.11 (2026-09-25) - codex

- [model] [fix] Carry optional metric grasp_geometry through public proposal/preparation contracts; publish Node 0.7.14.
- [model] [fix] 公共候选生成与准备契约保留可选米制 grasp_geometry，发布 Node 0.7.14。


## v2.7.10 (2026-09-25) - codex

- [policy] [feat] Add observed GraspNet benchmark profile and publish Node 0.7.13; retain independent GraspGen closure.
- [policy] [feat] 新增 GraspNet 观测几何 benchmark profile，发布 Node 0.7.13，保留独立 GraspGen 配置。
- [model] [fix] Rank native GraspNet output before the 24-candidate cap, then apply adapter NMS and retain at most 10 candidates.
- [model] [fix] GraspNet 原生候选排序后取 24 个，再由 adapter NMS 后保留最多 10 个。


## v2.6.19 (2026-09-24) - codex

- [sense] [fix] [completed] Remove the stale desktop-organization task label from visual scene-understanding requests so task-independent RGB scenes are described without domain bias; publish Node lock `0.7.0`.
- [sense] [fix] [完成] 移除视觉场景理解请求中过时的 desktop organization 任务标签，避免对任务无关 RGB 场景施加领域偏置；Node 锁定版本为 `0.7.0`。

## v2.6.18 (2026-09-24) - codex

- [policy] [fix] [completed] Carry runtime-profile `scene.observe` defaults through the frozen ToolSpec so task-bound Query arguments are completed by the Coordinator.
- [policy] [fix] [完成] 将 runtime profile 的 `scene.observe` 默认值写入冻结 ToolSpec，由 Coordinator 补齐 task-bound Query 参数。
- [tests] [fix] [completed] Keep the bundle/package version assertion aligned with the v2.6.18 feature revision; Skill suite: 347 passed.
- [tests] [fix] [完成] 将 bundle/package 版本一致性断言同步到 v2.6.18 功能修订；Skill 全量测试 347 项通过。

## v0.10.1 (2026-09-05) - codex

- [policy] [refactor] [completed] Changed the canonical workflow from a linear
  capability order to a dependency DAG: `scene.observe` enables independent
  `manipulation.capabilities` and `scene.understand` Queries, and `grasp.propose`
  joins both results. The reducer exposes all ready Tools and never chooses the
  Agent's call order.
- [policy] [refactor] [完成] 将 canonical workflow 从线性能力顺序重构为依赖 DAG：
  `scene.observe` 后 `manipulation.capabilities` 与 `scene.understand` 独立 ready，
  `grasp.propose` 汇合两者结果。Reducer 暴露全部 ready Tool，不替 Agent 决定调用顺序。

### Verification

- The DAG/reducer versions are `pick_and_place_semantic_dag_v4` and
  `pick_and_place_workflow_v5`; the Skill manifest and package are `0.10.1`.
- The combined core/Skill/adapter regression, static checks, and no-motion boundary
  review are recorded in the repository changelog; no Gateway, Dora, Action, simulator
  motion, or hardware was started.

## v0.10.0 (2026-09-06) - codex

- [policy] [feat] [completed] Promoted `manipulation.capabilities` to an explicit
  no-motion node in the canonical seven-node DAG (`observe -> capabilities ->
  understand -> propose -> prepare -> acquire -> place`) and required its immutable
  capability snapshot reference in every downstream step.
- [policy] [feat] [完成] 将 `manipulation.capabilities` 提升为 canonical 七节点 DAG 中的
  显式 no-motion 节点（`observe -> capabilities -> understand -> propose -> prepare ->
  acquire -> place`），并要求所有后续节点保持不可变 capability snapshot 引用。

### Verification

- Combined core/Skill/adapter regression: `670 passed, 1 skipped`.
- Ruff, compileall, and `git diff --check` pass; no Gateway, Dora, Action, simulator motion,
  or hardware was started.
- The DAG and reducer versions are bumped to `pick_and_place_semantic_dag_v2` and
  `pick_and_place_workflow_v3`; the Skill manifest and package are `0.10.0`.

## v0.9.0 (2026-09-05) - codex

- [policy] [refactor] [completed] Added an immutable Skill-scoped semantic DAG
  projection and made the replay reducer derive admissible nodes from declared
  dependencies rather than tuple position. The state freezes DAG version/digest,
  exposes all ready nodes, validates branch joins and restored-state bindings, and
  remains separate from PAOS task persistence, Tool execution, and motion authority.
- [policy] [refactor] [完成] 新增不可变的 Skill-scoped 语义 DAG projection，并让
  replay reducer 根据声明式依赖而非 tuple 下标判断可执行节点。状态冻结 DAG
  version/digest、公开全部 ready nodes、校验分支汇合与恢复状态绑定，同时继续与
  PAOS 任务持久化、Tool 执行和运动授权分离。

### Verification

- Tests cover dependency and cycle rejection, immutable node/DAG digests, parallel
  ready-node projection, join blocking, restored-state tampering, required bindings,
  terminal failures, and revision rebinding.
- The DAG does not create `PlanRevision`, invoke Gateway/Action/Dora, acquire a robot
  lease, or grant readiness/task/motion verdicts.

## v0.8.0 (2026-09-03) - codex

- [sense] [feat] [completed] Extended the provider-neutral `scene.understand` result with
  auditable derived perception artifacts for instance masks, object point clouds, and metric
  localization, including strict observation/entity/frame/calibration/source/provenance binding.
- [sense] [feat] [完成] 扩展 provider-neutral `scene.understand` 结果，增加可审计的实例
  mask、目标点云和度量定位派生资产，并严格绑定 observation、entity、frame、calibration、
  source 与 provenance。

### Verification

- Generic runtime and Fake Gateway reject unknown kinds, duplicate/unbound/out-of-order lineage,
  mismatched observation/entity/frame/calibration, malformed descriptors, and provider-private
  fields without creating an Action or authorizing motion.
- RoboTwin adapter only forwards plain provider-neutral mappings; model, CUDA, simulator, and
  artifact materialization remain outside the PAOS package.

## v0.7.0 (2026-09-02) - codex

- [policy] [feat] [completed] Added a replayable long-horizon pick-and-place workflow
  reducer over the existing Forge Tool API. It enforces the six-step order, preserves
  opaque references and terminal state, blocks skipped/unknown/failed transitions, and
  resumes only through an append-only revision without adding a Gateway route.
- [policy] [feat] [完成] 新增基于现有 Forge Tool API 的可重放长程 pick-and-place workflow
  reducer。它固定六阶段顺序，保存 opaque 引用与终态，阻断跳步/unknown/失败迁移，
  仅通过追加 revision 恢复，不新增 Gateway 路由。

### Verification

- Added `src/scene_observe/long_horizon.py` and `tests/test_long_horizon.py`; exported
  the reducer and workflow state types and updated the manifest, package version,
  README, SKILL.md, and discovery version assertions.
- The reducer delegates all execution to the existing AgentTask/ForgeToolClient path,
  accepts only terminal statuses and opaque references, validates observation,
  candidate-set, preparation, acquire, and place bindings, and serializes a redacted
  projection with no coordinates or provider/simulator fields.
- `pytest`: 169 passed; `ruff check`, `compileall`, and `git diff --check` passed before
  this metadata-only version bump. PAOS core remains unchanged and no new motion route
  or second execution protocol was introduced.

### Git Commit

- Commit: `4e3c57e` (bundle SHA-256 `f285ee78ee7dbf3374f3a1e86b025ad6860a4fb065ca4fc62f9542bda1eb0357`, 46,093 bytes)
- Branch: `feature/long-horizon-workflow`
- Time: 2026-09-02 (Asia/Shanghai)

## v0.6.0 (2026-09-01) - codex

- [policy] [feat] [completed] Added the provider-neutral `object.place` bounded Action.
  It requires a terminal successful acquire invocation, preserves immutable scene and
  candidate bindings, keeps transport/descent/release/retreat internal, and reports
  typed post-release evidence in the redacted `capability_outcome_summary_v1`.
- [policy] [feat] [完成] 新增 provider-neutral `object.place` bounded Action：要求引用已终态
  成功的 acquire invocation，保持场景与候选不可变绑定，transport/descent/release/retreat
  保持 Gateway 内部，并在脱敏的 `capability_outcome_summary_v1` 中返回类型化释放后证据。

### Verification

- Added `contracts/object.place.tool.yaml`, `src/scene_observe/object_place.py`, and
  `tests/test_object_place.py`; updated Fake Gateway routing, per-tool concurrency,
  Bundle manifest, package version, README, SKILL.md, and discovery assertions.
- Admission rejects stale, missing-calibration, malformed, unbound, unavailable, and
  non-terminal or unsuccessful acquire references before placement invocation identity
  allocation. Standard status/result and cancel routes preserve pending, terminal,
  cancellation, and unknown semantics.
- Public inputs contain only provider-neutral references and an opaque destination;
  no RoboTwin, simulator, provider-private, coordinate, or internal-phase fields are
  exposed. PAOS core remains unchanged and all tests remain no-motion fixtures.

### Git Commit

- Commit: `e51dbc9`
- Branch: `feature/object-place`
- Time: 2026-09-01 (Asia/Shanghai)

## v0.5.0 (2026-09-01) - codex

- [policy] [feat] [completed] Added the provider-neutral `object.acquire` bounded Action.
  It consumes a fresh preparation/candidate binding through standard Action admission,
  keeps approach/contact/close/lift/hold internal, and exposes a redacted,
  versioned `capability_outcome_summary_v1` only in terminal results.
- [policy] [feat] [完成] 新增 provider-neutral `object.acquire` bounded Action，通过标准
  Action admission 消费新鲜的 preparation/candidate 绑定；approach/contact/close/lift/hold
  保持 Gateway 内部阶段，仅在终态返回脱敏、版本化的 `capability_outcome_summary_v1`。

### Verification

- Added `contracts/object.acquire.tool.yaml`, `src/scene_observe/object_acquire.py`,
  and Action lifecycle coverage in `tests/test_object_acquire.py`; updated Fake Gateway,
  manifest, package version, README, SKILL.md, and discovery assertions.
- Admission rejects stale, missing-calibration, malformed, unbound, unavailable, and
  over-concurrency requests before invocation identity allocation. Standard status/result
  and cancel routes preserve pending, terminal, cancellation, and unknown semantics.
- No RoboTwin, simulator, provider-private, coordinate, or direct Agent-to-backend fields
  are included in the public contract; PAOS core remains unchanged.

### Git Commit

- Commit: `292457e`
- Branch: `feature/object-acquire`
- Time: 2026-09-01 (Asia/Shanghai)


## v0.4.0 (2026-09-01) - codex

- [sense] [feat] [completed] Added the provider-neutral `manipulation.prepare` Query
  for non-mutating workspace, kinematic, and collision readiness assessment over a
  bound `grasp.propose` candidate set. It returns per-candidate pass evidence,
  explicit empty/stale/unavailable/invalid states, and a deterministic preparation
  reference while keeping `motion_authorized=false` and exposing no Action or Session.
- [sense] [feat] [完成] 新增 provider-neutral `manipulation.prepare` Query，对绑定的
  `grasp.propose` 候选集执行非侵入式 workspace、kinematic、collision 准备评估。
  它返回逐候选通过证据、明确的 empty/stale/unavailable/invalid 状态和确定性
  preparation 引用，同时保持 `motion_authorized=false`，不暴露 Action 或 Session。

### Verification

- Added `contracts/manipulation.prepare.tool.yaml`,
  `src/scene_observe/manipulation_prepare.py`, and
  `tests/test_manipulation_prepare.py`; updated the Fake Gateway, Bundle manifest,
  README, SKILL.md, and package version.
- Inputs are strictly bound to one observation, scene revision, frame, calibration,
  freshness window, candidate-set reference, and provider-neutral candidates. Stale
  observations and missing calibration fail closed before the provider runs; empty
  candidates do not invoke the provider or fabricate preparation.
- Provider snapshots are checked for candidate/entity binding, exact fields, artifact
  provenance, and all three checks being `pass` before a candidate is marked prepared.
  Query output always contains `motion_authorized: false`.
- Tests exercise the real PAOS `ForgeToolClient` through the Fake Gateway and prove
  that preparation creates no Action, Session, invocation-status, or motion route.
- The package initializer now exports the preparation endpoint, provider protocol,
  snapshot, and ToolSpec; README and manifest descriptions cover all four Query
  capabilities and their provider-neutral adapter boundary.

### Git Commit

- Commit: `3d686da`
- Branch: `feature/manipulation-prepare`
- Time: 2026-09-01 15:05 (Asia/Shanghai)

## v0.3.0 (2026-09-01) - codex

- [sense] [feat] [completed] Added the provider-neutral `grasp.propose` Query as the third
  capability on a separate branch. It converts one verified scene understanding result into
  a generic grasp candidate set with candidate identity, frame/calibration binding,
  provenance, confidence/score, bounded funnel evidence, and explicit empty-candidate
  semantics while staying synchronous, read-only, and free of IK, planning, collision
  checking, Actions, Sessions, and motion authorization.
- [sense] [feat] [完成] 在独立分支上新增 provider-neutral `grasp.propose` Query 作为第三个能力。
  它把一个已验证的 scene understanding 结果转换为带候选身份、frame/calibration 绑定、
  provenance、置信度/评分、有界漏斗证据和明确空候选语义的通用抓取候选集；保持同步只读，
  不包含 IK、规划、碰撞检测、Action、Session 或运动授权。

### Verification

- Added `contracts/grasp.propose.tool.yaml`, `src/scene_observe/grasp_proposal.py`, and
  `tests/test_grasp_propose.py`; updated the Fake Gateway routes, Bundle manifest, and
  workflow guidance.
- Input requires the named observation reference, scene revision, frame, calibration,
  freshness, `max_age_ms`, and observation-bound targets. Stale and missing-calibration
  inputs fail closed before the provider runs; an empty target list returns `status=empty`
  without fabricated candidates.
- Output preserves `candidate_set_ref`, per-candidate identity/frame/provenance, reconciled
  funnel counts, and ambiguity evidence. Qualification is limited to `proposed`,
  `low_confidence`, and `ambiguous`; no field expresses IK success, collision clearance,
  reachability, or action admission, and `motion_authorized` stays `false`.
- The Fake Gateway advertises all three Query specs, reflects grasp-provider availability
  in the `grasp.propose` context, and fails closed when the provider is not configured.
- Tests use PAOS's real `ForgeToolClient.invoke_query_tool("grasp.propose", ...)` through the
  documented Gateway routes and prove no Action, Session, invocation, or motion route exists.

## v0.1.0 (2026-09-01) - codex

- [sense] [feat] Provider-neutral `scene.observe` Query contract, endpoint interface,
  no-motion Fake Gateway transport, and PAOS ForgeToolClient conformance tests.

## v0.1.1 (2026-09-01) - codex

- [sense] [fix] [completed] Added the named `observation_ref` required by the PAOS
  perception architecture so downstream Query capabilities can bind to one immutable
  observation without importing a provider or simulator.
- [sense] [fix] [完成] 增加 PAOS 感知架构要求的命名 `observation_ref`，使下游 Query
  能绑定一个不可变观测，而无需导入 provider 或仿真器。

### Verification

- `scene.observe` ToolSpec/output now requires `observation_ref` with the
  `observation://<scene_revision>/<frame>` shape.
- `pytest`: 7 passed; `ruff check`: passed; `compileall`: passed.
- Changed files: `contracts/scene.observe.tool.yaml`,
  `src/scene_observe/fake_gateway.py`, `tests/test_scene_observe.py`.

## v0.2.0 (2026-09-01) - codex

- [sense] [feat] [completed] Added the provider-neutral `scene.understand` Query as a
  separate capability branch. It will consume one named observation, preserve
  provenance/frame/calibration bindings, and return entity claims, relations,
  spatial envelopes, confidence, and ambiguity without motion or provider fields.
- [sense] [feat] [完成] 新增 provider-neutral `scene.understand` Query 独立能力分支。
  它将消费一个命名观测，保留 provenance/frame/calibration 绑定，并返回实体声明、关系、
  空间包络、置信度和歧义信息；不包含运动或 provider 字段。

### Verification

- Added `contracts/scene.understand.tool.yaml`, `src/scene_observe/understanding.py`,
  and `tests/test_scene_understand.py`; updated the Bundle manifest, workflow guidance,
  and Fake Gateway routes.
- Input requires the named observation reference, scene revision, frame, calibration,
  freshness, and artifact references. Output preserves entity/relation/spatial provenance
  and confidence while keeping `motion_authorized=false`.
- `pytest`: 13 passed; `ruff check`: passed; `compileall`: passed; Bundle archive
  validation passed (SHA-256 `d1766c1965e6b6dd664d4a5b08d79719e3826855e7b99a0f8d71e2373f912f20`, 12839 bytes).
- Fake Gateway advertises both Query specs while reflecting understanding-provider
  availability in the `scene.understand` context; unavailable providers remain fail-closed.
- [sense] [feat] Provider-neutral `scene.observe` Query contract, endpoint interface,
  no-motion Fake Gateway transport, and PAOS ForgeToolClient conformance tests.
## v2.6.20 (2026-09-24) - codex

- [sense] [fix] [completed] Treat an empty OpenAI scene-understanding result with no ambiguity as `entity_count_uncertain`; explicitly inspect colored geometric blocks and preserve the existing available/ambiguity contract.
- [sense] [fix] [完成] OpenAI 场景理解返回空实体且无歧义时标记为 `entity_count_uncertain`；明确检查彩色几何积木，并保持现有 available/ambiguity 契约。
- Adapter and persistent Node version: `0.7.1`.
## v2.9.1 (2026-09-29)

- 中文：澄清同步多视角 Qwen 输出中的 canonical 实体语义：单视角可见不构成身份歧义；不确定的跨视角检测必须保持为独立实体，已合并的多视角实体不得同时声明 identity uncertainty。
- English: Clarify canonical entity semantics for synchronized multi-view Qwen output: single-view visibility is not an identity ambiguity, uncertain cross-view detections remain separate entities, and a merged multi-view entity cannot simultaneously claim identity uncertainty.
- 中文：理解端将共享同一精确度量包络的多个语义实体标记为身份歧义；Agent 绑定选择明确禁止用环境支撑体替代未解析的任务实体。
- English: Mark multiple semantic entities sharing one exact metric envelope as identity-ambiguous, and explicitly forbid Agent binding selection from substituting environment supports for unresolved task entities.
- 中文：发布 Node `0.9.0`，SHA-256 为 `5daff79951a9f13f5cc1afa57c1158b8606e829cc37cfea6295060ced9b1c4c9`。
- English: Publish Node `0.9.0` with SHA-256 `5daff79951a9f13f5cc1afa57c1158b8606e829cc37cfea6295060ced9b1c4c9`。
## v2.9.2 (2026-09-29)

- 中文：拒绝空 entity_refs 的 entity_identity_uncertain，并要求 Qwen 只输出真实歧义，避免“No uncertainty detected”被 Grounding 按全局阻塞处理。
- English: Reject entity_identity_uncertain with empty entity_refs and require Qwen to emit only actual ambiguity, preventing “No uncertainty detected” from becoming a global Grounding blocker.
- 中文：发布 Node `0.9.1`，SHA-256 为 `e33035a64731c84fecc3e967d633084509cb0c113b6e03080f32acb4e4a3e851`。
- English: Publish Node `0.9.1` with SHA-256 `e33035a64731c84fecc3e967d633084509cb0c113b6e03080f32acb4e4a3e851`.
## v2.9.3 (2026-09-29)

- 中文：仅规范化空 `entity_ids` 且严格匹配“未检测到跨视角身份歧义”的 Qwen 否定占位符；其他空、未知实体或 canonical 多视角冲突继续 fail-closed。
- English: Normalize only an empty-`entity_ids` Qwen negative placeholder that strictly states no cross-view identity ambiguity; other empty, unknown-entity, or canonical multi-view conflicts remain fail-closed.
- 中文：Agent 绑定上下文明确区分感知无歧义与任务相关性，禁止以支撑面或其他环境实体替代未解析任务对象。
- English: Distinguish perception-unambiguous candidates from task relevance in Agent binding context and forbid substituting supports or other environment entities for unresolved task objects.
- 中文：发布 Node `0.9.2`，SHA-256 为 `2f875df0fb73125a006fea0fcb77a48af9f2a8215491e43fb317286e4dc78c63`。
- English: Publish Node `0.9.2` with SHA-256 `2f875df0fb73125a006fea0fcb77a48af9f2a8215491e43fb317286e4dc78c63`.
## v2.9.4 (2026-09-29)

- 中文：过滤 Qwen 对不同 canonical category/attributes 实体的宽泛跨视角身份歧义，保留重复语义签名的真实歧义；本地语义默认输出预算统一为 1536。
- English: Filter overbroad cross-view identity ambiguity for entities with distinct canonical category/attributes, retain real ambiguity for duplicate semantic signatures, and align the local semantic default output budget at 1536.
- 中文：发布 Node `0.10.0`，SHA-256 为 `ccdbbb3cd6049169e2f07c35fa7cae9fcab5638e1e57f0c84c74031fc1d4118a`。
- English: Publish Node `0.10.0` with SHA-256 `ccdbbb3cd6049169e2f07c35fa7cae9fcab5638e1e57f0c84c74031fc1d4118a`.
