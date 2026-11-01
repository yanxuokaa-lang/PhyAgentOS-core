# LabUtopia R03 grasp candidate exhaustion diagnosis

## Runtime evidence

- No-motion run: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r3/`
- Task: `task_9616f2b247084614`
- Observation scene: `labutopia-tabletop-rod-rack-v1:fe5b02fc9ce549718137d8d2b19ec42a:0`
- R03 point cloud: `artifact://labutopia/object-point-cloud/20a0cd12ef4e46aeb77356c0479d1a72.npy`
- R03 proposal artifact: `artifacts/labutopia/grasp-predictions/e3bdc0863d384360a490c759f61c34d8.json`
- Motion state: `simulated_motion_enabled=false`, `world_change_started=false`, `possession_state=empty`.

## Direct failure

R03 reached real Isaac `manipulation.prepare`, but all 32 retained candidates were rejected before motion. The dominant failure was `gripper_aperture_exceeded`; the remaining candidates failed self-collision, route/payload collision, or inverse kinematics. The preparation path correctly stopped with known zero motion.

The composed Franka finger-joint limits expose a maximum physical opening of approximately `0.080000 m`. The retained R03 set contained only 6 candidates at or below that width; none passed all later checks. Width is not an AgentLoop semantic and is not a reason to hard-code a grasp pose. It is provider evidence consumed by embodiment preparation.

## Same-point-cloud model diagnostic

A separate no-motion GraspNet inference used the same saved R03 point cloud, the same checkpoint, a deterministic seed, `max_points=12000`, `score_threshold=0.02`, and a 512-candidate output budget. It did not start Isaac, IK, a controller, or any Action.

- decoded: `690`
- canonicalized: `649`
- retained for analysis: `512`
- width range: `0.041746 m` to `0.100000 m`
- candidates with width `<= 0.080001 m`: `87`
- candidates with width `<= 0.070001 m`: `47`
- candidates with width `<= 0.060001 m`: `19`

Therefore the model produces many narrower alternatives. The current loss occurs at bounded sampling/retention: worker orientation diversity and Provider `selection_order=provider` preserve rotation families but do not explicitly preserve width and spatial coverage. A small set of wide/colliding families can consume the 32-candidate public budget.

## Ownership decision

- AgentLoop remains unchanged: it selects and records opaque references and never sees coordinates, USD paths, or gripper limits.
- Grasp Provider is the correct repair boundary for bounded candidate coverage because it owns translation of replaceable model output into provider-neutral proposals.
- Isaac preparation remains the final authority for composed-aperture, frame, IK, collision, payload, and workspace admission.
- No candidate is promoted to success by the new sampling policy; it only prevents viable native model candidates from being discarded before preparation.

## Planned correction

1. Request the existing supported maximum native sample pool (`512`) from the GraspNet worker.
2. After normal validation and NMS, select a bounded subset using position, approach direction, sign-symmetric closing direction, and grasp width diversity while retaining original score and geometry.
3. Keep the public result bounded (`64`) and deterministic.
4. Run the full no-motion AgentLoop route again. Only a candidate passing aperture, IK, collision, payload, workspace, and frame checks may authorize the subsequent simulated Action.

## Non-solutions

- Do not set an R03/R04 grasp pose in the prompt, PlanGraph, AgentLoop, or task definition.
- Do not replace current-world geometry with manifest wrapper translations or configured XY coordinates.
- Do not skip aperture, IK, collision, workspace, or same-capture evidence checks.
- Do not interpret a successful grasp preparation as liquid transfer or chemistry completion.

## r5 geometry-diverse rerun

