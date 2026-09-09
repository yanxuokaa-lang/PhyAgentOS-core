# 多次抓放修复状态 / Multi-pick-place repair status

日期 / Date: 2026-09-09. Version: v7.6.0.

本记录承接两轮诊断，记录实际代码修复。完整多物体 Agent 接入尚未交付；原有单次仿真成功证据保持原范围。
This record follows the two design reviews and describes implemented repairs. Full multi-object Agent integration remains unfinished; previous single-route simulation evidence keeps its original scope.

## 已实现 / Implemented

1. Planning 的失败、取消、停止结果保留效果是否开始、结果是否已知、现场版本及证据。只有显式 `world_change_started=false` 才可产生 `cancelled_before_start`；未知效果进入 `outcome_unknown`。
   Planning preserves effect-start, outcome knowledge, scene and evidence on unsuccessful execution. Before-start cancellation requires explicit no-effect evidence.
2. Gateway `data.result.capability_outcome_summary` 被投影到节点结果；动作的 `artifact_refs`、failure owner/code 不再丢失。节点内连续现场更新使用持久执行记录顺序中的最新版本。
   Nested Gateway summaries and artifacts reach node settlement; sequential scene updates retain the latest persisted revision.
3. 当前资源快照覆盖旧快照，空集合表示释放；新场景淘汰旧几何证据及条件。已开始效果但无新现场时等待观测。完整历史记录仍保留。
   Current resource snapshots replace earlier snapshots, scene changes retire old evidence, and unobserved effects require a fresh observation. Durable history is retained.
4. 历史完成节点不因后续现场变化自动失效；仍拒绝把旧前驱证据直接作为当前 required evidence。声明了 produced evidence 的义务必须提供这些证据才可成功。
   Historical completion survives scene progression, while direct reuse of stale required evidence remains rejected. Declared produced evidence is required for completion.
5. 语义图保存 entity/destination 输入绑定。经验记录接受正式 off/audit/enforce/recovery 模式，并保留旧 report 读入兼容。
   Semantic graphs persist entity/destination bindings. Experience records accept canonical verification modes and retain legacy report compatibility.
6. 通用 Runtime 对没有无效果证明的 cancel/stop 返回 unknown，并保留证据；明确 no-motion 的测试端点仍可取消。此修复不构成真实 provider 停止实现。
   Generic Runtime reports unknown for unconfirmed cancellation/stop while retaining evidence. Explicit no-motion endpoints retain cancellation behavior; this is not a physical stop driver.

## 六维代码检查 / Six-dimension code review

| 维度 / Dimension | 本次修复 / Repair | 剩余接入事项 / Remaining integration |
| --- | --- | --- |
| 架构集成 / Architecture | 复用 Planning、Coordinator 记录及 Runtime，无第二调度器 | 动态 Tool policy 与真实 Bundle 接线 |
| 失败路径 / Failure paths | 失败效果、取消未知及证据保留有回归测试 | provider poll/cancel、重启对账 |
| 权限安全 / Authority and safety | 无新硬件执行入口；未知现场阻断旧几何准入 | 持物 ownership、跨 acquire/place 占用与停止确认 |
| 配置复现 / Configuration | 无新增设备路径和阈值；测试命令如下 | 持久仿真 profile 与模型环境验收 |
| 可维护性 / Maintainability | 共享响应投影，兼容旧模式；保留既有安全条件 | 完整 semantic obligation completion policy |
| 可观察性 / Observability | 嵌套效果和 artifact refs 进入 settlement | 持久场景及多物体物理证据 |

对本次修复已做六维检查；不能把它视为整个接入方案的最终验收。R1/R2/R3/R6 及 R4 的真实停止接续仍需完成。
The repairs received six-dimensional review. This is not final acceptance of the full integration: R1/R2/R3/R6 and physical stop continuation in R4 remain open.

## 验证 / Validation

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin \
  tests/test_planning_module.py tests/test_planning_loop.py \
  tests/test_tui_long_horizon.py tests/test_planning_effect_recovery.py \
  tests/test_gateway_dora_no_motion_conformance.py \
  examples/forge-skills/pick-place-workflow/tests \
  examples/forge-adapters/robotwin20/tests
```

工作区结果：701 passed, 1 skipped。包含既有未提交 adapter 改动；不等于单独 commit 的仿真验收。本轮未运行模型、SAPIEN 运动或硬件。
Workspace result: 701 passed, 1 skipped, including existing uncommitted adapter changes. This is not isolated-commit simulation acceptance. No model, SAPIEN motion or hardware was run in this repair batch.

暂存区独立副本复测 / Isolated staged-tree validation: **699 passed, 1 skipped** using the same command; no dependency on the two additional uncommitted adapter tests.
