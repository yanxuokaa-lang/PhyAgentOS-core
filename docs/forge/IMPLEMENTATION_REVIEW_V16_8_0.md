# v16.8.0 implementation review / 实现复核

## Findings and disposition / 问题与处理

1. **Major, fixed — continuing to squeeze after invalid bilateral contact.**
   `phase_motion.py` now rejects qualified-body bilateral contact with a bad
   attachment transform immediately. Regression proves one control step then
   measured hold, with no lift or continued zero-target squeeze.
2. **Major, fixed — smoothing could change the collision path.** Stage-continuous
   samples and every swept joint interval run through existing limits/workspace/
   collision checks before readiness. Runtime consumes those exact samples;
   changed control period fails before a command. Tests inject an intermediate
   collision, workspace violation and joint-limit violation.
3. **Major, fixed — authored physics was not runtime physical evidence.** Apply
   session opinions before reset/capture, then independently read PhysX mass,
   COM and inertia. Native no-motion startup/reset passes for all eight vessels.
   Material bindings remain explicitly authored evidence; effective contact
   coefficients and grip retention are not inferred from configuration.
4. **Major, fixed — finger target and transient contact were lost at boundaries.**
   Bounded closure, stable contact settling, transient-loss stop, preserved finger
   aperture on later entry and per-substep sensor contact vectors now have tests.
   Cancellation keeps existing stop/settlement behavior and unregisters callbacks.

No unresolved Blocker/Major implementation finding in the reviewed scope. This
is code acceptance plus native no-motion evidence, not live-grasp acceptance.

## Architecture / 架构

- Tier C-Safety; runtime-motion and implementation-review skills applied.
  PAOS AGENTS and developer/manipulation/planning/speed-limit guides are the
  authority. Hephaestus-specific workflow docs are absent in this repository.
- Generic owner: AgentLoop selects opaque qualified refs; Skill projects domain
  parameters; Runtime/Coordinator own admission, cancellation, reconciliation,
  recovery and settlement. None acquires USD or force/joint parameters.
- Adapter owner: final-stage session opinions, private configuration, measured
  physics receipts, route retiming, contact commands and physical feedback.
  `physics_probe` exercises the existing backend; it is not an alternate executor.
- Replacement: optional profile leaves existing deployments without physics
  override intact; alternative USD object/robot paths pass the same module tests.
  Existing subtask-executor tests cover unchanged qualified-reference handoff.
- Evidence freshness: physics applies before reset and capture; readiness links
  the session receipt. Loaded sessions reject profile switching. Old recorded
  routes are used only for offline timing estimates, never live replay.
- Safety boundary: existing motion validation/stop path, no generic new gate or
  hash. Concrete failure is continuing closure after physical displacement/loss;
  Git/types/static tests cannot stop an already running actuator.

## Validation and limits / 验证与边界

- Full Adapter + existing Skill subtask executor: **450 passed, 2 skipped**;
  changed Python files pass Ruff and `git diff --check` is clean.
- Native USD physics module: 10 tests pass, including two cases skipped in the
  default environment because pxr is absent. Synthetic controller coverage proves
  mechanism/failure contracts, not actual physical tracking.
- Native Isaac probe: eight masses ~0.1 kg, valid inertia/COM, readback leaves
  joints/time unchanged, reset preserves physics/initial joints; zero commands.
  Receipt: physics-probe/202c33511beb4a099fd157965af89e8e.json under
  `out/lab-contact-timing-20261102-r1/artifacts/labutopia/`.
- Native log includes existing scale/material and CPU-particle errors. Rigid
  physics readback passed; fluid simulation and image quality were not accepted.
- Offline recorded-route timing falls from 50.683/51.300 to 22.366/24.167 s for
  R03/R05 arm movement before closure; geometric detour unchanged, no new tracking
  or full-route safety claim. Fresh preparation must qualify interpolation.
- No new physical grasp/pour/stir execution, video, or hardware proof. Explicit
  mass/friction/force assumptions still require fresh contact validation. R03
  insertion geometry may still fail, now stopped at the existing drift bound.
- Exact commands, diagnostics and troubleshooting branches are in
  `.task/labutopia-contact-and-timing-repair-20261102.md`.
