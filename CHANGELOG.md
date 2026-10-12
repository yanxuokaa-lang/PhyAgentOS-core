# Changelog

## v13.3.4 (2026-10-12 19:06) - codex

### 变更摘要 / Summary [完成]
- [env] [chore] 强制停止旧 Runtime，刷新 editable Core，并发布/安装包含 v13.3.3 Adapter handoff 修复的 Skill `3.0.21` / Node `1.0.11`；使用既有 profile/operator env 启动新 Runtime。 / Force-stop the old Runtime, refresh editable Core, publish/install Skill `3.0.21` / Node `1.0.11` containing the v13.3.3 Adapter handoff fix, and start a new Runtime with the existing profile/operator environment.
- [eval] [test] 新 host/simulator worker 完成 startup，Runtime/Dora/Gateway 和 11/11 Tool contexts ready；重启验收时无非终态任务且部署全程无 Query/Action/运动。用户随后独立创建的新任务正在执行，不属于部署流程。 / A new host/simulator worker completed startup; Runtime/Dora/Gateway and all 11 Tool contexts are ready, with no non-terminal task or deployment Query/Action/motion at restart acceptance. A user-launched task is now executing independently of deployment.

### 文件、验证与提交 / Files, validation, and commit
- `pick-place-workflow/pyproject.toml:L1-L6`、`skill.yaml:L1-L4,L219-L229`、`CHANGELOG.md:L1-L11`、`tests/test_grasp_propose.py:L262-L274`：发布 Skill `3.0.21` / Node `1.0.11` 并更新 lock/version regression。 / Publish Skill `3.0.21` / Node `1.0.11` and update lock/version regression.
- `out/releases/v13.3.4/`：Node/Skill artifacts；Node SHA `3d368ffb05dae5bf5ad7b27ea900702cfe7ea9318754c5199f2a4ed0d400af44`。 / Node/Skill release artifacts with the recorded Node SHA.
- `131 passed in 0.95s`；新 simulator worker PID `2244784`，startup `16.531s`；active runtime lock 使用 Skill `3.0.21` / Node `1.0.11`。用户任务的 LocateAnything 冷启动期间 readiness 曾短暂超时，完成后 11/11 contexts 恢复 ready。 / `131 passed in 0.95s`; new simulator worker PID `2244784`, startup `16.531s`; active lock uses Skill `3.0.21` / Node `1.0.11`. Readiness briefly timed out during the user's LocateAnything cold start and returned to 11/11 ready afterward.
- 全程 no-motion；deployment/release commit `4dc05f8b`；详见 [2026-10 part6 v13.3.4](changelog/2026-10_part6.md)。 / Entirely no-motion; deployment/release commit `4dc05f8b`; see the detailed part6 record.
- Log/index completion commit follows separately. / 日志与索引完成提交随后单独记录。

## v13.3.3 (2026-10-12 18:04) - codex

### 变更摘要 / Summary [完成]
- [comm] [fix] fallback 最终成功时仍释放本轮已尝试的 primary provider，避免 downstream enrichment 与残留 GPU residency 竞争。 / Release an attempted primary provider even when fallback supplies the final semantic result, preventing downstream enrichment from racing residual GPU residency.
- [policy] [fix] 对无世界变化且显式 retryable 的只读 Query provider/enrichment failure 增加同节点有界重试；保留已完成 Action settlement，禁止 Action replay。 / Add bounded same-node recovery for explicitly retryable, world-unchanged, read-only Query provider/enrichment failures; preserve completed Action settlements and prohibit Action replay.
- [eval] [test] 七维审查修复事务竞争、重复预算消耗和 projection 缺口；focused/cross-layer `447 passed`，root suite 与干净对照均为同一组 `10 failed`。 / Seven-dimension review fixed transactional races, duplicate budget consumption, and projection gaps; focused/cross-layer suites passed `447`, and the root suite has the same ten failures as the clean comparison.

### 七维审查与文件 / Seven-dimension review and files
- 架构、正确性、可观测性、恢复幂等、机器人安全、扩展兼容、AgentLoop 收敛均通过；无 RGB/颜色/方块/节点名分支。 / Architecture, correctness, observability, recovery idempotency, robotics safety, extension compatibility, and AgentLoop convergence pass; no RGB/color/block/node-name branch exists.
- `scene_understanding_fallback.py:L55-L69,L222-L243,L314-L366`、`single_view_perception.py:L20-L28,L832-L861,L1069-L1087`：修复 handoff 并区分 transient worker lifecycle 与 deterministic protocol failure。 / Fix handoff and distinguish transient worker lifecycle failures from deterministic protocol failures.
- `planning_facts.py:L7-L23`、`binding.py:L126-L216`、`task.py:L885-L917,L2011-L2233,L4986-L5009`、`planning_loop.py:L24-L32,L1853-L1878`：投影 nested retryability，事务授权有界 Query retry，并仅从 effective view 排除已释放 attempt。 / Project nested retryability, transactionally authorize bounded Query retries, and exclude released attempts only from the effective view.
- `schema.py:L359-L372`、`commands.py:L700-L719` 及对应测试：接入默认 `max_query_provider_retries=2` 和 handoff/recovery 回归。 / Wire the default `max_query_provider_retries=2` and handoff/recovery regressions.

