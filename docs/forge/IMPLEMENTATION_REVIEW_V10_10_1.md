# v10.10.1 Observed support and persistent contact qualification

## Architecture review and dispositions

Reviewed against `docs/zh/01-framework-introduction.md` (ownership and physical
execution), `docs/zh/03-developer-manual.md` sections 1, 5, 12 and 13, the
manipulation developer guide, visual geometry architecture and Agent input
selection design. Core/AgentLoop remain unchanged. This extends existing
adapter/provider composition inside the preparation Query.

- **Major fixed:** full support-cloud maximum elevated the whole tabletop by
  22.275 mm. A horizontal consensus model now checks inlier fraction, spatial
  coverage and fitted slope. It retains uncertainty and every residual point
  in local collision boxes. Unsupported support geometry explicitly fails.
- **Major fixed:** persistent preparation omitted existing contact qualification.
  It now tests the profile's finite backoffs using observed object/support
  geometry and calibrated embodiment hand geometry, then collision-aware contact
  planning. It never changes the original proposal or uses an old successful
  candidate, simulator table height or simulator object dimensions.
- **Major fixed during review:** choosing one arm after contact qualification
  could discard another arm's complete-route solution. Each qualified arm's
  smallest admissible variant is now separately rematerialized with its own
  attachment/placement transforms and review artifact. The existing full-route
  selector chooses among the resulting options. Candidate/arm option IDs remain
  unique while raw proposal identities are preserved.
- **Major fixed:** the upstream wrapper discarded native planner status. The
  serialized adapter call captures that result without modifying success or
  solver behavior and restores the instance method on success or exception.
- **Recovery:** `no_qualified_contacts` contains rejection counts and diagnostic
  references. Worker deadline errors retain timeout semantics. No task rewrite,
  automatic Tool retry, new ToolSpec, independent scheduler or motion grant.

Private execution correspondence and actor drift monitoring remain Runtime
checks. Planner object geometry remains observation-owned; measured robot joints
and embodiment collision geometry remain legitimate robot-state/model inputs.

## Established seven dimensions

| Dimension | Result and scope |
| --- | --- |
| Architecture integration | PASS: Grounding -> scene/collision artifacts -> persistent preparation -> internal serialized qualification -> rematerialization -> existing complete-route readiness. Core ownership unchanged. |
| Recovery and idempotency | PASS in tested scope: rejection publishes no assignment/approval; original task and old artifacts remain intact; deadlines propagate; historical no-motion evidence is not reused as execution success. |
| Robotics safety | PASS for no-motion changes: residuals retained, unsupported planes rejected, mesh/pinch checks precede IK, unknown dynamics/stop evidence remain unavailable. Execution acceptance is still BLOCKED. |
| Context and performance | Measured: nominal build 7.828 s; qualification 9.692 s; separate simulator lifecycle 22.441 s. Bounded public rejection summary replaces geometry payload. No model-context or model-latency improvement claimed. |
| Configuration and reproducibility | PASS: optional route-profile support policy, existing finite backoffs, persisted estimator settings, source snapshot and unique replay roots; Skill 2.4.1 / Node 0.4.1 isolated installation verified. |
| Maintainability and observability | PASS: existing qualifier reused, no second execution path, native failure detail retained, tests cover residuals, unsupported geometry, rematerialization, arm options, method restoration and deadline failure. |
| AgentLoop autonomy | Contract PASS: Agent continues to choose evidence/Tool inputs and recovery; qualification is provider geometry work. Fresh live-model recovery and end-to-end manipulation are NOT TESTED. |

The requested implementation and regression work is complete. The frozen scene
still has no qualified grasp under the current conservative object model;
**seven-dimensional implementation review is not a claim that the manipulation
task has succeeded.**

## Frozen no-motion experiment

Source: `task_10ac4c688c414cd7`, revision `revision_b68a84ef9815440b`, saved
observation/candidates/calibration/explicit target. The source task remains
`awaiting_replan`, completed=1, revisions=2, replans=0.

