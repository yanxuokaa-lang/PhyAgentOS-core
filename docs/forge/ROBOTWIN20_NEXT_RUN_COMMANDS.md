# RoboTwin persistent 下一轮运行命令

本文档记录当前 `feature/planning-loop` 分支上，使用
`pick-place-workflow 2.0.2` 和 `robotwin-persistent` profile 的下一轮操作命令。

当前约定：

- 场景理解 Provider 继续使用配置中的 GPT-Sol High（`gpt-5.6-sol`）。
- 不切换到 Qwen，不启动自我进化，不创建固定 YAML 或专用 Runner。
- 继续使用已有 AgentTask `task_e0595cd5f94045ef`，不要创建新任务。
- 不在文件、日志、Bundle 或任务提示中保存 `ROBOTWIN20_MODEL_API_KEY`。
- 任何 Action 都必须经过 PAOS readiness、planning binding、Gateway 和 Verifier 边界。

## 1. 安装或更新本地 Skill

当前 Bundle：

```text
/tmp/paos-robotwin20-release/skills/pick-place-workflow-2.0.2.tar.gz
```

本地安装不需要网络代理：

```bash
cd /home/yanxu/PhyAgentOS-forge

env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    paos skill install \
      --local \
      --yes \
      /tmp/paos-robotwin20-release/skills/pick-place-workflow-2.0.2.tar.gz
```

安装后检查：

```bash
env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    paos skill inspect pick-place-workflow
```

应显示 `pick-place-workflow 2.0.2`。如果提示 Skill 正在运行，先执行第 2 节。

## 2. 安全停止旧 Runtime

仅当 Runtime 正在运行时执行：

```bash
env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    paos skill stop pick-place-workflow
```

确认停止：

```bash
env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    paos skill status pick-place-workflow
```

如果普通停止因为活动 AgentTask、Session 或 invocation 被拒绝，不要直接使用 `--force`，先核对任务状态。

## 3. 注入模型 API Key

`runtime.env` 不保存密钥。每次新终端都要在当前进程中注入：

```bash
read -r -s -p "请输入 ROBOTWIN20_MODEL_API_KEY: " ROBOTWIN20_MODEL_API_KEY
echo
export ROBOTWIN20_MODEL_API_KEY
```

密钥只存在于当前 shell 环境。不要把它追加到 `runtime.env`、日志或 Bundle。

## 4. 启动 Runtime

```bash
cd /home/yanxu/PhyAgentOS-forge

env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    paos skill start pick-place-workflow \
      --profile robotwin-persistent \
      --env-file /home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime.env
```

然后检查：

```bash
env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    paos skill status pick-place-workflow
```

至少确认：

```text
Runtime: running
Gateway GET /tools: ready
scene.observe: ready
manipulation.capabilities: ready
scene.understand: ready
scene.bind: ready
manipulation.target: ready
grasp.propose: ready
manipulation.prepare: ready
object.acquire: ready
object.place: ready
```

## 5. 继续现有 AgentTask

当前任务 ID：`task_e0595cd5f94045ef`。Runtime ready 后执行：

```bash
cd /home/yanxu/PhyAgentOS-forge

timeout --signal=INT --kill-after=30s 3900s paos agent \
  --config /home/yanxu/.PhyAgentOS/config-rgb-no-evolution-long.json \
  --session cli:rgb-formal-skill-20260915-r7 \
  --no-logs \
  -m "继续当前未完成的 AgentTask task_e0595cd5f94045ef，不要创建新任务，不要取消或替换当前任务，也不要复用其他历史任务。当前 Provider 继续使用配置中的 GPT-Sol High，不切换 Qwen。首先读取任务权威状态、当前 Runtime 和 Tool context。若现有 scene.observe、scene.understand、scene.bind 证据仍属于当前 scene revision，则不要无理由重复感知，直接从 manipulation.target 继续；若 Runtime 重启导致证据 stale，才重新按 scene.observe、manipulation.capabilities、scene.understand、scene.bind 顺序执行，每个 Query 等待终态，不并行启动 LocateAnything 与 SAM2。根据本任务内可信 RGB-D、depth、calibration、segmentation、metric_localization、object_geometry 和 binding 证据构造语义 PlanGraph。PlanNode.conditions 只能使用 lowercase symbolic condition-fact keys；自然语言放入 obligation、required_evidence 或 input_bindings；required_evidence 只能使用 Coordinator 已持久化的精确 opaque evidence_refs，不得提交 observation://、metric_geometry 或其他自造别名。PlanGraph 物化后必须依次执行 forge_plan_activate、forge_plan_ready、forge_plan_select，由 Coordinator 生成 planning_binding；不得自行构造 digest 或 binding。读取 forge_plan_ready.node_diagnostics，若 ready_nodes 为空，依据缺失 dependencies、evidence、condition 或 Tool candidate 的诊断修正未执行图；不要绕过 readiness。每个 Action 必须通过 Forge Gateway 并等待 terminal result；每次世界变化后重新观察新的 scene revision。失败、unknown、取消未确认或 transport 断开时只能 stop、replay 或合法 replan。最后在最新 scene revision 上由 ForgeTaskVerifier 验证红、绿、蓝从左到右排列，只有 verifier 成功才能报告完成。"
```

## 6. 必须保持的边界

- `forge_plan_ready` 是只读控制面，不执行 Tool，不授权运动。
- `forge_plan_select` 只由 Coordinator 生成 planning binding，不直接调用 Gateway。
- `motion_authorized=false` 不是成功结果，也不能被模型输出覆盖。
- 失败、unknown、未确认取消或 transport 断开时，不得盲目重试物理 Action。
- 世界发生变化后必须获得新的 scene revision，并重新使用当前证据进行绑定和规划。
- 只有最新 scene revision 上成功的 `ForgeTaskVerifier` 才能作为任务成功证据。

## 7. 常见错误

### `Unknown scheme for proxy URL URL('socks://127.0.0.1:7897/')`

本地命令前加：

```bash
env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    <原命令>
```

### `Required environment is not configured: ROBOTWIN20_MODEL_API_KEY`

重新执行第 3 节，并在同一个终端执行第 4 节。

### `Skill 'pick-place-workflow' is currently running`

执行第 2 节，确认 `Runtime: stopped` 后再执行第 1 节。

### `ready_nodes=[]`

不要直接调用 Action。读取 `forge_plan_ready.node_diagnostics`：

- `dependencies`：前驱 Node 尚未完成；
- `evidence`：缺少当前任务持久化的精确 opaque ref；
- `unknown_conditions`：条件事实尚未由 Coordinator/Tool 产生；
- `false_conditions`：条件事实明确为 false；
- `no_tool_candidate`：Skill 没有匹配 Tool，或 stale scene 下没有 refresh Query。

只有修正语义图并重新获得 ready node 后，才能进入 `forge_plan_select`。

## 8. 彻底停止 Runtime

```bash
env -u ALL_PROXY -u all_proxy \
    -u HTTP_PROXY -u http_proxy \
    -u HTTPS_PROXY -u https_proxy \
    paos skill stop pick-place-workflow
```

本文档只记录命令和边界，不代表当前 AgentTask 已完成，也不代表仿真或硬件动作已经成功。
