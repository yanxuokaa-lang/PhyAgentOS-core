# Changelog
## Archive
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.10.11 (2026-10-09 00:10) - codex

### 变更摘要 / Change Summary
- [comm] [fix] 保留 Qwen/vLLM transport、timeout、authentication 分类穿过异常包装；Core route 改为配置无关的有界 token，Adapter lifecycle/readiness/JSONL seam 拒绝超长或非结构化诊断值。(local)
- [comm] [fix] Preserve Qwen/vLLM transport, timeout, and authentication classes through exception wrapping; make Core routes bounded provider-neutral tokens and reject oversized or unstructured Adapter diagnostics at lifecycle/readiness/JSONL seams. (local)
- [eval] [test] Adapter focused `80 passed`；Core focused `118 passed`；Ruff、compileall、`git diff --check` 通过。(local)
- [eval] [test] Adapter focused `80 passed`; Core focused `118 passed`; Ruff, compileall, and `git diff --check` passed. (local)
- [eval] [test] Adapter 全量 `844 passed, 18 failed`；失败为可选依赖和既有 fixture，变更路径无失败。(local)
- [eval] [test] Full Adapter `844 passed, 18 failed`; failures were optional dependencies and existing fixtures, with no changed-path failure. (local)
- [docs] [docs] 新增 `docs/forge/IMPLEMENTATION_REVIEW_V12_10_11.md`，记录三项 Major 发现和七维验收；无任务、无 Gateway Query/Action、无 simulator/物理运动。(local)
- [docs] [docs] Add `docs/forge/IMPLEMENTATION_REVIEW_V12_10_11.md` with three Major findings and seven-dimension acceptance; no task, Gateway Query/Action, simulator, or physical motion was used. (local)

### Findings / 发现与处置
- Major fixed: wrapped Qwen transport/timeout errors previously reached PAOS as `provider_failure`; exception metadata now preserves the stable class and retryability.
- Major fixed: Core silently dropped configured fallback routes not present in a fixed model-name allowlist; bounded provider-neutral route validation now preserves valid configuration.
- Major fixed: lifecycle and persistent diagnostic seams accepted unbounded strings; 128-character printable token bounds now fail closed.

### 文件与关键 Diff / Files and Key Diff
- `qwen3_vl_vllm_scene_understanding.py:L27-L87,L128-L144,L265-L286`：异常分类和包装元数据。(local)
- `understanding.py:L24-L27,L379-L429`：Core route/error-class 边界。(local)
- `qwen3_vl_vllm_lifecycle.py:L15-L20,L281-L299`、`persistent_host.py:L63-L65,L136-L170`：Adapter diagnostics bounds。(local)
```diff
-raise Qwen3VLVLLMInferenceError("qwen vLLM scene understanding request failed") from exc
+raise Qwen3VLVLLMInferenceError(..., provider_error_class=error_class,
+    retryable=error_class in {"timeout", "transport"}) from exc
```

### Git 提交 / Git Commit
- Commit: `1e3d4a8`（实现与七维审查 / implementation and seven-dimension review）
- Branch: `feature/planning-loop`; 时间 / Time: 2026-10-09 Asia/Shanghai

## v12.10.10 (2026-10-08 23:20) - codex

### 变更摘要 / Change Summary
- [comm] [fix] 修复 Qwen/vLLM lifecycle wrapper 丢失 bounded provider diagnostics，并让 fallback 覆盖基础 `Qwen3VLVLLMInferenceError`；合同/transport/timeout 分类保持在 Adapter 边界。 (local)
- [comm] [fix] Preserve bounded Qwen/vLLM diagnostics through the lifecycle wrapper and cover base `Qwen3VLVLLMInferenceError` in fallback; contract/transport/timeout classes remain Adapter-owned. (local)
- [eval] [test] Changed Adapter path `74 passed`；compileall、Ruff、diff check 通过；全程 no-motion。 (local)
- [eval] [test] Changed Adapter path passed (`74`); compileall, Ruff, and diff check passed; validation was no-motion. (local)
- [docs] [docs] 新增 `docs/forge/SCENE_UNDERSTANDING_PROVIDER_FAILURE_DIAGNOSIS_20261008.md`，不含任务专用分支。 (local)
- [docs] [docs] Added `docs/forge/SCENE_UNDERSTANDING_PROVIDER_FAILURE_DIAGNOSIS_20261008.md` with no task-specific branch. (local)