- Nominal build: `/home/yanxu/tmp/hephaestus/observed-prepare-p7r16emb`.
- Final evaluation: `/home/yanxu/tmp/hephaestus/observed-readiness-j2zqrw1g`.
- Earlier evaluations retained: `observed-readiness-5cejgvs_`, `observed-readiness-ivxcutta`.
- Metrics: `readiness-summary.json`, `preparation-metrics/`; per-candidate
  qualification: `preparation-builds/contact-qualification/contact-*.json`.
- Exact Runtime worker sources: `source/`; frozen build commands/config/diff:
  `replay.json`. Build and evaluation are separately timed stages.

Observed support has 70,606 points: 65,117 inliers, 5,489 residuals, 47 residual
collision boxes. Median height remains 0.740576269 m. Conservative top changes
from 0.762274925 m to **0.741737997 m**, including 1 mm uncertainty. Residuals
are not erased or flattened. No simulator height is read on this path.

24 candidates were materialized; unchanged workspace checks rejected 4.
The remaining 20 x 2 arms x 8 profile backoffs produced **320 geometry checks**:

- `finger_envelope_rejected`: 320;
- `mesh_support_penetration`: 278 (overlaps with the previous count);
- IK calls: 0, because no mesh/pinch-qualified variant reached the planner;
- qualified contacts, assignments, approvals and Actions: 0;
- final public code: `no_qualified_contacts`.

`curobo_collision_or_unavailable` on these skipped variants means unavailable
planner evidence, not 320 observed IK failures. The report distinguishes skipped
planning from the previous version's 36 approach / 4 contact IK failures.

The green camera-aligned envelope is still approximately 69.68 x 67.34 x
82.25 mm. This change does not shrink it to simulator dimensions. Further
manipulation progress requires better observation-derived object/contact geometry
or a fresh observation/candidate set that satisfies the existing grasp checks.
Whether an improved model admits a complete route must be measured separately.

The worker permits only snapshot, binding, qualification and readiness queries.
After initialization, attempted `scene.step()` calls raise; the final measured
counter is **0**. No live Gateway call, task resume, Runtime restart or live
installation occurred. There is no execution video from a no-motion run; complete
multi-Action video success remains unverified.

## Validation and reproducibility

- Core: **504 passed** (25.23 s).
- Adapter: **545 passed, 1 skipped** (5.52 s; Pillow-dependent module unavailable
  in the PAOS interpreter).
- Skill: **337 passed** (6.82 s).
- Final entrypoint-validation checks: 6 passed; Ruff, compileall and diff whitespace checks pass.

Run suites with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, PAOS Python and
`-m pytest -q -p pytest_asyncio.plugin`; test roots are `tests`,
`examples/forge-adapters/robotwin20/tests`, and
`examples/forge-skills/pick-place-workflow/tests`. Adapter PYTHONPATH includes
repository root, adapter `src`, `runtime`, `scripts` and workflow `src`.

```bash
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/paos/bin/python \
examples/forge-adapters/robotwin20/scripts/replay_observed_preparation.py evaluate \
  --replay-root /home/yanxu/tmp/hephaestus/observed-prepare-p7r16emb \
  --runtime-profile /home/yanxu/robotwin20-runtime/artifacts/paos-rgb-acceptance-v2-20260914-r6/persistent-host-runtime.json \
  --runtime-python /home/data/yanxu_migrated/miniconda3/envs/RoboTwin20/bin/python3.10
```

The script's build mode performs offline nominal materialization; evaluate runs
the real persistent qualifier before route selection. Each evaluation creates a
new root. GPU load/startup and solver nondeterminism affect timings and later
planner results; the saved sensor inputs remain fixed.

## Isolated release verification

Root: `/home/yanxu/tmp/hephaestus/paos-v10.10.1-release-uu0Jpy`.
Skill: `skills/pick-place-workflow-2.4.1.tar.gz`.
Node: `robotwin20_persistent_host-0.4.1-linux-x86_64.tar.gz`, 344846 bytes,
existing release SHA-256 `2ec74104a7be7b7db5dfc84cb07022e95318e60654a10befa8e7b5c149a91aa3`.
SkillInstaller and NodeInstaller verified the final archives in `isolated-final/` with an
isolated RuntimeStateStore. These packages have not replaced the live version.
