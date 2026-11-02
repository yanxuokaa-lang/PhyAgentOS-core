# Changelog

## 维护规则 / Maintenance Rules

修改前记录计划；完成后补充双语说明、行号、Diff、验证与 Git 信息。 / Log the plan, then record bilingual changes, lines, diffs, validation and Git information.

## Archive

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

## v16.5.0 (2026-11-01 22:18) - codex

### 预期修改 / Planned Changes [完成 / Completed; runtime remains blocked]
- [sense] [feat] 在 Isaac Adapter 私有 Task-Affordance Provider 中接入同一捕获、同一场景修订的无动作 grasp approach 可行性探针，只保留至少一个最终抓取方向与短接近段通过 Franka IK、连续性、workspace、自碰撞及环境碰撞检查的 opaque grasp 引用；不向 AgentLoop 暴露关节、USD 路径或碰撞细节。 / Add a same-capture, same-scene-revision no-motion grasp-approach feasibility probe behind the Isaac task-affordance Provider, retaining only opaque grasp refs with at least one final orientation and short approach that passes Franka IK, continuity, workspace, self-collision, and environment-collision checks without exposing joints, USD paths, or collision details to AgentLoop. (local)
- [env] [feat] 在 Engine/Worker/PhaseMotion Adapter 边界增加只读 feasibility RPC 与 Adapter 私有证据，复用最终组合场景、观测到执行体绑定、抓取对称变体和现有安全检查；探针不得发出控制器命令、改变世界或替代完整 Action preparation。 / Add a read-only feasibility RPC and Adapter-private evidence across the Engine/Worker/PhaseMotion boundary, reusing the final composed scene, observation-to-body binding, grasp-symmetry variants, and existing safety checks; the probe must issue no controller command, change no world state, and never replace full Action preparation. (local)
- [policy] [fix] Task-Affordance Preparation 仅返回 Query 中已通过 feasibility 的同工艺特征 opaque refs，并在场景修订、捕获、候选集合或 feasibility 证据缺失/过期/歧义时 fail closed；现有 Action preparation 继续只遍历该有序集合。 / Make task-affordance Preparation return only same-process-feature opaque refs that passed feasibility in the Query, failing closed on stale/missing/ambiguous scene, capture, candidate-set, or feasibility evidence while the existing Action preparation continues to traverse only that ordered set. (local)
- [test] [test] 先覆盖替代 Provider 不依赖 Isaac 私有字段、一个候选可行、全部候选不可达、stale capture/revision、无效探针结果、对称方向选择、零动作与 Action 不重新引入被排除候选；随后运行定向和完整回归及一次不带 `--execute` 的全链路 Agent 验证。 / Cover provider substitution without Isaac-private fields, one feasible candidate, all candidates unreachable, stale capture/revision, invalid probe results, symmetry-orientation selection, zero motion, and prevention of Action reintroducing rejected candidates; then run focused/full regression and one full-chain Agent validation without `--execute`. (local)
- [docs] [docs] 保存本轮主因诊断、PAOS 所有权/替换边界、证据链与新鲜度边界、findings-first 实现复核、验证命令及 no-motion 运行回执；只有完整 R03 acquire preparation 通过后才允许后续模拟执行。 / Save the root-cause diagnosis, PAOS ownership/substitution boundary, evidence lineage and freshness boundary, findings-first implementation review, validation commands, and no-motion receipt; permit later simulated execution only after complete R03 acquire preparation succeeds. (local)

### 架构与安全边界 / Architecture and Safety Boundary
- 通用层继续只拥有 task semantics、opaque refs、生命周期、恢复与 settlement；机器人 IK、关节种子、短接近采样、USD/PhysX 查询及失败细节由 Isaac Adapter 独占。 / The generic layer continues to own task semantics, opaque refs, lifecycle, recovery, and settlement; robot IK, joint seeds, short-approach sampling, USD/PhysX queries, and failure details remain exclusively owned by the Isaac Adapter.
- feasibility 是 Query/Preparation 的只读证据，不是第二个调度器、路线存储或成功 settlement；完整路线仍由 `manipulation.prepare` 重新验证。 / Feasibility is read-only Query/Preparation evidence, not a second scheduler, route store, or success settlement; `manipulation.prepare` still revalidates the complete route.
- 不新增 hash、冻结 contract 或额外发布 gate，不降低 workspace、IK 连续性、关节限位、自碰撞、环境碰撞、payload collision 或 possession 门禁。 / Add no hashes, frozen contracts, or release gates, and weaken none of the workspace, IK-continuity, joint-limit, self-collision, environment-collision, payload-collision, or possession gates.

### 续作计划 / Continuation Plan (2026-11-02) [完成 / Completed]
- [docs] [fix] 保存 r3 的真实拒绝诊断：R03 候选 15/16/23 的 world grasp z≈0.750917 m、approach z≈0.634282，后退 0.12/0.18 m 后 pre-grasp z≈0.674803/0.636746 m，小于既有 workspace z_min=0.7 m；该结论只证明现有候选/接近距离不合格，不证明物体不能抓取。 / Save the measured r3 rejection: the three qualified grasps backtrack below the existing workspace floor; this rejects the present approaches, not all possible grasps of the object. (local)
- [env] [fix] 补齐 feasibility artifact 的 capture identity、失败变体及工作空间坐标证据，保留 worker 拒绝的原始原因；验证探针与完整 preparation 的几何一致性，不修改安全阈值。 / Complete feasibility artifact capture identity and variant/workspace diagnostics, preserve worker rejection causes, and test geometric agreement with full preparation without changing safety thresholds. (local)
- [sense] [fix] 审查并修复探针替代实现、过期/错误 identity、缺失证据和 Provider 异常的失败路径；真实不可达与基础设施异常必须可区分。 / Review and repair substitution, stale/wrong identity, missing evidence, and provider-error paths; distinguish geometric infeasibility from infrastructure failure. (local)
- [eval] [chore] 运行定向/完整回归及新的无动作正式入口验证，保存诊断与实现复核，补齐当前任务、双语行号/Diff 和最近五版本后提交并推送当前分支；不纳入无关未提交文件。 / Run focused/full regressions and a fresh formal no-motion validation, save diagnosis/review, update task and bilingual line/diff records and latest five entries, then commit and push the current branch without unrelated changes. (local)

