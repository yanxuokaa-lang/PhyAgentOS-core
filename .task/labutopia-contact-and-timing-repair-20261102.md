# LabUtopia contact and trajectory timing repair / 接触与轨迹时序修复

## Diagnosis / 诊断

- R03/R05 executed 52.55/53.19 s with TCP travel 1.026/1.036 m; start-to-grasp displacement was 0.572/0.566 m. Staging rotations of 56.7/59.1 degrees took 10.78/11.50 s. `smooth_joint_segment` restarts a rest-to-rest quintic at every pose waypoint. Geometric qualification is not continuous trajectory timing.
- R05 successful route preparation took 8.731 s, after 6.649 s IK-continuity and 13.86 s payload-collision failures; successful-route time is not total search time. First-feasible search preserves safety but is not optimal-path evidence.
- R05 source `/World/conical_bottle02/mesh` authors density 0.1 with metre/kilogram units and no explicit mass. The final composed mesh is 64.8 x 64.8 x 115.2 mm after scale 0.70. `mass=0` schema fallback is not measured zero mass. PhysX mass/inertia must be read after initialization. The builder's 0.02 kg helper is not applied to reagent bottles.
- R05 closure has real transient bilateral impulses: at 52.652 s 0.026465/0.024484 N s; at 52.669 s 0.029889/0.028468 N s. At 52.685 s contact disappears and displacement reaches 26.27 mm; final return displacement is 393.292 mm. Final zero impulses do not prove absence of earlier contact.
- R03 is different: open-finger insertion displaced the object 26.785 mm; closure retained bilateral contact but attachment mismatch rejected lift. Neither run reached pour/stir.
- Closure currently changes both position targets from 0.04 m to zero in one command; arm velocity/acceleration limits do not apply to finger targets. Loss is only rejected on entering lift. This is an execution defect independent of route feasibility.
- OmniGlass has no physics material schema. Left rubber subset has friction 50000, right rubber does not; collider physics bindings are empty. These are authored inconsistencies, not proof of effective runtime friction. R05 convex hull vertex limit 10 versus R03 36 needs final collision inspection, not blind threshold relaxation.

Evidence: `out/lab-fullchain-truth-20261102-{qualified-execute-r2,near-arm-r05-r03-r1}/artifacts/labutopia/{readiness,phase-feedback,acquire-search}`; R05 quarter-speed video remains unchanged. Binary USD properties were read through composed Usd.Stage, not wrapper translation.

中文：轨迹主要是逐点起停造成慢与不连续；R05 的异常源密度、未限速闭爪、接触后继续压向零共同需要修复验证。R03 的张爪插入碰撞是另一问题。当前记录不证明实际质量、峰值力或完整抓取成功，不能用扩大容差掩盖失败。

## Ownership / 架构审核

- Tier C-Safety: no shared public contract change. This repository's AGENTS.md, PAOS developer manual and manipulation guide are authoritative; Hephaestus-specific workflow documents are absent here.
- Domain/AgentLoop/Coordinator retain semantic parameters, opaque selection, task lifecycle, cancellation and settlement. No new scheduler, recovery state or public physics fields.
- Isaac scene initialization owns private physics profiles before reset/capture; motion Adapter owns retiming, drive targets, contact evidence and stop behavior. Another Adapter remains replaceable without caller changes.
- Freshness: apply physical configuration before scene revision initialization and observations. Never change physics inside an admitted Action or reuse historical preparation. Reset preserves authored session opinions; actual physical values are separately measured.
- Existing contact and pose thresholds are reused. Concrete failure: continuing closure after displacement/contact loss physically ejects a body; static types and Git cannot stop a running controller. Enforce this at the existing motion boundary, not as a new generic gate/hash.
- Smallest leak tests: synthetic alternative scene/robot paths work through the same private configuration; same qualified references and parameter projection still pass unchanged; invalid/missing physics and unsafe retimed samples fail before commands.

