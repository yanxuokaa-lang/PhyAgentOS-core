# Changelog

## 最近五版本 / Latest five versions

## v13.3.11 (2026-10-13 00:06) - codex

### 变更摘要 / Summary [完成]
- [policy] [fix] 从持久化 AgentTask 为每个 node/continuation turn 重建冻结 Skill、执行阶段、已完成效果、no-replay、目标账本、当前世界 lineage 与节点 Tool policy，修复长任务压缩后重复查 contract/goal 或遗忘已完成前缀。 / Reconstruct frozen Skill, phase, completed effects, no-replay history, goal ledger, current-world lineage, and node Tool policy from persisted AgentTask facts for every node/continuation turn, preventing contract/goal rereads and completed-prefix loss after compaction.
- [eval] [test] 七维审查修复 effective settlement 冲突、stale calibration、歧义 attainment、unknown no-replay、无界兼容字段及 evidence-order 错误；无任务专用分支。 / The seven-dimension review fixes effective-settlement conflicts, stale calibration, ambiguous attainment, unknown no-replay, unbounded compatibility fields, and evidence-order handling without task-specific branches.

### 文件与关键 Diff / Files and Key Diff
- `PhyAgentOS/agent/prompt_context.py:L1020-L1776,L1837-L1848,L1945-L2044`：通用 durable context、effective settlement、exact-lineage world、goal ledger 与 bounded continuation。 / Generic durable context, effective settlements, exact-lineage world, goal ledger, and bounded continuation.
- `PhyAgentOS/agent/loop.py:L344-L355,L1893-L1915,L1964-L1980`、`planning_loop.py:L1492-L1524`：注入 authoritative loaders，并使节点提示消费冻结 Skill/contract/phase。 / Inject authoritative loaders and make node prompts consume frozen Skill/contract/phase facts.
- `tests/test_prompt_context.py:L769-L845,L1854-L2155`、`tests/test_planning_loop.py:L576-L592`、`tests/test_agent_foundation.py:L2143-L2182`：late settlement、unknown no-replay、lineage、attainment 歧义、compaction 与 AgentLoop 回归。 / Regressions for late settlement, unknown no-replay, lineage, attainment ambiguity, compaction, and AgentLoop integration.
- `docs/forge/CONTINUATION_CONTEXT_SKILL_COMPACTION_DIAGNOSIS_20261013.md:L1-L114`：证据、ownership、通用修复与七维审查。 / Evidence, ownership, generic repair, and seven-dimension review.

```diff
- compacted node = current node + Skill identity + generic rules
+ compacted node = frozen Skill route + phase + effects + no-replay + goal ledger + exact-lineage world + Tool policy
- raw settlement / partial attainment wildcard / unbounded compatibility lists
+ effective settlement / exact-or-unique attainment / bounded lists with totals
```

### 七维审查与安全边界 / Seven-Dimension Review and Safety Boundary
- 架构、正确性、可观测、恢复幂等、机器人安全、扩展兼容与 AgentLoop 收敛七维发现的 Blocker/Major 已全部修复；Coordinator/Runtime/Gateway/planner/motion ownership 不变。 / All Blocker/Major findings across architecture, correctness, observability, recovery/idempotency, robotics safety, extension compatibility, and AgentLoop convergence were fixed; ownership boundaries remain unchanged.
- 无 RGB、颜色、方块、benchmark、provider 或节点名分支；无新 persisted schema、ToolSpec、hash、baseline 或 gate。旧视觉实体、几何和 calibration 不会成为当前 Action 输入，歧义 attainment 保持 unknown。 / No task/provider/node-specific branch or new persisted schema, ToolSpec, hash, baseline, or gate; old visual/geometry/calibration facts cannot become current Action inputs, and ambiguous attainment stays unknown.
- focused `320 passed in 10.13s`；full `904 passed in 31.20s`；scoped Ruff、compileall、`git diff --check` 通过。未部署/重启 Runtime、调用 live Query/Action、读取相机或执行运动。 / Focused and full suites plus scoped static checks passed; no Runtime deployment/restart, live Query/Action, camera read, or motion occurred during implementation review.

### Git 提交 / Git Commit
- Implementation/review commit: `5782b0fa` on `feature/planning-loop`; documentation/index completion follows separately. / 实现与审查提交：`5782b0fa`，分支 `feature/planning-loop`；日志与索引引用随后补全。

## v13.3.10 (2026-10-12 23:25) - codex

### 变更摘要 / Summary [完成]
- [env] [chore] 按用户授权强制停止旧 Runtime，发布并安装 Skill `3.0.22` / Node `1.0.12`，刷新 editable Core，并启动既有 `robotwin-blocks-ranking-graspnet` profile。 / Under explicit authorization, force-stop the old Runtime, publish and install Skill `3.0.22` / Node `1.0.12`, refresh editable Core, and start the existing `robotwin-blocks-ranking-graspnet` profile.
- [eval] [test] 验证 artifact lock、运行源码、进程、端口及 11/11 Tool readiness；没有创建/恢复 AgentTask 或调用 Query/Action。 / Verify artifact locks, running source, processes, ports, and all 11 Tool contexts; create/resume no AgentTask and invoke no Query/Action.

### 文件、版本与关键 Diff / Files, Versions, and Key Diff
- `examples/forge-skills/pick-place-workflow/pyproject.toml:L1-L6`、`skill.yaml:L1-L4,L219-L229`：Skill `3.0.21` → `3.0.22`，Node `1.0.11` → `1.0.12`，Node SHA=`96818ddbe23927326055f53e8424a9599bc7e04ff0a5357003758f9ed07c9b51`。 / Bump Skill and Node versions and lock the recorded Node SHA.
- `examples/forge-skills/pick-place-workflow/CHANGELOG.md:L1-L11`、`tests/test_grasp_propose.py:L264-L274`：发布说明和版本一致性回归。 / Release notes and version-consistency regression.
- `out/releases/v13.3.10/robotwin20_persistent_host-1.0.12-linux-x86_64.tar.gz`、`pick-place-workflow-3.0.22.tar.gz`：Node/Skill release artifacts；Skill bundle SHA=`7e40780869f6238c40ba543b665e583ee105c59148c9af15677d7be0fa36f82c`。 / Node and Skill release artifacts with the recorded bundle SHA.

```diff
- Skill 3.0.21 / Node 1.0.11 / old host+simulator
+ Skill 3.0.22 / Node 1.0.12 / new host+simulator
+ typed placement-postcondition failure and per-Action measurement reset installed
```

