# v11.0.0 Observed occupancy and local gripper contact

## Result / 结论

The four requested changes are implemented in the existing Adapter/Runtime path.
Frozen replay now finds one qualified contact variant. Complete preparation still
rejects the route at descent with `MotionGenStatus.IK_FAIL`; no assignment,
execution approval, Gateway call or simulator step is produced. This is source
and no-motion acceptance, not manipulation or task-success acceptance.

四项改动已接入现有 Adapter/Runtime。冻结回放出现一个合格接触变体，完整路线仍在下降段
报 `IK_FAIL`；没有 assignment、执行批准、Gateway 调用或仿真步进。接触通过不等于任务成功。

## Design review and disposition

Reviewed against the framework introduction, developer manual, manipulation DAG
guide, visual geometry architecture and Agent input-selection design:

- Grounding binds existing observation/depth/mask/calibration references into
  scene facts. Runtime owns projection, measured robot-self filtering, convex
  contact checks, Curobo occupancy and execution checks. Core/Tool schemas and
  Agent selection authority are unchanged.
- All finite positive depth returns participate. Selected target points remain
  separate; other visible occupancy includes unclassified points. Self filtering
  uses current robot convex link shapes and world poses, including base movement.
  A target/self-label conflict rejects instead of deleting target points.
- Environment voxels merge only adjacent occupied X cells with equal Y/Z cells.
  Separate robot convex components remain separate. Whole-object bounds no longer
  decide whether the object fits the grasp aperture.
- Local checks use real open-finger/palm solids and their nominal straight sweeps.
  The inner finger region must contain observed target points; target and
  environment points inside forbidden solids reject. Existing support clearance
  and finite nonnegative planner clearance are still required.
- Actual planned approach/contact samples additionally check target occupancy
  against robot link solids. FK state restores on both success and rejection.
  Full attachment, support departure, transport/descent, detached-target retreat,
  peer arm, workspace, dynamics and stop-controller checks remain.
- Readiness, persistent execution setup and the independent probe share the
  observed collision loader. The independent probe also loads verified observed
  support facts, avoiding a hidden simulator table fallback on this path.
- Visibility counts explicitly describe convex vertices at contact/approach
  endpoints. They do not establish visibility throughout a swept volume. Unknown
  remains unknown. Existing public errors carry bounded counts/references, and
  successful preparation carries the selected contact reference. AgentLoop owns
  the choice to observe again; no forced retry, graph rewrite or top-K is added.

Review caught and repaired a missing finite/nonnegative clearance check, a
standalone probe support-source mismatch and missing public uncertainty evidence.
The new SciPy dependency is optional under adapter `collision`, loaded for runtime
convex calculations. It is not a Core dependency. Test installation was moved to
an isolated environment; the temporary SciPy install in PAOS was removed.

## Established seven dimensions / 原七维验收

| Dimension / 维度 | Result and evidence / 结果与证据 |
| --- | --- |
| Architecture integration / 架构集成 | PASS in source scope: same Grounding, artifact, preparation and Runtime execution seams; no Core branch or parallel task state. |
| Recovery and idempotency / 恢复与幂等 | PASS: existing failure code and diagnostic receipts persist, rejection publishes no assignment; scene mismatch and missing depth reject; original task and artifacts remain untouched. |
| Robotics safety / 机器人安全 | PASS for no-motion scope: no target point deletion or object/table truth injection, negative collision and joint-restoration tests, complete-route rejection retained; physical execution untested. |
| Context and performance / 上下文与性能 | Measured replay: 304 local variants, only 26 enter contact planning, one reaches full readiness. Public diagnostics contain bounded counts/references rather than raw depth; no LLM performance claim. |
| Configuration and reproducibility / 配置与可复现 | PASS: explicit depth scale/voxel/padding/minimum points, fixed sensor/candidate/calibration/target inputs, source snapshot and separate replay roots; live installation unchanged. |
| Maintainability and observability / 可维护性与可观测性 | PASS: pure geometry module plus Runtime loader, optional dependency, public uncertainty and per-phase reasons; regression tests and developer guide. |
| AgentLoop autonomy / AgentLoop 自主性 | Interface PASS: existing selection/recovery authority and failure codes preserved, uncertainty references exposed. Fresh model-driven recovery and end-to-end task acceptance remain untested. |

## Frozen comparison

Source task: `task_10ac4c688c414cd7`, revision `revision_b68a84ef9815440b`.
Build: `/home/yanxu/tmp/hephaestus/observed-prepare-ptvqs95r`.
Measured evaluation: `/home/yanxu/tmp/hephaestus/observed-readiness-k8wdi2pv`.
Public-diagnostic confirmation: `/home/yanxu/tmp/hephaestus/observed-readiness-aqcu4zbi`.
The evaluation's `source/`, `readiness-summary.json` and
`preparation-builds/contact-qualification/contact-*.json` preserve execution
sources, metrics and exact variant evidence. Original source inputs are unchanged.

