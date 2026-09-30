# Changelog
## Archive
- [2026-09 part20](changelog/2026-09_part20.md)
## v12.4.4 (2026-09-30 08:32) - codex

### 变更摘要 / Summary
- 隔离结构化节点 intent 与 AgentTask 级验证语义，修复 Coordinator 嵌套/扁平语义冲突。
- Separate structured node intent from AgentTask-level verification semantics, fixing Coordinator nested/flat semantic conflicts.
- 新增结构化 intent、旧式扁平兼容及 manipulation_intent_v2 构造回归；107 项通过并完成七维 Review。
- Add structured-intent, legacy-flat compatibility, and manipulation_intent_v2 construction regressions; 107 tests pass with seven-dimension review complete.

### 影响文件 / Affected Files
- PhyAgentOS/agent/plan_proposal.py L36-L48, L402-L410
- tests/test_agent_foundation.py L221-L251
- tests/test_planning_dispatch.py L199-L265
- docs/diagnostics/local-node-intent-task-verification-contamination-20260930.md L1-L40
- docs/reviews/v12.4.4-plan-materialization-seven-dimension-review.md L1-L33

### 验证 / Validation
- Focused pytest: 107 passed.
- Ruff, compileall, and git diff --check: passed.

## v12.4.3 (2026-09-30 08:20) - codex

### 变更摘要 / Summary
- [policy] [fix] 成功 Runtime rebind 后在同一持久化事务内消费活动 clarification，避免同一授权再次暴露或驱动 rebind。 (local)
- [Policy] [Fix] Consume the active clarification in the same persistence transaction after a successful Runtime rebind so the same authorization cannot expose or drive rebind again. (local)
- [eval] [exp] 增加返回记录、重载记录与 Tool 投影回归，保存 Run-4 诊断并完成七维实现 Review。 (local)
- [Eval] [Exp] Add returned-record, reloaded-record, and Tool-projection regressions, persist the Run-4 diagnosis, and complete the seven-dimension implementation review. (local)

### 影响文件 / Affected Files
- PhyAgentOS/forge/task.py
- tests/test_task_runtime_rebind.py
- docs/forge/RGB_ACCEPTANCE_RUN4_REBIND_AUTHORIZATION_CONSUMPTION_DIAGNOSIS_20260930.md
- docs/forge/IMPLEMENTATION_REVIEW_V12_4_3.md

### 文件变更详情 / File Changes

#### [修改] PhyAgentOS/forge/task.py L1115-L1122

修改前 / Before: successful rebind persisted Runtime and revision state while leaving the answered clarification active.

修改后 / After:
~~~python
# A successful rebind consumes the one-shot user authorization.
current.clarification_id = None
current.clarification_question = None
current.clarification_node_id = None
current.clarification_answer = None
~~~

修改说明 / Rationale: Runtime 迁移、revision 创建和一次性授权消费保持在同一 AgentTaskStore.update 状态转换中；task_runtime_rebound 事件继续保留历史 clarification_id。

#### [修改] tests/test_task_runtime_rebind.py L91-L117

- 验证返回记录和重新加载记录均已清除四个活动 clarification 字段。
- 验证成功 rebind 后 activate_skill 与 forge_task_rebind_runtime 均不再出现在 AgentLoop Tool 投影中。
- Verifies both returned and reloaded records clear the four active clarification fields and both rebind-related tools disappear from AgentLoop projection.

#### [新增] docs/forge/RGB_ACCEPTANCE_RUN4_REBIND_AUTHORIZATION_CONSUMPTION_DIAGNOSIS_20260930.md L1-L35

- 记录现场、根因、现有机制不足、遗漏后果与验收边界。
- Records the incident, root cause, existing-mechanism gap, omission impact, and acceptance boundary.

#### [新增] docs/forge/IMPLEMENTATION_REVIEW_V12_4_3.md L1-L65

- 从需求完整性、架构边界、状态机并发、机器人安全、兼容扩展、测试可观测性、发布验收七个维度完成 Review。
- Reviews requirement completeness, architecture, state and concurrency, robotics safety, compatibility, tests and observability, and release acceptance.

