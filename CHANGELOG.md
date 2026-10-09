# Changelog
## Archive
- [2026-10 part4](changelog/2026-10_part4.md)
- [2026-10 part5](changelog/2026-10_part5.md)
- [2026-10 part3](changelog/2026-10_part3.md)
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

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
| `changelog/2026-10_part4.md` | v13.0.14 | 完整双语记录 / Complete bilingual record |

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

## v13.0.11 (2026-10-09 16:45) - codex

### 变更摘要 / Summary
- [env] [chore] 删除不再使用的 `qwen3vl`、`smolvlm` 和 `minicpm-v` Conda 环境，保留现用 Qwen3-VL-4B 环境与服务。(local)
- [Env] [Chore] Remove the unused `qwen3vl`, `smolvlm`, and `minicpm-v` Conda environments while preserving the active Qwen3-VL-4B environments and service. (local)

### 文件与关键 Diff / Files and Key Diff
| 文件 / File | 行号 / Lines | 变更 / Change |
| --- | --- | --- |
| `changelog/2026-10.md` | L3-L40 | 记录三套环境删除、保留环境与服务验证 / Record removal of the three environments and retained-service verification |

```diff
- qwen3vl, smolvlm, minicpm-v
+ removed with conda env remove; qwen3vl-4b and paos-qwen3vl-4b-vllm retained
```

详见 [2026-10 月度日志](changelog/2026-10.md)。
See the [October 2026 detailed log](changelog/2026-10.md).

## v13.0.10 (2026-10-09 16:08) - codex

### 变更摘要 / Summary
- [docs] [docs] 为 v13.0.9 七维实现复审补充可复制的完整测试命令与实测结果 `195 passed in 2.16s`。(local)
- [docs] [docs] Add the reproducible full test command and measured result `195 passed in 2.16s` to the v13.0.9 seven-dimension implementation review.(local)

### 文件与关键 Diff / Files and Key Diff
| 文件 / File | 行号 / Lines | 变更 / Change |
| --- | --- | --- |
| `PhyAgentOS/agent/planning_loop.py` | L1736-L1808 | 以 bound ToolSpec 的 `(semantics, refreshes_scene)` 分类恢复 Query，并要求每个新 Action 依赖场景刷新 Query / Classify recovery Queries by bound ToolSpec profile and require each new Action to depend on a scene-refresh Query |
| `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py` | L650-L675 | no-motion provider 报告 world change 时优先给出安全拒绝 / Prioritize safety rejection when a no-motion provider reports world change |
| `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_place.py` | L715-L740 | 同上；保持放置结果契约校验 / Same; preserve placement result validation |
| `examples/forge-skills/pick-place-workflow/tests/test_unknown_action_recovery.py` | L58-L91, L313-L430 | 覆盖有效刷新 Query、非刷新 Query、未建立依赖及元数据冲突 / Cover refreshing and non-refreshing Queries, missing dependency, and metadata conflict |
| `examples/forge-adapters/robotwin20/tests/test_action_readiness_gate.py` | L137-L148, L239-L315 | 修正 no-motion fixture 并验证 Acquire/Place 错误优先级 / Correct no-motion fixture and verify Acquire/Place error priority |
| `docs/forge/IMPLEMENTATION_REVIEW_V13_0_9.md` | L1-L77 | 七维 finding、结论与可复现验证命令 / Seven-dimension findings, conclusions, and reproducible validation command |
| `changelog/2026-10_part3.md` | L3-L63 | 双语详细日志与失败场景 / Bilingual detailed log and failure scenarios |
| `docs/forge/UNKNOWN_ACTION_REPLAN_DIAGNOSIS_20261009.md` | L67-L118 | 更新恢复门禁诊断和回归结果 / Update recovery-gate diagnosis and regression results |

```diff
- any new Query can satisfy unknown-world recovery
+ only a new refreshes_scene Query can gate each new Action
- validate the whole no-motion result before checking reported motion
+ return motion_started_in_no_motion_mode when world_change_started is true
  exact focused test invocation: 195 passed in 2.16s
```

See [the detailed bilingual entry](changelog/2026-10_part3.md) and [seven-dimension review](docs/forge/IMPLEMENTATION_REVIEW_V13_0_9.md).
