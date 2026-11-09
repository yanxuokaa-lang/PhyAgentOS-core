# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

- [2026-11_part2](changelog/2026-11_part2.md)
- [2026-11](changelog/2026-11.md)
- [2026-10_part16](changelog/2026-10_part16.md)
- [2026-10_part15](changelog/2026-10_part15.md)
- [2026-10_part14](changelog/2026-10_part14.md)
- [2026-10_part13](changelog/2026-10_part13.md)
- [2026-10_part12](changelog/2026-10_part12.md)
- [2026-10_part11](changelog/2026-10_part11.md)
- [2026-10_part9](changelog/2026-10_part9.md)
- [2026-10_part10](changelog/2026-10_part10.md)
- [2026-10_part8](changelog/2026-10_part8.md)
- [2026-10_part7](changelog/2026-10_part7.md)
- [2026-10_part6](changelog/2026-10_part6.md)
- [2026-10_part5](changelog/2026-10_part5.md)
- [2026-10_part4](changelog/2026-10_part4.md)
- [2026-10_part3](changelog/2026-10_part3.md)
- [2026-10_part2](changelog/2026-10_part2.md)
- [2026-10_index_archive](changelog/2026-10_index_archive.md)
- [2026-10](changelog/2026-10.md)
- [2026-09_part9](changelog/2026-09_part9.md)
- [2026-09_part8](changelog/2026-09_part8.md)
- [2026-09_part7](changelog/2026-09_part7.md)
- [2026-09_part6](changelog/2026-09_part6.md)
- [2026-09_part5](changelog/2026-09_part5.md)
- [2026-09_part4](changelog/2026-09_part4.md)
- [2026-09_part3](changelog/2026-09_part3.md)
- [2026-09_part21](changelog/2026-09_part21.md)
- [2026-09_part20](changelog/2026-09_part20.md)
- [2026-09_part2](changelog/2026-09_part2.md)
- [2026-09_part19](changelog/2026-09_part19.md)
- [2026-09_part18](changelog/2026-09_part18.md)
- [2026-09_part17](changelog/2026-09_part17.md)
- [2026-09_part16](changelog/2026-09_part16.md)
- [2026-09_part15](changelog/2026-09_part15.md)
- [2026-09_part14](changelog/2026-09_part14.md)
- [2026-09_part13](changelog/2026-09_part13.md)
- [2026-09_part12](changelog/2026-09_part12.md)
- [2026-09_part11](changelog/2026-09_part11.md)
- [2026-09_part10](changelog/2026-09_part10.md)
- [2026-09](changelog/2026-09.md)

## 最近五版本 / Latest five versions

## v17.3.15 (2026-11-09 10:20) - codex

### 完成范围 / Completed Scope
- [env] [feat] Isaac acquire 路线搜索新增两项正向证据剪枝：`acquire_min_reorient_radius_m` 把姿态变化前的 raised/staging 航点径向推出基座折叠区；`_sample_terminal_arm_branches` 在路线搜索前对最终抓取位姿采样确定性 IK 分支，"有解且全部碰撞"才以 `grasp_terminal_arm_infeasible` 剪掉候选（零解不剪），碰撞自由分支反哺 pre-grasp IK warm start。 / Add two positive-evidence prunings to the Isaac acquire route search: `acquire_min_reorient_radius_m` pushes raised/staging waypoints radially out of the near-base wrist-fold region before orientation change; `_sample_terminal_arm_branches` samples deterministic IK branches at the final grasp pose before search and prunes only on positive evidence (solutions exist and all collide) as `grasp_terminal_arm_infeasible`, feeding collision-free branches back as pre-grasp IK warm starts.
- [env] [feat] `LabGraspTaskAffordanceProvider` 新增抓取漏斗统计（evaluated / geometry_qualified / gate_rejects / probe_rejects / qualified），持久化为 `grasp-affordance-funnel` artifact 并写入 diagnostics；新增离线回放脚本 `replay_task_affordance_funnel.py`。 / Add grasp funnel statistics to `LabGraspTaskAffordanceProvider` (evaluated / geometry_qualified / gate_rejects / probe_rejects / qualified), persisted as a `grasp-affordance-funnel` artifact with diagnostics, plus an offline replay script `replay_task_affordance_funnel.py`.
- [eval] [test] 新增/扩展 phase_motion 与 visual_perception 回归覆盖新配置、径向外推、terminal branch 剪枝与漏斗计数。 / Add/extend phase_motion and visual_perception regressions covering the new knobs, radial push-out, terminal-branch pruning and funnel counts.

### 文件变更详情 / File Changes
- [修改] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json`：新增 `acquire_min_reorient_radius_m: 0.5`、`acquire_probe_terminal_seed_count: 8`。 / Add `acquire_min_reorient_radius_m: 0.5` and `acquire_probe_terminal_seed_count: 8`.
- [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L259-L340, L424-L446, L470-L480, L1620-L1660：reorient 半径校验/外推、terminal IK 分支采样与正向证据剪枝、deterministic_ik_seeds。 / Reorient-radius validation/push-out, terminal IK branch sampling with positive-evidence pruning, and deterministic_ik_seeds.
- [修改] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py` L322-L510：gate/probe 拒绝按码计数并发布 funnel artifact。 / Count gate/probe rejects by code and publish the funnel artifact.
- [新增] `examples/forge-adapters/isaacsim_lab/scripts/replay_task_affordance_funnel.py`：离线回放历史 run 的漏斗直方图。 / Offline replay of historical run funnels.
- [修改] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py`（+131）、`tests/test_visual_perception.py`（+27）。 / Regression additions in both test files.

### 关键 Diff / Key Diff
```diff
before: every acquire variant enumerated through full corridor qualification
        (R05: 65/104 variants, 600s route_search_timeout)
after:  terminal pose IK branches sampled first; positive-evidence doomed
        variants pruned as grasp_terminal_arm_infeasible; reorientation
        moved to >=0.5m base radius; funnel counts persisted per run
