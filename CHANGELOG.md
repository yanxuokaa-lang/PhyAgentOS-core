# Changelog
## Archive
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

## v12.9.9 (2026-10-07 23:15) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 将新 controller qualification plan 默认升级为 schema v2，由公共 `ControllerQualificationPlan` contract 强制 qualification-owned source-manifest、capability 与 validation refs；显式 v1 继续读取已有批准的 legacy package。 (local)
- [sense] [fix] Default new controller qualification plans to schema v2 and enforce qualification-owned source-manifest, capability, and validation refs in the public `ControllerQualificationPlan` contract; explicit v1 remains readable for approved legacy packages. (local)
- [sense] [fix] qualification artifact identity 在 alias 生成前拒绝 `.`、`..` 与路径分隔符；删除 CLI 重复 ownership gate。 (local)
- [sense] [fix] Reject `.`, `..`, and path separators in qualification artifact identities before alias generation, and remove the duplicate CLI ownership gate. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/controller_qualification.py:L26-L29,L106-L134,L253-L344,L835-L856`：plan v2、显式 v1 兼容、package-owned ref 与安全 identity 校验。 (local)
- [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/__init__.py:L30-L45,L368-L380`、`scripts/materialize_controller_qualification_plan.py:L85-L112,L115-L165`：公开兼容常量并移除 CLI 重复规则。 (local)
- [新增测试 / Added Tests] `test_controller_qualification.py:L64-L157,L510-L550`、`test_simulation_probe.py:L44-L55,L509-L520`：v2 ownership、安全 ID、默认物化 v2 与显式 v1 compatibility。 (local)
- [修改 / Modified] Adapter `0.9.8`、Node `0.10.13`、Skill `3.0.5` 版本与锁；新增 `docs/forge/IMPLEMENTATION_REVIEW_V12_9_9.md:L1-L98`。 (local)

### 关键 Diff / Key Diff
```diff
-new plan ownership enforced by one CLI
+new plan ownership enforced by versioned public contract
+explicit v1 legacy read compatibility
```

### 七维 Code Review / Seven-Dimension Review
- 初审发现一个 Major 与一个 Minor：CLI-only ownership 可被其他 producer 绕过，artifact helper 接受路径语义；均已修复。最终 Blocker 0、Major 0、Minor 0，七维全部通过。 (local)
- Initial review found one Major and one Minor issue: CLI-only ownership could be bypassed by another producer, and the artifact helper accepted path semantics. Both are fixed; final review has zero remaining findings across all seven dimensions. (local)
- 无 RGB/颜色/排列/benchmark/相机/实体/候选/固定机械臂专用逻辑；无自动 observe、retry、replan、换候选、换臂或 Action。 (local)

### 验证 / Validation
- Adapter no-motion path `158 passed, 1 deselected`；Skill full `379 passed`；Ruff、compileall、`git diff --check` 通过。 (local)
- Node `0.10.13` SHA-256 `ecb7f18857e9b42ee21eee92bc6936151d71fb0e90df88c4ba89a054fa1d38d2`；Skill `3.0.5` SHA-256 `61f7625b39868241f23baad482a35d006cdf00deecb3b41cf22523e641056fc4`；未安装或启动。 (local)

### Git 提交 / Git Commit
- Commit: `b511e42`（qualification plan v2 contract ownership, regressions, and seven-dimension review）
- Branch: `feature/planning-loop`

