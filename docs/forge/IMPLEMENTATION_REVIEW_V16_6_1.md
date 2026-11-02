# v16.6.1 implementation review / 实现复核

## Findings and disposition / 问题与处理

1. **Major, fixed — reset qpos and scene transforms represented different
   states.** `engine.py::_refresh_initial_robot_state` stepped dynamics, restored
   qpos and rendered, leaving CPU USD link transforms from the stepped state.
   Real Isaac measurements found 6.56 mm hand error. Explicit kinematic update
   and PhysX-to-USD publication now replace that step; the same initial/reset
   helper is used, and native hand error falls to 0.000197 mm.
2. **Major, fixed — collision labels were insufficient to audit the geometry.**
   Sphere/box/self-sphere failures now retain exact checked joints/TCP, queried
   geometry, margin, pair and swept/measured finger mode in private receipts.
   Error wrapping preserves the record. AgentLoop consumes the existing opaque
   evidence reference; its public selection/Tool contract is unchanged.
3. **Major, prevented — conservative overlap was being interpreted as physical
   contact.** Five historical candidate-17 failures have mesh/table separation
   at the rejected intermediate sample while the padded full-travel box overlaps.
   The diagnostic explicitly labels a collision-model finding. This is not
   sufficient evidence to shrink the shape, lower margins, exempt the table,
   accept a final grasp or start a controller; existing checks are retained.

## Architecture and safety boundary / 架构与安全边界

- Authority: root AGENTS, PAOS developer manual, manipulation developer guide
  and visual geometry evidence architecture. Tier C-Safety: reset transforms
  affect FK, wrist-camera calibration and route validation.
- Generic semantics stay with AgentLoop; lifecycle/cancellation/settlement and
  recovery remain with Runtime/Coordinator. No second scheduler or candidate
  fallback is added. Same-capture and qualified-only selection tests still pass.
- Mechanisms live inside the Isaac Adapter. The diagnostic inspector uses the
  same Adapter scene initialization and FK/collider mechanisms; it does not
  become an alternate execution route or change the selected scene/model.
- Public interfaces/configuration are unchanged. Replacement-query tests verify
  primitive values and rejection; failed state synchronization propagates an
  error and restores the caller's timeline state instead of claiming readiness.
- No new hashes, frozen contracts, gates or safety-threshold changes. The new
  private diagnostic fields address the observed inability to distinguish
  actual mesh geometry from conservative overlap labels.
- Historical replay keeps original observation identity separate from current
  scene identity, commands no hypothetical joint state, and cannot authorize
  Action. New task evidence must come from a new formal capture.

## Verification / 验证

- Contract/regression: **421 passed** across Isaac, GraspNet worker/provider/
  profile and subtask executor. Seven reset tests first failed on the old path.
  Geometry diagnostics are tested with replacement PhysX-query stubs; reset
  tests cover before/after reset, playing/paused timeline and publication failure.
- Static checks: Ruff, compileall, `git diff --check` passed.
- Native mechanism evidence: r1/r3 receipt inspection on the actual composed
  LabUtopia scene. Hand error: `6.561186 mm -> 0.000197 mm`; maximum link error
  after repair `0.000201 mm`. Historical inspection changes neither joints nor
  physics time and issues zero controller commands. The interrupted r2 startup
  is not counted as successful evidence.
- Live execution evidence: none. The formal no-motion Agent follow-up is
  recorded in the diagnosis; collision-free complete acquisition, liquid
  transfer and stirring are not established by this local repair.
- Formal session `cli:lab-3019a1d6c656` / task `task_ebea061a2ed841e3` is
  cancelled at task-affordance. Four aperture rejections and 48 rejected
  approaches remain; all 24 collision attempts now retain structured geometry.
  Motion is disabled and controller outcomes are empty. This confirms the new
  diagnostic path is integrated, not that approach infeasibility is repaired.

No identified Blocker/Major remains in the reset synchronization and diagnostic
change. Manipulation-route availability is a separate runtime result; it must
not be relabeled as successful merely because this implementation passes tests.
