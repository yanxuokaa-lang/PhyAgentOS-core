# PAOS/Hephaestus Self-Evolution Architecture Conclusions

> Status: proposal
> Authority: non-normative until an implementation PR is accepted
> Scope: self-evolution capability fusion, not whole-project migration

## 1. Baseline Decision

The primary integration baseline is `origin/main` at the PAOS v1.0 Forge
architecture. Its physical execution path is
`ForgeToolClient -> Gateway Tool API -> ToolEndpoint`; its task and evolution
state is already represented by `AgentTask`, `PlanRevision`,
`ToolExecutionRecord`, `TaskEpisode`, `ExperienceCoordinator`, Lessons, and
guarded Skill promotion.

The local `preview` branch is a divergent v0.1.x Session-Centered Runtime
line. Its `BaseRolloutTarget`, `TargetSessionHandle`, and legacy Skill Runtime
extensions are compatibility references only and must not be copied into a
Forge PR. Every implementation PR must record its exact base branch, commit,
and Developer Manual version before code changes begin.

## 2. Decision

PhyAgentOS remains the host architecture for AgentTask, Forge Tool API,
Gateway binding, evidence, verification, Skill Runtime management, and
ExperienceCoordinator. Hephaestus is treated as a source of validated
self-evolution concepts, not as a package to be copied or embedded wholesale.

The fusion unit is one capability per PR. For `origin/main`, every capability
must first be expressed as a ToolEndpoint, ToolSpec, Skill Bundle profile, or
existing Agent/Experience extension. Hephaestus implementation classes are
references for semantics and failure behavior only; they are not a new PAOS
dependency or a second execution protocol.

## 3. Non-negotiable ownership

```text
AgentTask / PlanRevision     task planning and lifecycle truth
Gateway ToolResult           physical execution truth
ToolExecutionRecord          PAOS record linked to invocation/attempt IDs
TaskEpisode                  historical, redacted evidence projection
SkillCandidate               unpromoted workflow behavior change
Promotion Decision           guarded governance result for a Candidate
```

No Experience, Candidate, prompt, checkpoint, or recovery decision may rewrite
current-run AgentTask or Gateway truth. No self-evolution feature may change a
ToolSpec safety contract, Gateway admission, planner admission, calibration,
IK, collision, attachment/force semantics, or motion authorization.

## 4. Current Status And Gaps

`origin/main` already provides the self-evolution substrate needed for the
first fusion PRs: immutable Skill activation/binding, task-level outcome
envelopes, redacted TaskEpisodes, asynchronous reflection, scoped Lessons,
Skill Candidates, support thresholds, content validation, atomic Skill writes,
and rollback. Do not reimplement these as new services.

The material gaps are capability-specific rather than another evolution layer:

1. a simulator/robot Tool Bundle exposing scene observation, manipulation, and
   terminal evidence through strict ToolSpecs;
2. authoritative object identity, metric pose, attachment/lift/place state,
   and failure/unknown semantics in ToolEndpoint results;
3. a continuous workflow that can issue multiple bounded Actions/Sessions
   under one AgentTask and PlanRevision lineage;
4. independent simulated workflows that supply enough evidence for
   ExperienceCoordinator to distinguish reusable success from infrastructure
   or verifier failure;
5. replay and held-out/hazard evaluation only where real candidate data shows
   that the existing promotion gates are insufficient.

## 5. Revised PR Sequence For Forge

### PR0 - Baseline And Capability RFC

Lock the `origin/main` commit, Forge Developer Manual version, target simulator,
and the exact grasp capability boundary. This PR changes documentation only.

### PR1 - Tool Contract

Define Query, Action, and Session ToolSpecs for scene observation, grasp
planning, manipulation, and verification. Specify frames, units, tolerances,
readiness, max concurrency, timeout, cancel/stop, and unknown semantics.

### PR2 - Simulator Skill Bundle

Package the simulator Gateway, ToolEndpoint nodes, profile/dataflow, and locked
artifacts as a manifest-v2 Skill Bundle. No Agent-to-simulator or
Agent-to-Dora shortcut is permitted.

### PR3 - Fake Gateway And Conformance Tests

Test ToolSpec binding, context, Action/Session admission, invocation and
attempt identities, pending/terminal/unknown results, cancel/stop ownership,
and AgentTask aggregation using a mock Gateway before simulator execution.

### PR4 - Evidence And Verification

Connect before/after captures and terminal ToolResult data to the existing
`TaskVerificationContract`, without adding grasp-specific verifier code to the
Agent or Gateway client.

### PR5 - Continuous Manipulation Workflow

Add one Skill workflow that performs bounded multi-object manipulation through
the generic Tool API, keeps one AgentTask lineage, and uses PlanRevision only
when recovery is allowed by the task verdict.

### PR6 - Experience Integration

Use the existing `ForgeTaskOutcomeSource` and `ExperienceCoordinator` to create
TaskEpisodes, FailureObservations, and SkillCandidates from the workflow. No
new Attempt, Experience Store, Lesson engine, or Promotion service is added.

### PR7 - Candidate Evaluation Extension (Only If Needed)

Add replay, matched, held-out, or hazard evaluation only when PR6 produces a
demonstrated evaluation gap. Existing support thresholds, conflict blocking,
content checks, atomic writes, and rollback remain the default.

### PR8 - Evolution Audit

Extend existing Experience events only if the manipulation workflow needs
additional lineage fields. Report Skill-use, TaskOutcome, efficiency, and
safety without changing execution authority.

## 6. Required acceptance gates for every implementation PR

- ToolSpec schema, binding, and backward-compatible loading tests.
- Accepted and rejected Tool/Task admission tests where applicable.
- Missing, malformed, stale, duplicate, timeout, cancel, and unknown paths.
- Replay or artifact-binding test proving identity preservation.
- No automatic promotion in the same PR that introduces a new evidence type.
- No new access from Agent/Skill code to simulator SDK, Dora, or backend internals.
- Explicit current limitations and deferred work in the PR description.

## 7. Evolution eligibility rule

Reflection, retry, memory writes, checkpoints, and patch proposals are not
evolution by themselves. A Candidate may affect future Skill-use only when its
Forge execution is attributable, its evidence is complete enough for the
claim, and the existing promotion policy (or a separately justified
evaluation extension) supports the change.