```diff
- final fallback route -> skip primary release -> transient enrichment failure -> stop task
+ attempted primary -> lifecycle handoff -> bounded Query-only retry -> continue remaining suffix
+ completed Action settlement stays authoritative; Action/Session never enter retry path
```

### 验证与提交 / Validation and commit
- `447 passed in 13.88s`；root/current 与 clean `bb698ee7` 均为同一 `10 failed`；Ruff、compileall、diff check passed。 / `447 passed in 13.88s`; current and clean `bb698ee7` have the same ten failures; Ruff, compileall, and diff check passed.
- 全程 no-motion，未部署或重启 Runtime，未创建任务或调用 Gateway。 / Entirely no-motion; Runtime was not deployed/restarted and no task or Gateway call was made.
- Implementation/review commit: `6326718f` on `feature/planning-loop`; detailed record: [2026-10 part6 v13.3.3](changelog/2026-10_part6.md).
- Log/index completion commit follows separately. / 日志与索引完成提交随后单独记录。

## v13.3.2 (2026-10-12 16:27) - codex

### 变更摘要 / Summary [完成]
- [env] [chore] 强制停止旧 `pick-place-workflow` Runtime，确认当前 editable Core 直接加载 v13.3.1 checkout，并复用既有 `robotwin-blocks-ranking-graspnet` profile/operator env 启动新 Runtime。 / Force-stop the old Runtime, confirm the current editable Core directly loads the v13.3.1 checkout, and start a new Runtime with the existing profile/operator environment.
- [eval] [test] Runtime/Dora running、Gateway ready、11/11 Tool contexts ready；Qwen 8012 独立服务保持 ready；任务库无非终态任务。 / Runtime/Dora are running, Gateway and all 11 Tool contexts are ready, the independent Qwen 8012 service remains ready, and the task store has no non-terminal task.

### 部署证据 / Deployment Evidence
- Core import：`/home/yanxu/PhyAgentOS-forge/PhyAgentOS/agent/planning_loop.py`，`revision_settlement_loader=true`。 / Core imports the current checkout and exposes the v13.3.1 revision loader.
- Active lock：Skill `3.0.20` / Node `1.0.10`，Node SHA-256=`722cc67599c5c7792cb069d783597fde440464c2c97f4a2927cc1d9a4e248d63`。 / The active lock pins Skill 3.0.20 and Node 1.0.10 with the recorded SHA-256.
- Qwen `/v1/models`：`qwen3-vl-4b-awq`；task counts：`cancelled=200, failed=95`。 / Qwen reports the expected model; task counts contain only terminal states.
- no-motion：未创建 AgentTask、调用 Query/Action、读取相机、推进 simulator 或执行运动。 / No AgentTask, Query/Action, camera read, simulator step, or motion.

### Git 提交 / Git Commit
- Deployment log/index commit: `ecdd3981` on `feature/planning-loop`. / 部署日志与索引提交：`ecdd3981`，分支 `feature/planning-loop`。
- Commit-reference completion follows separately. / 提交引用补全随后记录。

## v13.3.1 (2026-10-12 15:37) - codex

