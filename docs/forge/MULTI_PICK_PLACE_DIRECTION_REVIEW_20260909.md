# 多物体接入方向复核与下一功能验收

## 结论

以 v8.0.0 为复核起点，文档的总体架构方向没有偏离 PAOS。
当前实现属于接入组件，不是已交付的 Agent 多物体任务系统。下一功能为
真实 Tool context 状态传播，服务于正式 Runtime Bundle 的启动和发现，
不新增任务调度器，不把内存 HTTP conformance transport 当成 Dora 部署。

## 依据与对照

| 规范 | 当前方向 | 结论 |
| --- | --- | --- |
| `docs/zh/01-framework-introduction.md` 第 1-6 节 | AgentTask、Execution、Evidence、Verdict 分开；provider 持物，不在 Agent 中执行机器人 | 一致 |
| `PLANNING_MODULE_DESIGN.md` Purpose/Ownership | 保留语义 DAG，七 Tool 仅作为可选工作流；没有新逐 Tool 调度器 | 一致 |
| `MANIPULATION_DAG_DEVELOPER_GUIDE.md` Ownership Matrix | adapter 负责路线/机械臂分配，Runtime 负责物理事实，Verifier 负责用户成功 | 一致 |
| `docs/zh/03-developer-manual.md` 第 12-13 节 | 独立 provider 环境和 provider-neutral Skill；实际 Bundle/contexts 尚未验收 | 方向一致，交付未完成 |
| `docs/user_development_guide/README.md` 第 1、4-6 节 | 下一部署必须走 RuntimeManager、Gateway Tool API、Dora 和 required Tools context | 必须保留，不得以 Python factory 替代 |
| 用户 Anti-OverDefense | 复用现有就绪状态、类型和测试，不新增 hash/发布门禁 | 一致 |

早期两个审核文件中的“尚未进入实现”是历史结论，不是当前状态。
当前状态查 `PERSISTENT_MULTI_PICK_PLACE_STATUS_20260909.md`；没有改写历史审核。
给各 Tool 声明 `object.relocate` 仅表示它可被该语义义务选用；
`compose_agent_plan` 要求 `placed:<entity>` 产出，Query 或 acquire 成功不能完成搬运。
最终用户任务仍须 Verifier，不凭所有 Tool 成功自动裁决排列正确。

## 本轮发现与修复

1. Major：`CapabilityRuntime.register_tool` 默认 ready=true，持久 Skill 没有提供
   当前健康投影。provider 丢失后 Tool context 仍可能宣称 ready，无法支撑指南要求的
   required_tools 验收。新增可选动态 context provider，发现和新调用使用相同来源；
   持久组合显式要求宿主注入。缺字段或异常投影为 unavailable，异常只公开类型。
2. Major：持久 place 在 succeeded/outcome_known=true 但无 artifact_refs 时仍生成
   placed 完成证据。改为 unknown/missing_execution_evidence，保留 world_change_started，
   不输出 placed。不能用成功字符串替代真实执行证据。

## 下一功能边界

`context_provider()` 是 endpoint 健康投影，不执行模型推理或运动，不创建 invocation，
也不判断某个候选能否抓取。宿主检查依赖与连接后返回明确 ready/binding_error；
持物状态、路线授权、现场和候选准入继续由 provider 执行侧检查。
新调用重新读取 context；已经接纳的 invocation 查询、cancel/stop 不依赖新调用的 ready，
避免故障时反而关闭对账和停止通道。静态 context 注册保持兼容。

## 六维验收

| 维度 | 功能验收依据 |
| --- | --- |
| 架构集成 | 通用 Runtime 增加 provider-neutral callback；持久 Skill 使用它，无新生命周期 owner |
| 失败路径 | 启动中、ready、断连、异常及缺 ready 的状态均测试；无证据成功归 unknown |
| 权限与安全 | unavailable 阻止新调用；已有 invocation 可查询/取消；无自动授权或动作 |
| 配置与复现 | callback 由宿主显式注入；静态接口兼容；独立测试和隔离暂存树验证 |
| 可维护性 | 发现和准入共用 get_context；不复制 health 状态库或固定 Tool 顺序 |
| 可观测性 | binding_error 显示异常类型；missing_execution_evidence 明确归属执行侧 |

本表验收范围仅为就绪状态传播和证据投影。正式 Bundle 的实际进程/Dora 生命周期、
完整路线 readiness、模型实体几何绑定以及真实 Agent 多物体仿真仍未验收。
