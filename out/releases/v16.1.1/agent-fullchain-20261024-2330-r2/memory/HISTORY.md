[2026-10-24 23:35 CST] 原场景全链路仿真验收：停止在视觉身份/功能点与几何资格检查阶段，未创建 AgentTask/semantic_subtasks，未执行任何 Action、抓取、倾倒、搅拌或归位。不是全链路验收通过。

## 用户请求与保留参数
- 首次 scene.observe 单次请求 sensor_refs=[sensor://tabletop_third_person,sensor://label_inspection_r01]，max_age_ms=1000，省略 max_capture_skew_ms 以保留契约默认 50。
- 目标顺序：视觉标签 R01 倾倒到唯一目标烧杯，R02 倾倒到同一烧杯，再用实际识别的搅拌棒搅拌归位。每个操作包含 acquire/process/return。
- 两次 pour 参数均为 tilt_rad=0.87, hold_s=0.6。stir 参数 radius_m=0.009, depth_m=0.04, turns=2, duration_s=4, direction=ccw。
- 不以相机名、固定位置、资产信息代替视觉身份；不放宽检查。未来只有合格才通过 semantic_subtasks 与 Runtime 执行，verification.mode=off；无液体模型，不报告转移体积或化学混合质量。

## 实际阶段记录
1. scene.observe context ready=true。最初 context 未列出 sensor_refs；助手在早期叙述称其仅列第三人称不准确。随后 scene.understand context 才明确列 sensor_refs=[sensor://tabletop_third_person]。此列表不是对另一相机不存在的证明。
2. 按指定参数执行双视图 observe。Gateway 包装 ok=true，但业务 status=unavailable，error.code=capture_skew_exceeded，message=observation set exceeds max_capture_skew_ms。observation_ref=observation://unknown/unknown，scene_revision/frame=unknown，calibration_ref=null，artifacts=[]，未返回可用 views。失败返回 capture_skew_ms=0 不能当成同步合格或实际偏差测量；实际超限偏差数值未知。未放宽 50 ms。
3. 单独第三人称 observe（只读诊断，不替代双视图）：available，freshness_ms=399，scene_revision=labutopia-tabletop-rod-rack-v1:39af844398e3440d9f3aef235f2f3295:0，observation_ref=observation://labutopia-tabletop-rod-rack-v1:39af844398e3440d9f3aef235f2f3295:0/tabletop_third_person，calibration_ref=artifact://labutopia/calibration/709d4e04460f4cbe93e2a9bc679cdf28.json。
4. 第三人称 scene.understand 返回 available，但不能代表动作资格通过。检测输出 8 个 reagent_bottle、1 个 mixing_vessel、1 个 stir_tool，另有试管；这是本次检测结果，不是预设数量。entities 未返回可读标签，relations=[]，spatial_envelopes=[]。
5. 单独标签相机 observe（只读诊断）：available，freshness_ms=235，与上述 scene_revision 相同；observation_ref=observation://labutopia-tabletop-rod-rack-v1:39af844398e3440d9f3aef235f2f3295:0/label_inspection_r01；calibration_ref=artifact://labutopia/calibration/0329dfcbba36408cb9746c4741199f05.json。
6. 标签相机 scene.understand available：1 个 reagent_bottle，entity://observed-d38b9ed8de8946c2b55459e68afae2a3，confidence=0.96。逐字返回文字如下（保留换行）：
```
R01    LAB REAGENT
蒸馏水
Distilled water
H2O
Simulation reagent
```
视觉文字来源 artifact://labutopia/rgb/6c209c2aac9d47cfa377e555e5f469c0.png。R01 文字识别成功不代表瓶口可用，也不建立与第三人称检测瓶的执行关联。R02 未可靠识别。
7. 最终：资格不足，保留诊断停止。动作执行数量=0；没有 Runtime 物理过程测量，没有用户级成功/归位完成结论。

## 第三人称理解返回的每项 ambiguity（均为 visual_object_unresolved）
- 标签可见，但完整文本（含小角标）无法在该分辨率可靠读取；转写为 null，未根据标签颜色推断化学身份。
- 机器人后方的大瓶严重遮挡；可识别玻璃表面，但标签及完整轮廓不可辨。
- 试管互相及与支架重叠；表观 6 支中左中两支区分不确定。
- 搅拌棒可见，但工作端无法可靠区分，棒端 process evidence 不可用。
- 试管口小且重叠，rim landmarks 不可用。
- entity://observed-ad42ef3284434660a9b9f808d70edd61（瓶）：process landmark is outside the instance mask。
- entity://observed-0b84b6abe3924a4db47a0c9a031ee7f2（瓶）：process landmark is outside the instance mask。
- entity://observed-ad4f3bf6cf074d658b4e0f743c41d077（瓶）：process landmark is outside the instance mask。
- entity://observed-d42c826007d34f0cb11e6c3402be8b8d（瓶）：process features require explicit image landmark support。
- entity://observed-959d8b607c8d4865bf3b370493545151（瓶）：observed rim fit or angular coverage is insufficient。
- entity://observed-771bdff98c774d5a9ba484f9887523c2（瓶）：observed rim fit or angular coverage is insufficient。
- entity://observed-bc671a5d140b438a9c1d1af08997e36c（瓶）：observed rim fit or angular coverage is insufficient。
- entity://observed-37da7557ce944522aa7c50cace35b41b（瓶）：process landmark is outside the instance mask。
- entity://observed-44cea568fed04e239ce67a2068334dbe（mixing_vessel）：process landmark is outside the instance mask；检测到唯一该类别不等于杯口几何合格。
- entity://observed-bd71c8a5acaf4fd5b68a65fdf85a99eb（试管）：process features require explicit image landmark support。
- entity://observed-371ab1f54f4c457aab9cd522f04dc216（试管）：process features require explicit image landmark support。
- entity://observed-522a7ab0d4ff432997523a19eaffc84a（试管）：process features require explicit image landmark support。
- entity://observed-df286dd06aa44a12974238f1e9e3b408（试管）：process features require explicit image landmark support。
- entity://observed-8e9937c210f4497294d816ae3fcc8c24（试管）：process features require explicit image landmark support。
- entity://observed-efaf57f68b98403197384eff57c9c8ba（试管）：process features require explicit image landmark support。
- entity://observed-89a2c50a75cf4ac8a046a5b16904a35c（搅拌棒）：process features require explicit image landmark support。

## 标签特写理解返回的每项 ambiguity（均为 visual_object_unresolved）
- 左上、上中、右上裁切的容器样碎片不能可靠判定为独立试剂瓶/烧杯/试管，也可能是透过前景玻璃看到的物体。
- entity://observed-d38b9ed8de8946c2b55459e68afae2a3：process features require explicit image landmark support。
- 派生 instance mask：artifact://labutopia/instance-mask/7fef70643780448d904a4f1ff26faa34.npy，1280x960，bbox=[255,0,1023,959]，foreground_pixels=580662。
- 派生 object point cloud：artifact://labutopia/object-point-cloud/93a3dbb1525949dc84770cba2b63cf4e.npy，point_count=200000；有点云不等于口部几何合格，spatial_envelopes=[]。

## 审计/证据限制
- 两个成功 observe 的可见摘要把 artifacts 压缩为 [{},{},{}]，也未展示 views/captured_at 等完整字段。后续 understand 输入使用了未在先前可见摘要展开的引用与时间；这些输入的来源链在本次可见日志中无法独立验证，不能描述为已验证的原始观测复制。特写 understand 响应后来明确返回了 RGB/depth/point_cloud/views 来源，第三人称响应仍未展开相同信息。未来应通过可审计 Query 记录精确复制字段，不重建或猜测引用。
- 标签特写 understand 回显 RGB=artifact://labutopia/rgb/6c209c2aac9d47cfa377e555e5f469c0.png，depth=artifact://labutopia/depth/3be336eaff0e49e0ac29cbb75688eccb.npy，point_cloud=artifact://labutopia/point_cloud/82b8fece23a548a6a7195d88db2ae0df.npy，captured_at=2026-10-24T15:33:57.873961Z。
- 所有识别结论为 scene.understand 工具报告；助手未另行直接打开图像作独立人工视觉核对。禁止把工具调用成功等同于身份/功能点合格，禁止把文字识别成功等同于动作执行成功。
