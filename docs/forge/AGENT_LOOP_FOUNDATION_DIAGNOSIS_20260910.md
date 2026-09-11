# Agent Loop 基础诊断与修复 / Foundation Diagnosis and Repair

日期 / Date: 2026-09-10. Scope: natural-language multi-object Agent Loop; evolution disabled.

## 1. 诊断 / Diagnosis

当前未提交的 `persistent_agent_runner.py` 不是完整 Agent Loop：

- 任务 YAML 预填对象、benchmark identity 和目标区域，替代了本应由 Agent 基于用户目标与现场证据产生的任务理解。
- `run_node_turn` 丢弃 prompt，按 `relocate_N` 和节点后缀执行固定逻辑；没有实际节点推理。
- category 字符串匹配后改写 geometry entity identity，不能证明感知对象与执行对象一致。
- 自定义 Verifier 用 benchmark pose 作用户级裁判；动作总数检查拒绝合法恢复，且姿态误差公式错误。
- 没有接入实际 recovery decision / replan proposer，不能证明基于事实的恢复能力。

The uncommitted runner substitutes task answers and node-name dispatch for reasoning, rewrites grounding identities, introduces a benchmark-owned final verdict, and has no model recovery path. Its custom verifier also miscounts recovered attempts and computes relative orientation incorrectly. Remove the implementation rather than retaining its architecture behind patches.

## 2. 所有权 / Ownership

| Owner | Responsibility |
| --- | --- |
| Deployment | Interpreter/model/Runtime/sensors/capabilities/limits; no task answers |
| Agent + Skill | Interpret the user request, select evidence-backed entities and destinations, propose semantic dependencies and success conditions |
| Perception + Adapter | Sensor evidence, measured geometry, transforms and grounded execution references; never rename entities to match benchmark answers |
| AgentTask / PlanningLoop | One task, append-only revisions, node settlement, bounded recovery and persisted facts |
| Forge / persistent Runtime | The only physical execution path, invocation/attempt/status and current world revision |
| ForgeTaskVerifier | Evaluate the original goal against all relevant records and final current-scene evidence |
| Experience / evolution | Consume settled outcomes later; never execute, authorize motion or rewrite historical results |

依据 / Sources: `docs/zh/01-framework-introduction.md` sections 1-6; `docs/zh/03-developer-manual.md` sections 12-13; `PLANNING_MODULE_DESIGN.md` generic attribute-sorting scenario; `docs/zh/06-consequence-driven-skill-evolution-design.md` sections 7 and 15.5.

## 3. 修复路线 / Repair Sequence

1. Delete the three uncommitted dedicated runner/profile/script files and their semantic-ID rewrite support. Keep the persistent host and existing safety authorities. Fixed-input fixtures remain fixtures, not natural-language acceptance.
2. Use the existing `activate_skill -> forge_task_create -> task-bound discovery -> forge_task_materialize_plan` path. Let the model submit semantic nodes; code supplies existing graph identity/digest metadata rather than requiring the model to fabricate it. This reuses existing integrity fields, not a new gate.
3. Supply each node turn with the original user goal, verification criteria and the task-bound Skill instructions. A later changed Skill must not silently alter an in-flight task. Persist the actually activated instructions with the task, using the existing task store.
4. Connect model recovery through the existing PlanningLoop callbacks; preserve the semantics that replay reprocesses settled facts without repeating a physical Action, while a new physical attempt requires replan and current-scene admission.
5. Preserve Query failure and unknown outcomes as node failures/uncertainty. Final success remains the existing Verifier's responsibility. Do not retain the deleted benchmark verifier or replace its math in place.
6. Update Skill guidance and tests. Run software acceptance before any authorized live perception/simulation acceptance.

## 4. 六维验收标准 / Acceptance Criteria

| Dimension | Required evidence |
| --- | --- |
| Architecture | Model-facing task and node paths use existing AgentLoop/Coordinator; no replacement execution runner |
| Failure/recovery | Query unavailable/unknown, model recovery rejection, stop/replay/replan, no unknown Action resubmission |
| Authority/safety | No sensor-to-actuator shortcut, unchanged readiness/approval checks, no motion during tests |
| Configuration/reproducibility | Different goals/entities use the same deployment; answers exist only in task output or test fixtures |
| Maintainability | Remove divergent implementation; share graph construction and existing lifecycle, no second store/scheduler/verifier |
| Observability | Persist original goal, Skill instructions, graph, decision context, records and recovery lineage |

