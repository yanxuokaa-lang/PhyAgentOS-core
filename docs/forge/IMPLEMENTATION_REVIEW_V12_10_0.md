# Implementation Review v12.10.0 / 七维实现审查

This review supersedes the initial v12.9.15 acceptance conclusion for the persisted-selection
continuation boundary; the v12.9.15 implementation remains the first-stage ordering fix.

## Findings and remediation / 发现与修复

### Major 1: structured wrapper rejection was discarded

`AgentLoopNodeExecutor._resume_node()` reconciled durable records first, but when no record
existed it recognized only strings beginning with `Error:`. Forge wrappers return failures as
JSON with `ok=false`, so deterministic codes such as `scene_bind_missing_entity_refs` were
replaced by `persisted selection execution produced no task-bound record`.

修复：通用解析 wrapper 的 `ok=false` envelope，优先保留 `error.code` 和有界的
`message/detail/reason`；输出经过既有 redaction 并限制为 2000 字符。无法解析、`ok=true`
但无 record 等异常仍保持原有 fail-closed 无记录错误。不会自动重试、重新选择或执行 Tool。

### Major 2: persisted observation selection bypassed freshness comparison

`ForgeToolQueryTool` previously checked stale-retry freshness against literal `arguments` before
resolving a persisted selection. AgentLoop intentionally passes `{}`, so a selected
`scene.observe` retry could increase `max_age_ms` without reaching the existing check.

修复：所有 projection/selection resolution 完成后，才使用 `resolved_arguments` 执行已有
freshness comparison。直接 Query 行为不变，持久化 selection 现在遵守同一规则。

## Seven dimensions / 七个维度

1. **Architecture / 架构：通过。** Coordinator 继续拥有 selection/binding；Tool wrapper
   继续拥有 Query 参数准入；AgentLoop 只解释 wrapper envelope 和 durable record。
2. **Correctness / 正确性：通过。** 校验对象统一为最终解析参数；合法 binding 产生 record，
   非法 binding 保留精确拒绝码且不会进入 Gateway。
3. **Recovery and idempotency / 恢复与幂等：通过。** durable record 仍优先于 wrapper 文本；
   无 record 的确定性拒绝立即收敛，不重新 POST、不重新选择。
4. **Robotics safety / 机器人安全：通过。** 修改仅涉及 Query admission 和错误投影；Action、
   trajectory、collision、frame/calibration、motion authorization 和 stop path 均未变化。
5. **Extensibility / 扩展性：通过。** JSON envelope 解析适用于任意 persisted Tool selection；
   freshness 规则由 tool ID 和参数契约驱动，没有颜色、排列、benchmark、相机或实体分支。
6. **Observability and maintainability / 可观测性与可维护性：通过。** 节点失败保留稳定 code，
   detail 使用既有 redaction 和长度上限；跨 wrapper 测试覆盖 record 与 no-record 两条路径。
7. **AgentLoop autonomy and convergence / 自主性与收敛：通过。** Agent 仍决定 selection；
   Core 不自动 observe、换实体、换候选、换臂、retry、replan 或 Action，只让确定性事实收敛。

## Validation / 验证

```text
PYTHONPATH=src:. python -m pytest -q \
  tests/test_planning_loop.py tests/test_forge_tool_api.py tests/test_planning_selection.py
139 passed

PYTHONPATH=src:. python -m pytest -q tests
795 passed

ruff check PhyAgentOS/agent/planning_loop.py \
  PhyAgentOS/agent/tools/forge_tool_api.py \
  tests/test_planning_loop.py tests/test_forge_tool_api.py
All checks passed!
```

`compileall` and `git diff --check` also pass. All tests are no-motion: no AgentTask was created
or resumed, no real Gateway Query/Action ran, and no simulator or physical state advanced.

## Final disposition / 最终结论

Blocker 0, Major 0, Minor 0 after remediation. This review does not claim Runtime/provider,
collision-world, Action reconciliation, or video behavior changed; those remain outside this diff.
