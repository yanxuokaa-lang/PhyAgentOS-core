# Runtime Launch Diagnosis v12.3.6

日期：2026-09-30（Asia/Shanghai）
范围：`pick-place-workflow 2.9.4` / `robotwin20_persistent_host 0.9.3`

## 结论

新版 Runtime 的生成 `dataflow.yaml` 没有损坏。此前直接运行生成目录中的
`dora start ... dataflow.yaml` 失败，是因为该路径绕过了 PAOS
`RuntimeManager` 的 profile 环境合成；Dora 收到未展开的 `${ROBOTWIN20_*}`
占位符后，在 YAML admission 阶段报 `EnvValue` 类型错误。

正式入口 `paos skill start` 已成功完成环境合成、Node 预检、Dora admission 和
Gateway readiness。没有修改生成 dataflow，也没有创建 AgentTask、Query、Action
或视频记录。

## 复现证据

- 直接启动：`nodes[0].env: data did not match any variant of untagged enum EnvValue`
  （raw dataflow 中仍包含 `${ROBOTWIN20_PAOS_PYTHON}` 等占位符）。
- 正式启动：
  `paos skill start pick-place-workflow --profile robotwin-blocks-ranking-graspnet --env-file /home/yanxu/.PhyAgentOS/deployments/robotwin-persistent/runtime-rgb-graspnet-run5.env`
  返回 `Skill pick-place-workflow is running`。
- Runtime 状态：Dora flow running，Gateway `GET /tools` ready，10/10 required
  Tool context ready。
- Node 发布校验：`robotwin20_persistent_host-0.9.3-linux-x86_64` SHA-256 verified。
- Qwen loopback 与双视角配置仍由已安装 profile 管理；本次未执行物理 Action。

## 根因与边界

`dataflow.yaml` 是安装制品的模板输入，不是供操作员直接调用的独立启动接口。
环境值由 `RuntimeManager.compose_runtime_environment` 合并 profile defaults、
operator env file 和进程环境，再传给 Dora。绕过该边界会把部署错误降级为 Dora
底层 schema 错误，并且无法得到 PAOS 的 Runtime state、Gateway identity 和
启动失败审计。

该问题不需要修改 AgentLoop、双视角绑定、Qwen provider 或动作安全策略；这些
模块的 v12.3.4/v12.3.5 修复保持不变。

## 修复验收

1. 通过 `paos skill start` 启动，不直接调用生成 dataflow。
2. `paos skill status` 显示 running，Gateway 和全部 required tools ready。
3. `paos forge-node verify pick-place-workflow robotwin20_persistent_host` 通过。
4. 在启动验证期间没有 AgentTask、物理 Action、invocation 或 manifest 被创建。