## 5. 真实场景后续验收 / Live Acceptance

After software verification, use a ready managed Runtime and the normal PAOS Agent entry. Observe the same persistent world, ground requested objects from sensors, finish each Action before progression, refresh before the next object, and obtain a final current-scene verdict. The development host is not automatically a published manifest-v2 Node artifact. Do not fabricate registration or treat contract tests as live model/robot proof.

Evolution remains off until this loop is demonstrated. Later patches may change reusable observation/decision/recovery guidance, not deployment answers, immutable facts or safety policy. A promoted Skill must demonstrably affect a subsequent task's decisions and measured outcome.

## 6. 实施与验证 / Implementation and Validation

Completed in the working tree:

- Removed the uncommitted `persistent_agent_runner.py`, task-answer YAML and dedicated launcher. No replacement execution protocol was added.
- Added `compile_task_plan()` and the `forge_task_materialize_plan` `nodes` path. The model selects semantic nodes; PAOS derives revision, graph and policy metadata and validates capabilities against the frozen Skill binding.
- Persisted the exact primary Skill instructions on `AgentTaskRecord`; node turns include the original goal, verification contract and those instructions. The field is immutable after task creation.
- Added a read-only `AgentRecoveryDecisions` planner adapter. It asks for `stop`, `replay` or `replan`, records the decision, and delegates all state changes to `PlanningLoop`/`AgentTaskCoordinator`. Invalid or unavailable model output falls back to `stop`.
- Updated the provider-neutral pick/place Skill with dynamic grounding, discovery, materialization and recovery guidance.

