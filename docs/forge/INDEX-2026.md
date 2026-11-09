# docs/forge 2026 索引

| 文件 | 日期 | 标题 | 摘要 |
|---|---|---|---|
| ROBOTWIN_ADAPTER_REFACTOR_DIAGNOSIS.md | 2026-09-02 | RoboTwin Adapter Refactor Diagnosis | 诊断能力迁移：保留通用 ToolSpec 与 ToolEndpoint，RoboTwin 仅作可替换 Adapter。 |
| STATE_FILE_IMPLEMENTATION_REVIEW_20260903.md | 2026-09-03 | 状态文件适配实现审查与修复记录 | 审查状态文件与 Evidence 边界，修复 store 迁移、schema 校验与 prompt 注入等缺陷。 |
| FRANKA_READINESS_INPUT_AUDIT_20260904.md | 2026-09-04 | Franka `blocks_ranking_rgb` readiness 输入审计 | 审计 Franka readiness 输入：缺几何与抓取候选产物，现有 GraspGen 结果不可复用，判定不可运行。 |
| ROBOTWIN_CONTROLLER_QUALIFICATION_EXECUTION_PLAN.md | 2026-09-06 | RoboTwin/SAPIEN Controller Qualification 执行计划 | 制定控制器资格测试计划：与当前 checkout、runtime 和命令族绑定，允许失败结论且不授权真实运动。 |
| REAL_SPEED_LIMITS_ARCHITECTURE.md | 2026-09-06 | PAOS 真实速度限制架构：RoboTwin Franka 与硬件 Franka | 设计速度限制链路：限制须来自 SDK/控制器权威来源，否定自造全局速度常数与调参换资格。 |
| MULTI_OBJECT_AGENT_LOOP_EXECUTION_PLAN_20260909.md | 2026-09-09 | 多对象完整 Agent Loop 执行方案 | 制定多对象任务从分解到 Verifier 的执行方案，先关闭实体绑定、持物、unknown 结果等六项问题。 |
| MULTI_PICK_PLACE_DIRECTION_REVIEW_20260909.md | 2026-09-09 | 多物体接入方向复核与下一功能验收 | 复核确认自 v8.0.0 起多物体接入方向未偏离 PAOS，下一功能为真实 Tool context 状态传播。 |
| MULTI_PICK_PLACE_IMPLEMENTATION_STATUS_20260909.md | 2026-09-09 | 多次抓放修复状态 / Multi-pick-place repair status | 记录 v7.6.0 修复：失败保留效果事实、快照替换、unknown 结算等，多物体接入仍未交付。 |
| PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md | 2026-09-09 | Persistent multi-object integration: v7.7.0 checkpoint | v7.7.0 检查点：六维验收已修复项与剩余 Blocker 清单，持久执行语义确定，整体仍未通过验收。 |
| TASK_UNDERSTANDING_MULTI_PICK_PLACE_INTEGRATION_REVIEW_20260909.md | 2026-09-09 | 任务理解与多次抓放接入诊断及方案审核 | 保存模块接入诊断并分析多次抓放组成方式，推荐复用 AgentTask/PlanGraph 并列出接入缺口。 |
| TASK_UNDERSTANDING_MULTI_PICK_PLACE_SECOND_REVIEW_20260909.md | 2026-09-09 | 多次抓放接入方案：第二轮架构审核 | 第二轮审核不通过：语义 DAG 被强制改成逐 Tool 队列、持物占用与退出语义缺失等 Blocker。 |
| AGENT_LOOP_FOUNDATION_DIAGNOSIS_20260910.md | 2026-09-10 | Agent Loop 基础诊断与修复 / Foundation Diagnosis and Repair | 诊断未提交 runner 预填答案、按节点名派发、自设 Verifier 等问题，明确所有权并给出修复方向。 |
| EVOPHY_CLOSED_LOOP_REVIEW.md | 2026-09-11 | EvoPhy Closed-Loop Review | 评审 EvoPhy 学习闭环：机械可测但未证明物理任务自主改进，修正扩展晋升与多条失败路径。 |
| QWEN3_VL_LIFECYCLE_AGENT_LOOP_ACCEPTANCE_20260916.md | 2026-09-16 | Qwen3-VL lifecycle and AgentLoop acceptance | 验收 Qwen3-VL 生命周期：prepare 缺 intent 等三问题，仅 Query 验证无运动。 |
| OPEN_WORLD_SCENE_UNDERSTANDING_PLAN_20260918.md | 2026-09-18 | Open-World Scene Understanding Plan | 规划开放世界场景理解：在现有 Qwen3-VL provider 上补支撑与容器等语义，不升级模型不加硬件。 |
| IMPLEMENTATION_REVIEW_V10_9_0.md | 2026-09-20 | v10.9.0 需求复核、Fresh Code Review 与七维验收 | 七维验收 v10.9.0：上下文缩减、计时、视频持久化等通过 no-motion 审查，真实场景验收待部署。 |
| OBSERVED_CONTACT_DIAGNOSIS_V10_10_3.md | 2026-09-20 | v10.10.3 Sensor attribution and observed-point collision design | 设计观测点碰撞与传感器归因：以实测点替代整包络碰撞，并调研多个开源抓取管线的机制。 |
| DIAGNOSTIC_BENCHMARK_GOAL_BASELINE_V11_2_3.md | 2026-09-21 | Current Task Diagnostics and Benchmark-Goal Baseline | 记录实施前诊断：绑定与目标查询成功但无 prepare 记录，两次 selection 被拒后节点阻塞。 |
| IMPLEMENTATION_REVIEW_V11_3_6.md | 2026-09-21 | v11.3.6 Consumer Projection and Oracle Baseline Acceptance | 审查消费者投影与 Oracle 基线：源码测试通过，Oracle 运行中断，验收未完成。 |
| GRASPGEN_RGB_ACCEPTANCE.md | 2026-09-24 | GraspGen RGB acceptance — amended execution objective | 修订 RGB 验收目标：抓取必须来自当前分割点云的 GraspGen 推理，禁止 Oracle 模板与自动回退。 |
| IMPLEMENTATION_REVIEW_V11_7_11.md | 2026-09-25 | v11.7.11：RGB 规划失败与既有七维度审查 | 审查 v11.7.8-11：修复碰撞缓存、任务终结、读线程污染，接触深度致完整路线仍不可行。 |
| IMPLEMENTATION_REVIEW_V11_7_13.md | 2026-09-25 | v11.7.13 GraspNet deployment and RGB acceptance review | 审查 GraspNet 部署：新增专用 profile、按原生分排序截断候选、重建 Node 与 Skill 制品。 |
| IMPLEMENTATION_REVIEW_V11_7_15.md | 2026-09-25 | v11.7.14-v11.7.15 GraspNet integration review | 审查 GraspNet 集成：修复几何 schema 拒收、抓取轴与深度换算三个 Blocker 及 GPU 饥饿。 |
| IMPLEMENTATION_REVIEW_V11_8_0.md | 2026-09-25 | v11.8.0 GraspNet coverage and recovery evidence review | 审查覆盖与恢复证据：修复 provider 失败丢失场景标识，新增朝向多样性预算采样扩大候选覆盖。 |
| IMPLEMENTATION_REVIEW_V11_9_1.md | 2026-09-26 | v11.9.1 Planning settlement and GraspNet coverage review | 修复语义标签与 opaque 证据的结算比较错误，GraspNet 采样预算扩至 128/32。 |
| IMPLEMENTATION_REVIEW_V11_9_3.md | 2026-09-26 | v11.9.3 Grounding bind idempotency review | 修复重复 scene.bind 产生等价绑定被误判歧义：同身份同实体集复用现有绑定。 |
| IMPLEMENTATION_REVIEW_V11_9_4.md | 2026-09-26 | v11.9.4 Grasp fact and exact scene-binding review | 发布抓取候选留存条件事实，prepare 经冻结 binding_ref 精确解析目标而非全扫描绑定。 |
| IMPLEMENTATION_REVIEW_V12_1_0.md | 2026-09-29 | v12.1.0 Settlement Reconciliation and Place Postcondition Review | 修复 unknown 终态无法被后续结果解析、place 成功证据不足定义、过期投影推进等问题。 |
| IMPLEMENTATION_REVIEW_V12_3_0.md | 2026-09-29 | PAOS v12.3.0 Multi-View and Possession-Aware Scene-State Implementation Review | 审查多视角与持物场景状态：修复多相机 artifact 拍平、Agent 伪造 carry-forward 等缺陷。 |
| MULTIVIEW_POSSESSION_SCENE_STATE_DIAGNOSIS_20260929.md | 2026-09-29 | PAOS Multi-View, Possession, and Scene-State Diagnosis | 诊断单视角观察与过粗场景失效：成功抓取后全量作废旧实体，提出双视角与差量失效方案。 |
| MULTIVIEW_SEMANTIC_BINDING_DIAGNOSIS_20260929.md | 2026-09-29 | 同步多视角语义与 scene.bind 选择诊断 | 诊断双相机采集正确但 Qwen 输出空身份歧义、Agent 误选环境表面，属三层契约缺口。 |
| IMPLEMENTATION_REVIEW_V12_3_1.md | 2026-09-30 | v12.3.1 Seven-Dimension Implementation Review | 审查多视角理解部署与 Qwen vLLM 兼容：修复计时日志不可见与 worker 终态清理归属。 |
| IMPLEMENTATION_REVIEW_V12_3_4.md | 2026-09-30 | v12.3.4 Seven-Dimension Implementation Review | 审查多视角理解与绑定集成：无 Blocker/Major，遗留冷启动延迟等 Minor，歧义证据仍被拒绝。 |
| IMPLEMENTATION_REVIEW_V12_3_5.md | 2026-09-30 | v12.3.5 Seven-Dimension Implementation Review | 审查 discovery 前缀裁剪：仅裁剪当前 revision 已成功 Query 的连续前缀，七维全部通过。 |
| IMPLEMENTATION_REVIEW_V12_3_6.md | 2026-09-30 | v12.3.6 Seven-Dimension Implementation Review | 审查 Runtime 启动边界并验证 v12.3.5 修复加载：无 Blocker/Major，物理验收未执行。 |
| IMPLEMENTATION_REVIEW_V12_4_1.md | 2026-09-30 | Implementation Review v12.4.1 — Explicit AgentTask Runtime Rebind | 审查显式 Runtime 重绑定：Coordinator 拥有迁移，需 Skill 激活与授权 ID。 |
| IMPLEMENTATION_REVIEW_V12_4_2.md | 2026-09-30 | Implementation Review v12.4.2 — AgentLoop Rebind Projection | 审查 rebind 工具投影：默认隐藏、澄清授权后可见，动作进行中保持隐藏，七维 PASS。 |
| IMPLEMENTATION_REVIEW_V12_4_3.md | 2026-09-30 | Implementation Review v12.4.3 | 复审 rebind 一次性授权消费与全新 discovery 链：控制面 PASS，RGB 端到端验收未完成。 |
| IMPLEMENTATION_REVIEW_V12_5_0.md | 2026-09-30 | v12.5.0 Multi-source prepare projection implementation review | 审查多来源 prepare 投影：命名 source slots 独立授权抓取与能力证据两个输入。 |
| RGB_ACCEPTANCE_RUN1_AGENTLOOP_DIAGNOSIS_20260930.md | 2026-09-30 | RGB Acceptance Run 1 AgentLoop Diagnosis | 诊断 Run1：discovery 成功后 PlanGraph 物化被拒，缺已满足前缀投影，无任何物理动作。 |
| RGB_ACCEPTANCE_RUN2_AGENTLOOP_DIAGNOSIS_20260930.md | 2026-09-30 | RGB Acceptance Run 2 AgentLoop Diagnosis (2026-09-30) | 诊断 Run2 四个根因：sensor 未枚举、重复观察、selection 未消费、bind 丢字段。 |
| RGB_ACCEPTANCE_RUN3_RUNTIME_REBIND_DIAGNOSIS_20260930.md | 2026-09-30 | RGB Acceptance Run 3 Runtime Rebind Diagnosis (2026-09-30) | 诊断 Run3 rebind 被拒：任务冻结绑定与替换 Runtime 冲突，要求显式 rebind 迁移而非放宽校验。 |
| RGB_ACCEPTANCE_RUN3_STAGING_DIAGNOSIS_20260930.md | 2026-09-30 | RGB Acceptance Run 3 Staging Diagnosis (2026-09-30) | 诊断 Run3 目的地占用死锁：需 Runtime 拥有的只读 staging 查询通用化解暂存放置。 |
| RGB_ACCEPTANCE_RUN3_STAGING_IMPLEMENTATION_REVIEW_20260930.md | 2026-09-30 | RGB Acceptance Run 3 — Provider-neutral Staging Seven-dimension Review | 七维评审 provider-neutral staging 实现：全部 PASS，与保存诊断及 PAOS 所有权一致。 |
| RGB_ACCEPTANCE_RUN4_REBIND_AUTHORIZATION_CONSUMPTION_DIAGNOSIS_20260930.md | 2026-09-30 | Run 4 Runtime Rebind Authorization Consumption Diagnosis | 诊断 Run4：rebind 成功但澄清授权未一次性消费，要求同一迁移中消费并隐藏 rebind 工具。 |
| RUNTIME_LAUNCH_DIAGNOSIS_V12_3_6.md | 2026-09-30 | Runtime Launch Diagnosis v12.3.6 | 诊断启动失败：绕过 RuntimeManager 直接 dora start 致环境占位符未展开，正式入口正常。 |
| SCENE_OBSERVE_ONEOF_DIAGNOSIS_20260930.md | 2026-09-30 | scene.observe oneOf 默认值污染与双视角证据诊断 | 诊断 oneOf 默认值污染：默认 sensor_ref 使双相机请求反复失败，空参数仅得单相机观测。 |
| JEV_P3B_CALIBRATION.md | 2026-10 | P3b 真实日志抽象校准 / Real-record calibration | 校准真实日志抽象：38 条事实归并 5 个抽象题，属开发数据重构，不构成 active 验收。 |
| AGENTLOOP_DIAGNOSIS_CONTINUATION_CONVERGENCE_20261002.md | 2026-10-02 | AgentLoop Diagnosis: Continuation and Recovery Convergence | 诊断 continuation 收敛失败：只读查询后误入观察链、模型中断造成 Coordinator 与控制器状态分歧。 |
| AGENTLOOP_DIAGNOSIS_ENTITY_PROJECTION_20261002.md | 2026-10-02 | AgentLoop Diagnosis: Canonical Entity Projection | 诊断规范实体投影：observed 与 execution 身份 join 失败，规范化未在每个物化入口强制。 |
| AGENTLOOP_DIAGNOSIS_RECOVERY_PRIORITY_20261002.md | 2026-10-02 | AgentLoop recovery priority diagnosis — v12.5.13 | 诊断三项恢复缺陷：循环内 selection 未消费、wrapper 错误覆盖成功终态、单节点别名未解析。 |
| DISCOVERY_CONTRACT_DIAGNOSIS_20261003.md | 2026-10-03 | Discovery contract availability diagnosis / 发现阶段契约可用性诊断 | 诊断工具契约消失：计数混淆请求与回执并隐藏读取入口，复用任务读取工具按需恢复指令。 |
| DISCOVERY_PROGRESS_DIAGNOSIS_20261003.md | 2026-10-03 | Discovery progress and status diagnosis / 发现阶段进展与状态诊断 | 诊断 discovery 空转：循环只计工具轮次不计数事实变化，改按首次成功获取计数并设预算。 |
| MULTIVIEW_PREPARATION_LINEAGE_DIAGNOSIS_20261004.md | 2026-10-04 | Multi-view Preparation Lineage Diagnosis / 双视角 Preparation 血缘诊断 | 诊断双视角 prepare 血缘：观察理解成功但 prepare 因观测碰撞证据缺失在 Runtime 查询失败。 |
| REPLAN_PROJECTION_CONVERGENCE_DIAGNOSIS_20261004.md | 2026-10-04 | Replan Projection and AgentLoop Convergence Diagnosis / Replan Projection 与 AgentLoop 收敛诊断 | 诊断 replan 投影不可达：保留节点集合与替换图不一致，投影源缺失且各轮无新事实。 |
| ACTION_FAILURE_EVIDENCE_AGENTLOOP_DIAGNOSIS_20261006.md | 2026-10-06 | Action Failure Evidence and AgentLoop Diagnosis / Action 失败证据与 AgentLoop 诊断 | 诊断 Action 失败证据被压缩：零步却声明实体变化，AgentLoop 缺结构化事实无法决策。 |
| PREPARATION_FAILURE_RECOVERY_CONTRACT_DIAGNOSIS_20261006.md | 2026-10-06 | Preparation Failure Recovery Contract Diagnosis | 诊断 prepare 失败恢复契约：Runtime 配置故障被默认可重试，应区分 provider 故障与证据刷新。 |
| PREPARE_ACTION_ROUTE_PLAN_DIAGNOSIS_20261006.md | 2026-10-06 | Prepare/Action Route-Plan Consistency Diagnosis / Prepare/Action 路线计划一致性诊断 | 诊断 prepare 通过但 acquire 重规划失败：Readiness 应持久化执行计划供 Action 消费。 |
| PREPARED_PLAN_DYNAMIC_WORLD_DIAGNOSIS_20261006.md | 2026-10-06 | Prepared Plan Dynamic-World Binding Diagnosis / Prepared Plan 动态规划世界绑定诊断 | 修复 Readiness 与 Persistent Action 间动态世界绑定缺失：持久化双臂状态并在步进前拒绝漂移。 |
| PREPARED_PLAN_INTEGRATION_REGRESSION_DIAGNOSIS_20261006.md | 2026-10-06 | Prepared Plan Integration Regression Diagnosis / Prepared Plan 集成回归诊断 | 诊断回归缺陷：测试仅内部注入 prepared plan，需覆盖 Readiness 到 Action 全链路。 |
| REPLAN_EFFECTIVE_DELTA_CONTRACT_DIAGNOSIS_20261006.md | 2026-10-06 | Replan Effective Delta Contract Diagnosis / Replan Effective Delta 契约诊断 | 诊断 replan 增量契约冲突：可保留集合与实际保留集合混淆，需按替换图对账并 fail-closed。 |
| REPLAN_PRESERVE_EVENT_DIAGNOSIS_20261006.md | 2026-10-06 | Replan Preserve Event Diagnosis / Replan Preserve 事件诊断 | 固定 replan 控制面事实：prepare 因无合格接触失败，拒因含支撑穿透与遮挡样本。 |
| RUNTIME_PROFILE_CONSUMER_DRIFT_DIAGNOSIS_20261006.md | 2026-10-06 | Runtime Profile Consumer Drift Diagnosis | 诊断 red_prepare 反复路线物化失败：基于持久化事实定位 profile 消费漂移。 |
| ACTION_NODE_AGENTLOOP_CONVERGENCE_DIAGNOSIS_20261007.md | 2026-10-07 | Action Node AgentLoop Convergence Diagnosis / Action 节点 AgentLoop 收敛诊断 | 区分循环收敛与 selection 配方缺失：要求 ToolSpec 声明投影槽位，Agent 受治理提交选择。 |
| ACTION_SELECTION_PROJECTION_DIAGNOSIS_20261007.md | 2026-10-07 | Action Selection Projection Diagnosis / Action 选择投影诊断 | 诊断 acquire 缺参数投影声明：十二个输入需手工映射，需支持唯一匹配展开。 |
| CAPABILITY_BOUND_ADMISSION_DIAGNOSIS_20261007.md | 2026-10-07 | Capability-Bound Admission Diagnosis / Capability 限位准入诊断 | 诊断限位准入：接触段样本超关节上限约 5e-9 rad 被拒，界定无运动准备与 Runtime 准入边界。 |
| CONTROLLER_SOURCE_QUALIFICATION_DEPLOYMENT_DIAGNOSIS_20261007.md | 2026-10-07 | Controller Source Qualification Deployment Diagnosis | 关闭控制器源摘要漂移的部署侧：新 Node 不重建资格证据即启动失败，属有意 fail-closed。 |
| OUTCOME_UNKNOWN_RECONCILIATION_DIAGNOSIS_20261007.md | 2026-10-07 | Outcome-Unknown Reconciliation Diagnosis / 未知结果对账诊断 | 诊断 outcome_unknown 生命周期：Agent 正确不重试不推进，界定对账所有权与恢复路径。 |
| PREPARATION_ARTIFACT_IDENTITY_DIAGNOSIS_20261007.md | 2026-10-07 | Preparation Artifact Identity Diagnosis | 诊断准备产物身份冲突：32 条路线物化成功后仍报与 runtime 证据冲突，零动作失败。 |
| PREPARATION_PROVIDER_ERROR_OBSERVABILITY_DIAGNOSIS_20261007.md | 2026-10-07 | Preparation Provider Error Observability Diagnosis | 诊断 provider 错误可观测性：私有记录具体异常而公开结果只剩笼统错误码，需结构化投影。 |
| IMPLEMENTATION_REVIEW_V12_9_6.md | 2026-10-07 | v12.9.6 Seven-Dimension Implementation Review | 审查控制器源摘要漂移修复：共享运动策略准入统一校验能力与资格证据，含正确性修复。 |
| IMPLEMENTATION_REVIEW_V12_9_8.md | 2026-10-07 | Implementation Review v12.9.8 | 审查 preparation_provider_error 修复：能力别名归属澄清与类型化投影，均为 Minor。 |
| IMPLEMENTATION_REVIEW_V12_9_9.md | 2026-10-07 | Implementation Review v12.9.9 | 审查 v12.9.9：资格计划契约升级 v2 强制资格 ID 派生引用，修复别名助手接受不安全身份。 |
| DISCOVERY_STALE_LINEAGE_CONVERGENCE_DIAGNOSIS_20261008.md | 2026-10-08 | Discovery Stale-Lineage Convergence Diagnosis / Discovery 过期血缘收敛诊断 | 诊断未知结果后 discovery 重复提交动作前 bind：ready=true 不代表血缘新鲜，需结构化指纹。 |
| PERSISTENT_ACTION_RECEIPT_TRANSPORT_DIAGNOSIS_20261008.md | 2026-10-08 | Persistent Action Receipt Transport Diagnosis / 持久化 Action Receipt 传输诊断 | 诊断回执传输中断：1.88MB artifact 超过行字节上限致 worker 中断，成功结果无法结算。 |
| PLACE_POSTCONDITION_PROJECTION_DIAGNOSIS_20261008.md | 2026-10-08 | Place Postcondition Projection Diagnosis / 放置后置条件投影诊断 | 诊断 place 投影缺口：底层成功但缺公共契约四字段，被 fail-closed 降级 unknown 要求对账。 |
| PLANNING_ARGUMENT_CANONICALIZATION_DIAGNOSIS_20261008.md | 2026-10-08 | Planning Argument Canonicalization Diagnosis / Planning 参数规范化诊断 | 诊断参数规范化：selection 与执行阶段 JSON 表示不一致触发绑定校验失败，请求未达 Gateway。 |
| PREPARATION_CAPABILITY_LINEAGE_DIAGNOSIS_20261008.md | 2026-10-08 | Preparation Capability Lineage Diagnosis / Preparation 能力血缘诊断 | 诊断能力血缘：子级再物化生成不同 arm_profiles 与父级 selector 不一致而 fail-closed。 |
| SCENE_BIND_SELECTION_CONSUMPTION_DIAGNOSIS_20261008.md | 2026-10-08 | Scene Bind Selection Consumption Diagnosis / Scene Bind Selection 消费诊断 | 诊断 selection 消费顺序：空参数被误判缺 entity_refs，Query 未达 Gateway。 |
| SCENE_BIND_STALE_LINEAGE_DIAGNOSIS_20261008.md | 2026-10-08 | Scene Bind Stale-Lineage Diagnosis / Scene Bind 过期血缘诊断 | 诊断过期血缘：两次绑定引用动作前 revision 被正确拒绝，但 Core 边界丢失血缘值。 |
| SCENE_UNDERSTANDING_PROVIDER_FAILURE_DIAGNOSIS_20261008.md | 2026-10-08 | Scene Understanding Provider Failure Diagnosis / 场景理解 Provider 失败诊断 | 诊断理解 provider 失败：HTTP 200 但 9.1 秒后记录错误，公开投影丢失结构化细节。 |
| DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md | 2026-10-09 | Decisions API：会话入口意图与路由的独立能力验证方案 | 制定独立验证方案：80 条合成样本与 runner，仅评估预测，不接入现有入口链路。 |
| DECISIONS_INTENT_ROUTING_DIAGNOSIS_20261009.md | 2026-10-09 | Decisions API：PAOS 会话入口意图识别与路由诊断 | 诊断入口意图与路由：System 1 优先做会话入口意图识别与路径选择，区分意图与状态依赖路由。 |
| GPT6_LUNA_DECISIONS_PAOS_FIT_ANALYSIS_20261009.md | 2026-10-09 | GPT-6 Luna Decisions API：PAOS 架构适配与替换分析 | 分析 Decisions 适配点：首选恢复三选一替换与 Lesson 排序，均为设计建议尚无实测。 |
| HELD_ENTITY_PROJECTION_DIAGNOSIS_20261009.md | 2026-10-09 | Held entity projection diagnosis / 持有实体投影诊断 | 诊断持有实体投影：抓取与观察成功但绑定节点无 selection 停止，不得追溯改写成功终态。 |
| IMPLEMENTATION_REVIEW_V13_0_4.md | 2026-10-09 | Implementation Review v13.0.4：Decisions 入口意图与路由验证方案 | 审查验证方案设计：修复输入不统一与标签泄漏、两题一致性等 Major，实验未运行。 |
| IMPLEMENTATION_REVIEW_V13_0_6.md | 2026-10-09 | Implementation Review v13.0.6：Decisions 能力验证方案复审 | 复审验证方案：修复状态条件不一致、协议边界与 endpoint 选择，仅验收设计与静态契约。 |
| QUERY_PROVIDER_BLOCK_RECOVERY_DIAGNOSIS_20261009.md | 2026-10-09 | Query Provider Block Recovery Diagnosis (2026-10-09) | 诊断放置后理解 Query 失败：传输成功但语义无效，需区分 provider 失败与传输状态。 |
| SYSTEM1_INTENT_ROUTING_COMPARATIVE_EXPERIMENT_REPORT_20261009.md | 2026-10-09 | System 1 入口意图与路由对比实验报告 | 对比 Laya 与 Jev：Jev 正确率 0.944 但超时致端到端 0.850，Laya 零样本不适合替换路由。 |
| SYSTEM1_INTENT_ROUTING_EXPERIMENT_RESULTS_20261009.md | 2026-10-09 | System 1 入口意图与路由能力实验结果 | 记录实验配置与对象：三类 backend、数据集投影与环境核验，GPT-6 因 404 未执行。 |
| SYSTEM1_SYSTEM2_DECISIONS_DIAGNOSIS_20261009.md | 2026-10-09 | PAOS：System 2 / System 1 分工诊断 | 诊断认知分工：LLM 负责复杂理解与计划，Decisions 承担有限候选内的局部判断与排序。 |
| UNKNOWN_ACTION_REPLAN_DIAGNOSIS_20261009.md | 2026-10-09 | Unknown Action Recovery Diagnosis / 未知 Action 恢复诊断 | 诊断未知 Action 恢复：lift 相位 unknown、世界已变化且持物不确定，禁止推断或重试。 |
| UNKNOWN_ACTION_REFRESH_BOOTSTRAP_DIAGNOSIS_20261009.md | 2026-10-09 | Unknown World-Change Refresh Bootstrap Diagnosis | 诊断未知世界变化恢复：正确路径是追加仅含场景刷新 Query 的 revision，再正常续跑。 |
| PREPARATION_NODE_DEPLOYMENT_DIAGNOSIS_20261010.md | 2026-10-10 | Preparation Node Deployment Diagnosis (2026-10-10) | 诊断部署漂移：修复已在源码但锁定的 Runtime 制品未更新，需重建部署而非仅改源码。 |
| PREPARATION_REFERENCE_COLLISION_DIAGNOSIS_20261010.md | 2026-10-10 | Preparation Reference Collision Diagnosis - 2026-10-10 | 诊断准备引用冲突：按场景与帧生成 preparation_ref 致索引冲突，改用 Coordinator 校验的身份。 |
| PREPARATION_SUPPORT_AMBIGUITY_DIAGNOSIS_20261010.md | 2026-10-10 | Preparation Support Ambiguity Diagnosis (2026-10-10) | 诊断支撑歧义：prepare 0.03 秒即报观测支撑面含糊，修复几何解析与可重规划恢复迁移。 |
| QUERY_PROVIDER_READY_CONTEXT_FAILURE_DIAGNOSIS_20261010.md | 2026-10-10 | Query Provider Failure with Ready Runtime Context (2026-10-10) | 诊断 provider 失败但上下文 ready：被误分类为等待 Runtime，造成不收敛轮询。 |
| SCENE_BIND_SELECTION_CONVERGENCE_DIAGNOSIS_20261010.md | 2026-10-10 | Scene Bind Selection Convergence Diagnosis / scene.bind 选择收敛诊断 | 诊断 bind 选择无进展：Agent 只读上下文未产生事实，需区分任务身份与环境几何证据。 |
| UNKNOWN_WORLD_RECONCILIATION_DIAGNOSIS_20261010.md | 2026-10-10 | Unknown World Reconciliation Diagnosis / 未知世界对账诊断 | 诊断三个任务在不确定动作后复用旧场景：需结构化对账与新鲜血缘，而非回退模型。 |
| UNKNOWN_ACQUIRE_GROUNDING_RECONCILIATION_DIAGNOSIS_20261011.md | 2026-10-11 | Unknown Acquire Grounding Reconciliation Diagnosis / 未知抓取 Grounding 对账诊断 | 诊断未知抓取后对账：bind 因 holding_state 期望不符拒绝，需先对账持物状态再绑定。 |
| AGENT_MODEL_PROVIDER_NODE_RECOVERY_DIAGNOSIS_20261012.md | 2026-10-12 | Agent 模型 Provider 节点恢复诊断 / Agent Model Provider Node Recovery Diagnosis | 诊断模型回合 pre-Tool 失败：新增等待恢复生命周期，而非转移恢复所有权。 |
| FROZEN_QUERY_SELECTION_NO_PROGRESS_DIAGNOSIS_20261012.md | 2026-10-12 | Frozen Query Selection No-Progress Diagnosis | 诊断冻结 Query 无进展：参数已完整冻结但校正轮未持久化 selection 而超时停止。 |
| PLACEMENT_POSTCONDITION_ENTITY_SELECTION_DIAGNOSIS_20261012.md | 2026-10-12 | Placement Postcondition and Semantic Join Selection Diagnosis | 诊断两类独立失败：放置朝向超差被压成 unknown，消费者投影漏选 grasp 记录。 |
| SCENE_UNDERSTANDING_ENRICHMENT_HANDOFF_DIAGNOSIS_20261012.md | 2026-10-12 | Scene-understanding enrichment handoff diagnosis / 场景理解 enrichment handoff 诊断 | 诊断 enrichment 失败传导：GPT 后备成功但 worker 失败被整体结算为不可重试。 |
| SCENE_UNDERSTANDING_PROVIDER_FAILURE_DIAGNOSIS_20261012.md | 2026-10-12 | Scene Understanding Provider Failure Diagnosis (2026-10-12) | 诊断 provider 链失败：主备路由对同一场景连续三次失败且标记不可重试，含失败时间表。 |
| CONTINUATION_CONTEXT_SKILL_COMPACTION_DIAGNOSIS_20261013.md | 2026-10-13 | Continuation Context and Skill Compaction Diagnosis (2026-10-13) | 诊断 continuation 工作集未重建：持久事实齐全但投影缺陷致模型声称缺失并重复读取。 |
| REFRESHED_SCENE_BIND_SELECTION_DIAGNOSIS_20261013.md | 2026-10-13 | Refreshed-scene binding selection diagnosis (2026-10-13) | 诊断证据刷新后 bind 未被调用：需区分必须选择的任务身份与留作证据的环境几何。 |
| UNKNOWN_ACTION_POSSESSION_RECONCILIATION_DIAGNOSIS_20261013.md | 2026-10-13 | Unknown Action 后的 possession 与身份对账诊断 | 诊断未知动作后对账：旧视觉身份与几何不可复用，稳定执行身份与原始 invocation 可延续。 |
| CURRENT_SUPPORT_BIND_DIAGNOSIS_20261014.md | 2026-10-14 | `current_support_bind` 阻塞诊断 | 诊断 current_support_bind 阻塞：e4-e8 是未解析支撑候选而非五个对象，不能全部提交绑定。 |
| JEV_AGENT_LOOP_REFACTOR_DIAGNOSIS_20261014.md | 2026-10-14 | JEV 参与 PAOS Agent Loop 的重构诊断与实施设计 | 设计 JEV 为同一 Loop 内可选局部决策能力，目标是降低每节点生成式调用与等待。 |
| JEV_IMPLEMENTATION_HANDOFF_20261014.md | 2026-10-14 | JEV Agent Loop 重构：七维修订与编码模型实施工单 | 面向编码模型的实施工单：P0-P4 分批接口与验收，程序/JEV/LLM 三层边界不更换运行期模型。 |
| JEV_RECENT_RUNS_DIAGNOSIS_20261014.md | 2026-10-14 | 最近十次 PAOS 运行的 JEV 替代边界与 Agent Loop 重构诊断 | 分析十次运行：selection 全为单 Tool 候选，先补输入投影与常规片段再接 JEV。 |
| EMBODIED_SYSTEM1_DATASET_AND_MODEL_DIAGNOSIS_20261015.md | 2026-10-15 | 面向模糊人类指令的具身 System 1：数据集与决策模型诊断 | 诊断具身 System 1 数据集与模型：实测 80 条数据去重统计，指出覆盖与可见性缺口。 |
| JEV_HELD_OUT_INTAKE_20261015.md | 2026-10-15 | JEV 专项留出候选入库 / Held-out Candidate Intake | 预登记留出候选入库：RoboTwin 瓶类两场景采集计划、六类覆盖边界与防挑选规则。 |
| LAB_POUR_STIR_DIAGNOSIS_20261015.md | 2026-10-15 | 多试剂倾倒与手持棒搅拌：场景升级诊断 | 诊断场景升级：复用现有链路新增 object.pour 与 tool.stir，重点在持物后的执行与验证链。 |
| LAB_POUR_STIR_FEASIBILITY_REVIEW_20261015.md | 2026-10-15 | 多试剂倾倒与手持棒搅拌：可行性自审 | 自审诊断与计划：列出 11 项发现与修订，Blocker 集中于持物阶段与真实资产可操作性。 |
| LAB_POUR_STIR_IMPLEMENTATION_PLAN_20261015.md | 2026-10-15 | 多试剂倾倒与手持棒搅拌：实施计划 | 制定实施计划：无液体首版与可配置场景，三接口有工作区实现但未接真实执行器。 |
| LAB_SCENE_ASSET_REVIEW_20261015.md | 2026-10-15 | 实验室场景构建与真实资产来源复审 | 复审资产来源：推荐从 LabUtopia 提取真实网格转换装配，程序化圆筒方案被用户否定。 |
| ROBOTWIN_MULTI_TASK_MANIPULATION_PLAN_20261015.md | 2026-10-15 | RoboTwin 多任务通用操作方案 | 制定三任务通用操作方案：一套 provider-neutral 流程，任务差异由目标关系与后置条件表达。 |
| VLM_SYSTEM1_VPP2_BRIDGE_DIAGNOSIS_20261015.md | 2026-10-15 | VLM—System 1—VPP2：执行前与执行中的桥接决策诊断 | 诊断 VLM 与 VPP2 间 System 1 桥接：适合研究指令失配拦截与状态感知决策，需对照实验。 |
| VLM_SYSTEM1_VPP2_BRIDGE_INNOVATION_DIRECTION_20261015.md | 2026-10-15 | 独立创新方向：VLM 与 VPP2 之间的 System 1 桥接决策模型 | 提出目标忠实、状态感知的桥接研究方向：定义五类失配场景与待实验检验的假设。 |
| COMPOSITE_POUR_STIR_DIAGNOSIS_20261018.md | 2026-10-18 | 倾倒与搅拌完整操作：PAOS 架构诊断与修订方案 | 修订操作粒度：一个完整操作对应一个 PlanNode/Action/invocation，内部保留多阶段事实。 |
| COMPOSITE_POUR_STIR_REVIEW_20261018.md | 2026-10-18 | 倾倒与搅拌复合 Action：设计自审 | 自审复合 Action 设计：记录 3 Blocker、5 Major 等发现与对应实施验收条件。 |
| IMPLEMENTATION_REVIEW_V14_12_16.md | 2026-10-20 | Implementation Review v14.12.16 / 七维实现审查 | 七维审查 manipulation target 与 LabUtopia adapter：no-motion 边界通过。 |
| IMPLEMENTATION_REVIEW_V15_1_7.md | 2026-10-20 | Implementation Review v15.1.7: Runtime-Bound Preparation Query | 审查 Runtime 绑定准备 Query：遗留 Major，子任务刷新缺 Coordinator intent。 |
| IMPLEMENTATION_REVIEW_V15_1_9.md | 2026-10-20 | Implementation Review v15.1.9: Coordinator-Owned Subtask Context | 审查子任务上下文：身份传递闭合但 assignment 仍先于子任务选择产生，live 保持禁用。 |
| IMPLEMENTATION_REVIEW_V15_1_10.md | 2026-10-20 | Implementation Review v15.1.10: Subtask Intent Wiring Audit | 审计 intent 接线：持久化 intent 尚无法被子任务 Action 消费，需协调式契约修改。 |
| IMPLEMENTATION_REVIEW_V15_1_11.md | 2026-10-20 | Implementation Review v15.1.11: Persisted Subtask Intent | 审查持久化子任务 intent：PlanNode 拥有语义 intent，经既有 builder 物化并校验血缘。 |
| LABUTOPIA_PAOS_SUBTASK_REVIEW_20261020.md | 2026-10-20 | LabUtopia/PAOS 子任务结算方案复核 | 复核子任务结算方案：cycle 工具吞掉既有边界，修正为子任务内多 Tool、一次结算。 |
| labutopia-paos-generalization-diagnosis-20261020.md | 2026-10-20 | LabUtopia PAOS Generalization Diagnosis | 诊断 pour/stir 完整 cycle 泛化性：候选抓取位姿未被消费、放置基于复位坐标两个 Blocker。 |
| labutopia-paos-review-v14-12-14.md | 2026-10-20 | LabUtopia `pour` / `stir` PAOS Review and Repair | 审查修复 pour/stir：pour live 通过，stir 尖端轨迹证据与反馈口径按 PAOS 重算修复。 |
| IMPLEMENTATION_REVIEW_V15_1_12.md | 2026-10-21 | Implementation Review v15.1.12: Task-Scoped Preparation | 审查任务域准备：prepare 移入被选子任务并由受信 intent 驱动，无 LabUtopia 专用适配器。 |
| IMPLEMENTATION_REVIEW_V15_1_13.md | 2026-10-21 | Implementation Review v15.1.13: Production Tool Schema Closure | 审查生产 Tool schema 闭合：回归验证 acquire 与 place 的 assignment 引用链。 |
| IMPLEMENTATION_REVIEW_V15_1_14.md | 2026-10-21 | Implementation Review v15.1.14: Reference-Addressed Assignment Resolution | 审查引用寻址解析：新增 store 端口与 resolver，按精确 ref 校验身份，不重建路线。 |
| IMPLEMENTATION_REVIEW_V15_1_15.md | 2026-10-21 | Implementation Review v15.1.15: Durable Assignment Artifact Store | 审查持久 assignment 存储：新增 SQLite 实现并透传 provider 自有路线参数。 |
| IMPLEMENTATION_REVIEW_V15_2_0.md | 2026-10-21 | Implementation Review v15.2.0: Restarted Assignment Resolution | 审查重启后解析：放宽 place 的 revision 严格相等要求，acquire 仍严格，修复场景推进后误拒。 |
| IMPLEMENTATION_REVIEW_V15_2_1.md | 2026-10-21 | Implementation Review v15.2.1: Provider-Owned Route Arguments | 审查 provider 自有路线参数：准备响应透传 adapter 注册的执行包，PAOS 不解析不授权。 |
| IMPLEMENTATION_REVIEW_V15_3_0.md | 2026-10-21 | Implementation Review v15.3.0: Provider-Neutral Subtask Composition | 审查子任务组合：三端口齐备才注册 execute_subtask，存储重开仍走 adapter 复检。 |
| IMPLEMENTATION_REVIEW_V15_4_0.md | 2026-10-21 | Implementation Review v15.4.0: Persistent Host Coordinator Composition | 审查持久宿主组合：从共享 workspace 构建绑定适配器与只读 resolver，混合配置 fail-closed。 |
| IMPLEMENTATION_REVIEW_V15_4_1.md | 2026-10-21 | Implementation Review v15.4.1: Semantic Binding into Subtask Plans | 审查语义绑定入口：新增 bind_subtask_from_semantics，结构化端口经两个实现验证。 |
| IMPLEMENTATION_REVIEW_V15_4_3.md | 2026-10-21 | Implementation Review v15.4.3: Semantic Task Creation Boundary | 审查语义任务创建：修复语义请求止步于任务创建的 Blocker，语义目标经实测证据绑定。 |
| IMPLEMENTATION_REVIEW_V15_4_5.md | 2026-10-21 | Implementation Review v15.4.5: Async Semantic Query Binding | 审查异步语义绑定：补 bind_async 与异步 builder，兼容异步 Gateway 客户端调用。 |
| IMPLEMENTATION_REVIEW_V15_4_7.md | 2026-10-22 | Implementation Review v15.4.7: Semantic Builder Host Assembly | 审查语义 builder 宿主装配：标准 CLI 宿主注入可选 builder，未配置时行为不变。 |
| IMPLEMENTATION_REVIEW_V15_4_10.md | 2026-10-22 | Implementation Review v15.4.10: AgentLoop Task-Creation Integration Evidence | 新增回归经 ToolRegistry 调用 forge_task_create，验证宿主到任务创建接线，全程无运动。 |
| IMPLEMENTATION_REVIEW_V15_4_11.md | 2026-10-22 | Implementation Review v15.4.11: Installed Workflow Extension Discovery | 构建 wheel 安装到临时目录，子进程验证 entry point 发现与 builder 构造。 |
| IMPLEMENTATION_REVIEW_V15_4_12.md | 2026-10-22 | Implementation Review v15.4.12: Combined Core and Workflow Installation | 构建并合并安装 Core 与工作流 wheel，子进程验证导入、发现与 CLI 注册。 |
| IMPLEMENTATION_REVIEW_V15_4_13.md | 2026-10-22 | Implementation Review v15.4.13: Standard CLI Builder Host Wiring | 审查 CLI 宿主接线：类型化 fake 验证 builder 收到同一客户端实例及未配置路径行为。 |
| IMPLEMENTATION_REVIEW_V15_4_14.md | 2026-10-22 | Implementation Review v15.4.14: AgentLoop Semantic Task ToolCall | 脚本化 provider 验证 forge_task_create 从模型请求到 Tool 派发的链路。 |
| IMPLEMENTATION_REVIEW_V15_4_15.md | 2026-10-22 | Implementation Review v15.4.15: LabUtopia Provider Composition Readiness | 审查组合就绪性：观测源须暴露 capture/query 端口，缺方法不再注册 Agent 可见复合 Tool。 |
| IMPLEMENTATION_REVIEW_V15_4_16.md | 2026-10-22 | Implementation Review v15.4.16: Isaac Camera Observation Source | 审查 Isaac 相机观测源：实现 capture 契约与产物写入，要求实际 media type 与实测标定。 |
| IMPLEMENTATION_REVIEW_V15_5_1.md | 2026-10-22 | Implementation Review v15.5.1: Live Isaac Camera Calibration Metadata | 审查实况相机标定元数据：读取活跃传感器并持久化，遗留跨进程相机句柄 Blocker。 |
| IMPLEMENTATION_REVIEW_V15_5_2.md | 2026-10-22 | Implementation Review v15.5.2: Reusable Isaac Worker Process | 审查可复用 worker 进程：长驻 SimulationApp，遗留相机注册不可用 Blocker。 |
| IMPLEMENTATION_REVIEW_V15_5_3.md | 2026-10-22 | Implementation Review v15.5.3: Session-Owned LabUtopia Task Lifecycle | 审查会话任务生命周期：修复 World 隐式重置，遗留 worker 场景与相机两个 Blocker。 |
| IMPLEMENTATION_REVIEW_V15_5_4.md | 2026-10-22 | Implementation Review v15.5.4: Episode-Owned Task Initialization | 审查 episode 初始化：显式初始化 World 且不回写感知位姿，遗留同场景证据 Blocker。 |
| IMPLEMENTATION_REVIEW_V15_5_5.md | 2026-10-22 | Implementation Review v15.5.5: Session-Owned Task State | 审查会话任务状态：修复 reset 漏赋任务状态字段，遗留 live 相机与 World 复用 Blocker。 |
| IMPLEMENTATION_REVIEW_V15_5_6.md | 2026-10-22 | Implementation Review v15.5.6: Worker-Owned Isaac Session Context | 审查 worker 会话上下文：跨 RPC 共享资源上下文，属会话所有权契约而非实况实现。 |
| IMPLEMENTATION_REVIEW_V15_5_7.md | 2026-10-22 | Implementation Review v15.5.7: Worker-Owned Isaac Scene Resources | 审查 worker 场景资源：World/USD/机器人移入 worker 会话复用，仍不提供相机 RPC。 |
| IMPLEMENTATION_REVIEW_V15_5_8.md | 2026-10-22 | Implementation Review v15.5.8: Durable Isaac Observation Artifacts | 审查观测产物写入：原子持久化相机数组与标定映射，失败显式上抛不伪造结果。 |
| IMPLEMENTATION_REVIEW_V15_5_9.md | 2026-10-22 | Implementation Review v15.5.9: Worker Camera Observation Wiring | 审查相机观测接线：按部署配置构造并注册相机句柄，缺失结果保持 unavailable。 |
| IMPLEMENTATION_REVIEW_V15_5_11.md | 2026-10-22 | Implementation Review v15.5.11: Worker-Owned Scene Revision | 审查 worker 场景修订：会话持有活跃修订单调推进，世界变化后即使未知也推进。 |
| IMPLEMENTATION_REVIEW_V15_5_13.md | 2026-10-22 | Implementation Review v15.5.13: RGB Observation Media | 审查观测媒体类型：RGB 存 PNG、深度与点云保持 NPY，消费方需按 media_type 解码。 |
| IMPLEMENTATION_REVIEW_V15_5_14.md | 2026-10-22 | Implementation Review v15.5.14: Artifact-Resolving Understanding Provider | 审查产物解析理解 provider：组合 resolver 与注入推理，遗留生产宿主未接真实模型。 |
| IMPLEMENTATION_REVIEW_V15_5_15.md | 2026-10-22 | Implementation Review v15.5.15: Persistent Runtime Provider Composition | 审查 Runtime 组合：支持完整 provider 或 resolver+推理两种形态，部署仍未接线。 |
| IMPLEMENTATION_REVIEW_V15_5_16.md | 2026-10-22 | Implementation Review v15.5.16: Lab Runtime Artifact Understanding Composition | 审查 Lab 运行时理解组合：完整 resolver/推理对视为理解就绪，不完整对拒绝注册。 |
| IMPLEMENTATION_REVIEW_V15_6_0.md | 2026-10-22 | Implementation Review v15.6.0: Shared Observation Artifact Root | 审查共享观测产物根：部署提供显式根传入隔离 worker，可注入 resolver，缺根 fail-closed。 |
| IMPLEMENTATION_REVIEW_V15_6_2.md | 2026-10-22 | Implementation Review v15.6.2: Deployment-Configured GPT Scene Understanding | 审查部署配置的 GPT 理解 provider：修复错误字段读取，GPT 仅贡献可见语义不做几何。 |
| IMPLEMENTATION_REVIEW_V15_6_3.md | 2026-10-22 | Implementation Review v15.6.3: Keep Model Vendors Outside PAOS Core | 审查厂商隔离：移除上一阶段放入 Core 的 OpenAI 实现，保留通用组合机制与端口。 |
| IMPLEMENTATION_REVIEW_V15_6_4.md | 2026-10-22 | Implementation Review v15.6.4: Provider-Neutral Inference Discovery | 审查推理发现：新增 inference factory 协议与注册表，非法或重复条目前置失败。 |
| IMPLEMENTATION_REVIEW_V15_6_5.md | 2026-10-22 | Implementation Review v15.6.5: Registry-Backed Runtime Composition | 审查注册表支持的 Runtime 组合：部署经注册表选择推理，LabUtopia 仅转发不分支。 |
| IMPLEMENTATION_REVIEW_V15_6_6.md | 2026-10-22 | Implementation Review v15.6.6: Vendor-Neutral HTTP Inference Adapter | 审查 HTTP 推理适配器：独立扩展包经 entry point 注册，错误传播不伪造空结果。 |
| IMPLEMENTATION_REVIEW_V15_6_7.md | 2026-10-22 | Implementation Review v15.6.7: Observation-to-HTTP No-Motion Evidence Chain | 审查无运动证据链：测试贯通相机源、产物写入、resolver 到 HTTP 理解端点的真实边界。 |
| IMPLEMENTATION_REVIEW_V15_6_8.md | 2026-10-22 | Implementation Review v15.6.8: Perception-Bound Task Projection | 修复语义标签投影到固定 profile 路径的 Blocker：任务投影要求新鲜感知绑定。 |
| IMPLEMENTATION_REVIEW_V15_6_9.md | 2026-10-22 | Implementation Review v15.6.9: Provider Target Resolution Boundary | 审查目标解析边界：profile 不再覆盖实测绑定 provenance，新增可替换目标解析端口。 |
| IMPLEMENTATION_REVIEW_V15_6_10.md | 2026-10-22 | Implementation Review v15.6.10: Standard Preparation Binding Wiring | 审查标准准备绑定：prepare Query 接受感知绑定与过程类型，LabUtopia 补 resolver 接缝。 |
| IMPLEMENTATION_REVIEW_V15_6_11.md | 2026-10-22 | Implementation Review v15.6.11: Internal Subtask Tool Dispatch | 审查内部 Tool 派发：注册内部 Runtime 端点并区分公开/内部可见性，外部不可调用。 |
| IMPLEMENTATION_REVIEW_V15_7_0.md | 2026-10-22 | Implementation Review v15.7.0: LabUtopia Phase RPC and Durable Routes | 审查阶段 RPC：默认后端对路线资格与阶段执行返回不可用，live 试剂任务仍不可执行。 |
| IMPLEMENTATION_REVIEW_V15_5_12.md | 2026-10-23 | Implementation Review v15.5.12: Provider-Neutral Artifact Resolution | 审查产物解析：只读 resolver 端口限定授权根内，路径不出实现边界，覆盖遍历攻击。 |
| IMPLEMENTATION_REVIEW_V15_8_0.md | 2026-10-23 | Implementation review v15.8.0 | 审查 Agent 指导的无液体 Isaac 任务组成：相机、任务创建与路线资格分别记录，物理任务未验收。 |
| IMPLEMENTATION_REVIEW_V16_0_0.md | 2026-10-23 | v16.0.0 透明几何接入审查 | 审查透明几何接入：修复深度误当瓶壁、标签上沿拟合成瓶口、候选覆盖等，交付查询接入。 |
| LAB_PERCEPTION_GRASPNET_REFACTOR_20261023.md | 2026-10-23 | 实验室感知与 GraspNet 接入诊断及重构方案 | 诊断感知接入：规则抓取与真实 Provider 间三个 Blocker，给出重构责任与实施顺序。 |
| LAB_TRANSPARENT_PERCEPTION_FEASIBILITY_20261023.md | 2026-10-23 | 透明实验器材感知：检索结果与可行性审核 | 审核透明感知方案：比较 ReMake/TransCG 等，推荐 SAM2 加 ReMake 并列本地 Blocker。 |
| LAB_TRANSPARENT_PERCEPTION_IMPLEMENTATION_20261023.md | 2026-10-23 | 原实验室场景的透明器材感知接入方案 | 制定透明器材接入方案：定位分割、ReMake 恢复几何、GraspNet 候选与功能点证据链。 |
| labutopia-paos-acceptance.md | 2026-10-23 | LabUtopia PAOS acceptance | 记录 LabUtopia 验收进展：场景感知重构、绑定修复，及完整 cycle 端点遗留控制器实验边界。 |
| GRASPNET_TASK_AFFORDANCE_SELECTION_20261030.md | 2026-10-30 | GraspNet Task-Affordance Selection Diagnosis | 诊断任务可供性选择：抓取分数非任务级选择，需在 selection 前新增任务资格阶段并复验。 |
| IMPLEMENTATION_REVIEW_V16_3_2.md | 2026-11-01 | Implementation Review v16.3.2 | 审查 v16.3.2：无 Blocker/Major，仅记录五项与本次无关的既有 fixture 失败。 |
| IMPLEMENTATION_REVIEW_V16_3_3.md | 2026-11-01 | v16.3.3 Implementation Review | 审查 v16.3.3：修复搅拌候选可能改变工作端的 Major，准备层重验证同采集候选集。 |
| IMPLEMENTATION_REVIEW_V16_3_7.md | 2026-11-01 | Implementation Review v16.3.7 | 审查 v16.3.7：修复 Skill 抹平 Adapter 恢复建议的 Major，仅投影受支持的显式建议。 |
| IMPLEMENTATION_REVIEW_V16_3_8.md | 2026-11-01 | Implementation Review v16.3.8 | 审查 v16.3.8：修复非法四元数逃逸错误契约与空目标绑定进入私有对称解析两个 Major。 |
| IMPLEMENTATION_REVIEW_V16_4_0.md | 2026-11-01 | Implementation Review v16.4.0 | 审查 v16.4.0：修复路线诊断无界膨胀，按代码与阶段聚合并有界输出，防上下文耗尽。 |
| IMPLEMENTATION_REVIEW_V16_6_0.md | 2026-11-02 | v16.6.0 review / 候选生成局部修复复核 | 审查 v16.6.0：区分生成与截断、补接近方向覆盖，阻止事后旋转制造证据。 |
| IMPLEMENTATION_REVIEW_V16_6_2.md | 2026-11-02 | v16.6.2 implementation review / 实现复核 | 审查 v16.6.2：以 cooked 凸组件替换整指包络，几何失败必须拒绝而非视为畅通。 |
| IMPLEMENTATION_REVIEW_V16_6_3.md | 2026-11-02 | v16.6.3 implementation review / 实现复核 | 审查 v16.6.3：IK 前检查最终 TCP 几何、错误不泄漏 USD 路径、修复空源诊断豁免。 |
| IMPLEMENTATION_REVIEW_V16_8_0.md | 2026-11-02 | v16.8.0 implementation review / 实现复核 | 审查 v16.8.0：修复继续挤压、平滑改碰撞路径、物理证据读取与边界接触丢失四个 Major。 |
