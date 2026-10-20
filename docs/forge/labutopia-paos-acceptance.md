# LabUtopia PAOS acceptance

This adapter exposes LabUtopia's existing `PourController` and `StirController`
through the PAOS complete-cycle endpoint.  A task such as “将标签为试剂A的
试剂瓶倒入烧杯” is projected by `project_pour_task()` into the profile-bound
refs `entity://conical_bottle03` and `destination://beaker2`; an Agent does not
provide arbitrary USD prim paths.

## Acceptance layers

1. **Discovery**: the runtime lists `object.pour_cycle` and, for a profile that
   explicitly enables stir, `tool.stir_cycle`. Unsupported controllers remain
   absent or return `unsupported`.
2. **Planning and preflight**: the Agent supplies semantic labels and PAOS
   evidence. Preparation returns `motion_authorized=false`, binds the current
   scene revision/frame/calibration, and creates one preparation/assignment
   record. The caller task id is checked before execution.
3. **Single public Action**: one `object.pour_cycle` or `tool.stir_cycle`
   invocation owns all seven internal phases. The adapter never creates nested
   Agent invocations and the PAOS possession object remains the only lifecycle
   state owner.
4. **Measured settlement**: success requires observed acquire, transport,
   process, reorient/exit, stow, release, and retreat events, valid feedback,
   the requested process goal, changed scene revision, artifact evidence, and
   an empty possession on support. A request parameter is not completion proof.
5. **Failure closure**: stale frame/calibration, wrong task ownership,
   unsupported operation/parameter, missing feedback, or a failed transport /
   process phase cannot produce `succeeded`. Live exceptions settle as
   `unknown` with the world-change state preserved for reconciliation.

For `stir_cycle`, the entity reference (`/World/glass_rod`) and the control /
feedback prim (`/World/glass_rod/Cylinder`) are separate profile fields. The
feedback samples use the control prim, and process completion additionally
requires measured container alignment, radius progress, the configured hold
duration, and at least 90% of the configured stir turns. The controller then
executes the existing LabUtopia place/release/retreat path; PAOS settles
`stow`, `release`, and `retreat` only from the post-release support observation.

## Dry-run versus live

`LabUtopiaCycleClient` defaults to `allow_live=False`. In this mode its
capability declaration is dry-run only and `start()` refuses motion. A live
Isaac Sim run must explicitly construct the client with `allow_live=True`, use
the LabUtopia profile, accept the Isaac Sim EULA, and run the worker in the
Isaac Sim Python environment. The no-motion tests use a fake engine only to
verify PAOS lifecycle wiring; they are not evidence that the real Franka task
has succeeded.

## Verification

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=examples/forge-skills/pick-place-workflow/src:examples/forge-adapters/isaacsim_lab/src \
pytest -q examples/forge-adapters/isaacsim_lab/tests/test_paos_integration.py
```

The controlled RTX 5060 Ti + Isaac Sim 5.1 pour run remains the accepted live
success.  A repaired stir worker run produced measured feedback and a video,
but PAOS correctly rejected the process because the real tip path did not meet
the requested geometry:

- result JSON: `/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.json`;
- video: `/home/yanxu/LabUtopia/outputs/paos-generic-cycle/result-1053288-509535575336321.mp4`;
- 1,404 feedback observations and 1,403 video frames;
- acquire and transport completed; process was `failed/stir_observation_not_qualified`;
- measured process tip radius was about `0.0033-0.1003 m` against the requested
  `0.009 +/- 0.002 m`, so reorient/stow/release/retreat remain unknown.

This is an evidence-bounded live failure, not a successful stir claim.  The
remaining fix belongs in LabUtopia's controller end-effector reference/IK
target, after which the same PAOS profile must be rerun.