- No-motion run: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r5/`
- Task: `task_cc9453d96d304e67`
- R03 proposal: `artifacts/labutopia/grasp-predictions/d7d4c4ed580f4da1b0066ae7d3a9973c.json`
- Provider funnel: `512` canonicalized candidates, `64` retained by deterministic geometry-diverse selection.
- Embodiment aperture: `24` retained candidates were at or below the composed Franka `0.080000 m` opening.
- Preparation failures: `40 gripper_aperture_exceeded`, `12 route_collision`, `9 self_collision`, `3 inverse_kinematics_failed`.
- Representative environment conflicts: hand/fingers against the R03 mesh, `panda_link5` against adjacent R04, hand/link6 against the table, and non-adjacent Franka link overlap.
- Safety outcome: `simulated_motion_enabled=false`, `world_change_started=false`, `outcome_known=true`, `possession_state=empty`; R04 and stirring were not started.
- The later LLM `403 insufficient_user_quota` occurred during Action reconciliation. It did not cause or invalidate the already-persisted R03 preparation result.

## Updated diagnosis

The candidate-width coverage repair worked, but it did not produce an admissible R03 route. The next investigation boundary is the Isaac Adapter and authored scene configuration, not AgentLoop:

1. Confirm the configured seven arm joints and two gripper joints are applied after world initialization and every task reset.
2. Capture the measured joint vector, TCP pose, wrist-camera world pose, and a passive tabletop frame before any preparation.
3. Verify `provider_from_tcp`, `world_from_camera`, GraspNet approach direction, and the pre-grasp construction use one consistent convention.
4. Compare the current straight-line pre-grasp route with a parameterized, collision-checked alternative initial posture or approach distance through no-motion preparation only.
5. Keep every aperture, IK, self-collision, environment-collision, payload, workspace, freshness, and frame check authoritative. No heuristic ranking may promote a failed route to success.

The current authored home state is `[0.0, -0.7853981634, 0.0, -2.3561944902, 0.0, 1.5707963268, 0.7853981634]` with gripper `[0.04, 0.04]`. It is already applied by the Adapter before and after task reset, so the previous “initial state is not set” hypothesis is no longer supported. Whether this home state is suitable for the R03/R04 layout remains a no-motion measurement question.

## Final-composed mesh point-cloud correction

- Probe: `out/labutopia-truth-mesh-cloud-probe-20261101-r1/`.
- The former simulator-truth object cloud cropped the rendered scene cloud by the final world AABB. For transparent R03 this admitted approximately `9,116` support-plane points at `z≈0.713886 m`, while the captured cloud stopped at `z=0.8316 m` although the final-composed USD mesh reached `z=0.9462 m`.
- The corrected provider projects final-composed USD mesh vertices into the current camera capture when mesh evidence is available. R03 now contains `1,214` object points spanning `z=0.712386–0.946214 m`; GLASS_ROD contains `66` points spanning `z=0.718386–0.968386 m`.
- Mesh-derived object evidence remains tied to the same observation, scene revision, frame, and calibration; bounds-only legacy state retains the rendered-depth fallback. No manifest coordinate or configured grasp pose is introduced.

## No-motion route probes after mesh correction

### Direct route (`r1`)

- Probe: `out/labutopia-r03-mesh-cloud-preparation-probe-20261101-r1/`.
- R03 produced 64 retained grasp candidates; 37 passed task-affordance qualification.
- Preparation failures were `20 route_collision`, `13 gripper_aperture_exceeded`, `2 self_collision`, and `2 inverse_kinematics_failed`.
- Seventeen collision failures referenced R03 itself. The current TCP-to-pre-grasp interpolation crossed the selected source or neighbouring scene geometry.

### Fixed overhead route (`r2`)

- Probe: `out/labutopia-r03-mesh-cloud-preparation-probe-20261101-r2/`.
- The route changed to `open → transit_raise → transit_cross → approach → grasp → close → lift` with a fixed `0.12 m` clearance.
- Source-crossing collisions decreased, but the fixed high route exposed new embodiment-specific failures including `panda_link5`/`panda_hand` and `panda_link1`/`panda_link6` self-collisions, neighbouring R01/R02 collisions, table collisions, IK failures, and one lift-time `payload_robot_collision`.
- The result remained `status=unavailable`, `failure_code=no_admissible_grasp`, `motion_authorized=false`; no Action was started.

## Next correction boundary

The fixed overhead route is not a valid global policy. Acquire preparation must search a small configured set of transit clearances inside the Isaac Adapter, qualify each complete route with the existing embodiment checks, and select only a fully admissible route. The clearance is Adapter-private route metadata; it does not belong in AgentLoop, PlanGraph, the public grasp contract, or the task prompt. If every configured clearance fails, preparation remains unavailable and motion remains disabled.

## Clearance-search rerun and task-affordance gap

- Probe: `out/labutopia-r03-mesh-cloud-preparation-probe-20261101-r3/`.
- The Adapter tried all configured acquire transit clearances (`0.04`, `0.08`, and `0.12 m`) for every task-affordance-qualified candidate. No route passed all embodiment checks; the result stayed `status=unavailable`, `failure_code=no_admissible_grasp`, `motion_authorized=false`, and no Action or controller command was started.
- Candidate-level failures were `18 route_collision`, `13 gripper_aperture_exceeded`, `3 self_collision`, `2 inverse_kinematics_failed`, and `1 payload_robot_collision`. Failures occurred mainly in `approach` (`18`), with additional `grasp` (`4`), `transit_cross` (`2`), and `lift` (`1`) failures.
- The clearance search therefore works as designed; transit height is no longer the immediate abstraction gap.
- The same-capture final-composed R03 mesh spans approximately `z=0.712386–0.946214 m`, but task-affordance admitted many grasp centers at `z≈0.712–0.728 m`. Those candidates collide with the table, fingers, or bottle at approach/grasp time.
- `_qualify_bottle_grasp()` currently rejects candidates above the opening clearance and below the observed axial minimum, but it does not require a positive axial clearance above the support end. A candidate immediately above the lowest mesh vertices can therefore pass the Provider even though it is not a useful bottle-body grasp.

## Planned task-affordance correction

1. Keep the correction inside `LabGraspTaskAffordanceProvider`; AgentLoop continues to select opaque references and does not receive coordinates, USD paths, or bottle-specific poses.
2. Derive a support-end exclusion band from the observed bottle axial extent and the candidate's reported gripper contact geometry. Do not encode R03/R04 coordinates or a fixed grasp point.
3. Reject support-end and opening-end candidates before preparation, while leaving final aperture, IK, self-collision, environment-collision, payload, workspace, and frame admission in Isaac preparation.
4. Add no-motion contract tests for support-end rejection, opening rejection, middle-body acceptance, same-capture identity, and threshold validation.
5. Rerun the real R03 no-motion preparation. Only a fully admitted preparation may permit the later Agent Action path.

## r6 task-affordance selection leakage

- No-motion run: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r6/`.
- Task: `task_a413a49677c04a72`.
- The Task-Affordance Query selected `grasp-affordance-set://22b4108e2bbd4421822466d95e7edd0c`, `grasp-affordance://3f0f8b4d6a3b4df78f7f3ac1c07562cd`, and `candidate://simulator-truth-R03/7ba39258ddf1496782d1e81c029e296c-59` from the same capture.
- The subsequent Action record retained `affordance_selection=task_qualified` and the selected opaque grasp reference, but the internal `manipulation.prepare` failure enumerated the original `-0` through `-63` GraspNet candidates. Provider-rejected support-end candidates therefore re-entered embodiment checks.
- Safety outcome remained correct: `world_change_started=false`, `possession_state=empty`; R04 and GLASS_ROD were not started.

