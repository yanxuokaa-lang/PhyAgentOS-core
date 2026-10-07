# v12.9.6 Seven-Dimension Implementation Review

Date: 2026-10-07 (Asia/Shanghai)

Scope: review and repair of the `SimulationProbeError: qualified controller
source digest drifted` failure observed by `task_802c0dc7a58b4434`.

## Evidence

The failed Action consumed successful `red_grasp` and `red_prepare` records, but
returned `simulator_steps=0`, `world_change_started=false`, `arm_attempts=[]`,
and `recommended_action=fix_runtime_contract`. The live controller source was
`f3770007...`, while the configured capability and qualification evidence
declared `6a1e9cdc...`. No simulator or physical motion occurred.

## Findings And Repairs

1. **Architecture: Major, fixed.** Shared motion-policy admission checked
   capability and qualification packages only for internal consistency. It did
   not check the controller source imported by the current Runtime. The source
   binding now lives in `runtime/robotwin_motion_policy.py` and is called by
   Readiness and Action through the existing validator. The worker keeps only
   the execution-time drift guard.

2. **Correctness: three Major findings, fixed.** A stale but internally valid snapshot could
   pass `manipulation.prepare` and fail only at `object.acquire`. Admission now
   validates controller id, exactly one controller-source record, source digest,
   source-version prefix, and left/right capability identity. A monitored host
   also performs the same read-only source check before Runtime composition.
   Startup also verifies that the configured left/right files declare the
   corresponding arm instead of merely containing valid documents. Rereading
   only the on-disk source at
   admission could misidentify an old process after that source file was
   replaced. Shared admission now binds evidence to the digest captured when
   the motion-policy module loaded. The execution guard separately rereads the
   file before every provider command, so post-admission replacement still
   fails before a simulator step.

3. **Recovery and idempotency: Pass.** The failure remains provider-owned,
   `retryable_in_revision=false`, `requires_replan=false`, and
   `recommended_action=fix_runtime_contract`. The AgentLoop still stops and does
   not retry, observe, switch arms/candidates, replan, or resend an Action.
   Existing execution-time source recheck remains fail-closed.

4. **Robotics safety: Pass.** The new checks run before route execution and do
   not authorize motion. Existing controller bounds, route, stop, calibration,
   collision, and settlement checks remain unchanged. The stale-source path is
   verified with zero simulator steps; no Gateway or simulator call is added.

5. **Extensibility and configuration: Pass after repair.** The logic is driven
   by generic `MotionCapabilityDocument` provider/source records and the existing
   materializer keys. It contains no RGB, color, order, benchmark-id, camera, or
   fixed-arm branch. Disabled-action profiles keep their previous startup path;
   monitored profiles receive the preflight through configuration.

6. **Observability and maintainability: one Minor finding, fixed.** The structured failure code and
   recommended action are preserved. The validator exposes the bound source
   digest to the Action state, and the startup error includes the underlying
   source-binding reason. Invalid configured path values are normalized into
   the same configuration error instead of leaking `TypeError`. Private route
   trajectories remain outside Agent output.

7. **AgentLoop autonomy and convergence: Pass.** Coordinator/Agent ownership
   is unchanged. The Agent still selects records and decides stop/replan; the
   Runtime only reports a deterministic contract failure. No hard-coded next
   step or automatic continuation was introduced.

## Regression Coverage

- `test_simulation_probe.py`: live-source success, provider mismatch, digest and
  version drift, post-import file replacement, invalid configured paths,
  configured stale snapshots, and wrong-arm path rejection.
- `test_persistent_route_evaluator.py`: internally valid stale evidence is
  rejected during Readiness with no world execution.
- `test_persistent_host.py`: monitored startup invokes preflight once and
  disabled mode does not invoke it.
- `test_persistent_action_approval.py`: existing prepared-plan/no-second-plan
  behavior remains covered.
- Core planning/recovery selection and outcome tests remain unchanged.

## Validation

- Changed Adapter path: `120 passed`.
- Full Skill suite: `379 passed`.
- Core planning/recovery subset: `174 passed`.
- Adapter non-video baseline: `805 passed, 10 deselected, 13 existing failures`.
  The failures are environment or unrelated fixture failures (`scipy`, YAML
  fixture, and legacy Action result contracts), not changed-path failures.
- Ruff, compileall, and `git diff --check`: passed.
- Validation created no AgentTask, invoked no Gateway Query/Action, advanced no
  simulator step, and did not restart the live Runtime.

## Release

- Adapter: `0.9.6`.
- Node: `0.10.11`, archive SHA-256
  `091b074cf378eaa4ca7661848de0b210d2560017f577d1d1ff8ec43895dd6db8`.
- Skill: `3.0.3`, bundle SHA-256
  `741a171c19a1db343dbacba927e3c70afe81fcd0a73ee2e7ecf594dff5a95fd8`.

Remaining deployment requirement: stop the old Runtime, regenerate the
capability validation and controller qualification package from the final
controller source, install the rebuilt Node/Skill artifacts, then perform the
read-only startup preflight before any new Action.
