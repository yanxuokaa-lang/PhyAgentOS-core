# Grasp coverage repair / 抓取覆盖修复

## Diagnosis / 诊断

v16.6.3 fresh no-motion run `task_4972b9d477f048d2` finds four
aperture failures and six candidates with four obstructed final orientations
each. These 24 endpoint results block 48 approach combinations. Final-pose
checking and private error boundaries are repaired, but no usable grasp exists
in the tested set. This does not prove all model predictions or the scene fail.

Observed funnel: 1059 decoded -> worker 512 -> NMS 389 -> retained 64.
Measure which eligible poses disappear at each selection stage on the same
captured point cloud before changing generation or geometric qualification.
Historical replay must not become fresh preparation authority.

## Ownership / 架构职责

- Generic domain/AgentLoop retains semantic parameters, opaque candidate
  selection, lifecycle, cancellation, recovery and settlement.
- Grasp Provider owns model decoding and bounded candidate coverage. Task-
  Affordance Provider owns grasp/process qualification against current evidence.
- Isaac Adapter owns composed geometry, coordinate transforms, aperture, IK,
  collision, complete-route preparation and controller feedback.
- Reuse existing ports; replacing a model/sampler must not change callers or
  public schemas. New candidates require new recorded opaque references; Action
  cannot shift old poses or recover Provider-rejected raw candidates.
- Freshness remains the existing observation/scene/frame/calibration chain.
  Missing geometry, stale identities, ambiguity or Provider failure stay explicit.
- Smallest leak tests: a substituted model emits a less frequent usable region;
  bounded selection retains its unmodified pose/score; rejected candidates cannot
  return through qualified-only recovery; no test invokes an actuator.

## Plan / 实施路线

1. Replay recorded point cloud with the same checkpoint/configuration/seed;
   persist native, sampled and retained hypotheses and compare coverage.
2. Fix the evidenced loss in its owning Provider; keep all safety/process checks.
3. Add substitution/failure/lineage tests, integrate configuration, then run fresh
   native no-motion qualification. Record remaining failures without success inflation.
4. Review architecture and publish precise changes and validation receipts.

## Measured loss and chosen repair / 实测丢失与修复决策

Replay output: `out/lab-grasp-sampling-20261102-r2/sampling.json`.
Same captured cloud, checkpoint, four input rotations, seed=0, point budget=12000.
GPU inference produced 1057 thresholded native candidates on replay versus 1059
decoded in the old run; do not claim bitwise determinism from the seed alone.

| Stage | Candidates | Existing process-qualified | Aperture rejects within qualified | Padded palm above table plane |
| --- | ---: | ---: | ---: | ---: |
| Native model pool | 1057 | 68 | 33 | 4 |
| Worker orientation sample | 512 | 43 | 21 | 2 |
| NMS + existing retained cap | 64 | 10 | 4 | 0 |

Both surviving worker hypotheses (raw worker indices 304 and 241) also survive
normal NMS into its 389 candidates. Thus the final retention limit, not NMS,
removes them. A measured cap sweep retains neither at 64/96/128, one at 192/256,
and both at 512. Candidate indices are diagnostic identities within this replay,
never production selectors. The GraspNet source revision read during measurement
is `280c215129f759ed8649cb4e89fc5dfee55f4f80`.

The last column is a diagnostic necessary condition, not collision/IK/route
admission: it transforms recorded cooked palm bounds with the captured camera
and calibrated provider/TCP/hand relations. Its two surviving worker hypotheses
have native scores approximately .0830 and .0536, TCP Z approximately .7354 and
.7346 m. There is no need to invent new poses to recover those missing contacts.

First-stage repair: align this experiment's `max_candidates` with its existing
`sample_count=512` cap, retaining all post-NMS candidates for task-affordance
qualification. Keep model thresholds, NMS, worker compute budget, original scores,
opening/support rules and all robot checks unchanged. Ordinary profiles are not
changed. This is a deployment coverage correction through existing interfaces;
adding a new geometry Provider or changing AgentLoop would not repair the
observed truncation and is unnecessary for this step.

The production-composition regression first reproduced `64 != 70` with a
substituted model producing 70 distinct contacts. It also checks unmodified
geometry/score, capture-specific opaque references and no publication on failure.
The first diagnostic launcher failed because the model environment lacks host
Pydantic dependencies; it was corrected to use only the existing isolated worker
protocol, without installing packages or merging model/host environments.

## Retention-only validation / 仅修复截断的原生验证

Fresh task `task_b32f6dea14194fe8`, revision `revision_9384fad17c744f7d`,
workspace `out/lab-fullchain-truth-20261102-full-pool-no-motion-r1/` cancelled
with unavailable R03 task-affordance. R03 retained 389 / R04 326 / rod 16.
R03 had 21 aperture failures and 20 candidates × eight approach combinations:
144 final palm/table records and 16 final finger/table records. The latter are
the two recovered hypotheses; neither reaches IK or short-approach checking.
Motion stays disabled, with no controller outcomes. Increasing retention fixes
real information loss but does not supply a qualified grasp by itself.

中文：补回的两个候选仅通过手掌检查，完整夹指开合扫掠仍与桌面重叠。
这不是实际接触测量，也不能据此断言场景所有抓取都不可行；不降低安全裕量。

## Observed-region inference / 观测区域推理

