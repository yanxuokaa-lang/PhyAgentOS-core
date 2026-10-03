# v12.5.15 seven-dimension implementation review / 七维实现审核

## Findings and disposition / 问题与处理

- **Major, fixed:** invocation history hid the only formal contract recovery route; request/result pairs doubled the count. Discovery now keeps context and task getters available regardless of historical read count.
- **Major, fixed:** file reads alone cannot recover task-owned Skill semantics after activation compaction. The existing task getter now offers opt-in persisted current instructions, preserved by prompt compaction without injecting prose into ordinary reads.
- **Major, fixed:** repeated shell/context reads consumed all iterations with no Coordinator evidence, and budget exhaustion returned no failure code. Discovery now distinguishes first successful distinct contract reads from repeated reads, corrects once, then returns `discovery_no_progress`; overall exhaustion returns `tool_iteration_limit`. Both entrypoints use Coordinator failure settlement.
- **Major, fixed during review:** budget failure could close a clarification checkpoint or an `unknown` physical invocation. Replan, waiting, cancellation, pause and uncertain owned execution remain recoverable; Coordinator still refuses unsettled Action/Session settlement.

以上问题均已在本轮源码修复；没有保留本轮新增路径的 Blocker/Major。下面的基线失败与实际运行缺口仍需明确区分。

## Seven dimensions / 七个维度

| Dimension / 维度 | Source and evidence / 依据 | Assessment / 结论 |
| --- | --- | --- |
| Architecture integration / 架构集成 | PromptContext owns request visibility; AgentLoop owns turn budget; existing task getter reads Coordinator state; Coordinator alone settles task status. | No second task/contract/Runtime authority. 没有平行状态机。 |
| Correctness / 正确性 | Paired-context, forced-compaction, distinct-contract-to-Query, corrective-recovery, repeated-read and both-entrypoint regressions. | Contract recovery remains callable; real local Query wrapper creates the fixture's own record. 不把读取当执行。 |
| Recovery and idempotency / 恢复与幂等 | Pending/unknown Action, replan, waiting and cancellation tests; existing settlement and planning recovery suites. | No auto-replay, no new task, no reinterpretation of unknown as physical success. |
| Robotics safety / 机器人安全 | Registry guard and Coordinator/Gateway admission are unchanged; local fixture transport only. | No live Query/Action, no calibration/frame/IK/collision/authorization relaxation. |
| Extension compatibility / 扩展兼容 | No added RGB/color/camera/provider branches; default-compatible getter option; new constructor option appended after existing positional parameters. | Generic discovery; both CLI and Gateway wire the same validated config. |
| Observability and maintainability / 可观测与可维护性 | Stable failure codes; task/revision/stall/correction log; shared failure convergence; bilingual diagnoses and operator config. | No narration-only success, no new hash/lock/gate, no shell replacement control plane. |
| AgentLoop autonomy / 自主规划 | Host only measures progress and returns a bounded failure; scripted model explicitly chooses the recovery Query. Node/continuation planning ownership is unchanged. | Host does not schedule observe, targets, PlanGraph or Action. 继续、澄清与 replan 仍基于实际结果。 |

## Validation / 验证

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q tests/test_prompt_context.py tests/test_agent_foundation.py tests/test_long_horizon_controller.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin -q tests
```

- Focused: **179 passed**. Full Core: **764 passed, 2 failed**. Ruff and `git diff --check` passed.
- Existing baseline failures are unchanged: `test_query_error_survives_live_and_persisted_settlement_and_recovery_prompt` has a SimpleNamespace without `invocation_id`; `test_rgb_attribute_sorting_loop_replans_after_drop_and_reducer_replays` expects `verify` but receives `arrange-green`. These were previously reproduced on parent `b83cb88`; this change does not modify either test or its production owner.
- 基线不是全绿；不得把它写成“所有测试通过”。本轮验证是无运动 control-plane 回归，不是 RGB benchmark 成功证据。

## Remaining boundary / 剩余边界

The scripted provider proves control flow, not live-model decision quality. Fresh error receipts count as new Coordinator evidence; this detector is not a semantic evaluator of every repeated Query failure, and the overall iteration cap still applies. Real provider/benchmark acceptance is not run. Existing Runtime, Qwen, proxy, installed Skill/Node and live task are unchanged. A new Agent process loads the updated Core; no Skill repackage is needed for these Core-only source changes.

实际部署任务未被取消、恢复或替换；没有擅自安装、重启服务或执行真实验收。
