# v11.3.6 Consumer Projection and Oracle Baseline Acceptance

## Scope and conclusion

This review covers the recent planning-loop changes: consumer-owned argument
projection, persisted runtime-binding propagation, the explicit RoboTwin Oracle
profile, provider diagnostics, and the isolated Skill/Node release. The source,
tests, bundle, and installation are accepted. The complete physical-task
acceptance is **not complete** because the fresh Oracle run stopped during
`scene.understand` before plan materialization and before any Action.

The distinction is intentional: a passing projection test proves that PAOS can
assemble a consumer request from authorized evidence; it does not prove that a
provider can understand a live scene, that a route exists, or that the
benchmark task succeeds.

## Implemented behavior

- `ArgumentProjectionPlan` is declared by the consumer ToolSpec. Core executes
  only the generic identity join, source collection, field allowlist, and
  output collection operations.
- `grasp.propose` declares `entity_geometry_target_v1`. It joins one selected
  `entity_ref` across `entities`, `spatial_envelopes`, and optional
  `derived_artifacts`, then removes producer-only fields before normal consumer
  schema validation.
- `ForgePlanSelectTool` uses the public dispatch projection API. Projection
  failures are persisted as `consumer_projection_invalid` before Gateway/Action
  admission and require the existing replan path; the Agent is not asked to
  guess another array path in the same selection.
- Plan materialization propagates unambiguous persisted `destination_ref` and
  `capability_snapshot_ref` values to preparation/place consumers. Ambiguous or
  stale values remain absent and are reported as unbindable.
- The benchmark-first profile uses explicit Runtime-owned `task.goal` facts
  (`goal_source=benchmark_task_definition`). The observation-owned profile does
  not fall back to benchmark destinations.
- Provider failures expose bounded `provider_route` and
  `provider_error_class` fields and persist a separate diagnostic JSONL record;
  credentials, stacks, and raw provider responses are not exposed.

## Seven-dimension acceptance

| Dimension | Result | Evidence and boundary |
| --- | --- | --- |
| Architecture integration | PASS | ToolSpec owns projection semantics; Core remains provider-neutral. Oracle and observation-owned profiles are explicit and isolated. Existing Coordinator, Gateway, Action, Verifier, and video interfaces are reused. |
| Recovery and idempotency | PASS | Missing, duplicate, and incomplete projection facts fail closed before Gateway execution. Rejection receipts use the existing Coordinator lifecycle. No automatic Tool retry or second task state machine was added. |
| Robotics safety | PASS for the exercised scope | Oracle run and all projection tests report `motion_authorized=false`; no Gateway Action or drive command occurred. Runtime remains the owner of physical identity, safety admission, and motion authorization. A live manipulation safety claim is not made. |
| Context and performance | PASS for bounded control-plane behavior; BLOCKED for live E2E | Node prompts receive source summaries and explicit browsing/projection paths rather than repeated full geometry payloads. Core: 513 passed; Skill: 342 passed; Adapter: 634 passed, 1 skipped. The fresh Oracle run still failed at provider transport/timeout during scene understanding. |
| Configuration and reproducibility | PASS | Skill `2.6.10` and Node `0.6.9` were built and installed in isolation. Node archive: `/home/yanxu/tmp/hephaestus/v11.3.6-build-LyErWX/robotwin20_persistent_host-0.6.9-linux-x86_64.tar.gz`; size `375543` bytes. The verified digest is recorded below. |
| Maintainability and observability | PASS with provider blocker | Projection logic is typed and declared in ToolSpecs. Negative regressions cover missing source, duplicate identity, duplicate envelope, and missing required fields. Diagnostics are bounded and persisted at `/home/yanxu/robotwin20-runtime/artifacts/paos-oracle-v11.2.1-20260921T031500/scene-understanding-diagnostics.jsonl`. |
| AgentLoop autonomy | PASS for the exercised interface; BLOCKED for E2E | The Agent activated the Skill, used explicit `task.goal`, recovered one invalid observation request from persisted evidence, and stopped on a non-retryable provider failure. No fake continuation, guessed geometry, or Action authorization occurred. |

