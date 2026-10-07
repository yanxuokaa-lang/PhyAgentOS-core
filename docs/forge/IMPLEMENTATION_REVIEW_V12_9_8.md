# Implementation Review v12.9.8

Date: 2026-10-07 (Asia/Shanghai)

## Scope

This review covers the generic fix for the `preparation_provider_error` in
`task_13315d0d962a45f5`. The failure occurred after all candidate routes were
materialized, when immutable Runtime evidence publication found one artifact
reference identifying different old and current capability documents.

The review covers qualification-owned capability aliases, route and capability
snapshot projection, Runtime admission, provider-error projection, release
artifacts, and AgentLoop behavior. It does not authorize or execute an Action.

## Findings

### Fixed Minor: public helper ownership and export were inconsistent

`qualification_capability_ref()` was used across deployment, materialization,
and Runtime admission but was not exported from the Adapter public surface. Its
docstring also called the alias Runtime-owned even though the qualification
package owns the evidence identity. The helper is now publicly exported and
described as qualification-owned.

### Fixed Minor: capability-ref projection lacked a declared mapping type

`PersistentCapabilityProvider` accepted the qualification binding map through
an untyped parameter. It now declares `Mapping[str, str] | None`, matching the
route-builder boundary and making the shared deployment projection explicit.

### Remaining findings

- Blocker: 0
- Major: 0
- Minor: 0

## Seven-Dimension Acceptance

### 1. Architecture: pass

The static arm profile continues to own topology and planning configuration.
The controller qualification owns concrete capability evidence identities.
Deployment projects the current qualification aliases into both the public
capability snapshot and route builder. The immutable artifact store remains the
publication authority. No parallel state machine or AgentLoop shortcut was
introduced.

### 2. Correctness: pass

Routes publish capability and validation payloads under the qualification ID,
then compare their content digests with the approved plan. Runtime admission
requires the same alias namespace and the same approved digests. Legacy plan
references remain readable for already approved packages, while new plan
generation requires qualification-owned references.

### 3. Recovery and idempotency: pass

Identical evidence under one reference remains idempotent. Different bytes
under one reference still fail closed before any pending artifact is published.
Legacy evidence and current qualification aliases coexist without deletion or
overwrite. The failure is non-retryable in the current revision and does not
request semantic replanning.

### 4. Robotics safety: pass

The change is confined to no-motion preparation evidence identity and
diagnostics. Frame, calibration, collision, IK, joint-limit, workspace, stop,
qualification, Action-admission, and reconciliation checks remain in place.
Validation created no AgentTask, invoked no Gateway Query or Action, and
advanced no simulator or physical step.

### 5. Extensibility: pass

The alias is derived from qualification identity and the Adapter's declared arm
binding. No object color, ordering, benchmark ID, camera, entity, candidate, or
selected-arm preference is encoded. The existing left/right literals belong to
the RoboTwin20 dual-arm qualification schema and are not new task policy.

### 6. Observability and maintainability: pass

Known publication conflicts now surface `artifact_identity_conflict` with
`failure_owner=runtime_provider`, `retryable_in_revision=false`,
`requires_replan=false`, and `recommended_action=fix_runtime_contract`. The
message exposes only a relative artifact path and preparation-build reference;
unknown provider exceptions remain generically flattened by Core.

### 7. AgentLoop autonomy and convergence: pass

The Agent still selects planning sources and Actions. Coordinator compiles the
declared projection, and Runtime validates its own evidence. This fix does not
automatically observe, retry, replan, switch a candidate or arm, or dispatch an
Action. A provider-owned immutable-identity failure therefore stops
deterministically instead of entering a repeated planning turn.

## Validation

- Changed Adapter path: `150 passed, 1 deselected`.
- Pick-place Skill full suite: `379 passed`.
- Focused post-review subset: `110 passed, 1 deselected`.
- Ruff on every changed Python file: passed.
- `compileall` and `git diff --check`: passed.
- Full Adapter baseline: `816 passed, 17 failed, 1 deselected`; the 17 failures
  are pre-existing environment/fixture failures involving unavailable `scipy`
  or `cv2`, a YAML monkeypatch, and old Action result fixtures. None intersects
  the changed source paths.
- Real-task no-motion replay used the persisted candidate and current approved
  qualification, produced qualification-owned refs, and passed route schema,
  qualification package, and controller-source validation with
  `simulator_steps=0` and `motion_authorized=false`.

## Release Artifacts

- Adapter: `0.9.7`
- Node: `0.10.12`
- Skill: `3.0.4`
- Node SHA-256: `912bed56c4d1dfd8627186f0e78fb2eb10f55dea6fb2ebf2825c496905835903`
- Skill SHA-256: `3917e65fa0e2372b18e0405ce60ac901bea7cf4d629ba48942c93209e1f2d4e4`

The artifacts were built and verified locally. They were not installed or
started during implementation review.
