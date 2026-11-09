<p align="center">
  <img src="docs/logo.png" alt="Moongate" width="220">
</p>

<h1 align="center">Moongate</h1>

Checks a pull request's diff against semantic rules you wrote, using [TypeSafe](https://typesafe.ai) Jev, and reports the results as PR annotations.

Rules are JSON in your repository. Each one is a question with three possible answers (violation, compliant, insufficient_evidence) plus a probability threshold. CI sends the selected diff and the question; the model picks an answer; Moongate applies your thresholds and decides the exit code.

Use it for things a linter can't see: "don't log credentials", "new endpoints need an auth check", "migrations must be reversible". There is no model writing or editing rules, and nothing runs your repository's code.

## Example output

```
::warning title=moongate: no_secret_logging::[violation] Possible credential logging. Log a request id instead. (source: AGENTS.md: never log credentials) [paths: src/handlers.py] [choice=violation p=1.000 confidence=1.000]
::notice title=moongate::conclusion advisory (exit 0)
```

The leading `[violation]` / `[needs review]` / `[not evaluated]` is Moongate's verdict after thresholds. The trailing `choice=` is the model's raw answer. They differ when an answer lands below a threshold.

## Setup

1. Add your TypeSafe key as the repository secret `TYPESAFE_API_KEY`.
2. Commit a `.moongate.json`.
3. Add the workflow:

```yaml
name: Semantic
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read

jobs:
  evaluate:
    # Forks get no secret, so skip them rather than report a fake pass.
    if: >-
      github.event.pull_request.head.repo.full_name == github.repository &&
      github.actor != 'dependabot[bot]'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v5
        with:
          ref: ${{ github.event.pull_request.base.sha }}
          fetch-depth: 0
          persist-credentials: false
      - uses: brickfrog/moongate@v0
        with:
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}
          api-key: ${{ secrets.TYPESAFE_API_KEY }}
```

The checkout and the policy both come from the base commit, so a PR can't edit the rules that judge it. Rule changes apply after merge.

There's no build step. The runner is compiled to JavaScript and committed in `dist/`, so the action is `runs: node24`.

## Configuration

`.moongate.json` at the repository root:

```json
{
  "version": 1,
  "model": "jev-1.13.0",
  "rules": [
    {
      "id": "no_secret_logging",
      "source": "AGENTS.md: never log credentials",
      "severity": "advisory",
      "globs": ["src/**/*.py"],
      "exclude": ["src/**/test_*.py"],
      "context": [],
      "thresholds": { "min_probability": 0.90, "min_confidence": 0.80 },
      "question": {
        "type": "choice",
        "instructions": "Does this change log a credential, token, or Authorization header value?",
        "criteria": {
          "violation": "The change logs a credential or an Authorization header value.",
          "compliant": "The change logs no credential material, or redacts it.",
          "insufficient_evidence": "The supplied changes do not establish either."
        }
      },
      "message": "Possible credential logging. Log a request id instead."
    }
  ]
}
```

Schema: [`skills/moongate-setup/references/moongate.schema.json`](skills/moongate-setup/references/moongate.schema.json).

Writing rules is the hard part, so it lives in a skill instead of the runner. Copy [`skills/moongate-setup`](skills/moongate-setup) into your agent's skills directory and ask it to set Moongate up. It reads your `AGENTS.md`/`CLAUDE.md`, sorts each instruction into deterministic (use a linter), semantically checkable, or process-only (a diff can't prove you ran the tests), and drafts advisory rules for the middle group. It never enables blocking and never calls the API.

## Severity and exit codes

| result | exit | job |
|---|---|---|
| advisory violation, or any review verdict | 0 | green, annotated |
| blocking violation | 1 | red |
| config or operational failure | 2 | red |

Rules are advisory unless you set `"severity": "blocking"` and supply thresholds.

If a rule can't be evaluated (unrepresentable evidence, evidence over the size budget), its severity decides what happens: blocking fails the run, advisory reports an error result and exits 0. An unevaluated rule never counts as a pass.

## Inputs

| input | required | default | meaning |
|---|---|---|---|
| `base` | yes | | Base commit. Policy is read from here. |
| `head` | yes | | Head commit to evaluate. |
| `api-key` | yes | | TypeSafe key. Passed through the environment only. |
| `config` | no | `.moongate.json` | Root-relative config path. |
| `repository` | no | `.` | Working directory to evaluate. |
| `github-token` | no | | Token with `checks:write`. See below. |

