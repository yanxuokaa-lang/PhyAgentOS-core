# RGB Acceptance Run 3 Staging Diagnosis (2026-09-30)

## Authoritative State

- AgentTask: task_5135852ae28a4b4e
- Skill binding: pick-place-workflow 2.9.5
- Initial synchronized camera/head plus camera/front observation, understanding, capabilities, and RGB-only binding all succeeded.
- Current observed order is red, blue, green. The final green and blue destinations are occupied by the opposite movable block.
- No physical Action has been admitted or executed in this task.

## Root Cause

The workflow correctly detects an occupied-destination cycle and refuses to overwrite a block. The Runtime publishes final benchmark destination references but does not publish a provider-neutral Query that converts observed free support geometry into an opaque staging destination reference. Asking the user to supply that opaque reference violates PAOS ownership; inventing a pose, using manipulation.target, or using simulator actor truth would violate the task constraints.

## Architectural Requirement

Add a read-only staging-destination Query owned by the Runtime and exposed through the Skill. Its inputs must be current observation, scene revision, calibration, binding, moving entity, observed support/free-space evidence, and object geometry. It must return an opaque destination_ref registered through the existing destination registry, plus provenance and clearance evidence. It must not authorize motion. manipulation.prepare and object.place remain the only readiness and world-changing boundaries.

The capability must be generic for rearrangement cycles and temporary placement; it must not encode RGB identities, benchmark slot coordinates, or a fixed block template.

## AgentLoop Finding

The third run followed the one-observation discovery chain and stopped fail-closed. The earlier automation of the second run did violate the intended no-blind-retry rule by launching multiple continuation windows against the same scene_bind_missing_entity_refs condition. That behavior is retired: a repeated identical authority failure is now treated as one terminal run diagnosis, not a reason to relaunch the Agent.