### 实际文件变更 / Actual File Changes
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/agent_host.py:L123-L125` 注入只读 feasibility 回调；继续使用原 Task-Affordance Query/Preparation 与 AgentLoop。 / Inject the read-only feasibility callback into the existing Task-Affordance and AgentLoop path. (local)
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/engine.py:L504-L526,L631-L663,L730-L749` 新增 Adapter backend 分发、同一 worker RPC 与失败身份保留；未增加 Core Tool 或 Action。 / Add Adapter/backend dispatch, same-worker RPC and failure identity preservation without a Core Tool or Action. (local)
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L1014-L1046,L1129-L1311` 允许显式虚拟 IK 种子并用 FK 验证一致性；生成几何轴对称短接近候选并复用既有 qualification；保存逐候选坐标、世界边界、capture identity 与失败原因。 / Support explicit hypothetical IK seeds with FK agreement, qualify geometry-equivalent short approaches through existing checks, and persist coordinates, world bounds, capture identity and causes. (local)
- [sense] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py:L9,L239-L240,L267-L269,L355-L459,L473,L538-L551,L1295-L1375` 组合过滤只保留可行 opaque grasp refs；复核回执并保存 Provider 异常/缺失证据诊断；解析私有执行 target 不扩大公共契约。 / Retain only feasible opaque grasp refs, revalidate receipts, record provider/missing-evidence errors and resolve private execution targets without widening public contracts. (local)
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/worker.py:L116-L151`、`examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/worker_session.py:L61-L62` 接入串行只读 RPC，拒绝缺失/过期场景，保持原 request identity 且不推进 revision。 / Wire a serialized read-only RPC, reject missing/stale scenes, preserve request identity and leave revision unchanged. (local)
- [eval] [chore] `examples/forge-adapters/isaacsim_lab/tests/test_engine.py:L1128-L1172`、`tests/test_phase_motion.py:L612-L820`、`tests/test_visual_perception.py:L1039-L1295`、`tests/test_worker_session.py:L7-L8,L65-L78,L151-L176,L193-L213`（后三者同属该 Adapter）覆盖替代回调、混合候选过滤、实际短路线 qualifier、workspace 复现、stale/invalid/missing/error 及零调用拒绝。 / Cover replacement callbacks, mixed-candidate filtering, the real short-route qualifier, recorded workspace rejection, stale/invalid/missing/error outcomes and zero-dispatch rejection. (local)
- [docs] [docs] `.task/current.md:L25-L26,L40-L76`、`.task/labutopia-r03-approach-feasibility-diagnosis-20261102.md:L1-L130`、`docs/forge/IMPLEMENTATION_REVIEW_V16_5_0.md:L1-L79` 保存继续任务、定量诊断及 PAOS 分层复核；诊断 L81-L130 包含验证命令和新的终态回执。 / Save the current task, quantitative diagnosis and PAOS ownership review; diagnosis lines 81–130 include validation commands and the fresh terminal receipt. (local)

### 关键代码 Diff / Key Code Diff

```diff
- grasp_task_affordance_provider=LabGraspTaskAffordanceProvider(visual)
+ grasp_task_affordance_provider=LabGraspTaskAffordanceProvider(
+     visual, approach_feasibility=visual.qualify_grasp_approach
+ )

- def qualify(self, waypoints, source, tcp_from_object, operation, supported_pose=None, tool_frame=None):
-     joints = self.joints()
+ def qualify(self, waypoints, source, tcp_from_object, operation, supported_pose=None,
+             tool_frame=None, *, initial_joints=None, initial_pose=None):
+     joints = self.joints() if initial_joints is None else np.asarray(initial_joints, dtype=float).copy()
+     # A supplied initial_pose must agree with FK before route qualification.

- # Body/process-compatible grasps immediately enter the task-affordance set.
+ # Same-capture private probe checks pre-grasp and grasp/close first.
+ # Only candidates with available, no-motion evidence enter the set.
+ # Full Action preparation still qualifies the entire route from live joints.

