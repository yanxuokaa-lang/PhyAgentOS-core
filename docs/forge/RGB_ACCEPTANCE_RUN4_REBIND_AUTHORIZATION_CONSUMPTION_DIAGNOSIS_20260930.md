# Run 4 Runtime Rebind Authorization Consumption Diagnosis

Date: 2026-09-30
Task: task_5135852ae28a4b4e
Scope: Coordinator and AgentLoop control plane only; no physical Action behavior is changed.

## Observed failure

The task received one explicit Runtime-rebind authorization and successfully rebound to the active Runtime. It then created a fresh revision and submitted a synchronized multi-view scene.observe. The answered clarification nevertheless remained active in the persisted task record, so AgentLoop projected activate_skill and forge_task_rebind_runtime again. The model attempted a second rebind and Coordinator rejected it with AgentTask is already bound to the active Runtime.

## Root cause

The successful rebind updated the Runtime snapshot and revision but treated the clarification answer as reusable task state rather than a one-shot authorization. Tool projection could not distinguish a still-valid answer from an answer already consumed by the state transition.

## Why existing mechanisms are insufficient

Git history, artifact versions, task primary keys, transactions, uniqueness constraints, and the active-Runtime guard prevent corruption and duplicate binding. They do not represent whether a valid authorization has already been spent. The stale answer remains valid data, so ordinary identity and transaction guarantees cannot prevent later reuse.

## Failure if omitted

AgentLoop can repeatedly expose a transition that is no longer legal, waste model iterations, produce avoidable Coordinator errors, and potentially reuse an old authorization after a later Runtime change. The fail-closed Coordinator guard prevents unsafe motion but does not restore one-shot authorization semantics.

## Required repair

1. Consume clarification_id, clarification_question, clarification_node_id, and clarification_answer in the same successful rebind state transition.
2. Preserve historical authorization evidence in task events rather than active fields.
3. Verify the returned and reloaded task no longer carries the clarification.
4. Verify AgentLoop Tool projection hides rebind-related tools after success.
5. Keep all existing no-in-flight-Action, exact clarification ID, Runtime identity, and revision freshness gates unchanged.

## Acceptance boundary

This repair closes the control-plane loop only. It does not prove the RGB manipulation acceptance run, which still requires three terminal acquire/place settlements, post-Action synchronized observations, release and retreat verification, final RGB ordering, ForgeTaskVerifier success, and a complete three-block video manifest.