## Implementation and validation plan / 实施验证计划

1. Save diagnosis and monthly plan before edits (done).
2. Add Adapter-private session physics application and authored/runtime receipts. Use documented simulation assumptions, never claim measured laboratory properties. Preserve external asset files.
3. Add phase-level retiming and full-path no-motion checks before execution; preserve mandatory stops, collision checks, cancellation and tracking.
4. Add bounded closure ramp/contact hold/drift checks and directional contact-window evidence. Preserve uncertain possession on failed physical execution.
5. Run focused and full Adapter/Skill regression, native no-motion physics readback and implementation review. Record limits explicitly; full two-pour/stir success requires a fresh authorized runtime task.
6. Complete bilingual log, exact diffs/lines, current-task status and guide; commit/push only owned files on feature/planning-loop.

## Implemented result / 实施结果

- Physics: `scene_physics.py` applies configured mass, convex decomposition,
  collider/subset physics bindings and the main finger drive limit in the USD
  session layer. External LabUtopia files remain untouched. The optional profile
  is consumed at the existing scene initialization boundary before reset/capture.
- Timing: acquisition movement stages get continuous, rest-endpoint samples;
  swept collision, joint and FK workspace checks run before readiness. Execution
  consumes the qualified samples directly, retaining stage holds and closure.
- Contact: finger targets ramp at 0.015 m/s and 0.15 m/s²; qualified bilateral
  contact freezes the target during settling. Drift beyond existing 8 mm / 0.08
  rad tolerances, misaligned contact and contact loss stop before lift. Cancellation
  preserves the existing measured-hold/uncertain-outcome path. Later phases keep
  measured aperture instead of commanding zero again.
- Evidence: per-substep body-ordered contact impulse, position and normal are
  preserved when the sensor supplies them. No net-force/peak-force inference.
- PAOS: no Core/AgentLoop/Tool/DAG public-contract changes. Same candidate chain,
  existing lifecycle/settlement owner and parameterized pour/stir remain intact.

中文：已完成 Adapter 内的物理配置、连续时序、渐进闭爪与失效停止；没有把瓶子
位置、夹持参数或仿真路径放入 AgentLoop，也没有放宽抓取和碰撞阈值。

## Validation / 验证

### Replacement plant and native USD

Full Adapter and subtask executor regression command (run from repository root):

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
.venv/bin/python -m pytest -p pytest_asyncio.plugin -q \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py
```

The default environment lacks pxr, so two real-USD cases skip there. They were
separately executed with the actual Isaac USD libraries: **10 physics tests pass**,
including alternative scene/robot paths, physical-material binding on collider
and subset, no source-layer mutation and missing-target rejection before mutation.
The native test invocation reuses only pure-Python pytest tooling, preloads native
NumPy/USD, and imports the actual private module without the unrelated application
package initializer. Reproduce in this installed environment:

```bash
ISAAC_EXT=/home/yanxu/miniconda3/envs/labutopia/lib/python3.11/site-packages/isaacsim/extscache
USD_EXT="$ISAAC_EXT/omni.usd.libs-1.0.1+69cbf6ad.lx64.r.cp311"
PHYSX_EXT="$ISAAC_EXT/omni.usd.schema.physx-107.3.26+107.3.3.lx64.r.cp311.u353"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
LD_LIBRARY_PATH="/home/yanxu/miniconda3/envs/labutopia/lib:$USD_EXT/bin:$PHYSX_EXT/bin" \
PYTHONPATH="$USD_EXT:$PHYSX_EXT" PHYSX_EXT="$PHYSX_EXT" \
/home/yanxu/miniconda3/envs/labutopia/bin/python - <<'PY'
import os, sys, types, pathlib
import numpy
from pxr import Plug
Plug.Registry().RegisterPlugins(os.environ['PHYSX_EXT'] + '/plugins/*/resources/')
from pxr import Usd, UsdPhysics, PhysxSchema
pkg = types.ModuleType('isaacsim_lab')
pkg.__path__ = [str(pathlib.Path('examples/forge-adapters/isaacsim_lab/src/isaacsim_lab').resolve())]
sys.modules['isaacsim_lab'] = pkg
import isaacsim_lab.scene_physics
sys.path.append(str(pathlib.Path('.venv/lib/python3.13/site-packages').resolve()))
import pytest
raise SystemExit(pytest.main(['-q', 'examples/forge-adapters/isaacsim_lab/tests/test_scene_physics.py']))
PY
```

An `asyncio_mode` warning is expected in this isolated synchronous test command.
Earlier attempts without the asyncio plugin, native library path or PhysX plugin
registration failed; only the corrected runs are reported as passing.

Final full regression: **450 passed, 2 skipped in 10.10 s**. Changed Python files
pass Ruff; `git diff --check` passes. The two skips are the native USD cases
separately passed above, not unexecuted physical-readback coverage.

### Native no-motion initialization/reset

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-skills/pick-place-workflow/src \
OMNI_KIT_ACCEPT_EULA=YES /home/yanxu/miniconda3/envs/labutopia/bin/python \
  -m isaacsim_lab.physics_probe \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --artifact-root out/lab-contact-timing-20261102-r1/artifacts/labutopia
```

