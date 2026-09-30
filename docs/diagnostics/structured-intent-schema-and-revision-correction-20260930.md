# Structured Intent Schema and Revision-Correction Diagnosis

## Incident

During the restored Run-4 AgentTask `task_5135852ae28a4b4e`, Coordinator accepted replacement revision `revision_10496f624121464a`. The next ready node was `prepare_red_acquire_replanned`. Its `forge_plan_select` request was rejected before Gateway execution because the persisted node-local structured intent contained the unsupported field `operation`. No `manipulation.prepare` invocation or physical Action occurred. The authoritative task returned to `awaiting_replan`.

## Concrete Failure Scenario

A model can produce an object that is structurally labelled as `manipulation_intent_v2` while including fields outside the versioned intent schema. Plan materialization accepts and persists the object, and the error appears only when a later selection projects the node into a Tool request. This consumes another planning/replan cycle and can strand a long-horizon task before any Gateway call.

## Architectural Ownership

The PlanProposal-to-Coordinator revision boundary owns acceptance of a proposed node contract. Tool selection owns choosing among already-valid frozen nodes; it must not be the first place that a persisted structured node contract is discovered to be malformed. Runtime and Gateway remain responsible for motion admission and execution, not for repairing Agent-authored planning schemas.

## Premature Agent Prediction Before Authoritative Result

Before the final Tool result was persisted, the Agent predicted that the rejection would be correctable within the same revision. The actual `forge_plan_select` result persisted `requires_replan=true`, returned `task_status=awaiting_replan`, and AgentLoop correctly handed control to the recovery lifecycle. Coordinator and AgentLoop state handling are correct; the prevention point is earlier PlanProposal validation so this malformed revision is never accepted.

## Why Existing Mechanisms Are Insufficient

Python types and ordinary Tool argument validation protect the eventual Tool call but do not prevent an invalid structured intent from being persisted inside an accepted revision. Git and version numbers cannot repair an already accepted task revision. The v12.4.4 isolation fix prevents task-level verification fields from contaminating node-local intent, but it does not validate Agent-authored keys already present inside that local intent.

## Required General Fix

1. Validate each recognized versioned structured intent before Coordinator accepts the revision.
2. Reject unknown fields and missing required fields explicitly; do not silently delete or coerce them.
3. Preserve legacy flat-only nodes through the existing compatibility path without forcing them into a versioned schema.
4. Reuse the same schema implementation used by downstream planning dispatch so proposal acceptance and selection cannot drift.
5. Preserve the existing AgentLoop handoff that follows authoritative `requires_replan` and `task_status`; cover it with regression evidence rather than adding another state branch.
6. Do not alter motion authorization, freshness, calibration, collision, IK, Gateway, invocation idempotency, or terminal-result gates.

## Acceptance

- A proposal containing `manipulation_intent_v2` plus unsupported `operation` is rejected before revision acceptance with a precise schema error.
- Valid acquire/place intents remain accepted and reach normal Coordinator selection.
- Legacy flat-only nodes retain compatibility behavior.
- Existing selection and AgentLoop regressions prove that `requires_replan=true` yields the persisted `awaiting_replan` handoff and prevents same-turn Tool continuation.
- Focused tests, static checks, the seven-dimension review, and the same-task Run-4 continuation all pass before acceptance is claimed.
