# AgentLoop Diagnosis: Continuation and Recovery Convergence

## Scope

This record captures the second repeated failure mode: a completed read-only
segment was treated as if it required a post-action observation chain, and a
model-turn interruption could leave the Coordinator and LongHorizon controller
with different states.

## Evidence

- `grasp.propose` is a query-only node. Its successful terminal result did not
  start a world change and did not create an invocation.
- The LongHorizon runner entered a continuation turn after the query, but the
  continuation produced no revision. The runner reported
  `segment_continuation_incomplete:no_state_transition` and the task could enter
  `awaiting_replan` without a persisted decision explaining whether to continue,
  replan, finalize, stop, or wait.
- The same prompt path could describe a refresh as post-placement evidence even
  though no `object.place` terminal result existed.
- A pending Coordinator selection could be present after a model turn ended;
  recovery still depended on the model rediscovering and selecting it again.

## Root Cause

Continuation was inferred from control-flow side effects (whether a new revision
appeared) rather than from an explicit Agent decision and Coordinator facts. The
runner used “no state transition” as a generic failure, while pending selections
and the latest settled node were not a first-class recovery checkpoint.

## Required Invariants

1. A pending selection for the active revision is consumed before any new
   discovery or selection and is consumed at most once.
2. A query-only terminal result lets the Agent choose a valid next segment,
   replan, finalize, stop, or wait; it does not force scene refresh.
3. A successful world-changing Action requires fresh observation before a
   downstream manipulation segment.
4. Only a terminal successful `object.place` record permits post-placement
   verification language and route selection.
5. Continuation/recovery decisions are persisted as structured
   `CONTINUE`, `REPLAN`, `FINALIZE`, `STOP`, or `WAIT_FOR_USER` outcomes. A
   missing decision is a blocked control-plane result, not evidence of physical
   success or a reason to replay an Action.

## Non-goals

The fix does not modify Runtime motion authorization or automatically retry any
Action. It remains fail-closed for unknown or non-terminal Action outcomes.
