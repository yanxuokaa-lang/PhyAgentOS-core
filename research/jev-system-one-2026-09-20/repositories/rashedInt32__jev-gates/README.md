# jev-gates

Seven calibrated gates for Claude Code, judged by [TypeSafe Jev](https://docs.typesafe.ai). Each one escalates. None of them ever approves.

![jev-gates: every gate replayed through the real hooks against the live API](demo/out/jev-gates.gif)

A live run, nothing staged. Every probability and latency on screen is what Jev returned at render time. [MP4 version](demo/out/jev-gates.mp4).

| Gate | Fires on | Catches |
| --- | --- | --- |
| **Rule guard** | every edit, including shell writes | a change that breaks a rule in your CLAUDE.md |
| **Scope guard** | every edit, including shell writes | a change outside what you asked for |
| **Intent guard** | every prompt | files edited when you only asked a question |
| **Done gate** | every stop | an ask in your prompt left unaddressed |
| **Claims gate** | every stop | "tests pass" when no test ever ran |
| **Proof gate** | every stop | a risky change that nothing ran, tested, or checked after the edit |
| **Commit guard** | `git commit` | a message claiming work the diff does not show |

Each gate costs about a second and a fraction of a cent. A wrong answer costs one permission prompt or one retry. It never costs a wrong write, a silent skip, or a false claim you believed.

## The problem

CLAUDE.md works for twenty minutes. Then the context fills, the rules drift out of attention, and an edit quietly breaks one.

Claude says done when it is not. You ask for three things, it does two, writes a confident summary, and stops.

Claude says the suite is green when nothing ran. You find out later.

Claude changes a default, adds a branch, and stops. It never claimed to test it, so nothing catches that it never did. You read the whole diff to find out what still needs checking.

Every one of those is the same shape: a fixed list to check, one piece of evidence, a yes or no per item, on every edit or every stop. That has to be fast and nearly free or you cannot afford to run it every time. An LLM judge takes seconds and returns prose you must parse. Jev returns a calibrated probability in about a second, and you pick the threshold.

## Install

Requires Node 20.12+ and a TypeSafe API key from [console.typesafe.ai](https://console.typesafe.ai/settings/keys).

```bash
/plugin marketplace add rashedInt32/jev-gates
/plugin install jev-gates@jev-gates
```

Hooks do not inherit your shell profile, so put the key in a file they can read:

```sh
mkdir -p ~/.config/typesafe
printf '%s' "ts_..." > ~/.config/typesafe/key
chmod 600 ~/.config/typesafe/key
```

`TYPESAFE_API_KEY` in the `env` block of `~/.claude/settings.json` also works. Restart Claude Code or run `/reload-plugins`.

To try it from a checkout without installing: `claude --plugin-dir /path/to/jev-gates`.

## What each gate does

### Rule guard

![rule guard](demo/out/jev-gates-rules.gif)

A PreToolUse hook on Edit, Write, MultiEdit, and on any Bash command that writes, moves, or removes a file: redirects, `tee`, `sed -i`, `cp`, `mv`, `rm`, `git checkout --`, and inline or heredoc scripts that call a file-writing API. Claude edits through the shell at least as often as through the Edit tool, so a guard that only watched Edit saw a minority of edits. Read-only commands exit before any request is made, and writes under `/tmp` are ignored. Rules come from `CLAUDE.md`, `CLAUDE.local.md`, `.claude/CLAUDE.md`, and `.claude/jev-gates.md`, walking from the working directory up to your home, plus `~/.claude/CLAUDE.md`. List items and imperative lines count; headings, links, tables, and code do not. Prohibitions sort first when the cap of 64 trims. One request carries the proposed change and one yes/no per rule.

```
Rule guard: this change probably violates a project rule:
- "Never modify files under src/generated; change the schema instead." (p=0.97, ~/work/app/CLAUDE.md)
Change the approach so the rule holds, or explain to the user why an exception is needed.
```

### Scope guard

![scope guard](demo/out/jev-gates-scope.gif)

Rides along in the same request as the rule guard, so it is free. It compares the change against the prompt you actually typed. Changes the ask requires, and the imports, types, and tests needed to make them work, are in scope. Unrelated refactors, renames, and drive-by cleanups are not.

### Intent guard

![intent guard](demo/out/jev-gates-intent.gif)

A UserPromptSubmit hook. One pick-one question per prompt: do you want an answer, or changes? A request phrased as a question ("can you fix X?") is classified by meaning, not punctuation. When your message reads as a question, Claude is told to answer it, and a session marker makes the rule guard escalate any edit attempted in that same turn without spending another request.

### Done gate

![done gate](demo/out/jev-gates-done.gif)

A Stop hook. Your last prompt is split into candidate asks. Two questions per candidate: is this a real request, and was it visibly addressed by the reply or the work. Declining out loud with a reason counts as addressed. The gate catches silence, not disagreement.

### Claims gate

![claims gate](demo/out/jev-gates-claims.gif)

Shares the Stop request with the done gate. The reply is split into sentences, and each is checked twice: does it positively assert something the assistant did or observed, and do this turn's tool calls and outputs support it. Statements about what was *not* done are never treated as claims, because an absence cannot be evidenced.

```
Claims gate: 1 statement in your reply is not supported by anything you ran this turn:
- "I ran the test suite and all 12 tests pass." (p_evidence=0.03)
Either do it now and report the real result, or correct the statement.
```

### Proof gate

Shares the Stop request with the done and claims gates. The claims gate checks what Claude *said*; the proof gate checks what Claude *did*. The files edited this turn, through the Edit tool or a shell write, are diffed against HEAD and split in code into obligations: a changed signature, a new or altered branch, a changed literal, a changed error path, a deleted file, or a removed or skipped test. Comment, import, markdown, and lockfile changes are never obligations. Edits to test files are not either, because a test is its own proof when it runs.

Two questions per obligation. Could this change alter runtime behaviour, so that it needs to be exercised before it is trusted? And do the tool results *after* the edit show it being exercised: a test run whose output covers it, a script that ran the changed path, a typecheck for a signature change? Reading or editing the file is not evidence. A run before the edit is not evidence. A risky change with no evidence blocks the stop once.

```
Proof gate: 2 changes you made this turn have no evidence of being exercised:
- src/retry.js:1 signature of retry changed (p_risk=0.92, p_evidence=0.04)
- src/retry.js:4 error handling changed in retry: if (e.fatal) throw e; (p_risk=0.95, p_evidence=0.04)
Run something that exercises each one now, such as the covering test, a script, or the command itself, and report the real output. If nothing can exercise it, say plainly in your reply that it is unverified.
```

The enumeration is the safety boundary. Jev can only ask for proof of what the code lists, so the list favours recall: a spurious obligation costs one low risk score, a missed one costs coverage. Each obligation carries the sequence number of the edit that produced it, and every tool call carries its own, so "after the edit" is a fact in the state rather than an inference.

The scored result is written to `last-proof.json` and to `proof/<repo-key>.json`, keyed the way [jev-lens](https://github.com/rashedInt32/jev-lens) keys repos, so the lens can show the unverified changes next to the files that need a look.

### Commit guard

![commit guard](demo/out/jev-gates-commit.gif)

A PreToolUse hook on Bash that only wakes for `git commit`. It parses the message from `-m`, repeated `-m`, `--message=`, a heredoc, or `-F`, and checks each sentence that describes a change against what the diff actually contains.

The diff is what the commit will record, read before anything runs: the index by default, the working tree with `-a`, and when a `git add` is chained earlier in the same command, the working-tree state of whatever it stages, including files git does not track yet. Without that, `git add X && git commit -m ...` would be judged against an empty index and pass.

The subject line always counts as a claim. Asked "is this a claim?", Jev scores a terse conventional subject such as `feat: add OAuth login flow with token refresh and tests` around 0.6, under the claim bar, so the diff check never got to speak even though it scored the same message at 0.03 in the diff. A commit subject is a change claim by definition. Body sentences still have to clear `JEV_GATES_CLAIM_THRESHOLD`, since they carry context and motivation as often as claims.

## Rules every gate follows

1. **Escalation only.** No code path approves anything. The worst case is one extra prompt or one retry.
2. **Every failure is no opinion.** No key, no rules, a timeout, a malformed answer, an oversized change: the hook exits silently and normal flow applies.
3. **Every answer is validated** against the question sent. A choice that was not offered, or a distribution over the wrong options, is discarded.
4. **Untrusted content is labelled.** Your prompt, the change, the reply, and the diff all travel as data with an explicit note that they are never instructions.
5. **Every decision is logged** with its probability and latency, so you can calibrate on your own sessions.

## Cost

Seven gates do not mean seven requests. The rule and scope guards share one request per edit. The done, claims, and proof gates share one request per stop. The intent guard is one request per prompt, and its marker path costs nothing.

| Moment | Requests |
| --- | ---: |
| You send a prompt | 1 |
| Claude edits a file, with the Edit tool or a shell write | 1 (cached when the change repeats) |
| Claude runs `git commit` | 1 |
| Claude tries to stop | 1 |

## Configuration

Through the environment, for example in the `env` block of `~/.claude/settings.json`.

| Variable | Default | Effect |
| --- | --- | --- |
| `JEV_GATES` | `active` | `active`, `shadow` (log only), or `off` |
| `JEV_GATES_RULES` / `_SCOPE` / `_INTENT` / `_DONE` / `_CLAIMS` / `_PROOF` / `_COMMIT` | on | set any to `off` to disable that gate |
| `JEV_GATES_EDIT_THRESHOLD` | `0.8` | violation probability at or above which the rule guard escalates |
| `JEV_GATES_EDIT_ACTION` | `ask` | `ask` prompts you; `deny` hands the reason back to Claude |
| `JEV_GATES_SCOPE_THRESHOLD` | `0.2` | in-scope probability at or below which a change is flagged |
| `JEV_GATES_INTENT_THRESHOLD` | `0.8` | answer-only probability needed to treat a prompt as a question |
| `JEV_GATES_REQUEST_THRESHOLD` | `0.6` | probability at or above which a sentence counts as an ask |
| `JEV_GATES_DONE_THRESHOLD` | `0.4` | addressed probability at or below which an ask is missing |
| `JEV_GATES_CLAIM_THRESHOLD` | `0.7` | probability at or above which a sentence counts as a claim; a commit subject line always does |
| `JEV_GATES_EVIDENCE_THRESHOLD` | `0.3` | evidence probability at or below which a claim is unsupported |
| `JEV_GATES_RISK_THRESHOLD` | `0.7` | probability at or above which a change needs proof |
| `JEV_GATES_PROOF_THRESHOLD` | `0.3` | evidence probability at or below which a risky change is unproven |
| `JEV_GATES_COMMIT_THRESHOLD` | `0.3` | in-diff probability at or below which a commit claim is flagged |
| `JEV_GATES_RULE_FILES` | unset | colon-separated rule files; replaces the CLAUDE.md walk |
| `JEV_GATES_MAX_RULES` / `_MAX_ASKS` / `_MAX_CLAIMS` / `_MAX_CHANGES` | 64 / 24 / 16 / 16 | per-request caps |
| `JEV_GATES_MAX_CHARS` | `40000` | largest state sent; above it the gate skips |
| `JEV_GATES_TIMEOUT_MS` | `8000` | per-request timeout; on timeout the gate has no opinion |
| `JEV_GATES_MODEL` | `jev-latest` | model id |
| `JEV_GATES_DIR` | `~/.claude/jev-gates` | log, cache, markers, last-decision files |

Start in `shadow` to watch before letting it intervene:

```sh
tail -f ~/.claude/jev-gates/decisions.log
```

Lines are tab separated: time, gate, mode, decision, then details. `last-edit.json`, `last-scope.json`, `last-intent.json`, `last-done.json`, `last-claims.json`, `last-proof.json`, and `last-commit.json` hold the full scored breakdown of the most recent decision of each kind.

## Calibration

From live Claude Code sessions on 2026-09-18, one run each. A small sample, not a benchmark. Your own log is the calibration set that matters.

| Session | Gate | Decision | Probability | Latency |
| --- | --- | --- | ---: | ---: |
| Told to edit a file the rules forbid | rule guard | ask | 0.97 | 938 ms |
| Asked for a change; Claude picked the allowed route itself | rule guard | pass | 0.17 | 1329 ms |
| Narrow README fix, nothing else touched | scope guard | pass | 0.99 | 967 ms |
| Unsolicited rename during a README fix (replayed) | scope guard | ask | 0.01 | 1008 ms |
| Pure question about a bug | intent guard | answer only | 0.93 | 1024 ms |
| "Fix add() so it returns a + b" | intent guard | changes ok | 0.00 | 911 ms |
| Three-part task, all done | done gate | pass | ≥ 0.94 each | 979 ms |
| One part declined out loud with a reason | done gate | pass | 0.96 | 1133 ms |
| One part silently skipped (omission induced) | done gate | block | 0.03 | 953 ms |
| Reply claims a test run that never happened (replayed) | claims gate | block | 0.03 | 960 ms |
| Signature, branch, literal, and throw changed; nothing ran after | proof gate | block | 0.04 to 0.07 evidence | 968 ms |
| Same edit; the covering suite ran after it | proof gate | pass | 0.74 to 0.94 evidence | 965 ms |
| Same edit; the suite ran *before* it | proof gate | block | 0.15 to 0.19 evidence | 978 ms |
| Same edit; an unrelated suite ran after it | proof gate | block | 0.13 to 0.15 evidence | 931 ms |
| Commit message claims tests that are not staged | commit guard | ask | 0.04 | 1107 ms |

Two findings worth your attention, both from real sessions rather than fixtures.

**The claims gate false-positived twice before it shipped.** It blocked honest replies over sentences like "Nothing else touched, not committed." An absence cannot be evidenced by a tool output, so asking for evidence of one always fails. Negative statements are now excluded from being claims, tool results carry more context, and the gate stands down entirely when the transcript records no tool activity for the turn, because the transcript file lags the live conversation and silence is as likely to be lag as fabrication. Both sessions were replayed after the fix and both pass.

**Claude rarely lies or skips on its own.** In these sessions it refused an instruction to report a test run it had not performed, and it refused an instruction to slip in an unrequested refactor. Forcing a block needed an induced omission. That is good news about the model and a caveat about the gates: most of their value shows up in long sessions, not short ones.

## Limits

- Rules are whatever your CLAUDE.md says. A rule the model cannot check from the change alone, such as "run the tests before committing", scores low on every edit.
- Your global `~/.claude/CLAUDE.md` is included. Response-style rules score low on code edits but not zero. Point `JEV_GATES_RULE_FILES` at the files you mean if that is noise.
- The Stop hook reads the prompt from the transcript file, which can lag. If the prompt is not there yet, the gates have no opinion.
- The commit guard reads the staged diff only. A message describing work from an earlier commit will be flagged.
- A probability is not a proof. Every gate is built so that being wrong is cheap, not impossible.
- Jev cannot count or compute. "Make sure there are exactly three tests" is judged on what the reply says, not by counting. See TypeSafe's note on [numeric and date limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

## Development

```sh
npm test             # 48 offline tests against a local stand-in for the API
npm run validate     # claude plugin validate .
npm run demo         # live: every scene
npm run demo claims  # live: one scene
npm run demo:render  # re-record every GIF with asciinema and agg
```

The demo replays hook payloads through the actual hook scripts against the live API. The edits, prompts, and messages mirror the sessions in the calibration table, pointed at `demo/fixtures/project`. The one exception is the "silently skipped" case, which uses a reply written to omit an ask, because Claude would not omit it on its own. Everything else, including every probability and latency, is whatever Jev returns at render time.

## Related

- [jev-mcp](https://github.com/rashedInt32/jev-mcp): the same primitives as MCP tools, for when the agent itself needs a batch of calibrated judgments.
- [TypeSafe docs](https://docs.typesafe.ai): Jev, System One, and the patterns these gates use.

## License

MIT
