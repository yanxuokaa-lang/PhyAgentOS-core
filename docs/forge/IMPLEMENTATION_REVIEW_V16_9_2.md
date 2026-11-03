# Implementation Review: v16.9.2

## Findings

1. **Fixed — transient tolerance originally falsified `grasp_valid`.** The first
   draft changed the measured sample to `grasp_valid=true`. The final code leaves
   both `contact_load_valid` and `grasp_valid` false and records a separate
   `contact_transient_grace_used` execution decision.
2. **Fixed — contact classification could recapture a different sensor frame.**
   `record()` captures the current interval once; unilateral-load classification
   now consumes that same window instead of calling the sensor again.
3. **Fixed — tolerance scope was broader than the diagnosed case.** It is now
   limited to `operation=acquire`, the first `lift` point immediately following
   a successfully completed `close`, one interval only, with fresh bilateral
   manifolds, one positive load and unchanged attachment limits.
4. **Major, unresolved — no new live acquisition proof.** The implementation is
   regression-validated only. The previous scene has unknown possession and
   must be reset/reconciled before any new Action.

## Architecture and safety

- The repair stays inside Isaac Adapter sensor/execution mechanisms.
- AgentLoop, Coordinator, Skill DAG, Provider candidate sets and public Tool
  contracts are unchanged.
- No threshold, collision exception, pose correction or candidate mutation is
  introduced.
- A second unloaded interval and all missing/stale/bilateral-loss cases stop
  fail-closed with `physical_grasp_lost`.
- Contract, Provider/preparation and live execution evidence remain separately
  graded; controller regression is not presented as motion success.

## Acceptance

Accept the bounded Adapter repair after the documented regression and static
checks. Do not accept the requested two-pour/stir workflow as complete. Fresh
simulation execution is a separate step after scene reset and state
reconciliation.