Result: **passed, eight bodies, zero motion commands**. All measured masses are
0.10000000149 kg; inertia matrices are finite, symmetric and positive definite.
Repeated readback does not advance simulation time or change joints. World reset
plus existing configured joint initialization preserves mass/inertia and initial
joint readings. Artifact:
`out/lab-contact-timing-20261102-r1/artifacts/labutopia/physics-probe/202c33511beb4a099fd157965af89e8e.json`.
Physics receipt: `scene-physics/629bde4671b0440fbaefa73a7c6632a0.json` under the same root.
Kit exits 0. Its log also reports unsupported particles on the CPU physics scene,
source scale-orientation warnings and source MDL parameter errors. These do not
invalidate rigid mass readback, but no fluid/rendering acceptance is claimed.

### Timing estimate, not new motion proof

For the saved R03/R05 routes, the same arm knots and configured velocity and
acceleration bounds give the following offline command durations at 60 Hz.
Exclude open/close/lift and holds; no scene collision query or controller runs:

| Recorded route | Old per-waypoint arm timing | Stage-continuous timing |
| --- | ---: | ---: |
| R03 | 50.683 s | 22.366 s |
| R05 | 51.300 s | 24.167 s |

R03 staging rotation changes 10.783 → 4.200 s; R05 11.483 → 5.117 s. These are
command-time estimates, **not measured new execution times**. The ~1 m geometric
detour and first-feasible search are unchanged. Actual resampled route safety and
tracking still require fresh preparation under the configured physics profile.

## Acceptance boundary and next native check / 验收边界与后续原生验证

- Code/test implementation complete; no new live-grasp success is claimed.
- Physical parameters are explicit starting assumptions: 0.06 kg empty vessel +
  0.04 kg rigid contents, configured friction, 2 N main-finger drive cap. They are
  neither measured properties nor fluid mass transfer. Do not increase force or
  tolerances blindly if grip is not retained.
- Next native run starts a fresh simulator, keeps B/R05 then A/R03 as selected
  targets, obtains fresh capture/candidates/preparation, and uses existing Action
  admission/recording. Never replay the old route after physics changes.
- Inspect approach drift first; R03 insertion failure is not solved merely by
  changing timing/mass. If drift stops insertion, inspect final finger/payload
  geometry and approach direction. If close loses grip, inspect per-substep
  contacts, joint/aperture tracking, displacement and authored materials together.
- Retimed collision rejection is a preparation failure, not permission to skip
  collision checks. A successful fresh grip is required before pour/stir, whose
  requested parameters and Coordinator settlement remain unchanged.
- Prior R05 videos remain saved. This no-motion probe produces no new motion video.
