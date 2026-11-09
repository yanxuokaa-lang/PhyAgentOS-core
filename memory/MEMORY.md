# Long-term Memory

This file stores important information that should persist across sessions.

## User Information

(Important facts about the user)

## Preferences

(User preferences learned over time)

## Project Context

### PhyAgentOS-forge 架构速查（2026-11-09 调研）

**定位**：具身任务 Agent 框架。Agent（认知规划）与 Forge Gateway（物理执行）分离：
`AgentLoop+Planner → ForgeToolClient → Gateway /tools → ToolInvocation → ToolEndpoint → Dora → 机器人/仿真器`。
PAOS 不 import RoboTwin/SAPIEN；仿真器参数只属于 Gateway adapter/profile。

**三类事实 / 单一所有者**：
- Execution（Gateway 拥有）/ Evidence（PAOS observation）/ Verdict（PAOS verification）分离；
- AgentTaskCoordinator（`forge/task.py`，SQLite WAL）是 task/revision/selection/record/settlement 唯一事实源；
- 全局最多一个非终态 AgentTask；PlanRevision 只追加；ID 体系（task/binding/revision/record/caller/invocation/attempt）互不为别名；
- admission/cancel/timeout/unknown 都不证明物理停止；unknown Action 只按 invocation ID 对账、绝不重发 POST。

**架构原则**（AGENTS.md 14 条，要点）：依赖方向 task→port→Provider→环境；机制/策略分离；跨边界只用领域对象；可替换性判定通用性；最小公共契约；证据血缘 observation→…→settlement 不混 revision；单一生命周期所有者（禁影子调度器）；能力发现先于执行、fallback 不许转成功；组合优于重复；failure-first；风险比例验证（无具体失败场景不加 gate/hash/schema）；Anti-OverDefense（v17.1.0 专项审查将其制度化：docs/reviews/overdefense-review-fullchain-20261105.md）。

**AgentLoop（一个闭环三种决策）**（docs/forge/JEV_AGENT_LOOP_REFACTOR_DIAGNOSIS_20261014.md + `agent/loop.py`、`agent/planning_loop.py`）：
- System 0 确定性程序：投影/ID 匹配/DAG/schema 校验/结算/预算；唯一候选或声明式投影可完整决定参数的 Query → **零模型选定**；
- System 1 JEV（小型语义分类服务）：有限候选有界选择（query_input_selection 已接入 off/shadow/active；method_fragment/recovery 决策点已预留）；一轮只试一次，弃权/超时升级 LLM 不回落；
- System 2 LLM：开放目标→DAG、新约束、复杂恢复；
- 节点回合：空历史起点 + Bounded Input View（只含当前节点不可变绑定、discovery 授权证据、直接前驱终态）→ 确定性优先 → JEV → LLM 白名单工具回合（forge_plan_ready/select）→ 冻结 input_schema 校验（拒绝即无 Tool record、无 Gateway 调用）→ selection receipt 交接执行 → 记录折叠成 ToolResultEnvelope → 纯函数 `settle_node` 结算（unknown/missing_evidence/stale/failed/completed）→ 非完成进 `_recover`（stop/replay/replan 受限枚举）；
- planning 包纯函数（不执行/不落库/不授权运动）；prompt 预算默认 272K 窗口/260K 压缩。

**关键文档入口**：docs/README.md（总索引）；docs/zh/01 框架介绍、03 开发者手册（8 条开发不变量+测试门禁 ruff/compileall/pytest）；docs/forge/README_zh.md（Tool API 契约）；docs/user_development_guide/README.md（§7.1 Anti-OverDefense 三条件闸门）；docs/adr/0001（Runtime binding 与 Skill Use 分离）。

### GPT（codex / GPT-5.6-sol）的角色与产出

- git 提交人 `codex`，占 fork 后 ~85% 提交（1439/1694），v0.1.0→v17.3.14 主干开发基本由它完成；每版配一份 IMPLEMENTATION_REVIEW 七维自审（共 145 份）。
- 三重身份：编码模型（实施者）、曾作为运行期规划/场景理解 provider（gpt-5.6-sol，后按 provider-neutral 原则移到部署注入）、被评估的 GPT-6 Luna Decisions API（404 未实测，如实记录）。
- JEV_IMPLEMENTATION_HANDOFF_20261014.md 是面向 GPT-5.6-sol 的分批工单：P0 selection 交接→P1a/1b 投影与瘦身→P2 方法片段→P3a/P3b 决策点→P4 恢复，已全部落地；要求 no-motion 纪律、不得伪造运行结果、阈值不得凭经验填。
- 主要已解决问题：场景理解 provider 可替换边界；scene.bind 缺字段历史事件；节点选择后多余 LLM 往返；常规续段免 LLM；R03/R04 semantic_binding_mismatch（冻结参数注入）；Isaac 抓取失败安全恢复（v17.0.0）；RoboTwin stack 单关系执行链（v17.3.x，motion 资格仍关闭并如实标注）。

