# v12.5.0 Multi-source prepare projection implementation review

Date: 2026-09-30 (Asia/Shanghai)
Scope: no-motion Coordinator, AgentLoop, ToolSpec, and manipulation preparation review.

## Findings first

- Blocker: 0.
- Major: 0.
- Resolved Major: `manipulation.prepare` previously could not express its two
  authoritative inputs because `projection_source` and `argument_sources` were
  forced to use one record. Named ToolSpec source slots now authorize the direct
  predecessor grasp record and current-scene capability evidence independently.
- Resolved Major: arm projection initially copied every arm identity. It now
  declaratively filters `availability == available` and rejects empty or duplicate
  arm lists before Gateway execution.
- Resolved Major: the node-turn prompt still described the legacy one-record
  projection after the API gained named sources. It now directs the Agent to pass
  only declared slot names and authorized record IDs, never source paths, candidate
  arrays, arm IDs, geometry, or opaque references.
- Minor: `tests/test_planning_loop.py::test_rgb_attribute_sorting_loop_replans_after_drop_and_reducer_replays`
  remains a deterministic pre-existing reducer replay failure (`arrange-green`
  versus expected `verify`). It fails in isolation and is outside the changed
  projection, selection, ToolSpec, and preparation paths.

## 1. Architecture integration

Pass. Multi-source projection is implemented in the existing planning contracts,
ToolSpec projection engine, node context authorization, Coordinator selection tool,
and ready-node description. No provider-specific join logic, parallel scheduler,
RGB-task branch, or Runtime-side argument assembly was introduced. Legacy
single-record projections remain supported.

## 2. Functional correctness

Pass. The candidates slot accepts only a successful direct-predecessor
`grasp.propose` record and filters candidates by the Coordinator-owned node
`entity_ref`. The capabilities slot accepts only authorized
`manipulation.capabilities` evidence and projects its snapshot plus available arm
IDs. Missing entity candidates, unavailable-only arms, duplicate arms, undeclared
slots, hidden records, wrong Tools, and Agent-authored projected fields fail closed.

## 3. Recovery and idempotency

Pass. Selection is control-plane only. Once the Coordinator persists a valid
selection, pending-selection recovery returns the original planning binding and
`use_selected_arguments=true`; it does not re-run projection or ask the Agent to
reassemble values. Existing invocation reconciliation, terminal-result semantics,
and no-resend behavior are unchanged.

## 4. Robotics safety

Pass. This change ends at read-only `manipulation.prepare` argument compilation and
does not invoke the Gateway, authorize motion, weaken workspace/collision/IK checks,
or bypass planning admission. Source records must share the active scene revision,
observation, calibration, and any frame exposed by both records. Stale or mixed-world
records are rejected before preparation or Action execution.

## 5. Configuration and extension behavior

Pass. Source roles, Tool ownership, field paths, collection filters, and list
predicates are declared in the provider-neutral ToolSpec planning extension. The
generic projection engine supports future multi-source consumers without adding
consumer names or provider conditions to Core. Existing single-source contracts and
ordinary `argument_sources` consumers retain their previous API.

## 6. Maintainability and observability

Pass. `forge_plan_ready` exposes only slot name, required Tool ID, and authorization
scope. `forge_plan_select` accepts record IDs only and persists structured rejection
diagnostics without exposing or accepting projected values. Contract validation
rejects mixed legacy/named projection shapes and duplicate outputs. No placeholder,
fake-success, or silent fallback path remains.

## 7. AgentLoop autonomy and validation

Pass. The Agent chooses authorized evidence records by declared semantic role; the
Coordinator owns candidate filtering and value assembly. The node prompt and Tool
description now match the live API, so the model no longer needs to guess nested
intent fields or combine candidate and capability values manually. Validation: 201
control-plane/AgentLoop tests passed with the unrelated reducer test deselected; 84
Skill/Runtime tests passed; Ruff, compileall, and `git diff --check` passed.

## Acceptance conclusion

Accepted for no-motion integration. The original requirement is met: parameter
assembly and candidate filtering are declarative, Coordinator-owned, source-scoped,
and scene-consistent. A new user-run task is still required to prove live Runtime
preparation, Action settlement, and end-to-end task completion; this review does not
claim physical execution success.
