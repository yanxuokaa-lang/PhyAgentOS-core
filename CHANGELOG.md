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

## v17.3.10 (2026-11-08 11:16) - codex

### 完成范围 / Completed Scope
- [env] [fix] 将可选 `relation.establish` Provider/resolver 从生产 `build_persistent_host` 贯通到既有 Persistent Runtime Bundle；缺少其一或 Provider 缺少 `admit` 时在 host 资源启动前拒绝。 / Forward the optional `relation.establish` Provider/resolver from production `build_persistent_host` to the existing Persistent Runtime Bundle; reject a partial pair or a Provider without `admit` before host resources start.
- [eval] [test] 覆盖 host 集成路径中 Provider 启用/省略、半配置拒绝和错误 Provider 拒绝。 / Cover enabled/omitted Provider composition and partial/invalid-provider rejection through the host integration path.
- [docs] [diag] 保存 host 入口之前遗漏端口转发的诊断；stack 几何、route/contact qualification 和仿真证据仍未具备。 / Record the missing forwarding at the host entry point; stack geometry, route/contact qualification and simulation evidence remain unavailable.

### 文件变更详情 / File Changes
- [修改] `examples/forge-adapters/robotwin20/src/robotwin20_adapter/persistent_host.py` L393-L400, L408-L423, L926-L944：暴露并校验 Provider/resolver 注入，再转交 bundle。 / Expose and validate Provider/resolver injection, then forward to the bundle.
- [修改] `examples/forge-adapters/robotwin20/tests/test_persistent_host.py` L291-L319, L468-L617：测试成对契约和启用/禁用 Provider 的 production-host 组合。 / Test the paired contract and production-host composition with and without the Provider.
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L285-L309：追加 host 入口诊断和 PAOS 所有权边界。 / Add the host-entry diagnosis and PAOS ownership boundary.
- [修改] `changelog/2026-11_part2.md` L644-L680：记录计划、详细 Diff、行号与验证。 / Record the plan, detailed diff, line references and validation.
- [修改] `CHANGELOG.md` L52-L81：更新最近五版本。 / Update the latest-five index.

### 关键 Diff / Key Diff
```diff
before: build_persistent_host -> Runtime Bundle without relation Provider/resolver
after:  build_persistent_host(optional Provider/resolver) -> pair/port validation
        -> Runtime Bundle -> optional relation.establish registration
omitted: unchanged default Tool set; no Action endpoint is registered
```

### 架构与验证 / Architecture and Validation
- Host 仅组合 Adapter Provider；通用 endpoint 校验 relation 和 evidence lineage；Runtime、Coordinator、AgentLoop 生命周期所有权不变。 / The host only composes the Adapter Provider; the generic endpoint validates relation/evidence lineage; Runtime, Coordinator and AgentLoop lifecycle ownership is unchanged.
- 定向 pytest `49 passed, 1 warning`；Ruff、compileall 通过。warning 是 pytest 环境不识别 `asyncio_mode`。 / Focused pytest: `49 passed, 1 warning`; Ruff and compileall pass. The warning is the environment's unrecognized `asyncio_mode` option.
- 无 task、Action admission、RoboTwin runtime、仿真或运动；stack 仍不可执行。 / No task, Action admission, RoboTwin runtime, simulation or motion; stack remains non-executable.

### Git 提交 / Git Commit
- Implementation: pending; branch: `feature/planning-loop`. / Implementation: pending; branch: `feature/planning-loop`.

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

## v17.3.7 (2026-11-07 18:02) - codex

