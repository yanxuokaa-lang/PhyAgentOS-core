# 11 PAOS tools
- Takeaway: Agent 调用的是有明确输入输出边界的感知与操作工具。
- Script: 例如先用 scene.observe 获取场景，再调用 scene.understand 和 grasp.propose，最后进入 object.acquire、object.place。Agent 看到的是工具能力与结果；底层 Runtime profile 可以更换实现，但调用边界保持一致。
- Evidence: pick-place-workflow skill.yaml and tool contracts.
- Question: Tool API 如何避免算法实现和任务逻辑耦合？

