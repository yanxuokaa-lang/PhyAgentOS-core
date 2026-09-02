# Forge v1.0 Contribution and Drift Controls

> Status: contribution-process guidance only. It is not Runtime behavior and is not an Agent-facing
> Tool contract.
>
> 本文是贡献流程规则，不是 Runtime 行为，也不是 Agent-facing Tool 契约。

## Baseline lock

Every feature or documentation PR records:

1. the exact `origin/main` base commit;
2. the PAOS Developer Manual and Forge Integration Contract versions used for review;
3. the selected extension point (`ToolEndpoint`, `ToolSpec`, Skill Bundle profile, provider/adapter,
   AgentTask, or ExperienceCoordinator);
4. the files and tests that prove the changed boundary.

The current v1.0 baseline is `c5740a5`. `preview` is an archived divergent branch and is never a
feature base. The local fork's `origin/main` and `upstream/main` must be compared before starting a
new PR; a non-zero diff requires an explicit decision.

## PR scope ladder

| Tier | Change | Required proof |
|:--|:--|:--|
| L1 | provider, adapter, or Query Tool | schema, context, rejected/accepted cases, no-motion proof |
| L2 | Action/Session or Bundle profile | lifecycle, ownership, pending/unknown/cancel/stop, cleanup, docs |
| L3 | AgentTask, Verification, Experience, or public state | migration test, rollback/failure matrix, full integration and architecture review |

Documentation-only process controls stay outside feature Runtime code. Do not add Git inspection,
repository state parsing, or PR state checks to Gateway, Skill Runtime, AgentTask, or Experience.

## Drift checklist

Before opening a PR:

```bash
git fetch origin main upstream main
git diff --stat origin/main...HEAD
git diff --check
```

Then confirm that public ToolSpecs remain provider-neutral, binding hashes and Runtime identities are
explicit, and no new direct import path connects Agent code to Dora, RoboTwin, SAPIEN, or a vendor SDK.
For Action/Session changes, include the exact no-motion or independently authorized runtime command;
never infer safety from a successful admission response.

## What is deliberately not migrated

- historical `preview` Target/Adapter module paths;
- old Session-centered queues or task files;
- Hephaestus-specific workflow-governance YAML;
- a second memory, receipt, evaluator, verifier, or promotion database;
- defensive code that hashes Git history during a task;
- defensive prose that repeats the same invariant in every Skill document.

Those concerns either remain historical reference material or are expressed once in the official
manuals and this contribution guide.

## Fork and worktree discipline

Keep one canonical v1.0 worktree for new work and preserve `preview` as an archive branch. Feature
branches are created from `origin/main`, pushed to the fork, and later opened as focused PRs against
the upstream `main`. A docs PR may migrate architecture conclusions without importing unrelated
runtime code or benchmark assets.

## 中文执行规则

每个 PR 锁定 `origin/main` 提交，说明扩展点、所有权、不变量和测试证据。代码防漂移措施只能
存在于贡献流程和审查材料中，不得混入 Runtime。`preview` 仅作历史参考；所有新代码和新文档
都从 PAOS v1.0 `main` 派生。
