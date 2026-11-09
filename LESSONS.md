# Lessons Learned

This legacy file is preserved for human-authored or historical notes.

When task experience evolution is enabled, it is not injected globally into every Agent turn.
Task failures are stored in the experience ledger and projected to the associated Skill at
`skills/<skill-name>/references/LESSONS.md`. Use `activate_skill` to load only lessons whose
scope applies to the current workflow. A lesson becomes active only after the same normalized,
workflow-related failure pattern is supported by three independent root tasks and passes
abstraction validation. Stable operator safety constraints belong in `AGENTS.md`
or `EMBODIED.md`, not in learned lessons.
