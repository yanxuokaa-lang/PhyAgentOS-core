# v12.3.4 Seven-Dimension Implementation Review

Date: 2026-09-30

Scope: provider-neutral synchronized multi-view scene understanding, Qwen vLLM
canonicalization, task-relevant scene binding, and the AgentLoop/Coordinator
integration. Safety mode: read-only Runtime validation; no physical Action was
executed.

## Findings

### Blocker

None open.

### Major

None open. The earlier oneOf argument pollution, canonical-entity ambiguity,
empty negative ambiguity placeholder, and environment-only binding fallback are
covered by implementation changes and regression tests. Runtime still rejects
ambiguous or stale evidence rather than authorizing motion.

### Minor residuals

- The first geometry request can still incur LocateAnything/SAM2 cold-start
  latency. The worker hibernation work removes repeated checkpoint reloads but
  does not hide the initial model load.
- Qwen lifecycle and Runtime restart remain operator-owned. Direct probing while
  the Runtime is hibernating is unsupported because it can race GPU ownership;
  validation must go through the Runtime-managed path.
- The live evidence is intentionally no-motion evidence. It proves discovery,
  semantics, and binding only; it does not claim acquire/place, retreat,
  verifier, or video-manifest acceptance.
- The current development `.venv` lacks optional `scipy`, `cv2`, and `pyyaml`
  packages used by geometry/video/backend fixtures. Those dependency failures
  are environment setup gaps, not semantic multi-view regressions.

## Seven dimensions

### 1. Architecture integration — PASS

Qwen remains a semantic provider, while Runtime owns observation provenance,
metric evidence, and binding authorization. The Adapter canonicalizes provider
claims at the provider boundary. Coordinator owns task-bound Query argument
materialization and validates the frozen ToolSpec before persistence or Gateway
execution. AgentLoop receives candidate categories and explicit constraints;
it cannot turn a perception recommendation into an actuator command.

The implementation is generic: it does not branch on RGB names, camera names,
benchmark poses, `manipulation.target`, or fixed grasp templates.

### 2. Recovery and idempotency — PASS

Invalid `scene.observe` argument combinations fail before a record or Gateway
call. Successful observations are selected by current-task record identity;
stale rejected records are not replayed as new evidence. Ambiguous entities and
duplicate metric envelopes remain fail-closed. Worker hibernation is distinct
from terminal shutdown, and shutdown failures do not silently become provider
success. No successful Action invocation is retried or synthesized.

### 3. Robotics safety — PASS

The changes affect perception and planning context only. Freshness, calibration,
scene identity, workspace, collision, IK, planning admission, motion
authorization, Gateway, terminal-result, release, retreat, and verifier gates
were not weakened. The live validation kept `motion_authorized=false` and
executed no Action. A missing or contradictory cross-view identity remains a
stop condition rather than a guessed binding.

### 4. Configuration and reproducibility — PASS

The local persistent profile explicitly uses a 1536-token Qwen budget, while
the Qwen service accepts two images and remains loopback/proxy isolated. Skill
and Node versions are immutable and installed as `pick-place-workflow 2.9.4`
and `robotwin20_persistent_host 0.9.3`; their recorded SHA values are in the
diagnosis. The no-motion validation is repeatable through the Runtime-managed
observe/understand/bind path.

### 5. Maintainability — PASS

Semantic identity signatures are computed from canonical category and normalized
attributes. Distinct signatures filter an overbroad identity ambiguity, while
duplicate signatures retain ambiguity and a single merged multi-view entity
still fails closed. The Agent projection names the distinction between
perception ambiguity and task relevance. Tests cover the generic cases instead
of adding an RGB-specific exception.

### 6. Observability — PASS

Provider diagnostics retain model, route, scene revision, image provenance,
elapsed time, raw response, and projected claims. Runtime records preserve the
selected observation, binding source, and ambiguity details. The 10-round live
record provides 10/10 observe and understand availability, 0 ms capture skew,
stable red/blue/green entity refs, and successful task-relevant binding.

### 7. AgentLoop autonomy — PASS

The loop uses Coordinator `ready`/`select` and current-task records, follows
the Query/Action distinction, and stops on invalid freshness, unavailable
grounding, or identity ambiguity. It does not invent opaque refs or substitute
environment entities when required task objects are unresolved. Model lifecycle
management stays outside Agent-authored plan nodes, preserving the control
plane/Runtime ownership boundary.

## Verification

- Qwen scene-understanding suite: `22 passed`.
- Full relevant Adapter + Skill suite: `1120 passed, 1 skipped, 3 existing
  baseline failures`; the three failures are unchanged baseline tests for place
  identity, intermediate video frames, and full workflow episode creation.
- A current broad collection reached `1257 passed`; 16 additional failures are
  missing optional `scipy`/`cv2`/`pyyaml` dependencies and one is the existing
  planning-loop reducer baseline. The affected suites are outside the changed
  semantic/binding path.
- Static checks: Ruff, compileall, and `git diff --check` passed.
- Live no-motion validation: 10/10 `scene.observe`, 10/10
  `scene.understand`, and task-relevant `scene.bind` available; capture skew
  0 ms in all rounds.
- No `object.acquire`, `object.place`, `ForgeTaskVerifier`, or video-manifest
  acceptance was performed.

## Acceptance conclusion

The implementation satisfies the original general requirement for synchronized
multi-view semantics and possession/occlusion-safe binding context without
RGB-arrangement-specific logic. There are no open Blocker or Major findings.
The remaining cold-start and operator-lifecycle notes are explicit Minor risks.
The next live acceptance must start from a fresh AgentTask and independently
prove every terminal Action, post-place retreat/return pose, final scene order,
verifier success, and complete three-block video manifest.