### 验证 / Validation
- Focused rebind and Tool-projection pytest files: passed with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1.
- Ruff: passed.
- compileall: passed.
- git diff check: passed.
- Broad grep-selected pytest run was non-authoritative because plugin autoload was disabled and unrelated async plugins were unavailable.

### Git 提交 / Git Commit
- Commit: 528ff02
- Branch: feature/planning-loop
- Time: 2026-09-30

## v12.4.2 (2026-09-30 08:15) - codex

### 变更摘要 / Summary
- 修复既有 AgentTask discovery phase 隐藏 rebind 所需 Tool 的问题。
- 仅在持久化 clarification answer 后显示 activate_skill / forge_task_rebind_runtime，并要求精确 clarification_id。
- 170 项回归和七维 Review 通过；完整 RGB 物理验收继续使用同一任务。

## v12.4.1 (2026-09-30 08:00) - codex

### 变更摘要 / Summary
- 增加用户明确授权的 AgentTask Runtime/Skill rebind，禁止 replacement Runtime 静默接管。
- 保留历史 binding/revision/Tool 记录，并为 replacement Runtime 创建强制全新 discovery 的 revision。
- 新增未结算 Action/Session 拒绝、binding lineage 验证、126 项回归和七维 Review。

### 影响文件 / Affected Files
- PhyAgentOS/forge/task.py L433-L435,L1006-L1131,L1753-L1756
- PhyAgentOS/agent/tools/forge_task.py L272-L314,L783-L794,L847-L858
- PhyAgentOS/agent/recovery_decisions.py L67-L80
- PhyAgentOS/verification/request_builder.py L383-L431
- tests/test_task_runtime_rebind.py L1-L170
- docs/forge/RGB_ACCEPTANCE_RUN3_RUNTIME_REBIND_DIAGNOSIS_20260930.md L1-L23
- docs/forge/IMPLEMENTATION_REVIEW_V12_4_1.md L1-L83

### 验证 / Validation
- Focused AgentTask and verification suite: 126 passed.
- Ruff, compileall, git diff --check: passed.
- Full RGB physical acceptance remains pending on the same AgentTask.

### Git 提交 / Git Commit
- Implementation: 7068773
- Branch: feature/planning-loop

## v12.4.0 (2026-09-30 08:30) - codex

### 变更摘要 / Summary
- 新增 provider-neutral manipulation.staging，解决通用占位目标循环。
- 保留所有 AgentLoop、Coordinator、运动和安全门禁。
- 发布并安装 Node 0.10.0 / Skill 2.10.0，完成七维 Review。

详细 Diff 与行号见 changelog/2026-09_part20.md。

## v12.3.6 (2026-09-30 06:22) - codex

### 变更摘要 / Change Summary
- [docs] [fix] 保存新版 Runtime 直接 Dora 启动失败与正式 `paos skill start` 成功的诊断；明确环境占位符只能由 `RuntimeManager` 物化，未执行任何物理 Action。 (local)
- [Docs] [Fix] Record the raw-Dora launch failure and successful official `paos skill start` launch; clarify that RuntimeManager must materialize environment placeholders; no physical Action was executed. (local)
- [docs] [review] 完成本轮七维 Review：Blocker 0、Major 0，完整 RGB 物理验收保留为后续任务。 (local)
- [Docs] [Review] Completed the seven-dimension review: Blocker 0, Major 0; full RGB physical acceptance remains a subsequent task. (local)

### 影响文件 / Affected Files
- `docs/forge/RUNTIME_LAUNCH_DIAGNOSIS_V12_3_6.md:L1-L46`
- `docs/forge/IMPLEMENTATION_REVIEW_V12_3_6.md:L1-L38`
- `changelog/2026-09_part20.md:L1536-L1543`

### 关键 Diff / Key Diff
**Before:** 操作员直接对生成的 `dataflow.yaml` 调用 Dora，未展开 `${ROBOTWIN20_*}`，在 YAML admission 阶段失败。

