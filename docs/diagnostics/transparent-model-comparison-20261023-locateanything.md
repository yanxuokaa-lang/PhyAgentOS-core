# LocateAnything → SAM2 → RGB-D → GraspNet 对比

日期：2026-10-24（Asia/Shanghai）
范围：同一 `tabletop_third_person` RGB-D 观测、同一 LocateAnything 目标和同一 GraspNet 配置，比较未接入 ReMake 的 raw-depth 基线与接入 ReMake 后的恢复深度。全程为离线 dry-run，未启动机械臂或运动准备。

## 主图

![LocateAnything/ReMake 五行对比](assets/transparent-model-comparison-20261023-locateanything/locateanything-remake-grasp-comparison.png)

左列是 raw-depth baseline，右列是 ReMake。每一行依次为 RGB、LocateAnything→SAM2 分割、深度、目标点云和 GraspNet 抓取位姿。RGB 和 mask 两侧使用同一帧、同一目标；深度、点云和候选只改变几何输入来源。

## 实际流程

1. 输入原始 RGB 为 `1600x1200`。LocateAnything 使用同一 RGB 的 `800x600` 缩放副本和查询 `conical flask`，成功返回 8 个框。
2. 选择右侧大型锥形瓶框 `[498,306,573,442]`（缩放图），映射回原图为 `[996,612,1146,884]`。
3. 用该框调用 SAM2，得到 `25,546` 个前景像素的目标 mask；raw 和 ReMake 两侧共用这张 mask。
4. 使用同一标定反投影：raw depth 和 ReMake depth 各生成 `25,546` 个目标点。
5. 使用同一 GraspNet checkpoint、同一 `12,000` 点输入预算、同一随机种子 `0` 和 `score >= 0.02` 阈值进行离线推理。

## 数值摘要

| 指标 | 未加入 ReMake：raw-depth | 加入 ReMake |
|---|---:|---:|
| LocateAnything/SAM2 mask 像素 | 25,546 | 25,546 |
| 深度 q05 / q50 / q95（m） | 1.706 / 1.842 / 2.191 | 0.715 / 0.835 / 1.097 |
| 目标点云点数 | 25,546 | 25,546 |
| GraspNet 解码候选数 | 915 | 259 |
| GraspNet 保留候选数 | 32 | 32 |
| 最高分 | 1.000 | 1.000 |

候选分数是 GraspNet 的模型分数，不是碰撞通过、几何真值误差或可执行授权。当前报告只展示候选，不调用 `manipulation.prepare`，不执行动作。

## 复现产物

- 主图：`assets/transparent-model-comparison-20261023-locateanything/locateanything-remake-grasp-comparison.png`
- LocateAnything 响应：`assets/transparent-model-comparison-20261023-locateanything/locateanything-response.json`
- SAM2 mask：`assets/transparent-model-comparison-20261023-locateanything/target-mask.npy`
- raw 目标点云：`assets/transparent-model-comparison-20261023-locateanything/raw-target-point-cloud.npy`
- ReMake 目标点云：`assets/transparent-model-comparison-20261023-locateanything/remake-target-point-cloud.npy`
- raw GraspNet 候选：`assets/transparent-model-comparison-20261023-locateanything/raw-grasps.json`
- ReMake GraspNet 候选：`assets/transparent-model-comparison-20261023-locateanything/remake-grasps.json`
- 数值摘要和全部保留候选：`assets/transparent-model-comparison-20261023-locateanything/comparison-summary.json`
- 运行配置：`assets/transparent-model-comparison-20261023-locateanything/run-config.json`

复现命令：

```bash
./.venv/bin/python scripts/render_locateanything_remake_grasp_comparison.py \
  --rgb out/releases/v16.0.0/remake-r2-20261023-c/artifacts/labutopia/rgb/aee040c9364741cdb2242ce505a3f096.png \
  --raw-depth out/releases/v16.0.0/remake-r2-20261023-c/artifacts/labutopia/depth/d36b98d9728f4ee284db7b41d7c3b2eb.npy \
  --remake-depth out/releases/v16.0.0/remake-r2-20261023-c/artifacts/labutopia/recovered-depth/706ec2206c5842fe91494f6520f523a9.npy \
  --calibration out/releases/v16.0.0/remake-r2-20261023-c/artifacts/labutopia/calibration/33764bfa92b143cdb1f815c8d9e646ee.json \
  --mask <sam2-mask.npy> --bbox 996 612 1146 884 \
  --locate-response <locateanything-response.json> \
  --raw-grasps <raw-grasps.json> --remake-grasps <remake-grasps.json> \
  --out docs/diagnostics/assets/transparent-model-comparison-20261023-locateanything
```

## DFNet

DFNet 本轮未完成推理，状态为 `pending_checkpoint`，不是模型效果差。运行环境在 `/home/yanxu/.cache/paos/transparent_geometry/checkpoints/` 只找到 `remake.tar` 和 `depth_anything_v2_vits.pth`，没有配置所需的 `dfnet.tar`；在 `/home`、`/mnt`、`/opt` 与 `/tmp` 的本地文件检查也未找到 DFNet 权重。已有 `out/releases/v16.0.0/dfnet-r2-20261023-a/perception.json` 显示 provider 在 understanding 阶段因权重不可用退出，未生成 DFNet 深度。

本轮还检查了官方 TransCG README 所列的 Google Drive 与 Baidu Netdisk 下载入口。Google Drive 请求在当前运行环境超时；Baidu 分享页可打开，但无登录会话下的提取码校验接口返回错误，未取得文件，也没有启动 DFNet 推理。恢复条件是将官方训练 checkpoint 放到配置路径 `~/.cache/paos/transparent_geometry/checkpoints/dfnet.tar`，再复用本报告的 RGB、LocateAnything 框、SAM2 mask、标定和 GraspNet 参数重跑。获得真实输出前，不应给 DFNet 填入深度、点云或抓取位姿，也不能据此判定模型优劣。