### 部署结果与安全边界 / Deployment Result and Safety Boundary
- 强制停止成功，旧 host PID `3209179`、worker PID `3209222` 退出，独立 Qwen PID `176466`/8012 未停止。新 host PID `3256163`、worker PID `3256218` 于 23:29 创建。 / Forced stop succeeded; the old host/worker exited while independent Qwen remained running. New host/worker processes were created at 23:29.
- Runtime lock `33f3c5ea.../runtime-lock.json` 固定 Skill `3.0.22`、Node `1.0.12` 与 Node SHA；Skill/Dora=`running`、Gateway=`ready`、11/11 Tool contexts=`ready`，19020/8012 监听。 / The new runtime lock pins Skill, Node, and Node SHA; Skill/Dora are running, Gateway and all 11 Tool contexts are ready, and ports 19020/8012 listen.
- release/workflow/provider fixture `456 passed in 13.72s`；Core v13.3.9 已通过 focused `315`、full `900`。任务库仅 `cancelled=203`、`failed=99`，没有 non-terminal task。 / Release/workflow/provider fixtures passed; Core v13.3.9 already passed focused and full suites. The task store contains only terminal tasks.
- 未调用 Gateway Query/Action、相机或 simulator action；readiness 不作为场景内容或任务成功证明。 / No Gateway Query/Action, camera, or simulator action was invoked; readiness is not treated as proof of scene contents or task success.

### Git 提交 / Git Commit
- Deployment/release commit: `0c3602ec` on `feature/planning-loop`; documentation/index completion follows separately. / 部署与发布提交：`0c3602ec`，分支 `feature/planning-loop`；日志与索引补全随后单独提交。

## v13.3.9 (2026-10-12 22:59) - codex

### 变更摘要 / Summary [完成]
- [model] [fix] 将 Runtime 已测得的放置后置条件超限从 `outcome_unknown` 修正为 `failed/outcome_known=true`，保留 release/retreat/empty-possession 与误差/容差；未分类 post-release 异常继续 fail-closed。 / Reclassify measured placement-postcondition violations from `outcome_unknown` to `failed/outcome_known=true`, retaining release/retreat/empty-possession and measurement/tolerance; unclassified post-release exceptions remain fail-closed.
- [policy] [fix] 已知 Action 后置条件失败确定性进入单一 scene-refresh Query recovery revision，不重放原 Action；consumer projection 缺少 semantic join field 时允许 AgentLoop 在同节点有界补齐。 / Deterministically route known Action postcondition failures to a recovery revision containing one scene-refresh Query without replaying the Action; allow AgentLoop to fill a missing consumer-projection semantic join field in the same node.
- [docs] [docs] 保存 `task_bc5b3e04a00b45f7` 的精确诊断：位置误差 `0.016338 m < 0.04 m`，姿态误差 `0.425647 rad > 0.35 rad`；后续 bind 已成功，真正阻塞是 `grasp.propose` selection 缺 `entity_ref` 且 Gateway 未调用。 / Preserve the exact diagnosis: position error passed, orientation error exceeded tolerance; subsequent binding succeeded, while the actual later blocker was a missing `entity_ref` in `grasp.propose` selection before any Gateway call.

### 文件与关键 Diff / Files and Key Diff
- `examples/forge-adapters/robotwin20/runtime/robotwin_persistent_engine.py:L58-L66,L579-L740,L796-L872`：typed known postcondition failure、每次 Action 清理旧测量、测量/容差与 known-terminal scene effects。 / Typed known postcondition failure, per-Action stale-measurement clearing, measurement/tolerance, and known-terminal scene effects.
- `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_manipulation.py:L47-L48,L130-L226`：bounded Action receipt allowlist。 / Bounded Action-receipt allowlist.
- `PhyAgentOS/agent/recovery_decisions.py:L79-L118,L218-L342`：区分 Query evidence 与 measured Action recovery，只生成 scene-refresh Query。 / Distinguish Query-evidence and measured-Action recovery and generate only a scene-refresh Query.
- `PhyAgentOS/agent/tools/planning.py:L431-L452`、`PhyAgentOS/agent/loop.py:L1675-L1725`：缺失通用 semantic join field 的同节点纠正。 / Same-node correction for a missing generic semantic join field.
- `tests/test_agent_foundation.py:L1364-L1410,L2620-L2920`、`tests/test_planning_selection.py:L337-L523`、`examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py:L490-L666`：no-motion recovery、projection、跨 Action 陈旧测量与 Runtime/receipt 回归。 / No-motion recovery, projection, cross-Action stale-measurement, Runtime, and receipt regressions.
- `docs/forge/PLACEMENT_POSTCONDITION_ENTITY_SELECTION_DIAGNOSIS_20261012.md:L1-L131`：证据、ownership、恢复边界、七维审查和验证。 / Evidence, ownership, recovery boundaries, seven-dimension review, and verification.

```diff
- measured postcondition violation -> outcome_unknown
+ measured postcondition violation -> failed, outcome_known=true, refresh_declared_evidence
+ unclassified post-release exception -> outcome_unknown

- projection missing selected <join_field> -> requires_replan
+ projection missing selected <join_field> -> bounded same-node correction

- recovery may ask the model to replay/replan
+ known measured Action failure -> scene-refresh Query only
```

### 架构、安全与验证 / Architecture, Safety, and Validation
- 修复保持 PAOS ownership：Runtime 拥有物理事实，Adapter 投影 bounded receipt，Coordinator 持久化选择，AgentLoop 编排有限纠正；无 RGB、颜色、方块、provider、task-id 或节点名分支。 / Preserve PAOS ownership: Runtime owns physical truth, Adapter projects bounded receipts, Coordinator persists selections, and AgentLoop orchestrates bounded correction; no RGB, color, block, provider, task-id, or node-name branch.
- 不改目标、容差、轨迹、分阶段运动、freshness、calibration、collision、IK 或 motion authorization；不新增 hash、baseline、gate、持久化 schema 或第二状态机。 / Change no target, tolerance, trajectory, staged motion, freshness, calibration, collision, IK, or motion authorization; add no hash, baseline, gate, persisted schema, or second state machine.
- 七维审查发现并修复 1 Major（跨 Action 陈旧 placement measurement）；无 Blocker 或未修复 Major。Focused/cross-layer `315 passed in 11.34s`；full repository `900 passed in 30.56s`；Ruff、compileall、`git diff --check` passed。全程 no-motion，未部署/重启 Runtime 或调用 live Gateway。 / Seven-dimension review found and fixed one Major (cross-Action stale placement measurement), with no Blocker or unresolved Major. Focused/cross-layer and full suites passed, as did Ruff, compileall, and diff checks; entirely no-motion with no Runtime deployment/restart or live Gateway call.

