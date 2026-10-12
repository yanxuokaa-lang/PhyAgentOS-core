# Continuation Context and Skill Compaction Diagnosis (2026-10-13)

## Scope and safety boundary

This diagnosis is based on persisted AgentTask, session, and planning-trace records for
`task_d359b5ef6179479d`. It did not resume the task, call a live Forge Query/Action, read a
camera, or advance the simulator. The fix is prompt-only reconstruction from Coordinator-owned
facts; it does not authorize motion or add a second execution state machine.

## Observed failure

The long-running task reached revision 11 with the current scene binding completed. The durable
record contained:

- eleven plan revisions and seventeen completed obligations;
- authoritative terminal settlements for the earlier acquire/place Action chain;
- the original goal-definition Query receipt;
- a fresh observation, understanding, and binding for the current scene;
- the frozen activated Skill `pick-place-workflow 3.0.22`.

Despite those facts, a later model turn said that the summary did not contain destination
occupancy/attainment state, considered reading `task.goal` again, and repeatedly described Tool
readiness/contracts. This narration was not proof that the records were absent. It showed that
the model-facing continuation working set did not reconstruct them.

## Root cause

There were two related projection defects.

1. `node_task_prompt_projection()` contained the current node and Skill identity but omitted the
   persisted Skill instructions, cross-revision completed effects, execution phase, no-replay
   history, goal ledger, and current-world lineage. `AgentLoop.run_node_turn()` explicitly relied
   on generic `_default_prompt` rules instead of re-injecting the frozen workflow.
2. conversation compaction deliberately removed the large activation result. This is correct for
   token control, but the node/continuation projections did not reconstruct the workflow and
   durable phase facts afterward. As the task grew, the model retained less workflow-specific
   knowledge and compensated by rereading Tool contexts or proposing generic transitions.

The problem was therefore not missing Runtime readiness, `scene.bind`, `task.goal`, or old-scene
reuse. It was a control-plane context reconstruction gap after durable state had already been
persisted.

## Correct ownership model

- AgentTask Coordinator owns task, revision, settlement, execution, SkillUse, and goal-definition
  truth.
- Gateway/Runtime owns provider and physical execution truth.
- prompt projection is a bounded read-only view rebuilt before each model request.
- Skill workflow text is a persisted, task-bound instruction; revision reasons and provider
  payloads remain data and cannot become instructions.
- Action success and current-scene goal attainment are distinct facts. A known terminal Action
  may establish `action_effect_confirmed`; only explicit current-scene verifier evidence may set
  `current_scene_attainment=confirmed` or `failed`.

## Generic fix

The node and continuation projections now reconstruct:

- `frozen_skill_route_context`: persisted Skill name, version, and instructions;
- `execution_phase_context`: current node, completed obligations, remaining active-segment
  obligations, recovery lineage, and counts;
- `no_replay_actions`: recent terminal Action/Session identities plus a global no-replay policy;
- `completed_effects`: stable execution identity, destination, scene transition, release, retreat,
  and outcome facts without reusing old visual geometry;
- `goal_ledger`: durable goal definitions, separate Action-effect and current-scene attainment
  states, and exact evidence provenance;
- `current_world_context`: only successful Query records matching the latest observation,
  scene-revision, and calibration lineage;
- `tool_contract_context`: only the frozen policy for the current node's Tool.

The summaries are capped and include total counts so a longer task does not recreate an unbounded
prompt. Coordinator settlement/admission remains the enforcement owner for replay prevention;
the prompt view is orientation, not a new safety gate.

The implementation contains no RGB, color, block, benchmark, provider, or concrete node-name
branch. It applies to any multi-revision AgentTask using persisted Skills, Query evidence, and
Action/Session settlements.

## Seven-dimension review

1. **Architecture:** the missing workflow/phase reconstruction is implemented in
   `prompt_context.py`; AgentLoop supplies authoritative loaders and the node executor only consumes
   the view. No Runtime, planner, Gateway, or motion-admission ownership moved, and no second state
   machine was introduced.
2. **Correctness:** stale successful Query records are rejected unless observation, scene revision,
   and calibration all match the latest capture. Action-to-goal association requires both stable
   execution identity and destination. Partial attainment evidence is accepted only when it resolves
   to exactly one goal, so a shared destination or entity cannot confirm multiple goals. Top-level
   node settlement and phase context both use the effective late-resolution view.
3. **Observability:** goal definition, known Action effect, and current-scene attainment are separate
   fields with record/revision provenance and total counts. Unknown attainment remains explicit
   instead of being inferred from a successful Action.
4. **Recovery/idempotency:** validated late settlements are projected consistently. Completed and
   unresolved `outcome_unknown` Action/Session invocations are included in the bounded no-replay
   orientation; the Coordinator remains the enforcement owner and unknown outcomes require
   reconciliation rather than replay.
5. **Robotics safety:** no motion path changed. Old visual identities, binding refs, geometry,
   coordinates, and calibration lineage never become current-scene Action arguments. Current-world
   evidence is exact-lineage only, and ambiguous attainment fails closed.
6. **Extension compatibility:** prompt projection versions were advanced while Tool/Skill interfaces
   and persisted schemas remain unchanged. Lightweight/legacy task fixtures fall back to aggregate
   execution records only when revision-local records are absent. All matching is generic; there is
   no RGB, color, block, benchmark, provider, or concrete node-name branch.
7. **AgentLoop convergence:** compacted node/continuation turns receive frozen Skill instructions,
   current phase, remaining obligations, current Tool policy, and bounded histories. Legacy
   continuation Query/entity/goal fields are also capped and retain total counts, preventing the
   compatibility view from defeating compaction or causing repeated contract reads.

All Blocker/Major findings discovered in the review were fixed. The final no-motion validation was
`320 passed` for the focused prompt/planning/AgentLoop suite and `904 passed in 31.20s` for the full
repository suite using `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` with `pytest_asyncio.plugin`. Plain pytest
autoload remains unsuitable in this environment because the installed ROS `launch_testing` plugin
imports a missing `lark` dependency; this is an environment/plugin issue, not a product-test bypass.

