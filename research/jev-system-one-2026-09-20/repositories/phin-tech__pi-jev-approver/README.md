# pi-jev-approver

A shell command approval extension for [Pi](https://pi.dev).
[TypeSafe](https://typesafe.ai)'s Jev model checks each command and decides
whether to allow it, deny it, or ask you.

[`pi-auto-approval`](https://pi.dev/packages/pi-auto-approval) uses the active
chat model for approval checks. This extension uses Jev, a smaller model built
for structured judgments. In our local [jev-test](../jev-test) comparisons,
Jev took about 500 ms per check, compared with 2.5–3.5 seconds for a chat model.

## Setup

```sh
pi install npm:pi-jev-approver   # once published
```

Set `TYPESAFE_API_KEY` in your environment using a key from
[typesafe.ai](https://typesafe.ai), then reload Pi. Run `/jev-approver` to
check status. Without the key, bash calls are denied.

Configuration lives in `~/.pi/pi-jev-approver/config.json`.
See [config.example.json](config.example.json) for an example, or run
`/jev-approver config` to inspect your settings.

## How approval works

Command rules run first. If no rule matches, each `bash` tool call is sent to
Jev with context about the command and working directory. Jev returns a risk
score from 0 to 2, confidence, and flags describing its concerns.

By default, a confident score of 0.5 or less allows the command; a confident
score of 1.5 or more denies it. Other results go to you for review, unless
you enable LLM escalation below.

The prompt offers **Allow**, **Always allow**, and **Deny**. **Always allow**
saves a rule in `config.json` for that exact command. If the config is invalid
or already has 50 rules, you'll get a warning that the rule wasn't saved.
Permanent deny rules must be added to the config by hand.

Every decision goes into a local, redacted JSONL audit log. When you're asked
to review a command, the prompt shows your previous decisions for that command
and your last reason. Jev only receives this history if you set
`PI_JEV_APPROVER_FEED_HISTORY=1`.

If Pi has no interactive UI, commands that need human approval are denied.

## Custom concerns

Jev checks for data loss, changes that are hard to undo, effects on shared
systems, downloaded code execution, and permission changes. Add your own
concerns in `config.json`:

```json
{
  "customConcerns": {
    "aws_command": "This command interacts with AWS infrastructure and could affect live cloud resources or incur cost"
  }
}
```

Each entry adds a question to every Jev request and can appear as the main
reason for a decision (`primary_concern`). Use lowercase snake_case keys.
The limit is 10 concerns, with up to 300 characters per description.

## Command rules

Use `commandRules` to allow or deny matching commands without calling Jev,
escalating to another model, or showing an approval prompt.

```json
{
  "commandRules": [
    {
      "pattern": "^git status$",
      "action": "allow",
      "weight": 20,
      "reason": "Show working tree status"
    },
    {
      "pattern": "drop\\s+(table|database)",
      "action": "deny",
      "weight": 100,
      "reason": "Never run raw SQL drops"
    }
  ]
}
```

- `pattern` is a regex matched against the raw command string. Matching is
  case-insensitive by default; set `"flags": ""` for case-sensitive matching.
- `action` is `"allow"` or `"deny"`. Deny rules appear as `HARD BLOCK` in the
  denial message and `/jev-approver recent`. They cannot be overridden by an
  LLM or approval prompt; you must edit the config.
- `weight` determines which rule wins when several match. Higher weights win;
  ties favor deny. The limit is 50 rules.

Commands that don't match a rule go through the normal approval process.
Rules match text, not shell semantics, so keep allow patterns narrow. A
pattern that only checks the start of a command can also match a command
with additional shell operations appended to it.

## Getting a second opinion

To have a chat model review uncertain results before asking you, enable
escalation in `config.json`:

```json
{
  "escalation": {
    "enabled": true,
    "model": "",
    "maxRiskScoreToEscalate": 1.5,
    "maxConfidenceToEscalate": 0.7
  }
}
```

Set `model` to a `provider/id` from Pi's model registry, or leave it empty to
use the current session model. Escalation uses the credentials already
configured in Pi. Jev still requires its separate `TYPESAFE_API_KEY`.

This is off by default and only runs when both Jev's risk score and confidence
are at or below the configured limits. You can read the second opinion in
`/jev-approver recent` or the audit log's `llmEscalation.rationale` field.
If the call fails, times out, or gives no clear decision, you're asked to decide.

Escalation requires `@oh-my-pi/pi-ai` or `@earendil-works/pi-ai` to be
resolvable, and `ctx.modelRegistry` to be available on the host. If either is
missing, the extension falls back to human review.

## Audit logs and privacy

Commands and the [context below](#context-sent-to-jev) are sent to TypeSafe
for classification.
If escalation is enabled, it also sends approval requests to the configured
chat model provider.

Before commands are written to the local audit log,
[src/redact.ts](src/redact.ts) removes common secret patterns, including
bearer tokens, password and token flags, long opaque strings, emails, IP
addresses, and home-directory usernames. Redaction is best-effort: it can
miss secrets in free-form shell commands.

There is no telemetry. Run `/jev-approver export` to create a timestamped,
redacted snapshot of the audit log. Review it before sharing. To check the
current redaction coverage, run:

```sh
npx tsx scripts/test-redact.ts
```

## Training a local classifier

Human approval decisions are logged alongside Jev's scores, confidence, and
flags. The training script uses those records to fit a logistic regression:

```sh
uv run --with scikit-learn,numpy scripts/train.py
```

The script uses nine features, including Jev's scores, branch protection, and
registry-publish detection, to look for patterns in what you allow and deny.
It needs at least 90 labeled records; below that, it runs a synthetic demo.
It trains a separate classifier without changing Jev's weights.

## Jev request reference

### Context sent to Jev

These fields come from command parsing, filesystem checks, Git, and the
audit log. Parsing and path detection are best-effort.

| Field | Contents | When sent |
| --- | --- | --- |
| `shell_command` | Raw command string | Always |
| `command_executable`, `command_subcommand`, `command_args` | Parsed command parts | Always |
| `command_file_path_like_args` | Arguments containing `/` or starting with `~` or `.` | Always |
| `git_branch`, `git_branch_is_protected` | Current branch; protected names match `main`, `master`, `prod(uction)?`, `release/*`, or `deploy/*` | In a Git repo |
| `git_has_uncommitted_changes` | Whether `git status --porcelain` is non-empty | When determinable |
| `project_ecosystem` | Node, Python, Rust, Go, Ruby, or Java, based on marker files in `cwd` | When a marker is found |
| `looks_like_public_registry_publish` | Matches for `npm/yarn/pnpm publish`, `twine upload`, `cargo publish`, `gem push`, or `mvn deploy` | Always |
| `command_paths_outside_project_directory` | Path-like arguments that resolve outside `cwd` | When path-like arguments exist |
| `command_targets_home_directory`, `command_targets_filesystem_root` | Whether any path resolves to `$HOME` or `/` | When path-like arguments exist |
| `prior_human_decisions_for_this_exact_command` | Review, allow, and deny counts, plus the last reason | When history is enabled and the command has been reviewed before |

### What Jev evaluates

| Question | Type | Meaning |
| --- | --- | --- |
| `risk_level` | Score, 0–2 | Overall risk used for the decision thresholds |
| `destructive` | Noul | Deletes, overwrites, or irreversibly discards local data |
| `hard_to_reverse` | Noul | Difficult to undo, such as a force-push |
| `affects_shared_or_remote_state` | Noul | Affects other people or systems |
| `downloads_and_executes_code` | Noul | Fetches and runs code from the network |
| `modifies_permissions_or_ownership` | Noul | Changes file or system access controls |
| Your `customConcerns` | Noul, one per entry | Additional concerns defined in config |
| `primary_concern` | Choice | Main reason shown in the approval prompt |

`primary_concern` can select any built-in or custom concern, as well as
`protected_branch_target`, `large_or_multi_step_command`,
`operates_outside_project_directory`, or `general_caution_no_single_driver`.
The risk instructions also ask Jev to consider branch protection,
install-time code execution, registry publishing, command history, and paths
outside the project.
