# 双线并行推进计划

## Context

两条线同时推进：**实验室仿真线**（Isaac/LabUtopia）当前瓶颈不是语义抓取点（simulator_truth + USD 网格功能点 + affordance gate 已解决），而是 acquire 路线资格链——R05 在 104 个变体上 600s 超时、R03 lift 脱手。用户决定：新建显式 oracle profile，真值直接产出语义抓取点并预选路线，保留 AgentLoop 以便继续迭代 agent 能力。**RoboTwin 线**继续 GraspNet/GraspGen（不用真值），目标是"物理失败→安全恢复→重规划→完成"能力：PAOS 通用层闭环已完备（`recovery_decisions.py` 的 fresh-observation replan + 测试覆盖），RoboTwin 侧缺 acquire 安全恢复驱动；用户决定先在已跑通 live 链的 blocks_ranking_rgb 上验证恢复闭环（配 config 门控失败注入），stack 运动前置并行推进。

---

## 路径一：实验室线 Oracle 执行 profile（Isaac/LabUtopia）

**形态**：显式命名的 oracle 执行模式（先例：v16.5.0 裁决的 simulator_truth + RoboTwin oracle baseline），真值全程标注 `geometry_source: simulator_ground_truth`，不冒充传感器推导；AgentLoop/execute_subtask 契约不变。

1. **先提交现有未提交改动**（terminal IK 剪枝、reorient 半径、漏斗统计 + 测试，5 文件 + 1 新脚本）作为独立版本——它们服务于感知驱动链，与 oracle 模式互补。只暂存这 6 个文件，不碰工作树里 out/releases 删除等无关状态。
2. **真值语义抓取生成器**：新模块 `examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/oracle_grasp_geometry.py`，从 final composed USD 网格 + 已有功能点推导（复用 `simulator_truth_perception.py` 的 `axial_grasp_symmetry` 截面带、`_pour_lip_evidence`、rod endpoint）直接产出类别感知抓取位姿：
   - 试剂瓶/混合容器：瓶身轴向对称带内、rim 下方、避开 pour_lip 方位的抓取位姿（角度等价候选）；
   - 玻璃棒：杆轴对齐、抓非工作端（工作端留给搅拌）；
   - 输出与现有 grasp provider 相同的 opaque-ref 候选形状，注入 `LabGraspTaskAffordanceProvider`（`visual_perception.py`）作为 oracle 分支，跳过 GraspNet 漏斗，evidence 标 `simulator_ground_truth`。
3. **路线真值预选（直击 600s 超时）**：`configs/labutopia-oracle-motion.json` 新增 `acquire_route_selection: "simulator_truth_preselected"`——由真值抓取位姿 + 场景真值布局从 104 变体空间中确定性选出**唯一**变体（approach 方向/朝向/走廊高度），`phase_motion.py` 的 `acquire_route_waypoints`/`qualify_grasp_approach` 在该模式下只资格检查这 1 个变体（O(1) 而非 O(104)）。保留全部终态安全检查（joint 限位、tracking、接触窗口、取消、终位姿探测）——豁免的是搜索，不是安全边界。
4. **倾倒/放置**：`process_waypoints`/place 不动，真值功能点经既有 task-affordance 选择流入 `tool_frame`/`process_frame`；护栏（max_tilt 等）保留。
5. **profile 接线**：`configs/labutopia-mixture.json` 增加执行模式字段（或新增 `labutopia-oracle.json`），`profile.py` 校验，`paos_client.py`/`agent_host.py` 注册不变（工具面不变）。
6. **测试**：oracle 抓取生成器几何正反例（瓶口避让、棒工作端保留、轴向等价）、单变体资格模式、evidence 标注、profile 校验；现有 348 项 isaacsim_lab 测试保持绿。
7. **live 验证（需你授权，仿真 only）**：一个倾倒子任务全链运行；测量单变体 acquire 资格时间（目标：秒级 vs 现在 600s）与子任务完成率。产出按惯例写入 CHANGELOG 与简短 review 文档。

## 路径二：RoboTwin 失败恢复能力（blocks_ranking_rgb 先行 + stack 前置并行）

### Track A：恢复闭环落在 blocks_ranking_rgb（已跑通 live 链）

