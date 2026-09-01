# PAOS PR Contribution and Code-Drift Controls

> Status: proposal
> Authority: contribution-process guidance; not a Runtime contract
> Scope: fork workflow, reviewability, and prevention of implementation drift

> Compatibility note: The normative implementation baseline is PAOS v1.0.0
> `main` and its Developer/Integration manuals. This document governs process
> only and does not redefine Tool API or Runtime behavior.

## 1. Purpose

This document adapts the useful process safeguards from Hephaestus without
copying its repository-specific governance tooling into PAOS. These safeguards
exist to keep an implementation PR aligned with its accepted design. For the
`upstream/main` Forge baseline they do not run inside a ToolEndpoint, Gateway,
Skill Bundle, AgentTask, or Agent loop.

## 2. Baseline Lock

The default fusion target is `upstream/main` and its v1.0 Forge Developer
Manual. Before opening an implementation branch, record the exact base commit,
manual version, target simulator, and capability boundary. The `preview`
branch is a divergent v0.1.x Session Runtime line; its Target/Adapter/
SkillRuntime code is compatibility material, not a second execution path for
Forge.

## 3. Stop That Shit modes

Use the smallest mode that matches the task:

| Mode | Use | Default effect |
|---|---|---|
| `change` | Implement an explicitly scoped feature or document change | Edits are allowed only for the requested result and necessary consequences |
| `review` | Review a design, diff, or PR | Report findings; do not edit |
| `monitor` | Wait for CI, an upstream response, or another external state change | Do not broaden the task while waiting |
| `status` / `runtime` | Inspect advisory Guard state | Read-only inspection |
| `lock change` | Edit only an already-known exact file set | Hard file boundary; do not invent additional targets |

For PAOS self-evolution work, use `review` while comparing the architecture or
PR plan, `lock change` for a bounded RFC or contract document, and `change` for
one implementation capability. `monitor` is not a reason to add speculative
hardening. The Skill is advisory; unless a host Guard explicitly reports an
armed denial, it must not be described as having blocked an action.

## 4. Stop Ladder for scope control

Before adding code, a schema field, a dependency, a compatibility layer, or a
paragraph of defensive documentation, answer in order:

1. Did the user or accepted PR scope request it?
2. Is it necessary to complete the current result?
3. What reachable caller, data path, test, deployment state, or acceptance gate
   proves that necessity?
4. Would omitting it make the current result fail, unsafe, or false?

If the answer remains no, do not add it. This rule prevents speculative retry,
fallback, hashing, dependency, state-machine, and documentation growth. It
does not remove a safety, privacy, compatibility, or failure disclosure that is
required at the decision point to keep the result correct or safe.

## 5. Defensive-code and defensive-documentation boundary

Do not add the following merely because they might help future work:

- a second Session, Memory, Skill Registry, Evaluator, or Promotion service;
- generic retries, caches, fallbacks, hashes, or dependency pins without a
  reachable current caller and acceptance test;
- Runtime logic that inspects Git history, PR state, or local workflow files;
- warnings, caveats, or hypothetical failure narratives unrelated to the
  current decision or user action;
- duplicate copies of `DESIGN_PRINCIPLES.md`, the RFC, or existing contracts.

Keep documentation focused on Goal, Non-goals, owner, reachable failure/unknown
semantics, required tests, rollback, and current limitations. Keep process
details in this contribution document or the PR description, not in Runtime
instructions or user-facing Skill text.

Safety-critical behavior remains required: fail-closed handling of stale or
unknown state, invalid actions, missing evidence, cancellation, timeout, and
hardware stop semantics must not be removed merely to reduce defensive code.

## 6. Measures that are applicable to PAOS

