# ⚡ JevShift

**Token Saver & Fast Decision Layer for OpenAI Codex — powered by Jev.**

JevShift moves routine judgment work away from the main coding model. Jev
classifies requests, reviews computer actions, fast-tracks safe permissions,
and decides when a large tool result can leave the active context.

## What it does

| Codex boundary | Jev decision | Result |
| --- | --- | --- |
| `UserPromptSubmit` | simple / standard / complex | Adds a short instruction to avoid unnecessary reasoning and tools |
| `PreToolUse` | unsafe? irrelevant? | Blocks high-confidence bad computer actions |
| `PermissionRequest` | safe to allow? needs human? | Auto-allows ordinary operations; destructive and credential-related actions stay human-reviewed |
| `PostToolUse` | keep full result? | Replaces dispensable large outputs with a preview and archives the exact result locally |

JevShift fails open when Jev is unavailable: normal Codex behavior continues.

## Requirements

- OpenAI Codex CLI/Desktop with lifecycle-hook support
- Node.js 20+
- A TypeSafe API key

## Install

```powershell
codex plugin marketplace add fabricio852/jevshift
codex plugin add jevshift@jevshift
[Environment]::SetEnvironmentVariable('TYPESAFE_API_KEY', 'your-key', 'User')
```

Restart Codex, open `/hooks`, review the four hooks, and trust them. On macOS
or Linux, export `TYPESAFE_API_KEY` from your shell profile instead.

## Defaults

- Evaluate tool results at 1,800 characters (`JEV_MIN_CHARS`)
- Keep full results at probability 0.5 or higher (`JEV_KEEP_THRESHOLD`)
- Keep a 320-character preview (`JEV_PREVIEW_CHARS`)
- Auto-allow permissions at `safe_to_allow >= 0.85` and `needs_human <= 0.15`
- Fail open on timeouts, network errors, or malformed responses

See [`.env.example`](.env.example) for runtime switches. Set
`JEV_ROUTING_HINTS=0`, `JEV_COMPUTER_PREFLIGHT=0`, or `JEV_AUTO_REVIEW=0` to
disable an individual layer.

## Privacy and safety

JevShift sends relevant prompt or tool data to TypeSafe for judgment. Large
outputs are clipped before assessment. Hidden output is appended exactly to
`filtered-results.jsonl` in Codex's writable plugin-data directory.

## Development

```sh
npm run check
npm test
```

The smoke test uses a local fake Jev endpoint and makes no external requests.

## Inspiration

The recoverable output-filtering idea was inspired by
[fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction), which
targets Claude Code's function-hook compaction API. JevShift is built for Codex
and uses Codex lifecycle boundaries instead.

## License

MIT
