# Implementation Review v12.4.1 — Explicit AgentTask Runtime Rebind

Date: 2026-09-30

## Scope

Review the control-plane transition that lets one durable, non-terminal AgentTask continue after its frozen Forge Runtime has been replaced. This review covers the rebind implementation only. It does not claim that the RGB arrangement, verifier, or video acceptance has completed.

## 1. Architecture integration — PASS

- Rebind is owned by AgentTaskCoordinator and exposed as forge_task_rebind_runtime.
- Runtime identity validation remains unchanged; a replacement Runtime cannot adopt a task through normal Tool validation.
- The Agent must activate the current primary Skill and pass its Coordinator-issued activation_id.
- The original binding is retained in supporting_skill_bindings and every old revision keeps its original skill_binding_id.
- The new Runtime receives a new immutable revision rather than rewriting prior execution history.

Blocker: 0. Major: 0.

## 2. Recovery and idempotency — PASS

- Rebind rejects terminal tasks, missing origin sessions, missing activation services, missing binding candidates, content mismatches, and attempts to rebind to the already-active binding.
- A repeated call after successful migration is rejected as an already-bound operation rather than creating another revision.
- No invocation is dispatched, replayed, reconciled, or replaced by this transition.
- Runtime task-binding ownership changes only after the durable task update succeeds; normal startup reconciliation can restore the dynamic set after a later process restart.

Blocker: 0. Major: 0.

## 3. Robotics safety — PASS

- Rebind is a control-plane operation and performs no Query, Action, Session, Gateway POST, robot movement, or simulator mutation.
- Any non-terminal task-owned Action or Session blocks migration.
- The new revision has no discovery evidence and explicitly requires scene.observe, scene.understand, manipulation.capabilities, and scene.bind before planning.
- Existing freshness, calibration, workspace, collision, IK, authorization, Coordinator, Gateway, terminal, and post-place gates are unchanged.

Blocker: 0. Major: 0.

## 4. Configuration and reproducibility — PASS

- The transition consumes the active Runtime and Skill activation already selected by the standard PAOS registries; it introduces no RGB, RobotWin pose, camera, destination, or provider special case.
- Tool input requires task_id, activation_id, and a non-empty reason. PAOS continues to generate binding and revision identities.
- Legacy records load with active_skill_instructions unset and fall back to primary_skill_instructions.

Blocker: 0. Major: 0.

## 5. Maintainability — PASS

- Initial identity instructions remain immutable; active_skill_instructions represents the currently selected method after migration.
- Verification validates each ToolExecutionRecord against its own PlanRevision binding, and each revision against the task's complete binding lineage.
- Runtime-only tasks remain compatible through the None binding lineage.
- The implementation reuses existing ForgeSkillBindingResolver, SkillActivationManager, AgentTaskStore, SkillUseRecord, and PlanRevision models.

Blocker: 0. Major: 0.

## 6. Observability — PASS

- Durable event task_runtime_rebound records the prior binding, replacement binding, new revision, and operator reason.
- runtime_snapshot_ref moves to the replacement instance while historical bindings remain available to prompt and verification projections.
- The saved diagnosis records the authoritative Coordinator rejection and confirms that no motion occurred.

Blocker: 0. Major: 0.

## 7. AgentLoop autonomy — PASS

- The Agent can recover the same task without creating a fourth AgentTask or asking the user for coordinates or opaque references.
- Migration requires an explicit current Skill activation and explicit rebind Tool call; it is never silently inferred from Runtime availability.
- The empty revision prevents the Agent from reusing stale discovery and provides a clean point for the synchronized dual-view discovery chain.
- Old settlements and execution records remain attached to their historical revision, preventing repeated execution from being mistaken for unfinished current work.

Blocker: 0. Major: 0.

## Validation

- Focused AgentTask, Tool, lineage, verifier, and planning integration suite: 126 passed.
- Ruff: passed.
- compileall: passed.
- git diff --check: passed.
- Runtime rebind tests cover successful history-preserving migration, fresh-discovery requirements, current Skill instructions, Tool exposure, and rejection with an unsettled Action.

## Conclusion

The implementation satisfies the saved diagnosis and PAOS ownership philosophy. It preserves frozen execution authority by default and permits migration only through a user-authorized, auditable, non-motion transition. The next acceptance step is to activate Skill 2.10.0, call forge_task_rebind_runtime for task_5135852ae28a4b4e, and continue the same task through fresh discovery and physical execution.
