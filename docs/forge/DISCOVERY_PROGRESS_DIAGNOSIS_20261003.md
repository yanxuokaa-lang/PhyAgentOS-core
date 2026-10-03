# Discovery progress and status diagnosis / 发现阶段进展与状态诊断

## Recorded facts / 日志事实

The same task performs repeated Skill/status/help/source reads until 40 model iterations. Five contexts were ready; no task-bound Query or PlanGraph was produced. CLI returned iteration exhaustion but persisted task status remained `executing`.

同一任务一直核查，没有真实发现执行；并非放置完成后的刷新，也并非目标注入或 Qwen 的本轮失败。

## Cause / 原因

The loop measures tool-call rounds, not changes in Coordinator facts. `exec` remains usable, so removing readers only changes how repeated reads occur. The max-iteration branch returns text without `turn_failure_code`; existing `_process_message` failure settlement never runs. The system-message branch also omits the normal failure-settlement path.

循环没有区分“读取帮助”和“新增执行记录”；失败结果与任务状态因此分歧。LiteLLM SOCKS cost-map warning falls back locally and does not explain normal model responses repeating this stage.

## Repair / 修复原则

Use current task/revision/status, execution record identity/status and graph state for discovery progress. Count first successful context acquisitions per tool as preparation, not every read. After bounded unchanged rounds, provide one correction naming the available formal routes; after continued stagnation return a structured failure through existing Coordinator settlement. Iteration exhaustion must also carry a failure code.

Agent chooses Query, clarification, continuation or replan from evidence; the host must not schedule observation or pretend a world-changing Action happened. Preserve unresolved invocation/session reconciliation and `awaiting_replan`. Share failure convergence for user and system turns. Tests must cover complete request/result pairs, compaction, actual Query dispatch, repeated shell reads and persisted state.

不取消当前部署任务，不重启服务，不安装包，不执行真实 Query/Action；以无运动测试验收源码修复。

## Operator configuration / 配置

`agents.defaults.discoveryNoProgressLimit` (Python: `discovery_no_progress_limit`) defaults to 6 consecutive unchanged discovery rounds. First distinct successful ToolSpec reads, first task-owned Skill recovery, and Coordinator record/status changes reset the counter. After one correction, another unchanged window ends the turn with `discovery_no_progress`; the existing `maxToolIterations` remains the overall bound. A genuine missing requirement may be handed to the user through clarification. Configuration changes take effect in a newly started Agent process, not a running Runtime.

该预算不影响非 Forge 会话、节点执行或物理对账。不会把只读 `motion_authorized=false` 当失败，不修改外部目标注入，不自动执行任何 Query/Action。模型仍负责根据当前证据选择后续计划、澄清或 replan。
