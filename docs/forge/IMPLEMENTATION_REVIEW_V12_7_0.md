# v12.7.0 Seven-Dimension Code Review / 七维实现审核

## Review scope / 审核范围

This review covers the two recorded failures: multi-view observation lineage at
`manipulation.prepare`, and replan projection/preserve/failure/convergence behavior.
It evaluates the implementation against PAOS ownership boundaries. It is a no-motion
source and test review, not a benchmark-success or physical-motion claim.

本审核覆盖两份已保存诊断：`manipulation.prepare` 的多视角观测血缘，以及 replan 的
projection、preserve、失败语义与收敛行为。审核依据 PAOS 所有权边界进行；这是无运动
源码与测试审核，不是 benchmark 跑通或真实运动成功声明。

## Findings and disposition / 问题与处理

- **Blocker, fixed:** valid synchronized observations exposed multiple top-level depth
  artifacts and were rejected by a single-view count assertion. The Adapter now selects
  exactly one view through the current binding's observation, frame, and calibration
  lineage. Missing, duplicate, or mismatched lineage remains fail-closed.
- **Major, fixed:** a recovery node could be DAG-ready while a ToolSpec predecessor or
  evidence source slot was unreachable. Plan admission now validates source-slot
  reachability from ToolSpec declarations before starting a model node turn.
- **Major, fixed:** `preserve_node_ids` could name a node absent from the replacement
  graph, leaving metadata without the node/settlement needed by downstream projection.
  Revision admission now requires the preserved node in both graphs, settled, and
  digest-identical before carrying settlement forward.
- **Major, fixed:** preparation failures lacked ownership and recovery semantics, so the
  Agent inferred Runtime repairs from prose. Query results now distinguish evidence,
  provider, timeout, and Adapter faults with retry/replan/recommended-action fields.
- **Major, fixed:** repeated context/readiness reads consumed planning turns without
  durable progress. AgentLoop now fingerprints Coordinator selection, rejection, and
  execution facts, offers one corrective turn, then returns
  `node_selection_no_progress` without dispatching work.
- **Major, fixed:** historical graph replay used active-revision settlements. Replay now
  requests effective settlements for each graph's own revision.
- **Major, fixed during review:** the first failure classification treated every declared
  provider rejection as an Adapter defect. Defaults now classify declared constraints as
  `runtime_provider`; unexpected exceptions alone are `runtime_adapter`, and stale or
  lineage defects are owned by `evidence`.
- **Major, fixed during review:** provider timeout was initially both retryable in the
  current revision and marked as requiring replan. It is now explicitly retryable in the
  current revision without forcing a replacement graph.

No unresolved Blocker or Major remains in the changed paths. The live benchmark was not
run, so model decision quality and simulator integration remain acceptance work rather
than evidence supplied by this review.

## Seven dimensions / 七个维度

| Dimension / 维度 | Evidence / 依据 | Assessment / 结论 |
| --- | --- | --- |
| Architecture integration / 架构集成 | Agent selects outcomes; ToolSpec declares projections; Coordinator admits revisions and persists facts; Adapter owns private perception inputs; Gateway remains Action boundary. | Pass. No parallel planner, state machine, or execution path. / 通过：未新增平行规划器、状态机或执行路径。 |
| Correctness / 正确性 | Multi-view resolver, projection admission, preserve validation, revision-local replay, and structured failure tests. | Pass for covered contracts; live benchmark not claimed. / 覆盖契约通过，不声称真实 benchmark 已跑通。 |
| Recovery and idempotency / 恢复与幂等 | Non-replannable Runtime fault stops before model recovery; preserved settlement requires unchanged graph identity; no Action replay added. | Pass. Recovery follows persisted facts and remains fail-closed. / 通过：恢复只依据持久化事实。 |
| Robotics safety / 机器人安全 | Missing/ambiguous frame, calibration, view, collision, IK, authorization, Gateway, and terminal facts remain rejecting; tests are Query-only/no-motion. | Pass. No safety gate was relaxed and no motion was executed. / 通过：未放宽门禁、未执行运动。 |
| Extension compatibility / 扩展兼容 | View selection uses opaque lineage; projection admission reads generic ToolSpec source slots; progress reads generic Coordinator facts. | Pass. No color, RGB ordering, benchmark layout, provider, or camera-ID branch. / 通过：无颜色、排列、布局、provider 或相机 ID 专用分支。 |
| Observability and maintainability / 可观测与可维护性 | Stable `failure_owner`, retry/replan semantics, recommended action, evidence requirements, and no-progress code; two diagnoses record provenance. | Pass. Errors identify the owning layer without parsing prose. / 通过：错误可直接定位所有者。 |
| AgentLoop autonomy and convergence / AgentLoop 自主性与收敛 | One corrective turn followed by bounded failure on an unchanged Coordinator fingerprint. Host does not select records, issue Queries, replan, or execute Actions. | Pass. Agent retains next-step choice and loops terminate on no progress. / 通过：Agent 保留决策权且无进展时收敛。 |

## Validation boundary / 验证边界

The focused Core and Adapter/Skill suites exercise the modified contracts without
starting Runtime, Gateway, simulator, or an AgentTask. Packaging checks verify only
that the installable Skill and Node contain the reviewed sources and match the existing
manifest lock mechanism. They do not authorize motion.

聚焦 Core、Adapter/Skill 测试在不启动 Runtime、Gateway、仿真器或 AgentTask 的前提下
覆盖修改契约。打包验证仅证明可安装 Skill/Node 包含审核源码并满足既有 manifest lock，
不构成运动授权。

- Full Core: `773 passed`.
- Focused Core/AgentLoop: `263 passed`.
- Focused Adapter/Skill/release: `250 passed`.
- Full Adapter/Skill: `1136 passed, 1 skipped, 5 failed`; each failure reproduced
  unchanged in a clean `HEAD` archive and is outside the changed paths.
- Ruff, compileall, and `git diff --check`: passed.
- Node `0.10.3`: SHA-256
  `f1379e2aff8162397bab08e313118f6222f7b0f5192673e7a7b82ea1543fb69a`.
- Skill `2.10.9`: SHA-256
  `be328fdc12f9a8065365e1be8c2da1017ef660bdb9430119a8bc964a5b59e28a`.
