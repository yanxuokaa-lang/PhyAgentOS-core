# v11.1.0 Gripper state and observed support representation

## Findings and disposition

- **Major fixed — control target used as geometry.** A normalized command mapped
  to -10/50 mm while the loaded physical fingers allow approximately 0/40 mm.
  Readiness now distinguishes bounded open prediction from unknown future holding;
  execution uses current joint measurements. A close command never asserts zero
  holding width. Contact detailed geometry also uses the bounded open prediction.
- **Major fixed — fixed-open CuRobo versus differing detailed geometry.** The
  Adapter updates all single/batch rollout kinematics with the same joint state,
  retaining native sphere geometry/margins. Missing future holding width retains
  measured reference geometry and explicitly labels the prediction unavailable.
  It does not independently reject a route or claim a predicted holding width.
  Measured peer-arm fingers are projected consistently. Exception cleanup restores
  planner state and preserves caller-owned attachment changes.
- **Major fixed — CuRobo metadata copy.** Its `JointState.copy_` can return a clone
  when optional derivative fields differ, which the configuration copy ignores.
  Locked positions are copied in place explicitly. All rollout instances are
  snapshotted before mutation because some tensors are shared between instances.
- **Major fixed — coarse support height.** Within the existing profile's 20 mm
  band around observed support, the vertical grid uses the existing 1 mm sensor
  uncertainty scale. Coarse 10 mm XY coverage and 1 mm uncertainty padding remain.
  Every return remains occupied; different height bins never merge. Mixed and
  unclassified returns are not replaced by a fitted plane or simulator truth.
- **Major corrected during review — excessive uncertainty expansion.** An initial
  implementation enlarged native finger spheres by 20 mm to cover an unknown
  0–40 mm holding interval. It enlarged directions the fingers never travel and
  caused additional rejection. The user correctly identified this as excessive
  gating in effect. That implementation and its route-acceptance conclusions were
  withdrawn before commit. Final code never changes native sphere radii.

Architecture references: framework introduction sections 1–3; developer manual
invariants, AgentLoop lifecycle and extension workflow; manipulation developer
guide ownership matrix; Agent input-selection design. Runtime owns measurement
and geometry, Adapter owns model conversion/profile; Core remains provider-neutral.
Existing Tool failures/evidence carry uncertainty and rejection for Agent-owned
recovery. No new task state, hash, admission gate, automatic retry or goal adjustment.

## Established seven dimensions

| Dimension | Result and scope |
| --- | --- |
| Architecture integration | PASS for source/integration: readiness, contact geometry, execution replanning and peer projection use the existing Adapter/Runtime boundary. Core/ToolSpec/AgentLoop unchanged. |
| Recovery and idempotency | PASS for no-motion state restoration and attachment preservation, including injected exceptions. Existing lifecycle/unknown-effect regression suites pass. No task resumed. |
| Robotics safety | PASS for bounded geometry and no-motion checks; no margins reduced, observations erased or controller commands issued. Full manipulation is not accepted. |
| Context and performance | Provider records distinguish measured reference from unavailable holding prediction. Refined world has 303 boxes versus 121; performance measured in isolated lifecycle, not live Tool latency. |
| Configuration and reproducibility | Existing descriptor/profile setting; old descriptors default to no refinement. Saved observation/candidate/seed/profile/source/interpreter and unique run directories. No simulator object truth used as planner input. |
| Maintainability and observability | Shared Runtime gripper helper, lazy CuRobo dependency, regression tests, real native-planner assertions and explicit missing-width diagnosis. |
| AgentLoop autonomy | Existing failure/recovery boundary preserved; no destination rewrite, prescribed RGB order, automatic reobserve or retry. Fresh model-driven recovery remains untested. |

## Frozen diagnostic evidence

Source: `task_10ac4c688c414cd7`, candidate `candidate://green-block-01/16`, right
arm, 20 mm backoff. Observation and original task records were not modified.

Final-source verification root:
`/home/yanxu/tmp/hephaestus/gripper-support-validation-AbSpTs`.
`run.py`, `source/`, `runtime.log` and `result.json` preserve the run. The script
explicitly overrides only the collision refinement policy in its isolated
in-memory diagnostic world, recomputing the existing world digest; it does not
publish an assignment or rewrite the original artifacts/task. A new production
preparation must materialize the updated profile normally.

The fixed-geometry checks measured:

- 76,277 environment points, all retained together with their 1 mm uncertainty;
  523 target points retained separately. 5,862 occupied cells, 303 merged boxes.
- At the identical previously diagnosed attached-sphere center/radius, minimum
  environment clearance changes from **-4.1247 mm to +4.1052 mm**. This comparison
  isolates representation overfill; it is not acceptance of the full descent.
- Measured/open joints approximately 40 mm; missing holding prediction retains
  the measured reference without sphere enlargement. Synthetic 17/18 mm FK
  input updates correctly. No future holding-width estimate is claimed.
- All single/batch rollout locked positions checked; qpos/planner state restored
  on normal and injected-error paths; route attachment survives temporary changes.
- At identical synthetic 0/17/40 mm finger states, CuRobo sphere displacement
  agrees with detailed SAPIEN finger-link FK within 3.40e-8 m. This checks state
  transport, not a new sphere/mesh fit. Native spheres remain unchanged when
  future width is unavailable.
- Zero simulation steps after initialization, zero Gateway calls, no motion
  authorization or video. Complete route acceptance is not implied by local
  support-clearance or state-consistency checks.
- Final lifecycle: 35.805 s. Left arm rejects at approach; right arm passes
  close/lift/transport and rejects at descent with IK_FAIL. The introduced close
  rejection is gone. This remaining rejection uses measured reference geometry,
  not a verified prediction of holding width, and is not proof of physical
  impossibility. No full-route admission is claimed.

Earlier roots remain for provenance: `tO8rKz` stopped at diagnostic digest mismatch;
`F7gCeQ` exposed stale lock metadata; `35Oxd4` verified restoration but showed row
height aggregation retaining excessive support overfill. `4ZLt4g` and `YNwS43`
verified geometry controls but used the withdrawn interval expansion; their close
rejections must not be treated as evidence against the actual grasp. None is the
final result.
Planner search nondeterminism can change phase rejection; fixed geometry controls
and state consistency, not candidate success, are this change's acceptance criteria.

## Validation

Core: 504 passed. Adapter: 591 passed, one Pillow-dependent module skipped in the
isolated PAOS-compatible interpreter. Skill: 337 passed. No release-sweep gate or
planning prompt change is included. Sphere radii remain the existing native model;
this work does not claim a new tight fit to detailed convex meshes. Narrower
pre-grasp holding predictions still require trustworthy provider evidence; actual
post-grasp motion requires measurements and existing runtime admission.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/tmp/hephaestus/observed-collision-tests-svvmHf/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/robotwin20/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -q -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests
```

To repeat the native diagnostic, copy the saved `run.py` into a fresh directory
created by `mktemp -d /home/yanxu/tmp/hephaestus/gripper-support-validation-XXXXXX`
and run it with `/home/data/yanxu_migrated/miniconda3/envs/RoboTwin20/bin/python3.10`.
It snapshots the then-current source and refuses to overwrite an existing run.
Live Skill/Node installation, runtime restart, task execution and full-task video
are outside this acceptance scope and were not performed.
