# v16.3.0 R12 recovery implementation review

## Outcome

`aligned` for the bounded recovery slice. The change does not bypass Isaac
collision checks and does not authorize motion. It converts one explicit,
known, zero-motion preparation rejection into the existing Coordinator-owned
Agent replan path.

## Findings resolved

- **Major:** R12 collapsed a known `no_admissible_grasp` route-collision result
  into `requires_replan=false`, so Recovery stopped even though the same
  capture contained alternative opaque candidates. Subtask aggregation now
  admits replan only with explicit no-motion and empty-possession facts.
- **Major:** Recovery context contained only the failed Action record. It now
  projects same-revision, same-capture alternative refs from the successful
  `manipulation.grasp_task_affordances` Query and excludes the failed ref.
- **Major:** When readiness evaluated and rejected more than one candidate,
  excluding only the Agent's selected reference could re-offer a provider-
  rejected candidate. The existing preparation diagnostic now carries optional
  opaque `rejected_candidate_refs`; Recovery excludes every evaluated
  rejection without exposing pose or provider geometry.
- **Blocker avoided:** no fallback pose, USD path, provider geometry, or
  automatic candidate retry was added. Missing/stale provenance yields stop.

## Ownership and evidence

Isaac Adapter owns route diagnostics and no-motion facts. The Subtask executor
owns finite internal-call aggregation. AgentRecoveryDecisions owns the
evidence-bounded model proposal. Coordinator/PlanRevision remains the sole
owner of revisions, replan budget, Tool admission, cancellation, and
settlement. The additive Tool metadata remains provider-neutral. Query -> candidate selection -> no-motion Preparation -> Action
ordering is unchanged; a replacement graph must repeat the governed read-only
selection/Preparation path before any Action.

## Validation

```text
PYTHONPATH=examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src:. \
  .venv/bin/python -m pytest -q \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py \
  tests/test_recovery_decisions.py \
  examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py \
  examples/forge-skills/pick-place-workflow/tests/test_manipulation_prepare.py
124 passed

./.venv/bin/ruff check \
  examples/forge-skills/pick-place-workflow/src/pick_place_workflow/subtask_executor.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py \
  examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/paos_client.py \
  examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py \
  PhyAgentOS/forge/capability_runtime/manipulation_prepare.py \
  PhyAgentOS/agent/recovery_decisions.py \
  tests/test_recovery_decisions.py
All checks passed!

./.venv/bin/python -m compileall -q \
  examples/forge-skills/pick-place-workflow/src/pick_place_workflow \
  examples/forge-adapters/isaacsim_lab/src/isaacsim_lab \
  PhyAgentOS/agent PhyAgentOS/forge/capability_runtime
Completed successfully.

git diff --check
Completed successfully.
```

The system Python invocation was not used as acceptance evidence because its
environment lacks the repository package paths and `loguru`. No Isaac runtime,
physical Action, pouring, stirring, or reset was started in this change.

## Residual risk

The next no-motion runtime must show that the Agent's replacement graph binds
one supplied alternative candidate and that Preparation evaluates it. A
successful replan still does not prove route feasibility, liquid transfer,
stirring, or task-level verification; those remain downstream evidence gates.