### 变更摘要 / Summary [完成]
- [policy] [fix] 历史 Action effect 与 continuation 统一使用 Coordinator effective settlement，late terminal 不再退化为原始 `outcome_unknown`。 / Historical Action effects and continuation now use Coordinator-effective settlements, so late terminal results no longer regress to raw `outcome_unknown`.
- [policy] [fix] scene invalidation 与 legacy restore 在事务内复核恢复所有权；重复 operator resume 幂等。 / Scene invalidation and legacy restore recheck recovery ownership transactionally; repeated operator resume is idempotent.
- [eval] [test] 七维审查修复 3 Major + 1 Minor；Core/集成 `333 passed`，通用恢复 `328 passed`，全程 no-motion。 / Seven-dimension review fixed 3 Major and 1 Minor findings; Core/integration `333 passed`, generic recovery `328 passed`, all no-motion.

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/agent/planning_loop.py:L161-L173,L321-L351`、`agent/loop.py:L538-L545`、`agent/tools/planning.py:L76-L87,L334-L345,L451-L462`：所有生产 context 路径接入 revision-aware effective settlement。 / Wire revision-aware effective settlements through all production context paths.
- `PhyAgentOS/forge/task.py:L1644-L1751,L1753-L1879,L2605-L2682,L2972-L3053,L3296-L3313`：事务复核、continuation 一致性、late effect 归约和 resume 幂等。 / Add transactional rechecks, continuation consistency, late-effect reduction, and resume idempotency.
- `tests/test_planning_loop.py:L3737-L3816,L3866-L3876,L3922-L4000`、`tests/test_planning_task_integration.py:L549-L679`：并发与 unknown-to-late-terminal continuation 回归。 / Add concurrency and unknown-to-late-terminal continuation regressions.
- `docs/forge/AGENT_MODEL_PROVIDER_NODE_RECOVERY_DIAGNOSIS_20261012.md:L5,L112-L121`：v13.3.1 独立七维审查补充。 / Add the v13.3.1 independent seven-dimension review.

```diff
- raw historical settlement / raw transactional completion
+ revision-aware effective settlement / consistent continuation and effect context
- pre-read-only recovery ownership checks
+ transactional revision, execution, node, predecessor and lifecycle rechecks
```

### 验证、部署与提交 / Validation, Deployment, and Commit
- Ruff、compileall、`git diff --check` passed；`333 passed` + `328 passed`。 / Static checks passed; `333 passed` plus `328 passed`.
- 未部署或重启 Runtime，未创建任务、调用 Query/Action 或产生运动。 / Runtime was not deployed or restarted; no task, Query/Action, or motion was created.
- Implementation/review commit: `60f8abb4` on `feature/planning-loop`. / 实现与审查提交：`60f8abb4`，分支 `feature/planning-loop`。
- Log/index completion commit follows separately. / 日志与索引完成提交随后记录。

## v13.3.0 (2026-10-12 14:09) - codex

### 变更摘要 / Summary [完成]
- [policy] [fix] 将 Tool 调用前 Agent 模型 provider failure 与 Query/Action failure 分层；新增 `waiting_for_agent_provider`，同 revision/node bounded recovery，禁止 Action replay。 / Separate pre-Tool Agent model provider failures from Query/Action failures; add `waiting_for_agent_provider`, bounded same-revision/node recovery, and prohibit Action replay.
- [policy] [fix] 历史 completed-effect context 按 `(revision_id,node_id,invocation_id)` 精确关联，只携带稳定执行身份和有界结果事实，不覆盖当前场景证据。 / Correlate historical completed effects by `(revision_id,node_id,invocation_id)`, carrying only stable execution identity and bounded outcome facts without overriding current-scene evidence.
- [eval] [test] 七维审查修复事务恢复竞争、legacy 迁移过宽和旧 settlement 兼容性；Core/config `265 passed`，广泛恢复 suite `326 passed`，全程 no-motion。 / Seven-dimension review fixed transactional recovery races, over-broad legacy migration, and legacy-settlement compatibility; Core/config `265 passed`, broad recovery suite `326 passed`, all no-motion.

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/forge/task.py`、`PhyAgentOS/agent/planning_loop.py`、`PhyAgentOS/agent/long_horizon.py`：新增 Coordinator-owned model-provider wait/release lifecycle and bounded historical effect projection. / Add the Coordinator-owned model-provider wait/release lifecycle and bounded historical effect projection.
- `PhyAgentOS/agent/prompt_context.py`、`PhyAgentOS/agent/loop.py`、`PhyAgentOS/config/schema.py`、`PhyAgentOS/cli/commands.py`：接入状态、可见工具和 retry 配置。 / Wire status, visible tools, and retry configuration.
- `tests/test_planning_loop.py`、`tests/test_long_horizon_controller.py`、`tests/test_agent_foundation.py`、`tests/test_verification_service_config.py`：恢复、并发、跨 revision、配置和 no-motion 回归。 / Add recovery, concurrency, cross-revision, config, and no-motion regressions.
- `docs/forge/AGENT_MODEL_PROVIDER_NODE_RECOVERY_DIAGNOSIS_20261012.md`：保存通用诊断和七维审查。 / Record the generic diagnosis and seven-dimension review.

```diff
- NodeTurnProviderError -> awaiting_replan
+ NodeTurnProviderError before Tool record -> waiting_for_agent_provider
+ same scene -> same node/revision retry; changed scene -> awaiting_replan
```

### 部署与提交 / Deployment and Commit
- 本轮未部署或重启 Runtime，未创建任务、调用 Query/Action 或产生运动。 / Runtime was not deployed or restarted; no task, Query/Action, or motion was created.
- Implementation/review commit: `df333e59`; branch `feature/planning-loop`. / 实现与审查提交：`df333e59`；分支 `feature/planning-loop`。
- Log/index completion commit follows separately. / 日志与索引完成提交随后单独记录。

<!-- v13.2.15 and earlier detailed records are archived in changelog/2026-10_part5.md. -->

## v13.2.13 (2026-10-12 12:20) - codex

### 变更摘要 / Summary
- [comm] [fix] 将语义 provider fallback 的双路失败扩展为独立 primary/fallback route、class 和 bounded code，并保留旧 `provider_error_class` 兼容字段；不记录异常正文、凭据、路径或模型输出。 / Extend dual semantic-provider failures with independent primary/fallback route, class, and bounded code while retaining the legacy `provider_error_class`; do not record exception text, credentials, paths, or model output.
- [policy] [fix] 通过既有 Adapter、Core Query、Runtime JSONL 和生命周期 seam 透传 allowlisted diagnostics；不改变 readiness、replan、motion authorization 或 Action replay。 / Carry allowlisted diagnostics through the existing Adapter, Core Query, Runtime JSONL, and lifecycle seams; do not change readiness, replan, motion authorization, or Action replay.
- [eval] [test] 覆盖双路 provider failure、primary 空结果、HTTP code 脱敏和 Core/sink 投影；provider/host/perception `94 passed`，Core AgentLoop/planning/recovery `263 passed`。 / Cover dual provider failure, empty primary results, HTTP-code redaction, and Core/sink projection; provider/host/perception `94 passed`, Core AgentLoop/planning/recovery `263 passed`.