### 文件与验证 / Files and Validation
- `qwen3_vl_vllm_scene_understanding.py:L66-L75,L111-L124,L206-L262,L332-L455`、`qwen3_vl_vllm_lifecycle.py:L278-L293`、`persistent_host.py:L53-L58,L654-L666`；未创建/恢复任务，未调用真实 Gateway Query/Action，未推进 simulator 或物理运动。 (local)
- `qwen3_vl_vllm_scene_understanding.py:L66-L75,L111-L124,L206-L262,L332-L455`, `qwen3_vl_vllm_lifecycle.py:L278-L293`, and `persistent_host.py:L53-L58,L654-L666`; no task was created/resumed, no real Gateway Query/Action was invoked, and no simulator or physical motion advanced. (local)

### Git 提交 / Git Commit
- Commit: `66a9d07`（implementation）; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.9 (2026-10-08 21:00) - codex

### 变更摘要 / Change Summary
- [env] [chore] 用户授权 force-stop 旧 `pick-place-workflow`，确认旧 Runtime、Dora、persistent worker 已停止；刷新当前分支 Core editable 安装并重启 profile，Runtime instance 为 `runtime_4cb91725948c4f16`。 (local)
- [env] [chore] User-authorized force-stop stopped the old `pick-place-workflow` Runtime, Dora flow, and persistent workers; refreshed the current-branch Core editable installation and restarted the profile as Runtime instance `runtime_4cb91725948c4f16`. (local)
- [eval] [test] Gateway `/tools` `ok=true`、11/11 Tool contexts ready、Node `1.0.1` verify passed；ownership 与非终态任务均为空。 (local)
- [eval] [test] Gateway `/tools` returned `ok=true`, all 11/11 Tool contexts are ready, and Node `1.0.1` verification passed; Runtime ownership and non-terminal tasks are empty. (local)

### 验证边界 / Validation Boundary
- 仅执行 lifecycle、editable install、bundle install、Node verify 与只读健康检查；未创建/恢复任务，未调用 Query/Action，未推进 simulator 或物理运动。 / Only lifecycle, editable installation, bundle installation, Node verification, and read-only health checks ran; no task was created/resumed, no Query/Action was invoked, and no simulator or physical motion advanced.

### Git 提交 / Git Commit
- Commit: `42b706b`（部署记录 / deployment record）; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.8 (2026-10-08 20:40) - codex

### 变更摘要 / Change Summary
- [Core] [fix] stale-lineage recovery 改为 operation-level，并从 active revision 持久化 Query response 恢复跨 bounded turn 的 stale signature。 (local)
- [Core] [fix] Make stale-lineage recovery operation-level and restore the stale signature across bounded turns from persisted Query responses in the active revision. (local)
- [eval] [test] 新增跨 turn stale record、通用 operation 文案和同批 Tool 延迟回归；Core `804 passed`，focused Adapter/Core `193 passed`。 (local)
- [eval] [test] Add cross-turn stale-record, generic operation wording, and same-batch deferral regressions; Core `804 passed`, focused Adapter/Core `193 passed`. (local)
- [docs] [docs] 增加七维审查记录 `IMPLEMENTATION_REVIEW_V12_10_8.md`。 (local)
- [docs] [docs] Add the seven-dimension review record `IMPLEMENTATION_REVIEW_V12_10_8.md`. (local)

### 七维复审 / Seven-Dimension Review
- 初审 2 项 Major 已修复；最终 Blocker 0、Major 0、Minor 0。 / Two initial Major findings were fixed; final Blocker 0, Major 0, Minor 0.

### Git 提交 / Git Commit
- Commit: `5aa2883`; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.7 (2026-10-08 19:33) - codex

