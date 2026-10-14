# `current_support_bind` 阻塞诊断

日期：2026-10-14（Asia/Shanghai）
任务：`task_8fed40f6212c4b19`
诊断范围：只读检查，不恢复任务、不修改任务状态、不调用 Runtime Query/Action。

## 结论

这次不是 `scene.bind` Gateway 调用失败，也不是三块方块绑定失败。真正的阻塞是：恢复计划把理解结果中的 `e4–e8` 当成五个必须绑定的支撑面实体，但理解结果同时报告这些实体跨视角身份不确定，并且全部共享同一个 metric localization。于是 `current_support_bind` 没有任何安全、合法的 Coordinator selection；AgentLoop 两次 corrective turn 后事实仍不变，按 `node_selection_no_progress` 进入 blocked/awaiting-replan。

更准确地说，`e4–e8` 是一组尚未解析的支撑/几何候选，不是五个已经可以提交给 `scene.bind` 的独立物理对象。把它们全部绑定会把同一几何证据复制成多个身份，可能让后续 route/collision planning 使用错误的支撑关系，因此当前 fail-closed 是正确的；错误在于恢复图把一个不可选择的语义问题物化成了普通绑定节点。

## 已确认事实

### 1. 世界变化和恢复边界

- `green_place` 的 terminal 结果为 `failed`，`failure_code=placement_postcondition_failed`。
- 该 Action 的 `release_confirmed=true`、`retreat_completed=true`、`clear_of_target=true`、`possession_state=empty`，新场景为 `623928b0a82a4a108a6ba743400395b8-5`。
- Coordinator 已按“已知后置条件失败”创建 fresh-evidence recovery；没有重放 green acquire/place，也没有重新执行红块动作。
- 恢复 revision `revision_b33b0fd932774bb1` 的 `scene.understand`、`manipulation.capabilities` 和 `current_scene_bind` 均成功落盘。该 `scene.bind` 只绑定了三个方块：
  - `e1 -> block-blue-1`
  - `e2 -> block-red-1`
  - `e3 -> block-green-1`

### 2. 当前理解结果

在同一 observation/scene revision 中，理解结果返回：

- `e1`：blue cube
- `e2`：red cube
- `e3`：green cube
- `e4`：white surface
- `e5–e8`：light gray surface

同时返回以下三类歧义：

1. `e5/e6` 在不同 view 中无法互相匹配；
2. `e7/e8` 在不同 view 中无法互相匹配；
3. `e4–e8` 多个 semantic entity 共享同一 metric localization。

这些实体的 spatial envelope 均为同一个范围：约 `[-0.4576,-0.3282,0.6101]` 到 `[0.4559,0.2024,1.0284]`。这不是五个独立支撑面已被可靠定位的证据。

理解结果中的 `on` 关系也重复指向多个表面候选，例如同一个方块同时被报告为位于 `e4`、`e5`、`e6`。因此这些关系不能直接当成唯一 support geometry。

### 3. 当前 revision 的实际状态

`revision_4ce7a2fa043b42a8` 只物化了一个节点：

```text
current_support_bind
obligation = bind_previously_unbound_observed_support_surfaces_for_green_failure_reconciliation
entity_refs = [e4, e5, e6, e7, e8]
```

该 revision 没有 `planning_selection`、没有 `execution_record`、没有 `scene.bind` 调用。事件顺序是：

```text
plan_continuation_started
  -> skill_use_recorded
  -> corrective planning turn
  -> corrective planning turn
  -> planning_node_blocked: node_selection_no_progress
```

所以报错中的“selection rejected”不能理解为 Runtime 拒绝了一个已提交的绑定；实际上 Coordinator 从未收到可执行的 selection。

## 根因分层

### A. 理解层把候选实体和可绑定实体混在一个集合

`scene.understand` 输出了 `entities`，但对 `identity_uncertain`、跨视角无法配对、共享 metric localization 没有提供足够强的“不可绑定”投影。模型能看到 `e4–e8` 是实体条目，却必须自行推断它们不能作为独立绑定对象。

这会把 provider 的候选/假设误当作稳定 execution grounding。问题是通用的：任何多视角实例重复、点云分割重复或 enrichment 复制都可能触发。

### B. 恢复规划把 support reconciliation 错建成 entity binding

绿色放置后置条件失败需要核对对象当前 identity、support relation 和 collision geometry；这不等价于“把理解结果中所有表面实体都绑定”。当前恢复图用 `entity_refs=[e4..e8]` 表达了错误的粒度：它要求逐个绑定候选，而不是要求解析一个唯一、可验证的 support relation/geometry。

