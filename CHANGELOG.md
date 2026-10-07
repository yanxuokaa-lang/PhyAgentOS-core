# Changelog
## Archive
- [2026-10 part2](changelog/2026-10_part2.md)
- [2026-10](changelog/2026-10.md)
- [2026-09 part21](changelog/2026-09_part21.md)
- [2026-09 part20](changelog/2026-09_part20.md)

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

## v12.9.4 (2026-10-07 18:45) - codex

### 变更摘要 / Change Summary
- [sense] [fix] Readiness 与 Action 复用同一 capability validation/controller qualification evidence 准入，并仅接受声明限位的精确 float32 往返表示。 (local)
- [sense] [fix] Make Readiness and Action reuse the same capability-validation/controller-qualification evidence admission and admit only exact float32 round-trip representations of declared limits. (local)
- [comm] [fix] `outcome_unknown + replay` 在一次只读 reducer replay 后进入 `reconciliation_required`，不重发 Action。 (local)
- [comm] [fix] Make `outcome_unknown + replay` enter `reconciliation_required` after one read-only reducer replay without resending the Action. (local)

### 文件变更详情 / File Changes
- [新增 / Added] `robotwin_motion_policy.py:L1-L174`：共享 capability/qualification evidence 准入与 controller-limit 适配。 (local)
- [修改 / Modified] `robotwin_route_planner.py:L17,L389-L399`、`robotwin_simulation_probe_worker.py:L45-L49,L1113-L1135`：Readiness 与 Action 共用 motion-policy validator。 (local)
- [修改 / Modified] `robotwin_capability_controller.py:L25-L61`：精确 float32 boundary encoding 匹配；`planning_loop.py:L1488-L1503`：未知结果 replay 后统一阻塞对账。 (local)
- [新增测试 / Added Tests] controller、persistent route evaluator 与 planning-loop 回归覆盖伪近界值、evidence gate、单次 replay 与任务收敛。 (local)
- [新增 / Added] `docs/forge/IMPLEMENTATION_REVIEW_V12_9_4.md:L1-L84`：两个 Major、一个 Minor、修复与七维验收。 (local)

### 关键 Diff / Key Diff
```diff
-Readiness validates capability JSON only
+Readiness and Action call validate_motion_policy_bindings()
-outcome_unknown + replay -> replay_required
+outcome_unknown + replay -> reducer-only replay -> reconciliation_required
-near-bound distance window
+exact float32(bound) match
```

### 七维 Code Review / Seven-Dimension Review
- 初审 Blocker 0、Major 2、Minor 1；全部修复。修复后七个维度均通过，Blocker 0、Major 0、Minor 0。 (local)
- Initial review found zero Blocker, two Major, and one Minor issue; all are fixed. All seven dimensions pass after fixes with zero remaining findings. (local)
- 没有 RGB/颜色/排列/benchmark/实体/候选/相机/固定机械臂分支，也没有自动观察、Action、重试、放置或 replan。 (local)

### 验证 / Validation
- Adapter `143 passed, 4 deselected`；Core `164 passed`；Skill/release `75 passed`；Ruff、compileall、`git diff --check` 通过。 (local)
- Node `0.10.10` SHA-256 `d807b1b3e6b9a86f6cc597da8ab6de9643b8b23a75bc72372889ac1d45fd195e`；Skill `3.0.2` SHA-256 `c9992caa9c256780307e1a4de33a15f90971292e5db82c7ebd5f49f0800f1772`。未安装或启动。 (local)
- 当前解释器缺少 `cv2`，4 个既有 video 用例未计入通过证据；未创建任务、调用 Gateway、推进模拟器/物理运动或改变 Runtime 生命周期。 (local)

### Git 提交 / Git Commit
- Commit: `b0fa615`（实现、修复与七维审核 / implementation, fixes, and seven-dimension review）
- Branch: `feature/planning-loop`
- 时间 / Time: `2026-10-07 Asia/Shanghai`

## v12.9.3 (2026-10-07 18:09) - codex

### 变更摘要 / Change Summary
- [sense] [fix] 统一 route readiness、prepared-plan admission 与 live controller 的 MotionCapability 数值边界语义，仅规范化 float32 往返边界误差，实质越界继续 fail-closed。 (local)
- [sense] [fix] Unify MotionCapability numerical-bound semantics across route readiness, prepared-plan admission, and the live controller, canonicalizing only float32 round-trip boundary error while material violations remain fail-closed. (local)
- [comm] [fix] 未知 Action 结果的 stop/replan 决策现在进入 `reconciliation_required` 阻塞投影；不自动重试、观察、放置、换臂、换候选或 replan。 (local)
- [comm] [fix] Stop/replan decisions after an unknown Action outcome now enter `reconciliation_required`; no automatic retry, observation, placement, arm/candidate switch, or replan is introduced. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `robotwin_capability_controller.py:L11-L65,L148-L169`、`robotwin_planning_geometry.py:L136-L174`、`robotwin_route_planner.py:L166-L224,L328-L410,L502-L509`：共享 capability-bound 规范化并接入逐臂 Readiness。 (local)
- [修改 / Modified] `robotwin_simulation_probe_worker.py:L554-L709,L1580-L1604`、`robotwin_persistent_engine.py:L555-L557`：Action 前重验并执行规范化的持久化轨迹。 (local)
- [修改 / Modified] `PhyAgentOS/agent/planning_loop.py:L1488-L1536`：未知结果优先进入 reconciliation；replay 保持 reducer-only。 (local)
- [新增测试 / Added Tests] `tests/test_planning_loop.py:L1291-L1350` 及 Adapter controller/planner/simulation/persistent tests：边界一致性、实质越界和未知结果收敛的 no-motion 回归。 (local)
- [新增 / Added] `CAPABILITY_BOUND_ADMISSION_DIAGNOSIS_20261007.md:L1-L75`、`OUTCOME_UNKNOWN_RECONCILIATION_DIAGNOSIS_20261007.md:L1-L74`、`IMPLEMENTATION_REVIEW_V12_9_3.md:L1-L74`：两份诊断与七维审核。 (local)