### 变更摘要 / Change Summary
- [comm] [fix] 动作后 scene revision 变化时，Adapter 返回结构化 `scene_revision_mismatch`（expected/actual、stage、恢复建议），旧 binding 继续 fail-closed，不自动替换 lineage。 (local)
- [comm] [fix] After an action-driven scene revision changes, the Adapter returns structured `scene_revision_mismatch` (expected/actual, stage, recovery advice); stale bindings remain fail-closed and are never silently rewritten. (local)
- [Core] [fix] AgentLoop 对相同 stale lineage 只允许一次纠正回合；没有成功新 observation/understanding 时以 `scene_lineage_no_progress` 收敛，并延迟同批后续 Tool。 (local)
- [Core] [fix] AgentLoop allows one corrective turn for the same stale lineage; without a successful new observation/understanding it converges as `scene_lineage_no_progress` and defers later Tools in that batch. (local)
- [docs] [docs] 保存 `SCENE_BIND_STALE_LINEAGE_DIAGNOSIS_20261008.md` 与 `DISCOVERY_STALE_LINEAGE_CONVERGENCE_DIAGNOSIS_20261008.md`，覆盖 PAOS ownership、AgentLoop 和七维验收。 (local)
- [docs] [docs] Persist `SCENE_BIND_STALE_LINEAGE_DIAGNOSIS_20261008.md` and `DISCOVERY_STALE_LINEAGE_CONVERGENCE_DIAGNOSIS_20261008.md` covering PAOS ownership, AgentLoop behavior, and seven-dimension acceptance. (local)

### 文件与验证 / Files and Validation
- `grounding.py:L93-L121,L1028-L1061`、`loop.py:L801,L1233-L1310,L1719-L1754`；Adapter/Core focused `192 passed`，planning/recovery `177 passed`，Core `803 passed`；Ruff、compileall、diff check 通过。 (local)
- `grounding.py:L93-L121,L1028-L1061`, `loop.py:L801,L1233-L1310,L1719-L1754`; Adapter/Core focused `192 passed`, planning/recovery `177 passed`, Core `803 passed`; Ruff, compileall, and diff check passed. (local)

### Git 提交 / Git Commit
- Commit: `c86d736`; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.6 (2026-10-08 18:00) - codex

### 变更摘要 / Change Summary
- [env] [chore] 授权 force-stop 清理残留 Runtime binding，刷新 Core editable 安装并启动新 Runtime `runtime_fe96f3c9efae4935`。 (local)
- [env] [chore] User-authorized force-stop cleared the stale Runtime binding, refreshed the Core editable installation, and started Runtime `runtime_fe96f3c9efae4935`. (local)
- [eval] [test] Gateway `/tools`、Dora、11/11 Tool contexts ready；Node `1.0.1` SHA-256 `947c2815fe1f9bb18b4c5794112259f792612e9963314c01df2f49d81ecbc63`；ownership 与非终态任务均为空。 (local)
- [eval] [test] Gateway `/tools`, Dora, and all 11/11 Tool contexts are ready; Node `1.0.1` SHA-256 is `947c2815fe1f9fbb18b4c5794112259f792612e9963314c01df2f49d81ecbc63`; Runtime ownership and non-terminal tasks are empty. (local)

### 验证边界 / Validation Boundary
- 仅执行 lifecycle、editable install 和只读健康检查；未创建/恢复任务，未调用 Query/Action，未推进 simulator 或物理运动。 / Only lifecycle, editable install, and read-only health checks ran; no task was created/resumed, no Query/Action was invoked, and no simulator or physical motion advanced.

### Git 提交 / Git Commit
- Commit: `a9814a1`; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.5 (2026-10-08 18:00) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 修复 Skill-bound task 的 unknown Action canonical 去重遗漏 `primary_skill_binding.required_tools` 的问题；冻结 ToolSpec 现在从任务的权威 Skill binding 解析，且在实时 readiness 前要求 reconciliation。 (local)
- [policy] [fix] Fix unknown-Action canonical de-duplication for Skill-bound tasks by resolving frozen ToolSpecs from `primary_skill_binding.required_tools`; reconciliation is required before live readiness. (local)
- [eval] [test] 增加 Skill-bound frozen binding、Runtime 不可用和历史 raw Action canonical 等价回归；证明 Action 不重发。 (local)
- [eval] [test] Add Skill-bound frozen-binding, unavailable-Runtime, and legacy raw Action canonical-equivalence regressions proving no Action resend. (local)

### 文件与审查 / Files and Review
- `PhyAgentOS/forge/task.py:L2702-L2748,L3845-L3874`、`tests/test_planning_task_integration.py:L285-L345`、`docs/forge/PLANNING_ARGUMENT_CANONICALIZATION_DIAGNOSIS_20261008.md:L84-L111`。
- 七维复审初审发现一项 Major，已修复；最终 Blocker 0、Major 0、Minor 0。 / Follow-up seven-dimension review found and fixed one Major; final Blocker 0, Major 0, Minor 0.