Validation evidence:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p pytest_asyncio.plugin -q`: **313 passed** (one existing Pydantic warning in a fixture).
- Focused foundation/planning tests: **49 passed**.
- `ruff check` on all changed implementation and foundation-test files: passed. The repository-wide command still reports a pre-existing import-order issue in `PhyAgentOS/agent/experience/__init__.py`, which is outside this repair.
- `python -m compileall -q PhyAgentOS tests`: passed.
- `git diff --check`: passed.

The tests are no-motion contract tests. They do not claim live model perception, RoboTwin execution, hardware movement, or formal manifest publication. Evolution remains disabled.

## 7. Persistent Runtime Preflight

On 2026-09-11 the real `RoboTwinPersistentEngine` worker was started through `check_persistent_runtime.py` with the repository adapter, RoboTwin runtime profile `franka-blocks-ranking.yaml`, and the RoboTwin20 Python environment. Startup completed a read-only snapshot successfully:

```text
status=passed
scene_revision=e2f84bbf24f84792b3af3cbe637ab1d6-1
motion_executed=false
```

This proves the persistent worker can create the configured world and expose an initial scene fact. It does not prove perception, grasp generation, route preparation, Action admission, placement, final verification, or model-driven task understanding. `paos skill list` currently reports no installed Skill Runtime, and the source-tree deployment is not registered as a formal manifest-v2 profile because the self-contained `robotwin20_persistent_host` Node artifact is not published. The next executable gate is therefore artifact-backed Runtime installation and `/tools` readiness, followed by the standard PAOS Agent entry.

## 8. Interrupted Discovery-to-Plan Turn (2026-09-11)

Later evidence supersedes the preflight-only installation status above: task
`task_7bd79d84408a49cd` completed three Queries with Skill 0.10.7. Understanding
returned available with four entities, four envelopes and twelve derived artifacts.
The CLI reached its 300-second turn limit without a persisted PlanGraph.
This proves no successful materialization, not that the model repeatedly planned
or that a materialization call was never attempted. Per-call timing was unavailable.

The coordinator now returns a separate `paos_record` receipt with its persisted
record/revision/task identity and evidence refs; Gateway data and stored response
remain unchanged. The Agent can submit selected nodes without fetching the whole
task merely to obtain those references. No fixed Query sequence is required.

Interrupted ordinary Agent turns retain completed messages through SessionManager.
Missing local Tool results receive explicit interruption notices, not remote
execution facts. Recovery must reconcile task/Gateway state before retrying.
Model and Tool timing/cancellation use existing logging, available with `paos agent --logs`.

Validation: 120 software regressions passed, including direct materialization and
same-task recovery after model/Tool interruption and actual turn timeout. The
model is scripted in tests. Next live validation must use the same task, enable
logs, submit a graph through the standard Agent and inspect persisted revisions;
do not treat this patch as RGB execution or final Verifier success.

## 9. Destination Discovery and Shell Cancellation

The next live turn exhausted its budget searching local files for destination refs.
The current Agent now receives a compact persisted active-task snapshot before
model inference, instead of relying solely on historical task IDs. This grants
no takeover, migration, cancellation or motion authority.
Shell commands use a dedicated POSIX process group; timeout/cancellation kills
that group and drains pipes before returning or propagating cancellation.
Deliberately detached descendants and Windows process trees are not covered by
the POSIX cleanup tests.

Destination grounding remains an implementation gap, not a prompt-only fix:
`persistent_route_builder.py` checks the requested destination against the selected
object's `target_ref` in adapter scene facts. Exposing benchmark target answers
would not demonstrate task understanding. A subsequent adapter/Tool change must
accept Agent-selected relational goals and resolve them from current observation
and calibration into scene-bound destination geometry, then retain existing
preparation, collision and Action admission. No Runtime-private file search should
be used to replace that public interface. This change does not implement that
interface and does not make arbitrary RGB sorting executable.

## 10. Observed Entity Binding and Row Layout (Development)

The source persistent deployment now registers `manipulation.layout`, a read-only
Query accepting `observation_ref`, `scene_revision`, `calibration_ref`,
`ordered_entities`, `axis` (`world+x` or `world+y`) and `max_age_ms` (1..60000).
Observation and understanding results are captured from successful public
endpoints, not accepted as caller-supplied geometry. Capture time is taken from
the observation endpoint; request freshness does not replace it.

The adapter inverts the calibrated world-to-camera CV rigid transform, compares
observed spatial envelopes with current execution-object oriented boxes and
requires a single overlapping box containing the observed center. Multiple
overlaps, missing geometry and many-to-one correspondence fail closed. Labels
never select actor identity. This is geometric correspondence evidence, not a
proof of model semantic accuracy. Partial views/noisy depth can be rejected.

Row horizontal slots and transverse center come from transformed observations.
Object orientation and support height remain execution-object geometric facts;
benchmark target poses are overwritten and do not choose requested positions.
Insufficient span for non-overlapping targets is rejected. The Query does not
certify support, workspace or route feasibility, and does not select temporary
destinations or a swap sequence. Those remain separate planning/preparation
obligations. Unsupported rearrangements must stop, not bypass preparation.

The output carries a layout artifact, explicit observed/execution identities,
scene-bound destination references and world-frame target transforms. An
adapter-private artifact also records actor identities and route scene facts.
Preparation accepts only a matching, unexpired layout, binds the observed IDs
inside the idle persistent worker and reuses existing route generation,
readiness, approval, acquisition and placement paths. Rebinding while holding
or moving is rejected. Original perception IDs and execution IDs remain distinct.
An updated scene requires new observation, understanding and layout resolution.

Software evidence: 111 tests passed, including public HTTP Query transport,
calibration, stale/expired evidence, duplicate entities, ambiguous correspondence,
worker alias binding, held-object rejection, deployment and planning regressions.
No live perception, planner, Action, simulation stepping or hardware IO was run.

Release status: source integration only. Installed Skill 0.10.7 and its locked
Node do not gain the new Tool; no manifest or installed runtime was changed.
Before standard Agent use, build a new Node, declare the new required Tool in a
versioned Skill manifest (including compatible test profiles), validate isolated
installation, and resolve the existing active task explicitly before switching
its Runtime. Do not use an unbound diagnostic call as a task-binding workaround.
Live identity accuracy, placement feasibility and final RGB verification remain
unaccepted. Evolution remains disabled.
