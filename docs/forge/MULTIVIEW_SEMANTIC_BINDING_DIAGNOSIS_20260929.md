# 同步多视角语义与 scene.bind 选择诊断

日期：2026-09-29
任务：`task_e83a9ebc490b4064` 及后续只读复现实验
安全模式：仅 `scene.observe` / `scene.understand` / `scene.bind` Query；未执行任何 Action。

## 结论

同步双相机采集本身已经正确：`camera/head` 与 `camera/front` 在同一 scene revision 中完成采样，capture skew 为 0 ms。剩余失败由两个相互关联但归属不同的问题造成：

1. Qwen 把已经合并为 canonical 多视角实体的对象再次声明为 `entity_identity_uncertain`，或输出 `entity_ids=[]` 且消息为“未检测到歧义”的否定占位符。
2. Agent 将“未被感知歧义过滤”误解为“任务相关”，在 RGB 方块不可绑定时改选白色支撑面；两个支撑面又共享同一个度量包络，因此 Runtime 正确地拒绝了歧义对应。

这不是 RGB 排列专用问题，也不是 Qwen 服务不可用。它是 Provider canonicalization、Runtime correspondence 和 Agent 任务相关性三层契约未对齐的问题。

## 权威证据

- 同步 `scene.observe` 返回两个视角、单一 scene revision 和 0 ms capture skew。
- Qwen 能稳定识别 red/green/blue canonical entities，并保留双视角 provenance。
- 异常输出同时包含正确 canonical entities 与以下空身份歧义：
  `entity_identity_uncertain(entity_ids=[], message="No cross-view identity uncertainty detected.")`。
- Grounding 对空实体范围按全局歧义处理，因此该占位符会阻塞全部实体。
- Agent 在任务方块被过滤后选择环境 surface，证明推荐列表只表达“感知无歧义”，不能表达“任务相关”。
- 两个 surface 的 metric envelope 完全相同，Runtime 的 ambiguous correspondence 拒绝是正确的 fail-closed 行为。

## 失败场景与现有机制不足

### Canonical 多视角实体与身份歧义冲突

一个实体若已经带有多个 `source_view_indexes`，Provider 就是在声明它是跨视角合并后的 canonical physical entity。对同一实体再次声明“跨视角身份不确定”会使下游无法判断应保留还是拆分。

类型、主键和普通 schema 只能证明字段形状合法，不能证明这两个语义声明互相一致。遗漏该校验会让 Grounding 对正确实体 fail-closed，并诱发 Agent 选择错误候选。

### 空身份歧义否定占位符

Qwen 可能用 ambiguity 数组表达“没有歧义”。空 scope 在 Runtime 中有明确的全局含义，不能直接透传。Adapter 只规范化严格匹配的否定 sentinel；其他空、含糊或未知实体的身份歧义仍然 contract error。

### 环境实体替代任务实体

`recommended_unambiguous_entity_refs` 只排除已知感知歧义，不证明候选满足任务目标。若 Agent 把 support surface、fixture 或 container 当作未解析任务对象的替代物，scene.bind 虽然仍是 Query，也会污染后续规划上下文。

## 通用修复边界

- Provider prompt 明确 canonical multi-view entity、单视角可见和跨视角未匹配检测的区别。
- Adapter 拒绝已合并多视角实体与 identity ambiguity 同时出现。
- Adapter 仅丢弃 `entity_ids=[]` 且严格匹配 no-uncertainty sentinel 的身份歧义；其他情况 fail-closed。
- Runtime 对不同语义实体共享完全相同 metric envelope 增加身份歧义。
- Agent prompt/context 显式提供候选 category，并声明“感知无歧义”不等于“任务相关”；禁止环境实体替代未解析任务对象。
- 不增加 RGB、相机名、Tool ID、固定抓取模板或仿真真值专用分支。
- 不放宽 freshness、标定、workspace、collision、IK、motion authorization、Gateway、Coordinator 或 terminal-result 门禁。

## 验收标准

1. Provider 单元测试覆盖 canonical multi-view 冲突、严格否定 sentinel 和其他空 identity ambiguity。
2. Runtime 测试覆盖重复 metric envelope 与空 identity ambiguity。
3. Agent 测试覆盖候选 category、任务相关性约束和环境实体替代禁令。
4. 同步双相机只读稳定性验证达到 10/10 available，RGB canonical entities 稳定且无空 identity ambiguity。
5. 只读 scene.bind 使用任务相关方块 refs 成功；不得以 environment-only selection 获得成功。
6. 所有 Blocker/Major 在七维实现审查中修复后才可接受。

## 未解决的独立边界

本修复只解决感知语义与绑定选择。最终放置目标仍必须来自符合任务约束的、非 simulator-truth 目标解析机制；不得静默使用 benchmark pose 或 `manipulation.target` 替代。

## v12.3.4 无运动现场验收证据

部署验证时间：2026-09-30（Asia/Shanghai）。验证仅调用只读 Query，未调用
`grasp.propose`、`manipulation.prepare`、`object.acquire`、`object.place` 或
`ForgeTaskVerifier`，因此不构成 RGB 排列任务完成证明。

- 已安装 Skill：`pick-place-workflow 2.9.4`。
- 已安装 Node：`robotwin20_persistent_host 0.9.3`。
- Node SHA-256：`ccdbbb3cd6049169e2f07c35fa7cae9fcab5638e1e57f0c84c74031fc1d4118a`。
- Skill bundle SHA-256：`0247fb4981a90ab8da347e69b5f11369f75ae94d96bfd2ced77fab8fa901fff4`。
- `scene.observe`：10/10 `available`；`camera/head` 与 `camera/front` 均出现于同一采样，capture skew 均为 0 ms。
- `scene.understand`：10/10 `available`；每轮均稳定产出三个可操作实体：
  `entity://e1`（red cube）、`entity://e2`（blue cube）、`entity://e3`（green cube）。
- `scene.bind`：使用当前任务的三个方块引用返回 `available`；未使用 environment-only selection，
  未以支撑面替代任务实体。
- 当前 scene revision：`04bd35d427f1464f8ca22a7ff47d10fc-1`。
- Runtime execution binding：red → `block-red-1`，green → `block-green-1`，blue → `block-blue-1`。
- `motion_authorized=false` 在整个验证期间保持不变；这证明绑定 Query 成功，不授予运动权限。

该结果将失败边界收窄为此前确认的 Provider/Runtime/Agent 契约错位：同步采样、语义 canonicalization、
空否定 ambiguity 规范化、任务相关性约束和 binding provenance 现已对齐。冷启动延迟仍是性能风险，
但不是实体身份或双视角绑定正确性的阻塞项。