**After:** 通过 `paos skill start ... --env-file ...` 进入 `RuntimeManager`，完成环境合成、Node 预检、Dora admission 和 Gateway readiness。

### 验证 / Validation
- `paos skill status pick-place-workflow`：running，Gateway ready，10/10 Tool context ready。
- `paos forge-node verify pick-place-workflow robotwin20_persistent_host`：Node 0.10.0 SHA verified。
- `curl --noproxy '*' -fsS http://127.0.0.1:19020/tools`：Gateway ready。
- v12.3.5 控制面回归：`117 passed`；Ruff、compileall、`git diff --check` passed。

### Git 提交 / Git Commit
- Commit: `aefaad0`
- Branch: `feature/planning-loop`

## v12.3.4 (2026-09-29 06:10) - codex

### 变更摘要 / Change Summary
- [sense] [fix] Qwen 多视角 canonical 实体使用通用 category/attribute 签名过滤宽泛 identity ambiguity；重复语义签名和 merged 单实体继续 fail-closed。
- [model] [fix] 本地 Qwen provider/profile 输出预算统一为 1536，避免双图 JSON 截断。
- [docs] [docs] 保存 10 轮无运动双相机稳定性与 task-relevant scene.bind 证据，并完成七维 Review。
- [Sense] [Fix] Filter overbroad Qwen identity ambiguity using generic category/attribute signatures; retain duplicate-signature and merged-entity fail-closed behavior.
- [Model] [Fix] Align the local Qwen provider/profile output budget at 1536 to prevent dual-view JSON truncation.
- [Docs] [Docs] Record 10-round no-motion synchronized-camera stability and task-relevant scene.bind evidence, with the seven-dimension Review.

### 影响文件 / Affected Files
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_scene_understanding.py:L27-L32,L81-L87,L279-L309,L327-L440`
- `examples/forge-adapters/robotwin20/profiles/forge-persistent/persistent-host.yaml:L17-L29`
- `PhyAgentOS/forge/capability_runtime/understanding.py:L823-L869,L957-L968`
- `PhyAgentOS/agent/prompt_context.py:L433-L455,L735-L746`
- `PhyAgentOS/agent/tools/forge_tool_api.py:L918-L932`
- `docs/forge/MULTIVIEW_SEMANTIC_BINDING_DIAGNOSIS_20260929.md:L66-L86`
- `docs/forge/IMPLEMENTATION_REVIEW_V12_3_4.md:L1-L123`

### 七维 Review / Seven-Dimension Review
- 架构、恢复/幂等、机器人安全、配置/可复现性、可维护性、可观测性和 AgentLoop 均通过；Blocker 0、Major 0。
- Architecture, recovery/idempotency, robotics safety, configuration/reproducibility, maintainability, observability, and AgentLoop all pass; Blocker 0, Major 0.
- Minor residuals: first geometry cold-start latency and operator-owned Runtime lifecycle; no physical Action or final RGB acceptance is claimed.

### 验证 / Validation
- Qwen: `22 passed`; Agent scene-bind projection: `12 passed, 30 deselected`; Skill scene-understand/grasp-propose: `100 passed`。
- Prior full relevant Adapter + Skill evidence: `1120 passed, 1 skipped, 3 existing baseline failures`。
- Ruff、compileall、`git diff --check` passed；现场只读验证为 observe/understand 10/10、capture skew 0 ms、task-relevant bind available。

### Git 提交 / Git Commit
- Implementation commit: `f7487ef`
- Documentation/review metadata commit: `fb3c756`
- Branch: `feature/planning-loop`

## v12.3.3 (2026-09-29 04:32) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 规范化空否定 identity ambiguity，保持 canonical 多视角冲突和未知实体 fail-closed。
- [policy] [fix] 禁止 Agent 以环境支撑面替代未解析任务实体；scene.bind 仍为只读 Query。
- [env] [chore] 发布 `pick-place-workflow 2.9.3` / `robotwin20_persistent_host 0.9.2`。
- [Sense] [Fix] Normalize the strict negative identity-ambiguity placeholder while keeping canonical multi-view conflicts and unknown entities fail-closed.
- [Policy] [Fix] Forbid environment-support substitution for unresolved task entities; scene.bind remains a read-only Query.
- [Env] [Chore] Released `pick-place-workflow 2.9.3` / `robotwin20_persistent_host 0.9.2`.

### 影响文件 / Affected Files
- `docs/forge/MULTIVIEW_SEMANTIC_BINDING_DIAGNOSIS_20260929.md`
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/qwen3_vl_vllm_scene_understanding.py`
- `PhyAgentOS/agent/prompt_context.py`
- `PhyAgentOS/agent/tools/forge_tool_api.py`

