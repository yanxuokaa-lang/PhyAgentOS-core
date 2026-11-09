# ActionJev

Code review for GitHub Actions and Gitea Actions, written in Rust and powered by
[TypeSafe Jev](https://typesafe.ai/).

ActionJev reads committed code, asks Jev structured review questions, and posts a
PR summary with code locations, suspected defect mechanisms, and assessment
scores. It also writes JSON and Markdown reports for your own tooling.

Jev returns typed judgments, not written explanations or patches. Findings need
human verification. A review with no findings does not prove the code is correct.

## What it does

- Reviews PR changes or eligible source files at a selected commit.
- Checks correctness, security, reliability, compatibility, and supplied tests.
- Updates a PR conversation comment using the platform's job token.
- Limits files, bytes, follow-up assessments, and concurrent requests.
- Runs bundled static binaries on Linux x64 and ARM64. No Rust installation or
  Docker is needed when using a published action version.

The reviewer reads Git objects and does not execute the reviewed code. It does
send eligible source to TypeSafe. Built-in filename exclusions reduce accidental
exposure but do not replace secret scanning.

## Get started

For GitHub or Gitea, follow the [setup guide](docs/setup.md). It includes complete
workflow examples, token permissions, and release pinning. You supply your own
`TYPESAFE_API_KEY`; PR comments use the automatic job token without a personal
access token.

Use a published tag such as `AlexBabescu/ActionJev@v0`, or pin its distribution
commit SHA. Source branches do not include packaged binaries. Start with
`fail-on: none` and evaluate known changes before making results a required gate.

For public repositories accepting outside contributions, use a trusted workflow
with environment approval. See [security and secret protection](SECURITY.md)
before enabling model calls.

### Try it on this repository

Opening or updating a PR automatically requests a review, including forks and
PRs targeting other branches. PRs authored by `AlexBabescu` run automatically.
For other authors, the bot posts a workflow link where Alex approves
`jev-approval` before model calls begin. Results replace the pending bot comment.

Maintainers can comment `/jev review` to request a rerun, or run **Jev PR review**
from Actions with a PR number. Reruns use the same author-based approval rule.
The reviewer uses trusted `main` code, so it can include changes that have not
reached a published release. Offline checks run on PRs; live release tests and
publishing run in a separate main workflow.

## How a review works

| Stage | What happens |
|---|---|
| Screen | One model request per file scores all configured review categories. |
| Locate | Each category above the screening threshold gets an evidence-region selection request. |
| Judge | If a region is selected, another request assesses support, mechanism, and impact. |
| Report | Rust applies thresholds, writes reports, and optionally updates the PR comment. |

The default follow-up threshold is 0.65. An actionable assessment also needs
support of at least 0.8, confidence of at least 0.7, and impact of at least 1 on
the default 0 to 4 scale. These are decision rules, not measured bug probabilities.
See [how to read results](docs/review-results.md) for examples and limitations.

## Configure the review

The [prompt policy](prompts/review.json) defines review guidance, category
questions, mechanism choices, and impact levels. Supply a trusted policy file to
customize a released action. In this repository, policy changes take effect in
manual reviews after merge.

[Configuration](docs/configuration.md) covers thresholds, budgets, exclusions,
outputs, and local use. [action.yml](action.yml) is the complete action input and
output reference.

## Documentation

| Guide | Covers |
|---|---|
| [Setup](docs/setup.md) | GitHub and Gitea workflows, credentials, runtime requirements |
| [Configuration](docs/configuration.md) | Inputs, custom policy, reports, CLI usage |
| [Review results](docs/review-results.md) | Scores, API calls, uncertainty, troubleshooting |
| [Security](SECURITY.md) | Trust boundaries, environment approval, vulnerability reporting |
| [Architecture](docs/architecture.md) | Git evidence, model requests, modules, failure handling |
| [Verification](docs/verification.md) | Offline tests, live integration, model calibration |
| [Distribution](docs/distribution.md) | Packaged binaries, release tags, mirrors |
| [Contributing](CONTRIBUTING.md) | Development setup, checks, pull requests |

## Project status

ActionJev is an early-stage open-source project. GitHub CI checks the integration
and both supported binary architectures. Model quality is a separate concern:
a recorded rounding calibration failed to classify the broken examples as
actionable. Live Gitea deployment remains unverified. See
[verification](docs/verification.md) for evidence and scope.

Documentation on `main` describes the source revision. For an installed release,
read the documentation at its pinned tag or commit. Check
[releases](https://github.com/AlexBabescu/ActionJev/releases) for published versions.

## Contributing

Bug reports, documentation fixes, and focused pull requests are welcome. Start
with [CONTRIBUTING.md](CONTRIBUTING.md). Report suspected vulnerabilities through
the private channel in [SECURITY.md](SECURITY.md), without posting credentials.

## License

[Apache-2.0](LICENSE).
