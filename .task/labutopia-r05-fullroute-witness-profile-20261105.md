# R05 full-route witness profile and funnel observability

Date: 2026-11-05. Scope: diagnosis of the v16.9.8 `route_search_timeout`
witnesses, a Provider-level funnel observability repair, an offline funnel
replay tool, and an AgentLoop review of the failed execution task. No safety
threshold, equality check, Tool schema, AgentLoop contract, or Gateway change.
No motion was authorized or executed.

## Witness profile (v16.9.8 execute r1, task_9fa51be5ed0d4e3f)

Source: `out/lab-fullchain-truth-20261104-v16_9_8-execute-r1/` (kept evidence;
all other pre-v16.9.7 run roots were deleted 2026-11-05 with user approval).

64 unique failing acquire attempts (`status=unavailable` in
`artifacts/labutopia/acquire-search/`, 720 events total):

| Failure family | Count | Physical meaning |
|---|---|---|
| `inverse_kinematics_failed` | 14 | no IK solution on route |
| `ik_discontinuity` | 18 | per-waypoint branch jump (staging_reorient 8, direct_pregrasp 4, approach 3, transit_cross 3) |
| `self_collision` link5/link2 × panda_hand | 18 | wrist folded back onto the forearm; checked q7 clustered at 2.8–2.9 rad (joint limit), q6 at 2.5 |
| `route_collision` link5 × `/World/table/surface/mesh` | 12 | forearm sphere (r=0.063 m) dips to z≈0.774 m at the final grasp pose |
| `route_collision` finger × environment | 1 | oriented-box overlap |

Failure-point geometry (parsed from `expected TCP` in witness errors):

- grasp/approach failures at horizontal radius ≈0.5 m, z≈0.8 m — inside the
  comfortable Franka reach envelope; this is not a reach problem;
- transit/staging failures at radius 0.2–0.4 m, z=1.0–1.3 m — held-bottle
  reorientation high and near the base folds the wrist.

## Funnel anatomy (root cause chain)

```
505 same-capture GraspNet candidates for R05 (approach families: ~165 down /
~156 side / ~153 up in camera frame; side-family scores reach 1.00)
  → geometric gates in LabGraspTaskAffordanceProvider._qualify_bottle_grasp
  → 5 survivors (refs 60, 56, 100, 178, 233 — matches the five persisted
     grasp-approach-feasibility receipts exactly)
  → short-approach probe: 56/60 inverse_kinematics_failed, 100
    route_collision (panda_hand × table), 233 gripper_aperture_exceeded
    (0.090098 m > 0.080 m composed limit)
  → 1 combination (candidate 178, score 0.23)
  → full-route search: 65 attempts, distinct exact prefixes, pruned_count=0,
    all fail (matrix above) → route_search_timeout
```

R05 fixture: 65 mm diameter × 115 mm bottle at world ≈[-0.270, 0.360, 0.712–0.828],
rim radius 15.0 mm (observed-geometry artifact, simulator ground truth).
The graspable band between the opening-clearance and support-clearance gates
admits exactly five side-grasp poses for this gripper, and none of their
full routes pass. The gates each carry a concrete physical rationale
(bottle-band, sidewall support, pour-lip occlusion); the witness matrix shows
the surviving pose family is the one the staged route qualifier cannot
execute (forearm-under-table at grasp, wrist-fold at reorient).

Conclusion: the bottleneck is not the route search (it enumerated honestly),
not robot reach (r≈0.5 m is comfortable), and not the mechanism layer per se
(v15.8.0 mechanism runs used a different 97.5 mm two-bottle fixture). It is
the combination of a five-pose graspable band on this fixture with a staged
route generator whose transport-orientation staging happens high and near the
base. Next repairs must be proposed against this profile; no threshold was
relaxed.

## Delivered repair v16.9.9 (observability + replay, no contract change)

1. `LabGraspTaskAffordanceProvider.propose` now counts first-failure gate
   rejects (`gate_rejects`), pre-probe geometry survivors
   (`geometry_qualified`), probe rejects (`probe_rejects`), evaluated and
   final qualified counts, writes a private
   `grasp-affordance-funnel` artifact via the existing store, records
   `funnel_ref` on the candidate set, and mirrors the funnel into
   `perception.diagnostics` when present. Public response schema unchanged
   (principle 5); Adapter-private evidence only.
