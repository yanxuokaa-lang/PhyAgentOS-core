# v16.7.1 Action handoff review

## Findings and disposition

- Major (resolved): the old launch instruction prohibited all Actions and the
  host default left execution disabled, while shared deployment guidance told
  both modes to execute ready nodes. R03 candidate qualification therefore did
  not imply advancement into its Action. Split mode-specific guidance; preserve
  the default and explicitly authorize the new simulator run.
- Major (resolved in reporting): seven independent qualified combinations and
  30 successful short-approach variant attempts are not complete-route or motion
  proof. Diagnose using final Coordinator outcomes, not the early response.
- Major (resolved for bounded selection/reporting): fresh r1 reaches Action,
  then its first preparation exhausts the 900-second worker request budget.
  All-variant min-travel optimization and missing progress receipts prevent
  distinguishing no complete route from optimization after success. Add explicit
  Adapter-private first-feasible mode; preserve min-travel as the default and
  all route checks. Per-route/stage diagnostics and native r2 now establish full
  acquire-route feasibility; measured contact failure remains a separate blocker.
- No Core/Tool schema/Provider contract changes. Existing same-set opaque refs,
  route preparation, collision margins and lifecycle owners remain intact.

## Ownership and safety

Tier C-Safety. Entry guidance and launch mode belong to the Isaac deployment.
AgentLoop selects semantic operations and opaque references; Coordinator owns
task lifecycle, cancellation, recovery and settlement. Runtime owns preparation,
motion, measured results and phase recordings. No second scheduler was added.
Grasp/geometry mechanism substitution continues through existing Provider ports.
The host contains no grasp coordinates, USD paths, joint values or fixed task
parameters. Only the new launch instruction supplies R03/R04 and process values.

Frames/calibration and candidate sets remain capture-bound. Every new run
re-observes; historical candidate IDs are diagnostic only. The full-path and
possession checks remain required before the relevant motion. A negative/unknown
result remains a failure, and raw excluded candidates cannot recover it.

## Validation

- 153 targeted host/phase/executor tests passed.
- 418 adapter and executor regression tests passed.
- New CLI tests prove default false / explicit --execute true and unchanged
  instruction forwarding; mode guidance tests distinguish read-only stop from
  qualified-predecessor Action selection and complete-route checks.
- Existing tests exercise phase recording on failure without extra simulation
  steps, qualified-only candidate recovery and rejection before motion.
- Ruff and git diff --check passed before native launch.
- Expanded route-policy regressions: 424 passed before rerun; an additional
  all-rejected first-feasible case and real qualification progress assertions
  pass in the 118-test phase suite. Invalid policies reject, default min-travel
  and explicit first-feasible select different fully checked routes, a collision
  does not emit a successful stage, and recording does not alter route sampling.
- Native r1: Action accepted, preparation timeout, no world change, no video.
- Native r2: complete acquire route passes in 8.182 s; actual motion produces
  3153 decoded frames (52.55 s). Transport/approach execute, then the open-gripper
  insertion pushes the object 26.785 mm and closure raises drift to 33.487 mm.
  The pre-lift grip check correctly rejects 34.220 mm / 0.197260 rad attachment
  error against 8 mm / 0.08 rad limits. Possession is uncertain, Action unknown,
  subsequent pouring/R04/stirring blocked. No success is fabricated.
- The Agent chose candidate 367 in r2 versus 420 in r1. These timings do not
  isolate policy speedup; tests independently establish first-feasible behavior.
- Final encompassing regression: 425 passed. Handoff/search change acceptance
  is supported; end-to-end manipulation acceptance remains blocked by dynamic
  contact mismatch, which needs Adapter contact qualification/repreparation.

Command:

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
./.venv/bin/python -m pytest -q examples/forge-adapters/isaacsim_lab/tests \
examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py
```

Run outputs: `out/lab-fullchain-truth-20261102-qualified-execute-r{1,2}/`.
Diagnosis: `.task/labutopia-action-handoff-20261102.md`.
