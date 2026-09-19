# v10.10.2 Observed cloud bounds and attributable contact rejection

## Review findings and disposition

- **Major fixed:** Grounding rotated a camera-axis bounding box, including empty
  corners, into the planning world. For the frozen green cloud, the resulting
  world height was 106.203 mm although all 523 measured points span 38.768 mm.
  Default unoriented box models now transform the complete cloud first, then
  bound it in world axes. Producer padding is retained through the absolute
  calibration rotation. No points are removed; no actor dimensions are inputs.
- **Major fixed:** one boolean concealed aperture, contact-span and palm overlap
  failures. Qualification now persists signed margins and independent reasons,
  and the existing public preparation error summarizes them. Acceptance
  inequalities and planner ordering are unchanged.
- **Major fixed:** a candidate outside the observed contact shell aborted the
  whole materializer as an infrastructure failure. A specific RouteInputError
  subtype now follows the existing candidate-rejection path. Other malformed
  input or provider failures still stop preparation.
- **Major prevented during review:** the world-aligned model retains the existing
  `observed-envelope/` namespace, including Runtime's missing-binding rejection.
  Regression cases cover both model frames, drift and model tampering.
- **Replay correction:** saved targets are reexpressed using only old and new
  observed models, preserving `target * inverse(source)` rather than accidentally
  rotating the object when model axes change. Both requested targets persist.

Reviewed against the framework introduction, developer manual, manipulation
developer guide, visual geometry architecture and Agent input-selection design.
Adapter Grounding owns observation-model projection; Runtime owns identity and
drift, Gateway owns motion, AgentLoop owns selection/recovery, Verifier owns
success. No new Core branch, Tool, task state, hash or admission mechanism.

## Established seven dimensions

| Dimension | Result and scope |
| --- | --- |
| Architecture integration | PASS: production Grounding and persistent preparation use existing provider/receipt paths. Custom shape and legacy no-cloud models remain compatible. |
| Recovery and idempotency | PASS: individual contact-shell rejection does not erase other candidates; diagnostics persist, no assignment is published on total rejection, source task is untouched. |
| Robotics safety | PASS for no-motion regression scope: all points and producer padding retained; stale/ambiguous/invalid claimed clouds reject; drift, collision, workspace and contact checks remain. Manipulation remains BLOCKED. |
| Context and performance | Measured: build 7.907 s, qualification 9.873 s, separate simulator lifecycle 22.748 s. Public failure adds bounded counts, full distances remain in artifacts. LLM timing not retested. |
| Configuration and reproducibility | PASS for source replay: fixed saved sensor/candidate inputs, existing calibration/profile/backoffs/deadline, unique roots, source snapshot and old/new target records. No new deployment package or live installation. |
| Maintainability and observability | PASS: typed candidate error, independent signed geometric diagnostics, geometry/lineage/padding/target regression tests, developer documentation. |
| AgentLoop autonomy | Interface PASS: existing Query failure carries causes to existing recovery; no forced retry, candidate policy or simulator-answer injection. Fresh live-model recovery remains untested. |

Source repairs and no-motion validation are complete. **There is still no
qualified grasp or admitted complete route. This is not task acceptance.**

## Frozen measurement

Task `task_10ac4c688c414cd7`, revision `revision_b68a84ef9815440b` remains
`awaiting_replan`, completed=1, revisions=2, replans=0.

- Old-model diagnostic control: `/home/yanxu/tmp/hephaestus/observed-readiness-i2l8i5nc`.
- Final new-model build: `/home/yanxu/tmp/hephaestus/observed-prepare-4nb_bsh4`.
- Final evaluation: `/home/yanxu/tmp/hephaestus/observed-readiness-qoxxzuyc`.
- `replay.json` contains build inputs, target reexpression, Git revision and diff.
  Evaluation `source/` preserves executed source; `readiness-summary.json` and
  `preparation-builds/contact-qualification/contact-*.json` hold measured results.

