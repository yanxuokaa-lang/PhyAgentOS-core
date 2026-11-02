# v16.7.0 implementation review / 实现复核

## Findings and disposition / 发现与处理

- **Major — retention discarded usable coverage before qualification.** Same-
  cloud replay finds two worker hypotheses passing existing process/aperture
  rules with the padded palm above the table plane. Both survive NMS (389 total)
  and disappear under retained=64. The experiment profile now keeps the existing
  bounded 512 worker pool after score filtering/NMS for task qualification.
  This repairs demonstrated selection loss without manufacturing new poses.
- **Major — larger candidate count is not a safety verdict.** No opening/support
  threshold, NMS, model score threshold, robot margin, IK, collision, full-route
  or qualified-only recovery check changes. A palm/table-plane necessary
  condition is diagnostic only; fresh native qualification remains authoritative.
- **Major — isolated model environment cannot import the host runtime stack.**
  The first diagnostic attempt failed on missing Pydantic. The replay now calls
  only the existing isolated worker protocol, preserving environment separation
  without installing dependencies or changing the production worker protocol.
- **Cost — larger Query evidence and qualification workload.** Inference still
  uses the same 512 output cap, 12000 points per pass and seed. Opt-in regions
  increase inference from four to at most sixteen passes; existing profiles
  default to zero regions and retain their original sampling behavior.
  Later qualification evaluates more native hypotheses. Existing context
  compaction and preparation deadlines remain; native results must report any
  resulting limit rather than silently truncate the pool again.
- **Major — retention alone did not repair usable coverage.** Native validation
  rejects both recovered poses on full-travel finger/table overlap. The worker
  now recomputes native predictions from bounded, same-capture observed subsets
  and preserves spatial/orientation/width diversity. Full-cloud inference and
  complete-capture qualification remain; no shifted pose or relaxed exclusion.
- **Major — coordinate and partial-success risks in multiple passes.** Tests
  check every region/rotation's inverse mapping, unchanged native geometry,
  request-wide budget and failure of a later regional pass. Region failure
  cannot publish preceding full-cloud success. Defaults remain compatible.
- **Minor — historical diagnostic at dirty HEAD was not fully reproducible.**
  Save exact worker source in new diagnostic receipts, alongside configuration
  and Git revision. No new hash, frozen contract or runtime gate is introduced.
- **Blocker — complete PlanNode arrays overflowed model context.** Regional r2
  created a task with 508/506/24 retained candidates but its prompt reached
  339858 tokens before output reserve. Existing task/node/working-set prompt
  projections now summarize large arrays using the existing phase display
  bound. Exact immutable Coordinator values and semantic parameters are retained;
  no sampling reduction or context-window override. Two failing regressions
  (robot and document candidates) reproduce the leak before the fix and prove
  all three views leave authority data unchanged afterward.

## Architecture / 架构

Generic AgentLoop/Coordinator continues to own task semantics, dependencies,
opaque selection, cancellation/recovery and settlement. Existing Grasp ports
carry unchanged candidates; Task-Affordance qualification determines which
references can enter preparation. Isaac Adapter owns current geometry, aperture,
coordinate transforms, IK and complete-route validation. Replacing GraspNet with
a different worker uses the same production composition, exercised by tests.

No public schema, capability, lifecycle, admission path or new Provider is
introduced. Coverage mechanisms remain private to the existing Grasp Provider.
The original observation/scene/frame/calibration lineage and new capture-scoped
opaque IDs are retained. Action recovery cannot reintroduce discarded or
unqualified raw candidates. No new hashes, baselines or generic gates are added.

The additional generic change is limited to existing read-only prompt views.
It contains no provider, USD, grasp-specific key or action-routing branch.
The repository-specific normative sources are `MANIPULATION_DAG_DEVELOPER_GUIDE.md`,
`VISUAL_GEOMETRY_EVIDENCE_ARCHITECTURE.md`, `AGENT_TOOL_INPUT_SELECTION_DESIGN.md`
and AGENTS.md. Hephaestus skill references to docs/AGENT_WORKFLOW.md and its
companion files do not exist here; they were not treated as PAOS authority.

## Evidence / 证据层级

Contract evidence: production-composition regression reproduced `64 != 70`, then
passes with unchanged model poses/scores and capture-scoped opaque references.
Provider failure publishes no candidates. Diagnostic tests persist explicit
failure rather than success and record configuration/commit/provenance.

Historical Provider evidence:
`out/lab-grasp-sampling-20261102-r2/sampling.json`, containing raw hypotheses,
worker output, profile, checkpoint/source path, random seed, input references,
command and repository commit. Model source revision is
`280c215129f759ed8649cb4e89fc5dfee55f4f80`. No change to `models/graspnet.py`
was present at inspection. Replay produces 1057 thresholded candidates versus
1059 decoded in the earlier run; a seed does not guarantee bitwise GPU replay.

