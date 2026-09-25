# v11.7.13 GraspNet deployment and RGB acceptance review

Date: 2026-09-25, Asia/Shanghai. Branch: feature/planning-loop.

## Findings and repairs

1. **Major, repaired: deployment did not expose the requested composition.**
   Generic profiles selected GraspNet, but observed actions were disabled; the
   benchmark action profile still selected GraspGen. Added the explicit
   robotwin-blocks-ranking-graspnet profile, reusing generic dataflow and existing
   observed geometry, benchmark goal and monitored Action owners.
2. **Major, repaired: native decode order controlled the worker cap.**
   Real inference on a captured 704-point perception cloud produced 1,024 decoded
   candidates. The previous first 24 scores were unsorted (0.091, 0.117, ..., 0.614).
   Sort by native score before the 24-candidate cap. Report the threshold count
   before truncation. Adapter NMS retains at most 10; it does not pad candidates.
3. **Major, repaired: deployed artifacts lagged source.**
   Rebuilt Node 0.7.13 and Skill 2.7.10 together using the existing artifact lock.
   The old task had only settled Queries and no Action invocation; Coordinator
   cancelled it before RuntimeManager stopped the old deployment.
4. **Minor, repaired: stale package assertion and documentation.**
   Update the package assertion from 2.6.20 to 2.7.10, remove duplicate oracle prose,
   correct the generic provider name and document the observed benchmark profile.
5. **Test coverage correction.** The PAOS environment lacks Pillow, so the existing
   perception-worker module skips collection. The new GraspNet ranking regression
   is in its own file and executes without optional image or model dependencies.

## Seven dimensions

| Dimension | Source review | Evidence / boundary |
| --- | --- | --- |
| Architecture integration | Pass | Provider ranking in isolated worker; selection/configuration in adapter/profile; no Core task-specific branch. |
| Recovery and idempotency | Unchanged; live evidence pending | Same-invocation reconciliation and Coordinator task ownership preserved; old query-only task cancelled through CLI. |
| Robotics safety | Preserved; full route pending | Observed geometry, GraspNet transform and provider depth; existing workspace/contact/collision/route/Action gates remain enabled. |
| Configuration and reproducibility | Pass for deployment | Explicit GraspNet env, checkpoint/source, sample 24 / retain 10, new artifact root, model gpt-5.6-sol high, existing Node lock verified. |
| Maintainability | Pass | Existing extension seams, independent provider configs, isolated regression; no new protocol or speculative gate. |
| Observability | Improved | Honest pre-cap worker count and scored candidates; source patch, session, config and process exit saved per run. |
| AgentLoop autonomy | Live validation in progress | PAOS Agent creates task and plans each segment; operator does not fabricate bindings or drive robot actions. |

## Validation

Dedicated GraspNet interpreter successfully loaded the existing baseline checkpoint
and ran inference on a captured observed point cloud. Local source commit and
models/graspnet.py matched the existing transform attestation. No new attestation
scheme or relaxed geometry checks were introduced.

Commands:

    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests examples/forge-skills/pick-place-workflow/tests -q
    /home/yanxu/miniconda3/envs/paos/bin/python -m ruff check examples/forge-adapters/robotwin20/runtime/graspnet_worker.py examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py examples/forge-skills/pick-place-workflow/tests/test_runtime_install_discovery.py examples/forge-skills/pick-place-workflow/tests/test_grasp_propose.py
    git diff --check

The first full run reported 1026 passed, 1 skipped. The isolated GraspNet ranking
regression then passed separately; final combined count is 1027 passed, 1 skipped.
The earlier Python 3.13/environment failures are not evidence of pre-existing code
failures. The PAOS Python 3.12 invocation with script paths and asyncio plugin is
used here. Optional Pillow-dependent worker tests remain skipped in this interpreter.

## Acceptance requirement remains active

Three independent RGB tasks are required, with at least one complete red/green/blue
placement, terminal Actions, post-release retreat and return evidence, an independent
ForgeTaskVerifier result, and a playable cumulative video. Package readiness and
unit tests do not satisfy this requirement. First live GraspNet task:
task_e6bc12008ff64bb9. Artifacts:
/home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260925T211115/run1.

Real baseline inference resamples the point cloud stochastically; the captured
input, checkpoint, source revision and resulting candidates are retained. This
review does not claim identical candidate ordering across independent model runs.