| Measurement | Old model | New model |
| --- | ---: | ---: |
| Materialized candidates | 20 / 24 | 19 / 24 |
| Candidate/arm/backoff variants | 320 | 304 |
| Finger-envelope rejection | 320 | 294 |
| Aperture exceeded | 304 | 288 |
| Palm-envelope overlap | 320 | 246 |
| Contact outside finger span | 0 | 0 |
| Mesh intersects support | 278 | 262 |
| Contact outside object | 0 | 92 |
| Actual IK calls | 0 | 0 |
| Qualified contact / assignment / Action | 0 | 0 |

Counts overlap and denominators differ; this is not a success-rate claim.
New-model materialization rejects candidates 11, 13, 15, 23 for workspace bounds
and candidate 22 for contact shell. Of 304 contact variants, ten pass the finger
envelope but still penetrate support. All planner evaluations are `not_evaluated`;
`curobo_collision_or_unavailable` denotes absent evidence, not measured IK failure.
Final public code remains `no_qualified_contacts`. Measured post-initialization
simulator steps, Gateway calls and Actions are all zero.

Green raw world point bounds are approximately
`[0.178684, 0.021272, 0.740592]` to `[0.248368, 0.107287, 0.779360]` m.
The new world-axis model is **69.684 x 86.014 x 38.768 mm**, including retained
producer padding/rounding. The old camera-axis dimensions were
69.684 x 67.343 x 82.247 mm; compare both in the same frame before interpreting
differences. The measured hand aperture is approximately **79.735 mm**; projected
object width and offset both affect acceptance.

A read-only point-height slice above 0.742 m retains 494 / 523 points and spans
52.604 x 50.593 mm in world XY. This indicates low support-height points strongly
affect lateral bounds, but does **not** prove they are mislabeled table points.
No such slice is used by production. Removing those points requires attributable
support/instance segmentation evidence and preserving uncertain occupancy.
Single-view visible surfaces also do not establish a complete hidden object shape.

Next work should test sensor-owned support/instance separation and contact-local
geometry with explicit uncertainty. Re-observation or revised candidates must
remain Agent choices. Do not shrink boxes to simulator dimensions, relax the
finger/support checks, or import the old successful benchmark candidate.

## Validation

- Adapter: **564 passed, 1 skipped** (5.79 s; Pillow-dependent test module).
- Core: **504 passed** (25.66 s).
- Skill: **337 passed** (7.29 s).
- Ruff, compileall and whitespace checks pass.
- A combined single-process run failed the existing adapter import-isolation
  assertion because other suites import forbidden SDKs during collection.
  The three supported separate-process suites above pass; the test was not weakened.

Run each suite separately using `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, PAOS Python,
`-m pytest -q -p pytest_asyncio.plugin` and its respective test root. Adapter
PYTHONPATH includes repository root, adapter `src`, `runtime`, `scripts`, workflow
`src`. Exact replay invocation uses the existing script:

```bash
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-skills/pick-place-workflow/src \
/home/yanxu/miniconda3/envs/paos/bin/python \
examples/forge-adapters/robotwin20/scripts/replay_observed_preparation.py evaluate \
  --replay-root /home/yanxu/tmp/hephaestus/observed-prepare-4nb_bsh4 \
  --runtime-profile /home/yanxu/robotwin20-runtime/artifacts/paos-rgb-acceptance-v2-20260914-r6/persistent-host-runtime.json \
  --runtime-python /home/data/yanxu_migrated/miniconda3/envs/RoboTwin20/bin/python3.10
```

Each rerun creates a new sibling directory. Previous failed/intermediate roots
remain intact. GPU load and planner initialization affect time. The last source
change after the final snapshot only orders a CLI import; no behavior changed.
Live Runtime was neither replaced nor restarted. No physical execution or complete
multi-Action video was produced; that user requirement remains unverified.