### 文件与关键 Diff / Files and key diff
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/scene_understanding_fallback.py:L9-L125,L204-L291`：独立记录 route/class/code，清理重入旧状态，记录 `empty_result`。 / Independently record route/class/code, clear stale re-entry state, and record `empty_result`.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_scene_understanding.py:L75-L177,L200-L331`、`openai_scene_understanding.py:L14-L152,L326-L443,L549-L656`：provider 错误映射为有界 code。 / Map provider failures to bounded codes.
- `PhyAgentOS/forge/capability_runtime/understanding.py:L448-L472`、`persistent_host.py:L136-L188`、`single_view_perception.py:L858-L887`：沿既有边界投影 allowlisted 字段并过滤原始敏感内容。 / Project allowlisted fields through existing boundaries while filtering raw sensitive content.
- `docs/forge/SCENE_UNDERSTANDING_PROVIDER_FAILURE_DIAGNOSIS_20261012.md:L1-L145`：保存三次双 provider 失败证据、根因、通用修复和七维审查。 / Record the three dual-provider failures, root cause, generic fix, and seven-dimension review.

```diff
- provider_route=none, provider_error_class=contract+provider_failure
+ primary_route=<primary>, primary_error_class=<class>, primary_error_code=<code>
+ fallback_route=<fallback>, fallback_error_class=<class>, fallback_error_code=<code>
```

### 验证与提交 / Validation and commit
- Ruff、compileall、`git diff --check` passed；全程 no-motion，未启动 Runtime、未创建 AgentTask、未调用 Gateway Query/Action。 / Ruff, compileall, and `git diff --check` passed; no motion, Runtime, AgentTask, or Gateway Query/Action was used.
- Implementation commit: `c6ec908e` on `feature/planning-loop`; documentation completion follows in the log update. / 实现提交：`c6ec908e`，分支 `feature/planning-loop`；日志更新随后完成。

详见 [2026-10 part5 v13.2.13](changelog/2026-10_part5.md)。See the detailed v13.2.13 record.

## v13.2.12 (2026-10-12 09:25) - codex

### 变更摘要 / Summary
- [env] [chore] 强制停止旧 Runtime，刷新 editable Core，安装 Skill `3.0.19` / Node `1.0.9` 并启动既有 profile；Runtime/Dora running、Gateway ready、11/11 Tool contexts ready。 / Force-stop the old Runtime, refresh editable Core, install Skill `3.0.19` / Node `1.0.9`, and start the existing profile; Runtime/Dora are running, Gateway is ready, and all 11 Tool contexts are ready.
- [eval] [test] 保留现有 `awaiting_replan=1` 任务；未创建任务、调用 Query/Action、读取相机、推进 simulator 或执行物理动作。 / Preserve the existing `awaiting_replan=1` task; create no task, invoke no Query/Action, read no camera, advance no simulator, and execute no physical motion.

详见 [2026-10 part5 v13.2.12](changelog/2026-10_part5.md)。See the detailed v13.2.12 record.
- Active lock: Skill `3.0.19` / Node `1.0.9`; Node SHA-256 `f721430c4bcb2960306c16c4defacae8e7652870eaffc4c0c1ab718d8f21fff4`.
- Runtime: `runtime_d4b66471c6d14ffc`; 11/11 Tool contexts ready; task store remains `awaiting_replan=1`, `cancelled=197`, `failed=92`.
- Deployment log/index commit: `2ea095d9` (this log update); branch `feature/planning-loop`.

## v13.2.11 (2026-10-12 09:05) - codex

### 变更摘要 / Summary
- [comm] [fix] 将语义 fallback 后的 metric enrichment worker failure 与 semantic provider readiness failure 分离；Core/AgentLoop 只对真正 provider-owned Query 使用 readiness/replan lifecycle。 / Separate metric-enrichment worker failures after semantic fallback from semantic-provider readiness failures; Core/AgentLoop use the readiness/replan lifecycle only for provider-owned Queries.
- [eval] [test] 完成七维审查，补充 Query-generic handoff、enrichment exclusion、worker bounded diagnostics、release lock 和 import-boundary 回归。 / Complete the seven-dimension review and add regressions for generic Query handoff, enrichment exclusion, bounded worker diagnostics, release locks, and import boundaries.

详见 [2026-10 part5 v13.2.11](changelog/2026-10_part5.md)。See the detailed v13.2.11 record.
- Skill `3.0.19` / Node `1.0.9`; Node SHA-256 `f721430c4bcb2960306c16c4defacae8e7652870eaffc4c0c1ab718d8f21fff4`. / Skill `3.0.19` / Node `1.0.9`; Node SHA-256 as recorded.
- Focused validation: `366 passed`; full root suite `858 passed, 5 unrelated failures`; Ruff/compileall/release-lock/diff checks passed. No Runtime, Query/Action, camera, simulator, or physical motion.
- Key contract diff: proposal-worker `failure_stage=provider` → `failure_stage=enrichment`; only semantic provider failures remain eligible for readiness-transition waiting.
- Implementation commit: `6e6af982` on `feature/planning-loop`.

