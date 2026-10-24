# 原场景仿真验收上下文
- 用户要求严格分开视觉文字识别与动作执行；保存实际阶段及每个问题。身份必须来自实际图像，禁止用相机名称、固定场景位置或资产信息代替。标签、功能点、几何不合格即停止，不放宽检查。
- 2026-10-24 本轮：双视图（tabletop_third_person + label_inspection_r01）max_age_ms=1000、默认 max_capture_skew_ms=50 失败，capture_skew_exceeded。两个单视图随后均可采集并调用 scene.understand，但不替代同步成功。
- 工具从特写报告文字：R01    LAB REAGENT / 蒸馏水 / Distilled water / H2O / Simulation reagent。R02 未可靠读出；R01 瓶口、其他瓶口、烧杯口及搅拌棒工作端资格不足。未建立跨视图执行绑定。
- 实际停止在观测/理解与资格检查；未创建 manipulation AgentTask/semantic_subtasks，未执行动作。无全链路通过结论。详见 HISTORY.md，含每项 ambiguity 与观测摘要压缩导致的来源链审计限制。
- 待执行用户参数（不是已执行结果）：依次 R01、R02 向唯一目标烧杯 pour，各 tilt_rad=0.87 hold_s=0.6；随后实际识别搅拌棒 stir radius_m=0.009 depth_m=0.04 turns=2 duration_s=4 direction=ccw 并归位。合格后才 semantic_subtasks 与 Runtime，verification.mode=off。无液体/化学模型，仅可报告实测无液体操作，不能报告体积或混合质量。
