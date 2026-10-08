# v12.9.13 Implementation Review / 实现审查

## Finding / 发现

本次问题的唯一 Major 根因是 Adapter 的 persistent place producer 在真实 route
完成后没有投影 `object.place` contract 要求的四项 postcondition。上层
`_ProjectedDriver` 因此按设计将结果降级为 `unknown` 并进入
`reconciliation_required`。未发现 Action 重试、重复放置或 Agent 自动 replan。

复审发现并修正一个 Minor contract 边界：`observation_ready` 现在要求
`new_scene_revision` 是非空字符串；新增不含 retreat 的 route 回归，确认不会
声明 `clear_of_target` 或 observation readiness。

## Seven dimensions / 七个维度

1. **架构 / Architecture：通过。** 字段在 `RoboTwinPersistentEngine` 的结果
   producer 边界生成，未修改 Core settlement、Gateway admission 或上层
   fail-closed 校验。
2. **正确性 / Correctness：通过。** `release_confirmed` 只在 release verification
   和完整 route 成功后发布；`retreat_completed` 与 `clear_of_target` 来自已执行
   的 retreat phase；`observation_ready` 依赖新 scene revision 和 action artifact
   即将物化，且要求 scene revision 是非空字符串。失败、取消、视频错误和不完整
   route 保持 false/unknown。
3. **恢复与幂等 / Recovery and idempotency：通过。** 没有自动重试、重复 Action、
   重新放置或隐式对账；真实未知结果仍由原有 reconciliation 处理。
4. **机器人安全 / Robotics safety：通过。** 没有放宽 route、release、clearance、
   collision、workspace、frame 或 calibration 检查；修改只投影已通过的执行事实，
   测试使用 no-motion substitute。
5. **扩展兼容 / Extensibility：通过。** 逻辑只依赖 provider-neutral phase names、
   scene revision 和 artifact boundary，不含 RGB、颜色、排列、benchmark、相机或
   固定机械臂分支；旧 failure projection 保持兼容。
6. **可观测性与可维护性 / Observability and maintainability：通过。** 四项字段
   同时写入 public result 与 action artifact；缺失字段的 runtime regression 保留
   `missing_place_postconditions`，诊断文档固定了真实 invocation 证据。
7. **AgentLoop 自主性与收敛 / AgentLoop autonomy and convergence：通过。** Agent
   仍依据权威终态决定下一步；producer 不自动观察、筛选、换臂、replan 或执行新
   Action。完整成功不会被误导进入对账，真正 unknown 仍停止在 reconciliation。

## Validation / 验证

- Adapter/Skill/AgentLoop focused suite: `59 passed`。
- 新增 no-video producer regression: passed；新增四项逐字段缺失 projection
  regression: passed。
- `ruff check`, `compileall`, `git diff --check`: passed。
- `test_persistent_task_video.py` 的 4 个媒体测试因当前环境未安装 `cv2` 失败，
  属于既有测试依赖缺失；没有把它们计入成功证据。
- 所有验证均未创建 AgentTask、调用 Gateway Query/Action、推进 simulator 或
  物理运动。

## Remaining risk / 剩余风险

需要在具备 `cv2` 的构建环境重新运行视频归档测试，并在停止旧 Runtime、安装新
Node 后进行只读 Tool/receipt 验收；在此之前不应对未知旧 invocation 重试。