- raise PhaseMotionError("workspace_violation", "pre-grasp TCP is outside workspace")
+ raise PhaseMotionError("workspace_violation",
+     f"pre-grasp TCP={pre[:3, 3].tolist()} outside world workspace "
+     f"min={self.config['workspace_min_m']}, max={self.config['workspace_max_m']}")
```

### 验证 / Validation
- 完整 Isaac Adapter + subtask executor 回归 `370 passed`；定向 phase/visual/worker 回归 `185 passed`；混合候选及无效 artifact ref 测试补强后 visual 回归 `67 passed`。 / Full Isaac Adapter plus subtask-executor regression passed 370; focused phase/visual/worker passed 185; strengthened mixed-candidate and invalid-artifact visual tests passed 67. (local)
- 十个代码/测试文件 Ruff、compileall 与 `git diff --check` 通过；没有禁用 async 插件或把未运行测试计为通过。 / Ruff on ten code/test files, compileall and diff checks passed; asynchronous tests were not disabled or reported as passed without running. (local)
- 初次新增 worker 参数化测试漏导入 pytest，收集失败后已补齐并重新通过；该失败不作为运行能力证据。 / An initial parametrized worker test missed its pytest import; collection was fixed and rerun successfully, with no runtime claim inferred. (local)

### 运行边界 / Runtime Boundary
- 2026-11-01 r3 已证明三个合格几何 grasp 的 24 个接近变体都越过 workspace 下界；该结论只覆盖当前候选和既有 approach 配置。 / The November 1 r3 artifacts prove all 24 short-approach variants violate the existing lower workspace bound; this covers only current candidates/configuration. (local)
- 2026-11-02 r1 在会话中断前写出相机、state 和 understanding，但进程已结束且没有 acceptance.json；标记为中断，不能作为最终资格化结果。 / November 2 r1 wrote camera/state/understanding artifacts before interruption; its process ended without acceptance.json, so it is incomplete rather than qualification evidence. (local)
- 2026-11-02 r2 使用相同正式 `python -m isaacsim_lab.agent_host` 入口和原提示词重跑，不传 `--execute`；task `task_51ae038c97d246fd`、session `cli:lab-5fe426934fb3` 最终 cancelled。R03 工艺 Query/preparation 通过；task-affordance 的三个 grasp 共 24 个变体全部 workspace rejection，未进入 IK/Action。 / November 2 r2 used the same formal Agent Host entry/instruction without `--execute`; the recorded task/session ended cancelled after process-feature preparation passed and all 24 grasp approaches failed workspace checks before IK/Action. (local)
- 新 artifact 包含完整 capture identity、world grasp/pre-grasp、approach 和 workspace 边界，复现 z=0.674803/0.636746 m；`acceptance.json` 记录 `simulated_motion_enabled=false`、`controller_outcomes=[]`；R04/GLASS_ROD 未执行。 / Fresh artifacts reproduce the measured low pre-grasp heights with full identity/geometry; acceptance confirms disabled motion, empty controller outcomes and no downstream execution. (local)
- 本次完成资格化前移和诊断修复；当前抓取方向/接近距离仍不可行，未宣称全链路倾倒/搅拌成功。 / Early qualification and diagnostic fixes are complete; current grasp directions/backoffs remain infeasible, with no full manipulation success claimed. (local)

### 实现复核 / Implementation Review
- [docs] [docs] 修复完整路线前缺失 embodiment 接近资格检查、artifact 身份/坐标不足、Provider 异常被泛化、测试完全桩替短路线等四项 Major；当前实现无剩余已识别 Blocker/Major。 / Resolve four Major findings in early embodiment qualification, artifact identity/coordinates, provider-error differentiation and real short-route test coverage; no identified implementation Blocker/Major remains. (local)
- [docs] [docs] `CHANGELOG.md` 最近五条恢复为与月度归档一致的完整记录；保留所有历史月度版本，不纳入无关报告修改或运行大文件。 / Restore the latest five full entries in CHANGELOG to match the monthly archive, preserve historical entries and exclude unrelated edits/large run artifacts. (local)

### Git 提交 / Git Commit
- Implementation commit: `8f3fa34e`.
- Branch: `feature/planning-loop`.
- Date: `2026-11-02` (Asia/Shanghai).
- Receipt: this log-only follow-up records the implementation commit and corrects the task-file line references; the rolling index contains the same complete entry. / 本次纯日志跟进回填实现提交并校正任务文件行号，滚动索引保留同一完整记录。
- Push command: `git push origin feature/planning-loop` (current branch; no branch switch). / 推送当前分支，不切换分支。

## v16.4.0 (2026-11-01 20:57) - codex

### 变更摘要 / Summary [完成 / Completed; no motion]
- [env] [feat] 在 Isaac Adapter 内将 acquire 路线搜索从单一固定 XY 的 `staging_reorient -> approach` 扩展为配置驱动的 staging 高度、沿 approach 的额外后退距离与切向偏移候选；候选继续使用原始 task-affordance opaque grasp 引用，不修改 AgentLoop 或共享 Tool contract。 / Extend Isaac Adapter acquire route search from one fixed-XY staging/approach corridor to configuration-driven staging heights, additional approach backoffs, and tangential offsets while preserving the original task-affordance opaque grasp refs and leaving AgentLoop/shared Tool contracts unchanged. (local)
- [env] [fix] 对每个新路线候选继续执行 workspace、完整姿态 IK、`0.5 rad` 连续性、关节限位、自碰撞、环境碰撞、payload collision 与 possession 门禁；不放宽阈值，不将失败转换为成功。 / Run every new route candidate through the unchanged workspace, full-pose IK, `0.5 rad` continuity, joint-limit, self/environment collision, payload-collision, and possession gates without weakening thresholds or converting failures to success. (local)
- [env] [refactor] 将 staging/approach 候选的配置解析、几何构造与确定性排序提取为 Adapter 私有帮助函数，避免在 `prepare` 中继续扩张嵌套且便于替换测试。 / Extract Adapter-private configuration parsing, geometry construction, and deterministic ordering helpers for staging/approach candidates instead of expanding nested preparation logic. (local)
- [test] [test] 增加配置拒绝、几何候选生成、切向偏移、额外后退、完整安全资格化、确定性排序及全部路线失败保持零动作的测试；先运行离线单元测试和 no-motion preparation，只有至少一条完整 R03 路线通过后才允许再次 `--execute`。 / Add tests for invalid configuration, geometric candidate generation, tangential offsets, extra backoff, complete safety qualification, deterministic ordering, and zero-motion all-route failure; run offline tests and no-motion preparation before any new `--execute`. (local)
- [docs] [docs] 保存主因诊断、PAOS 所有权/替换边界、证据新鲜度、失败优先路径和验证命令，并更新当前任务与最近五版本。 / Save the root-cause diagnosis, PAOS ownership/substitution boundary, evidence freshness, failure-first paths, and validation commands, then update the current task and latest-five index. (local)

### 架构与安全边界 / Architecture and Safety Boundary
- 通用层继续只拥有任务语义、opaque 引用、生命周期、恢复与 settlement；staging/approach 几何、IK 种子、关节与碰撞全部留在 Isaac Adapter。 / The generic layer continues to own only task semantics, opaque refs, lifecycle, recovery, and settlement; staging/approach geometry, IK seeds, joints, and collision remain inside the Isaac Adapter.
- 新候选由最终 grasp pose、approach 向量和配置生成，不读取 R03/R04 标签或硬编码物体坐标。 / New candidates derive from the final grasp pose, approach vector, and Adapter configuration without reading R03/R04 labels or hard-coding object coordinates.
- 本轮先完成 no-motion qualification；未经完整 preparation 通过，不启动控制器。 / This iteration completes no-motion qualification first and does not start the controller until full preparation passes.

### 实际实现 / Implementation
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L242-L374,L617-L620,L921-L974` 新增 Adapter 私有 corridor 配置验证、基于最终 grasp/approach 的 pre-grasp 与 staging 几何、确定性路线选择，以及有界失败聚合；旧 profile 缺少新字段时回退到原单 corridor。 / Add Adapter-private corridor validation, final-grasp/approach-derived pre-grasp and staging geometry, deterministic route selection, and bounded failure aggregation with legacy single-corridor fallback. (local)
- [env] [tune] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json:L13-L34` 配置 4 个有界候选：旧 `0.12 m` approach、`0.18 m` approach + `0.08 m` backoff，以及 `-0.06/0/+0.06 m` 水平切向偏移。 / Configure four bounded candidates covering the legacy approach plus longer approach/backoff and signed horizontal tangential offsets. (local)
- [test] [test] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py:L10-L22,L176-L517` 覆盖旧配置回退、去重、非法数值、水平/垂直 approach、逐 corridor 完整 qualification、确定性选择、全部失败零动作及 96 路线错误摘要上限。 / Cover legacy fallback, deduplication, invalid values, horizontal/vertical approaches, complete per-corridor qualification, deterministic selection, zero-motion all-route failure, and bounded 96-route diagnostics. (local)
- [docs] [docs] `.task/labutopia-r03-staging-corridor-diagnosis-20261101.md:L1-L76`、`.task/current.md:L1-L71`、`docs/forge/IMPLEMENTATION_REVIEW_V16_4_0.md:L1-L42` 保存运行诊断、当前阻塞、findings-first 复核和下一条证据驱动路线。 / Save runtime diagnosis, current blocker, findings-first review, and the next evidence-driven route. (local)

