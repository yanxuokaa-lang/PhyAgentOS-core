# LabUtopia R03/R04 no-motion semantic binding diagnosis

Date: 2026-11-01 (Asia/Shanghai)

## Scope and safety state

- Workspace: `out/lab-fullchain-truth-20261101-r03-r04-no-motion/`
- Task: `task_0391e76f784d474e`
- Final task state: `awaiting_replan`
- Controller outcome: `blocked`
- Motion state: no Action invocation, simulator step, or robot motion was authorized or started.
- R04 and `GLASS_ROD` were not reached because the R03 selection failed in the control plane.

## Successful evidence chain before the failure

The R03 route produced successful records for:

1. `manipulation.process_features`
2. `manipulation.prepare_process_features`
3. `manipulation.grasp_task_affordances`
4. `manipulation.prepare_grasp_task_affordance`

The records contained opaque references for the R03 pour lip, the beaker opening,
the grasp candidate set, the qualified grasp/process combination, and the selected
GraspNet candidate. The failure therefore occurred after provider evidence creation
and before IK/collision preparation.

## Direct failure

`forge_plan_select` for `manipulation.execute_subtask` returned:

```text
semantic_binding_mismatch:
Tool argument 'binding' does not match the node
```

The model reconstructed the complete observation-owned `binding` instead of
selecting only the opaque references needed for the task-qualified affordance.
The first attempt omitted `binding.grasp_candidates`. The second attempt copied
the array but changed one provider measurement:

```text
submitted binding.grasp_candidates[12].grasp_geometry.width_m
= 0.10000000149011612

frozen PlanGraph value
= 0.07873450219631195
```

Exact semantic equality correctly rejected the altered binding. The defect is
that the Tool route required the Agent to reproduce Coordinator-owned state, not
that validation was too strict.

Primary evidence:

- `out/lab-fullchain-truth-20261101-r03-r04-no-motion/acceptance.json`
- `out/lab-fullchain-truth-20261101-r03-r04-no-motion/sessions/cli_lab-c8c1d86bfc23.jsonl`

## Architecture decision

The frozen PlanGraph/Coordinator remains the single owner of:

- `subtask_id`
- `operation`
- complete `binding`
- `parameters`
- `tool_sequence`
- derived `ManipulationIntent`

The Agent selects only current provider/query-derived opaque references:

- `process_feature_refs`
- `process_feature_candidate_set_ref`
- `grasp_task_affordance_candidate_set_ref`
- `grasp_task_affordance_ref`
- `selected_grasp_candidate_ref`

`AgentComposedDispatch` will extend the existing `manipulation_intent_v2`
trusted argument builder for `manipulation.execute_subtask` to inject the exact
node-owned fields before schema validation and DecisionTrace persistence. If a
caller supplies any of those fields with a different value, selection remains
fail-closed with `semantic_binding_mismatch`.

This preserves the PAOS dependency direction:

```text
Agent semantic/opaque selection
-> Coordinator-owned frozen PlanNode
-> trusted Tool argument construction
-> Adapter no-motion preparation
-> Action only after preparation and separate authorization
```

No USD paths, simulator handles, raw coordinates, or Adapter objects enter
AgentLoop. No public contract, hash, shadow state machine, collision bypass, or
automatic retry is added.

## Acceptance criteria

1. Omitting all five frozen subtask fields from `forge_plan_select` still
   persists their exact PlanNode values.
2. A large `grasp_candidates` array remains byte-for-byte/equality equivalent
   to the frozen node without a model payload round trip.
3. Supplying a conflicting frozen field is rejected before Gateway invocation.
4. The resulting `ManipulationIntent` remains Coordinator-derived and has
   `motion_authorized=false`.
5. Focused planning/AgentLoop tests pass.
6. The R03/R04 no-motion rerun reaches real IK/collision preparation or records
   the next provider-owned no-motion blocker without starting Action.

## Post-fix no-motion rerun

Run workspace:

`out/lab-fullchain-truth-20261101-r03-r04-no-motion-r2/`

Result:

- Task: `task_36136be3dd04411e`
- Status: `failed` with known outcome after the user-defined stop condition.
- `simulated_motion_enabled=false`.
- The R03 `manipulation.execute_subtask` selection succeeded without copying the
  frozen binding and without `semantic_binding_mismatch`.
- The persisted Action arguments contain the exact Coordinator-owned full
  binding, user parameters `tilt_rad=0.87` and `hold_s=0.6`, the frozen Tool
  sequence, and a Coordinator-derived intent with `motion_authorized=false`.
- Internal `manipulation.prepare` ran and rejected selected candidate
  `candidate://simulator-truth-R03/89312b0cce07496db6f77ea48b4d690d-2`
  with `no_admissible_grasp` / `route_collision`: the approach finger geometry
  overlaps `/World/ReagentZones/A/R03/Model/mesh`.
- `completed_tool_ids=[]`, `world_change_started=false`,
  `possession_state=empty`, and the scene revision did not change.
- R04 and `GLASS_ROD` were not reached because the instruction required stopping
  on the first failed grasp/IK/collision qualification.

The original AgentLoop/Coordinator binding defect is resolved. The next blocker
is an Adapter-owned route/collision result for the selected R03 grasp candidate,
not a semantic-binding or parameter-transport failure.
