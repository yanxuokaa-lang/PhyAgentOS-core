# Changelog

## Archive

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

## v11.6.6 (2026-09-24 18:08) - codex

### 实际修改 / Completed changes

- [model] [fix] [完成] `persistent_host.py` 不再按 `route_geometry_source=oracle` 选择 `PersistentOracleGraspProvider`；所有 profile 均通过独立 `graspgen.yaml` 构建 GraspGen Provider。`graspgen.yaml` 的真实候选上限设为 10，禁止模板回退。(local)
- [Model] [Fix] [Completed] `persistent_host.py` no longer selects `PersistentOracleGraspProvider` from `route_geometry_source=oracle`; every profile builds the GraspGen provider from the independent `graspgen.yaml`. The real-candidate cap is 10 and template fallback is forbidden. (local)
- [policy] [fix] [完成] `materialize_complete_route.py` 接受当前 runtime profile 已有的 `max_observation_age_ms` 字段并校验为正整数；此前该字段使真实十候选 prepare 在 materializer 前错误返回 `route_materialization_invalid`。(local)
- [Policy] [Fix] [Completed] `materialize_complete_route.py` accepts and validates the existing positive `max_observation_age_ms` runtime field; previously this field caused the real ten-candidate preparation to fail before materialization with `route_materialization_invalid`. (local)
- [tests] [feat] [完成] persistent host、backend contract、GraspGen proposal/profile tests: `37 passed`;真实首次 GraspGen 任务确认实时点云存在，首个失败为错误 `GRASPGEN_SOURCE_ROOT`，修正后十个真实候选已进入 preparation，随后暴露并修复 runtime identity schema mismatch。(local)
- [Tests] [Feat] [Completed] Persistent-host, backend-contract, and GraspGen proposal/profile tests: `37 passed`; the first live GraspGen task confirmed the current point cloud, initially failed only because `GRASPGEN_SOURCE_ROOT` was wrong, then passed ten real candidates into preparation and exposed/fixed the runtime-identity schema mismatch. (local)

### 精确变更 / Exact files and diff

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py:L28,L546-L593` 删除 Oracle grasp Provider 分支，统一从 grasp profile 构建 GraspGen。
- `examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml:L3-L6` 增加 `provider_id: graspgen`，`max_candidates: 24` → `10`。
- `examples/forge-adapters/robotwin20/scripts/materialize_complete_route.py:L219-L244` 将 `max_observation_age_ms` 纳入严格 identity 字段并校验正整数。
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py:L239-L303` observed/oracle 两路线均断言 GraspGen Provider 与十候选配置。
- `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md:L1-L29` 记录实时感知→点云→GraspGen→十候选→prepare→Action→三轮验收。

**关键 Diff / Key diff:**
```diff
- if route_geometry_source == "oracle":
-     grasp = PersistentOracleGraspProvider(...)
- else:
-     grasp = build_grasp_provider(...)
+ grasp = build_grasp_provider(load_grasp_profile(grasp_profile), environ=variables)
+ max_candidates: 10
+ expected runtime identity fields += max_observation_age_ms
```

### Git 提交 / Git commit

- pending until live GraspGen acceptance completes.


### 变更计划 / Planned changes

- [model] [fix] [计划] 按用户明确要求，persistent host 抓取 Provider 始终由独立 grasp profile 构建，移除 route_geometry_source=oracle 隐式选择模板的耦合；GraspGen profile 保留十个真实候选进入 preparation，无模板 fallback。(local)
- [Model] [Fix] [Planned] Build the persistent grasp provider from its independent grasp profile; remove implicit template selection by oracle route geometry and retain ten real GraspGen candidates for preparation without template fallback. (local)
- [eval] [docs] [计划] 记录补充目标：先实时感知、分割与对象点云、GraspGen、十候选 preparation、单次 acquire/place 与 retreat 验收，再启动三轮 RGB 排列，至少一轮完整成功且有视频及 Verifier。已有 goal 工具不支持修改未完成目标正文，本文记录用户的新增约束。(local)
- [Eval] [Docs] [Planned] Record the amended objective: validate live perception, segmented object clouds, GraspGen, ten-candidate preparation and one acquire/place with retreat before three independent RGB trials with at least one full success, video and verifier. The goal API cannot edit the existing unfinished objective. (local)

### 预期文件 / Expected files

- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py`
- `examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml`
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py`
- `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md`
- `CHANGELOG.md`

现有 profile、Provider 接口和准备检查足以处理该问题，不新增 hash、gate 或 Action 重试。 / Existing profiles, provider interfaces and preparation checks suffice; no new hash, gate or Action retry.

### 追加修复计划 / Additional planned fix

- [agent] [fix] [计划] 当前真实 GraspGen 查询已成功并持久化十个候选，但后续节点把前驱 effects 重复写成未登记的 condition facts，AgentLoop 因 trusted condition_facts 为空而无 ready 节点。保留 dependencies 作为节点顺序与 settlement 门槛，编译时拒绝没有已登记事实来源、却重复直接前驱 effects 的 conditions，由 Agent 修正；不把 effects 提升为物理事实、不新增 Action 重试。(local)
- [Agent] [Fix] [Planned] The live GraspGen query succeeded and persisted ten candidates, but dependent nodes duplicated predecessor effects as unregistered condition facts, leaving AgentLoop with no ready node because trusted condition_facts is empty. Keep dependencies as ordering and settlement gates, and reject conditions duplicating direct predecessor effects without registered facts and let the Agent correct the plan; do not promote effects to physical facts or retry Actions. (local)

### 追加验证 / Additional validation

- [agent] [fix] [完成] 不删除 conditions、不提升 effects；提前拒绝不受事实支持的 effects-as-conditions，公开工具说明明确 dependencies 表示前驱完成。Agent foundation + plan bindings: 72 passed。
- [Agent] [Fix] [Completed] Preserve conditions and never promote effects; reject unsupported effects-as-conditions with actionable guidance. Agent foundation + plan bindings: 72 passed.
- [eval] [fix] [完成] 当前 runtime observation profile 回归及 materializer diagnostics: 6 passed。控制器部署参数现已按同一 package 修正 qualification/plan/evidence/validation 与左右能力文件；离线无运动 materialization 成功，不等同 readiness 或动作成功。
- [Eval] [Fix] [Completed] Runtime profile and materializer diagnostics: 6 passed. Correct qualification/plan/evidence/validation and arm capability paths from one package; offline no-motion materialization passed, not readiness or Action acceptance.
- 单块正式任务 / Single-block task: `task_cde71cc5ec254b5b`, log `/tmp/graspgen-single-v1166.log`; acceptance pending.

### 最终工作树行号 / Current worktree line ranges

