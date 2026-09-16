# Qwen3-VL lifecycle and AgentLoop acceptance

- Task ID: `qwen3vl-lifecycle-agent-loop-20260916`
- Stage bucket: `canonical single-run execution`
- Target layer: `agent`, `planning`, `task`, `adapter`, `skill`
- Current-run truth owner: `AgentTaskCoordinator` and task-bound Tool records
- Motion boundary: Query-only validation; no Action, Session, simulator step, or motion authorization

## Root cause

`task_4532207b1cc34d71` failed before IK, collision, or workspace evaluation. The
Agent supplied `destination_ref` and `capability_snapshot_ref` to
`manipulation.prepare` but omitted `intent`. The live Tool schema described each
field, while its planning projection could not declare that PAOS must derive the
Coordinator-owned intent identity. The model was therefore expected to assemble
`task_id`, `revision_id`, `node_id`, and `node_digest`, even though those values
belong to the Coordinator.

The Runtime correctly returned `invalid_intent_binding` with
`motion_authorized=false`. Recovery then exposed three separate issues: a
replacement graph used `retry_of` to reference a node outside that graph; the
120-second recovery deadline expired while the Agent corrected the graph; and
the loop used the globally active task instead of the current session task,
which contributed to creation of a placeholder `noop` task.

## Implemented route

ToolSpecs may declare `trusted_argument_builder: manipulation_intent_v2` in
their planning extension. During `forge_plan_select`, PAOS validates the
model-owned semantic fields, derives Coordinator-owned identity and observation
bindings, validates the final `ManipulationIntent`, and returns both the
planning binding and final Tool arguments. Admission verifies that the final
arguments match the persisted input digest.

Recovery exposes the deadline to the prompt, grants at most one bounded
submission lease, rejects cross-graph `retry_of`, rejects placeholder task
descriptions, and projects the current session's task. Storage still permits
only one non-terminal task globally; session selection does not weaken that
constraint.

The RoboTwin adapter wraps the local Qwen provider with a concurrency-safe vLLM
lifecycle manager. A request cancels idle sleep, wakes a sleeping engine, and
increments the active-request count. Sleep is possible only after the last
request exits. Normal inactivity uses the configured idle timeout; the
single-view composition also performs a synchronous level-1 sleep after Qwen
semantics and before starting LocateAnything, preventing both providers from
overlapping on the same GPU. Active Qwen requests block this handoff. Failed
control transitions re-arm the idle check so a later operator-owned vLLM
recovery cannot remain awake indefinitely. Control/status failure raises the
lifecycle-specific error and therefore enters the configured GPT-5.6-sol/high
fallback. Ordinary Qwen inference or output-contract failures remain failed
Queries and do not silently switch models. The manager never starts vLLM,
invokes robot Tools, or authorizes motion.

For vLLM 0.11.2, `VLLM_SERVER_DEV_MODE=1` is required when starting the server;
without it, `/sleep`, `/wake_up`, and `/is_sleeping` return HTTP 404 even with
`--enable-sleep-mode`.

## Seven-dimension acceptance

1. Architecture integration: lifecycle stays at the adapter provider boundary;
   trusted intent derivation stays in planning selection and Coordinator
   persistence.
2. Failure recovery: lifecycle errors enter the existing fallback; recovery has
   one bounded lease and preserves append-only revisions; lifecycle control
   failures re-arm idle state reconciliation.
3. Authorization and robot safety: all new paths retain
   `motion_authorized=false`; live validation invoked no Action or Session.
4. Configuration and reproducibility: lifecycle endpoint, idle timeout, control
   timeout, and sleep level are profile-owned; model and Node versions are
   locked by the Skill manifest.
5. Maintainability: the ToolSpec declaration is provider-neutral and contains no
   RGB task or RoboTwin Core special case.
6. Observability: lifecycle state/error and active-request count are available
   at the adapter boundary; task projection exposes recovery deadline and lease
   use.
7. AgentLoop autonomy: the Agent supplies semantic intent, while PAOS supplies
   trusted identity and returns directly reusable final Tool arguments.

## Validation evidence

- Core: `416 passed`
- Skill: `334 passed`
- RoboTwin adapter: `493 passed`
- Ruff, compileall, and `git diff --check`: passed
- Live no-motion image: sleeping memory about `276 MiB`; automatic wake request
  `6.865 s`; output `3` entities, `2` relations, `1` ambiguity, empty metric
  envelope; automatic idle sleep returned to `276 MiB`.
- Subsequent live requests: `4.474 s` and `3.687 s`, both with `3` entities and
  `2` relations.
- Final installed release: Skill `2.1.4`, Node `0.1.13`; Node SHA-256
  `58bc793aa2d90a7344c4ebea8b57140c45c168527eccd65929e906de4a55151f`;
  Skill archive SHA-256
  `259792c968d3d369d010961948d3fc21fa65b5f91d5f66d2e3388a74c6449bbf`.
