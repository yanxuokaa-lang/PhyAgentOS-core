# 14 Recovery
- Takeaway: 恢复会保留已完成事实，并把新的计划修订留在同一任务里。
- Script: 长程任务执行遇到阻塞时，控制器先依据节点状态和证据判断哪些工作还能继续。已完成节点不重复执行；结果未知的动作先暂停判断；需要调整时，在原 AgentTask 上追加 PlanRevision。
- Evidence: PhyAgentOS/agent/long_horizon.py and planning modules.
- Question: unknown Action 如何处理？

