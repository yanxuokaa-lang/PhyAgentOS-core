# PhyAgentOS 设计原则

> 规范版本：v1.0<br>
> 适用基线：Session-Centered Runtime（当前代码基线需以 PR 中锁定的 Commit 为准）<br>
> 维护对象：PhyAgentOS 主仓库及其 fork、Target/Skill/Policy/Perception 集成

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
| 未来演进方向 | HAL v3 等目标设计；只能作为兼容方向，不能提前宣称已支持 |

每份设计说明都必须分别列出这三类信息。文档版本（例如 v0.1.6）与代码包版本可能不同；提交前应记录实际 Commit、Python 版本和依赖环境。

## 2. 架构不变量

### 2.1 Session 是执行边界

Agent 的任务规划与物理执行通过 Workspace Protocol 和 Runtime 接口耦合，不能通过私有调用直接跨层。

标准状态流为：

```text
pending
  -> claimed
  -> preflight_checking
  -> running
  -> finalizing
  -> succeeded | failed | timed_out | cancelled
```

启用语义验收时还可能经过：

```text
finalizing -> awaiting_verification -> verifying
            -> succeeded | failed | replanned
```

必须遵守：

1. 使用 `SessionRegistry`、锁文件和 claim token 推进状态。
2. 不手工编辑运行中的 Session，不把 `running` 改写为 `succeeded`。
3. 不依赖当前尚未执行的 `depends_on` 调度语义。
4. 重跑使用受控的 Session 重置流程，并保留既有结果和 Artifact。

### 2.2 控制面与事实所有权

| 组件 | 负责内容 | 不负责内容 |
|---|---|---|
| Agent/Channel | 消息、上下文、规划、工具请求 | 直接调用 Target、伪造 Runtime 终态 |
| Watchdog/SessionRunner | claim、Preflight、生命周期、超时 | 任务语义规划、替代 Target 安全闭环 |
| Skill Runtime | 闭环编排、Policy/Builtin 调用 | 直接访问 SDK、Simulator、WebSocket |
| Target | 环境事实、动作执行、Target-side 安全 | Agent 规划、语义验收 |
| Adapter/Bridge | 显式格式转换、契约验证 | 隐式裁剪、补齐、降级 |
| Perception | 感知 Plan、Environment v2 写回、Artifact | 伪造几何或手工篡改环境事实 |
| SessionVerifier | 语义 verdict、Attempt、Lesson | 改写已经发生的物理执行事实 |

一个模块只能写入其拥有的数据。Workspace 文件的作者和读者也必须保持既有所有权，不得用 `TARGETS.md` 代替 `SESSIONS.md`，或用 `ENVIRONMENT.md` 代替执行结果。

### 2.3 显式 Contract，失败即拒绝

Observation 和 Action 的以下属性必须显式声明并可由 Preflight 比较：

- Key、Shape、dtype、layout
- representation、单位、归一化方式
- Empty Observation 语义
- Sensor、Environment Output 和 Tool Requirements
- RPC 版本、消息类型、错误码

不允许隐式裁剪、补零、补字段、单位猜测、dtype cast 或 representation 降级。确有转换需求时，新增命名明确、可独立测试的 `ActionBridge` 或 Adapter 规则。契约不完整或不兼容时，应在执行前进入 `rejected`。

### 2.4 Runtime 只能通过 Handle 访问 Target

Skill Runtime 的唯一 Target 访问面是 `TargetSessionHandle`，包括：

```python
observe()
action_chunk(chunk)
execution_status()
request_environment_refresh(request=None)
call_target_tool(tool_name, arguments)
stop(reason)
```

禁止在 Skill Runtime 内直接保存 Target SDK、WebSocket Client 或 Simulator Client。

### 2.5 状态、事实和证据不可伪造

- `SessionRegistry` 写 Session 状态。
- `ResultWriter` 写 Episode、`LOG.md` 和 `LESSONS.md`。
- `EnvironmentWriter` reconcile/merge `PhyAgentOS.environment.v2`。
- 大型图像、Mask、Depth、Point Cloud、Trace 和 logits 写入 Artifact。
- `SessionVerifier` 的语义失败不能伪造一次新的 Runtime 执行。