- Final installed-Runtime Query: all `9` Tools ready; request began and ended
  with vLLM sleeping, completed in `13.225 s`, and returned `3` entities and
  `2` relations. Four ambiguities remained explicit, including the unmodeled
  foreground object; no metric envelope or derived artifact was fabricated.
- The release packager excludes `.pytest_cache`, `.ruff_cache`, and
  `__pycache__`; the archive-content regression passed.
- Lifecycle fault injection: with the operator-owned vLLM stopped, the same
  Query used GPT fallback and returned `3` entities, `5` relations, and `3`
  metric envelopes in `121.011 s`; no Action or Session was created.
- Direct calls to the vLLM inference endpoint are outside lifecycle ownership
  and must not run concurrently with PAOS-managed sleep/wake transitions.

### Principles Gate

- Stage Bucket: `canonical single-run execution`
- Target Layer: `agent`, `planning`, `task`, `adapter`, `skill`
- Owner Seam: `AgentComposedDispatch`, `AgentTaskCoordinator`, and adapter scene-understanding provider boundary
- Proposal or Override: `proposal`
- Current-Run Truth Owner: `AgentTaskCoordinator`, task-bound Tool records, and live vLLM lifecycle status
- Decision Owner: Agent owns semantic choice; Coordinator owns identity, binding, and admission
- Evidence Source: current task observation, Tool results, NodeSettlement, and live lifecycle responses
- Evaluator Boundary: Runtime intent/readiness validation, planning admission, and existing Verifier
- Stop / Attempt Bound: one replan lease; stop on invalid identity, stale evidence, lifecycle/fallback failure, or unknown physical outcome
- Public Contract Impact: optional ToolSpec planning field and additive selection final arguments
- Legacy Surface Impact: compatible for ToolSpecs without a trusted argument builder
- Rollback / Containment: disable lifecycle or remove the per-Tool builder; existing Runtime validation remains authoritative

- [x] P1 stage alignment: lifecycle and planning ownership remain in their declared stages
- [x] P2 single mainline: no second execution or task state owner is introduced
- [x] P3 current-run truth: Coordinator records and live lifecycle state override model prose
- [x] P4 layer purity: Core planning is provider-neutral; vLLM control remains adapter-owned
- [x] P5 slot before branch: ToolSpec planning extension selects the trusted builder
- [x] P6 generic capability: no RGB object or task identifier is hard-coded in Core
- [x] P7 profile before template before mutation: lifecycle timing is profile-owned
- [x] P8 layered evidence: model claims, runtime readiness, and task evidence remain distinct
- [x] P9 no execution, no memory: no Action or experience promotion occurs in validation
- [x] P10 bounded recovery: one recovery lease; no blind retry or infinite extension
- [x] P11 public contract: selection adds final arguments and ToolSpec adds an optional policy field
- [x] P12 legacy containment: Tools without a trusted builder retain existing behavior
- [x] P13 scope closure: implementation, tests, package, install, and residual startup condition are recorded
- [x] P14 Agent loop: decision, evidence, admission, fallback, and stop bounds are explicit
- [x] P15 safety boundary: no new path grants motion authority

### Agent Route Contract

- Decision owner: Agent selects semantic intent and Tool; Coordinator owns task,
  revision, node identity, digest, final binding, and admission.
- Context sources and selection rule: current-session task projection, active
  PlanGraph, frozen ToolSpec policy, task-bound evidence, and live scene revision.
- Context projection/truncation: provider payloads remain behind Tool responses;
  prompt projection exposes bounded task and recovery fields only.
- Callable capability surface: `forge_plan_select`, task-bound Forge Query
  wrappers, and adapter-local scene-understanding inference.
- Runtime admission boundary: `AgentComposedDispatch`, Coordinator planning
  binding, Gateway ToolSpec, and existing Runtime validation.
- Observation / evidence source: exact current task observation, candidate,
  destination, and capability references.
- Evaluator and settlement boundary: Runtime `ManipulationIntent` validation,
  readiness provider, NodeSettlement, and existing Verifier.
- Success / partial / error / unknown semantics: lifecycle and intent errors are not
  success; they either fallback or enter bounded replan without world change.
- Interrupt / cancel / resume semantics: existing Coordinator cancellation and
  append-only revision paths; no force stop or blind action retry.
- Stop condition and attempt bound: stop on incomplete semantics, identity
  mismatch, stale scene, lifecycle failure without fallback, exhausted single
  lease, or any unknown physical outcome.
- Promotion boundary for memory or strategy candidates: none; this change does not promote memory or strategy.
- Rollback / hazard containment: optional ToolSpec builder can be removed per Tool;
  disabling lifecycle leaves the existing inference/fallback path; Runtime
  safety validation remains authoritative.

## Review outcome

`aligned`: the implementation fixes the interface ownership error without
weakening Runtime validation, introducing a second robot state owner, or
expanding motion authority.
