# PhyAgentOS 设计原则

> 规范版本：v1.0<br>
> 适用基线：PAOS v1.0.0 Forge（`upstream/main`，提交须在 PR 中重新锁定）<br>
> 维护对象：PhyAgentOS 主仓库及其 fork、Forge Tool/Skill/Provider/机器人与仿真器集成

本文档是 PhyAgentOS 二次开发的**唯一设计原则源**。方案、代码、测试和 PR 都应引用本文档，而不是在各自目录复制一套相互漂移的规则。

## 1. 规范用词与版本边界

- **必须（MUST）**：违反即不应合入，除非同时修改本文档并完成迁移评审。
- **应该（SHOULD）**：默认遵守；偏离时必须在方案和 PR 中说明原因、风险和替代方案。
- **可以（MAY）**：可选实现，不得被误解为当前 Runtime 的保证。

本文档同时区分三种信息：

| 类别 | 设计含义 |
|---|---|
| 架构不变量 | 所有扩展都必须保持的行为；不能通过“兼容模式”绕过 |
| 当前版本限制 | 当前代码或文档明确尚未实现的能力；设计不能假定其存在 |
| 未来演进方向 | 尚未实现的能力；只能作为兼容方向，不能提前宣称已支持 |

每份设计说明都必须分别列出这三类信息。文档版本与代码包版本可能不同；提交前应记录实际 Commit、Python 版本和依赖环境。

## 2. 架构不变量

### 2.1 Forge Tool API 是唯一物理执行链

Agent 的任务规划与物理执行只能经过 `ForgeToolClient → Gateway /tools → ToolEndpoint`，不能通过私有调用直接跨层。

标准状态流为：

```text
AgentTask
  -> PlanRevision
  -> Query / Action / Session records
  -> finalize / verification
  -> succeeded | failed | cancelled
```

恢复模式还可能经过：

```text
finalize -> verifier -> succeeded | failed | awaiting_replan
                      -> new PlanRevision
```

必须遵守：

1. 使用现有 AgentTask/PlanRevision/ToolExecutionRecord 生命周期；不得创建第二套执行状态机。
2. Query、Action、Session 必须分别遵守 v1.0 `/tools` 与 `/invocations` 契约。
3. Action/Session 的 accepted、cancel、timeout 和 `unknown` 不代表物理停止，禁止盲重试。
4. 恢复只能在同一 `task_id` 上追加有预算和 deadline 的 PlanRevision。

### 2.2 控制面与事实所有权

| 组件 | 负责内容 | 不负责内容 |
|---|---|---|
| Agent/Channel | 消息、上下文、规划、工具请求 | 直接调用物理后端、伪造 Runtime 终态 |
| AgentTask/Planner | 任务、PlanRevision、绑定调用和恢复 | 直接执行机器人 |
| Forge Gateway/ToolEndpoint | Tool 执行事实、Endpoint、Dora、机器人/仿真器 | 用户级语义判定 |
| Skill Runtime | Bundle、profile、Dora/Gateway 生命周期 | 直接访问 SDK、Simulator、WebSocket |
| Adapter/Provider | 显式格式转换、契约验证、后端实现 | 隐式裁剪、补齐、降级 |
| Evidence collector | 观测 Artifact 与质量元数据 | 伪造 Tool 执行事实 |
| Verification/Experience | 语义 verdict、Episode、Lesson、Candidate | 改写已发生的执行事实或授权运动 |

一个模块只能写入其拥有的数据。ToolResult、Evidence、Verdict、Episode 和 Candidate 必须保持独立；不得把 provider 输出直接当作任务成功或运动授权。

### 2.3 显式 Contract，失败即拒绝

Query、Action 和 Session 的输入、输出与以下物理属性必须在 ToolSpec/context 中显式声明，并由 Gateway/Endpoint 校验：

- Key、Shape、dtype、layout
- representation、单位、归一化方式
- Empty Observation 语义
- Sensor、Environment Output 和 Tool Requirements
- RPC 版本、消息类型、错误码

不允许隐式裁剪、补零、补字段、单位猜测、dtype cast 或 representation 降级。确有转换需求时，新增命名明确、可独立测试的 `ActionBridge` 或 Adapter 规则。契约不完整或不兼容时，应在执行前进入 `rejected`。

### 2.4 Runtime 只能通过 ToolEndpoint 访问物理后端

Skill Runtime 的唯一物理访问面是 Forge Tool API：

```python
GET /tools/{tool_id}
GET /tools/{tool_id}/context
POST /tools/{endpoint_id}/{operation}:invoke  # Query
POST /tools/{tool_id}:invoke                 # Action/Session
```

禁止 Agent、Skill 或 PAOS 核心直接保存或调用 Target SDK、Dora client、SAPIEN、RoboTwin 或 Simulator client。

### 2.5 状态、事实和证据不可伪造

