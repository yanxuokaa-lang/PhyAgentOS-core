# v11.7.14-v11.7.15 GraspNet integration review

Date: 2026-09-25. Scope: public candidate geometry, provider axes/depth,
serialized planner memory lifecycle. Acceptance is still active.

## Findings and repairs

1. **Blocker — public producer/consumer mismatch.** GraspNet returned valid optional
   width/height/depth, but the public proposal validator rejected all extra fields.
   v11.7.14 adds the shared provider-neutral geometry schema to proposal and prepare,
   validates finite positive metric dimensions, and retains rejection of unknown fields.
   Task task_5117890e1fbf42d5 confirms nine real candidates reached preparation.
2. **Blocker — inconsistent grasp axes.** Native GraspNet X is approach and Y closes.
   The identity provider transform treated Z as approach in the Panda adapter.
   v11.7.15 rotates provider axes into canonical Z-forward/Y-closing, preserving
   the center and updating the existing transform attestation. No synthetic grasps.
3. **Blocker — wrong native target conversion in depth adaptation.** Overwriting
   reference_distance with tip + bias - depth made the apparent round trip use a
   different reference from RoboTwin's actual fixed 0.12 m conversion. The fingertip
   was 40 mm farther back along the approach axis. Keep that reference fixed and
   use hand_to_contact = tip - depth; target_to_contact = reference - bias + hand_to_contact.
   Independent native-conversion tests cover two orientations and four depths.
4. **Major — cross-stage GPU starvation.** After run2 preparation the simulator/planner
   process occupied 6.93 GiB; a no-motion LocateAnything startup failed allocating
   the last 44 MiB. Reclaim only unreferenced Python objects and unused CUDA allocator
   cache at serialized observe/contact/route Query exit. Live planner tensors, world
   state and Action ownership persist. Live post-planning perception remains to verify.

## Seven review dimensions

| Dimension | Evidence and disposition |
|---|---|
| Architecture integration | Provider frame matrix remains in Adapter profile; PAOS Core only accepts generic optional metric geometry. Runtime owns memory and robot state. |
| Recovery/idempotency | Memory cleanup executes on successful and failed Queries; same world is retained. Action invocation/status/reconciliation unchanged. Run2 had no Actions. |
| Robotics safety | Independent fixed-offset round trip; no changed collision mesh, IK limit, margins, admission or motion authorization. Query serialization rejects active movement. |
| Configuration/reproducibility | 24 real scored proposals before adapter NMS, at most 10 retained. GraspNet profile and existing attestation agree. Run-specific inputs/artifacts retained. GraspNet resampling is stochastic. |
| Maintainability | Two existing frame parameters now retain separate physical meanings; new tests compare to native conversion rather than repeating the old formula. |
| Observability | Query cleanup logs allocated/reserved CUDA bytes. OOM diagnostic and per-candidate rejection artifacts retained. Run2 session metadata corrected to actual historical identity. |
| AgentLoop autonomy | Coordinator, selected argument projection and Action control remain unchanged. Repeated top-level wrapper arguments are still an observed concern; their exact underlying model tool calls are not retained in the parent session log. No unsupported root-cause claim. |

## Validation

- Public geometry repair: 146 focused tests; full Adapter/Skill 1037 passed, 1 skipped.
- Frame/depth repair: 45 focused tests; then full suite 1045 passed, 1 skipped.
- Integrated frame/depth/resource lifecycle: 1052 passed, 1 skipped in 13.44 seconds.
- The skipped existing perception-worker module needs Pillow in the PAOS interpreter.
- Same-load LocateAnything startup diagnostic reproduced CUDA OOM; it is not motion evidence.

Command:

    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src /home/yanxu/miniconda3/envs/paos/bin/python -m pytest -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests examples/forge-skills/pick-place-workflow/tests -q

## Real acceptance status

Root: /home/yanxu/robotwin20-runtime/artifacts/rgb-graspnet-acceptance-20260925T211115

- Run1 task_e6bc12008ff64bb9: failed at invalid_candidate before motion.
- Run2 task_5117890e1fbf42d5: real perception and GraspNet succeeded; all nine
  candidates failed contact/route qualification. Recovery observation succeeded;
  subsequent proposal-model startup failed due to the reproduced resource condition.
- Run3: pending corrected deployment. No RGB completion or video success is claimed.

Acceptance requires three independent tasks, at least one full RGB placement,
terminal Actions with retreat/return evidence, independent ForgeTaskVerifier success,
and a playable cumulative video. The repairs and unit tests alone do not satisfy it.
