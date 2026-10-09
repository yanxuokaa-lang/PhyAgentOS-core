# Changelog
## Archive
- [2026-10 part4](changelog/2026-10_part4.md)
- [2026-10 part5](changelog/2026-10_part5.md)
- [2026-10 part3](changelog/2026-10_part3.md)
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

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

## v13.0.12 (2026-10-09 18:50) - codex

### 变更摘要 / Summary
- [eval] [feat] 增加独立 Laya/Jev intent-routing adapters，与 GPT-6 Luna Decisions probe 共享 80 条样本和评分口径；不导入或执行 PAOS 路由。(local)
- [eval] [feat] Add standalone Laya/Jev intent-routing adapters sharing the 80-case dataset and scoring contract with the GPT-6 Luna Decisions probe; never import or execute PAOS routing. (local)
- [eval] [exp] 三个 Laya checkpoint 各完成 60 条 evaluation（route `0.333/0.483/0.45`）；Jev 完成 60 条 evaluation，coverage `0.90`、有效响应 joint `0.944`。(local)
- [eval] [exp] Complete 60-case evaluation for all three Laya checkpoints (route `0.333/0.483/0.45`) and 60-case Jev evaluation with coverage `0.90` and valid-response joint accuracy `0.944`. (local)
- [env] [chore] Laya 使用独立 `/home/yanxu/laya-system1/.venv` 和缓存；三个 checkpoint 固定到 snapshot `7b928d8...`，项目 `.venv` 的误装依赖已清理。(local)
- [env] [chore] Run Laya from dedicated `/home/yanxu/laya-system1/.venv` and cache; pin all three downloaded checkpoints to snapshot `7b928d8...` and clean accidental packages from the project `.venv`. (local)

### 文件与关键 Diff / Files and Key Diff
`research/decision-api-intent-probe/{jev,laya}_intent_probe.py`, corresponding configs and README,
the capability-validation plan, and `docs/forge/SYSTEM1_INTENT_ROUTING_EXPERIMENT_RESULTS_20261009.md`.

```diff
+ local Laya English/multilingual/typed-decisions adapters and smoke artifacts
+ remote Jev System One adapter with connection reuse, bounded retry, resume, usage and coverage
+ measured comparison report; no PAOS routing integration or replacement
```

详见 [v13.0.12 月度日志](changelog/2026-10_part3.md)和[实验结果](docs/forge/SYSTEM1_INTENT_ROUTING_EXPERIMENT_RESULTS_20261009.md)。
See the [v13.0.12 detailed log](changelog/2026-10_part3.md) and [experiment results](docs/forge/SYSTEM1_INTENT_ROUTING_EXPERIMENT_RESULTS_20261009.md).
