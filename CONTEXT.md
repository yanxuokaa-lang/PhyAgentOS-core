# PAOS Evolution Domain Glossary

本文件只记录领域术语，不规定代码实现细节。

## Execution Runtime Binding

Execution Runtime Binding 是任务与实际执行环境之间的归属关系，不代表任务采用某一种方法或固定流程。
_Avoid_: 将执行环境归属称为 Skill 使用。

## Tool Contract Binding

Tool Contract Binding 是一次任务使用某个执行接口时所依据的能力契约。它不能授予超出执行环境权限的动作。

## Skill Use

Skill Use 是 Agent 在某次决策中采用一个特定版本方法的事实。同一任务可以组合多个方法，历史使用不随方法更新而改变。
_Avoid_: 将安装能力包等同于实际采用其中的方法。

## Runtime Deployment Bundle

Runtime Deployment Bundle 是部署执行能力所需的可安装资源集合。它的生命周期与任务方法的选用不同。

## PAOS Core

PAOS Core 是任务、执行事实、Skill binding、候选生命周期和最终权限的现有宿主。它不包含某一篇
自我进化论文的具体算法。

## evolution module

`evolution` 是 PAOS 中独立、可选的自我进化扩展模块。它消费 Core 提供的 episode、transition、
settlement 和 candidate 接口，并把方法产生的候选交回既有生命周期。它不是第二个任务调度器、
事实库、planner 或 verifier。

代码位于 `extensions/evolution/`，拥有独立 `pyproject.toml`、测试、构建产物和本地 `.venv`。
PAOS 根 distribution 不包含该包；Core 只定义并调用 method-agnostic episode hook。同进程部署安装
extension wheel，出现依赖冲突、崩溃隔离或持续资源占用需求时才切换为独立 worker transport。

## Evolution method

Evolution method 是 `evolution` 模块内一种可注册的经验更新方式。方法拥有自己的归因、记忆更新或
候选生成逻辑，但不拥有 PAOS 的执行权限和最终晋升权。不同方法的证据、评测和后续使用结果相互隔离。

## EvoPhy

`EvoPhy` 是当前论文对应的 Evolution method 标识：从物理交互反馈驱动具身 Skill 自我进化。它是
`evolution` 下的一个方法，不是 PAOS Core 或 `evolution` 宿主模块的总称。

## PULSE

PULSE（Physical Outcome Logging for Skill Evolution）是 EvoPhy 使用的物理结果记录方式。它记录转移
的预期结果、后续观测、证据覆盖、延迟窗口和成本。

## TRACE

TRACE（Transition Attribution from Consequence Evidence）是 EvoPhy 的转移归因方法。它沿着 PULSE
记录定位最早偏离，输出排序后的转移、joint cause set 和 unknown。

## Local Skill Patch

Local Skill Patch 是针对单条工作流转移的局部 Skill 修订，改变 expectation、observation、decision
或 recovery 关系，并通过后续任务评估。

## Candidate

Candidate 是 Evolution method 提出的待评估 Skill/workflow 修订。Candidate 不是已经生效的 Skill，
只有经过既有评测与 promotion 边界后，才可能影响后续 binding。

## Future-use observation

Future-use observation 是对已晋升 Candidate 在后续任务中的实际使用结果的观察。它用于衡量迁移收益、
干扰和反证，不改写历史 episode。