1. **lift 阶段脱手检测**：在 `robotwin_persistent_engine.py` / 执行探针（`robotwin_simulation_probe_worker.py` 的 `execute_candidate_phases`）中，lift 结束后校验持有事实（夹爪 qpos 滑移/接触丢失），失败码对齐 Isaac 白名单语义（`physical_grasp_lost` 类）。
2. **安全恢复驱动移植**（模板：Isaac `phase_motion.py:1977` `_recover_failed_acquire`）：执行期逐步记录已下发关节命令（`execution_state` 内新增长度有界 log）；白名单失败码触发：停止→验证物体仍在支撑（残差/速度阈值）且无持有/接触→开爪→**逆序重放已执行关节命令**（每步过限位/跟踪/取消/deadline 检查）→回起始观测位。回执走引擎现有异常属性通道（`robotwin_persistent_engine.py:792-801` 需扩展携带 `returned_to_safe_pose`/`observation_ready`），**字段精确匹配** `_fresh_observation_recovery_record`（`PhyAgentOS/agent/recovery_decisions.py:166-227`）与 `object_acquire.py:564` 校验：known failed + `possession_state="empty"` + `object_support_state="on_support"` + `returned_to_safe_pose/observation_ready=True` + `requires_replan=True` + `recommended_action="refresh_perception_before_motion"` + `new_scene_revision != source`。条件不满足→`acquire_recovery_postcondition_failed` 保持 unknown（fail-closed 不变）。
3. **config 门控失败注入**：profile（`profiles/robotwin20/`）新增 `failure_injection: {enabled: false, mode: "grasp_slip", friction_scale | close_target_offset, trigger: {probability|nth_acquire}}`，仅在显式开启的仿真 profile 生效，作用于被抓 actor 材质/夹爪闭合目标，注入事实写入 action artifact（证据血缘）。默认关闭，不触碰生产链。
4. **端到端评测**：N 个种子运行 blocks_ranking（注入开启）：统计 失败检出率→安全恢复回执→fresh-observation replan（bootstrap revision）→重观测→新 GraspGen 候选→重抓→放置→benchmark `check_success` 的全链成功率；place 侧滑落路径（`_verify_release`→`placement_postcondition_failed`→确定性 replan）已存在，一并纳入统计。

### Track B：stack 运动前置（并行推进）

1. **stack 路线准备工厂**：让 stack 复用 blocks_ranking 的 persistent 准备链（`persistent_preparation.py`/`persistent_route_builder.py`/curobo world port）从 `relation.target` Query 候选 → assignment → 合格路线——用 tick 可停的 persistent 执行替代 benchmark 原生 `play_once()`（同时解决诊断中的"不可中断"阻断），`StackRelationExecutionProvider`（v17.3.14）改为消费合格路线。
2. **controller qualification 产物**：在 `/home/yanxu/robotwin20-runtime/stack-blocks-three/artifacts/controller-qualification/` 用现有 qualification worker 生成 qualification/plan/evidence/validation 四件套（q 系列重新生成+审批，不复用 blocks-ranking 旧产物）。
3. **stack postcondition 证据**：`StackBlocksThreeTaskAdapter`（`robotwin_blocks_ranking_adapter.py:223`）补 `postcondition_evidence`：放置后实测支撑关系（块间接触/位姿残差），复用 `_verify_release` 模式与 scene-effects v1。
4. **合流**：Track A 恢复能力 + Track B stack motion 就绪后，在 stack_blocks_three 上做同款失败注入评测——即用户要的"复杂任务 + 物理失败 + 重新规划完成"最终演示。

## 提交与文档纪律

- 每个可独立验收的批次一个版本提交（沿用 v17.3.x 风格：实现提交 + 回执提交），CHANGELOG 同步，关键批次附简短 IMPLEMENTATION_REVIEW；只暂存本批文件。
- 感知驱动 GraspGen 链（RoboTwin）保持现状：不用真值、无 oracle 回退（GRASPGEN_RGB_ACCEPTANCE 约束）；真值只出现在实验室线显式 oracle profile。

## Verification

1. `ruff check` + `python -m compileall` + 分包 pytest：`tests/`（恢复回执字段契约新增用例，镜像 `test_recovery_decisions.py:410`）、`examples/forge-adapters/robotwin20/tests/`（恢复驱动正反例、注入门控、stack 准备链）、`examples/forge-adapters/isaacsim_lab/tests/`（oracle 生成器、单变体资格）。
2. 失败路径测试先行：恢复条件不满足→unknown 保持；旧安全回执不覆盖新失败；注入关闭时行为与现状逐字节一致。
3. live 仿真运行（ Isaac oracle 倾倒子任务、blocks_ranking 注入评测、stack qualification）单独请求你的显式授权后执行，motion 纪律与审批链保持。