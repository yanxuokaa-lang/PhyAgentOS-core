# LabUtopia support-collider path diagnosis

## Scope

- Task: run the simulator-truth R03/R04 pour and GLASS_ROD stir workflow.
- Owner: Isaac Adapter collision mechanism.
- Public contracts: unchanged.
- AgentLoop/Coordinator: unchanged.

## Reproduced failure

The first authorized v16.9 run reached R03 Action preparation with the two
task-qualified candidates from the same capture, then rejected both as
`payload_collision`. The configured support path was `/World/table`, while
PhysX overlap reported `/World/table/surface/mesh`. The payload ignore rule
used exact string equality, so the normal initial bottle/table support contact
was treated as an obstacle even inside the existing bounded lift departure
window.

No controller motion started in that run: `world_change_started=false`,
`possession_state=empty`, and R04/stir were not entered.

## Fix boundary

`prim_path_is_within(path, root)` matches exactly one configured USD prim or a
descendant separated by `/`. It deliberately does not match lexical prefixes
such as `/World/tableware`. The helper is used only by payload collision
filtering when the existing `support_contact_allowed()` result is true or when
checking the released placement pose. General environment collision, robot
collision, workspace, IK, continuity, aperture and payload margins are not
changed.

## Validation

- Regression covers `/World/table` -> `/World/table/surface/mesh`.
- The same descendant is rejected when the support window is closed.
- `/World/tableware/...` remains an obstacle.
- Adapter plus subtask executor: 467 passed, 2 skipped.
- Ruff, compileall and `git diff --check`: passed.

## Fresh execution evidence

- Workspace: `out/lab-fullchain-truth-20261103-v16_9_1-execute-r1/`
- Task: `task_3ab10413aab34666`
- Action: `invocation://manipulation-execute_subtask/5e20cd84e50b4992`
- R03 process/grasp Query and both no-motion preparations succeeded.
- Full Action preparation selected candidate 57 and emitted readiness.
- Actual acquire motion started and generated
  `artifact://labutopia/phase-video/3a7c6036760444848d476edbceacd3aa.mp4`.
- Closure established a qualified bilateral grip. Lift then stopped with
  `physical_grasp_lost`; `world_change_started=true`, `outcome_known=false`,
  and `possession_state=uncertain`.
- R04 and GLASS_ROD did not start. The task is `awaiting_replan` and must not be
  resumed without physical reconciliation.

This live result proves the support-collider false positive is removed. It does
not prove stable acquisition, pouring, return, stirring, liquid transfer, or
chemical mixing.
