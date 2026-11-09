# ask-jev

An explicit, advisory audit of a local Codex conversation's recorded execution. Windows PowerShell 5.1 is the installation runtime; PowerShell 7.6.5 was also tested. No package installation is needed.

```text
:jev                         Audit the current conversation
:jev ask Did the tests pass?  A typed yes/no judgment plus evidence sufficiency
:jev --details               Include evidence window and omission counts
:jev help                    Local help
```

Commands use Codex's native `UserPromptSubmit` blocking reason to display results without starting a Codex model turn. **Audit and ask intentionally send selected conversation, instructions, and tool content to TypeSafe for separately billed Jev inference.** Help stays local. Ordinary prompts pass through silently, without transcript access or network calls by ask-jev.

Only trailing CR/LF is removed. Commands are case-sensitive. `:jevx`, quoted examples, leading spaces, and ordinary prose pass through. Invalid arguments after the exact `:jev` token remain blocked and show usage. Ask accepts one line ending in `?`, up to 2,000 characters; phrase it as a yes/no question. It returns probabilities, not generated explanations. For details in ask mode, use `:jev --details ask Did the tests pass?`. The flag changes display only.

## Install and remove

Keep this checkout at a stable absolute path. From its directory:

```powershell
powershell.exe -NoProfile -File .\install.ps1
# Or install for a different repository:
powershell.exe -NoProfile -File .\install.ps1 -Repository C:\path\to\repo
# Explicit user-level installation, across local repositories:
powershell.exe -NoProfile -File .\install.ps1 -User
```

Review/trust the project and hook through CLI `/hooks`, or desktop Settings → Hooks → **Reload hooks** → **User config** (for `-User`) → **UserPromptSubmit**. Review the command ending in `ask-jev/test-command.ps1`. Desktop lists can remain cached for five minutes. Reopen the target task afterward. The installer adds one command to the applicable `.codex/hooks.json` (or `$CODEX_HOME/hooks.json`). It preserves other hooks and settings and never edits trust hashes, enables disabled hooks, or changes execution policy. Reinstallation is idempotent. Both hosts use the same entry point. No conversation is sent during installation.

If updating an installation, rerun the installer in that scope. The Windows launcher uses PowerShell's `&` operator and single-quoted absolute paths. A changed hook definition requires a new trust review in Codex.

Prefer one installation scope: remove the repository installation before switching to `-User`. If both scopes contain ask-jev, a per-session/turn atomic marker prevents a second Jev request. These empty, hashed `.once` files live in the OS temporary `ask-jev-invocations` directory; they contain no transcript or report. A new command turn permits another audit. They may be cleared while Codex is closed.

```powershell
powershell.exe -NoProfile -File .\install.ps1 -Remove
powershell.exe -NoProfile -File .\install.ps1 -User -Remove
```

Removal deletes only ask-jev hook entries in the selected scope. Other settings and trust approvals remain intact; an empty hook array is harmless. Restart the affected task afterward.

## Configure TypeSafe

The client uses `TYPESAFE_API_KEY` and optional `TYPESAFE_MODEL` (default `jev-latest`). It reads only the process environment, then explicitly named Windows user environment variables. It does not search credential stores, shell profiles, `.env` files, or other applications.

For terminal and desktop use without putting the key in shell history:

```powershell
$key = Read-Host 'TypeSafe API key' -AsSecureString
[Environment]::SetEnvironmentVariable('TYPESAFE_API_KEY', ([pscredential]::new('unused', $key)).GetNetworkCredential().Password, 'User')
Remove-Variable key
```

Windows user environment storage is plaintext. The hook reads it on each audit, so an interactive profile is unnecessary. An existing process-level value takes precedence; update or clear it if replacing a key. Set `CODEX_HOME` in the same way if the desktop uses a nondefault Codex home. A missing key produces a local blocking error.

## Standalone CLI

```powershell
# Offline: emits the exact redacted request; makes zero network calls.
powershell.exe -NoProfile -File .\ask-jev.ps1 -Rollout C:\path\rollout.jsonl -Preview
# Live: one TypeSafe request, JSON result without the input trace.
powershell.exe -NoProfile -File .\ask-jev.ps1 -Rollout C:\path\rollout.jsonl -Json
powershell.exe -NoProfile -File .\ask-jev.ps1 -Rollout C:\path\rollout.jsonl -Question 'Did the last relevant check pass?'
# Include the evidence window and omission counts in a plain-text report:
powershell.exe -NoProfile -File .\ask-jev.ps1 -Rollout C:\path\rollout.jsonl -Details
```

`-SessionId` additionally checks the supplied rollout identity. `-Model` overrides the environment for a standalone run. Preview prints sensitive selected content to stdout only when explicitly requested; save it outside Git or under ignored `.local/`. The CLI and hook use the same extractor, questions, client, validation, and formatter.

## Evidence and limits

The extractor reads a size-bounded snapshot of the exact session, before the triggering command. Windows extended drive paths (`\\?\C:\...`) are accepted. After rewind, it follows explicit `history_base` links and their byte/ordinal cutoffs, verifies each segment belongs to the same session, and excludes discarded branches. It pairs tool calls/results by ID, removes transport copies and self-audit records, preserves repeated actions, and reports missing results, compaction, unknown records, truncation and budget omissions. Selected evidence is capped at 48 KiB; the complete request at 64 KiB. A partial window is explicitly labeled; absent evidence does not establish that something never happened. See [the trace policy](docs/trace-policy.md).

Each audit batches 13 focused checks and one mutually exclusive outcome. Probabilities are advisory, not calibrated guarantees. Low mutation-attribution probability does not identify someone else as the author. There are no generated explanations, fabricated citations, price estimates, automatic fixes, or per-turn audits.

Reports show the resolved Jev model and request time in the header, followed by the outcome, evidence sufficiency, and a one-line coverage warning. Possible issues are ordered by their probability of yes; verification and recovery appear separately. Every check remains visible. Percentages estimate whether the statement is true, not the fraction of the conversation checked or an overall quality score. The report ends with its line/turn range and Jev input-token count. `--details` adds session identity, timestamps, rewind information and omission counts. CLI `-Json` always includes those details and full input/output usage. Blank lines, short labels, and wrapped text keep the host report readable.

Configured-key matches and obvious credential fields are redacted; binary/base64 payloads and encrypted reasoning are omitted. **This is not comprehensive secret removal.** Review an offline preview before sending sensitive work. No telemetry, full request persistence, or raw-report persistence is enabled. Real rollouts and raw reports must stay out of Git.

The supervisor returns a blocking error for handled failures and kills an overlong worker at 28 seconds. Newly installed hooks have a 40-second host timeout. If the host disables or does not trust hooks, fails to launch PowerShell, or kills the supervisor before it responds, ask-jev cannot prevent a model turn. Transcript JSONL is not a stable Codex API. Windows local TUI/desktop using the PowerShell hook runner are the supported setup in this version; other session shells, remote/cloud sessions and other operating systems are unverified.

## Verification and ports

```powershell
powershell.exe -NoProfile -File .\tests\run.ps1
```

Offline tests use synthetic traces and an injected TypeSafe transport. They include the real supervisor crash and timeout paths. See [verification results and limitations](docs/verification.md) and [unchecked porting tasks](TODO.md). Claude Code and OpenCode are not implemented.

Contracts checked on 2026-09-16: [TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart), [TypeSafe API](https://docs.typesafe.ai/api), [Codex hooks](https://developers.openai.com/codex/hooks). Requests use `POST https://api.typesafe.ai/v1/systemone`, Bearer authentication, and the documented Noul/Choice schemas.

## License

[MIT](LICENSE).