### 关键 Diff / Key Diff
```diff
-planner/controller use different numerical admission
+one controller-owned rule is reused before persistence, before Action, and before provider write
-outcome_unknown stop/replan can bypass lifecycle convergence
+outcome_unknown stop/replan -> blocked: reconciliation_required:<node>
```

### 七维 Code Review / Seven-Dimension Review
- Blocker 0、Major 0、Minor 0；七个维度全部通过。没有 RGB/颜色/排列/benchmark/实体/候选/相机/固定机械臂专用分支，也没有自动 Action 或 replan。 (local)
- Zero Blocker, Major, or Minor findings; all seven dimensions pass. No RGB/color/order/benchmark/entity/candidate/camera/fixed-arm branch or automatic Action/replan was added. (local)

### 验证 / Validation
- Core `187 passed`；Adapter capability/Persistent chains `93 passed, 4 deselected` 与 `78 passed`；Skill/release `75 passed`；Ruff、compileall、`git diff --check` 通过。 (local)
- Node `0.10.9` SHA-256 `523ce506eeee3ffc143715ddd1bb98671dfa3ef7847d6de143da45214bfe4d8f`；Skill `3.0.1` SHA-256 `b323781c830e98259b8bb47b65a08f627b3b80ebd1fa1733a177f9f78da8865f`。未安装或启动。 (local)
- 当前解释器缺少现有视频测试依赖 `cv2`；验证未创建 AgentTask、调用 Gateway、推进 simulator/物理运动或改变 Runtime 生命周期。 (local)

### Git 提交 / Git Commit
- Commit: `3a1014a`（实现、诊断与七维审核 / implementation, diagnoses, and seven-dimension review）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-07 18:36 Asia/Shanghai

## v12.9.2 (2026-10-07 15:45) - codex

### 变更摘要 / Change Summary
- [env] [chore] 正常取消唯一 `awaiting_replan` 旧任务；在 invocation/session/task-binding ownership 清空且非终态任务为 0 后，无 `--force` 停止旧 Runtime。 (local)
- [env] [chore] Normally cancel the only old `awaiting_replan` task and stop the old Runtime without `--force` after invocation/session/task-binding ownership is empty and non-terminal tasks reach zero. (local)
- [chore] [release] 安装 Skill `pick-place-workflow 3.0.0`，保持 Node `robotwin20_persistent_host 0.10.8`、profile、operator env、权限和模型配置不变。 (local)
- [chore] [release] Install Skill `pick-place-workflow 3.0.0` while preserving Node `robotwin20_persistent_host 0.10.8`, the runtime profile, operator environment, permissions, and model configuration. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `changelog/2026-10_part2.md:L3-L57`：记录任务取消、正常 stop、安装/启动、版本/摘要和 no-motion 验收 / record task cancellation, normal stop, install/start, versions/digests, and no-motion acceptance.
- [修改 / Modified] `CHANGELOG.md:L8-L37`：维护最近五个版本 / maintain the latest five versions.

### 部署关键 Diff / Deployment Key Diff
```diff
-pick-place-workflow 2.10.14; runtime_1c512b49353c4b23; task_cb2ff2de02cd44ca awaiting_replan
+pick-place-workflow 3.0.0; runtime_c1c591d68c0b46aa; nonterminal_tasks=0
 robotwin20_persistent_host 0.10.8; robotwin-blocks-ranking-graspnet
```

### 验证 / Validation
- Runtime `runtime_c1c591d68c0b46aa` running，Dora flow running，Gateway ready，11/11 Tool context ready；Node lock 与实际 spawn 均为 `0.10.8`，Runtime ownership 为空，非终态任务为 0。
- 本地场景理解 primary 保持 `qwen3-vl-4b-awq`；fallback 保持 `gpt-6.1-sol`、`reasoning_effort=high`；operator env 权限保持 `0600`。
- Skill bundle SHA-256 `5b05405ba07e0831260ef2cd8e6fde2d42355c0299656ea693a1807d288b8805`；Node archive SHA-256 `6b5fd5c92d0fd420013a59ee69bffcc87a807c9a7e8b5b48e2883718fb423dc8`。
- 未创建/恢复 AgentTask，未调用 Gateway Query/Action，未执行 simulator step 或物理运动。

### Git 提交 / Git Commit
- Commit: `10daf18`（部署记录 / deployment record）
- Branch: `feature/planning-loop`
- 时间 / Time: 2026-10-07 16:09 Asia/Shanghai