每条结论都应能追溯到 Session、Attempt、Artifact 和时间戳。

## 3. 当前版本限制（不得假定已实现）

以下限制来自当前 v0.1.6 文档和代码边界，集成方案必须明确处理：

- `depends_on` 已进入 Schema，但当前调度器不能作为生产依赖保证。
- Factory 通过显式 Python 注册完成，不提供旧 `PhyAgentOS_plugin.toml` Driver 自动发现。
- 当前默认 Runtime 以 Dummy/Simulation 为主，没有可直接假定可用的完整 `real_robot` Runtime。
- Preflight 不是完整真机安全认证，尚未覆盖全部 Operator Override、SafetyGuard 参数、远端 Healthcheck 和断连安全闭环。
- 部分 Runtime 的 `strict_environment_contract` 仍可能为非严格配置。
- Goal Graph、Session Compiler、通用 CompositeTarget 和完整 Fleet 编排属于演进方向。
- 历史 `hal/hal_watchdog.py --driver ...` 示例不代表当前可安装 API。

方案和文档只能描述已注册、已测试、可复现的能力；未来方向必须标为 planned，不能写成当前支持列表。

## 4. 方案设计流程

所有中等及以上改动在编码前都应形成设计记录，按以下顺序完成：

### 第一步：锁定问题和边界

写清楚 Goal、Non-goals、目标用户、运行环境，以及不会改变的既有行为。先锁定上游 Commit、文档版本、Python 版本和外部服务版本。

### 第二步：选择扩展点

| 需求 | 首选扩展点 | 不应修改 |
|---|---|---|
| 新机器人/模拟器 | `BaseRolloutTarget` + `TargetAdapter` | AgentLoop、Scheduler |
| 新远程环境 | `TargetWSClient` + `RemoteTargetProxy` | Skill Runtime 内部网络逻辑 |
| 新策略服务 | Policy Client + `BasePolicyAdapter` | Target 内部实现 |
| 新闭环 | `PolicySkillRuntime` 或 `BuiltinSkillRuntime` | 原始 Target/SDK |
| 新动作变换 | `BaseActionBridge` | Adapter 中的隐式修正 |
| 新感知模型 | Perception Plugin + Config | 手工写 `ENVIRONMENT.md` |
| 新消息入口 | Channel | Runtime Session 状态机 |

### 第三步：定义所有权和 Contract

方案必须给出读写者、状态决策者、Observation/Action Schema、错误码、超时、取消、重试和资源释放语义。Contract 应先于实现存在，并能驱动 rejected 测试。

### 第四步：画出生命周期和失败矩阵

说明每个阶段由谁调用、谁写结果、失败后进入哪个状态，以及是否创建 Attempt 或新的 pending Session。连接错误、Policy 错误、Target 错误、Timeout 和语义失败不得折叠成同一个错误。

### 第五步：确定兼容和回滚策略

默认配置、既有注册项、旧 Session 文件和 Artifact 路径应保持不变。公共 Schema 或 RPC 变更必须提供版本/迁移方案、兼容读取策略和禁用新功能的回滚路径。

### 第六步：先写拒绝路径

优先实现并测试未知 Runtime、错误 Endpoint、缺失 Adapter、Shape 不兼容、Sensor 缺失、非法 Tool、Policy 超时和 Target 断连。只有拒绝行为确定后，accepted 路径才具备可运维性。

## 5. 代码写作规则

