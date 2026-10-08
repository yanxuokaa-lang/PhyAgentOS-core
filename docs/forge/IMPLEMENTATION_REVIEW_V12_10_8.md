# Implementation Review v12.10.8 / v12.10.8 实现审查

## Findings / Findings

### Major 1: operation-specific wording leaked into generic recovery

`AgentLoop` described every structured stale-lineage failure as “this binding”
and terminated with “Discovery stopped”. That was incorrect for a future
scene-lineage consumer such as a capability or route Query, and could cause an
Agent to choose the wrong recovery node.

**Fix:** `PhyAgentOS/agent/loop.py` now says “this operation”, “dependent
operation”, and “Control loop stopped”. No Tool name, color, arrangement, or
camera branch was added.

### Major 2: stale recovery was lost across bounded AgentLoop turns

`stale_lineage_signature` lived only in one `_run_agent_loop` invocation. A
persisted Query response could therefore be followed by a new bounded turn
that treated the same old selection as a first failure and submitted it again.

**Fix:** the loop reconstructs the latest signature from the active revision's
persisted Query responses. A successful `scene.observe` or `scene.understand`
record clears the earlier stale fact; otherwise the same expected/actual pair
is rejected on the next bounded turn. No automatic evidence Query or Action is
introduced.

## Seven-Dimension Review / 七维验收

- **Architecture / 架构:** Adapter owns current-scene truth and structured
  rejection; Coordinator persists the response; AgentLoop owns the decision and
  convergence. No parallel state machine.
- **Correctness / 正确性:** expected and actual revisions are compared and
  recovered from durable records; stale identity is never rewritten.
- **Recovery and idempotency / 恢复幂等:** same stale selection is not replayed
  across bounded turns; unknown Action reconciliation remains untouched.
- **Extensibility / 扩展兼容:** recovery is keyed by structured lineage fields,
  not RGB, colors, ordering, camera names, or a fixed Tool.
- **Observability / 可观测性:** error code, stage, expected/actual revision,
  recommendation, and persisted response remain available to Core and audit.
- **AgentLoop autonomy and convergence / 自主性与收敛:** Agent chooses fresh
  evidence; one correction remains possible, then repeated stale input stops
  explicitly without host-scheduled observation or Action.
- **Robotics safety / 机器人安全:** all tests are fake/no-motion; perception,
  planning, admission, and execution remain separate, and no motion authority
  is gained from a recovery hint.

## Validation / 验证

- Focused Adapter/Core: `193 passed`.
- Planning/recovery suite: rerun after the fix; no Gateway or simulator.
- `ruff`, `compileall`, and `git diff --check` required before acceptance.

## Residual Risk / 剩余风险

The full Adapter collection still depends on optional local packages and legacy
fixtures (`scipy`, `cv2`, YAML fixtures). Those are environment failures, not
evidence against this change; changed-path tests remain the acceptance gate.