## Candidate-set ownership correction

1. AgentLoop continues to select and forward opaque references only; it does not inspect grasp coordinates, geometry, USD paths, or gripper limits.
2. Task-Affordance Provider remains the authority that qualifies grasp/process combinations for the task and capture.
3. For `affordance_selection=task_qualified`, the subtask execution boundary must project only the selected qualified grasp into `manipulation.prepare.candidates`. It must fail before the Provider call when the selected reference is absent from the same-capture binding.
4. Isaac preparation remains the final authority for aperture, frame, IK, self-collision, environment collision, payload, workspace, and route admission, but may not recover candidates excluded by the upstream task-affordance selection.
5. Existing alternative-candidate recovery remains available only for routes that did not declare task-affordance qualification. Supporting multiple qualified alternatives later must resolve them from the opaque task-affordance candidate set, never from the raw GraspNet set.

This change does not add a hash, frozen contract, or new public schema. The concrete failure is semantic leakage across an existing safety boundary; ordinary types and raw binding validation cannot prevent it because both the selected reference and the raw candidates are individually valid while their combination violates candidate-set ownership.

## r7 selected-only correction result

- No-motion run: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r7/`.
- Task: `task_404dc9a3af234a63`.
- The Action record now contains `affordance_selection=task_qualified` and selected grasp `candidate://simulator-truth-R03/b19d0c7f5ab0470891fb9f2a89d6656b-45`.
- Internal `manipulation.prepare` rejected exactly that one candidate with `payload_robot_collision` during lift for all configured clearances. It did not reintroduce the other 63 raw GraspNet candidates.
- Safety outcome: `simulated_motion_enabled=false`, `controller_outcomes=[]`, `world_change_started=false`, `possession_state=empty`; R04 and stirring were not started.