### Git 提交 / Git Commit
- Implementation/review commit: `8eae0db3` on `feature/planning-loop`; documentation/index completion follows separately. / 实现与审查提交：`8eae0db3`，分支 `feature/planning-loop`；日志与索引补全随后单独提交。

## v13.3.8 (2026-10-12 22:02) - codex

### 变更摘要 / Summary [完成]
- [env] [chore] 按用户要求重新启动已进入 `failed` 的 `pick-place-workflow` Runtime：强制清理仍显示 running 的 Dora flow，再复用既有 Skill `3.0.21`、Node `1.0.11`、profile 与 operator-owned environment 创建新的 Runtime/simulator 生命周期。 / At the user's request, restart the failed `pick-place-workflow` Runtime: force-clean the Dora flow still reported as running, then reuse Skill `3.0.21`, Node `1.0.11`, the existing profile, and operator-owned environment to create a fresh Runtime/simulator lifecycle.
- [eval] [test] 仅验收生命周期、进程、端口与 11 项 Tool readiness；不自动恢复或取消现有 AgentTask，不调用 Query/Action，不读取相机，不推进 simulator action。 / Validate only lifecycle, processes, ports, and all 11 Tool contexts; do not automatically resume or cancel the existing AgentTask, invoke Query/Action, read cameras, or advance simulator actions.

### 停止前事实与边界 / Pre-Restart Facts and Boundary
- Runtime `runtime_e643e16c68a14f21` 已为 `failed`，Gateway 19020 无监听，但 Dora flow 仍报告 running；Runtime registry 无 active invocation/session，有一个 task binding。 / Runtime `runtime_e643e16c68a14f21` is already failed and Gateway port 19020 is not listening, while the Dora flow still reports running; the Runtime registry has no active invocation/session and one task binding.
- `task_84e561b1b98d450c` 为 `awaiting_replan`；当前未结算 `grasp.propose` 是 Query，settlement 记录 `world_change_started=false`。重启不把它解释为 Action 成功或失败，不恢复、取消或重放该任务。 / `task_84e561b1b98d450c` is awaiting replan; its unsettled `grasp.propose` is a Query whose settlement records `world_change_started=false`. Restart does not reinterpret it as Action success/failure and will not resume, cancel, or replay the task.
- 独立 Qwen PID `176466` 正常监听 8012，不属于本次 Skill Runtime 生命周期。 / Independent Qwen PID `176466` is listening normally on 8012 and is outside this Skill Runtime lifecycle.

### 实际重启与恢复 / Completed Restart and Recovery
- [env] [chore] 标准 `paos skill stop --force` 因 Dora coordinator 仍记录 active flow、但 daemon 已丢失而失败；`dora stop --force` 与 `dora destroy` 同样返回 `no daemon connection`。精确终止孤立 `dora start` PID `3128061` 后，确认系统仅有该一个 active flow，再终止陈旧 coordinator PID `2144356`；未删除状态文件或修改数据库。 / Standard `paos skill stop --force` failed because the Dora coordinator retained an active flow while the daemon was gone; `dora stop --force` and `dora destroy` likewise returned `no daemon connection`. After terminating the orphaned `dora start` PID `3128061`, the system was confirmed to have only that active flow, then stale coordinator PID `2144356` was terminated; no state file or database was deleted or edited.
- [env] [chore] 首次启动由 PAOS 重建 Dora coordinator/daemon 和 simulator，但 host 在配置阶段以 `model credential environment is unavailable: ROBOTWIN20_MODEL_API_KEY` fail-closed；原因是新 daemon 不再继承旧长期进程的 shell 凭据，而 operator env 本身不保存该 secret。 / The first start let PAOS recreate the Dora coordinator/daemon and simulator, but the host failed closed during configuration with `model credential environment is unavailable: ROBOTWIN20_MODEL_API_KEY`; the new daemon no longer inherited the old long-lived process's shell credential, while the operator env intentionally does not store that secret.
- [env] [chore] 从现有 PAOS provider 配置的 mode-`0600` `apiKeyFile` 读取同一凭据并仅注入启动子进程环境；未输出凭据值，未修改 config/operator env。清理首次失败 flow 后，第二次 PAOS start 成功。 / The existing credential was read from the PAOS provider configuration's mode-`0600` `apiKeyFile` and injected only into the startup child-process environment; its value was never output and config/operator env were not modified. After cleaning the first failed flow, the second PAOS start succeeded.
- [eval] [test] 新 Runtime `runtime_5511c31f7dc54e9e` 于 22:10:14 启动；Dora coordinator PID `3209109`、daemon PID `3209135`、host PID `3209179`、simulator worker PID `3209222`。Runtime/Dora=`running`、Gateway=`ready`、11/11 Tool contexts=`ready`，19020 与 Qwen 8012 均监听。 / New Runtime `runtime_5511c31f7dc54e9e` started at 22:10:14, with Dora coordinator PID `3209109`, daemon PID `3209135`, host PID `3209179`, and simulator worker PID `3209222`. Runtime/Dora are running, Gateway and all 11 Tool contexts ready, and ports 19020 and Qwen 8012 are listening.
- [eval] [test] `task_84e561b1b98d450c` 的 `task_cancel_requested` 事件发生在 22:03:34，早于本轮首次 stop 22:04:01；重启没有发起该取消。最终任务计数 `cancelled=203`、`failed=98`、non-terminal=`0`，新 Runtime 无 active invocation/session/task binding。 / The `task_cancel_requested` event for `task_84e561b1b98d450c` occurred at 22:03:34, before this run's first stop at 22:04:01; the restart did not initiate that cancellation. Final counts are `cancelled=203`, `failed=98`, and non-terminal=`0`, with no active invocation/session/task binding on the new Runtime.

### 影响文件 / Affected Files
- `changelog/2026-10_part6.md`
- `CHANGELOG.md`

### 文件变更详情 / File Changes
- [修改] `changelog/2026-10_part6.md:L292-L332`：记录 v13.3.8 Dora 控制面恢复、凭据传递失败分支、新 Runtime 进程与 no-motion 验收。 / Record v13.3.8 Dora control-plane recovery, the credential-propagation failure branch, new Runtime processes, and no-motion validation.
- [修改] `CHANGELOG.md:L5-L45`：将 v13.3.8 完整记录加入最近五版本并滚出 v13.3.3。 / Add the complete v13.3.8 record to the latest five versions and roll out v13.3.3.