- `AgentTaskStore` 写 AgentTask、PlanRevision 和 ToolExecutionRecord。
- `Forge Gateway` 写 ToolResult、invocation 和 attempt 事实。
- Evidence collector 写 Artifact 与质量元数据；ExperienceCoordinator 写 Episode、Lesson 和 Candidate。
- 大型图像、Mask、Depth、Point Cloud、Trace 和 logits 写入 Artifact。
- `Verification` 的语义失败不能伪造一次新的 Gateway 执行。

每条结论都应能追溯到适用的 task/revision、invocation/attempt、Artifact 和时间戳；没有真实状态所有权时不应虚构 Session。

## 3. 当前版本限制（不得假定已实现）

以下限制来自 PAOS v1.0.0 文档和代码边界，集成方案必须明确处理：

- Concrete Forge Skills、Node、模型和仿真资产不随 PAOS 核心分发，必须通过 manifest-v2 Bundle 独立安装。
- `execution.session` 不是默认要求；只有 Endpoint 确有持久资源/状态所有权时才使用。
- 当前证据采集是 best-effort；Forge ToolResult 和 invocation events 才是执行事实权威。
- `unknown` 对 PAOS 聚合是终态失败，但不证明物理停止，仍需按 `invocation_id` 追踪。
- 交叉 Tool 资源租约、隐式 Registry 下载和旧 `/agent/sessions`、`/policy/command` 路由不属于当前契约。
- 真机安全认证、跨后端评测和 held-out/hazard 晋升门槛必须由对应实现 PR 单独证明。

方案和文档只能描述已注册、已测试、可复现的能力；未来方向必须标为 planned，不能写成当前支持列表。

## 4. 方案设计流程

所有中等及以上改动在编码前都应形成设计记录，按以下顺序完成：

### 第一步：锁定问题和边界

写清楚 Goal、Non-goals、目标用户、运行环境，以及不会改变的既有行为。先锁定上游 Commit、文档版本、Python 版本和外部服务版本。

### 第二步：选择扩展点

| 需求 | 首选扩展点 | 不应修改 |
|---|---|---|
| 新机器人/模拟器 | ToolEndpoint + Skill Bundle profile/adapter | AgentLoop、AgentTask、核心执行链 |
| 新远程环境 | ToolEndpoint behind Gateway | Skill Runtime 内部私有 RPC |
| 新策略/感知服务 | provider interface + ToolSpec | ToolSpec 公共字段中的 provider 专用参数 |
| 新动作变换 | 显式 Adapter/Bridge | 隐式裁剪、补齐、单位猜测 |
| 新闭环 | bounded Action 或有真实所有权的 Session | 第二套执行/结算协议 |
| 自我进化 | ExperienceCoordinator、Lesson、SkillCandidate | 当前任务、安全门、Verifier 事实 |
| 新消息入口 | Agent Channel | Gateway/Tool API 状态机 |

### 第三步：定义所有权和 Contract

方案必须给出读写者、状态决策者、Observation/Action Schema、错误码、超时、取消、重试和资源释放语义。Contract 应先于实现存在，并能驱动 rejected 测试。

### 第四步：画出生命周期和失败矩阵

说明每个阶段由谁调用、谁写结果、失败后进入哪个 Tool/AgentTask 状态，以及是否创建 invocation/attempt 或新的 PlanRevision。连接错误、Provider 错误、Target 错误、Timeout 和语义失败不得折叠成同一个错误。

### 第五步：确定兼容和回滚策略

默认配置、既有 Tool binding、AgentTask 和 Artifact 路径应保持不变。公共 Schema 或 RPC 变更必须提供版本/迁移方案、兼容读取策略和禁用新功能的回滚路径。

### 第六步：先写拒绝路径

优先实现并测试未知 Runtime、错误 Endpoint、缺失 Adapter、Shape 不兼容、Sensor 缺失、非法 Tool、Provider 超时和后端断连。只有拒绝行为确定后，accepted 路径才具备可运维性。

## 5. 代码写作规则

1. **优先使用正式扩展点。** 使用 ToolEndpoint operation、ToolSpec、manifest-v2 Skill Bundle profile 和 provider/adapter 承载变化；修改 AgentTask、ForgeToolClient、RuntimeManager 或公共状态机前必须说明通用 API 无法表达该能力的证据。
2. **接口优先。** 先更新 Schema/Contract，再实现逻辑；禁止用运行时猜测替代声明。
3. **Adapter 尽量纯函数化。** 转换逻辑不应隐藏网络、状态推进或安全决策。
4. **绑定显式化。** ToolSpec binding、Bundle `required_tools`、profile/dataflow 和 locked Node artifact 必须可检查；只有通用 Forge task/Tool API 无法表达能力时才新增 Agent tool。
5. **生命周期幂等。** Endpoint 的取消/停止、Runtime 清理和重复初始化必须遵守对应 Query/Action/Session 语义并可安全重入。
6. **失败 fail-closed。** 未知动作、过期命令、断连、越界或校验缺失时拒绝/停止。
7. **避免全局可变状态。** 后端、Provider 和缓存状态必须绑定到明确的 Runtime、invocation 或确有所有权的 Session，不得通过进程全局缓存跨 AgentTask 泄漏。
8. **保持错误分层。** 使用稳定错误码和可操作信息，保留原始异常作为 Artifact/日志上下文。
9. **不提前实现未来语义。** 不因未定名的未来规划而伪造当前版本的安全、依赖或 Fleet 能力。
10. **文档与代码同步。** 新增注册关系、配置字段、Endpoint 或限制必须同时更新中英文文档。