### 验证边界 / Validation Boundary
- focused `230 passed`，完整 Core `802 passed in 28.45s`；Ruff、compileall、diff check 通过。全部 no-motion，未恢复任务、调用真实 Gateway、重启 Runtime或推进 simulator/物理运动。 (local)
- Focused tests passed (`230 passed`) and full Core passed (`802 passed in 28.45s`); Ruff, compileall, and diff checks passed. All validation was no-motion with no task resume, real Gateway call, Runtime restart, or simulator/physical motion. (local)

### Git 提交 / Git Commit
- Commit: `13f6c5e`; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.4 (2026-10-08 17:18) - codex

### 变更摘要 / Change Summary
- [policy] [fix] 统一 planning selection 与 Query/Action/Session execution 的 ToolSpec 默认参数规范化，修复持久化 selection 因执行阶段新增默认字段而被 binding 拒绝的问题。 (local)
- [policy] [fix] Unify ToolSpec default argument canonicalization across planning selection and Query/Action/Session execution, fixing persisted selections rejected when defaults were added only at execution time. (local)
- [policy] [fix] 历史 raw selection 仅在原 binding 身份不变且冻结 schema 规范化后参数完全等价时兼容；业务参数变化仍在 Gateway 前 fail-closed。 (local)
- [policy] [fix] Legacy raw selections are compatible only when the original binding identity is unchanged and frozen-schema canonical arguments are exactly equivalent; business-argument changes still fail closed before Gateway. (local)

### 文件与审查 / Files and Review
- `PhyAgentOS/planning/input_schema.py:L42-L128`、`PhyAgentOS/agent/planning_dispatch.py:L630-L660`、`PhyAgentOS/forge/task.py:L2654-L2995,L3475-L3540,L3824-L3917`。
- `tests/test_planning_module.py:L34-L66`、`tests/test_planning_dispatch.py:L100-L128`、`tests/test_planning_task_integration.py:L48-L345`、`docs/forge/PLANNING_ARGUMENT_CANONICALIZATION_DIAGNOSIS_20261008.md:L1-L82`。
- 七维初审发现 Action validation 顺序 Major 1，已修复；最终 Blocker 0、Major 0、Minor 0。 / Seven-dimension review found and fixed one Major Action-validation ordering issue; final Blocker 0, Major 0, Minor 0.

### 关键 Diff / Key Diff
```diff
- digest(raw selection) != digest(execution plus ToolSpec defaults)
+ digest(canonical selection) == digest(canonical execution)
```

### 验证边界 / Validation Boundary
- focused `230 passed`，完整 Core `802 passed in 28.49s`；Ruff、compileall、diff check 通过。全部 no-motion，未恢复任务、调用真实 Gateway、重启 Runtime或推进 simulator/物理运动。 (local)
- Focused tests passed (`230 passed`) and full Core passed (`802 passed in 28.49s`); Ruff, compileall, and diff checks passed. All validation was no-motion with no task resume, real Gateway call, Runtime restart, or simulator/physical motion. (local)

### Git 提交 / Git Commit
- Commit: `d24f6cb`; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.3 (2026-10-08 15:54) - codex

### 变更摘要 / Change Summary
- [comm] [fix] 发送前 JSONL 请求超限不再误终止仍同步的 persistent worker，也不再将明确未发送的请求标记为 world connection lost。 (local)
- [comm] [fix] JSONL requests rejected before transmission no longer terminate a synchronized persistent worker or mark an explicitly unsent request as a lost world connection. (local)
- [comm] [fix] receipt 限制引用数量/长度和终态字段类型；所有字段省略或约束均可由 `receipt_truncated` 观察，非有限数值不进入 JSON。 (local)
- [comm] [fix] Bound receipt reference counts/lengths and terminal field types; all omissions or constraints are visible through `receipt_truncated`, and non-finite numbers are excluded from JSON. (local)
- [chore] [release] Adapter `0.9.12`、Node `1.0.1`、Skill `3.0.9`；Node SHA-256 `947c2815fe1f9fbb18b4c5794112259f792612e9963314c01df2f49d81ecbc63`、Skill SHA-256 `8704dc608c6d20d1440a306c5bef180cd076e009b172c46e0cf0f4f218849ba7`。 (local)
- [chore] [release] Adapter `0.9.12`, Node `1.0.1`, Skill `3.0.9`; Node SHA-256 `947c2815fe1f9fbb18b4c5794112259f792612e9963314c01df2f49d81ecbc63`, Skill SHA-256 `8704dc608c6d20d1440a306c5bef180cd076e009b172c46e0cf0f4f218849ba7`. (local)