## v13.2.10 (2026-10-11 18:10) - codex

### 变更摘要 / Summary [完成]
- [eval] [fix] 同步发布版本一致性测试至 Skill `3.0.18` / Node `1.0.8`，修复部署后测试仍断言 `3.0.17` / `1.0.7` 的问题；不改变 Runtime 或运动行为。 / Align the release-version consistency test with Skill `3.0.18` / Node `1.0.8`, fixing stale `3.0.17` / `1.0.7` assertions after deployment; change no Runtime or motion behavior.

详见 [2026-10 part5 v13.2.10](changelog/2026-10_part5.md)。See the detailed v13.2.10 record.
- Skill release/install tests: `88 passed`; Ruff、compileall、`git diff --check` passed；Runtime 保持 running，未创建任务或执行运动。 / Skill release/install tests: `88 passed`; Ruff, compileall, and `git diff --check` passed; Runtime remains running, with no task creation or motion.
- Implementation commit: `31c391f9`; documentation commit: `be730b87` on `feature/planning-loop`.

## v13.2.8 (2026-10-11 10:30) - codex

### 变更摘要 / Summary [完成]
- [comm] [fix] 修复 grounding Query 的结构化 `recommended_action` 仅嵌套在 `error`/`diagnostics`、未进入 Core settlement 的响应投影缺口；保持 Runtime 对账语义可达，不改变运动授权或普通 grounding failure 行为。 / Fix the response projection gap where a grounding Query's structured `recommended_action` stayed nested under `error`/`diagnostics` and never reached Core settlement; keep Runtime reconciliation reachable without changing motion authorization or ordinary grounding failures.
- [eval] [test] 增加真实 GroundingEndpoint 到 Core fact projection 回归，覆盖 `reconcile_world` 字段与 no-motion recovery block。 / Add a real GroundingEndpoint-to-Core fact projection regression covering `reconcile_world` and the no-motion recovery block.

### Code Review Finding / 审查发现
- **Major：** `recommended_action` 原先只在 `error`/`diagnostics` 内，真实 Gateway 记录进入 Core settlement 时会丢失 `reconcile_world`；已在 `GroundingEndpoint` 顶层投影既有结构化字段，并保留嵌套诊断。 / **Major:** `recommended_action` was nested only under `error`/`diagnostics`, so real Gateway records lost `reconcile_world` before Core settlement; the existing structured fields are now projected at the `GroundingEndpoint` top level while nested diagnostics remain.
- 七维复审通过：架构、正确性、可观测性、恢复幂等、机器人安全、扩展兼容、AgentLoop 收敛均保持边界；Core `280 passed`、RobotWin `137 passed`、静态检查通过、全程 no-motion。 / Seven-dimension review passed for architecture, correctness, observability, recovery/idempotency, robotics safety, extension compatibility, and AgentLoop convergence; Core `280 passed`, RobotWin `137 passed`, static checks passed, all no-motion.

详见 [2026-10 part5 v13.2.8](changelog/2026-10_part5.md)。See the detailed v13.2.8 record.
- Commit: `4c626fdb` on `feature/planning-loop`.

## v13.2.9 (2026-10-11 10:45) - codex

### 变更摘要 / Summary [完成]
- [env] [chore] 在用户授权下强制停止旧 Runtime，刷新 editable Core，并发布包含 v13.2.8 Adapter 修复的 Skill `3.0.18` / Node `1.0.8`；启动既有 `robotwin-blocks-ranking-graspnet` profile。 / Under user authorization, force-stop the old Runtime, refresh editable Core, and publish Skill `3.0.18` / Node `1.0.8` containing the v13.2.8 Adapter fix; start the existing `robotwin-blocks-ranking-graspnet` profile.
- [eval] [test] 仅验收 Runtime/Dora/Gateway/Tool readiness、active lock、安装版本、任务库非终态数量和 no-motion；不创建 AgentTask、不调用 Query/Action、不读取相机、不推进 simulator。 / Validate only Runtime/Dora/Gateway/Tool readiness, active lock, installed versions, non-terminal task count, and no-motion; create no AgentTask, invoke no Query/Action, read no camera, and advance no simulator.

### 部署结果 / Deployment Result
- Skill `3.0.18` / Node `1.0.8` installed and verified; Runtime/Dora `running`, Gateway `ready`, 11/11 Tool contexts `ready`; active lock uses Node SHA `c5cf0ce28581b6b4b3739e0fac39864e81bebd4d2a2e8150675574053ebff582`. / Skill `3.0.18` / Node `1.0.8` installed and verified; Runtime/Dora are running, Gateway is ready, all 11/11 Tool contexts are ready, and the active lock uses the recorded Node SHA.
- Task store remains terminal-only (`cancelled=197`, `failed=92`); no AgentTask, Query/Action, camera, simulator, or motion was used. / The task store remains terminal-only; no AgentTask, Query/Action, camera, simulator, or motion was used.

