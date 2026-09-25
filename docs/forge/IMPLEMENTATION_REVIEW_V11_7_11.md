# v11.7.11：RGB 规划失败与既有七维度审查

日期：2026-09-25，Asia/Shanghai。分支：`feature/planning-loop`。

## 1. 范围与结论 / Scope and conclusion

审查 v11.7.8–v11.7.10 的观测几何、GraspGen、恢复规划和验收契约改动，以及本次 v11.7.11 修复。沿用 v10.9.4 / v10.10.0 的七个维度，不重新定义通过标准。

**结论：本次源码回归和无动作诊断完成；RGB 全链路验收未通过。** 最近三次有抓取候选的任务均在 preparation 阶段结束，没有进入完整路线准入，也没有执行 acquire/place。不能把 Query 成功、回归通过或单个 contact 前缀通过算成三方块任务成功。

本次未启动新的 AgentTask，未重启在线 Runtime，未部署新的 Node/Skill，也未修改现有任务状态。源代码修复尚未进入正在运行的 Node 0.7.12 / Skill 2.7.9。

Review complete at source/regression and no-action diagnostic scope. End-to-end RGB acceptance remains incomplete; the patched source has not been deployed to the running packages.

## 2. Findings：具体问题、边界与修复

### F1 — High，仍待解决：候选接触深度与实际碰撞模型没有形成可通过的完整路线

最近任务的大多数 candidate × arm × backoff 组合在局部接触检查就存在支撑面穿透；少数剩余组合的右臂在原生 contact IK 中被碰撞约束拒绝。解除环境约束的诊断副本能求出右臂接触位姿，放回原世界后指端球体侵入桌面和观测残余体素。因此右臂的 `IK_FAIL` 不能直接解释为纯运动学不可达。完整测量见第 3 节。

现有 backoff 最大 20 mm；额外 25.27314 mm 的受限诊断让一个右臂接触前缀通过，但另一个仍撞目标。**尚无证据支持统一扩大 backoff、旋转 90° 或缩小碰撞球。** 本次没有修改生产抓取深度、姿态或碰撞阈值。

### F2 — High，已修复：空世界替换保留旧 OBB 缓存

位置：`examples/forge-adapters/robotwin20/runtime/robotwin_curobo_world_port.py`，`restore_collision_world`。

安装的 CuRobo `WorldPrimitiveCollision._load_collision_model_in_cache` 对空 cuboid 列表提前返回，旧碰撞缓存仍启用。v11.7.10 仅覆盖 Mesh 清理，普通 `update_world(empty)` 不能表示完整空世界替换。它污染了第一次环境消融诊断；该结果已作废，不能用来归因。

修复：保留原 Mesh 清理路径，并在目标 cuboid 为空时复用 `clear_world_cache()`，再加载完整目标世界。回归验证空世界无旧障碍、随后恢复原桌面。该缺陷是确定的世界生命周期错误，**不等于已经证明它导致了全部生产 contact 拒绝**。

### F3 — High，已修复：recovery stop 返回失败但任务未终结落盘

位置：`PhyAgentOS/agent/planning_loop.py`，`PlanningLoopAdapter` 的 recovery stop 分支。

旧分支只返回 settlement.status，已知失败后的 stop 可能让持久化任务仍停在 awaiting_replan。修复通过既有 Coordinator `fail_task` 终结已知失败，返回 Coordinator 实际状态并清除 replan deadline。有未结清执行记录时保留 reconciliation，由 Coordinator 在事务内再次检查。未知 Action 不会被本修复当作已知失败，也不触发重发。

### F4 — High，已修复：旧 Worker 读线程污染新进程响应队列

位置：`examples/forge-adapters/robotwin20/src/robotwin20_adapter/process_worker.py`。

旧 stdout/stderr reader 每次访问可被重启替换的实例队列；旧进程延迟 EOF 可进入新 Worker 的队列，让新请求被误判为退出。修复将进程专属 queue/deque 显式传给 reader，重启创建新的 stderr deque。确定性延迟输出测试覆盖两条流和 EOF。