## Check runs

Without `github-token`, results are workflow log annotations. They show up in the job log and in the PR's Files tab, and the job's own pass or fail is the only status.

With a token that has `checks:write`, Moongate also publishes a check run named "Moongate": its own entry in the PR checks list, a summary, per-file annotations, and a re-run button. Branch protection can require it by name. Add `permissions: checks: write` to the job and pass `${{ secrets.GITHUB_TOKEN }}`.

If you register a GitHub App and mint an installation token, the check run appears under that app's name and avatar instead of github-actions:

```yaml
    permissions:
      contents: read
      checks: write
    steps:
      - uses: actions/create-github-app-token@v2
        id: app
        with:
          app-id: ${{ vars.MOONGATE_APP_ID }}
          private-key: ${{ secrets.MOONGATE_APP_KEY }}
      - uses: brickfrog/moongate@v0
        with:
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}
          api-key: ${{ secrets.TYPESAFE_API_KEY }}
          github-token: ${{ steps.app.outputs.token }}
```

The App route costs more setup, not less: you register the App, install it, and store its private key and id alongside the TypeSafe key. What it buys is presentation and control, a distinct identity in the checks list and a check that branch protection can require. It does not remove any secret, does not move compute off the consumer's runner, and does not make fork PRs work. Everything still runs in the caller's CI.

The check run's conclusion follows the exit code: 0 is success, 1 is failure, 2 is action_required. Publishing uses the same single evaluation that produced the annotations, so enabling it costs no extra model calls. If publishing fails, the job fails with exit 2 rather than reporting a result nobody can see.

## What gets sent

Only what a rule selects: patches for matching changed files, plus any exact `context` files that rule names. No repository archive, no PR title or description, no branch names, no telemetry.

- Patches come from the committed blob ids, not the working tree, so a rename or a file-to-directory change can't pull in excluded paths.
- Git hooks, external diff drivers, and textconv are off. A `.gitattributes` entry can't hide a selected file's contents.
- The key is read from `TYPESAFE_API_KEY` only, never appears in argv or a file, and is removed from every `git` child environment.
- Fork and Dependabot PRs are skipped by the workflow condition above. GitHub marks those jobs skipped; Moongate never reports them as passing.

Anyone who can push a workflow to your repository can use the secret. Reading policy from the base commit protects the action invocation, not the workflow file.

## Limitations

A verdict is a model's answer, not a proof. Exit 0 doesn't mean the code is fine.

Confidence comes from the answer's probability distribution. It doesn't tell you the answer is correct.

Verdicts move between runs. Ten replays of the identical request the runner builds, same pinned model: the label was `violation` all ten times, but probability ranged 0.87 to 0.92 (sd 0.015) and confidence 0.82 to 0.88 (sd 0.019). That rule's gate was 0.90/0.80, which falls inside the range, so 4 replays counted as a violation and 6 as a review on one unchanged PR. Keep thresholds away from where a rule actually lands. If a rule keeps landing near its gate, the rule needs work.

Repository content is untrusted input to a model. The instruction prefix saying so is a precaution, not a guarantee.

Each rule's evidence is one unit, capped at 65536 serialized bytes. Measured against `jev-1.13.0`: 149053 bytes (32827 input tokens) was accepted, 152935 bytes came back `max_tokens_exceeded`; the cap assumes a pessimistic 2 bytes per token. A rule whose diff exceeds it is reported unevaluated rather than truncated. Narrow its globs.

The model is pinned. Changing it invalidates your thresholds.

## Local use

```bash
moon build --target native --release
_build/native/release/build/cmd/moongate/moongate.exe validate --config .moongate.json
_build/native/release/build/cmd/moongate/moongate.exe check --base main --format text
```

`validate` needs no credential and makes no network call.

## Development

```bash
moon check --target native && moon check --target js
moon test --target native
moon build --target native --release && moon build --target js --release
cp _build/js/release/build/cmd/moongate-js/moongate-js.js dist/moongate.js
_build/native/release/build/cmd/itest/itest.exe \
  --bin "$PWD/_build/native/release/build/cmd/moongate/moongate.exe" \
  --action "$PWD/dist/index.js"
```

The integration suite builds real Git repositories and a loopback API fixture, and needs no credential. CI runs it against both the native binary and the committed JavaScript bundle, and fails if `dist/` is stale.

Design notes and threat model: [`DESIGN.md`](DESIGN.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE).