### 七维审查 / Seven-Dimension Review
- 架构、正确性、恢复幂等、机器人安全、扩展兼容、可观测性和 AgentLoop 自主性/收敛全部通过；初审发现发送前请求误杀 worker 的 Major 与 receipt 截断不可观察的 Minor，均已修复；最终 Blocker 0、Major 0、Minor 0。 (local)
- Architecture, correctness, recovery/idempotency, robotics safety, extensibility, observability, and AgentLoop autonomy/convergence pass; the initial Major worker-termination bug for pre-write request rejection and Minor unobservable receipt truncation were fixed; final Blocker 0, Major 0, Minor 0. (local)
- Node `1.0.1` 与 Skill `3.0.9` 已构建；review evidence: `docs/forge/IMPLEMENTATION_REVIEW_V12_10_3.md`。未停止、安装或重启 Runtime。 (local)
- Node `1.0.1` and Skill `3.0.9` were built; review evidence: `docs/forge/IMPLEMENTATION_REVIEW_V12_10_3.md`. Runtime was not stopped, installed, or restarted. (local)

### Git 提交 / Git Commit
- Commit: `d1d02c3`; Branch: `feature/planning-loop`; 时间 / Time: 2026-10-08 Asia/Shanghai

## v12.10.2 (2026-10-08 15:24) - codex

### 变更摘要 / Change Summary
- [comm] [fix] 将 persistent Action 的完整执行诊断留在 Runtime artifact，worker/Gateway 只传输 256 KiB 内 terminal receipt；避免 `green_acquire` 已成功却因约 1.05 MiB JSONL 响应超限而成为 unknown。 (local)
- [comm] [fix] Keep complete persistent Action diagnostics in Runtime artifacts and send only a terminal receipt capped at 256 KiB across worker/Gateway; prevent a successful `green_acquire` from becoming unknown because its approximately 1.05 MiB JSONL response exceeds the limit. (local)
- [comm] [fix] 传输错误保留具体协议码；receipt 生成失败保留 artifact refs、状态转 uncertain，AgentLoop 仍不自动重试或推进。 (local)
- [comm] [fix] Preserve concrete transport error codes; receipt projection failures retain artifact references and mark state uncertain, while AgentLoop still does not auto-retry or advance. (local)
- 七维审查记录于 `docs/forge/IMPLEMENTATION_REVIEW_V12_10_2.md`。Node `1.0.0` SHA-256 `36b81dc7ad6db5dcd430c817913fbfb8e138554070bc442d31ae3b4e6b618e45`；Skill `3.0.8` SHA-256 `9de90d504777afcdeb5ec47d5deaa03cface5210e8dbee883b4f10a5eb3ff64a`。 (local)
- Seven-dimension review is recorded in `docs/forge/IMPLEMENTATION_REVIEW_V12_10_2.md`. Node `1.0.0` SHA-256 `36b81dc7ad6db5dcd430c817913fbfb8e138554070bc442d31ae3b4e6b618e45`; Skill `3.0.8` SHA-256 `9de90d504777afcdeb5ec47d5deaa03cface5210e8dbee883b4f10a5eb3ff64a`. (local)

### Git 提交 / Git Commit
- 实现与制品已包含在后续 v12.10.3 审查收尾中 / Implementation and artifacts are included in the v12.10.3 review closeout.

## v12.10.1 (2026-10-08 14:46) - codex

