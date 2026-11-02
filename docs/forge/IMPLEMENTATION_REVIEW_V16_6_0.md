# v16.6.0 review / 候选生成局部修复复核

## Findings and disposition / 问题与处理

1. **Major, fixed: proposed diagnosis did not distinguish generation from
   truncation.** Saved R03 evidence has 44 native decoded candidates and 24 after
   NMS, below the configured 64-candidate budget. Neither increasing top-K nor
   rewriting Agent selection establishes the missing approaches. The saved
   diagnosis now separates these stages and preserves the actual counts.
2. **Major, fixed: the active native generation path lacked approach coverage.**
   Seven retained directions all point upward in world coordinates. Bounded,
   configured input-frame inference now recomputes native proposals from the
   same cloud and restores them to the capture frame. Paired native inference
   produces side/downward task-compatible candidates without changing workspace,
   approach distance or contact checks. This resolves coverage, not full-route
   feasibility or grasp success.
3. **Major, prevented: post-hoc grasp rotation would manufacture evidence.**
   The worker rotates inputs around their centroid, calls the model for every
   pass, then inverse-transforms translation and orientation. Tests distinguish
   transformed native output from simply flipping a previously rejected grasp.
   Width/depth/height and scores remain model-derived; all references keep their
   original capture provenance.
4. **Major, prevented: partial inference failure could masquerade as a complete
   evaluated set.** All configured passes must finish; a failed pass rejects the
   request through the existing worker unavailable path. Empty passes stay empty,
   and the existing aggregate candidate cap applies after merging.

## Ownership and compatibility / 所有权与兼容性

- Tier C-Safety; authority is repository AGENTS, PAOS developer manual and the
  manipulation/visual-evidence guides. The Hephaestus skill's differently named
  authority files are absent here; no replacement gate is invented.
- Worker/profile own inference coordinate variants. Isaac Adapter owns camera to
  world/TCP transforms, IK, aperture, contact/collision and complete routes.
- AgentLoop/Coordinator retain task selection, opaque references, freshness,
  recovery, cancellation and settlement. Public Tool and worker reply schemas
  are unchanged. There is no new controller, scheduler or fallback candidate set.
- Default worker behavior remains one identity pass. Only the explicit LabUtopia
  profile opts in; replacement-provider integration uses the existing protocol.
- Same-capture point-cloud geometry is unchanged; coordinate variants do not
  observe hidden surfaces. Scores are proposal scores, not motion permission.
- Safety thresholds and operation parameters are unchanged. The no-motion probe
  and full-route preparation must still reject unsafe or unavailable proposals.
- No new hashes, frozen contracts or release gates. The one-to-four pass bound
  controls the concrete request-time/GPU workload introduced by this mechanism.

## Evidence / 证据

- Contract tests: one-pass behavior, 90/180-degree frame restoration, invalid
  quaternion/pass bounds, total candidate cap, empty/failed inference, and
  replacement-worker results through the existing GraspNet Proposal Provider.
- Real model evidence: `out/lab-grasp-coordinate-replay-20261102-r1/` stores
  original capture, fixed seed, actual profile/checkpoint metadata, native
  identity/ensemble results, versions and timing. Its 3 -> 10 task-compatible
  candidates are historical geometry evidence, not fresh motion evidence.
- Integration tests and fresh no-motion run results are recorded in the
  diagnosis and changelog when completed. Live motion is not part of this repair
  verification; pouring/stirring success requires separate execution feedback.

Implementation review finds no remaining identified Blocker/Major in the changed
Provider mechanism. Runtime-route availability remains an empirical question.
