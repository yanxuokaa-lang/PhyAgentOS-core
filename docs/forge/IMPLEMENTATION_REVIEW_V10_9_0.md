# v10.9.0 需求复核、Fresh Code Review 与七维验收

审查日期：2026-09-20（Asia/Shanghai）。对象：`feature/planning-loop` 上相对
`facca10` 的本次实现。重新检查当前调用链及失败路径，并运行测试；未引用旧版本的
PASS 作为本次证据。This review covers the current implementation and fresh tests.

## 结论 / Decision

源码、隔离安装和 no-motion 功能验收通过；无已知未修复 Blocker/Major。
真实 RoboTwin 性能与端到端任务录像仍待部署后验收，不能宣称全部实际运行需求已验证。
Source and isolated no-motion checks pass; real-scene timing and real task video remain unverified.

## 原始需求对照 / Requirement mapping

| 原始需求 | 当前实现与证据 | 验收边界 |
|---|---|---|
| 缩减 green_prepare 约 44,856-token 上下文 | 通用字段目录、计数、引用、小型候选摘要；Agent 选 record_id/path，Coordinator 解析完整参数并按消费者 schema 校验。合成 24 候选上下文从 49,717 字符变为 1,456 字符，约减少 97.1%。selection 与恢复 prompt 也使用精简 receipt。 | 字符测量是合成 fixture，不是原任务的新 token 数；Skill 指令和必要 schema 仍占用上下文。 |
| 记录排队、首 token、完整响应时间 | 记录提交至响应头、首个有效内容/推理/Tool 流事件、完整响应；中断日志保留已观测时延；非流式 phases 为 unavailable。 | 响应头时延包含网络、连接池和服务端处理；没有服务端遥测就不能分离纯排队时间。 |
| 单次模型 300s，turn 420s | 当前部署 config 为 300/420，custom streamResponses=true；Core 默认不变。节点决策现在使用 turnTimeoutS，覆盖重复模型请求和控制面查询。 | long-horizon 的 420s 是决策阶段预算；已选择的 governed Tool 使用独立执行预算，避免把 prepare 压缩到模型剩余时间。未重启在运行进程。 |
| prepare Tool 总预算 | persistent ToolSpec default_timeout_ms=360000；profile preparation_timeout_s=330，贯穿 snapshot、grounding、materializer、双臂 readiness、finalization、worker 锁等待与启动。 | deadline 失败返回 preparation_timeout；既有 worker 终止清理有小量有界尾延迟。 |
| K=1/4/8/24 冻结场景 benchmark | 脚本在同一个已运行 Runtime 上，对同一输入的固定前缀执行四次公开 prepare Query，记录阶段 metrics、输入来源、commit 和环境信息；已有输出文件被拒绝。 | 目前只有测试矩阵，没有真实冻结场景耗时。unknown scene 不被写成 unchanged=true。运行时不能混入其他 prepare。 |
| top-K、早停、有限并发 | 保留现有候选/安全筛选语义；提供测量基础后再选策略。 | 未固定 top-K、未启用早停或并发；这些是待测量后的优化方案，不宣称已交付。6h48m 不作为配置目标。 |
| 多次执行合在一起的完整视频 | 同一 PAOS task owner 的多次 acquire/place 按序累计为 head-camera.mp4、observer-camera.mp4 和 manifest；执行中的采帧已接入 engine；最终 place 的 post_release_evidence 保留全部累计引用。 | 覆盖同一 Runtime 生命周期内同一 task 的执行阶段，按 stride 采样；不承诺后台等待录像、不同 task 合片或跨 Runtime 重建拼接。 |
| 正确持久保存视频 | 每个 Action 闭合内部片段，真实解码检查后原子发布；累计视频亦验证；失败/取消片段可留在后续累计结果中；缺失片段不得被后续成功掩盖。 | 当前产物是合成相机测试视频，不是用户真实任务完成录像。 |

## Fresh review 发现与修复 / Findings and fixes

1. **Major，已修复：执行过程没有接入 recorder。** archive 有首尾帧，但 engine
   未给执行状态设置 video_recorder。现连接既有 `_capture_probe_video` 入口，并在
   Action 结束移除；engine 路径测试验证两次 Action 共 10 帧，包含 6 个中间采样帧。
2. **Major，已修复：selection receipt 重新膨胀上下文。** 源值解析后曾完整返回
   tool_arguments。现返回空参数加 use_selected_arguments，执行时 Coordinator 读取
   原 selection；dispatch admission 和执行事务都仍验证精确参数、Tool、语义及 revision。
