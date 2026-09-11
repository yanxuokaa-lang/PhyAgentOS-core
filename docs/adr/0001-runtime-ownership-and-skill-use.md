# Separate Execution Ownership from Skill Use

Accepted direction: tasks own a Runtime binding and bind actual Tool contracts
before use; Agent-selected Skill versions are recorded per decision/node/attempt
and do not own the robot. This permits method composition and future Skill
evolution without rewriting execution history or transferring an in-flight Action.

The existing primary Skill binding combines deployment identity, instructions and
Tool authorization. Removing its activation check alone is rejected: recovery,
stop, verification and attribution still depend on that record. Preserve legacy
records and migrate consumers together; new semantics must not be inferred for
old tasks. Implementation is staged in the linked design, not complete in this ADR.

See [migration design](../forge/RUNTIME_BINDING_SKILL_USE_DESIGN.md).
