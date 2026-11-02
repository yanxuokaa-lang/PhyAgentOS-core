# v16.5.0 implementation review / 实现复核

## Findings and disposition / 问题与处理

1. **Major, fixed — qualification happened too late.** Prior task-affordance
   qualification checked grasp/process geometry but could admit a final approach
   that violates the embodiment workspace. The injected Adapter-private probe
   now checks configured pre-grasp variants and the complete short approach
   before returning opaque candidates. Full Action preparation remains required.
2. **Major, fixed — incomplete diagnostic identity.** Initial probe artifacts
   omitted observation/frame/calibration identity and numeric workspace evidence.
   Both accepted and rejected artifacts now contain the full capture identity,
   per-variant world grasp/pre-grasp coordinates and direction, workspace bounds,
   and evaluated outcomes. The public Query retains opaque references.
3. **Major, fixed — infrastructure errors conflated with geometry failures.**
   Callback exceptions and malformed/missing receipts previously collapsed into
   a generic infeasible-grasp report. Failure codes and private diagnostic
   receipts now distinguish those paths; a bare available response never
   manufactures successful feasibility evidence. Worker revision rejection
   preserves the original request identity and `stale_scene_revision` cause.
4. **Major, fixed — insufficient route-level test coverage.** Initial tests
   stubbed the entire short-route qualification. A new test exercises the real
   `qualify()` method with injectable FK/IK/collision mechanisms, and the recorded
   R03 geometry regression proves pre-grasp agreement with full acquire route
   construction and rejection before IK. These are contract/mechanism tests,
   not proof of physical execution.

以上问题均已在当前实现中处理。运行能力的剩余阻塞与实现缺陷分开记录：目前没有证据证明
R03 的完整 acquire 路线通过，更不能宣称两次倒液和搅拌已完成。

## PAOS boundary review / PAOS 边界复核

- Authority: repository `AGENTS.md`, `docs/zh/03-developer-manual.md`,
  `MANIPULATION_DAG_DEVELOPER_GUIDE.md`, and
  `VISUAL_GEOMETRY_EVIDENCE_ARCHITECTURE.md`. The Hephaestus skill's named
  `docs/AGENT_WORKFLOW.md` and related files do not exist here; PAOS documents
  govern implementation. No missing-document approval gate was invented.
- Tier C-Safety: observation/frame, kinematic and collision evidence changed.
  No public Tool schema, Core AgentLoop, task lifecycle or action endpoint added.
- Generic ownership: Coordinator/AgentLoop select task semantics and opaque refs;
  Runtime owns execution and settlement. Callback injection adds no scheduler,
  automatic reobserve, retry loop, robot controller or fabricated verdict.
- Mechanism ownership: Isaac Adapter resolves observed identities privately and
  evaluates current USD/robot state through the existing sequential worker.
  Replacing the callback/backend needs no caller-domain changes.
- Freshness: observation, scene revision, camera frame, calibration, grasp set,
  process-feature set and candidate reference bind the same query/preparation.
  Existing worker scene-revision and observed-body drift checks remain active.
- Safety: simulation/no-motion first, no controller commands from the probe;
  complete acquire qualification still checks measured start state, workspace,
  IK continuity, joints, collisions and payload before execution.
- Recovery: only the selected-first qualified opaque list reaches Action
  alternatives. The existing subtask executor regression ensures excluded raw
  candidates cannot reappear. Failed/unknown preparation never establishes
  successful grasping, possession, pouring or mixing.
- Evidence mode: explicit simulator truth is permitted by the user and existing
  PAOS experimental-mode documentation. It is not described as sensor-derived
  reconstructed geometry or a ReMake result.

## Validation / 验证

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  ./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py
```

- Full boundary suite: `370 passed`; no skipped asynchronous tests.
- Focused PhaseMotion/visual/worker suite: `185 passed`.
- Ruff on all ten touched implementation/test files, compileall and
  `git diff --check` passed.
- Contract evidence includes replacement callbacks, no-motion real short-route
  qualification, workspace rejection, missing/invalid/stale receipts, and
  same-qualified-set Action recovery. It does not prove Lula/PhysX or dynamics.
- Provider runtime evidence and final run receipt are recorded in
  `.task/labutopia-r03-approach-feasibility-diagnosis-20261102.md`.
- No real-hardware validation. No action video or liquid transfer claim arises
  from a no-motion qualification run.