### 关键代码 Diff / Key Code Diff
```diff
- acquire preparation uses one fixed pre-grasp XY corridor
- every failed route is appended as a full exception string
+ acquire preparation enumerates configured approach/backoff/tangential corridors
+ every corridor still passes the unchanged qualify() safety path
+ failure output aggregates code/phase/corridor/clearance/transport counts with bounded examples
```

### 验证 / Validation
- 定向回归：`151 passed`（`test_phase_motion.py`、`test_paos_integration.py`、`test_subtask_executor.py`）。 / Focused regression: `151 passed`.
- 完整回归：`346 passed`（全部 Isaac Adapter tests + subtask executor boundary）。 / Full regression: `346 passed`.
- `ruff check`、`compileall`、JSON parse、`git diff --check` 全部通过。 / Ruff, compileall, JSON parsing, and diff check passed.

### No-Motion 运行 / Runtime Evidence
- Workspace `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/`；session `cli:lab-b11c91c66271`；task `task_b16f8e5cbeb84dda`；action `invocation://manipulation-execute_subtask/3ebe297dca4e4fbf`；scene `labutopia-tabletop-rod-rack-v1:74e728eececc4cc590e7bd8dc431f73a:0`。 / Record the no-motion workspace, session, task, action, and scene revision. (local)
- Action 仅消费同次捕获 refs `16/23/15`；每个检查 `3 clearance x 2 transport x 4 corridor x 4 axial = 96` 条，共 288 条。 / Action consumed only same-capture refs `16/23/15`; each exercised 96 routes for 288 total. (local)
- 全部失败：140 IK discontinuity、49 IK unavailable、21 self-collision、78 environment collision；阶段为 `staging_reorient=173`、`approach=92`、`transit_cross=23`。 / All routes failed with the recorded IK/collision and phase distribution. (local)
- `simulated_motion_enabled=false`、`outcome_known=true`、`world_change_started=false`、`possession_state=empty`、`controller_outcomes=[]`；未启动 R04/GLASS_ROD，也未发起 `--execute`。 / The run remained known zero-motion with empty possession and no downstream execution. (local)
- 保留静态预览 `out/lab-fullchain-truth-20261101-staging-corridor-no-motion-r1/artifacts/labutopia/no-motion-video/staging-corridor-observation.mp4`，5 秒、1600x1200、30 fps，明确标注 controller disabled，不作为动作证据。 / Preserve a labelled five-second static observation preview, not Action evidence. (local)

### 实现复核 / Implementation Review
- Major（已修复）：96 条完整异常/候选导致约 74 KB Action error 与约 174k Agent context；改为有界聚合并由单元测试验证。 / Fixed the Major unbounded-diagnostics finding with bounded aggregation and a regression test.
- Blocker/Major：无剩余实现问题；公共 contract、AgentLoop 所有权、opaque refs 与完整运动安全门禁均未改变。 / No remaining implementation Blocker/Major; contracts, ownership, opaque refs, and safety gates remain unchanged.
- 运行阻塞仍存在：新 corridor 未产生完整可行路线，因此本轮不允许 simulated execution。 / Runtime feasibility remains blocked, so simulated execution is not authorized.

### Git 提交 / Git Commit
- Implementation commit: `fa0800a7`.
- Branch: `feature/planning-loop`.
- Time: `2026-11-01 21:20:30 +0800`.
- Log receipt commit: `9a4e8fdd`.
- Push: succeeded to `origin/feature/planning-loop`; remote advanced from `a5615644` to `9a4e8fdd`. / 已成功推送当前分支，远端从 `a5615644` 前进到 `9a4e8fdd`。


## v16.3.9 (2026-11-01 20:26) - codex

### 变更摘要 / Summary [完成 / Completed; zero motion]
- [env] [exp] 使用现有 LabUtopia 场景、`simulator_truth` 标签/深度/点云/最终 USD 几何和 v16.3.8 staged acquire 路线，发起 R03、R04 顺序倾倒及 GLASS_ROD 搅拌的全链路 Agent 仿真执行；不调用 ReMake。 / Start the full-chain R03/R04 sequential pour and GLASS_ROD stir Agent simulation using the existing LabUtopia scene, simulator-truth labels/depth/point clouds/final USD geometry, and the v16.3.8 staged acquire route without invoking ReMake. (local)
- [policy] [test] 两次倾倒的 `tilt_rad=0.87, hold_s=0.60` 与搅拌的 `radius_m=0.009, depth_m=0.04, turns=2.0, duration_s=4.0, direction=ccw` 仅通过用户提示词进入 PlanGraph 和原子动作参数；不在代码、启动脚本或抓取坐标中硬编码。 / Supply both pour parameters and all stir parameters only through the user prompt into PlanGraph and atomic action arguments, without hard-coding them in code, launch scripts, or grasp coordinates. (local)
- [env] [test] 显式启用 `--execute`，但继续要求同次捕获、工艺几何、task-affordance、夹爪开口、workspace、完整姿态 IK/连续性、自碰撞、环境碰撞、payload collision 和 possession 门禁全部通过后才能发出控制器命令；任一失败或未知结果立即停止后续节点。 / Enable `--execute` explicitly while retaining same-capture, process-geometry, task-affordance, aperture, workspace, full-pose IK/continuity, self/environment collision, payload-collision, and possession gates before any controller command; stop later nodes on any failure or unknown outcome. (local)
- [docs] [docs] 保留 Agent session、task、scene revision、候选/preparation、controller outcome、世界变化、持有状态、Host 日志与全部 MP4；若 preparation 在动作前失败，则保留真实相机静态预览并明确其非动作证据。 / Preserve the Agent session, task, scene revision, candidate/preparation evidence, controller outcomes, world-change and possession state, Host log, and all MP4 files; if preparation fails before motion, retain a real-camera static preview and label it as non-action evidence. (local)