| Hephaestus measure | PAOS adaptation | Where it belongs | Put into feature PR? |
|---|---|---|---|
| Frozen source commit/tree | Record base commit and candidate SHA in PR metadata | fork/PR workflow | No runtime code |
| Principles Gate | Add a short design checklist to each plan/PR | contribution template or PR body | No runtime dependency |
| Agent Route Contract | Require decision owner, context, capability, evidence, settlement, cancel/resume, promotion, rollback | architecture RFC and PR body | Only as documentation |
| Layer/owner map | Check new files against PAOS extension points | review checklist | No |
| Canonical/compat/legacy test classes | Use pytest markers and state which tests are primary proof | tests and PR metadata | Test markers only |
| Scope closure | Compare changed files to declared Done/Not-done surface | reviewer workflow | No |
| Exact diff and line accounting | Run `git diff --check`, inspect changed paths, and record tests | local workflow | No |
| Immutable evidence artifacts | Use existing ToolExecutionRecord/TaskEpisode evidence | Forge/Experience feature | Yes, only when that feature owns it |
| Task direction closeout | Keep local task notes or issue checklist separate from source code | local/untracked workflow | No |

The last two rows are product capabilities only when the corresponding PAOS
feature is being implemented. The other rows are process controls and must not
be bundled as hidden runtime behavior.

## 7. Measures that should not be copied

- Hephaestus-specific `.task/current.md` schema and repository paths.
- Hephaestus workflow-governance YAML, cleanup baseline, or import exceptions.
- Hephaestus module names as PAOS public APIs.
- Runtime checks that inspect Git history during an Agent or Target run.
- Absolute local paths, private artifact roots, internal memory references, or
  unpublished hardware evidence.
- A second Skill loader, second AgentTask registry, second execution protocol, or second promotion service.

PAOS may later adopt a small generic contribution checker, but that should be a
separate tooling proposal and must not be a prerequisite for Runtime startup.

## 8. Two-document and PR policy

Use one non-normative architecture RFC for the overall direction. Do not
pre-commit a set of documents that claim all future PRs are already final.

For each implementation PR, include only the contract and design text needed
for that capability together with code and tests. Keep the broader roadmap in
the RFC. A design document becomes normative only after the corresponding PR
is accepted and its tests establish the claimed behavior.

## 9. Fork and branch discipline

The fork is safe for staging docs and draft PRs; pushing to a fork does not
change the upstream repository until a PR is opened or merged. Branch ancestry
does affect the PR diff.

Before creating a PR:

1. Fetch the verified upstream repository and identify its actual default
   branch (`main`, `dev`, or another branch).
2. Create a fresh feature branch from that upstream branch.
3. Keep unrelated dependency edits, generated indexes, editor files, legacy
   preview Runtime files, and local experiments out of the branch.
4. Inspect `git diff --stat <upstream-base>...HEAD` before pushing.
5. Use one feature branch and one focused PR per capability; use explicit
   `Depends on #...` links for stacked work.

### 9.1 Verified fork and Forge worktree recipe

Fork the official `PhyAgentOS/PhyAgentOS` repository into the contributor's
account. The verified fork used for this work is
`yanxuokaa-lang/PhyAgentOS-core`, which now publishes `main` synchronized with
the official v1.0.0 baseline. Use `upstream/main` as the authoritative base and
refresh it before each PR.

For a fresh local checkout, clone the fork's default branch, then fetch the
official Forge baseline and create the feature branch from `upstream/main`:

```bash
git clone --branch main https://github.com/yanxuokaa-lang/PhyAgentOS-core.git PhyAgentOS-forge
cd PhyAgentOS-forge
git remote add upstream https://github.com/PhyAgentOS/PhyAgentOS.git
git fetch upstream main
git switch -c feature/<capability> --track upstream/main
```

When an existing local clone already contains the verified `upstream/main`
object, an isolated worktree is equivalent and avoids modifying the checked-out
`preview` files:

```bash
cd <existing-PhyAgentOS-clone>
git remote add upstream https://github.com/PhyAgentOS/PhyAgentOS.git
git fetch upstream main
git worktree add -b feature/<capability> \
  <path>/PhyAgentOS-forge upstream/main
```