详见 [2026-10 part5 v13.2.9](changelog/2026-10_part5.md)。See the detailed v13.2.9 record.
- Commit: `31c391f9` on `feature/planning-loop`.

## v13.2.7 (2026-10-11 09:47) - codex

### 变更摘要 / Summary
- [policy] [fix] 未知 world-changing Action 后的 uncertain possession 不再被 `scene.bind` recovery stop 错误终结；Runtime reconciliation recommendation 现在进入同一 AgentTask 的 blocked/awaiting-replan 生命周期。 (local)
- [Policy] [Fix] Do not terminalize uncertain possession after an unknown world-changing Action through `scene.bind` recovery stop; route the Runtime reconciliation recommendation into the same AgentTask's blocked/awaiting-replan lifecycle. (local)
- [eval] [test] 新增 uncertain possession grounding 与 PlanningLoop no-motion 回归；Core `261 passed`，RobotWin `137 passed`，Ruff/compileall/diff check 通过。 (local)
- [Eval] [Test] Add uncertain-possession grounding and PlanningLoop no-motion regressions; Core `261 passed`, RobotWin `137 passed`, and Ruff/compileall/diff checks pass. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/grounding.py:L115-L133`、`PhyAgentOS/agent/planning_loop.py:L1753-L1781`：显式传播 `reconcile_world` 并在模型 recovery 前保留对账任务所有权。 / Propagate `reconcile_world` explicitly and retain reconciliation task ownership before model recovery.
- `examples/forge-adapters/robotwin20/tests/test_grounding.py:L803-L816`、`tests/test_planning_loop.py:L1561-L1614`：覆盖 uncertain possession 和 failed `scene.bind` block。 / Cover uncertain possession and failed `scene.bind` blocking.
- `docs/forge/UNKNOWN_ACQUIRE_GROUNDING_RECONCILIATION_DIAGNOSIS_20261011.md:L1-L114`、`changelog/2026-10_part5.md:L3-L51`：保存权威诊断、七维审查和 no-motion 验证。 / Record authoritative diagnosis, seven-dimension review, and no-motion validation.

```diff
- uncertain possession -> scene.bind failed -> recovery stop -> task failed
+ uncertain possession -> reconcile_world -> blocked / awaiting_replan
```

详见 [2026-10 part5 v13.2.7](changelog/2026-10_part5.md)。See the detailed v13.2.7 record.
- Commit: `d2e73e62` on `feature/planning-loop`.

## v13.2.6 (2026-10-11 00:00) - codex

### 变更摘要 / Summary
- [env] [chore] 按授权强制停止旧 Runtime，安装 Skill `3.0.17` / Node `1.0.7`，并启动同一 `robotwin-blocks-ranking-graspnet` profile。 (local)
- [Env] [Chore] Under authorization, force-stop the old Runtime, install Skill `3.0.17` / Node `1.0.7`, and start the same `robotwin-blocks-ranking-graspnet` profile. (local)
- [eval] [test] Runtime/Dora running、Gateway ready、11/11 Tool contexts ready、非终态任务为 0；未调用 Query/Action，无物理运动。 (local)
- [Eval] [Test] Runtime/Dora running, Gateway ready, all 11/11 Tool contexts ready, and zero non-terminal tasks; no Query/Action calls or physical motion occurred. (local)

### 文件与锁 / Files and Lock
- `changelog/2026-10_part5.md:L3-L14`：记录强制停止、Core 刷新、Skill/Node 安装、启动、active lock 和 no-motion 验收。 / Record force-stop, Core refresh, Skill/Node installation, start, active lock, and no-motion acceptance.
- Active lock uses Skill `3.0.17` / Node `1.0.7`, Node SHA `92a501e6774a1910d8ad377925432e000d15a229f70ebfdf874105d81ba5dfef`.

详见 [2026-10 part5 v13.2.6](changelog/2026-10_part5.md)。See the detailed v13.2.6 record.

## v13.2.5 (2026-10-11 00:00) - codex

### 变更摘要 / Summary
- [policy] [fix] 修复未知 place 的后置验证异常丢失 Runtime 已确认释放事实的问题；结果继续为 `unknown`，但可安全进入 possession 对账。 (local)
- [Policy] [Fix] Preserve Runtime-confirmed release evidence when unknown-place postcondition verification raises; keep the result `unknown` while allowing safe possession reconciliation. (local)
- [eval] [test] 增加真实 `_verify_release()` 异常回归；定向 Adapter/Skill/AgentLoop 测试 `120 passed`，无物理运动。 (local)
- [Eval] [Test] Add a real `_verify_release()` exception regression; focused Adapter/Skill/AgentLoop tests passed (`120`), with no physical motion.
- [env] [chore] 发布 Skill `3.0.17` / Node `1.0.7`，Node SHA `92a501e6774a1910d8ad377925432e000d15a229f70ebfdf874105d81ba5dfef`。 (local)
- [Env] [Chore] Publish Skill `3.0.17` / Node `1.0.7`, with Node SHA `92a501e6774a1910d8ad377925432e000d15a229f70ebfdf874105d81ba5dfef`. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py:L641-L650,L674-L715`：异常路径保留 Runtime-owned possession 事实，并清理 exhausted route generator。 / Preserve Runtime-owned possession facts in the exception path and clear the exhausted route generator.
- `examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py:L490-L538`：覆盖 placement verification exception，不伪造成功。 / Cover placement-verification exceptions without fabricating success.
- `examples/forge-skills/pick-place-workflow/skill.yaml:L1-L3,L223-L229`、`pyproject.toml:L1-L3`、`tests/test_grasp_propose.py:L270-L274`：同步 Skill/Node 发布版本和锁。 / Align Skill/Node release versions and locks.