### 关键 Diff / Key Diff
```diff
- failed Runtime + coordinator-owned stale flow + missing daemon
+ fresh Dora coordinator/daemon + new Runtime/simulator lifecycle
- implicit credential inheritance from a long-lived daemon
+ existing mode-0600 apiKeyFile -> startup child environment only
  no task resume, Query/Action invocation, camera read, or simulator action
```

### 验证与安全边界 / Validation and Safety Boundary
- 本轮仅执行 Runtime/Dora 生命周期控制、配置预检和只读 readiness/process/port/task-store 检查。未调用 Gateway Query/Action、未读取相机、未推进 simulator action、未执行轨迹或运动。 / This run performed only Runtime/Dora lifecycle control, configuration preflight, and read-only readiness/process/port/task-store checks. It invoked no Gateway Query/Action, read no camera, advanced no simulator action, and executed no trajectory or motion.
- 首次启动的 simulator worker 完成初始化后因 host 配置缺失而正常关闭；最终成功启动创建了新的 simulator worker，因此场景生命周期重新初始化，但 readiness 不作为具体场景内容证明。 / The first-start simulator worker shut down after host configuration failed; the final successful start created another simulator worker, so the scene lifecycle was reinitialized, while readiness is not treated as proof of concrete scene contents.

### Git 提交 / Git Commit
- Restart log/index commit: `b6ce82b3` on `feature/planning-loop`; commit-reference completion follows separately. / 重启日志与索引提交：`b6ce82b3`，分支 `feature/planning-loop`；提交引用补全随后单独完成。

## v13.3.7 (2026-10-12 21:50) - codex

### 变更摘要 / Summary [完成]
- [env] [chore] 按用户明确授权强制停止旧 `pick-place-workflow` Runtime，刷新当前 checkout 的 editable Core，并复用已安装 Skill `3.0.21`、Node `1.0.11`、既有 `robotwin-blocks-ranking-graspnet` profile 与 operator-owned environment 启动新 Runtime。 / Under explicit user authorization, force-stop the old `pick-place-workflow` Runtime, refresh the editable Core from the current checkout, and start a new Runtime using the installed Skill `3.0.21`, Node `1.0.11`, existing `robotwin-blocks-ranking-graspnet` profile, and operator-owned environment.
- [eval] [test] 仅验收 Runtime/Dora/Gateway/11 项 Tool context、Core 导入路径、新 host/simulator 进程、Qwen 8012 与任务库状态；不创建或恢复 AgentTask，不调用 Query/Action，不读取相机，不推进 simulator action。 / Validate only Runtime/Dora/Gateway/all 11 Tool contexts, the Core import path, new host/simulator processes, Qwen on 8012, and task-store state; do not create or resume an AgentTask, invoke Query/Action, read cameras, or advance simulator actions.

### 部署与验收 / Deployment and Validation
- 强制停止成功；Runtime=`stopped`、Dora=`down`、Gateway=`unavailable`、19020 释放，旧 host PID `2244656`、simulator worker PID `2244784` 及 enrichment workers 退出；独立 Qwen PID `176466` 保持监听 8012。 / Forced shutdown succeeded; Runtime stopped, Dora went down, Gateway became unavailable, port 19020 was released, and the old host, simulator worker, and enrichment workers exited; independent Qwen PID `176466` remained on 8012.
- editable Core 从 `/home/yanxu/PhyAgentOS-forge` 导入并加载 v13.3.5/v13.3.6 选择恢复符号；已安装 Node `1.0.11` SHA-256 验证通过，Skill `3.0.21` / Node `1.0.11` 制品未改变。 / The editable Core imports from the current checkout with the v13.3.5/v13.3.6 selection-recovery symbols loaded; installed Node `1.0.11` passed SHA-256 verification, with Skill `3.0.21` / Node `1.0.11` artifacts unchanged.
- 新 Runtime `runtime_e643e16c68a14f21`、host PID `3128083`、simulator worker PID `3128204` 已启动，worker startup=`16.379s`；Runtime/Dora running、Gateway 与 11/11 Tool contexts ready。 / New Runtime `runtime_e643e16c68a14f21`, host PID `3128083`, and simulator worker PID `3128204` started, with worker startup taking `16.379s`; Runtime/Dora are running and Gateway plus all 11 Tool contexts are ready.
- 任务最终计数 `cancelled=202`、`failed=98`、non-terminal=`0`；未创建/恢复任务、调用 Query/Action、读取相机或推进 simulator action。readiness 不作为场景内容证明。 / Final task counts are `cancelled=202`, `failed=98`, and non-terminal=`0`; no task was created/resumed, no Query/Action invoked, no camera read, and no simulator action advanced. Readiness is not treated as scene-content proof.

### 文件与关键 Diff / Files and Key Diff
- `changelog/2026-10_part6.md:L250-L290`：完整双语部署记录。 / Complete bilingual deployment record.
- `CHANGELOG.md:L5-L30`：最近五版本索引。 / Latest-five index.

```diff
- old Runtime process using the previous Core process lifetime
+ runtime_e643e16c68a14f21 with fresh host/simulator processes
+ current editable Core imports v13.3.5/v13.3.6 changes
  installed Skill 3.0.21 / Node 1.0.11 unchanged
  no live Query, Action, camera read, simulator advancement, or motion
```

详见 [v13.3.7 月度日志](changelog/2026-10_part6.md)。 / See the [v13.3.7 detailed log](changelog/2026-10_part6.md).
- Deployment log/index commit: `ee95434d` on `feature/planning-loop`; commit-reference completion follows separately. / 部署日志与索引提交：`ee95434d`，分支 `feature/planning-loop`；提交引用补全随后单独完成。

## Archived detailed records / 已归档详细记录

The latest five records above are mirrored from the monthly archive. Older snapshots below remain for historical compatibility. / 上述最近五条与月度归档同步；以下旧快照仅为历史兼容保留。

## v13.3.6 (2026-10-12 21:37) - codex

### 变更摘要 / Summary [完成]
- [policy] [fix] 七维审查修复确定性 Query selection 绕过显式语义选择上下文的问题：只有节点不存在 `selection_required` 上下文时才允许零自由度自动持久化；实体歧义、不可用或其他 Agent-owned semantic selection 继续进入 bounded model turn。 / Seven-dimension review fixes deterministic Query selection bypassing an explicit semantic-selection context: zero-choice auto-persistence is allowed only when the node has no `selection_required` context; entity ambiguity, unavailable evidence, and other Agent-owned semantic selections continue through the bounded model turn.
- [eval] [test] 增加 available/unavailable 语义选择上下文均禁止自动 selection 的 no-motion 回归，保留普通冻结 Query 自动收敛、并发 selection、Action/Session 禁止重放与 evidence-lineage 回归。 / Add no-motion regressions proving both available and unavailable semantic-selection contexts block auto-selection, while retaining ordinary frozen-Query convergence, concurrent-selection, Action/Session no-replay, and evidence-lineage coverage.

