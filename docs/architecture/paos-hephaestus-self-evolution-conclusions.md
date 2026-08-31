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

## 3.1 Public Tool Boundary For Perception And Grasp

The public PAOS surface must expose physical intent and evidence boundaries, not
provider, simulator, or robot implementation steps. The recommended ToolSpecs
are:

| ToolSpec | Semantics | Public responsibility |
|---|---|---|
| `scene.observe` | Query | Return a measured RGB-D/state observation with sensor references, frame, calibration identity, time, freshness, and scene revision. |
| `scene.understand` | Query | Derive entity claims, relations, spatial envelopes, confidence, and ambiguity from one named observation. |
| `grasp.propose` | Query | Return a provider-neutral candidate set with candidate identity, frame/calibration binding, provenance, and bounded funnel evidence. |
| `manipulation.prepare` | Query | Perform non-mutating workspace, IK, collision, and complete-route admission for a selected candidate; return a short-lived preflight reference, never motion authority. |
| `object.acquire` | Action | Run the bounded approach/contact/close/lift/hold workflow and return typed execution and settlement facts. |
| `object.place` | Action | Run the bounded transport/descent/release/retreat workflow and return typed execution and settlement facts. |
| `scene.acquire_active_view` | Action | Move a camera-bearing embodiment only when a new view is explicitly required and admitted. |
| `execution.session` | Session, optional | Correlate a continuous capability lifecycle; it does not create a cross-Tool lease or grant motion permission. |

`task_outcome` is deliberately not a public Tool. User-level success remains
owned by `AgentTask finalize` and `TaskVerificationContract`, using ToolResult,
evidence, and the task criteria. Likewise, `approach`, `grasp`, `lift`, `place`,
and `retreat` are internal phases of bounded Actions rather than Agent-facing
Tools. This avoids both RoboTwin-specific APIs and an Agent-level robot action
script.

Every spatial ToolSpec must make frame, units, tolerances, readiness,
calibration requirements, timeout, cancellation/stop, and `unknown` semantics
inspectable through Tool context. `manipulation.prepare` and provider output
must never set `motion_authorized=true`; final authorization stays in the
Gateway/Runtime admission path.

## 3.2 Internal Gateway Module Boundary

The following Hephaestus capabilities should be internal interfaces behind the
ToolEndpoint or Skill Runtime. They are reusable implementation seams, not new
PAOS Agent tools:

| Internal interface | Absorbed responsibility |
|---|---|
| `ObservationSource` | Sensor capture, time association, and measured artifact materialization. |
| `FrameCalibrationResolver` | Intrinsics/extrinsics, frame transforms, calibration identity, and missing-calibration rejection. |
| `SceneInterpreter` | Detection, segmentation, semantic scene graph, relations, confidence, and ambiguity. |
| `GeometryIsolator` | Observation-backed masks, local/object point clouds, obstacle clouds, and support geometry. |
| `EntityAssociator` | Cross-observation identity continuity, revision binding, and stale-evidence rejection. |
| `GraspCandidateProvider` | AnyGrasp, GraspGen, GraspNet, heuristic, or future providers behind one provider-neutral result. |
| `CandidateCanonicalizer` | Provider pose/axis translation into the canonical candidate contract with adapter provenance. |
| `CandidatePostprocessor` | Score threshold, model collision, NMS, truncation, and reconciled funnel counts. |
| `ExecutionGeometryAdapter` | Candidate-to-TCP/hand/gripper geometry and bounded pregrasp/retreat construction for one profile. |
| `MotionAdmissionPlanner` | Workspace, IK, collision, pregrasp checkpoint, and complete transport/descent/retreat admission. |
| `AcquirePlaceExecutor` | Bounded Action execution, cancellation, stop handling, and unknown outcomes. |
| `EvidenceSettler` | Arrival, closure, attachment, stability, release, and post-action evidence settlement. |

The adapter/profile owns model names, provider variants, robot geometry,
camera layout, control mode, simulator configuration, and evaluator details.
The public Tool contract owns only the semantic fields and references needed to
bind those details. Missing measured geometry, transforms, or calibration must
return `unavailable`/rejection on the canonical route; metadata or simulator
ground truth cannot silently become perception evidence.

The candidate funnel is retained as compact evidence (for example, decode,
collision, NMS, translation, shortlist, and planner-admission stages), while
large point clouds, trajectories, and diagnostics remain ArtifactRefs. Provider
scores, NMS, model collision, and planner diagnostics are advisory or
qualification facts; none authorizes motion.

## 3.3 Stage Settlement For Self-Evolution

An `object.acquire` or `object.place` Action may contain multiple internal
phases, but its terminal result must include a bounded `CapabilityOutcomeSummary`
for attribution:

```text
capability_phase
status
failure_owner
failure_code
world_change_started
outcome_known
evidence_availability
artifact_refs
bounded_metric_names
```