## Qualified-set alternative recovery plan

The same task-affordance Query already returned eight qualified combinations from one opaque candidate set. The preparation receipt currently projects only the selected combination, so the Action cannot try other already-qualified grasps after an embodiment-specific route failure.

1. Task-Affordance preparation will revalidate the selected combination and current candidate set, then return an ordered list of unique qualified grasp refs with the selected ref first.
2. AgentLoop will continue to copy opaque references only. It will not inspect geometry or choose a replacement grasp inside the Action.
3. Subtask execution will resolve that ordered list against the unchanged same-capture `binding.grasp_candidates`; any missing, duplicate, out-of-set, or selected-not-first state fails before the Adapter Provider call.
4. Isaac preparation will iterate only the resolved qualified candidates and retain its existing aperture, IK, collision, payload, workspace, and frame authority.
5. Non-task-affordance relocate/grasp routes keep their existing raw bounded candidate recovery behavior.

This is a justified public contract extension because ordered qualified grasp references are stable cross-provider task semantics required by both the Task-Affordance Provider and the generic Action preparation boundary. Provider-private geometry, USD paths, scores, and robot constraints remain private.

## r8 qualified-set recovery and implementation-review finding

- No-motion run: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r8/`.
- Task-Affordance Preparation projected the selected grasp first and then the remaining qualified grasp references from the same candidate set. Action preparation no longer recovered from the raw 64-candidate GraspNet binding.
- Implementation review found one Major issue for stirring: two qualified combinations may use the same graspable rod but select different process endpoints, so projecting every qualified grasp without preserving the selected combination's `process_feature_refs` could pair an alternative grasp with the wrong working end.
- Fix: `LabGraspTaskAffordanceProvider.validate_selection()` now revalidates every combination against the current same-capture grasp and process-feature sets, but includes an alternative grasp only when its `process_feature_refs` exactly match the Agent-selected combination. The selected grasp remains first and duplicate grasp references are removed without inspecting geometry in AgentLoop.
- Regression coverage includes selected-first uniqueness, stale/missing evidence, Provider-rejected raw candidates, ordinary non-task-affordance compatibility, and stir endpoint compatibility.

## r9 final no-motion evidence

- No-motion run: `out/lab-fullchain-truth-20261101-r03-r04-no-motion-r9/`.
- Task: `task_114477e266344f0b`.
- Task-Affordance Preparation returned these eight ordered qualified references: `-45`, `-5`, `-32`, `-25`, `-31`, `-59`, `-38`, `-36`; `-45` was the Agent-selected first reference.
- Isaac `manipulation.prepare` returned `rejected_candidate_refs` with the same eight references in the same order. No candidate from the remaining raw 64-candidate GraspNet binding re-entered preparation.
- Failure classes were `payload_robot_collision`, `gripper_aperture_exceeded`, `inverse_kinematics_failed`, and route/self-collision. These remain Adapter-owned embodiment outcomes; the candidate-set ownership repair does not override or reinterpret them.
- Safety outcome: task `failed`, `simulated_motion_enabled=false`, `controller_outcomes=[]`, `world_change_started=false`, `outcome_known=true`, and `possession_state=empty`. R04 and GLASS_ROD were not started.

## Final architecture assessment

- AgentLoop owns semantic selection, lifecycle, settlement, and copying opaque references from the unique direct predecessor receipt. It does not inspect grasp geometry, USD paths, coordinates, joint limits, or collision details.
- Task-Affordance Provider owns qualification of grasp/process combinations and the ordered qualified alternative set for the same capture and selected process features.
- The subtask boundary validates selected-first ordering, uniqueness, and membership in the unchanged observation binding before calling the Adapter.
- Isaac Adapter remains the only owner of final-world transforms, aperture, IK, self-collision, environment collision, payload, workspace, route search, execution feedback, and stop behavior.
- No hash, frozen contract, shadow scheduler, collision bypass, or automatic motion retry was added. The next blocker is scene/route feasibility for R03, not AgentLoop candidate recovery.
