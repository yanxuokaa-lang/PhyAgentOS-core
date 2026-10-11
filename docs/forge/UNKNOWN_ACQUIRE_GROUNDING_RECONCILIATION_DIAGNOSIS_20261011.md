# Unknown Acquire Grounding Reconciliation Diagnosis / 未知抓取 Grounding 对账诊断

Date: 2026-10-11 (Asia/Shanghai)

## Incident Facts / 事件事实

The affected AgentTask is `task_241ca666321049c1`. Its final active revision is
`revision_487777c9e3c2420c`; the failed node is
`bind_current_visible_blue_green`, using `scene.bind`.

The authoritative chain is:

1. Initial observe, understand, capabilities, goal, and binding succeeded.
2. `red_acquire` returned `status=unknown`, `failure_code=SimulationProbeError`,
   `phase=lift`, `world_change_started=true`, `outcome_known=false`,
   `requires_replan=true`, and `new_scene_revision=...-2`.
3. The Runtime artifact contained no authoritative attachment or detachment fact;
   `scene_effects.effect_scope_complete=false` and
   `carry_forward_authorized=false`.
4. The recovery scene observation, `scene.understand`, and
   `manipulation.capabilities` all succeeded on the new scene revision.
5. The later `scene.bind` response was `status=unavailable`,
   `error.code=grounding_unavailable`, with diagnostics:

```text
expected.holding_state = ["empty", "holding"]
actual.holding_state   = "uncertain"
scene_validity          = "action_driven"
scene_revision          = current revision
```

No Action was submitted after the unknown acquire. The task was nevertheless
terminalized because the failed binding was sent to ordinary recovery, where the
recovery decision selected stop.

## Root Cause / 根因

The Runtime behavior was correct and fail-closed: a post-step acquire failure
changed the world but did not prove whether the object was attached. A fresh
image or semantic understanding cannot establish possession, so grounding
rejected `scene.bind` while the provider state remained `uncertain`.

The Core defect was classification at the AgentLoop boundary. The existing
`NodeSettlement` already carries the provider-neutral `recommended_action`
field, but grounding did not populate it for uncertain possession and the
planning recovery path treated the resulting binding failure as an ordinary
failed Query. That allowed a model-level `stop` choice to convert unresolved
Runtime ownership into `failed`, releasing the task lifecycle too early.

This is not a motion-authorization, target, scene-understanding, benchmark, or
selection defect. It is a missing reconciliation handoff after an unknown
world-changing Action.

## Generic Repair / 通用修复

- Grounding now emits `recommended_action=reconcile_world` and
  `fresh_evidence_requirements=("runtime_possession_reconciliation",)` only when
  the Runtime snapshot explicitly reports `holding_state=uncertain`.
- `PlanningLoopAdapter._recover()` treats that Runtime-owned recommendation as a
  safety handoff before invoking the recovery model. It records the existing
  blocked-node event and returns `reconciliation_required:<node>` while keeping
  the AgentTask in `awaiting_replan`.
- No possession state is inferred. `empty`/`holding` can still be established
  only by Runtime-owned facts; binding, preparation, Action admission, and
  `motion_authorized` remain unchanged.
- No Action or Query is replayed automatically. Once an authorized Runtime
  reconciliation changes the snapshot to a known state, the same task can be
  resumed through the normal bounded revision path.

## PAOS Ownership / PAOS 所有权

- Runtime owns physical outcome, possession, scene validity, and reconciliation
  facts.
- Gateway owns invocation/admission/readiness and does not infer possession.
- Coordinator owns append-only records, node settlement, task slot, and bounded
  recovery status.
- Agent chooses later plan content only after the Runtime reconciliation handoff
  has cleared; it cannot reinterpret `uncertain` as safe.

## Seven-Dimension Review / 七维审查

1. **Architecture / 架构**: The change is split at the existing Runtime
   diagnostics and PlanningLoop recovery seams; no parallel scheduler or RGB
   branch is introduced.
2. **Correctness / 正确性**: Only explicit `holding_state=uncertain` receives the
   reconciliation recommendation; ordinary grounding failures keep their old
   behavior.
3. **Errors and observability / 错误与可观测性**: The response retains
   `grounding_unavailable`, expected/actual state, and fresh-evidence metadata;
   the Coordinator records `reconciliation_required` instead of hiding it in a
   terminal failure.
4. **Recovery and idempotency / 恢复与幂等**: The original invocation and
   settlement stay immutable; no Action replay, automatic retry, or fabricated
   possession is added.
5. **Robotics safety / 机器人安全**: Unknown possession remains fail-closed;
   no frame, calibration, route, collision, IK, admission, or authorization
   gate is relaxed. Validation is no-motion.
6. **Extension compatibility / 扩展兼容**: Core consumes the existing generic
   `recommended_action` contract; the adapter branch is based on possession
   state, not task name, color, object, camera, or benchmark.
7. **AgentLoop convergence and maintainability / AgentLoop 收敛与维护**: A
   Runtime reconciliation obligation now deterministically blocks before model
   stop/replan, retains the single-task owner, and can be resumed after external
   Runtime evidence becomes authoritative.

## Validation / 验证

- Core recovery/planning/long-horizon/Agent foundation/Skill tests:
  `280 passed`.
- RobotWin grounding, persistent manipulation, preparation, and route-builder
  tests: `137 passed`.
- Ruff, compileall, and `git diff --check` passed.
- All tests used local fakes or fixtures only: no live AgentTask, Gateway Query,
  Gateway Action, camera capture, simulator step, or physical motion.