- `PhyAgentOS/agent/plan_proposal.py`: L127-L145
- `PhyAgentOS/agent/tools/forge_task.py`: L243-L245
- `examples/forge-adapters/robotwin20/profiles/robotwin20/graspgen.yaml`: L3-L4
- `examples/forge-adapters/robotwin20/pyproject.toml`: L3-L3
- `examples/forge-adapters/robotwin20/scripts/materialize_complete_route.py`: L231-L231, L245-L246
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py`: L27-L27, L544-L544, L569-L573
- `examples/forge-adapters/robotwin20/tests/test_materializer_diagnostics.py`: L72-L86
- `examples/forge-adapters/robotwin20/tests/test_persistent_host.py`: L232-L233, L235-L235, L259-L260, L264-L264, L296-L297
- `examples/forge-skills/pick-place-workflow/pyproject.toml`: L3-L3
- `examples/forge-skills/pick-place-workflow/skill.yaml`: L3-L3, L152-L153, L158-L158
- `tests/test_agent_foundation.py`: L1465-L1477
- `docs/forge/GRASPGEN_RGB_ACCEPTANCE.md`: L1-L24

## v11.6.5 (2026-09-24 17:10) - codex

### 变更记录 / Changes [完成]

- [agent] [fix] 真实任务 `task_f0d1c32d75fc494a` 在计划物化拒绝后以“将修正”文字结束，图仍为空。AgentLoop 在本回合尝试物化、任务仍处于 discovery 时允许一次文字后 continuation，要求通过正式工具修正或明确请求澄清；不重复已有 Tool。(local)
- [Agent] [Fix] Task `task_f0d1c32d75fc494a` ended with a promised correction after rejected materialization while its graph remained empty. Allow one continuation after prose when this turn attempted materialization and the task remains in discovery; use normal tools to correct or request clarification without replaying Tools. (local)

### 文件与 Diff / Files and diff

- `PhyAgentOS/agent/loop.py:L731,L1113-L1141`：`prose -> return` → `rejected materialization + discovery -> one model continuation`。仅使用现有模型与 Coordinator 工具；不重发 Tool。
- `tests/test_agent_foundation.py:L384-L420`：验证修正物化成功和重复文字的有界终止。 / Verify successful corrected materialization and bounded termination on repeated prose.
- Validation: Agent foundation, PlanningLoop, prompt context, turn timeout and provider timing suites: `160 passed`; Ruff and `git diff --check`: passed.
- RGB 三块验收尚未完成。 / Live RGB acceptance remains incomplete.

## v11.6.4 (2026-09-24 17:04) - codex

### 变更记录 / Changes [完成]

- [env] [tune] 按用户要求，将外部 PAOS 默认、RGB 短配置及 RGB 长配置的 `agents.defaults.model` 从 `gpt-6-sol` 改为 `gpt-5.6-sol`，推理强度保持 `high`。使用实际配置加载器验证。(local)
- [Env] [Tune] Change the external default, short RGB, and long RGB PAOS configurations from `gpt-6-sol` to `gpt-5.6-sol` with `high` reasoning as requested; validate through the configuration loader. (local)

### 文件与 Diff / Files and diff

- `/home/yanxu/.PhyAgentOS/config.json:L5`、`/home/yanxu/.PhyAgentOS/config-rgb-no-evolution.json:L5`、`/home/yanxu/.PhyAgentOS/config-rgb-no-evolution-long.json:L5`：`"model": "gpt-6-sol"` → `"model": "gpt-5.6-sol"`。
- 三份外部配置经 `PhyAgentOS.config.loader.load_config` 加载，均确认 `gpt-5.6-sol/high`。配置含本地凭据，Git 仅记录本次变更说明。
- All three external configurations resolve to `gpt-5.6-sol/high` through `load_config`; only the change record is tracked in Git because local configurations contain credentials.

## v11.6.3 (2026-09-24 12:22) - codex

- [agent] [fix] [完成] `PhyAgentOS/agent/loop.py:L809-L878` 在任务创建与 discovery 的无 Tool call `provider_timeout` 后复用同一模型请求一次；节点执行器仍单独管理 node turn 与 Action 对账。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/loop.py:L809-L878` retries the same model request once after a tool-free `provider_timeout` in task creation or discovery; the node executor still owns node turns and Action reconciliation. (local)
- [tests] [feat] [完成] `tests/test_agent_foundation.py:L333-L381` 覆盖两个阶段的恢复/连续失败与节点不叠加重试；相关测试 `158 passed`、Ruff、diff 检查通过。(local)
- [Tests] [Feat] [Completed] `tests/test_agent_foundation.py:L333-L381` covers recovery/repeated failure in both phases and no layered node retry; `158` related tests, Ruff, and diff checks passed. (local)
- Diff: `single preplanning model timeout -> turn failure` -> `one bounded same-request retry`.
- Detailed entry: [`changelog/2026-09_part13.md`](changelog/2026-09_part13.md). Live RGB acceptance remains incomplete.

## v11.6.2 (2026-09-24 12:05) - codex

- [agent] [fix] [完成] `PhyAgentOS/agent/planning_loop.py:L606-L623` 在无 selection、无执行记录的 `provider_timeout` 后使用现有一次 node-turn continuation，保留已固化选择和 Action 对账语义。(local)
- [Agent] [Fix] [Completed] `PhyAgentOS/agent/planning_loop.py:L606-L623` uses the existing single node-turn continuation after a pre-selection `provider_timeout` without an execution record, preserving persisted-selection and Action reconciliation behavior. (local)
- [tests] [feat] [完成] `tests/test_planning_loop.py:L1857-L1914` 覆盖一次超时后成功及连续超时阻塞；专项 `144 passed`，Ruff 与 diff 检查通过。(local)
- [Tests] [Feat] [Completed] `tests/test_planning_loop.py:L1857-L1914` covers success after one timeout and blocking after repeated timeouts; focused tests passed `144`, with Ruff and diff checks passing. (local)
- Diff: `pre-selection provider_timeout -> blocked` -> `one bounded same-node continuation`.
- Detailed entry: [`changelog/2026-09_part13.md`](changelog/2026-09_part13.md). Live RGB acceptance remains incomplete.