### Git 提交 / Git Commit
- Implementation commit: recorded in `changelog/2026-09_part20.md`
- Branch: `feature/planning-loop`

## v12.3.2 (2026-09-30 04:21) - codex

### 变更摘要 / Change Summary
- [policy] [fix] Coordinator Query 默认参数物化改为 oneOf-aware，并在 record/Gateway 前校验最终参数。 (local)
- [Policy] [Fix] Made Coordinator Query default materialization oneOf-aware and validated final arguments before record/Gateway boundaries. (local)
- [sense] [fix] 保存双视角失败与单视角成功诊断，跨视角身份继续 fail-closed。 (local)
- [Sense] [Fix] Persisted the dual-view failure versus single-view success diagnosis and kept cross-view identity fail-closed. (local)

### 影响文件 / Affected Files
- `docs/forge/SCENE_OBSERVE_ONEOF_DIAGNOSIS_20260930.md` L1-L35
- `PhyAgentOS/forge/task.py` L70-L133, L2453-L2472
- `tests/test_planning_task_integration.py` L335-L449
- `changelog/2026-09_part20.md`

### 关键 Diff / Key Diff
**Before:** Coordinator materialized every property default, so explicit `sensor_refs` gained the sibling default `sensor_ref`.

**After:** oneOf-aware materialization suppresses only sibling discriminator defaults, then validates final arguments before record creation and Gateway invocation.

### 七维 Review / Seven-Dimension Review
- 架构、契约、安全、provenance、失败语义、扩展性、测试发布七个维度均通过；无 RGB/相机/Tool ID 专用分支，身份不确定继续 fail-closed。
- Architecture, contract, safety, provenance, failure semantics, extensibility, and release testing passed; no RGB/camera/Tool-ID special case and ambiguous identity remains fail-closed.

### 验证 / Validation
- Coordinator / observation / Forge Tool API / RobotWin 多视角测试：122 passed
- Ruff、compileall、`git diff --check`：passed

### Git 提交 / Git Commit
- Implementation commit: `fcc033d94862`
- Branch: `feature/planning-loop`


## v12.3.1 (2026-09-30 03:51) - codex

### 变更状态 / Change Status

- [完成] 通用多视角/持物场景状态正式发布，并消除 LocateAnything/SAM2 每次 `scene.understand` 重载 checkpoint 的热路径瓶颈。
- [Completed] Release the general multi-view/possession scene-state path and remove repeated LocateAnything/SAM2 checkpoint reloads from warm `scene.understand` calls.

### 关键修改 / Key Changes

- 通用 `hibernate_on_release` 默认为 false；LocateAnything/SAM2 profile 显式启用 CPU hibernate、GPU wake 和串行 GPU ownership。
- Request `release` 与 Runtime terminal `shutdown` 分离；PersistentHost 显式拥有并关闭驻留感知 worker。
- 增加 startup/wake/request/sleep/shutdown INFO timing，不提高全局日志等级。
- 保留通用双视角 Qwen 路径：两图输入、xgrammar 无任意空白、最多 8 条非冗余关系、截断显式诊断。
- 额外静态相机由 runtime profile 所有并仅修改内存配置；旧 profile 缺省为空。
- 无 RGB 排列专用判断，无 Oracle/仿真真值回退，无运动门禁放宽。

