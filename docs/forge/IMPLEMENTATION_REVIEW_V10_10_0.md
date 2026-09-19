# v10.10.0 Observation-owned preparation and seven-dimension acceptance

## Findings and disposition

- **Blocker fixed:** `task_10ac4c688c414cd7` supplied legitimate visual envelope
  geometry, but readiness compared it with a SAPIEN actor frame. All 40 options
  failed before planning. Route provenance now checks the bound observed model;
  the existing private actor drift check independently checks its captured actor
  snapshot. No actor pose is copied into the estimate and no tolerance is relaxed.
- **Blocker fixed:** the planner attachment used actor pose, non-target obstacles
  used hidden actor boxes, and the support port read the simulator table. The
  observation-driven path now uses observed envelopes and the observed support
  cloud. Missing observations are not replaced by hidden geometry.
- **Major fixed:** visual models inherited a hidden actor functional-point offset.
  Their model origin is now the observed centroid and their axes are explicitly
  named `observed-envelope/<entity>`. Camera-aligned model axes are not a claim of
  known physical object orientation. Artifact provenance says `observed_envelope`.
- **Major fixed:** a ReplanSignal was converted to an empty successful provider
  response, erasing failure ownership. Full signals are now persisted, and public
  PreparationProviderError codes distinguish infrastructure/capability failure
  from evaluated route rejection. AgentLoop keeps its recovery decision authority.
- **Major fixed:** readiness projections used whichever arm passed, not necessarily
  the selected arm. Bounded per-arm results now determine that option's checks and
  failure phase; unavailable dynamics or stop-control evidence is never upgraded.

The design follows the framework introduction, developer manual, manipulation
developer guide, visual geometry architecture, and Agent input-selection design.
Core remains provider-neutral. Adapter owns geometry and diagnostics; Runtime
owns identity, physical effects and existing safety checks; Agent chooses inputs
and recovery; Verifier alone judges task success. No new hash mechanism, parallel
task state machine, fixed RGB goal, or motion permission was introduced.

## Established seven dimensions

| Dimension | Acceptance result |
| --- | --- |
| Architecture integration | PASS in source/integration scope: observation models feed materialization, readiness and Action attachment; Core/Agent contracts reused. Legacy benchmark geometry retains its separate provenance. |
| Recovery and idempotency | PASS: failures publish no assignment or execution approval; rejection receipts and metrics persist; original task/revision/evidence remain untouched. |
| Robotics safety | PASS for no-motion scope: actor drift, missing binding, model tampering, missing observed obstacles/support and unknown dynamic evidence reject; no Gateway or Action calls. Real execution is not accepted by this report. |
| Context and performance | Measured: 24 materializations in 7.926 s, 20 retained/40 arm options; real readiness 16.991 s, zero provider errors. Public diagnostics contain bounded text/references, not raw geometry. |
| Configuration and reproducibility | PASS: saved observation/candidates/calibration/explicit target, profile/seed, source snapshot, interpreter, exact materializer commands and unique output roots; Skill 2.4.0/Node 0.4.0 isolated installation verified. |
| Maintainability and observability | PASS: ordinary typed errors and existing ReplanSignal, explicit geometry provenance, regression coverage, developer/Skill documentation and reproducible replay CLI. |
| AgentLoop autonomy | Interface PASS: public error preserves actual failure reason for existing settlement/recovery; no automatic retry, DAG rewrite, top-K policy or simulator answer injection. A fresh real-model recovery turn remains untested. |

Overall: regressions validate the observation-ownership and error-propagation
changes. **Behavioral acceptance remains open:** the frozen task has no admitted
route. The comparison below exposes support-estimator and contact-qualification
work still needed. This is not manipulation or end-to-end task acceptance.

## Actual frozen-scene experiment

Source task: `task_10ac4c688c414cd7`, revision `revision_b68a84ef9815440b`.
Build root: `/home/yanxu/tmp/hephaestus/observed-prepare-8s4uczwu`.
Final readiness root: `/home/yanxu/tmp/hephaestus/observed-readiness-e_ngj45y`.

- 24 candidates attempted; candidates 11, 13, 15 and 22 rejected by unchanged
  workspace bounds. 20 retained, 40 candidate/arm options.
- All 40 entered the real readiness/planner path. Provider exceptions: **0**;
  previous actor/observation equality errors: **0**.
- Selected-arm results: **36 approach failures, 4 contact failures**, all reporting
  `planner route segment failed`. This evidence does not distinguish IK failure
  from collision/planner search failure; no narrower diagnosis is claimed.
