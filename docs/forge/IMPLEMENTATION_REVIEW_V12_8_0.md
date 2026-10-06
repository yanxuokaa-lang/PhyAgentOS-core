# v12.8.0 Implementation Review

## Scope

Review the profile-driven contact-qualification change that removes full-depth observed
occupancy from the current GraspNet experiment while retaining Curobo planning against other
bound objects and the table/support surface. This review covers no-motion preparation only;
it does not claim successful acquisition, placement, simulator stepping, or hardware motion.

## Findings

No Blocker or Major finding remains after implementation and focused regression testing.

### Minor: simplified world has deliberately bounded obstacle coverage

`planner_world_only` represents non-target bound objects, the native table, observed support
residuals, and peer-arm projections. It does not claim avoidance of unidentified objects or
unknown/occluded depth space. This matches the present experiment scope, but must not be used
as evidence for open-world or hardware collision safety. Such deployments must select the
full observed-occupancy policy or another validated environment representation.

## Seven-Dimension Review

1. **Architecture integration: pass.** Policy ownership is in the Adapter route-input
   profile. Deployment parses it once, the route builder sends it in the existing
   `contact_qualification` Query, and Runtime executes it after installing the existing
   collision world. No second planner or parallel task state machine was added.
2. **Correctness: pass.** `planner_world_only` evaluates every declared arm/backoff through
   Curobo, accepts only planner success with finite non-negative support clearance, then
   rematerializes dependent route geometry. Complete route readiness remains required after
   contact selection.
3. **Recovery and idempotency: pass.** Qualification remains a no-motion Query with
   `simulator_steps=0` and `motion_authorized=false`. It writes per-candidate diagnostics but
   creates no Action, ownership transition, or world change. Existing replan semantics are
   unchanged.
4. **Robotics safety: pass for the declared simulation scope.** Frame, calibration,
   workspace, IK, joint limits, native table binding, non-target obstacles, peer arms,
   authorization, Gateway admission, stop/reconciliation, and settlement remain active.
   This is not a hardware or unknown-obstacle safety proof.
5. **Extensibility and compatibility: pass.** The enum is independent of task, color, camera,
   benchmark ID, object count, and grasp provider. `observed_occupancy` remains available;
   route-input schema v4 makes policy selection explicit and rejects ambiguous combinations.
6. **Observability: pass.** Preparation metrics record the chosen mode, qualification output
   records `planner_world_contact`, and simplified-mode results contain no visibility or
   unknown/occluded counters. Existing diagnostic artifacts and failure ownership remain.
7. **AgentLoop behavior: pass.** The Agent still selects records, candidates, replans, and
   Actions through existing PAOS contracts. Core does not auto-observe, auto-select,
   auto-replan, or auto-execute based on this policy.

## Validation

- Focused Adapter tests: `79 passed`.
- Skill, release-bundle, and install-discovery tests: `87 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- Node `0.10.5` deterministic build: SHA-256
  `a431812a48ab34a9aab77142bacb4a3583133da585361351f94e24f97c052088`.
- Skill bundle `2.10.11` built successfully.
- Full Adapter suite rerun with the complete script/runtime import paths and explicit
  `pytest_asyncio`: `788 passed, 2 failed, 1 skipped`. The two failures reproduce in
  unrelated Action-result and task-video projection fixtures and do not call the changed
  qualification path. Focused planner-world/runtime regressions pass independently.

No AgentTask was created or resumed, no Gateway Query or Action was invoked, and no simulator
step or physical motion occurred during this implementation and review.