这是可复现的竞态，但历史第二次 understanding 的原始异常未保存，**不能据此宣称该历史失败的根因已经被证明**。

### F5 — Medium，已修复：感知下游失败仍显示 semantic success 的 none

位置：`examples/forge-adapters/robotwin20/src/robotwin20_adapter/single_view_perception.py`。

语义推理成功后，proposal / segmentation / localization 等下游失败仍沿用语义 provider 的 `provider_error_class=none`。修复记录本次失败阶段，并在已有诊断字段中报告 timeout / transport / provider_failure；下一次成功清除旧错误。日志只保留阶段和异常类型，不记录异常消息、模型文本或凭据。

### F6 — Medium，已修复：contact 评估无法区分 approach 与 contact 失败

位置：`examples/forge-adapters/robotwin20/runtime/robotwin_route_planner.py`，`_evaluate_contact`。

原来两个阶段都投影为同一个 `IK_FAIL`。现在补充 failed_phase，保留 native reason 和原准入结论；测试同时检查 joint state 未改变。它提升诊断精度，不增加新的运动准入路径。

## 3. 为什么路径不通过：捕获记录与受控诊断

### 3.1 三次抓取漏斗

| 开始时间 / Task | GraspGen：生成→模型过滤→NMS→保留 | 接触候选 | 候选×机械臂×backoff | 支撑面穿透 | 原生规划器评估 | 完整路线 / Actions |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 16:33:14 / task_538b582e72d248c9 | 24→24→24→10 | 9，另 1 个工作空间拒绝 | 144 | 142 | 2，均失败 | 0 / 0 |
| 17:04:17 / task_8f4a6bc796f14301，蓝块 | 24→23→23→10 | 9，另 1 个工作空间拒绝 | 144 | 144 | 0 | 0 / 0 |
| 17:28:26 / task_c241f2141c314762 | 24→24→24→10 | 8，另 2 个工作空间拒绝 | 128 | 126 | 2，均失败 | 0 / 0 |

144/128 是组合数量，不是独立 GraspGen 输出数量；拒绝原因可以重叠。`unobserved_samples` 在当前实现是诊断量，不是上述拒绝原因。

三次 mesh 支撑面净空范围分别为 -105.385202～+0.563459 mm、-136.247500～-11.256601 mm、-104.634566～+0.810970 mm。无需假设 NMS 删除了可行抓取来解释当前主要损耗：绝大多数组合在几何接触资格检查已被拒绝。

16:46 的 task_1e3a48b587aa4ace 在重复 understanding 失败，没有进入这张规划漏斗。其原始下游异常没有保留，不能推断为 GPU OOM 或特定 Worker 故障。

### 3.2 剩余候选具体失败阶段

在原始观测世界、20 mm backoff 下重新调用原生规划器：

| 捕获候选 | 左臂 | 右臂 |
| --- | --- | --- |
| 16:33 candidate://e3/2 | approach，IK_FAIL | contact，IK_FAIL |
| 17:28 candidate://e3/8 | approach，IK_FAIL | contact，IK_FAIL |

不能把该结果概括为“所有 grasp IK 不可达”，也不能将左臂的失败原因直接归给右臂。

### 3.3 有效环境消融与碰撞实测

第一次 `update_world(empty)` 保留旧 OBB，因此 `contact-ablation.json` 是无效消融。第二次显式清空碰撞缓存再加载空世界；保留关节限制与自碰撞检查，右臂两个候选均能求解接触位姿。随后在求解出的关节位置恢复原世界并检查：

| 候选 | 机器人模型 | 原世界障碍 | 净空 |
| --- | --- | --- | ---: |
| e3/2 | panda_leftfinger sphere 57，半径 15 mm | table | -2.687179 mm |
| e3/2 | 同上 | observed-voxel/81、101 | -1.396329、-2.166022 mm |
| e3/8 | panda_leftfinger sphere 57，半径 15 mm | table | -3.100772 mm |
| e3/8 | panda_rightfinger sphere 59 | table | -1.767956 mm |
| e3/8 | panda_leftfinger sphere 57 | observed-voxel/136、139 | -3.362775 mm |