The summary is a redacted projection, not a second settlement protocol. It lets
`ExperienceCoordinator` distinguish perception unavailable, candidate empty,
planner admission rejected, closure/attachment unconfirmed, and placement
verification failure. It must not contain object-specific answers, coordinates,
trajectories, provider-private payloads, RoboTwin task fields, or hardware
credentials. Evolution may learn observation refresh, candidate ranking,
provider/profile selection, operation order, and bounded recovery; it may not
change safety gates, planner legality, evidence validity, or motion authority.

## 4. Current Status And Gaps

`origin/main` already provides the self-evolution substrate needed for the
first fusion PRs: immutable Skill activation/binding, task-level outcome
envelopes, redacted TaskEpisodes, asynchronous reflection, scoped Lessons,
Skill Candidates, support thresholds, content validation, atomic Skill writes,
and rollback. Do not reimplement these as new services.

The material gaps are capability-specific rather than another evolution layer:

1. the provider-neutral Tool Bundle and the internal perception/geometry/planner
   seams described above;
2. authoritative entity identity, measured pose/geometry, attachment/lift/place
   evidence, and failure/unknown semantics in ToolEndpoint results;
3. a bounded phase-summary projection so ExperienceCoordinator can attribute
   failures without exposing low-level provider payloads;
4. a continuous workflow that can issue multiple bounded Actions/Sessions under
   one AgentTask and PlanRevision lineage;
5. independent simulated workflows that supply enough evidence to distinguish
   reusable success from infrastructure, backend-evaluator, or verifier failure;
6. replay and held-out/hazard evaluation only where real candidate data shows
   that the existing promotion gates are insufficient.

## 5. Revised PR Sequence For Forge

### PR0 - Baseline And Capability RFC

Lock the `origin/main` commit, Forge Developer Manual version, target simulator,
and the exact grasp capability boundary. This PR changes documentation only.

### PR1 - Provider-Neutral Tool Contract

Define the public Query/Action/optional Session ToolSpecs from section 3.1,
including strict schemas, frames, units, tolerances, readiness, concurrency,
timeout, cancel/stop, and unknown semantics. Do not expose provider phases or
make `task_outcome` a Tool.

### PR2 - Fake Gateway And Conformance Tests

Test ToolSpec binding, context, Action/Session admission, invocation and attempt
identities, pending/terminal/unknown results, cancel/stop ownership, stale
references, and AgentTask aggregation using a mock Gateway.

### PR3 - Simulator/Robot Skill Bundle Adapter

Package the Gateway, ToolEndpoints, profile/dataflow, and locked artifacts as a
manifest-v2 Skill Bundle. RoboTwin/SAPIEN or real-hardware details stay in the
profile and adapter; no Agent-to-simulator, Agent-to-Dora, or SDK dependency is
added to PAOS core.

### PR4 - Observation And Scene Understanding

Implement `scene.observe` and `scene.understand` using measured artifacts,
frame/calibration identity, scene revisions, entity continuity, and explicit
unavailable/stale results. Ground-truth simulator state is evaluator data, not
perception input.

### PR5 - Candidate Proposal

Implement `grasp.propose` and the internal provider, canonicalizer, and funnel
interfaces. Preserve candidate identity, provenance, units, frame/calibration
binding, empty-candidate semantics, and host-owned `motion_authorized=false`.

### PR6 - Preparation And Bounded Acquire/Place

Implement `manipulation.prepare`, `object.acquire`, and `object.place` through
one canonical Gateway path. Keep preflight non-mutating, revalidate current
scene/runtime state before Action admission, and emit bounded phase summaries
and evidence references.

### PR7 - Long-Horizon Simulation Workflow

Run one RoboTwin profile workflow through a single AgentTask and execution
context, retaining meaningful observation, proposal, preparation, Action, and
outcome records without creating a record per simulator step. Map simulator
success to backend evaluation only.

### PR8 - Generic Verification And Outcome Projection

Connect before/after captures, terminal ToolResult data, backend evaluation, and
phase summaries to the existing `TaskVerificationContract` and
`ForgeTaskOutcomeSource`. Do not add a grasp-specific verifier or a second
settlement protocol.

### PR9 - Experience Integration

Use the existing `ExperienceCoordinator` to create TaskEpisodes,
FailureObservations, and SkillCandidates from the workflow. Evolution may target
provider/profile choice, candidate ranking, observation refresh, operation order,
and bounded recovery; it cannot mutate safety or admission rules.

### PR10 - Evaluation Extension (Only If Needed)

Add replay, matched, held-out, hazard, and later real-hardware profile coverage
only when the preceding PRs demonstrate an evaluation gap. Existing support
thresholds, conflict blocking, content checks, atomic writes, and rollback remain
the default.

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
