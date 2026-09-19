# v10.9.6 Preparation materialization repair and acceptance

## Root cause and architecture review

`task_91ad705bbc9c4800` failed before readiness: the first materializer exited
after 0.364 s because four configured motion-capability/validation files did
not match the approved controller qualification plan. The CLI log contained
`route motion capabilities do not match controller qualification`; the Agent
received only `preparation_provider_error`. The previous actor-pose fix worked.

The local deployment referenced `paos-motion-capability-v2-20260906TntyqoT`,
while qualification bound files under
`paos-probe-v7.5.4-20260909T062313Z/robotwin/franka-bounded-q4`.
All four latter files match the existing qualification digests exactly; raw and
model-canonical comparisons confirmed this was not a serialization difference.
Only the four environment paths were corrected. No limits or qualification
evidence were edited, and no running process was restarted.

Architecture references: framework introduction, developer manual,
`MANIPULATION_DAG_DEVELOPER_GUIDE.md`, `REAL_SPEED_LIMITS_ARCHITECTURE.md`,
`VISUAL_GEOMETRY_EVIDENCE_ARCHITECTURE.md`, and Agent input-selection/recovery
design. Adapter owns geometry/configuration; Runtime owns collision state;
Core carries provider-neutral errors; Agent decides recovery. No new scheduler,
gate, hash mechanism, motion permission or Core provider branch was introduced.

## Review findings and fixes

- **Blocker fixed — deployment mismatch:** use the already-qualified capability
  package; the same wrong inputs still fail the original qualification check.
- **Blocker fixed — dropped obstacles:** real replay then revealed that grounding
  replaced the complete scene with only its target while retaining complete
  coverage. Replace only the target; preserve all other captured Runtime collision
  objects. Their geometry is safety context, not visual perception output.
- **Major fixed — obstacle/goal conflation:** current-scene v2 permits objects
  without destination fields; partial destinations remain invalid, the selected
  target must have a full destination, and v1 remains unchanged. No dummy obstacle
  destinations or weakened collision coverage were added.
- **Major fixed — one rejected candidate aborted the batch:** a typed workspace
  rejection now records the failed candidate and continues the existing loop.
  Invalid configuration, qualification mismatch, timeout and unclassified process
  failures still abort; no routes are imported on fatal/all-rejected failure.
  The workspace inequalities are unchanged. Only workspace rejection is currently
  classified as skippable; unrelated geometry errors remain fail-closed.
- **Major fixed — lost materializer diagnostics:** declared failures write an
  exclusive `materialization_error.json` and public JSON log result. Builder
  propagates code/message/log location through existing `PreparationProviderError`.
  Generic crashes retain logs and return `route_materialization_failed`.

Fresh source review found no remaining Blocker/Major in this repair's tested
scope. Real readiness and Action behavior are not established by materialization.

## Established seven dimensions / 原七维验收

| Dimension | Result and evidence |
| --- | --- |
| Architecture integration | PASS: adapter-only geometry and process changes; existing Core/Agent recovery error channel, no fixed RGB/task branch. |
| Recovery and idempotency | PASS: fatal/all-rejected paths publish no route; unique candidate output directories, no implicit Tool retry or revision rewrite. |
| Robotics safety | PASS, no-motion: qualification mismatch still rejected, two obstacles retained, workspace-rejected candidate excluded, no simulator/Gateway calls. |
| Context and performance | Materialization measured: 24 candidates, 23 retained, 46 arm options, 7.705 s; diagnostics do not add geometry to model context. IK/collision readiness latency remains unmeasured. |
| Configuration and reproducibility | PASS: corrected four local paths, versioned Node/Skill, command/input/metrics saved for frozen replay, isolated installation verified. Live deployment pending. |
| Maintainability and observability | PASS: typed workspace rejection, persisted CLI error, per-candidate reasons/timing, documentation and negative regressions. |
| AgentLoop autonomy | Interface PASS: public error uses existing settlement/recovery path; Agent remains responsible for stop/replan. Real-model recovery behavior not exercised. |

## Validation and reproducibility

- Core: **504 passed**, 25.73 s; Skill: **337 passed**, 7.36 s.
- Adapter: **522 passed, 1 skipped**, 5.99 s (Pillow-dependent perception-worker
  module skipped in this interpreter).
- Changed Python Ruff/compileall and `git diff --check`: PASS.
- Real saved-input `PersistentRouteBuilder`, with real materializer subprocesses:
  **24 attempted, 23 retained, 1 rejected, 46 arm options, 2 collision obstacles,
  7.705382 s total**. Rejected `candidate://block-01/14` violates workspace bounds.
  No readiness evaluator, simulator, model inference or Gateway was invoked.
- Saved scene client was an in-memory replay of persisted facts, not a live
  freshness assertion. Source task, binding, target, command files, base commit
  `9073aac`, dirty-worktree marker, per-candidate logs/timing and final bundle are
  retained at:
  `/home/yanxu/tmp/hephaestus/paos-v10.9.6-frozen-replay-rle4vnt0`.
  Files: `builder-summary.json`, `builder-bundle.json`, `scene-facts.json`, and
  `preparation-builds/route-*/command-*.json` plus logs and candidate artifacts.
- Negative control retains the old mismatched inputs and exits 1 with
  `motion_capability_qualification_mismatch` at
  `/home/yanxu/tmp/hephaestus/paos-v1096-mismatch-negative-ixplspgm`.
- Replay scripts: `/tmp/paos-materializer-replay-v1096.py` and
  `/tmp/paos-builder-replay-v1096.py`; they create unique output directories and
  do not overwrite production evidence. Timing depends on host load/filesystem
  caches; it is one frozen-scene measurement, not an IK or end-to-end benchmark.
- Node **0.3.2**, Skill **2.3.4**: `/tmp/paos-v10.9.6-release-C8EHwH`.
  Node size: 332890 bytes; existing release SHA-256:
  `955d0d08a3b392933dbeebabf2d3568901b86bbd94cdfe1d28b183bc6bf3b2ef`.
  SkillInstaller/NodeInstaller and Node lock verification pass in `isolated/`.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_asyncio.plugin tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:examples/forge-skills/pick-place-workflow/src \
  python -m pytest -q -p pytest_asyncio.plugin examples/forge-skills/pick-place-workflow/tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-adapters/robotwin20/runtime:examples/forge-adapters/robotwin20/scripts:examples/forge-skills/pick-place-workflow/src \
  python -m pytest -q -p pytest_asyncio.plugin examples/forge-adapters/robotwin20/tests
PYTHONPATH=.:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
  python /tmp/paos-builder-replay-v1096.py
```

本次未取消或恢复任务、未重启 Runtime。新代码包与修正的环境文件需要在后续部署启动后生效；
不能用此无运动验收宣称 readiness、抓取放置或跨 Action 视频已成功。
The running process retains its previous environment and embedded Node. Deploy
the new package and start a fresh run before evaluating readiness, motion or
the complete multi-Action video.
