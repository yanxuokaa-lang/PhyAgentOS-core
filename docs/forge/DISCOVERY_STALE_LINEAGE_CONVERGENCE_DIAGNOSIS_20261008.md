# Discovery Stale-Lineage Convergence Diagnosis / Discovery 过期血缘收敛诊断

## Problem / 问题

After `place_green` returned an uncertain, world-changing outcome, the Agent
correctly did not retry the Action. However, discovery repeatedly inspected and
submitted the same pre-action `scene.bind` inputs. `ready=true` was treated as
if it meant the binding lineage was current, although it only meant the Tool
context was available.

放置动作返回“世界可能已改变”的未知结果后，Agent 没有重试动作，这是正确的；但
discovery 多次检查并提交同一个动作前 `scene.bind` 输入。`ready=true` 只表示 Tool
上下文可用，并不表示绑定血缘仍然新鲜。

## AgentLoop Failure / AgentLoop 失败模式

```text
stale scene.bind rejection
  -> generic grounding_unavailable record
  -> no structured lineage fingerprint
  -> model checks the same Tool context
  -> same bind selection is submitted again
  -> task remains executing without a new task-bound record
```

The existing no-progress handling is not sufficient because it recognizes only
some provider errors and does not carry a freshness requirement from the
Adapter into the discovery progress state.

## Generic Recovery Contract / 通用恢复契约

When a structured `scene_revision_mismatch` is observed:

1. Mark the current binding lineage stale and reject it for reuse.
2. Permit at most one corrective Agent turn to choose a fresh declared
   observation/understanding path.
3. Require a new task-bound observation or understanding record before another
   bind using the changed world.
4. If no new fact appears, terminate with an explicit stale-lineage
   no-progress outcome instead of looping.

The loop does not call `scene.observe`, `scene.understand`, `scene.bind`, or an
Action automatically. It exposes the fact and the legal next-step condition to
the Agent, preserving PAOS autonomy and ownership.

## PAOS Design Alignment / PAOS 设计对齐

- **Perception** produces observations and scene understanding.
- **Planning** chooses a source lineage and proposes a binding.
- **Admission** validates revision and source identity; stale inputs fail
  closed.
- **Execution** remains behind the existing Action authorization and
  reconciliation boundary.
- **Settlement** records whether a new evidence fact was produced; repeated
  stale failures cannot masquerade as progress.

The implementation reuses existing task records, ToolSpec metadata, and
progress accounting. It does not add a parallel state machine or benchmark
special case.

## Seven-Dimension Acceptance / 七维验收

- Architecture: error ownership remains Adapter/Runtime; convergence remains
  Core/AgentLoop.
- Correctness: expected/actual scene revisions are preserved and compared.
- Recovery/idempotency: stale selections are not silently rewritten or replayed.
- Extensibility: contract is provider-neutral and works for any action-driven
  scene lineage.
- Observability: structured code, stage, recommendation, and revisions are
  persisted in the Tool record.
- AgentLoop convergence: one corrective turn, then explicit no-progress.
- Robotics safety: no automatic observation or motion; unknown Actions still
  require reconciliation.
