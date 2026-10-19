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

The live acceptance still requires a separate controlled run and inspection of
the returned `phase_events`, `feedback_observations`, video artifact, and scene
revision. The previous real pour attempt reached grasp but failed transport /
alignment, so dry-run and fake-engine results must not be reported as a live
pour success.