1. **优先新增，谨慎修改核心路径。** 使用新 Adapter、Bridge、Factory、Target 或 Skill Runtime 承载变化；修改公共基类、Scheduler 或状态机前必须说明必要性。
2. **接口优先。** 先更新 Schema/Contract，再实现逻辑；禁止用运行时猜测替代声明。
3. **Adapter 尽量纯函数化。** 转换逻辑不应隐藏网络、状态推进或安全决策。
4. **注册显式化。** 使用 `register_local_target_runtime`、`register_remote_target_runtime` 和 `register_skill_runtime`。
5. **生命周期幂等。** Target 的 `cancel`、`close`、清理和重复初始化必须可重复调用。
6. **失败 fail-closed。** 未知动作、过期命令、断连、越界或校验缺失时拒绝/停止。
7. **避免全局可变状态。** Session、Target、Policy Client 的运行状态必须绑定到明确的 Session/Handle，不得通过全局缓存跨 Session 泄漏。
8. **保持错误分层。** 使用稳定错误码和可操作信息，保留原始异常作为 Artifact/日志上下文。
9. **不提前实现未来语义。** 不因 HAL v3 规划而伪造当前版本的安全、依赖或 Fleet 能力。
10. **文档与代码同步。** 新增注册关系、配置字段、Endpoint 或限制必须同时更新中英文文档。

## 6. Remote RPC 规则

Remote Target 使用 `phyagentos.runtime_rpc.v2`、WebSocket 和 msgpack。请求至少包含：

```yaml
version: phyagentos.runtime_rpc.v2
type: target.action_chunk
session_id: sess_001
target_id: target_001
skillruntime_id: skill_001
episode_id: ep_001
seq: 17
timestamp_ns: 0
trace_id: trace_001
payload: {}
```

Response 必须匹配请求的 `seq`、Session、Target 和 Skill Runtime。错误使用 `runtime.error`，包含稳定 `error_code` 和可操作的 `message`。小型结构化控制数据可放入 Payload；大型数据必须落盘并传递 Path/URI。

## 7. Perception 与真机安全规则

Perception 必须分离 Sensor Config、Perception Config 和 Skill Requirements。2D 结果不得转换成没有依据的米制 3D Pose；环境状态应保留来源、版本和 Artifact 引用。

真机 Target 必须在 Target 侧独立实现并验证：

- 急停、Workspace Bounds、速度/加速度/力限制
- 命令时效、未知动作拒绝和断连停止
- Operator Override
- 幂等 `cancel`/`close` 和资源释放

现有 Preflight accepted 只表示配置/契约兼容，不能作为真机安全认证或运动授权。

## 8. 测试与质量门禁

每个新 Target、Skill、Policy 或 Adapter 至少覆盖：

```text
Schema
-> Factory
-> Preflight rejected
-> Preflight accepted
-> Dummy/Mock 单 Session
-> Timeout
-> Cancel/Close
-> Artifact、LOG、ENVIRONMENT、LESSONS
-> 多次运行资源释放
```

基础命令：

```bash
pytest
pytest tests/runtime
ruff check PhyAgentOS tests
```

涉及真机时，还必须有 Target-side 安全停止测试和明确的无硬件/仿真验证边界。

## 9. PR 合入清单

PR 描述必须逐项回答：

- [ ] 本次修改引用了本文档的适用原则和章节。
- [ ] 已说明扩展点、所有权和未修改的核心边界。
- [ ] Schema、Factory、Target/Skill/Adapter 注册关系完整。
- [ ] 有 Preflight accepted 与 rejected 用例。
- [ ] 有 timeout、cancel、close 和资源释放测试。
- [ ] 有至少一个可复现的端到端 Session Artifact。
- [ ] 未引入隐式裁剪、补齐、cast、降级或跨层调用。
- [ ] 已区分当前能力、当前限制和未来规划。
- [ ] 中英文启动说明、配置示例和已知限制已更新。
- [ ] 未夹带无关重构、格式化或依赖升级。
- [ ] 如改变公共 Schema/RPC/状态机，已提供迁移、兼容和回滚方案。

建议按风险分级：

| 等级 | 改动 | 额外门禁 |
|---|---|---|
| L1 | 独立 Adapter、Policy 或 Perception Plugin | 单元测试 + Preflight |
| L2 | 新 Target 或 Skill Runtime | 生命周期、端到端、资源释放、文档 |
| L3 | 公共 Schema、Session 状态机、RPC 或 Safety | 迁移测试、回滚方案、完整集成验证 |

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