- The existing worker evaluates both arms per option: 80 internal arm attempts
  for 40 options (72 approach, 8 contact failures). No concurrency/top-K change
  was made. This duplication is a measured optimization opportunity, not a reason
  to change safety checks or report a passing route.
- Readiness phase: 16.990861 s; sum of option evaluation times: 16.921714 s.
  Independent simulator startup + readiness + shutdown: 30.319350 s.
  Build and readiness were measured separately; their sum is not a single live
  end-to-end Tool measurement.
- Final public error: `no_admissible_route`; full failures in
  `preparation-rejections/2908b2e5befe4a01ab90f6930a93d7c8.json` and
  `readiness-summary.json`. Raw planner artifacts are under
  `simulation-route-readiness/`; executed worker sources are under `source/`.
- The independent simulator resets the configured seed before readiness. Only
  its logical revision is assigned the replay label; actors are not teleported
  to fit estimates. Runtime binding validates the saved snapshot. Initialization
  is distinct from the no-motion readiness phase. No Gateway, Action, drive
  command, or readiness simulation step is invoked; planner FK state is restored.
- Earlier replay initialization failures remain in `observed-prepare-h0344bhn`
  and `observed-prepare-ieo8d24e`; a support port projection error remains in
  `observed-prepare-8s4uczwu/readiness-summary.json`. The final result above uses
  the separate `observed-readiness-e_ngj45y` root and does not overwrite them.

Observation ownership does not prove estimate accuracy. The support model is a
world-axis bound of the segmented metric cloud, not an inferred exact plane; it
can be conservative under depth noise or occlusion. Improve the observation
estimator/candidate geometry from sensor evidence if needed. Do not shrink
obstacles, substitute actor truth or mark unknown dynamic checks as pass to obtain
a successful demonstration. Even a statically passing route still needs the
existing dynamic/contact and stop-control evidence before admission.

## Prior success versus current observation: measured comparison

Reference: `/home/yanxu/robotwin20-runtime/artifacts/paos-probe-v7.5.4-20260909T062313Z`,
request `franka-green-release-gap-v751`. Its grasp proposal references an observed
point cloud, but object/collision geometry explicitly says `sapien_collision_shape`;
support and attachment also used simulator geometry. It proves a qualified
single-object simulation route, not a perception-only multi-object Agent task.
Its final translation error was 4.568 mm. All three captured actual object centers
are identical between that reference and the present saved binding (0 mm delta).

| Object | Observed center error | Actual box dimensions | Observed envelope dimensions | Envelope/actual volume |
| --- | ---: | --- | --- | ---: |
| Red | 10.386 mm | 38.772 mm cubed | 70.335 x 60.731 x 73.179 mm | 5.363 |
| Green | 12.173 mm | 38.772 mm cubed | 69.684 x 67.343 x 82.247 mm | 6.622 |
| Blue | 6.815 mm | 38.772 mm cubed | 52.294 x 53.546 x 68.058 mm | 3.270 |

These envelope dimensions are in camera-aligned model axes, not physical object
axes. Their rotation difference must not be called an object attitude error.
Green center delta is (+6.319, +8.455, -6.062) mm. Its conservative world-Z
box interval is [0.700222, 0.806426] m, versus actual [0.740000, 0.778772] m.
The raw green cloud world-Z interval is [0.740592, 0.779360] m: the bound is much
looser than the actual measured points in world Z.

Observed support box top is 0.762275 m, 22.275 mm above the simulator table at
0.740000 m. Across 70,606 support points the world-Z median is 0.740576 m;
the 5th/95th percentiles are 0.739795/0.740728 m. Thus the full-cloud maximum
is not a representative support plane. A robust sensor-derived plane and
separate residual obstacles are needed; do not replace it with simulator height.

The reference selected a 16 mm contact backoff after testing bounded variants.
Its reported minimum sphere clearance was only 0.050918 mm; 0/5/10/15 mm
variants failed. Current materializations contain nominal proposals without that
qualification. Current candidate 0 differs from the qualified reference by
52.964 mm at the robot target and 91.999 degrees in orientation; its ingress is
30.834 degrees from downward vertical versus 3.548 degrees for the reference.
These are different grasp candidates, not a measured pose-estimation error.
Current retained ingress tilts span 3.349–140.414 degrees; confidence is not
reachability evidence. Placement goals also differ, but failures precede transport.

### Isolated no-motion controls

Diagnostic source/results: `/home/yanxu/tmp/hephaestus/geometry-comparison-2mMetG/`.
The script captures native `MotionGen.plan_single` status without changing its
result. Same current 20 candidates, initial robot state and route goals:

| Support | Non-target obstacles | Approach failures | Contact failures | Native failure |
| --- | --- | ---: | ---: | --- |
| Observed | Observed | 36 | 4 | IK_FAIL |
| Oracle diagnostic | Observed | 36 | 4 | IK_FAIL |
| Observed | Oracle diagnostic | 36 | 4 | IK_FAIL |
| Oracle diagnostic | Oracle diagnostic | 36 | 4 | IK_FAIL |

All 20 left-arm options fail approach; right-arm candidates 0/4/9/16 pass
approach but fail contact. `IK_FAIL` is Curobo's collision-aware IK stage result,
not proof of purely kinematic unreachability or absence of collision. Swapping
support/obstacle geometry does not rescue the current nominal candidate set.

Reference-prefix controls: `/home/yanxu/tmp/hephaestus/grasp-reference-comparison-3kTfI0/`.
Only approach/contact were evaluated, not attachment/transport or physical grasp:

| Reference right-arm grasp | Observed support | Oracle support |
| --- | --- | --- |
| Qualified, 16 mm backoff | Contact IK_FAIL | Both prefix phases pass |
| Same grasp, backoff removed | Contact IK_FAIL | Contact IK_FAIL |

Results are unchanged between observed/oracle non-target obstacles. This isolates
a support-model regression for a known reachable grasp and reproduces the need
for its contact adjustment. It does not prove that the same 16 mm adjustment will
rescue current candidates; blindly copying it would violate geometry ownership.
Both diagnostic runs restore joint positions exactly and record zero readiness
scene-step calls and zero Gateway calls. Oracle geometry is private diagnostic
control data only: no assignment, approval, task mutation or release evidence.

Next implementation should fit/support-check geometry from observed points,
integrate existing bounded contact qualification into persistent preparation,
retain raw planner failure classification, and re-evaluate complete routes.
Do not relax IK/collision checks, hard-code the old candidate/backoff, or treat
this seven-dimension code review as a passing real manipulation experiment.

## Validation and replay commands

Core: **504 passed**. Adapter: **533 passed, 1 skipped** (Pillow-dependent module
unavailable in the PAOS interpreter). Skill: **337 passed**. Ruff, compileall and
diff whitespace checks pass. Focused tests cover independent actor drift versus
estimate differences, model tampering, observation-only obstacle/support geometry,
failure persistence, per-arm selection and unavailable-capability rejection.

Set `PYTHONPATH` to the repository, adapter `src`, adapter `runtime`, adapter
`scripts`, and workflow `src`, using the existing PAOS interpreter:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests
python examples/forge-adapters/robotwin20/scripts/replay_observed_preparation.py build \
  --database /home/yanxu/.PhyAgentOS/workspace/.paos/agent_tasks/tasks.sqlite3 \
  --task-id task_10ac4c688c414cd7 \
  --source-root /home/yanxu/robotwin20-runtime/artifacts/paos-rgb-acceptance-v2-20260914-r6 \
  --materializer-command /home/yanxu/robotwin20-runtime/artifacts/paos-rgb-acceptance-v2-20260914-r6/preparation-builds/route-hys8arat/command-0.json \
  --output-parent /home/yanxu/tmp/hephaestus
python examples/forge-adapters/robotwin20/scripts/replay_observed_preparation.py evaluate \
  --replay-root /home/yanxu/tmp/hephaestus/observed-prepare-8s4uczwu \
  --runtime-profile /home/yanxu/robotwin20-runtime/artifacts/paos-rgb-acceptance-v2-20260914-r6/persistent-host-runtime.json \
  --runtime-python /home/data/yanxu_migrated/miniconda3/envs/RoboTwin20/bin/python3.10
```

Each build/evaluation gets a unique directory. Evaluation runs Core orchestration
in PAOS and planner code in the separately provisioned RoboTwin environment.
Timing depends on GPU/CPU load and planner initialization; the saved candidate set
is fixed, while solver nondeterminism may change route rejection details.

Release packages: `/tmp/paos-v10.10.0-release-uCs2qk` (Skill 2.4.0, Node 0.4.0).
Existing release verification: Node size 339632 bytes, SHA-256
`6fda36d1ef18a88b39ca5e46bf6ef3f40fd54d4f5c46fc88ceeaf48508b08327`.
The live task was not stopped/resumed and live Runtime was not restarted or
reinstalled. Physical execution, task completion and full multi-Action video
remain unverified; this no-motion run produced no execution video.
