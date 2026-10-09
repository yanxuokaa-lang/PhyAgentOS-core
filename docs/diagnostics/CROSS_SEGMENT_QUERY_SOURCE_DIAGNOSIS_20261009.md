# Cross-Segment Query Source Diagnosis / 跨段 Query 来源诊断

## Outcome / 结论

`task_73ef2b2d38eb4acb` completed the red acquire/place/checkpoint sequence and
then completed `green_grasp`. It stopped before `green_prepare` was materialized;
no green Action or new simulator motion was submitted.

`task_73ef2b2d38eb4acb` 已完成红块抓取、放置和检查点链，并完成
`green_grasp`。任务停止在 `green_prepare` 物化之前；没有提交绿色方块 Action，
也没有产生新的模拟器运动。

## Evidence / 证据

| Stage / 阶段 | Authoritative result / 权威结果 |
| --- | --- |
| Red preparation/acquire/place / 红块准备、抓取、放置 | Succeeded; acquire `invocation://object-acquire/25da88bdebed4308`, place `invocation://object-place/f1e0b2fe33ea4675` |
| Red checkpoint / 红块检查点 | Observe, capabilities, understand and bind all completed |
| Green candidates / 绿色候选 | `green_grasp` completed; record `tool_c8004c0034234a13`, 32 retained candidates |
| Green preparation / 绿色准备 | Continuation plan rejected before materialization; no provider query executed |
| Green/blue actions and final verification / 绿蓝动作与最终验收 | Not executed; whole task success is not established |

- Original blockage status: `waiting_for_user`, active revision
  `revision_c2f9020424754646`.
- Final database check: `failed`, `cancellation_requested=true`, terminal at
  2026-10-09 11:54:38 Asia/Shanghai. The latest event is `task_cancel_requested`.
  This external cancellation is subsequent to the source-contract blockage;
  this diagnosis/repair turn performed no cancellation or task mutation.
- Red revision `revision_2c9f2299c10546cc`: all eight nodes completed.
- Green revision: its only node, `green_grasp`, completed as
  `tool_c8004c0034234a13`; 1024 decoded, 128 canonicalized, 51 deduplicated and
  32 candidates retained.
- The first continuation proposal incorrectly supplied `destination_ref` in
  benchmark goal mode. Coordinator correctly rejected it because `task.goal`
  owns destination injection. Removing that field fixed this independent
  Agent-input error.
- The corrected `green_prepare` proposal failed with
  `projection_source_unreachable` before selection, provider invocation, IK,
  collision checking, or motion.

The `waiting_for_user` state was written after the Agent explicitly called the
clarification path to request a contract repair. It is not a new controller
qualification or manual motion approval requirement. The underlying rejection
belongs to Core Coordinator plan compilation, not the Runtime transport or
controller.

`waiting_for_user` 是 Agent 请求修复契约后走澄清路径写入的状态，不是新增控制器
资格审批或人工运动审批。拒绝发生在 Core Coordinator 计划编译边界，不是 Runtime
连接或控制器执行失败。

Source evidence: read-only task JSON in
`/home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3`, task-owned
action artifacts and video manifest, supplied continuation logs, and source
`agent/plan_proposal.py`, `agent/tools/forge_task.py`, `agent/planning_loop.py`.
Failed continuation proposals create no new PlanRevision; the supplied log and
persisted clarification retain their public rejection, while the repro test
demonstrates the exact pre-Gateway error path.

## Root Cause / 根因

The `manipulation.prepare` candidate slot declared `source_scope=predecessor`.
That requires a `grasp.propose` node among the new graph's direct dependencies.
However, continuation dependencies are intentionally graph-local, and the
completed `green_grasp` belongs to the preceding graph. Its persisted successful
record could be explicitly preserved as Coordinator evidence, but a predecessor-
only slot rejected evidence by definition. Repeating `grasp.propose` would violate
the Agent loop rule against repeating a completed current-scene Query.

`manipulation.prepare` 的候选槽原来声明为 `source_scope=predecessor`，因此要求
新图直接依赖一个 `grasp.propose` 节点。但 continuation 的依赖有意限制在新图内，
而已完成的 `green_grasp` 属于上一张图。Coordinator 可以显式保留该成功记录为
证据，但 predecessor-only 槽按定义拒绝 evidence；重复执行 Query 又违反 Agent loop
不得重复当前场景已完成 Query 的约束。

## Generic Repair / 通用修复

The candidate slot now uses the existing `authorized` source scope. It accepts
either a direct predecessor or an explicitly selected persisted Query. It does
not search history or trust Agent-authored payloads. Selection still requires:

- a task-bound successful record selected into the revision evidence context;
- exact producer Tool ID (`grasp.propose`);
- current scene, observation, frame and calibration identity;
- a unique candidate/entity join; and
- validation against the frozen `manipulation.prepare` input schema.

候选槽改用已有的 `authorized` 来源范围，可接受直接前驱或被显式选择的持久化
Query。它不会搜索历史记录，也不信任 Agent 手写 payload；任务归属、成功终态、
Tool ID、场景/观察/标定、实体唯一匹配和冻结 schema 校验全部保留。

This is provider-, object-, color-, count-, arm-, camera-, and benchmark-neutral.
It changes no Action authorization, retry policy, controller path, Runtime truth,
or final verification authority.

该修改与 provider、对象、颜色、数量、机械臂、相机和 benchmark 无关；不改变
Action 授权、重试策略、控制器路径、Runtime 事实权或最终验证权。

The AgentLoop continuation prompt also explains segmentation by declared source
scope. Strict predecessor producer/consumer chains remain in the same graph;
materialization does not execute an Action. This prevents shifting the same
dead end to the next preparation/acquisition or acquisition/placement boundary.

AgentLoop 续接提示同时说明按 ToolSpec 来源范围分段：严格 predecessor 的生产者和
消费者保留在同一张图；物化计划本身不执行 Action。这样避免修复候选复用之后，
又把相同死端移到准备/抓取或抓取/放置边界。

## Video Evidence / 视频证据

The task-owned cumulative red acquire/place recording is under
`task-video-d940db353002474cb491d84a58ba0258/cumulative/action-0002`.
Both head and observer videos are 320x240, 25 fps, 479 frames, 19.16 seconds.
The manifest owner is `paos:task_73ef2b2d38eb4acb` and lists the acquire and
place invocations as succeeded. There is no green Action video because no green
Action started.

- Head camera: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/5fabd9725dc948d198192f5c319ac9a9/task-video-d940db353002474cb491d84a58ba0258/cumulative/action-0002/video/head-camera.mp4`
- Observer camera: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/5fabd9725dc948d198192f5c319ac9a9/task-video-d940db353002474cb491d84a58ba0258/cumulative/action-0002/video/observer-camera.mp4`
- Manifest: `/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260926T0015/persistent/5fabd9725dc948d198192f5c319ac9a9/task-video-d940db353002474cb491d84a58ba0258/cumulative/action-0002/manifest.json`

The place artifact reports `status=succeeded`, `outcome_known=true`, release,
retreat, clear-of-target and observation-ready postconditions. Its placement
measurement is approximately 23.96 mm position error and 6.73 degrees
orientation error. These facts prove the red place Action terminal result, not
the complete multi-object user goal.
