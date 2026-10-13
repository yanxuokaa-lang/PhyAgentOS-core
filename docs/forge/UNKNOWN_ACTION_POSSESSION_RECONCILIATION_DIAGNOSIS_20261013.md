# Unknown Action 后的 possession 与身份对账诊断

日期：2026-10-13（Asia/Shanghai）
范围：PAOS AgentLoop、Coordinator、provider-neutral scene understanding、RobotWin persistent Adapter/Runtime
验证边界：只读制品与 no-motion 测试；本文不授权或触发任何运动。

## 结论

故障不是第二次 `scene.observe` 排除了被操作对象，也不是 `scene.bind` 参数错误。原始动作后图像仍包含该对象；视觉语义 provider 在机械臂遮挡下没有为它生成新的 observation-local entity，恢复 PlanGraph 随后把“不可复用旧视觉 ID”错误收缩成“只处理本轮已识别的其他实体”。受未知 Action 影响的稳定执行身份因而从恢复义务中静默消失，直到 Runtime 在 `scene.bind` 边界以 `holding_state=uncertain` 和 `runtime_possession_reconciliation` fail-closed。

正确边界是：旧视觉 ID、几何、binding、candidate 和 preparation 均不可跨世界变化复用；但受 Action 影响的稳定执行身份、原 invocation、未解决物理效果和需要重新建立的当前视觉身份必须继续存在于 Coordinator-owned 恢复上下文中。

## 证据链

任务 `task_2d374f88b79d4ae9` 的 acquire 终态为：

```text
status=unknown
failed_phase=lift
failure_code=SimulationProbeError
error_detail="attached object did not lift with the gripper"
world_change_started=true
outcome_known=false
recommended_action=reconcile_world
new_scene_revision=45a6b1e84eeb4aa9a48d411923062aaf-2
```

Runtime 同时声明 `effect_scope_complete=false`、`carry_forward_authorized=false`，因此禁止复制动作前视觉实体与几何。动作后观察成功，原始 head-camera 图像中仍可看到受影响对象，但它位于夹爪下方且受到明显遮挡；动作后 `scene.understand` 仅输出其他对象、机器人和表面，没有输出该对象的新 observation-local entity。

恢复 PlanGraph 随后只物化当前可见实体的绑定义务。该 selection 被 Coordinator 接受，Gateway 也实际调用了 `scene.bind`；Runtime 最终返回：

```text
grounding_unavailable
recommended_action=reconcile_world
fresh_evidence_requirements=[runtime_possession_reconciliation]
expected holding_state=[empty, holding]
actual holding_state=uncertain
```

因此第二次观察是必要且成功的；错误发生在“未知物理效果的恢复义务”和“开放世界视觉结果”之间。

## 根因分层

### Runtime 后置条件分类

现有 lift 检查只比较对象竖直位移。所有发生过 simulator step 的异常默认转为 `outcome_unknown`，即便 Runtime 已执行完整 lift 轨迹并可测得对象仍受支撑。另一方面，单凭错误字符串或单一位移阈值也不足以证明夹爪空载。

修复原则：使用异常类型承载结构化、Runtime-owned 测量。只有同时证明 lift 路段已到达、对象未达到最小提升、对象仍在支撑面且控制器停止时，才结算为 known failed acquire、`possession_state=empty`、`object_support_state=on_support`。任一测量缺失或不一致都继续保持 unknown。

### Coordinator 身份连续性

现有 `carried_entities` 只允许完整 scene effects 证明为 unchanged 或 held 的实体，unknown Action 返回空集合是正确的。缺失的是并列的 reconciliation hypothesis：它不 carry-forward 旧实体，而只说明某个稳定执行身份仍需在当前场景中被验证。

修复原则：从持久化 Action、动作前 `scene.bind` 与 `scene.understand` 构造 Coordinator-owned 假设，包含稳定执行身份、旧 observation-local 身份、旧语义类别、原 invocation、来源场景和未解决字段；不包含旧几何、位姿、calibration 或 candidate。

### Scene understanding 开放世界语义

视觉 provider 当前只按图像枚举可见实体。遮挡漏检会使对象从输出中消失，而不是产生“该稳定身份仍未对账”的结构化事实。

修复原则：将 reconciliation hypothesis 作为非权威注意线索传给 provider；无论 provider 是否重新识别该对象，PAOS endpoint 都必须为每个 hypothesis 生成 reconciliation 结果。没有被 provider 证实的新 observation-local 对应时，状态必须保持 `unresolved`，不得自动复用旧 ID 或声称对象不存在。

### AgentLoop 收敛

恢复的完成条件不是“绑定了若干当前可见实体”，而是“未知物理效果已被 Runtime 结算，且受影响稳定身份的当前状态已解决或明确阻塞”。局部绑定可以成为证据，但不能清除未解决义务。

修复原则：replan delta、节点 prompt 和持久阶段上下文保留 `runtime_possession_reconciliation`、`affected_execution_entity_reconciliation`、原 invocation 和受影响稳定身份。恢复次数保持有界；不得自动重放原 Action。

## PAOS 所有权边界

| 层 | 负责 | 不负责 |
|---|---|---|
| Runtime/Adapter | 物理测量、possession、支撑状态、停止结果、scene effects | 用户目标、视觉 ID 猜测、Agent 计划 |
| Coordinator | 持久化 invocation、settlement、稳定身份、恢复要求和来源 | 从自然语言或图像猜物理终态 |
| Scene understanding | 当前 observation-local 语义、遮挡/歧义、假设的视觉核查 | 复用旧几何、宣告 possession、授权运动 |
| AgentLoop | 编排有界 Query/replan 后缀、遵守 no-replay | 覆盖 Runtime 事实、直接重放未知 Action |

## 通用恢复状态机

```text
world-changing Action terminal
  ├─ known success
  │    -> normal post-action scene refresh
  ├─ known failed + stable possession/support facts
  │    -> refresh current evidence
  │    -> current understanding/binding
  │    -> new propose/prepare/new Action invocation if still required
  └─ outcome unknown
       -> retain affected stable execution identity
       -> Runtime possession reconciliation
       ├─ holding: prohibit reacquire; plan held-object recovery/place
       ├─ empty + on_support/displaced: refresh and re-localize; new attempt only through new plan
       └─ unresolved: bounded active sensing/safe recovery or explicit blocked state
```

## 非目标与禁止项

- 不添加颜色、方块、排列、benchmark、特定 task ID、节点名或 provider 名称分支。
- 不把历史 observation-local `entity_ref` 当作当前实体。
- 不将模型文本当作 possession 或支撑事实。
- 不因已识别其他实体就认为 reconciliation 完成。
- 不在 unknown outcome 上自动重试 acquire/place。
- 不新增无证据支持的 hash、baseline、冻结 contract 或全局 gate。

## 验证计划

1. Runtime fixture：完整 lift 到达 + 对象未提升 + 仍受支撑，结算 known failed/empty；缺少支撑证据时仍 unknown。
2. Adapter fixture：known failed acquire 的显式 empty possession 同步到 worker 与 public Action projection。
3. Core contract：Coordinator 自动注入 reconciliation hypotheses，Agent 不能手填或篡改。
4. Understanding fixture：provider 漏检时仍输出 unresolved reconciliation；不得追加旧实体到当前 entities。
5. AgentLoop fixture：unknown world effect 的 replan requirements 与 durable context 保留受影响稳定身份；不重放原 Action。
6. 回归：正常 held carry-forward、known placement failure、普通 scene understanding 和无关任务均保持原语义。
