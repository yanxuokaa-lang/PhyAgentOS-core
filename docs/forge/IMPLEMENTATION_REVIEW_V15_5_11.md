# Implementation Review v15.5.11: Worker-Owned Scene Revision

Date: 2026-10-22 (Asia/Shanghai)
Branch: `feature/planning-loop`

## Findings and disposition

No Blocker or Major findings remain for this bounded revision-lifecycle change.

- The profile revision is now only a scene identity seed. A worker session owns the active revision, with a session identity and a monotonically increasing sequence. A restarted worker therefore cannot accept an observation revision produced by a prior worker.
- Observation metadata resolves the active session revision at capture time. The worker exposes a read-only revision query for the PAOS host.
- Preparation and the host-side action entry reject unavailable or stale revisions before backend execution. The worker independently checks the revision immediately before dispatch, closing the race between host validation and serialized worker execution.
- When execution reports `world_change_started=True`, the worker advances its revision even if the terminal outcome is unknown. The returned `new_scene_revision` is the worker-owned value, replacing controller-generated revision strings.
- The LabUtopia profile can carry a live revision supplied by its caller; it no longer rejects it merely because it differs from the static profile seed. Omitting it still falls back to the seed and is rejected against an initialized live worker revision.
- No SHA/hash, duplicated task state, or AgentLoop node was added. Revision ownership is the worker scene owner; PAOS carries the token and its existing lifecycle remains unchanged.

## Architecture and developer-guide review

- **PAOS ownership:** task, invocation, receipt, and settlement ownership remain in Core. The adapter owns the simulator session and its scene revision.
- **Dependency direction:** Core-facing contracts remain unchanged. The Isaac adapter uses its existing worker-session boundary; no Isaac SDK or profile details were added to generic PAOS packages.
- **Extensibility:** the scene owner exposes only a revision string over the worker boundary. A future simulator backend can implement the same host resolver behavior without changing AgentLoop or task planning.
- **Failure semantics:** no initialized revision returns unavailable; mismatch returns invalid/stale; neither starts world change. Unknown outcomes after a started change invalidate the previous observation revision.
- **AgentLoop:** no AgentLoop code changed. Multiple internal Tools remain within their existing subtask execution and do not create extra model turns or settlements.
- **Anti-OverDefense:** session identity plus a sequence is sufficient for the concrete stale-observation scenario because the worker is the sole scene mutator in this process. No content hashing or generic revision gate was introduced.
- **Robotics safety:** all changes are no-motion contract/wiring. No Isaac Sim process, physics step, IK, collision query, or robot motion was run.

## Seven-dimension acceptance

| Dimension | Status | Evidence / remaining work |
|---|---|---|
| 1. Perception source | Partial | Worker session revision is attached to captured camera artifacts in stub wiring; no live camera capture or semantic perception was run. |
| 2. Binding and freshness | Partial | Live session revision, stale rejection, and revision advance are tested. Full observation-to-binding-to-preparation-to-assignment lineage and freshness remain incomplete. |
| 3. Agent task granularity | Partial, unchanged | AgentLoop is untouched; this revision adds no node/turn. Full pour/stir subtask settlement is not exercised. |
| 4. IK, workspace, collision | Not verified | No IK, workspace, or collision query ran. |
| 5. Grasp, hold, place truth | Not verified | No simulator state transition ran. |
| 6. Process feedback | Not verified | No pour/stir task executed and no physical process feedback was measured. |
| 7. Subtask settlement/recovery | Partial, unchanged | Existing settlement path is untouched; no live task receipt/recovery was run. |

Overall plan acceptance: **not accepted**. This phase proves revision lifecycle behavior against worker/API stubs only. Remaining blockers include real Isaac 5.1 camera/Task lifecycle validation, artifact serving/resolution, perception-derived binding and preparation/assignment lineage, and real no-motion-to-motion qualification of IK, collision, grasp/place, pour/stir feedback, and single subtask settlement.

## Validation

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src pytest -q examples/forge-adapters/isaacsim_lab/tests`: `79 passed`.
- `ruff check` on changed Python modules/tests: passed.
- `python -m compileall -q examples/forge-adapters/isaacsim_lab/src/isaacsim_lab`: passed.
- `git diff --check`: passed.
- Pytest reported the existing unknown `asyncio_mode` option warning with plugin autoload disabled. No Isaac Sim, Gateway, simulation step, IK, collision query, or motion ran.
