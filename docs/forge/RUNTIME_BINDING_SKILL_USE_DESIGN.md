# Runtime Ownership and Skill Use Migration

Status: accepted architectural direction; only identity-validation extraction is
implemented in the first stage. Current task creation still requires primary
Skill activation. This document does not describe already available behavior.

## Ownership

| Concern | Owner |
| --- | --- |
| Goal, PlanGraph, revisions, task lifecycle | AgentTaskCoordinator and persisted task |
| Runtime instance, Gateway identity and execution ownership | Task Runtime binding |
| Available and authorized operations | Runtime/Gateway deployment policy |
| Exact Tool contract used | Task-owned Tool binding, persisted before invocation |
| Method choice and composition | Agent |
| Skill name/version/instructions used at a decision | Append-only Skill-use record |
| Invocation/attempt/terminal result | Existing Tool execution records and Gateway |
| Task outcome | Existing final Verifier |
| Future method improvement | Optional evolution extension consuming settled evidence |

Runtime deployment currently uses manifest-v2 Skill packaging. Retain that
installation mechanism during migration, but distinguish the deployment bundle
from methods selected by the Agent. A method update must not require replacing a
live execution deployment; a deployment update must still respect task ownership.

## Required Behavior

1. A natural-language task may be created without activating a method Skill.
   An execution task selects a ready managed Runtime, or stays explicitly
   planning-only when no execution target is available. It cannot silently turn
   planning-only state into physical authority.
2. Before first use, resolve a Tool from that Runtime's authorized capability
   catalog, validate readiness/semantics, and persist the exact contract. Reuse
   the existing ToolSpec digest, not a new integrity scheme. Merely appearing in
   GET /tools is insufficient if deployment policy does not authorize it.
3. Initial Tool contracts are not the entire Skill allowlist. Later tools can be
   added only from the same authorized Runtime; existing Tool contracts cannot be
   replaced in place. Persist additions transactionally before caller intent.
4. Agent may use zero, one or multiple Skills. Each selected version and exact
   instruction snapshot is associated with the decision, node and attempt where
   it was used. Tool use is not proof of Skill use. Do not infer missing attribution.
5. Selecting a new Skill version affects a subsequent decision, not a pending
   model decision or Action. Activation alone is not movement permission. New
   constraints must still pass PlanRevision and Tool admission.
6. Pending/unknown Actions retain their original Runtime and contract until
   authoritative reconciliation. No automatic resend, Runtime transfer or
   historical Skill-version substitution is allowed.
7. Verifier receives actual execution contracts and actual Skill-use snapshots;
   method advice remains non-authoritative. Experience grouping uses the version
   used at that decision, not the latest installed Skill or deployment version.

## Migration Stages

### 1. Identity Separation

Extract Runtime instance/profile/Gateway equality checking from the legacy
ForgeSkillBinding resolver. Retain old deployment Skill/version checks for legacy
tasks. Add regression coverage for Runtime replacement and all identity fields.
This is an integrated preparatory refactor, not the new task path.

### 2. Persisted Ownership and Tool Use

Introduce explicit runtime_binding and tool_bindings for new task records,
independently of primary_skill_binding. Update record validation, SQLite round
trips, task summaries, planning policy lookup, revision ownership and cancellation
cleanup together. Keep legacy decode and validation; no bulk reinterpretation of
active records. Retain one nonterminal task per workspace in this migration.

New Tool enrollment uses Coordinator transactions and existing caller-intent
ordering. Concurrent enrollments cannot replace an already selected contract;
failed enrollment creates no execution record claiming success. Runtime switch
checks account for both old and new binding representations.

### 3. Method Selection and Attribution

Remove primary-only selection as the prerequisite for new task creation. Record
Skill uses through the existing activation/Agent decision flow, with selected
version and instruction content captured before the decision. Connect these
records to node/attempt evidence, including failed and cancelled turns. A task
without a Skill use remains valid and has no fabricated Skill attribution.

Update Agent tools, context guidance and CLI together. Do not introduce a second
Runner, fixed workflow or per-task YAML. Avoid repurposing legacy fields under a
new name without migrating their consumers.

### 4. Recovery, Verification and Experience

Migrate reconcile_nonterminal, status/result/stop, Runtime reference cleanup,
VerificationRequestBuilder lineage checks, planning admission/context projection,
TaskOutcomeSource and experience binding. Test process restart and mixed
old/new database records. Do not enable evolution as part of this migration.

### 5. Release and Integration

Run no-motion regression and isolated bundle installation, then explicitly
dispose of old test ownership before switching the live deployment. Create a new
task without activation and let the Agent select methods from fresh evidence.
Only separately authorized simulation execution may test physical Actions.

## Six-Dimensional Acceptance

- Architecture: task creation without a Skill, multiple Skill uses, Tool contracts
  enrolled on demand, and a single Coordinator/Gateway execution path.
- Failure/recovery: startup reconciliation, unknown Action, cancellation, crash
  before/after contract enrollment, and rejection of Runtime/Tool drift.
- Permissions/safety: unauthorized Tool cannot enroll, method selection cannot
  authorize motion, in-flight Actions cannot change Runtime or contract.
- Configuration/reproduction: mixed legacy/new records reload; deployment and
  method updates are independent; version provenance survives process restart.
- Maintainability: no fabricated Skill, duplicate task state, parallel Runner or
  fallback to unbound execution. Existing public APIs migrate together.
- Observability: each invocation traces to Runtime/contract, and each actual
  method use traces to its decision and historical version; Verifier cannot use
  newer instructions to reinterpret prior attempts.

Concrete safety boundary: a different Runtime may reuse a Tool name while
controlling a different world, and a changed contract may alter Action semantics.
Task IDs alone do not detect either failure. Preserve existing execution-boundary
identity and contract checks; no additional general gate/hash is required.