### 安全边界 / Safety Boundary
- 本次授权仅限 Isaac/LabUtopia 仿真，不授权真实机械臂或硬件 IO。 / This authorization applies only to Isaac/LabUtopia simulation and does not authorize physical hardware or robot IO.
- AgentLoop 不接收 USD 路径、关节角、IK 策略或碰撞绕过参数；这些机制继续由 Isaac Adapter 独占。 / AgentLoop receives no USD paths, joint angles, IK policy, or collision-bypass parameters; those mechanisms remain owned by the Isaac Adapter.
- 不降低或关闭任何现有运动安全门禁。 / No existing motion-safety gate will be reduced or disabled.

### 执行命令 / Execution Command
```bash
OMNI_KIT_ACCEPT_EULA=YES PYTHONUNBUFFERED=1 \
PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src \
./.venv/bin/python -m isaacsim_lab.agent_host \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --workspace out/lab-fullchain-truth-20261101-staged-symmetry-execute-r1 \
  --execute --execution-timeout-s 1800 \
  '<R03/R04 pour and GLASS_ROD stir instruction with explicit parameters and simulation authorization>'
```

### 实际运行 / Actual Runtime
- [env] [exp] Workspace `out/lab-fullchain-truth-20261101-staged-symmetry-execute-r1/`；session `cli:lab-dc8cd9539e91`；task `task_093815df65154b03`；action `invocation://manipulation-execute_subtask/118c1f7ccfea474e`；scene revision `labutopia-tabletop-rod-rack-v1:03b288762548416e890d5da8b38e9584:0`。 / Record the authorized execution workspace, Agent session, task, Action invocation, and scene revision. (local)
- [policy] [test] 持久化 PlanGraph 原样包含两次倾倒 `tilt_rad=0.87, hold_s=0.6` 和搅拌 `radius_m=0.009, depth_m=0.04, turns=2, duration_s=4, direction=ccw`；参数来自用户提示词，未由 Adapter、profile 或硬编码抓取点注入。 / The persisted PlanGraph preserves the exact user prompt parameters; the Adapter, profile, and grasp poses do not inject them. (local)
- [sense] [test] R03 的 process-feature Query/preparation 与 task-affordance Query/preparation 完成；Action 只消费同次捕获已资格化的 opaque grasp refs `15/23/16`，未回退到原始 64 个 GraspNet 候选。 / R03 process-feature and task-affordance Query/preparation completed, and Action consumed only same-capture qualified refs `15/23/16` without recovering from the raw 64-candidate GraspNet set. (local)
- [env] [test] 三个候选各检查 `3 clearance x 2 transport x 4 axial angle = 24` 条路线，共 72 条；失败分布为 22 次 IK 不连续、16 次 IK 无解、12 次真实自碰撞、22 次环境碰撞，集中在 `staging_reorient` 和 `approach`。 / Each of three candidates exercised 24 routes for 72 total; failures were 22 IK discontinuities, 16 unavailable IK solutions, 12 genuine self-collisions, and 22 environment collisions concentrated at staging reorientation and approach. (local)
- [env] [test] `manipulation.execute_subtask` 返回已知失败：`outcome_known=true`、`world_change_started=false`、scene revision 未变化、`possession_state=empty`、`controller_outcomes=[]`；R04 和 GLASS_ROD 未启动。 / The Action returned a known zero-motion failure with unchanged scene, empty possession, and no controller outcome; R04 and GLASS_ROD did not start. (local)
- [docs] [docs] 失败 Action 未返回动作 artifact；基于本次真实 RGB 帧生成 5 秒、1600x1200、30 fps 的静态预览 `out/lab-fullchain-truth-20261101-staged-symmetry-execute-r1/artifacts/labutopia/no-motion-video/r03-preparation-failed-observation.mp4`，画面明确标注 controller 未启动，不能作为动作证据。 / The failed Action returned no motion artifact; generate a labelled five-second static preview from the run's real RGB frame, explicitly not Action evidence. (local)

### 文件变更详情 / File Changes

#### [新增] `.task/labutopia-r03-authorized-execution-diagnosis-20261101.md` L1-L62

**新增内容 / Added:**
```text
authorized full-chain identity and prompt parameters
72-route failure distribution and collision ownership
PAOS boundary review plus labelled no-motion preview evidence
```

#### [修改] `.task/current.md` L23-L26

**修改前 / Before:**
```text
latest evidence is the controller-disabled no-motion run
```

**修改后 / After:**
```text
latest evidence is the authorized --execute attempt that failed before controller start
```

#### [修改] `CHANGELOG.md` L51-L73

**修改说明 / Description:** 将 v16.3.9 加入最近五版本并滚动移除最旧的 v16.3.4 详细条目。 / Add v16.3.9 to the latest-five window and roll the oldest v16.3.4 detail entry out to the monthly archive.

### 关键运行差异 / Key Runtime Diff
```diff
- v16.3.8 no-motion preparation probe with simulated_motion_enabled=false
+ authorized --execute Agent run with simulated_motion_enabled=true
+ identical safety preparation still blocks before the first controller command
+ exact prompt parameters and same-capture qualified opaque refs remain preserved
```

### 验证 / Validation
- Agent Host 进程完整退出并返回任务 `failed`；没有残留 `isaacsim_lab.agent_host` 或 worker 进程。 / The Agent Host exited completely with task status `failed`; no Agent Host or worker process remained.
- `acceptance.json`、session JSONL 与 task SQLite 一致记录 R03 Action 失败、R04/GLASS_ROD 未执行、`controller_outcomes=[]` 和零世界变化。 / Acceptance, session, and task-store records agree on the R03 failure, blocked downstream nodes, empty controller outcomes, and zero world change.
- 视频经 `ffprobe` 验证为 H.264、1600x1200、30 fps、5.0 秒，并人工检查标注和真实场景画面。 / `ffprobe` verifies H.264, 1600x1200, 30 fps, and 5.0 seconds; the overlay and real scene frame were visually checked.
- 诊断详情：`.task/labutopia-r03-authorized-execution-diagnosis-20261101.md`。 / Diagnosis: `.task/labutopia-r03-authorized-execution-diagnosis-20261101.md`.

