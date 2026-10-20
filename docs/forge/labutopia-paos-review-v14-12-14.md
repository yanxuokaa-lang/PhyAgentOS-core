# LabUtopia `pour` / `stir` PAOS Review and Repair

日期：2026-10-20（Asia/Shanghai）
范围：`examples/forge-adapters/isaacsim_lab` 与 PAOS complete-cycle 投影。
状态：pour live 已通过；stir 接口、反馈和失败闭环已修复，但 LabUtopia 真实 `StirController` 的尖端轨迹仍未达到 PAOS 请求，保留为失败而不是假成功。

## 保存的诊断

本轮审查发现的两个阻断问题来自真实 artifact 的统一 PAOS 重算，而不是控制器是否返回 `done=True`：

1. 旧 `stir` artifact 只有 `stir_angle_rad`、`transform_progress` 和对象路径，没有 PAOS 需要的 `tool_tip_x_m`、`tool_tip_y_m`、`tool_tip_depth_m`、`tool_tip_frame_id`。PAOS `normalize_feedback()` 因此返回 `missing_source_tool_tip_frame_id` 与 `missing_tool_tip_coordinates`，结果必须保持 `unknown`。
2. 旧 `pour` worker 用“达到 profile 下界直到 maximum tilt”判定过程窗口；PAOS 按本次 Action 的 `tilt_rad +/- tolerance` 判定。实测旧结果在 `1.23-1.36 rad`，请求是 `0.87 rad`，所以不能被 PAOS 重算为完成。
3. `turns`、`depth_m`、`duration_s`、`hold_s` 和倾角目标在部分 worker 结算路径中回退到 profile 默认值，调用方改变参数不能可靠改变完成条件。
4. 能力发现只检查 Isaac Sim import，不检查 EULA；在没有 `OMNI_KIT_ACCEPT_EULA` 时不能声明 live execution 或 motion authorization。
5. 真实 stir 控制器以夹爪/cspace 参考点执行圆周运动，而 PAOS 评价的是 `/World/glass_rod/Cylinder` 几何尖端；多次 live A/B 校正后，尖端半径仍约 `0.003-0.101 m`，无法满足请求 `0.009 +/- 0.002 m`，说明控制器末端参考与 USD 尖端姿态没有形成有效闭环。

这些故障不能靠 Git、版本号、类型或普通单元测试发现，因为它们是运行时控制 prim、几何端点、反馈 frame 和 PAOS 评价语义之间的错配。本轮没有增加 hash、冻结 contract 或重复门禁，而是复用既有 PAOS feedback adapter、scene revision 和 capability declaration。

## 修复内容

- `LabUtopiaProfile` 外置并校验工具尖端局部轴、工具尖端 frame、烧杯容器半径/深度、杯口高度、角度步长和半径/深度容差。
- worker 从 `/World/glass_rod/Cylinder` 的 live USD local bound 与 world transform 计算配置轴方向的真实几何端点；把端点转换到烧杯 frame，输出 `tool_tip_*` 字段。无法获得 USD 几何时不输出伪造坐标，PAOS 保持 invalid/unknown。
- `stir` 抓取证据使用 simulator gripper 的实际 attached prim；不再把对象是否仍高于初始位置作为唯一持物证据。
- `pour` 的过程窗口使用当前 Action 的 `magnitude`、`tolerance`、`maximum_tilt_rad` 和 `hold_s`；控制器旋转阶段的时间增量按目标倾角和速度配置。
- `stir` 的 `radius_m`、`depth_m`、`turns`、`duration_s`、`direction` 贯穿控制反馈和七阶段结算。
- preparation/execution 检查 action 的 `scene_revision`；能力发现保留 no-motion preparation，但只有 EULA 已接受时才声明 live execution。
- worker 在 stir 阶段使用实测 `tip - gripper` 偏置校正控制中心；若真实尖端轨迹仍不满足半径、深度、方向、圈数和持续时间，process 明确返回 `failed/stir_observation_not_qualified`。

## 七维验收矩阵

| 维度 | 结果 | 证据 / 边界 |
|---|---|---|
| 能力发现 | 通过 | operation-specific declaration；EULA 未接受时 `execution=false`、`motion_authorized=false` |
| PAOS 参数映射 | 通过 | dry-run 输出当前 Action 的 `tilt/radius/depth/turns/duration/direction`；不再只读 profile 默认值 |
| 单 Action 与任务所有权 | 通过 | 仍由一个 cycle invocation 持有七阶段；worker 内部不创建嵌套 PAOS invocation |
| frame / calibration / scene revision | 通过 | source profile 携带 frame、calibration、container/tool-tip frame；执行前拒绝 stale scene revision |
| 真实反馈 | 通过 | stir 使用附着 prim 和 USD geometry endpoint；缺失 tip feedback 明确 fail-closed；live 失败 artifact 已保留 |
| 七阶段生命周期 | 通过（成功路径）/ stir live 失败路径通过 | 成功路径要求 acquire → transport → process → reorient_exit → stow → release → retreat；stir process 不合格时后续阶段保持 unknown |
| no-motion / 失败闭环 / 安全 | 通过 | dry-run 不 import/step Isaac Sim；EULA、缺失几何、反馈结构错误不会升级为成功 |

## 验证记录

已通过：

```text
90 passed, 1 warning
```

命令：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src \
pytest -q examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-skills/pick-place-workflow/tests/test_cycle_protocol.py \
  examples/forge-skills/pick-place-workflow/tests/test_feedback_adapter.py \
  examples/forge-skills/pick-place-workflow/tests/test_composite_manipulation.py
python -m compileall -q examples/forge-adapters/isaacsim_lab/src
git diff --check
```

两条 dry-run 均返回 `status=prepared`、`motion_authorized=false`；`pour` dispatch 为 `PourController`，`stir` dispatch 为 `StirController`。当前聚焦测试为 `39 passed, 1 warning`；warning 是仓库已有的 pytest `asyncio_mode` 配置警告。

## Live 结果

- pour 既有验收仍通过：`/home/yanxu/LabUtopia/outputs/paos-pour-cycle/paos-live-result-20261019.json` 与对应视频，七阶段完成。
- stir 最新 live artifact：
  - JSON：`/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.json`
  - 视频：`/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.mp4`
  - 反馈：`1,404` 条，视频 `1,403` 帧；acquire/transport 完成，process `failed/stir_observation_not_qualified`，后续阶段 unknown。
  - process 段真实尖端半径约 `0.0033-0.1003 m`，深度约 `0.0305-0.0470 m`；请求半径 `0.009 m`，所以 PAOS 不接受成功。
- 这不是 PAOS 容差问题，也不是 dry-run 失败；必须修复 LabUtopia 控制器的末端参考/姿态或改为直接控制工具尖端后，才能重新宣称 stir live 成功。

## Remaining Live Work

下一步应在 LabUtopia 控制器边界修复末端参考：将圆周目标从夹爪参考点改为实际 `Cylinder` 尖端的姿态变换/IK 目标，再重新运行同一 profile。当前 artifact 已证明 adapter 会拒绝不合格尖端轨迹，旧 artifact 也不会被改写为成功。