### 审查发现与边界 / Review Finding and Boundary
- **Major：** `AgentLoopNodeExecutor` 在模型看到 `scene_bind_selection` 前执行 deterministic selection。若当前理解将冻结实体标为歧义或上下文 unavailable，schema 完整仍会触发 `scene.bind`；绑定 Query 虽不运动，却可产生错误稳定身份并污染后续 Action。现有 schema、Coordinator transaction 和 Query semantics 只验证形状、所有权与只读性质，不验证本轮语义歧义，因此不足。 / **Major:** `AgentLoopNodeExecutor` ran deterministic selection before the model could inspect `scene_bind_selection`. If current understanding marks frozen entities ambiguous or the context unavailable, a schema-complete node could still invoke `scene.bind`; the Query itself does not move, but an incorrect stable identity can contaminate later Actions. Existing schema, Coordinator transaction, and Query semantics validate shape, ownership, and read-only behavior, not current semantic ambiguity, so they are insufficient.
- 修复复用 `NodeExecutionContext` 已有 bounded selection projection，不增加 ToolSpec 字段、hash、baseline、全局 gate 或 RGB/颜色/对象/provider 分支；不改变 Runtime、Gateway 或 motion admission。 / The fix reuses the existing bounded selection projection on `NodeExecutionContext`; it adds no ToolSpec field, hash, baseline, global gate, or RGB/color/object/provider branch, and changes no Runtime, Gateway, or motion admission.

### 预期影响文件 / Planned Files
- `PhyAgentOS/agent/planning_loop.py`
- `tests/test_planning_loop.py`
- `docs/forge/FROZEN_QUERY_SELECTION_NO_PROGRESS_DIAGNOSIS_20261012.md`
- `changelog/2026-10_part6.md`
- `CHANGELOG.md`

### 实际修改与关键 Diff / Actual Changes and Key Diff
- [修改] `PhyAgentOS/agent/planning_loop.py:L153,L445-L458,L1041-L1048`：非持久化上下文标记 `agent_selection_required`；显式语义选择上下文交回模型，原始 execution/pending selection 仍先恢复。 / Add the non-persisted context flag `agent_selection_required`; explicit semantic choices return to the model while existing executions and pending selections still resume first.
- [修改] `tests/test_planning_loop.py:L664,L3287-L3288,L3457-L3499`：验证生产 context 设置标记、已持久化绑定优先恢复、available/unavailable 语义上下文均不触发 deterministic selection。 / Verify production-context flagging, precedence of persisted binding recovery, and rejection of deterministic selection for both available and unavailable semantic contexts.
- [修改] `docs/forge/FROZEN_QUERY_SELECTION_NO_PROGRESS_DIAGNOSIS_20261012.md:L99-L119,L142-L145,L176-L178`：记录语义选择 ownership 和接受前审查反例。 / Document semantic-selection ownership and the acceptance-review counterexample.
- **Minor（已修复 / fixed）：** v13.3.5 索引先前误写 Node executor 为 `L1017-L1036`，确定性恢复代码当前为 `L1041-L1060`；其新增 executor 回归当前为 `tests/test_planning_loop.py:L3395-L3614`，不是旧 `L3317-L3495`。历史归档保留原文，此处追加当前行号，并按规则用归档完整记录同步最近五版本。 / The earlier v13.3.5 index referenced outdated executor/test ranges; current deterministic recovery is `L1041-L1060` and its executor regressions are `tests/test_planning_loop.py:L3395-L3614`. Historical archive text remains intact; current locations are appended here and the latest five index entries are synchronized with full archive records.

```diff
 class NodeExecutionContext(BaseModel):
+    agent_selection_required: bool = False

+scene_bind_selection = _scene_bind_selection_context(...)
+agent_selection_required = scene_bind_selection is not None

 # Existing execution and pending selection resume first.
-if callable(persist_frozen_query):
+if callable(persist_frozen_query) and not context.agent_selection_required:
     selected = persist_frozen_query(context.task_id, context.node_id)
```

### 七维审查 / Seven-Dimension Review
1. **架构 / Architecture：** 上下文投影器声明语义决策 ownership，executor 只编排恢复顺序；复用 Coordinator admission，无第二执行通道。 / Context projection declares semantic-decision ownership; the executor only orders recovery, reusing Coordinator admission without a second execution path.
2. **正确性 / Correctness：** 修复 schema 完整被错误等同于“无语义决策”的 Major；现有 lineage 收窄规则保留，多显式来源不按时间戳猜选。 / Fix the Major that equated schema completeness with no semantic decision; lineage narrowing remains, and multiple explicit sources are never selected by timestamp.
3. **错误可观测 / Observability：** unavailable 和歧义事实继续进入模型上下文及 bounded no-progress；持久化失败无 durable winner 时仍抛出原始错误。 / Unavailability and ambiguity remain visible in model context and bounded no-progress handling; persistence failures without a durable winner still raise the original error.
4. **恢复幂等 / Recovery and idempotency：** execution/pending selection 优先；已接受 selection 不因上下文标志被丢弃，Action terminal/unknown 不重放。 / Executions and pending selections resume first; accepted selections survive the context flag, and terminal/unknown Actions are not replayed.
5. **机器人安全 / Robotics safety：** 语义身份选择不被只读属性绕过；frame/calibration/freshness 和 motion admission 均保持原有校验，无运动。 / Read-only semantics cannot bypass identity selection; frame, calibration, freshness, and motion admission retain existing validation, with no motion.
6. **扩展兼容 / Extension compatibility：** 通用 context 标志，默认 false 保持非语义 Query 兼容；不增加持久化 schema、ToolSpec 字段或任务分支。 / A generic context flag defaults to false for non-semantic Queries; no persisted schema, ToolSpec field, or task branch is added.
7. **AgentLoop 收敛 / AgentLoop convergence：** 零自由度 Query 自动 selection，语义选择走有界模型回合，已有 selection 直接恢复；不增加盲重试或无限等待。 / Zero-choice Queries auto-select, semantic choices use bounded model turns, and existing selections resume directly; no blind retry or infinite wait is introduced.
- 最终：1 Major、1 Minor 均修复，无 Blocker 或未修复 Major。 / Final: one Major and one Minor fixed, with no Blocker or unresolved Major.

