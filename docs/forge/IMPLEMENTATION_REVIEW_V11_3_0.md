# v11.3.0 Benchmark-first Oracle baseline: seven-dimension acceptance

## Scope and decision

The implementation makes benchmark goals an explicit Runtime-owned profile. The
`robotwin-blocks-ranking-oracle` profile exposes `task.goal` facts with
`goal_source=benchmark_task_definition`; the observation-owned profiles return
`benchmark_goal_disabled` and do not fall back to benchmark destinations. The
Coordinator propagates opaque `entity_ref`, `destination_ref`, and
`capability_snapshot_ref` values into preparation nodes, and the AgentLoop stops
the current node turn on deterministic plan-contract rejection instead of asking
the model to repeat the same invalid selection.

This release is accepted for source, package, installation, and read-only Oracle
baseline scope. It is **not** accepted as a completed three-block benchmark:
the live run stopped before `scene.bind`, planning, or any Action because the
scene-understanding provider returned a terminal non-retryable error.

## Seven dimensions

| Dimension | Result | Evidence and boundary |
| --- | --- | --- |
| Architecture integration | PASS | Runtime owns benchmark goals and opaque destinations; Core owns task/revision/selection; Agent chooses semantic nodes and recovery. Profiles are explicit and have no implicit fallback. Core 509 tests pass. |
| Recovery and idempotency | PASS | Missing bindings are rejected in ready projection; deterministic selection errors short-circuit one node turn; blocked nodes enter existing `awaiting_replan`; no Action retry or execution record is fabricated. Live failed tasks were cancelled with zero Action records. |
| Robotics safety | PASS for exercised scope | `task.goal`, observation, capabilities and understanding remained Queries with `motion_authorized=false`; no Gateway Action, acquire, place, simulator step, or physical motion occurred in the failed live runs. Oracle geometry is explicitly benchmark/oracle evidence, not perception truth. |
| Context and performance | PASS for source scope; live completion BLOCKED | The new binding path removes repeated opaque payload copying. Core 509 passed in 25.09 s; Skill 342 passed in 6.78 s. No claim is made for complete-task latency because no Action was admitted. |
| Configuration and reproducibility | PASS | Skill 2.6.6 and Node 0.6.6 were built in `/home/yanxu/tmp/hephaestus/oracle-v11.3.0-b66yP0`, installed without overwriting 2.6.5, and Node SHA verification passed. Model acceptance config is `gpt-5.6-sol` with `reasoningEffort=high`; runs used unique sessions/tasks and persisted SQLite records. |
| Maintainability and observability | PASS with open provider diagnosis | Tests cover positive/negative profile split, identity mapping, current-revision facts, missing bindings, and one-request short circuit. Live records preserve exact Tool errors and evidence refs. `scene.understand` currently exposes only `understanding_provider_error/provider_failure/retryable=false`; the underlying provider exception needs a separate adapter-side diagnostic run. |
| AgentLoop autonomy | PASS | The loop did not switch models, invent calibration, retry non-retryable understanding, or continue after a terminal capability/understanding failure. A read-only smoke task had to be explicitly stopped before another session could claim ownership, which is correct Coordinator lifecycle behavior. |

## Live acceptance runs

### Oracle goal and capability baseline

With Skill `pick-place-workflow 2.6.6`, Node `robotwin20_persistent_host 0.6.6`,
and profile `robotwin-blocks-ranking-oracle`:

- Direct `task.goal` returned `goal_source=benchmark_task_definition` and
  destinations `red-slot`, `green-slot`, and `blue-slot`, with
  `motion_authorized=false`.
- Task `task_caeacdf0c9574b00` used an incorrect goal calibration reference for
  `manipulation.capabilities`; the provider correctly rejected it as
  `provider_unavailable / RouteEvidenceError`. Replaying the same Runtime with
  the exact `scene.observe` calibration reference returned `available`.
- Task `task_ac9ace5e92c04b8a` used the corrected reference and reached
  `manipulation.capabilities=available`. `scene.understand` then returned
  `status=unavailable`, `code=understanding_provider_error`,
  `reason=provider_failure`, `retryable=false`. No bind, PlanGraph,
  selection, Gateway Action, or video was created.
- A second model attempt under `gpt-5.6-terra` was rejected by the upstream
  distributor with HTTP 503 `model_not_found` because no channel was available.
  After changing the explicit configuration to `gpt-5.6-sol/high`, a read-only
  smoke task (`task_85fca0ac44fc4b47`) successfully read benchmark goals. That
  smoke task was explicitly cancelled before starting a full task, preserving
  task ownership semantics.

## Validation commands and results

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests
509 passed in 25.09s

PYTHONPATH=examples/forge-skills/pick-place-workflow/src \
  python -m pytest -q -p pytest_asyncio.plugin \
  examples/forge-skills/pick-place-workflow/tests
342 passed in 6.78s
```

The dedicated SciPy-enabled adapter environment previously produced
`632 passed, 1 skipped`; the PAOS interpreter produces `623 passed, 1 skipped,
9 failed` for the existing SciPy-dependent observed-collision tests. The nine
failures are environment dependency failures (`ModuleNotFoundError: scipy`),
not regressions in the benchmark-goal or AgentLoop changes. Ruff and
`git diff --check` pass.

## Remaining blocker and next step

The next run should keep `gpt-5.6-sol/high`, capture the underlying
scene-understanding worker exception (without changing its retry policy), and
rerun from a fresh Oracle task only after that provider diagnosis. A complete
acceptance still requires three or more terminal Actions, a PAOS verifier
verdict, an independent RoboTwin `benchmark_result`, and a cumulative task
video manifest containing head and observer videos in Action order. None of
those artifacts exists in this release, so the benchmark is not reported as
successful.
