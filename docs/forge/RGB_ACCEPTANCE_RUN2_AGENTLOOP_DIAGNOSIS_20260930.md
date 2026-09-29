# RGB Acceptance Run 2 AgentLoop Diagnosis (2026-09-30)

## Scope

This diagnosis covers task_f710b414d6c2480b and the preceding cancelled task_65aaa658b40d4170. No physical Action was executed in the diagnosed failure paths.

## Evidence

- Attempt 1 selected unsupported camera/wrist. RobotWin exposes camera/head, camera/front, camera/left_wrist, and camera/right_wrist. Gateway returned sensor_unavailable.
- Attempt 2 successfully observed with camera/head plus camera/front, understood red, blue, and green entities, and bound the three task entities.
- Recovery persisted one complete Coordinator-admitted fresh_scene_bind selection, including the entity_refs array, but the model turn ended before consuming it. node_turn_incomplete left the selection resumable.
- Earlier malformed Tool and PlanGraph requests were rejected before Gateway or motion admission, so they produced no world change and no reusable observation.

## Root Causes

1. The scene.observe schema accepted arbitrary nonempty sensor strings but did not enumerate the RobotWin inventory.
2. The workflow did not state a single authoritative-observation invariant strongly enough, allowing a second observation attempt without a world change.
3. Pending-selection continuation was not an immediate mandatory workflow step, so a turn boundary could leave a legal selection admitted but unconsumed.
4. The first scene.bind selection did not preserve the complete entity_refs array. Runtime correctly rejected the missing field; the corrected persisted selection proved that literal top-level arrays are supported.

## Generic Fix

- Publish the finite RobotWin sensor inventory in both single-view and multi-view ToolSpec arguments.
- Require at least two unique sensors for multi-view observation, and require the workflow to preserve the complete explicit entity_refs array selected from the current understanding result.
- Reuse one successful observation until a world-changing Action reaches terminal success.
- Preserve synchronized scene, calibration, frame, freshness, and entity provenance through understand and bind.
- Consume a pending Coordinator selection exactly once with selected arguments instead of reselecting or rediscovering.

The fix is generic to RobotWin pick and place discovery and Coordinator continuation; it does not encode RGB targets, layouts, or task plans.