The existing isolated GraspNet worker now optionally infers on the full cloud
plus at most three overlapping half-interval subsets of its PCA projection.
Subsets contain only points from the same capture; PCA is a sampling direction,
not a claimed bottle/rod axis. Tiny/degenerate clouds keep full-cloud inference.
Each region uses the existing sampling/rotation/inverse-transform path, with a
common full-cloud pivot and unchanged native scores, poses and jaw geometry.
An inference failure aborts the request; it never publishes partial success.

The lab profile uses `--input-region-count 3 --sampling-policy geometry_diverse`.
Default region count is zero for existing deployments. Four regions × four
rotations bounds this experiment to 16 inference passes, each at 12000 points;
the output remains capped at 512. Space/orientation/aperture diversity changes
which original predictions survive sampling, never the predictions themselves.
Original full-capture geometry remains authoritative for process qualification
and obstacle checks: a crop is not evidence that removed obstacles disappeared.

中文：修复属于 Grasp Provider 内的推理覆盖机制，调用方、公共契约与 AgentLoop
路由不变。工艺资格由 Task-Affordance Provider 判断，Isaac Adapter 负责开口、
最终夹爪、IK 与完整路径；Action 只能使用同一次候选集合内已合格的 opaque 引用。
不恢复被排除的原始集合，不改瓶口/支撑阈值，不硬编码位置。

Historical replay `out/lab-grasp-sampling-20261102-r3/sampling.json` produced
9855 thresholded native candidates and 512 sampled candidates. This is coverage
evidence only. Fresh qualification is recorded separately after completion.
The diagnostic saves configuration and exact worker source alongside the Git
revision, because an uncommitted worker cannot be reproduced from HEAD alone.

## Prompt expansion defect / 提示展开缺陷

Regional r1 stopped before task creation because the Agent used the Chinese
category description as an instance label. Rerun r2 explicitly used BEAKER.
It created `task_f40a8448debf4900` / `revision_6b6676c26d4a45d8`, retaining
508 R03, 506 R04 and 24 rod candidates. The task then failed before node
selection: prompt estimate 339858 + output reserve 8192 exceeded window 272000
after compaction. Full input binding arrays in the persisted PlanGraph were
copied into the task prompt, rather than presented through a bounded view.

Fix the existing non-authoritative prompt projections, not inference budgets
or AgentLoop routing: task, node and working-set views now summarize arrays
above the existing 64-item phase display bound, while retaining scalar values,
small arrays, semantic parameters and surrounding opaque references. The
Coordinator's complete PlanNode/NodeExecutionContext remains unchanged.
Qualification, selected source resolution and Tool materialization consume those
exact records, never the summaries. No new gate or public Tool schema is added.
Replaying the actual r2 record produces a 62099-character task projection.

中文：上下文溢出不是碰撞。两类问题分别修复：Provider 改善覆盖，现有提示投影
避免完整候选数组反复注入。不是减少候选，也不是扩大模型窗口；summary 明确标为
非权威，不能作为 Tool 参数。机器人与文档检索两类替代数据验证同一规则。

Fresh validation uses `out/lab-fullchain-truth-20261102-region-no-motion-r3/`.

## Final native result / 最终原生结果

Task `task_a87e6bb320964db7`, revision `revision_acc11d27415a4747`, session
`cli:lab-ff91b390d264`: all four R03 process/affordance Query and preparation
nodes completed. The 508 R03 retained grasps produce 108 process-qualified
probe requests: 41 aperture rejects, 60 unavailable approach receipts and
**seven distinct available combinations**. Their 536 orientation/backoff attempt
records comprise 472 final palm/table, eight final finger/table, 12 self-collision,
nine later route-collision, five IK failures and 30 available attempts. Attempt
counts are not unique candidate counts; the earlier intermediate 20 successes
were attempt records, not 20 candidates.

Preparation selected `grasp-affordance://8986e73849994e3db75ecaef78536dd7` and
returned exactly seven same-set `qualified_grasp_candidate_refs`; the selected
grasp ends in `11e8091d0c6945d499806490da71de8c-194`. These are diagnostic
identities, not production selectors. R04 retained 506 and rod 24 proposals,
but their process qualification did not run because the sequential first Action
was not completed. The task-affordance result proves current process plus final
gripper/short-approach feasibility, not a complete acquire/pour/return route.

The final task state is `awaiting_replan`; the long-horizon outcome is `blocked`
with `node_turn_incomplete:pour_r03:node_selection_no_progress`. All four Tool
execution records are Queries, `simulated_motion_enabled=false`, and no Action
or physical controller execution was recorded. `controller_outcomes` contains
the blocked long-horizon orchestration result, not a robot motion result.
Host exits 1 because the requested complete no-motion workflow did not finish.
The initial `agent_response` predates the later long-horizon progress and is not
the authoritative final state; use the final persisted task and outcome.

中文：已解决“候选覆盖丢失/不足”和“完整数组撑爆上下文”两个实际缺陷；R03
从零个可用组合变为七个。下一阻塞是只读验证流程到达 `manipulation.execute_subtask`
动作节点，尚未获得完整 acquire/process/return 路径证据，R04 与玻璃棒也未完成资格
验证。后续应通过现有或正式设计的 preparation Query 承载完整无动作准备，或在
授权动作流程内先完成全部 preparation；不能用短接近通过替代完整路径或提前报成功。
