# Implementation Review v14.12.16 / 七维实现审查

日期：2026-10-20（Asia/Shanghai）
范围：PAOS provider-neutral manipulation target、LabUtopia `pour`/`stir` adapter、CLI dry-run 输入。

## 审查结论

接口集成和 no-motion 安全边界通过；本轮没有把 profile 路径、初始位置或固定姿态重新提升为感知事实。真实 Isaac Sim 的跨场景抓取、IK、碰撞、工具尖端轨迹和目标区域放置仍未在本轮重新执行，因此不能宣称“泛化 live 成功”。

## 七维 Review / Seven Dimensions

| 维度 | 结果 | 证据与边界 |
|---|---|---|
| 架构集成 / Architecture | 通过 | `manipulation_target.py` 是 PAOS 与 provider 的共享边界；engine 只在 Isaac worker 消费 world-resolved target；CLI 通过 `--target` 注入感知 JSON。 |
| 正确性 / Correctness | 通过（静态） | pose、四元数、方向、prim path、scene/frame/calibration identity 均校验；`world_from_control` 显式执行刚体变换；placement 使用 `return_pose` 的位置和姿态。 |
| 恢复与幂等 / Recovery & idempotency | 通过 | 缺失/非法 target 在 backend 前返回 `invalid`，`motion_authorized=false`；没有从 profile 或初始位置补造 target。 |
| 机器人安全 / Robotics safety | 通过（no-motion） | dry-run 不导入或 step Isaac Sim；缺失标定变换、EULA、场景身份或 perception target 不得启动 live；既有 IK、碰撞、workspace、stop 和七阶段结算门禁未放宽。 |
| 扩展兼容 / Extensibility | 通过（接口） | 不同 `/World/...` prim 层级由 target 提供；几何规格由 perception geometry/tool frame 提供；controller 不再从固定 `Cylinder` fallback 推断操作对象。真实不同资产仍需 live 验证。 |
| 可观测性与维护 / Observability | 通过 | dry-run 返回 target 状态和 controller dispatch；live feedback 继续携带 frame/calibration、工具路径、工具尖端和 phase events；CLI 支持复现 target 校验。 |
| AgentLoop 自主性 / AgentLoop autonomy | 通过 | PAOS 仍只公开一个 cycle Action；target 来自 Agent/感知前置结果，adapter 不自行选择对象、抓取姿态、目标位置或重试。 |

## 验证

```text
109 passed, 1 warning
python -m compileall -q examples/forge-adapters/isaacsim_lab/src examples/forge-skills/pick-place-workflow/src
.venv/bin/ruff check examples/forge-adapters/isaacsim_lab/src/isaacsim_lab examples/forge-adapters/isaacsim_lab/tests examples/forge-skills/pick-place-workflow/src/pick_place_workflow
git diff --check
```

测试覆盖 target frame 变换、旋转后的接近方向、缺失 world transform fail-closed、不同目标 pose、控制器参数映射、七阶段协议和发布 contract 一致性。

## 未关闭的 live 边界

1. 需要用包含真实 `manipulation_target`（尤其 `world_from_control`、`grasp_frame`、`tool_frame`、`destination_pose`、`return_pose`）的输入，在 RTX 5060 Ti + Isaac Sim 5.1 对 pour 和 stir 各执行一次。
2. 需要从 artifact 检查 PAOS candidate grasp 是否真实进入 RMPFlow/IK、目标姿态是否进入内部 PlaceController、以及不同玻璃棒几何的尖端轨迹是否满足 radius/depth/turns。
3. 现有 `/home/yanxu/LabUtopia` 用户改动未修改；本轮未把其 controller 改造成工具尖端闭环，因此旧 stir 失败 artifact 仍不能升级为成功。

在完成上述 live 证据前，结论是“provider-neutral 接口和失败闭环已实现”，不是“跨实验室资产的物理泛化已验收”。