### 变更摘要 / Change Summary
- [env] [chore] 通过 Coordinator 将旧任务置为终态并清空 Runtime ownership 后正常停止旧实例，刷新 Core editable 安装，并使用原 profile/env 启动新 Runtime `runtime_b08a1a96e9f74415`。 (local)
- [env] [chore] After moving the old task to a terminal state through the Coordinator and clearing Runtime ownership, normally stopped the old instance, refreshed the Core editable installation, and started Runtime `runtime_b08a1a96e9f74415` with the existing profile/environment. (local)
- [eval] [test] Skill `3.0.7`、Node `0.10.15`、Dora、Gateway 与 11/11 Tool contexts ready；ownership 与非终态任务均为空。 (local)
- [eval] [test] Skill `3.0.7`, Node `0.10.15`, Dora, Gateway, and all 11 Tool contexts are ready; Runtime ownership and non-terminal tasks are empty. (local)

### 验证边界 / Validation Boundary
- 仅执行 task stop、Runtime lifecycle、editable install 与只读状态检查；未创建/恢复任务，未调用 Query/Action，未推进 simulator 或物理运动。 (local)
- Only task stop, Runtime lifecycle, editable installation, and read-only state checks ran; no task was created/resumed, no Query/Action was invoked, and no simulator or physical motion advanced. (local)

### Git 提交 / Git Commit
- Commit: `e9cf9a0`; Branch: `feature/planning-loop`; 时间: 2026-10-08 Asia/Shanghai

## v12.10.0 (2026-10-08 14:33) - codex

### 变更摘要 / Change Summary
- [comm] [fix] AgentLoop 现在保留 persisted selection wrapper 的结构化拒绝码与有界脱敏 detail，不再把确定性错误降级成无 task-bound record。 (local)
- [comm] [fix] AgentLoop now preserves structured rejection codes and bounded redacted details from persisted-selection wrappers instead of degrading deterministic errors to a missing task-bound record. (local)
- [comm] [fix] stale observation freshness 校验现在基于最终 Coordinator-resolved arguments，持久化 selection 不能通过空 literal arguments 放宽 `max_age_ms`。 (local)
- [comm] [fix] Stale-observation freshness validation now uses final Coordinator-resolved arguments, so persisted selections cannot relax `max_age_ms` through empty literal arguments. (local)

### 文件与审查 / Files and Review
- `PhyAgentOS/agent/planning_loop.py:L873-L881,L1193-L1226`、`PhyAgentOS/agent/tools/forge_tool_api.py:L370-L389`。
- `tests/test_planning_loop.py:L2180-L2318`、`tests/test_forge_tool_api.py:L714-L759`、`docs/forge/IMPLEMENTATION_REVIEW_V12_10_0.md:L1-L67`。
- 初审 Major 2 已全部修复；最终七维 Blocker 0、Major 0、Minor 0。 / Both initial Major findings are fixed; final seven-dimension review has zero Blocker, Major, or Minor findings.

### 验证边界 / Validation Boundary
- 专项 `139 passed`，完整 Core `795 passed`；Ruff、compileall、diff check 通过。全部 no-motion；未创建任务、未调用真实 Gateway、未推进 simulator/物理运动。 (local)
- Focused tests passed (`139 passed`) and the full Core suite passed (`795 passed`); Ruff, compileall, and diff checks passed. All validation was no-motion with no task creation, real Gateway invocation, or simulator/physical motion. (local)

### Git 提交 / Git Commit
- Commit: `ac5ef79`; Branch: `feature/planning-loop`; 时间: 2026-10-08 Asia/Shanghai

## Older Summaries (full details remain in monthly archives)

### v12.9.15 (2026-10-08 13:43) - codex

### 变更摘要 / Change Summary
- [comm] [fix] 修复持久化 `scene.bind` selection 的消费顺序：先解析 Coordinator 参数，再执行实体引用校验，避免合法空参数在 Gateway 前被拒绝。 (local)
- [comm] [fix] Fix persisted `scene.bind` selection consumption ordering by resolving Coordinator arguments before entity-reference validation, preventing valid empty arguments from being rejected before Gateway admission. (local)
- [eval] [test] 新增成功消费和非法 selection fail-closed 回归；Core focused suite `136 passed`，Ruff、compileall 与 diff check 通过。 (local)
- [eval] [test] Add successful-consumption and invalid-selection fail-closed regressions; the Core focused suite passed (`136 passed`) with Ruff, compileall, and diff checks. (local)