unchanged: route qualification, safety checks, settlement and recovery
```

### 架构与验证 / Architecture and Validation
- 剪枝只发生在 Adapter 私有的运动几何层，且只凭正向证据（有解且全碰）剪枝；路线资格、接触窗口、settlement 与 v17.0.0 安全恢复不变。 / Pruning is Adapter-private motion geometry and positive-evidence only; route qualification, contact windows, settlement and v17.0.0 safe recovery are unchanged.
- 定向 pytest：`PYTHONPATH=... .venv/bin/python -m pytest examples/forge-adapters/isaacsim_lab/tests -q` -> `484 passed, 2 skipped`。 / Focused pytest over the full isaacsim_lab suite: `484 passed, 2 skipped`.
- 未运行仿真、PAOS task、Action 或运动。 / No simulation, PAOS task, Action or motion was run.

### Git 提交 / Git Commit
- Implementation commit: `64b97575`; branch: `feature/planning-loop`. / Implementation commit: `64b97575`; branch: `feature/planning-loop`.

## v17.3.14 (2026-11-08 18:15) - codex

### 完成范围 / Completed Scope
- [env] [feat] 新增 RoboTwin `StackRelationExecutionProvider`，将一条 Coordinator relation Action 组合为受当前 scene/assignment/candidate/approval 约束的 acquire -> place 阶段；成功要求区别于 acquire 的 scene revision、artifact evidence、有效 placement measurement、release、retreat、clear-of-target 和空夹爪。 / Add RoboTwin `StackRelationExecutionProvider` to compose one Coordinator relation Action into scene/assignment/candidate/approval-bound acquire -> place phases; success requires a scene revision distinct from acquire, artifact evidence, valid placement measurement, release, retreat, target clearance and empty gripper.
- [env] [fix] 取消后的 acquire、cancel/place handoff 竞态、worker poll exception、place start uncertain 与不完整/非有限 placement feedback 均保持 unknown，不伪报成功或遗漏取消；Host factory 使用同一个 persistent client/deployment 创建可替换 Provider。 / Keep cancelled acquire, cancellation/place-handoff races, worker-poll exceptions, uncertain place start and incomplete/non-finite placement feedback unknown; do not report success or lose cancellation. The Host factory constructs a replaceable Provider from the same persistent client/deployment.
- [eval] [test] 增加 Provider 与 Host integration 回归；Coordinator/AgentLoop/CapabilityRuntime 所有权和公共 Tool contract 不变。 / Add Provider and Host integration regressions; Coordinator/AgentLoop/CapabilityRuntime ownership and public Tool contracts remain unchanged.

### 文件变更详情 / File Changes
- [新增] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/stack_relation_execution.py` L1-L287：route/assignment/approval/scene 校验和持久 worker acquire/place 生命周期组合。 / Validate route/assignment/approval/scene and compose persistent-worker acquire/place lifecycle.
- [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py` L24, L393-L443, L931-L938；`examples/forge-adapters/robotwin20/tests/test_persistent_host.py` L576-L598：接入 Host provider factory，并验证 factory 收到 host-owned client/deployment。 / Add the Host Provider factory and verify it receives the host-owned client/deployment.
- [新增] `examples/forge-adapters/robotwin20/tests/test_stack_relation_execution.py` L1-L349：覆盖 route fail-closed、stale scene、acquire failure/cancel、cancel/place race、poll unknown、placement measurement/revision/evidence 和双阶段成功。 / Cover fail-closed routes, stale scenes, acquire failure/cancellation, cancel/place races, unknown polling, placement measurement/revision/evidence and successful two-phase composition.
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L528-L559；`changelog/2026-11_part2.md` L3-L55：保存实施诊断、精确差异和验证结果。 / Preserve implementation diagnosis, exact changes and validation results.

### 关键 Diff / Key Diff
```diff
before: no RoboTwin one-relation acquire/place Action composition
after:  current relation + qualified Adapter route -> acquire -> confirmed holding
        and fresh scene -> place -> measured placement/release/retreat/clearance
cancel/unknown/partial result: never inferred as success
still: no stack-specific route-preparation factory or controller qualification;
       motion_execution_supported remains false and task is not executable
```

```diff
- start place after an unlocked cancellation check
+ lock cancellation against acquire-to-place transition
- accept numeric placement residuals without finiteness checks
+ require finite non-negative residuals and a new scene revision
```

### 架构与验证 / Architecture and Validation
- 定向组合测试 `82 passed`；Ruff、compileall、scoped `git diff --check` 通过。 / Focused integration tests: `82 passed`; Ruff, compileall and scoped `git diff --check` pass.
- 未创建 PAOS task、未调用 Gateway Action、未启动 RoboTwin 仿真或运动。当前只证明 contract/Provider 行为，不证明实际 controller route/contact/stop。 / No PAOS task or Gateway Action was created or invoked, and no RoboTwin simulation or motion was started. Evidence proves only contract/Provider behavior, not actual controller route/contact/stop behavior.

### Git 提交 / Git Commit
- Implementation/diagnosis commit: `777cb547`; log-receipt commit: `f323c357`; branch: `feature/planning-loop`; both pushed successfully, verified 2026-11-08 18:34 Asia/Shanghai. / 实现与日志回执提交分别为 `777cb547`、`f323c357`；分支 `feature/planning-loop`；均已成功推送，2026-11-08 18:34 Asia/Shanghai 确认。

## v17.3.13 (2026-11-08 15:45) - codex

### 阶段结果 / Stage Result
- [docs] [diag] 更正 RoboTwin Provider 定位：relation Runtime 注入链已存在；stack 缺少从目标 Query 候选到 grasp/assignment/qualified route 及单个可取消、可测量关系 Action 的 Adapter 组合。 / Correct the RoboTwin Provider diagnosis: relation Runtime injection exists; stack lacks Adapter composition from target Query candidate through grasp/assignment/qualified route to one cancellable, measured relation Action.
- [policy] [diag] qualification artifacts 缺失，继续保持 `motion_execution_supported=False`；未添加代码或启动任务/Action/运动。 / Qualification artifacts are absent, so keep `motion_execution_supported=False`; no code or task/Action/motion was added or started.

### 文件变更详情 / File Changes
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L484-L526；`changelog/2026-11_part2.md` L3-L25：更正注册链结论并保存本次 Provider 输入/输出边界诊断。 / Correct the registration-path finding and preserve this Provider input/output boundary diagnosis.

### 关键 Diff / Key Diff
```diff
- missing: relation.establish Runtime injection
+ present: relation.establish injection and relation-target Query
+ missing: stack-specific qualified relation execution composition
```

### 验证 / Validation
- `git diff --check` passed; no execution tests run because implementation files remain unchanged. / `git diff --check` 通过；实现文件未改，因此未运行执行测试。

## v17.3.12 (2026-11-08 14:35) - codex

### 阶段结果 / Stage Result
- [env] [fix] 更正 Runtime inventory 误判，部署配置指向真实 `/home/data/yanxu_migrated/RoboTwin` checkout 与 `stack_blocks_three` 专用 profile；在 `/home/yanxu/robotwin20-runtime/stack-blocks-three/` 使用独立 artifact/assets 根，外置资产只通过明确链接接入。 / Correct the Runtime inventory error and point deployment at the real `/home/data/yanxu_migrated/RoboTwin` checkout and the task-specific `stack_blocks_three` profile; use isolated artifact/assets roots under `/home/yanxu/robotwin20-runtime/stack-blocks-three/` and explicitly link external assets.
- [env] [fix] preflight 现在计数受控资产 symlink 的实际文件；embodiment 路径接受 Runtime 根或明确的 `assets/embodiments` 资产根，仍拒绝任意逃逸；RTX 5060 Ti CuRobo extension 按 `sm_120` 重建。 / Count real files behind controlled asset symlinks; permit embodiment paths only under Runtime or the designated `assets/embodiments` root while rejecting arbitrary escapes; rebuild CuRobo extensions for RTX 5060 Ti `sm_120`.
- [env] [fix] 从真实 SAPIEN Entity 修复 table/block collision component 读取：优先 `get_components()`，保留 wrapper fallback。当前 no-motion Query 返回 tabletop 顶面 `z=0.7400000 m`、block target center `z=0.7650010 m`。 / Fix table/block collision-component access for real SAPIEN Entities by preferring `get_components()` while retaining the wrapper fallback. The live no-motion Query returns a tabletop height of `z=0.7400000 m` and block target center of `z=0.7650010 m`.
- [eval] [test] 增加贴合 SAPIEN Entity API 的 Adapter 回归；stack 的真实 no-motion setup/capture 和 preflight 通过。关系执行 Provider、route/contact qualification、stop behavior 尚未完成，故保持 `motion_execution_supported=False`，不创建 task 或调用 Action。 / Add Adapter regressions matching the SAPIEN Entity API; real stack no-motion setup/capture and preflight pass. Relation execution Provider, route/contact qualification and stop behavior remain unfinished, so `motion_execution_supported=False` and no task or Action is started.

### 文件变更详情 / File Changes
- [修改] `examples/forge-adapters/robotwin20/runtime/robotwin_backend.py` L77-L86、L320-L324：受控解析 Runtime 与外置 embodiment assets。 / Resolve Runtime and external embodiment assets through explicit allowed roots.
- [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/preflight.py` L157-L163、`tests/test_preflight.py`：跟随受控资产 symlink 统计实际资源。 / Count actual assets by following controlled asset symlinks.
- [修改] `examples/forge-adapters/robotwin20/runtime/robotwin_blocks_ranking_adapter.py` L585-L625、L628-L644：SAPIEN `get_components()` 兼容及 current table collision geometry Query。 / Support SAPIEN `get_components()` and current-table collision-geometry Query.
- [修改] `examples/forge-adapters/robotwin20/tests/test_robotwin_task_adapters.py` L22-L62、L147-L160：使用实体 API fixture，断言 block 尺寸和目标高度。 / Use Entity-API fixtures and assert block dimensions and target height.
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L401-L449：更正 artifact 根路径并记录实际 preflight/setup/Query 及 Provider 阻断。 / Correct the artifact-root path and record live preflight/setup/Query evidence and Provider blockers.
- [修改] `changelog/2026-11_part2.md` L644-L695：更新双语阶段结果、Diff、行号、验证和明确未完成的 Provider 项。 / Record bilingual stage results, diff, line references, validation and the explicitly unfinished Provider work.

### 关键 Diff / Key Diff
```diff
before: table.actor.components -> unavailable on real SAPIEN Entity
after:  Entity.get_components() -> inspect collision geometry -> available target
before: deployed Runtime/artifact paths did not resolve the intended task
after:  real task/profile + isolated artifact/assets roots + preflight ready
still:  no stoppable, route/contact-qualified relation Action Provider
```

### 架构与验证 / Architecture and Validation
- Coordinator 继续拥有 task/revision/settlement，AgentLoop 继续驱动工作流，CapabilityRuntime 拥有 Action invocation；Adapter 只拥有 RoboTwin geometry 与 future execution mechanism。未增加生命周期或 settlement store。 / Coordinator retains task/revision/settlement ownership, AgentLoop drives the workflow, CapabilityRuntime owns Action invocation, and the Adapter owns RoboTwin geometry and future execution mechanisms. No lifecycle or settlement store was added.
- 专用 preflight `ready=true`；no-motion `demo_clean` setup 与 RGB/depth/state capture 成功，实际 table Query 可用；`test_robotwin_task_adapters.py` `10 passed`，Ruff 与 `git diff --check` 通过。SAPIEN/OIDN 发出 CUDA-device warning 但 capture 返回 `sensor_available=true`。 / Dedicated preflight is `ready=true`; no-motion `demo_clean` setup and RGB/depth/state capture succeed, and the live table Query is available; `test_robotwin_task_adapters.py` reports `10 passed`, Ruff and `git diff --check` pass. SAPIEN/OIDN reports CUDA-device warnings, but capture returns `sensor_available=true`.
- 未调用 `play_once`、机械臂动作或 motion Action。同步整轨迹调用无法满足 Action cancellation/unknown-result 语义，缺少 stack route/contact 与 runtime-monitored approval；不能据此启用执行。 / No `play_once`, robot action or motion Action was invoked. Synchronous full-trajectory calls do not satisfy Action cancellation/unknown-result semantics, and stack route/contact plus runtime-monitored approval are absent; execution cannot be enabled on this evidence.

### Git 提交 / Git Commit
- Implementation: `0e469853`; receipt: `b91ea614`; branch: `feature/planning-loop`; push failed at 2026-11-08 14:46 Asia/Shanghai with GitHub TLS `GnuTLS recv error (-110)`. / Implementation: `0e469853`; receipt: `b91ea614`; branch: `feature/planning-loop`; push failed at 2026-11-08 14:46 Asia/Shanghai with GitHub TLS `GnuTLS recv error (-110)`.

## v17.3.11 (2026-11-08 12:49) - codex

### 完成范围 / Completed Scope
- [env] [diag] 确认配置的 Runtime/artifact roots 不存在，`RoboTwin20` 环境可导入 SAPIEN/Torch 但缺少 `robotwin`/Curobo；创建空目录不会提供 task class、资产或执行机制。 / Confirm configured Runtime/artifact roots are absent and `RoboTwin20` imports SAPIEN/Torch but lacks `robotwin`/Curobo; empty directories would not provide task classes, assets or execution mechanisms.
- [env] [diag] 官方 `RoboTwin-1.0` task inventory 是 `blocks_stack_easy`/`blocks_stack_hard`，没有 `stack_blocks_three`；不能通过直接安装官方 branch 修复当前 profile。 / Official `RoboTwin-1.0` task inventory has `blocks_stack_easy`/`blocks_stack_hard`, not `stack_blocks_three`; installing that branch alone cannot repair the current profile.
- [policy] [diag] 已有通用 Provider 注入路径，但没有基于确切 task/controller 接口实现并资格验证的 RoboTwin relation Provider、table geometry、route/contact 或执行反馈。保持 motion disabled；后续需提供定制 task source/revision，或明确接受改用官方 `blocks_stack_easy`。 / The generic Provider injection path exists, but no RoboTwin relation Provider based on exact task/controller interfaces has been implemented and qualified for table geometry, route/contact or execution feedback. Keep motion disabled; provide the custom task source/revision or explicitly accept official `blocks_stack_easy`.

### 文件变更详情 / File Changes
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L313-L356：保存 Runtime/dependency/task inventory 复核、benchmark 替换风险、PAOS Provider 缺口和继续条件。 / Record Runtime/dependency/task-inventory checks, benchmark-substitution risk, the PAOS Provider gap and continuation prerequisites.
- [修改] `changelog/2026-11_part2.md` L644-L674：追加本版本双语诊断、关键 Diff 和验证。 / Add this version's bilingual diagnosis, key diff and validation.
- [修改] `CHANGELOG.md` L52-L81：更新最近五版本。 / Update the latest-five versions.

### 关键 Diff / Key Diff
```diff
before: missing Runtime root/provider treated as generic provisioning gaps
after:  official RoboTwin-1.0 inventory does not contain stack_blocks_three;
        current environment also lacks robotwin and Curobo
decision: no empty roots, guessed task handles, silent benchmark substitution or motion enablement
```

### 架构与验证 / Architecture and Validation
- Coordinator/AgentLoop ownership unchanged; environment geometry, route/contact qualification and execution feedback remain Adapter/Provider responsibilities. No task, Action, simulator or motion was started. / Coordinator/AgentLoop ownership is unchanged; environment geometry, route/contact qualification and execution feedback remain Adapter/Provider responsibilities. No task, Action, simulator or motion was started.
- Read-only check: Runtime and artifact roots missing; `sapien=True`, `torch=True`, `robotwin=False`, `curobo=False`; official task-tree API lists `blocks_stack_easy.yml` and `blocks_stack_hard.yml`, not `stack_blocks_three`. No source behavior changed. / Read-only check: Runtime and artifact roots missing; `sapien=True`, `torch=True`, `robotwin=False`, `curobo=False`; official task-tree API lists `blocks_stack_easy.yml` and `blocks_stack_hard.yml`, not `stack_blocks_three`. No source behavior changed.

### Git 提交 / Git Commit
- Diagnosis commit: `3232614b`; receipt commit: `9d4ada95`; branch: `feature/planning-loop`; push stalled for 40 seconds and was interrupted, so both commits remain local (branch ahead 2). / Diagnosis commit: `3232614b`; receipt commit: `9d4ada95`; branch: `feature/planning-loop`; push stalled for 40 seconds and was interrupted, so both commits remain local (branch ahead 2).

## v17.3.9 (2026-11-08 15:10) - codex

### 完成范围 / Completed Scope
- [env] [fix] RoboTwin Persistent Runtime Bundle 现在将可选 `relation.establish` Provider 与 Coordinator context resolver 转发到通用 Runtime；未提供时维持原有工具集合，不注册 Action。 / Forward the optional `relation.establish` Provider and Coordinator context resolver to the generic Runtime; when omitted, preserve the existing tool set and do not register the Action.
- [eval] [test] 增加 no-motion Provider substitution 集成测试，验证 Provider/resolver 到达 endpoint，且不执行 Action admission。 / Add a no-motion Provider-substitution integration test proving the Provider/resolver reach the endpoint without Action admission.
- [docs] [diag] 记录 RoboTwin bundle 注入断层和本次边界；具体 stack Provider、table geometry、route/contact qualification 与 simulation evidence 仍缺失。 / Record the RoboTwin bundle injection gap and repair boundary; the concrete stack Provider, table geometry, route/contact qualification and simulation evidence remain absent.

### 文件变更详情 / File Changes
- [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_deployment.py` L169-L170, L195-L210：增加并转发可选 Provider/resolver。 / Add and forward optional Provider/resolver ports.
- [新增] `examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py` L317-L348：验证注入替换能力并避免调用 Action。 / Verify injected Provider substitution without Action invocation.
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L89-L108：保存本次失败场景、归属与残余阻断。 / Record the failure scenario, ownership and remaining blockers.
- [修改] `changelog/2026-11_part2.md` L605-L640：保存双语变更、精确行号、关键 Diff、测试与 Git 回执。 / Record bilingual changes, exact lines, key diff, tests and Git receipt.
- [修改] `CHANGELOG.md` L52-L70：加入 v17.3.9 并滚动最近五版本。 / Add v17.3.9 and roll the latest-five index.

### 关键 Diff / Key Diff
```diff
before: RoboTwin bundle -> generic Runtime without relation Action Provider/resolver
after:  RoboTwin bundle -> generic Runtime(relation_execution_provider,
        resolve_relation_context) -> registered relation.establish endpoint
still:  no concrete stack Provider or motion qualification; stack remains disabled
```

### 架构与验证 / Architecture and Validation
- 通用 Runtime/endpoint 保持 Provider-neutral，Coordinator/AgentLoop 生命周期不变；RoboTwin Adapter 仅传递可替换机制，不承担通用语义。 / Generic Runtime/endpoint remain Provider-neutral and Coordinator/AgentLoop lifecycle is unchanged; the RoboTwin Adapter only passes the replaceable mechanism, not generic semantics.
- 定向 pytest `22 passed, 1 warning`；Ruff 和 scoped `git diff --check` 通过。 / Focused pytest: `22 passed, 1 warning`; Ruff and scoped `git diff --check` pass.
- 未创建 task、未调用 Action、未启动仿真或机器人运动；stack 仍不可执行。 / No task or Action was started, and no simulation or robot motion occurred; stack remains non-executable.

### Git 提交 / Git Commit
- Implementation: `191478e8`; receipt: `24ae9691`; branch: `feature/planning-loop`; both pushes succeeded at 2026-11-08 15:28 Asia/Shanghai. / Implementation: `191478e8`; receipt: `24ae9691`; branch: `feature/planning-loop`; both pushes succeeded at 2026-11-08 15:28 Asia/Shanghai.

## v17.3.8 (2026-11-08 10:01) - codex

### 完成范围 / Completed Scope
- [policy] [feat] 新增可选 provider-neutral `relation.establish` Action Tool，经现有 CapabilityRuntime `ActionAdmission` deferred start 接入；Action 使用 Coordinator 绑定身份和实际 `relation.target` Query 结果重建候选 binding，只将几何与 lineage 传给 Provider。Provider 负责 support geometry、route/contact qualification、运动与执行反馈；AgentLoop/Coordinator 生命周期不变。 / Add an optional provider-neutral `relation.establish` Action Tool through the existing CapabilityRuntime `ActionAdmission` deferred-start path; rebuild the candidate binding from Coordinator-bound identity and the actual `relation.target` Query result, then pass only geometry and lineage to the Provider. The Provider owns support geometry, route/contact qualification, motion and execution feedback; AgentLoop/Coordinator lifecycle is unchanged. (local)
- [policy] [fix] relation plan node 写入校准引用；Action 静态 input binding keys 与 `PlanNode.input_bindings` 对齐，Query result 作为来源约束的动态前驱参数，当前 `on` relation 必须来自 `relation.target`。 / Include calibration reference in relation plan nodes; align static Action input-binding keys with `PlanNode.input_bindings`, keep the Query result as a source-constrained dynamic predecessor argument, and require `relation.target` provenance for current `on` relations. (local)
- [eval] [test] 测试覆盖 ToolSpec 投影/Agent 候选路由、Coordinator/Query lineage 拒绝、Provider substitution、显式 unavailable 和 provider exception 转 unknown；stack motion-disabled regression 保持通过。 / Tests cover ToolSpec projection/Agent candidate routing, Coordinator/Query-lineage rejection, Provider substitution, explicit unavailable and provider-exception-to-unknown; the stack motion-disabled regression remains passing. (local)

### 文件变更详情 / File Changes
- [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/agent_planning.py` L302-L401：将 `calibration_ref` 加入 relation planning inputs/PlanNode，保持 current-scene identity 完整。 / Add `calibration_ref` to relation planning inputs/PlanNode, preserving complete current-scene identity.
- [新增] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/relation_execution.py` L1-L194：定义 relation Provider port、ToolSpec、Coordinator-bound Action endpoint、deferred Runtime registration。 / Define the relation Provider port, ToolSpec, Coordinator-bound Action endpoint and deferred Runtime registration.
- [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/persistent_runtime.py` L33-L34, L664-L666, L762-L763, L860-L866：增加 Provider/resolver 成对注入和可选 Action 注册。 / Add paired Provider/resolver injection and optional Action registration.
- [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/__init__.py` L102-L112, L180-L186：导出关系 Action public contract。 / Export the relation Action public contract.
- [新增] `examples/forge-skills/pick-place-workflow/tests/test_relation_execution.py` L1-L182：覆盖 contract、deferred admission、substitution、stale lineage 和 unknown result。 / Cover the contract, deferred admission, substitution, stale lineage and unknown result.
- [修改] `examples/forge-skills/pick-place-workflow/tests/test_agent_planning.py` L1-L28, L294-L340：验证 `relation.establish` 被当前 relation PlanNode 选为 Tool candidate，且静态输入键完全匹配。 / Verify `relation.establish` is selected for the current relation PlanNode and its static input keys match exactly.
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L205-L261：保存架构职责、具体失败场景、机制理由和 contract/provider/simulation evidence 分层。 / Preserve architecture ownership, the concrete failure scenario, mechanism rationale and separate contract/provider/simulation evidence.
- [修改] `CHANGELOG.md` L52-L84：更新最近五版本摘要与完整变更详情。 / Update the latest-five summary and complete change details.
- [修改] `changelog/2026-11_part2.md` L572-L604：记录双语变更、行号、关键 Diff、验证与提交回执。 / Record bilingual changes, line references, key diff, validation and commit receipt.

### 关键 Diff / Key Diff
```diff
before: relation.establish had no Action endpoint; relation plan omitted calibration identity
after:  Agent PlanNode -> existing CapabilityRuntime ActionAdmission -> replaceable Provider
        relation Query result + selected candidate -> lineage-checked binding -> Provider
unknown Provider start/result -> outcome_unknown; never inferred as relation success
RoboTwin stack Provider/table geometry/route qualification remain absent; motion remains disabled
```

### 架构与验证 / Architecture and Validation
- Generic layer owns relation identity, current-node and Query lineage checks, candidate projection and Action handoff. Provider owns environment geometry, routes, contact checks, execution and feedback. Runtime owns invocation; Coordinator owns task/revision/settlement; AgentLoop remains the workflow driver. / Generic layer owns relation identity, current-node and Query-lineage checks, candidate projection and Action handoff. Provider owns environment geometry, routes, contact checks, execution and feedback. Runtime owns invocation; Coordinator owns task/revision/settlement; AgentLoop remains the workflow driver.
- 定向 pytest：`33 passed, 1 warning`；warning 为 pytest 环境不识别 `asyncio_mode`。Ruff 通过。邻接生命周期回归 `52 passed, 1 failed`，唯一失败是 `test_persistent_results_conform_to_published_live_schema[place-spec1]` 的 `returned_to_safe_pose` 输出字段与 schema 不一致，与本次 relation Action 修改无关。 / Focused pytest: `33 passed, 1 warning`; warning is the environment's unrecognized `asyncio_mode`. Ruff passes. Adjacent lifecycle regression: `52 passed, 1 failed`; the sole failure is `test_persistent_results_conform_to_published_live_schema[place-spec1]`, where the output's `returned_to_safe_pose` field does not match the schema; it is unrelated to this relation Action change.
- 未注册真实 stack Provider、未创建 PAOS task、未调用 Gateway Action、未启动 RoboTwin Runtime/仿真或运动；`stack_blocks_three` 仍不可执行。 / No concrete stack Provider was registered, no PAOS task was created, no Gateway Action was called, and no RoboTwin Runtime/simulation/motion was started; `stack_blocks_three` remains non-executable.

### Git 提交 / Git Commit
- Implementation commit: `0f5fb8c7`; log-receipt commit: `f86cf9e6`; branch: `feature/planning-loop`; `git push` succeeded at 2026-11-08 10:26 Asia/Shanghai. / Implementation commit: `0f5fb8c7`; log-receipt commit: `f86cf9e6`; branch: `feature/planning-loop`; `git push` succeeded at 2026-11-08 10:26 Asia/Shanghai.

## v17.3.1 (2026-11-06 17:13) - codex

### 回执补全 / Receipt Completion
- [chore] [docs] 记录 RoboTwin relation-target 实现提交 `d1a838884e546d2ae19e05a10909266794707df0`；向 `origin/feature/planning-loop` 的 HTTPS push 两次挂起且中断，远端回执未取得。 / Record the RoboTwin relation-target implementation commit `d1a838884e546d2ae19e05a10909266794707df0`; two HTTPS pushes to `origin/feature/planning-loop` stalled and were interrupted, so no remote receipt was obtained. (local)

### 文件变更 / File Changes
- `CHANGELOG.md` L52-L56、`changelog/2026-11_part2.md` L431-L466：更正实现 hash 并记录 push 状态。 / Correct the implementation hash and record push status.

### Git 提交 / Git Commit
- Implementation: `d1a838884e546d2ae19e05a10909266794707df0`; branch: `feature/planning-loop`; push pending. / Implementation: `d1a838884e546d2ae19e05a10909266794707df0`; branch: `feature/planning-loop`; push pending.

## v17.2.0 (2026-11-05 22:19) - codex

### 变更摘要 / Change Summary
- [policy] [feat] 新增关系目标 Agent 规划入口，按当前 observation/scene revision 编译单条义务，并要求前序结算证据；关系目标不投影为静态 `object.place`。 / Add relation-goal Agent planning that compiles one obligation per current observation/scene revision and requires predecessor settlement evidence; relation goals are not projected to static `object.place`. (local)
- [env] [feat] RoboTwin `stack_blocks_three` Adapter 只暴露关系目标和观测 actor 几何，不生成静态目标位姿；该任务被明确阻止进入 route/motion preparation。 / The RoboTwin `stack_blocks_three` Adapter exposes relation goals and observed actor geometry without static target poses; route/motion preparation is explicitly blocked for this task. (local)
- [eval] [test] 31 项 Agent planning、RoboTwin approval/Adapter 定向测试通过；Ruff 与 diff whitespace 检查通过。 / 31 focused Agent-planning and RoboTwin approval/Adapter tests pass; Ruff and diff whitespace checks pass. (local)

### 文件变更详情 / File Changes
- `agent_planning.py` L122-L197, L237-L299, L302-L420：关系目标模型及 fresh-scene 单段编译。 / Relation-goal model and fresh-scene segment compilation.
- `robotwin_blocks_ranking_adapter.py` L223-L339、`robotwin_persistent_engine.py` L226-L237, L285-L288, L370-L377, L428-L433, L468-L472：stack task facts、Adapter-derived actor identity 与拒绝运动路径。 / Stack task facts, Adapter-derived actor identity and motion-path refusal.
- `test_agent_planning.py` L308-L394、`test_robotwin_task_adapters.py` L1-L83、`test_persistent_action_approval.py` L267-L276, L327-L337, L418-L430：段规划、fake task 与 capability fixtures 回归。 / Segment-planning, fake-task and capability-fixture regressions.
- `.task/current.md` L1-L12、`changelog/2026-11_part2.md` L346-L388：状态、边界、验证和后续续段工作。 / Status, boundary, validation and continuation follow-up.

### 关键 Diff / Key Diff
```diff
+def compose_relation_goal_plan(..., scene_revision, observation_ref, available_evidence, ...):
+    # Compile one current-revision relation segment; require settled predecessors.
+    # Do not lower relation.establish to static object.place.
+motion_execution_supported = False  # stack_blocks_three
+if not self.task_adapter.motion_execution_supported:
+    raise ValueError("task adapter does not support motion route preparation")
```

### 架构与验证 / Architecture and Validation
- Coordinator/AgentLoop 尚无父任务续段生命周期入口；本次不宣称支持完整堆叠执行。下一步先实现结算后同父任务追加 revision、新 observation/evidence 接续，再接 relation Provider；期间 stack task 保持不可执行。 / Coordinator/AgentLoop lacks parent-task continuation lifecycle support; this change does not claim end-to-end stacking execution. Next, implement same-parent revision append after settlement with fresh observation/evidence, then connect a relation Provider; keep the stack task non-executable meanwhile.
- 未启动仿真、相机、Action 或运动。 / No simulator, camera, Action or motion was started.

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`。Implementation commit: `d967fd37`. / Implementation commit: `d967fd37`.

## v17.1.0 (2026-11-05 23:55) - codex

### 变更摘要 / Change Summary
- [policy] [refactor] 对规划、Isaac 组合层与 pick-place 执行链的 40 项过度防御发现逐项裁决并完成约 20 项低风险清理：集中 stale-scene readiness 谓词、合并三段完全同构的恢复分支、减少同步边界内重复解析与深拷贝、去除已由上游模型保证的结构重复校验，并保留碰撞、IK、运动、possession、scene freshness 与信任边界门禁。 / Adjudicate all 40 over-defense findings across planning, Isaac composition and the pick-place execution chain, applying about 20 low-risk cleanups while retaining collision, IK, motion, possession, scene-freshness and trust-boundary gates. (local)
- [policy] [fix] `prepare_held` 对期望参数做 JSON 往返归一化，修复 tuple/list 等价值误判；cycle/held Action 在同一同步 admission 流内复用已准入解析结果。 / Normalize expected `prepare_held` parameters through a JSON round trip to avoid tuple/list false positives; cycle and held Actions reuse admitted resolution in the same synchronous admission flow. (local)
- [docs] [docs] 五项拟删除内容被测试证明为承载行为后已回退，完整裁决与 deferred follow-up 保存于 `docs/reviews/overdefense-review-fullchain-20261105.md`。 / Revert five proposed removals after tests proved them load-bearing; preserve the full adjudication and deferred follow-ups in the review document. (local)

### 文件变更详情 / File Changes
- [修改 / Modified] `PhyAgentOS/agent/planning_dispatch.py` L42-L59, L193, L792；`PhyAgentOS/agent/planning_loop.py` L1345-L1372, L1493-L1495, L2081-L2084：集中 stale-scene predicate、合并重复 reconcile 并保留 load-bearing records 重读。 / Centralize the stale-scene predicate, collapse repeated reconciliation and retain the load-bearing records reread. (local)
- [修改 / Modified] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py` L432, L454, L472-L476, L499, L519, L534, L560, L716；`paos_client.py` L10, L234-L239, L303-L310, L326, L362：减少重复复制/能力探测并修复 held-route JSON 假阳性。 / Reduce repeated copies and capability probes and fix the held-route JSON false positive. (local)
- [修改 / Modified] `cycle_protocol.py` L163, L216；`held_manipulation.py` L439, L464-L466, L655-L663, L756-L759, L843-L845, L925-L931；`persistent_runtime.py` L416-L417；`subtask_executor.py` L339-L352, L465-L475, L639-L642, L865, L1133, L1177：清理重复 gap、解析、结构校验、possession/evidence 汇总。 / Remove duplicate gap, resolution, structural validation, possession and evidence aggregation work. (local)
- [修改 / Modified] `.task/current.md` L1-L24；`docs/reviews/overdefense-review-fullchain-20261105.md` L95-L132；`changelog/2026-11_part2.md` v17.1.0：保存完成状态、测试证据、回退依据和提交边界。 / Record completion state, test evidence, revert rationale and commit scope. (local)

### 关键 Diff / Key Diff
```diff
+def stale_scene_ready_nodes(graph, policies, settlements): ...
-if selected: resume(); else: resume()
+resume()
-if any(route.get(key) != value for key, value in arguments.items()):
+expected = json.loads(json.dumps(dict(arguments)))
-resolved = resolve_current()  # repeated at start
+resolved = deepcopy(admitted)
```

### 验证 / Validation
- [eval] [test] 聚焦模块 `410 passed, 6 failed`；完整 Core + Isaac Adapter + pick-place `2226 passed, 2 skipped, 16 failed`；全部失败节点均在独立 HEAD worktree 原样重现，本次新增失败为 0。 / Focused modules: `410 passed, 6 failed`; full Core + Isaac Adapter + pick-place: `2226 passed, 2 skipped, 16 failed`; every failure reproduces unchanged in an isolated HEAD worktree, so this cleanup adds zero failing tests. (local)
- [eval] [chore] Ruff、compileall 与定向 `git diff --check` 通过；未启动 Runtime、相机、仿真器或运动。 / Ruff, compileall and targeted `git diff --check` pass; no Runtime, camera, simulator or motion was started. (local)

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`。Implementation commit: `f2e98f0a`。 / Implementation commit: `f2e98f0a`. (local)

## v17.0.0 (2026-11-05 20:29) - codex

### 完成范围 / Completed Scope
- [env] [feat] Isaac Adapter 对配置允许的已知 acquire 失败执行有界恢复：先停止，确认物体仍受支撑、速度受限、无持有/接触载荷/双侧 manifold，再固定机械臂开爪并仅逆序执行本次已下发的合格关节命令回观察初始姿态；任一检查、碰撞、跟踪、取消或执行失败均返回 unknown/uncertain。 / For configured known acquire failures, the Isaac Adapter now performs bounded recovery: stop first, prove the object remains supported and slow with no hold/contact load/bilateral manifold, open the gripper at fixed arm joints, and reverse only the qualified joint commands actually issued in this attempt back to observation home; any check, collision, tracking, cancellation or execution failure returns unknown/uncertain. (local)
- [policy] [fix] Workflow 以 provider-neutral 的 `returned_to_safe_pose`、`observation_ready` 投影已知恢复终态；AgentLoop 只读取当前 revision、当前 node 的最新 Action 回执，在新 scene revision 上提供 fresh Query replan，不暴露 same-capture alternatives，也不复用旧 readiness、preparation、candidate set 或 opaque 引用。 / The workflow projects a known recovered terminal state through provider-neutral `returned_to_safe_pose` and `observation_ready`; AgentLoop reads only the latest Action receipt for the current revision/node and offers a fresh-Query replan on a new scene revision without exposing same-capture alternatives or reusing readiness, preparation, candidate sets or opaque references. (local)
- [env] [fix] 最终实现复核修复残留接触后置条件：恢复完成即使 `held=false`，只要 selected-body load 或 fresh bilateral manifold 仍存在，就保持 unknown/uncertain 并停止。 / Final implementation review fixes the residual-contact postcondition: even with `held=false`, recovery remains unknown/uncertain and stops whenever selected-body load or a fresh bilateral manifold still exists. (local)
- [docs] [diag] 保存 R03 抓取失败根因、PAOS 分层、证据新鲜度、停止条件、验收矩阵与最终复核结论。 / Save the R03 grasp-failure diagnosis, PAOS layering, evidence freshness, stop conditions, acceptance matrix and final review result. (local)

### 文件变更详情 / File Changes
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json` L19-L23；`examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py` L1046-L1053
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py` L295-L307, L813, L1977-L2131, L2164-L2168, L2296-L2307, L2361-L2429, L2453-L2526
- `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py` L1872-L2038
- `examples/forge-skills/pick-place-workflow/contracts/object.acquire.tool.yaml` L100-L120
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/object_acquire.py` L45-L66, L82-L108, L150-L171, L564-L581, L644-L668
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/persistent_runtime.py` L198-L207, L251-L288
- `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py` L526-L565, L843-L856, L1153-L1168
- `examples/forge-skills/pick-place-workflow/tests/test_object_acquire.py` L395-L447；`examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py` L687-L775
- `PhyAgentOS/agent/recovery_decisions.py` L166-L227, L302-L342, L477-L560；`tests/test_recovery_decisions.py` L352-L510
- `.task/labutopia-known-grasp-failure-recovery-20261105.md` L1-L130；`CHANGELOG.md` 最近五版本滚动更新

### 关键 Diff / Key Diff
```diff
+def _recover_failed_acquire(...):
+    if held or contact_load_valid or contact_manifold_valid or not supported:
+        raise PhaseMotionError("acquire_recovery_possession_uncertain", ...)
+    open_gripper_at_fixed_arm()
+    for point in reversed(executed_path):
+        collision_checked_command(point)
+    if held or contact_load_valid or contact_manifold_valid or not at_home:
+        raise PhaseMotionError("acquire_recovery_postcondition_failed", ...)

+returned_to_safe_pose: bool = False
+observation_ready: bool = False

+def _fresh_observation_recovery_record(...):
+    # latest Action receipt only; require new revision and complete safe facts
+    ...
```

### 架构审核 / Architecture Review
- 通用层仅持有恢复语义、scene revision 与证据生命周期；Isaac Adapter 私有持有关节、接触、USD/仿真实现和逆轨迹。Provider 可替换而不改变 AgentLoop 调用者。 / The generic layer owns only recovery semantics, scene revisions and evidence lifecycle; Isaac-private joints, contacts, USD/simulator mechanisms and reverse trajectories remain in the Adapter. Providers remain replaceable without changing AgentLoop callers.
- 不新增影子 scheduler、跨 revision 引用、硬编码候选编号、哈希或额外发布门禁；沿用既有 Coordinator/Runtime settlement 所有权与碰撞、关节、workspace、取消检查。 / No shadow scheduler, cross-revision reference, hard-coded candidate number, hash or extra release gate is added; existing Coordinator/Runtime settlement ownership and collision, joint, workspace and cancellation checks are reused.
- 最终 implementation review 无剩余 Blocker/Major；残余风险是尚未在真实 Isaac live motion 中验证恢复轨迹与新观测闭环。 / Final implementation review has no remaining Blocker or Major; the remaining risk is that the recovery trajectory and fresh-observation loop have not yet been validated in live Isaac motion.

### 验证 / Validation
- [eval] [test] 聚焦恢复回归 8 passed；Isaac Adapter + acquire/place/held/subtask/recovery 全量 625 passed、2 skipped（既有 native-USD skips）；AgentLoop/long-horizon 65 passed。 / Focused recovery regression passes 8 tests; the full Isaac Adapter plus acquire/place/held/subtask/recovery suite passes 625 with two pre-existing native-USD skips; AgentLoop/long-horizon passes 65. (local)
- [eval] [chore] Ruff、compileall、motion JSON parse 与 `git diff --check` 通过。pytest 使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -p pytest_asyncio.plugin` 隔离系统 ROS 插件。 / Ruff, compileall, motion JSON parsing and `git diff --check` pass. Pytest uses `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 -p pytest_asyncio.plugin` to isolate system ROS plugins. (local)
- [policy] [exp] 本轮未执行仿真或真实 live motion；下一次必须从 fresh reset、空夹爪、新 scene revision、新感知和新 preparation 开始。 / No simulated or real live motion ran in this change; the next execution must begin from a fresh reset, empty gripper, new scene revision, fresh perception and fresh preparation. (local)

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`.
- Implementation commit: `0d92159b976a5b004b67319f7d8b52a7f204ad2d`.

## v16.10.1 (2026-11-05 22:40) - claude

### 变更摘要 / Change Summary
- [sense] [fix] 修复抓取接近探测的检查范围错配:原 `check_final_gripper_pose` 只验证 palm/finger 几何,而路线资格化以全臂(link5)碰撞击杀候选——漏斗最后一道门验证的性质严格弱于路线要求。探测现对最终抓取位姿做**有界确定性多种子 IK 采样**(`acquire_probe_terminal_seed_count`,默认 8,校验 1–32;当前关节+关节中点+确定性偏移),逐分支运行不变的全臂碰撞检查。 / Fix the grasp-approach probe scope mismatch: `check_final_gripper_pose` validates palm/finger geometry only while the route qualifier kills candidates on whole-arm link5 collisions — the funnel's last gate verified a strictly weaker property than routes require. The probe now samples the final grasp pose with bounded deterministic IK seeds (`acquire_probe_terminal_seed_count`, default 8, validated 1–32; current joints, joint midpoint, deterministic offsets) and runs the unchanged whole-arm collision check per sampled branch. (local)
- [sense] [fix] 仅凭正向证据快速失败:当采样到 IK 解且**所有分支**碰撞时,变体以 `grasp_terminal_arm_infeasible` 拒绝(走廊枚举改变不了固定终点的死局);零解不剪枝;最后碰撞细节与诊断随错误下发,回执保留碰撞几何。幸存无碰分支反过来播种预抓 IK,替代原单一种子。 / Fail fast on positive evidence only: a variant is rejected with `grasp_terminal_arm_infeasible` when sampled IK solutions exist and every branch collides; zero solutions never prunes; the last collision detail and diagnostics ride on the error so receipts keep collision geometry. Surviving collision-free branches seed the pre-grasp IK, replacing the single current-joints warm start. (local)
- [sense] [fix] 顺序保持:终态采样惰性执行,仅在某个 distance 的 workspace 边界通过之后进行,`workspace_violation` 仍先于任何 IK,回执顺序保证不变。 / Ordering preserved: terminal sampling runs lazily only after a distance's workspace bound passes, so `workspace_violation` still precedes any IK and the receipt ordering guarantees are unchanged. (local)

### 预期修改 / Planned Files
- `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py`
- `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py`
- `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json`
- `.task/current.md`

### 关键 Diff / Key Diff
```diff
+def acquire_probe_terminal_seed_count(config): ...  # 1..32, default 8
+def deterministic_ik_seeds(seed_joints, limits, count): ...
+    def _sample_terminal_arm_branches(self, variant_desired, source, ...):
+        for warm in deterministic_ik_seeds(...):
+            joints, success = self.solver.compute_inverse_kinematics(..., warm_start=warm, ...)
+            self._collisions(joints, source, False, False, candidate_relation, False)
+                    if terminal is None:
+                        terminal = self._sample_terminal_arm_branches(...)
+                        if terminal["solution_count"] > 0 and terminal["collision_free_count"] == 0:
+                            raise PhaseMotionError("grasp_terminal_arm_infeasible", ...)
+warm_start=branch_seeds[0] if branch_seeds else seed_joints
```

### 验证 / Validation
- [eval] [test] phase-motion 154 passed(146+4 新:全分支碰撞拒绝且跳过短路线工作、零解不剪枝、分支播种预抓 IK、校验器拒绝);全量 Isaac Adapter + subtask executor 506 passed、2 skipped(既有 native-USD);Ruff、compileall 通过。 / Phase-motion passes 154 (146 plus four new: all-branches-collide rejection with skipped short-route work, zero-solution no-prune, branch-seeded pre-IK, validator rejection); the full suite passes 506 with two pre-existing native-USD skips; Ruff and compileall pass. (local)
- [policy] [exp] 预测(待 fresh run 验证):候选 178 的终态位姿在采样分支下将秒级判死,漏斗响应应诚实地给出零合格组合及具体原因,不再烧 600 秒走廊搜索。 / Prediction (pending fresh-run validation): candidate 178's terminal pose should be rejected in seconds under sampled branches, the funnel response should honestly surface zero qualified combinations with the concrete reason, and the 600 s corridor search should no longer burn. (local)

### Git 提交 / Git Commit
- Branch: `feature/planning-loop`.
- 尚未提交,等待用户审核。 / Not committed, pending user review. (local)
### v16.10.1 预测验证 / Prediction validated (2026-11-05 23:05)

- [eval] [exp] fresh 无运动跑 `out/lab-fullchain-truth-20261105-v16_10_1-no-motion-r1/`(task_7706c39bbe6a47eb)证实预测:漏斗 505→5→**0**,候选 56/60/178 的终态采样均为 solution_count=8、collision_free_count=0,以 `grasp_terminal_arm_infeasible` 秒级拒绝;100 死于终态夹爪碰撞,233 死于物理孔径极限。零路线搜索、零 600 秒燃烧,agent 回复列出全部门因。56/60 的历史单种子否决获正向证据确认。结论:当前夹具不存在任务合格抓取;孔径物理排除、几何门有谱系保留;剩余杠杆为夹具几何(垫高/外移试剂瓶,precedent:rod-storage patch),待用户批准。 / A fresh no-motion run confirms the prediction: funnel 505→5→0 with candidates 56/60/178 each sampled at 8 solutions and 0 collision-free branches, rejected `grasp_terminal_arm_infeasible` in seconds; 100 dies at final-gripper collision and 233 at the physical aperture limit. Zero route search, zero 600-second burn, and the agent response lists every gate reason. The historical single-seed rejections of 56/60 are confirmed with positive evidence. Consequence: no task-qualified grasp exists on this fixture; aperture widening is physically excluded, the gate set stands on lineage, and the remaining lever is fixture geometry (raise or relocate the reagent bottles), pending user approval. (local)