## 6. Remote/Tool API 规则

远程机器人、Provider 或 Simulator 只能作为 Gateway/ToolEndpoint 的后端实现。Agent-facing
协议始终是 Forge `/tools` 与 `/invocations`；WebSocket、gRPC、msgpack 或厂商 SDK 只能存在于
Endpoint/adapter 内部，且不得形成第二套 Agent 执行协议。

内部远程协议必须验证版本、operation、请求/响应关联、deadline、取消/停止、重放与
`unknown` 语义，并把稳定 `error_code` 映射回 ToolResult。小型结构化控制数据可放入
payload；大型观测、轨迹和诊断必须物化为有边界的 ArtifactRef。内部关联 ID 不得替代
PAOS `task_id`、`revision_id`、record ID、`caller_id`、Gateway `invocation_id` 或 `attempt_id`。

## 7. Perception 与真机安全规则

Perception 必须分离 Sensor Config、Perception Config 和 Skill Requirements。2D 结果不得转换成没有依据的米制 3D Pose；环境状态应保留来源、版本和 Artifact 引用。

真机 ToolEndpoint 的 adapter/硬件控制器必须在物理执行侧独立实现并验证：

- 急停、Workspace Bounds、速度/加速度/力限制
- 命令时效、未知动作拒绝和断连停止
- Operator Override
- 幂等 `cancel`/`close` 和资源释放

现有 Tool context/admission accepted 只表示配置/契约兼容，不能作为真机安全认证或运动授权。

## 8. 测试与质量门禁

每个新 ToolEndpoint、Skill、Provider、Policy 或 Adapter 至少覆盖：

```text
Schema/ToolSpec
-> binding/context
-> rejected paths
-> accepted Query 或 Action/Session admission
-> Mock Gateway
-> Timeout/cancel/unknown（适用时）
-> Artifact、AgentTask、verification/experience（适用时）
-> 多次运行资源释放
```

基础命令：

```bash
pytest
pytest tests/runtime
ruff check PhyAgentOS tests
```

涉及真机时，还必须有物理执行侧安全停止测试和明确的无硬件/仿真验证边界。

## 9. PR 合入清单

PR 描述必须逐项回答：

- [ ] 本次修改引用了本文档的适用原则和章节。
- [ ] 已说明扩展点、所有权和未修改的核心边界。
- [ ] Schema、ToolSpec、Endpoint、Skill Bundle/profile 注册关系完整。
- [ ] 有 context/binding 与 rejected/accepted 用例。
- [ ] 有 timeout、cancel、unknown 和资源释放测试（适用时）。
- [ ] 有至少一个可复现的 Query 或 AgentTask Artifact。
- [ ] 未引入隐式裁剪、补齐、cast、降级或跨层调用。
- [ ] 已区分当前能力、当前限制和未来规划。
- [ ] 中英文启动说明、配置示例和已知限制已更新。
- [ ] 未夹带无关重构、格式化或依赖升级。
- [ ] 如改变公共 Schema/RPC/状态机，已提供迁移、兼容和回滚方案。

建议按风险分级：

| 等级 | 改动 | 额外门禁 |
|---|---|---|
| L1 | 独立 provider/adapter 或 Query ToolSpec | 单元测试 + context/binding + rejected/accepted Query |
| L2 | 新 Action/Session ToolEndpoint 或 Skill Bundle profile | 生命周期、Mock Gateway、unknown/cancel/stop、资源释放、文档 |
| L3 | Forge Tool API、AgentTask、Verification、Experience 或公共状态机 | 迁移测试、回滚方案、完整集成验证与上游架构评审 |

## 10. 设计记录模板

```markdown
# Feature: <name>

## Goal / Non-goals
## Extension Point
## Ownership
## Invariants
## Current Limitations
## Future-compatible Direction
## Contracts
## Lifecycle and Failure Matrix
## Compatibility and Rollback
## Tests and Evidence
## PR Checklist
```

本文档的原则变更本身也必须通过 PR；修改不变量、状态机、Contract 或安全边界时，必须同时更新相关实现、测试、示例和中英文文档。