### 文件与诊断 / Files and Diagnosis
- `PhyAgentOS/agent/tools/forge_tool_api.py:L373-L387`、`tests/test_forge_tool_api.py:L302-L395`。
- `docs/forge/SCENE_BIND_SELECTION_CONSUMPTION_DIAGNOSIS_20261008.md:L1-L51`、`docs/forge/IMPLEMENTATION_REVIEW_V12_9_15.md:L1-L39`。

### 验证边界 / Validation Boundary
- 仅 Query/no-motion 验证；未创建任务、未调用真实 Gateway、未推进 simulator 或物理运动；未改变 Action admission、Runtime 安全门禁或运动授权。 (local)
- Query-only/no-motion validation; no task was created, no real Gateway was invoked, and no simulator or physical motion advanced; Action admission, Runtime safety gates, and motion authorization were unchanged.

### Git 提交 / Git Commit
- Commit: `3d89785`; Branch: `feature/planning-loop`; 时间: 2026-10-08 Asia/Shanghai

### v12.9.14 (2026-10-08 13:08) - codex

### 变更摘要 / Change Summary
- [env] [chore] 停止旧 Runtime 后安装 Adapter `0.9.10`、Skill `3.0.7`、Node `0.10.15`，启动并只读验收新 Runtime `runtime_3d10c4dfaf5c4382`；Gateway 和 11/11 Tool contexts ready，ownership 为空。 (local)
- [env] [chore] After stopping the old Runtime, install Adapter `0.9.10`, Skill `3.0.7`, and Node `0.10.15`, then start and read-only accept new Runtime `runtime_3d10c4dfaf5c4382`; Gateway and all 11/11 Tool contexts are ready with empty ownership. (local)
- [eval] [test] 未创建任务、未调用 Query/Action、未推进 simulator 或物理运动；旧 Runtime 残留 binding 按用户授权 force-stop，未重试未知的旧 `object.place` Action。 (local)
- [eval] [test] No task was created, no Query/Action was invoked, and no simulator or physical motion was advanced; the old Runtime's residual binding was force-stopped under user authorization, without retrying the unknown old `object.place` Action. (local)

### 制品 / Artifacts
- Skill bundle SHA-256: `cfa6854d2dceaae5c07d364de8d9556284a3537254199439efb3268fb85a9f86`
- Node SHA-256: `b7557228b537b7cb73c46dcee288d3c31e90729cef40bd9c70d40bf20ffa14b5`
- 实际 spawn: `robotwin20_persistent_host-0.10.15-linux-x86_64` / Actual spawn: `robotwin20_persistent_host-0.10.15-linux-x86_64`

### Git 提交 / Git Commit
- Commit: `82e078a` / Branch: `feature/planning-loop`

### v12.9.13 (2026-10-08 12:27) - codex

### 变更摘要 / Change Summary
- [comm] [fix] persistent place producer 现在将已验证的 release、retreat、clearance 与 observation postconditions 投影到 public result 和 action artifact，避免真实成功被 `_ProjectedDriver` 错误降级为 `unknown`。 (local)
- [comm] [fix] The persistent place producer now projects verified release, retreat, clearance, and observation postconditions into the public result and action artifact, preventing a real success from being downgraded to `unknown` by `_ProjectedDriver`. (local)
- [eval] [test] 增加 no-video producer、不完整 route、逐字段缺失 fail-closed、视频 artifact 字段回归；focused `59 passed`，视频测试因环境缺少 `cv2` 未计入成功证据。 (local)
- [eval] [test] Add no-video producer, incomplete-route, per-field fail-closed, and video-artifact field regressions; focused tests passed (`59 passed`), while video tests are not counted because `cv2` is unavailable in the environment. (local)

### 文件与审查 / Files and Review
- `robotwin_persistent_engine.py:L580-L721`、`test_persistent_manipulation.py:L154-L245`、`test_persistent_task_video.py:L63-L78`、`test_persistent_runtime.py:L189-L213`。
- `docs/forge/PLACE_POSTCONDITION_PROJECTION_DIAGNOSIS_20261008.md:L1-L47`、`docs/forge/IMPLEMENTATION_REVIEW_V12_9_13.md:L1-L49`；复审修复 scene revision 类型边界，七维审查 Blocker 0、Major 0。

### Git 提交 / Git Commit
- Commit: `464cebd`（放置后置条件结果投影与无运动回归 / place postcondition projection and no-motion regressions）
- Branch: `feature/planning-loop`
