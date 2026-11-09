# TrashCompact

TrashCompact deterministically reduces context and further refines compaction using TypeSafe's Jev.

## How it works

1. Deterministic rules remove context bloat without added value for reasoning and problem solving efforts. Recognized failed tool exchanges expire after two user turns. Recognized Node test output keeps final totals and failures instead of individual passing-test lines. User messages and recent reasoning stay protected. The last 5 records are checked for obvious noise without Jev scoring.
2. Jev scores assistant text for lasting value. Text is removed only when its score is low and confidence is sufficient. Unscored text, long entries, and unknown formats stay.
3. Jev selects useful excerpts for a short note to help continue after compaction.

TrashCompact can export a shorter transcript and supplies excerpts for compaction. Your live chat and original transcript stay unchanged.

If scoring fails, TrashCompact uses cached scores and available text. The note can miss details. See [setup and verification](docs/SETUP.md).

## Supported integrations

| Application | Integration |
|---|---|
| Codex | Scores completed turns and delivers the note after compaction. Requires `/hooks` trust review. |
| Claude Code | Scores completed turns and delivers the note after compaction. |
| OpenCode v1 | Adds excerpts to the summarizer's prompt. Requires 1.18.29 or newer with compaction plugin support. |
| OpenCode 2 | Adds excerpts to the summarizer's prompt. Verified with 2.0.10; beta `0.0.0-beta-19157` is unsupported. If issues arise, ask your agent to fix them. |

Codex and OpenCode can send selected tool output to TypeSafe for scoring. Claude Code keeps tool output local when selecting excerpts.

## Ask your agent to install

Copy the block for your application into its chat. Setup requires Node.js 20+, Git, npm, and a TypeSafe API key. Tested on Linux. Windows and macOS should work but remain untested. Please submit a [pull request](https://github.com/roguefort-dev/TrashCompact) with fixes if you encounter issues. On Windows, use PowerShell.

The prompts install the [TypeSafe agent skill](https://docs.typesafe.ai/agent-skill#installation) before TrashCompact.

### Claude Code

```text
First install the typesafe-ai agent skill globally for this application from https://github.com/typesafe-ai/skills, reusing an existing installation, and read its instructions. Then install https://github.com/roguefort-dev/TrashCompact.git at ~/.local/share/trashcompact for Claude Code. Follow docs/SETUP.md with target claude, preserving existing files and settings. I authorize the documented automatic TypeSafe scoring. Give me the absolute key-entry command to run privately and any approval/restart steps. Never handle the key yourself.
```

### Codex

```text
First install the typesafe-ai agent skill globally for this application from https://github.com/typesafe-ai/skills, reusing an existing installation, and read its instructions. Then install https://github.com/roguefort-dev/TrashCompact.git at ~/.local/share/trashcompact for Codex. Follow docs/SETUP.md with target codex, preserving existing files and settings. I authorize the documented automatic TypeSafe scoring. Give me the absolute key-entry command to run privately and the terminal /hooks trust-review and restart steps. Never handle the key yourself.
```

### OpenCode and OpenCode 2

```text
First install the typesafe-ai agent skill globally for this application from https://github.com/typesafe-ai/skills, reusing an existing installation, and read its instructions. Then install https://github.com/roguefort-dev/TrashCompact.git at ~/.local/share/trashcompact for OpenCode. Follow docs/SETUP.md, check version compatibility, and select target opencode or opencode2. Preserve existing files and settings. I authorize the documented automatic TypeSafe scoring. Give me the private key-entry command and approval/restart steps. Never handle the key yourself or enable the optional response-compaction service.
```

The key helper reads hidden terminal input and stores it in `~/.config/typesafe/env`. Enter the key there yourself. Codex hook trust requires `/hooks` in its terminal CLI. Restart the application after setup; after manual compaction, send a new message to observe the resumed task.

## Data processing and reference

Automatic scoring sends assistant text to TypeSafe. Selecting excerpts also sends the latest user request and nearby context. Tool output depends on the [integration](#supported-integrations). Local caches store scores; saved notes contain selected transcript excerpts.

- [Setup, compatibility, private key entry, and removal](docs/SETUP.md)
- [CLI flags, static rules, passage ranking, and limits](docs/CLI.md)
- [Optional OpenCode 2 response-compaction service](opencode2/README.md). This separate Linux service requests native summarization after completed responses.

MIT license.
