# Replan Lease Timing and Expired AgentTask Recovery

## Incident

AgentTask task_5135852ae28a4b4e entered awaiting_replan after a pre-Gateway planning semantic rejection. The code defect was repaired while the task remained persisted. On continuation, the Agent spent several model iterations reconciling state and composing the replacement segment. ForgeTaskBeginRevisionTool claimed the bounded replan lease only when its Tool execute method began, after the original deadline had already expired. Coordinator therefore terminated the task with AgentTask replan deadline expired before creating a replacement revision.

## Architectural Failure

The Coordinator already owns a one-shot bounded replan lease. The failure is its invocation boundary: the lease represents an Agent replan attempt, but it is claimed at final Tool dispatch instead of when AgentLoop begins the replan decision turn.

The persisted task then becomes terminal failed. Existing paos task resume only clears a pause flag and intentionally cannot reopen a terminal task. Creating a replacement AgentTask would lose the required task identity and violate the current acceptance run.

## Required General Fix

1. AgentLoop claims the existing bounded lease before the first provider request of an awaiting_replan turn.
2. Provide an explicit operator command that reopens the same AgentTask only when its terminal failure is exactly plan_revision_expired.
3. Recovery must reject cancellation, exhausted replan budget, and any unsettled Action or Session.
4. Recovery appends an authorization event, starts a fresh bounded deadline, and preserves every prior revision, settlement, Tool record, failure event, and task identity.
5. No motion authorization, freshness, calibration, collision, IK, Gateway, planning selection, invocation, or terminal-result rule changes.

## Why Existing Mechanisms Are Insufficient

Git and versioning repair code but do not extend a persisted task lease. pause/resume does not change terminal status. Replacing the task discards the acceptance identity. Direct SQLite edits bypass Coordinator ownership and are prohibited.

## Acceptance

- Replan lease is claimed once before the first replan model request.
- An exact deadline-expired task can be restored under the same task ID.
- Other failed, cancelled, completed, in-flight, or budget-exhausted tasks remain non-recoverable.
- The restored task still requires a normal Coordinator revision and all normal execution gates.