### 七维 Review / Seven-Dimension Review

- `docs/forge/IMPLEMENTATION_REVIEW_V12_3_1.md:L1-L179` 覆盖架构集成、恢复/幂等、机器人安全、配置/可复现性、可维护性、可观测性和 AgentLoop 自主性。
- 已修复 3 个 Major：timing 不可见、hibernate/shutdown 所有权不清、可选相机字段兼容性。
- 未解决 Blocker/Major：0。
- Residual：首次 LocateAnything 冷启动约 91 秒；CPU hibernate 占用约 12.1 GB RSS；Dora 外层 Host 仍可能超过既有 stop deadline 并报告 SIGKILL。

### 性能与部署 / Performance and Deployment

- Cold `scene.understand`: `111.435 s`；warm: `14.320 s`；约 `7.8x` 提升。
- 两次均返回 `status=available`、5 entities、20 geometry artifacts。
- Installed Skill: `pick-place-workflow 2.9.0`；Node: `robotwin20_persistent_host 0.8.15`。
- Node SHA-256: `5fa1d5afdb9aca2d4162a2e5464e9eeee44a9ac6e6e4f3291c0fa7ddee65420e`。
- Skill SHA-256: `2fff4ca06a74a6f0ee8d47a82aff9fb644664a0304a265dfe3b6e1a7b025fb3b`。
- Runtime profile `robotwin-blocks-ranking-graspnet` running；Gateway 与 10/10 Tool context ready；Qwen active 且 sleeping。

### 影响文件 / Affected Files

- Lifecycle：`process_worker.py:L19-L287`、`worker_protocol.py:L30-L72`、`locateanything_worker.py:L58-L112,L263-L269`、`sam2_worker.py:L43-L100,L216-L222`。
- Ownership：`single_view_perception.py:L188-L194,L251-L257,L521-L536`、`persistent_host.py:L63-L76,L175-L197,L670-L673,L772,L857`。
- Profiles/runtime：`perception_profile.py:L125-L156`、`robotwin_backend.py:L74-L118,L153-L192,L289-L297,L426-L445,L676-L678`、`materialize_complete_route.py:L240-L247`、runtime consumer compatibility lines。
- Qwen/multiview：`qwen3_vl_vllm_scene_understanding.py:L26-L50,L282-L309,L355-L359`、`franka-blocks-ranking.yaml:L5-L10`。
- Release/docs/tests：Skill manifest/version/lock, adapter and Skill regressions, `README.md:L168-L170,L266-L270,L297-L326`, and the v12.3.1 review.
- 完整逐文件行号和关键 before/after Diff 见 `changelog/2026-09_part20.md:L1161-L1321`。

### 关键 Diff / Key Diff

**Before:** request completion always terminated the worker process; the next call re-imported modules and reloaded checkpoints.

**After:** opt-in request completion sends `sleep`, retains the process and CPU checkpoint, releases CUDA cache, then sends `wake` for the next request; terminal Host close sends bounded `shutdown` and removes the child process.

### 验证 / Validation

- Ruff、compileall、`git diff --check`：通过。
- Lifecycle-focused: `75 passed in 1.89s`。
- Adapter + Skill: `1112 passed, 1 skipped, 3 baseline deselected in 13.63s`。
- `paos forge-node verify`：Node SHA verified；`paos skill status`：running、Gateway ready、10/10 Tool context ready。
- No-motion：只读 benchmark 仅使用 `scene.observe` / `scene.understand`，未执行 Action。

### Git 提交 / Git Commit

- Implementation commit: `98dbf7a8cd01cfa8d6038d3f381f90f0d04580f5`
- Branch: `feature/planning-loop`
- Git metadata time: 2026-09-30 04:03:34 +0800

## v12.3.0 (2026-09-29 01:39) - codex

