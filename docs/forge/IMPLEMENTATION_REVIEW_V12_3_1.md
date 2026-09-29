# v12.3.1 Seven-Dimension Implementation Review

Date: 2026-09-30

Scope: provider-neutral multi-view scene understanding deployment, local Qwen
vLLM compatibility, and retained LocateAnything/SAM2 worker lifecycle.
Safety mode: read-only perception validation; no `object.acquire`,
`object.place`, or other physical Action was executed.

## Findings

### Blocker

None open.

### Major fixed before acceptance

1. **Perception timings were invisible in the default Runtime log.**
   `JsonlProcessWorkerClient` already emitted startup/wake/request/sleep/shutdown
   timings, but the module logger remained below INFO in the persistent Host.
   `persistent_host._configure_operational_logging()` now exposes only the
   dedicated timing logger and installs the handler idempotently; it does not
   increase global log verbosity.

2. **Request release and terminal shutdown had ambiguous ownership.**
   CPU hibernation intentionally keeps worker processes alive after a request,
   but the Host did not explicitly own terminal cleanup. `SingleViewPerceptionInference`
   now provides `shutdown()`, provider adapters forward terminal shutdown to the
   process client, and `PersistentHost.close()` closes owned perception resources,
   lifecycle managers, and the persistent client even when an earlier close fails.

3. **The optional additional-camera extension broke minimal legacy profiles.**
   Some worker fixtures and existing profile consumers did not contain
   `additional_static_cameras`. All consumers now default the optional field to
   an empty collection, while runtime-profile validation still rejects malformed
   identities, non-finite vectors, unknown keys, and native camera-name conflicts.

No open Major remains.

### Minor and residual risks

- The first LocateAnything request remains a real cold start (`91.394 s` model
  startup; `111.435 s` total `scene.understand`). The change removes repeated
  cold starts; it does not hide or fake the initial load.
- Hibernation retains approximately `9.5 GB` LocateAnything RSS and `2.6 GB`
  SAM2 RSS on CPU. This is an explicit profile tradeoff, not the default worker
  behavior.
- Normal Runtime stop terminates both retained perception workers. Dora may still
  report the outer persistent Host as SIGKILLed after its existing stop deadline.
  That pre-existing Dora/persistent-world shutdown-budget issue is not fixed by
  this release and must not be reported as resolved.

## 1. Architecture integration

Result: **Pass**.

- `ProcessWorkerConfig.hibernate_on_release` is a generic, opt-in worker lifecycle
  capability and defaults to `false`; it is not tied to RGB sorting or RoboTwin
  task semantics.
- LocateAnything and SAM2 implement the same `sleep`/`wake` worker protocol.
  The process client owns transport serialization; `SingleViewPerceptionInference`
  owns the composition; `PersistentHost` owns terminal resource shutdown.
- The runtime profile owns the extra rendered-camera configuration. The Adapter
  modifies an in-memory copy of the third-party embodiment configuration and does
  not patch the RoboTwin checkout.
- Qwen remains the semantic provider; LocateAnything/SAM2/depth remain metric
  evidence providers. None of them authorizes motion.

## 2. Recovery and idempotency

Result: **Pass**.

- Repeated `release()` while sleeping is a no-op; the next request wakes and reuses
  the same PID. Explicit `shutdown()` terminates the process, resets client state,
  and allows a later request to create a new generation.
- Sleep, wake, request, and shutdown protocol failures abort the affected worker
  and fail closed. Late stdout/stderr readers remain generation-scoped.
- `PersistentHost.close()` attempts all owned resources and managers before
  surfacing the first close failure, preventing one failing resource from skipping
  cleanup of the rest.
- No successful Tool invocation is replayed or synthesized by this lifecycle.

## 3. Robotics safety

Result: **Pass**.

- Validation was limited to `scene.observe` and `scene.understand`; no physical
  Action, grasp proposal, IK admission, collision admission, or motion command was
  executed.
- Qwen, LocateAnything, and SAM2 retain serial GPU ownership. A provider lifecycle
  failure produces an unavailable Query result rather than stale geometry or a
  motion-capable fallback.
- Freshness, calibration, scene identity, workspace, collision, IK, planning
  admission, Gateway, Coordinator, and terminal-result gates were not relaxed.
