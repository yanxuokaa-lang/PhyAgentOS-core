# v16.6.3 implementation review / 实现复核

## Findings and disposition / 发现与处理

- **Major — final endpoint obstruction was masked by earlier route failures.**
  The short-approach probe previously searched pregrasp IK and reported the first
  branch failure without independently checking final rigid-gripper geometry.
  Adapter-private preflight now checks current cooked palm/finger bounds at each
  exact candidate final TCP, before IK. It does not change a candidate pose.
- **Major — public error text leaked simulator paths.** A regression reproduced
  USD paths in the returned `error` string. Public summaries now expose codes,
  counts and final-grasp phase, retaining the existing opaque feasibility ref.
  Detailed paths, transforms and collision geometry remain in private artifacts.
- **Major — empty-source diagnostic replay exempted all obstacles.** Review
  found prefix matching against `/` when the new replay passed an empty source.
  Four failing tests reproduced it; an explicit nonempty-source condition fixes
  the exemption while preserving normal bound-source/robot filtering.
- **Unsafe proposed alternative rejected — shrinking the hand sphere.** Native
  historical geometry has cooked hand vertices below tabletop height by
  0.574–1.341 mm at the five recorded failures. This is hypothetical geometry,
  not measured contact, but does not support dismissing the sphere as a false
  positive. Neither margins nor collision primitives are weakened.

修复范围内上述 Major 均已处理；当前候选集无法通过终态净空是仍然存在的任务阻塞，
不能将本次修复验收表述为抓取、倾倒或搅拌成功。

## Architecture decisions / 架构决定

- Domain/AgentLoop: task semantics, parameterized operations, opaque selections,
  cancellation/recovery and settlement retain their existing owners.
- Isaac Adapter: USD traversal, current cooked components, FK/TCP transforms,
  geometry overlap, IK and private diagnostics stay in their existing layer.
- Reuse: `cooked_body_boxes` factors the already-used finger extraction for palm
  use. It introduces no shared schema, SDK handle, USD path or new lifecycle.
- Replacement: geometry/cooking and overlap mechanisms are substituted in
  tests behind the existing Adapter interface. Provider/recovery regressions
  still enforce qualified-only selection and unchanged capture lineage.
- Freshness: the formal run uses one current observation/scene/calibration.
  Historical replay keeps original receipt and current scene identities separate;
  it cannot authorize motion or replace current preparation.
- Safety: original 3 mm per-axis margin, full opening sweep, measured-opening
  uncertainty, workspace, IK/continuity, self/environment/payload collision and
  full-route preparation remain. Clear final geometry is only necessary, never
  sufficient. No joint solution is invented for a pose-only check.
- Risk proportionality: no hash, baseline, frozen contract, scheduler or generic
  policy gate is added. This is an earlier evaluation of an existing geometric
  constraint at the robot motion preparation boundary.

## Validation evidence / 验证证据

Contract/algorithm evidence: **450 tests pass**, including blocked-final-before-IK,
clear-final-still-requires-route, missing geometry, actual margin/contact filtering,
pose-only diagnostics, public/private error separation, replacement mechanisms
and existing qualified-only recovery. Ruff, compileall and whitespace checks pass.
Pre-fix regressions failed as expected for missing preflight, USD leakage and
empty-source exemption; failures are not reported as passing evidence.

Provider evidence: `out/lab-palm-cooked-geometry-20261102-r1/geometry.json`
contains five historical cooked-hand samples with unchanged joints/physics time.
Formal fresh run `out/lab-fullchain-truth-20261102-final-gripper-no-motion-r1/`
has task `task_4972b9d477f048d2`, revision `revision_d41e73623a814c98`, session
`cli:lab-ca9ce2f70682`. Four candidates exceed 0.08 m aperture. The other six
candidates × four final orientations reject on palm/table; reused for two
backoffs, these become 48 failed approach records. R03 process queries succeed,
but task-affordance is unavailable and the task is cancelled, host exit 1.

Native pose-only replay `out/lab-final-gripper-geometry-20261102-r1/geometry.json`
exits 0 and reproduces all eight candidate-17 endpoint rejections with no source
exemption, zero joint samples/unreplayed attempts/controller commands, unchanged
joints and physics time. Initial FK/USD translation disagreement is at most
2.01e-7 m. This run includes the empty-source repair; the prior formal Agent run
used a nonempty bound source and does not exercise that diagnostic-only branch.
Kit material and GPU-particle errors remain in the native log; geometry evidence
does not validate rendering fidelity, liquid transfer or particle dynamics.

Live execution evidence: **none**. Motion is disabled, controller outcomes are
empty. No acquisition, R04 pour, stirring or liquid-transfer claim is made.

## Reproduction / 复现

```bash
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_profile.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py

OMNI_KIT_ACCEPT_EULA=YES \
PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/labutopia/bin/python \
  examples/forge-adapters/isaacsim_lab/scripts/inspect_collision_receipt.py \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture.json \
  --receipt out/lab-fullchain-truth-20261102-final-gripper-no-motion-r1/artifacts/labutopia/grasp-approach-feasibility/92b008d411fb4fb9b580bf1b883bb737.json \
  --output out/lab-final-gripper-geometry-NEW
```

The inspector's output directory must be new. Its no-source-contact-exemption
policy is diagnostic and deliberately differs from bound-source qualification.
