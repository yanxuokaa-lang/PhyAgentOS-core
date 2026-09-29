# scene.observe oneOf 默认值污染与双视角证据诊断

日期：2026-09-30
任务：`task_1483983454c942e6`
Revision：`revision_5a00d1bef5aa448f`
会话：`/home/yanxu/.PhyAgentOS/workspace/sessions/cli_rgb-acceptance-20260930-2.jsonl`

## 结论

本轮并不是 Qwen 在收到同步双相机图像后错误绑定实体。同步双相机 `scene.observe` 从未成功到达 Runtime：Coordinator 在 `AgentTaskCoordinator.invoke_query` 中无条件物化实时 ToolSpec 的所有 property default，给显式 `sensor_refs` 请求额外注入了默认 `sensor_ref=camera/head`。Runtime 因此收到两个互斥字段并返回 `invalid_sensor_ref`。

唯一成功观测 `tool_87d6e88d15ec45ab` 来自空参数请求，经默认值展开后是单相机 `camera/head`，scene revision 为 `3a4eef5b2fb644b5bd09d8d407595c30-1`。后续 `scene.understand` 只能基于该单视角证据工作；跨视角身份与空间关系不确定是正确的 fail-closed 结果，不应通过 RGB 专用规则静默合并。

## 权威调用时序

1. `tool_62b87104519b4760`：Agent 提交 `sensor_refs=[camera/head,camera/front]`；Runtime 返回 `invalid_sensor_ref: provide exactly one of sensor_ref or sensor_refs`。
2. `tool_b5291859dac04085`：Agent 错误改为数组形式的 `sensor_ref`；Runtime 返回 `sensor_ref must be a non-empty string`。
3. `tool_08c9619cf4c14761`：再次提交 `sensor_refs`；仍因默认 `sensor_ref` 污染而失败。
4. `tool_87d6e88d15ec45ab`：提交空参数；Coordinator 物化默认单相机和 freshness 参数，观测成功，但只有 `head_camera`。
5. `scene.understand` 使用该单视角成功记录，不能证明双视角实体一致性。
6. `tool_534bcdff28f14dd4`：再次提交 `sensor_refs`；同一污染再次触发 `invalid_sensor_ref`。

## 具体失败场景与现有机制不足

- 失败场景：JSON Schema 通过 `oneOf` 声明 `sensor_ref` 与 `sensor_refs` 互斥，同时实时 ToolSpec 为单视角分支声明默认值。调用者显式选择多视角分支后，Coordinator 仍物化兄弟分支默认值。
- Git、版本号、主键、事务、唯一约束、类型和普通持久化均无法阻止该问题，因为每个组件单独看都合法，错误发生在跨层参数合成。
- 现有 Gateway 校验只能在记录已创建并发出请求后拒绝，导致多个无效 Query record、模型反复解释旧成功记录以及不必要的推理轮次。
- 若不修复，任何带默认判别字段的 `oneOf` Tool 都可能出现同类污染，不限于 RobotWin、RGB 或相机工具。

## 修复边界

- 在 Coordinator 的通用 Query 参数物化层识别调用者已显式选定的 `oneOf` 分支，跳过兄弟分支判别字段默认值。
- 非判别默认值继续物化；未显式选分支时仍可采用声明的默认分支。
- 在创建 execution record 和调用 Gateway 前验证最终参数，非法参数不落盘、不发送。
- 不修改 Qwen 的身份判断，不放宽 freshness、标定、身份、碰撞、IK、运动授权或 Gateway/Coordinator 门禁。
- 不增加 RGB、相机名称或 Tool ID 专用分支。

