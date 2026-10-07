# Implementation Review v12.9.9

Date: 2026-10-07 (Asia/Shanghai)

## Findings First

### Major, fixed: ownership enforcement lived only in one CLI

`v12.9.8` enforced qualification-owned capability references in
`materialize_controller_qualification_plan.py`, but the public
`ControllerQualificationPlan` model still accepted any `artifact://` reference.
Another valid producer could therefore create a new plan with legacy global
references and reproduce the long-lived Runtime identity conflict.

The plan contract is now versioned to v2. New v2 plans require the source
manifest and both capability/validation references to be derived from the
qualification ID. Explicit v1 plans remain readable for already approved legacy
packages. The CLI no longer duplicates this ownership rule.

### Minor, fixed: unsafe identity accepted by alias helper

`qualification_capability_ref()` previously accepted `.`/`..` and path
separators. It now accepts only one non-empty artifact path segment, before any
artifact is materialized.

### Remaining findings

- Blocker: 0
- Major: 0
- Minor: 0

## Seven-Dimension Review

### 1. Architecture: pass

Ownership is enforced by the qualification contract owner, not by one command
line producer. Route materialization, capability projection, and Runtime
admission continue to consume the same qualification-owned identity.

### 2. Correctness: pass

The v2 schema validates the qualification namespace, source-manifest reference,
capability references, and validation references together. v1 is an explicit
compatibility path rather than an accidental default. Package validation still
cross-checks source manifest and plan bindings.

### 3. Recovery and idempotency: pass

The change does not overwrite, delete, retry, or migrate legacy artifacts. A
same-reference/different-content conflict remains fail-closed. Invalid new
plans fail before the staging package is published.

### 4. Robotics safety: pass

This is a no-motion contract and identity change. Qualification, frame,
calibration, route collision, IK, joint-limit, workspace, stop, Action
admission, and reconciliation checks remain unchanged. No Query, Action,
simulator step, or physical movement was executed.

### 5. Extensibility: pass

The rule is based on schema version and qualification identity. It does not
encode task objects, colors, ordering, benchmark IDs, cameras, candidates, or
arm preferences. Existing RoboTwin20 left/right topology remains an existing
qualification schema requirement.

### 6. Observability and maintainability: pass

Invalid contract construction reports package-owned reference or safe-segment
errors at the producer boundary. Runtime publication conflicts retain their
structured provider-owned diagnostics. There is now one ownership rule instead
of a CLI copy and a model copy.

### 7. AgentLoop autonomy and convergence: pass

No automatic recovery behavior was added. Agent and Coordinator ownership is
unchanged; contract-invalid preparation stops before a semantic planning loop
can repeat. No observation, candidate switch, arm switch, retry, replan, or
Action is dispatched automatically.

## Validation

- Qualification, approval, worker, deployment, route, readiness, and Runtime
  regression path: `158 passed, 1 deselected`.
- Pick-place Skill suite: `379 passed`.
- Ruff, compileall, and `git diff --check`: passed.
- The deselected test requires unavailable `cv2`; no changed path depends on it.
- No AgentTask was created or resumed and no Gateway Query/Action was called.

## Release Artifacts

- Adapter: `0.9.8`
- Node: `0.10.13`
- Skill: `3.0.5`
- Node SHA-256: `ecb7f18857e9b42ee21eee92bc6936151d71fb0e90df88c4ba89a054fa1d38d2`
- Skill SHA-256: `61f7625b39868241f23baad482a35d006cdf00deecb3b41cf22523e641056fc4`

Artifacts were built and locally verified. They were not installed or started.
