# Agent Instructions

You are a helpful AI assistant. Be concise, accurate, and friendly.

## Scheduled Reminders

Before scheduling reminders, check available skills and follow skill guidance first.
Use the built-in `cron` tool to create/list/remove jobs (do not call `PhyAgentOS cron` via `exec`).
Get USER_ID and CHANNEL from the current session (e.g., `8281248569` and `telegram` from `telegram:8281248569`).

**Do NOT just write reminders to MEMORY.md** — that won't trigger actual notifications.

## Heartbeat Tasks

`HEARTBEAT.md` is checked on the configured heartbeat interval. Use file tools to manage periodic tasks:

- **Add**: `edit_file` to append new tasks
- **Remove**: `edit_file` to delete completed tasks
- **Rewrite**: `write_file` to replace all tasks

When the user asks for a recurring/periodic task, update `HEARTBEAT.md` instead of creating a one-time cron reminder.

## 通用架构与编码原则 / General Architecture and Coding Principles

These principles apply to every new integration, not only robotics or
simulation work. They constrain ownership and dependency direction rather than
particular vendor names, environments, or class names.

### 1. Dependency direction

Upper layers define stable domain semantics; lower layers provide mechanisms.
The dependency direction is:

```text
task semantics / Agent -> domain capability ports -> Providers/Adapters -> environment or device
```

An implementation replacement must not force changes in the caller's domain
model, Tool contract, or AgentLoop route.

### 2. Mechanism and policy separation

Generic modules compose workflow, validation, evidence, and lifecycle policy.
Providers implement environment-specific capture, transformation, planning, or
execution mechanisms. Do not move environment behavior into a generic module
just because one provider currently needs it.

### 3. Domain objects over implementation objects

Cross-boundary inputs and outputs use stable domain objects and opaque
references. SDK handles, filesystem paths, scene-node names, device objects,
and backend-specific representations stay inside the Adapter boundary.

### 4. Substitutability

Judge generality by replacement, not by the absence of specialized code. A
provider, backend, data source, or execution environment should be replaceable
without changing its caller. For a shared abstraction, add at least one
substitution test when the change's risk and blast radius justify it.

### 5. Minimal public contracts

Public interfaces contain only semantics that remain valid across implementations.
Provider-only fields belong in provider metadata or an Adapter-private context.
Do not widen a shared contract to accommodate one environment without a second
independent use case.

### 6. Evidence lineage

Executable conclusions must be traceable through one evidence chain:

```text
observation -> interpretation -> measurement -> candidate -> preparation -> execution feedback -> settlement
```

Do not fabricate missing facts, silently mix revisions, or pair a fresh result
with stale preparation or execution evidence.

### 7. Single lifecycle owner

Each state has one authoritative owner. Other modules consume projections or
receipts and must not create shadow schedulers, duplicate state machines, or
parallel settlement stores. Preserve existing Runtime, Coordinator, AgentLoop,
and Adapter ownership boundaries.

### 8. Capability discovery before execution

Callers discover and validate capabilities before selecting or executing a
mechanism. Unsupported, unavailable, ambiguous, or unknown outcomes remain
explicit states; fallback must not convert them into success.

### 9. Composition over duplication

Extend behavior by composing existing ports, Tool contracts, and lifecycle
hooks. Add a new abstraction only when it represents a stable domain seam or
removes real duplication across independent implementations.

### 10. Failure-first design

Before implementing the success path, define behavior for incomplete input,
stale evidence, ambiguity, provider failure, preparation failure, cancellation,
and unknown execution outcomes. Preserve failure phase, owner, evidence, and
recovery boundary.

### 11. Risk-proportional validation

Validation depth must match change risk and blast radius. A shared public
contract, cross-system boundary, safety boundary, or irreversible action needs
substitution and failure-path tests. A local documentation or formatting change
does not require a new multi-provider harness. Do not add gates, hashes, or
schemas without a concrete failure scenario and a demonstrated gap in existing
controls.

### 12. Agent implementation order

For a new capability, follow this order:

```text
define ownership -> define domain port -> define Provider seam -> write no-motion/contract tests
-> wire one implementation -> run substitution or compatibility tests -> enable live execution only when authorized
```

Do not start from a concrete environment controller and retrofit the generic
interface afterwards.

### 13. Architecture review questions

Before coding, state explicitly:

- Which behavior belongs to the generic domain layer?
- Which behavior belongs to the Provider or Adapter?
- What can be replaced without changing the caller?
- Which evidence proves the result and where is its freshness boundary?
- Which component owns lifecycle, cancellation, settlement, and recovery?
- What is the smallest test that would expose an abstraction leak?

The review must find and resolve Blocker/Major architecture findings before
acceptance. The acceptance record must distinguish contract evidence,
provider evidence, and live execution evidence.

### 14. 通用性判定 / Generality test

An abstraction is general when it owns stable semantics and accepts changing
mechanisms through explicit ports. It is not general merely because it has a
generic name, and it is not invalid merely because an Adapter contains
environment-specific code.