```diff
- postcondition exception -> release_confirmed=false -> provider uncertain
+ postcondition exception + explicit Runtime release -> unknown + possession_state=empty
```

详见 [2026-10 part5 v13.2.5](changelog/2026-10_part5.md)。See the detailed v13.2.5 record.
- Commit: `fcd12820` on `feature/planning-loop`.

## v13.2.4 (2026-10-10 19:45) - codex

### 变更摘要 / Summary
- [policy] [fix] 保留 Runtime 已确认的未知 place 释放事实，避免 persistent provider 将可对账场景错误降级为 `uncertain`。 (local)
- [Policy] [Fix] Preserve Runtime-confirmed release facts after an unknown place so the persistent provider does not downgrade a reconcilable scene to `uncertain`. (local)
- [eval] [test] 增加 Runtime tuple/mapping 显式释放证据、缺失证据 fail-closed 和 provider possession projection 回归；定向 `97 passed`，无物理运动。 (local)
- [Eval] [Test] Add regressions for explicit Runtime release evidence in tuple/mapping seams, fail-closed missing evidence, and provider possession projection; focused suite `97 passed`, with no physical motion. (local)
- [env] [chore] 发布并锁定 Skill `3.0.16` / Node `1.0.6`，Node SHA `28f9386653388a7d3274bb61c3fcaa7bb811b72ba95d26e23742f65ceb83f1c4`。 (local)
- [Env] [Chore] Publish and lock Skill `3.0.16` / Node `1.0.6`, with Node SHA `28f9386653388a7d3274bb61c3fcaa7bb811b72ba95d26e23742f65ceb83f1c4`. (local)
- [env] [chore] 旧 Runtime 已停止并部署新 Node；Runtime/Dora running、Gateway ready、11/11 Tool contexts ready；非终态任务为 0，未调用 Query/Action。 (local)
- [Env] [Chore] The old Runtime was stopped and the new Node deployed; Runtime/Dora are running, Gateway is ready, all 11/11 Tool contexts are ready, with zero non-terminal tasks and no Query/Action calls. (local)

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py:L622-L640,L711-L712`、`examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py:L19-L38,L310-L325`：仅 Runtime-owned explicit release evidence 可投影 `possession_state=empty`；缺失证据保持 `uncertain`。 / Only explicit Runtime-owned release evidence projects `possession_state=empty`; missing evidence remains `uncertain`.
- `examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py:L94-L145,L386-L487`：覆盖未知 place 和 mapping seam 的证据边界。 / Cover unknown-place and mapping-seam evidence boundaries.
- `examples/forge-skills/pick-place-workflow/skill.yaml:L223-L229`、`pyproject.toml:L1-L4`、`CHANGELOG.md:L3-L6`、`tests/test_grasp_propose.py:L267-L275`：发布 Skill `3.0.16` / Node `1.0.6`。 / Publish Skill `3.0.16` / Node `1.0.6`.

```diff
- arbitrary mapping terminal -> release_confirmed=True
+ mapping terminal with planner_detached_after_release=true -> release_confirmed=True
+ missing release fact -> uncertain
```

详见 [2026-10 part5 v13.2.4](changelog/2026-10_part5.md)。See the detailed v13.2.4 record.
- Commit: `2384f6f` on `feature/planning-loop`.

## v13.2.3 (2026-10-10 19:25) - codex

### 变更摘要 / Summary
- [env] [chore] 按用户授权强制停止旧 Runtime，刷新 checkout editable Core，安装 Skill `3.0.15` bundle，并启动既有 `robotwin-blocks-ranking-graspnet` profile。 (local)
- [Env] [Chore] Under explicit authorization, force-stop the old Runtime, refresh the checkout editable Core, install the Skill `3.0.15` bundle, and start the existing `robotwin-blocks-ranking-graspnet` profile. (local)
- [eval] [test] Runtime/Dora running、Gateway ready、11/11 Tool contexts ready；活动 lock 为 Skill `3.0.15` / Node `1.0.5`；保留 1 个 `waiting_for_runtime` 任务；全程 no-motion。 (local)
- [Eval] [Test] Runtime/Dora running, Gateway ready, and all 11/11 Tool contexts ready; the active lock uses Skill `3.0.15` / Node `1.0.5`; one `waiting_for_runtime` task was preserved; no motion occurred. (local)

### 文件与关键 Diff / Files and Key Diff
- `changelog/2026-10_part5.md:L3-L32`：记录 stop、editable install、Skill install、start、active lock、readiness、任务计数和 no-motion 验收。 / Record stop, editable install, Skill install, start, active lock, readiness, task counts, and no-motion acceptance.

```diff
- old Runtime / Gateway unavailable
+ Runtime/Dora running / Gateway ready / 11 of 11 Tool contexts ready
+ Skill 3.0.15 / Node 1.0.5 active; waiting_for_runtime task preserved; no Query/Action or motion
```

详见 [2026-10 part5 v13.2.3](changelog/2026-10_part5.md)。See the detailed v13.2.3 record.
- Commit: `ac3921a` on `feature/planning-loop`.

<!-- v13.2.2 is archived in changelog/2026-10_part5.md. -->

## v13.2.1 (2026-10-10 17:40) - codex

### 变更摘要 / Summary
- [policy] [fix] 将 ready Runtime context 中的通用 Query provider failure 交回同一 AgentTask 的 bounded `awaiting_replan`，仅对 Runtime 明确不可用保留 `waiting_for_runtime`。 (local)
- [Policy] [Fix] Route generic Query provider failures with a ready Runtime context to the same AgentTask's bounded `awaiting_replan`, while retaining `waiting_for_runtime` only for explicitly unavailable Runtime contexts. (local)
- [eval] [test] Core recovery/planning/long-horizon/Skill suites `259 passed`；Ruff、compileall、diff check 通过；no-motion。 (local)
- [Eval] [Test] Core recovery/planning/long-horizon/Skill suites passed (`259`); Ruff, compileall, and diff checks passed; no-motion.

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/forge/task.py:L1519-L1638`：按 live Tool readiness 将 provider failure 分流为 Runtime wait 或 bounded replan，保留 append-only receipt 和 `motion_authorized=false`。 / Route provider failures by live Tool readiness to Runtime wait or bounded replan while preserving append-only receipts and `motion_authorized=false`.
- `PhyAgentOS/agent/planning_loop.py:L1645-L1684`：返回 Coordinator 的实际状态，避免 ready-context handoff 被硬编码成 Runtime wait。 / Return the Coordinator's actual status so ready-context handoffs are not hard-coded as Runtime waits.
- `tests/test_planning_loop.py:L3478-L3570,L3825-L3990`：增加 ready-context replan 及 Runtime transition 回归。 / Add ready-context replan and Runtime-transition regressions.
- `docs/forge/QUERY_PROVIDER_READY_CONTEXT_FAILURE_DIAGNOSIS_20261010.md:L1-L70`：保存两次任务证据、共同根因和通用修复边界。 / Preserve both task evidence, the common root cause, and the generic repair boundary.

