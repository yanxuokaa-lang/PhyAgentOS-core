# 13 Semantic DAG
- Takeaway: 高层对象移动意图会被展开成有依赖关系的工具调用图。
- Script: Agent 给出对象移动子任务后，当前实现会编译出观测、能力检查、场景理解、抓取提议、准备、获取和放置等节点。各对象的移动完成后再汇合到 verify，避免把一句高层意图直接当成可执行动作。
- Evidence: AgentSubtaskSpec and compose_executable_pick_place_plan implementation.
- Question: 依赖和证据为什么要显式进入 DAG？

