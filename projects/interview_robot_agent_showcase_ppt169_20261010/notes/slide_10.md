# 10 PAOS boundary
- Takeaway: Agent 经由 Forge Tool API 发起操作，完成状态由证据和验证器判断。
- Script: 在当前仓库里，Agent 生成 AgentTask 或 PlanRevision，再通过 ForgeToolClient 和 Gateway 调用工具。工具返回的执行记录、观测证据和最终 verdict 是不同事实，所以收到 Action accepted 不能直接当成任务完成。
- Evidence: README.md architecture and Unified Forge Tool API documentation.
- Question: 为什么要分开 execution、evidence 和 verdict？