## v12.9.8 (2026-10-07 22:30) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 修复长期 Runtime 中旧 capability evidence 与新 qualification evidence 复用同一 artifact ref 的冲突；路线、能力快照和 Runtime admission 统一使用 qualification-owned aliases。 (local)
- [sense] [fix] Fix conflicts where legacy and new qualification capability evidence reused one artifact ref in a long-lived Runtime; route materialization, capability snapshots, and Runtime admission now use qualification-owned aliases. (local)
- [comm] [fix] artifact publication conflict 结构化为不可重试 Runtime contract failure；AgentLoop 不自动 observe、retry、replan、换候选、换臂或执行 Action。 (local)
- [comm] [fix] Structure artifact publication conflicts as non-retryable Runtime contract failures; the AgentLoop does not automatically observe, retry, replan, switch candidates/arms, or dispatch Actions. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/controller_qualification.py:L109-L120,L819`、`arm_candidates.py:L86-L109,L859`、`persistent_capabilities.py:L5-L24`：qualification alias 公共导出、投影与类型契约。 (local)
- [修改 / Modified] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py:L210-L229,L285-L289`、`persistent_route_builder.py:L56-L79,L414-L447`、`runtime/robotwin_motion_policy.py:L206-L225`：部署、路线和 Runtime admission 统一证据引用。 (local)
- [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V12_9_8.md:L1-L121`：七维审查和剩余风险。 (local)
- [新增测试 / Added Tests] Adapter alias、artifact conflict、legacy coexistence、qualification binding 与 no-motion replay regressions. (local)

### 关键 Diff / Key Diff
```diff
- artifact://robotwin/<legacy-profile>/motion-capabilities
+ artifact://controller-qualification/<qualification-id>/capabilities/<arm>/document
- ValueError: materialized artifact conflicts with runtime evidence
+ artifact_identity_conflict / fix_runtime_contract / no automatic replan
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0、Minor 0；架构、正确性、恢复幂等、机器人安全、扩展性、可观测性和 AgentLoop 收敛全部通过。 (local)
- Zero Blocker, Major, or Minor findings; architecture, correctness, recovery/idempotency, robotics safety, extensibility, observability, and AgentLoop convergence all pass. (local)

### 验证 / Validation
- Adapter changed path `150 passed, 1 deselected`；Skill full `379 passed`；Ruff changed paths、compileall、`git diff --check` 通过。 (local)
- Node `0.10.12` SHA-256 `912bed56c4d1dfd8627186f0e78fb2eb10f55dea6fb2ebf2825c496905835903`；Skill `3.0.4` SHA-256 `3917e65fa0e2372b18e0405ce60ac901bea7cf4d629ba48942c93209e1f2d4e4`；未安装或启动。 (local)

### Git 提交 / Git Commit
- Commit: `4ce9f45`（qualification evidence identity fix, diagnostics, seven-dimension review, and no-motion regressions）
- Branch: `feature/planning-loop`

## v12.9.7 (2026-10-07 21:36) - codex

### 变更摘要 / Change Summary
- [env] [chore] 停止旧 Runtime，安装 Skill `3.0.3` 与 Node `0.10.11`，从最终 controller source 重建并审批 qualification evidence，更新八个 operator evidence 路径后启动新 Runtime。 (local)
- [env] [chore] Stopped the old Runtime, installed Skill `3.0.3` and Node `0.10.11`, rebuilt and approved qualification evidence from the final controller source, updated the eight operator evidence paths, and started the new Runtime. (local)
- [docs] [docs] 保存 controller-source qualification deployment diagnosis，并完成七维验收；没有 RGB/颜色/排列/相机/固定机械臂专用逻辑。 (local)
- [docs] [docs] Added the controller-source qualification deployment diagnosis and completed the seven-dimension acceptance review; no RGB/color/order/camera/fixed-arm-specific logic was added. (local)

### 文件变更详情 / File Changes
- [新增 / Added] `docs/forge/CONTROLLER_SOURCE_QUALIFICATION_DEPLOYMENT_DIAGNOSIS_20261007.md:L1-L133`：记录通用根因、PAOS 所有权边界、source-bound evidence rollover、部署证据、七维验收和剩余任务级边界。 (local)
- [修改 / Modified] `changelog/2026-10_part2.md:L3-L65`：记录旧 Runtime 停止、新制品安装、两次人工审批、8/8 qualification、env 路径更新和新 Runtime 验收。 (local)
- [修改 / Modified] `/home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env:L34-L42`：仅更新八个 capability/qualification 路径，保持 `0600`，不提交凭据文件。 (local)
- [修改 / Modified] `CHANGELOG.md:L8-L37`：维护最近五个版本索引。 (local)

### 关键 Diff / Key Diff
```diff
-old qualification evidence bound to controller source 6a1e9cdc...
+new approved qualification bound to controller source a693ada4...
-Runtime stopped with stale evidence
+runtime_7791dd9a1eb94972 running after validated evidence promotion
```

### 验证 / Validation
- Runtime `runtime_7791dd9a1eb94972` running；Dora、Gateway、11/11 Tool contexts ready；ownership 为空，AgentTask 非终态为 0。 (local)
- Runtime `runtime_7791dd9a1eb94972` is running; Dora, Gateway, and all 11 Tool contexts are ready; ownership is empty and non-terminal AgentTasks are 0. (local)
- Qualification `approved_pass`，8/8 isolated SAPIEN tests passed；最终 qualification SHA-256 `beb6733e51afb6d0d3277c761599b5d3a34c07d819b3aac17200c9b6154e8350`。 (local)
- Qualification is `approved_pass` with all 8/8 isolated SAPIEN tests passing; final qualification SHA-256 is `beb6733e51afb6d0d3277c761599b5d3a34c07d819b3aac17200c9b6154e8350`. (local)
- 任务级抓取/放置未执行；本次部署验收未调用 Gateway Query/Action 或创建 AgentTask。 (local)
- No task-level grasp/place was executed; deployment acceptance created no AgentTask and invoked no Gateway Query/Action. (local)

### Git 提交 / Git Commit
- Commit: `2e9e371`（部署诊断、资格证据与 Runtime 验收 / deployment diagnosis, qualification evidence, and Runtime acceptance）
- Branch: `feature/planning-loop`

## v12.9.6 (2026-10-07 20:35) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 将当前 Runtime 实际导入的 bounded-controller source 纳入共享 motion-policy 准入；Readiness、Action 和 monitored startup 均拒绝旧 capability snapshot。 (local)
- [sense] [fix] Bind the bounded-controller source imported by the current Runtime into shared motion-policy admission so Readiness, Action, and monitored startup all reject stale capability snapshots. (local)
- [comm] [fix] 保留执行期间逐 command source digest 复验；不可恢复的 Runtime contract failure 仍由 AgentLoop 确定停止，不触发自动恢复。 (local)
- [comm] [fix] Retain per-command source-digest revalidation during execution; non-recoverable Runtime contract failures still stop deterministically in AgentLoop without automatic recovery. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `robotwin_capability_controller.py:L10-L18`、`robotwin_motion_policy.py:L46-L113,L126-L255`：由 controller owner 捕获 import-time identity，并共享配置启动检查与 Readiness/Action 准入。 (local)
- [修改 / Modified] `robotwin_simulation_probe_worker.py:L45-L50,L1081-L1154,L1284-L1289,L1342-L1347,L2141-L2149`、`robotwin_persistent_engine.py:L484-L530`：消费共享 digest，删除重复 admission，保留 execution guard。 (local)
- [修改 / Modified] `persistent_host.py:L705-L721`：monitored Runtime composition 前校验配置的左右臂 source binding。 (local)
- [新增测试 / Added Tests] Adapter source/provider/version/arm/startup/Readiness/Action no-motion 回归；同步 Adapter `0.9.6`、Node `0.10.11`、Skill `3.0.3`。 (local)
- [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V12_9_6.md:L1-L104`：七维 finding、修复与验收。 (local)

### 关键 Diff / Key Diff
```diff
-evidence package internal consistency only
+shared admission compares evidence with the live imported controller source
+monitored startup rejects stale configured left/right capability sources
```
```diff
-worker-private source-binding admission
+shared validator output consumed by Readiness and Action
+execution-time digest guard remains before every provider command
```

### 七维 Code Review / Seven-Dimension Review
- 四个 Major 与一个 Minor 均已修复：live source 比较缺失、启动可接受旧 snapshot、配置左右臂身份未校验、磁盘 source 不代表进程加载身份，以及非法路径泄漏 `TypeError`。修复后七个维度全部通过，Blocker 0、Major 0、Minor 0。 (local)
- Four Major findings and one Minor finding are fixed: missing live-source comparison, startup acceptance of stale snapshots, missing configured-arm identity validation, disk source not representing loaded-process identity, and raw `TypeError` leakage for invalid paths. All seven dimensions pass with zero remaining findings. (local)
- 无 RGB/颜色/排列/benchmark/实体/候选/相机/固定机械臂分支；无自动观察、换候选、换臂、重试、replan 或 Action。 (local)
- No RGB/color/order/benchmark/entity/candidate/camera/fixed-arm branch and no automatic observation, candidate/arm switch, retry, replan, or Action was added. (local)

### 验证 / Validation
- Adapter changed path `120 passed`；Skill full `379 passed`；Core planning/recovery `174 passed`；release/version `88 passed`；Ruff、compileall、`git diff --check` 通过。 (local)
- Node SHA-256 `091b074cf378eaa4ca7661848de0b210d2560017f577d1d1ff8ec43895dd6db8`；Skill SHA-256 `741a171c19a1db343dbacba927e3c70afe81fcd0a73ee2e7ecf594dff5a95fd8`。 (local)
- 未创建/恢复 AgentTask，未调用 Gateway Query/Action，未推进 simulator/物理运动，也未改变 Runtime 生命周期。 (local)

### Git 提交 / Git Commit
- Commit: `4224d65`（实现、回归与七维审核 / implementation, regression coverage, and seven-dimension review）
- Branch: `feature/planning-loop`
- 时间 / Time: `2026-10-07 Asia/Shanghai`

## v12.9.5 (2026-10-07 19:07) - codex

### 变更摘要 / Change Summary
- [env] [chore] 将唯一非终态旧任务终结为 `failed`；旧 Runtime 保留的未知 Action ownership 经受支持的强制停止进入审计记录，未重发 Action，也未声明物理结果已对账。 (local)
- [env] [chore] Settle the only non-terminal old task as `failed`; preserve the old Runtime's unknown-Action ownership in the supported forced-stop audit without resending the Action or claiming physical reconciliation. (local)
- [chore] [release] 安装并启动 Skill `3.0.2`、Node `0.10.10`，保留 `robotwin-blocks-ranking-graspnet` profile、operator env、模型配置和权限。 (local)
- [chore] [release] Install and start Skill `3.0.2` and Node `0.10.10` while preserving the GraspNet profile, operator environment, model configuration, and permissions. (local)

### 部署关键 Diff / Deployment Key Diff
```diff
-pick-place-workflow 3.0.0; robotwin20_persistent_host 0.10.8; runtime_c1c591d68c0b46aa
+pick-place-workflow 3.0.2; robotwin20_persistent_host 0.10.10; runtime_4e1e061c14614c73
-task_e3949a368fad4e3d executing; retained invocation/task binding
+task_e3949a368fad4e3d failed; nonterminal_tasks=0; new runtime ownership=[]
```

### 验证 / Validation
- Dora flow、Gateway 与 11/11 Tool context ready；Node receipt 和实际 spawn 路径均验证为 `0.10.10`，新 Runtime ownership 为空。 (local)
- 本地场景理解 primary 保持 `qwen3-vl-4b-awq`；fallback 保持 `gpt-6.1-sol/high`；operator env 权限为 `0600`。 (local)
- Node SHA-256 `d807b1b3e6b9a86f6cc597da8ab6de9643b8b23a75bc72372889ac1d45fd195e`；Skill SHA-256 `c9992caa9c256780307e1a4de33a15f90971292e5db82c7ebd5f49f0800f1772`。 (local)
- 未创建/恢复新 AgentTask，未调用 Gateway Query/Action，未推进 simulator step 或物理运动。 (local)

### Git 提交 / Git Commit
- Commit: `409e0e2`（部署与验收记录 / deployment and acceptance record）
- Branch: `feature/planning-loop`
- 时间 / Time: `2026-10-07 Asia/Shanghai`
