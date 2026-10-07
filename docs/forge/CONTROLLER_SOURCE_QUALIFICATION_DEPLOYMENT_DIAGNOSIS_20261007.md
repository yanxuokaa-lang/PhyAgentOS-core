# Controller Source Qualification Deployment Diagnosis

Date: 2026-10-07 (Asia/Shanghai)

## Scope

This diagnosis closes the deployment side of the generic failure reported as
`SimulationProbeError: qualified controller source digest drifted`. It applies
to any capability-bounded controller and does not depend on RGB objects, color
order, a benchmark destination, a camera name, a candidate index, or a fixed
arm.

## Observed Failure

The previous Runtime loaded controller source SHA-256 `f3770007...`, while its
configured MotionCapability and controller qualification package declared
source SHA-256 `6a1e9cdc...`. Planning and preparation could consume the
internally consistent old package, but Action admission rejected it before the
first simulator step. The authoritative result was `simulator_steps=0`,
`world_change_started=false`, and `recommended_action=fix_runtime_contract`.

The code repair in v12.9.6 made Readiness, Action, and monitored Runtime startup
compare evidence with the controller source identity captured by the loaded
process. That repair intentionally made stale deployment evidence impossible
to reuse. Installing the new Node without rebuilding qualification evidence
would therefore fail closed at startup rather than silently weaken admission.

## Root Cause

Controller qualification is evidence about one executable controller snapshot,
not about a controller name alone. Version numbers, the Node receipt, package
schema validation, and internal evidence digests proved that each artifact was
valid, but they did not prove that the currently loaded controller source was
the source that had been qualified.

The missing deployment operation was a source-bound evidence rollover:

1. derive left and right MotionCapability documents from the final controller
   source;
2. independently validate those documents without motion;
3. materialize and validate an isolated qualification plan;
4. obtain explicit simulation-only approval;
5. execute the isolated qualification and validate every trace;
6. obtain explicit evidence-promotion approval;
7. update the operator environment atomically at the existing eight evidence
   keys before starting the monitored Runtime.

This is a cross-system motion-admission boundary. The existing source SHA is
necessary here because Git state, semantic versions, database keys, types, and
ordinary tests cannot identify the Python source snapshot loaded by another
Runtime process.

## PAOS Ownership Boundary

- The Adapter derives capabilities and produces qualification traces.
- Independent validators verify package bindings and trace digests.
- The operator approves simulation execution and later evidence promotion.
- The Runtime consumes the promoted package but cannot approve itself.
- The Coordinator and AgentLoop retain task selection and recovery ownership.

No layer automatically creates an AgentTask, selects a candidate, changes an
arm, observes again, replans, retries, or sends an Action. A provider-owned
source mismatch remains non-retryable within the current revision and reports
`fix_runtime_contract`.

## Deployment Evidence

The old Runtime `runtime_4e1e061c14614c73` was normally stopped only after all
tasks were terminal and invocation/session/task-binding ownership was empty.
Skill `pick-place-workflow 3.0.3` and Node
`robotwin20_persistent_host 0.10.11` were installed from verified local
artifacts.

The new evidence root is:

`/home/yanxu/robotwin20-runtime/artifacts/paos-v12.9.7-20261007T134232Z/`

Both arms bind final controller source SHA-256
`a693ada44b775b5becaea7583f151f54b1f710bd36ed63bdb7925de7b5e394c7`.
The no-motion plan validation returned `validated_no_motion_plan`. After
operator approval, all eight isolated SAPIEN qualification tests passed,
including nominal position/velocity, over-limit rejection, contact load,
dropped step, stop, error, and reset paths. Independent evidence validation
returned `validated_pass`; the promoted qualification is `approved_pass` with
SHA-256 `beb6733e51afb6d0d3277c761599b5d3a34c07d819b3aac17200c9b6154e8350`.

Qualification simulation changed only its isolated SAPIEN world. The final
record continues to declare `motion_authorized=false`,
`benchmark_motion_authorized=false`, and `hardware_motion_authorized=false`.

## Runtime Acceptance

The operator environment keeps mode `0600` and changes only the eight existing
capability/qualification paths. The new Runtime is
`runtime_7791dd9a1eb94972` with empty active invocation, session, and task
bindings. Dora is running, Gateway is ready, and all 11 Tool contexts are
ready. The installed Node receipt and spawned executable are version `0.10.11`;
the binary SHA-256 matches the receipt.

Scene understanding remains provider-neutral: local `qwen3-vl-4b-awq` is the
primary provider and `gpt-6.1-sol` with `reasoning_effort=high` is the fallback.
No Query or Action was invoked during startup acceptance, and the task store
contains zero non-terminal tasks.

## Seven-Dimension Review

1. **Architecture: pass.** Source admission remains in the shared motion-policy
   owner; evidence production, approval, validation, and Runtime consumption
   remain separate.
2. **Correctness: pass.** Capability, plan, approval, trace evidence,
   validation, final qualification, loaded source, and Node receipt are bound
   to the expected identities.
3. **Recovery and idempotency: pass.** Old evidence remains immutable, the new
   root is unique, and source mismatch does not trigger automatic retry.
4. **Robotics safety: pass.** Only explicitly approved isolated simulation was
   stepped. Benchmark and hardware motion remain unauthorized.
5. **Extensibility: pass.** The mechanism is driven by provider/source records
   and existing environment keys, with no task-, object-, color-, camera-, or
   arm-specific control branch.
6. **Observability and maintainability: pass.** Runtime ID, source and artifact
   digests, approvals, validation status, Node receipt, ownership, and Tool
   readiness are inspectable without exposing credentials.
7. **AgentLoop autonomy and convergence: pass.** Startup performs no semantic
   task transition. Runtime contract failures stop deterministically and leave
   the next decision to the Agent/Coordinator boundary.

## Remaining Boundary

This proves installation, qualification, startup, and readiness. It does not
prove that a new manipulation task will grasp or place successfully. Task-level
acceptance must begin with a newly authorized AgentTask and must preserve the
normal observe, plan, readiness, Action, terminal-result, and reconciliation
boundaries.
