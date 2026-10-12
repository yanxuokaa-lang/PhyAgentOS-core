# Placement Postcondition and Semantic Join Selection Diagnosis

Date: 2026-10-12

Task evidence: `task_bc5b3e04a00b45f7`

Scope: persisted diagnosis and generic PAOS recovery behavior; no live Runtime or motion execution.

## Conclusion

The task exposed two independent failures at different ownership boundaries.

1. The placement Action physically released the selected object and retreated, but its measured final orientation was outside the declared tolerance. The Runtime knew this terminal result, yet a generic `ValueError` caused Core to receive `outcome_unknown`.
2. After fresh observation, understanding, binding, and capability discovery succeeded, the next consumer projection selected only the understanding record. It did not select the projection's semantic join value (`entity_ref`). The Coordinator rejected the selection before invoking `grasp.propose`, but classified the missing join value as requiring a new revision, so the AgentLoop could not correct it in the same node.

This is not a scene-binding failure and is not evidence that a previous Action must be replayed. The fix is generic: classify measured Action postcondition failures as known failures requiring fresh evidence, and make a missing semantic join value a bounded same-node selection correction.

## Persisted evidence

### Placement result

| Fact | Value | Interpretation |
|---|---:|---|
| `release_confirmed` | `true` | The object was released. |
| `retreat_completed` | `true` | The manipulator completed retreat. |
| `clear_of_target` | `true` | The manipulator cleared the target region. |
| `possession_state` | `empty` | The object is no longer held. |
| `position_error_m` | `0.01633825489687694` | Within the `0.04 m` tolerance. |
| `orientation_error_rad` | `0.4256471066724228` | Outside the `0.35 rad` tolerance. |
| original exception | `ValueError: after-state placement verification failed` | A measured postcondition failure was flattened into an unknown outcome. |

The orientation error is approximately 24.39 degrees, while the tolerance is approximately 20.05 degrees. This proves that the final pose failed the declared orientation postcondition. It does not prove that staged placement caused the error, so this change does not alter trajectories, phases, targets, or tolerances.

### Recovery scene and subsequent selection

The subsequent current-scene `scene.observe`, `scene.understand`, `scene.bind`, and `manipulation.capabilities` records succeeded. The binding included the currently visible task entities. The later `grasp.propose` node had no frozen `entity_ref`, and the Agent submitted an understanding `projection_source` without an explicit semantic join value.

The resulting rejection was:

```text
consumer_projection_invalid:
consumer projection requires selected entity_ref
```

No Gateway invocation or grasp proposal occurred. Therefore this rejection cannot be attributed to the grasp provider, binding provider, physical scene, or motion authorization.

## Root cause 1: measured failure was represented as uncertainty

The persistent engine previously inferred outcome knowledge mainly from whether simulator state had changed. Once release occurred, an exception after that point defaulted to `status=unknown` and `outcome_known=false`. That is correct for an unclassified transport, stop, simulator, or measurement exception because the physical result may be uncertain. It is incorrect when verification itself completed and measured a declared postcondition outside tolerance.

The Runtime owns this distinction because it owns physical execution and after-state measurement. A typed `PlacementPostconditionError` now declares:

```text
failure_owner=execution_verification
failure_code=placement_postcondition_failed
outcome_known=true
retryable_in_revision=false
requires_replan=true
recommended_action=refresh_declared_evidence
```

The result remains a failure: it is not converted to success merely because release and retreat completed. At the same time, it is no longer described as physically unknown. Unclassified post-release exceptions remain fail-closed as `outcome_unknown`.

The bounded Action receipt now retains only the allowlisted placement measurement and tolerance values. This gives Core enough evidence to explain recovery without exposing provider-private details or copying Runtime state into the control plane.

Implementation review found that these measurements were stored in the persistent engine state and could otherwise leak into the receipt or artifact for a later Action. Each Action attempt now clears the previous attempt's placement measurement and tolerance before cancellation, preparation, or validation can return. A regression starts from deliberately stale values and proves that an unrelated failed attempt publishes none of them.

## Root cause 2: missing semantic join value was escalated to replan

The projection contract joins an authorized source record to a selected semantic entity. A source record chooses the evidence lineage; it does not choose which entity in that record is the consumer target. When `entity_ref` was omitted, the projection correctly rejected the request, but the rejection incorrectly set `requires_replan=true`.

No Tool had executed, no selection had been persisted, and no world state had changed. The current revision still contained all information needed for the Agent to add the missing join value. Replanning discarded that bounded correction opportunity and led to `node_selection_no_progress` behavior.

The Coordinator now reports any projection error of the existing generic form:

```text
consumer projection requires selected <join_field>
```

as `retryable_in_revision=true`, `requires_replan=false`, with the exact `missing_fields` value and a bounded correction recommendation. The AgentLoop uses that structured field name to request one same-node correction. Other projection contract failures retain their existing replan behavior.

This rule is based on the ToolSpec projection contract, not on `entity_ref`, RGB ordering, colors, blocks, a provider name, or a plan-node name.

## AgentLoop recovery semantics

For a known measured Action postcondition failure, recovery is deterministic and no model decision is needed:

```text
known Action failure with world change
  -> preserve persisted Action record and historical settlements
  -> create a replacement revision containing one scene-refresh Query
  -> observe and reconcile the current world
  -> plan only from current evidence
```

The replacement graph does not contain the failed physical Action, so recovery cannot immediately replay it. Earlier successful Actions also remain historical facts and are not replayed. Whether a later plan should perform a new corrective Action is a separate planning decision based on refreshed evidence; it is not inferred from a stale visual entity identifier.

For a missing semantic join value before Tool execution:

```text
selection rejected before execution
  -> keep the current revision and node
  -> expose the exact missing semantic join field
  -> allow one bounded Agent correction
  -> persist through the same Coordinator admission path
```

Existing correction budgets and no-progress guards still bound convergence. No waiting state, alternate execution path, or automatic entity choice was introduced.

## PAOS architecture and extension principles

- **Runtime owns physical truth:** release, retreat, possession, after-state measurement, and whether an outcome is known.
- **Adapter owns bounded projection:** only stable, allowlisted measurements and failure metadata cross into the Action receipt.
- **Coordinator owns durable selection:** source lineage and semantic join values are persisted through the existing selection transaction.
- **AgentLoop owns bounded correction:** argument-shape errors that can be corrected without execution remain in the current node; world-changing settled failures create a recovery revision.
- **Planner consumes current evidence:** stale visual IDs and geometry are not carried across a scene change. Historical Action effects remain context, not current perception.
- **Safety remains fail-closed:** unknown post-release exceptions remain unknown; no target, tolerance, calibration, trajectory, collision, IK, readiness, or motion-authorization rule was relaxed.

No new hash, baseline, global gate, persistent schema, task-specific rule, or duplicate state machine was added.

## Verification

All verification was fixture-based and no-motion.

- Focused and cross-layer suites: `315 passed`.
- Full repository suite: `900 passed`.
- Ruff: passed.
- Python compileall: passed.
- `git diff --check`: passed.

No Runtime was installed or restarted, no task was resumed, no Gateway Query or Action was invoked, no camera was read, and no simulator or robot motion was performed.
