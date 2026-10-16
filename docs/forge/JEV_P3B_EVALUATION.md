# JEV P3b 离线专项评测 / Offline Specialized Evaluation

本评测器只读取已采集、独立标注的 JSON 数据和配对测量，不启动 Agent Runtime，不调用 Gateway、
Query、Action、Session、相机、仿真或机械臂，也不自动修改 `mode=active` 配置。它输出普通验收报告；
操作员只有在报告 `active_eligible=true` 且数据来源和授权另行确认后，才可引用报告路径配置
`acceptancePolicyRef`。

The evaluator reads recorded, independently labeled JSON data and paired measurements only.
It starts no Agent Runtime, calls no Gateway/Query/Action/Session, camera, simulator, or robot,
and never changes a decision point to `active`. It produces an ordinary acceptance report;
an operator may reference that report through `acceptancePolicyRef` only after confirming its
provenance and authorization and only when `active_eligible=true`.

## 输入 / Inputs

配置使用 `jev_decision_evaluation_config_v1`，相对路径从配置文件所在目录解析：

```json
{
  "version": "jev_decision_evaluation_config_v1",
  "dataset": "dataset.json",
  "measurements": "measurements.json",
  "output_root": "runs",
  "acceptance_policy_ref": "artifact://jev-policy/query-v1",
  "splits": ["held_out"],
  "repetitions": 1
}
```

数据集使用 `jev_decision_evaluation_dataset_v1`。除 case 外，必须记录 `sampling_plan_ref`、
`labeling_protocol_ref`、`labeler_id`、独立的 `reviewer_id` 和预先确定的
`planned_held_out_cases`；正式 held-out 还必须提供相对数据集目录可读取的
`provenance_manifest_ref`。每条 case 必须声明 `case_id`、
`calibration|held_out` split、近重复隔离用的 `family_id`、类别、`decision_input_ref`、目标、
脱敏后的最小必要事实、完整候选 ID/描述、来源 `provenance_refs`，以及正确候选或 `must_escalate=true`。同一 family
不得跨 calibration/held_out。正式 held-out 集至少覆盖：

- `multi_entity`
- `multi_method`
- `no_applicable_option`
- `cross_scene`
- `illegal_combination`
- `complex_planning`

测量使用 `jev_decision_measurements_v1`。正式数据必须设置 `evidence_mode=measured`，并记录实际
provider、requested model、服务报告的 model version，以及配对 System 2 的 provider/model/version；
还要用与 case 完全相同的 `decision_input_ref` 记录 provider/host outcome、选中 ID、是否调用
System 2、JEV+fallback 决策总时延、同输入/同版本 System-2-only 时延，以及单列的 Tool/操作员等待。
provider 的 selected/escalate/unavailable/timeout/invalid 都留在总请求分母。数据集只保存评测所需的
脱敏最小事实，不得放入凭据或完整现场来源载荷。
只有宿主已持久化 selection 的记录才能携带 `decision_trace_ref`；接受记录不得同时声明调用了
System 2。

## 运行 / Run

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/evaluate_jev_decisions.py \
  --config /path/to/jev-p3b/config.json
```

Smoke 可使用 `--max-cases N`，但部分 case 运行永远不具备 active 资格。每次运行写入唯一 UTC
时间戳目录，不覆盖旧结果：

```text
<output_root>/<timestamp>-<nonce>/
  input_config.json
  input_dataset.json
  input_measurements.json
  run_manifest.json
  metrics.json
  acceptance_report.json
```

三个 `input_*.json` 文件固化本次实际解析的配置、数据集和测量，避免源文件随后修改导致报告无法复核。
manifest 保存 Git commit、数据集名称/版本、原始配置和测量路径、acceptance policy、split、重复数和 case ID；metrics
保存候选覆盖、raw 选择正确率、策略接受率、错误接受、必须升级召回、实际替代率、均值/p95
配对时延，以及 Tool/操作员等待。不同运行通过 `dataset_version`、provider/model version、commit
和 `selected_case_ids` 对齐比较。

## 配对前审计 / Pre-pairing audit

在发送任何 JEV 或 System-2 请求前，可以先对冻结候选生成的
`jev_decision_evaluation_dataset_v1` 运行只读 readiness audit：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/audit_jev_held_out_intake.py \
  --dataset /absolute/path/to/dataset.json \
  --output-root /absolute/path/to/intake-audits
```

该命令只读取数据集并写入唯一 UTC 目录，输出 `audit_report.json`、
`input_dataset.json` 和 `run_manifest.json`。它检查 held-out 样本、六类覆盖、
计划样本数、复核者身份元数据、`decision_input_ref` 唯一性和完整候选覆盖；失败时退出 2，
不读取凭据、不调用 JEV/System-2，也不产生 `active_eligible`。

`reviewer_identity_distinct` 只表示数据集中的 labeler/reviewer ID 不同，不能替代
未参与采集和标签编写的人工复核确认。审计会读取 `labeling_protocol_ref` 指向的本地 JSON，
要求 `status=completed`、`independent_review=true`、复核者身份匹配且覆盖全部 held-out case；
只改两个 ID 或只写自审说明不会通过。审计还会读取 `provenance_manifest_ref`，要求每条 case 的
`provenance_refs` 与 manifest 一致，并明确 `raw_free_text_uploaded=false`。远程 `artifact://` URI
本身不是本地 provenance 确认。

当前 `20261016-size-ranking-wide/intake_result.json` 仍是候选 intake manifest，
不是完整的 `jev_decision_evaluation_dataset_v1`，因此不能跳过标签冻结和独立复核直接运行正式配对。

## active 资格 / Active eligibility

报告只在以下条件全部满足时给出 `active_eligible=true`：

- `evidence_mode=measured`，完整 held-out case，无部分选择，且记录独立标注复核；
- 可读取的独立复核记录已完成并覆盖全部 held-out case，且 provenance manifest 映射完整、标记为已脱敏；
- calibration/held-out family 隔离且六类必需场景齐全；
- 每个 case/repetition 都有且仅有一条配对测量；
- 每条配对测量的 `decision_input_ref` 与标注 case 一致，且报告记录 acceptance policy；
- 所有记录包含真实 model version，且一次正式报告只含一个 provider/model/version；
- 可替代样例包含正确完整候选；
- 错误接受数为 0，所有必须升级样例实际进入 System 2；
- 至少存在一个正确接受且真实免去 System 2 的样例；
- JEV+fallback 决策总时延均值下降，p95 不恶化。

报告为候选覆盖、raw 选择、策略接受、错误接受、必须升级召回和实际替代率提供实际分母及
Wilson 95% 区间；错误接受为 0 也只表示观测到的样本没有错误，不把上界写成零风险。

fixture、缺失类别、缺失配对、错误接受、全量弃权、部分运行或缺少真实 model version 都会输出
明确的 `active_ineligibility_reasons`。fixture 可用于 CLI/统计 smoke，但不产生 active 证明。
