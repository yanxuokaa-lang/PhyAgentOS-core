# Implementation Review v13.0.4：Decisions 入口意图与路由验证方案

日期：2026-10-09
范围：

- `docs/forge/DECISIONS_INTENT_ROUTING_DIAGNOSIS_20261009.md`
- `docs/forge/DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md`

审查维度沿用项目既有七维标准：Architecture、Correctness、Recovery/Idempotency、Safety、
Extensibility/Compatibility、Observability/Maintainability、AgentLoop Autonomy/Convergence。
本轮审核方案设计，不把尚未运行的 API 实验写成能力通过。

## Findings before fixes

### Blocker

无。原方案明确不调用 PAOS handler，也没有已存在的运行时代码变更或现场副作用。

### Major

1. **Architecture / 输入不统一与标签泄漏风险。** 原 `available_handlers` 是逐样本自由文本，
   没有约束其独立于 gold 编写；按答案描述能力会泄漏标签。同一全量候选说明本身不构成泄漏，
   缺口是能力事实表达不统一、未约束输入构造。
2. **Correctness / 两题缺少一致性和标注裁决。** intent 与 route 独立返回，但原方案没有兼容
   矩阵、状态约束和单值 tie-break；`unavailable-handler selection` 也没有说明检查 prediction
   还是 gold，evaluation 的独立复核与争议裁决不完整。
3. **Recovery and idempotency / transport attempt 会污染逻辑预测。** 原方案只说保存 retry，未定义
   run/case/request/attempt 身份、timeout 后选择哪次响应、恢复时跳过条件和 exhausted failure
   处理。一次样本可能被重复计入基础准确率。
4. **Safety / 离线边界不可执行。** 原方案说“不执行 handler”，但未约束未来 runner 的 import、
   PAOS 写连接、真实 task ID、私有任务文本和 endpoint 边界。错误实现仍可能读取或控制现场任务。
5. **Extensibility and compatibility / provider 契约混合。** 目标是 Luna，但原方案把 OpenAI
   confidence/probabilities、endpoint 和 SDK 字段近似当作所有 Decisions provider 的共同接口，
   route policy 也可能被埋入 scorer。
6. **Observability and maintainability / 缺少可复查 attempt 与环境记录。** 原输出未覆盖 provider
   request ID、HTTP status、requested/reported model、wall/monotonic time、schema version、runner
   commit 和细分错误类型；难以区分 annotation、state、模型与 transport 问题。
7. **AgentLoop autonomy and convergence / 未限制未来路由循环。** 原方案没有明确“一次入站一次
   判断”、System 2 保留原始消息、Decision→System 2 不回环、route 只作 proposal；也没有
   simple-path coverage、incompatible pair 和 repeated-call instability 等收敛指标。

### Minor

1. 60 条 evaluation 只能验证第一轮可行性，不能证明线上可靠性或完成概率校准。
2. intent/route taxonomy 仍需在 20 条 development 和双人标注中验证；当前是可执行假设。
3. 本轮没有 endpoint、完整样本、runner 或 API 结果，因此不能判断 GPT-6 Luna 的实际能力。

## Fixes applied

| Finding | 修复 |
| --- | --- |
| Architecture | 用固定 `capability_state` 替代自由文本 handler；分离 dataset、builder、backend adapter、scorer 和 operator 所有权；standalone runner 不导入 PAOS 控制/执行模块。 |
| Correctness | 增加单值 route tie-break、双人 evaluation 复核与 API 前裁决、intent/route 兼容矩阵和 capability 约束；所有冲突只报告，不修正预测。 |
| Recovery/idempotency | 增加 `run_id/case_id/logical_request_id/attempt_index`、有限 transport retry、第一个完整有效响应选择、resume skip 与 supplemental-run 规则。 |
| Safety | synthetic-first、`synthetic:` task namespace、真实样本人工选择/脱敏、无 PAOS 写连接、单 endpoint host、无 handler 映射和无凭据输出。 |
| Extensibility/compatibility | 增加薄 backend adapter、`decision_backend/endpoint_kind/response_schema_version`；route policy 独立为 JSON，provider 缺失字段记 unavailable。 |
| Observability/maintainability | 增加 requests/attempts/responses/predictions/environment 分层记录、完整 per-attempt 字段、错误分类与 rerun/compare CLI 契约。 |
| AgentLoop autonomy/convergence | route 定义为 proposal；显式命令绕过；每入站 turn 一次判断；System 2 接收原始输入且不回环；新增简单路径覆盖、System 2 比例、兼容性和稳定性指标。 |

