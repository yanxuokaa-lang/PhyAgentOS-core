# v11.8.0 GraspNet coverage and recovery evidence review

Date: 2026-09-25. Acceptance remains active.

## Findings and dispositions

1. **Blocker: preparation failure loses the request scene.** The public endpoint
   returned scene_revision=unknown after a validated request failed in its provider.
   Task task_803ae1a6cae1449d then built a recovery observation depending on the
   failed prepare record. The trusted scene projector correctly excluded the
   conflicting response, leaving no ready node. Preserve validated request identity
   in all provider-failure responses. No successful checks or motion authority are
   fabricated. Six failure variants now test endpoint-to-context-to-ready recovery.
2. **Major: early score truncation discards useful orientation families.** Offline
   analysis uses the exact run3 observed red cloud and unmodified native Panda
   meshes. A fresh GraspNet inference decoded 1024 real poses: 402 pass support
   clearance and 57 pass observed swept contact checks. All score-top-24 collide;
   the first contact-valid native pose ranks 389. These are no-motion diagnostics,
   not IK/route success, and inference is stochastic.
   GraspNet now offers orientation-diverse budget sampling, selected in its profile:
   keep the highest native score, then maximize approach/closing angular coverage.
   All matrices, scores and dimensions remain original model outputs. Closing-axis
   sign is symmetric. The Adapter keeps normal NMS, then preserves provider order
   while retaining at most ten of the 24 actual proposals. The captured diagnostic
   retains one contact-valid pose after the exact shipped two-stage selection.
3. **Ruled out: a new collision frame or scale defect.** Independent SAPIEN URDF
   loading without simulator steps reproduces the run3 support penetrations.
   Component get_pose equals get_entity_pose here; native mesh scale is one.
   Palm and finger collisions are physical candidate rejections, not a reason to
   alter the robot mesh, support height, margins, or permitted contacts.

## Seven dimensions

| Dimension | Result and scope |
|---|---|
| Architecture integration | Public prepare owns response identity; isolated provider owns sampling; Adapter owns NMS/retention. Coordinator, readiness and Gateway retain their authorities. |
| Recovery/idempotency | Existing recovery sees failed Query evidence with the correct scene. No old receipts edited; no Action reissued. Trial 3 was cancelled through Coordinator after confirming no Actions. |
| Robotics safety | No motion in offline diagnostics. No collision, IK, complete-route, stop or unknown-outcome check relaxed. Sampling is advisory. |
| Configuration/reproducibility | GraspNet-only sampling-policy CLI and profile selection_order; default score order unchanged for other providers. Unique run4 artifacts, source diff, installed versions, same checkpoint and observed inputs retained. |
| Maintainability | Small helper reuses native candidate objects; generic provider order has two explicit choices. No new service, schema, frozen contract or hash mechanism. |
| Observability | Persisted raw diagnostic decoder, per-link support bounds, full contact results and retained native indices. Trial logs and independent final verifier remain the task evidence. |
| AgentLoop autonomy | Regression proves failed prepare can make its refresh node ready through existing trusted context. Live recovery and full RGB completion remain acceptance requirements. |

## Validation

- Focused prepare/context regressions: 77 passed.
- Integrated Adapter/Skill/context suite: 1069 passed, 1 skipped.
- Existing Pillow-dependent perception-worker module remains skipped in PAOS Python.
- Ruff and git diff --check pass; exact commands are in the monthly changelog.
- Raw candidate diagnostic: no motion, no simulator steps, unchanged loaded Panda meshes.

## Acceptance status

Run4 starts Skill 2.7.13 and Node 0.8.0 using robotwin-blocks-ranking-graspnet.
Three prior independent tasks did not reach physical Actions; they are failures,
not RGB successes. Required finish remains three tasks with at least one full
RGB arrangement, terminal acquire/place evidence, release-retreat-return checks,
fresh final observation, independent ForgeTaskVerifier and playable cumulative video.