### 变更状态 / Change Status
- [完成] PAOS 通用场景状态链路已支持同步多视角语义、持物状态只读绑定和 Runtime 证明的实体级 carry-forward；无 RGB 排列专用规则。
- [Completed] The general PAOS scene-state path now supports synchronized multi-view semantics, read-only binding while holding, and Runtime-proven entity-scoped carry-forward, with no RGB-sorting-specific rule.

### 关键修改 / Key Changes
- `scene.observe`：兼容单 `sensor_ref`，新增同步 `sensor_refs`、逐视角 provenance 和 capture-skew 校验。
- `scene.understand`：Qwen/OpenAI 语义 provider 一次消费全部 RGB；primary view 保留现有 metric RGB-D 边界，secondary-only 实体不伪造几何。
- Action/Coordinator：Runtime terminal `scene_effects` 证明 changed/unaffected entities；Agent 不能注入 carry-forward。
- Grounding/preparation/route：稳定 `holding` 可执行只读计算，旧实体继承必须通过 execution identity、effect evidence 和当前 pose 复核。
- Tool YAML、Core、Adapter、Skill 和 AgentLoop 回归同步更新。

### 七维 Review / Seven-Dimension Review
- `docs/forge/IMPLEMENTATION_REVIEW_V12_3_0.md:L1-L136` 覆盖架构集成、恢复/幂等、机器人安全、配置/可复现性、可维护性、可观测性和 AgentLoop 自主性。
- 已修复 1 个 Blocker 和 4 个 Major；未解决 Blocker/Major 为 0。
- 诊断基线：`docs/forge/MULTIVIEW_POSSESSION_SCENE_STATE_DIAGNOSIS_20260929.md:L1-L124`。

### 验证 / Validation
- 聚焦套件：`53 + 54 + 117 + 59 + 304` passed。
- 合并修改树：`1745 passed, 1 skipped, 25 failed`；干净 `HEAD`：`1695 passed, 1 skipped, 26 failed`。
- 修改树新增 50 个通过用例并减少 1 个基线失败；剩余 25 项均可在干净 `HEAD` 复现。
- No-motion only：未启动 Qwen、RobotWin simulator、Runtime 或物理 Action；未放宽任何运动门禁。

### 影响文件 / Affected Files
- Core：`PhyAgentOS/forge/capability_runtime/observation.py:L41-L354`、`understanding.py:L141-L938`、`PhyAgentOS/agent/tools/forge_tool_api.py:L259-L869`。
- Adapter/Runtime：`robotwin_backend.py:L195-L493`、`robotwin_persistent_engine.py:L400-L728`、`grounding.py:L73-L397`、各语义 provider 与 primary-view perception seam。
- Contracts/tests/docs：scene Tool YAML、Core/Adapter/Skill tests、诊断与七维 Review。

### Git 提交 / Git Commit
- Implementation commit: `b0648eb10d6828ef392d2dba1e79f78fd84797ab`
- Branch: `feature/planning-loop`
- Git metadata time: 2026-09-30 02:36:13 +0800

## v12.2.9 (2026-09-30 01:11) - codex

### 变更状态
- [完成] Clash 外部代理与本地 Qwen vLLM 已分离；主模型保持 shuaiapi/gpt-5.6-sol。
- [Completed] Clash external traffic and local Qwen vLLM are isolated; the primary model remains shuaiapi/gpt-5.6-sol.

### 变更摘要 / Change Summary
- [env] [fix] Runtime 使用 `socks5://127.0.0.1:7897` 和回环 NO_PROXY；Qwen 清除继承代理。 (local)
- [env] [tune] Qwen GPU memory utilization 由 0.65 降至 0.58，兼容运行中的 RobotWin。 (local)
- [docs] [docs] 新增双路径验证与 10-seed 报告。 (local)
- [Env] [Fix] Runtime uses `socks5://127.0.0.1:7897` with loopback NO_PROXY; Qwen clears inherited proxies. (local)
- [Env] [Tune] Reduced Qwen GPU memory utilization from 0.65 to 0.58 while RobotWin remains active. (local)
- [Docs] [Docs] Added dual-path verification and the 10-seed report. (local)