### Git 提交 / Git Commit
- Runtime evidence commit: `40745371`.
- Log receipt commit: `74023e97`.
- Push receipt commit: `a5615644`.
- Branch: `feature/planning-loop`.
- Push: runtime/log commits and the push receipt were pushed successfully. / 运行、日志及推送回执提交均已成功推送。


## v16.3.8 (2026-11-01 20:00) - codex

### 预期修改 / Planned Changes [完成 / Completed]
- [env] [feat] 在 Isaac Adapter 私有 preparation 中将 acquire 路线拆分为保持当前姿态垂直抬升、安全运输姿态横移、staging 位置重新定向和最终抓取接近；不修改 AgentLoop、Task-Affordance 公共契约或 opaque 引用语义。 / Split the Adapter-private acquire preparation route into current-orientation vertical raise, safe-transport-orientation translation, staging reorientation, and final grasp approach without changing AgentLoop, Task-Affordance public contracts, or opaque-reference semantics. (local)
- [sense] [feat] 由已验证的最终几何证据声明瓶体轴对称抓取语义，生成等价抓取方向候选；缺失轴证据时不得按标签、USD 路径或物体名称推断对称性。 / Derive axial grasp-symmetry semantics from validated final-geometry evidence and generate equivalent grasp orientations; do not infer symmetry from labels, USD paths, or object names when axis evidence is absent. (local)
- [env] [fix] 对每个 clearance、运输姿态和轴对称角组合复用现有 workspace、完整姿态 IK、连续性、关节限位、自碰撞、环境碰撞及 payload collision qualification，并按完整安全通过、总关节行程和配置顺序选择；所有失败保持零动作并保存逐组合原因。 / Reuse the existing workspace, full-pose IK, continuity, joint-limit, self-collision, environment-collision, and payload-collision qualification for every clearance, transport orientation, and axial-angle combination, selecting by complete safety success, total joint travel, and configuration order while preserving per-combination no-motion failures. (local)
- [test] [test] 增加安全运输 waypoint、staging 重定向、轴对称候选生成与排序、缺失轴证据、全部变体失败和安全门禁不被绕过的测试；只运行 no-motion preparation 和离线回归。 / Add tests for safe-transport waypoints, staging reorientation, axial candidate generation and ordering, missing-axis evidence, all-variant failure, and unchanged safety gates; run no-motion preparation and offline regression only. (local)
- [docs] [docs] 保存本轮诊断、PAOS 所有权与替换边界、证据新鲜度、零动作结论及 findings-first 实现审查。 / Save the diagnosis, PAOS ownership and substitution boundaries, evidence freshness, no-motion conclusion, and findings-first implementation review. (local)

### 架构与安全边界 / Architecture and Safety Boundary
- AgentLoop 只拥有任务语义、候选 opaque 引用、生命周期、恢复与 settlement；Isaac Adapter 独占关节状态、运输姿态、IK 分支、路线和碰撞机制。 / AgentLoop owns only task semantics, opaque candidate references, lifecycle, recovery, and settlement; the Isaac Adapter exclusively owns joint state, transport orientation, IK branches, routes, and collision mechanisms.
- 轴对称声明属于 Provider/Adapter 私有几何证据投影，不进入共享 Tool contract；替换 Provider 时调用方无需改变。 / Axial-symmetry declarations remain a Provider/Adapter-private projection of geometry evidence and do not enter the shared Tool contract, so callers remain unchanged when the Provider is replaced.
- 本轮不启动控制器，不放宽 workspace、IK 容差、连续性、关节限位、自碰撞、环境碰撞、payload collision 或 possession 门禁。 / This iteration does not start the controller or weaken workspace, IK-tolerance, continuity, joint-limit, self-collision, environment-collision, payload-collision, or possession gates.

