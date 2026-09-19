# v10.9.4 Runtime binding and recovery diagnostics review

## 需求与架构复核 / Requirements and architecture

The user requested a PAOS philosophy, architecture, extension, developer-guide
and AgentLoop review, repair, and the established seven-dimension acceptance.
Reviewed references: `docs/zh/01-framework-introduction.md`,
`docs/zh/03-developer-manual.md`, `docs/adr/0001-runtime-ownership-and-skill-use.md`,
`MANIPULATION_DAG_DEVELOPER_GUIDE.md`, `VISUAL_GEOMETRY_EVIDENCE_ARCHITECTURE.md`,
and `AGENT_TOOL_INPUT_SELECTION_DESIGN.md`.

修复保持 Agent 选择与恢复决策、Coordinator 持久化、Runtime 物理状态所有权；视觉几何不使用仿真真值补全。
Agent owns selection/recovery decisions; Coordinator persists facts; Runtime owns
physical state. Simulator poses are not substituted for visual geometry.

## Findings and disposition

- **Blocker fixed:** Runtime compared an observation-derived envelope pose with
  an actor's object-frame pose. It now selects the captured execution pose from
  existing `scene_facts.objects` by execution entity and actor identity. Grounding
  explicitly retains that snapshot. Visual route geometry and the original
  `atol=1e-6, rtol=0` remain unchanged. Missing, malformed, nonfinite or ambiguous
  snapshots reject; aliases publish only after every comparison passes.
- **Major fixed:** the process client collapsed worker failures to a string and
  the preparation endpoint collapsed them again. A worker rejection retains its
  code; the adapter maps known binding failures to provider-declared public
  diagnostics through the existing Query `error` object. Unrecognized exceptions
  remain sanitized. No adapter identifiers are introduced into Core decisions.
- **Major fixed:** both live and persisted settlement ignored nested Query
  errors after successful HTTP transport. Both now preserve `error.code` while
  retaining existing transport/error precedence and unsuccessful settlement.
- **Major fixed:** recovery lacked the failed execution response and validation
  details disappeared. The prompt now includes only failed-node diagnostic
  identity/status/error/evidence, without candidate geometry. Recovery and replan
  failure reasons retain bounded, redacted details in existing task history.
  Agent still chooses stop/replay/replan; no automatic Tool retry is added.
- **Deployment addressed:** the running self-contained Node would retain the old
  guard. A new Node 0.2.0 and Skill 2.3.2 are built and isolated-install verified.
  Existing release archive checks are reused. The live instance is not replaced.

No remaining Blocker/Major was identified in this source and no-motion review.
This is not a claim that real-model recovery or physical task execution passed.

## 既有七维验收 / Established seven dimensions

| Dimension | Result and evidence |
| --- | --- |
| Architecture integration | PASS: adapter owns frame semantics; Core handles generic errors; existing Gateway, Coordinator and AgentLoop paths remain authoritative. |
| Recovery and idempotency | PASS in tests: live/persisted error parity, failed revision/node scoping, replan validation detail, no automatic re-execution, atomic alias publication. |
| Robotics safety | PASS, no-motion: unchanged actor accepted despite visual-frame mismatch; translation/rotation, absent/duplicate/invalid/nonfinite snapshots rejected; existing tolerance preserved. |
| Context and performance | Functional PASS: only diagnostic fields added to recovery, no candidate geometry. Real 24-candidate preparation latency remains unmeasured. |
| Configuration and reproducibility | PASS: versioned Node/Skill, existing lock updated, deterministic Node rebuild and isolated transactional installation verified. Live deployment pending. |
| Maintainability and observability | PASS: explicit public error boundary, preserved raw adapter metrics, bounded/redacted recovery diagnostics, developer docs and regressions. |
| AgentLoop autonomy | Interface PASS: model receives failure cause and chooses recovery; no Core RoboTwin branch. Real-model recovery choice remains unmeasured. |

## Validation

- Core: **504 passed**, 25.60 s.
- Skill: **337 passed**, 7.18 s.
- Adapter: **515 passed, 1 skipped**, 5.35 s. The skipped perception-worker
  test module requires Pillow, absent from the PAOS interpreter.
- Initial focused run: 179 passed after correcting two test fixture assumptions;
  subsequent full suites include additional malformed/multi-entity checks.
- Redacted recovery-error persistence: 1 targeted test passed after review.
- Changed-file Ruff, compileall and `git diff --check`: PASS.
- Saved binding replay from `task_483b2de75c984218`, artifact
  `entity-bindings/3111be4d6be145f89a1a86b1f7f48fec.json`: old comparison rejects
  all three recorded actor poses; new guard accepts all three. A 2 mm change
  to the third actor is rejected without replacing the previous alias mapping.
  Actors were in-memory doubles populated from saved poses, not live simulator
  reads. Gateway calls and simulator steps: **0**.
- Release directory: `/tmp/paos-v10.9.4-release-CvcDv7`.
  Node archive: `robotwin20_persistent_host-0.2.0-linux-x86_64.tar.gz`, 331744 bytes.
  Skill archive: `skills/pick-place-workflow-2.3.2.tar.gz`.
  Existing Node lock SHA-256:
  `3ab1cd7e0079f9b1459248bd7a3ed94ec414288adfb6b6924af5595f88611080`.
  A second build was byte-identical; SkillInstaller and NodeInstaller completed
  in `isolated/`, and Node load/satisfies checks passed without starting Runtime.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src \
  python -m pytest -q -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
  python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
```

实际运行仍需部署新 Node 并建立新绑定，再测候选过滤、物理执行和跨 Action 完整录像。
No running task was cancelled/resumed and no Runtime was restarted. Deployment
and a fresh run are needed to validate real filtering, motion and the complete
multi-Action video; source/fixture tests do not establish those outcomes.