2. `examples/forge-adapters/isaacsim_lab/scripts/replay_task_affordance_funnel.py`:
   offline replay of the gate funnel from a persisted run
   (calibration + observed-geometry rim + object point cloud + grasp
   predictions). Verified against v16.9.8 R05: reproduces the exact five
   survivors. Reads run evidence, writes receipts only to a scratch store;
   no motion, no task.
3. Focused test
   `test_task_affordance_provider_records_gate_funnel_statistics`.

R05 replay histogram (first-failure attribution):
`too close to the support end` 178, `too close to the opening` 146,
`closes along the bottle axis` 74, `approach may occlude the opening` 35,
`asymmetric finger clearance` 34, `lacks bilateral sidewall support` 31,
`finger span not aligned` 2 → 5 survivors.

## AgentLoop review of task_9fa51be5ed0d4e3f

Held correctly:

- 16-node plan graph compiled with the requested R05 → R03 → GLASS_ROD order
  plus a terminal verify node; four Query nodes settled in order with
  persisted selections; one invalid early selection was rejected by the
  semantic-binding guard before any persisted selection.
- Evidence ordering intact: `before_evidence_captured` → `action_started` →
  `action_accepted` → `action_observed` → settle.
- Failure closure correct: `pour_r05` settled `failed/subtask_failed`,
  task terminal `failed` with `recovery_stopped:pour_r05:subtask_failed`;
  R03 and stir nodes never started; the agent response reported the failure
  without fabricated success or videos.

Findings:

1. The execution task was created with `verification.mode=off`, empty goal
   and zero criteria, so even a fully successful motion chain would finalize
   without semantic verification. Acceptable for this repair loop, but the
   acceptance run must use `enforce`/`recovery` with explicit goal and
   criteria (developer manual §4).
2. The 600 s route search runs inside one node turn with no loop-visible
   progress; the funnel artifact (this repair) makes the 505→5→1 collapse
   visible immediately on the next run instead of after an opaque timeout.
3. Recovery made no replan attempt; given the funnel admits exactly one
   combination, a replan could not change the outcome — consistent, but the
   future multi-candidate funnel should re-evaluate whether replan budget
   is better spent than stopped.

## Validation

```
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  .venv/bin/python -m pytest -q -p pytest_asyncio.plugin \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py
→ 495 passed, 2 skipped (pre-existing native-USD skips)

ruff check examples/forge-adapters/isaacsim_lab/src/isaacsim_lab/visual_perception.py → pass
```

Replay reproduction:

```
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  .venv/bin/python examples/forge-adapters/isaacsim_lab/scripts/replay_task_affordance_funnel.py \
  --artifacts out/lab-fullchain-truth-20261104-v16_9_8-execute-r1/artifacts/labutopia --entity R05
→ evaluated=505 geometry_qualified=5 final_qualified=5; survivors 60/56/100/178/233
```

## Open decisions (not taken in this repair)

- Keep all geometric gates as-is (each has a physical rationale) and change
  the staged route generator (e.g. reorient staging at larger radius), or
- widen the graspable band by fixture changes (bottle geometry/placement), or
- revisit the composed aperture margin (233 at 0.090098 m vs 0.080 m limit)
  only with a concrete measured failure scenario (principle 11).

## Follow-up v16.10.0: outward reorientation repair (route generator)

User selected the route-generator direction. Implemented and validated
(no motion yet):

- `acquire_route_waypoints` previously placed `transit_orient` at the raised
  copy of the route-start TCP. The route-start TCP is the arm home pose
  above the base (r≈0.3 in this run), so transport reorientation happened
  high above the base — the exact wrist-fold cluster (q7 at 2.8–2.9 rad) in
  the witness matrix. `staging_reorient` could also land inward when the
  approach-direction backoff pulls toward the base.
- New optional `acquire_min_reorient_radius_m` (validator included; default
  0 preserves legacy waypoint positions exactly) pushes the raised and
  staging waypoints radially outward from the base before any orientation
  change. Approach/grasp/close/lift poses are untouched; every route still
  passes the unchanged collision/IK/workspace/continuity qualification.
- `configs/labutopia-mixture-motion.json` sets 0.5 m (inside the existing
  workspace box |x|≤0.65, |y|≤0.7).
- Regressions: outward-push geometry, legacy-positions-without-config, and
  validator rejection. Phase-motion 146 passed; full Adapter + executor
  suite 498 passed, 2 native-USD skips.
- Not claimed fixed: grasp/approach-stage forearm-under-table failures
  (pose-family issue, 12–15 witnesses) — still open, untouched by design.
