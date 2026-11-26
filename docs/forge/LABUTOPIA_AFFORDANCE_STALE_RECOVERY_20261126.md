# v18.0.4：抓取准备 stale 的证据刷新恢复

## 实际失败与缺口

2026-11-26的132940双视角任务task_0c6254c467a44d06完成R05三阶段后，在R03抓取准备前failed。旧失败不改写；原始证据位于`out/labutopia-elevated-20261126/v18.0.3-r05-r03-live-dual-132940/`。

- event2063（14:04:30.591901+08:00）：R03 scene:0 process_features stale，LabSubtaskContinuation的场景版本差异分支已选择replan并刷新至scene:3。系统已有恢复能力。
- event2103（14:06:22.324234+08:00）：同scene:3的prepare_grasp_task_affordance请求把calibration从`bfe12131065a44a4937c1528fd463068.json`写成`bfe121310065a44a4937c1528fd463068.json`，Provider返回stale。Agent stop原文指出：“当前 settlement 的 world_change_started、outcome_known 和 requires_replan 均为 null，不满足 Runtime 明确报告 world_change_started=true 后 requires_replan=true 的恢复重规划条件”。
- 旧实时决策投影的三个字段为null；归档的persisted回放后来将只读结果推断为world_change_started=false/outcome_known=true。不能把后者倒写成决策当时已有的事实。预算未耗尽，实际缺口是Preparation未携带现成evidence恢复字段、同scene失配走super而未命中query_evidence分支，加上提示将无运动失败导向stop。

## 修复归属与行为

通用GraspTaskAffordancePreparationEndpoint对输入scene/frame不符、证据超龄、Provider身份不符或明确stale，统一保留原请求身份和错误并输出failure_owner=evidence、failure_code=grasp_affordance_evidence_stale、world_change_started=false、outcome_known=true、retryable_in_revision=false、requires_replan=true、recommended_action=refresh_declared_evidence、motion_authorized=false。output_schema仅允许这组已有恢复语义字段。invalid/unavailable/异常保持原类别，缺identity不能把这些故障误标成stale；available也不授权运动。

AgentRecoveryDecisions提示明确只读可刷新证据不要求先发生运动。实际选择和proposal仍使用既有_evidence_refresh_kind与声明的scene-refresh Query；Coordinator独占修订、预算和结算，unknown物理后果不能直接重试。Provider继续拥有当前capture/候选匹配，未修改Isaac生产Provider或Lab continuation，未修正opaque引用、增加retry loop/hash/gate。

## 无运动验证

- 5文件集中回归234 passed/10.28s；PlanningLoop预算/unknown子集17 passed/2.50s，共251。修改的2生产与3测试文件Ruff通过，git diff --check通过。
- 替代Provider的明确stale与返回identity失配均经过真实Preparation端；实时AgentLoopNodeExecutor和持久_tool_result_from_execution的8个诊断字段及settlement相同。Agent选择replan，只生成无旧绑定的声明scene.observe Query。Coordinator接受有预算的新修订并保留唯一完成Action，0预算拒绝。
- 实际LabSubtaskContinuation同scene Preparation失配明确不走自身scene差异分支，而通过父类恢复；已有fresh receipt continuation只续R03，R05完成记录和Action保持，unknown/partial不能绕过。测试使用真实端点与生命周期组件、替代外部Provider，不声称LLM语义准确率或新物理结果。

验证命令：

```bash
PYTHONPATH=examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/scene-understanding-http/src .venv/bin/python -m pytest examples/forge-skills/pick-place-workflow/tests/test_grasp_task_affordance.py tests/test_agent_foundation.py tests/test_recovery_decisions.py tests/test_planning_effect_recovery.py examples/forge-adapters/isaacsim_lab/tests/test_subtask_continuation.py -q
PYTHONPATH=examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest tests/test_planning_loop.py -q -k 'replan_budget or unknown'
```

## 待启动的真实验证

唯一新目录`out/labutopia-elevated-20261126/v18.0.4-r05-r03-evidence-recovery-143036/`从132940复制11必要配置/脚本，7份字节相同、3份仅路径变化、1份local host增加一次注入；未复制DB/工件。原R05→R03指令、60/60N、.02/.2m/s、retain4mm、阈值、replan4、provider retries12/delay15s、执行2700/3600s、真实global+wrist与overlay=false全部保持。没有再次启动静态preview。

local host在首次R03 Preparation入口deepcopy后给calibration文件名插入一个0，调用原生产endpoint/Provider，保存original/modified参数和实际响应到fault-injection.json；后续全部透传。故障发生在endpoint边界，持久调用record可能保存注入前参数，必须结合fault receipt理解，不能伪称LLM再次打错。无运动harness检查用临时目录和替代Provider验证R05 available→首次R03 stale/refresh→下次R03 available、触发一次且原参数未变；正式目录尚无fault receipt/任务DB。

验收将检查一次注入后Agent自主创建以scene.observe起始的新revision、新鲜refs重新准备R03、R05 Action仍一次、全部真实动作视频按顺序拼接且无文字卡。当前尚未启动，不产生新的运动结论。metadata保留当前来源commit并明确待主审新commit更新；seed/checkpoint不适用、服务/调度漂移及输入配置均记载。准备时RAM可用21Gi、GPU空闲8573MiB、/home空48Gi、/tmp空11Gi，无旧Isaac/host进程。

启动命令（主审更新code并授权后）：

```bash
.venv/bin/python -u out/labutopia-elevated-20261126/v18.0.4-r05-r03-evidence-recovery-143036/launch.py
```

English: The previous run already recovered a scene-revision mismatch, but a later same-scene grasp-preparation mismatch lacked existing evidence-refresh diagnostics and stopped. This patch supplies explicit no-motion/known-outcome recovery fields at the provider-neutral endpoint and clarifies Agent guidance; the existing Coordinator and declared scene-refresh Query retain ownership.251 no-motion tests cover endpoint status/schema, identical live/persisted settlement, bounded recovery, completed-action preservation and the actual Lab superclass/continuation path. An isolated unchanged dual-camera run with one endpoint-boundary calibration typo is prepared but unstarted. Its injected arguments and actual response will be recorded separately from pre-injection invocation arguments. No simulation, commit or push was performed for this patch.