### 实际修改 / Actual Changes
- [env] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/phase_motion.py:L198-L270,L754-L855` 增加配置校验、几何轴向等价 grasp 变体、完整路线 joint-travel 排序，并将 acquire 拆成 `transit_raise -> transit_orient -> transit_cross -> staging_reorient -> approach`；每个组合继续复用完整 safety qualification。 / Add configuration validation, geometry-supported axial grasp variants, full-route joint-travel ranking, and the staged acquire route while reusing the complete safety qualification for every combination. (local)
- [sense] [feat] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/simulator_truth_perception.py:L17-L83,L172-L187,L290-L307` 从最终组合网格的多个中间横截面验证轴对称，只有径向偏差与角覆盖满足条件时才生成 Adapter 私有 `grasp_symmetry`。 / Validate axial symmetry from multiple intermediate final-composed mesh cross-sections and publish Adapter-private `grasp_symmetry` only when radial deviation and angular coverage pass. (local)
- [sense] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py:L1145-L1168` 只为 reagent bottle、合法非空 `destination://`、已选工艺候选投影私有轴对称证据；不扩展共享 manipulation schema。 / Project private axial-symmetry evidence only for reagent bottles with a valid non-empty destination binding and selected process features, without widening the shared manipulation schema. (local)
- [env] [tune] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json:L13-L37` 配置 3 个抬升 clearance、2 个安全运输姿态和 4 个轴对称角；所有值仍由 Adapter 校验。 / Configure three raise clearances, two safe transport orientations, and four axial angles, all validated by the Adapter. (local)
- [test] [test] `examples/forge-adapters/isaacsim_lab/tests/test_phase_motion.py:L215-L393`、`examples/forge-adapters/isaacsim_lab/tests/test_visual_perception.py:L37-L111` 覆盖路线阶段、运输姿态、staging 重定向、完整资格化后排序、缺失对称证据、所有路线失败、横截面覆盖、非法 quaternion 与非法 destination。 / Cover route stages, transport orientation, staging reorientation, post-qualification ranking, missing symmetry, all-route failure, mesh-slice coverage, invalid quaternions, and invalid destinations. (local)
- [docs] [docs] `.task/labutopia-r03-staged-symmetry-diagnosis-20261101.md:L1-L85`、`.task/current.md:L1-L68`、`docs/forge/IMPLEMENTATION_REVIEW_V16_3_8.md:L1-L51` 保存诊断、当前阻塞、视频证据和 findings-first 实现复核。 / Save the diagnosis, current blocker, video evidence, and findings-first implementation review. (local)

### 关键 Diff / Key Diff
```diff
- lateral transit uses the final grasp orientation directly
- opening rim axis is treated as sufficient grasp-rotation evidence
- malformed quaternion/destination values can escape or enter private resolution
+ raise vertically with the current pose, orient for safe transport, translate, then reorient at staging
+ prove axial equivalence from several covered final-mesh body slices before enumerating angles
+ normalize configuration and destination failures through explicit Adapter validation
```

### 验证 / Validation
- 定向 phase-motion + visual-perception 回归：`135 passed`。 / Focused phase-motion plus visual-perception regression: `135 passed`.
- 完整 Isaac Adapter + subtask executor 边界回归：`329 passed`。 / Full Isaac Adapter plus subtask-executor boundary regression: `329 passed`.
- Ruff、compileall、motion JSON validation 与 `git diff --check` 通过。 / Ruff, compileall, motion JSON validation, and `git diff --check` passed.
- 实现复核修复两个 Major：非法字符串/布尔 quaternion 统一映射为 `invalid_motion_configuration`；空或错误前缀 destination 不再进入私有对称证据解析。修复后无剩余实现 Blocker/Major。 / The implementation review fixed two Major issues: malformed quaternion values now map to `invalid_motion_configuration`, and invalid destination bindings cannot enter private symmetry resolution. No implementation Blocker/Major remains.

### 无动作运行与视频 / No-Motion Runtime and Video
- Workspace `out/lab-fullchain-truth-20261101-staged-symmetry-no-motion-r1/`；session `cli:lab-91c7fcbbb264`；task `task_a7a9e1dc56014b26`；scene revision `labutopia-tabletop-rod-rack-v1:e3821a001bc84d8aaaa53bb89d8e7937:0`。 / Record the no-motion workspace, session, task, and scene revision. (local)
- R03 的 `23/16/15` 每个遍历 `3 clearance x 2 transport x 4 axial angle = 24` 条完整安全路线；失败已移动到 `staging_reorient` 与 `approach` 的 IK/自碰撞/桌面或相邻 R04 碰撞。 / Each R03 qualified grasp exercised 24 complete safety routes; failures now occur at staging reorientation or final approach due to IK, self-collision, table, or adjacent-R04 collision. (local)
- `simulated_motion_enabled=false`、`world_change_started=false`、`possession_state=empty`；无 controller command、抓取、倾倒或搅拌。 / Motion stayed disabled with no world change, possession, controller command, grasp, pour, or stir. (local)
- 保留 5 秒、1600x1200、30 fps 的静态真实相机预览：`out/lab-fullchain-truth-20261101-staged-symmetry-no-motion-r1/artifacts/labutopia/no-motion-video/staged-symmetry-observation.mp4`；视频明确标注 controller disabled，不作为 Action 执行证据。 / Preserve a five-second static real-camera preview explicitly marked controller-disabled; it is not Action execution evidence. (local)

### Git 提交 / Git Commit
- Implementation commit: `29a7b642` (`2026-11-01 20:19:22 +0800`).
- Log receipt commit: `fa8768db`.
- Branch: `feature/planning-loop`.
- Push: failed on 2026-11-01 because the GitHub TLS connection was non-properly terminated (`GnuTLS recv error (-110)`); commits remain local. / 推送失败：GitHub TLS 连接异常终止（`GnuTLS recv error (-110)`），提交保留在本地。


## v16.3.7 (2026-11-01 19:37) - codex

### 预期修改 / Planned Changes [完成 / Completed]
- [env] [fix] 在 Isaac Adapter preparation 中拒绝超过连续性阈值且邻近 IK 无法恢复的关节分支跳变，禁止将远端 Lula 解继续送入碰撞采样；阈值保留在 motion profile 配置。 / Reject joint-branch jumps during Isaac Adapter preparation when the nearby IK solver cannot recover a continuous solution, preventing a distant Lula solution from entering collision sampling; keep the threshold in the motion profile. (local)
- [env] [fix] 碰撞失败记录真实被检查的关节样本与 TCP，而不是只记录 waypoint 终点；混合 clearance 失败使用准确的路线不可用汇总并保留逐 clearance 原因。 / Record the actual checked joint sample and TCP for collision failures instead of only the waypoint endpoint; summarize mixed-clearance failures accurately while preserving every clearance-specific cause. (local)
- [policy] [fix] Skill/AgentLoop 边界只消费 Adapter 显式返回的 `requires_replan` 与 `recommended_action`，并区分“选择同次捕获替代候选”和“刷新抓取候选”；不得再解析错误文本或把两类恢复建议折叠为同一动作。 / At the Skill/AgentLoop boundary, consume only the Adapter's explicit `requires_replan` and `recommended_action`, preserving the distinction between selecting a same-capture alternative and refreshing grasp candidates; do not parse error text or collapse both recovery recommendations into one action. (local)
- [test] [test] 增加 IK 分支泄漏、连续局部解、碰撞采样诊断、混合失败汇总和显式恢复语义映射测试；不启动仿真动作。 / Add tests for IK branch leakage, continuous local recovery, collision-sample diagnostics, mixed-failure aggregation, and explicit recovery-semantics mapping without starting simulated motion. (local)
- [docs] [docs] 保存 R03 候选 15/16/23 的诊断、PAOS 所有权边界、无动作证据、实现审查和下一 Adapter 路线阻塞。 / Save the diagnosis for R03 candidates 15/16/23, PAOS ownership boundaries, no-motion evidence, implementation review, and the next Adapter route blocker. (local)

### 架构与安全边界 / Architecture and Safety Boundary
- AgentLoop 继续只拥有任务语义、opaque 引用、生命周期、settlement 与停止；不接收关节角、USD 路径、碰撞几何或 IK 策略。 / AgentLoop continues to own task semantics, opaque references, lifecycle, settlement, and stopping only; it receives no joint angles, USD paths, collision geometry, or IK policy.
- Task-Affordance Provider 继续负责工艺资格化；Isaac Adapter 独占初始状态、frame transform、IK 连续性、路线与碰撞机制。 / The Task-Affordance Provider continues to own process qualification; the Isaac Adapter exclusively owns initial state, frame transforms, IK continuity, routes, and collision mechanisms.
- 本次只修改无动作 preparation、错误投影和诊断，不放宽 workspace、IK 位姿容差、关节限位、自碰撞、环境碰撞、payload collision 或 Action 门禁，不启动控制器。 / This change modifies no-motion preparation, failure projection, and diagnostics only; it does not weaken workspace, IK pose tolerance, joint-limit, self-collision, environment-collision, payload-collision, or Action gates and starts no controller.

### 实际修改 / Actual Changes
- [env] [fix] `examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-motion.json:L27` 增加 `maximum_waypoint_joint_delta_rad=0.5`；`phase_motion.py:L204-L210,L746-L756,L805-L872` 以配置阈值筛除不连续 primary/tool-feature IK，附近解只有在完整求解成功且连续时才可替代，并在真实碰撞样本上记录 joint/TCP。 / Add the configurable waypoint joint-delta limit, reject discontinuous primary/tool-feature IK unless a successful continuous nearby solution exists, and report the actual collision-check joint/TCP sample. (local)
- [env] [fix] `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py:L146-L190` 保留 `ik_discontinuity`、`route_unavailable` 和拒绝候选引用，并投影明确的 `select_alternative_candidate` 或 `refresh_grasp_candidates` 零动作恢复建议。 / Preserve Adapter-owned discontinuity/route failures and rejected opaque refs, projecting explicit no-motion alternative-selection or grasp-refresh recommendations. (local)
- [policy] [fix] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py:L500-L542,L819-L839` 删除错误文本解析，验证完整零动作事实后，将两个受支持的 Adapter 建议分别映射到 Agent replan 语义；未知建议继续 fail closed。 / Remove diagnostic-string parsing and map the two supported Adapter recommendations to distinct Agent replan semantics only after all zero-motion facts are verified; unknown recommendations remain fail-closed. (local)
- [test] [test] `test_phase_motion.py:L282-L493`、`test_paos_integration.py:L927-L984`、`test_subtask_executor.py:L610-L683` 覆盖混合 clearance、远端 IK 不得进入碰撞采样、连续局部解、真实检查样本、候选继续遍历及显式恢复映射与负例。 / Cover mixed clearances, rejection of distant IK before collision sampling, successful continuous nearby IK, checked samples, bounded candidate continuation, explicit recovery mapping, and negative paths. (local)
- [docs] [docs] `.task/labutopia-r03-transit-ik-collision-diagnosis-20261101.md:L1-L66`、`.task/current.md:L1-L66`、`docs/forge/IMPLEMENTATION_REVIEW_V16_3_7.md:L1-L44` 保存诊断、当前阻塞和 findings-first 实现复核。 / Save the diagnosis, current blocker, and findings-first implementation review. (local)