实际 gripper mesh 的亚毫米正净空，不能推出更保守的原生碰撞球也有正净空。右臂当前是**碰撞约束下的接触 IK 失败**；移除环境获得的结果仍有负净空，仅用于诊断，未获准运动。左臂的环境、自碰撞与运动学贡献尚未独立分离。

### 3.4 深度差异诊断：找到方向，但没有完成通用修复

现有 GraspGen 训练 base-to-contact 深度为 105.27314 mm，RoboTwin gripper bias 为 80 mm，差值为 25.27314 mm。现有 declared backoff 最大 20 mm。沿既有 qualification 接口只额外测试差值深度，完整观测世界保持启用：

| 候选 / 右臂 | 25.27314 mm backoff 的结果 |
| --- | --- |
| e3/2 | contact 前缀通过；mesh 支撑净空 +5.169251 mm，原生球体净空 +1.949369 mm，inner target points 202 |
| e3/8 | 仍拒绝：contact observed target intersects robot link panda_rightfinger；mesh 支撑净空 +6.079267 mm，inner points 241 |

没有写入生产 profile，也没有执行 lift、transport、descent、release、retreat。一个 contact 前缀通过不能证明整个 manipulation.prepare 会通过。下一步应在 provider/embodiment 所有者边界核对 frame 与有限 backoff 语义，然后对完整路线验证。

待确认的 frame 问题：pinned GraspGen 文档定义 approach 为 Z、closing 为 X；RoboTwin Panda URDF 的指关节轴为 ±Y。必须结合 adapter conversion 和 robot delta 矩阵核对，不可只据轴名猜测统一旋转 90°。已有位置 round-trip 不足以证明完整接触 frame 等价。

参考：`docs/forge/GRASPGEN_CONTACT_DEPTH_POSTPROCESSING.md`、adapter `grasp_adaptation.py`、本地 pinned GraspGen `docs/GRIPPER_DESCRIPTION.md` 与 `config/grippers/franka_panda.*`，RoboTwin `assets/embodiments/franka-panda/panda.urdf` 和 `envs/robot/robot.py`。

### 3.5 与此前 retreat 问题分开

14:04 的 task_e36fbced0280470b 已走到放置后 retreat 准入，失败对象是 released-target AABB。v11.7.10 改为同一实测目标点云的释放扫掠凸包并保留配置中的 1 mm 不确定度；捕获回放右臂通过 11 段。

当时 AABB 与右指球重叠 9.3215 mm，而实测凸包原始净空为 4.3126 mm。最近几轮失败在更早的 contact 阶段，不能将它们描述为同一个 retreat bug 仍未解决。此前的路线回放同样不代表执行成功。

## 4. 既有七维度验收 / Established seven dimensions

| 维度 | 结果 | 依据与未完成项 |
| --- | --- | --- |
| Architecture integration | 源码范围通过 | Core 只处理通用任务状态；Runtime 拥有机器人、观测几何与规划器；candidate 数据沿已保存来源传递，未增加模型几何组装路径。 |
| Recovery and idempotency | 回归通过，在线验证待补 | stop 通过 Coordinator 落盘，未知 invocation 保留对账；Worker 代际隔离；不添加 Action 自动重发。 |
| Robotics safety | 无动作范围通过 | 保留碰撞、支撑、目标接触检查；消融仅在诊断副本，无 Gateway Actions、无路线执行；不是运动安全认证。 |
| Context and performance | 部分通过 | 增加阶段与错误类型，不向模型展开候选几何；尚无成功全链路延迟/上下文成本数据。 |
| Configuration and reproducibility | 未达到正式验收 | 保存脚本、输入根目录与诊断；17:04/17:28 的 Runtime 根目录含字面量反斜杠+n；16:46 复用 16:33 Runtime 根目录；新源码未部署。 |
| Maintainability and observability | 回归通过 | 精确 failed_phase、下游错误分类、旧进程隔离、空世界回归；历史 understanding 原始异常无法追补。 |
| AgentLoop autonomy | 部分通过，任务验收未通过 | 最近任务已有 3 个 revision，说明能恢复规划；仍无成功 acquire/place、最终 Verifier 或完成 RGB 的视频。 |

