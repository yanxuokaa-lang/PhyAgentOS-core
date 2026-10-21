# Implementation Review v15.3.0: Provider-Neutral Subtask Composition

Date: 2026-10-21 (Asia/Shanghai)

## Findings and disposition

The RoboTwin persistent Runtime composition now accepts the existing generic
perception binding adapter, a Coordinator-owned subtask context resolver, and a
provider-neutral durable assignment store. `manipulation.execute_subtask` is
registered only when all three ports are supplied. The adapter is bound to the
Runtime Query port after the ordinary observation/understanding/grasp/capability
providers are registered; it does not import RoboTwin or simulator objects.

The durable path is now closed on the resolver side: when a store is supplied,
PAOS resolves the canonical artifact and then delegates to the adapter's
`resolve_stored` port. RoboTwin `PreparedRoutes` restores the opaque provider
route and re-runs its own approval, scene-revision, possession, destination and
provenance checks before returning executable arguments. This prevents a
reopened SQLite store from bypassing adapter-owned live validation.

The host can own a configured SQLite store and closes it with other resources.
The perception adapter and Coordinator resolver remain explicit host ports; no
task identity, binding, or target is reconstructed from a profile or Prim path.

## PAOS architecture / extension / Developer Guide / AgentLoop review

- PAOS owns the domain ports, Tool registration, Runtime lifecycle, durable
  reference lookup, internal Tool receipts, and one subtask settlement boundary.
- RoboTwin owns provider execution routes, approval, current world checks, and
  route-to-worker mapping. Its private route fields remain opaque to PAOS.
- The Agent-facing surface still contains one `manipulation.execute_subtask`
  PlanNode; acquire, held preparation, process, and place remain internal calls.
- Partial composition is rejected. No fallback context, fake binding, inferred
  task id, or automatic motion authorization was added.
- The existing `pyproject.toml` lab-assets edit was user-owned and is not part of
  this change.

## Seven-dimension acceptance

1. Perception correctness: **partial**. The generic adapter is wired to the
   Runtime Query port, but no live sensor capture or semantic target run was
   executed in this stage.
2. Binding and freshness: **partial**. Existing adapter checks remain active;
   no-motion composition proves only port wiring, not fresh camera evidence.
3. Subtask-level AgentLoop boundary: **pass for composition**. The endpoint is
   registered as one Tool and internal receipts remain below Agent settlement.
4. IK, workspace, and collision: **partial**. Provider route artifacts retain
   their checks; no real planner/controller execution was run here.
5. Execution state: **not validated**. No Gateway Action or simulator step ran.
6. Process feedback: **not validated**. No pour or stir process ran.
7. Settlement and recovery: **partial**. SQLite close/reopen is covered and
   adapter live validation is re-entered; a complete Coordinator-driven
   subtask recovery run remains open.

Overall plan acceptance: **incomplete**. This stage removes the composition
blocker but does not claim the final LabUtopia/RoboTwin live-task acceptance.

## Validation

- Focused Runtime, subtask, composition, and RoboTwin deployment tests: **81 passed**.
- Ruff, compileall, and `git diff --check`: passed.
- No Isaac Sim, Gateway Action, simulator step, or robot motion was run.

## Remaining blocker

The production host entry point still needs an actual Coordinator-owned caller
to construct the semantic `BindingRequest` and pass the adapter/resolver ports.
Until that caller is available, the optional composition remains fail-closed and
the seven-dimension live perception/execution evidence cannot be accepted.
