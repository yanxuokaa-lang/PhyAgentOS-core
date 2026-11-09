# 04 Competition architecture
- Takeaway: 采集链路把机器人控制和图像落盘分开处理。
- Script: 多视角观测送入 pi0.5 微调流程；采集端以 60 Hz 控制机器人、15 Hz 记录图像，避免图像写盘拖慢遥操作。策略输出还会经过动作滤波，再进入控制链路。
- Evidence: 简历中的采样频率、约 200 条示范和滤波流程。
- Question: 为什么不直接执行策略动作？