### 影响文件 / Affected Files
- `runtime-rgb-graspnet-run5.env:L47-L55`
- `paos-qwen3vl-vllm.service:L7-L17`
- `docs/operations/clash-qwen-proxy-isolation.md:L1-L38`
- `changelog/2026-09_part20.md`、`CHANGELOG.md`

### 关键 Diff / Key Diff
- Runtime: 规范 Clash URI；新增 `NO_PROXY/no_proxy=127.0.0.1,localhost,::1`。
- Qwen unit: 清除六个代理变量；`gpu-memory-utilization 0.65 -> 0.58`。
- Documentation: 网络职责、GPU 共存、双路径和 seed 测试结果。

### 验证 / Validation
- Qwen direct with poisoned proxies: `{"health": 200, "models": 200, "ids": ["qwen3-vl-4b-awq"]}`
- shuaiapi via Clash: `{"proxy": "socks5://127.0.0.1:7897", "status": 403, "transport": "ok"}`
- Qwen seeds: transport 10/10, RGB complete 0/10；实体计数 [3,4]。
- 运行中 Qwen 无 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY；生产客户端保持 `trust_env=False`。
- 主模型仍为 shuaiapi/gpt-5.6-sol。
- Focused pytest: 34 passed in 0.21s；`git diff --check` 通过。
- `systemd-analyze verify` 因根分区 100% 无法创建临时工作目录；实际 daemon-reload、start、health、models 和 10 次推理均通过。

### Git 提交
- Commit: `51bac3302123`
- Branch: `feature/planning-loop`
- 时间: 2026-09-30 01:11

## v12.2.8 (2026-09-29 23:59) - codex

### 变更摘要 [完成]
- [policy] [fix] 中文：让 `scene.understand` 从当前任务最新成功的 `scene.observe` 收据同时投影 `freshness_ms` 与该观测请求使用的 `max_age_ms`，避免模型遗漏字面量后在 provider 调用前触发 `invalid_freshness`。 (local)
- [Policy] [Fix] English: Project both `freshness_ms` and the observation request's `max_age_ms` from the latest successful task-owned `scene.observe` receipt into `scene.understand`, preventing a model-omitted literal from causing pre-provider `invalid_freshness`. (local)
- [policy] [fix] 中文：修正 AgentLoop discovery 语义，只把明确的 provider-stage 不可重试错误交给 Runtime readiness 恢复；请求校验错误在同一任务中获得一次明确的参数修正机会，不再误报 Qwen/Runtime 不可用。 (local)
- [Policy] [Fix] English: Correct AgentLoop discovery semantics so only explicit non-retryable provider-stage failures yield to Runtime readiness recovery; request-validation failures receive one explicit same-task correction path instead of being misreported as Qwen/Runtime unavailability. (local)
- [policy] [fix] 中文：明确只读 Query 的 `motion_authorized=false` 不授予运动、也不阻塞剩余只读发现；真实运动许可仍由 prepare、planning admission、Coordinator 与 Gateway Action 边界裁决。 (local)
- [Policy] [Fix] English: Clarify that read-only Query `motion_authorized=false` neither grants motion nor blocks remaining read-only discovery; actual motion permission remains owned by prepare, planning admission, Coordinator, and the Gateway Action boundary. (local)

### 根因与架构边界 / Root cause and architecture boundary
- 真实失败：Agent 已从当前 observation 投影 scene/calibration/artifact 与 `freshness_ms`，却遗漏必填 `max_age_ms`；Runtime 在 provider 前返回 `invalid_freshness`，过宽的 discovery 提示又把所有 `retryable=false` 错误解释成 provider 阻塞。
- 修复位于 PAOS Agent Tool 参数投影与 AgentLoop 错误处置边界：Runtime freshness、calibration、scene identity、artifact 与 Action admission 校验保持不变。
- `max_age_ms` 从同一 task-owned `scene.observe` 的持久化请求参数复制，模型不能用另一个字面量覆盖当前 observation 的新鲜度预算。
- 未增加场景语义 fallback：合法但任务不充分的视觉结果不能静默改由另一个模型重解释；GPT/Qwen fallback 仍只适用于显式定义的 provider/infrastructure 故障。

