# PAOS PR Contribution and Code-Drift Controls

> Status: proposal
> Authority: contribution-process guidance; not a Runtime contract
> Scope: fork workflow, reviewability, and prevention of implementation drift

## 1. Purpose

This document adapts the useful process safeguards from Hephaestus without
copying its repository-specific governance tooling into PAOS. These safeguards
exist to keep an implementation PR aligned with its accepted design. They do
not run inside a Target, Skill Runtime, SessionRunner, or Agent loop.

## 2. Measures that are applicable to PAOS

| Hephaestus measure | PAOS adaptation | Where it belongs | Put into feature PR? |
|---|---|---|---|
| Frozen source commit/tree | Record base commit and candidate SHA in PR metadata | fork/PR workflow | No runtime code |
| Principles Gate | Add a short design checklist to each plan/PR | contribution template or PR body | No runtime dependency |
| Agent Route Contract | Require decision owner, context, capability, evidence, settlement, cancel/resume, promotion, rollback | architecture RFC and PR body | Only as documentation |
| Layer/owner map | Check new files against PAOS extension points | review checklist | No |
| Canonical/compat/legacy test classes | Use pytest markers and state which tests are primary proof | tests and PR metadata | Test markers only |
| Scope closure | Compare changed files to declared Done/Not-done surface | reviewer workflow | No |
| Exact diff and line accounting | Run `git diff --check`, inspect changed paths, and record tests | local workflow | No |
| Immutable evidence artifacts | Use for self-evolution Attempt/Candidate evidence | PAOS runtime feature | Yes, only when that feature owns it |
| Task direction closeout | Keep local task notes or issue checklist separate from source code | local/untracked workflow | No |

The last two rows are product capabilities only when the corresponding PAOS
feature is being implemented. The other rows are process controls and must not
be bundled as hidden runtime behavior.

## 3. Measures that should not be copied

- Hephaestus-specific `.task/current.md` schema and repository paths.
- Hephaestus workflow-governance YAML, cleanup baseline, or import exceptions.
- Hephaestus module names as PAOS public APIs.
- Runtime checks that inspect Git history during an Agent or Target run.
- Absolute local paths, private artifact roots, internal memory references, or
  unpublished hardware evidence.
- A second Skill loader, second Session registry, or second promotion service.

PAOS may later adopt a small generic contribution checker, but that should be a
separate tooling proposal and must not be a prerequisite for Runtime startup.

## 4. Two-document and PR policy

Use one non-normative architecture RFC for the overall direction. Do not
pre-commit a set of documents that claim all future PRs are already final.

For each implementation PR, include only the contract and design text needed
for that capability together with code and tests. Keep the broader roadmap in
the RFC. A design document becomes normative only after the corresponding PR
is accepted and its tests establish the claimed behavior.

## 5. Fork and branch discipline

The fork is safe for staging docs and draft PRs; pushing to a fork does not
change the upstream repository until a PR is opened or merged. Branch ancestry
does affect the PR diff.

Before creating a PR:

1. Fetch the verified upstream repository and identify its actual default
   branch (`main`, `dev`, or another branch).
2. Create a fresh feature branch from that upstream branch.
3. Keep unrelated dependency edits, generated indexes, editor files, and local
   experiments out of the branch.
4. Inspect `git diff --stat <upstream-base>...HEAD` before pushing.
5. Use one feature branch and one focused PR per capability; use explicit
   `Depends on #...` links for stacked work.

## 6. Current workspace warning

The local `preview` branch is not a clean upstream feature base. It tracks the
fork's `origin/preview`, while the worktree also contains unrelated changes in
`pyproject.toml` and untracked `.codegraph/` and `.cursor/` paths. These must
not be included in the architecture RFC or any feature PR.

## 7. Review checklist for code-drift prevention

- Does the implementation still match the accepted extension point?
- Did any new module become an accidental truth owner?
- Are proposal, current-run truth, evidence, memory, and promoted strategy
  still separate?
- Did the changed surface remain within the declared Candidate boundary?
- Are old routes explicitly compatibility, legacy, deleted, or still active?
- Do tests prove the active route rather than only a compatibility route?
- Did the PR add hidden dependencies, generated files, or unrelated formatting?
- Can the branch be rebased onto the intended upstream base without unrelated
  commits appearing in the diff?

## 8. Separation guarantee

The drift controls in this document are review and branch practices. They do
not add PAOS dependencies, runtime imports, Session fields, Target behavior,
or Agent tools. A future feature PR may reference these controls in its PR
description, but it must not silently implement them as part of the feature.