### 关键 Diff / Key Diff
```diff
- distant primary IK survives failed nearby recovery and enters collision sampling
- Skill searches error text and rewrites every route failure as alternative selection
+ reject discontinuous IK before collision sampling unless nearby IK fully succeeds
+ report checked joints/TCP and preserve every clearance-specific reason
+ consume typed Adapter recovery facts and preserve alternative-selection vs refresh semantics
```

### 验证 / Validation
- 定向回归：`123 passed, 1 warning`。 / Focused regression: `123 passed, 1 warning`.
- 完整 Isaac Adapter + subtask executor 回归：`312 passed`。 / Full Isaac Adapter plus subtask-executor regression: `312 passed`.
- Ruff、compileall、motion JSON validation 与 `git diff --check` 通过。 / Ruff, compileall, motion JSON validation, and `git diff --check` passed.
- 首次完整命令因缺少 `robotwin20_adapter` 的 `PYTHONPATH` 未完成收集；补齐仓库依赖路径后，禁用插件的运行得到 `310 passed, 2 async tests unavailable`，按正常 pytest 插件配置重跑后完整 `312 passed`。 / The first full command lacked the RobotWin adapter path; after correcting it, the plugin-disabled run passed 310 synchronous tests with two async tests unavailable, and the normal plugin-enabled run passed all 312.

### 无动作运行证据 / No-Motion Runtime Evidence
- Workspace `out/lab-fullchain-truth-20261101-ik-continuity-no-motion-r1/`；session `cli:lab-2a6cdb5274e6`；task `task_a5127feeb8c8476a`。 / Record the post-fix no-motion workspace, session, and task. (local)
- 候选 `16/15/23` 在 `0.04/0.08 m` clearance 的 primary IK 最大关节跳变为 `3.575-4.431 rad`，均在碰撞采样前返回 `ik_discontinuity`；`0.12 m` 均为 `inverse_kinematics_failed`。 / All qualified candidates reject discontinuous primary IK before collision sampling at lower clearances and have no IK solution at the highest clearance. (local)
- 旧的 `finger overlaps table` 与 `link2 overlaps link5/link6` 不再出现，证明这些标签受错误 IK 分支污染；这不证明新路线可执行。 / The prior table/self-collision labels no longer occur, proving they were contaminated by the invalid IK branch; this does not prove route executability. (local)
- `simulated_motion_enabled=false`、`controller_outcomes=[]`、`world_change_started=false`、`outcome_known=true`、`possession_state=empty`；R04 与 GLASS_ROD 未启动。 / Motion stayed disabled, no controller/world change occurred, possession remained empty, and later subtasks did not start. (local)

### 审查结论与剩余阻塞 / Review Conclusion and Remaining Blocker
- 实现审查发现并修复一个 Major：Skill 虽已停止解析字符串，但仍折叠不同 Adapter 恢复建议；修复后无剩余 Blocker/Major。 / The implementation review found and fixed one Major recovery-semantics collapse; no implementation Blocker/Major remains.
- 运行能力仍被 Adapter-owned `transit_cross` 完整姿态 IK/路线构造阻塞。下一步应分离 raise、safe-orientation translate、staging reorient 与 approach，并枚举瓶体轴对称等价方向；先做无动作 preparation，不得调低碰撞或 IK 门禁。 / Runtime capability remains blocked by full-pose IK and route construction for `transit_cross`; the next Adapter-private iteration must split route phases and enumerate bottle-axis-equivalent orientations under unchanged no-motion gates.

### Git 提交 / Git Commit
- Implementation commit: `38b46429` (`2026-11-01 19:54:27 +0800`).
- Branch: `feature/planning-loop`.
- Push: failed because `github.com:443` was unreachable after `136405 ms`; all commits remain local. / 推送失败：`github.com:443` 在 `136405 ms` 后仍不可达，全部提交保留在本地。