根目录不一致是独立的可复现性问题，没有证据证明它导致了某次感知异常。下一次验收应使用干净、唯一、与 task/Runtime 对应的目录，不覆写本次历史证据。

架构依据：`docs/zh/03-developer-manual.md`、`docs/adr/0001-runtime-ownership-and-skill-use.md`、`docs/forge/MANIPULATION_DAG_DEVELOPER_GUIDE.md`、`AGENT_TOOL_INPUT_SELECTION_DESIGN.md`、`VISUAL_GEOMETRY_EVIDENCE_ARCHITECTURE.md`。

## 5. 验证命令与证据

### 自动回归

主回归 **333 passed in 8.16s**，日志 `/tmp/paos-review-v11711-tests.log`：

```bash
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin \
  tests/test_agent_task_tool.py tests/test_agent_foundation.py tests/test_planning_loop.py \
  examples/forge-adapters/robotwin20/tests/test_grounding.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_deployment.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_host.py \
  examples/forge-adapters/robotwin20/tests/test_process_worker.py \
  examples/forge-adapters/robotwin20/tests/test_single_view_perception.py \
  examples/forge-adapters/robotwin20/tests/test_route_planner.py \
  examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py \
  examples/forge-adapters/robotwin20/tests/test_runtime_observed_collision.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_preparation.py \
  examples/forge-adapters/robotwin20/tests/test_simulation_probe.py
```

最后调整返回 Coordinator 实际状态后，以相同环境重跑 `tests/test_planning_loop.py` 和 `examples/forge-adapters/robotwin20/tests/test_curobo_world_port.py`：**74 passed in 2.85s**。这是重复覆盖，不与 333 相加。Changed-file Ruff 与 `git diff --check` 通过。

### 无动作诊断文件

根目录：`/home/yanxu/robotwin20-runtime/artifacts/rgb-review-contact-20260925/`。

- `captured-contact-funnels.json`：三次实际漏斗与拒绝分布。
- `contact-replay.json` / `contact_replay.py`：原场景阶段回放。
- `contact-ablation.json`：首次消融无效，仅保留调查历史。
- `contact-ablation-cleared.json` / `contact_ablation.py`：清缓存后的有效消融与原世界碰撞测量。
- `contact-depth-diagnostic.json` / `contact_depth_diagnostic.py`：深度诊断，保留实际接触准入与失败。
- 原 retreat 证据：`/home/yanxu/robotwin20-runtime/artifacts/rgb-retreat-diagnostic-20260925T1605/{start-collisions.json,full-route-mesh.json,full_route.py}`。

上述诊断均为 **0 Gateway Action calls / 0 simulator route trajectory execution steps**；模拟器初始化/reset 确实发生，不能描述为没有任何仿真步骤。诊断恢复机器人状态，不变更在线任务。

现有任务 `task_c241f2141c314762` 在审查时为 awaiting_replan、3 revisions、verification=enforce、0 Actions；本次未代替 Agent 作恢复选择。

## 6. 审查后的执行顺序

1. 核对 GraspGen provider frame → Panda hand frame 的完整旋转/平移和 backoff 含义；优先使用既有 provider-owned 后处理接口。
2. 固定捕获输入，对每个有限候选验证 approach/contact，再验证完整 lift/transport/descent/release/retreat/return；若仍失败，按精确 phase 分析碰撞证据。
3. 在真实 Worker 重启路径复测连续感知，使用新增阶段日志区分 semantic、proposal、segmentation、localization 故障。
4. 将经验证的源码打包、安装并核对实际执行版本，使用正确目录、enforce 验收与视频留存重启新的独立任务。
5. 执行用户要求的三次任务；至少一次完整 RGB 排列、ForgeTaskVerifier 通过且视频可播放，才记录全链路验收通过。物理失败允许保留真实失败记录，软件失败继续归因修复。

本审查没有新增 hash、基线或 gate，没有用传感器外几何替代观测，也没有通过降低碰撞阈值来制造通过结果。
