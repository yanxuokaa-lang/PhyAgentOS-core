# omp-auto-mode

Auto-mode for [oh-my-pi](https://github.com/oh-my-pi/oh-my-pi) (`omp`): every tool call the agent wants to run is classified as **safe**, **ask**, or **unsafe** *before* it executes, using [TypeSafe Jev](https://docs.typesafe.ai) as the judgment backend.

- `safe` — runs without interruption.
- `ask` — you get a confirmation dialog with the reason.
- `unsafe` — blocked; the model is told why so it can try something else.

```
$ omp-auto-mode -- git push --force origin main
{
  "label": "unsafe",
  "triggered": ["other_risk", "runs_untrusted", "network_egress", "destroys_data", "outside_project"],
  "uncertain": ["exposes_secrets", "system_config"],
  "hazards": { "destroys_data": 0.73, "network_egress": 0.81, … },
  …
}
```

## How it decides

Instead of one "is this dangerous?" question, each call is judged against seven independent yes/no **hazards** in a single Jev request. Code, not the model, owns the policy:

| hazard | fires → | catches |
|---|---|---|
| `exposes_secrets` | unsafe | reading/printing/sending keys, tokens, `.env`, `$(env)` |
| `destroys_data` | unsafe | `rm -rf ~`, disk formatting, overwriting a dotfile, force-push to main |
| `runs_untrusted` | unsafe | `curl … \| sh` |
| `outside_project` | ask | writes or `chmod` outside the project directory |
| `network_egress` | ask | `git push`, `curl -d`, deploy/publish |
| `system_config` | ask | `npm i -g`, `sudo`, global git/shell config |
| `other_risk` | ask | catch-all: hard to undo, costs money, affects others |

Two thresholds turn probabilities into a label (`fire = 0.7`, `clear = 0.3` by default):

- any **unsafe**-severity hazard ≥ `fire` → `unsafe`
- any hazard ≥ `fire`, or any specific hazard in `[clear, fire)` (the model is genuinely unsure) → `ask`
- everything below `clear` → `safe`

Because each hazard is an absolute judgment, `safe` means *every* hazard came back near zero — not that "safe" won a relative vote. The catch-all only counts when it fires outright; its mid-range means "mildly consequential", not "unsure", so it never prompts on its own.

## Install

Requires Node ≥ 23.6 (runs TypeScript natively) and a `TYPESAFE_API_KEY` in your environment.

```bash
git clone https://github.com/alexsatch/omp-auto-mode
cd omp-auto-mode && npm install
```

Load it into `omp` for one session, or link it permanently:

```bash
omp -e /path/to/omp-auto-mode
omp plugin link /path/to/omp-auto-mode
```

The extension gates `bash`, `write`, `edit`, `eval`, and `ast_edit`. Read-only tools are not classified. If the classifier itself is unreachable, the call falls through to omp's normal approval instead of failing closed.

### Allow and deny rules

Commands you trust (or never want run) can bypass the model entirely. Rules live in
`<project>/.omp/auto-mode.json` and `~/.omp/agent/auto-mode.json` (merged; deny always wins):

```json
{
  "allow": ["git status", "git diff *", "npm run *", "ls *"],
  "deny": ["git push --force *"]
}
```

A rule is a list of tokens with an optional trailing `*` meaning "any further arguments". Rules
match only commands that are a flat argument list — no `;`, `&&`, `|`, `$(…)`, globs, expansions,
or redirects to real files — so `git status; rm -rf ~` never matches `git status`; it goes to the
classifier. Redirects that cannot touch a file (`>/dev/null`, `2>/dev/null`, `2>&1`) are ignored
for matching, so `npm test 2>&1` matches an `npm test` rule.

When a call is classified `ask`, the dialog offers **Allow once**, **Always allow** (the exact
command, and its `<cmd> <sub> *` prefix when longer), and **Deny**. Choosing *Always allow* appends
the rule to the project file, so the list grows from real decisions.

## CLI

```bash
# classify one command
node src/cli.ts -- rm -rf ~/
node src/cli.ts --project-dir ~/work/app --fire 0.8 -- git push origin feature

# classify a batch of tool calls from a JSON file, all in one request
node src/cli.ts fixtures/tool-calls.json
```

Batch files look like `{ "project_dir": "...", "calls": [{ "id", "tool", "input" }] }`. Output is
one JSON envelope in both modes: `{ "model", "thresholds", "verdicts": [{ "id", "tool", "input",
"label", "triggered", "uncertain", "hazards" }] }`.

```bash
```

| flag / env | default | meaning |
|---|---|---|
| `--fire` / `AUTO_MODE_FIRE` | 0.7 | probability at or above which a hazard holds |
| `--clear` / `AUTO_MODE_CLEAR` | 0.3 | probability below which a hazard is absent |
| `--project-dir` | cwd | directory the command runs in (command mode) |
| `--model` | `jev-latest` | Jev model or alias |

Exit codes: `0` ok · `2` usage/config · `3` API failure.

## Development

```bash
npm run typecheck   # tsc --noEmit, free
npm test            # typecheck, then node --test against the live API (~27k input tokens)
```

The test suite is `test/classifier.test.ts` on `node:test`: it classifies every call in `fixtures/tool-calls.json` in one request and asserts each call's `expected` label. Jev's probabilities drift by a few hundredths between runs, so after changing hazard wording or thresholds run it a few times and fix flakes in the question text, not by widening thresholds. See [AGENTS.md](AGENTS.md) for the conventions.

Known limitation: clearly hostile commands tend to light up unrelated hazards too (`mkfs` scores high on `exposes_secrets`). Labels are unaffected — it only over-fires on calls that are already unsafe — but the reason string for a hard block may list hazards that do not literally apply.

## License

MIT