主要修复位置：

- 固定能力状态与标签规则：`DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md:L48-L163`
- 标注与关键对照：`DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md:L165-L211`
- backend/API 契约：`DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md:L213-L294`
- 阶段、恢复与幂等：`DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md:L296-L363`
- 指标与结论：`DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md:L365-L414`
- 可观测、安全与 AgentLoop：`DECISIONS_INTENT_ROUTING_CAPABILITY_VALIDATION_PLAN_20261009.md:L416-L483`
- 诊断中的未来边界：`DECISIONS_INTENT_ROUTING_DIAGNOSIS_20261009.md:L25-L28,L90-L96,L118-L129`

## Seven dimensions after fixes

1. **Architecture / 架构：方案级通过。** System 1 只消费 provider-neutral 输入并给出预测；
   PAOS 状态、任务、执行和 handler ownership 未复制。实验组件的输入、调用、评分和操作职责分离。
2. **Correctness / 正确性：方案级通过。** 单值 gold、family split、双人 evaluation 复核、兼容矩阵
   与状态约束形成可评分契约；scorer 不改模型答案。实际标签质量仍需样本创建后验证。
3. **Recovery and idempotency / 恢复与幂等：方案级通过。** 逻辑 request 与 transport attempt 分离；
   timeout retry、resume、terminal failure 和 supplemental run 不会重复污染基础预测。
4. **Safety / 安全：方案级通过。** synthetic-first standalone runner 没有 PAOS 写连接或 handler
   映射；真实消息需要选择和脱敏；凭据不落盘。当前没有 runtime、安全门禁或现场任务变更。
5. **Extensibility and compatibility / 扩展与兼容：方案级通过。** taxonomy/scorer 与 backend adapter
   分离，可在不改标签的情况下比较 Luna 与后续 provider；confidence 语义不跨 provider 假定。
6. **Observability and maintainability / 可观测与可维护：方案级通过。** 每个 run 能追溯数据、题目、
   policy、backend、环境、请求、attempt、原始响应、预测、指标和错误；旧输出不覆盖。
7. **AgentLoop autonomy and convergence / 自主与收敛：方案级通过。** Decisions 只给一次入口提议，
   显式命令和现有 owners 保持权威；System 2 不丢原消息、不回到 Decisions；全量 system2 会被
   coverage/算术对照识别为无简单路由价值。

## Validation

本轮只做文档和静态结构验证，不调用付费 API：

- UTF-8、Markdown fence、本地链接和嵌入 JSON 语法。
- 7 个 intent 与 5 个 route choice 唯一；20/60/80 样本表与 80/110 请求预算一致。
- 兼容矩阵覆盖全部 intent；恢复字段、安全边界、可观测字段和未来 AgentLoop 原则存在。
- `CHANGELOG.md` 最近五条与月度归档全文一致；`git diff --check` 通过。

## Remaining limitations

- GPT-6 Luna endpoint、访问权限与代理协议待用户提供。
- 80 条样本和第二名 evaluation 审阅者尚未创建/指定。
- runner、backend adapter、scorer 和输出目录尚未实现。
- 没有实际 accuracy、latency、usage、cost、confidence 或稳定性结果。

结论：原方案的七个 Major 设计缺口已在文档中修复；当前状态适合进入“创建样本与独立
runner”的下一阶段，不支持直接替换 PAOS 现有入口路由。