### Reproducibility identifiers

- Verified Node SHA-256: `c24f2196ee9469b95901145368ff4709ba5424b1002836391cbb0e4b57c9a63d`.
- Skill archive: `/home/yanxu/tmp/hephaestus/v11.3.6-build-LyErWX/skills/pick-place-workflow-2.6.10.tar.gz`.
- Oracle task: `task_0fe7fc1ce9b543c8`, revision `revision_ea04517944754a8f`, binding `binding_20b96cb9074d3a67f2a5e933`, runtime `runtime_496f17eedc834f40`.
- Oracle scene revision: `10770467cfd84f4499b5b305fad21e35-1`.
- Provider diagnostic: `provider_error_class=transport+timeout`, `route=none`, `retryable=false`.

## Live Oracle boundary

The Oracle run successfully reached Skill activation, task creation, benchmark
goal retrieval, scene observation, and capability discovery. The second
`scene.understand` request returned `status=unavailable` with the bounded
transport/timeout diagnostic. Consequently there is no `scene.bind`, no
PlanGraph materialization, no `grasp.propose`, no `manipulation.prepare`, no
`object.acquire`, no `object.place`, no Action record, no PAOS verifier verdict,
no independent RoboTwin `benchmark_result`, and no cumulative task video.

The task was cancelled through the Coordinator after the failure; the SQLite
task record reports `execution_records=0`. The session log is retained for
diagnosis at:

`/home/yanxu/.PhyAgentOS/workspace/sessions/cli_oracle-v11-3-6-20260922-r2.jsonl`

This is a provider/deployment blocker, not evidence that the projection design
or the robot route passed. Full acceptance requires a fresh Oracle run that
produces Action records, a PAOS verifier verdict, an independent RoboTwin
benchmark result, and a cumulative video manifest.

## Follow-up review v11.3.7

The review found and fixed one provider-diagnostic ownership defect. The
fallback adapter previously stored `timeout+transport` in its diagnostic sink,
but its raised exception did not carry that bounded classification. The PAOS
endpoint therefore could classify the same failure as generic
`provider_failure`, which could lead AgentLoop recovery to choose the wrong
branch. `SceneUnderstandingFallbackError` now carries `provider_error_class`
and `retryable`; the public endpoint uses those fields without exposing the
exception text. Focused coverage is 18 passed and the full suites are now Core
`517 passed`, Skill `342 passed`, Adapter `635 passed, 1 skipped`.

This fixes failure ownership; it does not make the upstream model endpoint
available and does not add automatic retry.

## Remaining incomplete work

1. The live Oracle provider still needs a fresh successful
   `scene.understand` run. The current artifact has `route=none` and
   `provider_error_class=transport+timeout`.
2. Full acceptance still needs real PAOS Action records, verifier verdict,
   independent RoboTwin benchmark result, and cumulative two-view video.
3. The adapter is intentionally specialized to `blocks_ranking_rgb`. The
   fixed `_ENTITIES`/target-pose worker is not a 50-task implementation. The
   other RoboTwin task families need separate Runtime task adapters and atomic
   Tool capabilities, as defined in the Oracle baseline design; treating them
   as pick/place would violate the ownership boundary.
4. Observed-profile end-to-end execution remains unverified after the Oracle
   baseline; only its source/contracts and no-motion regressions are accepted.

## Validation commands

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q \
  -p pytest_asyncio.plugin tests

PYTHONPATH=examples/forge-skills/pick-place-workflow/src \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q \
  -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests

PYTHONPATH=examples/forge-skills/pick-place-workflow/src:\
examples/forge-adapters/robotwin20/src:\
examples/forge-adapters/robotwin20/runtime:\
examples/forge-adapters/robotwin20/scripts \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q \
  -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
```

Observed results after v11.3.7: `517 passed`, `342 passed`, and
`635 passed, 1 skipped`.
`ruff check`, `compileall`, and `git diff --check` are also required release
checks; no live motion is implied by any of them.