| Measurement | Previous whole-envelope contact path | New observed local path |
| --- | ---: | ---: |
| Input proposals | 24 | 24 |
| Materialized candidates | 19 | 19 |
| Arm/backoff variants | 304 | 304 |
| Variants entering contact planner | 0 | 26 |
| Qualified contact variants | 0 | 1 |
| Admitted complete routes | 0 | 0 |

Four candidates (11, 13, 15, 23) fail workspace construction; candidate 22 misses
the observed contact shell. Of 304 local variants, 278 are not sent to IK;
25 planner evaluations fail and one succeeds. Independent rejection counts
overlap: 262 support penetrations, 244 environment/palm sweep collisions,
88 target/palm sweep collisions. No near-table target points were removed.

The successful contact is candidate 16, right arm, backoff 0.020 m, reported
contact clearance 0.0112078034 m. Its full route fails descent with `IK_FAIL`.
Readiness also retains `contact_dynamics_not_proven_without_stepping` and
`stop_controller_not_connected`; neither is upgraded to passing evidence.
`IK_FAIL` alone does not distinguish an unreachable target from collision-aware
IK rejection, so this report does not claim a narrower cause.

The scene has 76,800 valid depth points: 523 target and 76,277 environment;
robot-self points are zero in this particular image. At 10 mm voxels and 1 mm
padding, 4,934 occupied cells merge into 121 boxes. The separate self-filter
regression uses a positive robot return and verifies base-pose invalidation.

This measured evaluation takes 24.986 s for qualification/rematerialization/
readiness, 38.965 s including simulator initialization and shutdown. Build is a
separate phase, so these are not one live Tool latency measurement. Both motion
authorization and Gateway calls are false/zero, with zero readiness simulation
steps; simulator initialization is recorded separately.

The public-diagnostic confirmation retains the same single admitted contact and
descent rejection, taking 23.955 s inside preparation and 37.748 s for the worker
lifecycle. Its public error includes 41,862 free, 382 surface-band, 15,196 occluded
and 17,344 unobserved endpoint vertex samples summed over variants. These are
repeated diagnostic samples, not unique scene points or an occlusion volume.

## Limits and next diagnostic

Observed support remains a conservative fitted slab and attached target geometry
remains an observed envelope. The implementation does not reconstruct hidden
surfaces or prove force/contact stability from sparse samples. Unobserved volume
is not automatically occupied, and it is not asserted free either.

The next specific diagnostic is descent IK with the admitted contact transform,
unchanged requested destination, observed support/voxels and attached geometry.
Keep solver failure details separate from contact qualification. If observation
uncertainty affects that clearance, Agent may select a new observation. Do not
substitute simulator object poses, shrink obstacles to force a route or accept
terminal IK as complete-route success.

No live Skill/Runtime update, task resume or execution was performed. Multi-Action
continuous video remains unverified because this run performs no physical action.

## Validation and reproduction

Adapter: 588 passed, one Pillow-dependent module skipped. Core: 504 passed.
Skill: 337 passed. Suites run separately to preserve import-isolation checks.
Ruff and diff checks pass. Adapter regressions cover convex versus bounding-box
containment, palm/finger/sweep rejection, inner-contact evidence, voxel gaps,
depth visibility, unclassified occupancy, robot self conflict, base changes,
lineage/missing depth, FK restoration, finite clearance and public uncertainty.

Test interpreter: `/home/yanxu/tmp/hephaestus/observed-collision-tests-svvmHf/bin/python`
(isolated venv using existing test packages; NumPy 2.5.2, SciPy 1.18.1).
Runtime interpreter: `/home/data/yanxu_migrated/miniconda3/envs/RoboTwin20/bin/python3.10`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/tmp/hephaestus/observed-collision-tests-svvmHf/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests

PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/paos/bin/python examples/forge-adapters/robotwin20/scripts/replay_observed_preparation.py evaluate \
  --replay-root /home/yanxu/tmp/hephaestus/observed-prepare-ptvqs95r \
  --runtime-profile /home/yanxu/robotwin20-runtime/artifacts/paos-rgb-acceptance-v2-20260914-r6/persistent-host-runtime.json \
  --runtime-python /home/data/yanxu_migrated/miniconda3/envs/RoboTwin20/bin/python3.10
```

To rebuild saved inputs, use the build command in v10.10.0's report with
`--route-input-profile examples/forge-adapters/robotwin20/profiles/robotwin20/route-inputs-persistent.yaml`.
Each evaluation gets a unique root. Planner nondeterminism may change rejection
details; no rerun is permitted to overwrite the original evidence.
