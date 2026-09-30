# RGB Acceptance Run 3 Runtime Rebind Diagnosis (2026-09-30)

## Authoritative failure

- AgentTask: task_5135852ae28a4b4e
- Frozen Skill binding: pick-place-workflow 2.9.5
- Current Runtime: pick-place-workflow 2.10.0 / Node robotwin20_persistent_host 0.10.0
- Coordinator rejection: AgentTask Forge runtime binding is no longer active
- No staging Query or physical Action was invoked after the rejection.

## Root cause

The task correctly freezes Runtime instance identity, Gateway identity, Runtime profile, Skill version, ToolSpec digests, and task ownership. Replacing the Runtime to install the provider-neutral staging capability created a new Runtime instance and Skill version. The old task remains durable, but its execution owner no longer exists. Automatic adoption would let a different Runtime silently acquire task authority, while globally weakening identity validation would break invocation and motion ownership.

## Required architecture

Add an explicit control-plane rebind transition rather than relaxing execution validation. The transition must require a current primary Skill activation, reject terminal tasks and unsettled task-owned Actions/Sessions, archive the old primary binding as historical support, open a new immutable revision bound to the new Runtime, clear discovery evidence for that new revision, and leave every old revision and Tool record attached to its original binding. The transition is non-motion and must remain auditable.

Verification must validate each revision against its own historical binding, not rewrite all revisions to match the newest primary binding. All Tool execution after rebind must use the new revision and fresh discovery chain.