### 验证与部署边界 / Validation and Deployment Boundary
- 聚焦 `177 passed in 5.39s`；扩展控制面 `217 passed in 5.48s`；全仓库 `897 passed in 32.83s`。 / Focused: `177 passed in 5.39s`; expanded control plane: `217 passed in 5.48s`; full repository: `897 passed in 32.83s`.
- 命令 / Command：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p pytest_asyncio.plugin`；Ruff、compileall、`git diff --check` 通过。 / Ruff, compileall, and `git diff --check` passed.
- 未新建或切换分支，未安装/重启 Runtime，未创建/恢复任务，未调用 live Query/Action、相机或 simulator；测试只使用本地 fixture，无物理运动。 / No branch creation/switch, Runtime install/restart, task create/resume, or live Query/Action, camera, or simulator call; tests use local fixtures only, with no physical motion.

### Git 提交 / Git Commit
- Implementation commit: `0205be6a` on `feature/planning-loop`; log/index reference completion follows. / 实现提交：`0205be6a`，分支 `feature/planning-loop`；日志与索引提交引用随后补全。

## v13.3.5 (2026-10-12 20:31) - codex

### 变更摘要 / Summary [完成]
- [policy] [fix] 修复通用 AgentLoop 在 Query 节点已具备完整、唯一、Coordinator 冻结输入时仍要求模型重复搬运参数，导致两次无 selection 回合后 `node_selection_no_progress`；仅为零自由度 Query 生成既有 `forge_plan_select` 持久化，不改变 Action/Session 或含 projection/source/语义选择的节点。 / Fix the generic AgentLoop path that still asks the model to repeat complete, unique Coordinator-frozen Query inputs, causing `node_selection_no_progress` after two selection-free turns; persist the existing `forge_plan_select` admission only for zero-choice Queries, without changing Action/Session or projection/source/semantic-choice nodes.
- [policy] [fix] 修复 Query continuation 中同一 scene revision 的多条历史 `scene.understand` 记录污染当前 `scene.bind` 选择上下文：优先使用当前节点 `required_evidence` 明确授权的理解记录，并仅在无显式 lineage 时回退到唯一候选；不按 RGB、颜色、方块、节点名或 provider 分支。 / Fix multiple historical `scene.understand` records from the same scene revision contaminating the current `scene.bind` selection context in Query continuations: prefer the understanding record explicitly authorized by the current node's `required_evidence`, and fall back to a unique candidate only when no explicit lineage exists; add no RGB, color, block, node-name, or provider branch.
- [eval] [test] 增加通用 frozen Query auto-selection、拒绝 Action/多候选/缺字段与 projection 节点的 no-motion 回归；验证不调用 Gateway、不创建 Action、不重放历史 Action。 / Add no-motion regressions for generic frozen-Query auto-selection and rejection of Action, multi-candidate, missing-field, and projection nodes; verify no Gateway call, Action creation, or historical Action replay.

### 具体失败场景与设计边界 / Concrete Failure Scenario and Boundary
- 当前 `current_scene_cube_bindings` 的 `input_bindings` 已完整包含 `observation_ref`、`scene_revision`、`calibration_ref`、`entity_refs`，但 active revision 没有 selection、execution record 或 rejection；模型两次未调用 `forge_plan_select`，随后 Core 正确 fail-closed 为 `node_selection_no_progress`。 / The current node already contains complete `observation_ref`, `scene_revision`, `calibration_ref`, and `entity_refs`, yet the active revision has no selection, execution record, or rejection; the model omitted `forge_plan_select` twice and Core correctly failed closed as `node_selection_no_progress`.
- 当前节点以 `required_evidence` 明确引用最新理解 `tool:tool_392197f7a589482e`，但 `_scene_bind_selection_context()` 同时纳入同场景历史理解 `tool_a1281b35cc7848f7`；“恰好一条候选”的旧判断因此把有效上下文误报为 `unavailable`，而节点提示又要求 unavailable 时不得提交 selection，形成确定性的 no-progress。 / The current node explicitly references the latest understanding `tool:tool_392197f7a589482e` through `required_evidence`, but `_scene_bind_selection_context()` also admitted the same-scene historical understanding `tool_a1281b35cc7848f7`; the old exactly-one-candidate check therefore misreported valid context as `unavailable`, while the node prompt prohibited selection in that state, deterministically causing no progress.
- 现有 ToolSpec、PlanGraph digest、Coordinator transaction 和 no-progress guard 无法把“没有剩余 Agent 决策”变成 durable selection；因此只在不可变 Query 输入已经满足唯一 ToolSpec 且无 projection/source/runtime semantic fields 时自动走同一 Coordinator admission。普通版本号、主键和测试不能替代该 selection，因为它们不产生可消费的 planning binding。 / Existing ToolSpec, PlanGraph digest, Coordinator transaction, and no-progress guard do not turn “no Agent decision remains” into a durable selection; therefore only an immutable Query input satisfying one unique ToolSpec with no projection/source/runtime semantic fields uses the same Coordinator admission. Versions, keys, and tests cannot replace this selection because they do not produce a consumable planning binding.
- 不新增 hash、baseline、全局 gate、RGB/颜色/对象/节点/provider 分支；Action/Session、多个候选、缺字段和任何 projection/source 仍必须由 Agent 选择并 fail-closed。 / Add no hash, baseline, global gate, RGB/color/object/node/provider branch; Action/Session, multiple candidates, missing fields, and any projection/source remain Agent-selected and fail-closed.

### 预期影响文件 / Planned Files
- `PhyAgentOS/agent/planning_loop.py`
- `PhyAgentOS/agent/planning_dispatch.py`
- `PhyAgentOS/agent/loop.py`
- `tests/test_planning_loop.py`
- `tests/test_planning_dispatch.py`
- `tests/test_planning_selection.py`
- `tests/test_action_selection_projection.py`
- `tests/test_multi_source_projection.py`
- `tests/test_plan_proposal_bindings.py`
- `docs/forge/FROZEN_QUERY_SELECTION_NO_PROGRESS_DIAGNOSIS_20261012.md`
- `CHANGELOG.md`

### 实际变更与七维审查 / Actual Changes and Seven-Dimension Review
- [修改] `PhyAgentOS/agent/planning_loop.py:L465-L527`：`_scene_bind_selection_context()` 先按当前 PlanNode 的 `required_evidence` 收窄理解记录；无显式 lineage 时保留唯一授权候选回退；多个显式来源仍返回 unavailable。 / [Modified] `PhyAgentOS/agent/planning_loop.py:L465-L527`: `_scene_bind_selection_context()` now narrows understanding records by the current PlanNode's `required_evidence`, retains the unique-authorized fallback only without explicit lineage, and keeps multiple explicit sources unavailable.
- [修改] `tests/test_planning_loop.py:L918-L1001`：新增历史同场景理解被当前显式 lineage 排除、多个显式来源 fail-closed，以及无理解记录兼容断言。 / [Modified] `tests/test_planning_loop.py:L918-L1001`: add regressions for excluding same-scene historical understanding, failing closed on multiple explicit sources, and preserving the no-understanding case.
- [修改] `docs/forge/FROZEN_QUERY_SELECTION_NO_PROGRESS_DIAGNOSIS_20261012.md:L42-L49,L74-L78,L113-L123,L160-L162`：补充 evidence-lineage 根因、选择规则和 no-motion 验证边界。 / [Modified] `docs/forge/FROZEN_QUERY_SELECTION_NO_PROGRESS_DIAGNOSIS_20261012.md:L42-L49,L74-L78,L113-L123,L160-L162`: document the evidence-lineage root cause, selection rules, and no-motion validation boundary.

### 七维审查结论 / Seven-Dimension Review
1. **架构 / Architecture**：修复位于现有 `NodeContextProvider` 证据投影边界，不新增状态机或执行通道。 / The fix stays at the existing `NodeContextProvider` evidence-projection boundary; no second state machine or execution path was added.
2. **正确性 / Correctness**：显式 `required_evidence` 优先；多条显式来源和跨场景记录均不被猜选。 / Explicit `required_evidence` wins; multiple explicit sources and cross-scene records are never guessed.
3. **错误可观测 / Observability**：保留 bounded `unavailable` reason；没有吞掉缺失、重复或 stale evidence。 / Bounded `unavailable` reasons remain observable; missing, duplicate, and stale evidence are not swallowed.
4. **恢复幂等 / Recovery and idempotency**：只影响只读上下文生成，不创建重复 selection，不重复 Query，不改变历史 Action settlement。 / The change only affects read-only context construction; it creates no duplicate selection or Query and does not alter historical Action settlements.
5. **机器人安全 / Robotics safety**：不改变 freshness、calibration、workspace、collision、IK、motion authorization 或 Action admission；全程 no-motion。 / Freshness, calibration, workspace, collision, IK, motion authorization, and Action admission are unchanged; validation is entirely no-motion.
6. **扩展兼容 / Extension compatibility**：仅依赖通用 evidence refs、PlanNode 和 scene revision；无 RGB、颜色、对象、provider 或节点名分支。 / The rule depends only on generic evidence refs, PlanNode, and scene revision; no RGB, color, object, provider, or node-name branch exists.
7. **AgentLoop 收敛 / AgentLoop convergence**：当前节点不再因历史同场景记录误报 unavailable；真正多源歧义仍交回 Agent 并 fail-closed。 / The current node no longer becomes falsely unavailable due to historical same-scene records; genuine multi-source ambiguity remains Agent-owned and fail-closed.

### 验证 / Validation
- 聚焦：`175 passed in 5.47s`。 / Focused: `175 passed in 5.47s`.
- 全仓库：`895 passed in 31.78s`。 / Full repository: `895 passed in 31.78s`.
- Ruff、compileall、`git diff --check`：通过。 / Ruff, compileall, and `git diff --check`: passed.
- 未启动或重启 Runtime，未创建任务，未调用 Gateway Query/Action，未读取相机，未推进 simulator，未执行运动。 / No Runtime start/restart, task creation, Gateway Query/Action, camera read, simulator step, or motion occurred.

### 关键 Diff / Key Diff
```diff
- all authorized same-scene scene.understand records -> len != 1 -> unavailable
+ current PlanNode required_evidence lineage -> exactly one explicit record
+ no explicit lineage -> existing unique-authorized fallback
+ multiple explicit records -> unavailable (fail-closed)
```

### Git 提交 / Git Commit
- Commit: `5f07b5e4` on `feature/planning-loop`; documentation/index completion follows separately. / 提交：`5f07b5e4`，分支 `feature/planning-loop`；日志与索引补全随后单独提交。

## v13.3.4 (2026-10-12 19:06) - codex

### 变更摘要 / Summary [完成]
- [env] [chore] 按用户授权强制停止当前 `pick-place-workflow` Runtime，刷新当前 checkout 的 editable Core，并使用既有 `robotwin-blocks-ranking-graspnet` profile/operator environment 启动新 Runtime，使 simulator 重新初始化场景。 / Under explicit user authorization, force-stop the current `pick-place-workflow` Runtime, refresh the editable Core from this checkout, and start a new Runtime with the existing profile/operator environment so the simulator initializes a fresh scene.
- [eval] [test] 仅核对停止/启动生命周期、Core 导入路径、Runtime/Dora/Gateway/Tool readiness、Qwen 服务和任务库非终态计数；不创建或恢复 AgentTask，不调用 Query/Action，不读取相机，不推进 simulator action，不执行运动。 / Validate only stop/start lifecycle, Core import path, Runtime/Dora/Gateway/Tool readiness, Qwen service, and non-terminal task counts; do not create or resume an AgentTask, invoke Query/Action, read cameras, advance simulator actions, or execute motion.

### 部署边界 / Deployment boundary
- 当前任务库只有 terminal 状态（`cancelled=201`、`failed=97`），因此重启不会恢复或重放历史 Action。 / The task store contains only terminal states, so restart cannot resume or replay a historical Action.
- 本轮修复同时涉及 editable Core 与 RobotWin Adapter 源码；启动前将核对现有 Skill/Node artifact 是否已包含 v13.3.3 Adapter handoff 代码。若 artifact 仍为旧版本，则先按既有发布流程构建新版本并更新锁，禁止仅刷新 Core 后误报部署完成。 / This repair touches both editable Core and RobotWin Adapter source; before startup, verify whether the installed Skill/Node artifact contains the v13.3.3 Adapter handoff. If it is stale, build a new version and update the existing release lock before declaring deployment complete.
- Runtime ready 只证明服务就绪；不通过 scene Query 推断具体方块状态。新 persistent simulator worker 的启动证据用于确认初始场景生命周期已重新创建。 / Runtime readiness proves service availability only; no scene Query is used to infer object state. A newly started persistent simulator worker is the evidence that the initial-scene lifecycle was recreated.

### 预期影响文件 / Planned files
- `changelog/2026-10_part6.md`
- `CHANGELOG.md`
- 如需发布 Adapter：`examples/forge-skills/pick-place-workflow/pyproject.toml`、`skill.yaml`、`CHANGELOG.md`、版本回归与 `out/releases/v13.3.4/`。 / If an Adapter release is required: the workflow package/manifest/changelog/version regression and local `out/releases/v13.3.4/` artifacts.

### 实际部署结果 / Completed deployment
- [env] [chore] 发现已安装 Node `1.0.10` 不含 v13.3.3 的 `_primary_attempted` handoff 代码，因此发布并安装 Skill `3.0.21` / Node `1.0.11`；没有用“仅刷新 Core”替代 Adapter 部署。 / The installed Node `1.0.10` did not contain the v13.3.3 `_primary_attempted` handoff, so Skill `3.0.21` / Node `1.0.11` were published and installed; an editable-Core refresh was not misreported as an Adapter deployment.
- [env] [chore] `.venv/bin/paos skill stop pick-place-workflow --force` 成功；停止后 Runtime=`stopped`、Dora=`down`、Gateway=`unavailable`、19020 端口释放，旧 host/simulator worker 退出；独立 Qwen PID `176466` / 8012 保持运行。 / The force-stop succeeded; Runtime stopped, Dora went down, Gateway became unavailable, port 19020 was released, and the old host/simulator worker exited; independent Qwen PID `176466` on port 8012 remained running.
- [env] [chore] `.venv/bin/python -m pip install --no-deps -e .` 成功，`PhyAgentOS` 与 `AgentTaskCoordinator` 从当前 checkout 导入且包含 `authorize_retryable_query_attempt`。 / The editable Core refresh succeeded; `PhyAgentOS` and `AgentTaskCoordinator` import from this checkout and expose `authorize_retryable_query_attempt`.
- [env] [chore] 安装并验证 Skill `3.0.21` / Node `1.0.11` 后，使用既有 operator env 启动 `robotwin-blocks-ranking-graspnet`；active runtime lock 为 `.../7f0c4086fe4d3241f0e75e4bb491c6df4255afb0cc534fdb3267d26a19539d6d/runtime-lock.json`。 / After installing and verifying Skill `3.0.21` / Node `1.0.11`, started the existing profile with the operator-owned environment; the active runtime lock is the recorded `7f0c...` lock.
- [eval] [test] Runtime/Dora=`running`、Gateway=`ready`、11/11 Tool contexts=`ready`；新 host PID `2244656` 和 simulator worker PID `2244784` 于 19:19 创建，worker 记录 `phase=startup elapsed_s=16.531`，证明 simulator lifecycle 已重新初始化而非继续旧进程。 / Runtime and Dora are running, Gateway ready, and all 11 Tool contexts ready; new host PID `2244656` and simulator-worker PID `2244784` were created at 19:19, with `phase=startup elapsed_s=16.531`, proving the simulator lifecycle was reinitialized rather than continuing the old process.
- [eval] [test] 运行中 embedded Adapter 已核对包含 `_primary_attempted` 与 `retryable=retryable`；重启验收时任务库仅有 `cancelled=201`、`failed=97`。随后用户会话 `cli:rgb-benchmark-injected-20261001-75` 创建 `task_491f46f4e8e34d7c` 并进入 executing，此任务不是部署流程创建或恢复。 / The running embedded Adapter contains `_primary_attempted` and `retryable=retryable`; at restart acceptance the task store contained only `cancelled=201` and `failed=97`. The user subsequently created executing task `task_491f46f4e8e34d7c` from session `...-75`; deployment did not create or resume it.
- [eval] [test] 用户任务执行 `scene.understand` 时 LocateAnything 首次 startup 用时 `72.382s`，同步 Gateway health probe 一度报告 unavailable；host/simulator 进程持续存活，enrichment 完成后 Runtime 和 11/11 Tool contexts 自动恢复 ready。 / During the user's `scene.understand`, LocateAnything cold startup took `72.382s`, causing a synchronous Gateway health probe to report temporary unavailability; host/simulator processes remained alive and Runtime plus all 11 Tool contexts returned ready after enrichment completed.

### 文件变更详情 / File changes
- [修改] `examples/forge-skills/pick-place-workflow/pyproject.toml:L1-L6`、`skill.yaml:L1-L4,L219-L229`：Skill `3.0.20` → `3.0.21`，Node `1.0.10` → `1.0.11`，Node SHA 更新为 `3d368ffb05dae5bf5ad7b27ea900702cfe7ea9318754c5199f2a4ed0d400af44`。 / Bump the Skill and Node versions and update the Node lock SHA.
- [修改] `examples/forge-skills/pick-place-workflow/CHANGELOG.md:L1-L11`、`tests/test_grasp_propose.py:L262-L274`：记录通用 handoff/retryability 发布并同步版本一致性回归。 / Record the generic handoff/retryability release and align version-consistency regression.
- [新增] `out/releases/v13.3.4/robotwin20_persistent_host-1.0.11-linux-x86_64.tar.gz`、`pick-place-workflow-3.0.21.tar.gz`：从当前 Adapter/Workflow 源码构建并安装。 / Build and install the Node and Skill artifacts from current Adapter/Workflow sources.
- [修改] `changelog/2026-10_part6.md:L1-L46`、`CHANGELOG.md:L3-L14`：记录部署边界、停止/安装/启动证据和 no-motion 验收。 / Record deployment boundaries, stop/install/start evidence, and no-motion acceptance.

### 关键 Diff / Key diff
```diff
- Skill 3.0.20 / Node 1.0.10 (missing v13.3.3 Adapter handoff)
+ Skill 3.0.21 / Node 1.0.11 (current Adapter handoff + retryability)
- old host/simulator process
+ new host/simulator startup -> initial-scene lifecycle recreated
```

### 验证与安全边界 / Validation and safety boundary
- release/provider suite：`131 passed in 0.95s`；Node SHA、Skill lock、安装 receipt、runtime lock 一致。 / Release/provider suite: `131 passed in 0.95s`; Node SHA matches the Skill lock, installation receipt, and runtime lock.
- 部署流程未创建/恢复 AgentTask，未调用 Gateway Query/Action，未读取相机，未推进 simulator action，未执行物理运动；用户随后独立启动的新任务不归入部署动作。readiness 不被当作具体场景内容证明。 / The deployment created/resumed no AgentTask, invoked no Gateway Query/Action, read no camera, and executed no simulator action or physical motion; the user's subsequently launched task is independent of deployment. Readiness is not treated as proof of specific scene contents.

### Git 提交 / Git commit
- Deployment/release commit: `4dc05f8b` on `feature/planning-loop`. / 部署与发布提交：`4dc05f8b`，分支 `feature/planning-loop`。
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
