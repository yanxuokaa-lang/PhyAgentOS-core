# git-judge-jev

A GitHub Action that reads a pull request before you do and posts one comment: what the PR really does, which few hunks need a human, why, and what to verify in each.

It is built for pull requests written by coding agents.
A typical one is 30 files, a handful of them hold the actual change, and the description was written by the same agent that wrote the code.
Three things slip past a reviewer in those PRs: a test made green by loosening its assertion, a check quietly removed inside a "refactor", and a change the description never mentions.
git-judge-jev looks for exactly those, ranks the rest of the diff by how much attention it deserves, and sets the mechanical hunks aside.

- **Cheap.** About one cent and ten seconds for a 90-hunk PR.
- **Quiet.** One comment per PR, updated in place on every push. No inline comments, no review spam.
- **Narrow.** It does not hunt for logic bugs, suggest code, or comment on style. Every line it writes is tied to a specific claim about a specific hunk.
- **Readable by agents.** The same findings are exposed as JSON, so a coding agent can act on them without reading the diff.

The "jev" in the name is [TypeSafe](https://typesafe.ai)'s Jev, a small model that answers yes/no questions with calibrated probabilities instead of text.
Jev judges every hunk. A generative model is called only for the hunks Jev flags.

**Jump to:** [Use it](#use-it) | [Before the pull request](#before-the-pull-request) | [What it looks for](#what-it-looks-for) | [How it works](#how-it-works) | [Policy](#policy) | [Limits](#limits-you-should-know)

## What the comment looks like

Shortened from a real run on [a pull request in this repo](https://github.com/davidrydberg/git-judge-jev/pull/5).

> **TL;DR** This PR ties reports to the commit that produced them, assigns stable IDs to findings, and removes stale runs. Review the reporting changes: unflagged items now show up to 10 instead of 5.
>
> **Read first**
>
> - **Safety check weakened** (low) in `src/report.ts` L7-18<br>
>   The maximum number of unflagged items listed increased from 5 to 10, while a separate 50-item embedded reading-order limit was added.<br>
>   **Verify:** Verify that doubling the visible unflagged-item limit does not cause report-size regressions under the existing comment-size cap.
>
>   ```diff
>   -const MAX_UNFLAGGED_LISTED = 5;
>   +const MAX_UNFLAGGED_LISTED = 10;
>   +const MAX_EMBEDDED_READING_ORDER = 50;
>   ```
>
> **Then read**
>
> 1. `src/writer.ts` L117-140 - bugfix, other developers would notice. Close to a flag: safety check weakened 0.41, flags at 0.6
> 2. `src/policy.ts` L194-204 - other developers would notice
> 3. `README.md` L102-108 - docs, touches public API
>
> And 49 more hunks with no finding, in the `json` output of the action.
>
> **Skip** 4 mechanical, 32 generated.
>
> **Notes** This PR mixes bugfix, chore, feature, refactor changes. Consider splitting it.
>
> <sub>judged at c5d4477 | 97 hunks | 9.1 s | about $0.0098 | jev-1.13.0, gpt-5.6-luna</sub>

Every location links to its line in the Files tab.
"Close to a flag" shows a question that scored under its threshold. This run predates the lower default thresholds, which is why it says 0.6.
The code under a finding is printed from the diff itself, so a line the diff does not have is never shown.

## What it looks for

| Finding | Fails the check |
|---|---|
| A credential, key, or token in the added lines | yes |
| A table or column deleted, renamed, or truncated, or stored data rewritten | yes |
| A test made to pass by loosening or removing an assertion | no |
| Validation, error handling, a permission check, or a limit removed or weakened | no |
| A change presented as a refactor that alters behaviour | no |
| A comment that no longer matches the code beside it | no |
| Changes the PR description does not mention | no |
| Your own yes/no questions, from the policy file | no |

The workflow job is the check.
It fails only on the two gates, never on a warning.

It is early.
It runs on its own pull requests in this repo, and the thresholds it ships with are measured on a small suite, see [Measure a change to the judge](#measure-a-change-to-the-judge).

## Use it

You need two API keys: [TypeSafe](https://typesafe.ai) for Jev, and OpenAI for the writer model.
Jev is in early access behind a waitlist.
Setup is one workflow file and two secrets, there is nothing to host.

1. Add two repository secrets under Settings, Secrets and variables, Actions: `TYPESAFE_API_KEY` and `OPENAI_API_KEY`.
   Add `ANTHROPIC_API_KEY` only if your policy names a Claude model.
2. Add `.github/workflows/git-judge-jev.yml`:

```yaml
name: git-judge-jev
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, edited]

permissions:
  contents: read
  pull-requests: write
  issues: write

concurrency:
  group: git-judge-jev-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  git-judge-jev:
    runs-on: ubuntu-latest
    steps:
      - uses: davidrydberg/git-judge-jev@main
        with:
          typesafe-api-key: ${{ secrets.TYPESAFE_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

3. Open a pull request.

No checkout step is needed, git-judge-jev reads the diff through the GitHub API and never runs the PR's code.
`edited` re-runs it when the description changes, so fixing the description clears the findings about it.
The `concurrency` block cancels a run when a newer push arrives, so you do not pay to judge a commit nobody will read.
A run that still finishes late checks the PR head before posting and writes nothing if the head has moved.
A cancelled run stays on the old commit as "cancelled", and some views of the PR show it like a failed check. It is not one: the check that counts is the run on the latest commit.
There are no releases yet, so `@main` is the only ref.
Pin a commit SHA instead if you do not want to follow `main`.

Pull requests from forks are skipped.
GitHub gives them no secrets, and running with `pull_request_target` has not had a security review.
Dependabot pull requests get no secrets either. The run says so in a notice and passes.
A key missing from any other run is a broken setup and ends as "did not run", with the reason in the comment.

### Inputs and outputs

| Input | Required | |
|---|---|---|
| `typesafe-api-key` | yes | Judges every hunk with Jev |
| `openai-api-key` | when the writer model is an OpenAI model, which is the default | Confirms findings and writes the text |
| `anthropic-api-key` | when the policy names a Claude model | Same, for Claude |
| `github-token` | no, defaults to the workflow token | Reads the diff, writes the comment and labels |

| Output | |
|---|---|
| `conclusion` | `success`, `failure`, or `did_not_run` |
| `json` | The full findings, verdicts, reading order, and raw Jev answers, with the `headSha` that was judged and a stable `id` per finding |
| `handoff` | What the comment tells a coding agent: each finding with what to do about it and when it counts as resolved |

If TypeSafe cannot be reached, the check passes and the comment says git-judge-jev did not run.
Set `failOnError: true` in the policy to fail instead.
If only the writer model cannot be reached, the report still posts.
A gate stands on Jev alone and still fails the check. Warnings had no second look, so they are counted and not shown.
A single hunk TypeSafe will not answer for is listed as not judged, it does not cost the report.

## Before the pull request

The same pipeline runs from a terminal, for the coding agent that is about to open the pull request.
It judges the branch against its merge base, reads the policy from the base, posts nothing, and prints the report.

```sh
export TYPESAFE_API_KEY=... OPENAI_API_KEY=...
npx github:davidrydberg/git-judge-jev --base main --title "Refactor session handling" --description-file pr-body.md --agent
```

Exit code 0 means nothing blocks, 1 means a gate would fail the check, 2 means it could not run.
`--agent` prints the findings for a coding agent, the same block the comment carries. `--json` prints the full report, and with neither it prints the comment as Markdown.
Give it the title and description the pull request will have, since two findings compare the diff against them.

An agent can act on its own warnings here: restore the assertion it loosened, or rewrite the description to cover what it left out.
A gate is still for a human.
In a repo gated by no-mistakes, add the command to the commands in `.no-mistakes.yaml` so it runs before the push.

## The comment, section by section

| Section | What it holds |
|---|---|
| TL;DR | Two sentences: what the PR does as a whole, then what deserves attention |
| Blocking | The gates that fail the check |
| Read first | Each confirmed finding that is worth stopping for: what changed, what to verify, the changed lines that show it, and a box to dismiss it |
| Then read | The next ten hunks by attention, each with why it is there: the kind of change, the area, who would notice, any question that came close to a flag, and any claim that held but was minor |
| Not mentioned in the description | Files with changes the PR text does not cover |
| Skip | How many hunks were mechanical, lockfile, generated, or vendored, and which files were set aside by path |
| Notes | A weak or missing description, missing tests, a suggestion to split the PR, hunks that could not be judged |
| Dismissed | Collapsed list of the findings a reviewer ticked off |
| Jev answers | Collapsed table of every raw answer per hunk, for tuning thresholds. Only with `debug: true` |

A small pull request with nothing found gets the TL;DR and the skip count, and no reading order.
The order appears from ten judged hunks up, or as soon as there is a finding. It is always in the JSON.

### Across pushes

The comment is the memory, there is no other state.
On a push, a finding that was not in the previous report is marked "new since the last push".
Every warning has a box, "Not useful, hide it".
Tick it and from the next push on that finding is left out and costs no writer call, until the flagged hunk changes or someone unticks it.
A gate has no box. Anything holding a token can tick one, and a gate is cleared by a human on the merge.
The workflow log has one line per run, `feedback: 2 dismissed by a reviewer, 5 shown`, which is this repo's own precision record for tuning thresholds.

With `labels: true` git-judge-jev also applies labels (`area: auth`, `size: M`, `type: refactor`) and removes the ones that no longer apply.
A label named by a custom question is always applied.

### For coding agents

The comment has two readers, and a part for each.
The part for people is prose: each finding is a short paragraph on what changed, what the code around it shows, and who it touches, then what to verify.
The part for machines is a collapsed block at the end, "For coding agents", holding JSON. It is collapsed and not hidden, so an agent that reads the comment as text gets it, and a person can open it and see what the agent was told. The same JSON is the `handoff` output.

```json
{
  "id": "5705e682a617",
  "status": "new",
  "flag": "test_loosened",
  "severity": "high",
  "path": "test/pricing/discount.test.ts",
  "startLine": 10,
  "endLine": 20,
  "claim": "The test replaced an assertion that requires a RangeError with a non-null check.",
  "evidence": ["-    expect(() => applyDiscount(1000, 101)).toThrow(RangeError);"],
  "action": "fix_code",
  "resolvedWhen": "The assertion is as strict as before, and the test passes because the code under test was fixed."
}
```

`action` is one of `fix_code`, `fix_description`, `fix_code_or_description`, `human_only`, and `none`.
`action` and `resolvedWhen` are the only instructions in the block, and git-judge-jev writes them itself from a fixed table.
`claim` and `evidence` came out of the pull request, which its author controls, and the block tells its reader to treat them as data.
A gate is always `human_only`: it is cleared by a human, never by the agent that wrote the code.
The `id` stays the same across pushes as long as the flagged hunk does, and `status` says whether the finding is new since the last push.
A finding the writer called minor, or a reviewer dismissed, is not in the block. A pull request with nothing to act on has no block.

The `json` output is the full report for tuning: every verdict, the whole reading order, and every raw Jev answer.

## How it works

1. The diff is split into hunks.
   Lockfiles are set aside by path and are never sent anywhere.
   Generated files and vendored code are set aside too, but a path is written by the PR author, so they are still asked the two gate questions, and the comment names them.
2. Jev answers a fixed set of yes/no and multiple-choice questions about each hunk, with calibrated probabilities.
   The questions live in [`src/questions.ts`](src/questions.ts).
   The questions that can fail the check never see the PR description, since a description saying "safe refactor" is exactly what would sway them.
   Five of them raise no flag and only say what kind of logic changed: error handling, a condition, a network or database call, shared state, a limit or default.
   They spread the scores of ordinary code apart and become the reason shown beside a hunk.
   Questions about code are not asked of documentation.
3. Code, not a model, turns the answers into an attention score, flags, labels, and the check result.
   A gate is a probability against a threshold and nothing else.
   Warning thresholds are low on purpose: Jev is the recall stage, and the next step is the precision stage.
4. Only flagged hunks go to a generative model, GPT-5.6 Luna by default, one call per flag.
   Beside the hunk it reads the enclosing function as it is after the change, and the other hunks of the PR that change the same identifiers.
   A hunk alone cannot show whether a check removed here was moved somewhere else.
   It also gets facts that code, not a model, found by searching the whole diff and the file: names added here and removed in another hunk, which is moved code, and whether a name removed here is still in the file.
   It confirms or rejects the flag, says whether it is worth stopping a reviewer for, and writes one sentence on what changed and one on what to verify.
   A rejected warning is dropped. One that holds but does not matter becomes a reason beside the hunk under "Then read".
   A gate is kept either way, the writer model cannot clear one.
   The PR description goes only to the two claims that are about it: a change it leaves out, and a behaviour change passed off as a refactor.
5. One more call writes the TL;DR from the title, the file list with Jev's change type per file, and the confirmed findings.
   It never sees the diff.

A 90-hunk pull request takes about ten seconds and costs about one cent.

### What is sent where

| To | What |
|---|---|
| TypeSafe | Every hunk that is not a lockfile, with its file path. Also the PR title, description, and list of changed files |
| OpenAI, or Anthropic if configured | Only hunks that raised a flag, with the function around them and related hunks of the same PR. The PR description for two of the claims. Also the title and file paths for the TL;DR |
| Neither | A hunk flagged as a possible secret is never sent to the writer model, as a hunk or inside another hunk's context. It has already gone to one vendor |

## Policy

Every threshold and weight lives in `.git-judge-jev.yml` in the repo root.
The file is optional, and a missing file means the defaults.
It is read from the base branch, so a PR cannot loosen the policy it is judged by.
Unknown keys are errors.
The schema with every default is at the top of [`src/policy.ts`](src/policy.ts).

```yaml
minAttention: 0.5          # hunks scoring below this count as mechanical. 0 keeps every hunk
minDescriptionLength: 30   # shorter than this and the description counts as missing
maxHunks: 200
readingOrderFrom: 10       # with no finding and fewer judged hunks than this, the comment has no reading order
labels: false              # area, size, and type labels. They are often wrong on small PRs
debug: false               # the table of every raw Jev answer in the comment
thresholds:
  gates:
    secret_semantic: 0.9
  warnings:
    test_loosened: 0.4       # low on purpose, the writer model drops what the code does not show
weights:
  logicSignal: 1           # the strongest logic signal p scales area and blast radius by 1 + this * p
  testFile: 0.5            # a hunk in a test file counts area and blast radius at half. A loosened test counts in full
exclude:
  generated: ["**/*.gen.ts"]   # set aside, still checked for secrets and destructive data changes
  vendored: ["third_party/**"]
  unchecked: ["dist/**"]       # sent nowhere. For a large committed bundle, where that check is most of the run
generator:
  model: gpt-5.6-luna
  escalation:              # off unless present
    model: claude-opus-5
    areas: [auth, payments]
customQuestions:
  - id: invoicing
    question: This chunk touches invoicing.
    threshold: 0.6
    label: touches-invoicing
failOnError: false
```

A custom question raises a warning and a label.
It can never fail the check.

## Limits you should know

- The shipped thresholds are guesses. Jev's calibration differs per repo and per language, so expect to tune them. The Jev answers table in the comment is there to help with that.
- A generative model reads only flagged hunks. A subtle bug in a hunk that raised no flag gets no second look, at any setting.
- A hunk scoring under `minAttention` is left out of the reading order and can raise a gate but no warning. Set `minAttention: 0` to rank every hunk and let every warning fire on it.
- A large committed bundle is checked for the gates hunk by hunk, which can be most of a run's time and cost. List it under `exclude.unchecked` if you accept that it is sent nowhere.
- A change the description leaves out is reported only where Jev is sure the hunk changes logic, touches a sensitive area, or is one users or data would notice. An undescribed edit to documentation or a rename is not.
- The area and type labels are often wrong on small PRs, which is why they are off by default.
- The function around a hunk is found by indentation, not by a parser. In a minified or oddly indented file the writer gets a window of lines instead.
- A dismissal is a ticked box in a comment that anyone with write access can edit. It hides a warning, never a gate.
- A PR over GitHub's diff limit, about 300 files, ends as "did not run".
- A hunk too large for Jev's context is judged on its first part only and listed as such in the comment.
- Jev works best on English and on high-level languages.
- Jev does not treat its input as hostile. Code comments can sway it. That is why gates never see the description and why the writer model re-reads the code.

## Develop

Needs Node 24 or newer.

```sh
npm install
npm test
npm run typecheck
npm run lint
npm run build
```

No test needs an API key or the network.

To run the real pipeline on a local diff, put `TYPESAFE_API_KEY` and `OPENAI_API_KEY` in a `.env` file, which git ignores, and run:

```sh
npm run try -- test/fixtures/mixed.diff "PR title" "PR description"
```

It prints the comment and posts nothing.

### Measure a change to the judge

`eval/cases/` holds labelled pull requests: a `pr.diff` made by real `git diff`, and a `case.json` naming the hunks a reviewer must read and the flags that are true.
A hunk is named by its file and a string in its diff.

```sh
npm run eval -- --label my-change
npm run eval -- --policy experiment.yml --case real-stale-run-guard
```

It runs the real pipeline on every case and prints where the must-read hunks ranked, which true flags were raised, and every verdict that is false.
Every model answer is cached in `eval/.cache` by request, so trying a threshold or a weight costs nothing, and a changed question pays only for itself. The whole suite costs about two cents uncached.
`--label` saves the result to `eval/results/`, which is committed, so a change can be compared with the run before it.
Change a question, a weight, or a threshold only with a before and after from this.
A case may hold files as they are after the change under `head/`, and the writer then gets its context from them.

The cases in this repo are mostly planted defects. They guard against regressions, they do not say whether the tool is good.
For that, build cases from your own merged pull requests:

```sh
npm run corpus -- owner/repo --limit 50
npm run eval -- --cases eval/corpus
```

`corpus` reads GitHub through the `gh` CLI and calls no model.
A must-read hunk is one a human left a review comment on, or one whose lines a commit with "fix" or "revert" in its message changed within 14 days of the merge.
Every label says where it came from, so a wrong one is deleted by hand.
Findings are not labelled: the eval prints each case's verdicts, and you add the true ones to `case.json` as `flags`, or `flags: []`.
`eval/corpus/` is ignored by git. It is other repos' code, and the eval sends it to TypeSafe and the writer model.

## Release

GitHub runs the committed bundle `dist/index.cjs`, and so does `npx`. One bundle is both the action and the command line.
Run `npm run build` and commit `dist/` in the same commit as any change under `src/`.
To release, tag the commit `v1.0.0`, move the `v1` tag to it, and publish the release to the Marketplace from the GitHub release page. `action.yml` has the branding it asks for.
This repo runs git-judge-jev on its own pull requests from the PR's checkout, so every PR tests its own bundle.

## License

MIT
