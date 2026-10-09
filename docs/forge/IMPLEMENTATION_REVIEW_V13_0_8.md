# Implementation Review v13.0.8 / 七维实现审查

## Findings / 问题

No Blocker or Major finding remains in the unknown-Action recovery change.
The Runtime receipt facts are now carried into settlement, and the AgentLoop
still refuses automatic Action retry. Unknown physical state remains
unresolved until Runtime evidence or an operator reconciles it.

Two Adapter readiness tests fail in this checkout but are outside the changed
recovery path:

- `test_no_motion_gate_rejects_provider_that_reports_world_change` expected
  `motion_started_in_no_motion_mode`; the Adapter rejects earlier with
  `missing_new_scene_revision`.
- `test_place_action_reuses_the_same_reviewed_gate_and_acquire_identity` has
  its fake placement response rejected as `object placement result failed
  contract validation`.

These are retained as known test-suite failures, not hidden or attributed to
the recovery patch. The modified files do not change the Adapter readiness
gate or those fixtures.

## Seven Dimensions / 七个维度

1. **Architecture:** recovery metadata is defined at the provider-neutral
   planning contract boundary, projected from persisted execution receipts,
   and consumed by the existing AgentLoop/Coordinator recovery lifecycle.
   No Adapter-specific status branch was added.
2. **Correctness:** `world_change_started`, `outcome_known`,
   `retryable_in_revision`, `requires_replan`, and `recommended_action` remain
   distinct. Only the conjunction of unknown outcome, started world change,
   and Runtime-requested replanning can leave reconciliation blocking.
3. **Recovery and idempotency:** the failed Action's invocation is not
   repeated. Recovery appends a revision through the existing Coordinator
   lifecycle and remains subject to its replan budget.
4. **Robotics safety:** unknown possession is never converted to held/empty or
   success. The recovery revision must introduce a Query, and every new Action
   must depend on it. Runtime/Gateway admission remains authoritative.
5. **Extensibility and compatibility:** semantics are derived from bound
   Runtime ToolSpecs, not a task, object, sensor, color, benchmark, or robot
   identity. New receipt fields are optional, so historical records preserve
   reconciliation-only behavior.
6. **Observability and maintainability:** settlement and persisted recovery
   decisions retain the Runtime recommendation; invalid proposals surface as
   a replan reason. Regression tests cover both allowed and denied branches.
7. **AgentLoop autonomy and convergence:** explicit Runtime recovery intent
   reaches the existing proposer deterministically. Missing facts remain
   fail-closed; replan count and revision ownership remain Coordinator-owned.

## Validation / 验证

Focused no-motion command:

```bash
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p pytest_asyncio.plugin \
  examples/forge-skills/pick-place-workflow/tests/test_unknown_action_recovery.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_manipulation.py \
  examples/forge-adapters/robotwin20/tests/test_persistent_host.py \
  examples/forge-adapters/robotwin20/tests/test_grounding.py \
  examples/forge-skills/pick-place-workflow/tests/test_persistent_runtime.py \
  examples/forge-skills/pick-place-workflow/tests/test_object_acquire.py \
  examples/forge-skills/pick-place-workflow/tests/test_object_place.py -q
```

Result: `178 passed`. Ruff, compileall, and `git diff --check` pass. The two
Adapter readiness failures above were run separately and remain open. No live
Runtime, Gateway, simulator, or physical Action was invoked.