Native model / worker 512 / retained 64 have respectively 4 / 2 / 0 hypotheses
meeting existing process/aperture qualification and the padded-palm plane
necessary condition. Both worker hypotheses survive NMS. A cap sweep retains
zero at 64/96/128, one at 192/256 and both at 512. These are diagnostic counts,
not certified contacts or motion outcomes.

Fresh native validation workspace:
`out/lab-fullchain-truth-20261102-full-pool-no-motion-r1/`.
Task `task_b32f6dea14194fe8` cancelled: 21 aperture failures, 144 final palm/table
records and 16 final finger/table records. No candidate reached IK. Expanded
Query context reached approximately 258k/263808 tokens with existing compaction;
there was no context-limit failure. No live motion success is claimed.

Regional replay `out/lab-grasp-sampling-20261102-r3/sampling.json` produces 9855
thresholded native predictions, sampled to 512. This count is not admission.
Regional native no-motion workspace:
`out/lab-fullchain-truth-20261102-region-no-motion-r1/`.
It stopped before task creation on destination semantic ambiguity. Rerun r2
corrected the label and exposed the prompt overflow, with motion disabled and
no controller outcomes. Rerun r3 validates the prompt fix and native qualification.

## Reproduction / 复现

Final native r3: task `task_a87e6bb320964db7`, revision
`revision_acc11d27415a4747`. Four R03 Query/preparation nodes completed; seven
distinct qualified combinations are available and one is selected with exactly
seven same-set qualified recovery references. There are 30 successful variant
attempts, not 30 candidates. Rejected attempts remain: 472 palm/table, eight
finger/table, 12 self-collision, nine later route-collision and five IK failures;
41 requests fail aperture before attempt enumeration.

The complete no-motion workflow remains **unaccepted**: task `awaiting_replan`,
long-horizon outcome `blocked` at `pour_r03` with `node_selection_no_progress`,
host exit 1. `simulated_motion_enabled=false`; four Query and zero Action records.
The Action node was not executed, and full acquire/pour/return routes plus R04/rod
qualification are not proven. This is a remaining workflow boundary, not evidence
that the seven short-approach-qualified combinations collide on complete routes.
No Blocker/Major defect remains open in the changed coverage/projection code;
this acceptance does not claim the end-to-end manipulation goal is achieved.

Validation: 463 affected adapter/worker/executor tests and 62 prompt-context
tests pass. The broader 778-test run reports 773 passes and five failures in
unchanged planning-selection mocks (missing `graph.nodes`). Loading both changed
generic modules from Git HEAD in memory and rerunning that file reproduces the
same five failures / 35 passes. These pre-existing fixture failures are disclosed,
not suppressed or counted as success. Ruff, compileall and whitespace checks pass.
Native r3's post-creation prompt is 26594 tokens (18150 node facts); it passes
the prior context limit and enters current-capture process Query/selection.

From the repository root; use a new output directory to preserve prior evidence:

```bash
/home/yanxu/miniconda3/envs/graspnet/bin/python \
  examples/forge-adapters/isaacsim_lab/scripts/inspect_grasp_sampling.py \
  --profile examples/forge-adapters/isaacsim_lab/configs/labutopia-mixture-perception.json \
  --prediction out/lab-fullchain-truth-20261102-final-gripper-no-motion-r1/artifacts/labutopia/grasp-predictions/5556f32cda534ed5a8cbbd2acb0f400c.json \
  --artifact-root out/lab-fullchain-truth-20261102-final-gripper-no-motion-r1/artifacts/labutopia \
  --output out/lab-grasp-sampling-NEW

PYTHONPATH=.:examples/forge-adapters/isaacsim_lab/src:examples/forge-adapters/robotwin20/src:examples/forge-skills/pick-place-workflow/src \
./.venv/bin/python -m pytest -q \
  examples/forge-adapters/isaacsim_lab/tests \
  examples/forge-adapters/robotwin20/tests/test_graspnet_worker.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_proposal.py \
  examples/forge-adapters/robotwin20/tests/test_grasp_profile.py \
  examples/forge-skills/pick-place-workflow/tests/test_subtask_executor.py

PYTHONPATH=. ./.venv/bin/python -m pytest -q tests/test_prompt_context.py \
  tests/test_planning_loop.py tests/test_planning_source_assembly.py \
  tests/test_planning_selection.py tests/test_planning_dispatch.py \
  tests/test_planning_projection.py tests/test_planning_end_to_end.py
```

The replay captures native/worker pools; the original prediction artifact stores
the old retained set. Compare those exact poses, not ordinal IDs across captures.
