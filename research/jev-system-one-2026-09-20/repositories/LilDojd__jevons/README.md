> [!WARNING]
> Hi! This is a very experimental project for personal use riding on the Jev hypetrain. It is entirely LLM-generated, and there are no guarantees on its usability and/or correctness. Shoutout to Nandakishor Mukkunnoth and his [preprint](https://arxiv.org/abs/2503.23303).

# Jevons

![100% slop](https://img.shields.io/badge/%F0%9F%A4%96%20100%25-slop-a3e635?style=plastic&labelColor=4c1d95 "100% LLM-generated")

Jevons uses TypeSafe's Jev model to select skills, review code and suggest failure recovery steps in [Pi](https://github.com/badlogic/pi-mono).

## Start

Install [devenv](https://devenv.sh/). Check out this repository. SecretSpec requires an available, unlocked OS keyring for these commands. Run them from the repository root:

```sh
devenv shell
bun install --frozen-lockfile --ignore-scripts
secretspec set --provider keyring TYPESAFE_API_KEY
secretspec run --provider keyring -- ./node_modules/.bin/pi --no-extensions -e "$PWD/pi/extension.ts"
```

SecretSpec prompts for the key without displaying it. Never put the key in command arguments. If your runtime environment already supplies the key, use `--provider env` with `secretspec run`. Plain `devenv shell` does not load secrets.

**When you load Jevons in a trusted project, you enable data sharing.** Jevons can send conversation text, skill descriptions, tool arguments, selected source and diagnostic excerpts to TypeSafe. Free-text questions also use a question writer. By default, this writer is your current coding model. Keep secrets out of prompts, Git and the Nix store.

For a declarative installation, enable `dendriticSlop.extensions.jevons.enable` in [dendritic-slop](https://github.com/LilDojd/dendritic-slop). Pi lists Jevons as a package, not a file under `~/.pi/agent/extensions`. After you change the package pin, rebuild the configuration. Then restart Pi.

## Use

| Command                        | Action                                              |
| ------------------------------ | --------------------------------------------------- |
| `/jevons`                      | Open the action menu                                |
| `/jevons settings`             | Change settings immediately                         |
| `/jevons pause` / `/jevons on` | Stop requests / resume sharing                      |
| `/jevons ask QUESTION`         | Supply context and ask a focused question           |
| `/jevons review PATH…`         | Review selected paths, or all changes with no paths |
| `/jevons review PR_URL`        | Fetch and review a GitHub PR without executing it   |
| `/jevons gate PATH…`           | Confirm and run configured checks, then review      |
| `/jevons usage`                | Show reported token totals and unknown usage        |
| `/jevons activity PAGE`        | Browse recorded requests without source text        |

The agent can also call `jevons_decide` and `jevons_review`. For filenames with spaces, use the review tool's `paths` array. Press **Ctrl+O** to show questions, probabilities, models, usage and coverage.

## Settings

Use `/jevons settings` to change toggles, thresholds, the question writer or user-preference JSON. Preferences are saved atomically to `~/.pi/agent/jevons.json` (or your `PI_CODING_AGENT_DIR`) and follow you across sessions and projects. They override project preferences; old session-branch settings no longer override them. Existing sessions pick up external changes with `/jevons on` or a reload.

Commands/checks, model-routing profiles and review rules remain in project `jevons.json`; they are never copied into user preferences. Reset saves built-in preference defaults without changing project configuration. Changes cancel pending Jevons work and checks, not the coding agent. Paused sessions stay paused. See [defaults and validation](pi/policy.ts).

By default, Jevons assesses eligible skills in batches. It selects all that pass the relevance threshold. It also reviews code automatically. Model routing only suggests changes. Recovery records advice without interruption. Set recovery to `steer` to permit limited replan or ask-user messages. Investigation and pre-tool advice are off. Jevons has no project checks until you add them.

## Compaction

Compaction is provided separately by our [pi-jev-compact fork](https://github.com/LilDojd/pi-jev-compact), based on [019ec6e2's port](https://github.com/019ec6e2/pi-jev-compact). Its native Pi compaction hook replaces the old built-in pruning implementation. Enable `dendriticSlop.extensions.pi-jev-compact.enable` to install the pinned fork. It adds trust checks, bounded requests/responses, deadlines, safe diagnostics and source-free model/usage receipts without changing the pruning algorithm. No flake patches are applied.

The port follows Pi's auto-compaction and `/compact` flow, with `/jev-compact` for an explicit request. Retained history becomes text; images and thinking blocks in the compacted portion are not retained. It falls back to Pi's built-in summary when pruning fails or saves too little. Its configuration, requests and accounting are independent: `/jevons pause` and `/jevons usage` do not control or count this extension. See its README for configuration and data-sharing behavior.

## Limits and costs

- Confirm checks separately. Checks are mandatory unless you set `mandatory: false`. Uncertain optional checks remain selected. Failed, stale or unrun checks cannot count as verified. Reviews do not approve merges.
- Jevons has no spending cap or automatic billed retry. A request failure pauses data sharing. Usage includes all session branches. Unknown usage is not zero. A new session or extension reload enables data sharing again in trusted projects.
- Jevons limits requests to 48,000 UTF-8 bytes. State plus the longest question must fit within 24,000 bytes. Reviews split patches into 8,000-byte chunks and report missing coverage. Task-based automatic assessments stop if delivered task evidence exceeds 8,000 bytes or includes images.
- Old results do not verify the current revision. Run checks again when necessary. Jevons does not track changes to ignored files, external services or toolchains.

## Development

```sh
devenv shell -- bun run check
```

The project pins Bun, Node 24, Biome and dependencies. Biome formats, lints and organizes imports using `biome.json`. Dependabot checks Bun packages and GitHub Actions weekly.

## Releases

Use Conventional Commit subjects: `fix:` for patches, `feat:` for features, and `!` for breaking changes. Before version 1.0, breaking changes increase the minor version.

Release Please opens a version and changelog PR. Review it and run the checks before merging. If bot PR checks do not start, run **Check** manually on the release PR branch. After merge, the release workflow runs checks, then creates the GitHub tag and release. It does not publish to npm.
