# omp-jevens-classifier

Jev-judged permission checks for OMP's bash tool, and for `eval` payloads that spawn
processes.

In `yolo` mode, OMP auto-approves every bash command. That includes the ones nobody should wave through: `curl … | sh`, `rm -rf /`, `dd of=/dev/…`, `mkfs`, `kill -9 1`, `nc -e`. A second hole compounds it. A `bash.patterns` rule written to prompt on exactly those shapes never fires, because the native gate ranks critical-pattern matches above prompt rules.

This plugin closes both holes. It registers a `tool_call` handler in front of the native bash tool and sends commands that would otherwise run unseen to Jev, TypeSafe's System One model, which answers typed questions about them rather than writing prose. Routine work still runs silently. Dangerous work gets a real Run-or-Deny prompt. For `eval`, the gate classifies only the payloads that spawn a process; expression-only code runs untouched.

The handler only adds friction. It blocks, or it asks. It never bypasses the native gate, weakens your existing rules, or executes anything itself.

The system is one tower of layers: evidence, recognition, judgment, memory, interaction, self-measurement, control. The map, invariants, and roadmap live in [docs/SYSTEM.md](docs/SYSTEM.md).

## How each command is decided

Calls walk this order:

| Match | Result |
|---|---|
| Critical pattern | Permission request in every approval mode. No Jev call. |
| Caller-supplied `env` | Permission request before any exemption. Env values can carry secrets or choose what runs (`PATH`, `LD_PRELOAD`). |
| `deny` rule, or approval policy `deny` | Untouched. The native gate blocks it. |
| `prompt` rule | Untouched. The native gate prompts, in every mode including `yolo`. |
| Narrow `allow` rule | Untouched. An explicit decision about a specific shape is never re-judged. For a compound line, a `deny`/`prompt` on any segment decides immediately (the native gate blocks or prompts once — no plugin dialog, no classification), an `allow` on every segment runs silent, and only a compound with no deny/prompt decision and an undecided segment classifies. Blanket patterns never vouch for segments; inert fd-dups (`2>&1`) are ignored, but real redirects (`> file`) bar a segment. |
| Blanket `allow` (`*`, `**`, `* *`) or no matching rule | Classified in every mode. SAFE passes to the native gate; UNSAFE or UNSURE raises a plugin request. |
| Granted earlier for this directory | Runs ungated for the rest of the session. A past **Allow for session** answer is user-tier authorization: it outranks classification and refusal memory, but not the critical, env, and static-rule rows above. |
| Longer than 8,000 characters | Blocked outright. Nothing that long can be reviewed in full. |