### C. partial binding 的完成语义不足

`current_scene_bind` 成功绑定三个方块是有效的局部事实，但不代表失败 Action 的 support state 已解决。恢复计划随后追加 `current_support_bind` 是为了补足这个缺口，这个方向正确；但它没有把“局部 binding 成功、全局 reconciliation 仍未完成”作为显式 settlement 条件，而是生成了一个必然依赖模型选择的普通节点。

### D. AgentLoop 将确定性不可选误判成模型无进展

当所有候选 support entity 都处于 ambiguous/shared-localization 状态时，没有一个安全 selection。继续发送 corrective turn 不会改变 Coordinator facts，因为没有新的证据、没有新的 Tool 结果、也没有新的 revision。`node_selection_no_progress` 只是最终症状，根因是 selection admission 前缺少“不可绑定候选”诊断和受治理恢复分支。

## 当前行为中正确的部分

- 没有把 `e4–e8` 猜成某个默认桌面或 simulator geometry；
- 没有用旧 scene revision 的几何替代当前证据；
- 没有把三个方块绑定结果伪装成支撑面已经解析；
- 没有在 support 不确定时继续 acquire/place；
- 没有重放已经 terminal 的 green Action；
- `scene.bind` 没有被错误调用，Gateway/Runtime 没有被推进。

这些 fail-closed 行为应保留。

## 通用修复方向（本诊断不实施代码）

1. **理解输出增加绑定资格和关系资格。** 对实体/关系显式区分 `unique`、`ambiguous`、`unresolved`，并记录 metric geometry 是否唯一。Coordinator 只允许 `unique` 且 lineage 完整的实体进入 `scene.bind`。
2. **把 support reconciliation 建模为关系/几何解析义务。** 不要求绑定所有语义表面；应选择唯一 support relation 或唯一 observed support geometry。若候选共享同一 geometry，必须先解决 geometry identity，不能逐个绑定。
3. **让 Coordinator 在 selection 前过滤不可绑定引用。** 对 ambiguous、跨视角不匹配、共享 geometry 的 refs 返回结构化诊断，例如 `support_binding_not_admissible`、`ambiguous_entity_refs`、`non_unique_metric_geometry`，不要把它们留给模型反复猜选。
4. **保留局部 binding 与全局 reconciliation 的区别。** 三块方块的 binding settlement 可以完成，但必须继续持久化 `unresolved_effects=[object_support_state]`；只有 support relation/geometry 得到当前证据确认，恢复义务才算完成。
5. **为确定性不可选提供有限恢复。** 若已有只读的 support/geometry reconciliation Query，则创建新 revision 使用该 Query；若没有能增加信息的 Query，应直接进入 awaiting operator/replan，并说明缺少哪一类证据，而不是重复 corrective turn。不得自动观察、自动选取或自动执行动作。
6. **AgentLoop 收敛规则按“事实是否可能改变”分类。** 没有新证据、selection 候选集未改变时，第二次 corrective turn 应转成结构化 `selection_admission_blocked`，保留恢复义务和诊断；只有新的 observation/Query/revision 才允许再次尝试。
7. **保持通用性。** 修复应围绕 identity status、support relation、metric geometry lineage 和 selection admission，不得检查颜色、方块、RGB 任务名或特定 node id。

## 不应采用的修复

- 不应默认选择 `e4` 作为桌面；
- 不应把 `e4–e8` 全部强制绑定以“让节点前进”；
- 不应把三块 binding 当作 support 已解决；
- 不应因 `node_selection_no_progress` 自动重试 acquire/place；
- 不应仅通过增加 prompt 文案解决一个由证据资格和规划粒度造成的问题；
- 不应通过放宽 ambiguity gate、复用旧 geometry 或引入 RGB 专用分支绕过阻塞。

## 最终定性

本次阻塞是一个“证据候选被错误提升为绑定义务”的架构问题：理解层返回了可供分析的表面候选，恢复规划却要求把这些候选逐个绑定；由于候选没有唯一身份和唯一几何，Coordinator 没有合法 selection，AgentLoop 最终以 `node_selection_no_progress` 停止。安全门禁本身没有失效，真正需要修复的是理解结果的资格投影、support reconciliation 的建模粒度以及对确定性不可选节点的 AgentLoop 收敛策略。
