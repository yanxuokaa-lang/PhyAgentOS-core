# Implementation Review v13.0.6：Decisions 能力验证方案复审

日期：2026-10-09  
范围：`DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md`，以及其引用的入口诊断和 Decisions 官方协议记录。

本轮审查“进入能力验证实验”后的方案边界，不把尚未创建的样本、runner 或 API 结果写成已完成实验。审查沿用七个维度：Architecture、Correctness、Recovery/Idempotency、Safety、Extensibility/Compatibility、Observability/Maintainability、AgentLoop Autonomy/Convergence。

## Findings before fixes

### Blocker

无。方案明确 route 只保存为标签，未连接 PAOS handler、Coordinator、Gateway 或 Runtime。

### Major

1. **Correctness / 状态条件不一致。** `capability_state` 定义 `has_current_task` 可包含可查询的终态任务，但 route 矩阵和请求选项仍写 `active task`。同一条 terminal status 样本可能被标注器允许、却被题目排除，造成 gold 与模型题意不一致。
2. **Extensibility/Compatibility / 官方协议边界不完整。** 官方指南的图片示例使用 inline base64，当前 OpenAPI `createDecision` 描述同时列出公开 HTTP(S) URL；方案没有把该差异放进能力结论边界。未来复用时可能把未验证的图片输入能力当成已支持能力。
3. **Safety / endpoint 与客户端选择不够可执行。** 方案读取任意 `DECISIONS_API_URL`，但没有明确默认 HTTPS 和 `/v1/decisions` 路径；同时项目支持 Python 3.11/3.12，而官方 Decisions SDK 示例要求 Python 3.26.0+，直接照搬 SDK 会使 smoke 环境不可复现，或把 key 发往错误代理路径。

### Minor / limits

1. 样本、runner、config 和输出尚未创建，因此本轮只能验收设计和静态契约，不能验收 API 连通性或分类能力。
2. 本实验只覆盖文本入口；图片、代理服务、SDK 特有字段和服务端版本漂移仍需单独 development smoke。

## Fixes applied

| Finding | 修复 |
| --- | --- |
| 状态条件不一致 | `status_read` 统一要求当前关联任务（包含可查询 terminal task）和 `read_status`，并同步修改 route choice 描述。 |
| 官方协议差异 | 记录指南与 OpenAPI 的图片 URL 差异；本轮明确只发文本，未来图片能力必须单独 smoke，不纳入当前结论。 |
| endpoint/客户端边界 | 默认要求 HTTPS 与 `/v1/decisions`；兼容代理必须显式记录 host/kind；初始 smoke 推荐标准 HTTP，SDK 仅在版本和 Decisions 支持确认后使用。 |

## Seven dimensions after fixes

1. **Architecture / 架构：方案级通过。** dataset、request builder、backend adapter、scorer 和 operator 仍分责；实验不复制 PAOS 状态或执行平面。当前未实现 runner 是交付状态限制，不被误报为实验成功。
2. **Correctness / 正确性：方案级通过。** 七类 intent、五类 route、人工裁决、兼容矩阵和 capability 约束现在使用一致的“当前关联任务”定义。实际标注质量和 API 预测仍待执行验证。
3. **Recovery and Idempotency / 恢复与幂等：方案级通过。** logical request 与 transport attempt 分离，有限重试、原始响应保存和 resume 规则不改变；补测使用 supplemental run。
4. **Safety / 安全：方案级通过。** route 不触发操作；合成任务 ID、无 PAOS 写连接、无凭据日志保持不变；API key 发送边界增加 HTTPS/path 约束。
5. **Extensibility and Compatibility / 扩展兼容：方案级通过。** provider adapter 继续隔离 schema；图片协议冲突显式保留为未验证能力，HTTP 与 SDK 不再被混作同一前提。
6. **Observability and Maintainability / 可观测维护：方案级通过。** requests、attempts、responses、predictions、environment 和 errors 分层记录；新增 endpoint kind/host 和实际客户端版本记录要求。
7. **AgentLoop Autonomy and Convergence / AgentLoop 自主收敛：方案级通过。** Decisions 仍只给一次 proposal；System 2 接收原始输入，不回环；现有显式命令、停止和 waiting-for-user owner 不变。

## Validation

- 文档 UTF-8、Markdown fence、JSON 示例和本地链接检查通过。
- `status_read` 的矩阵、choice 描述与 `has_current_task` 定义一致。
- 80 条基础样本、110 条含选做请求预算和七维指标定义未改变。
- 官方 Decisions 文档与 OpenAPI 只读核对完成；本轮未调用 API、未创建 runner、未修改 PAOS 路由。
- `git diff --check` 通过；工作区中与本轮无关的未跟踪文件保持不变。

## Conclusion

本轮发现的 3 项 Major 已在方案级修复，结论为“设计复审通过”。这不等于 GPT-6 Luna 能力通过，也不授权替换现有入口。下一阶段仍需先创建并静态校验 80 条样本和 standalone runner，再按 5 条 development smoke、20 条 development、60 条 evaluation 顺序执行。
