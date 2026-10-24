# 透明材质深度恢复模型对比汇报

日期：2026-10-24
场景：`tabletop_third_person`；目标：右侧大型锥形瓶
流程：LocateAnything → SAM2 → raw/ReMake 深度 → 点云 → GraspNet

## 1. 目的

在同一帧 RGB-D、同一目标和同一抓取配置下，对比未加入 ReMake 与加入 ReMake 后的中间结果，评估玻璃锥形瓶的深度恢复如何影响点云和抓取候选。DFNet 计划使用同一流程作为第三个模型对照，但本轮没有获得权重，因此没有 DFNet 推理结果。

## 2. 对比图

![目标锥形瓶五行对比](../diagnostics/assets/transparent-model-comparison-20261023-locateanything/locateanything-remake-grasp-comparison.png)

左列：raw-depth baseline。

右列：ReMake。

从上到下：RGB、LocateAnything→SAM2 分割、深度、目标点云、GraspNet 抓取位姿。两侧的 RGB 和分割完全相同，差别从深度恢复开始。

## 3. 实验设置

- RGB 原始尺寸：`1600x1200`。
- LocateAnything：`nvidia/LocateAnything-3B`，revision `c32291ca5e996f5a7a485845b4f57a233936bba0`，输入缩放到 `800x600`，查询词 `conical flask`，seed `0`。
- 目标框：缩放图 `[498,306,573,442]`，映射到原图 `[996,612,1146,884]`。
- SAM2：`sam2.1_hiera_l.yaml`，`sam2.1_hiera_large.pt`。
- GraspNet：`checkpoint-rs.tar`，点数预算 `12,000`，score threshold `0.02`，seed `0`，保留上限 `32`。
- 运行方式：离线 dry-run；没有调用 `manipulation.prepare`，没有执行机械臂动作。

## 4. 结果

| 项目 | Raw-depth | ReMake |
|---|---:|---:|
| SAM2 mask 像素 | 25,546 | 25,546 |
| 深度 q05 / q50 / q95（m） | 1.706 / 1.842 / 2.191 | 0.715 / 0.835 / 1.097 |
| 目标点云点数 | 25,546 | 25,546 |
| GraspNet 解码数 | 915 | 259 |
| GraspNet 保留数 | 32 | 32 |
| 最高候选分数 | 1.000 | 1.000 |

Raw-depth 点云主要落在较远的背景/错误深度区间；ReMake 点云在目标区域形成更连续的近距离结构。当前没有独立的锥形瓶公制真值，因此不能把深度差直接写成模型误差。

## 5. 错误原因和修复

### 5.1 LocateAnything 原图推理显存不足

1600x1200 原图直接推理时，模型已经占用大部分显存，推理峰值还需要约 5.93 GiB，剩余显存约 5.92 GiB，触发 CUDA OOM。模型缓存完整，权重没有被删除。

修复方式：用同一 RGB 的 800x600 缩放副本运行 LocateAnything，再按 2 倍坐标映射回原图。缩放推理成功返回 8 个候选框。

### 5.2 旧探针没有锥形瓶抓取位姿

旧探针把 `mixing_vessel` 视为容器，排除在抓取源之外，因此之前图中候选数为 0。这不是 GraspNet 模型没有输出，而是探针的对象资格规则没有对该目标发起查询。

本次对照绕开运动准备，仅把 LocateAnything/SAM2 目标点云分别送入同一个 GraspNet Provider，得到 raw 与 ReMake 的离线候选。候选不具备执行授权。

## 6. DFNet 状态

当前检查 `/home/yanxu/.cache/paos/transparent_geometry/checkpoints/`，只有 `remake.tar` 和 `depth_anything_v2_vits.pth`，没有 `dfnet.tar`；同时在 `/home`、`/mnt`、`/opt` 和 `/tmp` 的本地文件检查中未找到 DFNet checkpoint。已有 `out/releases/v16.0.0/dfnet-r2-20261023-a/perception.json` 记录了 DFNet 在 understanding 阶段因 provider failure 退出，未产生模型输出。

本轮尝试访问 TransCG 官方 README 列出的 Google Drive 和 Baidu 下载入口。Google Drive 请求超时；Baidu 分享页可以打开，但提取码校验接口返回失败。权重没有下载，DFNet 没有运行。这是下载/权重缺失导致的实验阻塞，不是 DFNet 的效果结果。恢复条件：取得官方训练权重并放到 `~/.cache/paos/transparent_geometry/checkpoints/dfnet.tar`，随后复用本报告同一输入、mask、标定及 GraspNet 配置完成第三列对照。

因此目前不能用 DFNet 与 ReMake 做公平数值比较，也不能据此判定 DFNet 效果好或差。补齐 DFNet 权重后，必须复用本报告的 RGB、目标框、SAM2 mask、标定、GraspNet checkpoint、点数预算和阈值，追加一列 DFNet 深度、点云和抓取位姿。

## 7. 当前选择结论

在现有证据范围内，ReMake 是唯一完成了同目标深度、点云和 GraspNet 对照的透明几何模型，可以作为下一轮工程验证的暂定选择。这个结论不是最终模型定型：DFNet 尚未完成同场景推理，且两种模型都还缺少独立几何真值和运动准备验证。

## 8. 产物

- 主图：`docs/diagnostics/assets/transparent-model-comparison-20261023-locateanything/locateanything-remake-grasp-comparison.png`
- LocateAnything 响应：`locateanything-response.json`
- SAM2 mask：`target-mask.npy`
- raw/ReMake 点云：`raw-target-point-cloud.npy`、`remake-target-point-cloud.npy`
- raw/ReMake GraspNet 候选：`raw-grasps.json`、`remake-grasps.json`
- 汇总：`comparison-summary.json`
- 配置：`run-config.json`