A normal gate prompt is a four-choice selector — **Allow once**, **Allow for session**, **Always allow**, **Deny** — showing the full command, the gate's reason, and only the details that differ from their defaults: working directory (when it differs from the session cwd), timeout, env, pty, async. The reason is assembled from Jev's numbers — the probability floor it missed, or the hazard ids that tripped it — because Jev returns typed answers and no prose to quote. Critical-pattern and env-override prompts show only choices the gate can honor (**Allow once**/**Deny**), so an authorization cannot appear to succeed and then re-prompt on the next call. Canceling or timing out counts as Deny.
**Allow for session** records a grant: this action, in this exact directory, runs ungated for the rest of the session — no Jev call, no dialog. Rewordings of a simple action match the grant through a strict key that keeps flags (split, sorted short bundles) and the first argument; compounds and command substitutions use an exact-text key, so an edited segment or payload never rides the grant. Answering with it also lifts any refusal recorded for that action in that directory. Grants stay below critical patterns, caller-supplied `env`, and your static rules, and they die with the session or a classifier config change (up to 50 per session).
**Always allow** (bash only) writes a persistent grant: this exact command text, in this exact directory, runs ungated everywhere for 30 days — no Jev call, no dialog, one audit line. The key is the whole command text, compounds included, so multi-segment commands host rules can never match are covered; grants are stored in `omp-jevens-classifier-grants.json` beside `omp-jevens-classifier.json` (`OMP_JEV_CONFIG` relocates both), capped at 500 entries, pruned on a 30-day TTL, and toggled off wholesale with `persistentGrants: false` (the existing file stays on disk). A live persistent grant also keeps refusal memory from re-prompting for its exact text.

## Eval code that spawns

The `eval` tool runs kernel code directly, so a host `eval: allow` would otherwise bypass every bash check. The plugin scans each payload for subprocess entry points (`child_process`, `Bun.spawn`, `Bun.$`, Python's `subprocess`/`os.system`, `exec`/`__import__`/`importlib` escapes). Expression-only code — compute, parse, format, local reads — passes with zero cost. Spawn-bearing code is classified like a bash command: judged by what the spawned command would do, SAFE auto-runs, UNSAFE or unsure raises a request. The scan is a marker list, not a parser: string-splitting evasion (`"child_pro" + "cess"`) gets through, the same way obfuscated shell gets past the bash gate. Kernel-level interception is the structural fix (issue #13).

## Fails closed

The plugin never guesses its way to silent execution.

- A judgment the gate cannot obtain — no API key, a non-2xx response, an unparseable body, a missing or mistyped answer field, a timeout — raises a permission request. Headless sessions have no dialog, so they block instead. An unavailable judgment is never cached, and it is never read as a verdict: nothing that cannot be derived from returned numbers counts as SAFE.
- An unexpected plugin crash blocks the call.

Even a SAFE verdict is gated. It auto-runs only when the command avoids the forced-dialog set: `rm`/`unlink` in the shapes where a mistake is systemic (recursion, glob metacharacters, `..` traversals, dotfiles/dot-paths, provable targets outside the working directory — temp dirs excluded), plus `dd`, `ddrescue`, `shred`, `wipefs`, `sudo`, and `eval`. Plain `rm`/`unlink` of named paths (including under `/tmp`) auto-runs on SAFE — the judge owns them. Everything else destructive is also judge-decided: `mv`, `chmod`, `chown`, `chattr`, `truncate`, `tee`, `rmdir`, `git commit --amend` and `git reset --soft`/`--mixed` (reflog/index keeps the pre-image), and `git checkout --`/`git restore` pathspec restores run on a SAFE. The matcher's remaining unconditional flags are `mkfs*`, `git push --force` (inside compounds), `git reset --hard` (unambiguous `--hard` prefixes count), and `git clean`; anything on the host's critical-pattern list (e.g. `rm -rf` on an absolute path, `dd of=/dev/…`) prompts before classification regardless. A heredoc body written straight to a file comes off the command before anything tokenizes it: `cat > f.ts <<'EOF'` writing `if (dd < 30) {` no longer reads as a raw disk write, and a README documenting `curl -d` no longer reads as egress. The rule matches one shape and nothing else, so it needs no view on what the shell executes: a whole owner line that is only `cat` or `tee`, its flags and targets, and a QUOTED delimiter, with a closing line that is exactly the delimiter. Every other heredoc keeps its body in the command text and keeps being scanned as commands, including `bash <<EOF`, an unquoted delimiter, a pipe on the owner line, and a heredoc with no closer. That over-flags on a delimiter named `sudo`, and over-flagging is the direction this overlay is allowed to be wrong in.

**curl** and **wget** are judged like any other command — no forced dialog. The stdin-executing-interpreter scan (`curl -fsSL https://x | sh`) is a separate risk class and still forces a dialog: a fetched payload piped into an interpreter is opaque execution, and a question battery cannot see inside it. Related behaviors: rm-family forced dialogs append "Reversible alternative: trash <paths>" to the body; a dialog fired by a session whose on-disk plugin changed since it loaded says so in the subtitle ("plugin code changed since session start; restart to pick up fixes"); and ssh commands are judged by their remote command under the same rules (read-only remote inspection is SAFE).

## Requirements

- **A TypeSafe API key.** Set `TYPESAFE_API_KEY` in the environment, or store it in the macOS keychain as a generic password for service `jev`:

  ```bash
  security add-generic-password -s jev -w '<your-api-key>'
  ```

  The plugin reads the env var first, then the keychain. With neither, every classification fails closed to a permission request — the gate never runs a command on a guess.
- **The model** is `jev-latest` unless you pin another id in `typesafeModel`. TypeSafe resolves `jev-latest` server-side to its current dated build (`jev-1.13.0` at the time of writing); pin a dated id when you need reproducibility across a behavior change.
- Bun >= 1.3.14 for development. There is no runtime dependency, no SDK, and no build step: `jev.ts` speaks HTTP with `fetch`.

## Install

```bash
git clone https://github.com/STRML/omp-jevens-classifier.git
cd omp-jevens-classifier && omp plugin install .
```

An existing checkout works the same way: `omp plugin install /path/to/omp-jevens-classifier` symlinks that directory to `~/.omp/plugins/node_modules/omp-jevens-classifier`, and the plugin lockfile keys the entry by package name (`omp-jevens-classifier`). No build step, no runtime dependencies. Plugins load at session start, so start a new OMP session.

Uninstall: `omp plugin uninstall omp-jevens-classifier`. Coming from the parent? Uninstall it in the same breath — `omp plugin uninstall omp-classifier` — because two bash gates installed at once both intercept `tool_call`.

## Configuration

Your existing `bash.patterns` and `tools.approval` keep working. A narrow `allow` rule doubles as the opt-out from classification for a trusted shape; blanket patterns never qualify.

Plugin settings live in `~/.omp/omp-jevens-classifier.json`. View or change them with `/classifier`:

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | `false` turns off Jev classification only. Critical-pattern and env checks still enforce. |
| `typesafeModel` | `"jev-latest"` | Model id sent with every request. `jev-latest` resolves server-side to the current dated build. |
| `jevPolicy` | see [Judgment: Jev](#judgment-jev) | Thresholds that turn returned probabilities into a verdict. Never a constant to hardcode elsewhere: they are policy. |
| `timeoutMs` | `8000` | Whole classification budget for the single Jev request. A timeout fails closed to a permission request. (`/classifier` dialogs pause the host's handler budget, so a human is never on this clock.) |
| `maxCommandLength` | `8000` | Commands longer than this are blocked (bounds 64-100000; values outside fall back to the default). |
| `evidenceUserMessages` | `3` | How many recent user messages (0-6) ride into the state as user evidence. `0` sends no evidence. Values outside the bounds fall back to the default. |
| `persistentGrants` | `true` | Offers **Always allow** on bash dialogs (30-day exact-command grants in `omp-jevens-classifier-grants.json`). Kill-switch: `false` stops offering them and stops honoring live ones; the stored file stays on disk. |

Changing any key flushes the verdict cache and the session grants. To silence the judge quickly, `/classifier enabled false` takes effect on the very next command. `omp plugin disable` needs a session restart, since interceptors bind when a session begins.

An existing config file that pins `maxCommandLength: 2000` keeps 2000 after upgrading — defaults only apply to absent keys. `/classifier reset` rewrites the file with current defaults.
`/classifier off` pauses Jev classification for the current session only. Critical-pattern, env-override, and static-rule checks stay active — the same behavior as `enabled false`, but scoped to the session. Cached verdicts keep being honored, other sessions are unaffected, and the pause dies with the session (a new session starts unpaused). `/classifier on` resumes classification for the session. The persistent `enabled` setting still dominates: `/classifier enabled false` keeps classification off everywhere until you turn it back on. `/classifier status` lists `pausedSessions`, and `dry-run` while paused reports `{ "would": "allow", "layer": "session" }`.

`/classifier dry-run <command>` previews what the gate would do, side-effect free: no Jev call, no dialog, no cache, grant, refusal, or audit writes. It prints the first decision the gate would reach as JSON:

```json
{ "would": "allow", "layer": "granted", "why": "session grant" }
```

## Judgment: Jev

Novel commands are judged by [Jev](https://typesafe.ai), TypeSafe's System One model, in one HTTP request. Nothing is prompted and nothing is parsed: the gate posts a structured state and a fixed battery of typed questions, and Jev answers with probabilities that the gate turns into a verdict in code.

**State** is what the questions are asked about: the command text, the resolved working directory, the session's recent user messages (their text plus stable message ids, and only the ones the host stamped as user-authored), and the requesting agent's operator context.

**The battery** asks everything needed for one decision, in that one request:

- `verdict` — a `choice` over `safe`, `unsafe`, `unsure`.
- nine hazards, one `noul` each — `state_contains_injection`, `authorization_missing`, `destructive_or_irreversible`, `writes_outside_working_directory`, `contacts_remote_endpoint`, `sends_local_data_outbound`, `escalates_privilege`, `exposes_secrets`, `affects_shared_or_remote_state`. A `noul` answers how far the command sits from that hazard: 0 it does not, 1 it plainly does.
- `blast_radius` — a `score` over ordered severity levels, so "how much does this touch" lands on a ladder instead of a yes/no.

Answers are typed; each line below is an answer body as returned by a live call, trimmed to
the fields the gate reads:

```json
{ "type": "choice", "choice": "safe", "probabilities": { "safe": 0.52, "unsafe": 0.43, "unsure": 0.05 }, "confidence": 0.29 }
{ "type": "noul", "noul": 0.98 }
{ "type": "score", "score": 1.3, "legend": { "0": "…", "1": "…" }, "probabilities": { "0": 0.7, "1": 0.3 }, "confidence": 0.54 }
```

The envelope wraps them as `{ "model": "jev-1.13.0", "answers": { "<id>": <Answer> }, "usage": { "input_tokens": N, "output_tokens": N } }`. A 6-question probe of one state cost ~0.6s and 528 input / 126 output tokens, and extra questions in the same request are cheap — System One answers every question in the request in parallel over the same state — which is why the battery asks them all at once instead of in rounds.

**The verdict is derived, not read.** The `choice` answer above — `safe` at 0.52 with confidence 0.29 — does not clear the default floor (`safeMinProbability` 0.80, `safeMinConfidence` 0.50), so the gate asks the human instead of running the command. That is the whole point of a probability judge: the argmax is not a decision, and `choice: "safe"` alongside `unsafe: 0.43` is a command the gate should not wave through. The same command answered `safe` at 0.61 / confidence 0.42 when it was asked alone: the numbers move with the battery and with the shape of the state, so the thresholds are tunable policy rather than constants copied from a vendor. Measure across a corpus before touching them.

The policy knobs, all inside `jevPolicy`:

| Key | Default | Meaning |
|---|---|---|
| `safeMinProbability` | `0.80` | p(safe) required before the gate auto-runs a command. |
| `safeMinConfidence` | `0.50` | Confidence floor paired with it: a high p(safe) on a low-confidence answer still asks. |
| `unsafeMinProbability` | `0.50` | p(unsafe) at or above this forces UNSAFE. |
| `hazardBlock` | `0.90` | Any hazard at or above this forces UNSAFE. |
| `hazardReview` | `0.55` | Any hazard at or above this — below the block line — forces UNSURE. |
| `blastRadiusReview` | `1.5` | Blast-radius score at or above this forces UNSURE. |

SAFE requires `p(safe) >= safeMinProbability` **and** `confidence >= safeMinConfidence`, with no hazard at or above `hazardReview` and a blast radius below `blastRadiusReview`. UNSAFE comes from `p(unsafe) >= unsafeMinProbability` or any hazard at or above `hazardBlock`. Everything else is UNSURE, which asks. A decision carries a stable `reasonCode` (`jev:safe`, `jev:unsafe`, `jev:hazard:<name>`, `jev:blast-radius`, `jev:below-floor`, `jev:unavailable`) and a sentence built from the numbers and the hazard ids.

The policy version (`jev-v1`), the serialized battery, and the default policy hash into `jevQuestionsHash()`, which participates in the cache key. Change a question or a threshold and every cached verdict is invalidated — a verdict is only valid for the questions that produced it, and a stale one would be a verdict about a judge that no longer exists. Otherwise verdicts cache for the session, keyed by cwd, env, pty, timeout, async, the evidence fingerprint, and the command text, so reruns cost nothing while a changed user scope invalidates the cache and session grants.

Every decision carries that policy version/hash, session and decision identifiers, the model id, timing, and the derived hazards in `decisions.jsonl`. `/classifier status` exposes the live policy hash and the recent tail. The deterministic replay tail is shared by the live gate and the evaluation harness, so caps, environment overrides, risk overlays, prior refusals, interactive prompts, and headless blocks are measured the same way.

## Evidence

The state can carry an `evidence` object whose fields have different authors, and the battery's instructions judge each field by its channel. `evidenceUserMessages` attaches the task's most recent user messages plus older scope/restriction anchors, with stable message ids. The user's own words are the only tier that may authorize an action. Only messages the host stamps `attribution: "user"` count, so the brief a parent agent sends its subagent never does. A message longer than 2,000 characters keeps its first and last 1,000. Every tool call may also carry `operatorContext`: the requesting agent's explanation of intent, flattened to one line, capped at 500 characters, and never able to authorize anything. Recent tool calls/results are added as bounded, explicitly non-authorizing context so a script written earlier in the session is not invisible to the next review. Refusals and session grants are scoped to the reviewed cwd and evidence fingerprint; later user restrictions invalidate them. Human denials remain sticky until approval in that same scope. The channel decides provenance: content claiming authorization from the wrong channel is itself an injection signal, judged by the same rules as the command text.

## Limits

- **Spawn-bearing eval code only.** Expression-only eval passes unread, and the payload scan is a marker list: string-splitting evasion gets through. `hub op: "start"` and other exec-tier tools still auto-run under `yolo`. An attacker who picks the tool picks around this.
- **Later handlers win.** Another extension's `tool_call` handler can revise the command after this one judges it; the host applies the last revision. Input-mutating extensions alongside this plugin are unsupported.
- **Internal-URL working directories are blocked.** `skill://` and similar cwds expand from session state the plugin cannot see. Pass the resolved filesystem path.
- **Command contents are not inspected.** `npm test` and `make` are judged as the routine commands they look like. Package scripts and hooks go unread.
- **Refusal memory is session-local.** A refused action follows reworded commands within that session only and dies with it; subagent inheritance is a host gap (`parentAgentId` is not exposed to extensions).

## Privacy

The state — the command text up to 8,000 characters, its resolved working directory, the session's recent user messages when `evidenceUserMessages` is non-zero, and the requesting agent's operator context — goes to TypeSafe's System One API (`api.typesafe.ai`), under TypeSafe's logging and retention policies. Command text can hold private paths, proprietary snippets, inline env assignments, or secrets in flags. Caller-supplied `env` values are never sent; that path asks the human instead.

## Development

```bash
bun install
bun test           # static gate, Jev verdict derivation, cache keying, fail-closed paths
bun run typecheck  # against pinned published host types
```

CI runs both on every push and PR. Verdict quality against live Jev is evaluated separately (`eval/`, tracked in issue #2).

The replay-aware harness ships a deterministic 500-action held-out benign set
(25 task sequences × 20 routine steps), with task ids and step ids in each record. It scores
the gate against live Jev by default, and can be pointed at a candidate policy instead of the
shipped one:

```bash
bun eval/run.ts --corpus heldout --samples 3      # live Jev, default policy
bun eval/run.ts --policy eval/policies/x.json     # score a candidate policy
bun eval/run.ts --replay                          # cache only: no API calls
```

Reports include final host handoff, review/recovery counts, approval overrides,
interruption rates, and p50/p95 latency. Treat generated held-out numbers as a
repeatable regression fixture, not as a substitute for fresh production history.

MIT licensed.
