# Agent Instructions

You are a helpful AI assistant. Be concise, accurate, and friendly.

## Project Development Principles

Before proposing or implementing Runtime, Target, Skill, Policy, Adapter, Bridge, or
Perception changes, read `docs/DESIGN_PRINCIPLES.md`. Treat it as the single source of
truth: preserve Session/Workspace ownership, use explicit Contracts and Preflight,
access Targets only through `TargetSessionHandle`, keep safety fail-closed, and include
the required tests and evidence in the PR. Do not infer support for documented future
directions or treat Preflight acceptance as real-robot safety certification.

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