3. **Major，已修复：统一 deadline 漏掉真实 Query 链。** 已贯穿 initial/final
   snapshot、route builder、Grounding.scene_facts 和 bind_observed_entities；worker
   锁等待与启动计入剩余预算，readiness 超时不会被普通拒绝结果吞掉。
4. **Major，已修复：long-horizon node 不经过交互 turn timeout。** 为节点决策增加
   配置预算，超时返回既有 turn_timeout；选定 Tool 继续由其预算和持久结果处理。
5. **Major，已修复：owner 切换清空旧任务的视频累计状态。** Runtime 内按 owner
   保存归档，task-1 → task-2 → task-1 后仍能保留 task-1 的两段执行。
6. **Major，已修复：流中断的观测与清理缺失。** 成功、错误、取消路径均关闭流；
   超时日志保留已收到的首事件时间；非流式兼容路径不请求 streaming。

普通 schema、版本号或单元主键无法解决缺失采帧、预算未传递或 payload 重复投影。
修复沿用既有 receipt、事务、Query/Action 和 evidence 协议，没有新增运动权限、
第二任务状态机或 Core RoboTwin/RGB 特例。

## 既有七维验收 / Established seven dimensions

| 维度 | 源码/no-motion 结论 | 依据与剩余边界 |
|---|---|---|
| 1. 架构集成 | PASS | Agent 选择、Coordinator 解析/持久化、Gateway admission、Adapter 几何与 Runtime 物理所有权分离；累积录像由执行 owner 管理。 |
| 2. 失败恢复与幂等 | PASS | receipt 不允许替换 Tool/语义/参数；已消费 selection 不再执行；累计发布失败保留片段；owner 切换可恢复累计；未知结果不成为成功。 |
| 3. 机器人安全 | PASS（no-motion） | 测试无真实 Gateway Action/仿真步进。未改变标定、坐标系、关节/碰撞/stop/approval 检查。超时和录像失败不授权运动，真实运行仍待验收。 |
| 4. 上下文与性能 | 功能 PASS；实测待验收 | 合成上下文 49,717→1,456 字符，完整参数可恢复；模型时延可观测；真实 K=1/4/8/24 耗时及原任务新 prompt 大小未测。 |
| 5. 配置与可复现性 | 构建/隔离验证 PASS；部署待验收 | Skill 2.3.0、Adapter 0.4.0、Node 0.1.16；默认 profile 330s/Tool 360s；隔离安装及 Node SHA/启动帮助验证通过。运行中的 Runtime 未更新。 |
| 6. 可维护性与可观察性 | PASS | 通用来源选择、明确 timeout 错误、每阶段 metrics、stream timing、视频 manifest 与开发者文档；变更文件静态检查通过。 |
| 7. AgentLoop 自主性 | PASS | Agent 显式选 Tool 和输入来源，随后显式请求执行；没有自动替 Agent 选 top-K/机械臂/动作，没有新增生产者消费者私有映射。 |

## 验证 / Validation

- Core: **490 passed**；Skill: **335 passed**；Adapter: **505 passed, 1 skipped**（当前 paos 环境缺少可选 Pillow，perception worker 测试模块跳过）。
- 最后追加的 engine → post_release_evidence 投影检查：4 个视频测试通过。
- changed-file Ruff、compileall、uv lock --check、git diff --check 通过。
- 完整 Core 复验包含节点决策 timeout、独立 Tool 预算、来源 receipt 和 streaming 兼容。
- 四 Action 累计视频 fixture：两路 MP4 均可解码，8 帧按序累计；engine fixture
  额外证明中间执行帧真实进入录制，最终 place 保留全部三类视频引用。

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
uv lock --check
git diff --check
```

构建与隔离验证产物在 `/tmp/paos-v10.9.0-release-WS5VZy/`：

- `robotwin20_persistent_host-0.1.16-linux-x86_64.tar.gz`
- `skills/pick-place-workflow-2.3.0.tar.gz`
- `isolated/`：同一个 Skill 的隔离安装，未启动 Runtime。
- `video-smoke/`：合成四 Action 视频，不是用户真实任务录像。

现有 Skill 的升级包已准备；不需要安装一个新名称的 Skill。下一阶段是在受控更新
现有 Runtime 后，获取同一新场景的合法冻结请求、实测四组 K，再运行用户任务并验证
最终视频完整性。本次没有停止/恢复旧任务、更新活动 Runtime 或执行真实 Action。