```diff
- Query provider failure + ready Runtime -> waiting_for_runtime -> poll forever
+ Query provider failure + ready Runtime -> bounded awaiting_replan
+ Query provider failure + unavailable/unconfirmed Runtime -> waiting_for_runtime
```

详见 [2026-10 part5 v13.2.1](changelog/2026-10_part5.md)。See the detailed v13.2.1 record.
- Commit: `141ea85` on `feature/planning-loop`.

## v13.2.0 (2026-10-10 15:10) - codex

### 变更摘要 / Summary
- [env] [chore] 按用户授权强制停止旧 Runtime，刷新 checkout 的 editable Core，并启动既有 `robotwin-blocks-ranking-graspnet` profile。 (local)
- [Env] [Chore] Under explicit authorization, force-stop the old Runtime, refresh the checkout editable Core, and start the existing `robotwin-blocks-ranking-graspnet` profile. (local)
- [eval] [test] Runtime/Dora running、Gateway ready、11/11 Tool contexts ready；活动 runtime-lock 锁定 Skill `3.0.15` / Node `1.0.5`；任务库无非终态任务；全程 no-motion。 (local)
- [Eval] [Test] Runtime/Dora running, Gateway ready, and all 11/11 Tool contexts ready; the active runtime lock pins Skill `3.0.15` / Node `1.0.5`; no non-terminal task exists; no motion occurred. (local)

### 文件与关键 Diff / Files and Key Diff
- `changelog/2026-10_part5.md:L3-L22`：补全强停、安装、启动、活动 lock、readiness 与 no-motion 验收。 / Complete stop, install, start, active-lock, readiness, and no-motion evidence.

```diff
- old Runtime / stale Core
+ Runtime/Dora running; Gateway ready; 11/11 Tool contexts ready
+ Skill 3.0.15 / Node 1.0.5 active; zero non-terminal tasks; no Query/Action or motion
```

详见 [2026-10 part5 v13.2.0](changelog/2026-10_part5.md)。See the [2026-10 part5 v13.2.0](changelog/2026-10_part5.md).
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
- [2026-10 part6](changelog/2026-10_part6.md)
- [2026-10 part5](changelog/2026-10_part5.md)
- [2026-10 part4](changelog/2026-10_part4.md)
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