- Tool contexts remain explicit that perception is Query-only and does not grant
  motion authorization.

## 4. Configuration and reproducibility

Result: **Pass**.

- The shipped perception profile explicitly enables hibernation for only the two
  compatible local vision workers. Existing profiles inherit `false`.
- The deployed Qwen service is loopback-only, accepts two images, uses xgrammar
  with arbitrary whitespace disabled, supports sleep mode, and is isolated from
  the Clash proxy through loopback bypass.
- Installed release: Skill `pick-place-workflow 2.9.0`; Node
  `robotwin20_persistent_host 0.8.15`.
- Node archive SHA-256:
  `5fa1d5afdb9aca2d4162a2e5464e9eeee44a9ac6e6e4f3291c0fa7ddee65420e`.
- Skill bundle SHA-256:
  `2fff4ca06a74a6f0ee8d47a82aff9fb644664a0304a265dfe3b6e1a7b025fb3b`.

## 5. Maintainability

Result: **Pass**.

- Lifecycle commands are implemented once in `worker_protocol.py` and consumed by
  the generic process client; model-specific workers only implement model movement
  and cache release.
- Request-level `release()` and Runtime-level `shutdown()` are separate named
  operations, making ownership visible instead of relying on destructors or process
  exit side effects.
- Configuration validation rejects unsupported keys and invalid types while
  preserving compatibility for absent optional fields.
- Focused tests cover PID reuse, explicit terminal shutdown, sleep failure,
  timing visibility, Host close ordering, profile compatibility, and real model
  CPU/GPU transitions.

## 6. Observability

Result: **Pass**.

- Runtime logs expose `startup`, `wake`, `request`, `sleep`, and `shutdown`
  elapsed time for each isolated worker without enabling global DEBUG logging.
- The live benchmark separates semantic inference, model startup, model wake,
  per-entity inference, and sleep costs. This identifies the first LocateAnything
  checkpoint load, not Qwen, as the cold-path bottleneck.
- Cold `scene.understand`: `111.435 s`; warm: `14.320 s`; improvement: about
  `7.8x`.
- Both calls returned `status=available`, 5 entities, and 20 derived geometry
  artifacts.

## 7. AgentLoop autonomy

Result: **Pass**.

- The Agent still selects provider-neutral Tools through Coordinator/Gateway
  context; model lifecycle is not exposed as an Agent-authored Action or plan node.
- Provider readiness and unavailable failures remain observable to the AgentLoop,
  while service start/restart remains operator-owned. The loop does not retry an
  unchanged infrastructure failure or refresh observations to repair a provider.
- Installed Runtime status reports all ten Tool contexts ready. This proves the
  deployed Tool surface is available; it does not claim a completed RGB task or
  authorize motion.

## Verification evidence

- Final lifecycle-focused suite: `75 passed` (the earlier narrower lifecycle
  subset was `56 passed`).
- Full relevant Adapter and Skill suite: `1112 passed, 1 skipped, 3 deselected`.
- The three deselected tests also fail on clean `HEAD` and are unrelated baselines:
  `test_action_readiness_gate.py::test_place_action_reuses_the_same_reviewed_gate_and_acquire_identity`,
  `test_persistent_task_video.py::test_engine_records_intermediate_execution_frames`, and
  `test_full_workflow.py::test_full_workflow_uses_one_agent_task_and_creates_episode`.
- Installed Skill status: running profile `robotwin-blocks-ranking-graspnet`,
  Gateway ready, all ten Tool contexts ready.
- `paos forge-node verify pick-place-workflow robotwin20_persistent_host` verifies
  the installed `0.8.15` executable against the Skill lock.

## Acceptance conclusion

The implementation satisfies the original general requirement: synchronized
multi-view semantics and possession-aware scene state remain provider-neutral,
and repeated perception no longer reloads LocateAnything/SAM2 checkpoints after
every request. It preserves PAOS ownership boundaries, fail-closed robotics
semantics, and AgentLoop Tool abstraction without adding RGB-arrangement-specific
logic. There are no open Blocker or Major findings. Acceptance retains the cold
first-load and Dora outer-Host stop timeout as explicit residual risks.