### 完成范围 / Completed Scope
- [policy] [feat] 在现有 `relation.target` Query 后新增 no-motion 候选投影，验证当前节点的 entity/relation/support/observation/scene/frame/calibration identity，并保留 selected destination、pose、candidate set 和 geometry evidence。该投影不是 relation Action Provider，也不授权运动。 / Add a no-motion candidate projection after the existing `relation.target` Query, validating entity/relation/support/observation/scene/frame/calibration identity for the current node and preserving the selected destination, pose, candidate set and geometry evidence. This projection is not a relation Action Provider and does not authorize motion. (local)
- [eval] [test] 覆盖 freshness lineage、candidate selection、stale/unknown selection、missing evidence；RoboTwin table support 与 motion refusal 继续显式失败。 / Cover freshness lineage, candidate selection, stale/unknown selections and missing evidence; RoboTwin table support and motion refusal remain explicit failures. (local)

### 文件变更详情 / File Changes
- [修改] `examples/forge-skills/pick-place-workflow/src/pick_place_workflow/relation_target.py` L94-L153、L275-L278：提供 Action-facing domain binding projection，`motion_authorized=False`。 / Provide the Action-facing domain-binding projection with `motion_authorized=False`.
- [修改] `examples/forge-skills/pick-place-workflow/tests/test_relation_target.py` L1-L7、L94-L146：增加 relation binding contract 与拒绝路径。 / Add relation-binding contract and refusal-path tests.
- [修改] `.task/robotwin-stack-blocks-three-integration-diagnosis-20261106.md` L183-L203：记录本次边界及尚缺的 table geometry、Action Provider 和 route/contact qualification。 / Record this change's boundary and remaining table geometry, Action Provider and route/contact qualification gaps.
- [修改] `changelog/2026-11_part2.md` L545-L571：记录双语变更、文件范围、Diff、验证和 Git 提交信息。 / Record bilingual changes, file scope, diff, validation and Git commit information.

### 关键 Diff / Key Diff
```diff
before: Query candidate geometry had no provider-neutral domain projection
after:  bind_relation_target_candidate(result, candidate_ref, expected_current_node)
        -> destination + transform + evidence + scene/observation lineage; motion_authorized=False
still:  no relation.establish Action Provider; table support and stack route preparation unavailable
```

### 架构与验证 / Architecture and Validation
- AgentLoop/Coordinator lifecycle unchanged; Coordinator remains the sole settlement owner and RoboTwin Adapter owns environment geometry/route mechanisms. The projection does not bypass Action admission or settlement. / AgentLoop/Coordinator lifecycle is unchanged; Coordinator remains the sole settlement owner and the RoboTwin Adapter owns environment geometry/route mechanisms. The projection does not bypass Action admission or settlement.
- 定向测试 `40 passed, 1 warning`；warning 为 pytest 环境不识别 `asyncio_mode` 配置；`git diff --check` 通过。 / Focused tests: `40 passed, 1 warning`; the warning is that this pytest environment does not recognize the `asyncio_mode` option; `git diff --check` passes.
- 未创建 PAOS task、未调用 Gateway Action、未启动模拟或运动；stack Adapter 仍 `motion_execution_supported=False`。 / No PAOS task or Gateway Action was created or invoked, and no simulation or motion was started; the stack Adapter remains `motion_execution_supported=False`.

### Git 提交 / Git Commit
- Implementation: `5dab63fc`; receipt: `e61cf47a`; branch: `feature/planning-loop`; push succeeded. / Implementation: `5dab63fc`; receipt: `e61cf47a`; branch: `feature/planning-loop`; push succeeded.

## v17.3.6 (2026-11-07 17:46) - codex

### 推送回执 / Push Receipt
- [chore] [docs] `git push origin feature/planning-loop` 在 45 秒超时（exit 124）；随后只读 `git ls-remote` 在 20 秒超时（exit 124），未获得远端回执，本地分支仍 ahead 6。停止重复网络尝试。 / `git push origin feature/planning-loop` timed out after 45 seconds (exit 124); the subsequent read-only `git ls-remote` timed out after 20 seconds (exit 124), so no remote receipt is available and the local branch remains ahead by 6. Stop repeated network attempts. (local)

### 文件变更 / File Changes
- `changelog/2026-11_part2.md`：记录 v17.3.5 推送尝试结果。 / Record the v17.3.5 push attempt result.

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