### 文件变更详情 / File changes

#### [修改] `PhyAgentOS/agent/tools/forge_tool_api.py` L32-L58, L217-L237
**修改前 / Before:**
```python
"freshness_ms": {"path": ["response", "data", "freshness_ms"]},
# max_age_ms had to be authored as a literal by the model.
```
**修改后 / After:**
```python
"freshness_ms": {"path": ["response", "data", "freshness_ms"]},
"max_age_ms": {"path": ["arguments", "max_age_ms"]},
```
**修改说明：** 标准 observation-bound discovery Query 现在从同一成功 observation 收据复制身份、来源、新鲜度测量和原始新鲜度预算；显式 `argument_sources` 不能把这些字段切换到其他记录。

#### [修改] `PhyAgentOS/agent/loop.py` L1085-L1101, L1286-L1349
**修改前 / Before:**
```python
# Only provider blocking had an explicit control handoff.
# Request-validation errors were left to model interpretation.
```
**修改后 / After:**
```python
if self._scene_understanding_request_invalid(...):
    messages.append({"role": "system", "content": "...submit one corrected Query..."})
```
**修改说明：** 仅白名单中的 pre-provider request errors 获得修正指导；provider contract 错误、不可用和 Action 路径不被误归类。相同非法请求不得盲目重复。

#### [修改] `PhyAgentOS/agent/prompt_context.py` L711-L738
**修改前 / Before:**
```text
If scene.understand returns error.retryable=false, treat provider/runtime as blocked.
```
**修改后 / After:**
```text
Only understanding_provider_error + failure_stage=provider + retryable=false blocks.
Request validation is corrected in-task; read-only motion_authorized=false is expected.
```
**修改说明：** discovery 提示与 AgentLoop 的实际 provider-block predicate 对齐，并保持 Action motion admission fail-closed。

#### [修改] `tests/test_forge_tool_api.py` L111-L189, L192-L274, L301-L354
- 覆盖自动从 observation 请求继承 `max_age_ms`。
- 覆盖模型显式传入 observation 字段或 `argument_sources` 时仍使用当前任务最新成功 observation 的完整参数闭包。

#### [修改] `tests/test_agent_foundation.py` L543-L688
- 保留真实 provider-stage 不可重试错误立即 yield 的回归。
- 新增 `invalid_freshness` 在同一任务中进入一次修正模型回合的回归，证明不会误等 Runtime readiness。

#### [修改] `tests/test_prompt_context.py` L640-L664
- 验证 discovery 提示明确区分 provider failure、request validation 与只读 `motion_authorized=false`。

### 验证 / Validation
- 定向回归：`16 passed`。
- 完整 `tests/test_forge_tool_api.py tests/test_prompt_context.py`：`63 passed`。
- AgentLoop 场景理解相关回归：`5 passed, 78 deselected`。
- 扩展三文件测试：`140 passed, 6 failed`；6 个失败与 v12.2.5 时已记录的一致，均为 invocation-read/outcome_unknown 测试夹具缺少 `read_invocation`、`read_session_invocation` 或 client `base_url`，未经过本次修改路径。
- Ruff、compileall、`git diff --check`：通过。

### Implementation Review
- Blocker：无。
- Major：无。
- Minor：修正参数投影注释以包含 freshness budget；同步测试命名，不再声称验证已移除的模型字面量。

### 安全边界 / Safety boundary
- 未调用 Runtime、Gateway、Qwen、仿真器、机械臂或任何 Action；未修改任务 SQLite。
- 未降低 freshness、calibration、workspace、collision、IK、motion authorization、planning admission 或 terminal-result 门禁。
- 未增加自动仿真复位、跨任务持物转移或静默语义模型 fallback。

### Git 提交 / Git commit
- Production commit: `60d2b47`
- Branch: `feature/planning-loop`
