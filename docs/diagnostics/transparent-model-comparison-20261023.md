# 透明/玻璃锥形瓶模型对比诊断

日期：2026-10-23（Asia/Shanghai）  
范围：同一 `tabletop_third_person` 观测、同一 RGB/原始深度/实例分割/标定，比较未接入透明几何模型的原始深度基线、ReMake，以及 DFNet 的实际可用状态。报告只使用已有观测 artifact，不读取 USD/仿真真值回填几何。

## 结论摘要

本次目标是 `mixing_vessel` 类锥形瓶，选取回放中置信度最高、位置最适合作为工作流目标的实例：`entity://observed-45e51b6def3b416da8ef696395dad39c`，mask 框 `[774,603,829,695]`，置信度 0.99。它是场景理解类别，不代表系统已通过瓶型/身份真值验证。

| 路线 | 当前结果 | 直观判断 | 选型含义 |
|---|---|---|---|
| 未接入透明模型：原始 RGB-D / raw depth | RGB 中能看到目标并得到 mask，但 mask 内深度 q05/q50/q95 为 2.019/2.043/2.069 m；历史回放 mask→深度点云为 3,213 点 | 深度集中在远背景区，不能据此确认瓶体表面 | raw-depth 基线可复现，但玻璃瓶体几何仍无可靠证据 |
| ReMake | 同一目标生成 4,100 点的 object point cloud；深度 q05/q50/q95 约 0.739/0.830/1.205 m；该锥形瓶没有抓取候选（当前探针把 mixing vessel 排除为抓取源） | mask 内有连续的恢复深度和点云；不把别的物体候选借给它 | 作为下一轮主候选验证；仍需几何误差/瓶口功能点验证 |
| DFNet | `dfnet-r2-20261023-a` 在 understanding 阶段失败，缺少 DFNet checkpoint | 没有可比较的模型输出 | 不能把 DFNet 判定为效果差，先补齐权重并重跑同一输入 |

**当前建议：** 如果必须先选一个继续工程验证，选 ReMake；理由是它在同一输入上留下了恢复深度和逐物体点云，且该实例的局部几何提取可复现。这个选择表示“下一轮验证优先级”，不表示 ReMake 已通过玻璃几何精度或可执行抓取验收。

## 全景中间结果

![全景模型对比](assets/transparent-model-comparison-20261023/panorama-model-comparison.png)

全景图从左上到右下依次为：RGB 与全部实例 mask、raw depth、ReMake depth、用于恢复的多实例 union mask、原始整帧点云投影、ReMake 逐物体点云投影。颜色只用于显示深度/点云结构，不代表真值误差。

## 工作流目标锥形瓶

![目标锥形瓶对比](assets/transparent-model-comparison-20261023/target-conical-flask-comparison.png)

目标对象引用：`entity://observed-45e51b6def3b416da8ef696395dad39c`。像素框为 `[774, 603, 829, 695]`，mask 像素数为 `4,100`。

图中八个面板依次展示：

1. RGB 与目标实例 mask；
2. 同一 mask 内的原始深度基线；
3. ReMake 恢复深度；
4. `ReMake - raw` 的诊断差异；
5. raw-depth 与 ReMake 目标点云并排投影，采用共同相机坐标显示范围；
6. 当前目标候选状态；该锥形瓶在这条探针工作流中是容器，被排除在抓取源之外，因此没有对应 GraspNet 候选；
7. DFNet 运行状态，明确标出缺 checkpoint、无模型输出；
8. 预留空白面板，不承载推断信息。

候选不是执行结果：当前 `process_preparation` 仍为 `unavailable: geometry/feature qualification remains unverified`，没有启动运动。

## 目标对象数值对比

| 指标 | Raw depth 基线 | ReMake |
|---|---:|---:|
| mask 像素 | 4,100 | 4,100 |
| 深度 q05 / q50 / q95（m） | 2.019 / 2.043 / 2.069 | 0.739 / 0.830 / 1.205 |
| 几何点数 | 历史回放 `replay-cloud-7.npy`：3,213 | 4,100 |
| 几何状态 | 历史回放成功提取局部 geometry/features；深度统计仍集中在约 2.04 m | `unverified_estimate`, `visible_surface` |
| GraspNet 候选 | 不适用：该锥形瓶不是抓取源 | 不适用：该锥形瓶不是抓取源 |
| `proposed` 候选 | 不适用 | 不适用 |
| 最高候选分数 | — | — |

Raw depth 与 ReMake 的深度值不应直接被当成“ReMake 误差为多少”：当前没有目标锥形瓶的独立公制真值测量。这里的价值是展示模型是否从原始深度的背景/错误表面中恢复出可供后续点云查询的结构。

## 模型状态与复现证据

- 主对比记录：`out/releases/v16.0.0/remake-r2-20261023-c/perception.json`
- 同帧 RGB：`out/releases/v16.0.0/remake-r2-20261023-c/artifacts/labutopia/rgb/aee040c9364741cdb2242ce505a3f096.png`
- 原始深度：`.../depth/d36b98d9728f4ee284db7b41d7c3b2eb.npy`
- ReMake 恢复深度：`.../recovered-depth/706ec2206c5842fe91494f6520f523a9.npy`
- ReMake 透明区域 mask：`.../transparent-mask/e2aab2850fcf448ba3eef3cf9458f508.npy`
- 目标 mask：`.../instance-mask/7fdff4eebe354d33b593cfb8c8537aa4.npy`
- 目标点云：`.../object-point-cloud/3d699527aefb46b2a02479201b85a40a.npy`
- 目标候选摘要：`assets/transparent-model-comparison-20261023/target-summary.json`
- DFNet 失败记录：`out/releases/v16.0.0/dfnet-r2-20261023-a/perception.json`

本次可视化由 `scripts/render_transparent_model_diagnosis.py` 生成：

```bash
.venv/bin/python scripts/render_transparent_model_diagnosis.py \
  --run out/releases/v16.0.0/remake-r2-20261023-c \
  --out docs/diagnostics/assets/transparent-model-comparison-20261023 \
  --target-index 7
```

## 后续选型顺序

1. 先补齐 DFNet checkpoint，在同一 RGB、mask、标定和 GraspNet 设置下重跑；否则只能比较 raw 与 ReMake。
2. 对目标锥形瓶单独测瓶口、瓶身接触区和深度覆盖率，不用全图平均值替代。
3. 对两个模型使用同一候选采样和准备检查，比较 `proposed` 数量、最高分、候选落点是否覆盖可夹持区域。
4. 只有在独立几何误差和准备资格通过后，才把“候选更多/分数更高”转化为执行模型选择。

