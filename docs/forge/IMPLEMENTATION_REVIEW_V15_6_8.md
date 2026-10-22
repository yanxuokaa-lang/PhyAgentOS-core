# Implementation Review v15.6.8: Perception-Bound Task Projection

Date: 2026-10-22 (Asia/Shanghai)

## Findings and Disposition

### Blocker fixed: semantic labels were projected to fixed profile paths

The previous `project_pour_task` converted Agent labels to configured profile
labels and returned `source_path`/`destination_path`, while `LabUtopiaProfile`
derived `entity_ref` and `destination_ref` from fixed USD Prim paths. This could
make a task appear perception-grounded when no observation or grasp candidate
had selected the object. Ordinary profile validation could not detect that
identity substitution because the configured paths were valid.

The projection now requires a fresh PAOS perception binding and returns the
semantic task, parameters, and that binding only. It does not return a cycle
input, Prim path, or profile-derived entity identity. A mismatched requested
source label and a stale/incomplete binding fail closed. This deliberately
prevents the legacy cycle interface from being mistaken for the new measured
subtask path.

### Remaining integration boundary

The legacy cycle still requires an adapter-private
`manipulation_target` containing scene paths, poses, and controller frames.
The current provider-neutral `PerceptionBinding` does not establish a verified
mapping from its opaque refs and measured candidate to those simulator-private
fields. This stage therefore does not fabricate that mapping or send the
binding through the legacy cycle. The required next implementation is a
provider-owned target resolver that consumes the complete measured binding,
resolves opaque refs within the active scene session, and returns a validated
adapter-private target; it must then be called from the governed subtask path.

## PAOS Architecture, Extension, Developer Guide, and AgentLoop

- The shared `PerceptionBinding` now preserves semantic identity for both the
  manipulated entity and destination (`destination_semantic_label` and
  `destination_category`) alongside the existing measured pose/geometry,
  grasp candidate, observation, frame, calibration, revision, freshness, and
  evidence refs.
- Destination semantics are produced by the same understanding result used
  to resolve the destination ref; the task projection does not infer them from
  a scene profile.
- The cycle Tool schema accepts an optional artifact `binding_ref`; it remains
  optional for compatibility. No arbitrary metadata or Prim path was added to
  the public cycle contract.
- PAOS Core remains environment-neutral. Isaac/USD references remain inside
  the adapter-owned execution target contract.
- No AgentLoop plan node, tool sequence, settlement, Runtime lifecycle, or
  motion authorization changed. This phase does not claim the Agent planner is
  already invoking `manipulation.execute_subtask` for LabUtopia tasks.
- No new hash, baseline, or generic gate was introduced.

## Validation

- Perception-binding, subtask-executor, agent-planning, LabUtopia projection,
  and profile tests: `54 passed`.
- Ruff, compileall, and `git diff --check` pass.
- Validation was no-motion. No Isaac Sim, Gateway Action, IK, collision
  planning, robot, or hardware IO ran.

## Seven-Dimension Acceptance

| Dimension | Phase result | Evidence / gap |
| --- | --- | --- |
| 1. Perception correctness | Partial | Fixed-path identity projection is removed; no live camera/model accuracy or labeled-scene evaluation. |
| 2. Binding and freshness | Partial | Projection rejects incomplete/stale binding and preserves refs; real shared sensor-to-binding evidence is not exercised here. |
| 3. Agent subtask granularity | Partial | Generic one-settlement SubtaskExecutor tests pass; LabUtopia task projection is not yet wired to that executor. |
| 4. IK, workspace, collision | Not verified | No target resolver or live planner/simulator validation ran. |
| 5. Grasp, hold, place state | Not verified | No acquire/place Action or physical state transition ran. |
| 6. Pour/stir process feedback | Not verified | No process controller or measured feedback ran. |
| 7. Subtask settlement and recovery | Partial | Generic subtask receipts/settlement remain covered; no LabUtopia multi-tool execution or live recovery was exercised. |

## Overall Decision

This phase is accepted as a correction to task identity projection, not as
completion of the experiment. The next phase must implement and test the
adapter-owned target-resolution port from a fresh measured binding, wire that
port into the existing PAOS subtask sequence, and prove that LabUtopia returns
one terminal subtask settlement without an Agent turn between acquire,
process, and place. Real Isaac execution and process feedback remain separate
later acceptance steps.
