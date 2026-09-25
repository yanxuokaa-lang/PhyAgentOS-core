# GraspGen RGB acceptance — amended execution objective

用户要求 / User requirement (2026-09-24): 抓取位姿必须由本次实时感知、分割所得对象点云驱动 GraspGen 生成。不得使用 Oracle 模板旋转候选，也不得在失败后自动切换模板。
Grasp poses must originate from GraspGen inference on current segmented observation point clouds. Oracle templates and automatic template fallback are excluded.

## Stage 1: one complete relocation

1. A fresh task obtains scene.observe, scene.understand, capabilities, scene.bind and task.goal through the normal Coordinator lifecycle.
2. Persist sensor observation, segmentation/object-cloud references and GraspGen candidate provenance. Retain ten genuine candidates for manipulation.prepare; record actual counts and diagnose shortages without padding.
3. Coordinator resolves candidate arrays from persisted tool records. The model does not copy geometry, invent opaque references, or rebuild selected arguments.
4. Run manipulation.prepare and select an admitted candidate through the normal AgentLoop. Then execute object.acquire and object.place, each to terminal settlement.
5. Verify release, retreat away from destination, return to the selected arm's action-start end-effector pose, renewed observation and recorded video. Unknown Actions require reconciliation of the same invocation, never blind resubmission.

Only passing this real relocation qualifies the system to start Stage 2. Unit tests alone do not qualify.

## Stage 2: three independent RGB tasks

Run three independent tasks with current observations and fresh task identities. At least one must place all three blocks in RGB order, retain cumulative video and pass ForgeTaskVerifier. Record all three outcomes; genuine physical failures are allowed, software deadlocks are investigated and repaired. No 50-task expansion.

## Ownership and remaining simulation scope

The grasp provider is selected from the adapter grasp profile independently of route geometry. The supplied graspgen profile names GraspGen and samples 24 real candidates and retains at most ten after existing score/NMS filtering. Sampling and retained counts are configured separately; shortages are reported without padding. Benchmark destination_ref may still originate from task.goal. The acceptance profile uses observed route/collision geometry. Benchmark destinations remain task-specification input, while simulation dynamics and Action monitoring remain Runtime-owned. This stage is simulation execution, not hardware acceptance.

PAOS remains gpt-5.6-sol/high. Preserve architecture, extension boundaries, developer guidance, Coordinator ownership and AgentLoop recovery. The existing external goal has an unfinished objective and the goal tool cannot edit its text; this document records the user's supplemental acceptance requirements without falsely completing that goal.

## Observed geometry acceptance profile (2026-09-25)

Use `robotwin-blocks-ranking-graspgen` for the requested full-chain run.
Its explicit profile uses observation-owned route/collision geometry,
benchmark task destinations and monitored simulation Actions. The old oracle
profile is retained for diagnostic comparisons and is not a passing result for
this acceptance. Generate all 24 GraspGen candidates before canonicalization,
deduplication and filtering retain at most ten. Run the normal Coordinator and
AgentLoop, retain each invocation and require the final verifier/video evidence.
