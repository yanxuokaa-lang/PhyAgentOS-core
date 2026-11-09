# Umby's Jev Stack

A **skill tree** of [TypeSafe Jev](https://typesafe.ai/) agent skills over HTTP. Install the whole tree or grab one skill.

**Repo:** https://github.com/Umbylicus/umby-jev-stack · **Tree index:** [`TREE.md`](TREE.md)

## Quick start (4 steps)

1. **Get a key** — [console.typesafe.ai](https://console.typesafe.ai/) → create a TypeSafe API key.
2. **Install** — whole tree or one skill (see [Install](#install)).
3. **Set `JEV_API_KEY`** — exact name, case-sensitive.
4. **Prompt your agent** — e.g. *"Run umby-jev-review on this repo. Use frozen questions. Compile every finding."*

## Skill tree (10 skills)

| # | Skill | Use when |
| --- | --- | --- |
| 1 | [`umby-jev-review`](skills/umby-jev-review/) | Full repo review — six independent Nouls, executable defects only (v2.0) |
| 2 | [`umby-jev-diff-gate`](skills/umby-jev-diff-gate/) | Same hunts on git diff / PR patch only |
| 3 | [`umby-jev-secrets`](skills/umby-jev-secrets/) | Stricter secret + PII sweep |
| 4 | [`umby-jev-breaking-change`](skills/umby-jev-breaking-change/) | API / schema / export breaks |
| 5 | [`umby-jev-test-gap`](skills/umby-jev-test-gap/) | Behavior change without tests |
| 6 | [`umby-jev-agent-safety`](skills/umby-jev-agent-safety/) | Destructive command risk before run |
| 7 | [`umby-jev-prompt-screen`](skills/umby-jev-prompt-screen/) | Jailbreak / injection in user text |
| 8 | [`umby-jev-issue-triage`](skills/umby-jev-issue-triage/) | Issue type + urgency (independent) |
| 9 | [`umby-jev-docs-drift`](skills/umby-jev-docs-drift/) | Docs claims to verify later |
| 10 | [`umby-jev-browser`](skills/umby-jev-browser/) | Jev-driven browser loop — Playwright/a11y driver, error Nouls + next_action |

See [`TREE.md`](TREE.md) for install details and how to add skill 11+.

## Install

### Whole tree

```bash
npx plugins add Umbylicus/umby-jev-stack --target cursor
```

Select **`umby-jev-stack`**. Works with `--target claude-code` or `--target codex`.

### One skill

Same command — select the skill name when prompted (e.g. **`umby-jev-secrets`**).

**Manual:** `cp -r skills/<skill-id>/ ~/.cursor/skills/<skill-id>/`

## API key (`JEV_API_KEY`)

| Where | How |
| --- | --- |
| **Shell** | `export JEV_API_KEY="your-key"` |
| **Cursor desktop** | Settings → MCP/plugin env, or `launchctl setenv JEV_API_KEY "$JEV_API_KEY"` + quit/reopen from Dock |
| **Cursor cloud agents** | **Runtime Secret** named exactly `JEV_API_KEY` |

Verify: `test -n "$JEV_API_KEY" && echo ok` — **do not commit keys.**

## How every skill works

- **HTTP-first** — `POST https://api.typesafe.ai/v1/systemone`, model `jev-latest`
- **Independent Nouls** (or separate Choice + Score where documented) — every positive flag gets a compile row
- **Never** a single highest-priority Choice that hides co-occurring hits
- Jev classifies only; **you review** before fixes

[jev-review MCP](https://github.com/NiazMorshed2007/jev-review) is optional — not required.

## License

MIT — see [LICENSE](LICENSE).