### GPT 保守防御性编程造成的困难（核心结论）

- v17.1.0 全链审查归纳**五种 GPT-defense 签名**：A 同一不变量重复检查 3-4 次；B 每 turn 冗余全量 pass；C deepcopy 三明治；D 不可达路径伪造 fallback 死代码；E 影子策略复制漂移（loop 副本缺 refreshes_scene 检查反而放进更多节点）。40 项发现、~20 项清理、**5 项被测试证明 load-bearing 回滚**。
- Agent 侧保守（禁推测性选择）+ 契约过严叠加 → `node_selection_no_progress` / `discovery_no_progress` 系列不收敛停机（FROZEN_QUERY_SELECTION_NO_PROGRESS_20261012 等：输入已全部冻结仍要求模型重复选择；"恰好一个候选"遇两条 authorized 记录即 unavailable；证据候选被误升为绑定义务；三个任务无一提交 Action）。
- 保守全局门禁导致过早取消/过度拒绝，多起被用户审核推翻（object_shape_uncertain 全局门禁撤回；未知区间球膨胀 20mm 判过度拒绝撤回；保守包络误拒近桌路径）。
- 防御检查自身出错：prepare_held tuple/list JSON 往返假阳性；_recover stop 提前返回绕过 unknown 对账；fallback 成功反跳过 primary 释放。
- 刻意保留的合理防御（不可清理）：物理安全 fail-closed（碰撞/IK/运动/posession/新鲜度）、fallback 不转成功、EULA/motion 授权、数值边界准入、不可逆边界人工审批。
- 教训：该仓库"何为过度防御"没有静态答案，靠"具体失败场景+可达证据+测试证明 load-bearing"逐案裁决；改动前先查现有测试是否依赖该防御。

## Important Notes

- 当前分支 feature/planning-loop。2026-11-09 双线推进（v17.3.15→v17.5.3，13 个提交）+ 用户授权 live 阶段成果：
  - **q5 controller qualification 全链闭环**（blocks-ranking-rgb-franka-sapien-q5，/home/yanxu/robotwin20-runtime/artifacts/recovery-eval-20261109/）：capability 物化/验证 → plan → verify → 人工批准（用户授权）→ SAPIEN 运行 **passed**（七项测试证据）→ 独立验证 **validated_pass** → 证据批准 **approved_pass**。本机首次 controller qualification 通过。
  - 环境修复：迁移 RoboTwin 根的 assets/embodiments 符号链接反向（真实目录在迁移根，stack 资产根留反向链接），否则能力派生的防绕过检查拒绝跨根 URDF。
  - oracle run1：agent 反问倾倒参数（非交互无人应答）→ 指令需显式给参数并禁止反问；run2 发现 oracle provider 输出与通用 grasp-proposal 契约错配（封闭字段集+四阶段 funnel）→ v17.4.1 修复（343503b3）；run3 死于远程 API 余额。
  - **阻断：api.shuaiapi.com 余额耗尽（¥0.04，单请求 ¥0.045）**。本地 vLLM qwen3-vl-4b (127.0.0.1:8012) 仅 2048 上下文，不能驱动 agent。等充值后：重发 Isaac oracle run3（命令在 shell 历史与 run2 基础上）+ 启动恢复评测。
  - 恢复评测全部就绪：skill 3.0.30（node 1.0.20 内嵌恢复代码）已安装、profile `robotwin-blocks-ranking-recovery-eval` 已注册、部署 env 在 `/home/yanxu/.PhyAgentOS/deployments/robotwin-recovery-eval/runtime.env`（含 q5 资格路径；启动仍需注入 ROBOTWIN20_MODEL_API_KEY）。
  - 评测启动命令（充值后）：`paos skill start pick-place-workflow --profile robotwin-blocks-ranking-recovery-eval --env-file /home/yanxu/.PhyAgentOS/deployments/robotwin-recovery-eval/runtime.env`（先注入 API key；用 env -u 清代理）。
- 测试运行方式：`PYTHONPATH=examples/forge-adapters/robotwin20/runtime:.../robotwin20/scripts:.../robotwin20/src:examples/forge-skills/pick-place-workflow/src .venv/bin/python -m pytest ...`；isaacsim_lab 需自己的三路径组合。robotwin20 有 13 个既有失败（12 grounding + 1 task_video 顺序敏感）与本次工作无关。
- P2B-1（stack prepare_route 工厂）仍待实现：把 relation 绑定映射进 `PersistentPreparationProvider` 组合；q5 qualification 模式（materialize→verify→approve→run→validate→evidence-approve 六步，命令见本日操作）可为 stack 复用（换 qualification-id 与 artifact root）。
- JEV 另两个决策点（method_fragment_selection、recovery_method_selection）仍预留无消费路径。
- 向用户汇报时区分：契约证据 / provider 证据 / live 执行证据（AGENTS.md #13）。

---

*This file is automatically updated by PhyAgentOS when important information should be remembered.*