Verify the new worktree before editing:

```bash
git remote -v
git branch -vv
git rev-parse HEAD upstream/main
git status --short
git diff --stat upstream/main...HEAD
```

The expected result is a clean feature branch whose `HEAD` equals the current
`upstream/main`, with no diff before implementation. Push implementation
branches to the fork and open the PR from the fork branch into the official
`PhyAgentOS/PhyAgentOS:main` branch:

```bash
git push -u origin feature/<capability>
```

The verified setup used `c5740a58bbc53a68aa50be9f44e94d3a90e41446` as both
`HEAD` and `upstream/main`. This hash is an audit snapshot, not a permanent
pin; refresh it before each PR and record the new value in the PR metadata.

## 10. Current workspace warning

The local `preview` branch is not the Forge v1.0 feature base. It tracks the
fork's `origin/preview`, while the worktree also contains unrelated changes in
`pyproject.toml` and untracked `.codegraph/` and `.cursor/` paths. These, plus
legacy preview Runtime files, must not be included in a Forge architecture RFC
or feature PR.

## 11. Review checklist for code-drift prevention

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

## 12. Separation guarantee

The drift controls in this document are review and branch practices. They do
not add PAOS dependencies, runtime imports, Session fields, Target behavior,
or Agent tools. A future feature PR may reference these controls in its PR
description, but it must not silently implement them as part of the feature.

## 13. Perception-Grasp PR Boundary Review

The reviewed Hephaestus perception/grasp chain is accepted as a source of
semantics and failure evidence, with the following PAOS boundary:

```text
AgentTask / Skill workflow
  -> scene.observe / scene.understand / grasp.propose (Query)
  -> manipulation.prepare (non-mutating Query)
  -> object.acquire / object.place (bounded Action)
  -> AgentTask finalize + TaskVerificationContract

Gateway-internal only:
  ObservationSource -> calibration -> scene/geometry -> provider/canonicalizer
  -> funnel -> planner admission -> execution geometry -> settlement evidence
```

The first functional capability after the contract, fake Gateway, and Bundle
scaffolding is `scene.observe` (PR4). It is a provider-neutral Query that
returns one measured observation reference plus frame, calibration identity,
timestamp, freshness, and scene revision. It must be useful with both a
simulator and a real sensor, while simulator ground truth remains evaluator
data. No Action or Session is required for this first capability.

The public interface must not contain `robotwin_*`, provider names, simulator
SDK types, `task_name`, `task_config`, evaluator scripts, or low-level phases
such as `approach` and `lift`. These remain Skill Bundle profile, adapter, or
backend-evaluator data. `execution.session`, when used, must be a real,
explicitly owned stateful lifecycle with common status/result/stop semantics;
correlation alone is not a Session and it never creates a cross-Tool lease.
`task_outcome` remains PAOS finalization, not a new Tool.

Before accepting a capability PR, reviewers should verify:

- the public ToolSpec is semantic and backend-neutral;
- provider outputs carry candidate identity, provenance, frame/calibration,
  units, empty-result and funnel semantics, while never authorizing motion;
- observation-backed geometry is required on the canonical route and stale or
  missing calibration fails closed;
- workspace, IK, collision, complete-route planning, cancellation, unknown, and
  stop behavior remain Gateway/Runtime-owned;
- bounded Action results include a versioned redacted phase summary with
  failure owner, failure code, outcome-known state, evidence availability, and
  ArtifactRefs, and the generic AgentTask outcome source projects it before
  Experience analysis;
- simulator `check_success()` is recorded as backend evaluation and does not
  replace PAOS verification;
- the PR changes one capability surface and does not add a second AgentTask,
  execution, settlement, evaluator, or promotion protocol.

This review resolves the previous ambiguity between a small public Tool set and
the richer Hephaestus internal chain. It does not require importing Hephaestus,
RoboTwin, SAPIEN, Torch, or XPolicyLab into PAOS core.
