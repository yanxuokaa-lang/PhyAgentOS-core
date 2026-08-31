# PAOS/Hephaestus Self-Evolution Architecture Conclusions

> Status: proposal
> Authority: non-normative until an implementation PR is accepted
> Scope: self-evolution capability fusion, not whole-project migration

## 1. Decision

PhyAgentOS remains the host architecture for Agent, Workspace, Session,
Watchdog, Preflight, Skill Runtime, and verification. Hephaestus is treated as
a source of validated self-evolution concepts, not as a package to be copied
or embedded wholesale.

The fusion unit is one capability per PR. Every capability must first be
expressed using PAOS schemas, registries, Workspace files, and Runtime hooks.
Hephaestus implementation classes are references for semantics and failure
behavior only; they are not a new PAOS dependency or a second Runtime.

## 2. Non-negotiable ownership

```text
PAOS Session                 scheduling and lifecycle truth
PAOS Attempt                 one execution/evidence boundary
Node Settlement              execution result, including unknown
Experience Record            historical, queryable evidence projection
Skill Candidate              unpromoted behavior change
Promotion Decision           governance result for a Candidate
```

No Experience, Candidate, prompt, checkpoint, or retry decision may rewrite
current-run Runtime truth. No self-evolution feature may change Target safety,
planner admission, calibration, IK, collision, attachment/force semantics, or
motion authorization.

## 3. Current PAOS gaps

PAOS already provides AgentLoop, Session persistence, Markdown Skill loading,
Runtime Session lifecycle, ResultWriter, and SessionVerifier. The missing
self-evolution substrate is:

1. independent Attempt identity and immutable evidence indexing;
2. node-level settlement with explicit `unknown` semantics;
3. deterministic evaluation separated from model-assisted evaluation;
4. causal attribution from an outcome to a Skill-use decision;
5. structured Experience Records separate from conversational memory;
6. versioned Skill registry and inactive Candidate model;
7. frozen replay plus matched/held-out/hazard evaluation;
8. promotion, hold, reject, and rollback state transitions;
9. experience-conditioned Skill selection with applicability bounds;
10. typed Agent turn/checkpoint lineage and evolution audit reports.

## 4. Revised PR sequence

### PR0 - Self-Evolution RFC

Document terminology, ownership, lifecycle, non-goals, and this dependency
graph. This PR must not change Runtime behavior.

### PR1 - Attempt, Evidence, and Minimal Settlement

Add versioned schemas for `attempt_id`, parent identity, context/decision
digests, execution lineage, artifact references, and terminal settlement. Extend
ResultWriter atomically while preserving existing SessionResult behavior.

### PR2 - Evaluator and Attribution Contracts

Define Runtime settlement, deterministic task evaluation, model-assisted
evaluation, and attribution as separate interfaces. Missing evidence produces
`unknown`, never an inferred success or failure.

### PR3 - Experience Store

Add typed, provenance-bearing Experience Records and query APIs. Keep
`MEMORY.md` and `HISTORY.md` as human/Agent-facing projections; they are not
promotion truth.

### PR4 - Versioned Skill Registry

Add Skill identity, version, parent version, active pointer, applicability
boundary, and rollback reference. Preserve compatibility with existing
workspace `SKILL.md` loading.

### PR5 - Skill Candidate and Patch Proposal

Represent an inactive behavior change with source Attempts, changed surface,
applicability, evaluation version, governance state, and rollback reference.
Candidate creation must not activate or mutate a Skill.

### PR6 - Frozen Replay and Candidate Evaluation

Freeze inputs, providers, seeds, budgets, capability registry, and Skill-use
decisions. Evaluate matched, held-out, and hazard splits with targeted-update
ablation before any promotion decision.

### PR7 - Promotion, Hold, Reject, and Rollback

Implement explicit Candidate state transitions, atomic activation, conflict
checks, and rollback. Human or governance approval remains required for
promotion until separately authorized.

### PR8 - Experience-Conditioned Selection

Use only promoted, applicability-matching Experience Records to influence
future Skill selection. Current Observation, Preflight, and Runtime admission
remain mandatory.

### PR9 - Typed Agent Turn and Continuation Checkpoint

Add turn identity, context projection, capability digest, decision digest,
pending calls, and resume semantics. A checkpoint is coordination evidence,
not execution or promotion authority.

### PR10 - Evolution Audit Report

Produce a trace from source Attempt to Experience, Candidate, evaluation split,
promotion decision, and future Skill-use. Report changes in SkillUse,
TaskOutcome, Efficiency, and Safety.

## 5. Required acceptance gates for every implementation PR

- Schema and backward-compatible loading tests.
- Accepted and rejected contract/preflight tests where applicable.
- Missing, malformed, stale, duplicate, timeout, cancel, and unknown paths.
- Replay or artifact-binding test proving identity preservation.
- No automatic promotion in the same PR that introduces a new evidence type.
- No new access from Agent/Skill code to Target SDK or backend internals.
- Explicit current limitations and deferred work in the PR description.

## 6. Evolution eligibility rule

Reflection, retry, memory writes, checkpoints, and patch proposals are not
evolution by themselves. A Candidate may affect future Skill-use only when its
source execution is attributable, its evidence is complete enough for the
claim, and matched/held-out/hazard evaluation supports the change.

